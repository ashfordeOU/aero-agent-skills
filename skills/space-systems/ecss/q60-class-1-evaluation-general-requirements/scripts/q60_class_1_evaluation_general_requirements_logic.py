"""Need for, and extent of, a Class 1 part evaluation.

Anchor: ECSS-Q-ST-60C clause 4.2.3.1 (the point at which an evaluation has to
be run on a candidate part for the highest assurance class, because nothing
already in hand qualifies it for that use).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* Every piece of prior evidence offered in place of an evaluation belongs to a
  kind, and the kind fixes the most that evidence could ever be worth. A
  qualification against an approved space specification could stand alone; a
  commercial qualification or a datasheet declaration could never.
* Worth is only reachable when the evidence transfers. It transfers when the
  same manufacturing line and the same part variant are behind it, no process
  change has been notified since, the record is inside its validity period,
  and the environment it was taken in was at least as severe as the one the
  part now faces. Every rule that fails is named, because each names a
  different repair.
* Confidence in the prior qualification is the strongest admissible claim, not
  the sum of the weak ones. Three partial arguments do not add up to a
  qualification; they stay three partial arguments.
* Novelty overrides evidence. A technology never flown, and a part family
  whose construction is built for one programme, both take the full programme
  regardless of what is on offer.
* A reduced programme is never an empty one. The manufacturer assessment and
  the constructional analysis are tied to the line the part is actually built
  on, so outside evidence never carries them.
"""

from __future__ import annotations

import math

# The most a kind of prior evidence could be worth if it fully transfers.
EVIDENCE_CREDIT = {
    "qualification-to-approved-space-specification": 1.0,
    "qualification-by-another-space-agency": 0.8,
    "evaluation-on-same-part-from-same-line": 0.7,
    "flight-heritage-in-comparable-environment": 0.4,
    "manufacturer-commercial-qualification-only": 0.15,
    "datasheet-declaration-only": 0.0,
}

# A record older than this is outside its validity period.
EVIDENCE_VALIDITY_MONTHS = 48

# The evaluation programme owed when nothing prior carries.
FULL_PROGRAMME = (
    "manufacturer-assessment",
    "constructional-analysis",
    "radiation-capability-evaluation",
    "endurance-and-environmental-testing",
    "electrical-characterisation-over-temperature",
)

# Programme elements tied to the manufacturing line itself. Outside evidence
# never carries these, so a reduced programme still owes both.
LINE_SPECIFIC_ELEMENTS = (
    "manufacturer-assessment",
    "constructional-analysis",
)

TECHNOLOGY_MATURITIES = (
    "catalogue-standard-product",
    "modified-standard-product",
    "new-technology-not-previously-flown",
)

PART_FAMILIES = (
    "discrete-semiconductor",
    "monolithic-integrated-circuit",
    "application-specific-integrated-circuit",
    "hybrid-microcircuit",
    "passive-component",
    "electromechanical-component",
)

# Families whose construction is built for one programme, so no outside
# evidence can describe the article actually delivered.
PROGRAMME_SPECIFIC_FAMILIES = (
    "application-specific-integrated-circuit",
    "hybrid-microcircuit",
)

# Confidence at or above this, but short of a full qualification, buys a
# reduced programme rather than a waiver.
REDUCED_PROGRAMME_THRESHOLD = 0.6

# Confidence is a ratio of credits; a case meant to sit on a threshold can
# land a few units in the last place away from it.
CONFIDENCE_TOLERANCE = 1e-9

DECISIONS = (
    "class-1-evaluation-not-required",
    "class-1-reduced-evaluation-required",
    "class-1-full-evaluation-required",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _flag(mapping, key):
    """Return a required boolean field of a mapping or raise."""
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (key, value))
    return value


def evidence_credit(kind):
    """Most a kind of prior evidence is worth; unknown kinds are rejected."""
    if kind not in EVIDENCE_CREDIT:
        raise ValueError(
            "unknown prior-evidence kind %r (known: %s)"
            % (kind, ", ".join(sorted(EVIDENCE_CREDIT)))
        )
    return EVIDENCE_CREDIT[kind]


def evidence_transferable(item):
    """Decide whether one prior-evidence item transfers to this part.

    Returns ``(transferable, reasons)``; ``reasons`` names every rule that
    failed, because each one names a different repair.
    """
    if not isinstance(item, dict):
        raise ValueError(
            "prior evidence must be a mapping, got %r" % (type(item).__name__,)
        )
    reasons = []
    if not _flag(item, "same_manufacturing_line"):
        reasons.append("evidence-from-another-manufacturing-line")
    if not _flag(item, "same_part_variant"):
        reasons.append("evidence-from-another-part-variant")
    if _flag(item, "process_change_notified"):
        reasons.append("evidence-superseded-by-process-change")
    age = _real(item.get("evidence_age_months"), "evidence_age_months")
    if age < 0.0:
        raise ValueError("evidence_age_months must not be negative, got %r" % (age,))
    if age > float(EVIDENCE_VALIDITY_MONTHS):
        reasons.append("evidence-out-of-validity")
    ratio = _real(item.get("environment_severity_ratio"), "environment_severity_ratio")
    if ratio <= 0.0:
        raise ValueError(
            "environment_severity_ratio must be positive, got %r" % (ratio,)
        )
    if ratio < 1.0 - CONFIDENCE_TOLERANCE:
        reasons.append("evidence-environment-less-severe")
    return (len(reasons) == 0, reasons)


def assess_evidence(raw):
    """Grade one prior-evidence item into the credit it actually earns."""
    if not isinstance(raw, dict):
        raise ValueError(
            "prior evidence must be a mapping, got %r" % (type(raw).__name__,)
        )
    kind = raw.get("kind")
    ceiling = evidence_credit(kind)
    transferable, reasons = evidence_transferable(raw)
    credit = ceiling if transferable else 0.0
    return {
        "kind": kind,
        "credit_ceiling": ceiling,
        "credit": credit,
        "transferable": transferable,
        "reasons": reasons,
    }


def qualification_confidence(records):
    """Strongest admissible claim, never the sum of the weak ones."""
    if not isinstance(records, (list, tuple)):
        raise ValueError(
            "records must be a list or tuple, got %r" % (type(records).__name__,)
        )
    best = 0.0
    for record in records:
        credit = _real(record["credit"], "credit")
        if credit < 0.0:
            raise ValueError("credit must not be negative, got %r" % (credit,))
        if credit > best:
            best = credit
    return best


def normalize_part(part):
    """Validate the candidate part description and fill its defaults."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (type(part).__name__,))
    maturity = part.get("technology_maturity")
    if maturity not in TECHNOLOGY_MATURITIES:
        raise ValueError(
            "unknown technology_maturity %r (known: %s)"
            % (maturity, ", ".join(TECHNOLOGY_MATURITIES))
        )
    family = part.get("part_family")
    if family not in PART_FAMILIES:
        raise ValueError(
            "unknown part_family %r (known: %s)"
            % (family, ", ".join(PART_FAMILIES))
        )
    return {"technology_maturity": maturity, "part_family": family}


def novelty_forces_full_programme(part):
    """True when nothing on offer could describe the article delivered."""
    described = normalize_part(part)
    if described["technology_maturity"] == "new-technology-not-previously-flown":
        return True
    return described["part_family"] in PROGRAMME_SPECIFIC_FAMILIES


def programme_for(decision):
    """Evaluation elements a decision leaves outstanding."""
    if decision not in DECISIONS:
        raise ValueError(
            "unknown decision %r (known: %s)" % (decision, ", ".join(DECISIONS))
        )
    if decision == "class-1-evaluation-not-required":
        return ()
    if decision == "class-1-reduced-evaluation-required":
        return LINE_SPECIFIC_ELEMENTS
    return FULL_PROGRAMME


def assess_evaluation_need(part_id, part, prior_evidence):
    """Decide whether a Class 1 evaluation is owed, and how much of one."""
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part_id must be a non-empty string, got %r" % (part_id,))
    if not isinstance(prior_evidence, (list, tuple)):
        raise ValueError(
            "prior_evidence must be a list or tuple, got %r"
            % (type(prior_evidence).__name__,)
        )
    described = normalize_part(part)
    records = [assess_evidence(item) for item in prior_evidence]
    confidence = qualification_confidence(records)
    forced = novelty_forces_full_programme(part)

    if forced:
        decision = "class-1-full-evaluation-required"
    elif confidence >= 1.0 - CONFIDENCE_TOLERANCE:
        decision = "class-1-evaluation-not-required"
    elif confidence >= REDUCED_PROGRAMME_THRESHOLD - CONFIDENCE_TOLERANCE:
        decision = "class-1-reduced-evaluation-required"
    else:
        decision = "class-1-full-evaluation-required"

    findings = []
    for record in records:
        if not record["transferable"]:
            findings.append(
                {"evidence": record["kind"], "finding": "prior-evidence-does-not-transfer"}
            )
    if forced:
        findings.append(
            {"evidence": described["part_family"], "finding": "novelty-forces-full-programme"}
        )
    if records and confidence <= CONFIDENCE_TOLERANCE:
        findings.append(
            {"evidence": "all-declared", "finding": "no-admissible-prior-evidence"}
        )
    partial = [r for r in records if r["transferable"] and r["credit"] < 1.0]
    if len(partial) > 1 and confidence < 1.0 - CONFIDENCE_TOLERANCE:
        findings.append(
            {"evidence": "all-declared", "finding": "partial-evidence-is-not-additive"}
        )
    if decision == "class-1-reduced-evaluation-required":
        findings.append(
            {
                "evidence": "reduced-programme",
                "finding": "line-specific-elements-still-owed",
            }
        )

    programme = programme_for(decision)
    return {
        "part_id": part_id,
        "part": described,
        "evidence_records": records,
        "qualification_confidence": confidence,
        "decision": decision,
        "required_programme": list(programme),
        "findings": findings,
        "evaluation_required": decision != "class-1-evaluation-not-required",
    }
