#!/usr/bin/env python3
"""Purpose of the angular performance test on a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.19.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An assembly is characterised at normal incidence because that is the
condition the datasheet and the acceptance test share. A mission that
slews, holds a sun offset for thermal reasons, drifts through a
seasonal beta spread or tumbles in safe mode never sees that condition
at the moment power matters most. The angular performance test exists
to put a measured number on what the assembly delivers when the sun
arrives off the normal.

Two effects are stacked in that number and only one of them is free:

    cosine projection   the geometric term, cos of the incidence
                        angle, known before any hardware exists
    angular response    what the coverglass reflection, the cell
    factor              stack and the cell edge shadowing leave of
                        the projected value; measurable only

An assembly that followed the cosine exactly would need no test at all.
The response factor is the reason the clause exists, and it is the term
that decides whether the worst-case off-pointing power clears the
requirement or falls under it.

A test only serves that purpose if its angle envelope reaches the
attitude the mission drivers impose. A sweep stopping short of the
worst-case incidence angle leaves the one point the power budget
depends on to an extrapolation of a curve that is not a cosine.

The trigger angle, the credible-angle ceiling and the response-factor
floor below are a declared policy, not a physical constant: a project
substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Off-pointing driver -> the quantity the angular characterisation feeds.
OFF_POINTING_DRIVERS = {
    "spacecraft-slew-during-observation": "array-power-through-the-slew",
    "sun-offset-attitude-for-thermal-control": "array-power-at-the-held-offset",
    "single-axis-drive-seasonal-beta-spread": "seasonal-beta-angle-power-profile",
    "safe-mode-uncontrolled-attitude": "power-in-an-uncontrolled-attitude",
    "body-mounted-panel-geometry": "incidence-spread-across-body-mounted-panels",
}

RECOGNISED_DRIVERS = tuple(sorted(OFF_POINTING_DRIVERS))

COMMON_OBJECTIVE = "assembly-angular-response-characterisation"

ANGULAR_CHARACTERISATION_NOT_REQUIRED = "angular-characterisation-not-required"
ANGULAR_MEASUREMENT_NOT_PLANNED = "angular-measurement-not-planned"
ANGULAR_MEASUREMENT_INADEQUATE = "angular-measurement-inadequate"
OFF_POINTING_POWER_SHORTFALL = "off-pointing-power-shortfall"
ANGULAR_PERFORMANCE_CHARACTERISED = "angular-performance-characterised"

DEFAULT_ANGULAR_POLICY = {
    "off_pointing_trigger_deg": 5.0,
    "max_credible_test_angle_deg": 85.0,
    "min_response_factor": 0.2,
    "required_power_margin_fraction": 0.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12

_MAX_INCIDENCE_DEG = 90.0


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


def _require_incidence_angle(name, value):
    """0 degrees is normal incidence; at 90 the assembly is edge on and dark."""
    number = _require_number(name, value)
    if number < 0.0 or number >= _MAX_INCIDENCE_DEG:
        raise ValueError(
            "%s must be at least 0 and below %g degrees, got %r"
            % (name, _MAX_INCIDENCE_DEG, value)
        )
    return number


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_angular_policy(policy):
    """Check an angular-characterisation policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    trigger = _require_non_negative(
        "off_pointing_trigger_deg", policy.get("off_pointing_trigger_deg")
    )
    if trigger >= _MAX_INCIDENCE_DEG:
        raise ValueError(
            "off_pointing_trigger_deg %g must be below %g degrees"
            % (trigger, _MAX_INCIDENCE_DEG)
        )
    ceiling = _require_incidence_angle(
        "max_credible_test_angle_deg", policy.get("max_credible_test_angle_deg")
    )
    if not ceiling > trigger:
        raise ValueError(
            "max_credible_test_angle_deg %g must be above the %g degree trigger"
            % (ceiling, trigger)
        )
    floor = _require_positive("min_response_factor", policy.get("min_response_factor"))
    if floor > 1.0:
        raise ValueError(
            "min_response_factor %g must not exceed the ideal cosine value of 1"
            % (floor,)
        )
    _require_non_negative(
        "required_power_margin_fraction",
        policy.get("required_power_margin_fraction"),
    )
    return policy


def cosine_projected_output(normal_output, incidence_angle_deg):
    """Geometric term: the normal-incidence output projected onto the angle."""
    output = _require_positive("normal_output", normal_output)
    angle = _require_incidence_angle("incidence_angle_deg", incidence_angle_deg)
    return output * math.cos(math.radians(angle))


def angular_response_factor(measured_output, normal_output, incidence_angle_deg):
    """What the assembly keeps of the cosine projection; 1.0 is ideal."""
    measured = _require_non_negative("measured_output", measured_output)
    projected = cosine_projected_output(normal_output, incidence_angle_deg)
    return measured / projected


def cosine_departure_fraction(response_factor):
    """The share of the projected output the optics and geometry take away."""
    factor = _require_positive("response_factor", response_factor)
    return 1.0 - factor


def output_at_incidence(normal_output, incidence_angle_deg, response_factor):
    """Output at an angle: the cosine projection scaled by the response factor."""
    factor = _require_positive("response_factor", response_factor)
    return cosine_projected_output(normal_output, incidence_angle_deg) * factor


def response_factor_is_physical(response_factor, policy=DEFAULT_ANGULAR_POLICY):
    """True when the factor sits between the policy floor and the ideal cosine."""
    validate_angular_policy(policy)
    factor = _require_positive("response_factor", response_factor)
    return _at_least(factor, float(policy["min_response_factor"])) and _at_most(
        factor, 1.0
    )


def worst_case_incidence_deg(angles):
    """The largest incidence angle the declared drivers put the assembly at."""
    if not isinstance(angles, (list, tuple, set, frozenset)):
        raise ValueError("angles must be a collection of incidence angles")
    validated = [
        _require_incidence_angle("off_pointing_angle_deg", angle) for angle in angles
    ]
    if not validated:
        raise ValueError("at least one off-pointing incidence angle is required")
    return max(validated)


def power_margin_fraction(available_w, required_w):
    """How far the available power stands above what the budget asks for."""
    available = _require_non_negative("available_w", available_w)
    required = _require_positive("required_w", required_w)
    return (available - required) / required


def envelope_covers_mission(max_test_angle_deg, worst_case_angle_deg):
    """True when the planned sweep reaches the attitude the mission imposes."""
    tested = _require_incidence_angle("max_test_angle_deg", max_test_angle_deg)
    needed = _require_incidence_angle("worst_case_angle_deg", worst_case_angle_deg)
    return _at_least(tested, needed)


def driver_inventory(drivers):
    """Group the declared off-pointing drivers, rejecting an unrecognised one."""
    if not isinstance(drivers, (list, tuple, set, frozenset)):
        raise ValueError("drivers must be a collection of driver names")
    grouped = []
    for driver in drivers:
        if driver not in OFF_POINTING_DRIVERS:
            raise ValueError(
                "unknown off-pointing driver %r; recognised drivers are %s"
                % (driver, ", ".join(RECOGNISED_DRIVERS))
            )
        if driver not in grouped:
            grouped.append(driver)
    return tuple(sorted(grouped))


def characterisation_objectives(drivers):
    """What the angular test feeds, given the declared off-pointing drivers."""
    grouped = driver_inventory(drivers)
    if not grouped:
        return ()
    objectives = [OFF_POINTING_DRIVERS[driver] for driver in grouped]
    objectives.append(COMMON_OBJECTIVE)
    return tuple(objectives)


def assess_angular_performance_purpose(case, policy=DEFAULT_ANGULAR_POLICY):
    """Full clause 6.4.3.19.1 judgement for one angular performance test."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_angular_policy(policy)
    if "off_pointing_drivers" not in case:
        raise ValueError(
            "case is missing off_pointing_drivers; an absent inventory is not an "
            "empty one"
        )
    drivers = driver_inventory(case["off_pointing_drivers"])
    objectives = characterisation_objectives(case["off_pointing_drivers"])

    mission = case.get("mission")
    if not isinstance(mission, dict):
        raise ValueError("case is missing a mission block")
    worst_case = worst_case_incidence_deg(mission.get("off_pointing_angles_deg", []))
    normal_output = _require_positive(
        "mission normal_output_w", mission.get("normal_output_w")
    )
    required_output = _require_positive(
        "mission required_output_w", mission.get("required_output_w")
    )
    response_factor = _require_positive(
        "mission expected_response_factor", mission.get("expected_response_factor")
    )

    projected = cosine_projected_output(normal_output, worst_case)
    available = projected * response_factor
    margin = power_margin_fraction(available, required_output)
    margin_floor = float(policy["required_power_margin_fraction"])
    margin_met = _at_least(margin, margin_floor)

    trigger = float(policy["off_pointing_trigger_deg"])
    off_pointed = _at_least(worst_case, trigger)
    findings = []
    result = {
        "off_pointing_drivers": drivers,
        "objectives": objectives,
        "worst_case_incidence_deg": worst_case,
        "off_pointing_trigger_deg": trigger,
        "cosine_projected_output_w": projected,
        "expected_output_w": available,
        "cosine_departure_fraction": cosine_departure_fraction(response_factor),
        "power_margin_fraction": margin,
        "power_margin_met": margin_met,
        "max_test_angle_deg": None,
        "envelope_covers_mission": None,
        "response_factor_physical": None,
        "findings": findings,
    }

    if not (drivers and off_pointed):
        if not drivers:
            findings.append(
                "no off-pointing driver is declared, so no attitude puts the "
                "assembly off the normal"
            )
        if not off_pointed:
            findings.append(
                "the worst-case incidence angle %.3f deg is below the %.3f deg "
                "off-pointing trigger" % (worst_case, trigger)
            )
        result["required"] = False
        result["verdict"] = ANGULAR_CHARACTERISATION_NOT_REQUIRED
        return result

    result["required"] = True
    measurement = case.get("measurement")
    if measurement is None:
        findings.append(
            "the characterisation is required but no angular sweep is planned; "
            "the purpose is stated and not yet served"
        )
        result["verdict"] = ANGULAR_MEASUREMENT_NOT_PLANNED
        return result
    if not isinstance(measurement, dict):
        raise ValueError("measurement must be a mapping, got %r" % (measurement,))

    max_test_angle = _require_incidence_angle(
        "measurement max_test_angle_deg", measurement.get("max_test_angle_deg")
    )
    covers = envelope_covers_mission(max_test_angle, worst_case)
    physical = response_factor_is_physical(response_factor, policy)
    credible_ceiling = float(policy["max_credible_test_angle_deg"])
    within_ceiling = _at_most(max_test_angle, credible_ceiling)

    result["max_test_angle_deg"] = max_test_angle
    result["envelope_covers_mission"] = covers
    result["response_factor_physical"] = physical

    if not covers:
        findings.append(
            "the sweep stops at %.3f deg and the mission reaches %.3f deg, so "
            "the worst-case point is extrapolated rather than measured"
            % (max_test_angle, worst_case)
        )
    if not within_ceiling:
        findings.append(
            "the planned %.3f deg maximum is beyond the %.3f deg at which an "
            "angular measurement stays credible"
            % (max_test_angle, credible_ceiling)
        )
    if not physical:
        findings.append(
            "the expected response factor %.4f is outside the %.4f to 1 band a "
            "cosine-projected assembly can occupy"
            % (response_factor, float(policy["min_response_factor"]))
        )

    if findings:
        result["verdict"] = ANGULAR_MEASUREMENT_INADEQUATE
        return result
    if not margin_met:
        findings.append(
            "at %.3f deg the assembly offers %.4g W against the %.4g W required, "
            "a margin of %.4f below the %.4f floor"
            % (worst_case, available, required_output, margin, margin_floor)
        )
        result["verdict"] = OFF_POINTING_POWER_SHORTFALL
        return result

    result["verdict"] = ANGULAR_PERFORMANCE_CHARACTERISED
    return result
