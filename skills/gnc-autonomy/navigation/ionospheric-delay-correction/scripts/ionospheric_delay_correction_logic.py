"""Klobuchar broadcast ionospheric delay correction, pure stdlib math.

Implements the GPS L1 single-frequency Klobuchar broadcast model: the
earth-centred angle to the ionospheric pierce point, the subionospheric
point, the pierce-point geomagnetic latitude, the local time of day at
the pierce point, the amplitude and period quartic polynomials in the
broadcast alpha and beta coefficients, the day-curve shape about the
14:00 local-time peak, the vertical delay with its 5 ns night floor, the
elevation obliquity factor and the slant delay. Reference-only: RTCA
DO-229 and IS-GPS-200 section 20.3.3.5.1 (Klobuchar, IEEE TAES AES-23(3)
:325-331, 1987), summary paraphrase, no verbatim text.
"""

import math

C_LIGHT = 299792458.0
T_BASE = 5.0e-9
P_MIN = 72000.0
T_PEAK = 50400.0
DAY_SECONDS = 86400.0
WEEK_SECONDS = 604800.0
SEC_PER_SC = 43200.0
DEG_PER_SC = 180.0
PHI_CLAMP_SC = 0.416
POLE_LAT_SC = 0.064
POLE_LON_SC = 1.617


def _check_finite(value, name):
    """Raise ValueError unless value is a finite number."""
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))


def _check_el(el_deg):
    """Raise ValueError unless elevation is finite and in (0, 90] deg."""
    _check_finite(el_deg, "elevation")
    if not (0.0 < el_deg <= 90.0):
        raise ValueError("elevation must be in (0, 90] deg, got %r" % el_deg)


def _check_lat(lat_deg, name):
    """Raise ValueError unless a latitude is finite and in [-90, 90] deg."""
    _check_finite(lat_deg, name)
    if not (-90.0 <= lat_deg <= 90.0):
        raise ValueError("%s must be in [-90, 90] deg, got %r" % (name, lat_deg))


def _check_lon(lon_deg, name):
    """Raise ValueError unless a longitude is finite and in [-180, 180] deg."""
    _check_finite(lon_deg, name)
    if not (-180.0 <= lon_deg <= 180.0):
        raise ValueError("%s must be in [-180, 180] deg, got %r" % (name, lon_deg))


def _check_az(az_deg):
    """Raise ValueError unless azimuth is finite and in [0, 360) deg."""
    _check_finite(az_deg, "azimuth")
    if not (0.0 <= az_deg < 360.0):
        raise ValueError("azimuth must be in [0, 360) deg, got %r" % az_deg)


def _check_tow(tow_sec):
    """Raise ValueError unless GPS time of week is finite and in [0, 604800) s."""
    _check_finite(tow_sec, "time of week")
    if not (0.0 <= tow_sec < WEEK_SECONDS):
        raise ValueError(
            "time of week must be in [0, %r) s, got %r" % (WEEK_SECONDS, tow_sec)
        )


def _check_coeff(coeff, name):
    """Raise ValueError unless coeff is 4 finite numbers with a non-negative constant term."""
    if len(coeff) != 4:
        raise ValueError("%s must have exactly 4 coefficients, got %d" % (name, len(coeff)))
    for term in coeff:
        _check_finite(term, name)
    if coeff[0] < 0.0:
        raise ValueError("%s[0] must be non-negative, got %r" % (name, coeff[0]))


def _check_phi_m(phi_m_deg):
    """Raise ValueError unless the geomagnetic latitude is finite and in [-90, 90] deg."""
    _check_finite(phi_m_deg, "geomagnetic latitude")
    if not (-90.0 <= phi_m_deg <= 90.0):
        raise ValueError(
            "geomagnetic latitude must be in [-90, 90] deg, got %r" % phi_m_deg
        )


def _check_t_local(t_local_sec):
    """Raise ValueError unless the local time is finite and in [0, 86400) s."""
    _check_finite(t_local_sec, "local time")
    if not (0.0 <= t_local_sec < DAY_SECONDS):
        raise ValueError(
            "local time must be in [0, %r) s, got %r" % (DAY_SECONDS, t_local_sec)
        )


def _clamp(value, lo, hi):
    """Clamp value into [lo, hi]."""
    return max(lo, min(hi, value))


def earth_center_angle_deg(el_deg):
    """Workflow step 1: earth-centred angle to the ionospheric pierce point, degrees."""
    _check_el(el_deg)
    e_sc = el_deg / DEG_PER_SC
    psi_sc = 0.0137 / (e_sc + 0.11) - 0.022
    return DEG_PER_SC * psi_sc


def subionospheric_point_deg(lat_deg, lon_deg, el_deg, az_deg):
    """Workflow step 1: subionospheric point (lat_i_deg, lon_i_deg), lon normalized to [-180, 180)."""
    _check_lat(lat_deg, "user latitude")
    _check_lon(lon_deg, "user longitude")
    _check_az(az_deg)
    psi_deg = earth_center_angle_deg(el_deg)
    psi_sc = psi_deg / DEG_PER_SC
    lat_sc = lat_deg / DEG_PER_SC
    lon_sc = lon_deg / DEG_PER_SC
    az_rad = math.radians(az_deg)
    lat_i_sc = _clamp(lat_sc + psi_sc * math.cos(az_rad), -PHI_CLAMP_SC, PHI_CLAMP_SC)
    lon_i_sc = lon_sc + psi_sc * math.sin(az_rad) / math.cos(math.pi * lat_i_sc)
    lat_i_deg = lat_i_sc * DEG_PER_SC
    lon_i_deg_raw = lon_i_sc * DEG_PER_SC
    lon_i_deg = ((lon_i_deg_raw + 180.0) % 360.0) - 180.0
    return (lat_i_deg, lon_i_deg)


def geomagnetic_latitude_deg(lat_i_deg, lon_i_deg):
    """Workflow step 2: pierce-point geomagnetic latitude phi_m, degrees."""
    _check_lat(lat_i_deg, "subionospheric latitude")
    _check_lon(lon_i_deg, "subionospheric longitude")
    lat_i_sc = lat_i_deg / DEG_PER_SC
    lon_i_sc = lon_i_deg / DEG_PER_SC
    phi_m_sc = lat_i_sc + POLE_LAT_SC * math.cos(math.pi * (lon_i_sc - POLE_LON_SC))
    return phi_m_sc * DEG_PER_SC


def local_time_seconds(lon_i_deg, tow_sec):
    """Workflow step 2: local time of day at the pierce point, seconds in [0, 86400)."""
    _check_lon(lon_i_deg, "subionospheric longitude")
    _check_tow(tow_sec)
    lon_i_sc = lon_i_deg / DEG_PER_SC
    return (SEC_PER_SC * lon_i_sc + tow_sec) % DAY_SECONDS


def amplitude_seconds(alpha, phi_m_deg):
    """Workflow step 3: amplitude A of the day-curve polynomial, clamped to >= 0 s."""
    _check_coeff(alpha, "alpha")
    _check_phi_m(phi_m_deg)
    phi_m_sc = phi_m_deg / DEG_PER_SC
    raw = alpha[0] + alpha[1] * phi_m_sc + alpha[2] * phi_m_sc ** 2 + alpha[3] * phi_m_sc ** 3
    return max(0.0, raw)


def period_seconds(beta, phi_m_deg):
    """Workflow step 3: period P of the day-curve polynomial, clamped to >= 72000 s."""
    _check_coeff(beta, "beta")
    _check_phi_m(phi_m_deg)
    phi_m_sc = phi_m_deg / DEG_PER_SC
    raw = beta[0] + beta[1] * phi_m_sc + beta[2] * phi_m_sc ** 2 + beta[3] * phi_m_sc ** 3
    return max(P_MIN, raw)


def day_shape_factor(t_local_sec, period_sec):
    """Workflow step 4: day-curve shape c about the 14:00 local-time peak, in [0, 1]."""
    _check_t_local(t_local_sec)
    _check_finite(period_sec, "period")
    if period_sec <= 0.0:
        raise ValueError("period must be positive, got %r" % period_sec)
    x = 2.0 * math.pi * (t_local_sec - T_PEAK) / period_sec
    if abs(x) < math.pi / 2.0:
        return 1.0 - (x * x) / 2.0 + (x ** 4) / 24.0
    return 0.0


def vertical_delay_seconds(alpha, beta, phi_m_deg, t_local_sec):
    """Workflow step 4: vertical ionospheric delay, seconds, never below the 5e-9 s base."""
    amp = amplitude_seconds(alpha, phi_m_deg)
    per = period_seconds(beta, phi_m_deg)
    shape = day_shape_factor(t_local_sec, per)
    return T_BASE + amp * shape


def slant_factor(el_deg):
    """Workflow step 5: elevation obliquity factor F mapping vertical to slant delay."""
    _check_el(el_deg)
    return 1.0 + 2.0 * ((96.0 - el_deg) / 90.0) ** 3


def slant_delay_seconds(alpha, beta, lat_deg, lon_deg, el_deg, az_deg, tow_sec):
    """Workflow steps 1-5: full pipeline, slant ionospheric delay of the L1 line of sight, seconds."""
    lat_i_deg, lon_i_deg = subionospheric_point_deg(lat_deg, lon_deg, el_deg, az_deg)
    phi_m_deg = geomagnetic_latitude_deg(lat_i_deg, lon_i_deg)
    t_local_sec = local_time_seconds(lon_i_deg, tow_sec)
    t_vert = vertical_delay_seconds(alpha, beta, phi_m_deg, t_local_sec)
    f_obliquity = slant_factor(el_deg)
    return f_obliquity * t_vert


def delay_meters(delay_seconds):
    """Workflow step 6: convert a delay in seconds to metres via the vacuum speed of light."""
    _check_finite(delay_seconds, "delay")
    if delay_seconds < 0.0:
        raise ValueError("delay must be non-negative, got %r" % delay_seconds)
    return delay_seconds * C_LIGHT


def slant_delay_meters(alpha, beta, lat_deg, lon_deg, el_deg, az_deg, tow_sec):
    """Workflow step 6: slant ionospheric delay in metres (convenience wrapper)."""
    return delay_meters(
        slant_delay_seconds(alpha, beta, lat_deg, lon_deg, el_deg, az_deg, tow_sec)
    )
