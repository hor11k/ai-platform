from pathlib import Path

from typer.testing import CliRunner

from app.core.config import get_settings
from app.main import app

runner = CliRunner()

SAMPLE_INDEX = """\
/Volumes/DISK h3r/WRK/01 МСТК/Справка/Report Alpha.docx
/Volumes/DISK h3r/WRK/06 iQ/Протечки/Photo-1.jpg
/Volumes/DISK h3r/WRK/03 Match Point/Химки/Договор Химки.docx
"""


def test_find_help() -> None:
    result = runner.invoke(app, ["find", "--help"])
    assert result.exit_code == 0
    assert "Search indexed files" in result.stdout


def test_find_command_renders_results(tmp_path: Path, monkeypatch) -> None:
    index_path = tmp_path / "files.txt"
    index_path.write_text(SAMPLE_INDEX, encoding="utf-8")
    monkeypatch.setenv("SEARCH_INDEX_PATH", str(index_path))
    get_settings.cache_clear()

    result = runner.invoke(app, ["find", "alpha"])

    assert result.exit_code == 0
    assert "Score" in result.stdout
    assert "Filename" in result.stdout
    assert "Project" in result.stdout
    assert "Path" in result.stdout
    assert "Report Alpha.docx" in result.stdout


def test_find_multiple_words_no_quotes(tmp_path: Path, monkeypatch) -> None:
    index_path = tmp_path / "files.txt"
    index_path.write_text(SAMPLE_INDEX, encoding="utf-8")
    monkeypatch.setenv("SEARCH_INDEX_PATH", str(index_path))
    get_settings.cache_clear()

    result = runner.invoke(app, ["find", "договор", "химки"])

    assert result.exit_code == 0
    assert "Договор Химки.docx" in result.stdout
    assert "Search: договор химки" in result.stdout


def test_find_command_highlights_matches(tmp_path: Path, monkeypatch) -> None:
    index_path = tmp_path / "files.txt"
    index_path.write_text(SAMPLE_INDEX, encoding="utf-8")
    monkeypatch.setenv("SEARCH_INDEX_PATH", str(index_path))
    get_settings.cache_clear()

    result = runner.invoke(app, ["find", "договор", "химки"])

    assert result.exit_code == 0
    assert "Договор" in result.stdout
    assert "Химки" in result.stdout


def test_find_command_no_results(tmp_path: Path, monkeypatch) -> None:
    index_path = tmp_path / "files.txt"
    index_path.write_text(SAMPLE_INDEX, encoding="utf-8")
    monkeypatch.setenv("SEARCH_INDEX_PATH", str(index_path))
    get_settings.cache_clear()

    result = runner.invoke(app, ["find", "nonexistent-xyz"])

    assert result.exit_code == 0
    assert "No results for" in result.stdout


def test_find_command_missing_index(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SEARCH_INDEX_PATH", str(tmp_path / "missing.txt"))
    get_settings.cache_clear()

    result = runner.invoke(app, ["find", "alpha"])

    assert result.exit_code == 1
    assert "Search index not found" in result.stderr
