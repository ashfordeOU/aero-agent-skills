"""Powered-ascent gravity-loss accounting for launch vehicles (pure stdlib).

Owns the gravity-loss leg of the ascent delta-v budget: burn time from the
propellant load and flow rate, launch thrust-to-weight ratio, the gravity
loss for a vertical or pitched ascent, and the effective and required ideal
delta-v that bracket the losses. The pitched model holds the mean
flight-path angle constant for the whole burn (the leaf envelope). SI units
throughout: kg, kg/s, N, s, m/s, degrees.

Sibling leaves own the ideal budget itself (rocket-sizing), staging
allocation (rocket-staging) and post-injection budgeting
(mission-delta-v-budget); this module only converts an ideal budget input
into an ascent-feasible requirement.
"""

import math

G0 = 9.80665  # standard gravity, m/s^2


def burn_time(propellant_mass, mass_flow):
    """Return the powered-ascent burn time t_b = m_prop / m_dot in seconds.

    ValueError when the propellant load or the flow rate is not positive.
    """
    if propellant_mass <= 0:
        raise ValueError("propellant mass must be positive")
    if mass_flow <= 0:
        raise ValueError("propellant mass flow must be positive")
    return propellant_mass / mass_flow


def thrust_to_weight(thrust, initial_mass):
    """Return the launch thrust-to-weight ratio TWR = T / (m0 * g0).

    ValueError when the sea-level thrust or the initial mass is not
    positive.
    """
    if thrust <= 0:
        raise ValueError("sea-level thrust must be positive")
    if initial_mass <= 0:
        raise ValueError("initial mass must be positive")
    return thrust / (initial_mass * G0)


def gravity_loss_vertical(burn_time_s):
    """Return the vertical-ascent gravity loss g0 * t_b in m/s.

    ValueError when the burn time is negative.
    """
    if burn_time_s < 0:
        raise ValueError("burn time must not be negative")
    return G0 * burn_time_s


def gravity_loss_pitched(burn_time_s, mean_path_angle_deg):
    """Return the pitched-ascent gravity loss g0 * t_b * sin(gamma) in m/s.

    gamma is the constant mean flight-path angle in degrees, held fixed
    over the whole burn (the leaf envelope). ValueError when the burn time
    is negative or the mean path angle falls outside [0, 90] degrees.
    """
    if burn_time_s < 0:
        raise ValueError("burn time must not be negative")
    if not 0.0 <= mean_path_angle_deg <= 90.0:
        raise ValueError("mean flight-path angle must lie in [0, 90] degrees")
    return G0 * burn_time_s * math.sin(math.radians(mean_path_angle_deg))


def effective_delta_v(ideal_delta_v, gravity_loss, drag_loss=0.0):
    """Return the effective ascent delta-v: ideal budget minus the losses.

    effective = dv_ideal - dv_gravity - dv_drag. ValueError when any loss
    is negative or when the losses sum to more than the ideal delta-v.
    """
    if gravity_loss < 0:
        raise ValueError("gravity loss must not be negative")
    if drag_loss < 0:
        raise ValueError("drag loss must not be negative")
    if gravity_loss + drag_loss > ideal_delta_v:
        raise ValueError("losses sum to more than the ideal delta-v")
    return ideal_delta_v - gravity_loss - drag_loss


def required_ideal_delta_v(target_delta_v, gravity_loss, drag_loss=0.0):
    """Return the ideal delta-v required for a net target: target plus losses.

    required = dv_target + dv_gravity + dv_drag. The guard mirrors
    effective_delta_v: ValueError when any loss is negative or when the
    losses sum to more than the target net delta-v.
    """
    if gravity_loss < 0:
        raise ValueError("gravity loss must not be negative")
    if drag_loss < 0:
        raise ValueError("drag loss must not be negative")
    if gravity_loss + drag_loss > target_delta_v:
        raise ValueError("losses sum to more than the target delta-v")
    return target_delta_v + gravity_loss + drag_loss


def ascent_report(propellant_mass, mass_flow, thrust, initial_mass,
                  ideal_delta_v, target_delta_v, mean_path_angle_deg=90.0,
                  drag_loss=0.0):
    """Return the ascent dict with keys burn_time, thrust_to_weight,
    gravity_loss, effective_delta_v, required_ideal_delta_v.

    Gravity loss follows the pitched model at the constant mean
    flight-path angle; the default 90 degrees reproduces the vertical
    ascent loss. All guard errors propagate from the single-purpose
    functions.
    """
    t_b = burn_time(propellant_mass, mass_flow)
    twr = thrust_to_weight(thrust, initial_mass)
    grav = gravity_loss_pitched(t_b, mean_path_angle_deg)
    effective = effective_delta_v(ideal_delta_v, grav, drag_loss)
    required = required_ideal_delta_v(target_delta_v, grav, drag_loss)
    return {
        "burn_time": t_b,
        "thrust_to_weight": twr,
        "gravity_loss": grav,
        "effective_delta_v": effective,
        "required_ideal_delta_v": required,
    }
