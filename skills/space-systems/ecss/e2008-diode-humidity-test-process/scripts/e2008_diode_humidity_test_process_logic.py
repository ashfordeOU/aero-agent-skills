#!/usr/bin/env python3
"""Arranging a subgroup O protection diode load inside an ambient pressure
chamber for its damp exposure.

Anchor: ECSS-E-ST-20-08C clause 9.6.6.1.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The purpose clause says why protection diodes are stored damp. This one
says how they sit in the volume while they are, and a diode load is not
a cell load: the devices are small, they are three-dimensional, and they
come with terminals that stand proud of the package. Four things decide
whether the exposure is the one that was asked for:

    the sample        devices drawn from subgroup O, in the count the
                      plan declared. A tray topped up from another
                      subgroup is full without the plan being met
    the pressure      a band around ambient. A chamber that drifts out
                      of it drives moisture through a package seal by a
                      route the ambient soak never exercises
    the airflow       a diode shadows its neighbour. Free flow left on
                      the tray and a gap between packages are what turn
                      a stack of devices into an exposed stack; packed
                      edge to edge, the outer row is conditioned and the
                      inner rows are merely warm
    the case          every package surface kept above the dew point of
                      the air around it. Below it the terminals carry a
                      surface water film, and the leakage that follows
                      is a wet-surface artefact rather than the junction
                      degradation the exposure was run to find

The dew point is the one number that has to be computed rather than
read. Relative humidity is a ratio and says nothing on its own about
whether water forms; a Magnus relation turns the air temperature and the
humidity setpoint into the temperature at which that air saturates, and
the margin that matters is against the coldest diode case, not the
chamber setpoint, because the devices lag the air on every ramp.

The bands, floors and dwells below are a declared policy, not physical
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

DIODE_SAMPLE_PLAN_DEFICIENT = "subgroup-o-diode-sample-plan-deficient"
TERMINAL_CONDENSATION_RISK = "diode-terminal-condensation-risk"
CHAMBER_LOADING_DEFICIENT = "protection-diode-chamber-loading-deficient"
CHAMBER_LOADING_ACCEPTED = "protection-diode-chamber-loading-accepted"

LOADING_VERDICTS = (
    DIODE_SAMPLE_PLAN_DEFICIENT,
    TERMINAL_CONDENSATION_RISK,
    CHAMBER_LOADING_DEFICIENT,
    CHAMBER_LOADING_ACCEPTED,
)

DEFAULT_DIODE_CHAMBER_POLICY = {
    "min_subgroup_diodes": 5,
    "min_chamber_pressure_kpa": 86.0,
    "max_chamber_pressure_kpa": 106.0,
    "min_case_dew_point_margin_k": 2.0,
    "min_tray_free_flow_fraction": 0.30,
    "min_package_gap_mm": 3.0,
    "min_stabilisation_dwell_h": 2.0,
    "min_exposure_duration_h": 1000.0,
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
        raise ValueError("%s must be above absolute zero, got %r" % (name, value))
    return number


def _require_humidity(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 100.0:
        raise ValueError(
            "%s must be a relative humidity in per cent above zero and at most "
            "100, got %r" % (name, value)
        )
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 < number < 1.0:
        raise ValueError(
            "%s must be a fraction above zero and below one, got %r" % (name, value)
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


def validate_diode_chamber_policy(policy):
    """Check a protection diode chamber loading policy is self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_count("min_subgroup_diodes", policy.get("min_subgroup_diodes"))
    low = _require_positive(
        "min_chamber_pressure_kpa", policy.get("min_chamber_pressure_kpa")
    )
    high = _require_positive(
        "max_chamber_pressure_kpa", policy.get("max_chamber_pressure_kpa")
    )
    if not low < high:
        raise ValueError(
            "min_chamber_pressure_kpa %g must sit below max_chamber_pressure_kpa "
            "%g" % (low, high)
        )
    _require_positive(
        "min_case_dew_point_margin_k", policy.get("min_case_dew_point_margin_k")
    )
    _require_fraction(
        "min_tray_free_flow_fraction", policy.get("min_tray_free_flow_fraction")
    )
    _require_positive("min_package_gap_mm", policy.get("min_package_gap_mm"))
    _require_positive(
        "min_stabilisation_dwell_h", policy.get("min_stabilisation_dwell_h")
    )
    _require_positive(
        "min_exposure_duration_h", policy.get("min_exposure_duration_h")
    )
    return policy


def saturation_vapour_pressure_pa(temperature_c):
    """Pressure at which water vapour saturates at this temperature."""
    temperature = _require_temperature_c("temperature_c", temperature_c)
    return MAGNUS_P0_PA * math.exp(
        MAGNUS_A * temperature / (MAGNUS_B_C + temperature)
    )


def case_dew_point_c(air_temperature_c, relative_humidity_pct):
    """Temperature at which the chamber air saturates against a package."""
    temperature = _require_temperature_c("air_temperature_c", air_temperature_c)
    humidity = _require_humidity("relative_humidity_pct", relative_humidity_pct)
    gamma = math.log(humidity / 100.0) + (
        MAGNUS_A * temperature / (MAGNUS_B_C + temperature)
    )
    return MAGNUS_B_C * gamma / (MAGNUS_A - gamma)


def case_dew_point_margin_k(
    case_temperature_c, air_temperature_c, relative_humidity_pct
):
    """How far the coldest diode case stands above the dew point."""
    case = _require_temperature_c("case_temperature_c", case_temperature_c)
    return case - case_dew_point_c(air_temperature_c, relative_humidity_pct)


def subgroup_diode_count(sample_plan):
    """Devices the plan draws from the subgroup under test, subgroup O."""
    if not isinstance(sample_plan, dict):
        raise ValueError("sample_plan must be a mapping, got %r" % (sample_plan,))
    subgroup = sample_plan.get("subgroup")
    if not isinstance(subgroup, str) or not subgroup.strip():
        raise ValueError(
            "sample_plan is missing a subgroup label, got %r" % (subgroup,)
        )
    count = _require_count("sample_plan diode_count", sample_plan.get("diode_count"))
    if subgroup.strip().upper() != SUBGROUP_UNDER_TEST:
        return 0
    return count


def tray_free_flow_fraction(tray):
    """Share of the tray footprint the circulating air still reaches."""
    if not isinstance(tray, dict):
        raise ValueError("tray must be a mapping, got %r" % (tray,))
    area = _require_positive("tray tray_area_mm2", tray.get("tray_area_mm2"))
    footprint = _require_positive(
        "tray package_footprint_mm2", tray.get("package_footprint_mm2")
    )
    count = _require_count("tray device_count", tray.get("device_count"))
    occupied = footprint * count
    if occupied > area and not math.isclose(
        occupied, area, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "the load covers %g mm2 of a %g mm2 tray, which does not fit"
            % (occupied, area)
        )
    return 1.0 - (occupied / area)


def package_gap_mm(row):
    """Gap between packages when a row is spaced evenly, ends included."""
    if not isinstance(row, dict):
        raise ValueError("row must be a mapping, got %r" % (row,))
    length = _require_positive("row row_length_mm", row.get("row_length_mm"))
    width = _require_positive("row package_width_mm", row.get("package_width_mm"))
    count = _require_count("row device_count", row.get("device_count"))
    occupied = width * count
    if occupied >= length:
        raise ValueError(
            "%d packages of %g mm need %g mm, which a %g mm row cannot space"
            % (count, width, occupied, length)
        )
    return (length - occupied) / (count + 1)


def pressure_in_ambient_band(
    chamber_pressure_kpa, policy=DEFAULT_DIODE_CHAMBER_POLICY
):
    """True when the chamber sits inside the declared ambient band."""
    validate_diode_chamber_policy(policy)
    pressure = _require_positive("chamber_pressure_kpa", chamber_pressure_kpa)
    return _at_least(
        pressure, float(policy["min_chamber_pressure_kpa"])
    ) and _at_most(pressure, float(policy["max_chamber_pressure_kpa"]))


def assess_diode_damp_loading(case, policy=DEFAULT_DIODE_CHAMBER_POLICY):
    """Full clause 9.6.6.1.2 judgement for one diode chamber loading."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_diode_chamber_policy(policy)
    sample_plan = case.get("sample_plan")
    if sample_plan is None:
        raise ValueError("case is missing a sample_plan block")
    load = case.get("chamber_load")
    if not isinstance(load, dict):
        raise ValueError("case is missing a chamber_load block")

    planned = subgroup_diode_count(sample_plan)
    loaded = _require_count("chamber_load device_count", load.get("device_count"))
    air_temperature = _require_temperature_c(
        "chamber_load air_temperature_c", load.get("air_temperature_c")
    )
    humidity = _require_humidity(
        "chamber_load relative_humidity_pct", load.get("relative_humidity_pct")
    )
    case_temperature = _require_temperature_c(
        "chamber_load case_temperature_c", load.get("case_temperature_c")
    )
    pressure = _require_positive(
        "chamber_load chamber_pressure_kpa", load.get("chamber_pressure_kpa")
    )
    dwell = _require_positive(
        "chamber_load stabilisation_dwell_h", load.get("stabilisation_dwell_h")
    )
    exposure = _require_positive(
        "chamber_load exposure_duration_h", load.get("exposure_duration_h")
    )

    free_flow = tray_free_flow_fraction(
        {
            "tray_area_mm2": load.get("tray_area_mm2"),
            "package_footprint_mm2": load.get("package_footprint_mm2"),
            "device_count": loaded,
        }
    )
    gap = package_gap_mm(
        {
            "row_length_mm": load.get("row_length_mm"),
            "package_width_mm": load.get("package_width_mm"),
            "device_count": load.get("row_device_count", loaded),
        }
    )
    dew_point = case_dew_point_c(air_temperature, humidity)
    margin = case_dew_point_margin_k(case_temperature, air_temperature, humidity)

    findings = []
    result = {
        "subgroup_diodes": planned,
        "loaded_devices": loaded,
        "dew_point_c": dew_point,
        "case_dew_point_margin_k": margin,
        "tray_free_flow_fraction": free_flow,
        "package_gap_mm": gap,
        "chamber_pressure_kpa": pressure,
        "pressure_in_band": pressure_in_ambient_band(pressure, policy),
        "exposure_duration_h": exposure,
        "findings": findings,
    }

    sample_short = not _at_least(planned, float(policy["min_subgroup_diodes"]))
    if sample_short:
        findings.append(
            "the plan places %d subgroup %s diodes in the chamber against the %d "
            "the policy asks for"
            % (planned, SUBGROUP_UNDER_TEST, int(policy["min_subgroup_diodes"]))
        )

    condensation = not _at_least(
        margin, float(policy["min_case_dew_point_margin_k"])
    )
    if condensation:
        findings.append(
            "the coldest diode case stands %.3f K from the %.3f C dew point, "
            "inside the %.3f K margin, so a water film forms across the "
            "terminals rather than around them"
            % (margin, dew_point, float(policy["min_case_dew_point_margin_k"]))
        )

    if loaded < planned:
        findings.append(
            "the tray holds %d devices against the %d the subgroup %s plan draws"
            % (loaded, planned, SUBGROUP_UNDER_TEST)
        )
    if not result["pressure_in_band"]:
        findings.append(
            "the chamber holds %.2f kPa, outside the %.2f to %.2f kPa ambient "
            "band this exposure is run in"
            % (
                pressure,
                float(policy["min_chamber_pressure_kpa"]),
                float(policy["max_chamber_pressure_kpa"]),
            )
        )
    if not _at_least(free_flow, float(policy["min_tray_free_flow_fraction"])):
        findings.append(
            "the tray leaves %.4f of its footprint open against the %.4f the air "
            "needs to reach every package"
            % (free_flow, float(policy["min_tray_free_flow_fraction"]))
        )
    if not _at_least(gap, float(policy["min_package_gap_mm"])):
        findings.append(
            "packages sit %.3f mm apart against the %.3f mm that keeps one from "
            "shadowing the next"
            % (gap, float(policy["min_package_gap_mm"]))
        )
    if not _at_least(dwell, float(policy["min_stabilisation_dwell_h"])):
        findings.append(
            "the stabilisation dwell is %.2f h against the %.2f h the packages "
            "need before the exposure clock starts"
            % (dwell, float(policy["min_stabilisation_dwell_h"]))
        )
    if not _at_least(exposure, float(policy["min_exposure_duration_h"])):
        findings.append(
            "the exposure runs %.1f h against the %.1f h required"
            % (exposure, float(policy["min_exposure_duration_h"]))
        )

    if condensation:
        result["verdict"] = TERMINAL_CONDENSATION_RISK
    elif sample_short:
        result["verdict"] = DIODE_SAMPLE_PLAN_DEFICIENT
    elif findings:
        result["verdict"] = CHAMBER_LOADING_DEFICIENT
    else:
        result["verdict"] = CHAMBER_LOADING_ACCEPTED
    return result
