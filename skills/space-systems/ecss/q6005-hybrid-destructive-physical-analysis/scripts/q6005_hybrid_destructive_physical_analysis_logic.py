"""The ordered teardown that confirms the internal quality of a hybrid lot.

Anchor: ECSS-Q-ST-60-05 clause 14 (destructive physical analysis of sampled
hybrid microcircuits: how many units are drawn, in what order they are
examined, and what the measurements taken inside them have to reach).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* A destructive analysis is spent once. Everything that can be learnt without
  opening a unit is learnt first, because the lid can only come off after the
  sealed-package evidence has been taken, and a sequence that opens early has
  thrown away the hermeticity result it can never take again.
* The sample is drawn from the lot size, from a published plan, and it is
  counted up. A sample chosen for convenience measures the units that were
  easy to reach.
* A bond is graded against its own wire. The acceptance force follows the
  cross-section of the wire and the strength of its alloy, so one number
  applied to every diameter in the build passes thin wire that is about to
  fail and fails thick wire that is sound.
* A die is graded against its own area. Below a floor the attachment area is
  too small for an area rule to mean anything, so the floor governs.
* One unit failing is not the same as one measurement failing. Every
  measurement on every sample is compared, the failures are counted per unit,
  and the lot disposition follows the number of units affected.
* A sequence missing a mandatory step does not produce a failed lot, it
  produces no result: the analysis is incomplete and has to be finished
  before anything is concluded.
"""

from __future__ import annotations

import math

# The canonical order of the examination, with whether each step destroys the
# sealed package and whether it has to be performed.
DPA_STEPS = (
    ("external-visual-inspection", False, True),
    ("radiographic-inspection", False, True),
    ("particle-impact-noise-detection", False, True),
    ("fine-leak-hermeticity", False, True),
    ("gross-leak-hermeticity", False, True),
    ("residual-gas-analysis", True, False),
    ("internal-visual-inspection", True, True),
    ("bond-pull-test", True, True),
    ("die-shear-test", True, True),
    ("substrate-and-metallization-examination", True, False),
    ("cross-section-and-materials-examination", True, False),
)

STEP_ORDER = {}
STEP_IS_DESTRUCTIVE = {}
MANDATORY_STEPS = []
for _index, (_name, _destructive, _mandatory) in enumerate(DPA_STEPS):
    STEP_ORDER[_name] = _index
    STEP_IS_DESTRUCTIVE[_name] = _destructive
    if _mandatory:
        MANDATORY_STEPS.append(_name)
MANDATORY_STEPS = tuple(MANDATORY_STEPS)

# Units drawn for analysis, by the size of the lot they come from.
DPA_SAMPLE_PLAN = (
    (15, 1),
    (50, 2),
    (100, 3),
    (300, 4),
)

# Sample drawn from any lot larger than the last band.
DPA_SAMPLE_PLAN_TOP = 5

# Bond-pull acceptance: a fraction of the breaking force of the wire itself.
BOND_PULL_ACCEPTANCE_FRACTION = 0.35

# Ultimate strength of the bonding wire alloys, in megapascals.
WIRE_ALLOY_STRENGTH_MPA = {
    "aluminium-1-percent-silicon": 170.0,
    "aluminium-1-percent-magnesium": 210.0,
    "gold-99-99": 220.0,
}

# Die-shear acceptance: an area rule with a floor for very small dice.
DIE_SHEAR_STRENGTH_MPA = 6.2
DIE_SHEAR_FLOOR_N = 2.5

# Measurements taken inside an opened unit.
MEASURED_ATTRIBUTES = ("bond_pull_force_n", "die_shear_force_n")

# Units that may fail before the lot is refused.
MAX_FAILED_SAMPLES = 0

# Forces are sums of products; a case meant to sit exactly on a bound can
# land a few units in the last place away from it.
DPA_TOLERANCE = 1e-9

VERDICTS = (
    "dpa-passed",
    "dpa-passed-with-observations",
    "dpa-failed",
    "dpa-incomplete",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    """Return ``value`` as a finite positive float or raise."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _count(value, label):
    """Return ``value`` as a positive whole count or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def dpa_sample_size(lot_size):
    """Units drawn for analysis from a lot of this size."""
    size = _count(lot_size, "lot_size")
    for band, sample in DPA_SAMPLE_PLAN:
        if size <= band:
            return min(sample, size)
    return min(DPA_SAMPLE_PLAN_TOP, size)


def step_is_destructive(step):
    """True when a step opens the sealed package or consumes the unit."""
    if step not in STEP_IS_DESTRUCTIVE:
        raise ValueError(
            "unknown analysis step %r (known: %s)"
            % (step, ", ".join(name for name, _d, _m in DPA_STEPS))
        )
    return STEP_IS_DESTRUCTIVE[step]


def validate_sequence(sequence):
    """Check a proposed teardown order against the canonical one."""
    if not isinstance(sequence, (list, tuple)):
        raise ValueError("sequence must be a list or tuple, got %r" % (type(sequence).__name__,))
    if len(sequence) == 0:
        raise ValueError("an analysis must perform at least one step")
    seen = set()
    for step in sequence:
        step_is_destructive(step)  # validation only
        if step in seen:
            raise ValueError("analysis step %r is performed twice" % (step,))
        seen.add(step)

    findings = []
    out_of_order = []
    previous = -1
    for step in sequence:
        position = STEP_ORDER[step]
        if position < previous:
            out_of_order.append(step)
        previous = max(previous, position)
    if out_of_order:
        findings.append("analysis-step-performed-out-of-the-canonical-order")

    opened_at = None
    early = []
    for index, step in enumerate(sequence):
        if step_is_destructive(step) and opened_at is None:
            opened_at = index
        elif not step_is_destructive(step) and opened_at is not None:
            early.append(step)
    if early:
        findings.append("sealed-package-evidence-taken-after-the-unit-was-opened")

    missing = [step for step in MANDATORY_STEPS if step not in seen]
    if missing:
        findings.append("mandatory-analysis-step-not-performed")

    return {
        "sequence": list(sequence),
        "steps_out_of_order": out_of_order,
        "steps_after_opening": early,
        "missing_mandatory_steps": missing,
        "opened_at_index": opened_at,
        "sequence_valid": len(findings) == 0,
        "findings": findings,
    }


def minimum_bond_pull_force_n(wire_diameter_um, alloy):
    """Force a bond on this wire has to hold before it is accepted."""
    diameter = _positive(wire_diameter_um, "wire_diameter_um")
    if alloy not in WIRE_ALLOY_STRENGTH_MPA:
        raise ValueError(
            "unknown bonding wire alloy %r (known: %s)"
            % (alloy, ", ".join(sorted(WIRE_ALLOY_STRENGTH_MPA)))
        )
    radius_m = diameter * 0.5e-6
    area_m2 = math.pi * radius_m * radius_m
    breaking_force_n = WIRE_ALLOY_STRENGTH_MPA[alloy] * 1.0e6 * area_m2
    return BOND_PULL_ACCEPTANCE_FRACTION * breaking_force_n


def minimum_die_shear_force_n(die_area_mm2):
    """Force a die attachment of this area has to hold before it is accepted."""
    area = _positive(die_area_mm2, "die_area_mm2")
    by_area = DIE_SHEAR_STRENGTH_MPA * area
    if by_area < DIE_SHEAR_FLOOR_N:
        return DIE_SHEAR_FLOOR_N
    return by_area


def sample_minimums(build):
    """The acceptance forces the declared build implies."""
    if not isinstance(build, dict):
        raise ValueError("build must be a mapping, got %r" % (type(build).__name__,))
    return {
        "bond_pull_force_n": minimum_bond_pull_force_n(
            build.get("wire_diameter_um"), build.get("wire_alloy")
        ),
        "die_shear_force_n": minimum_die_shear_force_n(build.get("die_area_mm2")),
    }


def assess_sample(sample, minimums):
    """Compare one opened unit's measurements with the acceptance forces."""
    if not isinstance(sample, dict):
        raise ValueError("sample must be a mapping, got %r" % (type(sample).__name__,))
    if not isinstance(minimums, dict):
        raise ValueError("minimums must be a mapping, got %r" % (type(minimums).__name__,))
    serial = sample.get("serial")
    if not isinstance(serial, str) or not serial.strip():
        raise ValueError("every analysed unit must carry a serial, got %r" % (serial,))
    failures = []
    measured = {}
    for attribute in MEASURED_ATTRIBUTES:
        value = _positive(sample.get(attribute), attribute)
        measured[attribute] = value
        bound = _positive(minimums[attribute], "%s minimum" % attribute)
        if value < bound - DPA_TOLERANCE:
            failures.append("%s-below-the-acceptance-force" % attribute.replace("_", "-"))
    anomalies = sample.get("visual_anomalies", [])
    if not isinstance(anomalies, (list, tuple)):
        raise ValueError(
            "visual_anomalies must be a list or tuple, got %r" % (type(anomalies).__name__,)
        )
    observations = []
    for anomaly in anomalies:
        if not isinstance(anomaly, str) or not anomaly.strip():
            raise ValueError("every visual anomaly must be a non-empty string, got %r" % (anomaly,))
        observations.append(anomaly.strip())
    return {
        "serial": serial.strip(),
        "measured": measured,
        "minimums": dict(minimums),
        "failures": failures,
        "observations": observations,
        "sample_passed": len(failures) == 0,
    }


def lot_disposition(sample_records, sample_size_required):
    """Decide what the analysed units say about the lot they came from."""
    if not isinstance(sample_records, (list, tuple)):
        raise ValueError(
            "sample_records must be a list or tuple, got %r" % (type(sample_records).__name__,)
        )
    required = _count(sample_size_required, "sample_size_required")
    analysed = len(sample_records)
    failed = [record["serial"] for record in sample_records if not record["sample_passed"]]
    findings = []
    if analysed < required:
        findings.append("fewer-units-analysed-than-the-sample-plan-demands")
    if len(failed) > MAX_FAILED_SAMPLES:
        findings.append("analysed-unit-outside-the-acceptance-forces")
    return {
        "units_analysed": analysed,
        "units_required": required,
        "failed_serials": failed,
        "failed_count": len(failed),
        "sample_complete": analysed >= required,
        "lot_acceptable": len(findings) == 0,
        "findings": findings,
    }


def assess_destructive_physical_analysis(lot_id, lot_size, build, sequence, samples):
    """Grade a whole destructive physical analysis and name one verdict."""
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("lot_id must be a non-empty string, got %r" % (lot_id,))
    if not isinstance(samples, (list, tuple)):
        raise ValueError("samples must be a list or tuple, got %r" % (type(samples).__name__,))

    required = dpa_sample_size(lot_size)
    order = validate_sequence(sequence)
    minimums = sample_minimums(build)

    records = []
    seen = set()
    for sample in samples:
        record = assess_sample(sample, minimums)
        if record["serial"] in seen:
            raise ValueError("unit %r is analysed twice" % (record["serial"],))
        seen.add(record["serial"])
        records.append(record)
    disposition = lot_disposition(records, required)

    findings = []
    for finding in order["findings"]:
        findings.append({"item": "sequence", "finding": finding, "detail": lot_id})
    for record in records:
        for failure in record["failures"]:
            findings.append({"item": record["serial"], "finding": failure, "detail": lot_id})
        for observation in record["observations"]:
            findings.append(
                {
                    "item": record["serial"],
                    "finding": "visual-anomaly-recorded-on-an-analysed-unit",
                    "detail": observation,
                }
            )
    for finding in disposition["findings"]:
        if finding == "analysed-unit-outside-the-acceptance-forces":
            continue
        findings.append({"item": "sample", "finding": finding, "detail": lot_id})

    incomplete = bool(order["missing_mandatory_steps"]) or not disposition["sample_complete"]
    failed = (
        disposition["failed_count"] > MAX_FAILED_SAMPLES
        or bool(order["steps_out_of_order"])
        or bool(order["steps_after_opening"])
    )
    if incomplete:
        verdict = "dpa-incomplete"
    elif failed:
        verdict = "dpa-failed"
    elif findings:
        verdict = "dpa-passed-with-observations"
    else:
        verdict = "dpa-passed"
    return {
        "lot_id": lot_id,
        "sample_size_required": required,
        "sequence": order,
        "acceptance_forces": minimums,
        "samples": records,
        "disposition": disposition,
        "findings": findings,
        "verdict": verdict,
        "lot_released": verdict in ("dpa-passed", "dpa-passed-with-observations"),
    }
