#!/usr/bin/env python3
"""Periodic correlation of a daily working standard to a primary reference.

Anchor: ECSS-E-ST-20-08C clause 10.2.2.3.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A working standard is the cell that goes on the simulator every morning.
It is handled, thermally cycled, re-connected and left under the lamp,
and none of that leaves a mark a user would notice. The clause keeps it
honest by correlating it against a primary reference at an agreed
interval, so the question this module answers has three parts.

    is the correlation current      the interval is agreed in advance;
                                    what matters is the time since the
                                    last correlation, and a standard
                                    approaching its interval is a
                                    different report from one past it
    has the standard moved          each correlation is a ratio of the
                                    working reading to the reference
                                    reading; drift is that ratio against
                                    the ratio the baseline correlation
                                    recorded, not against a nominal
    is the movement real            a drift smaller than the expanded
                                    uncertainty of the correlation is
                                    not evidence the standard moved; it
                                    is evidence the method cannot see a
                                    move that small

Trend outranks any single step. Three correlations that each move a
tenth of a percent the same way are a standard on its way out, even
though no single step is near the limit, so consecutive same-sign steps
are counted and reported in their own right.

Uncertainty components are combined as a root sum of squares, which
assumes they are independent; a correlation whose components share a
source states that in its budget rather than relying on this module.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime
import math

UNCERTAINTY_COMPONENTS = (
    "primary-reference",
    "transfer-measurement",
    "working-standard-repeatability",
    "temperature-correction",
    "spectral-mismatch",
)

INTERVAL_STATES = ("within-interval", "correlation-due", "correlation-overdue")

VERIFICATION_DEFECTS = (
    "correlation-overdue",
    "cumulative-drift-beyond-limit",
    "step-drift-beyond-limit",
    "expanded-uncertainty-beyond-limit",
    "systematic-drift-trend",
)

TRACEABLE_VERDICT = "working-standard-traceable"
DUE_VERDICT = "working-standard-correlation-due"
OUT_OF_LIMIT_VERDICT = "working-standard-out-of-limit"

DEFAULT_LIMITS = {
    "drift_limit_percent": 0.5,
    "expanded_uncertainty_limit_percent": 2.0,
    "coverage_factor": 2.0,
    "due_window_fraction": 0.9,
    "systematic_run_limit": 3,
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


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A drift is a ratio of ratios and an expanded uncertainty a square
    root; either can land a few units in the last place from the bound
    it should sit on, and differently on two platforms. The bound is
    never loosened, only the comparison tolerates that error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _exceeds(value, limit):
    """value > limit with the same representation error absorbed."""
    return not _at_most(value, limit)


def parse_day(name, value):
    """Read one ISO calendar day, rejecting anything else."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string, got %r" % (name, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not an ISO calendar day: %r" % (name, value))


def validate_limits(limits):
    """Check the acceptance limits are present, finite and in range."""
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping, got %r" % (limits,))
    missing = set(DEFAULT_LIMITS) - set(limits)
    if missing:
        raise ValueError("limits are missing: %s" % ", ".join(sorted(missing)))
    _require_positive("drift_limit_percent", limits["drift_limit_percent"])
    _require_positive(
        "expanded_uncertainty_limit_percent", limits["expanded_uncertainty_limit_percent"]
    )
    _require_positive("coverage_factor", limits["coverage_factor"])
    fraction = _require_positive("due_window_fraction", limits["due_window_fraction"])
    if fraction > 1.0:
        raise ValueError(
            "due_window_fraction must not exceed one, got %r"
            % (limits["due_window_fraction"],)
        )
    run_limit = limits["systematic_run_limit"]
    if not isinstance(run_limit, int) or isinstance(run_limit, bool) or run_limit < 2:
        raise ValueError("systematic_run_limit must be an integer of at least two")
    return limits


def validate_uncertainty_budget(components):
    """Normalise the correlation uncertainty budget, in percent."""
    if not isinstance(components, dict) or not components:
        raise ValueError("the uncertainty budget must be a non-empty mapping")
    budget = {}
    for name in sorted(components):
        if name not in UNCERTAINTY_COMPONENTS:
            raise ValueError(
                "unknown uncertainty component %r; expected one of %s"
                % (name, ", ".join(UNCERTAINTY_COMPONENTS))
            )
        budget[name] = _require_non_negative("uncertainty component %s" % name, components[name])
    if "primary-reference" not in budget:
        raise ValueError(
            "the budget must carry the primary-reference component; "
            "an omitted term is unknown, not zero"
        )
    return budget


def combined_standard_uncertainty_percent(components):
    """Root sum of squares of the independent budget components."""
    budget = validate_uncertainty_budget(components)
    return math.sqrt(sum(value * value for value in budget.values()))


def expanded_uncertainty_percent(components, coverage_factor=2.0):
    """Combined uncertainty widened by the stated coverage factor."""
    factor = _require_positive("coverage_factor", coverage_factor)
    return factor * combined_standard_uncertainty_percent(components)


def validate_correlation(record):
    """Normalise one correlation against the primary reference."""
    if not isinstance(record, dict):
        raise ValueError("correlation must be a mapping, got %r" % (record,))
    day = parse_day("correlation date", record.get("date"))
    reference = _require_positive("reference_value_a", record.get("reference_value_a"))
    working = _require_positive("working_value_a", record.get("working_value_a"))
    return {
        "date": day,
        "reference_value_a": reference,
        "working_value_a": working,
        "ratio": working / reference,
        "laboratory": _require_identifier(
            "laboratory", record.get("laboratory", "unstated-laboratory")
        ),
    }


def validate_history(records):
    """Normalise a correlation history, oldest first and strictly ordered."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("history must be a non-empty sequence of correlations")
    history = []
    previous = None
    for record in records:
        entry = validate_correlation(record)
        if previous is not None and entry["date"] <= previous:
            raise ValueError(
                "correlation history is not in ascending date order at %s"
                % entry["date"].isoformat()
            )
        previous = entry["date"]
        history.append(entry)
    return tuple(history)


def cumulative_drift_percent(history):
    """Movement of the latest correlation against the baseline one."""
    entries = history if isinstance(history, tuple) else validate_history(history)
    baseline = entries[0]["ratio"]
    latest = entries[-1]["ratio"]
    return (latest / baseline - 1.0) * 100.0


def step_drifts_percent(history):
    """Movement between each pair of consecutive correlations."""
    entries = history if isinstance(history, tuple) else validate_history(history)
    return tuple(
        (entries[position]["ratio"] / entries[position - 1]["ratio"] - 1.0) * 100.0
        for position in range(1, len(entries))
    )


def longest_same_sign_run(history):
    """Longest run of consecutive steps moving the same way."""
    steps = step_drifts_percent(history)
    longest = 0
    current = 0
    previous_sign = 0
    for step in steps:
        sign = 0
        if _exceeds(abs(step), 0.0):
            sign = 1 if step > 0.0 else -1
        if sign == 0:
            current = 0
            previous_sign = 0
            continue
        current = current + 1 if sign == previous_sign else 1
        previous_sign = sign
        longest = max(longest, current)
    return longest


def elapsed_days(history, assessment_date):
    """Days between the latest correlation and the day being assessed."""
    entries = history if isinstance(history, tuple) else validate_history(history)
    day = parse_day("assessment date", assessment_date)
    delta = (day - entries[-1]["date"]).days
    if delta < 0:
        raise ValueError(
            "the assessment day %s precedes the latest correlation %s"
            % (day.isoformat(), entries[-1]["date"].isoformat())
        )
    return delta


def interval_state(elapsed, agreed_interval_days, due_window_fraction=0.9):
    """Whether the agreed interval is intact, approaching or passed."""
    days = _require_non_negative("elapsed days", elapsed)
    interval = _require_positive("agreed_interval_days", agreed_interval_days)
    fraction = _require_positive("due_window_fraction", due_window_fraction)
    if fraction > 1.0:
        raise ValueError("due_window_fraction must not exceed one")
    if _exceeds(days, interval):
        return "correlation-overdue"
    if _exceeds(days, fraction * interval) or math.isclose(
        days, fraction * interval, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        return "correlation-due"
    return "within-interval"


def drift_is_significant(drift_percent, expanded_percent):
    """Whether a movement is larger than the method can explain."""
    movement = abs(_require_number("drift_percent", drift_percent))
    expanded = _require_non_negative("expanded_percent", expanded_percent)
    return _exceeds(movement, expanded)


def assess_working_standard_verification(case, limits=DEFAULT_LIMITS):
    """Full clause 10.2.2.3.5 check of one working standard's correlations."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_limits(limits)
    identifier = _require_identifier("standard id", case.get("id"))
    history = validate_history(case.get("history"))
    interval_days = _require_positive(
        "agreed_interval_days", case.get("agreed_interval_days")
    )
    budget = validate_uncertainty_budget(case.get("uncertainty_budget"))
    combined = combined_standard_uncertainty_percent(budget)
    expanded = expanded_uncertainty_percent(budget, limits["coverage_factor"])
    elapsed = elapsed_days(history, case.get("assessment_date"))
    state = interval_state(elapsed, interval_days, limits["due_window_fraction"])
    cumulative = cumulative_drift_percent(history)
    steps = step_drifts_percent(history)
    run = longest_same_sign_run(history)
    defects = []
    if state == "correlation-overdue":
        defects.append(
            {
                "defect": "correlation-overdue",
                "detail": "%d days since the last correlation against an agreed %d"
                % (elapsed, int(interval_days)),
            }
        )
    if _exceeds(abs(cumulative), limits["drift_limit_percent"]):
        defects.append(
            {
                "defect": "cumulative-drift-beyond-limit",
                "detail": "the standard has moved %.6f %% from its baseline" % cumulative,
            }
        )
    for position, step in enumerate(steps, start=1):
        if _exceeds(abs(step), limits["drift_limit_percent"]):
            defects.append(
                {
                    "defect": "step-drift-beyond-limit",
                    "detail": "correlation %d moved %.6f %% from the one before it"
                    % (position, step),
                }
            )
    if _exceeds(expanded, limits["expanded_uncertainty_limit_percent"]):
        defects.append(
            {
                "defect": "expanded-uncertainty-beyond-limit",
                "detail": "the correlation carries %.6f %% expanded uncertainty" % expanded,
            }
        )
    if run >= limits["systematic_run_limit"]:
        defects.append(
            {
                "defect": "systematic-drift-trend",
                "detail": "%d consecutive correlations moved the same way" % run,
            }
        )
    findings = ["%s: %s" % (d["defect"], d["detail"]) for d in defects]
    out_of_limit = any(d["defect"] != "correlation-overdue" for d in defects)
    overdue = state == "correlation-overdue"
    if out_of_limit or overdue:
        verdict = OUT_OF_LIMIT_VERDICT
    elif state == "correlation-due":
        verdict = DUE_VERDICT
    else:
        verdict = TRACEABLE_VERDICT
    return {
        "standard": identifier,
        "correlation_count": len(history),
        "latest_correlation": history[-1]["date"].isoformat(),
        "elapsed_days": elapsed,
        "agreed_interval_days": interval_days,
        "interval_state": state,
        "combined_standard_uncertainty_percent": combined,
        "expanded_uncertainty_percent": expanded,
        "cumulative_drift_percent": cumulative,
        "step_drifts_percent": steps,
        "same_sign_run": run,
        "drift_is_significant": drift_is_significant(cumulative, expanded),
        "defects": defects,
        "findings": findings,
        "verdict": verdict,
        "traceable": verdict == TRACEABLE_VERDICT,
    }
