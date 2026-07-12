import json
from pathlib import Path

from app.services.ingest_state import FileStateEntry, IngestState, ScannedFile


def test_empty_state_treats_all_files_as_changed(tmp_path: Path) -> None:
    state = IngestState.empty()
    scanned = ScannedFile(path=tmp_path / "doc.txt", mtime=1.0, size=10)

    assert state.is_changed(scanned) is True


def test_unchanged_file_is_not_changed(tmp_path: Path) -> None:
    file_path = tmp_path / "doc.txt"
    state = IngestState.empty()
    scanned = ScannedFile(path=file_path, mtime=1.0, size=10)
    state.update_file(scanned)

    assert state.is_changed(scanned) is False


def test_mtime_change_detected(tmp_path: Path) -> None:
    file_path = tmp_path / "doc.txt"
    state = IngestState.empty()
    state.update_file(ScannedFile(path=file_path, mtime=1.0, size=10))

    changed = ScannedFile(path=file_path, mtime=2.0, size=10)

    assert state.is_changed(changed) is True


def test_size_change_detected(tmp_path: Path) -> None:
    file_path = tmp_path / "doc.txt"
    state = IngestState.empty()
    state.update_file(ScannedFile(path=file_path, mtime=1.0, size=10))

    changed = ScannedFile(path=file_path, mtime=1.0, size=20)

    assert state.is_changed(changed) is True


def test_state_round_trip(tmp_path: Path) -> None:
    state_path = tmp_path / "ingest_state.json"
    state = IngestState.empty()
    file_path = tmp_path / "doc.txt"
    scanned = ScannedFile(path=file_path, mtime=1.5, size=42)
    state.update_file(scanned)
    state.mark_scanned()
    state.save(state_path)

    loaded = IngestState.load(state_path)

    assert loaded.last_scan_at is not None
    assert loaded.files[str(file_path.resolve())] == FileStateEntry(mtime=1.5, size=42)


def test_load_missing_state_returns_empty(tmp_path: Path) -> None:
    loaded = IngestState.load(tmp_path / "missing.json")

    assert loaded.last_scan_at is None
    assert loaded.files == {}


def test_save_creates_parent_directory(tmp_path: Path) -> None:
    state_path = tmp_path / "nested" / "ingest_state.json"
    state = IngestState.empty()
    state.mark_scanned()
    state.save(state_path)

    assert state_path.is_file()
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert "last_scan_at" in payload
