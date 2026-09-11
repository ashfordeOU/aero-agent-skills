"""
e1009_transform_def_logic.py

Implements ECSS-E-ST-10-09C §5.4.9: defining each coordinate transformation
verbally, mathematically, and graphically relative to its parent frame, with
row-column convention checking and precision-consistency validation.

stdlib only — no third-party dependencies.
"""

import math
from typing import Dict, List, Optional

__all__ = [
    "CONVENTION_DCM",
    "CONVENTION_ACTIVE",
    "CONVENTION_PASSIVE",
    "KNOWN_CONVENTIONS",
    "ORTHOGONALITY_DEFAULT_TOLERANCE",
    "TransformEntry",
    "TransformValidationResult",
    "parse_transform_entry",
    "check_verbal_description",
    "check_graphical_reference",
    "check_parent_frame_defined",
    "check_orthogonality",
    "check_precision_consistency",
    "check_matrix_convention",
    "validate_transform_completeness",
    "audit_transform_set",
]

CONVENTION_DCM = "DCM"       # rows are child-frame axes expressed in the parent frame
CONVENTION_ACTIVE = "ACTIVE" # active rotation operating on row vectors
CONVENTION_PASSIVE = "PASSIVE"  # passive (alias) rotation operating on column vectors

KNOWN_CONVENTIONS = {CONVENTION_DCM, CONVENTION_ACTIVE, CONVENTION_PASSIVE}

ORTHOGONALITY_DEFAULT_TOLERANCE = 1e-6

_PRECISION_LOW = "LOW"       # 0–2 decimal places (manually rounded)
_PRECISION_MEDIUM = "MEDIUM" # 3–6 decimal places
_PRECISION_HIGH = "HIGH"     # 7+ decimal places (computed from library)


class TransformEntry:
    """One coordinate transformation in the system model."""

    def __init__(
        self,
        name: str,
        parent_frame: str,
        child_frame: str,
        verbal_description: str,
        matrix: List[List[float]],
        convention: str,
        graphical_reference: Optional[str] = None,
    ):
        self.name = name
        self.parent_frame = parent_frame
        self.child_frame = child_frame
        self.verbal_description = verbal_description
        self.matrix = matrix
        self.convention = convention
        self.graphical_reference = graphical_reference


class TransformValidationResult:
    """Aggregated findings for one audit run."""

    def __init__(self):
        self.findings: List[Dict] = []
        self._has_errors: bool = False

    def add_finding(self, entry_name: str, check: str, message: str, severity: str = "ERROR"):
        self.findings.append({
            "entry": entry_name,
            "check": check,
            "message": message,
            "severity": severity,
        })
        if severity in ("ERROR", "CRITICAL"):
            self._has_errors = True

    def is_compliant(self) -> bool:
        return not self._has_errors

    def error_count(self) -> int:
        return sum(1 for f in self.findings if f["severity"] in ("ERROR", "CRITICAL"))


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_transform_entry(raw: Dict) -> "TransformEntry":
    """
    Parse a raw dict into a TransformEntry.
    Raises ValueError on missing fields, bad matrix shape, or unknown convention.
    """
    required = ["name", "parent_frame", "child_frame",
                "verbal_description", "matrix", "convention"]
    missing = [k for k in required if k not in raw or raw[k] is None]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    name = str(raw["name"]).strip()
    if not name:
        raise ValueError("'name' must be a non-empty string")

    parent_frame = str(raw["parent_frame"]).strip()
    if not parent_frame:
        raise ValueError("'parent_frame' must be a non-empty string")

    child_frame = str(raw["child_frame"]).strip()
    if not child_frame:
        raise ValueError("'child_frame' must be a non-empty string")

    verbal = str(raw["verbal_description"]).strip()
    if not verbal:
        raise ValueError("'verbal_description' must be non-empty")

    _assert_matrix_shape(raw["matrix"])
    matrix: List[List[float]] = [[float(v) for v in row] for row in raw["matrix"]]

    convention = str(raw["convention"]).strip().upper()
    if convention not in KNOWN_CONVENTIONS:
        raise ValueError(
            f"'convention' must be one of {sorted(KNOWN_CONVENTIONS)}, got '{convention}'"
        )

    graphical_reference = raw.get("graphical_reference")
    if graphical_reference is not None:
        graphical_reference = str(graphical_reference).strip() or None

    return TransformEntry(
        name=name,
        parent_frame=parent_frame,
        child_frame=child_frame,
        verbal_description=verbal,
        matrix=matrix,
        convention=convention,
        graphical_reference=graphical_reference,
    )


def _assert_matrix_shape(matrix) -> None:
    if not isinstance(matrix, list) or len(matrix) != 3:
        raise ValueError("'matrix' must be a list of exactly 3 rows")
    for i, row in enumerate(matrix):
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError(f"matrix row {i} must have exactly 3 elements")
        for j, v in enumerate(row):
            if not isinstance(v, (int, float)):
                raise ValueError(
                    f"matrix[{i}][{j}] must be numeric, got {type(v).__name__}"
                )


# ---------------------------------------------------------------------------
# Single-entry checks
# ---------------------------------------------------------------------------

def check_verbal_description(entry: "TransformEntry") -> Optional[str]:
    """
    Return an error string if the verbal description is absent, too short,
    or does not mention the parent frame by name.
    """
    if not entry.verbal_description:
        return f"[{entry.name}] verbal_description is empty"
    if len(entry.verbal_description) < 10:
        return f"[{entry.name}] verbal_description is too short (< 10 chars)"
    if entry.parent_frame.lower() not in entry.verbal_description.lower():
        return (
            f"[{entry.name}] verbal_description does not reference the "
            f"parent frame '{entry.parent_frame}'"
        )
    return None


def check_graphical_reference(entry: "TransformEntry") -> Optional[str]:
    """Return an error string if the graphical reference is missing."""
    if not entry.graphical_reference:
        return f"[{entry.name}] graphical_reference is missing (required by §5.4.9)"
    return None


def check_parent_frame_defined(
    entry: "TransformEntry", known_frames: List[str]
) -> Optional[str]:
    """Return an error string if the parent frame is not in the defined set."""
    if entry.parent_frame not in known_frames:
        return (
            f"[{entry.name}] parent_frame '{entry.parent_frame}' is not in "
            f"the defined frame set"
        )
    return None


def check_matrix_convention(
    entry: "TransformEntry", expected_convention: str
) -> Optional[str]:
    """Return an error string if the entry's convention differs from the model-wide one."""
    expected = expected_convention.strip().upper()
    if expected not in KNOWN_CONVENTIONS:
        raise ValueError(
            f"expected_convention must be one of {sorted(KNOWN_CONVENTIONS)}"
        )
    if entry.convention != expected:
        return (
            f"[{entry.name}] convention is '{entry.convention}', "
            f"expected '{expected}'"
        )
    return None


def check_orthogonality(
    entry: "TransformEntry",
    tolerance: float = ORTHOGONALITY_DEFAULT_TOLERANCE,
) -> Optional[str]:
    """
    Return an error string if R^T R deviates from identity beyond tolerance,
    or if the determinant is not +1 (improper rotation / reflection).
    """
    R = entry.matrix
    Rt = _transpose(R)
    RtR = _matmul(Rt, R)
    I = _identity_3()
    dist = _frobenius_distance(RtR, I)
    if dist > tolerance:
        return (
            f"[{entry.name}] rotation matrix is not orthogonal: "
            f"||R^T R - I|| = {dist:.2e} (tolerance {tolerance:.2e})"
        )
    det = _determinant_3x3(R)
    if abs(det - 1.0) > tolerance:
        return (
            f"[{entry.name}] rotation matrix determinant is {det:.6f}, "
            f"expected +1.0 (tolerance {tolerance:.2e})"
        )
    return None


def validate_transform_completeness(entry: "TransformEntry") -> List[str]:
    """
    Run all single-entry checks and return a list of error strings.
    An empty list means the entry is complete and its matrix is valid.
    """
    errors: List[str] = []
    for fn in (check_verbal_description, check_graphical_reference, check_orthogonality):
        result = fn(entry)
        if result:
            errors.append(result)
    return errors


# ---------------------------------------------------------------------------
# Cross-entry check
# ---------------------------------------------------------------------------

def check_precision_consistency(entries: List["TransformEntry"]) -> List[str]:
    """
    Verify that all transform matrices use the same precision level.

    Precision levels: LOW (0–2 dp), MEDIUM (3–6 dp), HIGH (7+ dp).
    Entries at a lower level than the set maximum are flagged.
    Returns a list of error strings (empty means consistent).
    """
    if not entries:
        return []

    per_entry: Dict[str, str] = {}
    for entry in entries:
        max_dp = max(
            _decimal_places(entry.matrix[i][j])
            for i in range(3)
            for j in range(3)
        )
        per_entry[entry.name] = _precision_level(max_dp)

    levels = list(per_entry.values())
    order = {_PRECISION_LOW: 0, _PRECISION_MEDIUM: 1, _PRECISION_HIGH: 2}
    dominant = max(levels, key=lambda lv: order[lv])

    errors: List[str] = []
    for name, level in per_entry.items():
        if order[level] < order[dominant]:
            errors.append(
                f"[{name}] precision level is {level}, but the model uses "
                f"{dominant} precision — all entries must be consistent"
            )
    return errors


# ---------------------------------------------------------------------------
# Full audit
# ---------------------------------------------------------------------------

def audit_transform_set(
    entries: List["TransformEntry"],
    known_frames: List[str],
    expected_convention: str,
) -> "TransformValidationResult":
    """
    Full §5.4.9 audit across a set of transforms:
      1. Completeness per entry (verbal + graphical + orthogonality).
      2. Parent frame in the defined frame set.
      3. Convention matches the model-wide declaration.
      4. Precision consistent across all entries.
    """
    result = TransformValidationResult()

    for entry in entries:
        for msg in validate_transform_completeness(entry):
            result.add_finding(entry.name, "completeness", msg)

        msg = check_parent_frame_defined(entry, known_frames)
        if msg:
            result.add_finding(entry.name, "parent_frame", msg)

        msg = check_matrix_convention(entry, expected_convention)
        if msg:
            result.add_finding(entry.name, "convention", msg)

    for msg in check_precision_consistency(entries):
        entry_name = msg.split("]")[0].lstrip("[")
        result.add_finding(entry_name, "precision", msg)

    return result


# ---------------------------------------------------------------------------
# Linear-algebra helpers (stdlib, no numpy)
# ---------------------------------------------------------------------------

def _identity_3() -> List[List[float]]:
    return [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]


def _transpose(A: List[List[float]]) -> List[List[float]]:
    return [[A[j][i] for j in range(3)] for i in range(3)]


def _matmul(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    C = [[0.0] * 3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            for k in range(3):
                C[i][j] += A[i][k] * B[k][j]
    return C


def _frobenius_distance(A: List[List[float]], B: List[List[float]]) -> float:
    total = 0.0
    for i in range(3):
        for j in range(3):
            d = A[i][j] - B[i][j]
            total += d * d
    return math.sqrt(total)


def _determinant_3x3(m: List[List[float]]) -> float:
    return (
        m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
        - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
        + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
    )


def _decimal_places(value: float) -> int:
    """Count significant decimal places in the repr of a float."""
    s = repr(value)
    if "e" in s or "E" in s:
        # scientific notation → treat as high precision
        return 15
    if "." in s:
        frac = s.split(".", 1)[1].rstrip("0")
        return len(frac)
    return 0


def _precision_level(max_dp: int) -> str:
    if max_dp <= 2:
        return _PRECISION_LOW
    if max_dp <= 6:
        return _PRECISION_MEDIUM
    return _PRECISION_HIGH
