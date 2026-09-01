#!/usr/bin/env python3
"""Takeoff distance determination logic (paraphrase, common flight-test
methodology).

Measurement method per the FAR 25.113 / CS-25.113 takeoff distance
definition (standards-map.yaml, far-25 and cs-25: reference-only):
distance from brake release to the point 35 ft above the takeoff
surface, split into the ground roll, the rotation leg, and the
airborne climb segment. The ground roll integrates measured ground
speed over time with the trapezoid rule; stdlib only, offline,
deterministic.
"""

TARGET_HEIGHT_M = 10.668  # 35 ft obstacle height, FAR 25.113 / CS-25.113


def ground_roll_distance(v_m_s_list, t_s_list):
    """Ground roll distance from measured ground speed samples, in m.

    Trapezoid integration: s = sum((v_i + v_{i+1}) / 2 * dt_i) over
    consecutive samples. v in m/s, t in s. Raises ValueError when
    the sample lists differ in length, fewer than two samples are
    given, time is not strictly increasing, or any speed is
    negative.
    """
    if len(v_m_s_list) != len(t_s_list):
        raise ValueError(
            "speed and time samples must be equal length, got %d and %d"
            % (len(v_m_s_list), len(t_s_list))
        )
    if len(v_m_s_list) < 2:
        raise ValueError(
            "need at least two speed samples, got %d" % len(v_m_s_list)
        )
    s = 0.0
    for i in range(len(v_m_s_list) - 1):
        v0 = v_m_s_list[i]
        v1 = v_m_s_list[i + 1]
        t0 = t_s_list[i]
        t1 = t_s_list[i + 1]
        if v0 < 0 or v1 < 0:
            raise ValueError(
                "speed samples must be >= 0, got %r" % (v_m_s_list,)
            )
        if t1 <= t0:
            raise ValueError(
                "time samples must be strictly increasing, got %r then %r"
                % (t0, t1)
            )
        s += (v0 + v1) / 2.0 * (t1 - t0)
    return s


def rotation_distance(v_rot_m_s, t_rot_s):
    """Distance covered while rotating to liftoff, in m.

    s_rot = v_rot * t_rot, constant speed at the rotation speed.
    Raises ValueError on a non-positive rotation speed or time.
    """
    if v_rot_m_s <= 0:
        raise ValueError(
            "rotation speed must be > 0, got %r" % (v_rot_m_s,)
        )
    if t_rot_s <= 0:
        raise ValueError(
            "rotation time must be > 0, got %r" % (t_rot_s,)
        )
    return v_rot_m_s * t_rot_s


def climb_distance(v_liftoff_m_s, h_target_m, climb_rate_m_s):
    """Airborne distance to the obstacle height, in m.

    s_air = v_liftoff * h_target / climb_rate: the time to climb
    the target height at the climb rate, flown at the liftoff speed.
    Raises ValueError on a non-positive speed, height, or rate.
    """
    if v_liftoff_m_s <= 0:
        raise ValueError(
            "liftoff speed must be > 0, got %r" % (v_liftoff_m_s,)
        )
    if h_target_m <= 0:
        raise ValueError(
            "target height must be > 0, got %r" % (h_target_m,)
        )
    if climb_rate_m_s <= 0:
        raise ValueError(
            "climb rate must be > 0, got %r" % (climb_rate_m_s,)
        )
    return v_liftoff_m_s * h_target_m / climb_rate_m_s


def takeoff_distance(ground_roll_m, rotation_m, climb_m):
    """Total takeoff distance, in m.

    Returns {'ground_roll_m': ..., 'rotation_m': ..., 'climb_m': ...,
    'total_m': ground roll + rotation + climb}. Raises ValueError on
    a negative leg distance.
    """
    legs = [
        ("ground_roll_m", ground_roll_m),
        ("rotation_m", rotation_m),
        ("climb_m", climb_m),
    ]
    for name, value in legs:
        if value < 0:
            raise ValueError(
                "%s must be >= 0, got %r" % (name, value)
            )
    return {
        "ground_roll_m": ground_roll_m,
        "rotation_m": rotation_m,
        "climb_m": climb_m,
        "total_m": ground_roll_m + rotation_m + climb_m,
    }


def takeoff_distance_from_profile(
    v_m_s_list,
    t_s_list,
    v_rot_m_s,
    t_rot_s,
    climb_rate_m_s,
    h_target_m=TARGET_HEIGHT_M,
):
    """Full takeoff distance from one measured speed profile, in m.

    Chains ground_roll_distance on the samples, rotation_distance at
    the rotation speed, and climb_distance to the obstacle height at
    the liftoff speed (the last speed sample). Returns the
    takeoff_distance dict; the default target is 35 ft.
    """
    s_g = ground_roll_distance(v_m_s_list, t_s_list)
    s_r = rotation_distance(v_rot_m_s, t_rot_s)
    s_a = climb_distance(v_m_s_list[-1], h_target_m, climb_rate_m_s)
    return takeoff_distance(s_g, s_r, s_a)
