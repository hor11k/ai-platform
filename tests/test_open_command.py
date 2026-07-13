from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from app.core.config import get_settings
from app.main import app
from app.models.ask_response import AskResponse, RetrievalDebugItem, SourceGroup
from app.models.session_state import SessionEntry
from app.services.session_store import SessionStore

runner = CliRunner()

SAMPLE_INDEX = """\
/Volumes/DISK h3r/WRK/19 Химки/Договор займа Химки.docx
/Volumes/DISK h3r/WRK/18 ВТБ СПОРТ/Справка ВТБ Спорт.docx
"""


def test_open_help() -> None:
    result = runner.invoke(app, ["open", "--help"])

    assert result.exit_code == 0
    assert "Open a document" in result.stdout


def test_open_command_renders_relative_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    doc = tmp_path / "WRK" / "19 Химки" / "Договор займа Химки.docx"
    doc.parent.mkdir(parents=True)
    doc.write_text("loan", encoding="utf-8")

    session_path = tmp_path / "session.json"
    index_path = tmp_path / "files.txt"
    index_path.write_text(
        SAMPLE_INDEX.replace("/Volumes/DISK h3r", str(tmp_path)),
        encoding="utf-8",
    )

    monkeypatch.setenv("SEARCH_INDEX_PATH", str(index_path))
    monkeypatch.setenv("SESSION_STATE_PATH", str(session_path))
    get_settings.cache_clear()

    runner.invoke(app, ["find", "договор", "химки"])

    with patch("app.services.open_service.subprocess.run") as mock_run:
        result = runner.invoke(app, ["open", "1"])

    assert result.exit_code == 0
    assert "Opening:" in result.stdout
    assert "19 Химки/Договор займа Химки.docx" in result.stdout
    mock_run.assert_called_once()


def test_open_command_reports_missing_file(tmp_path: Path, monkeypatch) -> None:
    session_path = tmp_path / "session.json"
    missing = tmp_path / "WRK" / "19 Химки" / "missing.docx"
    SessionStore.save_results(
        session_path,
        command="find",
        results=[
            SessionEntry(path=str(missing), filename=missing.name),
        ],
    )

    monkeypatch.setenv("SESSION_STATE_PATH", str(session_path))
    get_settings.cache_clear()

    result = runner.invoke(app, ["open", "1"])

    assert result.exit_code == 1
    assert "File no longer exists" in result.stderr


def test_open_command_uses_ask_results(tmp_path: Path, monkeypatch) -> None:
    doc = tmp_path / "WRK" / "19 Химки" / "Договор займа Химки.docx"
    doc.parent.mkdir(parents=True)
    doc.write_text("loan", encoding="utf-8")
    session_path = tmp_path / "session.json"

    monkeypatch.setenv("SESSION_STATE_PATH", str(session_path))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()

    response = AskResponse(
        answer="Документ найден.",
        confidence=90,
        source_groups=[
            SourceGroup(
                primary_path=str(doc),
                primary_filename=doc.name,
            )
        ],
        sources=[str(doc)],
        retrieval_debug=[
            RetrievalDebugItem(
                score=200.0,
                reason="filename match (all terms)",
                filename=doc.name,
                path=str(doc),
            )
        ],
    )

    with patch("app.commands.ask.RagService.ask", return_value=response):
        ask_result = runner.invoke(
            app,
            ["ask", "Где лежит последний договор займа по Химкам?"],
        )

    assert ask_result.exit_code == 0

    with patch("app.services.open_service.subprocess.run") as mock_run:
        open_result = runner.invoke(app, ["open", "1"])

    assert open_result.exit_code == 0
    assert "19 Химки/Договор займа Химки.docx" in open_result.stdout
    mock_run.assert_called_once()
