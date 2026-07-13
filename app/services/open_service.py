import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.text import normalize_text
from app.models.session_state import SessionEntry, SessionState
from app.services.session_store import SessionStore


class OpenServiceError(Exception):
    """User-friendly error raised when a document cannot be opened."""


@dataclass(frozen=True, slots=True)
class OpenResult:
    path: str
    relative_path: str
    filename: str


class OpenService:
    """Open documents from the last find/ask result list."""

    def __init__(self, session_path: Path) -> None:
        self._session_path = session_path

    def open(self, target: str) -> OpenResult:
        state = SessionStore.load(self._session_path)
        entry = self._resolve_target(state, target)
        path = Path(entry.path)

        if not path.is_file():
            relative_path = self._relative_display_path(entry.path)
            msg = f"File no longer exists: {relative_path}"
            raise OpenServiceError(msg)

        self._launch_file(path)
        SessionStore.mark_opened(self._session_path, entry.path)

        return OpenResult(
            path=entry.path,
            relative_path=self._relative_display_path(entry.path),
            filename=entry.filename,
        )

    def _resolve_target(self, state: SessionState, target: str) -> SessionEntry:
        normalized_target = target.strip()
        if not normalized_target:
            msg = "Provide a result number, last, or a filename to open."
            raise OpenServiceError(msg)

        if normalized_target.lower() == "last":
            return self._resolve_last_opened(state)

        if normalized_target.isdigit():
            return self._resolve_index(state, int(normalized_target))

        return self._resolve_filename(state, normalized_target)

    def _resolve_last_opened(self, state: SessionState) -> SessionEntry:
        if not state.last_opened_path:
            msg = "No recently opened document. Run ai find or ai ask first."
            raise OpenServiceError(msg)

        filename = Path(state.last_opened_path).name
        return SessionEntry(path=state.last_opened_path, filename=filename)

    def _resolve_index(self, state: SessionState, index: int) -> SessionEntry:
        if not state.last_results:
            msg = "No recent results to open. Run ai find or ai ask first."
            raise OpenServiceError(msg)

        if index < 1 or index > len(state.last_results):
            msg = (
                f"Result {index} is out of range. "
                f"Last command returned {len(state.last_results)} result(s)."
            )
            raise OpenServiceError(msg)

        return state.last_results[index - 1]

    def _resolve_filename(self, state: SessionState, target: str) -> SessionEntry:
        if not state.last_results:
            msg = "No recent results to open. Run ai find or ai ask first."
            raise OpenServiceError(msg)

        normalized_target = normalize_text(target)
        matches = [
            entry
            for entry in state.last_results
            if normalized_target in normalize_text(entry.filename)
        ]

        if not matches:
            msg = f"No recent result matches: {target}"
            raise OpenServiceError(msg)

        if len(matches) > 1:
            exact = [
                entry
                for entry in matches
                if normalize_text(entry.filename) == normalized_target
            ]
            if len(exact) == 1:
                return exact[0]

        return matches[0]

    def _launch_file(self, path: Path) -> None:
        try:
            subprocess.run(["open", str(path)], check=True)
        except FileNotFoundError as exc:
            msg = "The macOS open command is not available on this system."
            raise OpenServiceError(msg) from exc
        except subprocess.CalledProcessError as exc:
            msg = f"Failed to open file: {path.name}"
            raise OpenServiceError(msg) from exc

    @staticmethod
    def _relative_display_path(path: str) -> str:
        parts = Path(path).parts
        if "WRK" in parts:
            wrk_index = parts.index("WRK")
            return str(Path(*parts[wrk_index + 1 :]))
        return Path(path).name
