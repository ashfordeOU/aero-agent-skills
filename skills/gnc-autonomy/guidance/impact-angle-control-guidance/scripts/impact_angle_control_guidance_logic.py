#!/usr/bin/env python3
"""Impact-angle-control guidance law for a planar terminal intercept.

Paraphrase of the energy-optimal impact-angle-constrained guidance
structure of the Ryoo-Cho-Tahk family (Ryoo, Cho and Tahk, "Optimal
Guidance Laws with Terminal Impact Angle Constraint," Journal of Guidance,
Control, and Dynamics 28(4):724-732, 2005, summarized by name and
paraphrase only, never reproduced): a time-to-go polynomial shaping law
specialized to a stationary target, written as a proportional-navigation-
like collision-course nulling baseline plus an impact-angle-error feedback
bias driven by the time-to-go.

Geometry is the planar terminal intercept against a stationary target:
speed V (m/s), current flight path angle gamma (rad), commanded terminal
flight path angle gamma_f (rad), crossrange offset y (m), crossrange
velocity component v_perp (m/s), time-to-go t_go (s). Units are SI
throughout: m, s, m/s, m/s^2, rad.

Reference note: ARP4754A (standards-map.yaml, reference-only) frames
development assurance for guided systems; the impact-angle-control law
itself is paraphrased public guidance-theory literature, summarized here.
"""

import math

W_Y = 6.0
W_V = 4.0
W_VF = 2.0


def crossrange_velocity(speed, gamma):
    """Crossrange velocity component, m/s.

    v = speed * sin(gamma). Raises ValueError when speed is not positive.
    """
    speed = float(speed)
    gamma = float(gamma)
    if speed <= 0.0:
        raise ValueError("speed must be > 0.0")
    return speed * math.sin(gamma)


def tgo_estimate(closing_speed, range_to_target):
    """Leading-order time-to-go on the closing geometry, s.

    t_go = range_to_target / closing_speed, exact on the collision course.
    Raises ValueError for a non-positive closing speed or a negative range.
    """
    closing_speed = float(closing_speed)
    range_to_target = float(range_to_target)
    if closing_speed <= 0.0:
        raise ValueError("closing_speed must be > 0.0")
    if range_to_target < 0.0:
        raise ValueError("range_to_target must be >= 0.0")
    return range_to_target / closing_speed


def impact_angle_error(commanded_gamma, gamma):
    """Impact-angle error, rad.

    e_g = commanded_gamma - gamma, the planar unwrapped difference between
    the commanded terminal flight path angle and the current flight path
    angle.
    """
    commanded_gamma = float(commanded_gamma)
    gamma = float(gamma)
    return commanded_gamma - gamma


def impact_angle_bias(speed, tgo, gamma, commanded_gamma):
    """Impact-angle-error feedback bias, m/s^2.

    v = crossrange_velocity(speed, gamma); v_f = crossrange_velocity(speed,
    commanded_gamma); a_bias = 2.0 * (v - v_f) / tgo. Positive when the
    current crossrange velocity exceeds the terminal one (a steeper
    terminal dive must first be set up), negative when the commanded
    course is shallower. Raises ValueError for non-positive speed or tgo.
    """
    speed = float(speed)
    tgo = float(tgo)
    if speed <= 0.0:
        raise ValueError("speed must be > 0.0")
    if tgo <= 0.0:
        raise ValueError("tgo must be > 0.0")
    v = crossrange_velocity(speed, gamma)
    v_f = crossrange_velocity(speed, commanded_gamma)
    return 2.0 * (v - v_f) / tgo


def collision_nulling_baseline(tgo, crossrange_offset, v_perp):
    """Proportional-navigation-like collision-course nulling term, m/s^2.

    a_base = -W_Y * (crossrange_offset + v_perp * tgo) / tgo**2, zero when
    the interceptor is already on the collision course (crossrange_offset
    + v_perp * tgo = 0). Raises ValueError for a non-positive tgo.
    """
    tgo = float(tgo)
    crossrange_offset = float(crossrange_offset)
    v_perp = float(v_perp)
    if tgo <= 0.0:
        raise ValueError("tgo must be > 0.0")
    return -W_Y * (crossrange_offset + v_perp * tgo) / (tgo * tgo)


def impact_angle_guidance_command(tgo, crossrange_offset, v_perp, speed,
                                   gamma, commanded_gamma):
    """Total impact-angle-control guidance command.

    Returns (a_cmd, a_base, a_bias, t_go, e_g): the total lateral
    acceleration command (m/s^2), the collision-course nulling baseline
    (m/s^2), the impact-angle-error bias (m/s^2), the time-to-go estimate
    (s) and the impact-angle error (rad). Raises ValueError for
    non-positive speed or tgo.
    """
    a_bias = impact_angle_bias(speed, tgo, gamma, commanded_gamma)
    a_base = collision_nulling_baseline(tgo, crossrange_offset, v_perp)
    a_cmd = a_base + a_bias
    e_g = impact_angle_error(commanded_gamma, gamma)
    return (a_cmd, a_base, a_bias, float(tgo), e_g)
