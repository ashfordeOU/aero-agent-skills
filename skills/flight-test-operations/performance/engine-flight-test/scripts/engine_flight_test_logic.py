#!/usr/bin/env python3
"""Engine flight test logic (paraphrase, common flight-test methodology).

Simplified installed-performance model in the FAR-25 / CS-25 general
performance context (standards-map.yaml, far-25 and cs-25:
reference-only): the determined thrust comes from the rate of climb or
the level acceleration with the measured drag, the fuel flow from the
thrust specific fuel consumption, the exhaust gas temperature margin
against the limit with an ISA day correction, the altitude thrust from
the sea-level value and the density ratio, and the acceleration and
deceleration transient times from the weight and the excess or idle
thrust force between the test speeds. Units: forces and weight in N,
speeds in m/s, fuel flow in kg/s, thrust specific fuel consumption in
kg/(N*s), temperatures in deg C, ambient temperature in K, densities
in kg/m^3.
"""

import math


def thrust_from_rate_of_climb(weight_n, roc_m_s, v_tas_m_s, drag_n):
    """Installed thrust determined from a steady rate of climb, in N.

    T = D + W * ROC / V, the small-angle form of T = D + W * sin(gamma)
    with sin(gamma) approximately ROC / V. Raises ValueError on a
    non-positive weight, airspeed, or drag, or a negative rate of
    climb.
    """
    if weight_n <= 0:
        raise ValueError("weight must be > 0, got %r" % (weight_n,))
    if roc_m_s < 0:
        raise ValueError("rate of climb must be >= 0, got %r" % (roc_m_s,))
    if v_tas_m_s <= 0:
        raise ValueError("true airspeed must be > 0, got %r" % (v_tas_m_s,))
    if drag_n <= 0:
        raise ValueError("drag must be > 0, got %r" % (drag_n,))
    return drag_n + weight_n * roc_m_s / v_tas_m_s


def thrust_from_acceleration(weight_n, accel_m_s2, drag_n, g_m_s2=9.80665):
    """Installed thrust determined from a level acceleration, in N.

    T = D + (W / g) * a, the level flight balance from Newton's second
    law with the mass from the weight. Raises ValueError on a
    non-positive weight, drag, or g, or a negative acceleration.
    """
    if weight_n <= 0:
        raise ValueError("weight must be > 0, got %r" % (weight_n,))
    if accel_m_s2 < 0:
        raise ValueError("acceleration must be >= 0, got %r" % (accel_m_s2,))
    if drag_n <= 0:
        raise ValueError("drag must be > 0, got %r" % (drag_n,))
    if g_m_s2 <= 0:
        raise ValueError("gravitational acceleration must be > 0, got %r" % (g_m_s2,))
    return drag_n + (weight_n / g_m_s2) * accel_m_s2


def fuel_flow_from_tsfc(tsfc_kg_n_s, thrust_n):
    """Fuel flow at the determined thrust, in kg/s.

    Wf = TSFC * T. Raises ValueError on non-positive inputs.
    """
    if tsfc_kg_n_s <= 0:
        raise ValueError("thrust specific fuel consumption must be > 0, got %r" % (tsfc_kg_n_s,))
    if thrust_n <= 0:
        raise ValueError("thrust must be > 0, got %r" % (thrust_n,))
    return tsfc_kg_n_s * thrust_n


def tsfc_from_flight(fuel_flow_kg_s, thrust_n):
    """Achieved thrust specific fuel consumption, in kg/(N*s).

    TSFC = Wf / T from the measured fuel flow and the determined
    thrust. Raises ValueError on non-positive inputs.
    """
    if fuel_flow_kg_s <= 0:
        raise ValueError("fuel flow must be > 0, got %r" % (fuel_flow_kg_s,))
    if thrust_n <= 0:
        raise ValueError("thrust must be > 0, got %r" % (thrust_n,))
    return fuel_flow_kg_s / thrust_n


def egt_margin(egt_measured_c, egt_limit_c):
    """Exhaust gas temperature margin against the limit, in deg C.

    margin = T_limit - T_egt. A negative margin means the exhaust gas
    temperature exceeds the limit and is a test finding, not an error.
    Raises ValueError when the measured temperature is below absolute
    zero or the limit is non-positive.
    """
    if egt_measured_c < -273.15:
        raise ValueError("measured EGT below absolute zero, got %r" % (egt_measured_c,))
    if egt_limit_c <= 0:
        raise ValueError("EGT limit must be > 0, got %r" % (egt_limit_c,))
    return egt_limit_c - egt_measured_c


def egt_corrected_to_isa(egt_measured_c, t_amb_k):
    """Exhaust gas temperature corrected to the ISA day, in deg C.

    T_corr = (T_egt + 273.15) * 288.15 / T_amb - 273.15, the absolute
    temperature ratio correction. Raises ValueError on a non-positive
    ambient temperature.
    """
    if t_amb_k <= 0:
        raise ValueError("ambient temperature must be > 0, got %r" % (t_amb_k,))
    return (egt_measured_c + 273.15) * 288.15 / t_amb_k - 273.15


def thrust_at_altitude(thrust_sl_n, rho_alt, rho_sl):
    """Sea-level thrust scaled to the test altitude, in N.

    T_alt = T_sl * rho_alt / rho_sl, the density ratio scaling at
    constant Mach number. Raises ValueError on non-positive inputs.
    """
    if thrust_sl_n <= 0:
        raise ValueError("sea-level thrust must be > 0, got %r" % (thrust_sl_n,))
    if rho_alt <= 0:
        raise ValueError("altitude density must be > 0, got %r" % (rho_alt,))
    if rho_sl <= 0:
        raise ValueError("sea-level density must be > 0, got %r" % (rho_sl,))
    return thrust_sl_n * rho_alt / rho_sl


def accel_time_between_speeds(weight_n, v1_m_s, v2_m_s, excess_thrust_n, g_m_s2=9.80665):
    """Time to accelerate between the test speeds, in s.

    t = (W / g) * (V2 - V1) / (T - D) at constant excess thrust.
    Raises ValueError when the weight, excess thrust, or g is
    non-positive, or when V2 does not exceed V1.
    """
    if weight_n <= 0:
        raise ValueError("weight must be > 0, got %r" % (weight_n,))
    if v2_m_s <= v1_m_s:
        raise ValueError("acceleration needs V2 > V1, got V1=%r V2=%r" % (v1_m_s, v2_m_s))
    if excess_thrust_n <= 0:
        raise ValueError("excess thrust must be > 0, got %r" % (excess_thrust_n,))
    if g_m_s2 <= 0:
        raise ValueError("gravitational acceleration must be > 0, got %r" % (g_m_s2,))
    return (weight_n / g_m_s2) * (v2_m_s - v1_m_s) / excess_thrust_n


def decel_time_between_speeds(weight_n, v1_m_s, v2_m_s, decel_force_n, g_m_s2=9.80665):
    """Time to decelerate between the test speeds, in s.

    t = (W / g) * (V1 - V2) / (D - T_idle) at constant idle thrust
    drag force. Raises ValueError when the weight, decel force, or g
    is non-positive, or when V1 does not exceed V2.
    """
    if weight_n <= 0:
        raise ValueError("weight must be > 0, got %r" % (weight_n,))
    if v1_m_s <= v2_m_s:
        raise ValueError("deceleration needs V1 > V2, got V1=%r V2=%r" % (v1_m_s, v2_m_s))
    if decel_force_n <= 0:
        raise ValueError("decel force must be > 0, got %r" % (decel_force_n,))
    if g_m_s2 <= 0:
        raise ValueError("gravitational acceleration must be > 0, got %r" % (g_m_s2,))
    return (weight_n / g_m_s2) * (v1_m_s - v2_m_s) / decel_force_n


def thrust_verification_error(achieved_n, predicted_n):
    """Achieved thrust against the predicted installed value, in percent.

    e = (T_ach - T_pred) / T_pred * 100; negative means a thrust
    shortfall. Raises ValueError on non-positive inputs.
    """
    if achieved_n <= 0:
        raise ValueError("achieved thrust must be > 0, got %r" % (achieved_n,))
    if predicted_n <= 0:
        raise ValueError("predicted thrust must be > 0, got %r" % (predicted_n,))
    return (achieved_n - predicted_n) / predicted_n * 100.0
