"""Recording and trending of cleanliness monitoring data against its limits.

Anchor: ECSS-Q-ST-70-50C, the clause on recording and trending monitoring
results. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
A monitoring location keeps a time-ordered record of results. Conformance
today is the cheap half of the question; the record exists so that a
location walking toward its action limit is caught before it arrives. So:

1. the record is validated as a record -- ordered, non-negative, dense
   enough to trend, with no sampling gap wider than the programme allows;
2. the level statistics are formed (mean, sample spread, extremes);
3. a least-squares line is fitted over elapsed time and the drift slope
   read off it;
4. the remaining time to the action limit is projected from the fit, from
   the last observation, and reported only when the drift is rising;
5. the trailing run of points above the alert level is counted, because a
   short run of consecutive alerts is a trigger in its own right even when
   no single point reached the action limit.

The action limit is set by the programme; the alert level is derived from
it by a stated fraction, so that the alert always sits below the action.
"""

import math

__all__ = [
    "LIMIT_TOLERANCE",
    "DEFAULT_ALERT_FRACTION",
    "MIN_TREND_POINTS",
    "require_real",
    "require_int",
    "validate_series",
    "series_statistics",
    "alert_level",
    "least_squares_fit",
    "projected_days_to_limit",
    "trailing_run_above",
    "longest_rising_run",
    "recording_gaps",
    "categorize_point",
    "assess_trend",
]

# Status boundaries are compared against limits derived by multiplication;
# an exact equality can land a few ULPs either side. Absorb it here, never
# by moving the action limit.
LIMIT_TOLERANCE = 1e-9

DEFAULT_ALERT_FRACTION = 0.5

# Two points define a line but cannot distinguish drift from scatter.
MIN_TREND_POINTS = 3

STATUSES = ("conforming", "alert", "action")


def require_real(value, label, positive=False, non_negative=False):
    """Return value as a float, rejecting booleans, strings and non-finites."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive and result <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, result))
    if non_negative and result < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, result))
    return result


def require_int(value, label, non_negative=False, positive=False):
    """Return value as an int, rejecting booleans and floats."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if positive and value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    if non_negative and value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def validate_series(series):
    """Return the record as a list of (day, value) pairs, strictly time-ordered."""
    if not isinstance(series, (list, tuple)) or len(series) < 2:
        raise ValueError("series must hold at least two (day, value) points")
    points = []
    for index, item in enumerate(series):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("series[%d] must be a (day, value) pair" % index)
        day = require_real(item[0], "series[%d] day" % index)
        value = require_real(item[1], "series[%d] value" % index, non_negative=True)
        points.append((day, value))
    for i in range(1, len(points)):
        if points[i][0] <= points[i - 1][0]:
            raise ValueError(
                "series days must strictly increase; %g follows %g at index %d"
                % (points[i][0], points[i - 1][0], i)
            )
    return points


def series_statistics(series):
    """Return the mean, sample standard deviation and extremes of the record."""
    points = validate_series(series)
    values = [value for _, value in points]
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    return {
        "count": n,
        "mean": mean,
        "stdev": math.sqrt(variance),
        "minimum": min(values),
        "maximum": max(values),
        "span_days": points[-1][0] - points[0][0],
    }


def alert_level(action_limit, alert_fraction=DEFAULT_ALERT_FRACTION):
    """Derive the alert level from the action limit by the stated fraction."""
    limit = require_real(action_limit, "action_limit", positive=True)
    fraction = require_real(alert_fraction, "alert_fraction", positive=True)
    if fraction >= 1.0:
        raise ValueError(
            "alert_fraction must be below 1 so the alert sits under the action "
            "limit, got %g" % fraction
        )
    return limit * fraction


def least_squares_fit(series):
    """Fit value against day by least squares; return slope, intercept, residual."""
    points = validate_series(series)
    if len(points) < MIN_TREND_POINTS:
        raise ValueError(
            "a trend needs at least %d points, got %d" % (MIN_TREND_POINTS, len(points))
        )
    n = len(points)
    mean_day = sum(day for day, _ in points) / n
    mean_value = sum(value for _, value in points) / n
    sxx = sum((day - mean_day) ** 2 for day, _ in points)
    if sxx <= 0.0:
        raise ValueError("series days carry no spread; a slope is undefined")
    sxy = sum((day - mean_day) * (value - mean_value) for day, value in points)
    slope = sxy / sxx
    intercept = mean_value - slope * mean_day
    residual = math.sqrt(
        sum((value - (intercept + slope * day)) ** 2 for day, value in points) / n
    )
    return {
        "slope_per_day": slope,
        "intercept": intercept,
        "residual_rms": residual,
        "mean_day": mean_day,
        "mean_value": mean_value,
    }


def projected_days_to_limit(series, action_limit):
    """Project days from the last observation until the fit reaches the limit."""
    points = validate_series(series)
    limit = require_real(action_limit, "action_limit", positive=True)
    fit = least_squares_fit(points)
    slope = fit["slope_per_day"]
    last_day = points[-1][0]
    fitted_last = fit["intercept"] + slope * last_day
    if slope <= 0.0:
        return None
    if fitted_last >= limit:
        return 0.0
    return (limit - fitted_last) / slope


def trailing_run_above(series, threshold):
    """Count how many of the most recent points sit above a threshold."""
    points = validate_series(series)
    level = require_real(threshold, "threshold", non_negative=True)
    run = 0
    for _, value in reversed(points):
        if value > level and not math.isclose(
            value, level, rel_tol=LIMIT_TOLERANCE, abs_tol=0.0
        ):
            run += 1
        else:
            break
    return run


def longest_rising_run(series):
    """Return the length of the longest strictly rising stretch of the record."""
    points = validate_series(series)
    best = 1
    current = 1
    for i in range(1, len(points)):
        if points[i][1] > points[i - 1][1]:
            current += 1
            if current > best:
                best = current
        else:
            current = 1
    return best


def recording_gaps(series, max_interval_days):
    """List the sampling intervals wider than the programme allows."""
    points = validate_series(series)
    maximum = require_real(max_interval_days, "max_interval_days", positive=True)
    gaps = []
    for i in range(1, len(points)):
        interval = points[i][0] - points[i - 1][0]
        if interval > maximum and not math.isclose(
            interval, maximum, rel_tol=LIMIT_TOLERANCE, abs_tol=0.0
        ):
            gaps.append({
                "from_day": points[i - 1][0],
                "to_day": points[i][0],
                "interval_days": interval,
            })
    return gaps


def categorize_point(value, action_limit, alert_fraction=DEFAULT_ALERT_FRACTION):
    """Categorize one result as conforming, alert or action."""
    measurement = require_real(value, "value", non_negative=True)
    limit = require_real(action_limit, "action_limit", positive=True)
    alert = alert_level(limit, alert_fraction)
    if measurement > limit and not math.isclose(
        measurement, limit, rel_tol=LIMIT_TOLERANCE, abs_tol=0.0
    ):
        return "action"
    if measurement > alert and not math.isclose(
        measurement, alert, rel_tol=LIMIT_TOLERANCE, abs_tol=0.0
    ):
        return "alert"
    return "conforming"


def assess_trend(spec):
    """Trend a monitoring record against its alert and action levels.

    spec keys: series (day, value pairs), action_limit, optional
    alert_fraction, max_interval_days, max_alert_run, horizon_days.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("series", "action_limit"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    points = validate_series(spec["series"])
    limit = require_real(spec["action_limit"], "action_limit", positive=True)
    fraction = require_real(
        spec.get("alert_fraction", DEFAULT_ALERT_FRACTION), "alert_fraction",
        positive=True,
    )
    alert = alert_level(limit, fraction)
    max_alert_run = require_int(spec.get("max_alert_run", 3), "max_alert_run",
                                positive=True)
    horizon = require_real(spec.get("horizon_days", 90.0), "horizon_days",
                           positive=True)
    statistics = series_statistics(points)
    statuses = [categorize_point(value, limit, fraction) for _, value in points]
    findings = []
    trend = None
    days_to_limit = None
    if len(points) < MIN_TREND_POINTS:
        findings.append(
            "record holds %d points; at least %d are needed before a drift can be "
            "separated from scatter" % (len(points), MIN_TREND_POINTS)
        )
    else:
        trend = least_squares_fit(points)
        days_to_limit = projected_days_to_limit(points, limit)
        if days_to_limit is not None and days_to_limit <= horizon:
            findings.append(
                "the fitted drift reaches the action limit in %.1f days, inside the "
                "%.0f day horizon" % (days_to_limit, horizon)
            )
    if "max_interval_days" in spec:
        gaps = recording_gaps(points, spec["max_interval_days"])
        for gap in gaps:
            findings.append(
                "sampling gap of %.1f days between day %.1f and day %.1f exceeds the "
                "recording interval" % (gap["interval_days"], gap["from_day"],
                                        gap["to_day"])
            )
    else:
        gaps = []
    run = trailing_run_above(points, alert)
    if run >= max_alert_run:
        findings.append(
            "%d consecutive results above the alert level %.4g; the run is itself a "
            "trigger" % (run, alert)
        )
    if statuses[-1] == "action":
        findings.append(
            "the latest result %.4g exceeds the action limit %.4g"
            % (points[-1][1], limit)
        )
    return {
        "statistics": statistics,
        "statuses": statuses,
        "latest_status": statuses[-1],
        "alert_level": alert,
        "action_limit": limit,
        "trend": trend,
        "days_to_action_limit": days_to_limit,
        "trailing_alert_run": run,
        "longest_rising_run": longest_rising_run(points),
        "gaps": gaps,
        "findings": findings,
        "in_control": not findings,
    }
