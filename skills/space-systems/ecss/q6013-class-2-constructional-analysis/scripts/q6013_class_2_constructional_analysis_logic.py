"""Constructional analysis of a commercial part at the intermediate class.

Anchor: ECSS-Q-ST-60-13C clause 5.2.3.3 (the examination of what is inside a
commercial EEE part, run to expose the construction weaknesses a datasheet
and an electrical test cannot show, at the intermediate assurance class).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The analysis is a set of inspection steps, each carrying a weight that says
  how much of the internal picture it supplies. Three of them are structural:
  the internal visual inspection, the die metallisation inspection and the
  wire bond integrity test each look at a failure mode nothing else in the
  set reaches, so an analysis that skipped one is incomplete regardless of
  how clean the rest came back.
* Some steps depend on the package. A hermeticity test and an internal water
  vapour measurement have nothing to measure on a plastic-encapsulated part,
  so for that package they leave the set rather than counting as gaps.
* Every step owes a sample, and the sample owes a size. A step performed on
  fewer parts than the step requires has been performed on too little to be
  representative, and is reported as under-sampled rather than as evidence.
* The sample has to come from the lot the programme is buying. A part from
  another date code describes a construction the programme is not receiving,
  which is the quietest way a constructional analysis is made to say nothing.
* What a step found is graded by severity, and the severity is scored against
  the weight of the step that found it. The weighted sum over the applicable
  weight is a construction risk index between zero and one, and the index is
  read against two bounds: acceptable, acceptable once mitigated, or rejected.
* A single disqualifying defect rejects the part type outright, and a named
  construction weakness always owes a mitigation. An index is a summary, and
  a summary can average a showstopper away.
"""

from __future__ import annotations

import math

# Inspection steps and the share of the internal picture each supplies.
STEP_WEIGHTS = {
    "external-visual-inspection": 0.4,
    "x-ray-radiography": 0.7,
    "hermeticity-and-seal-test": 0.6,
    "internal-visual-inspection": 1.0,
    "die-metallisation-inspection": 1.0,
    "wire-bond-integrity-test": 1.0,
    "die-shear-test": 0.8,
    "cross-section-and-materials-review": 0.7,
    "internal-water-vapour-measurement": 0.5,
}

# Steps that reach a failure mode nothing else in the set reaches.
STRUCTURAL_STEPS = (
    "internal-visual-inspection",
    "die-metallisation-inspection",
    "wire-bond-integrity-test",
)

PACKAGE_TYPES = ("hermetic", "plastic-encapsulated")

# Steps that only have something to measure on a hermetic package.
HERMETIC_ONLY_STEPS = (
    "hermeticity-and-seal-test",
    "internal-water-vapour-measurement",
)

# Sample size each step owes at the intermediate assurance class.
STEP_MIN_SAMPLE = {
    "external-visual-inspection": 3,
    "x-ray-radiography": 3,
    "hermeticity-and-seal-test": 3,
    "internal-visual-inspection": 2,
    "die-metallisation-inspection": 2,
    "wire-bond-integrity-test": 2,
    "die-shear-test": 2,
    "cross-section-and-materials-review": 1,
    "internal-water-vapour-measurement": 2,
}

# Severity of what a step found, and the score it contributes.
OBSERVATION_SEVERITY_SCORE = {
    "no-anomaly": 0.0,
    "cosmetic-anomaly": 0.1,
    "workmanship-deviation": 0.4,
    "construction-weakness": 0.8,
    "disqualifying-defect": 1.0,
}

# Severities that make a step a weakness the report has to carry forward.
WEAKNESS_SEVERITIES = ("construction-weakness", "disqualifying-defect")

DISQUALIFYING_SEVERITY = "disqualifying-defect"

# Bounds the construction risk index is read against at Class 2.
CLASS_2_ACCEPT_INDEX = 0.10
CLASS_2_MITIGATION_INDEX = 0.30

VERDICTS = (
    "construction-acceptable",
    "construction-acceptable-with-mitigation",
    "construction-rejected",
    "constructional-analysis-incomplete",
)

# The index is a ratio of sums of weights; a value that should sit on a bound
# can land a few units in the last place away from it.
INDEX_TOLERANCE = 1e-9


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


def step_weight(name):
    """Weight of one inspection step; unknown step names are rejected."""
    if name not in STEP_WEIGHTS:
        raise ValueError(
            "unknown inspection step %r (known: %s)"
            % (name, ", ".join(sorted(STEP_WEIGHTS)))
        )
    return STEP_WEIGHTS[name]


def severity_score(severity):
    """Score one observation severity; unknown severities are rejected."""
    if severity not in OBSERVATION_SEVERITY_SCORE:
        raise ValueError(
            "unknown observation severity %r (known: %s)"
            % (severity, ", ".join(sorted(OBSERVATION_SEVERITY_SCORE)))
        )
    return OBSERVATION_SEVERITY_SCORE[severity]


def required_sample(name):
    """Sample size one step owes at the intermediate assurance class."""
    step_weight(name)  # validation only
    return STEP_MIN_SAMPLE[name]


def step_applicable(name, package_type):
    """Decide whether the package gives this step anything to measure."""
    step_weight(name)  # validation only
    if package_type not in PACKAGE_TYPES:
        raise ValueError(
            "unknown package type %r (known: %s)" % (package_type, ", ".join(PACKAGE_TYPES))
        )
    if name in HERMETIC_ONLY_STEPS:
        return package_type == "hermetic"
    return True


def sample_representative(sample_date_code, lot_date_code):
    """Decide whether the analysis sample describes the lot being bought."""
    for value, label in ((sample_date_code, "sample_date_code"), (lot_date_code, "lot_date_code")):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return sample_date_code.strip() == lot_date_code.strip()


def normalize_step(raw):
    """Validate one inspection step record and fill its defaults."""
    if not isinstance(raw, dict):
        raise ValueError("step record must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("step")
    step_weight(name)  # validation only
    performed = raw.get("performed", True)
    if not isinstance(performed, bool):
        raise ValueError("performed of %r must be a boolean, got %r" % (name, performed))
    sample_size = _count(raw.get("sample_size", 0), "sample_size")
    severity = raw.get("severity", "no-anomaly")
    severity_score(severity)  # validation only
    if not performed and sample_size > 0:
        raise ValueError(
            "step %r is not performed yet declares a sample of %d" % (name, sample_size)
        )
    if not performed and severity != "no-anomaly":
        raise ValueError(
            "step %r is not performed yet reports an observation" % (name,)
        )
    note = raw.get("note", "")
    if not isinstance(note, str):
        raise ValueError("note of %r must be a string" % (name,))
    return {
        "step": name,
        "performed": performed,
        "sample_size": sample_size,
        "severity": severity,
        "note": note,
    }


def assess_step(raw, applicable=True):
    """Grade one inspection step into a weighted severity and its findings."""
    record = normalize_step(raw)
    if not isinstance(applicable, bool):
        raise ValueError("applicable must be a boolean, got %r" % (applicable,))
    name = record["step"]
    if not applicable:
        return {
            "step": name,
            "applicable": False,
            "performed": record["performed"],
            "sample_size": record["sample_size"],
            "required_sample": required_sample(name),
            "severity": record["severity"],
            "weight": 0.0,
            "score": 0.0,
            "weighted_score": 0.0,
            "structural": name in STRUCTURAL_STEPS,
            "findings": [],
        }
    weight = step_weight(name)
    needed = required_sample(name)
    score = severity_score(record["severity"])
    findings = []
    if not record["performed"]:
        findings.append("step-not-performed")
        if name in STRUCTURAL_STEPS:
            findings.append("structural-step-not-performed")
    elif record["sample_size"] < needed:
        findings.append("step-under-sampled")
        if name in STRUCTURAL_STEPS:
            findings.append("structural-step-not-representative")
    if record["severity"] in WEAKNESS_SEVERITIES:
        findings.append(record["severity"])
    elif record["severity"] == "workmanship-deviation":
        findings.append("workmanship-deviation")
    return {
        "step": name,
        "applicable": True,
        "performed": record["performed"],
        "sample_size": record["sample_size"],
        "required_sample": needed,
        "severity": record["severity"],
        "weight": weight,
        "score": score,
        "weighted_score": weight * score,
        "structural": name in STRUCTURAL_STEPS,
        "findings": findings,
    }


def construction_risk_index(records):
    """Weighted severity of the applicable steps over their total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (type(records).__name__,))
    if len(records) == 0:
        raise ValueError("an analysis must carry at least one step")
    total_weight = 0.0
    scored = 0.0
    for record in records:
        if not record.get("applicable", True):
            continue
        total_weight += _real(record["weight"], "weight")
        scored += _real(record["weighted_score"], "weighted_score")
    if total_weight <= 0.0:
        raise ValueError("no applicable step carries any weight")
    return scored / total_weight


def index_disposition(index):
    """Read a construction risk index against the two Class 2 bounds."""
    value = _real(index, "index")
    if value < 0.0:
        raise ValueError("a construction risk index must not be negative, got %r" % (value,))
    if value <= CLASS_2_ACCEPT_INDEX + INDEX_TOLERANCE:
        return "construction-acceptable"
    if value <= CLASS_2_MITIGATION_INDEX + INDEX_TOLERANCE:
        return "construction-acceptable-with-mitigation"
    return "construction-rejected"


def assess_analysis(
    part_id,
    package_type,
    steps,
    sample_date_code,
    lot_date_code,
):
    """Grade a whole constructional analysis of one commercial part type.

    Every step the class owes is graded, including the ones the report left
    out entirely -- a step nobody mentioned was not performed, not excused --
    and excluding the ones the package gives nothing to measure.
    """
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part_id must be a non-empty string, got %r" % (part_id,))
    if package_type not in PACKAGE_TYPES:
        raise ValueError(
            "unknown package type %r (known: %s)" % (package_type, ", ".join(PACKAGE_TYPES))
        )
    if not isinstance(steps, (list, tuple)):
        raise ValueError("steps must be a list or tuple, got %r" % (type(steps).__name__,))
    declared = {}
    for raw in steps:
        record = normalize_step(raw)
        if record["step"] in declared:
            raise ValueError("duplicate inspection step %r" % (record["step"],))
        declared[record["step"]] = record
    representative = sample_representative(sample_date_code, lot_date_code)
    records = []
    for name in sorted(STEP_WEIGHTS):
        records.append(
            assess_step(
                declared.get(name, {"step": name, "performed": False}),
                applicable=step_applicable(name, package_type),
            )
        )
    index = construction_risk_index(records)
    findings = []
    for record in records:
        for finding in record["findings"]:
            findings.append({"step": record["step"], "finding": finding})
    if not representative:
        findings.append(
            {"step": "sample-provenance", "finding": "sample-not-drawn-from-procurement-lot"}
        )
    incomplete = [
        r["step"]
        for r in records
        if r["applicable"]
        and r["structural"]
        and (not r["performed"] or r["sample_size"] < r["required_sample"])
    ]
    weaknesses = sorted(
        [r for r in records if r["applicable"] and r["severity"] in WEAKNESS_SEVERITIES],
        key=lambda r: (-r["weighted_score"], r["step"]),
    )
    disqualifying = [
        r["step"]
        for r in records
        if r["applicable"] and r["severity"] == DISQUALIFYING_SEVERITY
    ]
    if incomplete or not representative:
        verdict = "constructional-analysis-incomplete"
    elif disqualifying:
        verdict = "construction-rejected"
    else:
        verdict = index_disposition(index)
        # One weakness on a light step can be averaged into an acceptable
        # index. A named construction weakness always owes a mitigation.
        if verdict == "construction-acceptable" and weaknesses:
            verdict = "construction-acceptable-with-mitigation"
    return {
        "part_id": part_id,
        "package_type": package_type,
        "records": records,
        "applicable_steps": [r["step"] for r in records if r["applicable"]],
        "inapplicable_steps": [r["step"] for r in records if not r["applicable"]],
        "sample_representative": representative,
        "construction_risk_index": index,
        "index_disposition": index_disposition(index),
        "incomplete_structural_steps": incomplete,
        "weaknesses": [r["step"] for r in weaknesses],
        "disqualifying_steps": disqualifying,
        "findings": findings,
        "verdict": verdict,
        "usable_at_class_2": verdict == "construction-acceptable" and not findings,
    }
