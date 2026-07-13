from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from app.core.config import get_settings
from app.main import app
from app.services.session_store import SessionStore

runner = CliRunner()

SAMPLE_INDEX = """\
/Volumes/DISK h3r/WRK/19 Химки/Договор займа Химки 2024.docx
/Volumes/DISK h3r/WRK/19 Химки/Справка Химки.docx
/Volumes/DISK h3r/WRK/18 ВТБ СПОРТ/Справка ВТБ Спорт.docx
"""


def _configure_env(tmp_path: Path, monkeypatch, *, wrk_root: Path) -> tuple[Path, Path]:
    session_path = tmp_path / "session.json"
    index_path = tmp_path / "files.txt"
    index_lines = []
    for line in SAMPLE_INDEX.splitlines():
        if not line.strip():
            continue
        relative = line.split("/WRK/", 1)[1]
        index_lines.append(str(wrk_root / relative))
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    monkeypatch.setenv("SEARCH_INDEX_PATH", str(index_path))
    monkeypatch.setenv("SESSION_STATE_PATH", str(session_path))
    get_settings.cache_clear()
    return session_path, index_path


def test_find_open_last_integration(tmp_path: Path, monkeypatch) -> None:
    wrk_root = tmp_path / "WRK"
    loan = wrk_root / "19 Химки" / "Договор займа Химки 2024.docx"
    other = wrk_root / "19 Химки" / "Справка Химки.docx"
    vtb = wrk_root / "18 ВТБ СПОРТ" / "Справка ВТБ Спорт.docx"
    for path in (loan, other, vtb):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content", encoding="utf-8")

    session_path, _ = _configure_env(tmp_path, monkeypatch, wrk_root=wrk_root)

    find_result = runner.invoke(app, ["find", "договор", "займа", "химки"])
    assert find_result.exit_code == 0

    state = SessionStore.load(session_path)
    assert len(state.last_results) >= 1
    assert state.last_command == "find"

    with patch("app.services.open_service.subprocess.run") as mock_run:
        open_first = runner.invoke(app, ["open", "1"])

    assert open_first.exit_code == 0
    assert "Opening:" in open_first.stdout
    assert "19 Химки/Договор займа Химки 2024.docx" in open_first.stdout
    mock_run.assert_called_with(["open", str(loan)], check=True)

    with patch("app.services.open_service.subprocess.run") as mock_run:
        open_last = runner.invoke(app, ["open", "last"])

    assert open_last.exit_code == 0
    mock_run.assert_called_with(["open", str(loan)], check=True)


def test_find_open_filename_integration(tmp_path: Path, monkeypatch) -> None:
    wrk_root = tmp_path / "WRK"
    loan = wrk_root / "19 Химки" / "Договор займа Химки 2024.docx"
    loan.parent.mkdir(parents=True)
    loan.write_text("content", encoding="utf-8")

    _configure_env(tmp_path, monkeypatch, wrk_root=wrk_root)
    runner.invoke(app, ["find", "договор", "займа"])

    with patch("app.services.open_service.subprocess.run") as mock_run:
        result = runner.invoke(app, ["open", "Договор займа"])

    assert result.exit_code == 0
    assert "19 Химки/Договор займа Химки 2024.docx" in result.stdout
    mock_run.assert_called_once_with(["open", str(loan)], check=True)
