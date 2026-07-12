from pathlib import Path

from typer.testing import CliRunner

from app.core.config import get_settings
from app.main import app

runner = CliRunner()


def test_ingest_help() -> None:
    result = runner.invoke(app, ["ingest", "--help"])

    assert result.exit_code == 0
    assert "Incrementally index" in result.stdout


def test_ingest_command_rich_output(tmp_path: Path, monkeypatch) -> None:
    wrk = tmp_path / "wrk"
    downloads = tmp_path / "downloads"
    wrk.mkdir()
    downloads.mkdir()
    (wrk / "summary.txt").write_text("Ingest me", encoding="utf-8")

    monkeypatch.setenv("INGEST_WRK_PATH", str(wrk))
    monkeypatch.setenv("INGEST_DOWNLOADS_PATH", str(downloads))
    monkeypatch.setenv("SEARCH_INDEX_PATH", str(tmp_path / "files.txt"))
    monkeypatch.setenv("CONTENT_INDEX_PATH", str(tmp_path / "content"))
    monkeypatch.setenv("INGEST_STATE_PATH", str(tmp_path / "ingest_state.json"))
    get_settings.cache_clear()

    result = runner.invoke(app, ["ingest"])

    assert result.exit_code == 0
    assert "Ingest Summary" in result.stdout
    assert "Scanned files" in result.stdout
    assert "Skipped unchanged" in result.stdout
    assert "Incremental ingest completed successfully" in result.stdout
    assert (tmp_path / "content" / "summary.txt.txt").is_file()
