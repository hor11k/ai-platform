from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from exchangelib import DELEGATE, NTLM, Credentials

from app.services.exchange_service import ExchangeService, ExchangeServiceError

DOMAIN_USERNAME = r"fwind.int\zuevin"
MAILBOX_EMAIL = "zuevin@fordewind-sk.ru"


class _FakeSender:
    def __init__(self, name: str | None, email_address: str | None) -> None:
        self.name = name
        self.email_address = email_address


class _FakeMessage:
    def __init__(
        self,
        *,
        subject: str,
        sender: _FakeSender,
        received_at: datetime,
        is_read: bool,
    ) -> None:
        self.subject = subject
        self.sender = sender
        self.datetime_received = received_at
        self.is_read = is_read


def _fake_account(messages: list[_FakeMessage]) -> MagicMock:
    account = MagicMock()
    account.inbox.all.return_value.order_by.return_value.__getitem__.return_value = (
        messages
    )
    return account


def _service(
    tmp_path: Path,
    *,
    server: str | None = "https://mail.example.com/EWS/Exchange.asmx",
    username: str = DOMAIN_USERNAME,
    email: str = MAILBOX_EMAIL,
    password: str = "secret",
    account: MagicMock | None = None,
) -> ExchangeService:
    return ExchangeService(
        server=server,
        username=username,
        email=email,
        password=password,
        autodiscover_cache_path=tmp_path / "exchange_autodiscover.json",
        account=account,
    )


def test_list_inbox_reads_messages_from_exchange_account(tmp_path: Path) -> None:
    messages = [
        _FakeMessage(
            subject="Loan contract update",
            sender=_FakeSender("Alex Smith", "alex@example.com"),
            received_at=datetime(2026, 7, 13, 10, 15, tzinfo=UTC),
            is_read=False,
        ),
        _FakeMessage(
            subject="Weekly report",
            sender=_FakeSender(None, "reports@example.com"),
            received_at=datetime(2026, 7, 12, 8, 0, tzinfo=UTC),
            is_read=True,
        ),
    ]
    service = _service(tmp_path, account=_fake_account(messages))

    result = service.list_inbox()

    assert len(result) == 2
    assert result[0].subject == "Loan contract update"
    assert result[0].sender == "Alex Smith"
    assert result[0].is_read is False
    assert result[1].sender == "reports@example.com"


def test_connect_account_uses_ntlm_credentials_and_mailbox_email(tmp_path: Path) -> None:
    cache_path = tmp_path / "exchange_autodiscover.json"
    service = ExchangeService(
        server="https://mail.fordewind-sk.ru/EWS/Exchange.asmx",
        username=DOMAIN_USERNAME,
        email=MAILBOX_EMAIL,
        password="secret",
        autodiscover_cache_path=cache_path,
    )
    fake_account = MagicMock()
    credentials = Credentials(username=DOMAIN_USERNAME, password="secret")

    with (
        patch(
            "app.services.exchange_service.Credentials",
            return_value=credentials,
        ) as credentials_cls,
        patch("app.services.exchange_service.Configuration") as configuration_cls,
        patch(
            "app.services.exchange_service.Account",
            return_value=fake_account,
        ) as account_cls,
    ):
        account = service._connect_account()

    assert account is fake_account
    credentials_cls.assert_called_once_with(
        username=DOMAIN_USERNAME,
        password="secret",
    )
    configuration_cls.assert_called_once_with(
        service_endpoint="https://mail.fordewind-sk.ru/EWS/Exchange.asmx",
        credentials=credentials,
        auth_type=NTLM,
    )
    account_cls.assert_called_once_with(
        primary_smtp_address=MAILBOX_EMAIL,
        credentials=credentials,
        autodiscover=False,
        config=configuration_cls.return_value,
        access_type=DELEGATE,
    )


def test_connect_account_caches_configured_server_endpoint(tmp_path: Path) -> None:
    cache_path = tmp_path / "exchange_autodiscover.json"
    service = ExchangeService(
        server="https://mail.fordewind-sk.ru/EWS/Exchange.asmx",
        username=DOMAIN_USERNAME,
        email=MAILBOX_EMAIL,
        password="secret",
        autodiscover_cache_path=cache_path,
    )
    fake_account = MagicMock()

    with (
        patch("app.services.exchange_service.Configuration"),
        patch("app.services.exchange_service.Account", return_value=fake_account),
    ):
        service._connect_account()

    payload = cache_path.read_text(encoding="utf-8")
    assert "mail.fordewind-sk.ru" in payload
    assert MAILBOX_EMAIL in payload
    assert "fwind.int" in payload
    assert "zuevin" in payload


def test_resolve_service_endpoint_uses_autodiscover_cache(tmp_path: Path) -> None:
    cache_path = tmp_path / "exchange_autodiscover.json"
    cache_path.write_text(
        (
            '{\n  "email": "zuevin@fordewind-sk.ru",\n'
            '  "username": "fwind.int\\\\zuevin",\n'
            '  "service_endpoint": "https://cached.example.com/EWS/Exchange.asmx"\n}\n'
        ),
        encoding="utf-8",
    )
    service = ExchangeService(
        server=None,
        username=DOMAIN_USERNAME,
        email=MAILBOX_EMAIL,
        password="secret",
        autodiscover_cache_path=cache_path,
    )

    endpoint = service._resolve_service_endpoint()

    assert endpoint == "https://cached.example.com/EWS/Exchange.asmx"


def test_discover_service_endpoint_uses_mailbox_email(tmp_path: Path) -> None:
    cache_path = tmp_path / "exchange_autodiscover.json"
    fake_account = MagicMock()
    fake_account.protocol.service_endpoint = (
        "https://discovered.example.com/EWS/Exchange.asmx"
    )
    credentials = Credentials(username=DOMAIN_USERNAME, password="secret")

    service = ExchangeService(
        server=None,
        username=DOMAIN_USERNAME,
        email=MAILBOX_EMAIL,
        password="secret",
        autodiscover_cache_path=cache_path,
    )

    with (
        patch(
            "app.services.exchange_service.Credentials",
            return_value=credentials,
        ),
        patch(
            "app.services.exchange_service.Account",
            return_value=fake_account,
        ) as account_cls,
    ):
        endpoint = service._discover_service_endpoint()

    assert endpoint == "https://discovered.example.com/EWS/Exchange.asmx"
    account_cls.assert_called_once_with(
        primary_smtp_address=MAILBOX_EMAIL,
        credentials=credentials,
        autodiscover=True,
        access_type=DELEGATE,
    )
    assert "discovered.example.com" in cache_path.read_text(encoding="utf-8")


def test_list_inbox_raises_friendly_exchange_error(tmp_path: Path) -> None:
    account = MagicMock()
    account.inbox.all.side_effect = RuntimeError("connection failed")
    service = _service(tmp_path, account=account)

    with pytest.raises(ExchangeServiceError, match="Could not read Exchange inbox"):
        service.list_inbox()


def test_to_message_handles_missing_fields(tmp_path: Path) -> None:
    service = _service(tmp_path)

    message = service._to_message(_FakeMessage(
        subject="",
        sender=_FakeSender(None, None),
        received_at=datetime(2026, 1, 1, tzinfo=UTC),
        is_read=False,
    ))

    assert message.subject == "(No subject)"
    assert message.sender == "Unknown"
    assert message.is_read is False
