from app.models.ask_response import AskResponse
from app.services.context_builder import (
    ContextChunk,
    ContextResult,
    RetrievalDebug,
    SourceGroupResult,
)
from app.services.rag_service import RagService


class _StubContextBuilder:
    def __init__(self, result: ContextResult) -> None:
        self._result = result

    def build(self, question: str) -> ContextResult:
        return self._result


class _StubOpenAI:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.last_question: str | None = None
        self.last_context: str | None = None

    def answer_with_context(self, question: str, context: str) -> str:
        self.last_question = question
        self.last_context = context
        return self.answer


def _make_chunk(
    path: str,
    filename: str,
    *,
    score: float = 20.0,
    exact: bool = True,
) -> ContextChunk:
    return ContextChunk(
        path=path,
        filename=filename,
        content=f"Content for {filename}",
        score=score,
        has_content=True,
        version_group="loan khimki",
        file_date=20240801,
        version_number=2,
        exact_filename_match=exact,
        reason="filename match (all terms)",
    )


def test_rag_service_returns_answer_sources_and_confidence() -> None:
    primary = _make_chunk("/data/loan-2024.docx", "loan-2024.docx")
    older = _make_chunk("/data/loan-v2.docx", "loan-v2.docx", score=12.0, exact=False)
    result = ContextResult(
        chunks=[primary],
        source_groups=[
            SourceGroupResult(primary=primary, alternate_paths=("/data/loan-v2.docx",))
        ],
        confidence=88,
        retrieval_debug=[
            RetrievalDebug(
                score=200.0,
                reason="filename match (all terms)",
                filename="loan-2024.docx",
                path="/data/loan-2024.docx",
            )
        ],
    )
    openai = _StubOpenAI("The latest loan contract is stored in /data/loan-2024.docx.")
    service = RagService(
        context_builder=_StubContextBuilder(result),
        openai_service=openai,  # type: ignore[arg-type]
    )

    response = service.ask("Where is the latest loan contract for Khimki?")

    assert isinstance(response, AskResponse)
    assert "loan contract" in response.answer
    assert response.confidence == 88
    assert response.sources == ["/data/loan-2024.docx"]
    assert len(response.source_groups) == 1
    assert response.source_groups[0].alternate_paths == ["/data/loan-v2.docx"]
    assert older.path in response.source_groups[0].alternate_paths


def test_rag_service_handles_no_context() -> None:
    service = RagService(
        context_builder=_StubContextBuilder(
            ContextResult(
                chunks=[],
                source_groups=[],
                confidence=0,
                retrieval_debug=[],
            )
        ),
        openai_service=_StubOpenAI("should not be called"),  # type: ignore[arg-type]
    )

    response = service.ask("unknown topic")

    assert response.sources == []
    assert response.confidence == 0
    assert "could not find relevant documents" in response.answer.lower()
