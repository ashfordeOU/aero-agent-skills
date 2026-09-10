#!/usr/bin/env python3
"""ECSS-E-ST-10-04C clause 6.2 -- natural electromagnetic radiation
environment: solar spectrum bands, total solar irradiance (TSI), and
the planetary contribution (albedo + IR) (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
solar EM spectrum is split into bands by wavelength (XUV, EUV, UV,
visible, IR) plus solar radio emission, each with a reference
irradiance from the standard's reference index tables. TSI is defined
at a 1 AU reference distance and scales with heliocentric distance by
the inverse-square law. The planetary contribution to the incident EM
flux is reflected sunlight (TSI times the body's albedo coefficient)
plus the body's own infrared emission.

This module scopes only the workflow around assembling and validating
the EM radiation environment: spectrum band well-formedness, TSI
distance-scaling, and combining the planetary albedo/IR contributions.
The reference index values themselves (band irradiances, activity
indices) are out of scope here and are supplied by the caller, sourced
from the dedicated reference-index leaves (siblings e1004-indices,
e1004-ref-indices).
"""

REFERENCE_TSI_W_M2 = 1361.0


def validate_distance_au(distance_au):
    """Raise ValueError unless distance_au > 0."""
    if distance_au <= 0:
        raise ValueError("distance_au must be > 0: %r" % (distance_au,))


def validate_albedo(albedo):
    """Raise ValueError unless 0 <= albedo <= 1."""
    if not (0 <= albedo <= 1):
        raise ValueError("albedo must be in [0, 1]: %r" % (albedo,))


def validate_band(band):
    """Raise ValueError unless band is a dict with a non-empty name,
    0 <= wavelength_min_nm < wavelength_max_nm, and a non-negative
    irradiance_w_m2."""
    name = band.get("name")
    wavelength_min_nm = band.get("wavelength_min_nm")
    wavelength_max_nm = band.get("wavelength_max_nm")
    irradiance_w_m2 = band.get("irradiance_w_m2")

    if not name:
        raise ValueError("band must have a non-empty name: %r" % (band,))
    if wavelength_min_nm is None or wavelength_min_nm < 0:
        raise ValueError(
            "band %r wavelength_min_nm must be >= 0: %r" % (name, wavelength_min_nm)
        )
    if wavelength_max_nm is None or wavelength_max_nm <= wavelength_min_nm:
        raise ValueError(
            "band %r wavelength_max_nm must be > wavelength_min_nm: %r > %r"
            % (name, wavelength_max_nm, wavelength_min_nm)
        )
    if irradiance_w_m2 is None or irradiance_w_m2 < 0:
        raise ValueError(
            "band %r irradiance_w_m2 must be >= 0: %r" % (name, irradiance_w_m2)
        )


def check_spectrum_band_order(spectrum_bands):
    """Validate each band in spectrum_bands (a non-empty iterable of
    band dicts, each with name, wavelength_min_nm, wavelength_max_nm,
    irradiance_w_m2) and check the bands, taken in the given order,
    are ascending by wavelength_min_nm with no overlap between
    consecutive bands. Returns a new dict with the bands (unchanged
    order), an order_violations list of (prior, next) pairs where
    wavelength_min_nm decreases, and an overlap_violations list of
    (prior, next) pairs where the prior band's wavelength_max_nm
    exceeds the next band's wavelength_min_nm. Raises ValueError if
    spectrum_bands is empty or any band is malformed."""
    bands = list(spectrum_bands)
    if not bands:
        raise ValueError("spectrum_bands must be non-empty")

    for band in bands:
        validate_band(band)

    order_violations = []
    overlap_violations = []
    for prior, nxt in zip(bands, bands[1:]):
        if nxt["wavelength_min_nm"] < prior["wavelength_min_nm"]:
            order_violations.append((prior, nxt))
        if prior["wavelength_max_nm"] > nxt["wavelength_min_nm"]:
            overlap_violations.append((prior, nxt))

    return {
        "bands": bands,
        "order_violations": order_violations,
        "overlap_violations": overlap_violations,
    }


def compute_tsi_at_distance(distance_au, reference_tsi_w_m2=REFERENCE_TSI_W_M2):
    """Compute TSI at distance_au using the inverse-square law from
    reference_tsi_w_m2 at 1 AU. Raises ValueError unless distance_au > 0
    and reference_tsi_w_m2 > 0."""
    validate_distance_au(distance_au)
    if reference_tsi_w_m2 <= 0:
        raise ValueError(
            "reference_tsi_w_m2 must be > 0: %r" % (reference_tsi_w_m2,)
        )
    return reference_tsi_w_m2 / (distance_au ** 2)


def check_tsi_distance_monotonicity(
    distances_au, reference_tsi_w_m2=REFERENCE_TSI_W_M2
):
    """For a non-empty iterable distances_au, compute TSI at each
    distance and check TSI does not increase as distance increases.
    Returns a new dict with the sorted (distance_au, tsi_w_m2) pairs
    and a monotonic bool. Raises ValueError if distances_au is
    empty."""
    distances = sorted(set(distances_au))
    if not distances:
        raise ValueError("distances_au must be non-empty")

    pairs = [
        (distance, compute_tsi_at_distance(distance, reference_tsi_w_m2))
        for distance in distances
    ]

    monotonic = all(pairs[i][1] >= pairs[i + 1][1] for i in range(len(pairs) - 1))

    return {
        "reference_tsi_w_m2": reference_tsi_w_m2,
        "pairs": pairs,
        "monotonic": monotonic,
    }


def compute_planetary_reflected_flux(incident_tsi_w_m2, albedo):
    """Compute the reflected (albedo) flux: incident_tsi_w_m2 *
    albedo. Raises ValueError unless incident_tsi_w_m2 >= 0 and albedo
    is in [0, 1]."""
    if incident_tsi_w_m2 < 0:
        raise ValueError(
            "incident_tsi_w_m2 must be >= 0: %r" % (incident_tsi_w_m2,)
        )
    validate_albedo(albedo)
    return incident_tsi_w_m2 * albedo


def compute_planetary_total_flux(incident_tsi_w_m2, albedo, planetary_ir_w_m2):
    """Combine the reflected (albedo) flux and the body's own infrared
    emission into the total planetary contribution. Returns a new dict
    with reflected_flux_w_m2, planetary_ir_w_m2, and total_w_m2. Raises
    ValueError unless planetary_ir_w_m2 >= 0 (incident_tsi_w_m2 and
    albedo are validated by compute_planetary_reflected_flux)."""
    if planetary_ir_w_m2 < 0:
        raise ValueError(
            "planetary_ir_w_m2 must be >= 0: %r" % (planetary_ir_w_m2,)
        )
    reflected_flux_w_m2 = compute_planetary_reflected_flux(incident_tsi_w_m2, albedo)
    return {
        "reflected_flux_w_m2": reflected_flux_w_m2,
        "planetary_ir_w_m2": planetary_ir_w_m2,
        "total_w_m2": reflected_flux_w_m2 + planetary_ir_w_m2,
    }


def em_radiation_environment_specification(
    spectrum_bands,
    distance_au,
    albedo,
    planetary_ir_w_m2,
    reference_tsi_w_m2=REFERENCE_TSI_W_M2,
):
    """Assemble the EM radiation environment entry for the mission
    specification: the validated spectrum band report, TSI at
    distance_au, and the planetary reflected/IR contribution at that
    distance. Returns a new dict with a verified bool that is True only
    when the spectrum band report has no order or overlap violations."""
    band_report = check_spectrum_band_order(spectrum_bands)
    tsi_w_m2 = compute_tsi_at_distance(distance_au, reference_tsi_w_m2)
    planetary = compute_planetary_total_flux(tsi_w_m2, albedo, planetary_ir_w_m2)
    verified = not band_report["order_violations"] and not band_report[
        "overlap_violations"
    ]

    return {
        "distance_au": distance_au,
        "tsi_w_m2": tsi_w_m2,
        "band_report": band_report,
        "planetary": planetary,
        "verified": verified,
    }
