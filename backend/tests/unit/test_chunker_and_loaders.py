from app.ingestion.chunker import TextChunker

def test_text_chunker() -> None:
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    text = "A" * 120
    chunks = chunker.split_text("doc_1", text)
    assert len(chunks) > 1
    assert chunks[0].document_id == "doc_1"
