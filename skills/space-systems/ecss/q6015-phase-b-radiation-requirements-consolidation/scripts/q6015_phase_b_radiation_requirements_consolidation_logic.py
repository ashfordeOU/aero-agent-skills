"""Consolidation of the radiation requirement baseline at the system review.

Anchor: ECSS-Q-ST-60-15C clause 4.4.2 (radiation environment and hardness
assurance requirements settled by the system review, with the early part
screening and the first shielding work that feed it). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Grade every candidate requirement for the attributes that make it usable:
   an environment source, a design factor at or above the floor of its
   allocation level, and a declared verification method.
2. Convert the sector shielding model of an equipment location into a dose by
   weighting a dose-depth curve with the solid-angle fraction of each sector.
3. Screen a candidate part list against the specified level by radiation
   design margin and group each part into an accept, shield, test or reject
   disposition.
4. Decide whether the baseline may be declared settled at the system review,
   and name what blocks it when it may not.
"""

import math

__all__ = [
    "REQUIREMENT_ATTRIBUTES",
    "ALLOCATION_LEVELS",
    "VERIFICATION_METHODS",
    "MIN_DESIGN_FACTOR_BY_LEVEL",
    "RDM_ACCEPT_THRESHOLD",
    "RDM_TOLERANCE",
    "SECTOR_FRACTION_TOLERANCE",
    "grade_requirement",
    "grade_requirement_set",
    "validate_sector_model",
    "dose_at_thickness",
    "sector_shielded_dose",
    "radiation_design_margin",
    "screen_part",
    "screen_part_list",
    "consolidate_requirements",
]

REQUIREMENT_ATTRIBUTES = (
    "environment_source",
    "design_factor",
    "allocation_level",
    "verification_method",
)

ALLOCATION_LEVELS = ("system", "subsystem", "equipment", "part")

VERIFICATION_METHODS = ("analysis", "test", "similarity", "review-of-design")

# The lower the allocation level, the less of the chain is left to absorb an
# environment error, so the floor on the design factor rises going down.
MIN_DESIGN_FACTOR_BY_LEVEL = {
    "system": 1.0,
    "subsystem": 1.2,
    "equipment": 1.5,
    "part": 2.0,
}

# A part is only taken without further work when its capability stands clear
# of the specified level by this factor.
RDM_ACCEPT_THRESHOLD = 2.0

# Margin comparisons are ratios of interpolated quantities; absorb the
# representation error at the bound instead of moving the bound.
RDM_TOLERANCE = 1e-9

SECTOR_FRACTION_TOLERANCE = 1e-9


def _positive(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _token(label, value, allowed):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = value.strip().lower().replace("_", "-").replace(" ", "-")
    if key not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (label, ", ".join(allowed), value)
        )
    return key


def grade_requirement(record):
    """Grade one candidate requirement record for consolidation readiness."""
    if not isinstance(record, dict):
        raise ValueError("requirement record must be a mapping")
    identifier = record.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("requirement record must carry a non-empty 'id'")
    missing = [key for key in REQUIREMENT_ATTRIBUTES if record.get(key) in (None, "")]
    findings = []
    level = None
    factor = None
    if "allocation_level" not in missing:
        level = _token("allocation_level", record["allocation_level"], ALLOCATION_LEVELS)
    if "verification_method" not in missing:
        _token("verification_method", record["verification_method"], VERIFICATION_METHODS)
    if "design_factor" not in missing:
        factor = _positive("design_factor", record["design_factor"])
    for key in missing:
        findings.append("%s: attribute %s is not stated" % (identifier.strip(), key))
    if level is not None and factor is not None:
        floor = MIN_DESIGN_FACTOR_BY_LEVEL[level]
        if factor < floor and not math.isclose(factor, floor, rel_tol=0.0, abs_tol=1e-12):
            findings.append(
                "%s: design factor %g is below the %g floor for an allocation at %s level"
                % (identifier.strip(), factor, floor, level)
            )
    return {
        "id": identifier.strip(),
        "allocation_level": level,
        "design_factor": factor,
        "missing_attributes": missing,
        "findings": findings,
        "consolidated": not findings,
    }


def grade_requirement_set(records):
    """Grade a whole candidate requirement set, ordered by requirement id."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("requirement set must be a non-empty sequence")
    graded = [grade_requirement(record) for record in records]
    seen = set()
    for item in graded:
        if item["id"] in seen:
            raise ValueError("duplicate requirement id %r" % (item["id"],))
        seen.add(item["id"])
    graded.sort(key=lambda item: item["id"])
    return graded


def validate_sector_model(sectors):
    """Return the validated sector model as (fraction, thickness) pairs."""
    if not isinstance(sectors, (list, tuple)) or not sectors:
        raise ValueError("sector model must be a non-empty sequence of sectors")
    validated = []
    total = 0.0
    for index, sector in enumerate(sectors):
        if not isinstance(sector, (list, tuple)) or len(sector) != 2:
            raise ValueError("sector %d must be a (solid_angle_fraction, thickness_mm) pair" % index)
        fraction = _positive("sector %d solid-angle fraction" % index, sector[0])
        thickness = _positive("sector %d thickness_mm" % index, sector[1])
        if fraction > 1.0:
            raise ValueError("sector %d solid-angle fraction %g exceeds unity" % (index, fraction))
        total += fraction
        validated.append((fraction, thickness))
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=SECTOR_FRACTION_TOLERANCE):
        raise ValueError("sector solid-angle fractions sum to %g, not unity" % total)
    return validated


def dose_at_thickness(curve, thickness_mm):
    """Log-log interpolate a dose-depth curve; refuse to extrapolate."""
    if not isinstance(curve, (list, tuple)) or len(curve) < 2:
        raise ValueError("dose-depth curve needs at least two (thickness, dose) points")
    points = []
    for index, item in enumerate(curve):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("dose-depth point %d must be a (thickness_mm, dose) pair" % index)
        x = _positive("dose-depth point %d thickness" % index, item[0])
        y = _positive("dose-depth point %d dose" % index, item[1])
        points.append((x, y))
    for index in range(1, len(points)):
        if points[index][0] <= points[index - 1][0]:
            raise ValueError("dose-depth thicknesses must strictly increase (index %d)" % index)
    value = _positive("thickness_mm", thickness_mm)
    lo, hi = points[0][0], points[-1][0]
    if value < lo or value > hi:
        raise ValueError(
            "dose-depth curve spans [%g, %g] mm; %g mm is outside it, extrapolation refused"
            % (lo, hi, value)
        )
    for index in range(1, len(points)):
        x0, y0 = points[index - 1]
        x1, y1 = points[index]
        if value <= x1:
            if value == x0:
                return y0
            if value == x1:
                return y1
            t = (math.log(value) - math.log(x0)) / (math.log(x1) - math.log(x0))
            return math.exp(math.log(y0) + t * (math.log(y1) - math.log(y0)))
    return points[-1][1]


def sector_shielded_dose(sectors, curve):
    """Return the solid-angle weighted dose behind a sector shielding model."""
    validated = validate_sector_model(sectors)
    return sum(fraction * dose_at_thickness(curve, thickness) for fraction, thickness in validated)


def radiation_design_margin(capability, specified_level):
    """Return the ratio of a part capability to the level specified for it."""
    return _positive("capability", capability) / _positive("specified_level", specified_level)


def screen_part(part, specified_level):
    """Group one candidate part by its margin against the specified level."""
    if not isinstance(part, dict):
        raise ValueError("part record must be a mapping")
    reference = part.get("reference")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("part record must carry a non-empty 'reference'")
    level = _positive("specified_level", specified_level)
    capability = part.get("capability_krad")
    if capability is None:
        return {
            "reference": reference.strip(),
            "margin": None,
            "disposition": "test-required",
            "reason": "no capability data on record",
        }
    margin = radiation_design_margin(capability, level)
    if margin > RDM_ACCEPT_THRESHOLD or math.isclose(
        margin, RDM_ACCEPT_THRESHOLD, rel_tol=0.0, abs_tol=RDM_TOLERANCE
    ):
        disposition = "accept"
        reason = "margin stands clear of the acceptance factor"
    elif margin > 1.0 or math.isclose(margin, 1.0, rel_tol=0.0, abs_tol=RDM_TOLERANCE):
        disposition = "shield-or-relocate"
        reason = "capability covers the level but not the acceptance factor"
    else:
        disposition = "reject"
        reason = "capability is below the specified level"
    if part.get("capability_basis") == "similarity" and disposition != "reject":
        disposition = "test-required"
        reason = "capability is carried over by similarity and owes a test"
    return {
        "reference": reference.strip(),
        "margin": margin,
        "disposition": disposition,
        "reason": reason,
    }


def screen_part_list(parts, specified_level):
    """Screen a candidate part list, ordered by part reference."""
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("part list must be a non-empty sequence")
    screened = [screen_part(part, specified_level) for part in parts]
    screened.sort(key=lambda item: item["reference"])
    return screened


def consolidate_requirements(spec):
    """Run the clause 4.4.2 consolidation for one equipment location.

    spec keys: requirements (sequence of records), sectors, dose_depth_curve,
    parts, design_factor; optional open_shielding_actions (sequence of strings).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("requirements", "sectors", "dose_depth_curve", "parts", "design_factor"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    graded = grade_requirement_set(spec["requirements"])
    location_dose = sector_shielded_dose(spec["sectors"], spec["dose_depth_curve"])
    factor = _positive("design_factor", spec["design_factor"])
    specified_level = location_dose * factor
    screened = screen_part_list(spec["parts"], specified_level)
    open_actions = spec.get("open_shielding_actions", ())
    if not isinstance(open_actions, (list, tuple)):
        raise ValueError("open_shielding_actions must be a sequence")
    findings = []
    for item in graded:
        findings.extend(item["findings"])
    for item in screened:
        if item["disposition"] == "reject":
            findings.append("part %s is below the specified level and cannot be carried"
                            % item["reference"])
        elif item["disposition"] == "test-required":
            findings.append("part %s owes a radiation test before the system review"
                            % item["reference"])
    for action in open_actions:
        if not isinstance(action, str) or not action.strip():
            raise ValueError("open shielding action must be a non-empty string")
        findings.append("open shielding action: %s" % action.strip())
    return {
        "requirements": graded,
        "location_dose_krad": location_dose,
        "design_factor": factor,
        "specified_level_krad": specified_level,
        "screened_parts": screened,
        "findings": findings,
        "baseline_settled": not findings,
    }
