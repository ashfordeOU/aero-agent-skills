"""Parts fitted to an engineering qualification model under Class 3 rules.

Anchor: ECSS-Q-ST-60C clause 6.1.6 (handling of the parts fitted to
engineering qualification models under the Class 3 rules). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each fitted part: an identifier, the quality level it was actually
   fitted at, the level the flight build intends, and what the model has spent
   on it so far.
2. Measure the relaxation depth — how many rungs below the flight-intended
   level the fitted part sits. A part fitted at or above the intended level
   carries no relaxation at all and needs no substitution note.
3. Refuse a relaxation deeper than the programme allows, and refuse one the
   programme allows but nobody recorded a substitution note for.
4. Accumulate what the model has spent against the declared limit for each
   stress and keep the governing one — the stress nearest its limit is the one
   the disposition has to be argued on.
5. Return each part's post-use disposition, and state separately what that part
   means for the flight build, because a part fit to stay in the model is not
   thereby a part fit to fly.
6. Roll the parts up into one model-level verdict with ranked findings.
"""

import math

__all__ = [
    "ALLOWED_RELAXATION_DEPTH",
    "LIFE_STRESSES",
    "QUALITY_LEVEL_LADDER",
    "RETENTION_THRESHOLD",
    "TOLERANCE",
    "validate_part_id",
    "quality_level_rank",
    "relaxation_depth",
    "usage_completeness",
    "consumed_life",
    "governing_stress",
    "part_disposition",
    "flight_build_position",
    "assess_class_3_eqm_part_usage",
]

# Quality levels from the highest rung down. Rank 0 is the highest.
QUALITY_LEVEL_LADDER = (
    "space-level",
    "military-level",
    "automotive-level",
    "industrial-level",
    "commercial-level",
)

# The stresses an engineering qualification model spends on a fitted part.
LIFE_STRESSES = ("thermal_cycles", "rework_operations", "powered_hours")

# Default depth of relaxation a Class 3 model may run with before the fitted
# part stops being a stand-in for the flight part at all.
ALLOWED_RELAXATION_DEPTH = 1

# Default share of a stress limit above which a part stays with the model.
RETENTION_THRESHOLD = 0.8

# Consumed life and threshold comparisons are ratios; absorb representation
# error here rather than by moving a limit.
TOLERANCE = 1e-9

MANDATORY_USAGE_FIELDS = (
    "part_id",
    "fitted_quality_level",
    "flight_intended_quality_level",
    "spent",
)

_SEVERITY = {
    "usage-record-incomplete": 0,
    "relaxation-beyond-allowance": 1,
    "substitution-note-missing": 2,
    "life-limit-exceeded": 3,
    "retain-for-model-use-only": 4,
    "eligible-for-continued-model-use": 5,
}

_CLEAN = "eligible-for-continued-model-use"


def _require_text(value, label):
    """Return a non-blank stripped string, or raise ValueError."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_non_negative_number(value, label):
    """Return a finite non-negative real number, or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite" % label)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def _require_positive_number(value, label):
    """Return a finite strictly positive real number, or raise ValueError."""
    value = _require_non_negative_number(value, label)
    if value == 0.0:
        raise ValueError("%s must be strictly positive" % label)
    return value


def validate_part_id(value):
    """Return the validated identifier of one fitted part."""
    return _require_text(value, "part_id")


def quality_level_rank(level):
    """Return the ladder rank of one quality level; 0 is the highest rung."""
    text = _require_text(level, "quality level").lower()
    if text not in QUALITY_LEVEL_LADDER:
        raise ValueError(
            "unknown quality level %r; known: %s"
            % (level, ", ".join(QUALITY_LEVEL_LADDER))
        )
    return QUALITY_LEVEL_LADDER.index(text)


def relaxation_depth(fitted_level, flight_level):
    """Return how many rungs below the flight-intended level a part sits.

    Zero means the fitted part matches what the flight build intends. A
    negative result means the model was built with something better than the
    flight part, which is not a relaxation and raises no substitution question.
    """
    return quality_level_rank(fitted_level) - quality_level_rank(flight_level)


def usage_completeness(record):
    """Return (missing_fields, completeness_fraction) for one fitted part."""
    if not isinstance(record, dict):
        raise ValueError(
            "each fitted part must be a mapping, got %r" % (type(record).__name__,)
        )
    missing = []
    for field in MANDATORY_USAGE_FIELDS:
        if field not in record:
            missing.append(field)
            continue
        value = record[field]
        if value is None:
            missing.append(field)
        elif isinstance(value, str) and not value.strip():
            missing.append(field)
        elif field == "spent" and not isinstance(value, dict):
            missing.append(field)
    total = len(MANDATORY_USAGE_FIELDS)
    return (tuple(missing), (total - len(missing)) / total)


def consumed_life(spent, limits):
    """Return the consumed fraction of each declared stress limit."""
    if not isinstance(spent, dict):
        raise ValueError("spent must be a mapping of stress -> amount")
    if not isinstance(limits, dict) or not limits:
        raise ValueError("limits must be a non-empty mapping of stress -> limit")
    fractions = {}
    for stress in LIFE_STRESSES:
        if stress not in limits:
            raise ValueError("limits declares no value for %s" % stress)
        limit = _require_positive_number(limits[stress], "limit for %s" % stress)
        amount = _require_non_negative_number(spent.get(stress, 0), "spent %s" % stress)
        fractions[stress] = amount / limit
    for stress in spent:
        if stress not in LIFE_STRESSES:
            raise ValueError(
                "unknown stress %r; known: %s" % (stress, ", ".join(LIFE_STRESSES))
            )
    return fractions


def governing_stress(fractions):
    """Return (stress, fraction) for the stress nearest its declared limit."""
    if not isinstance(fractions, dict) or not fractions:
        raise ValueError("fractions must be a non-empty mapping")
    for stress in LIFE_STRESSES:
        if stress not in fractions:
            raise ValueError("fractions is missing %s" % stress)
    best = LIFE_STRESSES[0]
    for stress in LIFE_STRESSES[1:]:
        if fractions[stress] > fractions[best] + TOLERANCE:
            best = stress
    return (best, fractions[best])


def part_disposition(record, limits, allowed_depth=ALLOWED_RELAXATION_DEPTH,
                     retention_threshold=RETENTION_THRESHOLD):
    """Return the post-use disposition record of one fitted part."""
    if isinstance(allowed_depth, bool) or not isinstance(allowed_depth, int):
        raise ValueError("allowed_depth must be an integer")
    if allowed_depth < 0:
        raise ValueError("allowed_depth must not be negative")
    threshold = _require_non_negative_number(retention_threshold, "retention_threshold")
    if threshold > 1.0:
        raise ValueError("retention_threshold must lie in [0, 1]")

    missing, completeness = usage_completeness(record)
    raw = record.get("part_id")
    label = raw.strip() if isinstance(raw, str) and raw.strip() else "<unnamed>"
    out = {
        "part_id": label,
        "missing_fields": missing,
        "completeness": completeness,
        "relaxation_depth": None,
        "consumed": None,
        "governing_stress": None,
        "governing_fraction": None,
        "disposition": "usage-record-incomplete",
        "clean": False,
    }
    if missing:
        return out

    out["part_id"] = validate_part_id(record["part_id"])
    depth = relaxation_depth(
        record["fitted_quality_level"], record["flight_intended_quality_level"]
    )
    out["relaxation_depth"] = depth
    fractions = consumed_life(record["spent"], limits)
    out["consumed"] = fractions
    stress, fraction = governing_stress(fractions)
    out["governing_stress"] = stress
    out["governing_fraction"] = fraction

    if depth > allowed_depth:
        out["disposition"] = "relaxation-beyond-allowance"
        return out
    note = record.get("substitution_note")
    has_note = isinstance(note, str) and bool(note.strip())
    if depth > 0 and not has_note:
        out["disposition"] = "substitution-note-missing"
        return out
    if fraction > 1.0 + TOLERANCE:
        out["disposition"] = "life-limit-exceeded"
        return out
    if fraction > threshold + TOLERANCE:
        out["disposition"] = "retain-for-model-use-only"
        return out

    out["disposition"] = _CLEAN
    out["clean"] = True
    return out


def flight_build_position(disposition_record):
    """Return what one fitted part means for the flight build.

    A part that a model has already spent life on is not carried into the
    flight build on the strength of a clean model disposition. Only a part
    fitted at the flight-intended level, with nothing open against it, is even
    a candidate, and it is a candidate subject to review, never a decision.
    """
    if not isinstance(disposition_record, dict) or "disposition" not in disposition_record:
        raise ValueError("disposition_record must carry 'disposition'")
    if disposition_record["disposition"] != _CLEAN:
        return "not-eligible-for-flight-build"
    if (disposition_record.get("relaxation_depth") or 0) > 0:
        return "not-eligible-for-flight-build"
    return "flight-build-candidate-subject-to-review"


def assess_class_3_eqm_part_usage(spec):
    """Run the full clause 6.1.6 model part-handling assessment.

    spec keys: parts (sequence of fitted part mappings), limits (mapping of
    stress -> declared limit), optional allowed_relaxation_depth and optional
    retention_threshold.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("parts", "limits"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    parts = spec["parts"]
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("spec['parts'] must be a non-empty sequence")

    allowed = spec.get("allowed_relaxation_depth", ALLOWED_RELAXATION_DEPTH)
    threshold = spec.get("retention_threshold", RETENTION_THRESHOLD)

    records = []
    seen = set()
    for part in parts:
        record = part_disposition(part, spec["limits"], allowed, threshold)
        if record["part_id"] != "<unnamed>":
            if record["part_id"] in seen:
                raise ValueError("fitted part %s appears twice" % record["part_id"])
            seen.add(record["part_id"])
        record["flight_build_position"] = flight_build_position(record)
        records.append(record)

    findings = []
    for record in records:
        if record["disposition"] == _CLEAN:
            continue
        findings.append(
            {
                "severity": _SEVERITY.get(record["disposition"], 5),
                "reference": record["part_id"],
                "disposition": record["disposition"],
                "detail": _finding_detail(record),
            }
        )
    findings.sort(key=lambda entry: (entry["severity"], entry["reference"]))

    clean = sum(1 for record in records if record["clean"])
    clean_fraction = clean / len(records)
    candidates = tuple(
        sorted(
            record["part_id"]
            for record in records
            if record["flight_build_position"] == "flight-build-candidate-subject-to-review"
        )
    )
    return {
        "records": records,
        "clean_fraction": clean_fraction,
        "flight_build_candidates": candidates,
        "findings": findings,
        "model_usage_accepted": not findings,
        "verdict": "model-usage-accepted" if not findings else "hold",
    }


def _finding_detail(record):
    """Return the reason one fitted part is not cleanly disposed of."""
    disposition = record["disposition"]
    if disposition == "usage-record-incomplete":
        return "the usage record lacks %s, so no disposition can be taken" % ", ".join(
            record["missing_fields"]
        )
    if disposition == "relaxation-beyond-allowance":
        return "the fitted level sits %d rungs below the flight-intended level" % (
            record["relaxation_depth"],
        )
    if disposition == "substitution-note-missing":
        return "a relaxed part was fitted with no recorded substitution note"
    if disposition == "life-limit-exceeded":
        return "%s has passed its declared limit on this part" % record["governing_stress"]
    return "%s stands near its declared limit on this part" % record["governing_stress"]
