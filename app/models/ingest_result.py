from datetime import UTC, datetime

from pydantic import BaseModel, Field


class IngestResult(BaseModel):
    scanned_files: int = 0
    new_or_changed_files: int = 0
    text_indexed: int = 0
    skipped_unchanged: int = 0
    failed: int = 0
    file_index_total: int = 0
    last_scan_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
