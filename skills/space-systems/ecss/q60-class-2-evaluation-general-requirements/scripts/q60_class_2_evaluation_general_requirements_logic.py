"""Need for, and extent of, a Class 2 part evaluation.

Anchor: ECSS-Q-ST-60C clause 5.2.3.1 (the point at which an evaluation
becomes necessary on a part proposed for Class 2 use, because no prior
qualification stands behind it for that use).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* Every prior record offered in place of an evaluation was earned at some
  assurance class, and that class fixes the direction it may travel. A record
  earned at Class 1 carries down to a Class 2 use. A record earned at Class 3
  never carries up, whatever else is right about it.
* Direction is necessary but not sufficient. A record is admissible only when
  it describes the article that will actually be delivered: the same
  manufacturing line, the same part variant, no process change notified since,
  inside its validity window, and taken over a mission profile at least as
  demanding as the one the part now faces.
* Coverage is the strongest admissible record, never the sum of the weak ones.
  Three partial arguments stay three partial arguments.
* A tailored programme is something the customer agrees to, not something the
  evidence grants on its own. Coverage inside the tailored band with no
  agreement on record leaves the full programme standing.
* A tailored programme is never an empty one. The manufacturer assessment and
  the constructional analysis describe the line the part is built on, so no
  outside record reaches them, and any element the surviving record does not
  itself cover stays outstanding alongside them.
* Novelty overrides evidence. A technology never flown takes the full
  programme, because no outside record can describe an article that does not
  exist anywhere else.
"""

from __future__ import annotations

import math

# The assurance class this leaf decides for.
TARGET_ASSURANCE_CLASS = 2

# Each kind of prior record: the assurance class it was earned at, and the
# most of a Class 2 evaluation programme it could cover if it is admissible.
EVIDENCE_SOURCES = {
    "qualification-to-approved-space-specification": {
        "earned_at_class": 1,
        "coverage": 1.0,
    },
    "class-1-evaluation-on-the-same-part": {
        "earned_at_class": 1,
        "coverage": 1.0,
    },
    "customer-accepted-class-2-evaluation-on-the-same-part": {
        "earned_at_class": 2,
        "coverage": 0.9,
    },
    "space-agency-qualification-of-the-same-part": {
        "earned_at_class": 2,
        "coverage": 0.7,
    },
    "class-3-evaluation-on-the-same-part": {
        "earned_at_class": 3,
        "coverage": 0.3,
    },
    "manufacturer-commercial-qualification-only": {
        "earned_at_class": 3,
        "coverage": 0.15,
    },
    "datasheet-declaration-only": {
        "earned_at_class": 3,
        "coverage": 0.0,
    },
}

# The evaluation programme owed when nothing prior carries.
FULL_PROGRAMME = (
    "manufacturer-assessment",
    "constructional-analysis",
    "electrical-characterisation-over-temperature",
    "endurance-and-environmental-testing",
    "radiation-capability-assessment",
)

# Elements that describe the manufacturing line rather than the part type.
# Outside evidence never carries these, so a tailored programme still owes
# both of them.
LINE_TIED_ELEMENTS = (
    "manufacturer-assessment",
    "constructional-analysis",
)

# A record older than this is outside its validity window.
EVIDENCE_VALIDITY_MONTHS = 60

# Coverage at or above this, but short of a whole programme, may buy a
# tailored programme when the customer has agreed to the tailoring.
TAILORED_PROGRAMME_THRESHOLD = 0.6

# Coverage is a ratio of declared credits; a case meant to sit on a bound can
# land a few units in the last place away from it.
COVERAGE_TOLERANCE = 1e-9

TECHNOLOGY_MATURITIES = (
    "catalogue-standard-product",
    "modified-standard-product",
    "new-technology-not-previously-flown",
)

DECISIONS = (
    "class-2-evaluation-not-required",
    "class-2-tailored-evaluation-required",
    "class-2-full-evaluation-required",
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


def source_profile(kind):
    """Assurance class and coverage ceiling of a kind of prior record."""
    if kind not in EVIDENCE_SOURCES:
        raise ValueError(
            "unknown prior-evidence kind %r (known: %s)"
            % (kind, ", ".join(sorted(EVIDENCE_SOURCES)))
        )
    profile = EVIDENCE_SOURCES[kind]
    return {
        "kind": kind,
        "earned_at_class": profile["earned_at_class"],
        "coverage_ceiling": profile["coverage"],
    }


def carries_to_target_class(kind):
    """True when a record may travel to a Class 2 use at all.

    Evidence earned at a stricter class carries down. Evidence earned at a
    looser class never carries up.
    """
    return source_profile(kind)["earned_at_class"] <= TARGET_ASSURANCE_CLASS


def normalize_covered_elements(raw):
    """Validate the programme elements a record claims to cover."""
    if raw is None:
        return ()
    if isinstance(raw, str) or not isinstance(raw, (list, tuple, set, frozenset)):
        raise ValueError(
            "covered_elements must be a list or tuple of element names, got %r" % (raw,)
        )
    covered = []
    for element in raw:
        if element not in FULL_PROGRAMME:
            raise ValueError(
                "unknown programme element %r (known: %s)"
                % (element, ", ".join(FULL_PROGRAMME))
            )
        if element not in covered:
            covered.append(element)
    return tuple(covered)


def evidence_admissible(item):
    """Decide whether one prior record may stand in for a Class 2 evaluation.

    Returns ``(admissible, reasons)``; ``reasons`` names every rule that
    failed, because each one names a different repair.
    """
    if not isinstance(item, dict):
        raise ValueError(
            "prior evidence must be a mapping, got %r" % (type(item).__name__,)
        )
    profile = source_profile(item.get("kind"))
    reasons = []
    if not carries_to_target_class(profile["kind"]):
        reasons.append("evidence-earned-below-the-target-assurance-class")
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
        reasons.append("evidence-out-of-validity-window")
    demand = _real(item.get("mission_demand_ratio"), "mission_demand_ratio")
    if demand <= 0.0:
        raise ValueError("mission_demand_ratio must be positive, got %r" % (demand,))
    if demand < 1.0 - COVERAGE_TOLERANCE:
        reasons.append("evidence-mission-profile-less-demanding")
    return (len(reasons) == 0, reasons)


def assess_evidence(raw):
    """Turn one prior record into the coverage it actually earns."""
    if not isinstance(raw, dict):
        raise ValueError(
            "prior evidence must be a mapping, got %r" % (type(raw).__name__,)
        )
    profile = source_profile(raw.get("kind"))
    covered = normalize_covered_elements(raw.get("covered_elements"))
    admissible, reasons = evidence_admissible(raw)
    coverage = profile["coverage_ceiling"] if admissible else 0.0
    return {
        "kind": profile["kind"],
        "earned_at_class": profile["earned_at_class"],
        "coverage_ceiling": profile["coverage_ceiling"],
        "coverage": coverage,
        "covered_elements": list(covered),
        "admissible": admissible,
        "reasons": reasons,
    }


def strongest_admissible(records):
    """Return the single record carrying the most coverage, or ``None``."""
    if not isinstance(records, (list, tuple)):
        raise ValueError(
            "records must be a list or tuple, got %r" % (type(records).__name__,)
        )
    best = None
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(
                "each record must be a mapping, got %r" % (type(record).__name__,)
            )
        if not record.get("admissible"):
            continue
        coverage = _real(record.get("coverage"), "coverage")
        if coverage < 0.0:
            raise ValueError("coverage must not be negative, got %r" % (coverage,))
        if best is None or coverage > _real(best["coverage"], "coverage"):
            best = record
    return best


def evaluation_coverage(records):
    """Coverage carried by the strongest admissible record; never a sum."""
    best = strongest_admissible(records)
    if best is None:
        return 0.0
    return _real(best["coverage"], "coverage")


def normalize_context(context):
    """Validate the use context of the candidate part."""
    if not isinstance(context, dict):
        raise ValueError(
            "context must be a mapping, got %r" % (type(context).__name__,)
        )
    maturity = context.get("technology_maturity")
    if maturity not in TECHNOLOGY_MATURITIES:
        raise ValueError(
            "unknown technology_maturity %r (known: %s)"
            % (maturity, ", ".join(TECHNOLOGY_MATURITIES))
        )
    agreed = _flag(context, "tailoring_agreed_with_customer")
    return {
        "technology_maturity": maturity,
        "tailoring_agreed_with_customer": agreed,
    }


def novelty_forces_full_programme(context):
    """True when no outside record could describe the article delivered."""
    return (
        normalize_context(context)["technology_maturity"]
        == "new-technology-not-previously-flown"
    )


def residual_programme(decision, record=None):
    """Programme elements a decision leaves outstanding."""
    if decision not in DECISIONS:
        raise ValueError(
            "unknown decision %r (known: %s)" % (decision, ", ".join(DECISIONS))
        )
    if decision == "class-2-evaluation-not-required":
        return ()
    if decision == "class-2-full-evaluation-required":
        return FULL_PROGRAMME
    covered = ()
    if record is not None:
        if not isinstance(record, dict):
            raise ValueError(
                "record must be a mapping, got %r" % (type(record).__name__,)
            )
        covered = normalize_covered_elements(record.get("covered_elements"))
    return tuple(
        element
        for element in FULL_PROGRAMME
        if element in LINE_TIED_ELEMENTS or element not in covered
    )


def assess_class_2_evaluation_need(part_id, context, prior_evidence):
    """Decide whether a Class 2 evaluation is owed, and how much of one."""
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part_id must be a non-empty string, got %r" % (part_id,))
    if not isinstance(prior_evidence, (list, tuple)):
        raise ValueError(
            "prior_evidence must be a list or tuple, got %r"
            % (type(prior_evidence).__name__,)
        )
    described = normalize_context(context)
    records = [assess_evidence(item) for item in prior_evidence]
    best = strongest_admissible(records)
    coverage = 0.0 if best is None else _real(best["coverage"], "coverage")
    forced = novelty_forces_full_programme(context)
    agreed = described["tailoring_agreed_with_customer"]

    tailoring_withheld = False
    if forced:
        decision = "class-2-full-evaluation-required"
    elif coverage >= 1.0 - COVERAGE_TOLERANCE:
        decision = "class-2-evaluation-not-required"
    elif coverage >= TAILORED_PROGRAMME_THRESHOLD - COVERAGE_TOLERANCE:
        if agreed:
            decision = "class-2-tailored-evaluation-required"
        else:
            decision = "class-2-full-evaluation-required"
            tailoring_withheld = True
    else:
        decision = "class-2-full-evaluation-required"

    findings = []
    for record in records:
        if not record["admissible"]:
            findings.append(
                {
                    "evidence": record["kind"],
                    "finding": "prior-evidence-not-admissible",
                    "reasons": list(record["reasons"]),
                }
            )
        if "evidence-earned-below-the-target-assurance-class" in record["reasons"]:
            findings.append(
                {
                    "evidence": record["kind"],
                    "finding": "lower-class-evidence-does-not-carry-upward",
                    "reasons": ["earned-at-class-%d" % record["earned_at_class"]],
                }
            )
    if forced:
        findings.append(
            {
                "evidence": described["technology_maturity"],
                "finding": "new-technology-forces-full-programme",
                "reasons": [],
            }
        )
    if records and coverage <= COVERAGE_TOLERANCE:
        findings.append(
            {
                "evidence": "all-declared",
                "finding": "no-admissible-prior-evidence",
                "reasons": [],
            }
        )
    partial = [
        r for r in records if r["admissible"] and r["coverage"] < 1.0 - COVERAGE_TOLERANCE
    ]
    if len(partial) > 1 and coverage < 1.0 - COVERAGE_TOLERANCE:
        findings.append(
            {
                "evidence": "all-declared",
                "finding": "partial-evidence-is-not-additive",
                "reasons": [],
            }
        )
    if tailoring_withheld:
        findings.append(
            {
                "evidence": "programme-tailoring",
                "finding": "tailoring-not-agreed-with-customer",
                "reasons": [],
            }
        )
    if decision == "class-2-tailored-evaluation-required":
        findings.append(
            {
                "evidence": "tailored-programme",
                "finding": "line-tied-elements-still-owed",
                "reasons": list(LINE_TIED_ELEMENTS),
            }
        )

    programme = residual_programme(decision, best)
    return {
        "part_id": part_id,
        "context": described,
        "evidence_records": records,
        "evaluation_coverage": coverage,
        "decision": decision,
        "residual_programme": list(programme),
        "findings": findings,
        "evaluation_required": decision != "class-2-evaluation-not-required",
    }
