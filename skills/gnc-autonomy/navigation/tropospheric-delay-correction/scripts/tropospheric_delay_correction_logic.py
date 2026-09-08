"""Saastamoinen tropospheric delay correction, pure stdlib math.

Implements the Saastamoinen (1973) summary-form surface-met tropospheric
delay model for a single GNSS line of sight: the gravity/height factor
from station latitude and height, the zenith hydrostatic delay from
surface pressure, the zenith wet delay from the water-vapour partial
pressure and temperature, the zenith total delay, the cosecant
elevation-mapping-function, and the slant hydrostatic, wet and total
tropospheric delays. Reference-only: Saastamoinen, "Contributions to the
Theory of Atmospheric Refraction," Bulletin Geodesique 107:13-34, 1973,
and RTCA DO-229; Hopfield 1969 is the standard alternative, not
implemented. Summary paraphrase, no verbatim text.
"""

import math

K_TROP = 0.002277
WET_T_NUM = 1255.0
WET_T_C = 0.05
G_COS2 = 0.00266
G_H_KM = 0.00028
ES_0 = 6.112
MAGNUS_A = 17.62
MAGNUS_B = 243.12
KELVIN_OFFSET = 273.15
P_MIN_HPA = 300.0
P_MAX_HPA = 1100.0
T_MIN_K = 200.0
T_MAX_K = 340.0
H_MIN_KM = -1.0
H_MAX_KM = 10.0


def _check_finite(value, name):
    """Raise ValueError unless value is a finite number."""
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))


def _check_t(t_k):
    """Raise ValueError unless temperature is finite and in [200, 340] K."""
    _check_finite(t_k, "temperature")
    if not (T_MIN_K <= t_k <= T_MAX_K):
        raise ValueError(
            "temperature must be in [%r, %r] K, got %r" % (T_MIN_K, T_MAX_K, t_k)
        )


def _check_rh(rh_pct):
    """Raise ValueError unless relative humidity is finite and in [0, 100] percent."""
    _check_finite(rh_pct, "relative humidity")
    if not (0.0 <= rh_pct <= 100.0):
        raise ValueError(
            "relative humidity must be in [0, 100] percent, got %r" % rh_pct
        )


def _check_lat(phi_deg):
    """Raise ValueError unless geodetic latitude is finite and in [-90, 90] deg."""
    _check_finite(phi_deg, "latitude")
    if not (-90.0 <= phi_deg <= 90.0):
        raise ValueError("latitude must be in [-90, 90] deg, got %r" % phi_deg)


def _check_h(h_km):
    """Raise ValueError unless station height is finite and in [-1, 10] km."""
    _check_finite(h_km, "height")
    if not (H_MIN_KM <= h_km <= H_MAX_KM):
        raise ValueError(
            "height must be in [%r, %r] km, got %r" % (H_MIN_KM, H_MAX_KM, h_km)
        )


def _check_p(p_hpa):
    """Raise ValueError unless surface pressure is finite and in [300, 1100] hPa."""
    _check_finite(p_hpa, "pressure")
    if not (P_MIN_HPA <= p_hpa <= P_MAX_HPA):
        raise ValueError(
            "pressure must be in [%r, %r] hPa, got %r" % (P_MIN_HPA, P_MAX_HPA, p_hpa)
        )


def _check_e(e_hpa, t_k):
    """Raise ValueError unless partial pressure is finite and in [0, es(T)] hPa."""
    _check_finite(e_hpa, "water-vapour partial pressure")
    es_t = saturation_vapor_pressure_hpa(t_k)
    if not (0.0 <= e_hpa <= es_t):
        raise ValueError(
            "water-vapour partial pressure must be in [0, %r] hPa, got %r"
            % (es_t, e_hpa)
        )


def _check_el(el_deg):
    """Raise ValueError unless elevation is finite and in (0, 90] deg."""
    _check_finite(el_deg, "elevation")
    if not (0.0 < el_deg <= 90.0):
        raise ValueError("elevation must be in (0, 90] deg, got %r" % el_deg)


def saturation_vapor_pressure_hpa(t_k):
    """Workflow step 1: Magnus saturation vapour pressure es(T), hPa."""
    _check_t(t_k)
    t_c = t_k - KELVIN_OFFSET
    return ES_0 * math.exp(MAGNUS_A * t_c / (MAGNUS_B + t_c))


def water_vapor_pressure_hpa(t_k, rh_pct):
    """Workflow step 1: water-vapour partial pressure e = es(T) * RH/100, hPa."""
    _check_rh(rh_pct)
    es_t = saturation_vapor_pressure_hpa(t_k)
    return es_t * rh_pct / 100.0


def gravity_factor(phi_deg, h_km):
    """Workflow step 2: Saastamoinen gravity/height factor f(phi, H)."""
    _check_lat(phi_deg)
    _check_h(h_km)
    phi_rad = math.radians(phi_deg)
    return 1.0 - G_COS2 * math.cos(2.0 * phi_rad) - G_H_KM * h_km


def zenith_hydrostatic_delay_m(p_hpa, phi_deg, h_km):
    """Workflow step 3: zenith hydrostatic (dry) delay ZHD, metres."""
    _check_p(p_hpa)
    f = gravity_factor(phi_deg, h_km)
    return K_TROP * p_hpa / f


def zenith_wet_delay_m(e_hpa, t_k, phi_deg, h_km):
    """Workflow step 4: zenith wet delay ZWD, metres."""
    _check_e(e_hpa, t_k)
    f = gravity_factor(phi_deg, h_km)
    wet_factor = WET_T_NUM / t_k + WET_T_C
    return K_TROP * wet_factor * e_hpa / f


def zenith_total_delay_m(p_hpa, e_hpa, t_k, phi_deg, h_km):
    """Workflow step 5: zenith total delay ZTD = ZHD + ZWD, metres."""
    zhd = zenith_hydrostatic_delay_m(p_hpa, phi_deg, h_km)
    zwd = zenith_wet_delay_m(e_hpa, t_k, phi_deg, h_km)
    return zhd + zwd


def slant_mapping_factor(el_deg):
    """Workflow step 6: cosecant elevation-mapping-function m(E) = 1/sin(E)."""
    _check_el(el_deg)
    return 1.0 / math.sin(math.radians(el_deg))


def slant_hydrostatic_delay_m(p_hpa, phi_deg, h_km, el_deg):
    """Workflow step 7: slant hydrostatic delay, ZHD * m(E), metres."""
    _check_el(el_deg)
    m = slant_mapping_factor(el_deg)
    zhd = zenith_hydrostatic_delay_m(p_hpa, phi_deg, h_km)
    return zhd * m


def slant_wet_delay_m(e_hpa, t_k, phi_deg, h_km, el_deg):
    """Workflow step 7: slant wet delay, ZWD * m(E), metres."""
    _check_el(el_deg)
    m = slant_mapping_factor(el_deg)
    zwd = zenith_wet_delay_m(e_hpa, t_k, phi_deg, h_km)
    return zwd * m


def slant_delay_m(p_hpa, e_hpa, t_k, phi_deg, h_km, el_deg):
    """Workflow step 7: full pipeline, slant tropospheric delay ZTD * m(E), metres."""
    _check_el(el_deg)
    ztd = zenith_total_delay_m(p_hpa, e_hpa, t_k, phi_deg, h_km)
    m = slant_mapping_factor(el_deg)
    return ztd * m
