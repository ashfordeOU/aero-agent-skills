"""The ordered screening sequence every unit of a hybrid production batch runs.

Anchor: ECSS-Q-ST-60-05 clause 10.3 (the ordered set of stress and inspection
steps applied to every delivered unit of a production batch, as opposed to
the sample tests that speak only for the lot they were drawn from).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* Screening is a sequence, not a checklist. Each step is designed to precipitate
  a defect that the step after it can see, so a step performed in the wrong
  place still costs money and buys much less than its position on the plan
  suggests.
* The sealing operation splits the sequence in two. Everything that needs the
  package open has to happen before it, and everything that tests the closed
  package has to happen after it. A step on the wrong side of the seal is not
  merely misordered: it could not have been performed as written.
* Screening applies to every unit of the batch. A step run on part of the
  batch leaves the rest of the batch unscreened for the defect that step
  catches, whatever the yield on the units that did see it.
* A few steps are what screening exists for, and an absent one leaves the
  sequence incomplete rather than merely weaker, because no other step
  answers the question it answers.
* An inversion is read on both steps it involves, because neither of them ran
  where the sequence intended and the evidence from both is weakened.
* The sequence-conformity index is weighted credit over total weight. It
  ranks what is outstanding; a stage violation, a missing mandatory step or a
  batch a step never covered decides the outcome on its own, at any index.
"""

from __future__ import annotations

import math

# Where each screening step sits relative to the sealing operation.
PRE_SEAL_STAGE = "pre-seal"
SEAL_STAGE = "seal"
POST_SEAL_STAGE = "post-seal"

SEALING_STEP = "hybrid-package-sealing"

# The canonical sequence: the position each step is designed to occupy, the
# stage it belongs to, and the share of the screening argument it supplies.
SCREENING_STEPS = {
    "pre-seal-internal-visual-inspection": (10, PRE_SEAL_STAGE, 1.0),
    "pre-seal-thermographic-imaging": (20, PRE_SEAL_STAGE, 0.7),
    "pre-seal-burn-in-soak": (30, PRE_SEAL_STAGE, 0.9),
    "post-burn-in-internal-visual-inspection": (40, PRE_SEAL_STAGE, 0.8),
    "internal-circuit-photographic-record": (50, PRE_SEAL_STAGE, 0.6),
    SEALING_STEP: (60, SEAL_STAGE, 1.0),
    "post-seal-stabilization-bake": (70, POST_SEAL_STAGE, 0.6),
    "hybrid-package-thermal-cycling": (80, POST_SEAL_STAGE, 1.0),
    "hybrid-constant-acceleration-screen": (90, POST_SEAL_STAGE, 0.7),
    "post-seal-burn-in-screen": (100, POST_SEAL_STAGE, 1.0),
    "hybrid-seal-fine-and-gross-leak-test": (110, POST_SEAL_STAGE, 1.0),
    "final-electrical-measurement": (120, POST_SEAL_STAGE, 1.0),
    "hybrid-radiographic-inspection": (130, POST_SEAL_STAGE, 0.7),
    "post-seal-external-visual-inspection": (140, POST_SEAL_STAGE, 0.8),
}

# The steps the sequence exists for; without one it is incomplete.
MANDATORY_SCREENING_STEPS = (
    "pre-seal-internal-visual-inspection",
    SEALING_STEP,
    "hybrid-package-thermal-cycling",
    "post-seal-burn-in-screen",
    "hybrid-seal-fine-and-gross-leak-test",
    "final-electrical-measurement",
    "post-seal-external-visual-inspection",
)

STEP_OUTCOME_CREDIT = {
    "performed-in-order": 1.0,
    "performed-out-of-order": 0.4,
    "performed-on-part-of-batch": 0.2,
    "performed-on-the-wrong-side-of-the-seal": 0.0,
    "not-performed": 0.0,
}

# Sequence-conformity index an acceptable screening run has to reach.
ACCEPTANCE_INDEX = 0.90

# Indices are ratios of sums of weights; a case meant to sit on a bound can
# land a few units in the last place away from it.
SCREENING_TOLERANCE = 1e-9

VERDICTS = (
    "screening-sequence-accepted",
    "screening-sequence-accepted-with-open-actions",
    "screening-sequence-not-accepted",
    "screening-sequence-incomplete",
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


def canonical_position(step):
    """Position a screening step is designed to occupy; unknown steps raise."""
    if step not in SCREENING_STEPS:
        raise ValueError(
            "unknown screening step %r (known: %s)"
            % (step, ", ".join(sorted(SCREENING_STEPS)))
        )
    return SCREENING_STEPS[step][0]


def step_stage(step):
    """Whether a step needs the package open, closes it, or tests it closed."""
    canonical_position(step)  # validation only
    return SCREENING_STEPS[step][1]


def step_weight(step):
    """Share of the screening argument one step supplies."""
    canonical_position(step)  # validation only
    return SCREENING_STEPS[step][2]


def outcome_credit(outcome):
    """Credit a screening-step outcome earns."""
    if outcome not in STEP_OUTCOME_CREDIT:
        raise ValueError(
            "unknown step outcome %r (known: %s)"
            % (outcome, ", ".join(sorted(STEP_OUTCOME_CREDIT)))
        )
    return STEP_OUTCOME_CREDIT[outcome]


def canonical_sequence():
    """Every screening step in the position the sequence intends for it."""
    return tuple(sorted(SCREENING_STEPS, key=canonical_position))


def normalize_sequence(sequence):
    """Validate a performed sequence and reject a step listed twice."""
    if not isinstance(sequence, (list, tuple)):
        raise ValueError(
            "sequence must be a list or tuple, got %r" % (type(sequence).__name__,)
        )
    if len(sequence) == 0:
        raise ValueError("a screening sequence must carry at least one step")
    seen = set()
    normalized = []
    for raw in sequence:
        if isinstance(raw, str):
            raw = {"step": raw}
        if not isinstance(raw, dict):
            raise ValueError("step must be a mapping or a name, got %r" % (type(raw).__name__,))
        name = raw.get("step")
        canonical_position(name)  # validation only
        if name in seen:
            raise ValueError("duplicate screening step %r" % (name,))
        seen.add(name)
        units = raw.get("applied_units")
        if units is not None:
            _count(units, "applied_units")
        normalized.append({"step": name, "applied_units": units})
    return normalized


def inverted_steps(sequence):
    """Steps that did not run where the canonical sequence intends them.

    A step is inverted when some step performed before it belongs later, or
    some step performed after it belongs earlier. Both members of a swap are
    named, because neither ran where the sequence intended.
    """
    names = [record["step"] for record in normalize_sequence(sequence)]
    positions = [canonical_position(name) for name in names]
    inverted = set()
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if positions[i] > positions[j]:
                inverted.add(names[i])
                inverted.add(names[j])
    return sorted(inverted)


def stage_violations(sequence):
    """Steps performed on the wrong side of the sealing operation."""
    names = [record["step"] for record in normalize_sequence(sequence)]
    if SEALING_STEP not in names:
        return []
    seal_index = names.index(SEALING_STEP)
    violations = []
    for index, name in enumerate(names):
        stage = SCREENING_STEPS[name][1]
        if stage == PRE_SEAL_STAGE and index > seal_index:
            violations.append(name)
        elif stage == POST_SEAL_STAGE and index < seal_index:
            violations.append(name)
    return sorted(violations)


def missing_mandatory_steps(sequence):
    """Mandatory steps the performed sequence never ran."""
    names = {record["step"] for record in normalize_sequence(sequence)}
    return sorted(name for name in MANDATORY_SCREENING_STEPS if name not in names)


def batch_coverage_shortfalls(sequence, batch_size):
    """Steps applied to fewer than every unit of the batch.

    A step with no unit count declared is read as applied to the whole batch,
    which is the only reading that does not invent evidence; a count above
    the batch size is an input error rather than a generous step.
    """
    total = _count(batch_size, "batch_size")
    short = []
    for record in normalize_sequence(sequence):
        units = record["applied_units"]
        if units is None:
            continue
        if units > total:
            raise ValueError(
                "step %r reports %d units against a batch of %d"
                % (record["step"], units, total)
            )
        if units < total:
            short.append(record["step"])
    return sorted(short)


def grade_step(step, inverted, violating, short_covered, performed):
    """Turn one step's condition into an outcome, a credit and its findings."""
    canonical_position(step)  # validation only
    weight = step_weight(step)
    if not performed:
        outcome = "not-performed"
    elif violating:
        outcome = "performed-on-the-wrong-side-of-the-seal"
    elif short_covered:
        outcome = "performed-on-part-of-batch"
    elif inverted:
        outcome = "performed-out-of-order"
    else:
        outcome = "performed-in-order"
    credit = outcome_credit(outcome)
    findings = [] if outcome == "performed-in-order" else [outcome]
    mandatory_missing = step in MANDATORY_SCREENING_STEPS and not performed
    if mandatory_missing:
        findings.append("mandatory-screening-step-not-performed")
    return {
        "step": step,
        "stage": SCREENING_STEPS[step][1],
        "outcome": outcome,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "mandatory_missing": mandatory_missing,
        "findings": findings,
    }


def sequence_conformity_index(records):
    """Weighted credit of a set of graded screening steps over total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError(
            "records must be a list or tuple, got %r" % (type(records).__name__,)
        )
    if len(records) == 0:
        raise ValueError("a screening run must carry at least one step")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total screening weight must be positive")
    return earned / total_weight


def assess_screening_sequence(batch_id, batch_size, sequence):
    """Grade a whole performed screening sequence and name a single verdict."""
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("batch_id must be a non-empty string, got %r" % (batch_id,))
    total = _count(batch_size, "batch_size")
    normalized = normalize_sequence(sequence)

    performed = {record["step"] for record in normalized}
    inverted = set(inverted_steps(normalized))
    violating = set(stage_violations(normalized))
    short = set(batch_coverage_shortfalls(normalized, total))
    missing = missing_mandatory_steps(normalized)

    step_records = []
    for step in canonical_sequence():
        step_records.append(
            grade_step(
                step,
                inverted=step in inverted,
                violating=step in violating,
                short_covered=step in short,
                performed=step in performed,
            )
        )
    index = sequence_conformity_index(step_records)

    findings = []
    for record in step_records:
        for finding in record["findings"]:
            findings.append(
                {"item": record["step"], "finding": finding, "detail": record["stage"]}
            )

    incomplete = bool(missing)
    blocked = bool(violating) or bool(short)
    if incomplete:
        verdict = "screening-sequence-incomplete"
    elif blocked or index < ACCEPTANCE_INDEX - SCREENING_TOLERANCE:
        verdict = "screening-sequence-not-accepted"
    elif findings:
        verdict = "screening-sequence-accepted-with-open-actions"
    else:
        verdict = "screening-sequence-accepted"

    return {
        "batch_id": batch_id,
        "batch_size": total,
        "performed_step_count": len(normalized),
        "inverted_steps": sorted(inverted),
        "stage_violations": sorted(violating),
        "coverage_shortfalls": sorted(short),
        "missing_mandatory_steps": missing,
        "step_records": step_records,
        "sequence_conformity_index": index,
        "findings": findings,
        "verdict": verdict,
        "sequence_accepted": verdict
        in (
            "screening-sequence-accepted",
            "screening-sequence-accepted-with-open-actions",
        ),
    }
