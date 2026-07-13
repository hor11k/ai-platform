from pydantic import BaseModel, Field


class SessionEntry(BaseModel):
    path: str
    filename: str


class SessionState(BaseModel):
    last_command: str | None = None
    last_results: list[SessionEntry] = Field(default_factory=list)
    last_opened_path: str | None = None
