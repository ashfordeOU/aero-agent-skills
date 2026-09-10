"""Deterministic checks for the ECSS-E-ST-10-04C clause 8.2 plasma
environment definition: per-orbit-segment region applicability and
region-entry completeness (model, electron/ion density and
temperature) for spacecraft charging analysis.

Stdlib only, offline, no external dependencies.
"""

from __future__ import annotations

BASE_REQUIRED_REGIONS = {
    "leo": {"ionosphere"},
    "meo": {"plasmasphere"},
    "geo": {"plasmasphere", "outer_magnetosphere"},
    "gto": {"plasmasphere", "outer_magnetosphere", "magnetosheath"},
    "heo": {"plasmasphere", "outer_magnetosphere", "magnetosheath"},
    "l2": {"magnetotail_l2", "solar_wind"},
    "deep_tail": {"magnetotail_l2"},
    "interplanetary": {"solar_wind"},
    "planetary": {"planetary"},
}

WORST_CASE_REGIONS = {"outer_magnetosphere", "auroral"}

DENSITY_TEMPERATURE_FIELDS = (
    "electron_density",
    "electron_temperature",
    "ion_density",
    "ion_temperature",
)


def applicable_regions(regime, polar=False, has_plasma_sources=False):
    """Return the set of plasma regions applicable to an orbit
    segment given its regime, whether it is polar/high-latitude LEO,
    and whether the spacecraft carries an onboard plasma source."""
    if regime not in BASE_REQUIRED_REGIONS:
        raise ValueError(f"unknown orbit regime: {regime!r}")
    regions = set(BASE_REQUIRED_REGIONS[regime])
    if regime == "leo" and polar:
        regions.add("auroral")
    if has_plasma_sources:
        regions.add("induced")
    return regions


def assess_region_entry(entry, region=None):
    """Return a list of issue strings for a single region entry
    (dict with model / electron_density / electron_temperature /
    ion_density / ion_temperature keys); empty list means the entry
    is complete. If region is a worst-case region and the entry's
    basis is "long_term_average", flag it as understating risk."""
    issues = []
    if not entry.get("model"):
        issues.append("missing model")
    for field in DENSITY_TEMPERATURE_FIELDS:
        value = entry.get(field)
        if value is None or value <= 0:
            issues.append(f"missing or invalid {field}")
    if (
        region in WORST_CASE_REGIONS
        and entry.get("basis") == "long_term_average"
    ):
        issues.append(
            f"{region} entry uses long-term-average basis instead of "
            "worst-case"
        )
    return issues


def assess_orbit_segment(segment):
    """Assess one orbit segment dict:
    {"regime": str, "polar": bool, "has_plasma_sources": bool,
     "regions": {name: {"model", "electron_density",
     "electron_temperature", "ion_density", "ion_temperature",
     "basis"}}}
    Returns a result dict with required/missing regions, per-region
    issues, and an overall completeness flag."""
    regime = segment.get("regime")
    polar = bool(segment.get("polar", False))
    has_plasma_sources = bool(segment.get("has_plasma_sources", False))
    required = applicable_regions(regime, polar, has_plasma_sources)
    present = segment.get("regions", {})

    missing = sorted(required - set(present.keys()))
    region_issues = {}
    for name in sorted(required & set(present.keys())):
        issues = assess_region_entry(present[name], region=name)
        if issues:
            region_issues[name] = issues

    complete = not missing and not region_issues
    return {
        "regime": regime,
        "required_regions": sorted(required),
        "missing_regions": missing,
        "region_issues": region_issues,
        "complete": complete,
    }


def assess_plasma_environment(segments):
    """Assess the full charging-environment definition across all of
    the mission's orbit segments. Returns per-segment results and an
    overall completeness flag."""
    if not segments:
        raise ValueError("plasma environment must define at least one orbit segment")

    segment_results = [assess_orbit_segment(seg) for seg in segments]
    complete = all(r["complete"] for r in segment_results)
    return {
        "segment_results": segment_results,
        "complete": complete,
    }
