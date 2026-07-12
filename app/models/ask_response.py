from pydantic import BaseModel, Field


class SourceGroup(BaseModel):
    primary_path: str
    primary_filename: str
    alternate_paths: list[str] = Field(default_factory=list)


class AskResponse(BaseModel):
    answer: str
    confidence: int = 0
    source_groups: list[SourceGroup] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
