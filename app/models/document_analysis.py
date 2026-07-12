from pydantic import BaseModel, Field


class DocumentAnalysis(BaseModel):
    executive_summary: str
    risks: list[str] = Field(default_factory=list)
    key_dates: list[str] = Field(default_factory=list)
    key_amounts: list[str] = Field(default_factory=list)
    parties: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
