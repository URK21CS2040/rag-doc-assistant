QUERY_REWRITE_PROMPT = """You are a search query optimizer. Given the user question, output an optimized search query with core keywords to search the technical documentation vector database. Keep it concise.

Question: {question}

Search Query:"""

DOCUMENT_GRADE_PROMPT = """You are a relevance grader evaluating whether a retrieved technical documentation chunk is relevant to the user question. Return 'yes' if relevant, or 'no' if irrelevant.

Question: {question}

Chunk: {chunk}

Decision (only 'yes' or 'no'):"""

ANSWER_GENERATION_PROMPT = """You are an accurate, helpful technical assistant. Answer the user's question clearly, comprehensively, and directly based on the provided documentation context.

Documentation Context:
{context}

User Question: {question}

Instructions:
- Provide a direct, highly relevant, and complete answer based on the documentation context above.
- Match the answer directly to what was asked:
  * If asked about types or categories, list the types with definitions.
  * If asked for a definition, provide the definition directly.
  * If asked for a technical value or threshold, state the exact value from the documentation.
  * If asked for a formula, provide the formula only when supported by the documentation.
  * If asked what happens in a scenario (e.g. outage, failure, transition), explain the exact behavior and timing from the documentation.
- When multiple questions are asked in one message, address each question separately and clearly. Never skip any question.
- Write naturally and clearly. Do NOT follow any artificial templates or rigid format rules.
- Strictly do NOT use the label words "Main Answer:" or "Detailed Answer:".
- Strictly grounded: Never invent, assume, or generate unsupported facts, numbers, or definitions.
- If the documentation context does not contain enough information to answer a question, state clearly that it is not specified in the document.

Answer:"""

FALLBACK_GENERATION_PROMPT = """You are an accurate, helpful assistant. The user asked a question for which no matching documents were found in the local library.

User Question: {question}

Instructions:
- Always start your answer with:
*Note: No matching local documentation was found in the indexed library. Here is an answer from general technical knowledge:*

- Answer the question directly, clearly, and comprehensively.
- Strictly do NOT use the label words "Main Answer:" or "Detailed Answer:".

Answer:"""

WEB_SEARCH_GENERATION_PROMPT = """You are an accurate, helpful assistant. The user's question could not be answered from local documentation, so live web search results were retrieved via Tavily.

Web Search Context:
{web_context}

User Question: {question}

Instructions:
- Always start your answer with:
*Note: No matching local documentation was found in the indexed library. An answer was retrieved from live web search (Tavily):*

- Provide a direct, clear, and comprehensive answer to the user's question using the web search context.
- Write naturally based on the question (use tables, bullet points, or paragraphs where appropriate).
- Strictly do NOT use the label words "Main Answer:" or "Detailed Answer:".
- Ensure all information is grounded in the retrieved web search context.

Answer:"""
