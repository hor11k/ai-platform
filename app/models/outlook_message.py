from datetime import datetime

from pydantic import BaseModel


class OutlookMessage(BaseModel):
    subject: str
    sender: str
    received_at: datetime
    is_read: bool
