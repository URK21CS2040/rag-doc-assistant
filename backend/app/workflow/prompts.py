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
- Extract and explain all key concepts, definitions, types, specifications, formulas, or steps mentioned in the context that answer the question.
- Write naturally and clearly. Do NOT follow any artificial templates or rigid format rules.
- Strictly do NOT use the label words "Main Answer:" or "Detailed Answer:".
- If the documentation context provides specific facts or values, use them accurately without hallucinating.

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
