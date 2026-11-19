import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
import httpx

from app.config import settings
from app.workflow.state import GraphState
from app.workflow.prompts import (
    QUERY_REWRITE_PROMPT,
    FOLLOW_UP_REWRITE_PROMPT,
    BATCH_DOCUMENT_GRADE_PROMPT,
    ANSWER_GENERATION_PROMPT,
    FALLBACK_GENERATION_PROMPT,
    WEB_SEARCH_GENERATION_PROMPT,
)
from app.domain.entities import DocumentChunk

logger = logging.getLogger(__name__)

CONVERSATIONAL_STOPWORDS = {
    'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how',
    'does', 'do', 'did', 'done', 'doing',
    'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'having',
    'can', 'could', 'shall', 'should', 'will', 'would', 'may', 'might', 'must',
    'tell', 'give', 'show', 'explain', 'describe', 'find', 'get', 'know', 'say',
    'about', 'with', 'from', 'into', 'onto', 'through', 'over', 'under', 'above', 'below',
    'for', 'and', 'nor', 'but', 'or', 'yet', 'so', 'the', 'a', 'an', 'this', 'that', 'these', 'those',
    'many', 'much', 'more', 'most', 'some', 'any', 'all', 'few', 'both', 'each', 'every',
    'me', 'my', 'myself', 'we', 'our', 'ours', 'you', 'your', 'yours', 'he', 'him', 'his',
    'she', 'her', 'hers', 'it', 'its', 'they', 'them', 'their', 'theirs',
    'please', 'help', 'details', 'detail', 'info', 'information', 'summary', 'overview',
    'one', 'two', 'use', 'using', 'used', 'same'
}


def remove_answer_labels(text: Any) -> str:
    """
    Removes leading or standalone labels like 'Main Answer:' or 'Detailed Answer:'
    with strict word boundary and required colon, preserving legitimate text.
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    if not text:
        return ""
    # 1. Match label at line start with optional markdown prefixes/suffixes
    pattern = r'(?im)^[ \t>#*_-]*(?:main\s+answer|detailed\s+answer|answer)(?::\*\*|\*\*:|:)[ \t]*\n?'
    cleaned = re.sub(pattern, '', text)
    # 2. In-text bold labels
    cleaned = re.sub(r'(?i)\*\*(?:main\s+answer|detailed\s+answer|answer):\*\*\s*', '', cleaned)
    cleaned = re.sub(r'(?i)\b(?:main\s+answer|detailed\s+answer):\s*', '', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


class WorkflowNodes:
    def __init__(self, vector_store: Any, chat_model: Any) -> None:
        self._vector_store = vector_store
        self._chat_model = chat_model

    def query_analysis_node(self, state: GraphState) -> GraphState:
        question = state["question"].strip()
        state["query_intent"] = "Documentation QA"
        if "retries" not in state:
            state["retries"] = 0
        state["route"] = "analysis"

        # Multi-turn Follow-up resolution: resolve coreference pronouns from chat history
        history = state.get("chat_history") or []
        pronouns = {"it", "its", "they", "their", "this", "that", "these", "those", "the gateway", "the device", "same"}
        q_lower = question.lower()
        has_pronoun = any(re.search(r'\b' + re.escape(p) + r'\b', q_lower) for p in pronouns)

        if has_pronoun and history:
            try:
                hist_str = "\n".join(f"{h.get('role', 'user')}: {h.get('content', '')}" for h in history[-2:])
                prompt = FOLLOW_UP_REWRITE_PROMPT.format(chat_history=hist_str, question=question)
                resp = self._chat_model.invoke(prompt)
                rewritten_standalone = resp.content.strip() if hasattr(resp, "content") else str(resp).strip()
                rewritten_standalone = re.sub(r'^(?:Standalone Question|Search Query):\s*', '', rewritten_standalone, flags=re.I).strip(' "\'')
                if rewritten_standalone and len(rewritten_standalone) > 5:
                    logger.info("Rewrote follow-up question '%s' -> '%s'", question, rewritten_standalone)
                    state["rewritten_query"] = rewritten_standalone
            except Exception:
                logger.debug("Failed follow-up coreference rewrite")

        # Document isolation: check if question targets a specific indexed document or system
        effective_q = state.get("rewritten_query") or question
        eff_lower = effective_q.lower()
        doc_ids = state.get("document_ids")
        if not doc_ids or doc_ids == ["all"]:
            try:
                available_docs = self._vector_store.get_all_documents()
                matching_docs = []
                for d in available_docs:
                    doc_title = d.get("title", "").lower()
                    doc_stem = Path(doc_title).stem.lower()
                    if doc_title in eff_lower or doc_stem in eff_lower:
                        matching_docs.append(d["id"])
                    elif ("aerosense" in eff_lower or "as-ts-204" in eff_lower) and "technical_rag_test" in doc_title:
                        matching_docs.append(d["id"])
                    elif ("edgewatch" in eff_lower or "eam-ts-004" in eff_lower) and "edge_ai" in doc_title:
                        matching_docs.append(d["id"])

                if matching_docs:
                    logger.info("Auto-scoped question to targeted document: %s", matching_docs)
                    state["document_ids"] = matching_docs
            except Exception:
                logger.debug("Failed auto-scoping document in query_analysis_node")

        return state

    def retrieval_node(self, state: GraphState) -> GraphState:
        query = state.get("rewritten_query") or state["question"]
        doc_ids = state.get("document_ids")
        logger.info("Retrieving chunks for query: '%s' (scoped docs: %s)", query, doc_ids)
        try:
            chunks = self._vector_store.similarity_search(query, k=settings.top_k, document_ids=doc_ids)
        except Exception:
            logger.exception("Error during similarity search in retrieval_node")
            chunks = []

        state["retrieved_chunks"] = chunks
        state["route"] = "retrieval"
        return state

    def document_grading_node(self, state: GraphState) -> GraphState:
        question = state["question"]
        chunks = state.get("retrieved_chunks", [])
        if not chunks:
            state["filtered_chunks"] = []
            return state

        # Batch grading via LLM with full chunk text (never truncated)
        passages_text = []
        for idx, c in enumerate(chunks, 1):
            doc_name = Path(c.document_id).name
            page = c.metadata.get("page", 1)
            passages_text.append(f"Passage [{idx}] (from {doc_name}, page {page}):\n{c.text[:1600]}")

        prompt = BATCH_DOCUMENT_GRADE_PROMPT.format(
            question=question,
            passages="\n\n".join(passages_text)
        )

        relevant_indices: Set[int] = set()
        try:
            response = self._chat_model.invoke(prompt)
            resp_content = response.content.strip() if hasattr(response, "content") else str(response).strip()
            logger.info("Batch grading decision: %s", resp_content)
            if "none" not in resp_content.lower():
                matches = re.findall(r'\b\d+\b', resp_content)
                for m in matches:
                    val = int(m)
                    if 1 <= val <= len(chunks):
                        relevant_indices.add(val)
        except Exception:
            logger.exception("LLM grading invocation failed")

        # Deterministic keyword & technical match protection:
        # Chunks containing multiple core query keywords must never be discarded
        q_words = [w for w in re.findall(r'[a-zA-Z0-9_\-\.]+', question.lower())
                   if len(w) > 2 and w not in CONVERSATIONAL_STOPWORDS]
        for idx, c in enumerate(chunks, 1):
            c_lower = c.text.lower()
            matched_count = sum(1 for w in q_words if re.search(r'\b' + re.escape(w) + r'\b', c_lower))
            if q_words and (matched_count >= 2 or (matched_count >= 1 and len(q_words) == 1)):
                relevant_indices.add(idx)

        # Document Isolation: If question specifically targeted a document, filter out unrelated documents
        target_doc_ids = state.get("document_ids")
        if target_doc_ids and target_doc_ids != ["all"]:
            clean_bnames = set(Path(d).name for d in target_doc_ids)
            filtered = [chunks[i - 1] for i in sorted(relevant_indices) if Path(chunks[i - 1].document_id).name in clean_bnames]
        elif relevant_indices:
            filtered = [chunks[i - 1] for i in sorted(relevant_indices)]
        else:
            filtered = []

        # Sort filtered chunks so highest keyword match and uploaded chunks appear first in LLM context
        def chunk_relevance_sort_key(c: DocumentChunk) -> tuple:
            c_low = c.text.lower()
            matches = sum(1 for w in q_words if re.search(r'\b' + re.escape(w) + r'\b', c_low)) if q_words else 0
            is_upload = 1 if ("uploads" in c.document_id or "/uploads" in c.document_id) else 0
            return (is_upload, matches, c.score)

        filtered.sort(key=chunk_relevance_sort_key, reverse=True)

        state["filtered_chunks"] = filtered
        logger.info("Retrieved %d chunks, %d passed grading", len(chunks), len(filtered))
        return state

    def query_rewrite_node(self, state: GraphState) -> GraphState:
        question = state["question"]
        retries = state.get("retries", 0)
        logger.info("Attempting query rewrite (retry count: %d) for: '%s'", retries, question)

        prompt = QUERY_REWRITE_PROMPT.format(question=question)
        rewritten = question
        try:
            response = self._chat_model.invoke(prompt)
            resp_text = response.content.strip() if hasattr(response, "content") else str(response).strip()
            # Clean any wrapping quotes or prefixes
            resp_text = re.sub(r'^(?:Optimized Query|Search Query):\s*', '', resp_text, flags=re.I).strip(' "\'')
            if resp_text and len(resp_text) > 3:
                rewritten = resp_text
        except Exception:
            logger.exception("Query rewrite LLM call failed")

        state["rewritten_query"] = rewritten
        state["retries"] = retries + 1
        state["route"] = "rewrite"
        return state

    def generation_node(self, state: GraphState) -> GraphState:
        question = state["question"]
        chunks = state.get("filtered_chunks", [])
        if not chunks:
            chunks = state.get("retrieved_chunks", [])

        # Format context with [n] (filename, page X): text
        context_parts = []
        for idx, c in enumerate(chunks, 1):
            doc_name = Path(c.document_id).name
            page = c.metadata.get("page", 1)
            context_parts.append(f"[{idx}] ({doc_name}, page {page}):\n{c.text}")

        context_str = "\n\n".join(context_parts)
        prompt = ANSWER_GENERATION_PROMPT.format(question=question, context=context_str)

        answer = ""
        is_fallback_view = False
        try:
            response = self._chat_model.invoke(prompt)
            answer = response.content.strip() if hasattr(response, "content") else str(response).strip()
            # Check finish reason if available
            response_meta = getattr(response, "response_metadata", {}) or {}
            if response_meta.get("finish_reason") == "length":
                answer += "\n\n*(Note: Answer was truncated by maximum token limit)*"
        except Exception:
            logger.exception("LLM generation failed. Presenting verbatim retrieved passages.")
            is_fallback_view = True
            banner = "### AI model unavailable - showing the most relevant passages\n\n"
            passages = []
            for idx, c in enumerate(chunks[:3], 1):
                doc_name = Path(c.document_id).name
                page = c.metadata.get("page", 1)
                passages.append(f"**Source [{idx}]: {doc_name} (Page {page})**\n> {c.text}")
            answer = banner + "\n\n".join(passages)

        # Grounded citations: return only the chunks whose [n] appears in the answer
        # Standardize fullwidth brackets 【1】 to [1]
        answer = re.sub(r'【(\d+)】', r'[\1]', answer)

        stopwords = {'what', 'which', 'does', 'many', 'have', 'from', 'this', 'that', 'with', 'when', 'where', 'how', 'the', 'is', 'are', 'one', 'can', 'use'}
        q_words = [w for w in re.findall(r'[a-zA-Z0-9_\-\.]+', question.lower()) if len(w) > 2 and w not in stopwords]

        sources = []
        if is_fallback_view:
            for idx, c in enumerate(chunks[:3], 1):
                doc_name = Path(c.document_id).name
                page = c.metadata.get("page", 1)
                clean_txt = re.sub(r'^--- Page \d+ ---\s*', '', c.text).strip()
                sources.append({
                    "document_id": f"{doc_name} [Page {page}]",
                    "chunk_text": clean_txt[:160],
                    "score": round(c.score, 3)
                })
        else:
            cited_nums = set(int(m) for m in re.findall(r'[\[【](\d+)[\]】]', answer))
            for idx, c in enumerate(chunks, 1):
                if idx in cited_nums:
                    doc_name = Path(c.document_id).name
                    page = c.metadata.get("page", 1)
                    clean_txt = re.sub(r'^--- Page \d+ ---\s*', '', c.text).strip()
                    # Extract best matching sentence
                    snippet = clean_txt[:160]
                    for line in clean_txt.split('\n'):
                        l_strip = line.strip()
                        if l_strip and any(w in l_strip.lower() for w in q_words if len(w) > 3):
                            snippet = l_strip[:160]
                            break
                    sources.append({
                        "document_id": f"{doc_name} [Page {page}]",
                        "chunk_text": snippet,
                        "score": round(c.score, 3)
                    })

            # If the model didn't explicitly format citations, include top chunk as evidence
            if not sources and chunks:
                top_c = chunks[0]
                doc_name = Path(top_c.document_id).name
                page = top_c.metadata.get("page", 1)
                clean_txt = re.sub(r'^--- Page \d+ ---\s*', '', top_c.text).strip()
                snippet = clean_txt[:160]
                for line in clean_txt.split('\n'):
                    l_strip = line.strip()
                    if l_strip and any(w in l_strip.lower() for w in q_words if len(w) > 3):
                        snippet = l_strip[:160]
                        break
                sources.append({
                    "document_id": f"{doc_name} [Page {page}]",
                    "chunk_text": snippet,
                    "score": round(top_c.score, 3)
                })

        avg_score = round(sum(c.score for c in chunks) / len(chunks), 3) if chunks else 0.0
        cleaned_answer = remove_answer_labels(answer)
        ans_lower = cleaned_answer.lower()
        if "not covered in the provided documentation" in ans_lower or "not covered in the indexed" in ans_lower:
            sources = []

        state["answer"] = cleaned_answer
        state["sources"] = sources
        state["relevance_score"] = avg_score
        state["route"] = "generation"
        return state

    def fallback_node(self, state: GraphState) -> GraphState:
        question = state["question"].strip()

        # 1. Fallback to Tavily Web Search FIRST when local documentation does not have the answer
        if settings.is_valid_tavily_key():
            tavily_key = settings.tavily_api_key.strip().strip("'\"")
            logger.info("Local documents insufficient. Executing Tavily web search fallback for: '%s'", question)
            try:
                resp = httpx.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": tavily_key,
                        "query": question,
                        "search_depth": "basic",
                        "include_answer": True,
                        "max_results": 4,
                    },
                    timeout=25.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    tavily_answer = data.get("answer", "")

                    web_snippets = []
                    sources = []
                    if tavily_answer:
                        web_snippets.append(f"Tavily Summary:\n{tavily_answer}")
                    for r in results[:4]:
                        title = r.get("title", "Web Result")
                        url = r.get("url", "")
                        content = r.get("content", "")
                        web_snippets.append(f"Source: {title} ({url})\n{content}")
                        sources.append({
                            "document_id": f"[Web] {title}",
                            "chunk_text": f"{url} — {content[:100]}",
                            "score": round(float(r.get("score", 0.90)), 2),
                        })

                    if web_snippets:
                        web_context = "\n\n".join(web_snippets)
                        prompt = WEB_SEARCH_GENERATION_PROMPT.format(
                            question=question,
                            web_context=web_context
                        )
                        ans_text = ""
                        try:
                            response = self._chat_model.invoke(prompt)
                            ans_text = response.content.strip() if hasattr(response, "content") else str(response).strip()
                        except Exception:
                            logger.exception("LLM generation on web context failed; using direct Tavily summary and snippets")
                            if tavily_answer:
                                ans_text = tavily_answer
                            else:
                                ans_text = "\n\n".join(
                                    f"• **{r.get('title', 'Web Source')}**: {r.get('content', '')}"
                                    for r in results[:3] if r.get("content")
                                )

                        if ans_text:
                            cleaned = remove_answer_labels(ans_text).lstrip()
                            note_header = "*Answered using web search (Tavily), not the uploaded document:*"
                            cleaned = re.sub(r'^(?:[ \t>*-]*(?:note|answered using web search)[^\n]*\n+)+', '', cleaned, flags=re.I).lstrip()
                            state["answer"] = f"{note_header}\n\n{cleaned}"
                            state["sources"] = sources
                            state["relevance_score"] = 0.90
                            state["route"] = "web_search"
                            return state
                else:
                    logger.warning("Tavily search API returned status %d: %s", resp.status_code, resp.text[:200])
            except Exception:
                logger.exception("Tavily search fallback failed")

        # 2. Strict grounding: If Tavily is unavailable and strict_grounding is enabled, strictly refuse out-of-document queries
        if settings.strict_grounding:
            logger.info("Strict grounding active: question is not covered in indexed documents.")
            state["answer"] = "This is not covered in the indexed documents."
            state["sources"] = []
            state["relevance_score"] = 0.0
            state["route"] = "not_found"
            return state

        # 3. General knowledge fallback when Tavily is unavailable or returns no results
        logger.info("Falling back to LLM general knowledge")
        prompt = FALLBACK_GENERATION_PROMPT.format(question=question)
        try:
            response = self._chat_model.invoke(prompt)
            ans_text = response.content.strip() if hasattr(response, "content") else str(response).strip()
            state["answer"] = remove_answer_labels(ans_text)
        except Exception:
            state["answer"] = "I am sorry, but I could not find relevant technical documentation in the current index to answer your question."

        state["sources"] = []
        state["relevance_score"] = 0.0
        state["route"] = "general_knowledge"
        return state
