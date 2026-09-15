"""Handling of parts fitted to engineering qualification models on a Class 1 programme.

Anchor: ECSS-Q-ST-60C clause 4.1.6 (parts fitted to engineering qualification
models and how a Class 1 programme handles them). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the model build and the stress limits the programme declares for a
   part fitted to it.
2. Decide whether each fitted part may be there at all: how far its quality
   level sits below the flight-intended level, whether that relaxation is
   within what the programme allows, whether it was recorded as a substitution
   rather than left implicit, and whether the part is interchangeable with the
   flight-intended one in form, fit and function.
3. Account for what the model has spent on the part - thermal cycles, rework
   operations, powered hours - as a fraction of each declared limit, and keep
   the stress that governs.
4. Turn that account into the part's post-use disposition: returned to model
   stock, held for review, or scrapped.
5. State the flight-build position explicitly for every fitted part, and return
   one model-level verdict with ranked findings.
"""

import math

__all__ = [
    "RATIO_TOLERANCE",
    "QUALITY_LEVELS",
    "MAX_RELAXATION_STEPS",
    "RETENTION_THRESHOLD",
    "STRESS_KEYS",
    "MANDATORY_PART_ATTRIBUTES",
    "validate_part_id",
    "quality_level_rank",
    "relaxation_depth",
    "usage_permission",
    "validate_stress_limits",
    "consumed_life",
    "post_use_disposition",
    "evaluate_eqm_part",
    "assess_eqm_part_handling",
]

# Consumed life is a ratio of accumulated stress to a declared limit. An
# exactly-reached limit can land a few ULPs either side; absorb the
# representation error here rather than moving the limit.
RATIO_TOLERANCE = 1e-9

# Procurement quality levels, best first. The ladder is what a relaxation is
# measured on, so the order is part of the contract.
QUALITY_LEVELS = ("level-1", "level-2", "level-3", "commercial")

# How far below the flight-intended level a fitted part may sit at all.
MAX_RELAXATION_STEPS = 2

# Above this share of any declared limit, a part does not go back to model
# stock without a review.
RETENTION_THRESHOLD = 0.75

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

# Disposition -> severity used to rank findings. Lower sorts first.
_SEVERITY = {
    "record-incomplete": 0,
    "not-interchangeable": 1,
    "relaxation-too-deep": 2,
    "relaxation-not-recorded": 3,
    "stress-limit-exceeded": 4,
    "held-for-review": 5,
    "permitted": 9,
}

_PERMITTED = ("permitted-equivalent", "permitted-with-substitution-note")

_FLIGHT_POSITION = "barred-from-flight-build"
_FLIGHT_REASON = (
    "the part has spent the model's build, test and rework history; a flight "
    "build takes a part with its own unspent history"
)


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
    """Return how many ladder steps the fitted part sits below the flight part."""
    return quality_level_rank(fitted_level) - quality_level_rank(flight_level)


def usage_permission(part):
    """Return (permission, depth) for one part fitted to the model."""
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
    recorded = part.get("substitution_note")
    if isinstance(recorded, str) and recorded.strip():
        return ("permitted-with-substitution-note", depth)
    return ("relaxation-not-recorded", depth)


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
    per_stress = {}
    for key in STRESS_KEYS:
        spent = _require_non_negative_number(
            accumulated.get(key, 0), "accumulated '%s'" % key
        )
        per_stress[key] = spent / validated[key]
    governing = max(STRESS_KEYS, key=lambda key: (per_stress[key], key))
    return (per_stress[governing], governing, per_stress)


def post_use_disposition(fraction):
    """Return where a part goes once the model has finished with it."""
    value = _require_non_negative_number(fraction, "consumed life fraction")
    if value > 1.0 or math.isclose(value, 1.0, rel_tol=0.0, abs_tol=RATIO_TOLERANCE):
        return "scrap"
    if value > RETENTION_THRESHOLD or math.isclose(
        value, RETENTION_THRESHOLD, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
    ):
        return "hold-for-review"
    return "return-to-model-stock"


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
    """Return the handling record of one part fitted to the model."""
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
        "governing_stress": None,
        "per_stress": {},
        "disposition": None,
        "flight_build_position": _FLIGHT_POSITION,
        "flight_build_reason": _FLIGHT_REASON,
        "finding": "record-incomplete",
        "permitted": False,
    }
    if missing:
        return record

    permission, depth = usage_permission(part)
    record["permission"] = permission
    record["relaxation_depth"] = depth

    fraction, governing, per_stress = consumed_life(part, limits)
    record["consumed_life"] = fraction
    record["governing_stress"] = governing
    record["per_stress"] = per_stress
    record["disposition"] = post_use_disposition(fraction)

    if permission not in _PERMITTED:
        record["finding"] = permission
        return record

    record["permitted"] = True
    if record["disposition"] == "scrap":
        record["finding"] = "stress-limit-exceeded"
    elif record["disposition"] == "hold-for-review":
        record["finding"] = "held-for-review"
    else:
        record["finding"] = None
    return record


def assess_eqm_part_handling(spec):
    """Run the full clause 4.1.6 fitted-part handling assessment.

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
        if record["finding"] is None:
            continue
        findings.append(
            {
                "severity": _SEVERITY.get(record["finding"], 8),
                "part_id": record["part_id"],
                "disposition": record["finding"],
                "detail": _finding_detail(record),
            }
        )
    findings.sort(key=lambda entry: (entry["severity"], entry["part_id"]))

    scrap_list = tuple(
        sorted(record["part_id"] for record in records if record["disposition"] == "scrap")
    )
    governing = None
    scored = [r for r in records if r["consumed_life"] is not None]
    if scored:
        governing = max(scored, key=lambda r: (r["consumed_life"], r["part_id"]))["part_id"]

    meets = permitted_fraction > required or math.isclose(
        permitted_fraction, required, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
    )
    acceptable = meets and not findings
    return {
        "records": records,
        "permitted_fraction": permitted_fraction,
        "required_permitted_fraction": required,
        "parts_for_scrap": scrap_list,
        "governing_part": governing,
        "flight_build_position": _FLIGHT_POSITION,
        "findings": findings,
        "acceptable": acceptable,
        "verdict": "accept" if acceptable else "hold",
    }


def _finding_detail(record):
    """Return the human-readable reason a fitted part carries a finding."""
    finding = record["finding"]
    if finding == "record-incomplete":
        return "part lacks %s; its handling cannot be decided" % ", ".join(
            record["missing_attributes"]
        )
    if finding == "not-interchangeable":
        return "fitted part is not interchangeable with the flight-intended part"
    if finding == "relaxation-too-deep":
        return "fitted quality level sits %d steps below the flight level" % record[
            "relaxation_depth"
        ]
    if finding == "relaxation-not-recorded":
        return "quality level was relaxed without a recorded substitution note"
    if finding == "stress-limit-exceeded":
        return "%s has reached its declared limit; the part goes to scrap" % record[
            "governing_stress"
        ]
    return "%s is past the retention threshold; the part is held for review" % record[
        "governing_stress"
    ]
