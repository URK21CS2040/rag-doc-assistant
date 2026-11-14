from pathlib import Path
from pypdf import PdfReader

class DocumentLoader:
    def load(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            return ""
        
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            try:
                reader = PdfReader(str(path))
                text_parts = []
                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_parts.append(f"--- Page {i + 1} ---\n{page_text}")
                return "\n\n".join(text_parts)
            except Exception as e:
                print(f"Error loading PDF {file_path}: {e}")
                return ""
        else:
            return path.read_text(encoding="utf-8", errors="ignore")

class MarkdownLoader(DocumentLoader):
    pass
