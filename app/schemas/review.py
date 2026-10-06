from datetime import datetime

from app.domain.inspection.enums import ReviewDecision
from app.schemas.common import APIModel


class ReviewRequest(APIModel):
    decision: ReviewDecision
    note: str | None = None


class ReviewRecord(APIModel):
    decision: ReviewDecision
    note: str | None
    reviewed_at: datetime