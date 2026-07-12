from pathlib import Path

import pytest

from app.models.document_analysis import DocumentAnalysis
from app.services.analyze_service import AnalyzeService
from app.services.document_loader import DocumentLoader, LoadedDocument
from app.services.openai_service import OpenAIService


class _StubLoader(DocumentLoader):
    def __init__(self, document: LoadedDocument) -> None:
        super().__init__()
        self._document = document

    def load(self, file_path: Path) -> LoadedDocument:
        return self._document


class _StubOpenAI(OpenAIService):
    def __init__(self, analysis: DocumentAnalysis) -> None:
        super().__init__(api_key="test-key", model="gpt-5.5")
        self._analysis = analysis
        self.received_text: str | None = None

    def analyze_document(self, document_text: str) -> DocumentAnalysis:
        self.received_text = document_text
        return self._analysis


def test_analyze_service_orchestrates_loader_and_openai(tmp_path: Path) -> None:
    file_path = tmp_path / "agreement.txt"
    file_path.write_text("Agreement body", encoding="utf-8")
    document = LoadedDocument(
        path=file_path,
        filename="agreement.txt",
        format="txt",
        text="Agreement body",
    )
    expected = DocumentAnalysis(
        executive_summary="Summary",
        risks=["Risk A"],
        key_dates=["2026-01-01"],
        key_amounts=["100 USD"],
        parties=["Party A"],
        action_items=["Review contract"],
    )
    openai = _StubOpenAI(expected)
    service = AnalyzeService(
        document_loader=_StubLoader(document),
        openai_service=openai,
    )

    result = service.analyze(file_path)

    assert result == expected
    assert openai.received_text == "Agreement body"


def test_analyze_service_requires_openai() -> None:
    service = AnalyzeService(openai_service=None)

    with pytest.raises(ValueError, match="OpenAI is not configured"):
        service.analyze(Path("contract.txt"))
