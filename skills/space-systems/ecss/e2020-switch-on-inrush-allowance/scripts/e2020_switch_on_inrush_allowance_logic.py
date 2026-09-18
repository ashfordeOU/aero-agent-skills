#!/usr/bin/env python3
"""Switch-on inrush allowance of a protected power line.

Anchor: ECSS-E-ST-20-20C clause 5.3.2.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Turning a protected line on is the one moment the load is allowed to
draw more than the class current of its line. The allowance is narrow
and it is conditional: the excess is permitted only while the input
filter of the load is being charged, and only for as long as that
charging takes. Everything else above the class current is an overdraw
with a turn-on story attached to it.

That makes the check an ATTRIBUTION problem before it is an arithmetic
one. A turn-on profile is walked segment by segment, every segment above
the class current is picked out, and each one has to name input-filter
charging as its cause. A segment above the class current that is there
because the load has already been enabled, or because a downstream
converter has begun its own soft start, is not covered by this clause
however short it is.

The arithmetic then has three parts:

    how long the filter actually needs. While the limiter is limiting,
    its output is a current source, but the load is being served from
    the same current, so the charge is done by what is LEFT OVER:
    C*V / (I_limit - I_steady). Charging at the full limiting current is
    the common error and it understates the duration

    whether the excess fits. The whole turn-on excess has to be over
    before the limiter opens, so it is compared, with margin, against
    the SHORTEST trip-off delay rather than a nominal one

    whether the declared excess matches the need. An excess much longer
    than the filter requires is unattributed draw wearing a filter
    label; one much shorter says the filter never finished charging and
    the profile does not describe the real turn-on

Finally the profile has to settle: once the filter is charged the
current returns below the class current, which is where the steady-state
clause takes over. A profile that ends above the class current has not
completed a turn-on, it has started an overload.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SEGMENT_FIELDS = ("label", "cause", "current_a", "duration_s")
CAUSES = (
    "input-filter-charging",
    "load-operation",
    "converter-soft-start",
    "secondary-bus-energising",
    "undetermined",
)
PERMITTED_EXCESS_CAUSE = "input-filter-charging"

VERDICT_ALLOWED = "switch-on-excess-within-the-inrush-allowance"
VERDICT_NOT_ALLOWED = "switch-on-excess-outside-the-inrush-allowance"

FINDING_UNATTRIBUTED_EXCESS = (
    "excess-above-the-class-current-not-attributed-to-input-filter-charging"
)
FINDING_EXCESS_OUTRUNS_TRIP = "turn-on-excess-outruns-the-shortest-trip-off-delay"
FINDING_EXCESS_LONGER_THAN_NEED = "declared-excess-longer-than-the-input-filter-needs"
FINDING_EXCESS_SHORTER_THAN_NEED = "declared-excess-shorter-than-the-input-filter-needs"
FINDING_NO_SETTLING = "turn-on-profile-does-not-settle-below-the-class-current"
FINDING_PEAK_ABOVE_LIMITING = (
    "turn-on-peak-above-the-limiting-current-the-line-can-deliver"
)
ADVISORY_WINDOW_USE = "turn-on-excess-consumes-most-of-the-shortest-trip-off-delay"

# Placeholder turn-on profile: the shape a project's own profile takes.
DEFAULT_TURN_ON_PROFILE = (
    {
        "label": "input-filter-charge",
        "cause": "input-filter-charging",
        "current_a": 2.20,
        "duration_s": 5.5e-3,
    },
    {
        "label": "post-charge-operation",
        "cause": "load-operation",
        "current_a": 1.05,
        "duration_s": 20.0e-3,
    },
)

DEFAULT_INRUSH_POLICY = {
    "trip_off_time_margin": 1.20,
    "attribution_tolerance": 0.15,
    "window_advisory_fraction": 0.80,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A charge duration is a product divided by a difference, so a case
    meant to sit exactly on the trip-off delay can land a few units in
    the last place the wrong side of it. The delay is never widened;
    only the comparison tolerates the error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _strictly_below(value, limit):
    """value < limit, treating an exact landing on the limit as NOT below."""
    if math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return False
    return value < limit


def _strictly_above(value, limit):
    """value > limit, treating an exact landing on the limit as NOT above."""
    if math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return False
    return value > limit


def validate_inrush_policy(policy):
    """Check the trip-off margin, attribution band and advisory floor."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    margin = _require_positive(
        "trip_off_time_margin", policy.get("trip_off_time_margin")
    )
    if margin < 1.0:
        raise ValueError(
            "trip_off_time_margin below one relaxes the trip-off delay, got %r"
            % (margin,)
        )
    tolerance = _require_positive(
        "attribution_tolerance", policy.get("attribution_tolerance")
    )
    if tolerance >= 1.0:
        raise ValueError(
            "attribution_tolerance at or beyond unity accepts any duration, got %r"
            % (tolerance,)
        )
    fraction = _require_positive(
        "window_advisory_fraction", policy.get("window_advisory_fraction")
    )
    if fraction > 1.0:
        raise ValueError(
            "window_advisory_fraction must not exceed one, got %r" % (fraction,)
        )
    return policy


def validate_segment(segment):
    """Check one turn-on profile segment names a cause and a duration."""
    if not isinstance(segment, dict):
        raise ValueError("segment must be a mapping, got %r" % (segment,))
    missing = [f for f in SEGMENT_FIELDS if f not in segment]
    if missing:
        raise ValueError("segment is missing fields: %s" % ", ".join(sorted(missing)))
    label = segment["label"]
    if not isinstance(label, str) or not label.strip():
        raise ValueError("segment label must be a non-empty string, got %r" % (label,))
    return {
        "label": label,
        "cause": _require_choice("cause", segment["cause"], CAUSES),
        "current_a": _require_non_negative("current_a", segment["current_a"]),
        "duration_s": _require_positive("duration_s", segment["duration_s"]),
    }


def validate_profile(profile):
    """Normalise a turn-on profile and require unique segment labels."""
    if isinstance(profile, dict) or not hasattr(profile, "__iter__"):
        raise ValueError("profile must be a sequence of mappings")
    rows = [validate_segment(s) for s in profile]
    if not rows:
        raise ValueError("turn-on profile is empty; there is nothing to attribute")
    seen = set()
    for row in rows:
        if row["label"] in seen:
            raise ValueError("turn-on profile repeats the label %r" % (row["label"],))
        seen.add(row["label"])
    return tuple(rows)


def charge_current_available_a(limiting_current_a, steady_current_a):
    """Current left over to charge the input filter while the load runs.

    The load is served from the same limited output, so the filter is
    charged by the difference. A line whose steady load already consumes
    the limiting current never finishes charging and never comes on.
    """
    limiting = _require_positive("limiting_current_a", limiting_current_a)
    steady = _require_non_negative("steady_current_a", steady_current_a)
    available = limiting - steady
    if available <= 0.0:
        raise ValueError(
            "a steady load of %g A leaves nothing of a %g A limiting current to "
            "charge the input filter" % (steady, limiting)
        )
    return available


def input_filter_charge_time_s(
    capacitance_f, bus_voltage_v, limiting_current_a, steady_current_a
):
    """Time the input filter needs at the current left over for it."""
    capacitance = _require_non_negative("capacitance_f", capacitance_f)
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    available = charge_current_available_a(limiting_current_a, steady_current_a)
    return capacitance * voltage / available


def categorize_turn_on_excess(profile, class_current_a):
    """Group the profile segments that sit above the class current.

    Segments are grouped by whether their declared cause is input-filter
    charging, which is the only cause this allowance covers.
    """
    rows = validate_profile(profile)
    rated = _require_positive("class_current_a", class_current_a)
    excess = [row for row in rows if _strictly_above(row["current_a"], rated)]
    permitted = [row for row in excess if row["cause"] == PERMITTED_EXCESS_CAUSE]
    unattributed = [row for row in excess if row["cause"] != PERMITTED_EXCESS_CAUSE]
    return {
        "class_current_a": rated,
        "segments": rows,
        "excess_segments": tuple(excess),
        "permitted_segments": tuple(permitted),
        "unattributed_segments": tuple(unattributed),
        "total_excess_duration_s": math.fsum(row["duration_s"] for row in excess),
        "attributed_duration_s": math.fsum(row["duration_s"] for row in permitted),
        "peak_current_a": max(row["current_a"] for row in rows),
    }


def settles_below_class_current(profile, class_current_a):
    """Does the profile end below the class current once charging is done."""
    rows = validate_profile(profile)
    rated = _require_positive("class_current_a", class_current_a)
    return _strictly_below(rows[-1]["current_a"], rated)


def verify_excess_within_trip_window(
    excess_duration_s, trip_off_time_min_s, margin
):
    """Does the whole turn-on excess finish before the limiter opens."""
    excess = _require_non_negative("excess_duration_s", excess_duration_s)
    window = _require_positive("trip_off_time_min_s", trip_off_time_min_s)
    factor = _require_positive("margin", margin)
    if factor < 1.0:
        raise ValueError("margin below one relaxes the trip-off delay, got %r" % factor)
    required = excess * factor
    return {
        "excess_duration_s": excess,
        "trip_off_time_min_s": window,
        "margin": factor,
        "required_time_s": required,
        "slack_s": window - required,
        "window_usage": excess / window,
        "within_trip_window": _at_most(required, window),
    }


def verify_excess_attribution(
    attributed_duration_s, charge_time_s, tolerance
):
    """Does the declared filter-charging excess match what the filter needs."""
    declared = _require_non_negative("attributed_duration_s", attributed_duration_s)
    needed = _require_non_negative("charge_time_s", charge_time_s)
    band = _require_positive("tolerance", tolerance)
    if band >= 1.0:
        raise ValueError(
            "tolerance at or beyond unity accepts any duration, got %r" % (band,)
        )
    lower = needed * (1.0 - band)
    upper = needed * (1.0 + band)
    return {
        "attributed_duration_s": declared,
        "charge_time_s": needed,
        "lower_bound_s": lower,
        "upper_bound_s": upper,
        "not_shorter_than_needed": _at_least(declared, lower),
        "not_longer_than_needed": _at_most(declared, upper),
    }


def assess_switch_on_inrush(case, policy=DEFAULT_INRUSH_POLICY):
    """Full clause 5.3.2.1.1 turn-on check with a compliance verdict."""
    validate_inrush_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    required_fields = (
        "profile",
        "class_current_a",
        "limiting_current_a",
        "steady_current_a",
        "input_filter_capacitance_f",
        "bus_voltage_v",
        "trip_off_time_min_s",
    )
    missing = [f for f in required_fields if f not in case]
    if missing:
        raise ValueError("case is missing fields: %s" % ", ".join(sorted(missing)))
    limiting = _require_positive("limiting_current_a", case["limiting_current_a"])
    rated = _require_positive("class_current_a", case["class_current_a"])
    if _at_most(limiting, rated):
        raise ValueError(
            "a limiting current of %g A at or below the class current of %g A "
            "leaves no inrush allowance to assess" % (limiting, rated)
        )
    grouped = categorize_turn_on_excess(case["profile"], rated)
    charge_time = input_filter_charge_time_s(
        case["input_filter_capacitance_f"],
        case["bus_voltage_v"],
        limiting,
        case["steady_current_a"],
    )
    window = verify_excess_within_trip_window(
        grouped["total_excess_duration_s"],
        case["trip_off_time_min_s"],
        policy["trip_off_time_margin"],
    )
    attribution = verify_excess_attribution(
        grouped["attributed_duration_s"], charge_time, policy["attribution_tolerance"]
    )
    settles = settles_below_class_current(case["profile"], rated)

    findings = []
    advisories = []
    for row in grouped["unattributed_segments"]:
        findings.append(
            "%s: segment %s draws %.4f A for %.4g s as %s"
            % (
                FINDING_UNATTRIBUTED_EXCESS,
                row["label"],
                row["current_a"],
                row["duration_s"],
                row["cause"],
            )
        )
    if _strictly_above(grouped["peak_current_a"], limiting):
        findings.append(
            "%s: %.4f A declared against a %.4f A limiting current"
            % (FINDING_PEAK_ABOVE_LIMITING, grouped["peak_current_a"], limiting)
        )
    if not window["within_trip_window"]:
        findings.append(
            "%s: %.4g s of excess needs %.4g s against a %.4g s delay"
            % (
                FINDING_EXCESS_OUTRUNS_TRIP,
                window["excess_duration_s"],
                window["required_time_s"],
                window["trip_off_time_min_s"],
            )
        )
    if not attribution["not_longer_than_needed"]:
        findings.append(
            "%s: %.4g s declared against a %.4g s charge"
            % (
                FINDING_EXCESS_LONGER_THAN_NEED,
                attribution["attributed_duration_s"],
                attribution["charge_time_s"],
            )
        )
    if not attribution["not_shorter_than_needed"]:
        findings.append(
            "%s: %.4g s declared against a %.4g s charge"
            % (
                FINDING_EXCESS_SHORTER_THAN_NEED,
                attribution["attributed_duration_s"],
                attribution["charge_time_s"],
            )
        )
    if not settles:
        findings.append(
            "%s: the profile ends at %.4f A against a class current of %.4f A"
            % (FINDING_NO_SETTLING, grouped["segments"][-1]["current_a"], rated)
        )
    if not findings and window["window_usage"] > float(
        policy["window_advisory_fraction"]
    ):
        advisories.append(
            "%s: the excess uses %.1f%% of the delay"
            % (ADVISORY_WINDOW_USE, 100.0 * window["window_usage"])
        )

    compliant = not findings
    return {
        "verdict": VERDICT_ALLOWED if compliant else VERDICT_NOT_ALLOWED,
        "compliant": compliant,
        "excess": grouped,
        "charge_time_s": charge_time,
        "charge_current_available_a": charge_current_available_a(
            limiting, case["steady_current_a"]
        ),
        "trip_window": window,
        "attribution": attribution,
        "settles_below_class_current": settles,
        "findings": findings,
        "advisories": advisories,
    }
