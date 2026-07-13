from time import perf_counter

from loguru import logger
from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from app.exceptions import OpenAIServiceError
from app.models.document_analysis import DocumentAnalysis
from app.prompts.analyze import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from app.prompts.ask import SYSTEM_PROMPT as ASK_SYSTEM_PROMPT
from app.prompts.ask import USER_PROMPT_TEMPLATE as ASK_USER_PROMPT_TEMPLATE

_OPENAI_API_ERRORS = (
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
    APIStatusError,
)


def _openai_error_message(exc: Exception) -> str:
    message = str(exc)
    cause = exc.__cause__
    if cause is not None:
        cause_message = str(cause)
        if cause_message and cause_message not in message:
            return f"{message}: {cause_message}"
    return message


class OpenAIService:
    """Send document text to OpenAI and return structured analysis."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout: float = 120.0,
        client: OpenAI | None = None,
    ) -> None:
        self.model = model
        self._client = client or OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    def analyze_document(self, document_text: str) -> DocumentAnalysis:
        document_size = len(document_text)
        started_at = perf_counter()

        try:
            response = self._client.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": USER_PROMPT_TEMPLATE.format(
                            document_text=document_text
                        ),
                    },
                ],
                response_format=DocumentAnalysis,
            )
        except _OPENAI_API_ERRORS as exc:
            self._raise_openai_service_error(
                exc,
                request_size=document_size,
                started_at=started_at,
            )

        self._log_request(document_size, started_at, failed=False)

        parsed = response.choices[0].message.parsed
        if parsed is None:
            msg = "OpenAI returned an empty analysis response."
            raise ValueError(msg)
        return parsed

    def answer_with_context(self, question: str, context: str) -> str:
        request_size = len(question) + len(context)
        started_at = perf_counter()

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": ASK_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": ASK_USER_PROMPT_TEMPLATE.format(
                            question=question,
                            context=context,
                        ),
                    },
                ],
            )
        except _OPENAI_API_ERRORS as exc:
            self._raise_openai_service_error(
                exc,
                request_size=request_size,
                started_at=started_at,
            )

        self._log_request(request_size, started_at, failed=False)

        content = response.choices[0].message.content
        if not content:
            msg = "OpenAI returned an empty answer."
            raise ValueError(msg)
        return content.strip()

    def _raise_openai_service_error(
        self,
        exc: Exception,
        *,
        request_size: int,
        started_at: float,
    ) -> None:
        message = _openai_error_message(exc)
        self._log_request(request_size, started_at, failed=True)
        logger.error(
            "OpenAI error type={exc_type} message={exc_message}",
            exc_type=type(exc).__name__,
            exc_message=message,
        )
        raise OpenAIServiceError(message) from exc

    def _log_request(
        self,
        document_size: int,
        started_at: float,
        *,
        failed: bool,
    ) -> None:
        duration = perf_counter() - started_at
        message = (
            "OpenAI request {status} model={model} document_chars={document_size} "
            "duration_s={duration:.2f}"
        )
        status = "failed" if failed else "completed"
        log = logger.error if failed else logger.info
        log(
            message,
            status=status,
            model=self.model,
            document_size=document_size,
            duration=duration,
        )
