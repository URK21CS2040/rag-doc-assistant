from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Primary LLM Provider: "groq" (GroqCloud) by default
    llm_provider: str = "groq"

    # Groq (GroqCloud - api.groq.com) Configuration - Default LLM
    groq_api_key: Optional[str] = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-120b"

    # Grok (xAI - api.x.ai) Configuration (also supported)
    grok_api_key: Optional[str] = None
    xai_api_key: Optional[str] = None
    grok_base_url: str = "https://api.x.ai/v1"
    grok_model: str = "grok-beta"
    grok_embedding_model: str = "grok-embedding-small"

    # OpenAI Configuration (optional fallback / embeddings)
    openai_api_key: Optional[str] = None
    openai_embedding_model: str = "text-embedding-3-small"

    # Tavily Web Search API (bonus fallback when answer is not in documents)
    tavily_api_key: Optional[str] = None

    # Storage & Application Config
    chroma_persist_directory: str = "./data/chroma"
    port: int = 8000
    anonymized_telemetry: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def effective_llm_api_key(self) -> str:
        """Returns the primary API key for Groq (default), falling back to other configured keys."""
        if self.llm_provider.lower() == "groq" or self.groq_api_key:
            return self.groq_api_key or "gsk_your_groq_api_key_here"
        if self.llm_provider.lower() == "grok" or self.grok_api_key or self.xai_api_key:
            return self.grok_api_key or self.xai_api_key or "xai_your_grok_api_key_here"
        return self.openai_api_key or "your_api_key_here"

    @property
    def effective_embedding_api_key(self) -> str:
        """Returns the active embedding key."""
        return (
            self.openai_api_key
            or self.grok_api_key
            or self.xai_api_key
            or self.groq_api_key
            or "your_embedding_api_key_here"
        )

settings = Settings()
