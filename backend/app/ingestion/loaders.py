import logging
from pathlib import Path
from typing import List

try:
    import pymupdf
    HAS_PYMUPDF = True
except ImportError:
    pymupdf = None
    HAS_PYMUPDF = False

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    pypdf = None
    HAS_PYPDF = False

logger = logging.getLogger(__name__)

class DocumentLoader:
    def load(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._load_pdf(path)
        elif suffix in [".md", ".txt"]:
            return self._load_text(path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}. Only .pdf, .md, and .txt are supported.")

    def _load_pdf(self, path: Path) -> str:
        if HAS_PYMUPDF:
            return self._load_pdf_pymupdf(path)
        elif HAS_PYPDF:
            return self._load_pdf_pypdf(path)
        else:
            raise RuntimeError("Neither pymupdf nor pypdf is installed for PDF parsing")

    def _load_pdf_pypdf(self, path: Path) -> str:
        try:
            reader = pypdf.PdfReader(str(path))
        except Exception as e:
            logger.exception("Failed to open PDF document with pypdf: %s", path.name)
            raise ValueError(f"Could not open PDF file: {e}")

        if reader.is_encrypted:
            raise ValueError("Password-protected PDF")

        text_parts: List[str] = []
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                cleaned = page_text.strip()
                if cleaned:
                    text_parts.append(f"--- Page {i + 1} ---\n{cleaned}")
            except Exception as page_err:
                logger.warning("Error processing page %d of %s: %s", i + 1, path.name, page_err)
                continue

        total_extracted = "\n\n".join(text_parts).strip()
        if not total_extracted:
            raise ValueError("No extractable text found in PDF (scanned or image-only PDF)")
        return total_extracted

    def _load_pdf_pymupdf(self, path: Path) -> str:
        try:
            doc = pymupdf.open(str(path))
        except Exception as e:
            logger.exception("Failed to open PDF document: %s", path.name)
            raise ValueError(f"Could not open PDF file: {e}")

        if doc.is_encrypted or getattr(doc, "needs_pass", False):
            doc.close()
            raise ValueError("Password-protected PDF")

        text_parts: List[str] = []
        num_pages = len(doc)

        for i in range(num_pages):
            try:
                page = doc[i]
                page_text = page.get_text("text") or ""
                
                # Extract any structured tables on this page to markdown
                try:
                    tabs = page.find_tables()
                    if tabs and tabs.tables:
                        table_mds = []
                        for tab in tabs.tables:
                            t_md = tab.to_markdown()
                            if t_md and t_md.strip():
                                table_mds.append(t_md.strip())
                        if table_mds:
                            page_text += "\n\n" + "\n\n".join(table_mds)
                except Exception as tab_err:
                    logger.debug("Table extraction skipped for page %d: %s", i + 1, tab_err)

                cleaned_page_text = page_text.strip()
                if cleaned_page_text:
                    text_parts.append(f"--- Page {i + 1} ---\n{cleaned_page_text}")
            except Exception as page_err:
                logger.warning("Error processing page %d of %s: %s", i + 1, path.name, page_err)
                continue

        doc.close()

        total_extracted = "\n\n".join(text_parts).strip()
        if not total_extracted:
            raise ValueError("No extractable text found in PDF (scanned or image-only PDF)")

        return total_extracted

    def _load_text(self, path: Path) -> str:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").strip()
            if not content:
                raise ValueError("File is empty")
            return content
        except ValueError:
            raise
        except Exception as e:
            logger.exception("Failed to read text file: %s", path.name)
            raise ValueError(f"Could not read file: {e}")


class MarkdownLoader(DocumentLoader):
    pass
