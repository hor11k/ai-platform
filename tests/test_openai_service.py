from unittest.mock import patch

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    RateLimitError,
)

from app.exceptions import OpenAIServiceError
from app.models.document_analysis import DocumentAnalysis
from app.services.openai_service import OpenAIService


class _FakeMessage:
    def __init__(self, parsed: DocumentAnalysis | None) -> None:
        self.parsed = parsed


class _FakeChoice:
    def __init__(self, parsed: DocumentAnalysis | None) -> None:
        self.message = _FakeMessage(parsed)


class _FakeResponse:
    def __init__(self, parsed: DocumentAnalysis | None) -> None:
        self.choices = [_FakeChoice(parsed)]


class _FakeCompletions:
    def __init__(
        self,
        parsed: DocumentAnalysis | None = None,
        error: Exception | None = None,
    ) -> None:
        self._parsed = parsed
        self._error = error
        self.last_kwargs: dict | None = None

    def parse(self, **kwargs):
        self.last_kwargs = kwargs
        if self._error is not None:
            raise self._error
        return _FakeResponse(self._parsed)


class _FakeChat:
    def __init__(
        self,
        parsed: DocumentAnalysis | None = None,
        error: Exception | None = None,
    ) -> None:
        self.completions = _FakeCompletions(parsed=parsed, error=error)


class _FakeClient:
    def __init__(
        self,
        parsed: DocumentAnalysis | None = None,
        error: Exception | None = None,
    ) -> None:
        self.chat = _FakeChat(parsed=parsed, error=error)


def _api_status_error(
    status_code: int,
    message: str,
    error_cls: type[APIStatusError],
) -> APIStatusError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(status_code, request=request)
    return error_cls(message, response=response, body=None)


def test_openai_client_uses_default_timeout() -> None:
    with patch("app.services.openai_service.OpenAI") as mock_openai:
        mock_openai.return_value = _FakeClient()
        OpenAIService(api_key="test-key", model="gpt-5.5")

    mock_openai.assert_called_once_with(
        api_key="test-key",
        base_url=None,
        timeout=120.0,
    )


def test_openai_client_uses_configured_timeout() -> None:
    with patch("app.services.openai_service.OpenAI") as mock_openai:
        mock_openai.return_value = _FakeClient()
        OpenAIService(api_key="test-key", model="gpt-5.5", timeout=90.0)

    mock_openai.assert_called_once_with(
        api_key="test-key",
        base_url=None,
        timeout=90.0,
    )


def test_analyze_document_logs_request_metadata_on_success() -> None:
    expected = DocumentAnalysis(
        executive_summary="Summary",
        risks=[],
        key_dates=[],
        key_amounts=[],
        parties=[],
        action_items=[],
    )
    document_text = "Sensitive contract body"
    service = OpenAIService(
        api_key="test-key",
        model="gpt-5.5",
        client=_FakeClient(expected),
    )

    with patch("app.services.openai_service.logger") as mock_logger:
        service.analyze_document(document_text)

    mock_logger.info.assert_called_once()
    mock_logger.error.assert_not_called()
    log_kwargs = mock_logger.info.call_args.kwargs
    assert log_kwargs["model"] == "gpt-5.5"
    assert log_kwargs["document_size"] == len(document_text)
    assert log_kwargs["duration"] >= 0
    logged_payload = str(mock_logger.info.call_args)
    assert document_text not in logged_payload


def test_analyze_document_logs_request_metadata_on_failure() -> None:
    error = _api_status_error(500, "Internal server error", APIStatusError)
    document_text = "Sensitive contract body"
    service = OpenAIService(
        api_key="test-key",
        model="gpt-5.5",
        client=_FakeClient(error=error),
    )

    with patch("app.services.openai_service.logger") as mock_logger:
        try:
            service.analyze_document(document_text)
        except OpenAIServiceError:
            pass
        else:
            raise AssertionError("Expected OpenAIServiceError")

    mock_logger.error.assert_called_once()
    mock_logger.info.assert_not_called()
    log_kwargs = mock_logger.error.call_args.kwargs
    assert log_kwargs["model"] == "gpt-5.5"
    assert log_kwargs["document_size"] == len(document_text)
    assert log_kwargs["duration"] >= 0
    logged_payload = str(mock_logger.error.call_args)
    assert document_text not in logged_payload


def test_analyze_document_returns_structured_result() -> None:
    expected = DocumentAnalysis(
        executive_summary="A services agreement between two parties.",
        risks=["Late delivery penalties"],
        key_dates=["2026-12-31"],
        key_amounts=["1,500,000 RUB"],
        parties=["Alpha LLC", "Beta Ltd"],
        action_items=["Sign the contract"],
    )
    fake_client = _FakeClient(expected)
    service = OpenAIService(api_key="test-key", model="gpt-5.5", client=fake_client)

    result = service.analyze_document("Contract text")

    assert result == expected
    assert fake_client.chat.completions.last_kwargs is not None
    assert fake_client.chat.completions.last_kwargs["model"] == "gpt-5.5"


def test_analyze_document_raises_on_empty_response() -> None:
    fake_client = _FakeClient(None)
    service = OpenAIService(api_key="test-key", model="gpt-5.5", client=fake_client)

    try:
        service.analyze_document("Contract text")
    except ValueError as exc:
        assert "empty analysis response" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_analyze_document_maps_authentication_error() -> None:
    error = _api_status_error(401, "Invalid API key", AuthenticationError)
    service = OpenAIService(
        api_key="test-key",
        model="gpt-5.5",
        client=_FakeClient(error=error),
    )

    try:
        service.analyze_document("Contract text")
    except OpenAIServiceError as exc:
        assert "authentication failed" in str(exc)
        assert "OPENAI_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected OpenAIServiceError")


def test_analyze_document_maps_rate_limit_error() -> None:
    error = _api_status_error(429, "Rate limit reached", RateLimitError)
    service = OpenAIService(
        api_key="test-key",
        model="gpt-5.5",
        client=_FakeClient(error=error),
    )

    try:
        service.analyze_document("Contract text")
    except OpenAIServiceError as exc:
        assert "rate limit exceeded" in str(exc)
    else:
        raise AssertionError("Expected OpenAIServiceError")


def test_analyze_document_maps_connection_error() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    error = APIConnectionError(message="Connection refused", request=request)
    service = OpenAIService(
        api_key="test-key",
        model="gpt-5.5",
        client=_FakeClient(error=error),
    )

    try:
        service.analyze_document("Contract text")
    except OpenAIServiceError as exc:
        assert "Could not connect to OpenAI" in str(exc)
    else:
        raise AssertionError("Expected OpenAIServiceError")


def test_analyze_document_maps_api_status_error() -> None:
    error = _api_status_error(500, "Internal server error", APIStatusError)
    service = OpenAIService(
        api_key="test-key",
        model="gpt-5.5",
        client=_FakeClient(error=error),
    )

    try:
        service.analyze_document("Contract text")
    except OpenAIServiceError as exc:
        assert "OpenAI API error (500)" in str(exc)
        assert "Internal server error" in str(exc)
    else:
        raise AssertionError("Expected OpenAIServiceError")
