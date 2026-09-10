#!/usr/bin/env python3
"""ECSS-E-ST-10-04C Annex B.8 Størmer vertical cutoff rigidity
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): Annex
B.8's dipole-field Størmer theory gives, at a location's geomagnetic
latitude and radial distance from the dipole center, a vertical cutoff
rigidity below which zenith-arriving charged particles are deflected by
the geomagnetic field and cannot reach the location, and at or above
which they penetrate; the cutoff's scale (the Størmer constant) is
proportional to Earth's geomagnetic dipole moment, which itself decays
secularly over time, so the same location's cutoff must carry an epoch
coefficient rather than a single fixed value across a mission's life.
This module implements the epoch-scaled Størmer constant, the vertical
cutoff rigidity formula, per-location and per-orbit penetration
(unshielded-fraction) accounting against an optional budget, and
worst-case-epoch selection; it does not implement off-zenith
(east-west-asymmetric) cutoff directions or full IGRF/offset-dipole
field geometry.
"""

import math

# Størmer constant at the reference epoch (GV), for radial distance in
# Earth radii -- the standard engineering value for Earth's dipole
# moment circa the reference epoch.
STORMER_CONSTANT_REFERENCE_GV = 59.6
REFERENCE_EPOCH_YEAR = 2020

# Fractional change in geomagnetic dipole moment per year, applied to
# the reference-epoch Størmer constant. Representative of the well-
# known secular decay trend (~-5% per century); negative because the
# moment is decreasing.
SECULAR_DECAY_FRACTION_PER_YEAR = -0.0005


def dipole_moment_scale_factor(epoch_year):
    """Dipole moment (and Størmer constant) scale factor relative to
    the reference epoch. Raises ValueError if the epoch is far enough
    from the reference that the scaled moment would be non-physical
    (zero or negative)."""
    scale = 1.0 + SECULAR_DECAY_FRACTION_PER_YEAR * (epoch_year - REFERENCE_EPOCH_YEAR)
    if scale <= 0:
        raise ValueError(
            "epoch_year %r yields a non-physical (<=0) dipole moment "
            "scale factor under the secular decay coefficient" % (epoch_year,)
        )
    return scale


def stormer_constant_gv(epoch_year):
    """Epoch-scaled Størmer constant (GV), for radial distance in Earth
    radii."""
    return STORMER_CONSTANT_REFERENCE_GV * dipole_moment_scale_factor(epoch_year)


def vertical_cutoff_rigidity_gv(geomagnetic_latitude_deg, radial_distance_re, epoch_year):
    """Vertical (zenith-arrival) Størmer cutoff rigidity (GV) at a
    geomagnetic latitude and radial distance (Earth radii) for a given
    epoch: stormer_constant(epoch) * cos^4(latitude) / radial_distance^2.
    Raises ValueError for a latitude outside [-90, 90] or a non-positive
    radial distance."""
    if not -90.0 <= geomagnetic_latitude_deg <= 90.0:
        raise ValueError("geomagnetic_latitude_deg must be within [-90, 90]")
    if radial_distance_re <= 0:
        raise ValueError("radial_distance_re must be > 0")

    c_st = stormer_constant_gv(epoch_year)
    lat_rad = math.radians(geomagnetic_latitude_deg)
    return c_st * math.cos(lat_rad) ** 4 / radial_distance_re**2


def is_penetrating(particle_rigidity_gv, cutoff_rigidity_gv):
    """True when a particle of the given rigidity (GV) is at or above
    the local cutoff rigidity (GV) and therefore penetrates
    (unshielded); False when it is deflected (shielded). Raises
    ValueError for a negative rigidity."""
    if particle_rigidity_gv < 0:
        raise ValueError("particle_rigidity_gv must be >= 0")
    if cutoff_rigidity_gv < 0:
        raise ValueError("cutoff_rigidity_gv must be >= 0")
    return particle_rigidity_gv >= cutoff_rigidity_gv


def orbit_unshielded_fraction(orbit_points, threshold_rigidity_gv, epoch_year):
    """Fraction (0.0-1.0) of equal-time-weighted orbit_points at which a
    particle of threshold_rigidity_gv penetrates the local vertical
    cutoff. orbit_points: iterable of dicts with keys
    "geomagnetic_latitude_deg" and "radial_distance_re". Raises
    ValueError for an empty orbit_points."""
    points = list(orbit_points)
    if not points:
        raise ValueError("orbit_points must be non-empty")

    penetrating = [
        is_penetrating(
            threshold_rigidity_gv,
            vertical_cutoff_rigidity_gv(
                point["geomagnetic_latitude_deg"], point["radial_distance_re"], epoch_year
            ),
        )
        for point in points
    ]
    return sum(penetrating) / len(penetrating)


def geomagnetic_shielding_violations(
    case_id, orbit_points, threshold_rigidity_gv, epoch_year, max_unshielded_fraction
):
    """Violation list (empty if compliant) for the unshielded fraction
    of one orbit/case. max_unshielded_fraction: the case's allowable
    unshielded-time budget, or None if no requirement has been captured
    yet (itself a finding when the unshielded fraction is nonzero)."""
    unshielded_fraction = orbit_unshielded_fraction(orbit_points, threshold_rigidity_gv, epoch_year)
    if max_unshielded_fraction is None:
        if unshielded_fraction > 0:
            return [
                {
                    "issue": "missing_unshielded_fraction_budget",
                    "case": case_id,
                    "unshielded_fraction": unshielded_fraction,
                }
            ]
        return []
    if unshielded_fraction > max_unshielded_fraction:
        return [
            {
                "issue": "unshielded_fraction_exceeded",
                "case": case_id,
                "unshielded_fraction": unshielded_fraction,
                "max_unshielded_fraction": max_unshielded_fraction,
            }
        ]
    return []


def worst_case_epoch_for_shielding(mission_start_year, mission_end_year):
    """The mission epoch (calendar year) giving the most conservative
    (lowest) vertical cutoff rigidity across the mission's lifetime.
    Since the dipole moment's secular trend is monotonic across a
    mission's span, the worst case sits at whichever endpoint the trend
    is moving toward. Raises ValueError if mission_end_year precedes
    mission_start_year."""
    if mission_end_year < mission_start_year:
        raise ValueError("mission_end_year must be >= mission_start_year")
    if SECULAR_DECAY_FRACTION_PER_YEAR < 0:
        return mission_end_year
    return mission_start_year


def stormer_shielding_review(case):
    """Full Annex B.8 geomagnetic-shielding review for one case.

    case: {"case_id": str, "orbit_points": [{"geomagnetic_latitude_deg":
    float, "radial_distance_re": float}, ...], "threshold_rigidity_gv":
    float, "epoch_year": int|float, "max_unshielded_fraction": float |
    None}. Returns the violation list (empty if compliant)."""
    return geomagnetic_shielding_violations(
        case["case_id"],
        case["orbit_points"],
        case["threshold_rigidity_gv"],
        case["epoch_year"],
        case.get("max_unshielded_fraction"),
    )


def is_stormer_shielding_compliant(review):
    """True when a stormer_shielding_review result is empty -- the case
    satisfies Annex B.8 for this assessment."""
    return len(review) == 0
