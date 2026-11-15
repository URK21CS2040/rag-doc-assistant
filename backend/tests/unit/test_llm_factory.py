from app.core.llm_factory import LLMFactory
from app.config import settings

def test_groq_default_chat_model():
    chat_model = LLMFactory.create_chat_model(temperature=0.2)
    underlying = getattr(chat_model, "runnable", chat_model)
    assert underlying.model_name == settings.groq_model
    assert "api.groq.com" in str(underlying.openai_api_base)
    assert underlying.temperature == 0.2

def test_embeddings_initialization():
    embeddings = LLMFactory.create_embeddings()
    assert embeddings is not None
    vec = embeddings.embed_query("test query")
    assert len(vec) == 384
