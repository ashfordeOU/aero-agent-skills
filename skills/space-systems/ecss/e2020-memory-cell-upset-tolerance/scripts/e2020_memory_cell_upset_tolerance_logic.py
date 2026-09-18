#!/usr/bin/env python3
"""A flipped bit in the housekeeping must not take the load down with it.

Anchor: ECSS-E-ST-20-20C clause 5.2.18.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A retriggerable limiter carries small pieces of state: the cell that says
whether retrigger is armed, the cell that reports what the limiter is
currently doing. Radiation flips those cells. The clause says that when
one flips, the load that was being powered stays powered.

That is a narrow statement and it is easy to widen or narrow by accident,
so the assessment below holds four lines.

The effect of an upset is a property of the design, not of the cell. Two
cells with identical upset rates matter differently: one whose flip is
read as a command to open the switch costs the load immediately, one
whose flip disarms retrigger costs the load at the next disturbance, and
one that only mis-reports costs nothing until somebody on the ground
believes it. They are grouped by that effect before anything is counted.

A mitigation has to be able to do what is claimed for it. Parity that
detects an upset and raises a flag has not restored the cell; claiming
full coverage for a detect-only mechanism is a paperwork result, and it
is refused here rather than carried into a rate.

The residual rate is what survives the mitigation, and it is a rate, so
it needs a duration before it means anything. The same cell is tolerable
on a six-month mission and not on a fifteen-year one, and the projection
is where that becomes visible.

The dominant cell is worth naming even when the total passes. A total
built from one bad cell and a dozen good ones is one change away from
being fine; a total spread evenly is not.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CELL_POPULATION_NOT_ESTABLISHED = "limiter-memory-cell-population-not-established"
LOAD_LOSS_PATH_UNMITIGATED = "memory-cell-upset-opens-the-powered-load-path"
LOAD_LOSS_RATE_EXCEEDED = "memory-cell-upset-load-loss-rate-exceeded"
UPSET_TOLERANCE_DEMONSTRATED = "limiter-memory-cell-upset-tolerance-demonstrated"

IN_SCOPE_FUNCTIONS = ("retrigger-enable", "status")
CELL_FUNCTIONS = IN_SCOPE_FUNCTIONS + ("command-latch", "housekeeping-counter")

UPSET_EFFECTS = (
    "no-output-effect",
    "load-switched-off",
    "retrigger-inhibited",
    "status-misreported",
)
LOAD_LOSING_EFFECTS = ("load-switched-off", "retrigger-inhibited")

MITIGATIONS = ("none", "parity-detect", "edac", "triple-redundant", "periodic-scrub")
DETECT_ONLY_MITIGATIONS = ("parity-detect",)

DEFAULT_UPSET_POLICY = {
    "min_mitigation_coverage": 1.0,
    "max_load_loss_events": 0.0,
    "mission_days": 5475.0,
    "dominant_share_advisory": 0.5,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_member(name, value, allowed):
    label = _require_label(name, value)
    if label not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), label)
        )
    return label


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_non_negative(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero" % name)
    return value


def _require_fraction(name, value):
    value = _require_non_negative(name, value)
    if value > 1.0:
        raise ValueError("%s must not exceed one, got %r" % (name, value))
    return value


def _at_most(value, bound):
    """value <= bound, absorbing floating-point representation error."""
    return value <= bound or math.isclose(
        value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, bound):
    """value >= bound, absorbing floating-point representation error."""
    return value >= bound or math.isclose(
        value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_upset_policy(policy):
    """Check the declared upset-tolerance policy can be assessed against."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction("min_mitigation_coverage", policy.get("min_mitigation_coverage"))
    _require_non_negative("max_load_loss_events", policy.get("max_load_loss_events"))
    _require_positive("mission_days", policy.get("mission_days"))
    share = _require_fraction(
        "dominant_share_advisory", policy.get("dominant_share_advisory")
    )
    if share <= 0.0:
        raise ValueError(
            "dominant_share_advisory of zero fires on every population and "
            "therefore says nothing"
        )
    return policy


def validate_cell_record(cell):
    """Read one memory cell, what it holds, and what a flip does to the load."""
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping, got %r" % (cell,))
    identifier = _require_label("cell id", cell.get("id"))
    if not identifier:
        raise ValueError("cell id must not be blank")
    function = _require_member(
        "function on %s" % identifier, cell.get("function"), CELL_FUNCTIONS
    )
    effect = _require_member(
        "upset_effect on %s" % identifier, cell.get("upset_effect"), UPSET_EFFECTS
    )
    rate = _require_non_negative(
        "upset_rate_per_day on %s" % identifier, cell.get("upset_rate_per_day")
    )
    mitigation = _require_member(
        "mitigation on %s" % identifier, cell.get("mitigation"), MITIGATIONS
    )
    coverage = _require_fraction(
        "mitigation_coverage on %s" % identifier, cell.get("mitigation_coverage")
    )
    if mitigation == "none" and coverage > 0.0:
        raise ValueError(
            "cell %s claims %r coverage with no mitigation behind it"
            % (identifier, coverage)
        )
    if mitigation in DETECT_ONLY_MITIGATIONS and _at_least(coverage, 1.0):
        raise ValueError(
            "cell %s claims full coverage from %s, which detects an upset "
            "without restoring the cell" % (identifier, mitigation)
        )
    return {
        "id": identifier,
        "function": function,
        "upset_effect": effect,
        "upset_rate_per_day": rate,
        "mitigation": mitigation,
        "mitigation_coverage": coverage,
    }


def cell_records(cells):
    """Read every declared memory cell, in record order."""
    if not isinstance(cells, (list, tuple)) or not cells:
        raise ValueError(
            "cells must be a non-empty sequence; upset tolerance cannot be "
            "assessed over a population nobody listed"
        )
    records = []
    seen = set()
    for cell in cells:
        record = validate_cell_record(cell)
        if record["id"] in seen:
            raise ValueError("duplicate cell id %r in the record" % record["id"])
        seen.add(record["id"])
        records.append(record)
    return tuple(records)


def group_by_scope(records):
    """Split the cells this clause speaks about from the rest.

    Command latches and housekeeping counters are outside the clause; they
    are grouped so the totals below have an honest denominator, not so they
    are judged.
    """
    in_scope = tuple(
        record for record in records if record["function"] in IN_SCOPE_FUNCTIONS
    )
    out_of_scope = tuple(
        record for record in records if record["function"] not in IN_SCOPE_FUNCTIONS
    )
    return in_scope, out_of_scope


def costs_the_load(record):
    """True when a flip of this cell takes power away from the load."""
    return record["upset_effect"] in LOAD_LOSING_EFFECTS


def load_losing_cells(records):
    """In-scope cells whose upset reaches the powered load."""
    in_scope, _ = group_by_scope(records)
    return tuple(record for record in in_scope if costs_the_load(record))


def residual_upset_rate(record):
    """Upsets per day that still reach the load after the mitigation."""
    if not costs_the_load(record):
        return 0.0
    return record["upset_rate_per_day"] * (1.0 - record["mitigation_coverage"])


def undercovered_cells(records, policy=DEFAULT_UPSET_POLICY):
    """Load-losing cells whose mitigation falls short of the declared floor."""
    validate_upset_policy(policy)
    floor = policy["min_mitigation_coverage"]
    return tuple(
        record["id"]
        for record in load_losing_cells(records)
        if not _at_least(record["mitigation_coverage"], floor)
    )


def mission_load_loss_events(records, policy=DEFAULT_UPSET_POLICY):
    """Expected load-losing upsets across the declared mission duration."""
    validate_upset_policy(policy)
    daily = sum(residual_upset_rate(record) for record in load_losing_cells(records))
    return daily * policy["mission_days"]


def dominant_cell(records):
    """The load-losing cell carrying the largest residual rate, or None."""
    scored = [
        (residual_upset_rate(record), record["id"])
        for record in load_losing_cells(records)
        if residual_upset_rate(record) > 0.0
    ]
    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], item[1]))
    return scored[0][1], scored[0][0]


def upset_advisories(records, policy=DEFAULT_UPSET_POLICY):
    """Things worth saying about a population that already meets the clause."""
    validate_upset_policy(policy)
    advisories = []
    in_scope, out_of_scope = group_by_scope(records)
    misreporting = sorted(
        record["id"]
        for record in in_scope
        if record["upset_effect"] == "status-misreported"
    )
    if misreporting:
        advisories.append(
            "status reported by %s can be wrong after an upset without the "
            "load noticing; the risk moves to whatever acts on that reading"
            % ", ".join(misreporting)
        )
    total = sum(residual_upset_rate(record) for record in load_losing_cells(records))
    dominant = dominant_cell(records)
    if dominant is not None and total > 0.0:
        share = dominant[1] / total
        if _at_least(share, policy["dominant_share_advisory"]):
            advisories.append(
                "cell %s carries %.1f%% of the residual load-losing rate; the "
                "population total is really one cell" % (dominant[0], share * 100.0)
            )
    scrubbed = sorted(
        record["id"]
        for record in load_losing_cells(records)
        if record["mitigation"] == "periodic-scrub"
    )
    if scrubbed:
        advisories.append(
            "coverage on %s comes from periodic scrubbing, so it holds only "
            "while the scrub keeps running and its interval stays below the "
            "upset spacing" % ", ".join(scrubbed)
        )
    if not out_of_scope:
        advisories.append(
            "every declared cell is a retrigger or status cell; a limiter with "
            "no state outside those two usually means the population was "
            "filtered before it was recorded"
        )
    return tuple(advisories)


def assess_memory_cell_upset_tolerance(case, policy=DEFAULT_UPSET_POLICY):
    """Full clause 5.2.18.2.1 verdict for one limiter's memory population."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_upset_policy(policy)

    findings = []
    advisories = []
    result = {
        "in_scope_cells": (),
        "out_of_scope_cells": (),
        "load_losing_cells": (),
        "undercovered_cells": (),
        "mission_load_loss_events": None,
        "dominant_cell": None,
        "dominant_residual_rate": None,
        "findings": findings,
        "advisories": advisories,
    }

    records = cell_records(case.get("cells"))
    in_scope, out_of_scope = group_by_scope(records)
    result["in_scope_cells"] = tuple(record["id"] for record in in_scope)
    result["out_of_scope_cells"] = tuple(record["id"] for record in out_of_scope)

    if not in_scope:
        findings.append(
            "no declared cell holds retrigger or status state, so the clause "
            "has not been shown to apply to this limiter"
        )
        result["verdict"] = CELL_POPULATION_NOT_ESTABLISHED
        return result

    losing = load_losing_cells(records)
    result["load_losing_cells"] = tuple(record["id"] for record in losing)

    undercovered = undercovered_cells(records, policy)
    result["undercovered_cells"] = undercovered
    if undercovered:
        for cell_id in undercovered:
            record = next(item for item in losing if item["id"] == cell_id)
            findings.append(
                "an upset of cell %s is read as %s and its %s mitigation covers "
                "%.3f of the declared floor %.3f, so a single flip reaches the "
                "powered load"
                % (
                    record["id"],
                    record["upset_effect"],
                    record["mitigation"],
                    record["mitigation_coverage"],
                    policy["min_mitigation_coverage"],
                )
            )
        result["verdict"] = LOAD_LOSS_PATH_UNMITIGATED
        return result

    events = mission_load_loss_events(records, policy)
    result["mission_load_loss_events"] = events
    dominant = dominant_cell(records)
    if dominant is not None:
        result["dominant_cell"] = dominant[0]
        result["dominant_residual_rate"] = dominant[1]

    advisories.extend(upset_advisories(records, policy))

    if not _at_most(events, policy["max_load_loss_events"]):
        findings.append(
            "the residual upset rate projects %.6f load-losing events across "
            "%.0f days against an allowance of %.6f"
            % (events, policy["mission_days"], policy["max_load_loss_events"])
        )
        result["verdict"] = LOAD_LOSS_RATE_EXCEEDED
        return result

    result["verdict"] = UPSET_TOLERANCE_DEMONSTRATED
    return result
