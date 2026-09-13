#!/usr/bin/env python3
"""Magnetic-cleanliness control plan audit - ECSS-E-ST-20-07C clause 4.2.5.1.

Deterministic, offline, standard-library-only helpers that turn the
documented-plan requirement of clause 4.2.5.1 into a checkable procedure:

  1. verify the plan carries its mandatory parts,
  2. allocate the system stray-field requirement into per-item
     source-emission-limits (a uniform split, or the negotiated limit an
     item declares for itself),
  3. categorize each item into its magnetic-screening level,
  4. evaluate each item's point-dipole field at the reference-distance, and
  5. combine the contributions and aggregate the plan verdict.

No verbatim standard text is reproduced; the clause is cited as an anchor
only.
"""

import math

__all__ = [
    "REQUIRED_PLAN_SECTIONS",
    "ALLOCATION_METHODS",
    "ORIENTATION_FACTORS",
    "SCREENING_LEVELS",
    "validate_plan_sections",
    "categorize_screening_level",
    "dipole_field_nt",
    "allocate_emission_limits",
    "check_item_emission",
    "combined_field_nt",
    "assess_magnetic_cleanliness_plan",
]

# Parts the documented plan must carry (clause 4.2.5.1).
REQUIRED_PLAN_SECTIONS = (
    "design-guidelines",
    "source-emission-limits",
    "magnetic-screening-procedure",
    "verification-approach",
    "dipole-budget-maintenance",
)

ALLOCATION_METHODS = ("equal-share", "root-sum-square")

# Point-dipole geometry factor: twice as strong on axis as on the equator.
ORIENTATION_FACTORS = {"axial": 2.0, "equatorial": 1.0}

SCREENING_LEVELS = (
    "dipole-mapping-and-compensation",
    "full-dipole-mapping",
    "powered-current-loop-mapping",
    "single-axis-screening",
    "screening-exempt",
)

# mu0 / (4 pi) in T*m/A.
MU0_OVER_4PI = 1.0e-7
TESLA_TO_NT = 1.0e9

# Construction thresholds driving the magnetic-screening level.
COMPENSATION_MOMENT_THRESHOLD_AM2 = 0.5
MAPPING_MOMENT_THRESHOLD_AM2 = 0.05
FERROMAGNETIC_MASS_THRESHOLD_KG = 0.01
EXEMPTION_MOMENT_THRESHOLD_AM2 = 0.005

VALID_SCREENING_STATUS = ("complete", "planned", "none")

# Absorbs floating-point representation error at an exactly on-limit result.
# It never widens the engineering limit.
LIMIT_REL_TOL = 1e-9
LIMIT_ABS_TOL = 1e-12

_ITEM_KEYS = (
    "id",
    "declared_moment_am2",
    "ferromagnetic_mass_kg",
    "contains_permanent_magnet",
    "carries_current_loop",
    "screening_status",
)
_PLAN_KEYS = (
    "sections",
    "system_limit_nt",
    "reference_distance_m",
    "allocation_method",
    "orientation",
    "items",
)


def _as_finite_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    out = _as_finite_float(value, label)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return out


def _non_negative(value, label):
    out = _as_finite_float(value, label)
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return out


def _require_keys(mapping, keys, context):
    if not isinstance(mapping, dict):
        raise ValueError("%s must be a mapping, got %r" % (context, type(mapping).__name__))
    missing = [k for k in keys if k not in mapping]
    if missing:
        raise ValueError("%s missing required key(s): %s" % (context, ", ".join(missing)))


def _as_bool(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_plan_sections(sections):
    """Return the mandatory plan parts that are not documented."""
    if isinstance(sections, str) or not hasattr(sections, "__iter__"):
        raise ValueError("sections must be an iterable of strings, got %r" % (sections,))
    present = set()
    for item in sections:
        if not isinstance(item, str):
            raise ValueError("section entry must be a string, got %r" % (item,))
        present.add(item.strip().lower())
    return tuple(s for s in REQUIRED_PLAN_SECTIONS if s not in present)


def categorize_screening_level(item):
    """Return the magnetic-screening level an item's construction demands."""
    _require_keys(item, _ITEM_KEYS[:5], "item")
    moment = _non_negative(item["declared_moment_am2"], "declared_moment_am2")
    mass = _non_negative(item["ferromagnetic_mass_kg"], "ferromagnetic_mass_kg")
    has_magnet = _as_bool(item["contains_permanent_magnet"], "contains_permanent_magnet")
    has_loop = _as_bool(item["carries_current_loop"], "carries_current_loop")
    if has_magnet or moment >= COMPENSATION_MOMENT_THRESHOLD_AM2:
        return "dipole-mapping-and-compensation"
    if mass >= FERROMAGNETIC_MASS_THRESHOLD_KG or moment >= MAPPING_MOMENT_THRESHOLD_AM2:
        return "full-dipole-mapping"
    if has_loop:
        return "powered-current-loop-mapping"
    if moment >= EXEMPTION_MOMENT_THRESHOLD_AM2:
        return "single-axis-screening"
    return "screening-exempt"


def dipole_field_nt(moment_am2, distance_m, orientation="axial"):
    """Point-dipole stray field in nanotesla at a reference distance."""
    moment = _non_negative(moment_am2, "moment_am2")
    distance = _positive(distance_m, "distance_m")
    if not isinstance(orientation, str):
        raise ValueError("orientation must be a string, got %r" % (orientation,))
    key = orientation.strip().lower()
    if key not in ORIENTATION_FACTORS:
        raise ValueError(
            "unknown orientation %r; expected one of %s"
            % (orientation, ", ".join(sorted(ORIENTATION_FACTORS)))
        )
    tesla = MU0_OVER_4PI * ORIENTATION_FACTORS[key] * moment / (distance ** 3)
    return tesla * TESLA_TO_NT


def allocate_emission_limits(system_limit_nt, item_count, method="root-sum-square"):
    """Split the system stray-field requirement into a per-item limit."""
    limit = _positive(system_limit_nt, "system_limit_nt")
    if isinstance(item_count, bool) or not isinstance(item_count, int):
        raise ValueError("item_count must be an integer, got %r" % (item_count,))
    if item_count < 1:
        raise ValueError("item_count must be >= 1, got %r" % (item_count,))
    if not isinstance(method, str):
        raise ValueError("method must be a string, got %r" % (method,))
    key = method.strip().lower()
    if key not in ALLOCATION_METHODS:
        raise ValueError(
            "unknown allocation method %r; expected one of %s"
            % (method, ", ".join(ALLOCATION_METHODS))
        )
    if key == "equal-share":
        return limit / float(item_count)
    return limit / math.sqrt(float(item_count))


def _within_limit(value, limit):
    return value <= limit or math.isclose(
        value, limit, rel_tol=LIMIT_REL_TOL, abs_tol=LIMIT_ABS_TOL
    )


def check_item_emission(item, allocated_limit_nt, reference_distance_m, orientation="axial"):
    """Compare one item's dipole contribution with its allocated limit."""
    _require_keys(item, _ITEM_KEYS, "item")
    limit = _positive(allocated_limit_nt, "allocated_limit_nt")
    field = dipole_field_nt(
        item["declared_moment_am2"], reference_distance_m, orientation
    )
    status = item["screening_status"]
    if not isinstance(status, str) or status.strip().lower() not in VALID_SCREENING_STATUS:
        raise ValueError(
            "item %r screening_status must be one of %s, got %r"
            % (item["id"], ", ".join(VALID_SCREENING_STATUS), status)
        )
    level = categorize_screening_level(item)
    screening_required = level != "screening-exempt"
    screening_recorded = status.strip().lower() != "none"
    return {
        "item_id": item["id"],
        "screening_level": level,
        "screening_status": status.strip().lower(),
        "field_nt": field,
        "allocated_limit_nt": limit,
        "within_limit": _within_limit(field, limit),
        "screening_gap": screening_required and not screening_recorded,
    }


def combined_field_nt(fields):
    """Root-sum-square combination of incoherent item contributions."""
    values = list(fields)
    if not values:
        raise ValueError("fields must be a non-empty sequence")
    total = 0.0
    for i, value in enumerate(values):
        magnitude = _non_negative(value, "fields[%d]" % i)
        total += magnitude * magnitude
    return math.sqrt(total)


def assess_magnetic_cleanliness_plan(plan):
    """Audit a documented magnetic-cleanliness control plan end to end."""
    _require_keys(plan, _PLAN_KEYS, "plan")
    missing_sections = validate_plan_sections(plan["sections"])
    limit = _positive(plan["system_limit_nt"], "system_limit_nt")
    distance = _positive(plan["reference_distance_m"], "reference_distance_m")
    items = list(plan["items"])
    if not items:
        raise ValueError("plan items must not be empty; allocation needs at least one item")
    seen = set()
    for item in items:
        _require_keys(item, _ITEM_KEYS, "item")
        item_id = item["id"]
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError("item id must be a non-empty string, got %r" % (item_id,))
        if item_id in seen:
            raise ValueError("duplicate item id %r" % (item_id,))
        seen.add(item_id)
    allocation = allocate_emission_limits(limit, len(items), plan["allocation_method"])
    records = []
    for item in items:
        # A programme may negotiate an item-specific limit instead of taking
        # the uniform split; when it does, that limit governs this item and
        # the combined cross-check below is what keeps the set honest.
        item_limit = item.get("allocated_limit_nt", allocation)
        records.append(
            check_item_emission(item, item_limit, distance, plan["orientation"])
        )
    total_field = combined_field_nt([r["field_nt"] for r in records])
    findings = []
    for section in missing_sections:
        findings.append("plan does not document the %s part" % section)
    for record in records:
        if not record["within_limit"]:
            findings.append(
                "item %s radiates %.4g nT at the reference-distance against a %.4g nT "
                "allocation" % (record["item_id"], record["field_nt"], record["allocated_limit_nt"])
            )
        if record["screening_gap"]:
            findings.append(
                "item %s needs %s but has no magnetic-screening on record"
                % (record["item_id"], record["screening_level"])
            )
    system_ok = _within_limit(total_field, limit)
    if not system_ok:
        findings.append(
            "combined stray field %.4g nT exceeds the %.4g nT system requirement"
            % (total_field, limit)
        )
    negotiated = tuple(
        i["id"] for i in items if "allocated_limit_nt" in i
    )
    return {
        "missing_sections": missing_sections,
        "allocated_limit_nt": allocation,
        "records": tuple(records),
        "combined_field_nt": total_field,
        "system_limit_nt": limit,
        "system_within_limit": system_ok,
        "negotiated_allocation_ids": negotiated,
        "uniform_allocation_used": not negotiated,
        "findings": tuple(findings),
        "compliant": not findings,
    }
