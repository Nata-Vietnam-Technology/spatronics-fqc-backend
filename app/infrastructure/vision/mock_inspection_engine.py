# Provides a mock inspection engine and sample point results for development.
from app.domain.inspection.enums import (
    InspectionGroup,
    InspectionResult,
    InspectionTargetType,
    IssueType,
)
from app.domain.inspection_engine.interfaces import InspectionEngine
from app.domain.inspection_engine.types import (
    EngineBoundingBox,
    EngineCheck,
    EngineEvidence,
    EngineEvidenceValue,
    EnginePoint,
    EnginePolygon,
    InspectionEngineInput,
    InspectionEngineOutput,
)


class MockInspectionEngine(InspectionEngine):
    def inspect(
        self, inspection_input: InspectionEngineInput
    ) -> InspectionEngineOutput:
        view_ids = inspection_input.view_ids
        if len(view_ids) < 3:
            raise ValueError("The mock inspection engine requires at least three views")

        points = (
            EnginePoint(
                id="IP-001",
                target_ref="R12",
                target_type=InspectionTargetType.COMPONENT,
                requires_review=True,
                region=EngineBoundingBox(
                    view_id=view_ids[0], x=0.42, y=0.31, width=0.08, height=0.05
                ),
                checks=(
                    _check(
                        "001-PRESENCE",
                        InspectionGroup.PRESENCE,
                        InspectionResult.PASS,
                        "Presence",
                        "Present",
                        "Present",
                    ),
                    _check(
                        "001-POSITION",
                        InspectionGroup.POSITION,
                        InspectionResult.REVIEW,
                        "Offset",
                        0,
                        1.4,
                        "mm",
                        IssueType.WRONG_POSITION,
                        1.4,
                    ),
                    _check(
                        "001-COLOR",
                        InspectionGroup.COLOR,
                        InspectionResult.PASS,
                        "Color",
                        "red",
                        "red",
                    ),
                    _check(
                        "001-ORIENTATION",
                        InspectionGroup.ORIENTATION,
                        InspectionResult.PASS,
                        "Orientation",
                        "normal",
                        "normal",
                    ),
                ),
            ),
            EnginePoint(
                id="IP-002",
                target_ref="C5",
                target_type=InspectionTargetType.COMPONENT,
                requires_review=False,
                region=EngineBoundingBox(
                    view_id=view_ids[1], x=0.65, y=0.18, width=0.06, height=0.07
                ),
                checks=(
                    _check(
                        "002-PRESENCE",
                        InspectionGroup.PRESENCE,
                        InspectionResult.PASS,
                        "Presence",
                        "Present",
                        "Present",
                    ),
                    _check(
                        "002-POSITION",
                        InspectionGroup.POSITION,
                        InspectionResult.PASS,
                        "Offset",
                        0,
                        0.2,
                        "mm",
                    ),
                ),
            ),
            EnginePoint(
                id="IP-003",
                target_ref="U1",
                target_type=InspectionTargetType.COMPONENT,
                requires_review=True,
                region=EnginePolygon(
                    view_id=view_ids[2],
                    points=((0.2, 0.2), (0.28, 0.2), (0.28, 0.28), (0.2, 0.28)),
                ),
                checks=(
                    _check(
                        "003-PRESENCE",
                        InspectionGroup.PRESENCE,
                        InspectionResult.PASS,
                        "Presence",
                        "Present",
                        "Present",
                    ),
                    _check(
                        "003-ORIENTATION",
                        InspectionGroup.ORIENTATION,
                        InspectionResult.FAIL,
                        "Notch",
                        "top-left",
                        "bottom-left",
                        issue_type=IssueType.REVERSED_ORIENTATION,
                    ),
                ),
            ),
            EnginePoint(
                id="IP-004",
                target_ref="Wire-01",
                target_type=InspectionTargetType.WIRE,
                requires_review=True,
                region=EngineBoundingBox(
                    view_id=view_ids[0], x=0.12, y=0.72, width=0.38, height=0.04
                ),
                checks=(
                    _check(
                        "004-WIRE",
                        InspectionGroup.WIRE,
                        InspectionResult.REVIEW,
                        "Wire position",
                        "within path",
                        "slight deviation",
                        issue_type=IssueType.WRONG_WIRE_POSITION,
                    ),
                ),
            ),
        )
        return InspectionEngineOutput(points=points)


def _check(
    check_id: str,
    group: InspectionGroup,
    result: InspectionResult,
    label: str,
    expected: str | int | float,
    observed: str | int | float,
    unit: str | None = None,
    issue_type: IssueType | None = None,
    difference: str | int | float | None = None,
) -> EngineCheck:
    return EngineCheck(
        id=f"CHK-{check_id}",
        group=group,
        issue_type=issue_type,
        result=result,
        evidence=EngineEvidence(
            expected=(EngineEvidenceValue(label=label, value=expected, unit=unit),),
            observed=(EngineEvidenceValue(label=label, value=observed, unit=unit),),
            difference=(
                (EngineEvidenceValue(label=label, value=difference, unit=unit),)
                if difference is not None
                else None
            ),
        ),
    )
