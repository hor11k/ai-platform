import time
from pathlib import Path

from app.services.ingest_service import IngestService


def _configure_paths(tmp_path: Path) -> dict[str, Path]:
    wrk = tmp_path / "wrk"
    downloads = tmp_path / "downloads"
    wrk.mkdir()
    downloads.mkdir()
    return {
        "scan_paths": [wrk, downloads],
        "file_index_path": tmp_path / "files.txt",
        "content_index_path": tmp_path / "content",
        "state_path": tmp_path / "ingest_state.json",
    }


def test_ingest_indexes_new_files(tmp_path: Path) -> None:
    paths = _configure_paths(tmp_path)
    source = paths["scan_paths"][0] / "report.txt"
    source.write_text("Quarterly report", encoding="utf-8")

    service = IngestService(**paths, max_workers=2)
    result = service.ingest()

    assert result.scanned_files == 1
    assert result.new_or_changed_files == 1
    assert result.text_indexed == 1
    assert result.skipped_unchanged == 0
    assert result.file_index_total == 1
    assert (paths["content_index_path"] / "report.txt.txt").is_file()
    assert str(source.resolve()) in paths["file_index_path"].read_text(encoding="utf-8")


def test_ingest_skips_unchanged_files(tmp_path: Path) -> None:
    paths = _configure_paths(tmp_path)
    source = paths["scan_paths"][0] / "stable.txt"
    source.write_text("Stable content", encoding="utf-8")

    service = IngestService(**paths, max_workers=2)
    first = service.ingest()
    content_path = paths["content_index_path"] / "stable.txt.txt"
    first_mtime = content_path.stat().st_mtime

    second = service.ingest()

    assert first.text_indexed == 1
    assert second.new_or_changed_files == 0
    assert second.text_indexed == 0
    assert second.skipped_unchanged == 1
    assert content_path.stat().st_mtime == first_mtime


def test_ingest_reindexes_changed_files(tmp_path: Path) -> None:
    paths = _configure_paths(tmp_path)
    source = paths["scan_paths"][0] / "draft.txt"
    source.write_text("Version 1", encoding="utf-8")

    service = IngestService(**paths, max_workers=2)
    service.ingest()

    time.sleep(0.01)
    source.write_text("Version 2", encoding="utf-8")

    result = service.ingest()

    assert result.new_or_changed_files == 1
    assert result.text_indexed == 1
    assert (paths["content_index_path"] / "draft.txt.txt").read_text(
        encoding="utf-8"
    ) == "Version 2"


def test_ingest_includes_non_indexable_in_file_index(tmp_path: Path) -> None:
    paths = _configure_paths(tmp_path)
    text_file = paths["scan_paths"][0] / "doc.txt"
    image_file = paths["scan_paths"][1] / "photo.jpg"
    text_file.write_text("hello", encoding="utf-8")
    image_file.write_bytes(b"image")

    result = IngestService(**paths, max_workers=2).ingest()

    assert result.new_or_changed_files == 2
    assert result.text_indexed == 1
    index_lines = paths["file_index_path"].read_text(encoding="utf-8").splitlines()
    assert len(index_lines) == 2


def test_ingest_progress_callbacks(tmp_path: Path) -> None:
    paths = _configure_paths(tmp_path)
    (paths["scan_paths"][0] / "a.txt").write_text("a", encoding="utf-8")
    (paths["scan_paths"][0] / "b.txt").write_text("b", encoding="utf-8")

    started: list[int] = []
    progressed: list[str] = []

    service = IngestService(**paths, max_workers=2)
    service.ingest(
        on_start=started.append,
        progress_callback=progressed.append,
    )

    assert started == [2]
    assert sorted(progressed) == ["a.txt", "b.txt"]
