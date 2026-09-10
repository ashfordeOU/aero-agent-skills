#!/usr/bin/env python3
"""ECSS-E-ST-10-04C clause 9.2.7 L2 / deep magnetotail radiation
environment definition logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
spacecraft at the Sun-Earth L2 point and in the deep magnetotail spend
their time far beyond Earth's trapped radiation belts, so the
long-term trapped-electron/proton belt models (AE/AP-family,
IGE-2006, MEOv2, MOBE-DIC) do not apply there and no geomagnetic
cutoff (Størmer) shielding is available. The baseline environment for
these locations is the unshielded galactic-cosmic-ray spectrum and the
unshielded solar-energetic-particle environment (proton fluence, peak
flux, heavy-ion spectrum), owned by the sibling leaves e1004-gcr,
e1004-sep-fluence, e1004-sep-peakflux, e1004-sep-direction, and
contrasted with the LEO cutoff treatment in e1004-stormer. A halo or
Lissajous orbit around L2 can still carry the spacecraft through the
magnetotail's plasma sheet and lobes for parts of each orbit; those
crossings add a transient plasma-sheet energetic-electron population
relevant to surface charging, tracked separately from the deep-space
GCR/SEP dose baseline. Reference: ECSS-E-ST-10-04C clause 9.2.7, with
Annex I particle-radiation background.
"""

TRAPPED_BELT_OUTER_BOUNDARY_RE = 10.0

DEEP_SPACE_COMPONENTS = ("gcr_unshielded", "sep_proton_unshielded", "sep_heavy_ion_unshielded")
MAGNETOTAIL_CHARGING_COMPONENT = "plasma_sheet_energetic_electrons"

REGIONS = ("l2_deep_space", "magnetotail_lobe", "magnetotail_plasma_sheet")


def trapped_belt_applies(distance_re):
    """True when distance_re (Earth radii from Earth center) is inside
    the trapped-belt boundary, meaning trapped-belt models (AE/AP,
    IGE-2006, MEOv2, MOBE-DIC) still apply and this leaf's unshielded
    deep-space baseline is not yet appropriate. Raises ValueError for a
    negative distance."""
    if distance_re < 0:
        raise ValueError("distance_re must be non-negative")
    return distance_re < TRAPPED_BELT_OUTER_BOUNDARY_RE


def classify_segment(distance_re, plasma_sheet_crossing, lobe_crossing):
    """Region classification for one mission-timeline segment. A
    plasma-sheet crossing takes precedence over a lobe crossing when
    both are flagged; otherwise the segment is plain L2/deep-space.
    Raises ValueError if a magnetotail crossing is flagged while the
    segment is still inside the trapped-belt boundary -- magnetotail
    crossings are a beyond-the-belts phenomenon in this leaf's scope."""
    if trapped_belt_applies(distance_re) and (plasma_sheet_crossing or lobe_crossing):
        raise ValueError("magnetotail crossing flagged inside the trapped-belt boundary")
    if plasma_sheet_crossing:
        return "magnetotail_plasma_sheet"
    if lobe_crossing:
        return "magnetotail_lobe"
    return "l2_deep_space"


def required_components(region):
    """Radiation/plasma components required for a region's environment
    definition. L2 deep-space and magnetotail-lobe segments require
    the unshielded GCR + SEP deep-space baseline; the plasma sheet
    additionally requires the transient energetic-electron charging
    component. Raises ValueError for an unknown region."""
    if region not in REGIONS:
        raise ValueError("unknown region: %r" % (region,))
    if region == "magnetotail_plasma_sheet":
        return DEEP_SPACE_COMPONENTS + (MAGNETOTAIL_CHARGING_COMPONENT,)
    return DEEP_SPACE_COMPONENTS


def geomagnetic_shielding_applies(region):
    """False for every L2/deep-magnetotail region: none of them sit
    inside the geomagnetic-cutoff (Størmer) shielded zone used for
    LEO, so the full unshielded GCR and SEP spectra apply. Raises
    ValueError for an unknown region."""
    if region not in REGIONS:
        raise ValueError("unknown region: %r" % (region,))
    return False


def build_environment_definition(segments):
    """Radiation environment definition for a mission timeline built
    from segments, each a dict with distance_re, plasma_sheet_crossing,
    lobe_crossing. Returns a new dict: per-segment region/components/
    shielding, the union of required components across the timeline,
    and whether a magnetotail charging supplement is needed anywhere.
    Raises ValueError if segments is empty."""
    if not segments:
        raise ValueError("segments must not be empty")
    segment_results = []
    all_components = set()
    for segment in segments:
        region = classify_segment(
            segment["distance_re"],
            segment["plasma_sheet_crossing"],
            segment["lobe_crossing"],
        )
        components = required_components(region)
        all_components.update(components)
        segment_results.append({
            "region": region,
            "components": components,
            "geomagnetic_shielding": geomagnetic_shielding_applies(region),
        })
    return {
        "segments": segment_results,
        "components_required": tuple(sorted(all_components)),
        "needs_magnetotail_charging_supplement": MAGNETOTAIL_CHARGING_COMPONENT in all_components,
    }


def verify_definition_complete(definition):
    """True when every segment in a built definition carries its full
    required-components set as a subset of components_required, and no
    segment claims geomagnetic shielding (L2/deep-magnetotail never
    uses geomagnetic shielding)."""
    for segment in definition["segments"]:
        if segment["geomagnetic_shielding"]:
            return False
        if not set(segment["components"]).issubset(set(definition["components_required"])):
            return False
    return True
