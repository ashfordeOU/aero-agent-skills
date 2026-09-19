"""Flight lot radiation verification testing and phase D action closure.

Anchor: ECSS-Q-ST-60-15C clause 4.4.4 (flight lot verification testing and the
closure of the remaining hardness assurance actions before the qualification
and production milestones). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide whether a flight lot owes a lot verification test at all: mandatory
   for the harder part categories, and forced on the others when no heritage
   lot covers the flight material.
2. Test heritage coverage on the diffusion lot identity of the delivered
   parts, not on the date code or the part reference alone.
3. Accept or reject a tested lot on the worst result of a sample that is at
   least as large as its category demands.
4. Grade the remaining hardness assurance actions against the milestone being
   approached and return one campaign verdict.
"""

import math

__all__ = [
    "PART_CATEGORIES",
    "REQUIRED_SAMPLE_SIZE",
    "RLAT_MANDATORY",
    "MILESTONE_SEQUENCE",
    "ACTION_STATUSES",
    "MARGIN_TOLERANCE",
    "normalize_category",
    "required_sample_size",
    "normalize_milestone",
    "milestone_index",
    "lot_is_covered",
    "lot_verification_required",
    "evaluate_lot_test",
    "assess_flight_lot",
    "open_action_findings",
    "assess_verification_campaign",
]

PART_CATEGORIES = ("radiation-critical", "radiation-sensitive", "radiation-tolerant")

# The harder the category, the more of the flight lot has to be consumed by
# the verification test before the rest of it may be built into flight units.
REQUIRED_SAMPLE_SIZE = {
    "radiation-critical": 10,
    "radiation-sensitive": 5,
    "radiation-tolerant": 3,
}

# Whether the lot verification test is owed regardless of heritage.
RLAT_MANDATORY = {
    "radiation-critical": True,
    "radiation-sensitive": True,
    "radiation-tolerant": False,
}

MILESTONE_SEQUENCE = ("qualification-review", "production-readiness-review", "acceptance-review")

ACTION_STATUSES = ("open", "in-work", "closed")

MARGIN_TOLERANCE = 1e-9


def _positive(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _slug(label, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = value.strip().lower().replace("_", "-").replace(" ", "-")
    while "--" in key:
        key = key.replace("--", "-")
    key = key.strip("-")
    if not key:
        raise ValueError("%s must not be empty" % label)
    return key


def normalize_category(value):
    """Return the canonical radiation category of a part."""
    key = _slug("part category", value)
    if key not in REQUIRED_SAMPLE_SIZE:
        raise ValueError(
            "unknown part category %r; expected one of %s"
            % (value, ", ".join(PART_CATEGORIES))
        )
    return key


def required_sample_size(category):
    """Return the verification sample size a part category demands."""
    return REQUIRED_SAMPLE_SIZE[normalize_category(category)]


def normalize_milestone(value):
    """Return the canonical milestone token."""
    key = _slug("milestone", value)
    if key not in MILESTONE_SEQUENCE:
        raise ValueError(
            "unknown milestone %r; expected one of %s"
            % (value, ", ".join(MILESTONE_SEQUENCE))
        )
    return key


def milestone_index(value):
    """Return the position of a milestone in the phase D sequence."""
    return MILESTONE_SEQUENCE.index(normalize_milestone(value))


def _lot_key(record, label):
    if not isinstance(record, dict):
        raise ValueError("%s must be a mapping" % label)
    reference = _slug("%s part reference" % label, record.get("part_reference"))
    diffusion = _slug("%s diffusion lot" % label, record.get("diffusion_lot"))
    return (reference, diffusion)


def lot_is_covered(flight_lot, heritage_lots):
    """Return True when a heritage lot shares the flight lot's diffusion lot."""
    key = _lot_key(flight_lot, "flight lot")
    if not isinstance(heritage_lots, (list, tuple)):
        raise ValueError("heritage lots must be a sequence")
    for index, heritage in enumerate(heritage_lots):
        if _lot_key(heritage, "heritage lot %d" % index) == key:
            return True
    return False


def lot_verification_required(flight_lot, heritage_lots=()):
    """Decide whether a flight lot owes a verification test, and say why."""
    category = normalize_category(flight_lot.get("category"))
    if RLAT_MANDATORY[category]:
        return (True, "category %s always owes a lot verification test" % category)
    if lot_is_covered(flight_lot, heritage_lots):
        return (
            False,
            "category %s is covered by heritage data on the same diffusion lot" % category,
        )
    return (
        True,
        "category %s has no heritage data on this diffusion lot" % category,
    )


def evaluate_lot_test(results, specified_level, required_margin, minimum_sample):
    """Accept or reject a tested lot on its worst result and its sample size."""
    if not isinstance(results, (list, tuple)) or not results:
        raise ValueError("lot test results must be a non-empty sequence")
    if not isinstance(minimum_sample, int) or isinstance(minimum_sample, bool):
        raise ValueError("minimum_sample must be an integer")
    if minimum_sample < 1:
        raise ValueError("minimum_sample must be at least 1")
    level = _positive("specified_level", specified_level)
    required = _positive("required_margin", required_margin)
    values = [
        _positive("lot test result %d" % index, value) for index, value in enumerate(results)
    ]
    worst = min(values)
    margin = worst / level
    sample_ok = len(values) >= minimum_sample
    margin_ok = margin > required or math.isclose(
        margin, required, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    )
    if not sample_ok:
        reason = "sample of %d is below the %d the category demands" % (
            len(values),
            minimum_sample,
        )
    elif not margin_ok:
        reason = "worst result gives a margin of %.4f against the required %.4f" % (
            margin,
            required,
        )
    else:
        reason = "worst result clears the required margin on a full sample"
    return {
        "sample_size": len(values),
        "worst_result": worst,
        "margin": margin,
        "sample_sufficient": sample_ok,
        "margin_met": margin_ok,
        "accepted": sample_ok and margin_ok,
        "reason": reason,
    }


def assess_flight_lot(flight_lot, specified_level, required_margin, heritage_lots=()):
    """Assess one flight lot end to end."""
    if not isinstance(flight_lot, dict):
        raise ValueError("flight lot must be a mapping")
    reference = _slug("flight lot part reference", flight_lot.get("part_reference"))
    diffusion = _slug("flight lot diffusion lot", flight_lot.get("diffusion_lot"))
    category = normalize_category(flight_lot.get("category"))
    required, reason = lot_verification_required(flight_lot, heritage_lots)
    record = {
        "part_reference": reference,
        "diffusion_lot": diffusion,
        "category": category,
        "test_required": required,
        "requirement_reason": reason,
        "test": None,
        "accepted": True,
        "blocker": None,
    }
    if not required:
        return record
    results = flight_lot.get("test_results")
    if results is None:
        record["accepted"] = False
        record["blocker"] = "lot verification test is owed but no results are on record"
        return record
    evaluation = evaluate_lot_test(
        results, specified_level, required_margin, required_sample_size(category)
    )
    record["test"] = evaluation
    record["accepted"] = evaluation["accepted"]
    if not evaluation["accepted"]:
        record["blocker"] = evaluation["reason"]
    return record


def open_action_findings(actions, milestone):
    """Return the hardness assurance actions still open at a milestone."""
    if not isinstance(actions, (list, tuple)):
        raise ValueError("actions must be a sequence")
    limit = milestone_index(milestone)
    findings = []
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            raise ValueError("action %d must be a mapping" % index)
        identifier = _slug("action %d id" % index, action.get("id"))
        due = milestone_index(action.get("due_milestone"))
        status = _slug("action %d status" % index, action.get("status"))
        if status not in ACTION_STATUSES:
            raise ValueError(
                "action %s has status %r; expected one of %s"
                % (identifier, action.get("status"), ", ".join(ACTION_STATUSES))
            )
        if due <= limit and status != "closed":
            findings.append(
                "action %s is due by %s and is still %s"
                % (identifier, MILESTONE_SEQUENCE[due], status)
            )
    return findings


def assess_verification_campaign(spec):
    """Run the clause 4.4.4 verification campaign assessment.

    spec keys: flight_lots, specified_level, required_margin, milestone;
    optional heritage_lots and actions.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("flight_lots", "specified_level", "required_margin", "milestone"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    lots = spec["flight_lots"]
    if not isinstance(lots, (list, tuple)) or not lots:
        raise ValueError("flight_lots must be a non-empty sequence")
    heritage = spec.get("heritage_lots", ())
    milestone = normalize_milestone(spec["milestone"])
    assessed = [
        assess_flight_lot(lot, spec["specified_level"], spec["required_margin"], heritage)
        for lot in lots
    ]
    assessed.sort(key=lambda item: (item["part_reference"], item["diffusion_lot"]))
    blockers = []
    for item in assessed:
        if item["blocker"] is not None:
            blockers.append(
                "lot %s/%s: %s" % (item["part_reference"], item["diffusion_lot"], item["blocker"])
            )
    blockers.extend(open_action_findings(spec.get("actions", ()), milestone))
    return {
        "milestone": milestone,
        "lots": assessed,
        "lots_tested": sum(1 for item in assessed if item["test"] is not None),
        "lots_exempt": sum(1 for item in assessed if not item["test_required"]),
        "blockers": blockers,
        "milestone_ready": not blockers,
    }
