"""Launch window analysis for orbital missions (pure Python 3, stdlib only).

Functions:
- launch_azimuth_for_inclination: direct-injection launch azimuth from
  cos(inc) = cos(lat) * sin(az).
- daily_window_center_halfwidth: window center and half-width from the
  plane-crossing geometry (site in the orbit plane).
- sun_sync_ltan_to_raan: local time of ascending node (LTAN) to RAAN for
  sun-synchronous orbits.
- plane_change_delta_v: dv = 2 * v * sin(di / 2).
- window_open_close: open/close times and duration from the center and
  half-width, plus the window repeat period from the relative rate
  (Earth rotation minus node regression).
- elevation_angle_at_crossing: satellite elevation above the launch site
  horizon near the plane-crossing instant (zenith pass model).
- beta_angle: sun elevation relative to the orbit plane (lighting check).

Units: angles in degrees, time in seconds, speed in km/s, distances in
km. Deterministic and offline: no ephemerides, no network, only the
constants below.

The geometry is the classic "the launch site is in the orbit plane"
condition. The site's right ascension is its local sidereal time
LST = GMST + site_lon. The site lies in the orbit plane when
sin(theta) = cos(lat) * sin(inc) * sin(raan - LST) + sin(lat) * cos(inc)
= 0, which solves to LST = raan + asin(tan(lat) / tan(inc)) for the
ascending-side crossing and LST = raan + 180 - asin(tan(lat) / tan(inc))
for the descending-side crossing. The window center is that instant; the
half-width is the time the site stays within the out-of-plane tolerance.
"""

import math

EARTH_RADIUS_KM = 6371.0
EARTH_MU_KM3_S2 = 398600.4418
EARTH_ROTATION_DEG_PER_DAY = 360.9856  # sidereal rate
SUN_SYNC_REGRESSION_DEG_PER_DAY = 0.9856  # RAAN rate that tracks the sun
DEG = math.pi / 180.0


def launch_azimuth_for_inclination(target_inc_deg, site_lat_deg):
    """Direct-injection launch azimuth for a target inclination.

    cos(inc) = cos(lat) * sin(az)  =>  az = asin(cos(inc) / cos(lat)).

    Due east (az = 90 deg) gives inc = lat. Direct injection requires
    inc >= |lat| (and inc <= 180 - |lat| for retrograde orbits), because
    |cos(inc) / cos(lat)| > 1 has no real solution; a ValueError is
    raised outside that range. Retrograde targets (inc > 90) launch
    westward: az = 180 - asin(cos(inc) / cos(lat)), in [90, 180].
    """
    lat = abs(site_lat_deg)
    if not (0.0 <= target_inc_deg <= 180.0):
        raise ValueError(
            "target inclination must be in [0, 180] deg, got %r" % (target_inc_deg,)
        )
    if not (-90.0 <= site_lat_deg <= 90.0):
        raise ValueError(
            "site latitude must be in [-90, 90] deg, got %r" % (site_lat_deg,)
        )
    if target_inc_deg < lat or target_inc_deg > 180.0 - lat:
        raise ValueError(
            "target inclination %.3f deg cannot be direct-injected from "
            "latitude %.3f deg (direct injection needs %.3f <= inc <= %.3f)"
            % (target_inc_deg, site_lat_deg, lat, 180.0 - lat)
        )
    ratio = math.cos(target_inc_deg * DEG) / math.cos(lat * DEG)
    # numerical guard: the feasibility check above keeps |ratio| <= 1
    ratio = max(-1.0, min(1.0, ratio))
    az = math.degrees(math.asin(ratio))
    if target_inc_deg > 90.0:
        az = 180.0 - az
    return az


def direct_injection_feasible(target_inc_deg, site_lat_deg):
    """True when the target inclination can be direct-injected from the site."""
    try:
        launch_azimuth_for_inclination(target_inc_deg, site_lat_deg)
        return True
    except ValueError:
        return False


def _plane_crossing_alpha(inc_deg, site_lat_deg, raan_deg, node="ascending"):
    """Right ascension (LST) at which the site lies in the orbit plane.

    Returns (crossing_alpha_deg, t) with t = tan(lat) / tan(inc). The
    ascending-side crossing is at raan + asin(t); the descending-side at
    raan + 180 - asin(t). Raises ValueError when |t| > 1 (the site never
    crosses the plane, same feasibility limit as the azimuth formula).
    """
    lat = abs(site_lat_deg)
    if abs(math.cos(inc_deg * DEG)) < 1e-12:
        t = 0.0  # polar orbit: tan(inc) is infinite
    else:
        t = math.tan(lat * DEG) / math.tan(inc_deg * DEG)
    if abs(t) > 1.0 + 1e-12:
        raise ValueError(
            "orbit inclination %.3f deg never crosses latitude %.3f deg "
            "at the launch site (|tan(lat)/tan(inc)| > 1)"
            % (inc_deg, site_lat_deg)
        )
    t = max(-1.0, min(1.0, t))
    delta = math.degrees(math.asin(t))
    if node == "descending":
        alpha = raan_deg + 180.0 - delta
    else:
        alpha = raan_deg + delta
    return alpha % 360.0, t


def daily_window_center_halfwidth(
    inc_deg,
    site_lat_deg,
    raan_deg,
    site_lon_deg,
    gmst_at_ref_deg,
    tolerance_deg,
    node_regression_deg_per_day=0.0,
    earth_rate_deg_per_day=EARTH_ROTATION_DEG_PER_DAY,
    node="ascending",
):
    """Daily launch window center and half-width (seconds from reference).

    The window center is the instant the target orbit plane passes
    through the launch site: site LST = GMST + site_lon equals the plane
    crossing right ascension. The half-width is the time the site stays
    within tolerance_deg of the plane near the crossing. The site's
    out-of-plane angle grows as sin(theta) = cos(lat) * sin(inc) *
    (sqrt(1 - t^2) * u + t * u^2 / 2) with u the angular offset from the
    crossing and t = tan(lat) / tan(inc); the half-width solves that
    expression for sin(theta) = sin(tolerance). Both the site and the
    node move: the relative rate is earth_rate - node_regression, so a
    sun-synchronous orbit (node_regression = +0.9856 deg/day) gives a
    window that repeats at exactly 360.0 deg/day, the same local solar
    time every day.

    Returns a dict: center_seconds, half_width_seconds, center_lst_deg,
    crossing_alpha_deg, relative_rate_deg_per_day, t.
    """
    alpha_cross, t = _plane_crossing_alpha(inc_deg, site_lat_deg, raan_deg, node)
    rel_rate = earth_rate_deg_per_day - node_regression_deg_per_day
    if rel_rate <= 0.0:
        raise ValueError("relative rate must be positive, got %r" % (rel_rate,))
    d_lst = (alpha_cross - site_lon_deg - gmst_at_ref_deg) % 360.0
    center_seconds = d_lst / rel_rate * 86400.0

    lat = abs(site_lat_deg)
    cos_lat_sin_i = math.cos(lat * DEG) * math.sin(inc_deg * DEG)
    a_lin = cos_lat_sin_i * math.sqrt(max(0.0, 1.0 - t * t))
    b_quad = cos_lat_sin_i * t / 2.0
    eps = tolerance_deg * DEG
    if b_quad == 0.0:
        u = eps / a_lin if a_lin > 0.0 else float("inf")
    else:
        disc = a_lin * a_lin + 4.0 * b_quad * eps
        u = (-a_lin + math.sqrt(max(0.0, disc))) / (2.0 * b_quad)
    half_deg = math.degrees(max(0.0, u))
    half_seconds = half_deg / rel_rate * 86400.0

    return {
        "center_seconds": center_seconds,
        "half_width_seconds": half_seconds,
        "center_lst_deg": alpha_cross,
        "crossing_alpha_deg": alpha_cross,
        "relative_rate_deg_per_day": rel_rate,
        "t": t,
    }


def window_open_close(
    inc_deg,
    site_lat_deg,
    raan_deg,
    site_lon_deg,
    gmst_at_ref_deg,
    tolerance_deg,
    node_regression_deg_per_day=0.0,
    earth_rate_deg_per_day=EARTH_ROTATION_DEG_PER_DAY,
    node="ascending",
):
    """Open/close times and duration of the daily launch window.

    Same inputs as daily_window_center_halfwidth. Returns a dict with
    window_center_seconds, window_open_seconds, window_close_seconds,
    window_duration_seconds, half_width_seconds, center_lst_deg and
    window_period_days = 360 / (earth_rate - node_regression), the time
    between successive windows. The period is exactly 1.0 day for a
    sun-synchronous orbit.
    """
    g = daily_window_center_halfwidth(
        inc_deg,
        site_lat_deg,
        raan_deg,
        site_lon_deg,
        gmst_at_ref_deg,
        tolerance_deg,
        node_regression_deg_per_day=node_regression_deg_per_day,
        earth_rate_deg_per_day=earth_rate_deg_per_day,
        node=node,
    )
    center = g["center_seconds"]
    half = g["half_width_seconds"]
    return {
        "window_center_seconds": center,
        "window_open_seconds": center - half,
        "window_close_seconds": center + half,
        "window_duration_seconds": 2.0 * half,
        "half_width_seconds": half,
        "center_lst_deg": g["center_lst_deg"],
        "window_period_days": 360.0 / g["relative_rate_deg_per_day"],
    }


def sun_sync_ltan_to_raan(ltan_hours, sun_ra_deg=0.0):
    """RAAN of a sun-synchronous orbit from its LTAN.

    The ascending node crossing happens at local solar time LTAN, so the
    node meridian sits (LTAN - 12) hours west of the subsolar meridian:
    raan = sun_ra + 15 * (LTAN - 12), mod 360. LTAN 12:00 gives
    raan = sun_ra (node under the sun); LTAN 06:00 (dawn-dusk) gives
    raan = sun_ra - 90; LTAN 18:00 gives sun_ra + 90.
    """
    if not (0.0 <= ltan_hours <= 24.0):
        raise ValueError("LTAN must be in [0, 24] hours, got %r" % (ltan_hours,))
    return (sun_ra_deg + 15.0 * (ltan_hours - 12.0)) % 360.0


def plane_change_delta_v(inclination_change_deg, speed_km_s):
    """Delta-v for an orbit plane change: dv = 2 * v * sin(di / 2)."""
    return 2.0 * speed_km_s * math.sin(inclination_change_deg * DEG / 2.0)


def elevation_angle_at_crossing(
    altitude_km,
    time_seconds_from_crossing=0.0,
    earth_radius_km=EARTH_RADIUS_KM,
):
    """Satellite elevation angle above the launch site horizon.

    At the plane-crossing instant the launch site lies on the ground
    track (a zenith pass), so the elevation at t = 0 is 90 deg. Near the
    crossing the sub-satellite point moves at the orbital angular rate
    v / r, and the elevation follows the standard pass geometry:
    e = atan2(cos(mu) - R / r, sin(mu)) with mu = v * t / r. The horizon
    (e = 0) is at mu = acos(R / r), about 5 minutes either side for a
    400 km orbit. Returns degrees (negative below the horizon).
    """
    r = earth_radius_km + altitude_km
    v = math.sqrt(EARTH_MU_KM3_S2 / r)
    mu = v * time_seconds_from_crossing / r
    return math.degrees(
        math.atan2(
            math.cos(mu) - earth_radius_km / r,
            math.sin(mu),
        )
    )


def beta_angle(sun_ra_deg, sun_dec_deg, raan_deg, inc_deg):
    """Sun elevation relative to the orbit plane (lighting geometry).

    beta is the angle between the sun direction and the orbit plane,
    sin(beta) = n_hat . s_hat with n_hat the orbit normal. |beta| near
    90 deg means the sun lies in the plane (dawn-dusk orbits at
    equinox); beta near 0 means the sun is perpendicular to the plane
    (noon-midnight orbits). Negative when the sun is below the plane.
    """
    nx = math.sin(inc_deg * DEG) * math.sin(raan_deg * DEG)
    ny = -math.sin(inc_deg * DEG) * math.cos(raan_deg * DEG)
    nz = math.cos(inc_deg * DEG)
    sx = math.cos(sun_dec_deg * DEG) * math.cos(sun_ra_deg * DEG)
    sy = math.cos(sun_dec_deg * DEG) * math.sin(sun_ra_deg * DEG)
    sz = math.sin(sun_dec_deg * DEG)
    sin_beta = nx * sx + ny * sy + nz * sz
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_beta))))
