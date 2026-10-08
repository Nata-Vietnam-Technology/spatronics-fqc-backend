# Builds shift inspection history and calculates its summary counts.
from app.domain.inspection.enums import InspectionResult
from app.application.ports.inspection_repository import InspectionRepository
from app.schemas.shift import (
    ShiftHistoryItem,
    ShiftHistoryResponse,
    ShiftHistorySummary,
    ShiftInfo,
)


class ShiftService:
    def __init__(self, repository: InspectionRepository) -> None:
        self._repository = repository

    def get_inspections(
        self,
        *,
        shift_id: str,
        result: InspectionResult | None = None,
        reviewed: bool | None = None,
    ) -> ShiftHistoryResponse:
        inspections = self._repository.get_by_shift(shift_id)
        inspections.sort(
            key=lambda inspection: inspection.completed_at or inspection.started_at,
            reverse=True,
        )
        all_items = [
            ShiftHistoryItem(
                id=inspection.id,
                sku_code=inspection.sku_code,
                inspected_at=inspection.completed_at or inspection.started_at,
                result=inspection.current_result,
                required_review=any(
                    point.requires_review for point in inspection.points
                ),
                reviewed_points=sum(
                    point.review is not None for point in inspection.points
                ),
                confirmed_defects=sum(
                    point.current_result is InspectionResult.FAIL
                    for point in inspection.points
                ),
            )
            for inspection in inspections
        ]

        items = all_items
        if result is not None:
            items = [item for item in items if item.result is result]
        if reviewed is not None:
            items = [item for item in items if (item.reviewed_points > 0) is reviewed]

        summary = ShiftHistorySummary(
            inspected=len(all_items),
            pass_=sum(item.result is InspectionResult.PASS for item in all_items),
            fail=sum(item.result is InspectionResult.FAIL for item in all_items),
            required_review=sum(item.required_review for item in all_items),
        )
        return ShiftHistoryResponse(
            shift=ShiftInfo(id=shift_id, label=_shift_label(shift_id)),
            summary=summary,
            items=items,
        )


def _shift_label(shift_id: str) -> str:
    parts = shift_id.split("-")
    if len(parts) > 1 and parts[0].upper() == "SHIFT":
        return f"Shift {parts[1]}"
    return shift_id
