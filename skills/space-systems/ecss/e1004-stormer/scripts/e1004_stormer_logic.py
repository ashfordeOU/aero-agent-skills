#!/usr/bin/env python3
"""ECSS-E-ST-10-04C clause 9.2.4 + Annex B.8 geomagnetic shielding logic
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): a
planet's internal magnetic field partially shields a point in near-Earth
space from charged-particle radiation (solar energetic particles, SEP,
and galactic cosmic rays, GCR). The dipole-approximation measure of that
shielding is the Stormer vertical cutoff rigidity: the minimum particle
rigidity (momentum per unit charge) able to reach a given point along
the local vertical/zenith direction. A particle whose rigidity is below
the local cutoff is geomagnetically excluded at that point; a particle
at or above the cutoff can arrive. The vertical cutoff is a first-order,
dipole-field, vertical-incidence approximation -- Annex B.8 flags that a
rigorous treatment (accounting for the real, non-dipole field, the
penumbra of allowed/forbidden trajectories near the cutoff, and
off-vertical arrival directions) requires numerical trajectory tracing
(backward integration of candidate particle trajectories through a field
model), not the closed-form formula. This module implements the
closed-form vertical cutoff, the access/exclusion test built on it, and
the orbit-averaged exposure fraction used to scope when the cheaper
vertical-cutoff approximation is sufficient versus when trajectory
tracing is warranted.
"""

import math

STORMER_CONSTANT_GV = 59.6
SHIELDING_METHODS = ("vertical_stormer_cutoff", "trajectory_tracing")


def vertical_cutoff_rigidity(geomagnetic_latitude_deg, radial_distance_re):
    """Stormer vertical cutoff rigidity in GV at a point given its
    geomagnetic latitude (degrees) and radial distance from the dipole
    center in Earth radii: R_c = STORMER_CONSTANT_GV * cos(lat)^4 / r^2.
    Raises ValueError for a latitude outside [-90, 90] or a non-positive
    radial distance."""
    if not (-90.0 <= geomagnetic_latitude_deg <= 90.0):
        raise ValueError("geomagnetic_latitude_deg must be within [-90, 90]")
    if radial_distance_re <= 0:
        raise ValueError("radial_distance_re must be positive")
    lat_rad = math.radians(geomagnetic_latitude_deg)
    cutoff = STORMER_CONSTANT_GV * (math.cos(lat_rad) ** 4) / (radial_distance_re ** 2)
    # Snap float noise at the magnetic poles (cos(90 deg) is not exactly
    # zero in floating point) so a zero-cutoff point is truly reachable
    # by zero-rigidity particles (physically correct: R_c = 0 at the pole).
    return 0.0 if abs(cutoff) < 1e-12 else cutoff


def is_access_allowed(particle_rigidity_gv, cutoff_rigidity_gv):
    """True when a particle of particle_rigidity_gv can reach a point
    whose vertical cutoff rigidity is cutoff_rigidity_gv -- i.e. the
    particle rigidity is at or above the local cutoff. Raises
    ValueError if either rigidity is negative."""
    if particle_rigidity_gv < 0:
        raise ValueError("particle_rigidity_gv must be non-negative")
    if cutoff_rigidity_gv < 0:
        raise ValueError("cutoff_rigidity_gv must be non-negative")
    return particle_rigidity_gv >= cutoff_rigidity_gv


def evaluate_orbit_point(geomagnetic_latitude_deg, radial_distance_re, particle_rigidity_gv):
    """Shielding assessment at one orbit point for a particle of given
    rigidity: the local vertical cutoff and whether the particle is
    allowed to reach the point. Returns a new dict."""
    cutoff = vertical_cutoff_rigidity(geomagnetic_latitude_deg, radial_distance_re)
    return {
        "geomagnetic_latitude_deg": geomagnetic_latitude_deg,
        "radial_distance_re": radial_distance_re,
        "cutoff_rigidity_gv": cutoff,
        "allowed": is_access_allowed(particle_rigidity_gv, cutoff),
    }


def orbit_shielding_profile(track_points, particle_rigidity_gv):
    """Shielding profile over an orbit ground track. track_points is a
    sequence of (geomagnetic_latitude_deg, radial_distance_re) pairs.
    Returns a new dict with the per-point evaluations, the min/max
    cutoff seen along the track, and the fraction of points where the
    particle is allowed to arrive. Raises ValueError if track_points is
    empty."""
    if not track_points:
        raise ValueError("track_points must not be empty")
    points = [
        evaluate_orbit_point(lat, r, particle_rigidity_gv)
        for lat, r in track_points
    ]
    cutoffs = [point["cutoff_rigidity_gv"] for point in points]
    allowed_count = sum(1 for point in points if point["allowed"])
    return {
        "points": points,
        "min_cutoff_rigidity_gv": min(cutoffs),
        "max_cutoff_rigidity_gv": max(cutoffs),
        "fraction_exposed": allowed_count / len(points),
    }


def attenuated_flux(unshielded_flux, particle_rigidity_gv, cutoff_rigidity_gv):
    """Local flux after applying the vertical-cutoff step-function
    shielding model: unshielded_flux if the particle rigidity is at or
    above cutoff_rigidity_gv, otherwise 0.0. Raises ValueError for a
    negative unshielded_flux."""
    if unshielded_flux < 0:
        raise ValueError("unshielded_flux must be non-negative")
    if is_access_allowed(particle_rigidity_gv, cutoff_rigidity_gv):
        return unshielded_flux
    return 0.0


def select_shielding_method(needs_penumbra_resolution, needs_off_vertical_directions):
    """Method to use per Annex B.8: trajectory_tracing when either the
    penumbra (band of allowed/forbidden trajectories straddling the
    vertical cutoff) must be resolved or particle arrival directions
    other than local vertical/zenith matter (e.g. detailed SEE
    worst-case or dose mapping); otherwise the cheaper
    vertical_stormer_cutoff approximation is sufficient."""
    if needs_penumbra_resolution or needs_off_vertical_directions:
        return "trajectory_tracing"
    return "vertical_stormer_cutoff"


def verify_shielding_assessment(method, profile, particle_rigidity_gv):
    """Overall verification of a geomagnetic-shielding assessment.
    Requires: method is one of SHIELDING_METHODS, particle_rigidity_gv
    is positive, and profile (as returned by orbit_shielding_profile)
    is internally consistent (fraction_exposed matches the recorded
    points). Returns a new dict; raises ValueError for an unknown
    method or non-positive particle_rigidity_gv."""
    if method not in SHIELDING_METHODS:
        raise ValueError("unknown shielding method: %r" % (method,))
    if particle_rigidity_gv <= 0:
        raise ValueError("particle_rigidity_gv must be positive")
    points = profile["points"]
    recomputed_fraction = sum(1 for point in points if point["allowed"]) / len(points)
    fraction_consistent = recomputed_fraction == profile["fraction_exposed"]
    return {
        "method": method,
        "fraction_consistent": fraction_consistent,
        "fully_shielded": profile["fraction_exposed"] == 0.0,
        "fully_exposed": profile["fraction_exposed"] == 1.0,
        "passed": fraction_consistent,
    }
