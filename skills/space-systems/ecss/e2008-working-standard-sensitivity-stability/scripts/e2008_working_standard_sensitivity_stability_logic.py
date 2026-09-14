#!/usr/bin/env python3
"""Sensitivity stability of a group of secondary working standards.

Anchor: ECSS-E-ST-20-08C clause 10.2.2.3.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The question the clause asks is whether a working standard still has the
sensitivity it was calibrated with. It cannot be answered from that
standard alone, because a single device read on two occasions gives one
number that moved, and nothing in that number says whether the device
changed or the light did. So the comparison is made across a group of at
least five standards read in the same session: the group carries its own
reference, and the session light level cancels.

The method therefore has three layers.

Normalise. Short-circuit current depends on cell temperature, so every
reading is corrected back to the reference temperature before anything is
compared. Comparing raw currents taken at different temperatures reports
the thermometer, not the device.

Ratio. Within one session each normalised reading is divided by the
median of the group. Whatever the source was doing that day multiplies
every device equally and divides straight back out, so the ratio is a
property of the device and not of the session.

Track. The ratio series for one device across sessions is what drift
actually looks like. Total change from first to last session says where
it ended up; a least-squares slope over elapsed days, annualised, says
how fast it is going; and the largest excursion from the starting ratio
catches a device that wandered out and came back, which a first-to-last
comparison reports as perfectly stable.

One blind spot is handled explicitly. If every device in the group moved
together, the ratios do not move at all, because they are ratios. The
absolute group level is therefore tracked as well: a shift of the whole
group is either the source or a correlated drift of every standard, and
either way the campaign cannot certify the group until it is explained.

Dispositions are sensitivity-stable, refer-for-review and drifted.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math
import statistics

DAYS_PER_YEAR = 365.25

STABLE = "sensitivity-stable"
REFER = "refer-for-review"
DRIFTED = "sensitivity-drifted"
STANDARD_DISPOSITIONS = (STABLE, REFER, DRIFTED)

_SEVERITY_ORDER = {STABLE: 0, REFER: 1, DRIFTED: 2}

GROUP_STABLE = "working-standard-group-stable"
GROUP_REFERRED = "working-standard-group-referred"
GROUP_UNSTABLE = "working-standard-group-unstable"

_VERDICT_BY_SEVERITY = {
    STABLE: GROUP_STABLE,
    REFER: GROUP_REFERRED,
    DRIFTED: GROUP_UNSTABLE,
}

DEFAULT_STABILITY_CRITERIA = {
    # the clause compares a group, and a group below five devices cannot
    # carry a median that is robust to one of its own members moving
    "min_group_size": 5,
    "min_sessions": 3,
    "reference_temperature_c": 25.0,
    # where the device ended up, as a share of where it started
    "max_ratio_drift_fraction": 0.0050,
    "ratio_drift_review_factor": 2.0,
    # how fast it is going, annualised from the least-squares slope
    "max_annual_drift_fraction": 0.0050,
    "annual_drift_review_factor": 2.0,
    # the furthest it went, even if it came back
    "max_ratio_excursion_fraction": 0.0100,
    # one session in which the group does not agree with itself
    "max_session_scatter_fraction": 0.0300,
    # the whole group moving together, which ratios cannot see
    "max_common_mode_shift_fraction": 0.0100,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_finite(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_finite(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_finite(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    Every limit here is compared against a ratio of measured currents or
    a least-squares slope, so a value that should sit exactly on a limit
    can evaluate a few units in the last place above it. The limit is
    never widened; only the comparison tolerates the representation
    error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = STABLE
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_stability_criteria(criteria):
    """Check a stability criteria set is complete and self-consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    group_size = _require_count(
        "criteria min_group_size", criteria.get("min_group_size"), minimum=1
    )
    if group_size < 5:
        raise ValueError(
            "the clause compares a group of at least five standards; a "
            "min_group_size of %d cannot carry the comparison" % group_size
        )
    sessions = _require_count(
        "criteria min_sessions", criteria.get("min_sessions"), minimum=1
    )
    if sessions < 2:
        raise ValueError(
            "drift needs at least two sessions to be visible, got %d" % sessions
        )
    _require_finite(
        "criteria reference_temperature_c", criteria.get("reference_temperature_c")
    )
    for key in (
        "max_ratio_drift_fraction",
        "max_annual_drift_fraction",
        "max_ratio_excursion_fraction",
        "max_session_scatter_fraction",
        "max_common_mode_shift_fraction",
    ):
        fraction = _require_positive("criteria %s" % key, criteria.get(key))
        if fraction >= 1.0:
            raise ValueError(
                "criteria %s is a share of a measured current and a whole "
                "unit of it is not a tolerance, got %r" % (key, fraction)
            )
    for key in ("ratio_drift_review_factor", "annual_drift_review_factor"):
        factor = _require_positive("criteria %s" % key, criteria.get(key))
        if factor < 1.0:
            raise ValueError(
                "criteria %s must be at least one; a review band cannot be "
                "tighter than the accept band, got %r" % (key, factor)
            )
    if not _at_most(
        criteria["max_ratio_drift_fraction"], criteria["max_ratio_excursion_fraction"]
    ):
        raise ValueError(
            "a device may not be allowed to end up further from its start "
            "than the furthest it was ever allowed to go: %r against %r"
            % (
                criteria["max_ratio_drift_fraction"],
                criteria["max_ratio_excursion_fraction"],
            )
        )
    return criteria


def normalize_short_circuit_current(
    current_a, temperature_c, alpha_per_c, reference_temperature_c
):
    """Correct one short-circuit-current reading to the reference temperature.

    Short-circuit current rises with cell temperature, so a reading taken
    warm looks like a more sensitive device. The correction divides the
    reading by the temperature factor that produced it, which is what
    makes two readings taken months apart comparable at all.
    """
    current = _require_positive("current_a", current_a)
    temperature = _require_finite("temperature_c", temperature_c)
    reference = _require_finite("reference_temperature_c", reference_temperature_c)
    alpha = _require_finite("alpha_per_c", alpha_per_c)
    if not -1.0 < alpha < 1.0:
        raise ValueError(
            "alpha_per_c is a relative coefficient per degree and cannot "
            "reach a whole unit, got %r" % (alpha,)
        )
    factor = 1.0 + alpha * (temperature - reference)
    if factor <= 0.0:
        raise ValueError(
            "a temperature factor of %.6f at %.2f C is not physical; the "
            "coefficient or the temperature is wrong" % (factor, temperature)
        )
    return current / factor


def session_ratios(session, alpha_per_c, criteria=DEFAULT_STABILITY_CRITERIA):
    """Normalise one session's readings and ratio each against the median.

    The median, not the mean, carries the session. One device that has
    genuinely moved would drag a mean toward itself and hide half its own
    drift; a median of five or more devices does not move for one of
    them.
    """
    validate_stability_criteria(criteria)
    if not isinstance(session, dict):
        raise ValueError("session must be a mapping, got %r" % (session,))
    session_id = _require_identifier("session_id", session.get("session_id"))
    elapsed = _require_non_negative("elapsed_days", session.get("elapsed_days"))
    readings = session.get("readings")
    if not isinstance(readings, (list, tuple)):
        raise ValueError("session %s needs a list of readings" % session_id)
    if len(readings) < criteria["min_group_size"]:
        raise ValueError(
            "session %s carries %d standards; the comparison needs at least %d"
            % (session_id, len(readings), criteria["min_group_size"])
        )
    normalized = {}
    for reading in readings:
        if not isinstance(reading, dict):
            raise ValueError("each reading must be a mapping, got %r" % (reading,))
        standard_id = _require_identifier("standard_id", reading.get("standard_id"))
        if standard_id in normalized:
            raise ValueError(
                "standard %s appears twice in session %s" % (standard_id, session_id)
            )
        normalized[standard_id] = normalize_short_circuit_current(
            reading.get("short_circuit_current_a"),
            reading.get("temperature_c"),
            reading.get("alpha_per_c", alpha_per_c),
            criteria["reference_temperature_c"],
        )
    median = statistics.median(normalized.values())
    if median <= 0.0:
        raise ValueError(
            "session %s has a non-positive median current" % (session_id,)
        )
    ratios = {key: value / median for key, value in normalized.items()}
    scatter = max(abs(value - 1.0) for value in ratios.values())
    return {
        "session_id": session_id,
        "elapsed_days": elapsed,
        "normalized_current_a": normalized,
        "median_normalized_current_a": median,
        "ratios": ratios,
        "max_scatter_fraction": scatter,
        "scatter_flagged": not _at_most(
            scatter, criteria["max_session_scatter_fraction"]
        ),
    }


def least_squares_slope(points):
    """Slope of a straight line through (x, y) points, per unit of x."""
    if not isinstance(points, (list, tuple)) or len(points) < 2:
        raise ValueError("a slope needs at least two points, got %r" % (points,))
    xs = [_require_finite("x", x) for x, _ in points]
    ys = [_require_finite("y", y) for _, y in points]
    n = float(len(xs))
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx <= 0.0:
        raise ValueError(
            "every point shares the same x value, so no slope is defined"
        )
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    return sxy / sxx


def drift_metrics(ratio_series):
    """Where a device ended up, how fast it is going, and how far it went.

    ratio_series is a list of (elapsed_days, ratio) in time order. The
    three numbers answer different questions and a device can pass two of
    them and fail the third.
    """
    if not isinstance(ratio_series, (list, tuple)) or len(ratio_series) < 2:
        raise ValueError(
            "drift needs at least two sessions, got %r" % (ratio_series,)
        )
    days = []
    ratios = []
    for elapsed, ratio in ratio_series:
        days.append(_require_non_negative("elapsed_days", elapsed))
        ratios.append(_require_positive("ratio", ratio))
    for earlier, later in zip(days, days[1:]):
        if later <= earlier:
            raise ValueError(
                "sessions must be in strict time order, got %r after %r"
                % (later, earlier)
            )
    first = ratios[0]
    last = ratios[-1]
    slope_per_day = least_squares_slope(list(zip(days, ratios)))
    return {
        "first_ratio": first,
        "last_ratio": last,
        "total_drift_fraction": last / first - 1.0,
        "annual_drift_fraction": slope_per_day * DAYS_PER_YEAR / first,
        "max_excursion_fraction": max(abs(r / first - 1.0) for r in ratios),
        "span_days": days[-1] - days[0],
    }


def assess_standard_drift(
    standard_id, ratio_series, criteria=DEFAULT_STABILITY_CRITERIA
):
    """Disposition one working standard from its ratio series."""
    validate_stability_criteria(criteria)
    _require_identifier("standard_id", standard_id)
    metrics = drift_metrics(ratio_series)

    reasons = []
    dispositions = []

    total = abs(metrics["total_drift_fraction"])
    limit = criteria["max_ratio_drift_fraction"]
    review_limit = limit * criteria["ratio_drift_review_factor"]
    if _at_most(total, limit):
        dispositions.append(STABLE)
    elif _at_most(total, review_limit):
        dispositions.append(REFER)
        reasons.append(
            "ended %.5f from where it started, past the %.5f allowance"
            % (total, limit)
        )
    else:
        dispositions.append(DRIFTED)
        reasons.append(
            "ended %.5f from where it started, past the %.5f review limit; the "
            "calibration it carries no longer describes it" % (total, review_limit)
        )

    annual = abs(metrics["annual_drift_fraction"])
    annual_limit = criteria["max_annual_drift_fraction"]
    annual_review = annual_limit * criteria["annual_drift_review_factor"]
    if _at_most(annual, annual_limit):
        dispositions.append(STABLE)
    elif _at_most(annual, annual_review):
        dispositions.append(REFER)
        reasons.append(
            "is moving at %.5f per year, past the %.5f allowance"
            % (annual, annual_limit)
        )
    else:
        dispositions.append(DRIFTED)
        reasons.append(
            "is moving at %.5f per year, past the %.5f review limit"
            % (annual, annual_review)
        )

    excursion = metrics["max_excursion_fraction"]
    excursion_limit = criteria["max_ratio_excursion_fraction"]
    if _at_most(excursion, excursion_limit):
        dispositions.append(STABLE)
    else:
        dispositions.append(REFER)
        reasons.append(
            "went %.5f from its starting ratio at some point, past the %.5f "
            "allowance, even though a first-to-last comparison would not show "
            "it" % (excursion, excursion_limit)
        )

    result = dict(metrics)
    result.update(
        {
            "standard_id": standard_id,
            "session_count": len(ratio_series),
            "disposition": _worst(dispositions),
            "reasons": reasons,
        }
    )
    return result


def assess_sensitivity_stability(campaign, criteria=DEFAULT_STABILITY_CRITERIA):
    """Clause 10.2.2.3.2 stability screen over a group of working standards."""
    validate_stability_criteria(criteria)
    if not isinstance(campaign, dict):
        raise ValueError("campaign must be a mapping, got %r" % (campaign,))
    campaign_id = _require_identifier("campaign_id", campaign.get("campaign_id"))
    alpha = _require_finite("alpha_per_c", campaign.get("alpha_per_c"))
    sessions = campaign.get("sessions")
    if not isinstance(sessions, (list, tuple)):
        raise ValueError("campaign %s needs a list of sessions" % campaign_id)
    if len(sessions) < criteria["min_sessions"]:
        raise ValueError(
            "campaign %s carries %d sessions; drift needs at least %d"
            % (campaign_id, len(sessions), criteria["min_sessions"])
        )

    resolved = [session_ratios(session, alpha, criteria) for session in sessions]
    for earlier, later in zip(resolved, resolved[1:]):
        if later["elapsed_days"] <= earlier["elapsed_days"]:
            raise ValueError(
                "sessions must be given in strict time order; %s is not after %s"
                % (later["session_id"], earlier["session_id"])
            )
    population = set(resolved[0]["ratios"])
    for session in resolved[1:]:
        if set(session["ratios"]) != population:
            missing = sorted(population - set(session["ratios"]))
            extra = sorted(set(session["ratios"]) - population)
            raise ValueError(
                "session %s does not carry the same group: missing %r, extra %r"
                % (session["session_id"], missing, extra)
            )

    findings = []
    assessed = []
    for standard_id in sorted(population):
        series = [
            (session["elapsed_days"], session["ratios"][standard_id])
            for session in resolved
        ]
        result = assess_standard_drift(standard_id, series, criteria)
        for reason in result["reasons"]:
            findings.append("%s: %s" % (standard_id, reason))
        assessed.append(result)

    verdict = _worst([result["disposition"] for result in assessed])

    for session in resolved:
        if session["scatter_flagged"]:
            verdict = _worst((verdict, REFER))
            findings.append(
                "session %s: the group disagrees with itself by %.5f, past the "
                "%.5f allowance, so the session itself is in question before "
                "any device is"
                % (
                    session["session_id"],
                    session["max_scatter_fraction"],
                    criteria["max_session_scatter_fraction"],
                )
            )

    first_level = resolved[0]["median_normalized_current_a"]
    last_level = resolved[-1]["median_normalized_current_a"]
    common_mode = last_level / first_level - 1.0
    common_mode_flagged = not _at_most(
        abs(common_mode), criteria["max_common_mode_shift_fraction"]
    )
    if common_mode_flagged:
        verdict = _worst((verdict, REFER))
        findings.append(
            "the group level moved %.5f between the first and last session, "
            "past the %.5f allowance; ratios cannot see a shift every device "
            "shares, so this is the source or the whole group drifting "
            "together" % (common_mode, criteria["max_common_mode_shift_fraction"])
        )

    return {
        "campaign_id": campaign_id,
        "group_size": len(population),
        "session_count": len(resolved),
        "span_days": resolved[-1]["elapsed_days"] - resolved[0]["elapsed_days"],
        "sessions": [
            {
                "session_id": session["session_id"],
                "elapsed_days": session["elapsed_days"],
                "median_normalized_current_a": session[
                    "median_normalized_current_a"
                ],
                "max_scatter_fraction": session["max_scatter_fraction"],
                "scatter_flagged": session["scatter_flagged"],
            }
            for session in resolved
        ],
        "flagged_session_ids": [
            session["session_id"] for session in resolved if session["scatter_flagged"]
        ],
        "standards": assessed,
        "common_mode_shift_fraction": common_mode,
        "common_mode_flagged": common_mode_flagged,
        "verdict": _VERDICT_BY_SEVERITY[verdict],
        "disposition": verdict,
        "drifted_standard_ids": [
            result["standard_id"]
            for result in assessed
            if result["disposition"] == DRIFTED
        ],
        "not_stable_ids": [
            result["standard_id"]
            for result in assessed
            if result["disposition"] != STABLE
        ],
        "findings": findings,
    }
