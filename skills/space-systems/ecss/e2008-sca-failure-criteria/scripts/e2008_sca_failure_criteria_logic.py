#!/usr/bin/env python3
"""Failure criteria for a solar cell assembly under subgroup testing.

Anchor: ECSS-E-ST-20-08C clause 6.5.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A qualification or acceptance campaign does not test one solar cell
assembly, it tests subgroups of them, and the subgroup carries an
allowance for how many may fail. That allowance is only meaningful if
"failed" is decided the same way for every assembly in the subgroup,
before anyone counts.

An assembly fails when any single criterion is met. The criteria are
not weighed against one another and they do not average:

    maximum power       degradation from the pre-test value beyond the
                        declared fraction
    short-circuit       the same, against its own fraction, because a
    current             current loss points at the cell and the
                        coverglass rather than at the interconnects
    open-circuit        the same again, because a voltage loss points
    voltage             at a shunt or a cracked junction
    insulation          resistance to structure fallen below the floor
    resistance          the design depends on
    disqualifying       a defect that ends the assembly whatever the
    defect              electrical readings say

The electrical criteria are separated deliberately. A ten per cent
power loss made of current alone and one made of voltage alone are
different failures with different causes, and a single combined limit
hides whichever one the campaign was run to find.

Observed defects are grouped, not scored: an observation is either
disqualifying, acceptable, or unrecognised. An unrecognised observation
stops the judgement rather than being quietly treated as acceptable,
because the whole point of the criteria list is that nothing arrives at
the count undeclared.

The degradation limits, the insulation floor and the subgroup allowance
below are a declared policy, not a physical constant: a project
substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Defect -> the criterion it satisfies. Any of these ends the assembly.
DISQUALIFYING_DEFECTS = {
    "cell-fracture-crossing-the-junction": "cell-fracture",
    "interconnect-rupture": "interconnect-rupture",
    "coverglass-adhesive-delamination": "coverglass-delamination",
    "coverglass-loss": "coverglass-loss",
    "bus-bar-detachment": "bus-bar-detachment",
    "cell-to-substrate-debonding": "substrate-debonding",
}

# Observations that do not on their own end the assembly.
ACCEPTABLE_OBSERVATIONS = (
    "edge-chip-within-allowance",
    "coverglass-surface-mark",
    "adhesive-fillet-irregularity",
    "handling-witness-mark",
)

RECOGNISED_OBSERVATIONS = tuple(
    sorted(tuple(DISQUALIFYING_DEFECTS) + ACCEPTABLE_OBSERVATIONS)
)

MAX_POWER_CRITERION = "maximum-power-degradation-beyond-limit"
SHORT_CIRCUIT_CURRENT_CRITERION = "short-circuit-current-degradation-beyond-limit"
OPEN_CIRCUIT_VOLTAGE_CRITERION = "open-circuit-voltage-degradation-beyond-limit"
INSULATION_CRITERION = "insulation-resistance-below-floor"
DEFECT_CRITERION = "disqualifying-defect-present"

ASSEMBLY_ACCEPTED = "assembly-accepted"
ASSEMBLY_FAILED = "assembly-failed"

SUBGROUP_ACCEPTED = "subgroup-accepted"
SUBGROUP_REJECTED = "subgroup-rejected"

DEFAULT_FAILURE_POLICY = {
    "max_power_loss_fraction": 0.02,
    "max_short_circuit_current_loss_fraction": 0.02,
    "max_open_circuit_voltage_loss_fraction": 0.02,
    "min_insulation_resistance_ohm": 1.0e8,
    "allowed_failed_assemblies": 0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_whole_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a whole number of assemblies, got %r"
                         % (name, value))
    return value


def _require_fraction(name, value):
    number = _require_non_negative(name, value)
    if number > 1.0:
        raise ValueError("%s must not exceed 1, got %r" % (name, value))
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_failure_policy(policy):
    """Check a subgroup failure policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction("max_power_loss_fraction", policy.get("max_power_loss_fraction"))
    _require_fraction(
        "max_short_circuit_current_loss_fraction",
        policy.get("max_short_circuit_current_loss_fraction"),
    )
    _require_fraction(
        "max_open_circuit_voltage_loss_fraction",
        policy.get("max_open_circuit_voltage_loss_fraction"),
    )
    _require_positive(
        "min_insulation_resistance_ohm", policy.get("min_insulation_resistance_ohm")
    )
    _require_whole_count(
        "allowed_failed_assemblies", policy.get("allowed_failed_assemblies")
    )
    return policy


def relative_loss_fraction(before, after):
    """Share of a pre-test value the test took away; negative means a gain."""
    start = _require_positive("before", before)
    end = _require_non_negative("after", after)
    return (start - end) / start


def insulation_resistance_holds(resistance_ohm, policy=DEFAULT_FAILURE_POLICY):
    """True when the resistance to structure stays at or above the floor."""
    validate_failure_policy(policy)
    resistance = _require_positive("resistance_ohm", resistance_ohm)
    return _at_least(resistance, float(policy["min_insulation_resistance_ohm"]))


def categorize_observations(observations):
    """Group observations into disqualifying and acceptable, rejecting unknowns."""
    if not isinstance(observations, (list, tuple, set, frozenset)):
        raise ValueError("observations must be a collection of observation names")
    disqualifying = []
    acceptable = []
    for observation in observations:
        if observation in DISQUALIFYING_DEFECTS:
            if observation not in disqualifying:
                disqualifying.append(observation)
        elif observation in ACCEPTABLE_OBSERVATIONS:
            if observation not in acceptable:
                acceptable.append(observation)
        else:
            raise ValueError(
                "unrecognised observation %r; recognised observations are %s"
                % (observation, ", ".join(RECOGNISED_OBSERVATIONS))
            )
    return tuple(sorted(disqualifying)), tuple(sorted(acceptable))


def disqualifying_criteria(observations):
    """The criteria the disqualifying defects in an observation list satisfy."""
    disqualifying, _acceptable = categorize_observations(observations)
    return tuple(DISQUALIFYING_DEFECTS[defect] for defect in disqualifying)


def _electrical_losses(record):
    before = record.get("before")
    after = record.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValueError(
            "an assembly record needs a before and an after measurement block"
        )
    return {
        "power_loss_fraction": relative_loss_fraction(
            before.get("pmax_w"), after.get("pmax_w")
        ),
        "short_circuit_current_loss_fraction": relative_loss_fraction(
            before.get("isc_a"), after.get("isc_a")
        ),
        "open_circuit_voltage_loss_fraction": relative_loss_fraction(
            before.get("voc_v"), after.get("voc_v")
        ),
    }


def assess_cell_assembly(record, policy=DEFAULT_FAILURE_POLICY):
    """Decide whether one solar cell assembly counts as failed."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    validate_failure_policy(policy)
    identifier = record.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("an assembly record needs a non-empty id")
    if "observations" not in record:
        raise ValueError(
            "record is missing observations; an absent inspection is not a "
            "clean one"
        )

    losses = _electrical_losses(record)
    resistance = _require_positive(
        "insulation_resistance_ohm", record.get("insulation_resistance_ohm")
    )
    disqualifying, acceptable = categorize_observations(record["observations"])

    criteria = []
    if not _at_most(
        losses["power_loss_fraction"], float(policy["max_power_loss_fraction"])
    ):
        criteria.append(MAX_POWER_CRITERION)
    if not _at_most(
        losses["short_circuit_current_loss_fraction"],
        float(policy["max_short_circuit_current_loss_fraction"]),
    ):
        criteria.append(SHORT_CIRCUIT_CURRENT_CRITERION)
    if not _at_most(
        losses["open_circuit_voltage_loss_fraction"],
        float(policy["max_open_circuit_voltage_loss_fraction"]),
    ):
        criteria.append(OPEN_CIRCUIT_VOLTAGE_CRITERION)
    insulation_ok = insulation_resistance_holds(resistance, policy)
    if not insulation_ok:
        criteria.append(INSULATION_CRITERION)
    if disqualifying:
        criteria.append(DEFECT_CRITERION)

    failed = bool(criteria)
    result = dict(losses)
    result.update(
        {
            "id": identifier,
            "insulation_resistance_ohm": resistance,
            "insulation_holds": insulation_ok,
            "disqualifying_defects": disqualifying,
            "acceptable_observations": acceptable,
            "defect_criteria": disqualifying_criteria(record["observations"]),
            "criteria_met": tuple(criteria),
            "failed": failed,
            "verdict": ASSEMBLY_FAILED if failed else ASSEMBLY_ACCEPTED,
        }
    )
    return result


def assess_subgroup(records, policy=DEFAULT_FAILURE_POLICY):
    """Count the failed assemblies in a subgroup against its allowance."""
    validate_failure_policy(policy)
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of assembly records")
    if not records:
        raise ValueError("a subgroup needs at least one assembly record")

    assessed = []
    seen = []
    for record in records:
        outcome = assess_cell_assembly(record, policy)
        if outcome["id"] in seen:
            raise ValueError(
                "assembly id %r appears twice in the subgroup" % (outcome["id"],)
            )
        seen.append(outcome["id"])
        assessed.append(outcome)

    failed = tuple(
        outcome["id"] for outcome in assessed if outcome["failed"]
    )
    allowance = int(policy["allowed_failed_assemblies"])
    within = len(failed) <= allowance
    findings = []
    for outcome in assessed:
        if outcome["failed"]:
            findings.append(
                "%s met %s"
                % (outcome["id"], ", ".join(outcome["criteria_met"]))
            )
    if not within:
        findings.append(
            "%d of %d assemblies failed against an allowance of %d"
            % (len(failed), len(assessed), allowance)
        )
    return {
        "assemblies": tuple(assessed),
        "assembly_count": len(assessed),
        "failed_ids": failed,
        "failed_count": len(failed),
        "allowed_failed_assemblies": allowance,
        "within_allowance": within,
        "findings": findings,
        "verdict": SUBGROUP_ACCEPTED if within else SUBGROUP_REJECTED,
    }
