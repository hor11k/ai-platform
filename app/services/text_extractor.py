from pathlib import Path

from docx import Document
from pypdf import PdfReader


class TextExtractor:
    """Extract plain text for indexing."""

    INDEXABLE_SUFFIXES = {".pdf", ".docx", ".txt"}

    def is_indexable(self, path: Path) -> bool:
        return path.suffix.lower() in self.INDEXABLE_SUFFIXES

    def extract(self, path: Path) -> str | None:
        suffix = path.suffix.lower()
        if suffix not in self.INDEXABLE_SUFFIXES:
            return None

        try:
            if suffix == ".txt":
                text = path.read_text(encoding="utf-8", errors="ignore")
            elif suffix == ".docx":
                text = self._extract_docx(path)
            else:
                text = self._extract_pdf(path)
        except OSError:
            return None

        cleaned = text.strip()
        return cleaned or None

    def _extract_docx(self, path: Path) -> str:
        document = Document(path)
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs]
        return "\n".join(paragraph for paragraph in paragraphs if paragraph)

    def _extract_pdf(self, path: Path) -> str:
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(page.strip() for page in pages if page.strip())
