#!/usr/bin/env python3
"""Ideal gas turbine (Brayton) cycle logic, air-standard (paraphrase,
common-knowledge thermodynamics).

Common-knowledge summary (standards-map.yaml, far-33: public domain
regulation context): FAR-33 concerns engine type certification and
does not prescribe cycle analysis methods. The ideal Brayton cycle
relations below are standard undergraduate thermodynamics: the
compressor and turbine are isentropic, the working fluid is a perfect
gas with constant specific heat, and the cycle thermal efficiency
depends only on the pressure ratio and the specific heat ratio.

Units: temperatures in kelvin, pressure ratio dimensionless, specific
heat ratio gamma dimensionless, cp in J/(kg K), specific work in J/kg.
"""


def brayton_thermal_efficiency(pressure_ratio, gamma=1.4):
    """Ideal Brayton cycle thermal efficiency, eta = 1 - PR**((1-gamma)/gamma).

    Valid for pressure_ratio > 1 and gamma > 1 (dimensionless).
    Returns the dimensionless efficiency (fraction, not percent)."""
    if pressure_ratio <= 1:
        raise ValueError("pressure ratio must be > 1, got %r" % (pressure_ratio,))
    if gamma <= 1:
        raise ValueError("specific heat ratio must be > 1, got %r" % (gamma,))
    return 1.0 - pressure_ratio ** ((1.0 - gamma) / gamma)


def compressor_exit_temperature(t1_k, pressure_ratio, gamma=1.4):
    """Isentropic compressor exit temperature, T2 = T1 * PR**((gamma-1)/gamma).

    t1_k in kelvin (> 0), pressure_ratio dimensionless (> 1).
    Returns the exit temperature in kelvin."""
    if t1_k <= 0:
        raise ValueError("inlet temperature must be > 0, got %r" % (t1_k,))
    if pressure_ratio <= 1:
        raise ValueError("pressure ratio must be > 1, got %r" % (pressure_ratio,))
    return t1_k * pressure_ratio ** ((gamma - 1.0) / gamma)


def turbine_exit_temperature(t3_k, pressure_ratio, gamma=1.4):
    """Isentropic turbine exit temperature, T4 = T3 / PR**((gamma-1)/gamma).

    t3_k in kelvin (> 0), pressure_ratio dimensionless (> 1).
    Returns the exit temperature in kelvin."""
    if t3_k <= 0:
        raise ValueError("turbine inlet temperature must be > 0, got %r" % (t3_k,))
    if pressure_ratio <= 1:
        raise ValueError("pressure ratio must be > 1, got %r" % (pressure_ratio,))
    return t3_k / pressure_ratio ** ((gamma - 1.0) / gamma)


def cycle_specific_work(t1_k, t3_k, pressure_ratio, gamma=1.4, cp=1005.0):
    """Net specific work, w = cp*(T3 - T2) - cp*(T2 - T1), T2 isentropic.

    Temperatures in kelvin (> 0), pressure_ratio dimensionless (> 1),
    cp in J/(kg K) (> 0). Returns the net specific work in J/kg."""
    if t1_k <= 0:
        raise ValueError("inlet temperature must be > 0, got %r" % (t1_k,))
    if t3_k <= 0:
        raise ValueError("turbine inlet temperature must be > 0, got %r" % (t3_k,))
    if pressure_ratio <= 1:
        raise ValueError("pressure ratio must be > 1, got %r" % (pressure_ratio,))
    if cp <= 0:
        raise ValueError("specific heat must be > 0, got %r" % (cp,))
    t2_k = compressor_exit_temperature(t1_k, pressure_ratio, gamma)
    return cp * (t3_k - t2_k) - cp * (t2_k - t1_k)
