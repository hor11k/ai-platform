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
        except AuthenticationError as exc:
            self._log_request(document_size, started_at, failed=True)
            raise OpenAIServiceError(
                "OpenAI authentication failed. Verify OPENAI_API_KEY in config/.env."
            ) from exc
        except RateLimitError as exc:
            self._log_request(document_size, started_at, failed=True)
            raise OpenAIServiceError(
                "OpenAI rate limit exceeded. Wait a moment and try again."
            ) from exc
        except APIConnectionError as exc:
            self._log_request(document_size, started_at, failed=True)
            raise OpenAIServiceError(
                "Could not connect to OpenAI. Check your network and OPENAI_BASE_URL."
            ) from exc
        except APIStatusError as exc:
            self._log_request(document_size, started_at, failed=True)
            raise OpenAIServiceError(
                f"OpenAI API error ({exc.status_code}): {exc.message}"
            ) from exc

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
        except AuthenticationError as exc:
            self._log_request(request_size, started_at, failed=True)
            raise OpenAIServiceError(
                "OpenAI authentication failed. Verify OPENAI_API_KEY in config/.env."
            ) from exc
        except RateLimitError as exc:
            self._log_request(request_size, started_at, failed=True)
            raise OpenAIServiceError(
                "OpenAI rate limit exceeded. Wait a moment and try again."
            ) from exc
        except APIConnectionError as exc:
            self._log_request(request_size, started_at, failed=True)
            raise OpenAIServiceError(
                "Could not connect to OpenAI. Check your network and OPENAI_BASE_URL."
            ) from exc
        except APIStatusError as exc:
            self._log_request(request_size, started_at, failed=True)
            raise OpenAIServiceError(
                f"OpenAI API error ({exc.status_code}): {exc.message}"
            ) from exc

        self._log_request(request_size, started_at, failed=False)

        content = response.choices[0].message.content
        if not content:
            msg = "OpenAI returned an empty answer."
            raise ValueError(msg)
        return content.strip()

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
