#!/usr/bin/env python3
"""Retention of the cell-assembly attachment through test and mission life.

Anchor: ECSS-E-ST-20-08C clause 5.3.3.11.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Adherence measured once on an as-bonded coupon says nothing about a
panel that still has to survive humidity storage, a vibration run, a
thermal-vacuum soak and years of solar-array-thermal-cycling. The
property this clause asks for is that the cell assemblies stay attached
to the panel for the whole of that -- not that they were attached on the
day they were bonded.

The evidence is a stage-by-stage record. Every stage after the as-bonded
reference carries:

    strength              adherence measured on that stage's coupons
    detached cell count   cell assemblies that came off during the stage

From that record three separate questions get answered:

    retention   strength held against the as-bonded reference, both
                overall and step to step, so a single punishing stage
                cannot hide inside a gentle average
    detachment  any cell assembly that came off at any stage, which is
                a direct failure of the property regardless of what the
                surviving coupons measured
    life        whether the cycles actually run cover the mission cycles
                with the declared test factor, and what strength the
                extrapolation leaves at end of life

Retention floors, the per-stage drop allowance, the test factor and the
per-decade degradation are a declared project policy, not physical
constants; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REFERENCE_STAGE = "as-bonded-reference"

RECOGNIZED_STAGES = (
    REFERENCE_STAGE,
    "humidity-storage",
    "solar-array-thermal-cycling",
    "sine-and-random-vibration",
    "acoustic-noise",
    "thermal-vacuum-soak",
    "post-environment-reference",
)

ATTACHMENT_RETAINED = "attachment-retained"
ATTACHMENT_NOT_RETAINED = "attachment-not-retained"
ATTACHMENT_NOT_EVALUATED = "attachment-not-evaluated"

DEFAULT_ATTACHMENT_POLICY = {
    "min_retention_fraction": 0.70,
    "max_stage_drop_fraction": 0.20,
    "required_minimum_mpa": 0.35,
    "max_detached_cells": 0,
    "cycle_test_factor": 1.25,
    "per_decade_loss_fraction": 0.10,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_fraction(name, value):
    value = _require_non_negative(name, value)
    if value > 1.0:
        raise ValueError("%s must not exceed 1.0, got %r" % (name, value))
    return value


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a non-negative integer, got %r" % (name, value))
    return value


def _require_positive_count(name, value):
    value = _require_count(name, value)
    if value == 0:
        raise ValueError("%s must be greater than zero" % name)
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    Retention is a quotient and the end-of-life strength is a power, so
    a case meant to sit exactly on its floor can land a few units in the
    last place below it. The floor is never lowered; only the comparison
    tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_attachment_policy(policy):
    """Check a retention policy carries sane numbers before it is used."""
    _require_mapping("policy", policy)
    _require_fraction("min_retention_fraction", policy.get("min_retention_fraction"))
    _require_fraction("max_stage_drop_fraction", policy.get("max_stage_drop_fraction"))
    _require_positive("required_minimum_mpa", policy.get("required_minimum_mpa"))
    _require_count("max_detached_cells", policy.get("max_detached_cells"))
    factor = _require_positive("cycle_test_factor", policy.get("cycle_test_factor"))
    if factor < 1.0:
        raise ValueError("cycle_test_factor must be at least 1.0, got %r" % (factor,))
    loss = _require_fraction(
        "per_decade_loss_fraction", policy.get("per_decade_loss_fraction")
    )
    if loss >= 1.0:
        raise ValueError("per_decade_loss_fraction must stay below 1.0")
    return policy


def retention_fraction(stage_strength_mpa, reference_strength_mpa):
    """Share of the as-bonded strength still present at a later stage."""
    stage = _require_positive("stage_strength_mpa", stage_strength_mpa)
    reference = _require_positive("reference_strength_mpa", reference_strength_mpa)
    return stage / reference


def cycle_coverage(tested_cycles, mission_cycles, test_factor):
    """Do the cycles actually run cover the mission with the test factor."""
    tested = _require_positive_count("tested_cycles", tested_cycles)
    mission = _require_positive_count("mission_cycles", mission_cycles)
    factor = _require_positive("test_factor", test_factor)
    if factor < 1.0:
        raise ValueError("test_factor must be at least 1.0, got %r" % (factor,))
    required = mission * factor
    ratio = tested / required
    return {
        "required_cycles": required,
        "tested_cycles": float(tested),
        "coverage_ratio": ratio,
        "covered": _at_least(ratio, 1.0),
    }


def life_extrapolated_strength_mpa(
    reference_strength_mpa, tested_cycles, mission_cycles, per_decade_loss_fraction
):
    """Strength left at mission life when the test stopped short of it.

    Degradation is taken per decade of cycles beyond the tested count. A
    test that already ran past the mission leaves the measured strength
    untouched -- the extrapolation never credits a recovery.
    """
    reference = _require_positive("reference_strength_mpa", reference_strength_mpa)
    tested = _require_positive_count("tested_cycles", tested_cycles)
    mission = _require_positive_count("mission_cycles", mission_cycles)
    loss = _require_fraction("per_decade_loss_fraction", per_decade_loss_fraction)
    if loss >= 1.0:
        raise ValueError("per_decade_loss_fraction must stay below 1.0")
    if mission <= tested:
        return reference
    decades = math.log10(mission / tested)
    return reference * (1.0 - loss) ** decades


def evaluate_stage(stage, reference_strength_mpa, previous_strength_mpa, policy):
    """Sentence one environmental stage against the retention policy."""
    validate_attachment_policy(policy)
    _require_mapping("stage", stage)
    name = _require_choice("stage", stage.get("stage"), RECOGNIZED_STAGES)
    strength = _require_positive("strength_mpa", stage.get("strength_mpa"))
    detached = _require_count("detached_cell_count", stage.get("detached_cell_count", 0))
    reference = _require_positive("reference_strength_mpa", reference_strength_mpa)
    previous = _require_positive("previous_strength_mpa", previous_strength_mpa)

    retention = retention_fraction(strength, reference)
    stage_drop = max(0.0, 1.0 - strength / previous)
    reasons = []
    if not _at_most(detached, int(policy["max_detached_cells"])):
        reasons.append(
            "%d cell assembly(ies) came off during %s against an allowed %d"
            % (detached, name, int(policy["max_detached_cells"]))
        )
    if not _at_least(retention, float(policy["min_retention_fraction"])):
        reasons.append(
            "%s retained %.3f of the as-bonded strength against a floor of %.3f"
            % (name, retention, float(policy["min_retention_fraction"]))
        )
    if not _at_most(stage_drop, float(policy["max_stage_drop_fraction"])):
        reasons.append(
            "%s alone took %.3f of the strength against a per-stage allowance of %.3f"
            % (name, stage_drop, float(policy["max_stage_drop_fraction"]))
        )
    return {
        "stage": name,
        "strength_mpa": strength,
        "detached_cell_count": detached,
        "retention_fraction": retention,
        "stage_drop_fraction": stage_drop,
        "retained": not reasons,
        "findings": reasons,
    }


def evaluate_attachment_property(record, policy=DEFAULT_ATTACHMENT_POLICY):
    """Full clause 5.3.3.11.2 retention assessment with a verdict."""
    validate_attachment_policy(policy)
    _require_mapping("record", record)
    stages = record.get("stages")
    if not isinstance(stages, (list, tuple)) or not stages:
        raise ValueError("record must carry a non-empty stages sequence")

    first = _require_mapping("stages[0]", stages[0])
    if first.get("stage") != REFERENCE_STAGE:
        raise ValueError(
            "the first stage must be the %s measurement, got %r"
            % (REFERENCE_STAGE, first.get("stage"))
        )
    reference = _require_positive("reference strength_mpa", first.get("strength_mpa"))
    reference_detached = _require_count(
        "reference detached_cell_count", first.get("detached_cell_count", 0)
    )

    findings = []
    evaluated = []
    previous = reference
    for index, stage in enumerate(stages[1:], start=1):
        _require_mapping("stages[%d]" % index, stage)
        if stage.get("stage") == REFERENCE_STAGE:
            raise ValueError(
                "the as-bonded reference may only appear as the first stage"
            )
        result = evaluate_stage(stage, reference, previous, policy)
        evaluated.append(result)
        findings.extend(result["findings"])
        previous = result["strength_mpa"]

    total_detached = reference_detached + sum(
        result["detached_cell_count"] for result in evaluated
    )
    if reference_detached:
        findings.append(
            "%d cell assembly(ies) were already off at the as-bonded reference"
            % reference_detached
        )

    result = {
        "reference_strength_mpa": reference,
        "stages": evaluated,
        "total_detached_cells": total_detached,
        "findings": findings,
    }

    if not evaluated:
        result.update(
            {
                "final_strength_mpa": reference,
                "worst_retention_fraction": 1.0,
                "cycle_coverage": None,
                "life_strength_mpa": None,
                "compliant": None,
                "verdict": ATTACHMENT_NOT_EVALUATED,
            }
        )
        findings.append(
            "only the as-bonded reference was measured; the property is not "
            "demonstrated until the environmental stages are run"
        )
        return result

    final_strength = evaluated[-1]["strength_mpa"]
    worst_retention = min(entry["retention_fraction"] for entry in evaluated)

    coverage = None
    life_strength = None
    tested_cycles = record.get("tested_thermal_cycles")
    mission_cycles = record.get("mission_thermal_cycles")
    if tested_cycles is not None and mission_cycles is not None:
        coverage = cycle_coverage(
            tested_cycles, mission_cycles, float(policy["cycle_test_factor"])
        )
        life_strength = life_extrapolated_strength_mpa(
            final_strength,
            tested_cycles,
            mission_cycles,
            float(policy["per_decade_loss_fraction"]),
        )
    else:
        findings.append(
            "no tested and mission cycle counts supplied; life coverage is not "
            "demonstrated and the extrapolation is outstanding"
        )

    reasons = []
    if not _at_most(total_detached, int(policy["max_detached_cells"])):
        reasons.append(
            "%d cell assembly(ies) detached across the sequence" % total_detached
        )
    if not _at_least(worst_retention, float(policy["min_retention_fraction"])):
        reasons.append(
            "worst retention %.3f is below the floor of %.3f"
            % (worst_retention, float(policy["min_retention_fraction"]))
        )
    if any(not entry["retained"] for entry in evaluated):
        reasons.append("at least one stage failed its own retention check")
    if coverage is None:
        reasons.append("mission-life cycle coverage was never established")
    else:
        if not coverage["covered"]:
            reasons.append(
                "cycles run cover only %.3f of the mission requirement"
                % coverage["coverage_ratio"]
            )
        if not _at_least(life_strength, float(policy["required_minimum_mpa"])):
            reasons.append(
                "end-of-life strength %.4f MPa is below the required %.4f MPa"
                % (life_strength, float(policy["required_minimum_mpa"]))
            )

    compliant = not reasons
    for reason in reasons:
        if reason not in findings:
            findings.append(reason)
    result.update(
        {
            "final_strength_mpa": final_strength,
            "worst_retention_fraction": worst_retention,
            "cycle_coverage": coverage,
            "life_strength_mpa": life_strength,
            "compliant": compliant,
            "verdict": ATTACHMENT_RETAINED if compliant else ATTACHMENT_NOT_RETAINED,
        }
    )
    return result
