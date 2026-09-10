#!/usr/bin/env python3
"""ECSS-E-ST-10-04C Annex E (info) geomagnetic field model reference
data (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
geomagnetic environment near Earth is described by an internal field
model (source: core currents, released as a 5-year-generation
coefficient set such as IGRF) that dominates close to Earth, and by
external/magnetospheric field models (source: magnetospheric ring,
tail, and magnetopause currents) that become significant further out
and whose selection depends on geomagnetic activity level. Beyond the
nominal magnetopause standoff distance, which itself moves with
solar-wind dynamic pressure, the region is no longer inside the
magnetosphere and an Earth-field model does not apply without first
checking position against that boundary. This module implements
field-model-regime classification by altitude, internal-field
spherical-harmonic degree/order sizing, coefficient-generation epoch
validation, external-model tier selection from geomagnetic activity,
and magnetopause standoff/position checks; it does not implement the
internal or external field models' own coefficient evaluation.
"""

EARTH_RADIUS_KM = 6371.2

# Field-model regime boundaries, expressed as radial distance from
# Earth's center in Earth radii. Within INTERNAL_ONLY_LIMIT_RE the
# internal field alone is an adequate description; out to
# EXTERNAL_REQUIRED_LIMIT_RE the external field's contribution is
# significant and must be added; beyond that the position may be
# outside the magnetosphere and must be checked against the
# magnetopause before any Earth-field model is assumed to apply.
INTERNAL_ONLY_LIMIT_RE = 2.0
EXTERNAL_REQUIRED_LIMIT_RE = 10.0

REGIME_INTERNAL_ONLY = "internal_only"
REGIME_INTERNAL_PLUS_EXTERNAL = "internal_plus_external"
REGIME_BEYOND_NOMINAL_MAGNETOPAUSE = "beyond_nominal_magnetopause"

# Internal-field spherical-harmonic degree/order required for an
# accurate value, by altitude band. Higher-degree terms decay quickly
# with radial distance, so the required degree falls as altitude
# increases.
DEGREE_ORDER_BANDS_KM = (
    (1000.0, 13),
    (6000.0, 10),
    (20000.0, 8),
)
DEGREE_ORDER_BEYOND_BANDS = 4

# IGRF-style coefficient generation cadence: each generation's
# definitive coverage and its following predictive (secular-variation)
# coverage each span this many years.
GENERATION_EPOCH_START_YEAR = 1900
GENERATION_SPAN_YEARS = 5

EPOCH_STATUS_DEFINITIVE = "definitive"
EPOCH_STATUS_PREDICTIVE = "predictive"
EPOCH_STATUS_STALE = "stale"

# External/magnetospheric model tier selected by geomagnetic activity
# (Kp index, 0-9), with the additional inputs that tier requires
# beyond Kp itself.
_EXTERNAL_MODEL_BANDS = (
    (2.0, "T89", ("kp_index",)),
    (4.0, "T96", ("solar_wind_dynamic_pressure_npa", "imf_bz_nt", "dst_index_nt")),
    (
        6.0,
        "T01",
        (
            "solar_wind_dynamic_pressure_npa",
            "imf_by_nt",
            "imf_bz_nt",
            "dst_index_nt",
        ),
    ),
)
_EXTERNAL_MODEL_STORM_TIER = (
    "T04",
    (
        "solar_wind_dynamic_pressure_npa",
        "imf_by_nt",
        "imf_bz_nt",
        "dst_index_nt",
        "sym_h_index_nt",
    ),
)
KP_INDEX_MIN = 0.0
KP_INDEX_MAX = 9.0

# Nominal subsolar magnetopause standoff distance (Earth radii) at a
# reference solar-wind dynamic pressure; the standoff distance scales
# down as pressure increases and up as pressure decreases.
NOMINAL_MAGNETOPAUSE_STANDOFF_RE = 10.0
REFERENCE_DYNAMIC_PRESSURE_NPA = 2.0
MAGNETOPAUSE_PRESSURE_EXPONENT = 1.0 / 6.0

POSITION_INSIDE_MAGNETOPAUSE = "inside_magnetopause"
POSITION_OUTSIDE_OR_AT_MAGNETOPAUSE = "outside_or_at_magnetopause"


def altitude_to_radial_distance_re(altitude_km):
    """Radial distance from Earth's center, in Earth radii, for an
    altitude in km. Raises ValueError for a negative altitude."""
    if altitude_km < 0:
        raise ValueError("altitude_km must be >= 0")
    return (EARTH_RADIUS_KM + altitude_km) / EARTH_RADIUS_KM


def classify_field_model_regime(altitude_km):
    """Field-model regime for an orbit altitude (km): REGIME_INTERNAL_ONLY,
    REGIME_INTERNAL_PLUS_EXTERNAL, or REGIME_BEYOND_NOMINAL_MAGNETOPAUSE.
    Raises ValueError for a negative altitude."""
    radial_re = altitude_to_radial_distance_re(altitude_km)
    if radial_re <= INTERNAL_ONLY_LIMIT_RE:
        return REGIME_INTERNAL_ONLY
    if radial_re <= EXTERNAL_REQUIRED_LIMIT_RE:
        return REGIME_INTERNAL_PLUS_EXTERNAL
    return REGIME_BEYOND_NOMINAL_MAGNETOPAUSE


def required_igrf_degree(altitude_km):
    """Internal-field spherical-harmonic degree/order required for an
    accurate value at an orbit altitude (km). Raises ValueError for a
    negative altitude."""
    if altitude_km < 0:
        raise ValueError("altitude_km must be >= 0")
    for band_limit_km, degree in DEGREE_ORDER_BANDS_KM:
        if altitude_km <= band_limit_km:
            return degree
    return DEGREE_ORDER_BEYOND_BANDS


def validate_igrf_epoch(epoch_year, generation_epoch):
    """Validity status of an IGRF-style coefficient generation
    (generation_epoch, e.g. 2020) when evaluated at epoch_year.

    Returns {"status": EPOCH_STATUS_*, "years_since_generation_epoch":
    int}. Raises ValueError if generation_epoch is not a valid 5-year
    generation epoch (>= 1900, on a 5-year cadence from 1900), or if
    epoch_year precedes generation_epoch."""
    if generation_epoch < GENERATION_EPOCH_START_YEAR or (
        (generation_epoch - GENERATION_EPOCH_START_YEAR) % GENERATION_SPAN_YEARS
    ):
        raise ValueError(
            "generation_epoch %r is not a valid IGRF-style 5-year "
            "generation epoch" % (generation_epoch,)
        )
    if epoch_year < generation_epoch:
        raise ValueError(
            "epoch_year %r precedes generation_epoch %r" % (epoch_year, generation_epoch)
        )
    years_elapsed = epoch_year - generation_epoch
    if years_elapsed < GENERATION_SPAN_YEARS:
        status = EPOCH_STATUS_DEFINITIVE
    elif years_elapsed < GENERATION_SPAN_YEARS * 2:
        status = EPOCH_STATUS_PREDICTIVE
    else:
        status = EPOCH_STATUS_STALE
    return {"status": status, "years_since_generation_epoch": years_elapsed}


def select_external_model(kp_index):
    """External/magnetospheric model tier for a geomagnetic activity
    (Kp) index. Returns {"model": str, "required_inputs": tuple of
    str}. Raises ValueError if kp_index is outside [0, 9]."""
    if kp_index < KP_INDEX_MIN or kp_index > KP_INDEX_MAX:
        raise ValueError("kp_index must be within [%s, %s]" % (KP_INDEX_MIN, KP_INDEX_MAX))
    for band_limit, model, required_inputs in _EXTERNAL_MODEL_BANDS:
        if kp_index <= band_limit:
            return {"model": model, "required_inputs": required_inputs}
    model, required_inputs = _EXTERNAL_MODEL_STORM_TIER
    return {"model": model, "required_inputs": required_inputs}


def magnetopause_standoff_re(dynamic_pressure_npa):
    """Subsolar magnetopause standoff distance (Earth radii) for a
    solar-wind dynamic pressure (nPa), by simplified empirical scaling
    against the nominal standoff at the reference pressure. Raises
    ValueError if dynamic_pressure_npa is not positive."""
    if dynamic_pressure_npa <= 0:
        raise ValueError("dynamic_pressure_npa must be > 0")
    return NOMINAL_MAGNETOPAUSE_STANDOFF_RE * (
        REFERENCE_DYNAMIC_PRESSURE_NPA / dynamic_pressure_npa
    ) ** MAGNETOPAUSE_PRESSURE_EXPONENT


def classify_magnetopause_position(radial_distance_re, dynamic_pressure_npa):
    """Position of a radial distance (Earth radii) relative to the
    magnetopause under a given solar-wind dynamic pressure (nPa):
    POSITION_INSIDE_MAGNETOPAUSE or POSITION_OUTSIDE_OR_AT_MAGNETOPAUSE.
    Raises ValueError if radial_distance_re is not positive or
    dynamic_pressure_npa is not positive."""
    if radial_distance_re <= 0:
        raise ValueError("radial_distance_re must be > 0")
    standoff_re = magnetopause_standoff_re(dynamic_pressure_npa)
    if radial_distance_re >= standoff_re:
        return POSITION_OUTSIDE_OR_AT_MAGNETOPAUSE
    return POSITION_INSIDE_MAGNETOPAUSE


def field_model_source_selection(altitude_km, kp_index, dynamic_pressure_npa=None):
    """Full Annex E field-model-source determination for an orbit
    altitude (km) and geomagnetic activity (Kp) index.

    Returns {"regime": str, "igrf_degree": int, "external_model":
    dict | None, "magnetopause_position": str | None}. external_model
    is set whenever the regime requires it (REGIME_INTERNAL_PLUS_EXTERNAL
    or REGIME_BEYOND_NOMINAL_MAGNETOPAUSE); magnetopause_position is
    set only for REGIME_BEYOND_NOMINAL_MAGNETOPAUSE, which additionally
    requires dynamic_pressure_npa. Raises ValueError for a negative
    altitude, an out-of-range kp_index, or a missing
    dynamic_pressure_npa when the regime requires the magnetopause
    check."""
    regime = classify_field_model_regime(altitude_km)
    igrf_degree = required_igrf_degree(altitude_km)
    external_model = None
    magnetopause_position = None
    if regime != REGIME_INTERNAL_ONLY:
        external_model = select_external_model(kp_index)
    if regime == REGIME_BEYOND_NOMINAL_MAGNETOPAUSE:
        if dynamic_pressure_npa is None:
            raise ValueError(
                "dynamic_pressure_npa is required to evaluate the "
                "magnetopause position beyond the nominal "
                "external-field-model limit"
            )
        radial_re = altitude_to_radial_distance_re(altitude_km)
        magnetopause_position = classify_magnetopause_position(
            radial_re, dynamic_pressure_npa
        )
    return {
        "regime": regime,
        "igrf_degree": igrf_degree,
        "external_model": external_model,
        "magnetopause_position": magnetopause_position,
    }
