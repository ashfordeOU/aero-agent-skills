"""Constructional analysis on Class 2 component evaluation samples.

Anchor: ECSS-Q-ST-60C clause 5.2.3.3 (the cross-sectioning and internal
inspection of representative samples inside a Class 2 component evaluation).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The analysis destroys what it looks at, so the sample set is the whole
  argument. Size comes from two directions at once — a floor for the part
  family, and one sample for every declared procurement lot — and the larger
  of the two governs.
* Size is not the same question as reach. A set can be the right size and
  still leave a declared lot or a declared date code unsectioned, and the
  analysis then speaks about the samples rather than about the part.
* An inspection step that was never executed is not a step that found nothing.
  Mandatory steps are tracked apart from the conformance index, so a skipped
  one leaves the analysis incomplete instead of merely lowering a score.
* An anomaly is graded by the barrier it sits on and by how far it spreads
  through the set, not by how alarming the photograph is. A single occurrence
  on a critical barrier still carries half that barrier's weight, because the
  set is small and nothing can be re-sectioned.
* Construction that differs from what the manufacturer declared is the failure
  the analysis exists to catch. It is conclusive on its own, whatever the
  conformance index says.
"""

from __future__ import annotations

import math

# Smallest destructive sample set that says anything about a part family.
FAMILY_SAMPLE_FLOOR = {
    "discrete-semiconductor": 2,
    "monolithic-integrated-circuit": 3,
    "hybrid-microcircuit": 3,
    "passive-component": 2,
    "electromechanical-component": 2,
    "connector": 2,
}

# Internal barriers a construction anomaly can sit on, with the weight each
# barrier carries when something is found on it.
ANOMALY_LOCATIONS = {
    "package-hermetic-seal": 1.0,
    "die-metallisation": 0.9,
    "internal-wire-bond": 0.85,
    "die-attach": 0.8,
    "external-termination-finish": 0.45,
    "internal-cavity-cleanliness": 0.35,
}

# Steps without which the analysis has not been performed.
MANDATORY_STEPS = (
    "external-visual-inspection",
    "internal-visual-inspection",
    "metallographic-cross-section",
    "die-material-and-marking-check",
)

# Steps that add confidence but whose absence is not incompleteness.
OPTIONAL_STEPS = (
    "scanning-electron-microscopy",
    "wire-bond-strength-check",
    "residual-gas-analysis",
)

ANALYSIS_STEPS = MANDATORY_STEPS + OPTIONAL_STEPS

# A single occurrence still carries this share of its barrier's weight,
# because the set is small and nothing can be sectioned twice.
BASE_INCIDENCE_SHARE = 0.5

MAJOR_SEVERITY_THRESHOLD = 0.7
MINOR_SEVERITY_THRESHOLD = 0.35

# Severity is a product of declared weights; a case meant to sit on a bound
# can land a few units in the last place away from it.
SEVERITY_TOLERANCE = 1e-9

ANOMALY_GRADES = ("major", "minor", "observation")

VERDICTS = (
    "class-2-construction-accepted",
    "class-2-construction-accepted-with-limitation",
    "class-2-construction-rejected",
    "class-2-construction-analysis-incomplete",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _count(value, label):
    """Return ``value`` as a non-negative integer count or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def _flag(mapping, key):
    """Return a required boolean field of a mapping or raise."""
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (key, value))
    return value


def _label(value, label):
    """Return a required non-empty string field or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def family_sample_floor(family):
    """Smallest sample set the part family alone demands."""
    if family not in FAMILY_SAMPLE_FLOOR:
        raise ValueError(
            "unknown part family %r (known: %s)"
            % (family, ", ".join(sorted(FAMILY_SAMPLE_FLOOR)))
        )
    return FAMILY_SAMPLE_FLOOR[family]


def required_sample_count(family, declared_lots):
    """Sample count owed: the family floor or one per declared lot, whichever
    is larger."""
    if isinstance(declared_lots, str) or not isinstance(
        declared_lots, (list, tuple, set, frozenset)
    ):
        raise ValueError(
            "declared_lots must be a list or tuple of lot names, got %r"
            % (declared_lots,)
        )
    lots = {_label(lot, "declared lot") for lot in declared_lots}
    if not lots:
        raise ValueError("at least one procurement lot must be declared")
    return max(family_sample_floor(family), len(lots))


def normalize_samples(samples):
    """Validate the sectioned sample set."""
    if isinstance(samples, str) or not isinstance(samples, (list, tuple)):
        raise ValueError(
            "samples must be a list or tuple of mappings, got %r" % (samples,)
        )
    normalized = []
    seen = set()
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError(
                "each sample must be a mapping, got %r" % (type(sample).__name__,)
            )
        sample_id = _label(sample.get("sample_id"), "sample_id")
        if sample_id in seen:
            raise ValueError("duplicate sample_id %r" % (sample_id,))
        seen.add(sample_id)
        normalized.append(
            {
                "sample_id": sample_id,
                "lot": _label(sample.get("lot"), "lot"),
                "date_code": _label(sample.get("date_code"), "date_code"),
                "construction_matches_declaration": _flag(
                    sample, "construction_matches_declaration"
                ),
            }
        )
    return normalized


def sample_set_reach(samples, declared_lots, declared_date_codes):
    """Decide whether the sectioned set reaches everything it speaks for.

    Returns ``(reaches, gaps)``; ``gaps`` names every declared lot and date
    code no sample covered, because each one is a separate repair.
    """
    normalized = normalize_samples(samples)
    covered_lots = {sample["lot"] for sample in normalized}
    covered_codes = {sample["date_code"] for sample in normalized}
    gaps = []
    for lot in sorted({_label(lot, "declared lot") for lot in declared_lots}):
        if lot not in covered_lots:
            gaps.append("declared-lot-not-sectioned:%s" % lot)
    for code in sorted({_label(c, "declared date code") for c in declared_date_codes}):
        if code not in covered_codes:
            gaps.append("declared-date-code-not-sectioned:%s" % code)
    return (len(gaps) == 0, gaps)


def normalize_steps(steps):
    """Validate the inspection steps actually carried out."""
    if not isinstance(steps, dict):
        raise ValueError("steps must be a mapping, got %r" % (type(steps).__name__,))
    normalized = {}
    for name, record in steps.items():
        if name not in ANALYSIS_STEPS:
            raise ValueError(
                "unknown analysis step %r (known: %s)"
                % (name, ", ".join(ANALYSIS_STEPS))
            )
        if not isinstance(record, dict):
            raise ValueError(
                "step %r must map to a mapping, got %r" % (name, type(record).__name__)
            )
        executed = _flag(record, "executed")
        conforms = _flag(record, "conforms")
        if conforms and not executed:
            raise ValueError(
                "step %r cannot conform without having been executed" % (name,)
            )
        normalized[name] = {"executed": executed, "conforms": conforms}
    return normalized


def missing_mandatory_steps(steps):
    """Mandatory steps that were never executed."""
    normalized = normalize_steps(steps)
    return tuple(
        name
        for name in MANDATORY_STEPS
        if name not in normalized or not normalized[name]["executed"]
    )


def step_conformance(steps):
    """Share of the executed steps that conformed; zero when none ran."""
    normalized = normalize_steps(steps)
    executed = [r for r in normalized.values() if r["executed"]]
    if not executed:
        return 0.0
    conforming = [r for r in executed if r["conforms"]]
    return float(len(conforming)) / float(len(executed))


def anomaly_severity(location, affected_samples, sample_count):
    """Severity of one anomaly: its barrier weight scaled by how far it
    spreads through the sectioned set."""
    if location not in ANOMALY_LOCATIONS:
        raise ValueError(
            "unknown anomaly location %r (known: %s)"
            % (location, ", ".join(sorted(ANOMALY_LOCATIONS)))
        )
    total = _count(sample_count, "sample_count")
    if total <= 0:
        raise ValueError("sample_count must be positive, got %r" % (sample_count,))
    affected = _count(affected_samples, "affected_samples")
    if affected <= 0:
        raise ValueError(
            "affected_samples must be positive, got %r" % (affected_samples,)
        )
    if affected > total:
        raise ValueError(
            "affected_samples %d exceeds sample_count %d" % (affected, total)
        )
    incidence = float(affected) / float(total)
    weight = ANOMALY_LOCATIONS[location]
    return weight * (BASE_INCIDENCE_SHARE + (1.0 - BASE_INCIDENCE_SHARE) * incidence)


def grade_anomaly(severity):
    """Group one severity into a major, minor or observation grade."""
    value = _real(severity, "severity")
    if value < 0.0:
        raise ValueError("severity must not be negative, got %r" % (value,))
    if value >= MAJOR_SEVERITY_THRESHOLD - SEVERITY_TOLERANCE:
        return "major"
    if value >= MINOR_SEVERITY_THRESHOLD - SEVERITY_TOLERANCE:
        return "minor"
    return "observation"


def assess_anomaly(anomaly, sample_count):
    """Turn one reported anomaly into a graded record."""
    if not isinstance(anomaly, dict):
        raise ValueError(
            "anomaly must be a mapping, got %r" % (type(anomaly).__name__,)
        )
    location = anomaly.get("location")
    severity = anomaly_severity(
        location, anomaly.get("affected_samples"), sample_count
    )
    return {
        "location": location,
        "affected_samples": anomaly.get("affected_samples"),
        "severity": severity,
        "grade": grade_anomaly(severity),
    }


def assess_constructional_analysis(
    part_id,
    part_family,
    declared_lots,
    declared_date_codes,
    samples,
    steps,
    anomalies,
):
    """Read a Class 2 constructional analysis and return one verdict."""
    _label(part_id, "part_id")
    required = required_sample_count(part_family, declared_lots)
    normalized_samples = normalize_samples(samples)
    sample_count = len(normalized_samples)
    if sample_count == 0:
        raise ValueError("at least one sectioned sample is required")
    if isinstance(anomalies, str) or not isinstance(anomalies, (list, tuple)):
        raise ValueError(
            "anomalies must be a list or tuple of mappings, got %r" % (anomalies,)
        )

    reaches, gaps = sample_set_reach(samples, declared_lots, declared_date_codes)
    missing = missing_mandatory_steps(steps)
    conformance = step_conformance(steps)
    graded = [assess_anomaly(item, sample_count) for item in anomalies]
    mismatched = [
        sample["sample_id"]
        for sample in normalized_samples
        if not sample["construction_matches_declaration"]
    ]

    findings = []
    if sample_count < required:
        findings.append(
            {
                "subject": "sample-set",
                "finding": "sectioned-sample-count-below-requirement",
                "detail": "%d of %d" % (sample_count, required),
            }
        )
    for gap in gaps:
        findings.append(
            {"subject": "sample-set", "finding": "declared-population-unreached", "detail": gap}
        )
    for name in missing:
        findings.append(
            {"subject": name, "finding": "mandatory-step-not-executed", "detail": name}
        )
    for sample_id in mismatched:
        findings.append(
            {
                "subject": sample_id,
                "finding": "construction-differs-from-declaration",
                "detail": sample_id,
            }
        )
    for record in graded:
        if record["grade"] != "observation":
            findings.append(
                {
                    "subject": record["location"],
                    "finding": "%s-construction-anomaly" % record["grade"],
                    "detail": "%d of %d samples"
                    % (record["affected_samples"], sample_count),
                }
            )

    has_major = any(record["grade"] == "major" for record in graded)
    has_minor = any(record["grade"] == "minor" for record in graded)
    complete = not missing and reaches and sample_count >= required

    if mismatched or has_major:
        verdict = "class-2-construction-rejected"
    elif not complete:
        verdict = "class-2-construction-analysis-incomplete"
    elif has_minor:
        verdict = "class-2-construction-accepted-with-limitation"
    else:
        verdict = "class-2-construction-accepted"

    return {
        "part_id": part_id,
        "part_family": part_family,
        "required_sample_count": required,
        "sectioned_sample_count": sample_count,
        "sample_set_reaches_declared_population": reaches,
        "population_gaps": gaps,
        "missing_mandatory_steps": list(missing),
        "step_conformance": conformance,
        "anomalies": graded,
        "declaration_mismatch_samples": mismatched,
        "analysis_complete": complete,
        "findings": findings,
        "verdict": verdict,
    }
