from pathlib import Path

from app.services.ingest_state import ScannedFile


class FileScanner:
    """Recursively scan configured directories for files."""

    def __init__(self, scan_paths: list[Path]) -> None:
        self._scan_paths = scan_paths

    def scan(self) -> list[ScannedFile]:
        discovered: dict[str, ScannedFile] = {}
        for root in self._scan_paths:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if self._should_skip(path):
                    continue
                stat = path.stat()
                discovered[str(path.resolve())] = ScannedFile(
                    path=path.resolve(),
                    mtime=stat.st_mtime,
                    size=stat.st_size,
                )
        return sorted(discovered.values(), key=lambda item: str(item.path))

    def _should_skip(self, path: Path) -> bool:
        name = path.name
        return name.startswith(".") or name == "Icon\r"
