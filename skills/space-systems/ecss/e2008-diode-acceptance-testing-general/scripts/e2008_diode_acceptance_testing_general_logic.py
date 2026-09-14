#!/usr/bin/env python3
"""Acceptance testing of diodes, delivery and qualification populations.

Anchor: ECSS-E-ST-20-08C clause 9.4.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Acceptance is owed by two diode populations, not one: the parts being
delivered, and the parts the qualification campaign consumes. The second
is the one that gets dropped, because a diode mounted into a
qualification coupon is not being shipped and acceptance reads like an
obligation somebody else carries. It is the other way round -- a
qualification result only means something if the diode it was produced
on was a sound diode to begin with.

Diodes also split their acceptance work by basis. Some activities are
run on every part in the lot; others are drawn on a sample of it, and a
sampled activity is judged on the share of its population actually
reached rather than on any one part. Grading a sampled activity part by
part reports almost every diode as missing a record it never owed, and
grading a per-diode activity as a sample closes a lot on a handful of
measurements.

    per-diode   visual inspection, forward voltage and reverse leakage:
                every delivered or consumed diode carries its own record
    sampled     thermal endurance, mechanical shock and terminal
                strength: a declared share of the population is drawn,
                and the share is what is graded

Four record states are held apart because different people disposition
them through different paperwork: no record at all, marked not yet run,
recorded as failed, recorded as passed. Absence is the worst, because
nobody can say whether the work was skipped, lost or never scheduled.

The activity set, the sample share and the failure policy below are
declared project policy, not physical constants; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

POPULATIONS = ("delivery", "qualification")

PER_DIODE_ACTIVITIES = (
    "diode-visual-inspection",
    "diode-forward-voltage-measurement",
    "diode-reverse-leakage-measurement",
)

SAMPLED_ACTIVITIES = (
    "diode-thermal-endurance-sample",
    "diode-mechanical-shock-sample",
    "diode-terminal-strength-sample",
)

ACCEPTANCE_ACTIVITIES = PER_DIODE_ACTIVITIES + SAMPLED_ACTIVITIES

OUTCOME_PASSED = "passed"
OUTCOME_FAILED = "failed"
OUTCOME_NOT_RUN = "not-run"
OUTCOMES = (OUTCOME_PASSED, OUTCOME_FAILED, OUTCOME_NOT_RUN)

DIODE_ACCEPTED = "diode-accepted"
DIODE_FAILED = "diode-failed"
DIODE_NOT_RUN = "diode-activity-not-run"
DIODE_NO_RECORD = "diode-activity-not-recorded"

DIODE_RANK = {
    DIODE_NO_RECORD: 0,
    DIODE_NOT_RUN: 1,
    DIODE_FAILED: 2,
    DIODE_ACCEPTED: 3,
}

LOT_ACCEPTED = "diode-lot-accepted"
LOT_NOT_ACCEPTED = "diode-lot-not-accepted"

DEFAULT_ACCEPTANCE_POLICY = {
    "min_sample_share": 0.10,
    "min_per_diode_share": 1.0,
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


def _require_share(name, value):
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

    A sampled share and a cleared share are both quotients of two part
    counts, so a lot drawn to exactly the declared share can evaluate a
    unit in the last place below it. The comparison absorbs that; the
    declared minimum itself is untouched.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def resolve_policy(policy=None):
    """Merge project policy over the declared defaults and validate it."""
    settings = dict(DEFAULT_ACCEPTANCE_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    _require_share("min_sample_share", settings.get("min_sample_share"))
    _require_share("min_per_diode_share", settings.get("min_per_diode_share"))
    _require_flag(
        "carry_dispositioned_failure", settings.get("carry_dispositioned_failure")
    )
    return settings


def validate_diode_record(diode):
    """Check one diode entry names a population and only owed activities."""
    _require_mapping("diode", diode)
    diode_id = _require_label("diode_id", diode.get("diode_id"))
    population = _require_choice("population", diode.get("population"), POPULATIONS)
    records = diode.get("acceptance_records") or {}
    _require_mapping("acceptance_records", records)
    cleaned = {}
    for activity, outcome in records.items():
        name = _require_choice(
            "acceptance activity", activity, ACCEPTANCE_ACTIVITIES
        )
        cleaned[name] = _require_choice("outcome for %s" % name, outcome, OUTCOMES)
    return {
        "diode_id": diode_id,
        "population": population,
        "acceptance_records": cleaned,
    }


def assess_diode(diode):
    """Grade one diode against the activities every part owes.

    Sampled activities are deliberately not owed here. A part that was
    never drawn into a sample is not missing anything, and counting it as
    missing buries the parts that genuinely carry no record.
    """
    record = validate_diode_record(diode)
    records = record["acceptance_records"]
    missing = [a for a in PER_DIODE_ACTIVITIES if a not in records]
    not_run = [
        a for a in PER_DIODE_ACTIVITIES if records.get(a) == OUTCOME_NOT_RUN
    ]
    failed = [a for a in PER_DIODE_ACTIVITIES if records.get(a) == OUTCOME_FAILED]
    passed = [a for a in PER_DIODE_ACTIVITIES if records.get(a) == OUTCOME_PASSED]

    findings = []
    for activity in missing:
        findings.append(
            "%s: no record at all for %s; nobody can say whether the work was "
            "skipped, lost or never scheduled" % (record["diode_id"], activity)
        )
    for activity in not_run:
        findings.append(
            "%s: %s is marked as not yet run" % (record["diode_id"], activity)
        )
    for activity in failed:
        findings.append(
            "%s: %s is recorded as failed and needs a disposition"
            % (record["diode_id"], activity)
        )

    if missing:
        verdict = DIODE_NO_RECORD
    elif not_run:
        verdict = DIODE_NOT_RUN
    elif failed:
        verdict = DIODE_FAILED
    else:
        verdict = DIODE_ACCEPTED

    return {
        "diode_id": record["diode_id"],
        "population": record["population"],
        "missing": missing,
        "not_run": not_run,
        "failed": failed,
        "passed": passed,
        "verdict": verdict,
        "findings": findings,
    }


def sampled_activity_coverage(diodes, activity, min_sample_share):
    """Grade a sampled activity on the share of its population reached."""
    if not isinstance(diodes, (list, tuple)) or not diodes:
        raise ValueError("diodes must be a non-empty sequence")
    name = _require_choice("activity", activity, SAMPLED_ACTIVITIES)
    minimum = _require_share("min_sample_share", min_sample_share)

    drawn = 0
    passed = 0
    failed = 0
    for diode in diodes:
        records = validate_diode_record(diode)["acceptance_records"]
        outcome = records.get(name)
        if outcome is None:
            continue
        drawn += 1
        if outcome == OUTCOME_PASSED:
            passed += 1
        elif outcome == OUTCOME_FAILED:
            failed += 1
    sampled_share = drawn / len(diodes)
    meets_share = _at_least(sampled_share, minimum)

    findings = []
    if not meets_share:
        findings.append(
            "%s reached %.4g of the population against a declared %.4g sample "
            "share" % (name, sampled_share, minimum)
        )
    if failed:
        findings.append(
            "%s failed on %d drawn part(s); a sampled failure speaks for the "
            "population, not for the part it landed on" % (name, failed)
        )
    return {
        "activity": name,
        "population_size": len(diodes),
        "drawn": drawn,
        "passed": passed,
        "failed": failed,
        "sampled_share": sampled_share,
        "meets_sample_share": meets_share,
        "findings": findings,
    }


def summarise_population(diodes, population, policy=None):
    """Summarise one population over both the per-diode and sampled work."""
    settings = resolve_policy(policy)
    name = _require_choice("population", population, POPULATIONS)
    members = [d for d in diodes if validate_diode_record(d)["population"] == name]
    if not members:
        return {
            "population": name,
            "diodes": 0,
            "accepted": 0,
            "accepted_share": 0.0,
            "meets_per_diode_share": False,
            "assessments": [],
            "sampled": [],
            "wholly_untested": False,
            "present": False,
            "findings": [],
        }

    assessments = [assess_diode(d) for d in members]
    findings = []
    for assessment in assessments:
        findings.extend(assessment["findings"])

    sampled = [
        sampled_activity_coverage(members, activity, settings["min_sample_share"])
        for activity in SAMPLED_ACTIVITIES
    ]
    for entry in sampled:
        findings.extend("%s population: %s" % (name, f) for f in entry["findings"])

    accepted = [a for a in assessments if a["verdict"] == DIODE_ACCEPTED]
    accepted_share = len(accepted) / len(assessments)
    meets_per_diode = _at_least(accepted_share, settings["min_per_diode_share"])

    wholly_untested = all(
        not validate_diode_record(d)["acceptance_records"] for d in members
    )
    if wholly_untested:
        findings.append(
            "the %s population carries no acceptance work at all; that is a "
            "decision somebody made, not a run of thin travellers" % name
        )
    return {
        "population": name,
        "diodes": len(assessments),
        "accepted": len(accepted),
        "accepted_share": accepted_share,
        "meets_per_diode_share": meets_per_diode,
        "assessments": assessments,
        "sampled": sampled,
        "wholly_untested": wholly_untested,
        "present": True,
        "findings": findings,
    }


def assess_diode_acceptance(case):
    """Full clause 9.4.1 roll-up over both diode populations."""
    _require_mapping("case", case)
    lot_id = _require_label("lot_id", case.get("lot_id"))
    diodes = case.get("diodes")
    if not isinstance(diodes, (list, tuple)) or not diodes:
        raise ValueError("case must carry a non-empty diodes sequence")
    settings = resolve_policy(case.get("policy"))

    seen = set()
    for diode in diodes:
        diode_id = validate_diode_record(diode)["diode_id"]
        if diode_id in seen:
            raise ValueError("diode %r appears twice in one lot" % diode_id)
        seen.add(diode_id)

    summaries = {
        population: summarise_population(diodes, population, settings)
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
            "the lot holds no %s diodes at all, so the clause cannot be shown "
            "reached on that population" % population
        )

    grouped = {}
    for population in POPULATIONS:
        for assessment in summaries[population]["assessments"]:
            grouped.setdefault(assessment["verdict"], []).append(
                assessment["diode_id"]
            )
    for names in grouped.values():
        names.sort()

    blocking = set(grouped) - {DIODE_ACCEPTED}
    if settings["carry_dispositioned_failure"]:
        blocking -= {DIODE_FAILED}

    sampling_short = any(
        not entry["meets_sample_share"]
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
        and not summaries[population]["meets_per_diode_share"]
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
        all_assessments, key=lambda a: (DIODE_RANK[a["verdict"]], a["diode_id"])
    )
    return {
        "lot_id": lot_id,
        "populations": summaries,
        "grouped_diodes": grouped,
        "missing_populations": missing_population,
        "weakest_diode": weakest["diode_id"],
        "verdict": verdict,
        "findings": findings,
    }
