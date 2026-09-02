#!/usr/bin/env python3
"""Landing distance determination logic (paraphrase, common
flight-test methodology).

Simplified model in the FAR 25.125 landing distance context
(standards-map.yaml, far-25 and cs-25: reference-only): approach at
the reference speed Vref derived from the 1g stall speed, cover the
airborne flare segment, then brake on the ground. The certification
field length applies the 1.67 factor to the demonstrated distance.
"""

DEFAULT_APPROACH_FACTOR = 1.23
DEFAULT_FLARE_TIME_S = 5.0
DEFAULT_FIELD_LENGTH_FACTOR = 1.67
G = 9.80665


def approach_speed(vs1g_m_s, factor=DEFAULT_APPROACH_FACTOR):
    """Reference approach speed Vref from the 1g stall speed, in m/s.

    Vref = factor * vs1g. factor defaults to 1.23 per the FAR 25.125
    landing approach context and is configurable (e.g. 1.3). Raises
    ValueError on a non-positive stall speed or factor.
    """
    if vs1g_m_s <= 0:
        raise ValueError("stall speed must be > 0, got %r" % (vs1g_m_s,))
    if factor <= 0:
        raise ValueError("approach factor must be > 0, got %r" % (factor,))
    return factor * vs1g_m_s


def airborne_distance(vref_m_s, t_air_s=None):
    """Airborne flare segment distance from Vref to touchdown, in m.

    s_air = Vref * t_air. t_air defaults to 5.0 s when not given.
    Raises ValueError on a non-positive approach speed or a negative
    flare time.
    """
    if vref_m_s <= 0:
        raise ValueError("approach speed must be > 0, got %r" % (vref_m_s,))
    if t_air_s is None:
        t_air_s = DEFAULT_FLARE_TIME_S
    if t_air_s < 0:
        raise ValueError("flare time must be >= 0, got %r" % (t_air_s,))
    return vref_m_s * t_air_s


def ground_roll(vref_m_s, a_brake_m_s2):
    """Braking ground roll from the touchdown speed Vref, in m.

    s_ground = Vref^2 / (2 * a_brake) with a_brake the braking
    deceleration magnitude in m/s^2. Raises ValueError on a
    non-positive approach speed or a non-positive deceleration.
    """
    if vref_m_s <= 0:
        raise ValueError("approach speed must be > 0, got %r" % (vref_m_s,))
    if a_brake_m_s2 <= 0:
        raise ValueError("braking deceleration must be > 0, got %r" % (a_brake_m_s2,))
    return vref_m_s ** 2 / (2.0 * a_brake_m_s2)


def brake_deceleration(mu, g=G):
    """Braking deceleration magnitude from the friction coefficient.

    a_brake = mu * g, full braking on a dry runway, no reverse
    thrust; mu is dimensionless, g defaults to 9.80665 m/s^2. Raises
    ValueError on a non-positive friction coefficient.
    """
    if mu <= 0:
        raise ValueError("braking friction coefficient must be > 0, got %r" % (mu,))
    return mu * g


def total_landing_distance(vref_m_s, t_air_s, a_brake_m_s2):
    """Demonstrated landing distance: airborne leg plus ground roll.

    Returns {'airborne_m': s_air, 'ground_roll_m': s_ground,
    'total_m': s_air + s_ground}. Raises ValueError on any invalid
    leg input.
    """
    s_air = airborne_distance(vref_m_s, t_air_s)
    s_ground = ground_roll(vref_m_s, a_brake_m_s2)
    return {
        "airborne_m": s_air,
        "ground_roll_m": s_ground,
        "total_m": s_air + s_ground,
    }


def certified_field_length(demonstrated_m, factor=DEFAULT_FIELD_LENGTH_FACTOR):
    """Certification landing field length from the demonstrated distance.

    certified = factor * demonstrated_m with factor defaulting to
    1.67 per the FAR 25.125 landing field length context. Returns
    {'demonstrated_m': ..., 'factor': ..., 'certified_m': ...}.
    Raises ValueError on a negative demonstrated distance or a
    non-positive factor.
    """
    if demonstrated_m < 0:
        raise ValueError("demonstrated distance must be >= 0, got %r" % (demonstrated_m,))
    if factor <= 0:
        raise ValueError("field length factor must be > 0, got %r" % (factor,))
    return {
        "demonstrated_m": demonstrated_m,
        "factor": factor,
        "certified_m": demonstrated_m * factor,
    }


def runway_verdict(required_m, runway_m):
    """Runway fits verdict for a required landing distance, in m.

    Returns {'required_m': ..., 'runway_m': ..., 'margin_m':
    runway_m - required_m, 'verdict': 'fits' when margin >= 0 else
    'too short'}.
    """
    margin = runway_m - required_m
    return {
        "required_m": required_m,
        "runway_m": runway_m,
        "margin_m": margin,
        "verdict": "fits" if margin >= 0 else "too short",
    }
