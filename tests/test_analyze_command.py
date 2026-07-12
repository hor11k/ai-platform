from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from app.core.config import get_settings
from app.exceptions import OpenAIServiceError
from app.main import app
from app.models.document_analysis import DocumentAnalysis

runner = CliRunner()

SAMPLE_ANALYSIS = DocumentAnalysis(
    executive_summary="A construction contract with milestone payments.",
    risks=["Penalty for delay"],
    key_dates=["2026-06-30"],
    key_amounts=["2,000,000 RUB"],
    parties=["Contractor LLC", "Client JSC"],
    action_items=["Submit work acceptance act"],
)


def test_analyze_help() -> None:
    result = runner.invoke(app, ["analyze", "--help"])
    assert result.exit_code == 0
    assert "Analyze a document" in result.stdout


def test_analyze_command_renders_results(tmp_path: Path, monkeypatch) -> None:
    file_path = tmp_path / "contract.txt"
    file_path.write_text("Contract body", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()

    with patch(
        "app.commands.analyze.AnalyzeService.analyze",
        return_value=SAMPLE_ANALYSIS,
    ):
        result = runner.invoke(app, ["analyze", str(file_path)])

    assert result.exit_code == 0
    assert "Executive Summary" in result.stdout
    assert "construction contract" in result.stdout
    assert "Risks" in result.stdout
    assert "Penalty for delay" in result.stdout
    assert "Key Dates" in result.stdout
    assert "Key Amounts" in result.stdout
    assert "Parties" in result.stdout
    assert "Action Items" in result.stdout


def test_analyze_command_missing_api_key(tmp_path: Path, monkeypatch) -> None:
    file_path = tmp_path / "contract.txt"
    file_path.write_text("Contract body", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()

    result = runner.invoke(app, ["analyze", str(file_path)])

    assert result.exit_code == 1
    assert "OPENAI_API_KEY is not configured" in result.stderr


def test_analyze_command_missing_file(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()

    result = runner.invoke(app, ["analyze", "missing-file.txt"])

    assert result.exit_code == 1
    assert "File not found" in result.stderr


def test_analyze_command_openai_error(tmp_path: Path, monkeypatch) -> None:
    file_path = tmp_path / "contract.txt"
    file_path.write_text("Contract body", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()

    with patch(
        "app.commands.analyze.AnalyzeService.analyze",
        side_effect=OpenAIServiceError("OpenAI rate limit exceeded. Wait and retry."),
    ):
        result = runner.invoke(app, ["analyze", str(file_path)])

    assert result.exit_code == 1
    assert "OpenAI rate limit exceeded" in result.stderr
