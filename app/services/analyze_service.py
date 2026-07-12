from pathlib import Path

from app.models.document_analysis import DocumentAnalysis
from app.services.document_loader import DocumentLoader
from app.services.openai_service import OpenAIService


class AnalyzeService:
    """Orchestrate document loading and AI analysis."""

    def __init__(
        self,
        document_loader: DocumentLoader | None = None,
        openai_service: OpenAIService | None = None,
    ) -> None:
        self._document_loader = document_loader or DocumentLoader()
        self._openai_service = openai_service

    def analyze(self, file_path: Path) -> DocumentAnalysis:
        if self._openai_service is None:
            msg = "OpenAI is not configured. Set OPENAI_API_KEY in config/.env."
            raise ValueError(msg)

        document = self._document_loader.load(file_path)
        return self._openai_service.analyze_document(document.text)
