"""Deterministic checks for the ECSS-E-ST-10-04C clause 9.3 radiation
environment specification (RES): per-orbit-segment component
applicability, component-entry completeness, and RES-level roll-up.

Stdlib only, offline, no external dependencies.
"""

from __future__ import annotations

REQUIRED_RES_SECTIONS = (
    "mission_and_orbit_definition",
    "environment_components_addressed",
    "model_selection_and_justification",
    "per_orbit_segment_data",
    "uncertainty_discussion",
    "worst_case_vs_average_basis",
    "references",
)

VALID_BASES = ("long_term_average", "worst_case", "fluence", "spectrum")

BASE_REQUIRED_COMPONENTS = {
    "leo": {"trapped_radiation", "gcr", "neutron_albedo"},
    "meo": {"trapped_radiation", "gcr", "sep", "internal_charging"},
    "geo": {"trapped_radiation", "gcr", "sep", "internal_charging"},
    "gto": {"trapped_radiation", "gcr", "sep", "internal_charging"},
    "heo": {"trapped_radiation", "gcr", "sep", "internal_charging"},
    "l2": {"gcr", "sep"},
    "deep_tail": {"gcr", "sep"},
    "interplanetary": {"gcr", "sep"},
}

WORST_CASE_PROTON_REGIMES = {"meo", "geo", "gto", "heo"}
LONG_MISSION_YEARS_THRESHOLD = 5.0


def required_components(regime, polar=False, mission_duration_years=0.0):
    """Return the set of radiation components applicable to an orbit
    segment given its regime, whether it is polar/high-inclination
    LEO, and the mission duration relevant to that segment."""
    if regime not in BASE_REQUIRED_COMPONENTS:
        raise ValueError(f"unknown orbit regime: {regime!r}")
    components = set(BASE_REQUIRED_COMPONENTS[regime])
    if regime == "leo" and polar:
        components.add("sep")
    if (
        regime in WORST_CASE_PROTON_REGIMES
        and mission_duration_years >= LONG_MISSION_YEARS_THRESHOLD
    ):
        components.add("trapped_proton_worst_case")
    return components


def assess_component_entry(entry):
    """Return a list of issue strings for a single component entry
    (dict with model / basis / uncertainty keys); empty list means
    the entry is complete."""
    issues = []
    if not entry.get("model"):
        issues.append("missing model")
    if entry.get("basis") not in VALID_BASES:
        issues.append("missing or invalid basis")
    if not entry.get("uncertainty"):
        issues.append("missing uncertainty statement")
    return issues


def assess_orbit_segment(segment):
    """Assess one orbit segment dict:
    {"regime": str, "polar": bool, "mission_duration_years": float,
     "components": {name: {"model", "basis", "uncertainty"}}}
    Returns a result dict with required/missing components, per-
    component issues, and an overall completeness flag."""
    regime = segment.get("regime")
    polar = bool(segment.get("polar", False))
    duration = float(segment.get("mission_duration_years", 0.0))
    required = required_components(regime, polar, duration)
    present = segment.get("components", {})

    missing = sorted(required - set(present.keys()))
    component_issues = {}
    for name in sorted(required & set(present.keys())):
        issues = assess_component_entry(present[name])
        if issues:
            component_issues[name] = issues

    complete = not missing and not component_issues
    return {
        "regime": regime,
        "required_components": sorted(required),
        "missing_components": missing,
        "component_issues": component_issues,
        "complete": complete,
    }


def assess_res(res):
    """Assess a full RES dict:
    {"sections_present": [str, ...], "orbit_segments": [segment, ...]}
    Returns missing top-level sections, per-segment results, and an
    overall completeness flag."""
    segments = res.get("orbit_segments", [])
    if not segments:
        raise ValueError("RES must define at least one orbit segment")

    sections_present = set(res.get("sections_present", []))
    missing_sections = sorted(set(REQUIRED_RES_SECTIONS) - sections_present)

    segment_results = [assess_orbit_segment(seg) for seg in segments]
    complete = not missing_sections and all(
        r["complete"] for r in segment_results
    )
    return {
        "missing_sections": missing_sections,
        "segment_results": segment_results,
        "complete": complete,
    }
