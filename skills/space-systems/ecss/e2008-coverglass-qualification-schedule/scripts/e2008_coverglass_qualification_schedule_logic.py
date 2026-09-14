#!/usr/bin/env python3
"""The coverglass qualification campaign runs on a schedule that carries dates.

Anchor: ECSS-E-ST-20-08C clause 8.6.2. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The production and test schedule underpinning a coverglass qualification is
a dated document, and the dates are the content. A list of steps in the
right order is a sequence; a list of steps with planned start and end dates
is a schedule, and only the second can be checked against the day the
qualified coverglass is owed. So four things are asked of every step:

    presence    is the step declared at all, and is it a step this campaign
                knows about
    precedence  does it start on or after the day the steps it depends on
                finish -- which list position never shows, because a step
                can sit fifth in the list and still be planned to start in
                week one
    duration    does an exposure hold its article for the minimum dwell the
                campaign sets, rather than being compressed to fit
    milestone   does the campaign finish on or before the date the customer
                needs the qualified coverglass by, and with how much float

The arms are ranked rather than merged. An absent prerequisite is reported
ahead of a dated precedence break, because there is nothing to move the step
behind; a precedence break ahead of a shortened dwell, because re-dating the
step usually changes its dwell anyway; and a shortened dwell ahead of a
milestone overrun, because a campaign still holding an invalid exposure has
no finish date worth comparing.

Dates are ISO calendar dates supplied by the caller. Nothing is read from
the clock, so the same plan returns the same verdict every run.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math
from datetime import date

COVERGLASS_STEP_KINDS = (
    "production",
    "measurement",
    "environmental",
    "documentation",
)

# min_duration_days  the shortest the step may be planned to run for
REQUIRED_COVERGLASS_QUALIFICATION_STEPS = {
    "coverglass-lot-manufacture": {
        "kind": "production",
        "prerequisites": (),
        "min_duration_days": 1,
    },
    "coverglass-lot-identification": {
        "kind": "production",
        "prerequisites": ("coverglass-lot-manufacture",),
        "min_duration_days": 1,
    },
    "coverglass-incoming-visual-inspection": {
        "kind": "measurement",
        "prerequisites": ("coverglass-lot-identification",),
        "min_duration_days": 1,
    },
    "coverglass-dimensional-measurement": {
        "kind": "measurement",
        "prerequisites": ("coverglass-incoming-visual-inspection",),
        "min_duration_days": 1,
    },
    "coverglass-baseline-transmittance-measurement": {
        "kind": "measurement",
        "prerequisites": ("coverglass-incoming-visual-inspection",),
        "min_duration_days": 2,
    },
    "coverglass-surface-resistivity-measurement": {
        "kind": "measurement",
        "prerequisites": ("coverglass-incoming-visual-inspection",),
        "min_duration_days": 1,
    },
    "coverglass-thermal-cycling": {
        "kind": "environmental",
        "prerequisites": (
            "coverglass-baseline-transmittance-measurement",
            "coverglass-dimensional-measurement",
        ),
        "min_duration_days": 21,
    },
    "coverglass-ultraviolet-exposure": {
        "kind": "environmental",
        "prerequisites": ("coverglass-baseline-transmittance-measurement",),
        "min_duration_days": 30,
    },
    "coverglass-particle-irradiation": {
        "kind": "environmental",
        "prerequisites": ("coverglass-baseline-transmittance-measurement",),
        "min_duration_days": 7,
    },
    "coverglass-humidity-exposure": {
        "kind": "environmental",
        "prerequisites": ("coverglass-baseline-transmittance-measurement",),
        "min_duration_days": 10,
    },
    "coverglass-post-exposure-transmittance-measurement": {
        "kind": "measurement",
        "prerequisites": (
            "coverglass-thermal-cycling",
            "coverglass-ultraviolet-exposure",
            "coverglass-particle-irradiation",
            "coverglass-humidity-exposure",
        ),
        "min_duration_days": 2,
    },
    "coverglass-post-exposure-visual-inspection": {
        "kind": "measurement",
        "prerequisites": (
            "coverglass-thermal-cycling",
            "coverglass-ultraviolet-exposure",
            "coverglass-particle-irradiation",
            "coverglass-humidity-exposure",
        ),
        "min_duration_days": 1,
    },
    "coverglass-qualification-report": {
        "kind": "documentation",
        "prerequisites": (
            "coverglass-post-exposure-transmittance-measurement",
            "coverglass-post-exposure-visual-inspection",
        ),
        "min_duration_days": 5,
    },
}

STEP_SCHEDULED = "step-scheduled"
STEP_PREREQUISITE_ABSENT = "step-prerequisite-absent"
STEP_STARTS_BEFORE_PREREQUISITE_ENDS = "step-starts-before-prerequisite-ends"
STEP_DWELL_SHORT = "step-dwell-short"
STEP_OVERRUNS_MILESTONE = "step-overruns-milestone"

STEP_VERDICT_RANK = (
    STEP_PREREQUISITE_ABSENT,
    STEP_STARTS_BEFORE_PREREQUISITE_ENDS,
    STEP_DWELL_SHORT,
    STEP_OVERRUNS_MILESTONE,
    STEP_SCHEDULED,
)

SCHEDULE_RUNNABLE = "coverglass-schedule-runnable"
SCHEDULE_NOT_RUNNABLE = "coverglass-schedule-not-runnable"

DEFAULT_COVERGLASS_SCHEDULE_POLICY = {
    "require_every_step_declared": True,
    "enforce_dated_precedence": True,
    "enforce_minimum_dwell": True,
    "enforce_milestone": True,
    "min_milestone_float_days": 10,
    "min_declared_step_fraction": 1.0,
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
        raise ValueError("%s must be a whole number of days, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _require_fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return value


def _require_date(name, value):
    if isinstance(value, date):
        return value
    text = _require_text(name, value)
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO calendar date, got %r" % (name, value))


def validate_schedule_policy(policy):
    """Check a coverglass schedule policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "require_every_step_declared",
        "enforce_dated_precedence",
        "enforce_minimum_dwell",
        "enforce_milestone",
    ):
        _require_flag(key, policy.get(key))
    _require_count("min_milestone_float_days", policy.get("min_milestone_float_days"))
    _require_fraction(
        "min_declared_step_fraction", policy.get("min_declared_step_fraction")
    )
    return policy


def required_coverglass_qualification_steps():
    """The dated steps a coverglass qualification campaign is read against."""
    return {
        name: dict(spec)
        for name, spec in REQUIRED_COVERGLASS_QUALIFICATION_STEPS.items()
    }


def normalise_schedule(steps):
    """Read the declared dated steps, refusing anything that cannot be run."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("steps must be a non-empty sequence of mappings")
    read = {}
    for step in steps:
        if not isinstance(step, dict):
            raise ValueError("step must be a mapping, got %r" % (step,))
        name = _require_text("name", step.get("name"))
        if name not in REQUIRED_COVERGLASS_QUALIFICATION_STEPS:
            raise ValueError(
                "schedule declares %s, which is not a coverglass qualification "
                "step" % name
            )
        if name in read:
            raise ValueError("schedule declares step %s twice" % name)
        starts_on = _require_date("starts_on", step.get("starts_on"))
        ends_on = _require_date("ends_on", step.get("ends_on"))
        if ends_on < starts_on:
            raise ValueError(
                "step %s ends on %s, before it starts on %s"
                % (name, ends_on.isoformat(), starts_on.isoformat())
            )
        read[name] = {
            "name": name,
            "kind": REQUIRED_COVERGLASS_QUALIFICATION_STEPS[name]["kind"],
            "starts_on": starts_on,
            "ends_on": ends_on,
            "duration_days": (ends_on - starts_on).days + 1,
        }
    return read


def step_duration_days(step):
    """How many calendar days the declared step is planned to occupy."""
    if not isinstance(step, dict):
        raise ValueError("step must be a mapping, got %r" % (step,))
    starts_on = _require_date("starts_on", step.get("starts_on"))
    ends_on = _require_date("ends_on", step.get("ends_on"))
    if ends_on < starts_on:
        raise ValueError("step ends before it starts")
    return (ends_on - starts_on).days + 1


def resolve_dated_precedence(schedule):
    """Split each step's prerequisites into the absent and the too-late."""
    if not isinstance(schedule, dict) or not schedule:
        raise ValueError("schedule must be a non-empty mapping of read steps")
    resolution = {}
    for name, entry in schedule.items():
        spec = REQUIRED_COVERGLASS_QUALIFICATION_STEPS[name]
        absent = []
        late = []
        for prerequisite in spec["prerequisites"]:
            if prerequisite not in schedule:
                absent.append(prerequisite)
                continue
            if schedule[prerequisite]["ends_on"] > entry["starts_on"]:
                late.append(prerequisite)
        resolution[name] = {
            "absent_prerequisites": sorted(absent),
            "late_prerequisites": sorted(late),
            "satisfied": not absent and not late,
        }
    return resolution


def campaign_window(schedule):
    """The first day the campaign touches an article and the last."""
    if not isinstance(schedule, dict) or not schedule:
        raise ValueError("schedule must be a non-empty mapping of read steps")
    starts = min(entry["starts_on"] for entry in schedule.values())
    ends = max(entry["ends_on"] for entry in schedule.values())
    return {
        "campaign_start": starts.isoformat(),
        "campaign_end": ends.isoformat(),
        "span_days": (ends - starts).days + 1,
    }


def milestone_float_days(schedule, required_by):
    """Days between the last scheduled day and the day the coverglass is owed."""
    window = campaign_window(schedule)
    owed = _require_date("required_by", required_by)
    ends = date.fromisoformat(window["campaign_end"])
    return (owed - ends).days


def assess_schedule_step(
    name, schedule, resolution, required_by, policy=DEFAULT_COVERGLASS_SCHEDULE_POLICY
):
    """Verdict for one dated step, with the arms ranked."""
    validate_schedule_policy(policy)
    name = _require_text("name", name)
    if name not in schedule:
        raise ValueError("step %s is not in the read schedule" % name)
    entry = schedule[name]
    resolved = resolution[name]
    spec = REQUIRED_COVERGLASS_QUALIFICATION_STEPS[name]
    owed = _require_date("required_by", required_by)
    minimum = spec["min_duration_days"]
    dwell_ok = entry["duration_days"] >= minimum
    within_milestone = entry["ends_on"] <= owed

    findings = []
    if resolved["absent_prerequisites"]:
        verdict = STEP_PREREQUISITE_ABSENT
        findings.append(
            "step %s depends on %s, and the schedule does not declare it at all"
            % (name, ", ".join(resolved["absent_prerequisites"]))
        )
    elif policy["enforce_dated_precedence"] and resolved["late_prerequisites"]:
        verdict = STEP_STARTS_BEFORE_PREREQUISITE_ENDS
        findings.append(
            "step %s starts on %s, before %s finishes"
            % (
                name,
                entry["starts_on"].isoformat(),
                ", ".join(resolved["late_prerequisites"]),
            )
        )
    elif policy["enforce_minimum_dwell"] and not dwell_ok:
        verdict = STEP_DWELL_SHORT
        findings.append(
            "step %s is planned for %d days against a minimum dwell of %d"
            % (name, entry["duration_days"], minimum)
        )
    elif policy["enforce_milestone"] and not within_milestone:
        verdict = STEP_OVERRUNS_MILESTONE
        findings.append(
            "step %s finishes on %s, after the qualified coverglass is owed on %s"
            % (name, entry["ends_on"].isoformat(), owed.isoformat())
        )
    else:
        verdict = STEP_SCHEDULED

    return {
        "name": name,
        "kind": entry["kind"],
        "starts_on": entry["starts_on"].isoformat(),
        "ends_on": entry["ends_on"].isoformat(),
        "duration_days": entry["duration_days"],
        "min_duration_days": minimum,
        "dwell_sufficient": dwell_ok,
        "within_milestone": within_milestone,
        "absent_prerequisites": resolved["absent_prerequisites"],
        "late_prerequisites": resolved["late_prerequisites"],
        "verdict": verdict,
        "scheduled": verdict == STEP_SCHEDULED,
        "findings": findings,
    }


def worst_step_verdict(verdicts):
    """The step verdict that has to be closed first across the campaign."""
    if not isinstance(verdicts, (list, tuple, set, frozenset)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    ranked = []
    for verdict in verdicts:
        verdict = _require_text("verdict", verdict)
        if verdict not in STEP_VERDICT_RANK:
            raise ValueError("unknown step verdict %s" % verdict)
        ranked.append(STEP_VERDICT_RANK.index(verdict))
    return STEP_VERDICT_RANK[min(ranked)]


def assess_coverglass_qualification_schedule(
    plan, policy=DEFAULT_COVERGLASS_SCHEDULE_POLICY
):
    """Full clause 8.6.2 sweep over a dated coverglass qualification schedule."""
    validate_schedule_policy(policy)
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    campaign_id = _require_text("campaign_id", plan.get("campaign_id"))
    required_by = _require_date("required_by", plan.get("required_by"))
    schedule = normalise_schedule(plan.get("steps"))
    resolution = resolve_dated_precedence(schedule)

    assessments = [
        assess_schedule_step(name, schedule, resolution, required_by, policy)
        for name in sorted(schedule)
    ]

    findings = []
    undeclared = sorted(
        set(REQUIRED_COVERGLASS_QUALIFICATION_STEPS) - set(schedule)
    )
    if policy["require_every_step_declared"]:
        for name in undeclared:
            findings.append(
                "campaign %s declares no %s at all" % (campaign_id, name)
            )
    for entry in assessments:
        findings.extend(entry["findings"])

    window = campaign_window(schedule)
    float_days = milestone_float_days(schedule, required_by)
    required_float = policy["min_milestone_float_days"]
    float_ok = True
    if policy["enforce_milestone"]:
        float_ok = float_days >= required_float
        if not float_ok:
            findings.append(
                "campaign %s finishes on %s against a need date of %s, leaving "
                "%d days of float where %d are required"
                % (
                    campaign_id,
                    window["campaign_end"],
                    required_by.isoformat(),
                    float_days,
                    required_float,
                )
            )

    total = len(REQUIRED_COVERGLASS_QUALIFICATION_STEPS)
    declared_fraction = len(schedule) / float(total)
    minimum = float(policy["min_declared_step_fraction"])
    declared_ok = _at_least(declared_fraction, minimum)
    if not declared_ok:
        findings.append(
            "the schedule declares %d of %d coverglass qualification steps "
            "against a required share of %.3f" % (len(schedule), total, minimum)
        )

    open_steps = sorted(
        entry["name"] for entry in assessments if not entry["scheduled"]
    )
    grouped = {}
    for entry in assessments:
        grouped.setdefault(entry["verdict"], []).append(entry["name"])

    runnable = (
        declared_ok
        and float_ok
        and not open_steps
        and not (policy["require_every_step_declared"] and undeclared)
    )
    return {
        "verdict": SCHEDULE_RUNNABLE if runnable else SCHEDULE_NOT_RUNNABLE,
        "campaign_id": campaign_id,
        "required_by": required_by.isoformat(),
        "campaign_window": window,
        "milestone_float_days": float_days,
        "required_milestone_float_days": required_float,
        "milestone_float_sufficient": float_ok,
        "step_assessments": assessments,
        "grouped_by_verdict": {k: sorted(v) for k, v in grouped.items()},
        "undeclared_steps": undeclared,
        "open_step_ids": open_steps,
        "worst_verdict": worst_step_verdict(
            [entry["verdict"] for entry in assessments]
        ),
        "declared_step_fraction": declared_fraction,
        "required_step_fraction": minimum,
        "every_step_declared": not undeclared,
        "findings": findings,
    }
