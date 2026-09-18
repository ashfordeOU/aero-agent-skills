"""Shortest spacing allowed between two consecutive external turn on commands.

Anchor: ECSS-E-ST-20-20C clause 5.4.1.4.1 (the minimum interval a channel
requires between two successive externally issued turn on commands).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Decide whether the clause bites. It addresses channels that are switched on
   by an external command; a foldback or retriggerable limiter recovers on its
   own and is reported outside the clause rather than failed by it.
2. Work out what the interval actually is. A channel usually carries more than
   one contributor -- a declared minimum, the time the die needs to recover
   thermally from the previous inrush, and the time the output filter needs to
   settle -- and the interval that governs is the largest of them, not the one
   written on the interface sheet.
3. Say so when the declared figure is not the governing one. A channel
   commanded at its declared minimum while a longer thermal recovery is still
   running is being re-triggered inside recovery, and the interface sheet is
   the thing that has to move.
4. Grade a command schedule against the governing interval: every consecutive
   pair, the gap it leaves, and the shortfall where the gap is too small.
5. Repair the schedule rather than only failing it. Each command is pushed to
   the earliest instant the channel admits it, which cascades through the
   commands behind it, and the shift at the end of the schedule is the cost of
   the constraint in the timeline the operator planned.

The governing interval and the repaired schedule are the two numbers a review
needs: a violation list alone says a command sequence is inadmissible without
saying what sequence would have been.
"""

import math

__all__ = [
    "INTERVAL_TOLERANCE_MS",
    "LIMITER_CATEGORIES",
    "EXTERNALLY_COMMANDED_CATEGORIES",
    "INTERVAL_CONTRIBUTORS",
    "normalise_category",
    "validate_constraints",
    "validate_schedule",
    "required_interval_ms",
    "governing_constraint",
    "max_on_command_rate_hz",
    "command_gaps_ms",
    "earliest_admissible_time_ms",
    "spacing_violations",
    "repair_schedule_ms",
    "assess_on_command_spacing",
]

# Command times are quoted in milliseconds and a schedule is routinely built
# exactly on the interval. Absorb the representation error, not the interval.
INTERVAL_TOLERANCE_MS = 1e-9

# Categories switched on by an external command, which is what the clause
# places the spacing requirement on.
EXTERNALLY_COMMANDED_CATEGORIES = ("latching", "high-power")
LIMITER_CATEGORIES = EXTERNALLY_COMMANDED_CATEGORIES + ("retriggerable", "foldback")

# The declared figure is mandatory; the physical contributors are optional but
# govern whenever they are longer.
INTERVAL_CONTRIBUTORS = (
    "declared_min_interval_ms",
    "thermal_recovery_ms",
    "inrush_settling_ms",
)

_CATEGORY_ALIASES = {
    "lcl": "latching",
    "latching-current-limiter": "latching",
    "hpc": "high-power",
    "high-power-limiter": "high-power",
    "rcl": "retriggerable",
    "fcl": "foldback",
}


def _text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _positive_real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError("%s must be positive and finite, got %g" % (label, number))
    return number


def normalise_category(category):
    """Return the canonical limiter category name."""
    key = _text(category, "category")
    key = _CATEGORY_ALIASES.get(key, key)
    if key not in LIMITER_CATEGORIES:
        raise ValueError(
            "unknown limiter category %r; known: %s"
            % (category, ", ".join(LIMITER_CATEGORIES))
        )
    return key


def validate_constraints(spec):
    """Return the validated spacing constraints of one channel.

    spec keys: category, declared_min_interval_ms, and optionally
    thermal_recovery_ms and inrush_settling_ms.
    """
    if not isinstance(spec, dict):
        raise ValueError("constraints spec must be a mapping")
    for key in ("category", "declared_min_interval_ms"):
        if key not in spec:
            raise ValueError("constraints spec missing required key '%s'" % key)
    constraints = {
        "category": normalise_category(spec["category"]),
        "declared_min_interval_ms": _positive_real(
            spec["declared_min_interval_ms"], "declared_min_interval_ms"
        ),
    }
    for key in INTERVAL_CONTRIBUTORS[1:]:
        if key in spec and spec[key] is not None:
            constraints[key] = _positive_real(spec[key], key)
    return constraints


def validate_schedule(times):
    """Return the validated command schedule as ascending millisecond times."""
    if not isinstance(times, (list, tuple)):
        raise ValueError("command schedule must be a sequence")
    if not times:
        raise ValueError("a command schedule needs at least one command")
    validated = []
    for i, value in enumerate(times):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("schedule[%d] must be a real number, got %r" % (i, value))
        number = float(value)
        if not math.isfinite(number) or number < 0.0:
            raise ValueError(
                "schedule[%d] must be a non-negative finite time, got %g" % (i, number)
            )
        if validated and number <= validated[-1]:
            raise ValueError(
                "schedule[%d] time %g ms does not follow the previous command at "
                "%g ms; commands must be listed in strictly ascending order"
                % (i, number, validated[-1])
            )
        validated.append(number)
    return validated


def required_interval_ms(constraints):
    """Return the interval the channel actually requires between on commands."""
    return max(
        constraints[key] for key in INTERVAL_CONTRIBUTORS if key in constraints
    )


def governing_constraint(constraints):
    """Return the name of the contributor that sets the required interval."""
    required = required_interval_ms(constraints)
    for key in INTERVAL_CONTRIBUTORS:
        if key in constraints and math.isclose(
            constraints[key], required, rel_tol=0.0, abs_tol=INTERVAL_TOLERANCE_MS
        ):
            return key
    return INTERVAL_CONTRIBUTORS[0]


def max_on_command_rate_hz(constraints):
    """Return the highest sustained on-command rate the channel admits."""
    return 1000.0 / required_interval_ms(constraints)


def command_gaps_ms(times):
    """Return the gap between each consecutive pair of commands."""
    schedule = validate_schedule(times)
    return [schedule[i] - schedule[i - 1] for i in range(1, len(schedule))]


def earliest_admissible_time_ms(previous_time_ms, constraints):
    """Return the earliest instant a further on command may be issued."""
    if not isinstance(previous_time_ms, (int, float)) or isinstance(
        previous_time_ms, bool
    ):
        raise ValueError(
            "previous_time_ms must be a real number, got %r" % (previous_time_ms,)
        )
    previous = float(previous_time_ms)
    if not math.isfinite(previous) or previous < 0.0:
        raise ValueError(
            "previous_time_ms must be non-negative and finite, got %g" % previous
        )
    return previous + required_interval_ms(constraints)


def spacing_violations(constraints, times):
    """Return one record per consecutive pair spaced closer than admitted."""
    schedule = validate_schedule(times)
    required = required_interval_ms(constraints)
    violations = []
    for i in range(1, len(schedule)):
        gap = schedule[i] - schedule[i - 1]
        shortfall = required - gap
        if shortfall > 0.0 and not math.isclose(
            shortfall, 0.0, rel_tol=0.0, abs_tol=INTERVAL_TOLERANCE_MS
        ):
            violations.append(
                {
                    "index": i,
                    "previous_time_ms": schedule[i - 1],
                    "time_ms": schedule[i],
                    "gap_ms": gap,
                    "shortfall_ms": shortfall,
                }
            )
    return violations


def repair_schedule_ms(constraints, times):
    """Return the earliest admissible schedule that keeps the command order."""
    schedule = validate_schedule(times)
    required = required_interval_ms(constraints)
    repaired = [schedule[0]]
    for requested in schedule[1:]:
        repaired.append(max(requested, repaired[-1] + required))
    return repaired


def assess_on_command_spacing(spec):
    """Grade one channel's on-command schedule against clause 5.4.1.4.1.

    spec keys: category, declared_min_interval_ms, optional
    thermal_recovery_ms and inrush_settling_ms, and command_times_ms.
    """
    if not isinstance(spec, dict):
        raise ValueError("spacing spec must be a mapping")
    if "command_times_ms" not in spec:
        raise ValueError("spacing spec missing required key 'command_times_ms'")
    constraints = validate_constraints(spec)
    schedule = validate_schedule(spec["command_times_ms"])

    scope_findings = []
    findings = []

    in_scope = constraints["category"] in EXTERNALLY_COMMANDED_CATEGORIES
    if not in_scope:
        scope_findings.append(
            "category %s is not switched on by an external command, so the "
            "clause places no on-command spacing on it" % constraints["category"]
        )

    required = required_interval_ms(constraints)
    governing = governing_constraint(constraints)
    declared = constraints["declared_min_interval_ms"]

    if governing != "declared_min_interval_ms":
        findings.append(
            "the declared minimum interval %g ms is shorter than the %g ms set "
            "by %s; a command issued at the declared figure re-triggers the "
            "channel before it has recovered"
            % (declared, required, governing.replace("_", " "))
        )

    violations = spacing_violations(constraints, schedule)
    for violation in violations:
        findings.append(
            "command %d at %g ms follows the previous one by %g ms, %g ms short "
            "of the %g ms the channel requires"
            % (
                violation["index"],
                violation["time_ms"],
                violation["gap_ms"],
                violation["shortfall_ms"],
                required,
            )
        )

    repaired = repair_schedule_ms(constraints, schedule)
    admissible = not findings

    if not in_scope:
        verdict = "out-of-scope"
    elif admissible:
        verdict = "compliant"
    else:
        verdict = "non-compliant"

    return {
        "category": constraints["category"],
        "in_scope": in_scope,
        "declared_min_interval_ms": declared,
        "required_interval_ms": required,
        "governing_constraint": governing,
        "max_on_command_rate_hz": max_on_command_rate_hz(constraints),
        "command_count": len(schedule),
        "gaps_ms": command_gaps_ms(schedule),
        "violations": violations,
        "repaired_schedule_ms": repaired,
        "schedule_shift_ms": repaired[-1] - schedule[-1],
        "admissible": admissible,
        "verdict": verdict,
        "findings": scope_findings + findings,
    }
