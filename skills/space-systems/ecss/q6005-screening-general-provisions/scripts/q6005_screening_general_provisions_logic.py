"""Baseline provisions governing how a hybrid screening sequence is run.

Anchor: ECSS-Q-ST-60-05 clause 10.3.1 (the general provisions that sit above
the individual screening steps: how the sequence is planned, how it is
applied to the batch, how its results are recorded, and what happens when a
batch loses too many units to it).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* Screening is applied to every unit offered for delivery. A sequence run on
  a sample is a lot test wearing the wrong name, and the units it never
  touched carry none of its evidence.
* The sequence is written down and approved before it runs. A sequence agreed
  on the shop floor cannot be audited afterwards, because there is nothing to
  audit it against.
* Every step carries its reject criterion in advance. A criterion settled
  after the data is in is a decision about the batch, not a screen.
* The result is recorded per unit, not per batch. A batch-level pass hides
  which unit drifted, and the drift is the reason the screen was run.
* Units removed by screening are counted against an allowance. A batch that
  loses more than the allowance is not a good batch with some bad units in
  it; the population itself is suspect and the survivors inherit that doubt.
* Re-screening is bounded. Each pass consumes life the unit will not have in
  flight, so a batch re-screened past the limit is disqualified by the
  screening rather than saved by it.
* The provision index is weighted credit over total weight. It ranks what is
  outstanding; a missing mandatory provision, a reject rate over the
  allowance or a re-screen past the limit decides the outcome on its own, at
  any index.
"""

from __future__ import annotations

import math

# The governing provisions and the share of the argument each supplies.
SCREENING_PROVISIONS = {
    "screening-applied-to-every-delivered-unit": 1.0,
    "approved-written-screening-procedure": 1.0,
    "reject-criteria-fixed-before-the-run": 1.0,
    "per-unit-screening-data-recorded-and-retained": 1.0,
    "screening-equipment-calibration-current": 0.8,
    "rework-and-rescreen-rules-defined": 0.7,
    "screening-results-named-in-the-delivery-record": 0.6,
    "operator-qualification-recorded": 0.5,
}

# The provisions without which there is no screening programme to grade.
MANDATORY_PROVISIONS = (
    "screening-applied-to-every-delivered-unit",
    "approved-written-screening-procedure",
    "reject-criteria-fixed-before-the-run",
    "per-unit-screening-data-recorded-and-retained",
)

PROVISION_STATE_CREDIT = {
    "satisfied-and-evidenced": 1.0,
    "satisfied-not-evidenced": 0.7,
    "partially-satisfied": 0.4,
    "not-satisfied": 0.0,
}

# Share of a batch screening may remove before the population itself is
# suspect rather than merely imperfect.
DEFAULT_REJECT_ALLOWANCE = 0.10

# Passes a batch may be re-screened before the stress itself disqualifies it.
MAXIMUM_RESCREEN_CYCLES = 1

# Provision index an acceptable screening programme has to reach.
ACCEPTANCE_INDEX = 0.85

# Rates and indices are ratios of sums; a case meant to sit on a bound can
# land a few units in the last place away from it.
PROVISION_TOLERANCE = 1e-9

VERDICTS = (
    "screening-provisions-satisfied",
    "screening-provisions-satisfied-with-open-actions",
    "screening-provisions-not-satisfied",
    "batch-rejected-on-screening-yield",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _count(value, label, minimum=1):
    """Return ``value`` as a whole count at or above ``minimum`` or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (label, minimum, value))
    return value


def _fraction(value, label):
    """Return ``value`` as a finite fraction between zero and one or raise."""
    number = _real(value, label)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (label, value))
    return number


def provision_weight(name):
    """Share of the provision argument one governing provision supplies."""
    if name not in SCREENING_PROVISIONS:
        raise ValueError(
            "unknown screening provision %r (known: %s)"
            % (name, ", ".join(sorted(SCREENING_PROVISIONS)))
        )
    return SCREENING_PROVISIONS[name]


def provision_state_credit(state):
    """Credit a provision state earns."""
    if state not in PROVISION_STATE_CREDIT:
        raise ValueError(
            "unknown provision state %r (known: %s)"
            % (state, ", ".join(sorted(PROVISION_STATE_CREDIT)))
        )
    return PROVISION_STATE_CREDIT[state]


def assess_provision(name, state):
    """Grade one governing provision into a credit and its findings."""
    weight = provision_weight(name)
    credit = provision_state_credit(state)
    mandatory = name in MANDATORY_PROVISIONS
    findings = []
    if state == "not-satisfied":
        findings.append("provision-not-satisfied")
    elif state == "partially-satisfied":
        findings.append("provision-partially-satisfied")
    elif state == "satisfied-not-evidenced":
        findings.append("provision-not-evidenced")
    mandatory_missing = mandatory and state in ("not-satisfied", "partially-satisfied")
    if mandatory_missing:
        findings.append("mandatory-provision-not-satisfied")
    return {
        "provision": name,
        "state": state,
        "mandatory": mandatory,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "mandatory_missing": mandatory_missing,
        "findings": findings,
    }


def provision_index(records):
    """Weighted credit of a set of graded provisions over the total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError(
            "records must be a list or tuple, got %r" % (type(records).__name__,)
        )
    if len(records) == 0:
        raise ValueError("a screening programme must carry at least one provision")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total provision weight must be positive")
    return earned / total_weight


def batch_reject_fraction(rejected_units, batch_size):
    """Share of the batch screening removed."""
    total = _count(batch_size, "batch_size")
    rejected = _count(rejected_units, "rejected_units", minimum=0)
    if rejected > total:
        raise ValueError(
            "rejected_units (%d) exceeds the batch size (%d)" % (rejected, total)
        )
    return float(rejected) / float(total)


def batch_within_reject_allowance(rejected_units, batch_size, allowance=None):
    """True while screening removed no more of the batch than allowed.

    A batch that lands exactly on the allowance is inside it, so the
    comparison carries the tolerance rather than a bare inequality.
    """
    limit = (
        DEFAULT_REJECT_ALLOWANCE
        if allowance is None
        else _fraction(allowance, "allowance")
    )
    fraction = batch_reject_fraction(rejected_units, batch_size)
    return fraction <= limit + PROVISION_TOLERANCE


def rescreen_within_limit(cycles, limit=None):
    """True while a batch has not been re-screened past the permitted passes."""
    passes = _count(cycles, "cycles", minimum=0)
    bound = (
        MAXIMUM_RESCREEN_CYCLES
        if limit is None
        else _count(limit, "limit", minimum=0)
    )
    return passes <= bound


def surviving_units(rejected_units, batch_size):
    """Units still offered for delivery after screening removed its rejects."""
    total = _count(batch_size, "batch_size")
    rejected = _count(rejected_units, "rejected_units", minimum=0)
    if rejected > total:
        raise ValueError(
            "rejected_units (%d) exceeds the batch size (%d)" % (rejected, total)
        )
    return total - rejected


def assess_screening_provisions(
    batch_id,
    batch_size,
    rejected_units,
    rescreen_cycles=0,
    provisions=None,
    reject_allowance=None,
):
    """Grade a screening programme's governing provisions and name a verdict."""
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("batch_id must be a non-empty string, got %r" % (batch_id,))
    if provisions is None:
        provisions = {}
    if not isinstance(provisions, dict):
        raise ValueError(
            "provisions must be a mapping, got %r" % (type(provisions).__name__,)
        )
    for name in provisions:
        provision_weight(name)  # validation only

    total = _count(batch_size, "batch_size")
    fraction = batch_reject_fraction(rejected_units, total)
    within_allowance = batch_within_reject_allowance(
        rejected_units, total, reject_allowance
    )
    within_rescreen = rescreen_within_limit(rescreen_cycles)
    survivors = surviving_units(rejected_units, total)

    records = []
    for name in sorted(SCREENING_PROVISIONS):
        state = provisions.get(name, "not-satisfied")
        if not isinstance(state, str):
            raise ValueError("provision state must be a string, got %r" % (state,))
        records.append(assess_provision(name, state))
    index = provision_index(records)

    findings = []
    for record in records:
        for finding in record["findings"]:
            findings.append(
                {"item": record["provision"], "finding": finding, "detail": record["state"]}
            )
    if not within_allowance:
        findings.append(
            {
                "item": "batch-yield",
                "finding": "screening-reject-rate-over-allowance",
                "detail": "%d of %d units removed" % (rejected_units, total),
            }
        )
    if not within_rescreen:
        findings.append(
            {
                "item": "rescreen",
                "finding": "rescreen-passes-over-limit",
                "detail": "%r passes" % (rescreen_cycles,),
            }
        )
    if survivors == 0:
        findings.append(
            {
                "item": "batch-yield",
                "finding": "no-unit-survived-screening",
                "detail": "%d of %d units removed" % (rejected_units, total),
            }
        )

    mandatory_missing = any(record["mandatory_missing"] for record in records)
    if not within_allowance or not within_rescreen or survivors == 0:
        verdict = "batch-rejected-on-screening-yield"
    elif mandatory_missing or index < ACCEPTANCE_INDEX - PROVISION_TOLERANCE:
        verdict = "screening-provisions-not-satisfied"
    elif findings:
        verdict = "screening-provisions-satisfied-with-open-actions"
    else:
        verdict = "screening-provisions-satisfied"

    return {
        "batch_id": batch_id,
        "batch_size": total,
        "rejected_units": rejected_units,
        "surviving_units": survivors,
        "reject_fraction": fraction,
        "within_reject_allowance": within_allowance,
        "within_rescreen_limit": within_rescreen,
        "provision_records": records,
        "provision_index": index,
        "findings": findings,
        "verdict": verdict,
        "batch_releasable": verdict
        in (
            "screening-provisions-satisfied",
            "screening-provisions-satisfied-with-open-actions",
        ),
    }
