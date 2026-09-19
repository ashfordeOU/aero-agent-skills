#!/usr/bin/env python3
"""Thermal performance test of a two-phase heat transport assembly.

Anchor: ECSS-E-ST-31-02C clause 5.6.9. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The thermal performance test maps a transport device -- a heat pipe, a
loop or a capillary-pumped assembly -- over the power and temperature
envelope it is qualified for, and adds two demonstrations that a steady
map cannot show on its own:

    power mapping   transported power against the temperature drop it
                    costs, at each required power and sink temperature
    start-up        transport established from a cold, unprimed device
                    inside the declared time
    regulation      the control setpoint held inside its band while the
                    device runs

The transported power is not the power the heater drew: the parasitic
leak to the surroundings never crossed the device, so it is subtracted
before anything is graded. The transport capability itself moves with
operating temperature, so the capability a point is graded against is
interpolated from the declared curve at that point's own temperature.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

POINT_GRADES = ("within-capability", "at-capability", "beyond-capability")
STEADY_VERDICTS = ("steady", "not-steady")
CAMPAIGN_VERDICTS = ("performance-demonstrated", "performance-not-demonstrated")

DEFAULT_STEADY_RATE_LIMIT_K_PER_MIN = 0.1
DEFAULT_CELL_POWER_TOLERANCE_W = 0.5
DEFAULT_CELL_TEMPERATURE_TOLERANCE_K = 2.0

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


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _close(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _close(value, limit)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or _close(value, limit)


def transported_power_w(applied_power_w, parasitic_loss_w=0.0):
    """Power that actually crossed the device, heater draw less the leak."""
    applied = _require_positive("applied_power_w", applied_power_w)
    parasitic = _require_non_negative("parasitic_loss_w", parasitic_loss_w)
    if parasitic >= applied:
        raise ValueError(
            "parasitic loss %g W is not below the applied power %g W; no power "
            "reached the transport path" % (parasitic, applied)
        )
    return applied - parasitic


def temperature_drop_k(evaporator_temp_k, condenser_temp_k):
    """Evaporator-to-condenser drop the transported power had to pay."""
    evaporator = _require_positive("evaporator_temp_k", evaporator_temp_k)
    condenser = _require_positive("condenser_temp_k", condenser_temp_k)
    if condenser > evaporator and not _close(condenser, evaporator):
        raise ValueError(
            "condenser %g K sits above the evaporator %g K; the transport "
            "direction is reversed and the point is not interpretable"
            % (condenser, evaporator)
        )
    drop = evaporator - condenser
    return drop if drop > 0.0 else 0.0


def transport_conductance_w_per_k(transported_w, drop_k):
    """Conductance of the transport path at one mapped point."""
    power = _require_positive("transported_w", transported_w)
    drop = _require_positive("drop_k", drop_k)
    return power / drop


def validate_capability_curve(curve):
    """Check the declared transport-capability curve is usable."""
    if not isinstance(curve, (list, tuple)) or len(curve) < 2:
        raise ValueError("capability curve needs at least two points")
    previous_temp = None
    cleaned = []
    for index, entry in enumerate(curve):
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise ValueError(
                "capability curve point %d must be a (temperature_k, "
                "capability_w) pair" % index
            )
        temperature = _require_positive("capability temperature_k", entry[0])
        capability = _require_positive("capability_w", entry[1])
        if previous_temp is not None and temperature <= previous_temp:
            raise ValueError(
                "capability curve temperatures must strictly increase; %g K "
                "follows %g K" % (temperature, previous_temp)
            )
        previous_temp = temperature
        cleaned.append((temperature, capability))
    return cleaned


def capability_at_temperature_w(curve, temperature_k):
    """Transport capability interpolated at one operating temperature.

    Extrapolation is refused: a capability outside the declared curve is
    not evidence, and silently continuing the last slope is exactly how a
    beyond-capability point gets reported as compliant.
    """
    points = validate_capability_curve(curve)
    temperature = _require_positive("temperature_k", temperature_k)
    low_temp, low_cap = points[0]
    high_temp, high_cap = points[-1]
    if temperature < low_temp and not _close(temperature, low_temp):
        raise ValueError(
            "operating temperature %g K is below the curve span starting at "
            "%g K; the capability would be extrapolated" % (temperature, low_temp)
        )
    if temperature > high_temp and not _close(temperature, high_temp):
        raise ValueError(
            "operating temperature %g K is above the curve span ending at "
            "%g K; the capability would be extrapolated" % (temperature, high_temp)
        )
    for (t0, c0), (t1, c1) in zip(points, points[1:]):
        if temperature <= t1 or _close(temperature, t1):
            if _close(temperature, t0):
                return c0
            fraction = (temperature - t0) / (t1 - t0)
            return c0 + fraction * (c1 - c0)
    return high_cap


def grade_capability_utilisation(transported_w, capability_w):
    """Categorize one mapped point against the capability it consumed."""
    power = _require_positive("transported_w", transported_w)
    capability = _require_positive("capability_w", capability_w)
    utilisation = power / capability
    if _close(utilisation, 1.0):
        grade = "at-capability"
    elif utilisation > 1.0:
        grade = "beyond-capability"
    else:
        grade = "within-capability"
    return {"utilisation": utilisation, "grade": grade}


def assess_steady_state(rate_k_per_min, limit_k_per_min=DEFAULT_STEADY_RATE_LIMIT_K_PER_MIN):
    """Decide whether a dwell had settled before the point was recorded."""
    rate = _require_number("rate_k_per_min", rate_k_per_min)
    limit = _require_positive("limit_k_per_min", limit_k_per_min)
    steady = _at_most(abs(rate), limit)
    return {
        "drift_k_per_min": abs(rate),
        "limit_k_per_min": limit,
        "verdict": "steady" if steady else "not-steady",
        "steady": steady,
    }


def grade_mapping_point(point, curve, steady_rate_limit_k_per_min=DEFAULT_STEADY_RATE_LIMIT_K_PER_MIN, max_drop_k=None):
    """Full grading of one power/temperature mapping point."""
    _require_mapping("point", point)
    applied = _require_positive("applied_power_w", point.get("applied_power_w"))
    transported = transported_power_w(applied, point.get("parasitic_loss_w", 0.0))
    evaporator = _require_positive("evaporator_temp_k", point.get("evaporator_temp_k"))
    condenser = _require_positive("condenser_temp_k", point.get("condenser_temp_k"))
    drop = temperature_drop_k(evaporator, condenser)
    capability = capability_at_temperature_w(curve, condenser)
    utilisation = grade_capability_utilisation(transported, capability)
    steady = assess_steady_state(
        point.get("drift_k_per_min", 0.0), steady_rate_limit_k_per_min
    )
    findings = []
    conductance = None
    if drop > 0.0:
        conductance = transport_conductance_w_per_k(transported, drop)
    else:
        findings.append(
            "evaporator and condenser read the same temperature; the "
            "conductance of this point is not resolvable by the instrumentation"
        )
    drop_ok = True
    if max_drop_k is not None:
        limit = _require_positive("max_drop_k", max_drop_k)
        drop_ok = _at_most(drop, limit)
        if not drop_ok:
            findings.append(
                "temperature drop %.3f K exceeds the allowed %.3f K" % (drop, limit)
            )
    if utilisation["grade"] == "beyond-capability":
        findings.append(
            "transported %.3f W against a capability of %.3f W at %.2f K"
            % (transported, capability, condenser)
        )
    if not steady["steady"]:
        findings.append(
            "dwell drifting at %.4f K/min was not steady when the point was taken"
            % steady["drift_k_per_min"]
        )
    accepted = (
        utilisation["grade"] != "beyond-capability" and steady["steady"] and drop_ok
    )
    return {
        "applied_power_w": applied,
        "transported_power_w": transported,
        "temperature_drop_k": drop,
        "conductance_w_per_k": conductance,
        "capability_w": capability,
        "utilisation": utilisation["utilisation"],
        "grade": utilisation["grade"],
        "steady": steady["steady"],
        "accepted": accepted,
        "findings": findings,
    }


def mapping_coverage(
    points,
    required_cells,
    power_tolerance_w=DEFAULT_CELL_POWER_TOLERANCE_W,
    temperature_tolerance_k=DEFAULT_CELL_TEMPERATURE_TOLERANCE_K,
):
    """Which cells of the required power/sink-temperature matrix were run."""
    if not isinstance(points, (list, tuple)):
        raise ValueError("points must be a sequence")
    if not isinstance(required_cells, (list, tuple)) or not required_cells:
        raise ValueError("required_cells must be a non-empty sequence")
    power_tol = _require_positive("power_tolerance_w", power_tolerance_w)
    temp_tol = _require_positive("temperature_tolerance_k", temperature_tolerance_k)
    covered = []
    missing = []
    for index, cell in enumerate(required_cells):
        if not isinstance(cell, (list, tuple)) or len(cell) != 2:
            raise ValueError(
                "required cell %d must be a (power_w, sink_temp_k) pair" % index
            )
        want_power = _require_positive("cell power_w", cell[0])
        want_temp = _require_positive("cell sink_temp_k", cell[1])
        hit = False
        for point in points:
            _require_mapping("point", point)
            got_power = _require_positive(
                "applied_power_w", point.get("applied_power_w")
            )
            got_temp = _require_positive(
                "condenser_temp_k", point.get("condenser_temp_k")
            )
            if _at_most(abs(got_power - want_power), power_tol) and _at_most(
                abs(got_temp - want_temp), temp_tol
            ):
                hit = True
                break
        (covered if hit else missing).append((want_power, want_temp))
    return {
        "required": len(required_cells),
        "covered": covered,
        "missing": missing,
        "complete": not missing,
    }


def assess_start_up(start_up):
    """Grade the start-up demonstration from a cold, unprimed device."""
    _require_mapping("start_up", start_up)
    initial = _require_positive(
        "initial_temperature_k", start_up.get("initial_temperature_k")
    )
    limit = _require_positive("time_limit_s", start_up.get("time_limit_s"))
    established = start_up.get("transport_established")
    if not isinstance(established, bool):
        raise ValueError(
            "start_up transport_established must be a boolean, got %r" % (established,)
        )
    findings = []
    if not established:
        return {
            "initial_temperature_k": initial,
            "time_to_transport_s": None,
            "time_limit_s": limit,
            "verdict": "start-up-not-demonstrated",
            "demonstrated": False,
            "findings": ["transport never established on the start-up attempt"],
        }
    elapsed = _require_positive(
        "time_to_transport_s", start_up.get("time_to_transport_s")
    )
    in_time = _at_most(elapsed, limit)
    if not in_time:
        findings.append(
            "transport established after %.1f s against a limit of %.1f s"
            % (elapsed, limit)
        )
    return {
        "initial_temperature_k": initial,
        "time_to_transport_s": elapsed,
        "time_limit_s": limit,
        "verdict": "start-up-demonstrated" if in_time else "start-up-too-slow",
        "demonstrated": in_time,
        "findings": findings,
    }


def assess_regulation(regulation):
    """Grade the setpoint-regulation demonstration over its samples."""
    _require_mapping("regulation", regulation)
    setpoint = _require_positive("setpoint_k", regulation.get("setpoint_k"))
    band = _require_positive("band_k", regulation.get("band_k"))
    samples = regulation.get("samples_k")
    if not isinstance(samples, (list, tuple)) or len(samples) < 2:
        raise ValueError("regulation needs at least two samples_k readings")
    deviations = [
        abs(_require_positive("regulation sample_k", sample) - setpoint)
        for sample in samples
    ]
    worst = max(deviations)
    held = _at_most(worst, band)
    findings = []
    if not held:
        findings.append(
            "worst deviation %.4f K exceeds the regulation band %.4f K"
            % (worst, band)
        )
    return {
        "setpoint_k": setpoint,
        "band_k": band,
        "samples": len(deviations),
        "worst_deviation_k": worst,
        "verdict": "regulation-held" if held else "regulation-exceeded",
        "held": held,
        "findings": findings,
    }


def run_thermal_performance_test(campaign):
    """Whole clause 5.6.9 test with a single demonstrated / not verdict."""
    _require_mapping("campaign", campaign)
    curve = campaign.get("capability_curve")
    points = campaign.get("points")
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("campaign needs at least one mapping point")
    required_cells = campaign.get("required_cells") or [
        (
            _require_positive("applied_power_w", point.get("applied_power_w")),
            _require_positive("condenser_temp_k", point.get("condenser_temp_k")),
        )
        for point in points
    ]
    steady_limit = campaign.get(
        "steady_rate_limit_k_per_min", DEFAULT_STEADY_RATE_LIMIT_K_PER_MIN
    )
    graded = [
        grade_mapping_point(
            point,
            curve,
            steady_rate_limit_k_per_min=steady_limit,
            max_drop_k=campaign.get("max_drop_k"),
        )
        for point in points
    ]
    coverage = mapping_coverage(points, required_cells)
    start_up = assess_start_up(campaign["start_up"]) if campaign.get("start_up") else None
    regulation = (
        assess_regulation(campaign["regulation"]) if campaign.get("regulation") else None
    )
    findings = []
    for index, result in enumerate(graded):
        for note in result["findings"]:
            findings.append("point %d: %s" % (index, note))
    if not coverage["complete"]:
        findings.append(
            "%d required mapping cells were never run" % len(coverage["missing"])
        )
    if start_up is None:
        findings.append("no start-up demonstration was supplied")
    else:
        findings.extend("start-up: %s" % note for note in start_up["findings"])
    if regulation is None:
        findings.append("no regulation demonstration was supplied")
    else:
        findings.extend("regulation: %s" % note for note in regulation["findings"])
    worst_utilisation = max(result["utilisation"] for result in graded)
    demonstrated = (
        all(result["accepted"] for result in graded)
        and coverage["complete"]
        and start_up is not None
        and start_up["demonstrated"]
        and regulation is not None
        and regulation["held"]
    )
    return {
        "points": graded,
        "coverage": coverage,
        "start_up": start_up,
        "regulation": regulation,
        "worst_utilisation": worst_utilisation,
        "accepted_points": sum(1 for result in graded if result["accepted"]),
        "verdict": "performance-demonstrated"
        if demonstrated
        else "performance-not-demonstrated",
        "demonstrated": demonstrated,
        "findings": findings,
    }
