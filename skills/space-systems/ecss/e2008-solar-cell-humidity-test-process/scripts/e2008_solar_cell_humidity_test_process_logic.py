#!/usr/bin/env python3
"""Conditioning a subgroup O sample inside an ambient pressure damp chamber.

Anchor: ECSS-E-ST-20-08C clause 7.5.7.1.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The purpose clause says why the cells are stored damp. This one says how
the chamber is driven while they are, and almost every way of getting it
wrong produces a soak that looks nominal in the log.

Four things decide whether the conditioning is the one that was asked
for:

    the sample        cells drawn from subgroup O, in a count the plan
                      declared, and not topped up from another subgroup
    the pressure      ambient, held inside a tolerance. A chamber that
                      drifts into pressure is a different test with a
                      different failure mechanism
    the surface       every cell front face kept above the dew point of
                      the air around it. Below it the test stops being
                      damp storage and becomes liquid immersion at the
                      coldest spot in the chamber
    the profile       ramps slow enough not to shock the coverglass
                      bond, a stabilisation dwell before the soak clock
                      starts, and a soak that reaches its full duration

The dew point is the one that has to be computed rather than read. A
Magnus relation turns the chamber air temperature and its relative
humidity into the temperature at which that air saturates; the margin
that matters is between it and the coldest cell surface, not the
chamber setpoint, because the cells are the coldest thing in the volume
whenever the chamber is still coming up.

The tolerances and floors below are a declared policy, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SUBGROUP_UNDER_TEST = "O"

MAGNUS_A = 17.625
MAGNUS_B_C = 243.04
MAGNUS_P0_PA = 610.94
ABSOLUTE_ZERO_C = -273.15
ABSOLUTE_HUMIDITY_CONSTANT = 2.16679

PLAN_DEFICIENT = "subgroup-o-sample-plan-deficient"
CONDENSATION_RISK = "chamber-condensation-risk"
CONDITIONING_DEFICIENT = "damp-conditioning-deficient"
CONDITIONING_ACCEPTED = "damp-conditioning-accepted"

DEFAULT_CONDITIONING_POLICY = {
    "min_subgroup_cells": 5,
    "ambient_pressure_pa": 101325.0,
    "pressure_tolerance_pa": 5000.0,
    "min_dew_point_margin_k": 2.0,
    "max_ramp_rate_k_per_min": 1.0,
    "min_stabilisation_dwell_min": 30.0,
    "min_soak_duration_h": 1000.0,
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


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


def _require_temperature_c(name, value):
    number = _require_number(name, value)
    if number <= ABSOLUTE_ZERO_C:
        raise ValueError(
            "%s must be above absolute zero, got %r" % (name, value)
        )
    return number


def _require_humidity(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 100.0:
        raise ValueError(
            "%s must be a relative humidity in per cent above zero and at most "
            "100, got %r" % (name, value)
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


def validate_conditioning_policy(policy):
    """Check a damp conditioning policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_count("min_subgroup_cells", policy.get("min_subgroup_cells"))
    ambient = _require_positive(
        "ambient_pressure_pa", policy.get("ambient_pressure_pa")
    )
    tolerance = _require_positive(
        "pressure_tolerance_pa", policy.get("pressure_tolerance_pa")
    )
    if tolerance >= ambient:
        raise ValueError(
            "pressure_tolerance_pa %g must be smaller than the ambient "
            "pressure %g it is a tolerance on" % (tolerance, ambient)
        )
    _require_positive(
        "min_dew_point_margin_k", policy.get("min_dew_point_margin_k")
    )
    _require_positive(
        "max_ramp_rate_k_per_min", policy.get("max_ramp_rate_k_per_min")
    )
    _require_positive(
        "min_stabilisation_dwell_min", policy.get("min_stabilisation_dwell_min")
    )
    _require_positive("min_soak_duration_h", policy.get("min_soak_duration_h"))
    return policy


def saturation_vapour_pressure_pa(temperature_c):
    """Pressure at which water vapour saturates at this temperature."""
    temperature = _require_temperature_c("temperature_c", temperature_c)
    return MAGNUS_P0_PA * math.exp(
        MAGNUS_A * temperature / (MAGNUS_B_C + temperature)
    )


def partial_vapour_pressure_pa(temperature_c, relative_humidity_pct):
    """Vapour pressure the chamber air actually holds at this setpoint."""
    humidity = _require_humidity("relative_humidity_pct", relative_humidity_pct)
    return saturation_vapour_pressure_pa(temperature_c) * (humidity / 100.0)


def dew_point_c(temperature_c, relative_humidity_pct):
    """Temperature at which the chamber air saturates and water forms."""
    temperature = _require_temperature_c("temperature_c", temperature_c)
    humidity = _require_humidity("relative_humidity_pct", relative_humidity_pct)
    gamma = math.log(humidity / 100.0) + (
        MAGNUS_A * temperature / (MAGNUS_B_C + temperature)
    )
    return MAGNUS_B_C * gamma / (MAGNUS_A - gamma)


def absolute_humidity_g_per_m3(temperature_c, relative_humidity_pct):
    """Water the chamber air carries, per cubic metre of that air."""
    temperature = _require_temperature_c("temperature_c", temperature_c)
    vapour = partial_vapour_pressure_pa(temperature, relative_humidity_pct)
    return ABSOLUTE_HUMIDITY_CONSTANT * vapour / (temperature - ABSOLUTE_ZERO_C)


def dew_point_margin_k(surface_temperature_c, temperature_c, relative_humidity_pct):
    """How far the coldest cell surface stands above the dew point."""
    surface = _require_temperature_c(
        "surface_temperature_c", surface_temperature_c
    )
    return surface - dew_point_c(temperature_c, relative_humidity_pct)


def pressure_is_ambient(chamber_pressure_pa, policy=DEFAULT_CONDITIONING_POLICY):
    """True when the chamber sits at ambient pressure inside its tolerance."""
    validate_conditioning_policy(policy)
    pressure = _require_positive("chamber_pressure_pa", chamber_pressure_pa)
    offset = abs(pressure - float(policy["ambient_pressure_pa"]))
    return _at_most(offset, float(policy["pressure_tolerance_pa"]))


def subgroup_cell_count(sample_plan):
    """Cells the plan draws from the subgroup under test, subgroup O."""
    if not isinstance(sample_plan, dict):
        raise ValueError("sample_plan must be a mapping, got %r" % (sample_plan,))
    subgroup = sample_plan.get("subgroup")
    if not isinstance(subgroup, str) or not subgroup.strip():
        raise ValueError(
            "sample_plan is missing a subgroup label, got %r" % (subgroup,)
        )
    count = _require_count("sample_plan cell_count", sample_plan.get("cell_count"))
    if subgroup.strip().upper() != SUBGROUP_UNDER_TEST:
        return 0
    return count


def assess_damp_conditioning(case, policy=DEFAULT_CONDITIONING_POLICY):
    """Full clause 7.5.7.1.2 judgement for one damp conditioning profile."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_conditioning_policy(policy)
    sample_plan = case.get("sample_plan")
    if sample_plan is None:
        raise ValueError("case is missing a sample_plan block")
    profile = case.get("chamber_profile")
    if not isinstance(profile, dict):
        raise ValueError("case is missing a chamber_profile block")

    cells = subgroup_cell_count(sample_plan)
    air_temperature = _require_temperature_c(
        "chamber_profile temperature_c", profile.get("temperature_c")
    )
    humidity = _require_humidity(
        "chamber_profile relative_humidity_pct",
        profile.get("relative_humidity_pct"),
    )
    surface_temperature = _require_temperature_c(
        "chamber_profile cell_surface_temperature_c",
        profile.get("cell_surface_temperature_c"),
    )
    chamber_pressure = _require_positive(
        "chamber_profile chamber_pressure_pa", profile.get("chamber_pressure_pa")
    )
    ramp_rate = _require_positive(
        "chamber_profile ramp_rate_k_per_min", profile.get("ramp_rate_k_per_min")
    )
    dwell = _require_positive(
        "chamber_profile stabilisation_dwell_min",
        profile.get("stabilisation_dwell_min"),
    )
    soak = _require_positive(
        "chamber_profile soak_duration_h", profile.get("soak_duration_h")
    )

    dew_point = dew_point_c(air_temperature, humidity)
    margin = dew_point_margin_k(surface_temperature, air_temperature, humidity)

    findings = []
    result = {
        "subgroup_cells": cells,
        "dew_point_c": dew_point,
        "dew_point_margin_k": margin,
        "absolute_humidity_g_per_m3": absolute_humidity_g_per_m3(
            air_temperature, humidity
        ),
        "chamber_pressure_pa": chamber_pressure,
        "pressure_ambient": pressure_is_ambient(chamber_pressure, policy),
        "soak_duration_h": soak,
        "findings": findings,
    }

    sample_short = not _at_least(cells, float(policy["min_subgroup_cells"]))
    if sample_short:
        findings.append(
            "the plan places %d subgroup %s cells in the chamber against the %d "
            "the policy asks for"
            % (cells, SUBGROUP_UNDER_TEST, int(policy["min_subgroup_cells"]))
        )

    condensation = not _at_least(margin, float(policy["min_dew_point_margin_k"]))
    if condensation:
        findings.append(
            "the coldest cell surface stands %.3f K from the %.3f C dew point, "
            "inside the %.3f K margin, so water forms on the cells rather than "
            "around them"
            % (margin, dew_point, float(policy["min_dew_point_margin_k"]))
        )

    if not result["pressure_ambient"]:
        findings.append(
            "the chamber holds %.1f Pa, outside %.1f Pa of the %.1f Pa ambient "
            "this conditioning is run at"
            % (
                chamber_pressure,
                float(policy["pressure_tolerance_pa"]),
                float(policy["ambient_pressure_pa"]),
            )
        )
    if not _at_most(ramp_rate, float(policy["max_ramp_rate_k_per_min"])):
        findings.append(
            "the profile ramps at %.3f K/min, above the %.3f K/min ceiling the "
            "coverglass bond is taken through"
            % (ramp_rate, float(policy["max_ramp_rate_k_per_min"]))
        )
    if not _at_least(dwell, float(policy["min_stabilisation_dwell_min"])):
        findings.append(
            "the stabilisation dwell is %.1f min against the %.1f min the cells "
            "need to reach the setpoint before the soak clock starts"
            % (dwell, float(policy["min_stabilisation_dwell_min"]))
        )
    if not _at_least(soak, float(policy["min_soak_duration_h"])):
        findings.append(
            "the soak runs %.1f h against the %.1f h required"
            % (soak, float(policy["min_soak_duration_h"]))
        )

    if condensation:
        result["verdict"] = CONDENSATION_RISK
    elif sample_short:
        result["verdict"] = PLAN_DEFICIENT
    elif findings:
        result["verdict"] = CONDITIONING_DEFICIENT
    else:
        result["verdict"] = CONDITIONING_ACCEPTED
    return result
