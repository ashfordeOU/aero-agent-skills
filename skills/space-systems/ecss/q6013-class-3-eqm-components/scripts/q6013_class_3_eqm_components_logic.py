"""Part choice for an engineering qualification model at the lowest class.

Anchor: ECSS-Q-ST-60-13C clause 6.1.6 (choice of commercial components fitted
to an engineering qualification model when the programme works at the lowest
assurance class). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate the slot: the flight-intended part, the candidates offered for it
   and the window inside which the model has to be built.
2. Rule out a candidate whose function or pinout differs from the intended
   part. The model exists to exercise the design, and a candidate that changes
   what the circuit does never exercises it, whatever the class allows.
3. Rule out a candidate that cannot arrive inside the build window, because a
   part that misses the build is not a choice.
4. Weight the remaining build-standard differences into a match fraction.
5. Pick the best admissible candidate with a reproducible tie-break, list the
   build-standard deltas the choice creates, map each delta onto the record
   the flight build then has to carry, and return one slot verdict.
"""

import math

__all__ = [
    "MATCH_TOLERANCE",
    "HARD_ATTRIBUTES",
    "DEFAULT_SOFT_WEIGHTS",
    "DELTA_RECORD",
    "REJECTION_REASONS",
    "SLOT_VERDICTS",
    "validate_identifier",
    "validate_soft_weights",
    "hard_mismatches",
    "soft_deltas",
    "match_fraction",
    "screen_candidate",
    "delta_records",
    "choose_eqm_part",
]

# Match fractions are sums of weights subtracted from unity; an exactly-met
# floor can land a few ULPs low. Absorb that here, not by moving the floor.
MATCH_TOLERANCE = 1e-9

# Attributes on which a difference makes the candidate a different design
# rather than a less representative build standard. No weighting rescues
# these, and no assurance class makes them negotiable.
HARD_ATTRIBUTES = ("function", "pinout")

# Build-standard attributes that may differ on a model at the lowest class,
# and the share of the match argument each one carries. The weights sum to
# unity.
DEFAULT_SOFT_WEIGHTS = {
    "package": 0.30,
    "supply_range": 0.25,
    "manufacturer": 0.20,
    "screening_level": 0.15,
    "mounting_technology": 0.10,
}

# Differing attribute -> the delta the flight build then has to carry on the
# record, because the model no longer demonstrates it.
DELTA_RECORD = {
    "package": "mechanical-interface-delta",
    "supply_range": "operating-range-delta",
    "manufacturer": "supply-source-delta",
    "screening_level": "assurance-level-delta",
    "mounting_technology": "assembly-process-delta",
}

REJECTION_REASONS = ("hard-attribute-mismatch", "outside-build-window")

SLOT_VERDICTS = (
    "intended-part-fitted",
    "substitution-recorded",
    "escalate",
)


def validate_identifier(value, label):
    """Return a non-blank stripped identifier, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_non_negative_int(value, label):
    """Return a non-negative integer, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def validate_soft_weights(weights=None):
    """Return a validated soft-attribute weight mapping summing to unity."""
    if weights is None:
        weights = DEFAULT_SOFT_WEIGHTS
    if not isinstance(weights, dict) or not weights:
        raise ValueError("weights must be a non-empty mapping")
    cleaned = {}
    for name, value in weights.items():
        attribute = validate_identifier(name, "weight attribute name")
        if attribute in HARD_ATTRIBUTES:
            raise ValueError(
                "%s is a hard attribute and may not be weighted" % attribute
            )
        if attribute not in DELTA_RECORD:
            raise ValueError(
                "attribute %s has no declared build-standard delta record; add it "
                "to the record map before weighting it" % attribute
            )
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("weight of %s must be a real number" % attribute)
        number = float(value)
        if not math.isfinite(number) or number <= 0.0:
            raise ValueError("weight of %s must be positive and finite" % attribute)
        cleaned[attribute] = number
    total = math.fsum(cleaned.values())
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=MATCH_TOLERANCE):
        raise ValueError("soft weights must sum to unity, got %.12f" % total)
    return cleaned


def hard_mismatches(candidate, intended):
    """Return the hard attributes on which a candidate differs from intended."""
    for label, mapping in (("candidate", candidate), ("intended", intended)):
        if not isinstance(mapping, dict):
            raise ValueError("%s must be a mapping" % label)
    differing = []
    for attribute in HARD_ATTRIBUTES:
        if attribute not in candidate:
            raise ValueError("candidate lacks the hard attribute %s" % attribute)
        if attribute not in intended:
            raise ValueError("intended part lacks the hard attribute %s" % attribute)
        left = validate_identifier(candidate[attribute], "candidate %s" % attribute)
        right = validate_identifier(intended[attribute], "intended %s" % attribute)
        if left.lower() != right.lower():
            differing.append(attribute)
    return tuple(differing)


def soft_deltas(candidate, intended, weights=None):
    """Return the weighted attributes on which a candidate differs."""
    for label, mapping in (("candidate", candidate), ("intended", intended)):
        if not isinstance(mapping, dict):
            raise ValueError("%s must be a mapping" % label)
    graded = validate_soft_weights(weights)
    differing = []
    for attribute in sorted(graded):
        if attribute not in candidate:
            raise ValueError("candidate lacks the attribute %s" % attribute)
        if attribute not in intended:
            raise ValueError("intended part lacks the attribute %s" % attribute)
        left = validate_identifier(candidate[attribute], "candidate %s" % attribute)
        right = validate_identifier(intended[attribute], "intended %s" % attribute)
        if left.lower() != right.lower():
            differing.append(attribute)
    return tuple(differing)


def match_fraction(deltas, weights=None):
    """Return the share of the build standard a candidate still shares."""
    graded = validate_soft_weights(weights)
    if not isinstance(deltas, (list, tuple)):
        raise ValueError("deltas must be a sequence of attribute names")
    lost = 0.0
    seen = set()
    for name in deltas:
        attribute = validate_identifier(name, "delta attribute")
        if attribute not in graded:
            raise ValueError("delta %s is not a weighted attribute" % attribute)
        if attribute in seen:
            raise ValueError("delta %s listed more than once" % attribute)
        seen.add(attribute)
        lost += graded[attribute]
    value = 1.0 - lost
    if value < 0.0:
        value = 0.0
    return value


def delta_records(deltas):
    """Return the records the flight build has to carry for these deltas."""
    if not isinstance(deltas, (list, tuple)):
        raise ValueError("deltas must be a sequence of attribute names")
    records = set()
    for name in deltas:
        attribute = validate_identifier(name, "delta attribute")
        if attribute not in DELTA_RECORD:
            raise ValueError("delta %s has no declared record obligation" % attribute)
        records.add(DELTA_RECORD[attribute])
    return tuple(sorted(records))


def screen_candidate(candidate, intended, build_window_days, weights=None):
    """Return the admissibility record of one candidate for the model slot.

    candidate keys: reference, function, pinout, the weighted attributes, and
    lead_days.
    """
    if not isinstance(candidate, dict):
        raise ValueError("each candidate must be a mapping")
    reference = validate_identifier(candidate.get("reference"), "reference")
    window = _require_non_negative_int(build_window_days, "build_window_days")
    lead_days = _require_non_negative_int(candidate.get("lead_days"), "lead_days")
    hard = hard_mismatches(candidate, intended)
    graded = validate_soft_weights(weights)
    soft = soft_deltas(candidate, intended, graded)
    value = match_fraction(soft, graded)

    reason = None
    if hard:
        reason = "hard-attribute-mismatch"
    elif lead_days > window:
        reason = "outside-build-window"
    return {
        "reference": reference,
        "lead_days": lead_days,
        "hard_mismatches": hard,
        "soft_deltas": soft,
        "match_fraction": value,
        "admissible": reason is None,
        "rejection_reason": reason,
        "delta_records": delta_records(soft),
    }


def choose_eqm_part(spec):
    """Run the full clause 6.1.6 model part choice for one slot.

    spec keys: intended (mapping), candidates (non-empty sequence),
    build_window_days, optional floor (default 0.5), optional weights.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("intended", "candidates", "build_window_days"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    candidates = spec["candidates"]
    if not isinstance(candidates, (list, tuple)) or not candidates:
        raise ValueError("spec['candidates'] must be a non-empty sequence")
    floor = spec.get("floor", 0.5)
    if isinstance(floor, bool) or not isinstance(floor, (int, float)):
        raise ValueError("floor must be a real number")
    floor = float(floor)
    if not math.isfinite(floor) or floor < 0.0 or floor > 1.0:
        raise ValueError("floor must lie in [0, 1], got %r" % (spec.get("floor"),))
    graded = validate_soft_weights(spec.get("weights"))

    records = [
        screen_candidate(item, spec["intended"], spec["build_window_days"], graded)
        for item in candidates
    ]
    seen = set()
    for record in records:
        if record["reference"] in seen:
            raise ValueError("candidate %s is offered twice" % record["reference"])
        seen.add(record["reference"])

    admissible = [record for record in records if record["admissible"]]
    ranked = sorted(
        admissible,
        key=lambda r: (-r["match_fraction"], r["lead_days"], r["reference"]),
    )

    findings = []
    for record in records:
        if record["admissible"]:
            continue
        findings.append(
            {
                "severity": 0 if record["rejection_reason"] == REJECTION_REASONS[0] else 1,
                "reference": record["reference"],
                "detail": "%s ruled out: %s"
                % (record["reference"], record["rejection_reason"]),
            }
        )
    findings.sort(key=lambda item: (item["severity"], item["reference"]))

    if not ranked:
        return {
            "records": records,
            "ranked": (),
            "chosen": None,
            "floor": floor,
            "match_fraction": None,
            "meets_floor": False,
            "build_standard_deltas": (),
            "flight_build_records": (),
            "findings": findings,
            "verdict": "escalate",
        }

    chosen = ranked[0]
    value = chosen["match_fraction"]
    meets_floor = value > floor or math.isclose(
        value, floor, rel_tol=0.0, abs_tol=MATCH_TOLERANCE
    )
    if not chosen["soft_deltas"]:
        verdict = "intended-part-fitted"
    elif meets_floor:
        verdict = "substitution-recorded"
    else:
        verdict = "escalate"
    if chosen["soft_deltas"]:
        findings.append(
            {
                "severity": 1 if meets_floor else 0,
                "reference": chosen["reference"],
                "detail": "%s differs on %s; the flight build carries %s"
                % (
                    chosen["reference"],
                    ", ".join(chosen["soft_deltas"]),
                    ", ".join(chosen["delta_records"]),
                ),
            }
        )
        findings.sort(key=lambda item: (item["severity"], item["reference"]))
    return {
        "records": records,
        "ranked": tuple(record["reference"] for record in ranked),
        "chosen": chosen,
        "floor": floor,
        "match_fraction": value,
        "meets_floor": meets_floor,
        "build_standard_deltas": chosen["soft_deltas"],
        "flight_build_records": chosen["delta_records"],
        "findings": findings,
        "verdict": verdict,
    }
