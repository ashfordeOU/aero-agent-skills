#!/usr/bin/env python3
"""Periodic analysis of the nonconformance records a project has collected.

Anchor: ECSS-Q-ST-10-09 clause 5.5.3, the requirement that the
nonconformance records are analysed periodically — for trends, for
causes that keep coming back, and for the indicators that feed product
assurance reporting and the corrective and preventive action process.
The procedure below is a paraphrase into implementable steps; no
standard text is reproduced.

Four things follow from what the analysis is for.

A count is not a rate. Ten nonconformances in a month of full
production and ten in a month of a single integration shift are not the
same signal, so every period is normalised by the exposure it carries
before any period is compared with any other.

A trend is a slope, not a pair of endpoints. Reading the first and last
period tells you about two periods; the least-squares slope over the
normalised rates uses all of them and does not swing on one noisy month.

A recurring cause is a share, not a tally. The largest cause group
matters when it takes a large part of the whole and has happened enough
times to be a pattern rather than a coincidence, so both the share and
the occurrence count gate the corrective action call.

The analysis has to be current to be an analysis. A study last run
further back than the analysis interval is a record of an old programme,
and the clause is not discharged by it.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

TREND_RISING = "nonconformance-rate-rising"
TREND_FALLING = "nonconformance-rate-falling"
TREND_FLAT = "nonconformance-rate-flat"

RECORDS_NOT_ANALYSED = "nonconformance-records-not-analysed"
ANALYSIS_BASIS_TOO_SHORT = "nonconformance-analysis-basis-too-short"
CORRECTIVE_ACTION_REQUIRED = "nonconformance-corrective-action-required"
TREND_UNDER_WATCH = "nonconformance-trend-under-watch"
ANALYSIS_REPORTED_NO_ACTION = "nonconformance-analysis-reported-no-action"

DEFAULT_ANALYSIS_POLICY = {
    "min_periods": 3,
    "analysis_interval_days": 90,
    "recurring_cause_share": 0.35,
    "min_recurrence_count": 3,
    "rate_alert": 0.5,
    "rising_slope_action": 0.05,
    "flat_slope_tolerance": 1e-9,
    "pareto_share": 0.8,
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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole count, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_day(name, value):
    return _require_count(name, value)


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    label = value.strip()
    if not label:
        raise ValueError("%s must not be blank" % name)
    return label


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _above(value, limit):
    """value > limit, and not merely by representation error."""
    return value > limit and not math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_analysis_policy(policy):
    """Check the policy the periodic analysis is graded against."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    periods = _require_count("min_periods", policy.get("min_periods"))
    if periods < 2:
        raise ValueError(
            "min_periods must be at least two; a trend cannot be taken over one "
            "period, got %r" % (policy.get("min_periods"),)
        )
    _require_positive(
        "analysis_interval_days", policy.get("analysis_interval_days")
    )
    _require_fraction("recurring_cause_share", policy.get("recurring_cause_share"))
    recurrence = _require_count(
        "min_recurrence_count", policy.get("min_recurrence_count")
    )
    if recurrence < 2:
        raise ValueError(
            "min_recurrence_count must be at least two; one occurrence is not a "
            "recurrence, got %r" % (policy.get("min_recurrence_count"),)
        )
    _require_positive("rate_alert", policy.get("rate_alert"))
    _require_positive("rising_slope_action", policy.get("rising_slope_action"))
    _require_number("flat_slope_tolerance", policy.get("flat_slope_tolerance"))
    _require_fraction("pareto_share", policy.get("pareto_share"))
    return policy


def validate_period_record(period):
    """Read one reporting period: what was found, and over how much work."""
    if not isinstance(period, dict):
        raise ValueError("period must be a mapping, got %r" % (period,))
    return {
        "period": _require_label("period", period.get("period")),
        "nonconformance_count": _require_count(
            "nonconformance_count", period.get("nonconformance_count")
        ),
        "exposure": _require_positive("exposure", period.get("exposure")),
    }


def validate_periods(periods):
    """Read every period, refusing the same period label twice."""
    if not isinstance(periods, (list, tuple)):
        raise ValueError("periods must be a sequence of period records")
    checked = []
    seen = set()
    for period in periods:
        record = validate_period_record(period)
        if record["period"] in seen:
            raise ValueError("period %r appears twice" % record["period"])
        seen.add(record["period"])
        checked.append(record)
    if not checked:
        raise ValueError("the analysis declares no periods at all")
    return tuple(checked)


def period_rates(periods):
    """Nonconformances per unit of exposure, period by period."""
    return tuple(
        record["nonconformance_count"] / record["exposure"]
        for record in validate_periods(periods)
    )


def mean_rate(periods):
    """Mean of the normalised period rates."""
    rates = period_rates(periods)
    return sum(rates) / float(len(rates))


def latest_rate(periods):
    """Normalised rate of the most recent period."""
    return period_rates(periods)[-1]


def total_nonconformances(periods):
    """Nonconformances counted across every period."""
    return sum(record["nonconformance_count"] for record in validate_periods(periods))


def trend_slope(periods):
    """Least-squares slope of the normalised rate against the period index."""
    rates = period_rates(periods)
    count = len(rates)
    if count < 2:
        raise ValueError("a trend needs at least two periods, got %d" % count)
    mean_index = (count - 1) / 2.0
    mean_value = sum(rates) / float(count)
    numerator = 0.0
    denominator = 0.0
    for index, rate in enumerate(rates):
        offset = index - mean_index
        numerator += offset * (rate - mean_value)
        denominator += offset * offset
    return numerator / denominator


def trend_direction(slope, policy=None):
    """Name the direction of a slope, with a flat band around zero."""
    policy = validate_analysis_policy(policy or DEFAULT_ANALYSIS_POLICY)
    value = _require_number("slope", slope)
    tolerance = abs(float(policy["flat_slope_tolerance"]))
    if abs(value) <= tolerance:
        return TREND_FLAT
    return TREND_RISING if value > 0.0 else TREND_FALLING


def validate_cause_record(cause):
    """Read one cause group: the category, and how often it came back."""
    if not isinstance(cause, dict):
        raise ValueError("cause must be a mapping, got %r" % (cause,))
    count = _require_count("count", cause.get("count"))
    if count == 0:
        raise ValueError("a cause group with no occurrences is not a group")
    return {
        "cause_category": _require_label(
            "cause_category", cause.get("cause_category")
        ),
        "count": count,
    }


def cause_totals(causes):
    """Group the cause records, summing a category declared more than once."""
    if not isinstance(causes, (list, tuple)):
        raise ValueError("causes must be a sequence of cause records")
    totals = {}
    for cause in causes:
        record = validate_cause_record(cause)
        name = record["cause_category"]
        totals[name] = totals.get(name, 0) + record["count"]
    return totals


def ranked_causes(causes):
    """Cause categories ordered by occurrences, then by name for ties."""
    totals = cause_totals(causes)
    return tuple(sorted(totals.items(), key=lambda item: (-item[1], item[0])))


def dominant_cause(causes):
    """The largest cause group, with the share of the whole it takes."""
    ranked = ranked_causes(causes)
    if not ranked:
        return None
    total = sum(count for _, count in ranked)
    name, count = ranked[0]
    return {"cause_category": name, "count": count, "share": count / float(total)}


def pareto_cause_count(causes, policy=None):
    """How many cause categories it takes to reach the Pareto share."""
    policy = validate_analysis_policy(policy or DEFAULT_ANALYSIS_POLICY)
    ranked = ranked_causes(causes)
    if not ranked:
        return 0
    total = float(sum(count for _, count in ranked))
    target = float(policy["pareto_share"])
    running = 0.0
    taken = 0
    for _, count in ranked:
        running += count / total
        taken += 1
        if _at_least(running, target):
            break
    return taken


def check_cause_consistency(periods, causes):
    """Refuse cause groups accounting for more records than were counted."""
    counted = total_nonconformances(periods)
    grouped = sum(cause_totals(causes).values())
    if grouped > counted:
        raise ValueError(
            "the cause groups account for %d nonconformances against the %d "
            "the periods counted" % (grouped, counted)
        )
    return counted - grouped


def analysis_is_current(last_analysis_day, as_of_day, policy=None):
    """True when the periodic analysis was run inside its interval."""
    policy = validate_analysis_policy(policy or DEFAULT_ANALYSIS_POLICY)
    day = _require_day("as_of_day", as_of_day)
    if last_analysis_day is None:
        return False
    last = _require_day("last_analysis_day", last_analysis_day)
    if last > day:
        raise ValueError(
            "last_analysis_day %d sits after as_of_day %d" % (last, day)
        )
    return (day - last) <= float(policy["analysis_interval_days"])


def recurrence_calls_for_action(causes, policy=None):
    """True when one cause group is both large enough and frequent enough."""
    policy = validate_analysis_policy(policy or DEFAULT_ANALYSIS_POLICY)
    dominant = dominant_cause(causes)
    if dominant is None:
        return False
    if dominant["count"] < int(policy["min_recurrence_count"]):
        return False
    return _at_least(dominant["share"], float(policy["recurring_cause_share"]))


def assess_nonconformance_records_analysis(case):
    """Grade the periodic analysis and say what it obliges the project to do."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    policy = validate_analysis_policy(case.get("policy") or DEFAULT_ANALYSIS_POLICY)

    findings = []
    advisories = []
    result = {
        "periods_analysed": 0,
        "total_nonconformances": 0,
        "mean_rate": None,
        "latest_rate": None,
        "trend_slope": None,
        "trend_direction": None,
        "dominant_cause": None,
        "pareto_cause_count": None,
        "ungrouped_records": None,
        "analysis_current": False,
        "verdict": None,
        "findings": findings,
        "advisories": advisories,
    }

    analysis = case.get("analysis")
    if analysis is None:
        findings.append(
            "no periodic analysis of the nonconformance records has been "
            "carried out, so nothing feeds the reporting or the corrective "
            "action process"
        )
        result["verdict"] = RECORDS_NOT_ANALYSED
        return result
    if not isinstance(analysis, dict):
        raise ValueError("analysis must be a mapping, got %r" % (analysis,))

    as_of_day = _require_day("as_of_day", analysis.get("as_of_day"))
    current = analysis_is_current(analysis.get("last_analysis_day"), as_of_day, policy)
    result["analysis_current"] = current
    if not current:
        findings.append(
            "the last analysis is older than the %g day interval, so the study "
            "on record describes an earlier programme"
            % float(policy["analysis_interval_days"])
        )
        result["verdict"] = RECORDS_NOT_ANALYSED
        return result

    periods = analysis.get("periods")
    if periods is None:
        raise ValueError("the analysis declares no periods to work from")
    checked = validate_periods(periods)
    causes = analysis.get("causes", ())
    ungrouped = check_cause_consistency(checked, causes)

    result["periods_analysed"] = len(checked)
    result["total_nonconformances"] = total_nonconformances(checked)
    result["ungrouped_records"] = ungrouped

    if len(checked) < int(policy["min_periods"]):
        findings.append(
            "the analysis rests on %d period(s) against the %d it owes, which "
            "is not a basis for a trend"
            % (len(checked), int(policy["min_periods"]))
        )
        result["verdict"] = ANALYSIS_BASIS_TOO_SHORT
        return result

    slope = trend_slope(checked)
    direction = trend_direction(slope, policy)
    dominant = dominant_cause(causes)

    result["mean_rate"] = mean_rate(checked)
    result["latest_rate"] = latest_rate(checked)
    result["trend_slope"] = slope
    result["trend_direction"] = direction
    result["dominant_cause"] = dominant
    result["pareto_cause_count"] = pareto_cause_count(causes, policy)

    if ungrouped > 0:
        advisories.append(
            "%d nonconformance record(s) carry no cause group, so the "
            "recurrence picture is drawn from part of the set" % ungrouped
        )

    if recurrence_calls_for_action(causes, policy):
        findings.append(
            "cause group %s holds %d records, %.3g per cent of those grouped, "
            "which is a recurring cause rather than a coincidence"
            % (
                dominant["cause_category"],
                dominant["count"],
                dominant["share"] * 100.0,
            )
        )
        result["verdict"] = CORRECTIVE_ACTION_REQUIRED
        return result

    if _above(result["latest_rate"], float(policy["rate_alert"])):
        findings.append(
            "the latest period runs at %.3g nonconformances per unit of "
            "exposure against the %.3g alert indicator"
            % (result["latest_rate"], float(policy["rate_alert"]))
        )
        result["verdict"] = CORRECTIVE_ACTION_REQUIRED
        return result

    if direction == TREND_RISING and _at_least(
        slope, float(policy["rising_slope_action"])
    ):
        findings.append(
            "the normalised rate is rising at %.3g per period, at or past the "
            "%.3g that calls for action"
            % (slope, float(policy["rising_slope_action"]))
        )
        result["verdict"] = CORRECTIVE_ACTION_REQUIRED
        return result

    if direction == TREND_RISING:
        advisories.append(
            "the normalised rate is rising at %.3g per period, below the %.3g "
            "action indicator; it is reported and watched"
            % (slope, float(policy["rising_slope_action"]))
        )
        result["verdict"] = TREND_UNDER_WATCH
        return result

    result["verdict"] = ANALYSIS_REPORTED_NO_ACTION
    return result
