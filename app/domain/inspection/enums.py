# Defines shared inspection result, target, issue, and grouping values.
from enum import Enum

class InspectionResult(str, Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"


class ReviewDecision(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class InspectionGroup(str, Enum):
    PRESENCE = "presence"
    POSITION = "position"
    COLOR = "color"
    ORIENTATION = "orientation"
    WIRE = "wire"
    BRIDGE = "bridge"
    SYSTEM = "system"


class IssueType(str, Enum):
    MISSING_COMPONENT = "missing_component"
    WRONG_COMPONENT = "wrong_component"
    WRONG_POSITION = "wrong_position"
    WRONG_COLOR = "wrong_color"
    REVERSED_ORIENTATION = "reversed_orientation"
    WRONG_WIRE_COLOR = "wrong_wire_color"
    WRONG_WIRE_POSITION = "wrong_wire_position"
    SOLDER_BRIDGE = "solder_bridge"
    IMAGE_QUALITY = "image_quality"
    ALIGNMENT = "alignment"


class InspectionTargetType(str, Enum):
    COMPONENT = "component"
    WIRE = "wire"
    SOLDER = "solder"
    SYSTEM = "system"


class ViewSide(str, Enum):
    FRONT = "front"
    BACK = "back"
    UNKNOWN = "unknown"
