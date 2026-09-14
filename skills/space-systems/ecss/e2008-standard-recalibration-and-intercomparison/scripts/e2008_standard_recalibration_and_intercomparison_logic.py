#!/usr/bin/env python3
"""Recalibration and intercomparison schedule for solar-array standards.

Anchor: ECSS-E-ST-20-08C clause 10.2.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A standard cell does not announce that it has moved. It keeps producing
a plausible current while its calibration quietly drifts, so the clause
puts two independent controls on it, both at intervals the customer has
agreed rather than at intervals the laboratory finds convenient:

    recalibration     the standard goes back to the calibrating body
    intercomparison   the standards are cross-checked against each other

The two answer different questions. A calendar says the standard is
in-date; an intercomparison says the standard still agrees with the one
above it. Either can fail while the other passes, and a deviation that
has left the agreed band outranks any amount of calendar validity --
an in-date certificate does not make a drifted cell correct.

A series of past intercomparisons is more than a pass record: fitted
against elapsed days it gives a drift rate, and the drift rate projects
the day the deviation will reach the agreed band edge. That projection
is what turns a schedule into a decision, because it says whether the
next agreed interval lands before or after the standard goes out.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STANDARD_ROLES = ("primary-standard", "working-standard")
ACTIVITIES = ("recalibration", "intercomparison")

STATUS_IN_DATE = "in-date"
STATUS_DUE_SOON = "due-soon"
STATUS_OVERDUE = "overdue"

DEVIATION_WITHIN_BAND = "within-band"
DEVIATION_OUT_OF_BAND = "out-of-band"

VERDICT_FIT = "in-date-and-consistent"
VERDICT_DUE_SOON = "calibration-due-soon"
VERDICT_INTERCOMPARISON_OVERDUE = "intercomparison-overdue"
VERDICT_RECALIBRATION_OVERDUE = "recalibration-overdue"
VERDICT_OUT_OF_BAND = "intercomparison-out-of-band"

DAYS_PER_YEAR = 365.25

DEFAULT_SCHEDULE_POLICY = {
    "recalibration_interval_days": 730.0,
    "intercomparison_interval_days": 182.0,
    "deviation_band_percent": 1.0,
    "warning_fraction": 0.9,
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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A deviation sitting exactly on the agreed band edge, or a day count
    landing exactly on the agreed interval, must read the same on every
    platform. The band and the interval are never widened; only the
    comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _is_zero(value):
    return math.isclose(value, 0.0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def validate_schedule_policy(policy):
    """Check an agreed-interval policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "recalibration_interval_days", policy.get("recalibration_interval_days")
    )
    _require_positive(
        "intercomparison_interval_days", policy.get("intercomparison_interval_days")
    )
    _require_positive("deviation_band_percent", policy.get("deviation_band_percent"))
    fraction = _require_positive("warning_fraction", policy.get("warning_fraction"))
    if fraction > 1.0:
        raise ValueError(
            "warning_fraction must not exceed one, got %r" % (fraction,)
        )
    if float(policy["intercomparison_interval_days"]) > float(
        policy["recalibration_interval_days"]
    ):
        raise ValueError(
            "the intercomparison interval must not be longer than the "
            "recalibration interval; the cross-check exists to bridge it"
        )
    return policy


def agreed_interval_days(activity, case=None, policy=DEFAULT_SCHEDULE_POLICY):
    """Interval in force, with a customer-agreed value beating the default."""
    _require_choice("activity", activity, ACTIVITIES)
    validate_schedule_policy(policy)
    key = "%s_interval_days" % activity.replace("-", "_")
    agreed_key = "agreed_%s" % key
    if isinstance(case, dict) and case.get(agreed_key) is not None:
        return _require_positive(agreed_key, case[agreed_key])
    return float(policy[key])


def interval_status(days_since, interval_days, warning_fraction=0.9):
    """Where a day count sits inside an agreed interval."""
    elapsed = _require_non_negative("days_since", days_since)
    interval = _require_positive("interval_days", interval_days)
    fraction_limit = _require_positive("warning_fraction", warning_fraction)
    if fraction_limit > 1.0:
        raise ValueError("warning_fraction must not exceed one")
    fraction = elapsed / interval
    if not _at_most(elapsed, interval):
        status = STATUS_OVERDUE
    elif not _at_most(fraction, fraction_limit):
        status = STATUS_DUE_SOON
    else:
        status = STATUS_IN_DATE
    return {
        "days_since": elapsed,
        "interval_days": interval,
        "days_remaining": interval - elapsed,
        "fraction_elapsed": fraction,
        "status": status,
    }


def relative_deviation_percent(working_value, primary_value):
    """Signed deviation of a working standard against the primary, percent."""
    working = _require_positive("working_value", working_value)
    primary = _require_positive("primary_value", primary_value)
    return 100.0 * (working - primary) / primary


def deviation_status(deviation_percent, band_percent):
    """Whether a deviation is inside the band the customer agreed."""
    deviation = _require_number("deviation_percent", deviation_percent)
    band = _require_positive("band_percent", band_percent)
    if _at_most(abs(deviation), band):
        return DEVIATION_WITHIN_BAND
    return DEVIATION_OUT_OF_BAND


def _normalize_history(history):
    if isinstance(history, dict) or not isinstance(history, (list, tuple)):
        raise ValueError("history must be a list of mappings, got %r" % (history,))
    if len(history) < 2:
        raise ValueError("a drift rate needs at least two intercomparisons")
    points = []
    for entry in history:
        if not isinstance(entry, dict):
            raise ValueError("history entry must be a mapping, got %r" % (entry,))
        day = _require_number("day", entry.get("day"))
        deviation = _require_number(
            "deviation_percent", entry.get("deviation_percent")
        )
        points.append((day, deviation))
    points.sort(key=lambda pair: pair[0])
    for earlier, later in zip(points, points[1:]):
        if _is_zero(later[0] - earlier[0]):
            raise ValueError(
                "two intercomparisons share day %g; the history is ambiguous"
                % earlier[0]
            )
    return points


def drift_rate_percent_per_year(history):
    """Least-squares drift of the deviation across past intercomparisons."""
    points = _normalize_history(history)
    count = float(len(points))
    mean_day = sum(day for day, _ in points) / count
    mean_dev = sum(dev for _, dev in points) / count
    covariance = sum((day - mean_day) * (dev - mean_dev) for day, dev in points)
    variance = sum((day - mean_day) ** 2 for day, _ in points)
    if _is_zero(variance):
        raise ValueError("every intercomparison sits on the same day; no drift is fittable")
    return (covariance / variance) * DAYS_PER_YEAR


def days_to_band_edge(deviation_percent, drift_rate_percent_per_year_value, band_percent):
    """Days until the drift carries the deviation onto the agreed band edge.

    Returns None when the deviation is not moving toward an edge, and
    zero when it is already outside the band.
    """
    deviation = _require_number("deviation_percent", deviation_percent)
    drift = _require_number(
        "drift_rate_percent_per_year", drift_rate_percent_per_year_value
    )
    band = _require_positive("band_percent", band_percent)
    if not _at_most(abs(deviation), band):
        return 0.0
    if _is_zero(drift):
        return None
    edge = band if drift > 0.0 else -band
    remaining = edge - deviation
    if remaining / drift <= 0.0:
        return None
    return (remaining / drift) * DAYS_PER_YEAR


def plan_standard_recalibration(case, policy=DEFAULT_SCHEDULE_POLICY):
    """Full clause 10.2.5 schedule and consistency check for one standard."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_schedule_policy(policy)
    role = _require_choice("role", case.get("role"), STANDARD_ROLES)
    warning = _require_positive(
        "warning_fraction", case.get("warning_fraction", policy["warning_fraction"])
    )
    band = _require_positive(
        "deviation_band_percent",
        case.get("deviation_band_percent", policy["deviation_band_percent"]),
    )
    recal = interval_status(
        case.get("days_since_recalibration"),
        agreed_interval_days("recalibration", case, policy),
        warning,
    )
    inter = interval_status(
        case.get("days_since_intercomparison"),
        agreed_interval_days("intercomparison", case, policy),
        warning,
    )
    findings = []
    deviation = None
    deviation_grade = None
    if case.get("working_standard_isc_a") is not None:
        deviation = relative_deviation_percent(
            case.get("working_standard_isc_a"), case.get("primary_standard_isc_a")
        )
        deviation_grade = deviation_status(deviation, band)
    drift = None
    projection = None
    if case.get("intercomparison_history") is not None:
        drift = drift_rate_percent_per_year(case["intercomparison_history"])
        if deviation is not None:
            projection = days_to_band_edge(deviation, drift, band)
    if deviation_grade == DEVIATION_OUT_OF_BAND:
        verdict = VERDICT_OUT_OF_BAND
        findings.append(
            "the working standard deviates %.3f%% from the primary against an "
            "agreed band of %.3f%%; an in-date certificate does not make a "
            "drifted cell correct" % (deviation, band)
        )
    elif recal["status"] == STATUS_OVERDUE:
        verdict = VERDICT_RECALIBRATION_OVERDUE
        findings.append(
            "recalibration is %.1f days past the agreed interval"
            % (-recal["days_remaining"])
        )
    elif inter["status"] == STATUS_OVERDUE:
        verdict = VERDICT_INTERCOMPARISON_OVERDUE
        findings.append(
            "intercomparison is %.1f days past the agreed interval"
            % (-inter["days_remaining"])
        )
    elif STATUS_DUE_SOON in (recal["status"], inter["status"]):
        verdict = VERDICT_DUE_SOON
        findings.append(
            "an agreed interval is inside its warning fraction; book the slot "
            "before the standard falls out of date"
        )
    else:
        verdict = VERDICT_FIT
    if projection is not None and not _is_zero(projection):
        next_due = min(recal["days_remaining"], inter["days_remaining"])
        if projection < next_due:
            findings.append(
                "the fitted drift reaches the band edge in %.1f days, before the "
                "next agreed activity at %.1f days; shorten the interval"
                % (projection, next_due)
            )
    if role == "primary-standard" and inter["status"] != STATUS_IN_DATE:
        findings.append(
            "a primary standard has no higher artefact to be checked against, so "
            "its schedule rests on recalibration by the calibrating body"
        )
    return {
        "role": role,
        "recalibration": recal,
        "intercomparison": inter,
        "deviation_percent": deviation,
        "deviation_band_percent": band,
        "deviation_status": deviation_grade,
        "drift_rate_percent_per_year": drift,
        "days_to_band_edge": projection,
        "verdict": verdict,
        "usable_for_measurement": verdict in (VERDICT_FIT, VERDICT_DUE_SOON),
        "findings": findings,
    }
