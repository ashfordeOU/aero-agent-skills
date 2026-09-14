#!/usr/bin/env python3
"""A protection diode qualification programme runs at two levels, not one.

Anchor: ECSS-E-ST-20-08C clause 9.5.3. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The qualification programme for external protection diodes covers the bare
diodes and the complete diode assemblies they are built into. Those are two
populations with two activity sets, and a programme that closes one of them
is not most of the way to closing both -- it has answered a different
question:

    coverage    does each level carry its own required activity set, or has
                one level been planned and the other assumed
    specimens   does each planned activity run on enough specimens for the
                result to say anything about the population
    provenance  are the specimens drawn from the diode lots the programme
                names, including the assemblies, which have to be built
                from those same bare diodes rather than from whatever was
                on the bench
    sequence    does the bare-diode level close before the assembly level
                starts, so an assembly result is not resting on parts that
                were still unqualified when it was taken

The arms are ranked rather than merged. Specimens from the wrong lots
outrank a specimen count that is merely short, because a short campaign
still measures the right population while a foreign one measures something
else and reports a number anyway.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

QUALIFICATION_LEVELS = ("bare-protection-diode", "protection-diode-assembly")

REQUIRED_LEVEL_ACTIVITIES = {
    "bare-protection-diode": (
        "bare-diode-visual-inspection",
        "bare-diode-forward-voltage-measurement",
        "bare-diode-reverse-leakage-measurement",
        "bare-diode-thermal-cycling",
        "bare-diode-thermal-vacuum-exposure",
    ),
    "protection-diode-assembly": (
        "diode-assembly-visual-inspection",
        "diode-assembly-electrical-characterisation",
        "diode-assembly-thermal-cycling",
        "diode-assembly-humidity-exposure",
        "diode-assembly-mechanical-load",
    ),
}

ACTIVITY_LEVEL = {
    activity: level
    for level, activities in REQUIRED_LEVEL_ACTIVITIES.items()
    for activity in activities
}

ACTIVITY_SOUND = "activity-sound"
ACTIVITY_PROVENANCE_MISMATCH = "activity-provenance-mismatch"
ACTIVITY_SPECIMENS_SHORT = "activity-specimens-short"
ACTIVITY_OUT_OF_SEQUENCE = "activity-out-of-sequence"

ARM_RANK = (
    ACTIVITY_PROVENANCE_MISMATCH,
    ACTIVITY_SPECIMENS_SHORT,
    ACTIVITY_OUT_OF_SEQUENCE,
)

PROGRAMME_COMPLETE = "programme-complete"
PROGRAMME_INCOMPLETE = "programme-incomplete"

DEFAULT_DIODE_PLAN_POLICY = {
    "min_bare_diode_specimens": 6,
    "min_assembly_specimens": 4,
    "require_specimen_provenance": True,
    "require_bare_level_before_assembly": True,
    "min_planned_activity_fraction": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return value


def _require_id_set(name, value):
    if not isinstance(value, (list, tuple, set, frozenset)) or not value:
        raise ValueError("%s must be a non-empty sequence of identifiers" % name)
    read = set()
    for item in value:
        read.add(_require_text("%s entry" % name, item))
    return read


def validate_diode_plan_policy(policy):
    """Check a qualification plan policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_count("min_bare_diode_specimens", policy.get("min_bare_diode_specimens"), 1)
    _require_count("min_assembly_specimens", policy.get("min_assembly_specimens"), 1)
    _require_flag("require_specimen_provenance", policy.get("require_specimen_provenance"))
    _require_flag(
        "require_bare_level_before_assembly",
        policy.get("require_bare_level_before_assembly"),
    )
    _require_fraction(
        "min_planned_activity_fraction", policy.get("min_planned_activity_fraction")
    )
    return policy


def qualification_levels():
    """The two populations the programme has to cover."""
    return tuple(QUALIFICATION_LEVELS)


def required_level_activities(level):
    """The activity set one level of the programme owes."""
    level = _require_text("level", level)
    if level not in REQUIRED_LEVEL_ACTIVITIES:
        raise ValueError(
            "level must be one of %s, got %r"
            % (", ".join(QUALIFICATION_LEVELS), level)
        )
    return tuple(REQUIRED_LEVEL_ACTIVITIES[level])


def activity_level(activity):
    """Which level a planned activity belongs to."""
    activity = _require_text("activity", activity)
    if activity not in ACTIVITY_LEVEL:
        raise ValueError("plan names an unknown qualification activity %s" % activity)
    return ACTIVITY_LEVEL[activity]


def min_specimens_for_level(level, policy=DEFAULT_DIODE_PLAN_POLICY):
    """How many specimens this level needs before a result means anything."""
    validate_diode_plan_policy(policy)
    level = _require_text("level", level)
    if level == "bare-protection-diode":
        return int(policy["min_bare_diode_specimens"])
    if level == "protection-diode-assembly":
        return int(policy["min_assembly_specimens"])
    raise ValueError(
        "level must be one of %s, got %r" % (", ".join(QUALIFICATION_LEVELS), level)
    )


def specimen_sufficiency(entry, policy=DEFAULT_DIODE_PLAN_POLICY):
    """Does this planned activity carry enough specimens for its level."""
    validate_diode_plan_policy(policy)
    if not isinstance(entry, dict):
        raise ValueError("plan entry must be a mapping, got %r" % (entry,))
    level = activity_level(entry.get("activity"))
    count = _require_count("specimen_count", entry.get("specimen_count"), 0)
    minimum = min_specimens_for_level(level, policy)
    return {
        "level": level,
        "specimen_count": count,
        "minimum": minimum,
        "shortfall": max(0, minimum - count),
        "sufficient": count >= minimum,
    }


def specimen_provenance(entry, programme_lot_ids):
    """Are this activity's specimens drawn from the diode lots the programme names."""
    if not isinstance(entry, dict):
        raise ValueError("plan entry must be a mapping, got %r" % (entry,))
    programme = _require_id_set("programme_lot_ids", programme_lot_ids)
    declared = _require_id_set("specimen_lot_ids", entry.get("specimen_lot_ids"))
    foreign = sorted(declared - programme)
    return {
        "declared_lot_ids": sorted(declared),
        "foreign_lot_ids": foreign,
        "traceable": not foreign,
    }


def assembly_start_barrier(entries):
    """The sequence number the bare-diode level closes on, or None if it is absent."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence, got %r" % (entries,))
    barrier = None
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("plan entry must be a mapping, got %r" % (entry,))
        if activity_level(entry.get("activity")) != "bare-protection-diode":
            continue
        sequence = _require_count("sequence", entry.get("sequence"), 1)
        if barrier is None or sequence > barrier:
            barrier = sequence
    return barrier


def assess_planned_activity(
    entry, programme_lot_ids, barrier=None, policy=DEFAULT_DIODE_PLAN_POLICY
):
    """Verdict for one planned qualification activity, with the arms ranked."""
    validate_diode_plan_policy(policy)
    if not isinstance(entry, dict):
        raise ValueError("plan entry must be a mapping, got %r" % (entry,))
    activity = _require_text("activity", entry.get("activity"))
    level = activity_level(activity)
    declared_level = entry.get("level")
    if declared_level is not None:
        declared_level = _require_text("level", declared_level)
        if declared_level != level:
            raise ValueError(
                "activity %s belongs to %s, not to %s"
                % (activity, level, declared_level)
            )
    sequence = _require_count("sequence", entry.get("sequence"), 1)
    specimens = specimen_sufficiency(entry, policy)
    provenance = specimen_provenance(entry, programme_lot_ids)
    findings = []

    out_of_sequence = (
        policy["require_bare_level_before_assembly"]
        and level == "protection-diode-assembly"
        and barrier is not None
        and sequence <= barrier
    )

    if policy["require_specimen_provenance"] and not provenance["traceable"]:
        verdict = ACTIVITY_PROVENANCE_MISMATCH
        findings.append(
            "%s draws specimens from %s, which the programme does not name"
            % (activity, ", ".join(provenance["foreign_lot_ids"]))
        )
    elif not specimens["sufficient"]:
        verdict = ACTIVITY_SPECIMENS_SHORT
        findings.append(
            "%s plans %d specimens against a %s minimum of %d"
            % (activity, specimens["specimen_count"], level, specimens["minimum"])
        )
    elif out_of_sequence:
        verdict = ACTIVITY_OUT_OF_SEQUENCE
        findings.append(
            "%s runs at step %d, before the bare-diode level closes at step %d"
            % (activity, sequence, barrier)
        )
    else:
        verdict = ACTIVITY_SOUND
    return {
        "activity": activity,
        "level": level,
        "sequence": sequence,
        "specimens": specimens,
        "provenance": provenance,
        "verdict": verdict,
        "sound": verdict == ACTIVITY_SOUND,
        "findings": findings,
    }


def level_coverage(entries, level):
    """Which of a level's required activities the plan actually schedules."""
    required = set(required_level_activities(level))
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence, got %r" % (entries,))
    planned = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("plan entry must be a mapping, got %r" % (entry,))
        activity = _require_text("activity", entry.get("activity"))
        if activity_level(activity) == level:
            planned.add(activity)
    missing = sorted(required - planned)
    return {
        "level": level,
        "planned_activities": sorted(planned),
        "missing_activities": missing,
        "complete": not missing,
    }


def worst_arm(verdicts):
    """The arm that has to be closed first across a set of activity verdicts."""
    if not isinstance(verdicts, (list, tuple, set, frozenset)):
        raise ValueError("verdicts must be a sequence, got %r" % (verdicts,))
    present = set(verdicts)
    for arm in ARM_RANK:
        if arm in present:
            return arm
    return None


def assess_diode_qualification_plan(plan, policy=DEFAULT_DIODE_PLAN_POLICY):
    """Full clause 9.5.3 sweep over a protection diode qualification programme."""
    validate_diode_plan_policy(policy)
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    programme_id = _require_text("programme_id", plan.get("programme_id"))
    lot_ids = sorted(_require_id_set("diode_lot_ids", plan.get("diode_lot_ids")))
    entries = plan.get("activities")
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("plan activities must be a non-empty sequence of mappings")

    barrier = assembly_start_barrier(entries)
    seen = set()
    assessments = []
    for entry in entries:
        assessed = assess_planned_activity(entry, lot_ids, barrier, policy)
        if assessed["activity"] in seen:
            raise ValueError("plan schedules %s twice" % assessed["activity"])
        seen.add(assessed["activity"])
        assessments.append(assessed)
    assessments.sort(key=lambda item: (item["level"], item["activity"]))

    findings = []
    coverage = {}
    missing_total = 0
    for level in QUALIFICATION_LEVELS:
        coverage[level] = level_coverage(entries, level)
        missing_total += len(coverage[level]["missing_activities"])
        if not coverage[level]["planned_activities"]:
            findings.append(
                "programme %s plans nothing at all at the %s level"
                % (programme_id, level)
            )
        elif coverage[level]["missing_activities"]:
            findings.append(
                "the %s level is missing %s"
                % (level, ", ".join(coverage[level]["missing_activities"]))
            )
    for entry in assessments:
        findings.extend(entry["findings"])

    if (
        policy["require_bare_level_before_assembly"]
        and barrier is None
        and coverage["protection-diode-assembly"]["planned_activities"]
    ):
        findings.append(
            "programme %s schedules assembly work with no bare-diode level to "
            "close first" % programme_id
        )

    required_total = sum(len(v) for v in REQUIRED_LEVEL_ACTIVITIES.values())
    planned_total = required_total - missing_total
    planned_fraction = planned_total / float(required_total)
    minimum = float(policy["min_planned_activity_fraction"])
    coverage_ok = _at_least(planned_fraction, minimum)
    if not coverage_ok:
        findings.append(
            "the programme plans %d of %d required activities against a required "
            "share of %.3f" % (planned_total, required_total, minimum)
        )

    grouped = {}
    for entry in assessments:
        grouped.setdefault(entry["verdict"], []).append(entry["activity"])
    open_activities = sorted(
        entry["activity"] for entry in assessments if not entry["sound"]
    )
    complete = coverage_ok and not missing_total and not open_activities
    return {
        "verdict": PROGRAMME_COMPLETE if complete else PROGRAMME_INCOMPLETE,
        "programme_id": programme_id,
        "diode_lot_ids": lot_ids,
        "activity_assessments": assessments,
        "grouped_by_verdict": {k: sorted(v) for k, v in grouped.items()},
        "level_coverage": coverage,
        "assembly_start_barrier": barrier,
        "open_activities": open_activities,
        "planned_activity_fraction": planned_fraction,
        "required_activity_fraction": minimum,
        "both_levels_covered": missing_total == 0,
        "close_first": worst_arm([entry["verdict"] for entry in assessments]),
        "findings": findings,
    }
