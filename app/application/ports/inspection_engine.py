# Declares the interface implemented by inspection engines.
from typing import Protocol

from app.application.ports.inspection_engine_types import (
    InspectionEngineInput,
    InspectionEngineOutput,
)


class InspectionEngine(Protocol):
    def inspect(
        self, inspection_input: InspectionEngineInput
    ) -> InspectionEngineOutput: ...
