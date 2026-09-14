#!/usr/bin/env python3
"""Acceptance testing of bare solar cells, both populations.

Anchor: ECSS-E-ST-20-08C clause 7.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Acceptance reaches two populations of bare cells, not one: the cells
being delivered, and the cells the qualification campaign consumes. The
second is the one that gets dropped, because a qualification cell is not
being shipped and acceptance looks like somebody else's obligation. It
is the reverse -- a qualification result only means something if the
cell it was produced on was itself a sound cell.

Bare cells also differ from assemblies in how the work is applied. Some
acceptance activities are run on every cell in the lot; others are run
on a sample of it, and a sampled activity is judged on the fraction of
the population actually tested rather than on any single cell. Grading
a sampled activity cell by cell reports nearly every cell as missing a
record it never owed, and grading an every-cell activity as a sample
accepts a lot on a handful of cells.

    every-cell   visual inspection and illuminated electrical
                 performance: every delivered or consumed cell carries
                 its own record
    sample       dimensional check, mass measurement and contact
                 adherence: a declared fraction of the population is
                 drawn, and the fraction is what is graded

Four record states are kept apart because different people disposition
them through different paperwork: no record at all, recorded as not yet
run, recorded as failed, recorded as passed. Absence is the worst,
because nobody can tell whether the work was skipped, lost or never
scheduled.

The activity set, the sample fractions and the failure policy below are
declared project policy, not physical constants; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

POPULATIONS = ("delivery", "qualification")

EVERY_CELL_ACTIVITIES = (
    "cell-visual-inspection",
    "cell-electrical-performance",
)

SAMPLE_ACTIVITIES = (
    "cell-dimensional-check",
    "cell-mass-measurement",
    "cell-contact-adherence",
)

ACCEPTANCE_ACTIVITIES = EVERY_CELL_ACTIVITIES + SAMPLE_ACTIVITIES

OUTCOME_PASSED = "passed"
OUTCOME_FAILED = "failed"
OUTCOME_NOT_RUN = "not-run"
OUTCOMES = (OUTCOME_PASSED, OUTCOME_FAILED, OUTCOME_NOT_RUN)

CELL_ACCEPTED = "cell-accepted"
CELL_FAILED = "cell-failed"
CELL_NOT_RUN = "cell-activity-not-run"
CELL_NO_RECORD = "cell-activity-not-recorded"

CELL_RANK = {
    CELL_NO_RECORD: 0,
    CELL_NOT_RUN: 1,
    CELL_FAILED: 2,
    CELL_ACCEPTED: 3,
}

LOT_ACCEPTED = "acceptance-lot-accepted"
LOT_NOT_ACCEPTED = "acceptance-lot-not-accepted"

DEFAULT_ACCEPTANCE_POLICY = {
    "min_sample_fraction": 0.10,
    "min_every_cell_share": 1.0,
    "carry_dispositioned_failure": False,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if not 0.0 < value <= 1.0:
        raise ValueError(
            "%s must sit above zero and at or below one, got %r" % (name, value)
        )
    return float(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A sampled fraction and a cleared share are both quotients of two cell
    counts, so a lot drawn to exactly the declared fraction can evaluate
    a unit in the last place below it. The comparison absorbs that; the
    declared minimum is untouched.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def resolve_policy(policy=None):
    """Merge project policy over the declared defaults and validate it."""
    settings = dict(DEFAULT_ACCEPTANCE_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    _require_fraction("min_sample_fraction", settings.get("min_sample_fraction"))
    _require_fraction(
        "min_every_cell_share", settings.get("min_every_cell_share")
    )
    _require_flag(
        "carry_dispositioned_failure", settings.get("carry_dispositioned_failure")
    )
    return settings


def validate_cell_record(cell):
    """Check one cell entry names a population and only owed activities."""
    _require_mapping("cell", cell)
    cell_id = _require_label("cell_id", cell.get("cell_id"))
    population = _require_choice("population", cell.get("population"), POPULATIONS)
    records = cell.get("acceptance_records") or {}
    _require_mapping("acceptance_records", records)
    cleaned = {}
    for activity, outcome in records.items():
        name = _require_choice("acceptance activity", activity, ACCEPTANCE_ACTIVITIES)
        cleaned[name] = _require_choice(
            "outcome for %s" % name, outcome, OUTCOMES
        )
    return {
        "cell_id": cell_id,
        "population": population,
        "acceptance_records": cleaned,
    }


def assess_cell(cell):
    """Grade one cell against the activities every cell owes.

    Sampled activities are deliberately not owed here. A cell that was
    never drawn into a sample is not missing anything, and counting it as
    missing buries the cells that genuinely carry no record.
    """
    record = validate_cell_record(cell)
    records = record["acceptance_records"]
    missing = [a for a in EVERY_CELL_ACTIVITIES if a not in records]
    not_run = [
        a
        for a in EVERY_CELL_ACTIVITIES
        if records.get(a) == OUTCOME_NOT_RUN
    ]
    failed = [
        a for a in EVERY_CELL_ACTIVITIES if records.get(a) == OUTCOME_FAILED
    ]
    passed = [
        a for a in EVERY_CELL_ACTIVITIES if records.get(a) == OUTCOME_PASSED
    ]

    findings = []
    for activity in missing:
        findings.append(
            "%s: no record at all for %s; nobody can tell whether the work was "
            "skipped, lost or never scheduled"
            % (record["cell_id"], activity)
        )
    for activity in not_run:
        findings.append(
            "%s: %s is recorded as not yet run" % (record["cell_id"], activity)
        )
    for activity in failed:
        findings.append(
            "%s: %s is recorded as failed and needs a disposition"
            % (record["cell_id"], activity)
        )

    if missing:
        verdict = CELL_NO_RECORD
    elif not_run:
        verdict = CELL_NOT_RUN
    elif failed:
        verdict = CELL_FAILED
    else:
        verdict = CELL_ACCEPTED

    return {
        "cell_id": record["cell_id"],
        "population": record["population"],
        "missing": missing,
        "not_run": not_run,
        "failed": failed,
        "passed": passed,
        "verdict": verdict,
        "findings": findings,
    }


def sample_activity_coverage(cells, activity, min_sample_fraction):
    """Grade a sampled activity on the share of the population it reached."""
    if not isinstance(cells, (list, tuple)) or not cells:
        raise ValueError("cells must be a non-empty sequence")
    name = _require_choice("activity", activity, SAMPLE_ACTIVITIES)
    minimum = _require_fraction("min_sample_fraction", min_sample_fraction)

    drawn = 0
    passed = 0
    failed = 0
    for cell in cells:
        records = validate_cell_record(cell)["acceptance_records"]
        outcome = records.get(name)
        if outcome is None:
            continue
        drawn += 1
        if outcome == OUTCOME_PASSED:
            passed += 1
        elif outcome == OUTCOME_FAILED:
            failed += 1
    sampled_fraction = drawn / len(cells)
    meets_sample = _at_least(sampled_fraction, minimum)

    findings = []
    if not meets_sample:
        findings.append(
            "%s reached %.4g of the population against a declared %.4g sample "
            "fraction" % (name, sampled_fraction, minimum)
        )
    if failed:
        findings.append(
            "%s failed on %d sampled cell(s); a sampled failure speaks for the "
            "lot, not for the cell" % (name, failed)
        )
    return {
        "activity": name,
        "population_size": len(cells),
        "drawn": drawn,
        "passed": passed,
        "failed": failed,
        "sampled_fraction": sampled_fraction,
        "meets_sample_fraction": meets_sample,
        "findings": findings,
    }


def summarise_population(cells, population, policy=None):
    """Summarise one population over both the every-cell and sampled work."""
    settings = resolve_policy(policy)
    name = _require_choice("population", population, POPULATIONS)
    members = [c for c in cells if validate_cell_record(c)["population"] == name]
    if not members:
        return {
            "population": name,
            "cells": 0,
            "accepted": 0,
            "accepted_share": 0.0,
            "meets_every_cell_share": False,
            "assessments": [],
            "sampled": [],
            "wholly_untested": False,
            "present": False,
            "findings": [],
        }

    assessments = [assess_cell(c) for c in members]
    findings = []
    for assessment in assessments:
        findings.extend(assessment["findings"])

    sampled = [
        sample_activity_coverage(
            members, activity, settings["min_sample_fraction"]
        )
        for activity in SAMPLE_ACTIVITIES
    ]
    for entry in sampled:
        findings.extend(
            "%s population: %s" % (name, f) for f in entry["findings"]
        )

    accepted = [a for a in assessments if a["verdict"] == CELL_ACCEPTED]
    accepted_share = len(accepted) / len(assessments)
    meets_share = _at_least(accepted_share, settings["min_every_cell_share"])

    wholly_untested = all(
        not validate_cell_record(c)["acceptance_records"] for c in members
    )
    if wholly_untested:
        findings.append(
            "the %s population carries no acceptance work at all; that is a "
            "decision somebody made, not a run of thin travellers" % name
        )
    return {
        "population": name,
        "cells": len(assessments),
        "accepted": len(accepted),
        "accepted_share": accepted_share,
        "meets_every_cell_share": meets_share,
        "assessments": assessments,
        "sampled": sampled,
        "wholly_untested": wholly_untested,
        "present": True,
        "findings": findings,
    }


def assess_bare_cell_acceptance(case):
    """Full clause 7.3.1 roll-up over both bare cell populations."""
    _require_mapping("case", case)
    lot_id = _require_label("lot_id", case.get("lot_id"))
    cells = case.get("cells")
    if not isinstance(cells, (list, tuple)) or not cells:
        raise ValueError("case must carry a non-empty cells sequence")
    settings = resolve_policy(case.get("policy"))

    seen = set()
    for cell in cells:
        cell_id = validate_cell_record(cell)["cell_id"]
        if cell_id in seen:
            raise ValueError("cell %r appears twice in one lot" % cell_id)
        seen.add(cell_id)

    summaries = {
        population: summarise_population(cells, population, settings)
        for population in POPULATIONS
    }
    findings = []
    for population in POPULATIONS:
        findings.extend(summaries[population]["findings"])

    missing_population = [
        population
        for population in POPULATIONS
        if not summaries[population]["present"]
    ]
    for population in missing_population:
        findings.append(
            "the lot holds no %s cells at all, so the clause cannot be shown "
            "reached on that population" % population
        )

    grouped = {}
    for population in POPULATIONS:
        for assessment in summaries[population]["assessments"]:
            grouped.setdefault(assessment["verdict"], []).append(
                assessment["cell_id"]
            )
    for names in grouped.values():
        names.sort()

    blocking = set(grouped) - {CELL_ACCEPTED}
    if settings["carry_dispositioned_failure"]:
        blocking -= {CELL_FAILED}

    sampling_short = any(
        not entry["meets_sample_fraction"]
        for population in POPULATIONS
        for entry in summaries[population]["sampled"]
    )
    sampled_failure = any(
        entry["failed"] > 0
        for population in POPULATIONS
        for entry in summaries[population]["sampled"]
    )
    share_short = any(
        summaries[population]["present"]
        and not summaries[population]["meets_every_cell_share"]
        for population in POPULATIONS
    )

    if (
        not blocking
        and not sampling_short
        and not share_short
        and not missing_population
        and not (sampled_failure and not settings["carry_dispositioned_failure"])
    ):
        verdict = LOT_ACCEPTED
    else:
        verdict = LOT_NOT_ACCEPTED

    all_assessments = [
        assessment
        for population in POPULATIONS
        for assessment in summaries[population]["assessments"]
    ]
    weakest = min(
        all_assessments, key=lambda a: (CELL_RANK[a["verdict"]], a["cell_id"])
    )
    return {
        "lot_id": lot_id,
        "populations": summaries,
        "grouped_cells": grouped,
        "missing_populations": missing_population,
        "weakest_cell": weakest["cell_id"],
        "verdict": verdict,
        "findings": findings,
    }
