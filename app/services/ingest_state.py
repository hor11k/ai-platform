import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ScannedFile:
    path: Path
    mtime: float
    size: int


@dataclass(frozen=True, slots=True)
class FileStateEntry:
    mtime: float
    size: int


@dataclass(slots=True)
class IngestState:
    last_scan_at: datetime | None
    files: dict[str, FileStateEntry]

    @classmethod
    def empty(cls) -> IngestState:
        return cls(last_scan_at=None, files={})

    @classmethod
    def load(cls, path: Path) -> IngestState:
        if not path.is_file():
            return cls.empty()

        data = json.loads(path.read_text(encoding="utf-8"))
        last_scan_raw = data.get("last_scan_at")
        last_scan_at = datetime.fromisoformat(last_scan_raw) if last_scan_raw else None
        files = {
            file_path: FileStateEntry(
                mtime=entry["mtime"],
                size=entry["size"],
            )
            for file_path, entry in data.get("files", {}).items()
        }
        return cls(last_scan_at=last_scan_at, files=files)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        last_scan_at = self.last_scan_at.isoformat() if self.last_scan_at else None
        payload = {
            "last_scan_at": last_scan_at,
            "files": {
                file_path: {"mtime": entry.mtime, "size": entry.size}
                for file_path, entry in self.files.items()
            },
        }
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def is_changed(self, scanned_file: ScannedFile) -> bool:
        key = str(scanned_file.path.resolve())
        entry = self.files.get(key)
        if entry is None:
            return True
        return entry.mtime != scanned_file.mtime or entry.size != scanned_file.size

    def update_file(self, scanned_file: ScannedFile) -> None:
        key = str(scanned_file.path.resolve())
        self.files[key] = FileStateEntry(
            mtime=scanned_file.mtime,
            size=scanned_file.size,
        )

    def mark_scanned(self) -> None:
        self.last_scan_at = datetime.now(UTC)
