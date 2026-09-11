"""
ECSS-E-ST-10-09C §5.3.3 figure conventions for coordinate-frame diagrams.

Deterministic checks for coordinate-frame definitions and figure-convention
compliance used in space-system documentation. Stdlib only; offline.
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_AXIS_LABELS = {"x", "y", "z"}

FRAME_TYPES = {"inertial", "body", "orbital", "sensor", "structural"}

VALID_EULER_CHARS = {"1", "2", "3", "x", "y", "z"}

_ORTHO_THRESHOLD = 1e-9


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AxisVector:
    label: str
    components: Tuple[float, float, float]


@dataclass
class CoordinateFrame:
    name: str
    frame_type: str
    origin_description: str
    axes: List[AxisVector]


@dataclass
class FigureSpec:
    figure_id: str
    title: str
    frame: CoordinateFrame
    reference_frame: Optional[str] = None
    euler_sequence: Optional[str] = None
    euler_angles_deg: Optional[Tuple[float, float, float]] = None


@dataclass
class CheckResult:
    passed: bool
    findings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Vector helpers
# ---------------------------------------------------------------------------

def _dot(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(
    a: Tuple[float, float, float], b: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _magnitude(v: Tuple[float, float, float]) -> float:
    return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)


def _normalize(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    mag = _magnitude(v)
    if mag < 1e-15:
        raise ValueError("Cannot normalize a zero-length vector")
    return (v[0] / mag, v[1] / mag, v[2] / mag)


# ---------------------------------------------------------------------------
# Core checks
# ---------------------------------------------------------------------------

def validate_right_hand_rule(axes: List[AxisVector]) -> CheckResult:
    """
    Verify that exactly three named axes (x, y, z) form a right-handed
    orthogonal triad. Returns a CheckResult with any violations listed.
    """
    if len(axes) != 3:
        return CheckResult(False, [f"Expected 3 axes, got {len(axes)}"])

    findings: List[str] = []

    labels = {ax.label.lower() for ax in axes}
    if labels != VALID_AXIS_LABELS:
        findings.append(
            f"Axis labels {sorted(labels)} do not form the required {{x, y, z}} triad"
        )

    axis_map = {ax.label.lower(): ax.components for ax in axes}
    if not all(k in axis_map for k in ("x", "y", "z")):
        findings.append("Cannot perform orthogonality check: axis label(s) missing")
        return CheckResult(False, findings)

    try:
        xn = _normalize(axis_map["x"])
        yn = _normalize(axis_map["y"])
        zn = _normalize(axis_map["z"])
    except ValueError as exc:
        findings.append(f"Zero-length axis vector: {exc}")
        return CheckResult(False, findings)

    xy_dot = abs(_dot(xn, yn))
    xz_dot = abs(_dot(xn, zn))
    yz_dot = abs(_dot(yn, zn))

    if xy_dot > _ORTHO_THRESHOLD:
        findings.append(f"x and y axes are not orthogonal (|dot| = {xy_dot:.2e})")
    if xz_dot > _ORTHO_THRESHOLD:
        findings.append(f"x and z axes are not orthogonal (|dot| = {xz_dot:.2e})")
    if yz_dot > _ORTHO_THRESHOLD:
        findings.append(f"y and z axes are not orthogonal (|dot| = {yz_dot:.2e})")

    # Right-hand rule: x cross y must align with z
    x_cross_y = _cross(xn, yn)
    alignment = _dot(x_cross_y, zn)

    if abs(alignment - 1.0) > _ORTHO_THRESHOLD:
        if abs(alignment + 1.0) < _ORTHO_THRESHOLD:
            findings.append(
                "Axes form a left-handed triad; z must equal x cross y for a right-handed frame"
            )
        else:
            findings.append(
                f"Axes do not form a right-handed triad (x cross y · z = {alignment:.6f})"
            )

    return CheckResult(len(findings) == 0, findings)


def validate_frame_type(frame_type: str) -> CheckResult:
    """
    Confirm the frame type is one of the ECSS-recognized coordinate-frame
    categories. Returns a CheckResult with the finding if not recognized.
    """
    if frame_type.lower() in FRAME_TYPES:
        return CheckResult(True)
    return CheckResult(
        False,
        [
            f"Frame type '{frame_type}' is not a recognized ECSS category; "
            f"expected one of: {sorted(FRAME_TYPES)}"
        ],
    )


def validate_euler_sequence(sequence: str) -> CheckResult:
    """
    Verify that an Euler-angle sequence string is three characters long,
    contains only valid axis designators, and has no two consecutive identical
    axes (a requirement for both proper-Euler and Tait-Bryan sequences).
    """
    findings: List[str] = []

    if len(sequence) != 3:
        return CheckResult(
            False,
            [f"Euler sequence '{sequence}' must be exactly 3 characters; got {len(sequence)}"],
        )

    for ch in sequence:
        if ch not in VALID_EULER_CHARS:
            findings.append(
                f"Invalid axis designator '{ch}' in Euler sequence '{sequence}'; "
                f"use digits 1-3 or letters x/y/z"
            )

    if findings:
        return CheckResult(False, findings)

    if sequence[0] == sequence[1] or sequence[1] == sequence[2]:
        findings.append(
            f"Consecutive identical axes in sequence '{sequence}'; "
            "this is not a valid proper-Euler or Tait-Bryan rotation sequence"
        )

    return CheckResult(len(findings) == 0, findings)


def check_figure_completeness(spec: FigureSpec) -> CheckResult:
    """
    Verify that a FigureSpec carries all annotations required by the §5.3.3
    figure conventions: figure ID, title, named origin, all three axis labels,
    and a non-blank frame name.
    """
    findings: List[str] = []

    if not spec.figure_id.strip():
        findings.append("Figure ID must not be blank")
    if not spec.title.strip():
        findings.append("Figure title must not be blank")
    if not spec.frame.name.strip():
        findings.append("Coordinate frame name must not be blank")
    if not spec.frame.origin_description.strip():
        findings.append("Origin description must be annotated in the figure")

    labels = {ax.label.lower() for ax in spec.frame.axes}
    for required_label in sorted(VALID_AXIS_LABELS):
        if required_label not in labels:
            findings.append(f"Required axis label '{required_label}' is missing from the figure")

    return CheckResult(len(findings) == 0, findings)


def validate_figure_spec(spec: FigureSpec) -> CheckResult:
    """
    Run all §5.3.3 checks on a FigureSpec and return an aggregated result:
    frame-type validity, right-hand rule, Euler-sequence format (when provided),
    annotation completeness, and Euler-angle consistency.
    """
    findings: List[str] = []

    completeness = check_figure_completeness(spec)
    findings.extend(completeness.findings)

    ft_result = validate_frame_type(spec.frame.frame_type)
    findings.extend(ft_result.findings)

    rhr_result = validate_right_hand_rule(spec.frame.axes)
    findings.extend(rhr_result.findings)

    if spec.euler_sequence is not None:
        es_result = validate_euler_sequence(spec.euler_sequence)
        findings.extend(es_result.findings)

    if spec.euler_angles_deg is not None and spec.euler_sequence is None:
        findings.append(
            "euler_angles_deg is specified but no euler_sequence is provided; "
            "a rotation sequence must accompany angle values"
        )

    return CheckResult(len(findings) == 0, findings)


def describe_axis_orientation(axis: AxisVector) -> str:
    """
    Return a human-readable string describing the dominant direction of an axis
    vector, for use in figure annotation review output.
    """
    c = axis.components
    mag = _magnitude(c)
    if mag < 1e-15:
        return f"Axis {axis.label}: zero vector (direction undefined)"
    n = _normalize(c)
    dominant_idx = max(range(3), key=lambda i: abs(n[i]))
    direction_label = ["X", "Y", "Z"][dominant_idx]
    sign = "+" if n[dominant_idx] > 0 else "-"
    return (
        f"Axis {axis.label}: primarily {sign}{direction_label} "
        f"({c[0]:.4f}, {c[1]:.4f}, {c[2]:.4f})"
    )


def summarize_frame(frame: CoordinateFrame) -> dict:
    """
    Return a plain-dict summary of a CoordinateFrame suitable for logging or
    reporting: name, type, origin, and orientation descriptions for each axis.
    """
    return {
        "name": frame.name,
        "type": frame.frame_type,
        "origin": frame.origin_description,
        "axes": [describe_axis_orientation(ax) for ax in frame.axes],
    }
