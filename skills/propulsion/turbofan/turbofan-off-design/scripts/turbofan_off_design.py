#!/usr/bin/env python3
"""Turbofan off-design performance relations (SI units, stdlib only).

Off-design turbofan assessment: corrected mass flow and corrected
speed at the engine inlet, altitude net thrust with the ram drag
penalty, SFC altitude and throttle behavior, throttle-setting
sanity, and the fan/core component matching verdict. Invalid inputs
raise ValueError instead of returning nonsense numbers.

Contract: docs/harness-contract.md gate 3.
"""

import math


def corrected_mass_flow(m_dot, t, p, t_ref=288.15, p_ref=101325.0):
    """Correct physical mass flow (kg/s) to the reference condition.

    m_dot_c = m_dot * sqrt(t_ref / t) / (p / p_ref), with t in K and
    p in Pa. At t = t_ref and p = p_ref the corrected flow equals
    the physical flow.
    """
    if m_dot <= 0.0:
        raise ValueError("mass flow must be positive, got %r" % (m_dot,))
    if t <= 0.0:
        raise ValueError("temperature must be positive, got %r" % (t,))
    if p <= 0.0:
        raise ValueError("pressure must be positive, got %r" % (p,))
    if t_ref <= 0.0:
        raise ValueError("reference temperature must be positive, got %r" % (t_ref,))
    if p_ref <= 0.0:
        raise ValueError("reference pressure must be positive, got %r" % (p_ref,))
    return m_dot * math.sqrt(t_ref / t) / (p / p_ref)


def corrected_speed(physical_speed, t, t_ref=288.15):
    """Correct physical rotor speed (rpm) to the reference condition.

    N_c = N * sqrt(t_ref / t), with t in K. At t = t_ref the
    corrected speed equals the physical speed.
    """
    if physical_speed < 0.0:
        raise ValueError("speed must be non-negative, got %r" % (physical_speed,))
    if t <= 0.0:
        raise ValueError("temperature must be positive, got %r" % (t,))
    if t_ref <= 0.0:
        raise ValueError("reference temperature must be positive, got %r" % (t_ref,))
    return physical_speed * math.sqrt(t_ref / t)


def net_thrust_altitude(sea_level_thrust, rho, rho0, mach_factor, ram_drag=0.0):
    """Scale sea-level static thrust (N) to an altitude flight point.

    F_alt = F_SL * (rho / rho0) * mach_factor - ram_drag, with
    rho/rho0 the density ratio, mach_factor the ram and Mach
    recovery factor (about 1 at low speed, lower at high Mach), and
    ram_drag (N) the inlet momentum drag subtracted from gross
    thrust to give net thrust.
    """
    if sea_level_thrust <= 0.0:
        raise ValueError("sea-level thrust must be positive, got %r" % (sea_level_thrust,))
    if rho <= 0.0:
        raise ValueError("density must be positive, got %r" % (rho,))
    if rho0 <= 0.0:
        raise ValueError("reference density must be positive, got %r" % (rho0,))
    if mach_factor <= 0.0 or mach_factor > 1.5:
        raise ValueError(
            "mach factor must be in (0, 1.5], got %r" % (mach_factor,)
        )
    if ram_drag < 0.0:
        raise ValueError("ram drag must be non-negative, got %r" % (ram_drag,))
    return sea_level_thrust * (rho / rho0) * mach_factor - ram_drag


def sfc_altitude_factor(sfc_sea_level, rho, rho0, exponent=0.15):
    """Apply the SFC altitude factor to a sea-level SFC value.

    SFC_alt = SFC_SL * (rho / rho0)^exponent, with exponent in the
    quick-model range 0.1 to 0.2 (default 0.15). SFC falls with
    altitude (density ratio below 1) and equals the sea-level value
    at the reference density.
    """
    if sfc_sea_level <= 0.0:
        raise ValueError("sea-level SFC must be positive, got %r" % (sfc_sea_level,))
    if rho <= 0.0:
        raise ValueError("density must be positive, got %r" % (rho,))
    if rho0 <= 0.0:
        raise ValueError("reference density must be positive, got %r" % (rho0,))
    if exponent <= 0.0:
        raise ValueError("exponent must be positive, got %r" % (exponent,))
    return sfc_sea_level * (rho / rho0) ** exponent


def throttle_verdict(throttle_frac):
    """Classify a throttle fraction of the maximum rating.

    Bands: below 0.05 below-idle (unstable combustor), 0.05 to 0.30
    idle, 0.30 to 0.65 cruise, 0.65 to 0.95 climb, 0.95 to 1.00
    max-continuous, 1.00 to 1.05 over-throttle (rating exceeded).
    Fractions outside (0, 1.05] are rejected as out of range.
    """
    if throttle_frac <= 0.0 or throttle_frac > 1.05:
        raise ValueError(
            "throttle fraction must be in (0, 1.05], got %r" % (throttle_frac,)
        )
    if throttle_frac < 0.05:
        return "below-idle"
    if throttle_frac < 0.30:
        return "idle"
    if throttle_frac < 0.65:
        return "cruise"
    if throttle_frac < 0.95:
        return "climb"
    if throttle_frac <= 1.00:
        return "max-continuous"
    return "over-throttle"


def component_matching_verdict(fan_matching, core_matching, band=0.10):
    """Judge fan and core matching from their corrected-flow deltas.

    The deltas are fractional deviations from the matched operating
    point (0.05 = 5 percent high, -0.05 = 5 percent low). Both must
    stay within the band (default 0.10 = plus/minus 10 percent) for
    the point to be matched; otherwise the verdict names the
    component(s) off-design.
    """
    if band <= 0.0:
        raise ValueError("band must be positive, got %r" % (band,))
    fan_ok = abs(fan_matching) <= band
    core_ok = abs(core_matching) <= band
    if fan_ok and core_ok:
        return "matched"
    if not fan_ok and not core_ok:
        return "fan-and-core-off-design"
    if not fan_ok:
        return "fan-off-design"
    return "core-off-design"
