import html
import re
import ipaddress
import logging
from pathlib import Path
from typing import List, Tuple, Optional
from urllib.parse import urlparse
from html.parser import HTMLParser
import httpx

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


class HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: List[str] = []
        self.text_parts: List[str] = []
        self.in_title: bool = False
        self.ignore_tag_depth: int = 0
        self.ignored_tags = {
            "script", "style", "noscript", "svg", "iframe"
        }
        self.block_tags = {
            "p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
            "li", "article", "section", "tr", "blockquote", "pre", "hr", "br"
        }

    def handle_starttag(self, tag: str, attrs: list) -> None:
        tag_lower = tag.lower()
        if tag_lower in self.ignored_tags:
            self.ignore_tag_depth += 1
            return
        if self.ignore_tag_depth > 0:
            return
        if tag_lower == "title":
            self.in_title = True
        elif tag_lower in self.block_tags:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in self.ignored_tags:
            self.ignore_tag_depth = max(0, self.ignore_tag_depth - 1)
            return
        if self.ignore_tag_depth > 0:
            return
        if tag_lower == "title":
            self.in_title = False
        elif tag_lower in self.block_tags:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.ignore_tag_depth > 0:
            return
        if self.in_title:
            self.title_parts.append(data)
        else:
            text = data.strip()
            if text:
                self.text_parts.append(data)

    def get_title(self) -> str:
        raw_title = " ".join(self.title_parts).strip()
        cleaned = re.sub(r'\s+', ' ', raw_title)
        return html.unescape(cleaned)

    def get_text(self) -> str:
        raw = "".join(self.text_parts)
        lines = [line.strip() for line in raw.splitlines()]
        cleaned = []
        prev_empty = False
        for line in lines:
            if line:
                cleaned.append(line)
                prev_empty = False
            elif not prev_empty:
                cleaned.append("")
                prev_empty = True
        result = "\n".join(cleaned).strip()
        return html.unescape(result)


class UrlLoader:
    def __init__(self, timeout: float = 20.0, max_bytes: int = 10 * 1024 * 1024) -> None:
        self._timeout = timeout
        self._max_bytes = max_bytes

    def load(self, url: str) -> Tuple[str, str]:
        """
        Fetches a public URL and extracts its title and clean readable text.
        Returns (title, text).
        """
        url = url.strip()
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Only http:// and https:// URLs are supported.")

        hostname = parsed.hostname
        if not hostname:
            raise ValueError(f"Invalid URL: missing hostname in '{url}'")

        # SSRF checks
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_loopback or ip.is_private or ip.is_reserved or ip.is_link_local:
                raise ValueError(f"Access to private/local network address '{hostname}' is not permitted.")
        except ValueError:
            # Domain name (not IP)
            if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0"):
                raise ValueError(f"Access to local host '{hostname}' is not permitted.")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 RAGDocAssistant/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain,application/pdf,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            with httpx.Client(timeout=self._timeout, follow_redirects=True, verify=True) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Failed to fetch URL ({e.response.status_code} {e.response.reason_phrase})")
        except httpx.RequestError as e:
            raise ValueError(f"Network error while connecting to URL: {e}")

        content_bytes = resp.content
        if len(content_bytes) > self._max_bytes:
            raise ValueError(f"Content from URL exceeds maximum allowed size of {self._max_bytes // (1024 * 1024)}MB")

        content_type = resp.headers.get("content-type", "").lower()

        # 1. Handle PDF URL
        if "application/pdf" in content_type or parsed.path.lower().endswith(".pdf"):
            title = Path(parsed.path).name or "PDF Document"
            text = self._extract_pdf_bytes(content_bytes, title)
            return title, text

        # 2. Handle HTML / Plain text
        raw_html = resp.text
        if "text/html" in content_type or "<html" in raw_html.lower() or "<body" in raw_html.lower():
            parser = HTMLTextExtractor()
            parser.feed(raw_html)
            title = parser.get_title()
            text = parser.get_text()
            if not title:
                title = f"{hostname}{parsed.path}"
        else:
            title = f"{hostname}{parsed.path}"
            text = raw_html.strip()

        if not text or len(text.strip()) < 20:
            raise ValueError("No extractable textual content found at this URL (site may require JavaScript rendering or login)")

        return title, text

    def _extract_pdf_bytes(self, pdf_bytes: bytes, filename: str) -> str:
        if not pdf_bytes.startswith(b"%PDF-"):
            raise ValueError("Invalid PDF format returned from URL")
        if HAS_PYMUPDF:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            parts = []
            for i, page in enumerate(doc):
                t = page.get_text("text").strip()
                if t:
                    parts.append(f"--- Page {i + 1} ---\n{t}")
            doc.close()
            extracted = "\n\n".join(parts).strip()
            if not extracted:
                raise ValueError("No extractable text in PDF at URL")
            return extracted
        elif HAS_PYPDF:
            import io
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            parts = []
            for i, page in enumerate(reader.pages):
                t = (page.extract_text() or "").strip()
                if t:
                    parts.append(f"--- Page {i + 1} ---\n{t}")
            extracted = "\n\n".join(parts).strip()
            if not extracted:
                raise ValueError("No extractable text in PDF at URL")
            return extracted
        else:
            raise RuntimeError("PDF parser not available")
