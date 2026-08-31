#!/usr/bin/env python3
"""Landing gear sizing logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: gated
false): landing gear static loads split the maximum landing weight
over the gear struts; with the CG located a distance aft of the
main gear, static equilibrium about the main gear gives the nose
load as W * cg_aft / wheelbase and the main load as the balance.
The shock absorber stroke follows from the energy balance
0.5*m*v^2 = n*m*g*stroke, so stroke = v^2 / (2*n*g) with
g = 9.80665 m/s^2. The tire rating margin is static load over
tire rating; the rating covers the load when the margin is at
most 1.0. FAR-25.723 / CS-25.723 shock absorption verification is
a drop test; this module provides the sizing-level energy check
only. Invalid inputs raise ValueError throughout.
"""

G = 9.80665  # standard acceleration of gravity, m/s^2


def static_load_per_strut(max_landing_weight_N, main_struts, nose_strut=0):
    """Even-split static load per strut: weight / (main + nose struts).

    Idealization: equal load on every strut regardless of CG
    position; use main_gear_load_share for a CG-based split.

    Raises ValueError if the weight is not positive, there are no
    main struts, or the nose strut count is negative.
    """
    if max_landing_weight_N <= 0:
        raise ValueError(
            "maximum landing weight must be positive: %r" % (max_landing_weight_N,)
        )
    if main_struts < 1:
        raise ValueError("main_struts must be >= 1: %r" % (main_struts,))
    if nose_strut < 0:
        raise ValueError("nose_strut must be >= 0: %r" % (nose_strut,))
    return max_landing_weight_N / (main_struts + nose_strut)


def main_gear_load_share(max_landing_weight_N, cg_aft_of_main_gear_m, wheelbase_m):
    """Nose and main gear loads from static equilibrium about the main gear.

    nose_load = W * cg_aft / wheelbase; main_load = W - nose_load.

    Raises ValueError if the wheelbase is not positive, the CG
    distance is negative, or the CG lies aft of the wheelbase.
    """
    if wheelbase_m <= 0:
        raise ValueError("wheelbase must be positive: %r" % (wheelbase_m,))
    if cg_aft_of_main_gear_m < 0:
        raise ValueError(
            "cg_aft_of_main_gear_m must be non-negative: %r"
            % (cg_aft_of_main_gear_m,)
        )
    if cg_aft_of_main_gear_m > wheelbase_m:
        raise ValueError(
            "CG aft of main gear %r exceeds wheelbase %r"
            % (cg_aft_of_main_gear_m, wheelbase_m)
        )
    nose_load = max_landing_weight_N * cg_aft_of_main_gear_m / wheelbase_m
    return {"nose_load": nose_load, "main_load": max_landing_weight_N - nose_load}


def required_shock_stroke(sink_speed_m_s, landing_load_factor):
    """Ideal constant-force shock stroke: v^2 / (2 * n * g).

    Energy balance 0.5*m*v^2 = n*m*g*stroke with g = G.

    Raises ValueError if the sink speed is negative or the load
    factor is not positive.
    """
    if sink_speed_m_s < 0:
        raise ValueError(
            "sink speed must be non-negative: %r" % (sink_speed_m_s,)
        )
    if landing_load_factor <= 0:
        raise ValueError(
            "landing load factor must be positive: %r" % (landing_load_factor,)
        )
    return sink_speed_m_s ** 2 / (2.0 * landing_load_factor * G)


def tire_rating_margin(static_load_N, tire_rating_N):
    """Tire rating margin: static load / tire rating.

    Raises ValueError if either argument is not positive.
    """
    if static_load_N <= 0:
        raise ValueError("static load must be positive: %r" % (static_load_N,))
    if tire_rating_N <= 0:
        raise ValueError("tire rating must be positive: %r" % (tire_rating_N,))
    return static_load_N / tire_rating_N


def landing_gear_verdict(static_load_N, tire_rating_N, sink_speed_m_s, landing_load_factor):
    """Sizing check: tire margin plus shock stroke plus verdict.

    Returns a dict with static_load, tire_margin, tire_ok (margin
    <= 1.0), stroke (full precision), stroke_m (rounded to 4
    decimals), and verdict ('gear sized' or 'tire overloaded').
    """
    margin = tire_rating_margin(static_load_N, tire_rating_N)
    stroke = required_shock_stroke(sink_speed_m_s, landing_load_factor)
    tire_ok = margin <= 1.0
    return {
        "static_load": static_load_N,
        "stroke": stroke,
        "tire_margin": margin,
        "tire_ok": tire_ok,
        "stroke_m": round(stroke, 4),
        "verdict": "gear sized" if tire_ok else "tire overloaded",
    }
