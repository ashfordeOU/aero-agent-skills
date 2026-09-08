#!/usr/bin/env python3
"""Impact-time-control guidance (ITCG) law for a planar salvo intercept.

Paraphrase of the canonical biased proportional-navigation impact-time-
control structure (Jeon, Lee and Tahk, "Impact-time-control guidance law
for anti-ship missiles," IEEE Transactions on Aerospace and Electronic
Systems 42(2):629-641, 2006, summarized by name only, never reproduced):
a proportional-navigation (PN) baseline acceleration plus an impact-time-
error feedback term driven by the time-to-go, so a group of interceptors
can be commanded to arrive at the same, chosen impact time.

Geometry is the planar collision-course intercept against a stationary
target: closing speed Vc (m/s), line of sight rate lambda_dot (rad/s),
range to target R (m), navigation constant N (dimensionless, > 1), and a
commanded remaining time-to-go t_go_des (s). Units are SI throughout: m,
s, m/s, m/s^2, rad, rad/s.

Reference note: ARP4754A (standards-map.yaml, reference-only) frames
development assurance for guided systems; the ITCG law itself is
paraphrased public guidance-theory literature, summarized here.
"""

import math

K_IT_DEFAULT = 4.0


def png_baseline(nav_constant, closing_speed, los_rate):
    """Proportional-navigation baseline acceleration, m/s^2.

    a_png = N * Vc * lambda_dot. Raises ValueError when the navigation
    constant does not exceed 1 (required for a converging intercept law)
    or when the closing speed is negative.
    """
    nav_constant = float(nav_constant)
    closing_speed = float(closing_speed)
    los_rate = float(los_rate)
    if nav_constant <= 1.0:
        raise ValueError("nav_constant must exceed 1.0 for a converging intercept law")
    if closing_speed < 0.0:
        raise ValueError("closing_speed must be >= 0.0")
    return nav_constant * closing_speed * los_rate


def tgo_estimate_png(closing_speed, range_to_target):
    """Leading-order PNG time-to-go on the collision course, s.

    t_go = R / Vc, exact when the interceptor flies the collision
    triangle. Raises ValueError for a non-positive closing speed or a
    negative range.
    """
    closing_speed = float(closing_speed)
    range_to_target = float(range_to_target)
    if closing_speed <= 0.0:
        raise ValueError("closing_speed must be > 0.0")
    if range_to_target < 0.0:
        raise ValueError("range_to_target must be >= 0.0")
    return range_to_target / closing_speed


def impact_time_bias(gain, closing_speed, tgo_desired, tgo_actual):
    """Impact-time-error feedback bias acceleration, m/s^2.

    e_t = t_go_des - t_go_actual; a_b = gain * Vc * e_t / t_go_actual^2.
    A positive error (later commanded arrival) gives a positive bias
    that lengthens the intercept path; a negative error shortens it.
    Raises ValueError when gain, closing speed, the actual time-to-go
    or the desired time-to-go is not strictly positive.
    """
    gain = float(gain)
    closing_speed = float(closing_speed)
    tgo_desired = float(tgo_desired)
    tgo_actual = float(tgo_actual)
    if gain <= 0.0:
        raise ValueError("gain must be > 0.0")
    if closing_speed <= 0.0:
        raise ValueError("closing_speed must be > 0.0")
    if tgo_actual <= 0.0:
        raise ValueError("tgo_actual must be > 0.0")
    if tgo_desired <= 0.0:
        raise ValueError("tgo_desired must be > 0.0")
    e_t = tgo_desired - tgo_actual
    return gain * closing_speed * e_t / (tgo_actual ** 2)


def itcg_command(nav_constant, closing_speed, los_rate, range_to_target,
                  tgo_desired, gain=None):
    """Total ITCG lateral acceleration command for the engagement state.

    Combines the workflow steps: the PN baseline (step 2), the PNG
    time-to-go estimate (step 3), the impact-time error (step 4) and
    the time-to-go-error-feedback bias (step 5), summed into the total
    command (step 6). Returns (a_cmd, a_png, a_b, tgo_png, e_t).
    """
    if gain is None:
        gain = K_IT_DEFAULT
    a_png = png_baseline(nav_constant, closing_speed, los_rate)
    tgo_png = tgo_estimate_png(closing_speed, range_to_target)
    e_t = tgo_desired - tgo_png
    a_b = impact_time_bias(gain, closing_speed, tgo_desired, tgo_png)
    a_cmd = a_png + a_b
    return (a_cmd, a_png, a_b, tgo_png, e_t)


def time_to_impact_seconds(range_to_target, closing_speed):
    """Natural (uncontrolled) time to impact on the collision course, s.

    Equal in closed form to tgo_estimate_png; provided as a named
    workflow entry point for the natural-time identity check.
    """
    return tgo_estimate_png(closing_speed, range_to_target)
