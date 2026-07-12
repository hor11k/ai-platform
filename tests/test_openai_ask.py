from unittest.mock import patch

from app.services.openai_service import OpenAIService


class _FakeMessage:
    def __init__(self, content: str | None) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str | None) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str | None) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content: str | None) -> None:
        self._content = content
        self.last_kwargs: dict | None = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeResponse(self._content)


class _FakeChat:
    def __init__(self, content: str | None) -> None:
        self.completions = _FakeCompletions(content)


class _FakeClient:
    def __init__(self, content: str | None) -> None:
        self.chat = _FakeChat(content)


def test_answer_with_context_returns_natural_language_answer() -> None:
    service = OpenAIService(
        api_key="test-key",
        model="gpt-5.5",
        client=_FakeClient("The contract is in the Khimki folder."),
    )

    answer = service.answer_with_context(
        question="Where is the loan contract?",
        context="Path: /data/loan.docx",
    )

    assert answer == "The contract is in the Khimki folder."


def test_answer_with_context_logs_without_question_or_context_body() -> None:
    service = OpenAIService(
        api_key="test-key",
        model="gpt-5.5",
        client=_FakeClient("Answer"),
    )
    question = "Secret question"
    context = "Secret document body"

    with patch("app.services.openai_service.logger") as mock_logger:
        service.answer_with_context(question=question, context=context)

    logged_payload = str(mock_logger.info.call_args)
    assert question not in logged_payload
    assert context not in logged_payload
    assert mock_logger.info.call_args.kwargs["model"] == "gpt-5.5"
