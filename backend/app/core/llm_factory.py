import hashlib
import logging
from typing import Any, List
import numpy as np
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app.config import settings

logger = logging.getLogger(__name__)

try:
    from fastembed import TextEmbedding
    HAS_FASTEMBED = True
except ImportError:
    TextEmbedding = None
    HAS_FASTEMBED = False


class LocalHashEmbeddings:
    """
    Deterministic n-gram feature hashing embeddings.
    Zero external dependencies, instant execution, and offline-compatible.
    Used when FastEmbed is unavailable and no OpenAI key is provided.
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


class FastEmbedEmbeddings:
    """
    Local semantic embeddings using BAAI/bge-small-en-v1.5 via fastembed.
    Fast, offline-capable, real semantic vector representation (384-dim).
    """
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self.model_name = model_name
        self.dim = 384
        logger.info("Initializing FastEmbedEmbeddings with model: %s", model_name)
        self._model = TextEmbedding(model_name=model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings = list(self._model.embed(texts))
        return [e.tolist() for e in embeddings]

    def embed_query(self, text: str) -> List[float]:
        embeddings = list(self._model.embed([text]))
        if not embeddings:
            return [0.0] * self.dim
        return embeddings[0].tolist()


class LLMFactory:
    @staticmethod
    def create_chat_model(temperature: float = 0.0) -> Any:
        """
        Creates Groq as the default LLM with single fallback model (GroqCloud LPU).
        Also supports Grok (xAI) or OpenAI based on settings.
        Budgeted timeout: primary 12s, fallback 10s, max 1 retry each (total ~22-25s budget).
        """
        provider = settings.llm_provider.lower()
        if provider == "groq" or (settings.groq_api_key and not settings.grok_api_key):
            primary_model = settings.groq_model
            fallback_model = settings.groq_fallback_model

            primary = ChatOpenAI(
                model=primary_model,
                temperature=temperature,
                max_tokens=3000,
                max_retries=1,
                request_timeout=30.0,
                api_key=settings.effective_llm_api_key,
                base_url=settings.groq_base_url,
            )
            fallback1 = ChatOpenAI(
                model=fallback_model,
                temperature=temperature,
                max_tokens=2500,
                max_retries=1,
                request_timeout=30.0,
                api_key=settings.effective_llm_api_key,
                base_url=settings.groq_base_url,
            )
            fallback2 = ChatOpenAI(
                model="openai/gpt-oss-120b",
                temperature=temperature,
                max_tokens=3000,
                max_retries=1,
                request_timeout=35.0,
                api_key=settings.effective_llm_api_key,
                base_url=settings.groq_base_url,
            )
            runnable = primary.with_fallbacks([fallback1, fallback2])
            return runnable
        elif provider == "grok" or settings.grok_api_key or settings.xai_api_key:
            return ChatOpenAI(
                model=settings.grok_model,
                temperature=temperature,
                max_tokens=2000,
                max_retries=1,
                request_timeout=30.0,
                api_key=settings.grok_api_key or settings.xai_api_key or settings.effective_llm_api_key,
                base_url=settings.grok_base_url,
            )
        else:
            return ChatOpenAI(
                model="gpt-4o-mini",
                temperature=temperature,
                max_tokens=2000,
                max_retries=1,
                request_timeout=30.0,
                api_key=settings.openai_api_key or settings.effective_llm_api_key,
            )

    @staticmethod
    def create_embeddings() -> Any:
        """
        Creates embeddings client.
        Uses OpenAI if OPENAI_API_KEY is configured and valid.
        Defaults to local FastEmbedEmbeddings (BAAI/bge-small-en-v1.5) for real semantic retrieval.
        """
        if settings.openai_api_key and settings.openai_api_key.startswith("sk-") and not settings.openai_api_key.startswith("sk-your"):
            logger.info("Using OpenAIEmbeddings: %s", settings.openai_embedding_model)
            return OpenAIEmbeddings(
                model=settings.openai_embedding_model,
                api_key=settings.openai_api_key,
            )
        if HAS_FASTEMBED:
            return FastEmbedEmbeddings()
        logger.warning("fastembed is not installed in current environment; falling back to LocalHashEmbeddings")
        return LocalHashEmbeddings()
