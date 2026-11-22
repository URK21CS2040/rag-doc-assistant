QUERY_REWRITE_PROMPT = """You are a search query optimizer for technical documentation.
The user asked: {question}

Previous retrieval did not find sufficient matching passages.
Generate an improved, concise search query using alternative keywords, synonyms, and domain terminology to locate the relevant section in the documents. Output ONLY the query string, nothing else.

Optimized Query:"""

FOLLOW_UP_REWRITE_PROMPT = """You are an expert conversation assistant.
Given the chat history and the user's latest follow-up question, rewrite the question into a clear, self-contained standalone search query that can be understood without the chat history.
Do NOT answer the question. Only output the rewritten question string, nothing else.

Chat History:
{chat_history}

Follow-up Question: {question}

Standalone Question:"""

BATCH_DOCUMENT_GRADE_PROMPT = """You are an accurate relevance grader evaluating candidate documentation passages against a user question.

Question: {question}

Candidate passages:
{passages}

Instructions:
- Evaluate each numbered passage carefully.
- Match semantics and concepts, NOT exact phrasing. A short factual passage that answers or explains a longer narrative or scenario question IS relevant.
- A passage is relevant if it contains facts, numbers, technical specifications, definitions, architecture details, hardware components, or context that help answer the question.
- If a passage mentions parameters, components, or topics discussed in the question, mark it as relevant.
- Reply ONLY with a comma-separated list of the indices of the relevant passages (e.g. "1, 2" or "1").
- If NONE of the passages are relevant, reply with "NONE".

Relevant indices:"""

DOCUMENT_GRADE_PROMPT = """You are a relevance grader evaluating whether a retrieved technical documentation chunk is relevant to the user question. Return 'yes' if relevant, or 'no' if irrelevant.

Question: {question}

Chunk: {chunk}

Decision (only 'yes' or 'no'):"""

ANSWER_GENERATION_PROMPT = """You are an accurate, strictly grounded technical assistant.
Answer the user's question accurately, clearly, and in direct accordance with what is asked, using ONLY the documentation context below.

Rules:
1. Grounding & Precision: Answer only using retrieved evidence from the context. Preserve exact numerical values, units, thresholds, processor types, and technical specifications verbatim (e.g. '48', 'ARM-based quad-core', 'Ethernet', '-10 °C to 55 °C'). Never round, estimate, or invent values.
2. Citation Requirement: Cite [n] after every fact, statement, or value you provide, corresponding to the passage index.
3. Document Isolation & Attribution:
   - When answering, prioritize the specific document or system requested by the user.
   - If passages come from different documents or describe different systems (e.g. different platforms or versions), do NOT blend or substitute their specifications. Clearly state which document supports each fact (e.g. "Document A specifies X [1], while Document B specifies Y [2].").
   - Never allow an unrelated document to overwrite or substitute the specifications of another document.
4. Handling Missing Information: If the requested information is completely missing from the context, explicitly state: "This information is not covered in the provided documentation." If the context provides partial information, answer the documented facts citing [n] and note what specific aspect is not covered in the provided documentation. Never make up missing technical specifications.
5. Adaptive Explanation & Formatting:
   - When the user asks to "explain", "describe", "how", "why", or "compare", do NOT just state a cold fact or dump raw text. Provide a clear, well-structured explanation that breaks down the concepts, mechanics, or reasoning based on the retrieved evidence.
   - For direct factual questions (e.g. 'What is X?', 'Who is Y?'), answer directly and concisely in 1-3 sentences.
   - For listing questions ('List...', 'Enumerate...'), provide a grouped, bulleted list. Never copy-paste entire raw paragraphs.
   - Strictly do NOT use the label words "Main Answer:" or "Detailed Answer:". Address the question directly and cleanly.
6. If question includes specific condition/timeframe (after X, during Y), pick the fact matching THAT specific condition, not the first matching entity.
7. Do NOT write 'According to Document [n]' — drop inline [n] mark after fact.

Documentation Context:
{context}

User Question: {question}

Answer:"""

FALLBACK_GENERATION_PROMPT = """You are an accurate technical assistant. The user asked a question for which no matching documents were found in the local documentation library.

User Question: {question}

Instructions:
- Always start your answer with:
*Note: No matching local documentation was found in the indexed library. Here is an answer from general technical knowledge:*

- Answer the question directly, clearly, and concisely.
- Strictly do NOT use the label words "Main Answer:" or "Detailed Answer:".

Answer:"""

WEB_SEARCH_GENERATION_PROMPT = """You are an accurate, discerning research assistant. The user's question could not be answered from local documentation, so live web search results were retrieved via Tavily.

Web Search Context:
{web_context}

User Question: {question}

Instructions:
1. Required Header:
   Always start your answer with:
   *Note: No matching local documentation was found in the indexed library. An answer was retrieved from live web search (Tavily):*

2. Source Evaluation & Reliability:
   - Do not automatically trust the first search result. Critically evaluate the credibility, authority, and depth of supporting evidence across all provided sources.
   - For specialized topics (e.g. sports, economics, law, medicine, technology), prioritize authoritative primary sources or dedicated statistical databases (e.g. ESPN, Cricbuzz, official records) over secondary aggregators or forum posts.

3. Numerical Discrepancies & Statistical Context:
   - When sources cite conflicting numbers, determine the reference timeframe, measurement date, and context from article titles, URLs, and timestamps.
   - For cumulative career statistics (such as career sixes, runs, matches, or goals), totals accumulate over time. Never present an older intermediate milestone (e.g., reaching 200 sixes in 2019) as a current career total when a more recent, reliable source reports an updated career total.
   - However, do not assume all numerical statistics are monotonically increasing: account for corrections, changing rules/definitions, and specific measurement windows (e.g., calendar year vs. career, tournament vs. all-time).
   - If reliable sources genuinely disagree and the discrepancy cannot be resolved by date or definition, explicitly disclose the discrepancy (e.g. "Source [1] reports X while Source [2] reports Y") rather than inventing false certainty.

4. Grounded Numbered Citations:
   - Cite the supporting source index [n] (e.g. [1], [2]) directly after every fact, figure, or statement derived from that source.
   - Ensure the cited source actually supports the specific claim or number. Never fabricate citations or publication dates.

5. Formatting & Missing Information:
   - If the retrieved web results do not contain reliable information to answer the question, state that clearly.
   - Strictly do NOT use the label words "Main Answer:" or "Detailed Answer:".
   - Provide a direct, concise, and well-reasoned answer.

Answer:"""
