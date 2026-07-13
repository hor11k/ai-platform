from pathlib import Path
from unittest.mock import patch

import pytest

from app.models.session_state import SessionEntry
from app.services.open_service import OpenService, OpenServiceError
from app.services.session_store import SessionStore


@pytest.fixture
def session_path(tmp_path: Path) -> Path:
    return tmp_path / "session.json"


def _save_results(session_path: Path, entries: list[SessionEntry]) -> None:
    SessionStore.save_results(
        session_path,
        command="find",
        results=entries,
    )


def test_open_by_index_opens_first_result(session_path: Path) -> None:
    doc = session_path.parent / "WRK" / "19 Химки" / "Договор займа.docx"
    doc.parent.mkdir(parents=True)
    doc.write_text("loan", encoding="utf-8")
    _save_results(
        session_path,
        [SessionEntry(path=str(doc), filename=doc.name)],
    )
    service = OpenService(session_path)

    with patch("app.services.open_service.subprocess.run") as mock_run:
        result = service.open("1")

    assert result.filename == "Договор займа.docx"
    assert result.relative_path == "19 Химки/Договор займа.docx"
    mock_run.assert_called_once_with(["open", str(doc)], check=True)
    assert SessionStore.load(session_path).last_opened_path == str(doc)


def test_open_last_reopens_previous_document(session_path: Path) -> None:
    first = session_path.parent / "first.docx"
    second = session_path.parent / "second.docx"
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")
    _save_results(
        session_path,
        [
            SessionEntry(path=str(first), filename=first.name),
            SessionEntry(path=str(second), filename=second.name),
        ],
    )
    service = OpenService(session_path)

    with patch("app.services.open_service.subprocess.run"):
        service.open("2")

    with patch("app.services.open_service.subprocess.run") as mock_run:
        result = service.open("last")

    assert result.path == str(second)
    mock_run.assert_called_once_with(["open", str(second)], check=True)


def test_open_by_filename_matches_recent_results(session_path: Path) -> None:
    doc = session_path.parent / "Договор займа Химки.docx"
    doc.write_text("loan", encoding="utf-8")
    other = session_path.parent / "other.docx"
    other.write_text("other", encoding="utf-8")
    _save_results(
        session_path,
        [
            SessionEntry(path=str(other), filename=other.name),
            SessionEntry(path=str(doc), filename=doc.name),
        ],
    )
    service = OpenService(session_path)

    with patch("app.services.open_service.subprocess.run") as mock_run:
        result = service.open("Договор займа")

    assert result.path == str(doc)
    mock_run.assert_called_once_with(["open", str(doc)], check=True)


def test_open_missing_file_raises_friendly_error(session_path: Path) -> None:
    missing = session_path.parent / "missing.docx"
    _save_results(
        session_path,
        [SessionEntry(path=str(missing), filename=missing.name)],
    )
    service = OpenService(session_path)

    with pytest.raises(OpenServiceError, match="File no longer exists"):
        service.open("1")


def test_open_without_results_raises_friendly_error(session_path: Path) -> None:
    service = OpenService(session_path)

    with pytest.raises(OpenServiceError, match="No recent results"):
        service.open("1")


def test_open_last_without_history_raises_friendly_error(session_path: Path) -> None:
    service = OpenService(session_path)

    with pytest.raises(OpenServiceError, match="No recently opened document"):
        service.open("last")


def test_open_out_of_range_index_raises_friendly_error(session_path: Path) -> None:
    doc = session_path.parent / "only.docx"
    doc.write_text("only", encoding="utf-8")
    _save_results(session_path, [SessionEntry(path=str(doc), filename=doc.name)])
    service = OpenService(session_path)

    with pytest.raises(OpenServiceError, match="out of range"):
        service.open("3")
