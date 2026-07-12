from pathlib import Path

from app.services.file_scanner import FileScanner


def test_scan_finds_files_recursively(tmp_path: Path) -> None:
    wrk = tmp_path / "wrk"
    downloads = tmp_path / "downloads"
    (wrk / "nested").mkdir(parents=True)
    downloads.mkdir()
    (wrk / "nested" / "alpha.txt").write_text("alpha", encoding="utf-8")
    (downloads / "beta.txt").write_text("beta", encoding="utf-8")

    scanner = FileScanner([wrk, downloads])
    scanned = scanner.scan()

    assert len(scanned) == 2
    names = {item.path.name for item in scanned}
    assert names == {"alpha.txt", "beta.txt"}


def test_scan_skips_hidden_files(tmp_path: Path) -> None:
    root = tmp_path / "wrk"
    root.mkdir()
    (root / "visible.txt").write_text("ok", encoding="utf-8")
    (root / ".hidden.txt").write_text("hidden", encoding="utf-8")

    scanned = FileScanner([root]).scan()

    assert len(scanned) == 1
    assert scanned[0].path.name == "visible.txt"


def test_scan_ignores_missing_directories(tmp_path: Path) -> None:
    root = tmp_path / "wrk"
    root.mkdir()
    (root / "only.txt").write_text("ok", encoding="utf-8")

    scanned = FileScanner([root, tmp_path / "missing"]).scan()

    assert len(scanned) == 1


def test_scan_deduplicates_same_path(tmp_path: Path) -> None:
    root = tmp_path / "wrk"
    root.mkdir()
    (root / "doc.txt").write_text("content", encoding="utf-8")

    scanned = FileScanner([root, root]).scan()

    assert len(scanned) == 1
