#!/usr/bin/env python3
"""Regenerative gas turbine (Brayton) cycle logic, air-standard (paraphrase,
common-knowledge thermodynamics).

Common-knowledge summary (standards-map.yaml, far-33: public domain
regulation context): FAR-33 concerns engine type certification and
does not prescribe cycle analysis methods. The regenerative Brayton
cycle relations below are standard undergraduate thermodynamics: a
regenerator transfers heat from the turbine exhaust to the compressor
exit air before the combustor, with effectiveness eps, and the cycle
thermal efficiency follows from the pressure ratio, the temperature
limits, and that effectiveness.

Units: temperatures in kelvin, pressure ratio dimensionless, specific
heat ratio gamma dimensionless, regenerator effectiveness dimensionless
(0 to 1), efficiencies as fractions, efficiency gain in percentage
points.
"""


def _validate_cycle_temps(t1_k, t3_k):
    """Common temperature validation: 0 < t1 < t3 (kelvin)."""
    if t1_k <= 0:
        raise ValueError("inlet temperature must be > 0, got %r" % (t1_k,))
    if t3_k <= t1_k:
        raise ValueError(
            "turbine inlet temperature must exceed inlet temperature, "
            "got t1=%r t3=%r" % (t1_k, t3_k)
        )


def _validate_gamma(gamma):
    """Specific heat ratio must exceed 1 (dimensionless)."""
    if gamma <= 1:
        raise ValueError("specific heat ratio must be > 1, got %r" % (gamma,))


def _validate_pressure_ratio(pressure_ratio):
    """Pressure ratio must exceed 1 (dimensionless)."""
    if pressure_ratio <= 1:
        raise ValueError("pressure ratio must be > 1, got %r" % (pressure_ratio,))


def simple_cycle_efficiency(pressure_ratio, t1_k, t3_k, gamma=1.4):
    """Simple Brayton cycle thermal efficiency, eta = 1 - PR**((1-gamma)/gamma).

    pressure_ratio dimensionless (> 1), t1_k, t3_k in kelvin (0 < t1 < t3),
    gamma dimensionless (> 1). Returns the dimensionless efficiency
    (fraction, not percent)."""
    _validate_cycle_temps(t1_k, t3_k)
    _validate_pressure_ratio(pressure_ratio)
    _validate_gamma(gamma)
    return 1.0 - pressure_ratio ** ((1.0 - gamma) / gamma)


def regenerative_efficiency(pressure_ratio, t1_k, t3_k, effectiveness, gamma=1.4):
    """Regenerative Brayton cycle thermal efficiency with effectiveness eps.

    eta = 1 - (T6 - T1)/(T3 - T5), where T2 = T1*r and T4 = T3/r with
    r = PR**((gamma-1)/gamma), T5 = T2 + eps*(T4 - T2) is the regenerator
    cold-side exit, and T6 = T4 - eps*(T4 - T2) the hot-side exit.

    pressure_ratio dimensionless (> 1), temperatures in kelvin
    (0 < t1 < t3), effectiveness dimensionless (0 <= eps <= 1),
    gamma dimensionless (> 1). At eps = 0 this reproduces the simple
    cycle. Returns the dimensionless efficiency (fraction)."""
    _validate_cycle_temps(t1_k, t3_k)
    _validate_pressure_ratio(pressure_ratio)
    _validate_gamma(gamma)
    if effectiveness < 0.0 or effectiveness > 1.0:
        raise ValueError(
            "regenerator effectiveness must be in [0, 1], got %r" % (effectiveness,)
        )
    r = pressure_ratio ** ((gamma - 1.0) / gamma)
    t2_k = t1_k * r
    t4_k = t3_k / r
    t5_k = t2_k + effectiveness * (t4_k - t2_k)
    t6_k = t4_k - effectiveness * (t4_k - t2_k)
    return 1.0 - (t6_k - t1_k) / (t3_k - t5_k)


def optimum_pressure_ratio_regenerative(t1_k, t3_k, gamma=1.4):
    """Optimum pressure ratio for the regenerative cycle.

    The pressure ratio at which the turbine exit temperature equals the
    compressor exit temperature (T4 = T2), so the regenerator has zero
    temperature difference: PR_opt = (T3/T1)**(gamma/(2*(gamma-1))).
    Below it regeneration raises efficiency, above it lowers it.

    Temperatures in kelvin (0 < t1 < t3), gamma dimensionless (> 1).
    Returns the dimensionless pressure ratio."""
    _validate_cycle_temps(t1_k, t3_k)
    _validate_gamma(gamma)
    return (t3_k / t1_k) ** (gamma / (2.0 * (gamma - 1.0)))


def efficiency_gain(eta_regenerative, eta_simple):
    """Regenerative over simple cycle efficiency gain in percentage points.

    gain = (eta_regenerative - eta_simple) * 100. Both efficiencies are
    fractions strictly between 0 and 1. A negative result means
    regeneration lowered the efficiency."""
    for eta in (eta_regenerative, eta_simple):
        if eta <= 0.0 or eta >= 1.0:
            raise ValueError(
                "efficiency must be a fraction in (0, 1), got %r" % (eta,)
            )
    return (eta_regenerative - eta_simple) * 100.0
