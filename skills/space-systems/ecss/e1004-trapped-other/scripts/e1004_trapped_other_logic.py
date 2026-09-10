#!/usr/bin/env python3
"""ECSS-E-ST-10-04C clause 9.2 trapped-radiation environment handling for
non-LEO/GEO/MEO orbits (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): HEO,
GTO, and interplanetary-transfer trajectories sweep through the slot
region, the outer electron belt, and the inner proton belt on every
revolution instead of dwelling in one characteristic band the way a
LEO, MEO, or GEO orbit does, and an interplanetary-transfer trajectory
eventually leaves the magnetosphere -- and the trapped-radiation
population with it -- once it crosses the magnetopause, whose nominal
subsolar standoff distance is on the order of 10 Earth radii,
compressed to roughly 6 Earth radii or less under strong solar-wind
forcing. This module implements orbit-regime categorization, splitting
a trajectory's dwell time into the trapped domain (inside the
magnetopause standoff distance) versus the interplanetary domain
(beyond it), and a required-trapped-species (proton and electron)
coverage check; it does not implement the per-L-shell flux/fluence
table lookup itself, which is the same interpolation problem already
solved by the LEO/MEO/GEO sibling leaves and should be reused per
trapped-domain segment.
"""

EARTH_RADIUS_KM = 6378.0

# Nominal subsolar magnetopause standoff distance, and the
# storm-compressed worst-case distance, in Earth radii.
NOMINAL_MAGNETOPAUSE_STANDOFF_RE = 10.0
COMPRESSED_MAGNETOPAUSE_STANDOFF_RE = 6.0

LEO_MAX_ALT_KM = 2000.0
GEO_BAND_KM = (35586.0, 35986.0)

TRAPPED_DOMAIN = "trapped_domain"
INTERPLANETARY_DOMAIN = "interplanetary_domain"

ORBIT_REGIMES = frozenset({"gto", "heo", "interplanetary_transfer"})
REQUIRED_TRAPPED_SPECIES = frozenset({"proton", "electron"})


def classify_orbit_regime(perigee_alt_km, apogee_alt_km):
    """Orbit regime this leaf covers: "gto", "heo", or
    "interplanetary_transfer". apogee_alt_km may be None for an
    escape/hyperbolic trajectory with no bounded apogee. Raises
    ValueError when perigee/apogee are inconsistent, or when the orbit
    lies wholly within the LEO, MEO, or GEO band already handled by a
    dedicated sibling leaf."""
    if perigee_alt_km < 0:
        raise ValueError("perigee_alt_km must be >= 0")
    if apogee_alt_km is None:
        return "interplanetary_transfer"
    if apogee_alt_km < perigee_alt_km:
        raise ValueError("apogee_alt_km must be >= perigee_alt_km")
    if apogee_alt_km <= LEO_MAX_ALT_KM:
        raise ValueError(
            "orbit lies wholly within LEO; use e1004-trapped-leo"
        )
    if perigee_alt_km > LEO_MAX_ALT_KM and apogee_alt_km < GEO_BAND_KM[0]:
        raise ValueError(
            "orbit lies wholly within MEO; use e1004-meo-meov2"
        )
    if GEO_BAND_KM[0] <= perigee_alt_km and apogee_alt_km <= GEO_BAND_KM[1]:
        raise ValueError(
            "orbit lies wholly within GEO; use the dedicated GEO leaf"
        )
    if perigee_alt_km <= LEO_MAX_ALT_KM and (
        GEO_BAND_KM[0] <= apogee_alt_km <= GEO_BAND_KM[1]
    ):
        return "gto"
    return "heo"


def magnetopause_standoff_km(storm_compressed):
    """Magnetopause standoff distance in km for the chosen solar-wind
    condition: the storm-compressed distance if storm_compressed is
    True, otherwise the nominal subsolar distance."""
    standoff_re = (
        COMPRESSED_MAGNETOPAUSE_STANDOFF_RE
        if storm_compressed
        else NOMINAL_MAGNETOPAUSE_STANDOFF_RE
    )
    return standoff_re * EARTH_RADIUS_KM


def classify_domain(radial_distance_km, storm_compressed=False):
    """Domain for a radial distance from Earth's center: TRAPPED_DOMAIN
    if it is within the magnetopause standoff distance for the chosen
    solar-wind condition, otherwise INTERPLANETARY_DOMAIN. Raises
    ValueError for a negative distance."""
    if radial_distance_km < 0:
        raise ValueError("radial_distance_km must be >= 0")
    if radial_distance_km <= magnetopause_standoff_km(storm_compressed):
        return TRAPPED_DOMAIN
    return INTERPLANETARY_DOMAIN


def split_trajectory_segments(segments, storm_compressed=False):
    """Split trajectory segments into trapped-domain and
    interplanetary-domain groups.

    segments: iterable of dicts with keys "radial_distance_km" and
    "dwell_seconds". Does not mutate segments. Returns
    (trapped_segments, interplanetary_segments), each a list of the
    original segment dicts. Raises ValueError for a negative
    dwell_seconds or radial_distance_km."""
    trapped_segments = []
    interplanetary_segments = []
    for segment in segments:
        dwell_seconds = segment["dwell_seconds"]
        if dwell_seconds < 0:
            raise ValueError("dwell_seconds must be >= 0")
        domain = classify_domain(
            segment["radial_distance_km"], storm_compressed
        )
        if domain == TRAPPED_DOMAIN:
            trapped_segments.append(segment)
        else:
            interplanetary_segments.append(segment)
    return trapped_segments, interplanetary_segments


def required_species_coverage(regime):
    """Trapped species that must be covered wherever trapped-domain
    dwell exists for the given orbit regime. Raises ValueError for a
    regime outside ORBIT_REGIMES."""
    if regime not in ORBIT_REGIMES:
        raise ValueError("unrecognized orbit regime %r" % (regime,))
    return REQUIRED_TRAPPED_SPECIES


def trapped_other_assessment(mission):
    """Full clause 9.2 trapped-environment applicability assessment for
    one mission.

    mission: {"mission_id": str, "perigee_alt_km": float,
    "apogee_alt_km": float | None, "storm_compressed": bool,
    "segments": [{"radial_distance_km": float, "dwell_seconds": float},
    ...], "species_covered": iterable of species strings the analysis
    case actually covers}. Returns a dict with the categorized regime,
    trapped/interplanetary dwell totals, the excluded-segment count,
    and a findings list (empty when the assessment is complete).
    Raises ValueError via classify_orbit_regime when the orbit does not
    belong to this leaf's scope."""
    mission_id = mission["mission_id"]
    regime = classify_orbit_regime(
        mission["perigee_alt_km"], mission["apogee_alt_km"]
    )
    segments = mission.get("segments", [])
    trapped_segments, interplanetary_segments = split_trajectory_segments(
        segments, mission.get("storm_compressed", False)
    )
    trapped_seconds = sum(s["dwell_seconds"] for s in trapped_segments)
    interplanetary_seconds = sum(
        s["dwell_seconds"] for s in interplanetary_segments
    )

    findings = []
    if not segments:
        findings.append(
            {
                "issue": "no_trajectory_segments_supplied",
                "mission": mission_id,
            }
        )
    required = required_species_coverage(regime)
    covered = set(mission.get("species_covered", ()))
    missing = required - covered
    if trapped_seconds > 0 and missing:
        findings.append(
            {
                "issue": "missing_trapped_species_coverage",
                "mission": mission_id,
                "missing_species": sorted(missing),
            }
        )

    return {
        "mission_id": mission_id,
        "regime": regime,
        "trapped_seconds": trapped_seconds,
        "interplanetary_seconds": interplanetary_seconds,
        "excluded_segment_count": len(interplanetary_segments),
        "findings": findings,
    }


def is_trapped_other_compliant(assessment):
    """True when a trapped_other_assessment result carries no open
    findings -- the mission's trapped-environment applicability
    assessment is complete for this leaf's scope."""
    return len(assessment["findings"]) == 0
