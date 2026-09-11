"""
ECSS-E-ST-10C §5.4.1 — Reference frame definition and validation logic.

Implements deterministic, offline checks for:
  - Origin description completeness
  - Axis unit-vector normalization
  - Mutual orthogonality of axes
  - Right-handed coordinate system (z = x × y)
  - Frame type / time-dependence consistency
  - Inertial epoch requirement
  - ECSS naming convention
  - Parent-frame chain traceability
"""

import math
import re


# ---------------------------------------------------------------------------
# Frame type enumeration (plain strings — no external enum dep)
# ---------------------------------------------------------------------------

FRAME_TYPES = frozenset({
    "inertial",
    "body_fixed",
    "orbit_referenced",
    "planet_fixed",
    "topocentric",
})

TIME_VARYING_TYPES = frozenset({"body_fixed", "orbit_referenced", "planet_fixed", "topocentric"})
TIME_FIXED_TYPES = frozenset({"inertial"})

AXIS_NAMES = ("x", "y", "z")

# Maximum length for a frame name per ECSS §5.4.1 naming convention.
FRAME_NAME_MAX_LEN = 64

# Pattern: uppercase letters, digits, underscores; must begin with a letter.
_FRAME_NAME_RE = re.compile(r'^[A-Z][A-Z0-9_]*$')

# Tolerance for floating-point geometric checks.
DEFAULT_TOL = 1e-9


# ---------------------------------------------------------------------------
# Vector helpers (stdlib math only)
# ---------------------------------------------------------------------------

def _dot(a, b):
    return sum(ai * bi for ai, bi in zip(a, b))


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _magnitude(v):
    return math.sqrt(_dot(v, v))


def normalize(v):
    """Return a unit vector in the direction of v; raises ValueError if v is zero."""
    m = _magnitude(v)
    if m < 1e-12:
        raise ValueError("Cannot normalize a zero vector.")
    return tuple(x / m for x in v)


def derive_third_axis(x_axis, y_axis):
    """
    Derive the right-handed z-axis as (norm(x)) × (norm(y)).

    Returns a normalized tuple (zx, zy, zz).
    Raises ValueError if either input is a zero vector.
    """
    xn = normalize(x_axis)
    yn = normalize(y_axis)
    z = _cross(xn, yn)
    return normalize(z)


# ---------------------------------------------------------------------------
# Individual validation checks
# ---------------------------------------------------------------------------

def check_frame_name(name):
    """
    Verify the frame name follows the ECSS §5.4.1 naming convention:
    uppercase alphanumeric with underscores, starts with a letter, ≤ 64 chars.

    Returns a list of issue strings (empty = OK).
    """
    issues = []
    if not name:
        issues.append("Frame name must not be empty.")
        return issues
    if len(name) > FRAME_NAME_MAX_LEN:
        issues.append(
            f"Frame name '{name}' is {len(name)} characters; "
            f"ECSS limit is {FRAME_NAME_MAX_LEN}."
        )
    if not _FRAME_NAME_RE.match(name):
        issues.append(
            f"Frame name '{name}' does not conform to ECSS naming convention "
            "(uppercase letters, digits, underscores; must start with a letter)."
        )
    return issues


def check_origin_description(name, origin_description):
    """
    Verify the origin description is present and substantive (≥ 10 chars).

    Returns a list of issue strings (empty = OK).
    """
    issues = []
    if not origin_description or not origin_description.strip():
        issues.append(
            f"Frame '{name}' has no origin description; "
            "the origin must be explicitly stated."
        )
    elif len(origin_description.strip()) < 10:
        issues.append(
            f"Frame '{name}' origin description is too brief "
            f"('{origin_description}'); provide a full description."
        )
    return issues


def check_unit_vectors(name, axes, tol=DEFAULT_TOL):
    """
    Verify each of the three axis direction vectors is a unit vector.

    `axes` must be a sequence of three (ax, ay, az) tuples corresponding to x, y, z.
    Returns a list of issue strings (empty = OK).
    """
    issues = []
    if len(axes) != 3:
        issues.append(
            f"Frame '{name}': expected 3 axes, got {len(axes)}."
        )
        return issues
    for label, v in zip(AXIS_NAMES, axes):
        m = _magnitude(v)
        if abs(m - 1.0) > tol:
            issues.append(
                f"Frame '{name}' axis '{label}' has magnitude {m:.8f}; "
                "must be a unit vector (magnitude = 1.0)."
            )
    return issues


def check_orthogonality(name, axes, tol=DEFAULT_TOL):
    """
    Verify the three axes are mutually orthogonal (pairwise dot products ≈ 0).

    Returns a list of issue strings (empty = OK).
    """
    issues = []
    if len(axes) != 3:
        return issues  # already caught in check_unit_vectors
    x, y, z = axes
    for (a, b, label) in ((x, y, "x·y"), (x, z, "x·z"), (y, z, "y·z")):
        d = _dot(a, b)
        if abs(d) > tol:
            issues.append(
                f"Frame '{name}': axes not orthogonal ({label} = {d:.3e}; "
                f"must satisfy |dot| ≤ {tol})."
            )
    return issues


def check_right_handedness(name, axes, tol=DEFAULT_TOL):
    """
    Verify the axes form a right-handed system: z must equal x × y.

    Returns a list of issue strings (empty = OK).
    """
    issues = []
    if len(axes) != 3:
        return issues  # already caught
    x, y, z = axes
    computed_z = _cross(x, y)
    deviation = _magnitude(tuple(computed_z[i] - z[i] for i in range(3)))
    if deviation > tol:
        issues.append(
            f"Frame '{name}': axes are not right-handed "
            f"(|z - x×y| = {deviation:.3e}; must be ≤ {tol})."
        )
    return issues


def check_time_dependence(name, frame_type, time_dependent, epoch):
    """
    Verify that the time-dependence flag and epoch are consistent with the frame type.

    - Inertial frames must be time-independent and must supply an epoch.
    - Body-fixed and orbit-referenced frames must be time-varying.

    Returns a list of issue strings (empty = OK).
    """
    issues = []
    if frame_type not in FRAME_TYPES:
        issues.append(
            f"Frame '{name}': unknown frame type '{frame_type}'. "
            f"Must be one of: {sorted(FRAME_TYPES)}."
        )
        return issues

    if frame_type in TIME_FIXED_TYPES and time_dependent:
        issues.append(
            f"Frame '{name}' is type '{frame_type}' (inertial) but "
            "marked time_dependent=True; inertial frames must be time-independent."
        )
    if frame_type in TIME_VARYING_TYPES and not time_dependent:
        issues.append(
            f"Frame '{name}' is type '{frame_type}' but marked "
            "time_dependent=False; this frame type is time-varying."
        )
    if frame_type == "inertial" and not epoch:
        issues.append(
            f"Inertial frame '{name}' must specify an epoch (e.g. 'J2000.0')."
        )
    return issues


def check_frame_chain(frames):
    """
    Verify that every non-root frame references a parent that is defined in `frames`.

    `frames` is a list of dicts, each with at least:
      { "name": str, "parent_frame": str | None }

    Returns a list of issue strings (empty = OK).
    """
    issues = []
    known = {f["name"] for f in frames}
    for f in frames:
        parent = f.get("parent_frame")
        if parent is not None and parent not in known:
            issues.append(
                f"Frame '{f['name']}' references parent '{parent}' "
                "which is not present in the provided frame set."
            )
    return issues


# ---------------------------------------------------------------------------
# Master validator
# ---------------------------------------------------------------------------

def validate_frame(frame):
    """
    Run all validation checks on a single reference frame definition dict.

    Expected keys:
      name             (str)   ECSS-convention identifier
      origin           (str)   Physical description of the origin point
      axes             (list)  Three (x, y, z) unit-vector tuples: [x_axis, y_axis, z_axis]
      frame_type       (str)   One of FRAME_TYPES
      time_dependent   (bool)  True if axes rotate/translate with time
      epoch            (str|None) Required for inertial frames (e.g. 'J2000.0')
      parent_frame     (str|None) Parent frame name; None for root/inertial frames

    Returns:
      { "name": str, "valid": bool, "issues": [str] }
    """
    name = frame.get("name", "")
    issues = []
    issues += check_frame_name(name)
    issues += check_origin_description(name, frame.get("origin", ""))
    axes = frame.get("axes", [])
    issues += check_unit_vectors(name, axes)
    issues += check_orthogonality(name, axes)
    issues += check_right_handedness(name, axes)
    issues += check_time_dependence(
        name,
        frame.get("frame_type", ""),
        frame.get("time_dependent", False),
        frame.get("epoch"),
    )
    return {"name": name, "valid": len(issues) == 0, "issues": issues}


# ---------------------------------------------------------------------------
# Convenience: build a canonical right-handed frame from x and y only
# ---------------------------------------------------------------------------

def make_frame(name, origin, x_axis, y_axis, frame_type,
               time_dependent, epoch=None, parent_frame=None):
    """
    Construct a frame dict with z derived as normalize(x × y).

    All inputs are validated via validate_frame before return.
    Returns (frame_dict, result_dict) where result_dict is from validate_frame.
    """
    xn = normalize(x_axis)
    yn = normalize(y_axis)
    zn = derive_third_axis(xn, yn)
    frame = {
        "name": name,
        "origin": origin,
        "axes": [xn, yn, zn],
        "frame_type": frame_type,
        "time_dependent": time_dependent,
        "epoch": epoch,
        "parent_frame": parent_frame,
    }
    result = validate_frame(frame)
    return frame, result
