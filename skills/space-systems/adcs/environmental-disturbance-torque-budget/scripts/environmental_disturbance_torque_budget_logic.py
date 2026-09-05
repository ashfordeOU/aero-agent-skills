"""Worst-case environmental disturbance torque budget for a LEO spacecraft.

Pure standard-library module. Estimates the four principal environmental
disturbance torque magnitudes acting on a spacecraft in a circular low
Earth orbit at a given attitude, rolls the per-source magnitudes into a
conservative worst-case budget, and compares the total against actuator
capability:

- gravity gradient: T = 1.5 * n^2 * |I_zz - I_yy| * |sin(2 * theta)|, with n
  the mean motion of the circular orbit, I_zz and I_yy the in-plane
  principal moments, and theta the attitude offset in degrees (the term
  peaks at +-45 degrees and vanishes at 0 and +-90 degrees).
- solar radiation pressure: T = P_sr * A * cos(i) * (1 + r) * L, with
  reflectivity r in [0, 1]: r = 0 is a fully absorbing surface (momentum
  flux P * A * cos(i) alone) and r = 1 a fully specular surface (momentum
  doubling to 2 * P * A * cos(i)); the default 1.0 is the worst case.
- residual magnetic dipole: T = m_res * B for the worst-case orthogonal
  geometry of the residual dipole magnitude against the local field
  magnitude (the same m x B physics a magnetorquer commands, applied here
  to the spacecraft residual dipole).
- aero drag: T = 0.5 * rho * v^2 * Cd * A * L at the explicit free-stream
  density rho and the circular-orbit speed v = sqrt(mu / r).

total_worst_case is the aligned-axis sum of the four magnitudes, the
conservative assumption that all four act on the same control axis at
their worst geometry simultaneously. disturbance_impulse_per_orbit =
total * orbit_period is the wheel momentum the reaction wheels must absorb
and the desaturation demand per orbit. torque_margin(available,
disturbance) rates an actuator capability against the total.

Conventions: circular orbit at radius = Earth radius + altitude, with
module Earth constants matching the adcs pack convention
(EARTH_RADIUS_M = 6378 km, EARTH_MU = 3.986004418e14 m3/s2). The
atmospheric density is an explicit input: this module bounds disturbance
torques, it does not model the atmosphere. All quantities are SI (m, s,
rad/s, kg m2, N m, N m s).
"""

import math

# Solar radiation pressure at 1 AU, N/m2.
SOLAR_PRESSURE_PA = 4.5e-6
# Earth gravitational parameter, m3/s2.
EARTH_MU = 3.986004418e14
# Earth mean radius, m (the 6,378 km convention of the adcs pack).
EARTH_RADIUS_M = 6378.0e3
# Worst-case attitude offset for the gravity-gradient term, degrees.
THETA_WORST_DEG = 45.0
DEG_TO_RAD = math.pi / 180.0


def orbital_mean_motion(radius_m):
    """Mean motion n = sqrt(EARTH_MU / radius_m**3) of a circular orbit.

    radius_m is the orbital radius in m (Earth radius plus altitude). The
    orbit must lie above the surface: a radius at or below EARTH_RADIUS_M
    raises ValueError.
    """
    if radius_m <= EARTH_RADIUS_M:
        raise ValueError("orbital radius must lie above the Earth surface")
    return math.sqrt(EARTH_MU / radius_m ** 3.0)


def orbital_velocity(radius_m):
    """Circular-orbit speed v = sqrt(EARTH_MU / radius_m), in m/s.

    Used by the aero drag term. A radius at or below EARTH_RADIUS_M raises
    ValueError.
    """
    if radius_m <= EARTH_RADIUS_M:
        raise ValueError("orbital radius must lie above the Earth surface")
    return math.sqrt(EARTH_MU / radius_m)


def orbit_period_s(radius_m):
    """Orbit period 2 * pi / n, in s, the per-orbit horizon for the impulse."""
    return 2.0 * math.pi / orbital_mean_motion(radius_m)


def gravity_gradient_torque(n_orbital, i_zz, i_yy, theta_deg):
    """Gravity-gradient disturbance torque magnitude, in N m.

    T = 1.5 * n^2 * |I_zz - I_yy| * |sin(2 * theta)| about the third body
    axis when the body z and y principal moments i_zz and i_yy lie in the
    plane swept between the local vertical and the body frame at attitude
    offset theta_deg. The absolute values keep the magnitude sign-free for
    either spread direction and either theta sign; the magnitude peaks at
    +-45 degrees and vanishes at 0 and +-90 degrees.
    """
    if n_orbital <= 0.0:
        raise ValueError("orbital mean motion must be positive")
    if i_zz <= 0.0 or i_yy <= 0.0:
        raise ValueError("principal moments of inertia must be positive")
    if abs(theta_deg) > 90.0:
        raise ValueError("attitude offset magnitude must not exceed 90 degrees")
    theta_rad = theta_deg * DEG_TO_RAD
    return 1.5 * n_orbital ** 2.0 * abs(i_zz - i_yy) * abs(
        math.sin(2.0 * theta_rad))


def solar_pressure_torque(area_m2, cos_incidence, lever_arm_m,
                          reflectivity=1.0):
    """Solar radiation pressure disturbance torque, in N m.

    T = SOLAR_PRESSURE_PA * A * cos(i) * (1 + r) * L. Reflectivity r is the
    surface reflection coefficient: r = 0 is a fully absorbing surface
    (force P * A * cos(i), the momentum flux alone) and r = 1 a fully
    specularly reflecting surface (force 2 * P * A * cos(i), momentum
    doubling); the default 1.0 is the worst case. cos_incidence is the
    cosine of the angle between the sunlit surface normal and the sun line,
    in [0, 1].
    """
    if area_m2 <= 0.0:
        raise ValueError("sunlit area must be positive")
    if cos_incidence < 0.0 or cos_incidence > 1.0:
        raise ValueError("cosine of incidence must lie in [0, 1]")
    if lever_arm_m <= 0.0:
        raise ValueError("force lever arm must be positive")
    if reflectivity < 0.0 or reflectivity > 1.0:
        raise ValueError("surface reflectivity must lie in [0, 1]")
    return (SOLAR_PRESSURE_PA * area_m2 * cos_incidence
            * (1.0 + reflectivity) * lever_arm_m)


def magnetic_residual_torque(residual_dipole_Am2, b_field_T):
    """Residual magnetic dipole disturbance torque, in N m.

    T = m_res * B for the worst-case orthogonal geometry (m perpendicular
    to B) of the residual dipole magnitude against the local field
    magnitude. A zero dipole is legal and returns 0.0.
    """
    if residual_dipole_Am2 < 0.0:
        raise ValueError("residual dipole magnitude must not be negative")
    if b_field_T <= 0.0:
        raise ValueError("local magnetic field magnitude must be positive")
    return residual_dipole_Am2 * b_field_T


def aero_drag_torque(rho, velocity_m_s, cd, area_m2, lever_arm_m):
    """Free-molecular aero drag disturbance torque, in N m.

    T = 0.5 * rho * v^2 * Cd * A * L at the explicit atmospheric density
    rho (kg/m3); feed orbital_velocity(radius_m) for the circular-orbit
    speed v.
    """
    if rho <= 0.0 or velocity_m_s <= 0.0 or cd <= 0.0:
        raise ValueError("density, velocity and drag coefficient must be positive")
    if area_m2 <= 0.0 or lever_arm_m <= 0.0:
        raise ValueError("drag area and lever arm must be positive")
    return 0.5 * rho * velocity_m_s ** 2.0 * cd * area_m2 * lever_arm_m


def disturbance_impulse(torque, period_s):
    """Per-orbit disturbance impulse torque * period_s, in N m s.

    The wheel momentum the spacecraft must absorb per orbit at the given
    disturbance torque. A zero torque is legal and returns 0.0.
    """
    if torque < 0.0:
        raise ValueError("disturbance torque must not be negative")
    if period_s <= 0.0:
        raise ValueError("orbit period must be positive")
    return torque * period_s


def torque_margin(available, disturbance):
    """Capability ratio available / disturbance, dimensionless.

    available is an actuator capability (reaction wheel torque in N m, or
    magnetorquer achievable torque m_max * B) against a disturbance
    torque; a ratio >= 1.0 means the actuator can cancel the worst-case
    disturbance.
    """
    if available <= 0.0:
        raise ValueError("available actuator torque must be positive")
    if disturbance <= 0.0:
        raise ValueError("disturbance torque must be positive")
    return available / disturbance


def worst_case_budget(radius_m, i_zz, i_yy, solar_area_m2, cos_incidence,
                      solar_lever_m, residual_dipole_Am2, b_field_T, rho,
                      drag_cd, drag_area_m2, drag_lever_m, theta_deg=45.0,
                      reflectivity=1.0):
    """Worst-case environmental disturbance torque budget for a LEO orbit.

    Returns a dict with keys mean_motion_rad_s, orbital_velocity_m_s,
    orbit_period_s, gravity_gradient, solar_pressure, magnetic_residual,
    aero_drag, total_worst_case, dominant_source and
    disturbance_impulse_per_orbit. theta_deg defaults to 45.0 (the
    worst-case attitude for the gravity-gradient term) and reflectivity to
    1.0 (the worst case); both are passable. total_worst_case is the
    conservative sum of the four per-source magnitudes on the documented
    assumption that all four act on the same control axis at their worst
    geometry simultaneously. dominant_source is the source key with the
    largest magnitude. disturbance_impulse_per_orbit =
    total_worst_case * orbit_period_s. ValueErrors propagate from the
    component functions.
    """
    n = orbital_mean_motion(radius_m)
    v = orbital_velocity(radius_m)
    period = orbit_period_s(radius_m)
    gravity = gravity_gradient_torque(n, i_zz, i_yy, theta_deg)
    solar = solar_pressure_torque(solar_area_m2, cos_incidence,
                                  solar_lever_m, reflectivity)
    magnetic = magnetic_residual_torque(residual_dipole_Am2, b_field_T)
    aero = aero_drag_torque(rho, v, drag_cd, drag_area_m2, drag_lever_m)
    sources = {
        "gravity_gradient": gravity,
        "solar_pressure": solar,
        "magnetic_residual": magnetic,
        "aero_drag": aero,
    }
    total = gravity + solar + magnetic + aero
    dominant = max(sources, key=lambda k: sources[k])
    return {
        "mean_motion_rad_s": n,
        "orbital_velocity_m_s": v,
        "orbit_period_s": period,
        "gravity_gradient": gravity,
        "solar_pressure": solar,
        "magnetic_residual": magnetic,
        "aero_drag": aero,
        "total_worst_case": total,
        "dominant_source": dominant,
        "disturbance_impulse_per_orbit": total * period,
    }
