import re
from typing import List
from app.domain.entities import DocumentChunk

class TextChunker:
    """
    Boundary-aware and page-aware text chunker.
    Splits text along natural structural boundaries (paragraphs, lines, sentences, words)
    while preserving page numbers and table integrity.
    """
    def __init__(self, chunk_size: int = 1200, chunk_overlap: int = 200) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def split_text(self, document_id: str, text: str) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        if not text or not text.strip():
            return chunks

        # Detect page boundaries (e.g. '--- Page 1 ---')
        page_pattern = r'(--- Page \d+ ---)'
        page_splits = re.split(page_pattern, text)

        if len(page_splits) > 1:
            for i in range(1, len(page_splits), 2):
                page_marker = page_splits[i].strip()
                match = re.search(r'Page (\d+)', page_marker)
                page_num = int(match.group(1)) if match else 1
                page_content = page_splits[i + 1].strip() if i + 1 < len(page_splits) else ""
                if not page_content:
                    continue

                # If the entire page comfortably fits within chunk_size, keep it intact
                if len(page_content) + len(page_marker) + 2 <= int(self._chunk_size * 1.25):
                    full_chunk_text = f"{page_marker}\n{page_content}"
                    chunks.append(
                        DocumentChunk(
                            chunk_id=f"{document_id}_p{page_num}_c0",
                            document_id=document_id,
                            text=full_chunk_text,
                            metadata={"source": document_id, "page": page_num}
                        )
                    )
                else:
                    # Page is larger than chunk_size, split cleanly on natural boundaries
                    sub_chunks = self._split_segment(page_content, self._chunk_size, self._chunk_overlap)
                    for sub_idx, sub_text in enumerate(sub_chunks):
                        if not sub_text.startswith("--- Page"):
                            sub_text = f"{page_marker}\n{sub_text}"
                        chunks.append(
                            DocumentChunk(
                                chunk_id=f"{document_id}_p{page_num}_c{sub_idx}",
                                document_id=document_id,
                                text=sub_text,
                                metadata={"source": document_id, "page": page_num}
                            )
                        )
        else:
            # Unpaged text (e.g. Markdown or plain text)
            sub_chunks = self._split_segment(text, self._chunk_size, self._chunk_overlap)
            for idx, sub_text in enumerate(sub_chunks):
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{document_id}_chunk_{idx}",
                        document_id=document_id,
                        text=sub_text,
                        metadata={"source": document_id}
                    )
                )

        return chunks

    def _split_segment(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        segments: List[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + chunk_size, text_len)
            if end < text_len:
                slice_text = text[start:end]
                split_idx = -1
                for sep in ['\n\n', '\n', '. ', '? ', '! ', '; ', ' ']:
                    idx = slice_text.rfind(sep)
                    if idx >= int(chunk_size * 0.4):
                        split_idx = idx + (len(sep) if '\n' in sep else 0)
                        break
                if split_idx != -1:
                    end = start + split_idx

            seg = text[start:end].strip()
            if seg:
                segments.append(seg)

            if end >= text_len:
                break

            next_start = max(start + 1, end - chunk_overlap)
            if next_start < end:
                sp = text.find(' ', next_start, min(next_start + 40, end))
                nl = text.find('\n', next_start, min(next_start + 40, end))
                if nl != -1 and nl < next_start + 30:
                    next_start = nl + 1
                elif sp != -1:
                    next_start = sp + 1
            start = next_start

        return segments
