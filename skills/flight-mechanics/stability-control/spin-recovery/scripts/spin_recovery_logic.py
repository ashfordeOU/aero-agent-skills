#!/usr/bin/env python3
"""Spin recovery logic (paraphrase, common flight-mechanics methodology).

A spin is a developed post-stall rotation of an aircraft about a near
vertical axis, sustained by autorotation: beyond the stall angle the
wing lift curve slope turns negative, so a wing half that is more
stalled produces less lift and less drag than the less stalled half,
and the asymmetric moments keep the rotation going. FAR-25 and CS-25
require transport aeroplanes to demonstrate recovery from spins or to
show that spins cannot occur (summary reference only, standards-map
yaml); the simplified models here are the standard engineering
estimates used in spin analysis:

- Post-stall lift: linear drop beyond the stall angle,
  Cl = cl_max + m_post * (alpha - alpha_stall), m_post < 0.
- Autorotative band: the alpha range over which the wing sits on the
  negative-slope post-stall region, ending where the post-stall lift
  model returns to zero.
- Spin descent rate: vertical velocity of the stalled descent,
  V_d = sqrt(2 * W / (rho * S * C_D_spin)).
- Developed spin rotation rate: Omega = 2 * V_d * nu / b, where nu is
  the nondimensional rotation rate (steep spins near 0.2 to 0.3,
  developed spins 0.3 to 0.5, flat spins above 0.5).
- Spin flatness ratio: nu = Omega * b / (2 * V_d); high ratio means a
  rotation-dominated flat spin, low ratio a descent-dominated steep
  spin.
- Recovery sizing: altitude lost during recovery is V_d * t_rec, and
  the rotation decays exponentially so the time to stop the rotation
  is tau * ln(Omega_0 / Omega_stop).

All inputs are SI: forces in N, areas in m^2, density in kg/m^3,
speeds in m/s, angles in degrees, angular rates in rad/s, times in s.
"""

import math


def post_stall_lift_coefficient(cl_max, alpha_stall_deg, alpha_deg,
                                post_stall_slope_per_deg):
    """Post-stall section lift coefficient on the autorotative band.

    Cl = cl_max + m_post * (alpha - alpha_stall) for alpha above the
    stall angle, with the pre-stall value cl_max returned below it.
    Worked anchor: cl_max = 1.4, alpha_stall = 16 deg,
    m_post = -0.02 / deg, alpha = 20 deg gives Cl = 1.4 - 0.02 * 4
    = 1.32. Raises ValueError when cl_max is non-positive, the
    post-stall slope is not negative, or the angles are out of range.
    """
    if cl_max <= 0:
        raise ValueError("cl_max must be > 0, got %r" % (cl_max,))
    if post_stall_slope_per_deg >= 0:
        raise ValueError(
            "post-stall slope must be < 0 for autorotation, got %r"
            % (post_stall_slope_per_deg,))
    if not (-90.0 < alpha_stall_deg < 90.0):
        raise ValueError(
            "stall angle must be in (-90, 90) deg, got %r"
            % (alpha_stall_deg,))
    if not (-90.0 < alpha_deg < 90.0):
        raise ValueError("alpha must be in (-90, 90) deg, got %r"
                         % (alpha_deg,))
    if alpha_deg <= alpha_stall_deg:
        return cl_max
    return cl_max + post_stall_slope_per_deg * (alpha_deg - alpha_stall_deg)


def autorotation_band_end_deg(cl_max, alpha_stall_deg,
                              post_stall_slope_per_deg):
    """Upper edge of the autorotative band (deg).

    The wing autorotates while it sits on the negative-slope post-stall
    region, i.e. from alpha_stall until the linear post-stall model
    returns to zero lift: alpha_end = alpha_stall + cl_max / |m_post|.
    Worked anchor: cl_max = 1.4, alpha_stall = 16 deg, m_post = -0.02
    gives 16 + 1.4 / 0.02 = 86 deg. Raises ValueError on non-positive
    cl_max or non-negative post-stall slope.
    """
    if cl_max <= 0:
        raise ValueError("cl_max must be > 0, got %r" % (cl_max,))
    if post_stall_slope_per_deg >= 0:
        raise ValueError(
            "post-stall slope must be < 0 for autorotation, got %r"
            % (post_stall_slope_per_deg,))
    if not (-90.0 < alpha_stall_deg < 90.0):
        raise ValueError(
            "stall angle must be in (-90, 90) deg, got %r"
            % (alpha_stall_deg,))
    return alpha_stall_deg + cl_max / abs(post_stall_slope_per_deg)


def stall_penetration_deg(alpha_deg, alpha_stall_deg):
    """Stall penetration in degrees: alpha - alpha_stall, floor 0.

    Worked anchor: alpha = 20 deg, alpha_stall = 16 deg gives 4 deg.
    Raises ValueError when alpha_stall is outside (-90, 90) deg.
    """
    if not (-90.0 < alpha_stall_deg < 90.0):
        raise ValueError(
            "stall angle must be in (-90, 90) deg, got %r"
            % (alpha_stall_deg,))
    if not (-90.0 < alpha_deg < 90.0):
        raise ValueError("alpha must be in (-90, 90) deg, got %r"
                         % (alpha_deg,))
    return max(0.0, alpha_deg - alpha_stall_deg)


def autorotative_condition(alpha_deg, alpha_stall_deg, band_end_deg):
    """True when the wing is on the autorotative post-stall band.

    Autorotation requires the wing to sit beyond the stall peak and
    inside the negative-slope band: alpha_stall < alpha < band_end.
    Worked anchors: (20, 16, 86) True; (10, 16, 86) False (not
    stalled); (90, 16, 86) False (past the band). Raises ValueError
    when the band is empty (band_end <= alpha_stall).
    """
    if band_end_deg <= alpha_stall_deg:
        raise ValueError(
            "band end %r must exceed stall angle %r" % (band_end_deg,
                                                        alpha_stall_deg))
    return alpha_stall_deg < alpha_deg < band_end_deg


def spin_descent_rate(weight_n, wing_area_m2, rho_kg_m3, cd_spin,
                      g0=9.80665):
    """Vertical descent speed of the developed spin (m/s).

    V_d = sqrt(2 * W / (rho * S * C_D_spin)): the stalled descent
    balances the weight against the drag of the spinning configuration
    (flat spins C_D near 1.0 to 1.6, steep spins lower). g0 is
    accepted for interface symmetry; the drag balance is
    weight-based. Worked anchor: W = 15000 N, S = 16 m^2,
    rho = 1.225, C_D_spin = 1.2 gives sqrt(30000 / 23.52)
    = 35.71 m/s. Raises ValueError when any input is non-positive.
    """
    if weight_n <= 0:
        raise ValueError("weight must be > 0, got %r" % (weight_n,))
    if wing_area_m2 <= 0:
        raise ValueError("wing area must be > 0, got %r" % (wing_area_m2,))
    if rho_kg_m3 <= 0:
        raise ValueError("density must be > 0, got %r" % (rho_kg_m3,))
    if cd_spin <= 0:
        raise ValueError("spin drag coefficient must be > 0, got %r"
                         % (cd_spin,))
    return math.sqrt(2.0 * weight_n / (rho_kg_m3 * wing_area_m2 * cd_spin))


def spin_rotation_rate(weight_n, wing_area_m2, span_m, rho_kg_m3, cd_spin,
                       nondim_rate=0.4):
    """Developed spin rotation rate about the spin axis (rad/s).

    Omega = 2 * V_d * nu / b with V_d the spin descent rate and nu the
    nondimensional rotation rate (steep spins 0.2-0.3, developed
    0.3-0.5, flat above 0.5). Worked anchor: W = 15000 N, S = 16 m^2,
    b = 10 m, rho = 1.225, C_D_spin = 1.2, nu = 0.4 gives
    2 * 35.71 * 0.4 / 10 = 2.86 rad/s. Raises ValueError when any
    input is non-positive or nu is outside (0, 1].
    """
    if weight_n <= 0:
        raise ValueError("weight must be > 0, got %r" % (weight_n,))
    if wing_area_m2 <= 0:
        raise ValueError("wing area must be > 0, got %r" % (wing_area_m2,))
    if span_m <= 0:
        raise ValueError("span must be > 0, got %r" % (span_m,))
    if rho_kg_m3 <= 0:
        raise ValueError("density must be > 0, got %r" % (rho_kg_m3,))
    if cd_spin <= 0:
        raise ValueError("spin drag coefficient must be > 0, got %r"
                         % (cd_spin,))
    if not (0.0 < nondim_rate <= 1.0):
        raise ValueError(
            "nondimensional rotation rate must be in (0, 1], got %r"
            % (nondim_rate,))
    vd = spin_descent_rate(weight_n, wing_area_m2, rho_kg_m3, cd_spin)
    return 2.0 * vd * nondim_rate / span_m


def spin_flatness_ratio(rotation_rate_rad_s, span_m, descent_rate_ms):
    """Spin flatness ratio nu = Omega * b / (2 * V_d).

    The ratio of the wingtip tangential speed to the descent speed:
    below about 0.3 the spin is steep and descent-dominated, 0.3-0.5
    is a developed spin, above 0.5 is a rotation-dominated flat spin.
    Worked anchor: Omega = 2.857 rad/s, b = 10 m, V_d = 35.71 m/s
    gives 2.857 * 10 / (2 * 35.71) = 0.4. Raises ValueError when any
    input is non-positive.
    """
    if rotation_rate_rad_s <= 0:
        raise ValueError("rotation rate must be > 0, got %r"
                         % (rotation_rate_rad_s,))
    if span_m <= 0:
        raise ValueError("span must be > 0, got %r" % (span_m,))
    if descent_rate_ms <= 0:
        raise ValueError("descent rate must be > 0, got %r"
                         % (descent_rate_ms,))
    return rotation_rate_rad_s * span_m / (2.0 * descent_rate_ms)


def recovery_altitude_loss(descent_rate_ms, recovery_time_s):
    """Altitude lost during the spin recovery (m).

    h = V_d * t_rec: the aircraft keeps descending at the spin descent
    rate until the rotation stops and the dive recovery begins. Worked
    anchor: V_d = 35.71 m/s for 3 s gives 107.1 m. Raises ValueError
    when either input is non-positive.
    """
    if descent_rate_ms <= 0:
        raise ValueError("descent rate must be > 0, got %r"
                         % (descent_rate_ms,))
    if recovery_time_s <= 0:
        raise ValueError("recovery time must be > 0, got %r"
                         % (recovery_time_s,))
    return descent_rate_ms * recovery_time_s


def rotation_stop_time(rotation_rate_rad_s, time_constant_s,
                       stop_rate_rad_s=0.2):
    """Time to stop the spin rotation (s).

    The rotation decays exponentially after the recovery controls are
    applied, t = tau * ln(Omega_0 / Omega_stop). Worked anchor:
    Omega_0 = 2.857 rad/s, tau = 1.5 s, Omega_stop = 0.2 rad/s gives
    1.5 * ln(14.29) = 3.99 s. Raises ValueError when the rates are
    non-positive or Omega_stop is not below Omega_0.
    """
    if rotation_rate_rad_s <= 0:
        raise ValueError("rotation rate must be > 0, got %r"
                         % (rotation_rate_rad_s,))
    if time_constant_s <= 0:
        raise ValueError("time constant must be > 0, got %r"
                         % (time_constant_s,))
    if stop_rate_rad_s <= 0:
        raise ValueError("stop rate must be > 0, got %r"
                         % (stop_rate_rad_s,))
    if stop_rate_rad_s >= rotation_rate_rad_s:
        raise ValueError(
            "stop rate %r must be below the spin rate %r"
            % (stop_rate_rad_s, rotation_rate_rad_s))
    return time_constant_s * math.log(rotation_rate_rad_s / stop_rate_rad_s)
