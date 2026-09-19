#!/usr/bin/env python3
"""Screening test programme for an ECSS thermal test.

Anchor: ECSS-Q-ST-70-04C, the method variant that screens rather than
qualifies. The procedure below is a paraphrase into implementable steps;
no standard text is reproduced.

Screening is the cheap variant, and its whole definition is the cycle
count per class plus how many specimens carry it. A class is a statement
about how much is already known: a novel material and process is screened
hardest, a modified one less, a heritage one least.

The class an item is booked under is not the class it is entitled to. A
process change, a supplier change or an absence of flight heritage each
pull the item back towards novel, and an item screened under a heritage
count it has lost entitlement to is screened to a number that no longer
means anything.

Specimen count and chamber capacity together decide how many runs the
programme takes, and the programme duration is per run, not per specimen.

A screening result is evidence of a gross defect, never a qualification.
Every programme carries that limit with it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CLASS_I_NOVEL = "class-i-novel"
CLASS_II_MODIFIED = "class-ii-modified"
CLASS_III_HERITAGE = "class-iii-heritage"
SCREENING_CLASSES = (CLASS_I_NOVEL, CLASS_II_MODIFIED, CLASS_III_HERITAGE)

PROCESS_CHANGE = "process-change"
SUPPLIER_CHANGE = "supplier-change"
NO_FLIGHT_HERITAGE = "no-flight-heritage"
ESCALATION_FLAGS = (PROCESS_CHANGE, SUPPLIER_CHANGE, NO_FLIGHT_HERITAGE)

DEFAULT_SCREENING_POLICY = {
    "cycles_per_class": {
        CLASS_I_NOVEL: 20,
        CLASS_II_MODIFIED: 12,
        CLASS_III_HERITAGE: 6,
    },
    "specimens_per_class": {
        CLASS_I_NOVEL: 6,
        CLASS_II_MODIFIED: 4,
        CLASS_III_HERITAGE: 3,
    },
    "min_cycles": 4,
    "min_specimens": 3,
    "max_specimens_per_run": 8,
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


def _require_positive_int(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(
            "%s must be an integer of at least 1, got %r" % (name, value)
        )
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
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _ceil_div(numerator, denominator):
    """Integer ceiling division; no float rounding anywhere near it."""
    return -(-numerator // denominator)


def validate_screening_policy(policy):
    """Check the class tables are complete, ordered and above the floors."""
    _require_mapping("policy", policy)
    cycles = _require_mapping("policy cycles_per_class", policy.get("cycles_per_class"))
    specimens = _require_mapping(
        "policy specimens_per_class", policy.get("specimens_per_class")
    )
    for table_name, table in (("cycles_per_class", cycles), ("specimens_per_class", specimens)):
        missing = set(SCREENING_CLASSES) - set(table)
        if missing:
            raise ValueError(
                "policy %s is missing: %s" % (table_name, ", ".join(sorted(missing)))
            )
        for item_class in SCREENING_CLASSES:
            _require_positive_int("%s[%s]" % (table_name, item_class), table[item_class])
    min_cycles = _require_positive_int("min_cycles", policy.get("min_cycles"))
    min_specimens = _require_positive_int("min_specimens", policy.get("min_specimens"))
    _require_positive_int(
        "max_specimens_per_run", policy.get("max_specimens_per_run")
    )
    ordered = [cycles[item_class] for item_class in SCREENING_CLASSES]
    if ordered != sorted(ordered, reverse=True):
        raise ValueError(
            "cycles_per_class must not increase with heritage: %s" % (ordered,)
        )
    if cycles[CLASS_III_HERITAGE] < min_cycles:
        raise ValueError(
            "the lightest class screens on %d cycles, below the floor of %d"
            % (cycles[CLASS_III_HERITAGE], min_cycles)
        )
    if specimens[CLASS_III_HERITAGE] < min_specimens:
        raise ValueError(
            "the lightest class screens %d specimens, below the floor of %d"
            % (specimens[CLASS_III_HERITAGE], min_specimens)
        )
    return policy


def escalate_screening_class(item_class, flags, policy=DEFAULT_SCREENING_POLICY):
    """Pull a claimed class back towards novel, one step per standing flag."""
    validate_screening_policy(policy)
    claimed = _require_choice("item_class", item_class, SCREENING_CLASSES)
    if not isinstance(flags, (list, tuple, set, frozenset)):
        raise ValueError("flags must be a sequence, got %r" % (flags,))
    standing = []
    for flag in flags:
        _require_choice("flag", flag, ESCALATION_FLAGS)
        if flag not in standing:
            standing.append(flag)
    index = SCREENING_CLASSES.index(claimed)
    effective_index = max(0, index - len(standing))
    effective = SCREENING_CLASSES[effective_index]
    reasons = []
    if effective != claimed:
        reasons.append(
            "booked as %s but %s stand against it, so the programme runs as %s"
            % (claimed, ", ".join(sorted(standing)), effective)
        )
    return {
        "claimed_class": claimed,
        "effective_class": effective,
        "steps": index - effective_index,
        "standing_flags": sorted(standing),
        "reasons": reasons,
    }


def screening_cycle_count(item_class, policy=DEFAULT_SCREENING_POLICY):
    """Cycles the class is screened on."""
    validate_screening_policy(policy)
    _require_choice("item_class", item_class, SCREENING_CLASSES)
    return policy["cycles_per_class"][item_class]


def screening_specimen_count(item_class, policy=DEFAULT_SCREENING_POLICY):
    """Specimens the class is screened with."""
    validate_screening_policy(policy)
    _require_choice("item_class", item_class, SCREENING_CLASSES)
    return policy["specimens_per_class"][item_class]


def chamber_run_count(specimen_count, policy=DEFAULT_SCREENING_POLICY):
    """Runs needed to put every specimen through the chamber."""
    validate_screening_policy(policy)
    count = _require_positive_int("specimen_count", specimen_count)
    return _ceil_div(count, policy["max_specimens_per_run"])


def screening_duration_s(cycle_count, cycle_duration_s, run_count):
    """Chamber time: cycles times cycle duration, once per run."""
    cycles = _require_positive_int("cycle_count", cycle_count)
    duration = _require_positive("cycle_duration_s", cycle_duration_s)
    runs = _require_positive_int("run_count", run_count)
    return cycles * duration * runs


def define_screening_programme(case, policy=DEFAULT_SCREENING_POLICY):
    """Full screening programme: class, cycles, specimens, runs, duration."""
    validate_screening_policy(policy)
    _require_mapping("case", case)
    item = case.get("item_id")
    if not isinstance(item, str) or not item.strip():
        raise ValueError("case item_id must be a non-empty string")
    resolution = escalate_screening_class(
        case.get("claimed_class"), case.get("flags", ()), policy
    )
    effective = resolution["effective_class"]
    cycles = screening_cycle_count(effective, policy)
    specimens = case.get("specimen_count")
    if specimens is None:
        specimens = screening_specimen_count(effective, policy)
        specimen_source = "policy"
    else:
        specimens = _require_positive_int("specimen_count", specimens)
        specimen_source = "declared"
    cycle_duration = _require_positive(
        "cycle_duration_s", case.get("cycle_duration_s")
    )
    runs = chamber_run_count(specimens, policy)
    duration = screening_duration_s(cycles, cycle_duration, runs)

    findings = list(resolution["reasons"])
    duties = []
    policy_specimens = screening_specimen_count(effective, policy)
    if specimen_source == "declared" and specimens < policy_specimens:
        findings.append(
            "%d specimens were declared where %s calls for %d; the programme runs "
            "thinner than the class it is booked under"
            % (specimens, effective, policy_specimens)
        )
    if runs > 1:
        findings.append(
            "%d specimens do not fit one chamber load of %d, so the programme takes "
            "%d sequential runs and the duration multiplies accordingly"
            % (specimens, policy["max_specimens_per_run"], runs)
        )
    if not _at_least(cycles, policy["min_cycles"]):
        findings.append(
            "%d cycles is below the screening floor of %d"
            % (cycles, policy["min_cycles"])
        )
    duties.append(
        "state that a screening result evidences gross defects only; it is not a "
        "qualification and cannot be cited as one"
    )
    duties.append(
        "re-screen against the effective class whenever a process, supplier or "
        "heritage flag changes after the programme was written"
    )

    return {
        "item_id": item,
        "claimed_class": resolution["claimed_class"],
        "effective_class": effective,
        "escalation_steps": resolution["steps"],
        "standing_flags": resolution["standing_flags"],
        "cycle_count": cycles,
        "specimen_count": specimens,
        "specimen_source": specimen_source,
        "run_count": runs,
        "cycle_duration_s": cycle_duration,
        "programme_duration_s": duration,
        "findings": findings,
        "duties": duties,
    }
