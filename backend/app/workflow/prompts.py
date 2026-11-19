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
Answer the user's question concisely and accurately using ONLY the documentation context below.

Rules:
1. Grounding & Precision: Answer only using retrieved evidence from the context. Preserve exact numerical values, units, thresholds, processor types, and technical specifications verbatim (e.g. '48', 'ARM-based quad-core', 'Ethernet', '-10 °C to 55 °C'). Never round, estimate, or invent values.
2. Citation Requirement: Cite [n] after every fact, statement, or value you provide, corresponding to the passage index.
3. Document Isolation & Attribution:
   - When answering, prioritize the specific document or system requested by the user.
   - If passages come from different documents or describe different systems (e.g. different platforms or versions), do NOT blend or substitute their specifications. Clearly state which document supports each fact (e.g. "According to Document A [1]: ... while according to Document B [2]: ...").
   - Never allow an unrelated document to overwrite or substitute the specifications of another document.
4. Handling Missing Information: If the requested information is not mentioned anywhere in the context, explicitly state: "This information is not covered in the provided documentation." Never make up missing technical specifications.
5. Formatting: Strictly do NOT use the label words "Main Answer:" or "Detailed Answer:". Address the question directly and cleanly.

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

WEB_SEARCH_GENERATION_PROMPT = """You are an accurate technical assistant. The user's question could not be answered from local documentation, so live web search results were retrieved via Tavily.

Web Search Context:
{web_context}

User Question: {question}

Instructions:
- Always start your answer with:
*Note: No matching local documentation was found in the indexed library. An answer was retrieved from live web search (Tavily):*

- Provide a direct, concise, and complete answer based on the web search context above.
- Strictly do NOT use the label words "Main Answer:" or "Detailed Answer:".
- Ensure all information is grounded in the retrieved web search context.

Answer:"""
