"""Blade-element hover performance of a helicopter main rotor.

Pure stdlib implementation of the blade-element hover model: the rotor
thrust coefficient C_T from a collective pitch schedule and the Betz tip
loss factor B, the inflow ratio lambda from the uniform-inflow hover
closure lambda = sqrt(C_T / 2), the collective pitch required to hover
at a target thrust coefficient, the torque coefficient C_Q with its
induced (lambda * C_T) and profile (sigma * Cd0 / 8) split, the rotor
shaft torque Q = C_Q * rho * A * Vtip^2 * R and shaft power P = C_Q *
rho * A * Vtip^3, and the figure of merit FM = C_T^1.5 / (sqrt(2) *
C_Q) from the coefficients.

Conventions (SI): rotor radius R (m), disk area A = PI * R^2, tip speed
Vtip = Omega * R (m/s), solidity sigma, mean blade drag coefficient
Cd0, thrust T (N), inflow ratio lambda = v_i / Vtip, lift-curve slope a
(1/rad). The induced and profile contributions appear only inside the
C_Q split; this module does not reproduce the momentum-theory ideal
power or profile power quantities of the hover-performance leaf.

All functions return floats in SI units. Non-physical inputs raise
ValueError. Deterministic: no randomness anywhere.
"""

import math

# Module constants (SI).
RHO_SL = 1.225          # sea-level air density, kg/m^3 (default only)
G = 9.80665             # standard gravitational acceleration, m/s^2
A_LIFT_DEFAULT = 5.73   # default rotor lift-curve slope, 1/rad
PI = math.pi


def _require_positive(name, value):
    """Raise ValueError unless value > 0."""
    if value <= 0:
        raise ValueError("%s must be positive" % name)


def _require_non_negative(name, value):
    """Raise ValueError unless value >= 0."""
    if value < 0:
        raise ValueError("%s must be non-negative" % name)


def _require_tip_loss(tip_loss):
    """Raise ValueError unless tip_loss lies in (0, 1] (Betz factor)."""
    if tip_loss <= 0 or tip_loss > 1:
        raise ValueError("tip_loss must lie in (0, 1]")


def thrust_coefficient(collective_rad, solidity, lift_slope, inflow_ratio,
                       tip_loss):
    """Blade-element thrust coefficient from the pitch schedule.

    C_T = (sigma * a / 2) * (theta0 * B^3 / 3 - lambda * B^2 / 2), with
    theta0 the collective pitch (rad), sigma the solidity, a the
    lift-curve slope (1/rad), lambda the inflow ratio and B the Betz tip
    loss factor in (0, 1]. The B^3 / 3 term integrates the pitch loading
    over the blade and the B^2 / 2 term removes the inflow incidence at
    the tip.
    """
    _require_non_negative("collective_rad", collective_rad)
    _require_positive("solidity", solidity)
    _require_positive("lift_slope", lift_slope)
    _require_non_negative("inflow_ratio", inflow_ratio)
    _require_tip_loss(tip_loss)
    return (solidity * lift_slope / 2.0) * (
        collective_rad * tip_loss ** 3 / 3.0
        - inflow_ratio * tip_loss ** 2 / 2.0)


def inflow_ratio_from_ct(c_t):
    """Uniform-inflow hover closure lambda = sqrt(C_T / 2).

    Momentum balance for a hovering rotor gives C_T = 2 * lambda^2, so
    the inflow ratio follows directly from the thrust coefficient.
    """
    if c_t < 0:
        raise ValueError("c_t must be non-negative")
    return math.sqrt(c_t / 2.0)


def collective_for_thrust_coefficient(c_t, solidity, lift_slope, tip_loss):
    """Collective pitch theta0 (rad) required to hover at a target C_T.

    Closed form from the blade-element integral with the uniform-inflow
    closure: theta0 = (3 / B^3) * (2 * C_T / (sigma * a) + lambda *
    B^2 / 2) with lambda = sqrt(C_T / 2). A tip loss below 1 raises the
    required collective at fixed thrust coefficient.
    """
    _require_non_negative("c_t", c_t)
    _require_positive("solidity", solidity)
    _require_positive("lift_slope", lift_slope)
    _require_tip_loss(tip_loss)
    inflow = inflow_ratio_from_ct(c_t)
    return (3.0 / tip_loss ** 3) * (
        2.0 * c_t / (solidity * lift_slope) + inflow * tip_loss ** 2 / 2.0)


def torque_coefficient(c_t, inflow_ratio, solidity, drag_coefficient):
    """Rotor torque coefficient C_Q = lambda * C_T + sigma * Cd0 / 8.

    The induced contribution lambda * C_T carries the inflow work and
    the profile contribution sigma * Cd0 / 8 the section drag; the two
    are combined here and reported separately by the convenience chains.
    """
    _require_non_negative("c_t", c_t)
    _require_non_negative("inflow_ratio", inflow_ratio)
    _require_positive("solidity", solidity)
    _require_positive("drag_coefficient", drag_coefficient)
    return inflow_ratio * c_t + solidity * drag_coefficient / 8.0


def rotor_torque(c_q, rho, area, tip_speed, radius):
    """Rotor shaft torque Q = C_Q * rho * A * Vtip^2 * R in N m."""
    _require_positive("c_q", c_q)
    _require_positive("rho", rho)
    _require_positive("area", area)
    _require_positive("tip_speed", tip_speed)
    _require_positive("radius", radius)
    return c_q * rho * area * tip_speed ** 2 * radius


def rotor_power_from_torque(c_q, rho, area, tip_speed, radius):
    """Rotor shaft power P = Q * Omega = C_Q * rho * A * Vtip^3 in W.

    Same inputs as rotor_torque; the tip speed cancels the radius so the
    power is the torque coefficient times rho * A * Vtip^3.
    """
    _require_positive("c_q", c_q)
    _require_positive("rho", rho)
    _require_positive("area", area)
    _require_positive("tip_speed", tip_speed)
    _require_positive("radius", radius)
    return c_q * rho * area * tip_speed ** 3


def figure_of_merit_from_coefficients(c_t, c_q):
    """Figure of merit FM = C_T^1.5 / (sqrt(2) * C_Q).

    Ratio of the ideal induced power implied by C_T to the total shaft
    power implied by C_Q; real rotors sit near 0.5-0.7. Degenerate at
    zero thrust coefficient, hence c_t <= 0 is rejected.
    """
    if c_t <= 0:
        raise ValueError("c_t must be positive")
    if c_q <= 0:
        raise ValueError("c_q must be positive")
    return c_t ** 1.5 / (math.sqrt(2.0) * c_q)


def _torque_coefficient_split(c_t, inflow_ratio, solidity, drag_coefficient):
    """Induced, profile and total torque coefficient as a tuple."""
    induced = inflow_ratio * c_t
    profile = solidity * drag_coefficient / 8.0
    return induced, profile, induced + profile


def hover_blade_element_summary(thrust_N, radius_m, rho, solidity,
                                lift_slope, drag_coefficient, tip_speed,
                                tip_loss, collective_rad):
    """One hover operating point: thrust and pitch schedule to verdicts.

    Returns a dict with keys thrust_coefficient, inflow_ratio,
    torque_coefficient_induced, torque_coefficient_profile,
    torque_coefficient_total, rotor_torque_Nm, rotor_power_W and
    figure_of_merit. C_T comes from the thrust C_T = T / (rho * A *
    Vtip^2), the inflow ratio from the uniform-inflow closure, then the
    C_Q split, torque, power and figure of merit. The supplied
    collective is verified to reproduce the thrust-derived C_T through
    the blade-element integral (relative tolerance 1e-6), so the pitch
    schedule and the thrust describe the same hover state; mismatched
    inputs raise ValueError. ValueErrors from the primitives propagate.
    """
    _require_positive("thrust_N", thrust_N)
    _require_positive("radius_m", radius_m)
    _require_positive("rho", rho)
    _require_positive("solidity", solidity)
    _require_positive("lift_slope", lift_slope)
    _require_positive("drag_coefficient", drag_coefficient)
    _require_positive("tip_speed", tip_speed)
    _require_tip_loss(tip_loss)
    _require_non_negative("collective_rad", collective_rad)

    area = PI * radius_m ** 2
    c_t = thrust_N / (rho * area * tip_speed ** 2)
    inflow = inflow_ratio_from_ct(c_t)

    c_t_blade_element = thrust_coefficient(
        collective_rad, solidity, lift_slope, inflow, tip_loss)
    if abs(c_t_blade_element - c_t) > 1e-6 * c_t:
        raise ValueError(
            "collective_rad does not reproduce the thrust-derived C_T; "
            "pitch schedule and thrust describe different hover states")

    induced, profile, total = _torque_coefficient_split(
        c_t, inflow, solidity, drag_coefficient)
    torque = rotor_torque(total, rho, area, tip_speed, radius_m)
    power = rotor_power_from_torque(total, rho, area, tip_speed, radius_m)
    return {
        "thrust_coefficient": c_t,
        "inflow_ratio": inflow,
        "torque_coefficient_induced": induced,
        "torque_coefficient_profile": profile,
        "torque_coefficient_total": total,
        "rotor_torque_Nm": torque,
        "rotor_power_W": power,
        "figure_of_merit": figure_of_merit_from_coefficients(c_t, total),
    }


def collective_pitch_polar(collectives_rad, radius_m, rho, solidity,
                           lift_slope, drag_coefficient, tip_speed,
                           tip_loss):
    """Hover polar across a range of collective pitches.

    Returns one dict per collective with the keys of
    hover_blade_element_summary plus collective_rad. Each entry closes
    the inflow ratio by the fixed-point iteration lambda = sqrt(C_T /
    2) of the blade-element thrust coefficient (tolerance 1e-10, at
    most 200 iterations; hover-relevant collectives converge quickly).
    ValueErrors from the primitives propagate.
    """
    _require_positive("radius_m", radius_m)
    _require_positive("rho", rho)
    _require_positive("solidity", solidity)
    _require_positive("lift_slope", lift_slope)
    _require_positive("drag_coefficient", drag_coefficient)
    _require_positive("tip_speed", tip_speed)
    _require_tip_loss(tip_loss)

    area = PI * radius_m ** 2
    results = []
    for collective in collectives_rad:
        _require_non_negative("collective_rad", collective)
        inflow = 0.0
        for _ in range(200):
            c_t = thrust_coefficient(collective, solidity, lift_slope,
                                     inflow, tip_loss)
            inflow_new = inflow_ratio_from_ct(c_t)
            if abs(inflow_new - inflow) < 1e-10:
                inflow = inflow_new
                break
            inflow = inflow_new
        else:
            raise ValueError(
                "fixed-point inflow iteration did not converge for "
                "collective %r" % (collective,))
        c_t = thrust_coefficient(collective, solidity, lift_slope, inflow,
                                 tip_loss)
        induced, profile, total = _torque_coefficient_split(
            c_t, inflow, solidity, drag_coefficient)
        results.append({
            "collective_rad": collective,
            "thrust_coefficient": c_t,
            "inflow_ratio": inflow,
            "torque_coefficient_induced": induced,
            "torque_coefficient_profile": profile,
            "torque_coefficient_total": total,
            "rotor_torque_Nm": rotor_torque(total, rho, area, tip_speed,
                                            radius_m),
            "rotor_power_W": rotor_power_from_torque(total, rho, area,
                                                     tip_speed, radius_m),
            "figure_of_merit": figure_of_merit_from_coefficients(c_t,
                                                                 total),
        })
    return results
