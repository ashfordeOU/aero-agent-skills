#!/usr/bin/env python3
"""Ground-adjustable undervoltage trip point against the nominal bus value.

Anchor: ECSS-E-ST-20-20C clause 5.4.3.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An undervoltage protection drops a load off the bus when the bus falls
too far. Where that "too far" sits is not one number chosen at design
time: the trip point is declared as a share of the nominal bus voltage
and is adjustable on the ground across a required span, because the
right setting depends on the mission, the battery and the loads that end
up behind the unit. This clause is about the span, not about one point.

Expressing the point as a share of nominal is what makes the requirement
portable. The same unit on a 28 V bus and on a 50 V bus trips at the same
fraction of its supply, so the ladder of settings is validated in per
cent and converted to volts only once the nominal value is known. A trip
point quoted straight in volts hides which bus it belongs to.

A setting is not a point either. Reference tolerance, divider tolerance,
sensing offset and drift widen every setting into a band, and it is the
band, not the label on the setting, that has to sit where the design
needs it. Two bounds close on that band from opposite directions.

From above, the whole band has to stay clear of the lowest voltage the
bus reaches in normal operation, by a declared margin. A band that
reaches into the normal operating range does not protect anything -- it
sheds the load during a manoeuvre, a battery discharge or an eclipse,
and the unit is off when it was needed.

From below, the band has to stay above the voltage under which the
protected equipment can no longer be relied on. A trip point set beneath
that floor lets the equipment run into a region where its behaviour is
not characterised, which is the situation the protection exists to
prevent.

Only settings whose band clears both bounds are usable, and the required
adjustment span has to be covered by the usable settings, not by the
ladder as printed. A unit advertising a wide adjustment whose top half
nuisance-trips is not adjustable over that span in any useful sense.

The granularity matters as much as the span. If the gap between
neighbouring settings is wider than the resolution the design calls for,
the required point may fall between two settings and neither is it.

Finally, the adjustment is a ground activity. A trip point reachable by
telecommand in flight is a different and more dangerous thing than one
set by a strap or a resistor before launch, and a design that offers it
does not meet a ground-adjustable requirement.

Comparisons are inclusive at the bound, and the tolerance below absorbs
representation error rather than widening a declared limit.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SETTING_LADDER_NOT_ESTABLISHED = "undervoltage-setting-ladder-not-established"
NOMINAL_BUS_NOT_ESTABLISHED = "nominal-bus-voltage-not-established"
REQUIRED_RANGE_NOT_ESTABLISHED = "required-adjustment-range-not-established"
ADJUSTMENT_NOT_GROUND_ONLY = "undervoltage-adjustment-not-ground-only"
THRESHOLD_RANGE_COMPLIANT = "undervoltage-threshold-range-compliant"
THRESHOLD_RANGE_DEFICIENT = "undervoltage-threshold-range-deficient"

USABLE = "setting-usable"
NUISANCE_TRIP_RISK = "setting-reaches-into-the-normal-bus-range"
BELOW_EQUIPMENT_FLOOR = "setting-sits-below-the-equipment-operating-floor"

GROUND_ADJUSTMENT_MEANS = ("strap", "link", "resistor", "potentiometer", "jumper")

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_setting(setting):
    """Read one selectable trip point, declared as a share of nominal."""
    if not isinstance(setting, dict):
        raise ValueError("a setting must be a mapping, got %r" % (setting,))
    identifier = _require_label("setting id", setting.get("id"))
    if not identifier:
        raise ValueError("a setting id must not be blank")
    percent = _require_positive(
        "percent_of_nominal on %s" % identifier, setting.get("percent_of_nominal")
    )
    if not percent < 100.0:
        raise ValueError(
            "setting %s trips at %g per cent of nominal; a point at or above "
            "the nominal bus is not an undervoltage trip"
            % (identifier, percent)
        )
    return {"id": identifier, "percent_of_nominal": percent}


def validate_setting_ladder(settings):
    """Check the selectable points form a real ladder with no repeats."""
    if not isinstance(settings, (list, tuple)):
        raise ValueError("settings must be a sequence of selectable trip points")
    if len(settings) < 2:
        raise ValueError(
            "an adjustable trip point needs at least two settings; one "
            "setting is a fixed threshold"
        )
    ladder = [validate_setting(setting) for setting in settings]
    seen_ids = set()
    seen_points = []
    for entry in ladder:
        if entry["id"] in seen_ids:
            raise ValueError("duplicate setting id %r" % entry["id"])
        seen_ids.add(entry["id"])
        for point in seen_points:
            if math.isclose(
                entry["percent_of_nominal"], point, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
            ):
                raise ValueError(
                    "two settings both trip at %g per cent of nominal, so one "
                    "of them adjusts nothing" % point
                )
        seen_points.append(entry["percent_of_nominal"])
    return tuple(sorted(ladder, key=lambda entry: entry["percent_of_nominal"]))


def threshold_volts(percent_of_nominal, nominal_bus_v):
    """Turn a share of the nominal bus into the volts the unit trips at."""
    percent = _require_positive("percent_of_nominal", percent_of_nominal)
    nominal = _require_positive("nominal_bus_v", nominal_bus_v)
    return nominal * percent / 100.0


def setting_band(threshold_v, relative_tolerance, absolute_tolerance_v):
    """Widen one nominal trip point into the band it can actually land in."""
    threshold = _require_positive("threshold_v", threshold_v)
    relative = _require_non_negative("relative_tolerance", relative_tolerance)
    if not relative < 1.0:
        raise ValueError(
            "a relative setting tolerance of %g is at or beyond unity, which "
            "leaves no trip point at all" % relative
        )
    absolute = _require_non_negative("absolute_tolerance_v", absolute_tolerance_v)
    spread = threshold * relative + absolute
    return {
        "nominal_v": threshold,
        "lower_v": threshold - spread,
        "upper_v": threshold + spread,
        "spread_v": spread,
    }


def coarsest_step_percent(ladder):
    """The widest gap between neighbouring settings, in per cent of nominal."""
    points = [entry["percent_of_nominal"] for entry in validate_setting_ladder(ladder)]
    return max(later - earlier for earlier, later in zip(points, points[1:]))


def grade_setting(setting, nominal_bus_v, limits):
    """Place one setting's band against the two bounds that close on it."""
    entry = validate_setting(setting)
    nominal = _require_positive("nominal_bus_v", nominal_bus_v)
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping, got %r" % (limits,))
    threshold = threshold_volts(entry["percent_of_nominal"], nominal)
    band = setting_band(
        threshold,
        limits.get("relative_tolerance", 0.0),
        limits.get("absolute_tolerance_v", 0.0),
    )
    minimum_bus = _require_positive(
        "minimum_steady_state_bus_v", limits.get("minimum_steady_state_bus_v")
    )
    clearance = _require_non_negative(
        "nuisance_clearance_v", limits.get("nuisance_clearance_v", 0.0)
    )
    floor = _require_positive(
        "equipment_minimum_operating_v", limits.get("equipment_minimum_operating_v")
    )
    ceiling = minimum_bus - clearance
    reasons = []
    if not _at_most(band["upper_v"], ceiling):
        reasons.append(NUISANCE_TRIP_RISK)
    if not _at_least(band["lower_v"], floor):
        reasons.append(BELOW_EQUIPMENT_FLOOR)
    return {
        "id": entry["id"],
        "percent_of_nominal": entry["percent_of_nominal"],
        "threshold_v": threshold,
        "band_lower_v": band["lower_v"],
        "band_upper_v": band["upper_v"],
        "usable_ceiling_v": ceiling,
        "usable_floor_v": floor,
        "usable": not reasons,
        "outcome": USABLE if not reasons else reasons[0],
        "reasons": tuple(reasons),
    }


def grade_ladder(settings, nominal_bus_v, limits):
    """Grade every selectable point, keeping the ladder in rising order."""
    ladder = validate_setting_ladder(settings)
    return tuple(grade_setting(entry, nominal_bus_v, limits) for entry in ladder)


def usable_span_percent(graded):
    """The lowest and highest usable settings, as shares of nominal."""
    if not isinstance(graded, (list, tuple)):
        raise ValueError("graded must be a sequence of graded settings")
    usable = [entry for entry in graded if entry["usable"]]
    if not usable:
        return None
    points = [entry["percent_of_nominal"] for entry in usable]
    return {
        "low_percent": min(points),
        "high_percent": max(points),
        "usable_count": len(usable),
    }


def range_coverage(span, required_low_percent, required_high_percent):
    """Whether the usable settings reach both ends of the required span."""
    low_required = _require_positive("required_low_percent", required_low_percent)
    high_required = _require_positive("required_high_percent", required_high_percent)
    if not high_required > low_required:
        raise ValueError(
            "the required adjustment range from %g to %g per cent does not "
            "rise, so it is not a range" % (low_required, high_required)
        )
    if span is None:
        return {
            "covered": False,
            "low_shortfall_percent": high_required - low_required,
            "high_shortfall_percent": high_required - low_required,
        }
    low_gap = span["low_percent"] - low_required
    high_gap = high_required - span["high_percent"]
    return {
        "covered": _at_most(low_gap, 0.0) and _at_most(high_gap, 0.0),
        "low_shortfall_percent": max(low_gap, 0.0),
        "high_shortfall_percent": max(high_gap, 0.0),
    }


def adjustment_is_ground_only(access):
    """Whether the declared means of adjustment is a ground activity."""
    means = _require_label("adjustment_means", access).lower()
    if not means:
        raise ValueError("the means of adjustment must be named")
    return any(token in means for token in GROUND_ADJUSTMENT_MEANS)


def assess_undervoltage_threshold_range(case):
    """Full clause 5.4.3.1.1 adjustable trip point decision for one unit."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))

    findings = []
    advisories = []
    result = {
        "unit_id": _require_label("unit_id", case.get("unit_id", "unit")),
        "nominal_bus_v": None,
        "graded_settings": (),
        "usable_span_percent": None,
        "coverage": None,
        "coarsest_step_percent": None,
        "findings": findings,
        "advisories": advisories,
    }

    settings = case.get("settings")
    if settings is None:
        findings.append(
            "no selectable trip points are declared, so the threshold has not "
            "been shown to be adjustable at all"
        )
        result["verdict"] = SETTING_LADDER_NOT_ESTABLISHED
        return result
    ladder = validate_setting_ladder(settings)

    nominal = case.get("nominal_bus_v")
    if nominal is None:
        findings.append(
            "no nominal bus voltage is declared, so a trip point given as a "
            "share of nominal cannot be turned into volts"
        )
        result["verdict"] = NOMINAL_BUS_NOT_ESTABLISHED
        return result
    result["nominal_bus_v"] = _require_positive("nominal_bus_v", nominal)

    required_low = case.get("required_low_percent")
    required_high = case.get("required_high_percent")
    if required_low is None or required_high is None:
        findings.append(
            "no required adjustment range is declared, so there is no span the "
            "usable settings can be shown to cover"
        )
        result["verdict"] = REQUIRED_RANGE_NOT_ESTABLISHED
        return result

    access = case.get("adjustment_means")
    if access is not None and not adjustment_is_ground_only(access):
        findings.append(
            "the trip point is adjusted by %s, which is not a ground activity; "
            "a threshold reachable in flight is a different provision from the "
            "ground-adjustable one required here" % _require_label("means", access)
        )
        result["verdict"] = ADJUSTMENT_NOT_GROUND_ONLY
        return result
    if access is None:
        advisories.append(
            "no means of adjustment is declared, so the ground-only part of "
            "the requirement has not been demonstrated"
        )

    limits = case.get("limits", {})
    graded = grade_ladder(ladder, result["nominal_bus_v"], limits)
    result["graded_settings"] = graded

    span = usable_span_percent(graded)
    result["usable_span_percent"] = span
    coverage = range_coverage(span, required_low, required_high)
    result["coverage"] = coverage
    result["coarsest_step_percent"] = coarsest_step_percent(ladder)

    low_required = _require_positive("required_low_percent", required_low)
    high_required = _require_positive("required_high_percent", required_high)
    for entry in graded:
        inside = _at_least(entry["percent_of_nominal"], low_required) and _at_most(
            entry["percent_of_nominal"], high_required
        )
        for reason in entry["reasons"]:
            if reason == NUISANCE_TRIP_RISK:
                message = (
                    "setting %s at %g per cent of nominal can trip as high as "
                    "%g V, inside the %g V the bus is allowed to reach in "
                    "normal operation"
                    % (
                        entry["id"],
                        entry["percent_of_nominal"],
                        entry["band_upper_v"],
                        entry["usable_ceiling_v"],
                    )
                )
            else:
                message = (
                    "setting %s at %g per cent of nominal can trip as low as "
                    "%g V, under the %g V floor the protected equipment is "
                    "characterised to"
                    % (
                        entry["id"],
                        entry["percent_of_nominal"],
                        entry["band_lower_v"],
                        entry["usable_floor_v"],
                    )
                )
            if inside:
                findings.append(message)
            else:
                advisories.append(
                    message + "; it sits outside the required range but stays "
                    "selectable, so it should be marked"
                )

    if span is None:
        findings.append(
            "no setting on the ladder is usable, so the trip point is not "
            "adjustable anywhere inside the required range"
        )
    elif not coverage["covered"]:
        findings.append(
            "the usable settings span %g to %g per cent of nominal and miss "
            "the required %g to %g per cent by %g per cent at the bottom and "
            "%g per cent at the top"
            % (
                span["low_percent"],
                span["high_percent"],
                required_low,
                required_high,
                coverage["low_shortfall_percent"],
                coverage["high_shortfall_percent"],
            )
        )

    step_limit = case.get("max_step_percent")
    if step_limit is not None:
        step_limit = _require_positive("max_step_percent", step_limit)
        if not _at_most(result["coarsest_step_percent"], step_limit):
            findings.append(
                "neighbouring settings are %g per cent of nominal apart, "
                "coarser than the %g per cent the design calls for, so a "
                "required trip point can fall between two settings"
                % (result["coarsest_step_percent"], step_limit)
            )

    if findings:
        result["verdict"] = THRESHOLD_RANGE_DEFICIENT
        return result

    result["verdict"] = THRESHOLD_RANGE_COMPLIANT
    return result
