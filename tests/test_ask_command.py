from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from app.core.config import get_settings
from app.main import app
from app.models.ask_response import AskResponse, RetrievalDebugItem, SourceGroup

runner = CliRunner()


def test_ask_help() -> None:
    result = runner.invoke(app, ["ask", "--help"])
    assert result.exit_code == 0
    assert "Natural-language question" in result.stdout


def test_ask_command_renders_answer(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()

    response = AskResponse(
        answer="Последний договор займа по Химкам лежит в каталоге проекта.",
        confidence=85,
        source_groups=[
            SourceGroup(
                primary_path="/data/loan-2024.docx",
                primary_filename="loan-2024.docx",
                alternate_paths=["/data/loan-v2.docx"],
            )
        ],
        sources=["/data/loan-2024.docx"],
        retrieval_debug=[
            RetrievalDebugItem(
                score=290.0,
                reason="filename match (all terms)",
                filename="loan-2024.docx",
                path="/data/loan-2024.docx",
            )
        ],
    )

    with patch("app.commands.ask.RagService.ask", return_value=response):
        result = runner.invoke(
            app,
            ["ask", "Где лежит последний договор займа по Химкам?"],
        )

    assert result.exit_code == 0
    assert "Confidence:" in result.stdout
    assert "85%" in result.stdout
    assert "Answer" in result.stdout
    assert "договор займа" in result.stdout
    assert "Sources" in result.stdout
    assert "loan-2024.docx" in result.stdout
    assert "Older versions:" in result.stdout
    assert "loan-v2.docx" in result.stdout
    assert "Retrieved documents" in result.stdout
    assert "filename match" in result.stdout


def test_ask_command_warns_on_low_confidence(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()

    response = AskResponse(
        answer="Возможный ответ.",
        confidence=55,
        source_groups=[
            SourceGroup(
                primary_path="/data/doc.docx",
                primary_filename="doc.docx",
            )
        ],
        sources=["/data/doc.docx"],
    )

    with patch("app.commands.ask.RagService.ask", return_value=response):
        result = runner.invoke(app, ["ask", "Где документ?"])

    assert result.exit_code == 0
    assert "55%" in result.stdout
    assert "may be incomplete" in result.stdout


def test_ask_command_missing_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()

    result = runner.invoke(app, ["ask", "Найди все документы по ВТБ Спорт."])

    assert result.exit_code == 1
    assert "OPENAI_API_KEY is not configured" in result.stderr
