from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from app.core.config import get_settings
from app.main import app
from app.models.outlook_message import OutlookMessage
from app.services.exchange_service import ExchangeServiceError

runner = CliRunner()


def test_inbox_help() -> None:
    result = runner.invoke(app, ["inbox", "--help"])

    assert result.exit_code == 0
    assert "Exchange inbox" in result.stdout


def test_inbox_command_renders_messages(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(
        "EXCHANGE_SERVER",
        "https://mail.fordewind-sk.ru/EWS/Exchange.asmx",
    )
    monkeypatch.setenv("EXCHANGE_USERNAME", r"fwind.int\zuevin")
    monkeypatch.setenv("EXCHANGE_EMAIL", "zuevin@fordewind-sk.ru")
    monkeypatch.setenv("EXCHANGE_PASSWORD", "secret")
    monkeypatch.setenv(
        "EXCHANGE_AUTODISCOVER_CACHE_PATH",
        str(tmp_path / "exchange_autodiscover.json"),
    )
    get_settings.cache_clear()

    messages = [
        OutlookMessage(
            subject="Loan contract update",
            sender="Alex Smith",
            received_at=datetime(2026, 7, 13, 10, 15, tzinfo=UTC),
            is_read=False,
        )
    ]

    with patch(
        "app.commands.inbox.ExchangeService.list_inbox",
        return_value=messages,
    ):
        result = runner.invoke(app, ["inbox"])

    assert result.exit_code == 0
    assert "Outlook Inbox" in result.stdout
    assert "Loan contract update" in result.stdout
    assert "Alex Smith" in result.stdout
    assert "2026-07-13 10:15" in result.stdout


def test_inbox_command_requires_exchange_credentials(monkeypatch) -> None:
    monkeypatch.setenv("EXCHANGE_USERNAME", "")
    monkeypatch.setenv("EXCHANGE_PASSWORD", "")
    monkeypatch.setenv("EXCHANGE_EMAIL", "")
    get_settings.cache_clear()

    result = runner.invoke(app, ["inbox"])

    assert result.exit_code == 1
    assert "EXCHANGE_USERNAME and EXCHANGE_PASSWORD must be configured" in result.stderr


def test_inbox_command_reports_service_errors(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(
        "EXCHANGE_SERVER",
        "https://mail.fordewind-sk.ru/EWS/Exchange.asmx",
    )
    monkeypatch.setenv("EXCHANGE_USERNAME", r"fwind.int\zuevin")
    monkeypatch.setenv("EXCHANGE_EMAIL", "zuevin@fordewind-sk.ru")
    monkeypatch.setenv("EXCHANGE_PASSWORD", "secret")
    monkeypatch.setenv(
        "EXCHANGE_AUTODISCOVER_CACHE_PATH",
        str(tmp_path / "exchange_autodiscover.json"),
    )
    get_settings.cache_clear()

    with patch(
        "app.commands.inbox.ExchangeService.list_inbox",
        side_effect=ExchangeServiceError("Exchange authentication failed"),
    ):
        result = runner.invoke(app, ["inbox"])

    assert result.exit_code == 1
    assert "Exchange authentication failed" in result.stderr
