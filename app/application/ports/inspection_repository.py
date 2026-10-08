# Defines the inspection repository port used by application services.
from typing import Protocol

from app.schemas.inspection import Inspection


class InspectionRepository(Protocol):
    def allocate_inspection_id(self) -> str: ...

    def save(self, inspection: Inspection) -> None: ...

    def get_by_id(self, inspection_id: str) -> Inspection | None: ...

    def get_by_shift(self, shift_id: str) -> list[Inspection]: ...
