"""Probabilistic safety targets and their allocation across hazards.

Anchor: ECSS-Q-ST-40C clause 6.4.4 with Annex E (quantitative safety targets
and the severity/probability acceptance criteria). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the severity categories in order and the per-mission probability
   limit each one carries, and refuse a target set that is not stricter as
   severity rises.
2. Allocate a severity's system-level target down to the hazards contributing
   to it, in proportion to declared weights, so each hazard receives a budget
   rather than the whole target.
3. Aggregate a group of hazard probabilities as a union of independent
   contributions, not as a naive sum, so a group can be graded against its
   target without the sum exceeding one.
4. Place a hazard's predicted per-mission probability in a probability band
   and read the Annex E acceptance verdict for the band and severity pair.
5. Compare predicted against allocated budget and group against group target,
   absorbing floating-point representation error at the boundary with a named
   tolerance instead of relaxing the engineering limit.
"""

import math

__all__ = [
    "SEVERITY_ORDER",
    "DEFAULT_TARGETS",
    "PROBABILITY_BANDS",
    "RISK_ACCEPTANCE",
    "TARGET_TOLERANCE",
    "validate_probability",
    "validate_severity",
    "validate_targets",
    "allocate_target",
    "aggregate_probability",
    "probability_band",
    "risk_acceptance",
    "compare_to_target",
    "assess_probabilistic_targets",
]

# Severity categories, most severe first.
SEVERITY_ORDER = ("catastrophic", "critical", "major", "minor")

# Per-mission probability limit per severity category. Programme-specific in
# practice; these are the house defaults the allocation starts from.
DEFAULT_TARGETS = {
    "catastrophic": 1.0e-4,
    "critical": 1.0e-3,
    "major": 1.0e-2,
    "minor": 1.0e-1,
}

# Probability bands, ascending in upper bound. A probability sitting exactly on
# a bound belongs to the band that bound closes.
PROBABILITY_BANDS = (
    ("extremely-improbable", 1.0e-8),
    ("extremely-remote", 1.0e-6),
    ("remote", 1.0e-4),
    ("occasional", 1.0e-2),
    ("probable", 1.0),
)

# Annex E style acceptance matrix: severity category against probability band.
RISK_ACCEPTANCE = {
    "catastrophic": {
        "extremely-improbable": "acceptable",
        "extremely-remote": "acceptable-with-review",
        "remote": "undesirable",
        "occasional": "unacceptable",
        "probable": "unacceptable",
    },
    "critical": {
        "extremely-improbable": "acceptable",
        "extremely-remote": "acceptable",
        "remote": "acceptable-with-review",
        "occasional": "undesirable",
        "probable": "unacceptable",
    },
    "major": {
        "extremely-improbable": "acceptable",
        "extremely-remote": "acceptable",
        "remote": "acceptable",
        "occasional": "acceptable-with-review",
        "probable": "undesirable",
    },
    "minor": {
        "extremely-improbable": "acceptable",
        "extremely-remote": "acceptable",
        "remote": "acceptable",
        "occasional": "acceptable",
        "probable": "acceptable-with-review",
    },
}

# A budget comparison is a ratio of very small numbers: an exact equality can
# land a few ULPs on the wrong side. Absorbed here, not by widening the target.
TARGET_TOLERANCE = 1e-12


def validate_probability(value, label):
    """Return a probability in (0, 1]; raise on anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    probability = float(value)
    if not math.isfinite(probability):
        raise ValueError("%s must be finite" % label)
    if probability <= 0.0 or probability > 1.0:
        raise ValueError("%s must lie in (0, 1], got %r" % (label, value))
    return probability


def validate_severity(value):
    """Return a known severity category; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("severity must be a string, got %r" % (value,))
    severity = value.strip().lower()
    if severity not in SEVERITY_ORDER:
        raise ValueError(
            "severity must be one of %s, got %r" % (", ".join(SEVERITY_ORDER), value)
        )
    return severity


def validate_targets(targets=None):
    """Return the validated per-severity target set.

    Every severity category must carry a target, and the target must get
    stricter as severity rises; a set that does not is a tailoring error.
    """
    if targets is None:
        targets = DEFAULT_TARGETS
    if not isinstance(targets, dict):
        raise ValueError("targets must be a mapping of severity to probability")
    unknown = sorted(key for key in targets if key not in SEVERITY_ORDER)
    if unknown:
        raise ValueError("targets carry unknown severity categories: %s" % ", ".join(unknown))
    result = {}
    for severity in SEVERITY_ORDER:
        if severity not in targets:
            raise ValueError("targets leave severity %r without a limit" % severity)
        result[severity] = validate_probability(targets[severity], "targets[%r]" % severity)
    for index in range(1, len(SEVERITY_ORDER)):
        stricter = result[SEVERITY_ORDER[index - 1]]
        looser = result[SEVERITY_ORDER[index]]
        if stricter >= looser:
            raise ValueError(
                "target for %s (%g) must be stricter than the target for %s (%g)"
                % (SEVERITY_ORDER[index - 1], stricter, SEVERITY_ORDER[index], looser)
            )
    return result


def allocate_target(target, weights):
    """Split a severity target over contributors in proportion to weights."""
    target = validate_probability(target, "target")
    if not isinstance(weights, dict) or not weights:
        raise ValueError("weights must be a non-empty mapping of contributor to weight")
    cleaned = {}
    for key, value in weights.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("weight keys must be non-empty strings, got %r" % (key,))
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("weights[%r] must be a real number, got %r" % (key, value))
        weight = float(value)
        if not math.isfinite(weight) or weight <= 0.0:
            raise ValueError("weights[%r] must be positive and finite, got %r" % (key, value))
        cleaned[key.strip()] = weight
    total = math.fsum(cleaned.values())
    if total <= 0.0:
        raise ValueError("weights must sum to a positive value")
    return {key: target * weight / total for key, weight in cleaned.items()}


def aggregate_probability(values):
    """Return the union probability of independent contributions."""
    if not isinstance(values, (list, tuple)):
        raise ValueError("values must be a sequence of probabilities")
    survival = 1.0
    for index, value in enumerate(values):
        probability = validate_probability(value, "values[%d]" % index)
        survival *= 1.0 - probability
    return 1.0 - survival


def probability_band(probability):
    """Return the band a per-mission probability falls in."""
    value = validate_probability(probability, "probability")
    for name, upper in PROBABILITY_BANDS:
        if value < upper or math.isclose(value, upper, rel_tol=TARGET_TOLERANCE, abs_tol=0.0):
            return name
    return PROBABILITY_BANDS[-1][0]


def risk_acceptance(severity, probability):
    """Return the acceptance verdict for a severity and probability pair."""
    category = validate_severity(severity)
    band = probability_band(probability)
    return RISK_ACCEPTANCE[category][band]


def compare_to_target(predicted, target):
    """Compare a predicted probability with the limit allocated to it."""
    predicted = validate_probability(predicted, "predicted")
    target = validate_probability(target, "target")
    within = predicted < target or math.isclose(
        predicted, target, rel_tol=TARGET_TOLERANCE, abs_tol=0.0
    )
    return {
        "predicted": predicted,
        "target": target,
        "margin_ratio": target / predicted,
        "within_target": within,
    }


def _hazard_record(hazard, index):
    """Return one normalised hazard contribution."""
    if not isinstance(hazard, dict):
        raise ValueError("hazards[%d] must be a mapping" % index)
    allowed = ("id", "severity", "predicted_probability", "weight")
    unknown = sorted(key for key in hazard if key not in allowed)
    if unknown:
        raise ValueError(
            "hazards[%d] carries unknown keys: %s" % (index, ", ".join(unknown))
        )
    identifier = hazard.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("hazards[%d].id must be a non-empty string" % index)
    weight = hazard.get("weight", 1.0)
    if isinstance(weight, bool) or not isinstance(weight, (int, float)):
        raise ValueError("hazards[%d].weight must be a real number" % index)
    weight = float(weight)
    if not math.isfinite(weight) or weight <= 0.0:
        raise ValueError("hazards[%d].weight must be positive and finite" % index)
    return {
        "id": identifier.strip(),
        "severity": validate_severity(hazard.get("severity")),
        "predicted": validate_probability(
            hazard.get("predicted_probability"), "hazards[%d].predicted_probability" % index
        ),
        "weight": weight,
    }


def assess_probabilistic_targets(spec):
    """Set, allocate and grade probabilistic safety targets for a hazard set.

    spec keys: hazards (sequence of {id, severity, predicted_probability,
    optional weight}) and optional targets (severity to per-mission limit).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "hazards" not in spec:
        raise ValueError("spec missing required key 'hazards'")
    hazards = spec["hazards"]
    if not isinstance(hazards, (list, tuple)) or not hazards:
        raise ValueError("spec['hazards'] must be a non-empty sequence")
    targets = validate_targets(spec.get("targets"))
    records = [_hazard_record(hazard, index) for index, hazard in enumerate(hazards)]
    seen = set()
    for record in records:
        if record["id"] in seen:
            raise ValueError("hazard id %r appears twice" % record["id"])
        seen.add(record["id"])
    groups = {}
    for record in records:
        groups.setdefault(record["severity"], []).append(record)
    findings = []
    graded = []
    group_rows = []
    for severity in SEVERITY_ORDER:
        members = groups.get(severity)
        if not members:
            continue
        budgets = allocate_target(
            targets[severity], {member["id"]: member["weight"] for member in members}
        )
        for member in members:
            budget = budgets[member["id"]]
            comparison = compare_to_target(member["predicted"], budget)
            verdict = risk_acceptance(severity, member["predicted"])
            graded.append(
                {
                    "id": member["id"],
                    "severity": severity,
                    "predicted": member["predicted"],
                    "allocated_target": budget,
                    "margin_ratio": comparison["margin_ratio"],
                    "within_target": comparison["within_target"],
                    "band": probability_band(member["predicted"]),
                    "acceptance": verdict,
                }
            )
            if not comparison["within_target"]:
                findings.append(
                    "%s predicts %.3e against an allocated budget of %.3e"
                    % (member["id"], member["predicted"], budget)
                )
            if verdict == "unacceptable":
                findings.append(
                    "%s is %s at %s severity and cannot be carried without redesign"
                    % (member["id"], probability_band(member["predicted"]), severity)
                )
        union = aggregate_probability([member["predicted"] for member in members])
        group = compare_to_target(union, targets[severity])
        group_rows.append(
            {
                "severity": severity,
                "hazard_count": len(members),
                "aggregate_probability": union,
                "target": targets[severity],
                "margin_ratio": group["margin_ratio"],
                "within_target": group["within_target"],
            }
        )
        if not group["within_target"]:
            findings.append(
                "the %s group aggregates to %.3e against a target of %.3e"
                % (severity, union, targets[severity])
            )
    return {
        "targets": targets,
        "hazards": graded,
        "groups": group_rows,
        "findings": findings,
        "verdict": "targets-met" if not findings else "targets-not-met",
    }
