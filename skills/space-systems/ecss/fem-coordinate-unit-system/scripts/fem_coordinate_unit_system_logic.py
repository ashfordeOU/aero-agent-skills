"""
fem_coordinate_unit_system_logic.py

ECSS-E-ST-32C clause 4.2 — coordinate-system and unit-system convention
checks for FEM exchange packages.

Ref: ECSS-E-ST-32C (paraphrased; no verbatim standard text).
stdlib only — no third-party dependencies.
"""

import math

# Approved ECSS unit-system families: (force, mass, length, pressure).
# Physical basis:
#   SI:     1 N = 1 kg * m/s²;   1 Pa  = 1 N/m²
#   mm-N-t: 1 N = 1 t  * mm/s²; 1 MPa = 1 N/mm²
#           (1 t = 1000 kg → 1 t * mm/s² = 1000 kg * 0.001 m/s² = 1 N ✓)
APPROVED_UNIT_SYSTEMS = {
    "SI": {
        "force": "N",
        "mass": "kg",
        "length": "m",
        "pressure": "Pa",
    },
    "mm-N-t": {
        "force": "N",
        "mass": "t",
        "length": "mm",
        "pressure": "MPa",
    },
}

# For each (force, length) pair: set of pressure units derivable as force/length².
_ALLOWED_PRESSURE = {
    ("N", "m"):  {"Pa", "N/m2"},
    ("N", "mm"): {"MPa", "N/mm2"},
}

# For each (force, length) pair: set of mass units consistent with F = m * a.
_ALLOWED_MASS = {
    ("N", "m"):  {"kg"},
    ("N", "mm"): {"t"},
}


# ---------------------------------------------------------------------------
# Vector helpers
# ---------------------------------------------------------------------------

def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a, b):
    return sum(ai * bi for ai, bi in zip(a, b))


def _mag(v):
    return math.sqrt(sum(vi * vi for vi in v))


def _norm(v):
    m = _mag(v)
    if m < 1e-12:
        raise ValueError("Cannot normalise a zero-length vector.")
    return tuple(vi / m for vi in v)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_right_hand_rule(x_axis, y_axis, z_axis, tol=1e-6):
    """
    Verify that three vectors form a right-handed orthonormal Cartesian frame.

    Returns (ok: bool, message: str).
    Checks:
      - All axes are non-zero and normalisable.
      - Each pair of axes is mutually orthogonal (|dot| < tol after normalisation).
      - z_axis ≈ cross(x_axis, y_axis) within tol (right-hand rule).
    """
    try:
        xn = _norm(x_axis)
        yn = _norm(y_axis)
        zn = _norm(z_axis)
    except ValueError as exc:
        return False, f"Axis normalisation failed: {exc}"

    if abs(_dot(xn, yn)) > tol:
        return False, "X and Y axes are not orthogonal."
    if abs(_dot(xn, zn)) > tol:
        return False, "X and Z axes are not orthogonal."
    if abs(_dot(yn, zn)) > tol:
        return False, "Y and Z axes are not orthogonal."

    z_derived = _cross(xn, yn)
    deviation = _mag(tuple(zn[i] - z_derived[i] for i in range(3)))
    if deviation > tol:
        return False, (
            f"Axes do not satisfy the right-hand rule "
            f"(z ≠ cross(x, y); deviation={deviation:.2e})."
        )
    return True, "Right-hand rule satisfied."


def validate_coordinate_frame(frame):
    """
    Validate a coordinate frame definition dict.

    Required keys:
        label      (str): non-empty identifier for this frame.
        origin_ref (str): label of the frame that defines this frame's origin.
        x_axis     (sequence of 3 floats)
        y_axis     (sequence of 3 floats)
        z_axis     (sequence of 3 floats)

    Returns list[str] of error descriptions (empty list = valid).
    """
    errors = []
    required = ["label", "origin_ref", "x_axis", "y_axis", "z_axis"]
    missing = [k for k in required if k not in frame]
    if missing:
        for k in missing:
            errors.append(f"Missing required field: '{k}'.")
        return errors  # cannot proceed without axes

    if not isinstance(frame["label"], str) or not frame["label"].strip():
        errors.append("'label' must be a non-empty string.")
    if not isinstance(frame["origin_ref"], str) or not frame["origin_ref"].strip():
        errors.append("'origin_ref' must be a non-empty string.")

    for axis in ("x_axis", "y_axis", "z_axis"):
        try:
            if len(frame[axis]) != 3:
                errors.append(f"'{axis}' must be a 3-element sequence.")
        except TypeError:
            errors.append(f"'{axis}' must be a sequence of 3 numbers.")

    if errors:
        return errors

    ok, msg = check_right_hand_rule(frame["x_axis"], frame["y_axis"], frame["z_axis"])
    if not ok:
        errors.append(f"Coordinate frame '{frame['label']}': {msg}")

    return errors


def validate_unit_system(declared):
    """
    Check that a declared unit-system dict is physically consistent and matches
    an approved ECSS combination.

    'declared' must have keys: force, mass, length, pressure.

    Returns (ok: bool, issues: list[str]).
    ok is True only when issues is empty.
    """
    issues = []
    required = ["force", "mass", "length", "pressure"]
    missing = [k for k in required if k not in declared]
    if missing:
        for k in missing:
            issues.append(f"Missing unit field: '{k}'.")
        return False, issues

    force    = declared["force"]
    mass     = declared["mass"]
    length   = declared["length"]
    pressure = declared["pressure"]

    allowed_p = _ALLOWED_PRESSURE.get((force, length))
    if allowed_p is None:
        issues.append(
            f"No approved pressure derivation for force='{force}', length='{length}'."
        )
    elif pressure not in allowed_p:
        issues.append(
            f"Pressure unit '{pressure}' is inconsistent with force='{force}' "
            f"and length='{length}' (expected one of {sorted(allowed_p)})."
        )

    allowed_m = _ALLOWED_MASS.get((force, length))
    if allowed_m is None:
        issues.append(
            f"No approved mass rule for force='{force}', length='{length}'."
        )
    elif mass not in allowed_m:
        issues.append(
            f"Mass unit '{mass}' is inconsistent with force='{force}' "
            f"and length='{length}' (expected one of {sorted(allowed_m)})."
        )

    if not issues:
        matched = any(
            s["force"] == force
            and s["mass"] == mass
            and s["length"] == length
            and s["pressure"] == pressure
            for s in APPROVED_UNIT_SYSTEMS.values()
        )
        if not matched:
            issues.append(
                "Unit combination is internally consistent but is not a named "
                "ECSS-approved system; flag for explicit project approval."
            )

    return len(issues) == 0, issues


def validate_fem_exchange_package(package):
    """
    Validate a FEM exchange package for coordinate-system and unit-system conformance.

    Expected keys in 'package':
        unit_system        (dict): keys force, mass, length, pressure.
        coordinate_frames  (list[dict]): each validated by validate_coordinate_frame.
        global_frame_label (str): label of the designated global reference frame.

    Returns dict:
        ok                  (bool)
        unit_errors         (list[str])
        frame_errors        (list[str])
        global_frame_errors (list[str])
    """
    result = {
        "ok": True,
        "unit_errors": [],
        "frame_errors": [],
        "global_frame_errors": [],
    }

    # --- unit system ---
    if "unit_system" not in package:
        result["unit_errors"].append("Package is missing 'unit_system'.")
        result["ok"] = False
    else:
        ok, issues = validate_unit_system(package["unit_system"])
        if not ok:
            result["unit_errors"].extend(issues)
            result["ok"] = False

    # --- coordinate frames ---
    frames = package.get("coordinate_frames", [])
    if not frames:
        result["frame_errors"].append("No coordinate frames declared in package.")
        result["ok"] = False

    valid_labels = set()
    for frame in frames:
        errs = validate_coordinate_frame(frame)
        if errs:
            result["frame_errors"].extend(errs)
            result["ok"] = False
        else:
            valid_labels.add(frame["label"])

    # --- global frame ---
    global_label = package.get("global_frame_label", "")
    if not global_label:
        result["global_frame_errors"].append(
            "'global_frame_label' is not declared in the package."
        )
        result["ok"] = False
    elif global_label not in valid_labels:
        result["global_frame_errors"].append(
            f"Global frame '{global_label}' is not present in coordinate_frames."
        )
        result["ok"] = False

    return result
