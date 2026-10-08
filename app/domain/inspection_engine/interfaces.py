# Declares the interface implemented by inspection engines.
from typing import Protocol

from app.domain.inspection_engine.types import (
    InspectionEngineInput,
    InspectionEngineOutput,
)


class InspectionEngine(Protocol):
    def inspect(
        self, inspection_input: InspectionEngineInput
    ) -> InspectionEngineOutput: ...
