from unittest.mock import patch

import httpx
from openai import APIConnectionError

from app.exceptions import OpenAIServiceError
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
    def __init__(
        self,
        content: str | None = None,
        error: Exception | None = None,
    ) -> None:
        self._content = content
        self._error = error
        self.last_kwargs: dict | None = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        if self._error is not None:
            raise self._error
        return _FakeResponse(self._content)


class _FakeChat:
    def __init__(
        self,
        content: str | None = None,
        error: Exception | None = None,
    ) -> None:
        self.completions = _FakeCompletions(content=content, error=error)


class _FakeClient:
    def __init__(
        self,
        content: str | None = None,
        error: Exception | None = None,
    ) -> None:
        self.chat = _FakeChat(content=content, error=error)


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


def test_answer_with_context_preserves_openai_connection_error_cause() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    error = APIConnectionError(message="Connection error.", request=request)
    error.__cause__ = httpx.UnsupportedProtocol(
        "Request URL is missing an 'http://' or 'https://' protocol."
    )
    service = OpenAIService(
        api_key="test-key",
        model="gpt-5.5",
        client=_FakeClient(error=error),
    )

    try:
        service.answer_with_context(
            question="Where is the contract?",
            context="Path: /data/loan.docx",
        )
    except OpenAIServiceError as exc:
        message = str(exc)
        assert "Could not connect to OpenAI" not in message
        assert "Connection error." in message
        assert "Request URL is missing an 'http://' or 'https://' protocol." in message
        assert exc.__cause__ is error
    else:
        raise AssertionError("Expected OpenAIServiceError")
