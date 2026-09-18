#!/usr/bin/env python3
"""Component rating limits while an LCL or HLCL holds current limitation.

Anchor: ECSS-E-ST-20-20C clause 5.2.3.4.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A latching current limiter spends almost all its life in switch mode,
where the pass element is saturated and dissipates almost nothing. The
interesting state is the other one. Once the branch demands more than
the limit, the element leaves saturation and holds the current at the
limit value by standing off the difference between the bus voltage and
whatever the load pulls the output down to. In that state it behaves
as a linear element carrying the full limited current with most of the
bus voltage across it, and it stays there for the whole trip-off delay
before the device latches off.

The clause is about what that state does to the parts. Three limits
are live at once:

    junction temperature  the dissipation raises the junction above the
                          mounting reference through the thermal path,
                          transiently for a short delay and in steady
                          state for a long one
    safe operating area   at a given drain-source voltage the element
                          has a pulse-duration-dependent current
                          ceiling that is far below its d.c. rating
    derated ratings       the current, the voltage and the junction
                          temperature all carry a derating factor, so
                          the limit that applies is never the datasheet
                          maximum

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MODE_SWITCH = "switch-mode"
MODE_LIMITATION = "current-limitation-mode"
MODES = (MODE_SWITCH, MODE_LIMITATION)

WITHIN_RATINGS = "limitation-mode-within-ratings"
BEYOND_RATINGS = "limitation-mode-beyond-ratings"

# Conservative defaults when a project does not declare its own.
DEFAULT_CURRENT_DERATING = 0.75
DEFAULT_VOLTAGE_DERATING = 0.75
DEFAULT_JUNCTION_DERATING = 0.80

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


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_derating(name, value):
    number = _require_positive(name, value)
    if number > 1.0:
        raise ValueError("%s must be a factor at or below one, got %r" % (name, value))
    return number


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A dissipation built from a voltage difference and a limited current
    can land a few units in the last place either side of a ceiling
    written in watts. The ceiling is never relaxed; only the comparison
    tolerates the representation error, which is why no caller uses a
    bare <= on a derived float.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def operating_mode(demanded_current_a, limit_current_a):
    """Whether the branch demand puts the device into limitation."""
    demanded = _require_non_negative("demanded_current_a", demanded_current_a)
    limit = _require_positive("limit_current_a", limit_current_a)
    if demanded > limit and not math.isclose(
        demanded, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        return MODE_LIMITATION
    return MODE_SWITCH


def pass_element_voltage_v(bus_voltage_v, output_voltage_v):
    """Voltage the pass element stands off while it holds the limit."""
    bus = _require_positive("bus_voltage_v", bus_voltage_v)
    output = _require_non_negative("output_voltage_v", output_voltage_v)
    if output > bus:
        raise ValueError(
            "output_voltage_v %g cannot exceed bus_voltage_v %g in limitation"
            % (output, bus)
        )
    return bus - output


def limitation_dissipation_w(bus_voltage_v, output_voltage_v, limit_current_a):
    """Power the pass element turns into heat while limiting."""
    drop = pass_element_voltage_v(bus_voltage_v, output_voltage_v)
    current = _require_positive("limit_current_a", limit_current_a)
    return drop * current


def limitation_energy_j(power_w, duration_s):
    """Energy the element absorbs over the whole trip-off delay."""
    power = _require_non_negative("power_w", power_w)
    duration = _require_positive("duration_s", duration_s)
    return power * duration


def transient_thermal_impedance(steady_resistance_c_per_w, time_constant_s, duration_s):
    """Thermal impedance the path presents for a pulse of that length.

    A single-pole path warms towards its steady-state resistance, so a
    delay much shorter than the time constant sees only part of it and a
    long one sees effectively all of it.
    """
    steady = _require_positive("thermal_resistance_c_per_w", steady_resistance_c_per_w)
    tau = _require_positive("thermal_time_constant_s", time_constant_s)
    duration = _require_positive("duration_s", duration_s)
    return steady * (1.0 - math.exp(-duration / tau))


def junction_temperature_c(power_w, thermal_impedance_c_per_w, reference_temperature_c):
    """Junction temperature the dissipation reaches above its mounting."""
    power = _require_non_negative("power_w", power_w)
    impedance = _require_positive("thermal_impedance_c_per_w", thermal_impedance_c_per_w)
    reference = _require_number("reference_temperature_c", reference_temperature_c)
    return reference + power * impedance


def derated_limit(rated_value, derating_factor):
    """The limit that actually applies once the derating rule is used."""
    rated = _require_positive("rated_value", rated_value)
    factor = _require_derating("derating_factor", derating_factor)
    return rated * factor


def derated_junction_limit_c(rated_junction_c, reference_c, derating_factor):
    """Junction ceiling after derating the rise above the mounting point.

    Derating a temperature in degrees Celsius directly would make the
    ceiling depend on the unit, so the factor is applied to the allowed
    rise above the mounting reference, which is the physical quantity.
    """
    rated = _require_number("rated_junction_c", rated_junction_c)
    reference = _require_number("reference_temperature_c", reference_c)
    factor = _require_derating("derating_factor", derating_factor)
    if rated <= reference:
        raise ValueError(
            "rated_junction_c %g must sit above the mounting reference %g"
            % (rated, reference)
        )
    return reference + (rated - reference) * factor


def _soa_points(soa_curve):
    """Validated, voltage-ordered points of a safe operating area boundary."""
    if not isinstance(soa_curve, (list, tuple)) or len(soa_curve) < 2:
        raise ValueError("soa_curve needs at least two (voltage, current) points")
    points = []
    for index, point in enumerate(soa_curve):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("soa_curve point %d must be a (voltage, current) pair" % (index,))
        volts = _require_positive("soa_curve point %d voltage" % (index,), point[0])
        amps = _require_positive("soa_curve point %d current" % (index,), point[1])
        points.append((volts, amps))
    points.sort()
    for earlier, later in zip(points, points[1:]):
        if math.isclose(earlier[0], later[0], rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
            raise ValueError("soa_curve holds two points at the same voltage")
    return tuple(points)


def soa_curve_span_v(soa_curve):
    """Lowest and highest voltage the given boundary actually covers."""
    points = _soa_points(soa_curve)
    return (points[0][0], points[-1][0])


def soa_voltage_is_covered(soa_curve, voltage_v):
    """Whether the boundary says anything at all at that voltage."""
    low, high = soa_curve_span_v(soa_curve)
    voltage = _require_positive("voltage_v", voltage_v)
    if voltage < low:
        return math.isclose(voltage, low, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)
    if voltage > high:
        return math.isclose(voltage, high, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)
    return True


def soa_boundary_current_a(soa_curve, voltage_v):
    """Current ceiling the safe operating area allows at that voltage.

    The boundary is given as points of (drain-source voltage, allowed
    current) for the pulse duration in question, and is interpolated
    logarithmically between them, which is how such a boundary is drawn.
    A voltage outside the span of the curve is refused rather than
    extrapolated.
    """
    points = _soa_points(soa_curve)
    voltage = _require_positive("voltage_v", voltage_v)
    low, high = points[0][0], points[-1][0]
    if voltage < low or voltage > high:
        if not (
            math.isclose(voltage, low, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)
            or math.isclose(voltage, high, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)
        ):
            raise ValueError(
                "voltage %g lies outside the curve span %g to %g; the boundary is not extrapolated"
                % (voltage, low, high)
            )
    for (v0, i0), (v1, i1) in zip(points, points[1:]):
        if voltage <= v1 or math.isclose(voltage, v1, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
            if math.isclose(voltage, v0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
                return i0
            if math.isclose(voltage, v1, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
                return i1
            span = math.log(v1) - math.log(v0)
            share = (math.log(voltage) - math.log(v0)) / span
            return math.exp(math.log(i0) + share * (math.log(i1) - math.log(i0)))
    return points[-1][1]


def margin_fraction(value, limit):
    """Headroom a value keeps against its limit, negative once past it."""
    bound = _require_positive("limit", limit)
    number = _require_number("value", value)
    return (bound - number) / bound


def assess_limitation_mode(case):
    """Full clause 5.2.3.4.1 judgement of one limitation-mode condition."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))

    limit_current = _require_positive("limit_current_a", case.get("limit_current_a"))
    demanded = _require_non_negative(
        "demanded_current_a", case.get("demanded_current_a", limit_current)
    )
    mode = operating_mode(demanded, limit_current)
    bus_v = _require_positive("bus_voltage_v", case.get("bus_voltage_v"))
    output_v = _require_non_negative("output_voltage_v", case.get("output_voltage_v"))
    delay = _require_positive("trip_off_delay_s", case.get("trip_off_delay_s"))
    reference_c = _require_number(
        "reference_temperature_c", case.get("reference_temperature_c")
    )
    thermal_r = _require_positive(
        "thermal_resistance_c_per_w", case.get("thermal_resistance_c_per_w")
    )
    thermal_tau = _require_positive(
        "thermal_time_constant_s", case.get("thermal_time_constant_s")
    )
    rated_current = _require_positive("rated_current_a", case.get("rated_current_a"))
    rated_voltage = _require_positive("rated_voltage_v", case.get("rated_voltage_v"))
    rated_junction = _require_number("rated_junction_c", case.get("rated_junction_c"))
    current_factor = _require_derating(
        "current_derating_factor", case.get("current_derating_factor", DEFAULT_CURRENT_DERATING)
    )
    voltage_factor = _require_derating(
        "voltage_derating_factor", case.get("voltage_derating_factor", DEFAULT_VOLTAGE_DERATING)
    )
    junction_factor = _require_derating(
        "junction_derating_factor",
        case.get("junction_derating_factor", DEFAULT_JUNCTION_DERATING),
    )

    drop_v = pass_element_voltage_v(bus_v, output_v)
    dissipation_w = limitation_dissipation_w(bus_v, output_v, limit_current)
    energy_j = limitation_energy_j(dissipation_w, delay)
    impedance = transient_thermal_impedance(thermal_r, thermal_tau, delay)
    junction_c = junction_temperature_c(dissipation_w, impedance, reference_c)

    current_limit = derated_limit(rated_current, current_factor)
    voltage_limit = derated_limit(rated_voltage, voltage_factor)
    junction_limit_c = derated_junction_limit_c(rated_junction, reference_c, junction_factor)

    findings = []
    if mode != MODE_LIMITATION:
        findings.append(
            "demanded current %.3f A does not exceed the %.3f A limit, so the device stays in switch mode and this assessment does not apply"
            % (demanded, limit_current)
        )

    if not _at_most(limit_current, current_limit):
        findings.append(
            "limited current %.3f A exceeds the derated current rating %.3f A"
            % (limit_current, current_limit)
        )
    if not _at_most(drop_v, voltage_limit):
        findings.append(
            "pass element stands off %.3f V, above the derated voltage rating %.3f V"
            % (drop_v, voltage_limit)
        )
    if not _at_most(junction_c, junction_limit_c):
        findings.append(
            "junction reaches %.1f C over the %.3f s delay, above the derated ceiling %.1f C"
            % (junction_c, delay, junction_limit_c)
        )

    soa_ceiling = None
    if case.get("soa_curve") is not None:
        if not soa_voltage_is_covered(case.get("soa_curve"), drop_v):
            low, high = soa_curve_span_v(case.get("soa_curve"))
            findings.append(
                "the safe operating area boundary spans %.3f V to %.3f V and says nothing at the %.3f V the element stands off; extend the curve rather than extrapolating it"
                % (low, high, drop_v)
            )
        else:
            soa_ceiling = soa_boundary_current_a(case.get("soa_curve"), drop_v)
            if not _at_most(limit_current, soa_ceiling):
                findings.append(
                    "limited current %.3f A sits above the %.3f A safe operating area boundary at %.3f V for this pulse length"
                    % (limit_current, soa_ceiling, drop_v)
                )

    within = not findings
    return {
        "mode": mode,
        "pass_element_voltage_v": drop_v,
        "dissipation_w": dissipation_w,
        "energy_j": energy_j,
        "transient_thermal_impedance_c_per_w": impedance,
        "junction_temperature_c": junction_c,
        "derated_current_limit_a": current_limit,
        "derated_voltage_limit_v": voltage_limit,
        "derated_junction_limit_c": junction_limit_c,
        "soa_boundary_current_a": soa_ceiling,
        "current_margin_fraction": margin_fraction(limit_current, current_limit),
        "voltage_margin_fraction": margin_fraction(drop_v, voltage_limit),
        "verdict": WITHIN_RATINGS if within else BEYOND_RATINGS,
        "within_ratings": within,
        "findings": findings,
    }
