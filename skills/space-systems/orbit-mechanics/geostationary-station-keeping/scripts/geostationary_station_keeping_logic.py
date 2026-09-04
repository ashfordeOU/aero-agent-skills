"""Geostationary station keeping: GEO orbit geometry and maneuver plan.

Pure Python stdlib implementation of the geostationary station-keeping
plan quantities for a GEO satellite: the geosynchronous radius and
orbital speed from the sidereal day, the annual north-south delta-v
from the inclination drift amplitude with the two-burn-per-year model,
the per-burn delta-v, the burn time from thruster thrust and spacecraft
mass, the annual propellant mass from the specific impulse over the
annual delta-v, the east-west deadband drift-cycle period and maneuver
cadence from the longitude acceleration magnitude and the box
half-width, and the uncontrolled drift time until the inclination
tolerance is exceeded.

Units are explicit per function: radii in km, speeds in m/s, delta-v in
m/s, time in s (burn) or days or years, mass in kg, propellant in kg.

Module constants (standard Earth values):
    MU          Earth gravitational parameter, km3/s2
    SIDEREAL_DAY  Earth rotation period vs the stars, s
    G0          standard gravity, m/s2
"""

import math

MU = 398600.4418          # Earth gravitational parameter, km3/s2
SIDEREAL_DAY = 86164.0905  # sidereal day, s
G0 = 9.80665              # standard gravity, m/s2
PI = math.pi


def geosynchronous_radius():
    """Return the geosynchronous orbit radius in km.

    The circular orbit whose period equals the sidereal day,
    r = (MU * (T / (2 * pi))**2) ** (1/3). ~42164 km.
    """
    period_arg = SIDEREAL_DAY / (2.0 * PI)
    return (MU * period_arg * period_arg) ** (1.0 / 3.0)


def geo_speed():
    """Return the geosynchronous circular orbital speed in m/s.

    v = 1000 * sqrt(MU / r) with r in km, converting km/s to m/s.
    """
    return 1000.0 * math.sqrt(MU / geosynchronous_radius())


def ns_annual_delta_v(inc_drift_deg_per_year):
    """Return the annual north-south delta-v in m/s for an inclination
    drift of inc_drift_deg_per_year degrees per year.

    Two burns per year keep the inclination inside a band of half-width
    drift/2, so the annual delta-v is 2 * v * sin(drift / 2).
    """
    if inc_drift_deg_per_year < 0.0:
        raise ValueError("inclination drift must be non-negative")
    return 2.0 * geo_speed() * math.sin(
        math.radians(inc_drift_deg_per_year) / 2.0
    )


def ns_per_burn_delta_v(inc_drift_deg_per_year):
    """Return the per-burn north-south delta-v in m/s.

    Half of the annual value, because the annual total is split into two
    burns per year at the nodal crossings.
    """
    return ns_annual_delta_v(inc_drift_deg_per_year) / 2.0


def burn_time(delta_v_m_s, thrust_N, mass_kg):
    """Return the burn duration in s for an impulsive delta-v.

    t = m * delta_v / F, constant-thrust approximation for a burn short
    against the orbital period.
    """
    if thrust_N <= 0.0:
        raise ValueError("thrust must be positive")
    if mass_kg <= 0.0:
        raise ValueError("mass must be positive")
    if delta_v_m_s < 0.0:
        raise ValueError("delta-v must be non-negative")
    return mass_kg * delta_v_m_s / thrust_N


def annual_propellant(delta_v_m_s, isp_s, mass_kg):
    """Return the propellant mass in kg for an annual delta-v.

    Rocket equation over the year, m_prop = m * (1 - exp(-delta_v /
    (isp * g0))), with the spacecraft mass at the start of the year.
    """
    if isp_s <= 0.0:
        raise ValueError("specific impulse must be positive")
    if mass_kg <= 0.0:
        raise ValueError("mass must be positive")
    if delta_v_m_s < 0.0:
        raise ValueError("delta-v must be non-negative")
    return mass_kg * (1.0 - math.exp(-delta_v_m_s / (isp_s * G0)))


def ew_cycle_period(box_half_width_deg, lon_accel_deg_day2):
    """Return the east-west deadband drift-cycle period in days.

    Inside a longitude box of half-width box_half_width_deg under a
    residual longitude acceleration lon_accel_deg_day2 the satellite
    drifts box-to-box in T = 2 * sqrt(2 * half_width / accel) days.
    """
    if box_half_width_deg <= 0.0:
        raise ValueError("box half width must be positive")
    if lon_accel_deg_day2 <= 0.0:
        raise ValueError("longitude acceleration must be positive")
    return 2.0 * math.sqrt(2.0 * box_half_width_deg / lon_accel_deg_day2)


def ew_maneuvers_per_year(box_half_width_deg, lon_accel_deg_day2):
    """Return the east-west maneuver cadence, maneuvers per year.

    365.25 days per year divided by the drift-cycle period, one
    correction maneuver per deadband crossing.
    """
    return 365.25 / ew_cycle_period(box_half_width_deg, lon_accel_deg_day2)


def uncontrolled_drift_years(inc_tolerance_deg, inc_drift_deg_per_year):
    """Return the years until the inclination tolerance is exceeded
    with station keeping off.

    Linear drift model: time = tolerance / drift rate.
    """
    if inc_tolerance_deg <= 0.0:
        raise ValueError("inclination tolerance must be positive")
    if inc_drift_deg_per_year <= 0.0:
        raise ValueError("inclination drift must be positive")
    return inc_tolerance_deg / inc_drift_deg_per_year
