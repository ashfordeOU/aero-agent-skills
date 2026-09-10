#!/usr/bin/env python3
"""ECSS-E-ST-10-04C Annex B.9 Mobius/Directional Intensity Change (DIC)
geomagnetic transmission model (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): a charged
primary reaches a position from a given arrival direction only if its
magnetic rigidity exceeds a geomagnetic cutoff rigidity; the vertical-
incidence Stormer cutoff depends on geomagnetic latitude alone, but the
real cutoff is direction-dependent -- higher for primaries arriving from
local geomagnetic east and lower from local geomagnetic west (the east-west
effect), growing from zero at zenith angle 0 toward its largest magnitude
near the horizon -- and the transition across the cutoff is a penumbra band
of partial transmission rather than a sharp step. This module implements
the vertical cutoff, a Mobius-class directional (DIC) correction, penumbra
transmission-probability classification, spectrum-weighted transmitted
flux, and worst-case-direction selection/compliance; it does not implement
real trajectory tracing or non-dipole field harmonics, and its directional
amplitude and penumbra width are representative engineering approximations,
not a transcription of Annex B.9's own coefficients.
"""

import math

# Present-epoch dipole-approximation Stormer cutoff constant (GV), a
# representative engineering value rather than an epoch-exact transcription.
STORMER_CUTOFF_CONSTANT_GV = 59.6

# Amplitude of the east-west directional correction (dimensionless, must be
# in [0, 1) so the directional factor never reaches zero or goes negative).
DEFAULT_EAST_WEST_AMPLITUDE = 0.5

# Fractional half-width of the penumbra band around the directional cutoff.
DEFAULT_PENUMBRA_FRACTION = 0.1

EAST_AZIMUTH_DEG = 90.0
WEST_AZIMUTH_DEG = 270.0
HORIZON_ZENITH_DEG = 90.0

FORBIDDEN = "forbidden"
PENUMBRA = "penumbra"
ALLOWED = "allowed"


def vertical_cutoff_rigidity_gv(geomagnetic_latitude_deg):
    """Vertical-incidence Stormer-type cutoff rigidity (GV) for a
    geomagnetic latitude: STORMER_CUTOFF_CONSTANT_GV * cos^4(latitude).
    Raises ValueError if latitude is outside [-90, 90]."""
    if not -90.0 <= geomagnetic_latitude_deg <= 90.0:
        raise ValueError("geomagnetic_latitude_deg must be within [-90, 90]")
    cos_lat = math.cos(math.radians(geomagnetic_latitude_deg))
    return STORMER_CUTOFF_CONSTANT_GV * cos_lat**4


def _east_west_factor(zenith_angle_deg, azimuth_from_geomagnetic_north_deg, east_west_amplitude):
    """Dimensionless DIC directional factor: 1 + amplitude * sin(zenith) *
    sin(azimuth), so it equals 1 at zenith 0 (no azimuth dependence), rises
    above 1 toward geomagnetic east, and falls below 1 toward geomagnetic
    west, growing in magnitude toward the horizon."""
    zenith_rad = math.radians(zenith_angle_deg)
    azimuth_rad = math.radians(azimuth_from_geomagnetic_north_deg)
    return 1.0 + east_west_amplitude * math.sin(zenith_rad) * math.sin(azimuth_rad)


def directional_cutoff_rigidity_gv(
    geomagnetic_latitude_deg,
    zenith_angle_deg,
    azimuth_from_geomagnetic_north_deg,
    east_west_amplitude=DEFAULT_EAST_WEST_AMPLITUDE,
):
    """Direction-resolved cutoff rigidity (GV): the vertical cutoff scaled
    by the DIC east-west directional factor for the given zenith angle (deg,
    0 = local vertical, 90 = horizon) and azimuth from geomagnetic north
    (deg, clockwise, east = 90). Raises ValueError for a zenith angle
    outside [0, 90] or an east_west_amplitude outside [0, 1)."""
    if not 0.0 <= zenith_angle_deg <= 90.0:
        raise ValueError("zenith_angle_deg must be within [0, 90]")
    if not 0.0 <= east_west_amplitude < 1.0:
        raise ValueError("east_west_amplitude must be within [0, 1)")
    vertical = vertical_cutoff_rigidity_gv(geomagnetic_latitude_deg)
    factor = _east_west_factor(
        zenith_angle_deg, azimuth_from_geomagnetic_north_deg, east_west_amplitude
    )
    return vertical * factor


def transmission_probability(
    particle_rigidity_gv, cutoff_rigidity_gv, penumbra_fraction=DEFAULT_PENUMBRA_FRACTION
):
    """Transmission probability in [0, 1] for a particle rigidity (GV)
    against a directional cutoff rigidity (GV): 0 at or below the penumbra's
    lower edge, 1 at or above its upper edge, and a linear ramp between,
    where the penumbra spans cutoff * (1 -/+ penumbra_fraction). Raises
    ValueError for a negative rigidity/cutoff or a penumbra_fraction
    outside (0, 1)."""
    if particle_rigidity_gv < 0:
        raise ValueError("particle_rigidity_gv must be >= 0")
    if cutoff_rigidity_gv < 0:
        raise ValueError("cutoff_rigidity_gv must be >= 0")
    if not 0.0 < penumbra_fraction < 1.0:
        raise ValueError("penumbra_fraction must be within (0, 1)")
    lower = cutoff_rigidity_gv * (1.0 - penumbra_fraction)
    upper = cutoff_rigidity_gv * (1.0 + penumbra_fraction)
    if particle_rigidity_gv <= lower:
        return 0.0
    if particle_rigidity_gv >= upper:
        return 1.0
    return (particle_rigidity_gv - lower) / (upper - lower)


def classify_transmission(
    particle_rigidity_gv, cutoff_rigidity_gv, penumbra_fraction=DEFAULT_PENUMBRA_FRACTION
):
    """Transmission category for a particle rigidity against a directional
    cutoff: FORBIDDEN, PENUMBRA, or ALLOWED, from transmission_probability."""
    probability = transmission_probability(
        particle_rigidity_gv, cutoff_rigidity_gv, penumbra_fraction
    )
    if probability <= 0.0:
        return FORBIDDEN
    if probability >= 1.0:
        return ALLOWED
    return PENUMBRA


def directional_intensity_change(
    particle_rigidity_gv,
    geomagnetic_latitude_deg,
    zenith_angle_deg,
    azimuth_from_geomagnetic_north_deg,
    east_west_amplitude=DEFAULT_EAST_WEST_AMPLITUDE,
    penumbra_fraction=DEFAULT_PENUMBRA_FRACTION,
):
    """Full DIC evaluation for one candidate particle rigidity and arrival
    direction: {"cutoff_rigidity_gv": ..., "transmission_probability": ...,
    "category": ...}."""
    cutoff = directional_cutoff_rigidity_gv(
        geomagnetic_latitude_deg,
        zenith_angle_deg,
        azimuth_from_geomagnetic_north_deg,
        east_west_amplitude,
    )
    probability = transmission_probability(particle_rigidity_gv, cutoff, penumbra_fraction)
    category = classify_transmission(particle_rigidity_gv, cutoff, penumbra_fraction)
    return {
        "cutoff_rigidity_gv": cutoff,
        "transmission_probability": probability,
        "category": category,
    }


def transmitted_flux(
    spectrum,
    geomagnetic_latitude_deg,
    zenith_angle_deg,
    azimuth_from_geomagnetic_north_deg,
    east_west_amplitude=DEFAULT_EAST_WEST_AMPLITUDE,
    penumbra_fraction=DEFAULT_PENUMBRA_FRACTION,
):
    """Total transmitted flux for an incident differential rigidity
    spectrum at one arrival direction: sum over spectrum of flux *
    transmission_probability(rigidity). spectrum: iterable of dicts with
    keys "rigidity_gv" and "flux" (both >= 0). Does not mutate spectrum."""
    cutoff = directional_cutoff_rigidity_gv(
        geomagnetic_latitude_deg,
        zenith_angle_deg,
        azimuth_from_geomagnetic_north_deg,
        east_west_amplitude,
    )
    total = 0.0
    for bin_ in spectrum:
        rigidity = bin_["rigidity_gv"]
        flux = bin_["flux"]
        if rigidity < 0:
            raise ValueError("rigidity_gv must be >= 0")
        if flux < 0:
            raise ValueError("flux must be >= 0")
        total += flux * transmission_probability(rigidity, cutoff, penumbra_fraction)
    return total


def worst_case_direction_cutoff(
    geomagnetic_latitude_deg, east_west_amplitude=DEFAULT_EAST_WEST_AMPLITUDE
):
    """The analytic lowest-cutoff (easiest-access, worst-case) arrival
    direction at a geomagnetic latitude under this leaf's DIC model: the
    horizon-grazing, due-geomagnetic-west direction. Returns {"zenith_angle_deg":
    90.0, "azimuth_from_geomagnetic_north_deg": 270.0, "cutoff_rigidity_gv": ...}."""
    cutoff = directional_cutoff_rigidity_gv(
        geomagnetic_latitude_deg,
        HORIZON_ZENITH_DEG,
        WEST_AZIMUTH_DEG,
        east_west_amplitude,
    )
    return {
        "zenith_angle_deg": HORIZON_ZENITH_DEG,
        "azimuth_from_geomagnetic_north_deg": WEST_AZIMUTH_DEG,
        "cutoff_rigidity_gv": cutoff,
    }


def is_worst_case_compliant(case_cutoff_gv, worst_case_cutoff_gv, tolerance_gv=1e-6):
    """True when a case's evaluated directional cutoff is at least as
    conservative as (no higher than) the worst-case direction's cutoff,
    within a small floating-point tolerance."""
    return case_cutoff_gv <= worst_case_cutoff_gv + tolerance_gv


def direction_case_review(case):
    """Full Annex B.9 directional-transmission review for one radiation
    environment case.

    case: {"case_id": str, "geomagnetic_latitude_deg": float,
    "particle_rigidity_gv": float, "zenith_angle_deg": float,
    "azimuth_from_geomagnetic_north_deg": float, "east_west_amplitude":
    float | None, "penumbra_fraction": float | None, "worst_case_required":
    bool}. Returns {"directional_intensity_change": {...}, "worst_case":
    {...}, "findings": [...]}; findings is empty when the case does not
    require worst-case coverage or already meets it."""
    east_west_amplitude = case.get("east_west_amplitude", DEFAULT_EAST_WEST_AMPLITUDE)
    penumbra_fraction = case.get("penumbra_fraction", DEFAULT_PENUMBRA_FRACTION)
    dic = directional_intensity_change(
        case["particle_rigidity_gv"],
        case["geomagnetic_latitude_deg"],
        case["zenith_angle_deg"],
        case["azimuth_from_geomagnetic_north_deg"],
        east_west_amplitude,
        penumbra_fraction,
    )
    worst_case = worst_case_direction_cutoff(
        case["geomagnetic_latitude_deg"], east_west_amplitude
    )
    findings = []
    if case.get("worst_case_required") and not is_worst_case_compliant(
        dic["cutoff_rigidity_gv"], worst_case["cutoff_rigidity_gv"]
    ):
        findings.append(
            {
                "issue": "non_worst_case_direction_used",
                "case": case["case_id"],
                "used_cutoff_gv": dic["cutoff_rigidity_gv"],
                "worst_case_cutoff_gv": worst_case["cutoff_rigidity_gv"],
            }
        )
    return {
        "directional_intensity_change": dic,
        "worst_case": worst_case,
        "findings": findings,
    }


def is_direction_case_compliant(review):
    """True when a direction_case_review result carries no findings."""
    return len(review["findings"]) == 0
