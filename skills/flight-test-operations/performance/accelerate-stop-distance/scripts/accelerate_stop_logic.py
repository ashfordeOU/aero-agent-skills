#!/usr/bin/env python3
"""Rejected takeoff accelerate-stop distance logic (paraphrase,
common flight-test methodology).

Simplified constant-acceleration model in the FAR 25.109 accelerate-
stop distance context (standards-map.yaml, far-25 and cs-25:
reference-only): accelerate to the decision speed V1, then stop with
the braking deceleration. The balanced field length V1 is None in
this model.
"""


def accelerate_distance(v1_m_s, a_acc_m_s2):
    """Distance to accelerate from rest to v1, in m.

    s_acc = v1^2 / (2 * a_acc). v1 in m/s, a_acc in m/s^2. Raises
    ValueError on a non-positive decision speed or acceleration.
    """
    if v1_m_s <= 0:
        raise ValueError("decision speed must be > 0, got %r" % (v1_m_s,))
    if a_acc_m_s2 <= 0:
        raise ValueError("acceleration must be > 0, got %r" % (a_acc_m_s2,))
    return v1_m_s ** 2 / (2.0 * a_acc_m_s2)


def stop_distance(v1_m_s, a_brake_m_s2):
    """Distance to stop from v1 with the braking deceleration, in m.

    s_stop = v1^2 / (2 * a_brake). v1 in m/s, a_brake in m/s^2
    (positive magnitude). Raises ValueError on a non-positive
    decision speed or braking deceleration.
    """
    if v1_m_s <= 0:
        raise ValueError("decision speed must be > 0, got %r" % (v1_m_s,))
    if a_brake_m_s2 <= 0:
        raise ValueError("braking deceleration must be > 0, got %r" % (a_brake_m_s2,))
    return v1_m_s ** 2 / (2.0 * a_brake_m_s2)


def accelerate_stop_distance(v1_m_s, a_acc_m_s2, a_brake_m_s2):
    """Rejected takeoff distance: accelerate leg plus stop leg, in m.

    Returns {'accelerate_m': s_acc, 'stop_m': s_stop, 'total_m':
    s_acc + s_stop, 'balanced_v1': None}. The balanced field length
    V1 is None in this simplified constant-acceleration model.
    """
    s_acc = accelerate_distance(v1_m_s, a_acc_m_s2)
    s_stop = stop_distance(v1_m_s, a_brake_m_s2)
    return {
        "accelerate_m": s_acc,
        "stop_m": s_stop,
        "total_m": s_acc + s_stop,
        "balanced_v1": None,
    }


def brake_deceleration(mu_b, g=9.80665):
    """Braking deceleration magnitude from the friction coefficient.

    a_brake = mu_b * g, full braking, no reverse thrust; mu_b is
    dimensionless, g defaults to 9.80665 m/s^2. Raises ValueError on
    a non-positive friction coefficient.
    """
    if mu_b <= 0:
        raise ValueError("braking friction coefficient must be > 0, got %r" % (mu_b,))
    return mu_b * g


def runway_verdict(required_m, runway_m):
    """Runway fits verdict for a required distance, in m.

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
