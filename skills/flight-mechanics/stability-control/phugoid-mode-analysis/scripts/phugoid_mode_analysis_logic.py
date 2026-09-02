#!/usr/bin/env python3
"""Phugoid (long-period) longitudinal mode analysis logic (common
flight-mechanics methodology, Lanchester approximation, paraphrase).

The phugoid is the slow longitudinal oscillation that follows a speed
or thrust disturbance. It trades kinetic and potential energy along the
flight path at roughly constant angle of attack, so it is a height and
airspeed oscillation rather than a pitch oscillation. Lanchester's
approximation treats the motion at constant cruise speed V and constant
lift coefficient, giving a lightly damped oscillation whose frequency
depends on gravity and speed only:

  omega_p = g0 * sqrt(2) / V              [rad/s]  natural frequency
  T_p     = 2 * pi / omega_p = 2 * pi * V / (g0 * sqrt(2))   [s]
  zeta_p  = 1 / (sqrt(2) * (L/D))                  [drag damping]
  omega_d = omega_p * sqrt(1 - zeta_p^2)  [rad/s]  damped frequency
  zeta_p * omega_p = g0 / (V * (L/D))              [/s] identity
  t_half  = ln(2) / (zeta_p * omega_p)    [s]      time to half
  N_half  = t_half / T_p                  [cycles] cycles to half

The damping term comes from drag: each cycle the drag does work against
the energy exchange, so the decay rate scales with the inverse of the
lift-to-drag ratio. Small-damping validity: the Lanchester model
assumes zeta_p << 1, which needs L/D >= 8 (zeta_p <= 0.088); the
frequency separation from the short period mode is assumed (the phugoid
frequency must sit well below the short period frequency for the
two-timescale split to hold). All functions raise ValueError on
non-physical inputs.
"""

import math

G = 9.80665  # standard gravity, m/s^2

MIN_LD = 8.0      # L/D floor for the small-damping approximation
MIN_LD_HARD = 1.0  # physical floor: zeta_p = 1/(sqrt(2)*(L/D)) must be < 1
SQRT2 = math.sqrt(2.0)


def _require_number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))


def _require_positive(name, value):
    _require_number(name, value)
    if value <= 0:
        raise ValueError("%s must be > 0, got %r" % (name, value))


def phugoid_frequency(v, g=G):
    """Phugoid natural frequency omega_p = g * sqrt(2) / V, in rad/s."""
    _require_positive("speed", v)
    _require_positive("gravity", g)
    return g * SQRT2 / v


def phugoid_period(v, g=G):
    """Phugoid period T_p = 2 * pi / omega_p, in seconds."""
    omega = phugoid_frequency(v, g)
    return 2.0 * math.pi / omega


def phugoid_damping_ratio(l_d):
    """Phugoid damping ratio zeta_p = 1 / (sqrt(2) * (L/D)), dimensionless.

    Drag-damping approximation, valid for large L/D. L/D must be at
    least 1 so that zeta_p stays below 1 (oscillatory mode).
    """
    _require_positive("lift-to-drag ratio", l_d)
    if l_d < MIN_LD_HARD:
        raise ValueError(
            "lift-to-drag ratio must be >= 1 for an oscillatory phugoid, got %r"
            % (l_d,)
        )
    return 1.0 / (SQRT2 * l_d)


def damped_frequency(v, l_d, g=G):
    """Damped phugoid frequency omega_d = omega_p * sqrt(1 - zeta^2)."""
    omega = phugoid_frequency(v, g)
    zeta = phugoid_damping_ratio(l_d)
    return omega * math.sqrt(1.0 - zeta * zeta)


def time_to_half_amplitude(v, l_d, g=G):
    """Time to half amplitude t_half = ln(2) / (zeta_p * omega_p), in s.

    Uses the identity zeta_p * omega_p = g / (V * (L/D)) for the
    closed form t_half = ln(2) * V * (L/D) / g.
    """
    _require_positive("speed", v)
    _require_positive("gravity", g)
    # phugoid_damping_ratio enforces the L/D >= 1 floor
    phugoid_damping_ratio(l_d)
    return math.log(2.0) * v * l_d / g


def cycles_to_half_amplitude(l_d):
    """Cycles to half amplitude N_half = t_half / T_p.

    Independent of speed: N_half = ln(2) * sqrt(2) * (L/D) / (2 * pi),
    about 0.156 * (L/D). Needs only the lift-to-drag ratio.
    """
    phugoid_damping_ratio(l_d)
    return math.log(2.0) * SQRT2 * l_d / (2.0 * math.pi)


def ld_valid_for_small_damping(l_d, min_ld=MIN_LD):
    """Small-damping validity check: True when L/D >= min_ld.

    The Lanchester damping approximation zeta_p = 1/(sqrt(2)*(L/D))
    assumes zeta_p is small; below L/D 8 (zeta_p about 0.09) the
    model overstates the damping accuracy.
    """
    _require_positive("lift-to-drag ratio", l_d)
    _require_positive("minimum lift-to-drag ratio", min_ld)
    return l_d >= min_ld


def phugoid_characteristics(v, l_d, g=G, min_ld=MIN_LD):
    """Complete phugoid mode summary from the Lanchester approximation.

    Returns a dict with omega_p (natural frequency rad/s), period s,
    zeta_p (damping ratio), omega_d (damped frequency rad/s), t_half
    (time to half amplitude s), cycles_half (cycles to half amplitude),
    small_damping_valid (L/D floor verdict), and the stated assumption
    that omega_p sits well below the short period frequency.
    """
    _require_positive("speed", v)
    _require_positive("gravity", g)
    zeta = phugoid_damping_ratio(l_d)
    omega = phugoid_frequency(v, g)
    omega_d = omega * math.sqrt(1.0 - zeta * zeta)
    t_half = math.log(2.0) * v * l_d / g
    period = 2.0 * math.pi / omega
    return {
        "omega_p": omega,
        "period": period,
        "zeta_p": zeta,
        "omega_d": omega_d,
        "t_half": t_half,
        "cycles_half": t_half / period,
        "small_damping_valid": ld_valid_for_small_damping(l_d, min_ld),
        "separation_assumption": (
            "omega_p assumed well below the short period frequency "
            "(two-timescale longitudinal split)"
        ),
    }
