"""Manufacturer quality system assessment for Class 1 commercial parts.

Anchor: ECSS-Q-ST-60-13C clause 4.2.3.2 (assessing the manufacturer of a
commercial part -- its quality system and the controls behind the product --
before the part is accepted for the highest assurance class).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The assessment is scored over a fixed set of dimensions, each weighted by
  how much of the risk it holds down. Three of them are veto dimensions: the
  quality management system, the commitment to notify process changes, and
  traceability back to the wafer and the assembly lot. A programme that loses
  any one of those cannot recover it with a high score elsewhere, because the
  three are what make every later control mean anything.
* A dimension carries two independent facts: how well it was rated, and what
  the rating was based on. A rating is discounted by the confidence its
  evidence basis earns -- an on-site audit at full weight, a remote audit a
  little below, a third-party certificate below that, a self-declared
  questionnaire at half, and an unevidenced claim at nothing. A perfect rating
  from a questionnaire is worth half a perfect rating from an audit, and the
  two are never recorded as the same thing.
* A veto dimension is also breached when its evidence basis sits under the
  floor, whatever its rating says. Believing a self-declaration about
  traceability is the failure mode the floor exists to stop.
* Evidence ages. Past its validity period the assessment cannot be accepted
  outright, however it scored, and the best available outcome becomes an
  acceptance with actions.
* The outcome is a weighted score plus the ranked list of what is owed, so the
  programme knows both where it stands and which dimension to attack first.
"""

from __future__ import annotations

import math

# Assessment dimensions and the share of the risk each one holds down.
DIMENSION_WEIGHTS = {
    "quality-management-system": 1.0,
    "process-change-notification-commitment": 1.0,
    "lot-traceability-to-wafer-and-assembly": 1.0,
    "reliability-monitoring-programme": 0.8,
    "failure-analysis-and-corrective-action": 0.8,
    "obsolescence-and-discontinuance-notice": 0.6,
    "subcontracted-assembly-control": 0.6,
    "component-change-history-availability": 0.4,
}

# Dimensions that sink the assessment on their own.
VETO_DIMENSIONS = (
    "quality-management-system",
    "process-change-notification-commitment",
    "lot-traceability-to-wafer-and-assembly",
)

RATING_SCORES = {
    "meets-requirement": 1.0,
    "meets-with-minor-observation": 0.75,
    "partially-meets": 0.4,
    "does-not-meet": 0.0,
}

EVIDENCE_CONFIDENCE = {
    "on-site-audit": 1.0,
    "remote-audit": 0.85,
    "third-party-certificate": 0.7,
    "self-declared-questionnaire": 0.5,
    "no-evidence": 0.0,
}

# Evidence basis a veto dimension has to reach before its rating is believed.
VETO_EVIDENCE_FLOOR = 0.7

# Beyond this the evidence is outside its validity period.
ASSESSMENT_VALIDITY_MONTHS = 36

ACCEPT_THRESHOLD = 0.8
ACTIONS_THRESHOLD = 0.6

VERDICTS = (
    "manufacturer-assessment-accepted",
    "manufacturer-assessment-actions-required",
    "manufacturer-assessment-rejected",
)

# The score is a ratio of sums of products; a value that should land on a
# threshold can miss it by a few units in the last place. The thresholds
# themselves are never lowered by this tolerance.
SCORE_TOLERANCE = 1e-9


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def dimension_weight(name):
    """Weight of one assessment dimension; unknown names are rejected."""
    if name not in DIMENSION_WEIGHTS:
        raise ValueError(
            "unknown assessment dimension %r (known: %s)"
            % (name, ", ".join(sorted(DIMENSION_WEIGHTS)))
        )
    return DIMENSION_WEIGHTS[name]


def rating_score(rating):
    """Score of an assessment rating before the evidence discount."""
    if rating not in RATING_SCORES:
        raise ValueError(
            "unknown rating %r (known: %s)" % (rating, ", ".join(sorted(RATING_SCORES)))
        )
    return RATING_SCORES[rating]


def evidence_confidence(basis):
    """Confidence factor earned by the basis a rating was taken on."""
    if basis not in EVIDENCE_CONFIDENCE:
        raise ValueError(
            "unknown evidence basis %r (known: %s)"
            % (basis, ", ".join(sorted(EVIDENCE_CONFIDENCE)))
        )
    return EVIDENCE_CONFIDENCE[basis]


def effective_credit(rating, basis):
    """Rating discounted by the confidence of the evidence behind it."""
    return rating_score(rating) * evidence_confidence(basis)


def normalize_dimension(raw):
    """Validate one dimension declaration and fill in its defaults."""
    if not isinstance(raw, dict):
        raise ValueError("dimension must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("dimension")
    dimension_weight(name)  # validation only
    rating = raw.get("rating", "does-not-meet")
    rating_score(rating)  # validation only
    basis = raw.get("evidence_basis", "no-evidence")
    evidence_confidence(basis)  # validation only
    return {"dimension": name, "rating": rating, "evidence_basis": basis}


def assess_dimension(raw):
    """Grade one dimension into a credit, a veto decision and its findings."""
    entry = normalize_dimension(raw)
    name = entry["dimension"]
    weight = dimension_weight(name)
    credit = effective_credit(entry["rating"], entry["evidence_basis"])
    confidence = evidence_confidence(entry["evidence_basis"])
    findings = []
    veto_breach = None
    if name in VETO_DIMENSIONS:
        if entry["rating"] == "does-not-meet":
            veto_breach = "veto-dimension-not-met"
        elif confidence < VETO_EVIDENCE_FLOOR - SCORE_TOLERANCE:
            veto_breach = "veto-dimension-evidence-below-floor"
        if veto_breach is not None:
            findings.append(veto_breach)
    if entry["evidence_basis"] == "no-evidence":
        findings.append("dimension-unevidenced")
    if credit < 1.0 - SCORE_TOLERANCE and "dimension-unevidenced" not in findings:
        findings.append("dimension-action-owed")
    return {
        "dimension": name,
        "rating": entry["rating"],
        "evidence_basis": entry["evidence_basis"],
        "weight": weight,
        "confidence": confidence,
        "credit": credit,
        "weighted_credit": weight * credit,
        "shortfall": weight * (1.0 - credit),
        "veto_breach": veto_breach,
        "findings": findings,
    }


def assessment_score(records):
    """Weighted credit of a set of graded dimensions over the total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (type(records).__name__,))
    if len(records) == 0:
        raise ValueError("an assessment must carry at least one dimension")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total assessment weight must be positive")
    return earned / total_weight


def evidence_in_validity(age_months):
    """True while the assessment evidence is inside its validity period."""
    age = _real(age_months, "age_months")
    if age < 0.0:
        raise ValueError("age_months must not be negative, got %r" % (age_months,))
    return age <= float(ASSESSMENT_VALIDITY_MONTHS) + SCORE_TOLERANCE


def verdict_for_score(score, veto_breached, in_validity):
    """Name the outcome from the score, the veto state and the evidence age."""
    value = _real(score, "score")
    if not isinstance(veto_breached, bool):
        raise ValueError("veto_breached must be a boolean, got %r" % (veto_breached,))
    if not isinstance(in_validity, bool):
        raise ValueError("in_validity must be a boolean, got %r" % (in_validity,))
    if veto_breached:
        return "manufacturer-assessment-rejected"
    if value < ACTIONS_THRESHOLD - SCORE_TOLERANCE:
        return "manufacturer-assessment-rejected"
    if value < ACCEPT_THRESHOLD - SCORE_TOLERANCE:
        return "manufacturer-assessment-actions-required"
    if not in_validity:
        return "manufacturer-assessment-actions-required"
    return "manufacturer-assessment-accepted"


def ranked_actions(records):
    """Dimensions owing an action, largest weighted shortfall first."""
    owed = [r for r in records if r["shortfall"] > SCORE_TOLERANCE]
    return sorted(owed, key=lambda r: (-r["shortfall"], r["dimension"]))


def assess_manufacturer(manufacturer_id, dimensions, evidence_age_months):
    """Grade a manufacturer over the whole dimension set and name the outcome.

    Every dimension is graded, including the ones the declaration left out --
    an unmentioned dimension is unevidenced, not excused.
    """
    if not isinstance(manufacturer_id, str) or not manufacturer_id.strip():
        raise ValueError(
            "manufacturer_id must be a non-empty string, got %r" % (manufacturer_id,)
        )
    if not isinstance(dimensions, (list, tuple)):
        raise ValueError(
            "dimensions must be a list or tuple, got %r" % (type(dimensions).__name__,)
        )
    declared = {}
    for raw in dimensions:
        entry = normalize_dimension(raw)
        if entry["dimension"] in declared:
            raise ValueError("duplicate assessment dimension %r" % (entry["dimension"],))
        declared[entry["dimension"]] = entry
    records = []
    for name in sorted(DIMENSION_WEIGHTS):
        records.append(assess_dimension(declared.get(name, {"dimension": name})))
    score = assessment_score(records)
    in_validity = evidence_in_validity(evidence_age_months)
    breaches = [r["dimension"] for r in records if r["veto_breach"] is not None]
    findings = []
    for record in records:
        for finding in record["findings"]:
            findings.append({"dimension": record["dimension"], "finding": finding})
    if not in_validity:
        findings.append(
            {"dimension": "assessment-evidence", "finding": "evidence-out-of-validity"}
        )
    verdict = verdict_for_score(score, len(breaches) > 0, in_validity)
    return {
        "manufacturer_id": manufacturer_id,
        "records": records,
        "score": score,
        "veto_breaches": breaches,
        "evidence_in_validity": in_validity,
        "actions": [r["dimension"] for r in ranked_actions(records)],
        "findings": findings,
        "verdict": verdict,
        "acceptable_for_class_1": verdict == "manufacturer-assessment-accepted",
    }
