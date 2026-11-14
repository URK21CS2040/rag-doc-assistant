QUERY_REWRITE_PROMPT = """You are an AI query understanding and vector search analyst.
Analyze the user's question:
1. Determine the user's primary intent (e.g., "Code Implementation", "Conceptual Guide", "Comparison & Matrix", "Architecture & Lifecycle", "Debugging & Fix", or "General Lookup").
2. Produce an expanded search query with core keywords, synonyms, and subtopics to maximize retrieval accuracy while preserving all entity names and subjects accurately.

Format your output EXACTLY as:
INTENT: <2-4 words summarizing intent>
SEARCH_QUERY: <concise keyword-rich search query>

Question: {question}"""

DOCUMENT_GRADE_PROMPT = "You are a relevance grader evaluating whether a retrieved technical documentation chunk is relevant to the user question. Return 'yes' if relevant, or 'no' if irrelevant.\n\nQuestion: {question}\n\nChunk: {chunk}\n\nDecision (yes/no):"

ANSWER_GENERATION_PROMPT = """You are an expert technical documentation assistant.
Detected Intent: {intent}
User Question: {question}

Context from Documentation:
{context}

Instructions:
- Tailor the structure and tone directly to the detected intent.
- Ensure 100% factual correctness: never hallucinate, invent, or misstate names, roles, or attributes.
- If the user needs code or implementation, provide clean, runnable, well-explained code snippets.
- If comparing concepts, structure the answer clearly and use tables or bulleted tradeoffs where helpful.
- Cite the source documentation accurately.

Answer:"""

FALLBACK_GENERATION_PROMPT = """You are an accurate, highly knowledgeable technical assistant. The user asked a question for which no matching documents were found in the local documentation library.

Instructions:
- Answer the user's question clearly, thoroughly, and with 100% factual accuracy.
- Carefully verify all real-world facts, names, roles, and attributes. Do not hallucinate or guess details.
- Start your answer with:
> *Note: No matching local documentation was found in the indexed library. Here is an answer from general technical knowledge:*

Question: {question}

Answer:"""

WEB_SEARCH_GENERATION_PROMPT = """You are an accurate, highly knowledgeable assistant. The user asked a question for which no matching documents were found in the local documentation library, so live web information was retrieved via Tavily search.

Instructions:
- Carefully verify all real-world facts, names, roles, and attributes (e.g., exact player names, bowling styles, left-hand vs right-hand batting, teams) strictly against the provided web context and established facts.
- Never confuse or invent names (e.g., Mitchell Santner, NOT Tom Santner) or player profiles (e.g., Mitchell Santner is a left-hand bat and slow left-arm orthodox spinner; Will Jacks is a right-hand bat and right-arm off-break spinner).
- Provide a clear, direct, and well-structured answer with tables or bullet points where appropriate.
- Start your answer with:
> *Note: No matching local documentation was found in the indexed library. An answer was retrieved from live web search (Tavily):*

Question: {question}

Web Search Context:
{web_context}

Answer:"""
