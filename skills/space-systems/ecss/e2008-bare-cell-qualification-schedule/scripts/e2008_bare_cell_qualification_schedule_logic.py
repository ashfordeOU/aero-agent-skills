#!/usr/bin/env python3
"""Production and test schedule for qualifying a bare solar cell.

Anchor: ECSS-E-ST-20-08C clause 7.4.2. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A bare cell is qualified by running one identified cell lot through an
ordered sequence of production, measurement, environmental and destructive
steps, and the order carries the meaning. A measurement taken before the
lot was marked cannot be traced back to the cells it describes; an
environmental exposure run before the illuminated baseline leaves nothing
to read the degradation against; a destructive pull test run early takes
cells out of the lot that the later exposures were counting on.

So a declared bare cell schedule is asked three questions:

    presence      is every required step actually in the sequence
    order         does each step follow the steps it depends on, rather
                  than merely appearing somewhere in the list
    lot supply    can the lot still field the sample each step needs, at
                  the point that step is declared, after the destructive
                  steps ahead of it have retired their cells

The lot is a live pool, not a budget. Every step draws a sample; only the
destructive steps retire what they drew. Two schedules that retire the same
number of cells in total therefore run out at different steps, and the step
that runs out is the one the lot size has to be argued against.

The three arms are ranked. An absent prerequisite is reported ahead of a
misplaced step, and a misplaced step ahead of a sample shortfall, because
enlarging a lot for a sequence still in the wrong order buys cells for a
campaign nobody can run.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import copy

BARE_CELL_STEP_KINDS = (
    "production",
    "measurement",
    "environmental",
    "destructive",
    "documentation",
)

# sample_size  cells the step needs available when it runs
# cells_retired  cells the step permanently removes from the lot
REQUIRED_BARE_CELL_STEPS = {
    "cell-lot-manufacture": {
        "kind": "production",
        "prerequisites": (),
        "sample_size": 0,
        "cells_retired": 0,
    },
    "lot-identification-marking": {
        "kind": "production",
        "prerequisites": ("cell-lot-manufacture",),
        "sample_size": 0,
        "cells_retired": 0,
    },
    "initial-visual-inspection": {
        "kind": "measurement",
        "prerequisites": ("lot-identification-marking",),
        "sample_size": 6,
        "cells_retired": 0,
    },
    "dimension-and-thickness-measurement": {
        "kind": "measurement",
        "prerequisites": ("initial-visual-inspection",),
        "sample_size": 6,
        "cells_retired": 0,
    },
    "initial-illuminated-iv-measurement": {
        "kind": "measurement",
        "prerequisites": ("initial-visual-inspection",),
        "sample_size": 6,
        "cells_retired": 0,
    },
    "spectral-response-measurement": {
        "kind": "measurement",
        "prerequisites": ("initial-illuminated-iv-measurement",),
        "sample_size": 3,
        "cells_retired": 0,
    },
    "bare-cell-thermal-cycling": {
        "kind": "environmental",
        "prerequisites": (
            "initial-illuminated-iv-measurement",
            "dimension-and-thickness-measurement",
        ),
        "sample_size": 4,
        "cells_retired": 0,
    },
    "bare-cell-humidity-exposure": {
        "kind": "environmental",
        "prerequisites": ("initial-illuminated-iv-measurement",),
        "sample_size": 4,
        "cells_retired": 0,
    },
    "bare-cell-particle-irradiation": {
        "kind": "environmental",
        "prerequisites": (
            "initial-illuminated-iv-measurement",
            "spectral-response-measurement",
        ),
        "sample_size": 4,
        "cells_retired": 4,
    },
    "contact-adhesion-pull-test": {
        "kind": "destructive",
        "prerequisites": (
            "initial-visual-inspection",
            "initial-illuminated-iv-measurement",
        ),
        "sample_size": 3,
        "cells_retired": 3,
    },
    "reverse-bias-endurance-test": {
        "kind": "destructive",
        "prerequisites": ("initial-illuminated-iv-measurement",),
        "sample_size": 2,
        "cells_retired": 2,
    },
    "final-illuminated-iv-measurement": {
        "kind": "measurement",
        "prerequisites": (
            "bare-cell-thermal-cycling",
            "bare-cell-humidity-exposure",
        ),
        "sample_size": 4,
        "cells_retired": 0,
    },
    "final-visual-inspection": {
        "kind": "measurement",
        "prerequisites": (
            "bare-cell-thermal-cycling",
            "bare-cell-humidity-exposure",
        ),
        "sample_size": 4,
        "cells_retired": 0,
    },
    "bare-cell-qualification-report": {
        "kind": "documentation",
        "prerequisites": (
            "final-illuminated-iv-measurement",
            "final-visual-inspection",
            "bare-cell-particle-irradiation",
            "contact-adhesion-pull-test",
            "reverse-bias-endurance-test",
        ),
        "sample_size": 0,
        "cells_retired": 0,
    },
}

STEP_SCHEDULED = "step-scheduled"
STEP_PREREQUISITE_ABSENT = "step-prerequisite-absent"
STEP_OUT_OF_ORDER = "step-out-of-order"
STEP_SAMPLE_UNAVAILABLE = "step-sample-unavailable"

STEP_VERDICT_ORDER = {
    STEP_SCHEDULED: 0,
    STEP_SAMPLE_UNAVAILABLE: 1,
    STEP_OUT_OF_ORDER: 2,
    STEP_PREREQUISITE_ABSENT: 3,
}

SCHEDULE_RUNNABLE = "bare-cell-schedule-runnable"
SCHEDULE_NOT_RUNNABLE = "bare-cell-schedule-not-runnable"

DEFAULT_BARE_CELL_SCHEDULE_POLICY = {
    "retest_reserve_cells": 2,
    "require_report_last": True,
    "require_marking_before_measurement": True,
}


def required_bare_cell_steps():
    """A private copy of the required step set, safe to edit."""
    return copy.deepcopy(REQUIRED_BARE_CELL_STEPS)


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def validate_bare_cell_schedule_policy(policy):
    """Check a schedule policy is complete and usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_count("policy retest_reserve_cells", policy.get("retest_reserve_cells"))
    _require_flag("policy require_report_last", policy.get("require_report_last"))
    _require_flag(
        "policy require_marking_before_measurement",
        policy.get("require_marking_before_measurement"),
    )
    return policy


def _normalise_sequence(sequence):
    if not isinstance(sequence, (list, tuple)):
        raise ValueError("sequence must be a list of step names, got %r" % (sequence,))
    if not sequence:
        raise ValueError("sequence must name at least one step")
    seen = []
    for entry in sequence:
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError("every step name must be a non-empty string, got %r" % (entry,))
        name = entry.strip()
        if name not in REQUIRED_BARE_CELL_STEPS:
            raise ValueError(
                "%r is not a bare cell qualification step; known steps are %s"
                % (name, ", ".join(sorted(REQUIRED_BARE_CELL_STEPS)))
            )
        if name in seen:
            raise ValueError("step %r appears twice in the sequence" % (name,))
        seen.append(name)
    return tuple(seen)


def resolve_step_prerequisites(sequence):
    """Split every step's prerequisites into absent ones and late ones.

    Presence and position are separate questions. A prerequisite nobody
    declared cannot be fixed by moving anything; a prerequisite declared
    after the step that needs it is a reordering.
    """
    order = _normalise_sequence(sequence)
    position = dict((name, index) for index, name in enumerate(order))
    resolved = {}
    for name in order:
        absent = []
        late = []
        for need in REQUIRED_BARE_CELL_STEPS[name]["prerequisites"]:
            if need not in position:
                absent.append(need)
            elif position[need] > position[name]:
                late.append(need)
        resolved[name] = {
            "position": position[name],
            "absent_prerequisites": tuple(absent),
            "late_prerequisites": tuple(late),
        }
    return resolved


def walk_cell_lot(sequence, lot_size):
    """Run the lot through the declared order, one step at a time.

    Every step draws a sample from the cells still in the lot; only the
    destructive steps retire what they drew. The walk reports the opening
    and closing balance at each step and the first step the lot cannot
    supply.
    """
    order = _normalise_sequence(sequence)
    _require_count("lot_size", lot_size, minimum=1)
    available = lot_size
    walk = []
    exhausted_at = None
    total_retired = 0
    for name in order:
        spec = REQUIRED_BARE_CELL_STEPS[name]
        sample = spec["sample_size"]
        retired = spec["cells_retired"]
        short = sample > available
        if short and exhausted_at is None:
            exhausted_at = name
        drawn = min(sample, available)
        actually_retired = min(retired, drawn)
        closing = available - actually_retired
        walk.append(
            {
                "step": name,
                "kind": spec["kind"],
                "opening_cells": available,
                "sample_size": sample,
                "cells_short": max(sample - available, 0),
                "cells_retired": actually_retired,
                "closing_cells": closing,
                "sample_available": not short,
            }
        )
        total_retired += actually_retired
        available = closing
    return {
        "lot_size": lot_size,
        "steps": walk,
        "cells_retired_total": total_retired,
        "cells_remaining": available,
        "exhausted_at": exhausted_at,
    }


def assess_schedule_step(name, resolution, walk_entry):
    """Rank one step's three arms into a single step verdict."""
    if name not in REQUIRED_BARE_CELL_STEPS:
        raise ValueError("%r is not a bare cell qualification step" % (name,))
    if not isinstance(resolution, dict) or not isinstance(walk_entry, dict):
        raise ValueError("resolution and walk_entry must both be mappings")
    findings = []
    verdict = STEP_SCHEDULED
    if resolution.get("absent_prerequisites"):
        verdict = STEP_PREREQUISITE_ABSENT
        findings.append(
            "%s depends on %s, which the sequence never declares"
            % (name, ", ".join(resolution["absent_prerequisites"]))
        )
    elif resolution.get("late_prerequisites"):
        verdict = STEP_OUT_OF_ORDER
        findings.append(
            "%s is placed ahead of %s, which it depends on"
            % (name, ", ".join(resolution["late_prerequisites"]))
        )
    elif not walk_entry.get("sample_available", True):
        verdict = STEP_SAMPLE_UNAVAILABLE
        findings.append(
            "%s needs %d cells and the lot holds %d where it is placed"
            % (name, walk_entry["sample_size"], walk_entry["opening_cells"])
        )
    return {"step": name, "verdict": verdict, "findings": findings}


def _worst_step_verdict(verdicts):
    worst = STEP_SCHEDULED
    for verdict in verdicts:
        if STEP_VERDICT_ORDER[verdict] > STEP_VERDICT_ORDER[worst]:
            worst = verdict
    return worst


def assess_bare_cell_schedule(plan, policy=DEFAULT_BARE_CELL_SCHEDULE_POLICY):
    """Clause 7.4.2 assessment of one declared bare cell schedule."""
    validate_bare_cell_schedule_policy(policy)
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    lot_id = plan.get("lot_id")
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("plan needs a non-empty lot_id")
    sequence = _normalise_sequence(plan.get("sequence"))
    lot_size = _require_count("plan lot_size", plan.get("lot_size"), minimum=1)

    resolved = resolve_step_prerequisites(sequence)
    walk = walk_cell_lot(sequence, lot_size)
    by_step = dict((entry["step"], entry) for entry in walk["steps"])

    steps = []
    findings = []
    counts = dict((state, 0) for state in STEP_VERDICT_ORDER)
    for name in sequence:
        result = assess_schedule_step(name, resolved[name], by_step[name])
        counts[result["verdict"]] += 1
        steps.append(result)
        findings.extend(result["findings"])

    undeclared = tuple(
        name for name in sorted(REQUIRED_BARE_CELL_STEPS) if name not in sequence
    )
    if undeclared:
        findings.append(
            "%d required steps are not in the sequence: %s"
            % (len(undeclared), ", ".join(undeclared))
        )

    reserve = policy["retest_reserve_cells"]
    reserve_met = walk["cells_remaining"] >= reserve
    if not reserve_met:
        findings.append(
            "the lot ends with %d cells against a retest reserve of %d; a lot "
            "sized to the campaign leaves nothing for a repeat"
            % (walk["cells_remaining"], reserve)
        )

    report_last = True
    if policy["require_report_last"] and "bare-cell-qualification-report" in sequence:
        report_last = sequence[-1] == "bare-cell-qualification-report"
        if not report_last:
            findings.append(
                "the qualification report is not the last step; a report closed "
                "before the last test describes a campaign that had not finished"
            )

    marking_ok = True
    if policy["require_marking_before_measurement"]:
        marked = resolved.get("lot-identification-marking")
        first_measurement = None
        for name in sequence:
            if REQUIRED_BARE_CELL_STEPS[name]["kind"] == "measurement":
                first_measurement = resolved[name]["position"]
                break
        if first_measurement is not None:
            if marked is None or marked["position"] > first_measurement:
                marking_ok = False
                findings.append(
                    "a measurement runs before the lot is marked, so its result "
                    "cannot be traced back to the cells it describes"
                )

    worst = _worst_step_verdict([result["verdict"] for result in steps])
    runnable = (
        worst == STEP_SCHEDULED
        and not undeclared
        and reserve_met
        and report_last
        and marking_ok
    )
    return {
        "lot_id": lot_id,
        "verdict": SCHEDULE_RUNNABLE if runnable else SCHEDULE_NOT_RUNNABLE,
        "worst_step_verdict": worst,
        "steps": steps,
        "step_verdict_counts": counts,
        "undeclared_steps": undeclared,
        "declared_fraction": len(sequence) / float(len(REQUIRED_BARE_CELL_STEPS)),
        "cell_walk": walk,
        "retest_reserve_met": reserve_met,
        "report_closes_schedule": report_last,
        "marking_precedes_measurement": marking_ok,
        "findings": findings,
    }
