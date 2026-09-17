"""Handling of parts fitted to engineering qualification models on a Class 2 programme.

Anchor: ECSS-Q-ST-60C clause 5.1.6 (parts fitted to engineering qualification
models and how a Class 2 programme handles them). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the programme's per-stress limits and the reuse reserve it keeps
   back for a part that may go on to a flight build.
2. Decide whether each fitted part may be on the model at all: interchangeability
   first, then how many rungs of the quality ladder it sits below the
   flight-intended part, whether that depth is inside the Class 2 allowance, and
   whether a depth greater than zero was justified in writing.
3. Account for what the model has spent on the part - thermal cycles, rework
   operations, powered hours - as a fraction of each declared limit, keep the
   stress that governs, and turn the rest into remaining margin.
4. Decide the part's post-campaign disposition from that account.
5. Decide, only for a part the project actually nominates, whether it may be
   carried into a flight build: the Class 2 relief that separates this clause
   from its Class 1 counterpart, and one that costs a retained margin and a
   recorded re-screening rather than being free.
6. Return one model-level verdict with ranked findings.
"""

import math

__all__ = [
    "RATIO_TOLERANCE",
    "QUALITY_LEVELS",
    "MAX_RELAXATION_STEPS",
    "RETENTION_THRESHOLD",
    "REUSE_MARGIN_RESERVE",
    "STRESS_KEYS",
    "MANDATORY_PART_ATTRIBUTES",
    "PERMITTED_PERMISSIONS",
    "REUSE_ELIGIBLE",
    "validate_part_id",
    "quality_level_rank",
    "relaxation_depth",
    "usage_permission",
    "validate_stress_limits",
    "consumed_life",
    "remaining_margin",
    "post_campaign_disposition",
    "flight_reuse_eligibility",
    "evaluate_eqm_part",
    "assess_eqm_part_handling",
]

# Consumed life and margin are ratios against a declared limit. An exactly
# reached limit can land a few units in the last place either side; absorb the
# representation error here rather than moving the limit.
RATIO_TOLERANCE = 1e-9

# Procurement quality levels, best first. The ladder is what a relaxation is
# measured on, so the order is part of the contract.
QUALITY_LEVELS = (
    "level-1",
    "level-2",
    "level-3",
    "commercial-upscreened",
    "commercial",
)

# How far below the flight-intended level a fitted part may sit on a Class 2
# model. The allowance is wider than a Class 1 model carries; it is not open.
MAX_RELAXATION_STEPS = 3

# Above this share of any declared limit a part does not go back to model stock
# without a review.
RETENTION_THRESHOLD = 0.75

# The share of life a part must still hold for a flight build to be allowed to
# take it. Class 2 permits the carry-over; it does not permit a spent part.
REUSE_MARGIN_RESERVE = 0.40

# The stresses a model spends on a part, each with its own declared limit.
STRESS_KEYS = ("thermal_cycles", "rework_operations", "powered_hours")

# The attributes without which a fitted part cannot be assessed at all.
MANDATORY_PART_ATTRIBUTES = (
    "part_id",
    "part_number",
    "fitted_quality_level",
    "flight_quality_level",
    "interchangeable",
)

PERMITTED_PERMISSIONS = (
    "permitted-equivalent",
    "permitted-with-justification",
)

REUSE_ELIGIBLE = (
    "eligible",
    "eligible-after-rescreening",
)

# Finding -> severity used to rank findings. Lower sorts first.
_SEVERITY = {
    "record-incomplete": 0,
    "not-interchangeable": 1,
    "relaxation-too-deep": 2,
    "relaxation-not-justified": 3,
    "stress-limit-exceeded": 4,
    "reuse-margin-exhausted": 5,
    "rescreening-outstanding": 6,
    "held-for-review": 7,
}


def _require_text(value, label):
    """Return a non-blank stripped string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_bool(value, label):
    """Return a real boolean, or raise."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _require_non_negative_number(value, label):
    """Return a finite, non-negative real number, or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite" % label)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def _recorded(value):
    """Return whether a free-text record actually says something."""
    return isinstance(value, str) and bool(value.strip())


def validate_part_id(value):
    """Return the validated identifier of one fitted part."""
    return _require_text(value, "part_id")


def quality_level_rank(level):
    """Return the ladder position of a procurement quality level, best = 0."""
    text = _require_text(level, "quality level").lower()
    if text not in QUALITY_LEVELS:
        raise ValueError(
            "unknown quality level %r; known: %s" % (level, ", ".join(QUALITY_LEVELS))
        )
    return QUALITY_LEVELS.index(text)


def relaxation_depth(fitted_level, flight_level):
    """Return how many ladder rungs the fitted part sits below the flight part."""
    return quality_level_rank(fitted_level) - quality_level_rank(flight_level)


def usage_permission(part):
    """Return (permission, depth) for one part fitted to the Class 2 model."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (type(part).__name__,))
    for key in ("fitted_quality_level", "flight_quality_level", "interchangeable"):
        if key not in part:
            raise ValueError("part missing required key '%s'" % key)
    depth = relaxation_depth(part["fitted_quality_level"], part["flight_quality_level"])
    if not _require_bool(part["interchangeable"], "interchangeable"):
        return ("not-interchangeable", depth)
    if depth <= 0:
        return ("permitted-equivalent", depth)
    if depth > MAX_RELAXATION_STEPS:
        return ("relaxation-too-deep", depth)
    if _recorded(part.get("relaxation_justification")):
        return ("permitted-with-justification", depth)
    return ("relaxation-not-justified", depth)


def validate_stress_limits(limits):
    """Return the validated per-stress limits the programme declares."""
    if not isinstance(limits, dict):
        raise ValueError("stress_limits must be a mapping")
    validated = {}
    for key in STRESS_KEYS:
        if key not in limits:
            raise ValueError("stress_limits missing '%s'" % key)
        value = _require_non_negative_number(limits[key], "stress limit '%s'" % key)
        if value <= 0.0:
            raise ValueError("stress limit '%s' must be strictly positive" % key)
        validated[key] = value
    return validated


def consumed_life(part, limits):
    """Return (fraction, governing_stress, per_stress) for one fitted part."""
    validated = validate_stress_limits(limits)
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    accumulated = part.get("accumulated", {})
    if not isinstance(accumulated, dict):
        raise ValueError("part 'accumulated' must be a mapping of stress -> value")
    for key in accumulated:
        if key not in STRESS_KEYS:
            raise ValueError(
                "accumulated declares unknown stress %r; known: %s"
                % (key, ", ".join(STRESS_KEYS))
            )
    per_stress = {}
    for key in STRESS_KEYS:
        spent = _require_non_negative_number(
            accumulated.get(key, 0), "accumulated '%s'" % key
        )
        per_stress[key] = spent / validated[key]
    governing = max(STRESS_KEYS, key=lambda key: (per_stress[key], key))
    return (per_stress[governing], governing, per_stress)


def remaining_margin(fraction):
    """Return the share of life the governing stress has not yet spent."""
    value = _require_non_negative_number(fraction, "consumed life fraction")
    return max(0.0, 1.0 - value)


def post_campaign_disposition(fraction):
    """Return where a part goes once the model campaign is over."""
    value = _require_non_negative_number(fraction, "consumed life fraction")
    if value > 1.0 or math.isclose(value, 1.0, rel_tol=0.0, abs_tol=RATIO_TOLERANCE):
        return "scrap"
    if value > RETENTION_THRESHOLD or math.isclose(
        value, RETENTION_THRESHOLD, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
    ):
        return "hold-for-review"
    return "return-to-model-stock"


def flight_reuse_eligibility(permission, fraction, rescreening_recorded):
    """Return whether a model-fitted part may be carried into a flight build."""
    _require_bool(rescreening_recorded, "rescreening_recorded")
    if permission not in PERMITTED_PERMISSIONS:
        return "not-eligible-unpermitted"
    margin = remaining_margin(fraction)
    if margin < REUSE_MARGIN_RESERVE and not math.isclose(
        margin, REUSE_MARGIN_RESERVE, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
    ):
        return "not-eligible-margin-exhausted"
    if not rescreening_recorded:
        return "eligible-after-rescreening"
    return "eligible"


def _part_completeness(part):
    """Return (missing_attributes, completeness_fraction) for one fitted part."""
    if not isinstance(part, dict):
        raise ValueError("each part must be a mapping, got %r" % (type(part).__name__,))
    missing = []
    for attribute in MANDATORY_PART_ATTRIBUTES:
        if attribute not in part:
            missing.append(attribute)
            continue
        value = part[attribute]
        if value is None:
            missing.append(attribute)
        elif isinstance(value, str) and not value.strip():
            missing.append(attribute)
    total = len(MANDATORY_PART_ATTRIBUTES)
    return (tuple(missing), (total - len(missing)) / total)


def evaluate_eqm_part(part, limits):
    """Return the handling record of one part fitted to the Class 2 model."""
    missing, completeness = _part_completeness(part)
    raw = part.get("part_id") if isinstance(part, dict) else None
    label = raw.strip() if isinstance(raw, str) and raw.strip() else "<unnamed>"
    record = {
        "part_id": label,
        "missing_attributes": missing,
        "completeness": completeness,
        "relaxation_depth": None,
        "permission": "record-incomplete",
        "consumed_life": None,
        "remaining_margin": None,
        "governing_stress": None,
        "per_stress": {},
        "disposition": None,
        "nominated_for_flight_reuse": False,
        "reuse_eligibility": None,
        "permitted": False,
        "findings": ("record-incomplete",),
    }
    if missing:
        return record

    permission, depth = usage_permission(part)
    record["permission"] = permission
    record["relaxation_depth"] = depth

    fraction, governing, per_stress = consumed_life(part, limits)
    record["consumed_life"] = fraction
    record["remaining_margin"] = remaining_margin(fraction)
    record["governing_stress"] = governing
    record["per_stress"] = per_stress
    record["disposition"] = post_campaign_disposition(fraction)

    nominated = _require_bool(
        part.get("nominated_for_flight_reuse", False), "nominated_for_flight_reuse"
    )
    record["nominated_for_flight_reuse"] = nominated
    rescreened = _require_bool(
        part.get("rescreening_recorded", False), "rescreening_recorded"
    )
    if nominated:
        record["reuse_eligibility"] = flight_reuse_eligibility(
            permission, fraction, rescreened
        )

    findings = []
    if permission not in PERMITTED_PERMISSIONS:
        findings.append(permission)
    else:
        record["permitted"] = True
        if record["disposition"] == "scrap":
            findings.append("stress-limit-exceeded")
        elif record["disposition"] == "hold-for-review":
            findings.append("held-for-review")
    if nominated and record["reuse_eligibility"] == "not-eligible-margin-exhausted":
        findings.append("reuse-margin-exhausted")
    if nominated and record["reuse_eligibility"] == "eligible-after-rescreening":
        findings.append("rescreening-outstanding")
    record["findings"] = tuple(findings)
    return record


def assess_eqm_part_handling(spec):
    """Run the full clause 5.1.6 Class 2 fitted-part handling assessment.

    spec keys: parts (sequence of fitted part mappings), stress_limits
    (per-stress limits), optional required_permitted_fraction (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("parts", "stress_limits"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    parts = spec["parts"]
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("spec['parts'] must be a non-empty sequence")
    limits = validate_stress_limits(spec["stress_limits"])

    required = spec.get("required_permitted_fraction", 1.0)
    if isinstance(required, bool) or not isinstance(required, (int, float)):
        raise ValueError("required_permitted_fraction must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError(
            "required_permitted_fraction must lie in [0, 1], got %r"
            % (spec["required_permitted_fraction"],)
        )

    records = []
    seen = set()
    for part in parts:
        record = evaluate_eqm_part(part, limits)
        if record["part_id"] != "<unnamed>":
            if record["part_id"] in seen:
                raise ValueError(
                    "part %s is fitted twice in the model build" % record["part_id"]
                )
            seen.add(record["part_id"])
        records.append(record)

    permitted = sum(1 for record in records if record["permitted"])
    permitted_fraction = permitted / len(records)

    findings = []
    for record in records:
        for finding in record["findings"]:
            findings.append(
                {
                    "severity": _SEVERITY.get(finding, 8),
                    "part_id": record["part_id"],
                    "finding": finding,
                    "detail": _finding_detail(record, finding),
                }
            )
    findings.sort(
        key=lambda entry: (entry["severity"], entry["part_id"], entry["finding"])
    )

    scrap_list = tuple(
        sorted(r["part_id"] for r in records if r["disposition"] == "scrap")
    )
    reusable = tuple(
        sorted(
            r["part_id"] for r in records if r["reuse_eligibility"] in REUSE_ELIGIBLE
        )
    )
    governing = None
    scored = [r for r in records if r["consumed_life"] is not None]
    if scored:
        governing = max(
            scored, key=lambda r: (r["consumed_life"], r["part_id"])
        )["part_id"]

    meets = permitted_fraction > required or math.isclose(
        permitted_fraction, required, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
    )
    acceptable = meets and not findings
    return {
        "records": records,
        "permitted_fraction": permitted_fraction,
        "required_permitted_fraction": required,
        "meets_required_permitted_fraction": meets,
        "parts_for_scrap": scrap_list,
        "parts_cleared_for_flight_reuse": reusable,
        "governing_part": governing,
        "findings": findings,
        "acceptable": acceptable,
        "verdict": "accept" if acceptable else "hold",
    }


def _finding_detail(record, finding):
    """Return the human-readable reason a fitted part carries one finding."""
    if finding == "record-incomplete":
        return "part lacks %s; its handling cannot be decided" % ", ".join(
            record["missing_attributes"]
        )
    if finding == "not-interchangeable":
        return "fitted part is not interchangeable with the flight-intended part"
    if finding == "relaxation-too-deep":
        return (
            "fitted quality level sits %d rungs below the flight level, past the "
            "Class 2 allowance" % record["relaxation_depth"]
        )
    if finding == "relaxation-not-justified":
        return "quality level was relaxed with no justification on the record"
    if finding == "stress-limit-exceeded":
        return "%s has reached its declared limit; the part goes to scrap" % record[
            "governing_stress"
        ]
    if finding == "reuse-margin-exhausted":
        return (
            "part is nominated for a flight build with %.3f margin left on %s, "
            "under the reserve" % (record["remaining_margin"], record["governing_stress"])
        )
    if finding == "rescreening-outstanding":
        return "part is nominated for a flight build with no re-screening recorded"
    return "%s is past the retention threshold; the part is held for review" % record[
        "governing_stress"
    ]
