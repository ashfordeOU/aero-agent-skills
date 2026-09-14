#!/usr/bin/env python3
"""Blocking diode acceptance testing, general.

Anchor: ECSS-E-ST-20-08C clause 12.4.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Acceptance reaches two populations of blocking diode at once: the parts
being delivered, and the parts the qualification work consumes. The
second is the half that gets dropped, because a qualification diode is
not being shipped and acceptance reads like somebody else's obligation.

Populations
    delivery       diodes being shipped against the order
    qualification  diodes consumed by the qualification campaign

Acceptance activities split by the basis they are applied on. Every unit
carries the visual inspection, the forward voltage measurement and the
reverse leakage measurement. The thermal shock, the solderability check
and the seal leak test are drawn on a sample of the lot.

Record states, which are four different things and not two
    passed   the work ran and the unit met its limit
    failed   the work ran and the unit did not
    not-run  the work is scheduled and has not happened
    absent   there is no record at all

Absent is the worst of the four, because it cannot be dispositioned:
nobody knows whether the work was skipped, lost or never scheduled.

A sampled activity is graded over its population, on the share of that
population actually drawn. Grading it unit by unit reports nearly every
unit as missing a record it never owed; grading an every-unit activity as
a sample accepts a whole lot on a handful of inspections.

The activity split, the sampling floor, the cleared floor and the failure
policy below are declared project positions, not physical constants; a
project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

POPULATIONS = ("delivery", "qualification")

EVERY_UNIT_ACTIVITIES = (
    "visual-inspection",
    "forward-voltage-measurement",
    "reverse-leakage-measurement",
)

SAMPLED_ACTIVITIES = (
    "thermal-shock",
    "solderability",
    "seal-leak-test",
)

ACCEPTANCE_ACTIVITIES = EVERY_UNIT_ACTIVITIES + SAMPLED_ACTIVITIES

RECORD_STATES = ("passed", "failed", "not-run", "absent")

UNIT_UNDOCUMENTED = "unit-record-absent"
UNIT_UNRUN = "unit-work-not-run"
UNIT_FAILED = "unit-failed"
UNIT_CLEAR = "unit-clear"

UNIT_RANK = {
    UNIT_UNDOCUMENTED: 0,
    UNIT_UNRUN: 1,
    UNIT_FAILED: 2,
    UNIT_CLEAR: 3,
}

LOT_POPULATION_UNTOUCHED = "a-population-carries-no-acceptance"
LOT_INCOMPLETE = "acceptance-incomplete"
LOT_ACCEPTED = "both-populations-accepted"

LOT_RANK = {
    LOT_POPULATION_UNTOUCHED: 0,
    LOT_INCOMPLETE: 1,
    LOT_ACCEPTED: 2,
}

DEFAULT_ACCEPTANCE_POLICY = {
    "every_unit_activities": EVERY_UNIT_ACTIVITIES,
    "sampled_activities": SAMPLED_ACTIVITIES,
    "min_sample_share": 0.1,
    "min_cleared_share": 0.95,
    "dispositioned_failure_closes_lot": False,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


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


def _require_share(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError("%s must sit between 0 and 1, got %r" % (name, value))
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    Every share below is a quotient of counted units, so a lot drawn to
    exactly the declared fraction can land a unit in the last place under
    it. The comparison absorbs that; the floor stays as declared.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def resolve_policy(policy=None):
    """Merge a project position over the declared default."""
    settings = dict(DEFAULT_ACCEPTANCE_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    every = tuple(settings["every_unit_activities"])
    sampled = tuple(settings["sampled_activities"])
    if not every:
        raise ValueError(
            "a policy with no every-unit activities accepts a whole lot on a "
            "sample nobody agreed to substitute"
        )
    for name in every:
        _require_choice("every-unit activity", name, ACCEPTANCE_ACTIVITIES)
    for name in sampled:
        _require_choice("sampled activity", name, ACCEPTANCE_ACTIVITIES)
    overlap = sorted(set(every) & set(sampled))
    if overlap:
        raise ValueError(
            "activity %s cannot be applied on both bases at once" % overlap[0]
        )
    settings["every_unit_activities"] = every
    settings["sampled_activities"] = sampled
    settings["min_sample_share"] = _require_share(
        "min_sample_share", settings["min_sample_share"]
    )
    settings["min_cleared_share"] = _require_share(
        "min_cleared_share", settings["min_cleared_share"]
    )
    closes = settings["dispositioned_failure_closes_lot"]
    if not isinstance(closes, bool):
        raise ValueError(
            "dispositioned_failure_closes_lot must be true or false, got %r"
            % (closes,)
        )
    return settings


def grade_unit(unit, settings=None):
    """Grade one diode against the every-unit activities only.

    A unit never drawn into a sample is not missing anything, so the
    sampled activities take no part in this verdict.
    """
    config = settings if settings is not None else resolve_policy()
    _require_mapping("unit", unit)
    unit_id = _require_label("unit_id", unit.get("unit_id"))
    population = _require_choice(
        "population", unit.get("population"), POPULATIONS
    )
    records = _require_mapping("records", unit.get("records"))

    states = {}
    for activity, state in records.items():
        name = _require_choice("activity", activity, ACCEPTANCE_ACTIVITIES)
        states[name] = _require_choice("record state", state, RECORD_STATES)

    absent = []
    not_run = []
    failed = []
    passed = []
    for activity in config["every_unit_activities"]:
        state = states.get(activity, "absent")
        if state == "absent":
            absent.append(activity)
        elif state == "not-run":
            not_run.append(activity)
        elif state == "failed":
            failed.append(activity)
        else:
            passed.append(activity)

    if absent:
        verdict = UNIT_UNDOCUMENTED
    elif not_run:
        verdict = UNIT_UNRUN
    elif failed:
        verdict = UNIT_FAILED
    else:
        verdict = UNIT_CLEAR

    return {
        "unit_id": unit_id,
        "population": population,
        "absent": sorted(absent),
        "not_run": sorted(not_run),
        "failed": sorted(failed),
        "passed": sorted(passed),
        "drawn_for": sorted(
            a for a in config["sampled_activities"] if a in states
        ),
        "sampled_failures": sorted(
            a
            for a in config["sampled_activities"]
            if states.get(a) == "failed"
        ),
        "verdict": verdict,
    }


def sampled_activity_coverage(graded, activity, population, min_share):
    """Grade one sampled activity over the population it speaks for."""
    _require_choice("activity", activity, ACCEPTANCE_ACTIVITIES)
    _require_choice("population", population, POPULATIONS)
    floor = _require_share("min_sample_share", min_share)
    members = [row for row in graded if row["population"] == population]
    if not members:
        raise ValueError(
            "population %r holds no units, so a sampled activity has nothing "
            "to speak for" % population
        )
    drawn = [row for row in members if activity in row["drawn_for"]]
    failures = [row for row in members if activity in row["sampled_failures"]]
    share = len(drawn) / len(members)
    return {
        "activity": activity,
        "population": population,
        "population_size": len(members),
        "drawn": len(drawn),
        "drawn_share": share,
        "share_floor_met": _at_least(share, floor),
        "failed_units": sorted(row["unit_id"] for row in failures),
    }


def population_summary(graded, population, settings):
    """Roll one population up: cleared share, sampled results, reach."""
    _require_choice("population", population, POPULATIONS)
    members = [row for row in graded if row["population"] == population]
    if not members:
        return {
            "population": population,
            "present": False,
            "units": 0,
            "cleared": 0,
            "cleared_share": 0.0,
            "cleared_floor_met": False,
            "wholly_untouched": False,
            "sampled": [],
            "weakest": None,
        }
    cleared = [row for row in members if row["verdict"] == UNIT_CLEAR]
    share = len(cleared) / len(members)
    touched = [
        row
        for row in members
        if row["passed"] or row["failed"] or row["not_run"] or row["drawn_for"]
    ]
    sampled = [
        sampled_activity_coverage(
            graded, activity, population, settings["min_sample_share"]
        )
        for activity in settings["sampled_activities"]
    ]
    weakest = min(members, key=lambda row: (UNIT_RANK[row["verdict"]], row["unit_id"]))
    return {
        "population": population,
        "present": True,
        "units": len(members),
        "cleared": len(cleared),
        "cleared_share": share,
        "cleared_floor_met": _at_least(share, settings["min_cleared_share"]),
        "wholly_untouched": not touched,
        "sampled": sampled,
        "weakest": weakest["unit_id"],
    }


def population_reach(graded):
    """Name the populations present, absent and present but untouched."""
    present = sorted({row["population"] for row in graded})
    absent = [name for name in POPULATIONS if name not in present]
    untouched = []
    for name in present:
        members = [row for row in graded if row["population"] == name]
        if all(
            not row["passed"]
            and not row["failed"]
            and not row["not_run"]
            and not row["drawn_for"]
            for row in members
        ):
            untouched.append(name)
    return {
        "present": present,
        "absent": absent,
        "untouched": sorted(untouched),
        "both_reached": not absent and not untouched,
    }


def assess_blocking_diode_acceptance(lot):
    """Full clause 12.4.1 review of one blocking diode lot record."""
    _require_mapping("lot", lot)
    lot_id = _require_label("lot_id", lot.get("lot_id"))
    settings = resolve_policy(lot.get("policy"))

    units = lot.get("units")
    if not isinstance(units, (list, tuple)) or not units:
        raise ValueError("lot must carry a non-empty units sequence")

    graded = []
    seen = []
    for unit in units:
        row = grade_unit(unit, settings)
        if row["unit_id"] in seen:
            raise ValueError("unit %r appears twice in the lot" % row["unit_id"])
        seen.append(row["unit_id"])
        graded.append(row)

    reach = population_reach(graded)
    summaries = [
        population_summary(graded, name, settings) for name in POPULATIONS
    ]

    findings = []
    for name in reach["absent"]:
        findings.append(
            "%s: the %s population is absent from the lot record, so the clause "
            "reaches only half the diodes it owes" % (lot_id, name)
        )
    for name in reach["untouched"]:
        findings.append(
            "%s: every diode in the %s population carries an empty acceptance "
            "record, which is a decision and not a paperwork gap" % (lot_id, name)
        )
    for row in sorted(graded, key=lambda r: (UNIT_RANK[r["verdict"]], r["unit_id"])):
        if row["verdict"] == UNIT_UNDOCUMENTED:
            findings.append(
                "%s: diode %s has no record for %s, so it cannot be "
                "dispositioned" % (lot_id, row["unit_id"], ", ".join(row["absent"]))
            )
        elif row["verdict"] == UNIT_UNRUN:
            findings.append(
                "%s: diode %s still owes %s"
                % (lot_id, row["unit_id"], ", ".join(row["not_run"]))
            )
        elif row["verdict"] == UNIT_FAILED:
            findings.append(
                "%s: diode %s failed %s"
                % (lot_id, row["unit_id"], ", ".join(row["failed"]))
            )
    for summary in summaries:
        if not summary["present"]:
            continue
        for sample in summary["sampled"]:
            if not sample["share_floor_met"]:
                findings.append(
                    "%s: %s reached %.4g of the %s population against a %.4g "
                    "floor"
                    % (
                        lot_id,
                        sample["activity"],
                        sample["drawn_share"],
                        sample["population"],
                        settings["min_sample_share"],
                    )
                )
            for unit_id in sample["failed_units"]:
                findings.append(
                    "%s: %s failed on %s, and the sample speaks for the whole "
                    "%s population"
                    % (lot_id, sample["activity"], unit_id, sample["population"])
                )

    failures = [row for row in graded if row["verdict"] == UNIT_FAILED]
    blocked = [
        row
        for row in graded
        if row["verdict"] in (UNIT_UNDOCUMENTED, UNIT_UNRUN)
    ]
    sample_short = any(
        not sample["share_floor_met"]
        for summary in summaries
        if summary["present"]
        for sample in summary["sampled"]
    )
    sample_failed = any(
        sample["failed_units"]
        for summary in summaries
        if summary["present"]
        for sample in summary["sampled"]
    )
    cleared_short = any(
        not summary["cleared_floor_met"] for summary in summaries if summary["present"]
    )

    if cleared_short:
        for summary in summaries:
            if summary["present"] and not summary["cleared_floor_met"]:
                findings.append(
                    "%s: %.4g of the %s population is clear against a %.4g "
                    "floor"
                    % (
                        lot_id,
                        summary["cleared_share"],
                        summary["population"],
                        settings["min_cleared_share"],
                    )
                )

    if reach["absent"] or reach["untouched"]:
        verdict = LOT_POPULATION_UNTOUCHED
    elif blocked or sample_short or sample_failed:
        verdict = LOT_INCOMPLETE
    elif failures and settings["dispositioned_failure_closes_lot"]:
        verdict = LOT_INCOMPLETE
    elif cleared_short:
        verdict = LOT_INCOMPLETE
    else:
        verdict = LOT_ACCEPTED

    return {
        "lot_id": lot_id,
        "units": graded,
        "reach": reach,
        "populations": summaries,
        "verdict": verdict,
        "findings": findings,
    }
