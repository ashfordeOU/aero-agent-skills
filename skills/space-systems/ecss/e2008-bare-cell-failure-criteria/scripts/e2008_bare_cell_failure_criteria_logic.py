#!/usr/bin/env python3
"""Conditions that mark a bare solar cell failed in subgroup testing.

Anchor: ECSS-E-ST-20-08C clause 7.6.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A subgroup of bare cells goes through a test and an inspection, and the
question afterwards is not how well the subgroup did on average but which
individual cells are now failed articles. Two independent kinds of
condition put a cell in that state:

    measured    an electrical parameter has lost more than its declared
                allowance between the before and after readings, or the
                cell has stopped conducting altogether
    observed    an inspection has found one of the conditions the test
                specification listed as disqualifying, which fails the
                cell on presence without any measurement at all

Both are checked, every mode a cell shows is named rather than the first
one found, and a cell whose after readings are missing is neither passed
nor failed -- it is not evaluated, and a subgroup carrying one cannot be
closed. An unknown reading is not a good reading.

The subgroup rollup is a separate, declared question: how many failed
cells a subgroup may carry before the subgroup itself is failed. It
never changes any individual cell's state.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MAXIMUM_POWER = "maximum-power"
SHORT_CIRCUIT_CURRENT = "short-circuit-current"
OPEN_CIRCUIT_VOLTAGE = "open-circuit-voltage"
MEASURED_PARAMETERS = (MAXIMUM_POWER, SHORT_CIRCUIT_CURRENT, OPEN_CIRCUIT_VOLTAGE)

_ALLOWANCE_KEY = {
    MAXIMUM_POWER: "max_power_loss_fraction",
    SHORT_CIRCUIT_CURRENT: "max_short_circuit_loss_fraction",
    OPEN_CIRCUIT_VOLTAGE: "max_open_circuit_voltage_loss_fraction",
}
_BEFORE_KEY = {
    MAXIMUM_POWER: "power_before_w",
    SHORT_CIRCUIT_CURRENT: "short_circuit_current_before_a",
    OPEN_CIRCUIT_VOLTAGE: "open_circuit_voltage_before_v",
}
_AFTER_KEY = {
    MAXIMUM_POWER: "power_after_w",
    SHORT_CIRCUIT_CURRENT: "short_circuit_current_after_a",
    OPEN_CIRCUIT_VOLTAGE: "open_circuit_voltage_after_v",
}

POWER_DEGRADATION = "maximum-power-degradation"
CURRENT_DEGRADATION = "short-circuit-current-degradation"
VOLTAGE_DEGRADATION = "open-circuit-voltage-degradation"
ELECTRICAL_OPEN_CIRCUIT = "electrical-open-circuit"
DISQUALIFYING_CONDITION = "disqualifying-condition-observed"

_DEGRADATION_MODE = {
    MAXIMUM_POWER: POWER_DEGRADATION,
    SHORT_CIRCUIT_CURRENT: CURRENT_DEGRADATION,
    OPEN_CIRCUIT_VOLTAGE: VOLTAGE_DEGRADATION,
}

CELL_PASSED = "bare-cell-passed"
CELL_FAILED = "bare-cell-failed"
CELL_NOT_EVALUATED = "bare-cell-not-evaluated"

REQUIREMENT_NOT_ESTABLISHED = "failure-criteria-not-established"
SUBGROUP_NOT_EVALUABLE = "subgroup-not-evaluable"
SUBGROUP_WITHIN_FAILURE_ALLOWANCE = "subgroup-within-failure-allowance"
SUBGROUP_FAILURE_ALLOWANCE_EXCEEDED = "subgroup-failure-allowance-exceeded"

DEFAULT_FAILURE_POLICY = {
    # how much of a subgroup may be failed before the subgroup is failed
    "max_failed_fraction": 0.0,
    # an after reading below this share of the before reading is an open cell
    "open_circuit_current_fraction": 0.02,
    # an apparent gain larger than this is a setup defect, not a result
    "max_credible_gain_fraction": 0.05,
    # an accepted cell using this share of its allowance is advised on
    "marginal_band_fraction": 0.90,
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


def _require_share(name, value, allow_zero=True):
    number = _require_number(name, value)
    if number < 0.0 or (number == 0.0 and not allow_zero):
        raise ValueError("%s must not be negative, got %r" % (name, value))
    if number > 1.0:
        raise ValueError(
            "%s is a share of a measured value and cannot exceed one, got %r"
            % (name, value)
        )
    return number


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    Degradation is a ratio of two measured readings, so a loss sitting
    exactly on its allowance can evaluate a few units in the last place
    above it. The allowance is never widened; only the comparison
    tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_failure_policy(policy):
    """Check the subgroup policy the cell states are rolled up under."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_share("policy max_failed_fraction", policy.get("max_failed_fraction"))
    _require_share(
        "policy open_circuit_current_fraction",
        policy.get("open_circuit_current_fraction"),
    )
    _require_share(
        "policy max_credible_gain_fraction",
        policy.get("max_credible_gain_fraction"),
    )
    _require_share(
        "policy marginal_band_fraction", policy.get("marginal_band_fraction")
    )
    return policy


def validate_failure_criteria(criteria):
    """Check the declared criteria set a cell is judged failed against."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    reference = criteria.get("criteria_reference")
    if not isinstance(reference, str):
        raise ValueError(
            "criteria_reference must be a string naming the specification that "
            "fixes these allowances, got %r" % (reference,)
        )
    allowances = {}
    for parameter in MEASURED_PARAMETERS:
        key = _ALLOWANCE_KEY[parameter]
        allowances[parameter] = _require_share(
            "criteria %s" % key, criteria.get(key), allow_zero=False
        )
    conditions = criteria.get("disqualifying_conditions")
    if not isinstance(conditions, (list, tuple)):
        raise ValueError(
            "disqualifying_conditions must be the list of observed conditions "
            "the specification declares, got %r" % (conditions,)
        )
    grouped = []
    for condition in conditions:
        if not isinstance(condition, str) or not condition.strip():
            raise ValueError(
                "each disqualifying condition must be a non-empty name, got %r"
                % (condition,)
            )
        token = condition.strip()
        if token in grouped:
            raise ValueError("disqualifying condition %r is listed twice" % (token,))
        grouped.append(token)
    return {
        "criteria_reference": reference.strip(),
        "allowances": allowances,
        "disqualifying_conditions": tuple(grouped),
    }


def degradation_fraction(before, after):
    """Share of a parameter lost between the before and after readings."""
    start = _require_positive("before reading", before)
    end = _require_number("after reading", after)
    return (start - end) / start


def validate_cell_record(cell, criteria, policy=DEFAULT_FAILURE_POLICY):
    """Read one subgroup cell record back, refusing what cannot be used."""
    validate_failure_policy(policy)
    checked = validate_failure_criteria(criteria)
    if not isinstance(cell, dict):
        raise ValueError("each cell record must be a mapping, got %r" % (cell,))
    identifier = cell.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("each cell record needs a non-empty id")
    readings = {}
    missing = []
    for parameter in MEASURED_PARAMETERS:
        before = cell.get(_BEFORE_KEY[parameter])
        after = cell.get(_AFTER_KEY[parameter])
        start = _require_positive(
            "%s %s" % (identifier, _BEFORE_KEY[parameter]), before
        )
        if after is None:
            missing.append(parameter)
            readings[parameter] = {"before": start, "after": None, "loss": None}
            continue
        end = _require_number("%s %s" % (identifier, _AFTER_KEY[parameter]), after)
        if end < 0.0:
            raise ValueError(
                "%s reports a negative %s reading of %r" % (identifier, parameter, after)
            )
        loss = degradation_fraction(start, end)
        gain = -loss
        if gain > policy["max_credible_gain_fraction"] and not math.isclose(
            gain, policy["max_credible_gain_fraction"], rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        ):
            raise ValueError(
                "%s reads %.4f higher on %s after the test than before it, past "
                "the %.4f credible band; that is a setup defect rather than a "
                "result" % (identifier, gain, parameter, policy["max_credible_gain_fraction"])
            )
        readings[parameter] = {"before": start, "after": end, "loss": loss}
    observed = cell.get("observed_conditions", [])
    if not isinstance(observed, (list, tuple)):
        raise ValueError(
            "%s observed_conditions must be a list, got %r" % (identifier, observed)
        )
    seen = []
    for condition in observed:
        if not isinstance(condition, str) or not condition.strip():
            raise ValueError(
                "%s carries an unnamed observed condition %r" % (identifier, condition)
            )
        token = condition.strip()
        if token not in checked["disqualifying_conditions"]:
            raise ValueError(
                "%s reports condition %r, which the criteria set does not list; "
                "a condition nobody declared cannot decide a cell"
                % (identifier, token)
            )
        if token not in seen:
            seen.append(token)
    return {
        "id": identifier.strip(),
        "readings": readings,
        "missing_parameters": tuple(missing),
        "observed_conditions": tuple(seen),
    }


def cell_failure_modes(cell, criteria, policy=DEFAULT_FAILURE_POLICY):
    """Every failure mode one cell shows, not only the first one found."""
    checked = validate_failure_criteria(criteria)
    record = validate_cell_record(cell, criteria, policy)
    modes = []
    findings = []
    for parameter in MEASURED_PARAMETERS:
        reading = record["readings"][parameter]
        if reading["after"] is None:
            continue
        allowance = checked["allowances"][parameter]
        if not _at_most(reading["loss"], allowance):
            modes.append(_DEGRADATION_MODE[parameter])
            findings.append(
                "%s lost %.4f of its %s against a %.4f allowance"
                % (record["id"], reading["loss"], parameter, allowance)
            )
    current = record["readings"][SHORT_CIRCUIT_CURRENT]
    if current["after"] is not None:
        floor = current["before"] * policy["open_circuit_current_fraction"]
        if _at_most(current["after"], floor):
            modes.append(ELECTRICAL_OPEN_CIRCUIT)
            findings.append(
                "%s draws %.6f A against a %.6f A floor; the cell has stopped "
                "conducting" % (record["id"], current["after"], floor)
            )
    for condition in record["observed_conditions"]:
        modes.append(DISQUALIFYING_CONDITION)
        findings.append(
            "%s shows %s, a condition the criteria set fails on presence"
            % (record["id"], condition)
        )
    return {"id": record["id"], "modes": tuple(modes), "findings": findings}


def cell_disposition(cell, criteria, policy=DEFAULT_FAILURE_POLICY):
    """State one cell is left in by the subgroup test and inspection."""
    checked = validate_failure_criteria(criteria)
    record = validate_cell_record(cell, criteria, policy)
    detected = cell_failure_modes(cell, criteria, policy)
    if detected["modes"]:
        state = CELL_FAILED
    elif record["missing_parameters"]:
        state = CELL_NOT_EVALUATED
    else:
        state = CELL_PASSED
    worst_used = 0.0
    for parameter in MEASURED_PARAMETERS:
        reading = record["readings"][parameter]
        if reading["after"] is None:
            continue
        used = reading["loss"] / checked["allowances"][parameter]
        if used > worst_used:
            worst_used = used
    return {
        "id": record["id"],
        "state": state,
        "modes": detected["modes"],
        "findings": detected["findings"],
        "missing_parameters": record["missing_parameters"],
        "observed_conditions": record["observed_conditions"],
        "losses": {
            parameter: record["readings"][parameter]["loss"]
            for parameter in MEASURED_PARAMETERS
        },
        "allowance_used_fraction": worst_used,
    }


def subgroup_dispositions(cells, criteria, policy=DEFAULT_FAILURE_POLICY):
    """State every cell in one subgroup, refusing a repeated identifier."""
    if not isinstance(cells, (list, tuple)) or not cells:
        raise ValueError(
            "a subgroup must carry at least one cell record; an empty subgroup "
            "is not a clean subgroup"
        )
    seen = set()
    dispositions = []
    for cell in cells:
        disposition = cell_disposition(cell, criteria, policy)
        if disposition["id"] in seen:
            raise ValueError("duplicate cell id %r in the subgroup" % (disposition["id"],))
        seen.add(disposition["id"])
        dispositions.append(disposition)
    return dispositions


def subgroup_failed_fraction(dispositions):
    """Share of the subgroup the criteria leave in the failed state."""
    if not dispositions:
        raise ValueError("an empty subgroup has no failed fraction")
    failed = sum(1 for item in dispositions if item["state"] == CELL_FAILED)
    return failed / float(len(dispositions))


def subgroup_within_allowance(dispositions, policy=DEFAULT_FAILURE_POLICY):
    """Whether the failed share stays inside the declared allowance."""
    validate_failure_policy(policy)
    return _at_most(
        subgroup_failed_fraction(dispositions), policy["max_failed_fraction"]
    )


def marginal_cell_advisories(dispositions, policy=DEFAULT_FAILURE_POLICY):
    """Passed cells that spent most of an allowance and kept the word pass."""
    validate_failure_policy(policy)
    advisories = []
    for item in dispositions:
        if item["state"] != CELL_PASSED:
            continue
        used = item["allowance_used_fraction"]
        if not _at_most(used, policy["marginal_band_fraction"]):
            advisories.append(
                "%s passed having spent %.4f of an allowance; the word pass "
                "hides how little is left" % (item["id"], used)
            )
    return tuple(advisories)


def assess_bare_cell_failures(case, policy=DEFAULT_FAILURE_POLICY):
    """Clause 7.6.1 failure screen over one subgroup of bare cells."""
    validate_failure_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    criteria = case.get("failure_criteria")
    cells = case.get("cells")
    if cells is None:
        raise ValueError("a subgroup case needs a cells list")
    if criteria is None:
        return {
            "verdict": REQUIREMENT_NOT_ESTABLISHED,
            "findings": [
                "no failure criteria set supplied; a cell cannot be called "
                "failed against a requirement nobody wrote down"
            ],
            "failed_cells": [],
            "not_evaluated_cells": [],
            "advisories": [],
        }
    checked = validate_failure_criteria(criteria)
    if not checked["criteria_reference"]:
        return {
            "verdict": REQUIREMENT_NOT_ESTABLISHED,
            "findings": [
                "the criteria set carries no specification reference, so no "
                "failure call made against it can be audited"
            ],
            "failed_cells": [],
            "not_evaluated_cells": [],
            "advisories": [],
        }

    dispositions = subgroup_dispositions(cells, criteria, policy)
    findings = []
    for item in dispositions:
        findings.extend(item["findings"])
    failed = [item["id"] for item in dispositions if item["state"] == CELL_FAILED]
    unevaluated = [
        item["id"] for item in dispositions if item["state"] == CELL_NOT_EVALUATED
    ]
    for item in dispositions:
        if item["state"] == CELL_NOT_EVALUATED:
            findings.append(
                "%s is missing its after reading on %s, so it is neither passed "
                "nor failed" % (item["id"], ", ".join(item["missing_parameters"]))
            )

    failed_fraction = subgroup_failed_fraction(dispositions)
    if unevaluated:
        verdict = SUBGROUP_NOT_EVALUABLE
    elif subgroup_within_allowance(dispositions, policy):
        verdict = SUBGROUP_WITHIN_FAILURE_ALLOWANCE
    else:
        verdict = SUBGROUP_FAILURE_ALLOWANCE_EXCEEDED
        findings.append(
            "%.4f of the subgroup is failed against a %.4f allowance"
            % (failed_fraction, policy["max_failed_fraction"])
        )

    return {
        "verdict": verdict,
        "criteria_reference": checked["criteria_reference"],
        "cell_count": len(dispositions),
        "dispositions": dispositions,
        "failed_cells": failed,
        "not_evaluated_cells": unevaluated,
        "failed_fraction": failed_fraction,
        "modes_seen": tuple(
            sorted({mode for item in dispositions for mode in item["modes"]})
        ),
        "findings": findings,
        "advisories": list(marginal_cell_advisories(dispositions, policy)),
    }
