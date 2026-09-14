#!/usr/bin/env python3
"""Acceptance thresholds for bare cells, as fixed in the source control drawing.

Anchor: ECSS-E-ST-20-08C clause 7.3.2.2.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The criterion is narrow and worth stating exactly: a bare cell is
admissible when the currents measured on it reach the thresholds its own
source control drawing fixes. Four things follow from that sentence, and
each is a way a campaign gets it wrong.

The thresholds come from the drawing, and from the drawing that governs
this cell type. Not the cell vendor's datasheet typical, not the value
the previous programme flew, not a house minimum carried forward. A
verdict quoted with no drawing reference behind it is not a verdict
against this clause, so an unreferenced requirement closes the
assessment rather than passing it.

The judgement is per cell, not per lot average. A bare cell is an
article that will be laid down or will not, so a lot mean that clears
the threshold over a cell that does not clear it has decided nothing
about that cell. The lot-level question is a separate one -- how many
cells the delivery may lose and still be worth accepting -- and it is
answered from a declared allowance, not from arithmetic on the mean.

Both currents have to reach their threshold. A cell that clears the
short-circuit minimum and misses the on-load minimum is failing exactly
where the array design will feel it, and the short-circuit pass does
not offset it.

The sense is a floor in both cases: more current is better, so a cell
landing exactly on a threshold is admissible. The comparison tolerance
exists to absorb representation error rather than to widen the drawing.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SHORT_CIRCUIT_CURRENT = "short-circuit-current"
CURRENT_AT_TEST_VOLTAGE = "current-at-test-voltage"

REQUIREMENT_NOT_ESTABLISHED = "source-control-drawing-requirement-not-established"
LOT_REJECT_FRACTION_EXCEEDED = "lot-reject-fraction-exceeded"
LOT_MEETS_DRAWING_LIMITS = "lot-meets-drawing-limits"

DEFAULT_ACCEPTANCE_POLICY = {
    "max_reject_fraction": 0.1,
    "marginal_band_fraction": 0.02,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


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


def validate_acceptance_policy(policy):
    """Check the lot acceptance policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    reject = _require_non_negative(
        "max_reject_fraction", policy.get("max_reject_fraction")
    )
    if reject > 1.0:
        raise ValueError(
            "max_reject_fraction %g is above one; an allowance that admits a "
            "lot with no usable cell is not an acceptance policy" % reject
        )
    marginal = _require_positive(
        "marginal_band_fraction", policy.get("marginal_band_fraction")
    )
    if marginal > 1.0:
        raise ValueError(
            "marginal_band_fraction %g is above one; every accepted cell "
            "would be flagged marginal" % marginal
        )
    return policy


def validate_drawing_limits(limits):
    """Check the thresholds the source control drawing fixes can be judged against."""
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping, got %r" % (limits,))
    reference = _require_label(
        "drawing_reference", limits.get("drawing_reference")
    )
    short_circuit = _require_positive(
        "min_short_circuit_current_a", limits.get("min_short_circuit_current_a")
    )
    at_voltage = _require_positive(
        "min_current_at_test_voltage_a",
        limits.get("min_current_at_test_voltage_a"),
    )
    voltage = _require_positive("test_voltage_v", limits.get("test_voltage_v"))
    if not _at_most(at_voltage, short_circuit):
        raise ValueError(
            "the drawing asks for %g A on load against a %g A short-circuit "
            "minimum, which no cell delivers" % (at_voltage, short_circuit)
        )
    return {
        "drawing_reference": reference,
        "min_short_circuit_current_a": short_circuit,
        "min_current_at_test_voltage_a": at_voltage,
        "test_voltage_v": voltage,
    }


def validate_cell_record(cell):
    """Read one measured bare cell's two currents."""
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping, got %r" % (cell,))
    identifier = _require_label("cell id", cell.get("id"))
    if not identifier:
        raise ValueError("cell id must not be blank")
    short_circuit = _require_positive(
        "short_circuit_current_a on %s" % identifier,
        cell.get("short_circuit_current_a"),
    )
    at_voltage = _require_positive(
        "current_at_test_voltage_a on %s" % identifier,
        cell.get("current_at_test_voltage_a"),
    )
    return identifier, short_circuit, at_voltage


def margin_fraction(measured_a, required_a):
    """How far a measured current stands above its threshold, as a fraction."""
    measured = _require_positive("measured_a", measured_a)
    required = _require_positive("required_a", required_a)
    return measured / required - 1.0


def cell_verdict(cell, limits):
    """Judge one bare cell against both drawing thresholds."""
    checked = validate_drawing_limits(limits)
    identifier, short_circuit, at_voltage = validate_cell_record(cell)
    short_circuit_margin = margin_fraction(
        short_circuit, checked["min_short_circuit_current_a"]
    )
    at_voltage_margin = margin_fraction(
        at_voltage, checked["min_current_at_test_voltage_a"]
    )
    shortfalls = []
    if not _at_least(short_circuit, checked["min_short_circuit_current_a"]):
        shortfalls.append(SHORT_CIRCUIT_CURRENT)
    if not _at_least(at_voltage, checked["min_current_at_test_voltage_a"]):
        shortfalls.append(CURRENT_AT_TEST_VOLTAGE)
    return {
        "id": identifier,
        "short_circuit_margin_fraction": short_circuit_margin,
        "current_at_test_voltage_margin_fraction": at_voltage_margin,
        "limiting_margin_fraction": min(short_circuit_margin, at_voltage_margin),
        "shortfalls": tuple(shortfalls),
        "accepted": not shortfalls,
    }


def cell_verdicts(cells, limits):
    """Judge every measured bare cell, in record order."""
    if not isinstance(cells, (list, tuple)):
        raise ValueError("cells must be a sequence of measured cell records")
    if not cells:
        raise ValueError("no bare cell was measured, so there is nothing to judge")
    verdicts = []
    seen = set()
    for cell in cells:
        verdict = cell_verdict(cell, limits)
        if verdict["id"] in seen:
            raise ValueError("duplicate cell id %r in the record" % verdict["id"])
        seen.add(verdict["id"])
        verdicts.append(verdict)
    return tuple(verdicts)


def lot_reject_fraction(verdicts):
    """Share of the judged cells that missed at least one threshold."""
    if not isinstance(verdicts, (list, tuple)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    rejected = sum(1 for verdict in verdicts if not verdict["accepted"])
    return rejected / len(verdicts)


def lot_within_reject_allowance(verdicts, policy=DEFAULT_ACCEPTANCE_POLICY):
    """True when the rejected share is inside the declared lot allowance."""
    validate_acceptance_policy(policy)
    return _at_most(
        lot_reject_fraction(verdicts), float(policy["max_reject_fraction"])
    )


def weakest_cell(verdicts):
    """The judged cell with the smallest margin against either threshold."""
    if not isinstance(verdicts, (list, tuple)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    return min(verdicts, key=lambda verdict: verdict["limiting_margin_fraction"])


def marginal_cell_advisories(verdicts, policy=DEFAULT_ACCEPTANCE_POLICY):
    """Name accepted cells sitting only just above a drawing threshold.

    These do not move the verdict -- an accepted cell is accepted -- but a
    delivery that clears the drawing by a hair will not clear it again
    after any degradation, and that is worth saying once here rather than
    rediscovering it after the cells are laid down.
    """
    validate_acceptance_policy(policy)
    if not isinstance(verdicts, (list, tuple)):
        raise ValueError("verdicts must be a sequence")
    band = float(policy["marginal_band_fraction"])
    advisories = []
    for verdict in verdicts:
        if not verdict["accepted"]:
            continue
        if _at_most(verdict["limiting_margin_fraction"], band):
            advisories.append(
                "cell %s is accepted on a margin of %.3g per cent, inside the "
                "%.3g per cent marginal band; it meets the drawing today and "
                "has almost nothing left for degradation"
                % (
                    verdict["id"],
                    verdict["limiting_margin_fraction"] * 100.0,
                    band * 100.0,
                )
            )
    return tuple(advisories)


def assess_bare_cell_acceptance(case, policy=DEFAULT_ACCEPTANCE_POLICY):
    """Full clause 7.3.2.2.3 acceptance decision for one measured bare-cell lot."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_acceptance_policy(policy)

    findings = []
    advisories = []
    result = {
        "drawing_reference": None,
        "min_short_circuit_current_a": None,
        "min_current_at_test_voltage_a": None,
        "test_voltage_v": None,
        "cell_verdicts": (),
        "accepted_cells": (),
        "rejected_cells": (),
        "lot_reject_fraction": None,
        "weakest_cell_id": None,
        "weakest_cell_margin_fraction": None,
        "findings": findings,
        "advisories": advisories,
    }

    limits = case.get("drawing_limits")
    if limits is None:
        findings.append(
            "no source control drawing threshold is referenced, so there is "
            "nothing these cells can be judged against"
        )
        result["verdict"] = REQUIREMENT_NOT_ESTABLISHED
        return result
    checked = validate_drawing_limits(limits)
    result["drawing_reference"] = checked["drawing_reference"]
    result["min_short_circuit_current_a"] = checked["min_short_circuit_current_a"]
    result["min_current_at_test_voltage_a"] = checked[
        "min_current_at_test_voltage_a"
    ]
    result["test_voltage_v"] = checked["test_voltage_v"]
    if not checked["drawing_reference"]:
        findings.append(
            "the thresholds carry no drawing reference; a current minimum with "
            "no drawing behind it is not the criterion of this clause"
        )
        result["verdict"] = REQUIREMENT_NOT_ESTABLISHED
        return result

    verdicts = cell_verdicts(case.get("cells"), limits)
    result["cell_verdicts"] = verdicts
    result["accepted_cells"] = tuple(
        verdict["id"] for verdict in verdicts if verdict["accepted"]
    )
    result["rejected_cells"] = tuple(
        verdict["id"] for verdict in verdicts if not verdict["accepted"]
    )
    result["lot_reject_fraction"] = lot_reject_fraction(verdicts)

    weakest = weakest_cell(verdicts)
    result["weakest_cell_id"] = weakest["id"]
    result["weakest_cell_margin_fraction"] = weakest["limiting_margin_fraction"]

    for verdict in verdicts:
        if verdict["accepted"]:
            continue
        findings.append(
            "cell %s misses the drawing %s threshold of drawing %s, short by "
            "%.3g per cent"
            % (
                verdict["id"],
                " and ".join(verdict["shortfalls"]),
                checked["drawing_reference"],
                abs(verdict["limiting_margin_fraction"]) * 100.0,
            )
        )

    advisories.extend(marginal_cell_advisories(verdicts, policy))

    if not lot_within_reject_allowance(verdicts, policy):
        findings.append(
            "%.3g per cent of the lot misses a drawing threshold, above the "
            "%.3g per cent the acceptance policy allows"
            % (
                result["lot_reject_fraction"] * 100.0,
                float(policy["max_reject_fraction"]) * 100.0,
            )
        )
        result["verdict"] = LOT_REJECT_FRACTION_EXCEEDED
        return result

    result["verdict"] = LOT_MEETS_DRAWING_LIMITS
    return result
