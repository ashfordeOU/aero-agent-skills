#!/usr/bin/env python3
"""Link performance under failure modes, ECSS-E-ST-50C clause 5.6.11.4.

Paraphrased requirement, no standard text reproduced. The clause carries one
obligation: the communications link performance requirements are stated for,
and have to hold in, the failure modes declared for the mission - not only in
the undegraded nominal case.

Two things follow that implementations lose. First, a declared failure mode
that no performance figure covers is not a passing mode, it is an unassessed
one, and silence in the budget is not evidence of compliance. Second, the
governing case is whichever mode leaves the least margin, which is rarely the
mode with the largest single degradation once concurrent contributors are
added up.

This module models a failure mode as a named set of decibel degradation
contributors plus the direction of the link it touches and whether redundancy
recovers it. It sums the contributors in a deterministic order, subtracts them
from the nominal margin, grades every mode against the required margin, names
the governing mode and reports every declared mode the budget never covered.

All margin arithmetic is decibel addition and subtraction of IEEE doubles,
which is correctly rounded and therefore identical on every host; no power of
ten and no logarithm is taken, and the compliance comparison carries an
explicit tolerance so a mode that lands exactly on the required margin is
graded the same way everywhere.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# A margin that lands on the requirement counts as met. Decibel sums are
# exact-rounded but a contributor list can still land a unit in the last
# place away from the bound, so the comparison carries a tolerance rather
# than relying on a strict inequality.
MARGIN_TOLERANCE_DB = 1e-9

UPLINK = "uplink"
DOWNLINK = "downlink"
BOTH = "both"
DIRECTIONS = (UPLINK, DOWNLINK, BOTH)

NOMINAL_MODE = "nominal"

MET = "met"
NOT_MET = "not-met"
UNASSESSED = "unassessed"


def validate_decibels(value, name):
    """Return value as a finite float decibel figure, refusing junk."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number of decibels, got %r" % (name, value))
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return result


def validate_direction(direction):
    """Return the link direction, refusing anything outside the three."""
    if not isinstance(direction, str):
        raise ValueError("direction must be text, got %r" % (direction,))
    token = direction.strip().lower()
    if token not in DIRECTIONS:
        raise ValueError(
            "direction must be one of %s, got %r" % (", ".join(DIRECTIONS), direction)
        )
    return token


def validate_mode(mode):
    """Return one failure mode in a normal form, refusing a malformed one."""
    if not isinstance(mode, dict):
        raise ValueError("a failure mode must be a mapping, got %r" % (mode,))
    name = mode.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("a failure mode needs a non-empty name, got %r" % (name,))
    contributors = mode.get("degradations_db", {})
    if not isinstance(contributors, dict):
        raise ValueError(
            "degradations_db for %r must map a contributor to decibels" % name
        )
    cleaned = {}
    for key in sorted(contributors):
        if not isinstance(key, str) or not key.strip():
            raise ValueError("a degradation contributor in %r needs a name" % name)
        amount = validate_decibels(contributors[key], "degradation %s/%s" % (name, key))
        if amount < 0.0:
            raise ValueError(
                "degradation %s/%s must not be negative, got %r" % (name, key, amount)
            )
        cleaned[key.strip()] = amount
    recovered = mode.get("recovered_by_redundancy", False)
    if not isinstance(recovered, bool):
        raise ValueError("recovered_by_redundancy for %r must be true or false" % name)
    return {
        "name": name.strip(),
        "degradations_db": cleaned,
        "direction": validate_direction(mode.get("direction", BOTH)),
        "recovered_by_redundancy": recovered,
    }


def normalise_modes(modes):
    """Return the declared modes in name order, refusing a duplicate name."""
    if not isinstance(modes, (list, tuple)):
        raise ValueError("modes must be a sequence of failure modes")
    seen = {}
    for mode in modes:
        clean = validate_mode(mode)
        if clean["name"] in seen:
            raise ValueError("failure mode %r is declared twice" % clean["name"])
        seen[clean["name"]] = clean
    return tuple(seen[name] for name in sorted(seen))


def total_degradation_db(mode):
    """Sum one mode's concurrent contributors in a deterministic order."""
    clean = validate_mode(mode)
    total = 0.0
    for key in sorted(clean["degradations_db"]):
        total += clean["degradations_db"][key]
    return total


def mode_margin_db(nominal_margin_db, mode):
    """Margin left in one failure mode, nominal margin less its degradations."""
    nominal = validate_decibels(nominal_margin_db, "nominal_margin_db")
    return nominal - total_degradation_db(mode)


def mode_applies(mode, direction):
    """True when a mode touches the link direction being graded."""
    clean = validate_mode(mode)
    wanted = validate_direction(direction)
    if wanted == BOTH or clean["direction"] == BOTH:
        return True
    return clean["direction"] == wanted


def margin_meets(margin_db, required_margin_db):
    """True when a margin reaches the requirement, bound inclusive."""
    margin = validate_decibels(margin_db, "margin_db")
    required = validate_decibels(required_margin_db, "required_margin_db")
    return margin >= required - MARGIN_TOLERANCE_DB


def uncovered_modes(declared_modes, required_mode_names):
    """Name every mode the mission requires that the budget never covered."""
    if not isinstance(required_mode_names, (list, tuple, set, frozenset)):
        raise ValueError("required_mode_names must be a collection of names")
    covered = {mode["name"] for mode in normalise_modes(declared_modes)}
    missing = []
    for name in required_mode_names:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("a required mode name must be non-empty text")
        if name.strip() not in covered:
            missing.append(name.strip())
    return tuple(sorted(set(missing)))


def governing_mode(nominal_margin_db, modes, direction=BOTH):
    """Name the applicable mode that leaves the least margin, ties by name."""
    applicable = [m for m in normalise_modes(modes) if mode_applies(m, direction)]
    if not applicable:
        return None
    best_name = None
    best_margin = None
    for mode in applicable:
        margin = mode_margin_db(nominal_margin_db, mode)
        if best_margin is None or margin < best_margin - MARGIN_TOLERANCE_DB:
            best_name, best_margin = mode["name"], margin
    return best_name


def assess_failure_mode_performance(
    nominal_margin_db,
    required_margin_db,
    modes,
    required_mode_names=(),
    direction=BOTH,
):
    """Grade the declared link performance against clause 5.6.11.4."""
    nominal = validate_decibels(nominal_margin_db, "nominal_margin_db")
    required = validate_decibels(required_margin_db, "required_margin_db")
    wanted = validate_direction(direction)
    declared = normalise_modes(modes)

    per_mode = []
    failing = []
    for mode in declared:
        applies = mode_applies(mode, wanted)
        margin = mode_margin_db(nominal, mode)
        met = margin_meets(margin, required)
        per_mode.append(
            {
                "name": mode["name"],
                "applies": applies,
                "degradation_db": total_degradation_db(mode),
                "margin_db": margin,
                "recovered_by_redundancy": mode["recovered_by_redundancy"],
                "grade": MET if met else NOT_MET,
            }
        )
        if applies and not met:
            failing.append(mode["name"])

    missing = uncovered_modes(declared, required_mode_names)
    governing = governing_mode(nominal, declared, wanted) if declared else None
    nominal_met = margin_meets(nominal, required)

    if missing:
        verdict = UNASSESSED
    elif failing or not nominal_met:
        verdict = NOT_MET
    else:
        verdict = MET

    return {
        "verdict": verdict,
        "compliant": verdict == MET,
        "direction": wanted,
        "nominal_margin_db": nominal,
        "required_margin_db": required,
        "nominal_mode_grade": MET if nominal_met else NOT_MET,
        "modes": tuple(per_mode),
        "governing_mode": governing,
        "failing_modes": tuple(sorted(failing)),
        "uncovered_required_modes": missing,
        "finding": (
            "every required failure mode is covered and meets the margin"
            if verdict == MET
            else "required failure modes are not covered by the budget"
            if verdict == UNASSESSED
            else "at least one applicable failure mode falls short of the margin"
        ),
    }
