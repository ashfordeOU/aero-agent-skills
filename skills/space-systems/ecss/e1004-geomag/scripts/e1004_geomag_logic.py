#!/usr/bin/env python3
"""ECSS-E-ST-10-04C clause 5.2 geomagnetic field model selection,
IGRF epoch/secular-variation handling, and B,L field logic
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
geomagnetic field has an internal (core-origin) component, well
represented by an IGRF-class spherical-harmonic model published at
fixed 5-year epochs with accompanying secular-variation (SV)
coefficients, and an external (magnetospheric) component that
dominates the difference from the internal-only estimate at high
geocentric distance. B,L coordinates label a field point by its local
magnitude B and the McIlwain L-shell it lies on; a dipole
approximation gives the equatorial field on an L-shell as the epoch
equatorial surface field strength divided by L cubed. This module
implements regime classification, model selection, IGRF epoch
validity/secular-variation scaling, and the dipole B,L computation; it
does not implement full spherical-harmonic synthesis of the real IGRF
coefficient set, Stormer cutoff geometry (see the sibling e1004-stormer
leaf), or trapped-belt flux models (see the sibling e1004-trapped-leo
leaf).
"""

MODEL_BY_REGIME = {
    "internal_only": "IGRF-class internal field model",
    "internal_plus_external": "IGRF-class internal field model + external/magnetospheric field model (e.g. Tsyganenko-class)",
}

INTERNAL_EXTERNAL_THRESHOLD_RE = 5.0

IGRF_EARLIEST_EPOCH_YEAR = 1900.0
IGRF_LATEST_EPOCH_YEAR = 2025.0
IGRF_EPOCH_STEP_YEARS = 5.0
IGRF_SV_EXTRAPOLATION_LIMIT_YEARS = 5.0


def classify_field_regime(geocentric_distance_re):
    """Classify a geocentric distance (Earth radii) into
    "internal_only" (at or below the internal/external threshold
    distance) or "internal_plus_external" (above it). Raises
    ValueError when the distance is not positive."""
    if geocentric_distance_re <= 0:
        raise ValueError("geocentric distance must be positive")
    if geocentric_distance_re <= INTERNAL_EXTERNAL_THRESHOLD_RE:
        return "internal_only"
    return "internal_plus_external"


def select_geomag_model(regime):
    """Reference geomagnetic model name for one field regime
    ("internal_only" or "internal_plus_external"). Raises ValueError
    for an unknown regime."""
    if regime not in MODEL_BY_REGIME:
        raise ValueError("unknown field regime: %r" % (regime,))
    return MODEL_BY_REGIME[regime]


def nearest_igrf_epoch(target_year):
    """Nearest published IGRF epoch (5-year grid) at or before
    target_year. Raises ValueError when target_year is before the
    earliest published epoch."""
    if target_year < IGRF_EARLIEST_EPOCH_YEAR:
        raise ValueError("target year is before the earliest published IGRF epoch")
    steps = int((target_year - IGRF_EARLIEST_EPOCH_YEAR) // IGRF_EPOCH_STEP_YEARS)
    return IGRF_EARLIEST_EPOCH_YEAR + steps * IGRF_EPOCH_STEP_YEARS


def is_within_igrf_validity(target_year):
    """True when target_year is covered by interpolation between
    published epochs or by secular-variation extrapolation within
    IGRF_SV_EXTRAPOLATION_LIMIT_YEARS of the latest published epoch.
    Raises ValueError when target_year is before the earliest
    published epoch."""
    nearest_igrf_epoch(target_year)
    if target_year <= IGRF_LATEST_EPOCH_YEAR:
        return True
    return (target_year - IGRF_LATEST_EPOCH_YEAR) <= IGRF_SV_EXTRAPOLATION_LIMIT_YEARS


def apply_secular_variation(epoch_field_value, secular_variation_rate, delta_years):
    """Field value at delta_years after its epoch, obtained by adding
    the secular-variation rate scaled by the elapsed time. Raises
    ValueError when delta_years is negative."""
    if delta_years < 0:
        raise ValueError("delta_years must not be negative")
    return epoch_field_value + secular_variation_rate * delta_years


def equatorial_field_at_l(l_shell, equatorial_surface_field):
    """Dipole-approximation equatorial field magnitude at l_shell,
    obtained by scaling equatorial_surface_field by l_shell ** -3.
    Raises ValueError when l_shell is not positive."""
    if l_shell <= 0:
        raise ValueError("l_shell must be positive")
    return equatorial_surface_field / (l_shell ** 3)


def assess_geomag_case(case):
    """Full geomagnetic model-selection and compliance assessment for
    one case dict. Required keys: id, geocentric_distance_re,
    target_year, declared_model, epoch_b0, secular_variation_rate.
    Optional key: l_shell. Returns a new dict; does not mutate the
    input. Raises ValueError when 'id' is missing or the case's
    geocentric_distance_re / target_year is invalid."""
    if "id" not in case:
        raise ValueError("geomagnetic case is missing an id")
    regime = classify_field_regime(case["geocentric_distance_re"])
    required_model = select_geomag_model(regime)
    model_ok = case["declared_model"] == required_model
    target_year = case["target_year"]
    epoch_valid = is_within_igrf_validity(target_year)
    base_epoch = nearest_igrf_epoch(target_year)
    delta_years = target_year - base_epoch
    adjusted_b0 = apply_secular_variation(
        case["epoch_b0"], case["secular_variation_rate"], delta_years
    )
    result = {
        "id": case["id"],
        "regime": regime,
        "required_model": required_model,
        "model_ok": model_ok,
        "base_epoch": base_epoch,
        "delta_years": delta_years,
        "epoch_valid": epoch_valid,
        "adjusted_b0": adjusted_b0,
        "compliant": model_ok and epoch_valid,
    }
    if "l_shell" in case:
        result["b_at_l"] = equatorial_field_at_l(case["l_shell"], adjusted_b0)
    return result


def build_geomag_assessment(cases):
    """Assessment record: one assess_geomag_case() result per case,
    in input order. Raises ValueError on a duplicate case id."""
    record = []
    seen_ids = set()
    for case in cases:
        assessment = assess_geomag_case(case)
        if assessment["id"] in seen_ids:
            raise ValueError("duplicate geomagnetic case id: %r" % (assessment["id"],))
        seen_ids.add(assessment["id"])
        record.append(assessment)
    return record


def noncompliant_items(record):
    """Case ids in the record that are not compliant, in record
    order -- these cannot support the geomagnetic field model
    definition as-is."""
    return [entry["id"] for entry in record if not entry["compliant"]]


def all_compliant(record):
    """True when every entry in the assessment record is compliant."""
    return len(noncompliant_items(record)) == 0
