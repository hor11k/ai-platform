import json
from pathlib import Path

from app.models.session_state import SessionEntry, SessionState


class SessionStore:
    """Persist the last find/ask result list and last opened document."""

    @classmethod
    def load(cls, path: Path) -> SessionState:
        if not path.is_file():
            return SessionState()

        data = json.loads(path.read_text(encoding="utf-8"))
        return SessionState.model_validate(data)

    @classmethod
    def save(cls, path: Path, state: SessionState) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            state.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def save_results(
        cls,
        path: Path,
        *,
        command: str,
        results: list[SessionEntry],
    ) -> None:
        state = cls.load(path)
        state.last_command = command
        state.last_results = results
        cls.save(path, state)

    @classmethod
    def mark_opened(cls, path: Path, opened_path: str) -> None:
        state = cls.load(path)
        state.last_opened_path = opened_path
        cls.save(path, state)
