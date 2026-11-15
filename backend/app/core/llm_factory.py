import hashlib
from typing import Any, List
import numpy as np
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app.config import settings

class LocalHashEmbeddings:
    """
    Deterministic n-gram feature hashing embeddings.
    Zero external dependencies, instant execution, and offline-compatible.
    Used automatically when Groq is the primary LLM and no external embedding API key is provided.
    """
    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def _embed_single(self, text: str) -> List[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        words = text.lower().split()
        if not words:
            return vec.tolist()
        for word in words:
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16) % self.dim
            vec[h] += 1.0
            for i in range(max(1, len(word) - 2)):
                sub = word[i:i+3]
                h_sub = int(hashlib.sha256(sub.encode("utf-8")).hexdigest(), 16) % self.dim
                vec[h_sub] += 0.5
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_single(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_single(text)

class LLMFactory:
    @staticmethod
    def create_chat_model(temperature: float = 0.0) -> ChatOpenAI:
        """
        Creates Groq as the default LLM (GroqCloud with LPU inference).
        Also supports Grok (xAI) or OpenAI based on settings.
        """
        provider = settings.llm_provider.lower()
        if provider == "groq" or (settings.groq_api_key and not settings.grok_api_key):
            primary_model = settings.groq_model
            fallback_1_model = "openai/gpt-oss-120b" if primary_model == "openai/gpt-oss-20b" else "openai/gpt-oss-20b"
            primary = ChatOpenAI(
                model=primary_model,
                temperature=temperature,
                max_tokens=2500,
                api_key=settings.effective_llm_api_key,
                base_url=settings.groq_base_url,
            )
            fallback_1 = ChatOpenAI(
                model=fallback_1_model,
                temperature=temperature,
                max_tokens=2500,
                api_key=settings.effective_llm_api_key,
                base_url=settings.groq_base_url,
            )
            fallback_2 = ChatOpenAI(
                model="qwen/qwen3.8-27b",
                temperature=temperature,
                max_tokens=950,
                api_key=settings.effective_llm_api_key,
                base_url=settings.groq_base_url,
            )
            return primary.with_fallbacks([fallback_1, fallback_2])
        elif provider == "grok" or settings.grok_api_key or settings.xai_api_key:
            return ChatOpenAI(
                model=settings.grok_model,
                temperature=temperature,
                api_key=settings.grok_api_key or settings.xai_api_key or settings.effective_llm_api_key,
                base_url=settings.grok_base_url,
            )
        else:
            return ChatOpenAI(
                model="gpt-4o-mini",
                temperature=temperature,
                api_key=settings.openai_api_key or settings.effective_llm_api_key,
            )

    @staticmethod
    def create_embeddings() -> Any:
        """
        Creates embeddings client.
        Uses OpenAI if OPENAI_API_KEY is configured.
        Uses Grok if GROK_API_KEY is configured.
        Otherwise falls back to fast LocalHashEmbeddings for seamless Groq operation.
        """
        if settings.openai_api_key and settings.openai_api_key.startswith("sk-"):
            return OpenAIEmbeddings(
                model=settings.openai_embedding_model,
                api_key=settings.openai_api_key,
            )
        if settings.grok_api_key and settings.grok_api_key.startswith("xai-"):
            return OpenAIEmbeddings(
                model=settings.grok_embedding_model,
                api_key=settings.grok_api_key,
                base_url=settings.grok_base_url,
            )
        # Default for Groq: local zero-cost embedding
        return LocalHashEmbeddings()
