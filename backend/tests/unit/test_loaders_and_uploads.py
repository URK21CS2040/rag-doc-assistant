import io
from pathlib import Path
import pytest
import pymupdf
from app.ingestion.loaders import DocumentLoader

def test_loader_text_file(tmp_path: Path):
    loader = DocumentLoader()
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Hello world text content", encoding="utf-8")

    content = loader.load(str(txt_file))
    assert "Hello world text content" in content


def test_loader_pymupdf_pdf(tmp_path: Path):
    loader = DocumentLoader()
    pdf_path = tmp_path / "valid.pdf"

    # Create a small valid PDF using PyMuPDF
    doc = pymupdf.open()
    page1 = doc.new_page()
    page1.insert_text((50, 72), "First page documentation facts.")
    page2 = doc.new_page()
    page2.insert_text((50, 72), "Second page architecture details.")
    doc.save(str(pdf_path))
    doc.close()

    content = loader.load(str(pdf_path))
    assert "--- Page 1 ---" in content
    assert "First page documentation facts." in content
    assert "--- Page 2 ---" in content
    assert "Second page architecture details." in content


def test_loader_empty_pdf_raises_value_error(tmp_path: Path):
    loader = DocumentLoader()
    pdf_path = tmp_path / "empty_scanned.pdf"

    # Create empty page PDF (simulating scanned/image PDF without OCR text)
    doc = pymupdf.open()
    doc.new_page()  # Blank page with no text
    doc.save(str(pdf_path))
    doc.close()

    with pytest.raises(ValueError) as excinfo:
        loader.load(str(pdf_path))
    assert "No extractable text found in PDF" in str(excinfo.value)


def test_loader_unsupported_extension(tmp_path: Path):
    loader = DocumentLoader()
    doc_path = tmp_path / "document.docx"
    doc_path.write_bytes(b"dummy docx binary data")

    with pytest.raises(ValueError) as excinfo:
        loader.load(str(doc_path))
    assert "Unsupported file format" in str(excinfo.value)

