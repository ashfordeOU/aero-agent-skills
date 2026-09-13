#!/usr/bin/env python3
"""Vehicle magnetic dipole budget - ECSS-E-ST-20-07C clause 4.2.5.2.

Deterministic, offline, standard-library-only helpers that turn the
maintained three-axis dipole budget of clause 4.2.5.2 into a checkable
procedure:

  1. categorize every magnetic contributor,
  2. roll the signed axis components up into the nominal vehicle dipole,
  3. combine the per-axis uncertainties by root-sum-square and form the
     worst-case vector with a declared coverage factor,
  4. check each axis and the resultant magnitude against the budget
     allocations, and
  5. cross the worst-case dipole with the ambient field to size the
     magnetic-disturbance-torque against the attitude-control authority.

No verbatim standard text is reproduced; the clause is cited as an anchor
only.
"""

import math

__all__ = [
    "CONTRIBUTOR_CATEGORIES",
    "AXES",
    "DEFAULT_COVERAGE_FACTOR",
    "DEFAULT_TORQUE_MARGIN",
    "validate_dipole_vector",
    "categorize_contributor",
    "roll_up_dipole_budget",
    "vector_magnitude",
    "magnetic_disturbance_torque",
    "check_axis_budget",
    "torque_margin",
    "assess_magnetic_budget",
]

AXES = ("x", "y", "z")

# Contributor kind -> budget category (clause 4.2.5.2 roll-up).
CONTRIBUTOR_CATEGORIES = {
    "permanent-magnet": "permanent-magnetization",
    "remanent-magnetization": "permanent-magnetization",
    "hard-magnetic-material": "permanent-magnetization",
    "latching-relay": "permanent-magnetization",
    "soft-magnetic-material": "induced-magnetization",
    "induced-magnetization": "induced-magnetization",
    "structure-induced-moment": "induced-magnetization",
    "current-loop": "current-loop-moment",
    "harness-loop": "current-loop-moment",
    "solar-array-loop": "current-loop-moment",
    "magnetorquer-residual": "current-loop-moment",
    "compensation-magnet": "compensation-moment",
    "trim-magnet": "compensation-moment",
    "compensation-loop": "compensation-moment",
}

DEFAULT_COVERAGE_FACTOR = 1.0

# Attitude control needs headroom over the disturbance, not parity.
DEFAULT_TORQUE_MARGIN = 2.0

# Absorbs floating-point representation error at an exactly on-limit result.
# It never widens the engineering allocation.
LIMIT_REL_TOL = 1e-9
LIMIT_ABS_TOL = 1e-15

_CONTRIBUTOR_KEYS = ("id", "kind", "vector_am2")


def _as_finite_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _require_keys(mapping, keys, context):
    if not isinstance(mapping, dict):
        raise ValueError("%s must be a mapping, got %r" % (context, type(mapping).__name__))
    missing = [k for k in keys if k not in mapping]
    if missing:
        raise ValueError("%s missing required key(s): %s" % (context, ", ".join(missing)))


def validate_dipole_vector(vector, label="vector", non_negative=False):
    """Coerce a three-component dipole vector to a tuple of finite floats."""
    if isinstance(vector, (str, bytes, dict)) or not hasattr(vector, "__iter__"):
        raise ValueError("%s must be a sequence of three components, got %r" % (label, vector))
    items = list(vector)
    if len(items) != 3:
        raise ValueError("%s must have exactly 3 components, got %d" % (label, len(items)))
    out = []
    for axis, value in zip(AXES, items):
        component = _as_finite_float(value, "%s.%s" % (label, axis))
        if non_negative and component < 0.0:
            raise ValueError("%s.%s must be >= 0, got %r" % (label, axis, value))
        out.append(component)
    return tuple(out)


def categorize_contributor(kind):
    """Return the budget category for a magnetic contributor kind."""
    if not isinstance(kind, str):
        raise ValueError("contributor kind must be a string, got %r" % (kind,))
    key = kind.strip().lower()
    if not key:
        raise ValueError("contributor kind must not be empty")
    if key not in CONTRIBUTOR_CATEGORIES:
        raise ValueError(
            "uncategorized contributor kind %r; known kinds: %s"
            % (kind, ", ".join(sorted(CONTRIBUTOR_CATEGORIES)))
        )
    return CONTRIBUTOR_CATEGORIES[key]


def vector_magnitude(vector):
    """Euclidean magnitude of a three-component vector."""
    x, y, z = validate_dipole_vector(vector, "vector")
    return math.sqrt(x * x + y * y + z * z)


def roll_up_dipole_budget(contributors, coverage_factor=DEFAULT_COVERAGE_FACTOR):
    """Sum signed contributor vectors and form the worst-case dipole."""
    if isinstance(contributors, dict) or not hasattr(contributors, "__iter__"):
        raise ValueError("contributors must be an iterable of mappings")
    items = list(contributors)
    if not items:
        raise ValueError("contributors must not be empty; a budget needs at least one entry")
    k = _as_finite_float(coverage_factor, "coverage_factor")
    if k < 0.0:
        raise ValueError("coverage_factor must be >= 0, got %r" % (coverage_factor,))
    nominal = [0.0, 0.0, 0.0]
    variance = [0.0, 0.0, 0.0]
    by_category = {}
    seen = set()
    for entry in items:
        _require_keys(entry, _CONTRIBUTOR_KEYS, "contributor")
        entry_id = entry["id"]
        if not isinstance(entry_id, str) or not entry_id.strip():
            raise ValueError("contributor id must be a non-empty string, got %r" % (entry_id,))
        if entry_id in seen:
            raise ValueError("duplicate contributor id %r" % (entry_id,))
        seen.add(entry_id)
        category = categorize_contributor(entry["kind"])
        vector = validate_dipole_vector(entry["vector_am2"], "contributor %s vector_am2" % entry_id)
        uncertainty = validate_dipole_vector(
            entry.get("uncertainty_am2", (0.0, 0.0, 0.0)),
            "contributor %s uncertainty_am2" % entry_id,
            non_negative=True,
        )
        subtotal = by_category.setdefault(category, [0.0, 0.0, 0.0])
        for i in range(3):
            nominal[i] += vector[i]
            subtotal[i] += vector[i]
            variance[i] += uncertainty[i] * uncertainty[i]
    combined_uncertainty = tuple(math.sqrt(v) for v in variance)
    worst_case = tuple(
        abs(nominal[i]) + k * combined_uncertainty[i] for i in range(3)
    )
    return {
        "nominal_vector_am2": tuple(nominal),
        "uncertainty_vector_am2": combined_uncertainty,
        "worst_case_vector_am2": worst_case,
        "worst_case_magnitude_am2": math.sqrt(sum(c * c for c in worst_case)),
        "nominal_magnitude_am2": math.sqrt(sum(c * c for c in nominal)),
        "by_category_am2": {k2: tuple(v) for k2, v in sorted(by_category.items())},
        "coverage_factor": k,
        "contributor_count": len(items),
    }


def magnetic_disturbance_torque(dipole_vector_am2, field_vector_t):
    """Cross product of the vehicle dipole with the ambient field."""
    m = validate_dipole_vector(dipole_vector_am2, "dipole_vector_am2")
    b = validate_dipole_vector(field_vector_t, "field_vector_t")
    torque = (
        m[1] * b[2] - m[2] * b[1],
        m[2] * b[0] - m[0] * b[2],
        m[0] * b[1] - m[1] * b[0],
    )
    return {
        "torque_vector_nm": torque,
        "torque_magnitude_nm": math.sqrt(sum(c * c for c in torque)),
    }


def _within_limit(value, limit):
    return value <= limit or math.isclose(
        value, limit, rel_tol=LIMIT_REL_TOL, abs_tol=LIMIT_ABS_TOL
    )


def check_axis_budget(worst_case_vector_am2, axis_allocations_am2, magnitude_allocation_am2):
    """Check the worst-case dipole against the axis and magnitude budget."""
    worst = validate_dipole_vector(worst_case_vector_am2, "worst_case_vector_am2", non_negative=True)
    limits = validate_dipole_vector(axis_allocations_am2, "axis_allocations_am2")
    for axis, limit in zip(AXES, limits):
        if limit <= 0.0:
            raise ValueError("axis_allocations_am2.%s must be > 0, got %r" % (axis, limit))
    magnitude_limit = _as_finite_float(magnitude_allocation_am2, "magnitude_allocation_am2")
    if magnitude_limit <= 0.0:
        raise ValueError(
            "magnitude_allocation_am2 must be > 0, got %r" % (magnitude_allocation_am2,)
        )
    magnitude = math.sqrt(sum(c * c for c in worst))
    axes = {}
    for i, axis in enumerate(AXES):
        axes[axis] = {
            "worst_case_am2": worst[i],
            "allocation_am2": limits[i],
            "remaining_am2": limits[i] - worst[i],
            "within_limit": _within_limit(worst[i], limits[i]),
        }
    driving = min(AXES, key=lambda a: axes[a]["remaining_am2"])
    return {
        "axes": axes,
        "magnitude_am2": magnitude,
        "magnitude_allocation_am2": magnitude_limit,
        "magnitude_within_limit": _within_limit(magnitude, magnitude_limit),
        "driving_axis": driving,
        "within_limit": all(axes[a]["within_limit"] for a in AXES)
        and _within_limit(magnitude, magnitude_limit),
    }


def torque_margin(control_authority_nm, disturbance_torque_nm):
    """Ratio of attitude-control authority to the disturbance torque."""
    authority = _as_finite_float(control_authority_nm, "control_authority_nm")
    if authority <= 0.0:
        raise ValueError("control_authority_nm must be > 0, got %r" % (control_authority_nm,))
    disturbance = _as_finite_float(disturbance_torque_nm, "disturbance_torque_nm")
    if disturbance < 0.0:
        raise ValueError("disturbance_torque_nm must be >= 0, got %r" % (disturbance_torque_nm,))
    if disturbance == 0.0:
        return float("inf")
    return authority / disturbance


def assess_magnetic_budget(
    contributors,
    axis_allocations_am2,
    magnitude_allocation_am2,
    field_vector_t,
    control_authority_nm,
    coverage_factor=DEFAULT_COVERAGE_FACTOR,
    required_torque_margin=DEFAULT_TORQUE_MARGIN,
):
    """Maintain and check a clause 4.2.5.2 vehicle magnetic dipole budget."""
    required = _as_finite_float(required_torque_margin, "required_torque_margin")
    if required < 1.0:
        raise ValueError(
            "required_torque_margin must be >= 1.0 (parity or better), got %r"
            % (required_torque_margin,)
        )
    rollup = roll_up_dipole_budget(contributors, coverage_factor)
    budget = check_axis_budget(
        rollup["worst_case_vector_am2"], axis_allocations_am2, magnitude_allocation_am2
    )
    torque = magnetic_disturbance_torque(rollup["worst_case_vector_am2"], field_vector_t)
    margin = torque_margin(control_authority_nm, torque["torque_magnitude_nm"])
    torque_ok = margin >= required or math.isclose(
        margin, required, rel_tol=LIMIT_REL_TOL, abs_tol=LIMIT_ABS_TOL
    )
    findings = []
    for axis in AXES:
        record = budget["axes"][axis]
        if not record["within_limit"]:
            findings.append(
                "%s-axis worst-case dipole %.4g A*m2 exceeds its %.4g A*m2 allocation"
                % (axis, record["worst_case_am2"], record["allocation_am2"])
            )
    if not budget["magnitude_within_limit"]:
        findings.append(
            "resultant worst-case dipole %.4g A*m2 exceeds the %.4g A*m2 magnitude allocation"
            % (budget["magnitude_am2"], budget["magnitude_allocation_am2"])
        )
    if not torque_ok:
        findings.append(
            "magnetic-disturbance-torque %.4g N*m leaves a torque margin of %.3f against a "
            "required %.3f" % (torque["torque_magnitude_nm"], margin, required)
        )
    return {
        "rollup": rollup,
        "budget": budget,
        "torque": torque,
        "torque_margin": margin,
        "required_torque_margin": required,
        "torque_within_authority": torque_ok,
        "driving_axis": budget["driving_axis"],
        "findings": tuple(findings),
        "compliant": not findings,
    }
