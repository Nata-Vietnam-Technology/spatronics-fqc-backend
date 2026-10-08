# Implements the inspection repository interface with in-memory storage.
from itertools import count

from app.schemas.inspection import Inspection


class InMemoryInspectionRepository:
    def __init__(self) -> None:
        self._inspections: dict[str, Inspection] = {}
        self._inspection_ids = count(1)

    def allocate_inspection_id(self) -> str:
        return f"INS-{next(self._inspection_ids):05d}"

    def save(self, inspection: Inspection) -> None:
        self._inspections[inspection.id] = inspection.model_copy(deep=True)

    def get_by_id(self, inspection_id: str) -> Inspection | None:
        inspection = self._inspections.get(inspection_id)
        return inspection.model_copy(deep=True) if inspection is not None else None

    def get_by_shift(self, shift_id: str) -> list[Inspection]:
        return [
            inspection.model_copy(deep=True)
            for inspection in self._inspections.values()
            if inspection.shift_id == shift_id
        ]
