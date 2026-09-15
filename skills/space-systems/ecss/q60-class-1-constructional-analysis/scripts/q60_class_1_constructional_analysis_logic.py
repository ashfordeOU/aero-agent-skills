"""Constructional analysis of Class 1 evaluation samples.

Anchor: ECSS-Q-ST-60C clause 4.2.3.3 (the cross-sectioning and internal
inspection of representative samples carried out as part of evaluating a part
for the highest assurance class).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The analysis is destructive, so the sample set is the whole argument. The
  number of samples is the larger of a family minimum and one sample for each
  declared diffusion lot and each declared assembly lot, and the samples have
  to actually span the lots and date codes they claim to represent.
* Each inspection step carries a weight and an outcome. A few steps are the
  ones the analysis exists for -- the internal visual inspection, the
  metallographic cross-section, the die-attach examination and the
  interconnect examination -- and an analysis missing any of them is
  incomplete rather than merely weaker.
* An observed anomaly is grouped into a severity category from what it touches
  and how widely it appears, never from how bad it looked. Construction
  outside what the manufacturer declared is critical on one sample; an
  interconnect-integrity anomaly is critical once it spans the sample set and
  major below that; workmanship on a minority of samples is minor.
* The conformance index is weighted credit over total weight. It ranks what is
  outstanding; a critical anomaly or a missing mandatory step decides the
  outcome on its own, at any index.
"""

from __future__ import annotations

import math

# Smallest sample set that can carry the analysis for a part family.
FAMILY_MINIMUM_SAMPLES = {
    "monolithic-integrated-circuit": 2,
    "discrete-semiconductor": 2,
    "hybrid-microcircuit": 3,
    "passive-component": 2,
    "electromechanical-component": 2,
    "connector-or-interconnect": 2,
}

SAMPLES_PER_DIFFUSION_LOT = 1
SAMPLES_PER_ASSEMBLY_LOT = 1

# Inspection steps and the share of the construction argument each supplies.
INSPECTION_STEP_WEIGHTS = {
    "external-visual-and-dimensional-check": 0.5,
    "package-seal-and-encapsulation-review": 0.7,
    "internal-visual-inspection": 1.0,
    "metallographic-cross-section-preparation": 1.0,
    "die-attach-integrity-examination": 0.9,
    "wire-bond-and-interconnect-examination": 0.9,
    "metallisation-and-passivation-examination": 0.8,
    "die-topology-and-marking-review": 0.5,
}

# The steps the analysis exists for; an analysis without one is incomplete.
MANDATORY_STEPS = (
    "internal-visual-inspection",
    "metallographic-cross-section-preparation",
    "die-attach-integrity-examination",
    "wire-bond-and-interconnect-examination",
)

STEP_OUTCOME_CREDIT = {
    "conforming": 1.0,
    "minor-deviation": 0.7,
    "major-deviation": 0.0,
    "step-not-performed": 0.0,
}

SEVERITY_CATEGORIES = (
    "critical-construction-anomaly",
    "major-construction-anomaly",
    "minor-construction-anomaly",
)

# An anomaly on at least this share of the samples is a lot-wide feature of
# the construction rather than a one-off escape.
LOT_WIDE_SAMPLE_FRACTION = 0.5

# Conformance index an acceptable construction has to reach.
ACCEPTANCE_INDEX = 0.90

# Indices are ratios of sums of weights; a case meant to sit on a bound can
# land a few units in the last place away from it.
ANALYSIS_TOLERANCE = 1e-9

VERDICTS = (
    "construction-acceptable-for-class-1",
    "construction-acceptable-with-open-actions",
    "construction-not-acceptable-for-class-1",
    "constructional-analysis-incomplete",
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
    """Return ``value`` as a positive whole count or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < 1:
        raise ValueError("%s must be at least one, got %r" % (label, value))
    return value


def _flag(mapping, key):
    """Return a required boolean field of a mapping or raise."""
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (key, value))
    return value


def family_minimum(family):
    """Smallest sample set for a part family; unknown families are rejected."""
    if family not in FAMILY_MINIMUM_SAMPLES:
        raise ValueError(
            "unknown part family %r (known: %s)"
            % (family, ", ".join(sorted(FAMILY_MINIMUM_SAMPLES)))
        )
    return FAMILY_MINIMUM_SAMPLES[family]


def required_sample_count(family, diffusion_lots, assembly_lots):
    """Samples the analysis needs before it can speak for the declared lots."""
    minimum = family_minimum(family)
    diffusion = _count(diffusion_lots, "diffusion_lots")
    assembly = _count(assembly_lots, "assembly_lots")
    return max(
        minimum,
        diffusion * SAMPLES_PER_DIFFUSION_LOT,
        assembly * SAMPLES_PER_ASSEMBLY_LOT,
    )


def normalize_samples(samples):
    """Validate the sample set and reject a repeated sample identifier."""
    if not isinstance(samples, (list, tuple)):
        raise ValueError(
            "samples must be a list or tuple, got %r" % (type(samples).__name__,)
        )
    seen = set()
    normalized = []
    for raw in samples:
        if not isinstance(raw, dict):
            raise ValueError("sample must be a mapping, got %r" % (type(raw).__name__,))
        sample_id = raw.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id.strip():
            raise ValueError("sample_id must be a non-empty string, got %r" % (sample_id,))
        if sample_id in seen:
            raise ValueError("duplicate sample identifier %r" % (sample_id,))
        seen.add(sample_id)
        record = {"sample_id": sample_id}
        for key in ("diffusion_lot", "assembly_lot", "date_code"):
            value = raw.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    "sample %r must name its %s" % (sample_id, key.replace("_", " "))
                )
            record[key] = value
        normalized.append(record)
    return normalized


def sample_coverage(samples, declared):
    """Declared lots and date codes no sample in the set represents."""
    if not isinstance(declared, dict):
        raise ValueError(
            "declared lots must be a mapping, got %r" % (type(declared).__name__,)
        )
    normalized = normalize_samples(samples)
    uncovered = []
    for key, prefix in (
        ("diffusion_lots", "diffusion-lot"),
        ("assembly_lots", "assembly-lot"),
        ("date_codes", "date-code"),
    ):
        listed = declared.get(key)
        if not isinstance(listed, (list, tuple)) or len(listed) == 0:
            raise ValueError("declared %s must be a non-empty list" % (key,))
        field = key[:-1]
        represented = {record[field] for record in normalized}
        for item in listed:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("declared %s entries must be non-empty strings" % (key,))
            if item not in represented:
                uncovered.append("%s:%s" % (prefix, item))
    return sorted(uncovered)


def step_weight(name):
    """Weight of one inspection step; unknown step names are rejected."""
    if name not in INSPECTION_STEP_WEIGHTS:
        raise ValueError(
            "unknown inspection step %r (known: %s)"
            % (name, ", ".join(sorted(INSPECTION_STEP_WEIGHTS)))
        )
    return INSPECTION_STEP_WEIGHTS[name]


def outcome_credit(outcome):
    """Credit an inspection outcome earns."""
    if outcome not in STEP_OUTCOME_CREDIT:
        raise ValueError(
            "unknown step outcome %r (known: %s)"
            % (outcome, ", ".join(sorted(STEP_OUTCOME_CREDIT)))
        )
    return STEP_OUTCOME_CREDIT[outcome]


def normalize_step(raw):
    """Validate one inspection-step record and fill its defaults."""
    if not isinstance(raw, dict):
        raise ValueError("step must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("step")
    step_weight(name)  # validation only
    outcome = raw.get("outcome", "step-not-performed")
    outcome_credit(outcome)  # validation only
    return {"step": name, "outcome": outcome}


def assess_step(raw):
    """Grade one inspection step into a credit and its findings."""
    record = normalize_step(raw)
    name = record["step"]
    outcome = record["outcome"]
    weight = step_weight(name)
    credit = outcome_credit(outcome)
    findings = []
    if outcome == "minor-deviation":
        findings.append("step-minor-deviation")
    elif outcome == "major-deviation":
        findings.append("step-major-deviation")
    elif outcome == "step-not-performed":
        findings.append("step-not-performed")
    mandatory_missing = name in MANDATORY_STEPS and outcome == "step-not-performed"
    if mandatory_missing:
        findings.append("mandatory-step-not-performed")
    return {
        "step": name,
        "outcome": outcome,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "mandatory_missing": mandatory_missing,
        "findings": findings,
    }


def conformance_index(records):
    """Weighted credit of a set of graded steps over the total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError(
            "records must be a list or tuple, got %r" % (type(records).__name__,)
        )
    if len(records) == 0:
        raise ValueError("an analysis must carry at least one inspection step")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total inspection weight must be positive")
    return earned / total_weight


def categorize_anomaly(anomaly, sample_count):
    """Group one observed anomaly into a severity category.

    The category comes from what the anomaly touches and how widely it appears
    across the sample set, never from how bad it looked down the microscope.
    """
    if not isinstance(anomaly, dict):
        raise ValueError("anomaly must be a mapping, got %r" % (type(anomaly).__name__,))
    total = _count(sample_count, "sample_count")
    observed = anomaly.get("observed_on_samples")
    if isinstance(observed, bool) or not isinstance(observed, int):
        raise ValueError("observed_on_samples must be a whole number, got %r" % (observed,))
    if observed < 1:
        raise ValueError("observed_on_samples must be at least one, got %r" % (observed,))
    if observed > total:
        raise ValueError(
            "observed_on_samples (%d) exceeds the sample count (%d)" % (observed, total)
        )
    outside_declared = _flag(anomaly, "outside_declared_construction")
    touches_interconnect = _flag(anomaly, "affects_interconnect_integrity")
    workmanship_only = _flag(anomaly, "workmanship_only")
    fraction = float(observed) / float(total)
    lot_wide = fraction >= LOT_WIDE_SAMPLE_FRACTION - ANALYSIS_TOLERANCE
    if outside_declared:
        return "critical-construction-anomaly"
    if touches_interconnect and lot_wide:
        return "critical-construction-anomaly"
    if touches_interconnect:
        return "major-construction-anomaly"
    if workmanship_only and not lot_wide:
        return "minor-construction-anomaly"
    return "major-construction-anomaly"


def assess_constructional_analysis(
    part_id, family, declared_lots, samples, steps, anomalies=()
):
    """Grade a whole constructional analysis and name one verdict."""
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part_id must be a non-empty string, got %r" % (part_id,))
    if not isinstance(steps, (list, tuple)):
        raise ValueError("steps must be a list or tuple, got %r" % (type(steps).__name__,))
    if not isinstance(anomalies, (list, tuple)):
        raise ValueError(
            "anomalies must be a list or tuple, got %r" % (type(anomalies).__name__,)
        )
    if not isinstance(declared_lots, dict):
        raise ValueError(
            "declared_lots must be a mapping, got %r" % (type(declared_lots).__name__,)
        )
    normalized_samples = normalize_samples(samples)
    if len(normalized_samples) == 0:
        raise ValueError("a constructional analysis must carry at least one sample")

    # sample_coverage validates the declared lot lists, so it runs first and
    # the sample count is then required against lists known to be well formed.
    uncovered = sample_coverage(normalized_samples, declared_lots)
    required = required_sample_count(
        family,
        len(declared_lots["diffusion_lots"]),
        len(declared_lots["assembly_lots"]),
    )

    declared_steps = {}
    for raw in steps:
        record = normalize_step(raw)
        if record["step"] in declared_steps:
            raise ValueError("duplicate inspection step %r" % (record["step"],))
        declared_steps[record["step"]] = record
    step_records = []
    for name in sorted(INSPECTION_STEP_WEIGHTS):
        step_records.append(assess_step(declared_steps.get(name, {"step": name})))
    index = conformance_index(step_records)

    findings = []
    if len(normalized_samples) < required:
        findings.append(
            {
                "item": "sample-set",
                "finding": "sample-size-below-minimum",
                "detail": "%d of %d" % (len(normalized_samples), required),
            }
        )
    for item in uncovered:
        findings.append(
            {"item": item, "finding": "declared-lot-not-represented", "detail": item}
        )
    for record in step_records:
        for finding in record["findings"]:
            findings.append(
                {"item": record["step"], "finding": finding, "detail": record["outcome"]}
            )

    categorized = []
    for anomaly in anomalies:
        severity = categorize_anomaly(anomaly, len(normalized_samples))
        categorized.append({"anomaly": anomaly.get("anomaly_id"), "severity": severity})
        findings.append(
            {
                "item": anomaly.get("anomaly_id"),
                "finding": severity,
                "detail": "%d of %d samples" % (
                    anomaly.get("observed_on_samples"),
                    len(normalized_samples),
                ),
            }
        )

    incomplete = (
        len(normalized_samples) < required
        or bool(uncovered)
        or any(r["mandatory_missing"] for r in step_records)
    )
    critical = any(
        entry["severity"] == "critical-construction-anomaly" for entry in categorized
    )
    if incomplete:
        verdict = "constructional-analysis-incomplete"
    elif critical or index < ACCEPTANCE_INDEX - ANALYSIS_TOLERANCE:
        verdict = "construction-not-acceptable-for-class-1"
    elif findings:
        verdict = "construction-acceptable-with-open-actions"
    else:
        verdict = "construction-acceptable-for-class-1"
    return {
        "part_id": part_id,
        "part_family": family,
        "sample_count": len(normalized_samples),
        "required_sample_count": required,
        "uncovered_declarations": uncovered,
        "step_records": step_records,
        "conformance_index": index,
        "anomalies": categorized,
        "findings": findings,
        "verdict": verdict,
        "acceptable_for_class_1": verdict
        in (
            "construction-acceptable-for-class-1",
            "construction-acceptable-with-open-actions",
        ),
    }
