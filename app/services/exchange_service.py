import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from exchangelib import DELEGATE, NTLM, Account, Credentials
from exchangelib.configuration import Configuration

from app.models.outlook_message import OutlookMessage


class ExchangeServiceError(Exception):
    """User-friendly error raised when Exchange EWS calls fail."""


class ExchangeService:
    """Read Exchange inbox messages via EWS."""

    def __init__(
        self,
        server: str | None,
        username: str,
        email: str,
        password: str,
        autodiscover_cache_path: Path,
        *,
        account: Any | None = None,
    ) -> None:
        self._server = server.strip() if server else None
        self._username = username
        self._email = email
        self._password = password
        self._autodiscover_cache_path = autodiscover_cache_path
        self._account = account

    def list_inbox(self, *, limit: int = 50) -> list[OutlookMessage]:
        account = self._account or self._connect_account()
        try:
            items = account.inbox.all().order_by("-datetime_received")[:limit]
            return [self._to_message(item) for item in items]
        except Exception as exc:
            raise ExchangeServiceError(
                f"Could not read Exchange inbox: {exc}"
            ) from exc

    def _build_credentials(self) -> Credentials:
        return Credentials(username=self._username, password=self._password)

    def _build_configuration(
        self, endpoint: str, credentials: Credentials
    ) -> Configuration:
        return Configuration(
            service_endpoint=endpoint,
            credentials=credentials,
            auth_type=NTLM,
        )

    def _connect_account(self) -> Account:
        credentials = self._build_credentials()
        endpoint = self._resolve_service_endpoint()

        try:
            config = self._build_configuration(endpoint, credentials)
            account = Account(
                primary_smtp_address=self._email,
                credentials=credentials,
                autodiscover=False,
                config=config,
                access_type=DELEGATE,
            )
        except Exception as exc:
            raise ExchangeServiceError(
                f"Exchange authentication failed: {exc}"
            ) from exc

        self._cache_autodiscover(endpoint)
        return account

    def _resolve_service_endpoint(self) -> str:
        if self._server:
            return self._server

        cached = self._load_autodiscover_cache()
        if cached and cached.get("email") == self._email:
            endpoint = cached.get("service_endpoint")
            if isinstance(endpoint, str) and endpoint:
                return endpoint

        return self._discover_service_endpoint()

    def _discover_service_endpoint(self) -> str:
        credentials = self._build_credentials()
        try:
            account = Account(
                primary_smtp_address=self._email,
                credentials=credentials,
                autodiscover=True,
                access_type=DELEGATE,
            )
            endpoint = account.protocol.service_endpoint
        except Exception as exc:
            raise ExchangeServiceError(
                "EXCHANGE_SERVER is not configured and autodiscover failed. "
                "Set EXCHANGE_SERVER in config/.env."
            ) from exc

        if not endpoint:
            raise ExchangeServiceError("Autodiscover did not return a service endpoint.")

        self._cache_autodiscover(endpoint)
        return endpoint

    def _to_message(self, item: Any) -> OutlookMessage:
        sender = getattr(item, "sender", None)
        if sender is not None:
            sender_label = sender.name or sender.email_address or "Unknown"
        else:
            sender_label = "Unknown"

        received_at = getattr(item, "datetime_received", None)
        if received_at is None:
            received_at = datetime.now(UTC)
        elif received_at.tzinfo is None:
            received_at = received_at.replace(tzinfo=UTC)

        return OutlookMessage(
            subject=getattr(item, "subject", None) or "(No subject)",
            sender=sender_label,
            received_at=received_at,
            is_read=bool(getattr(item, "is_read", False)),
        )

    def _load_autodiscover_cache(self) -> dict[str, str] | None:
        if not self._autodiscover_cache_path.is_file():
            return None

        try:
            payload = json.loads(
                self._autodiscover_cache_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(payload, dict):
            return None
        return payload

    def _cache_autodiscover(self, service_endpoint: str) -> None:
        self._autodiscover_cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "email": self._email,
            "username": self._username,
            "service_endpoint": service_endpoint,
        }
        self._autodiscover_cache_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
