#!/usr/bin/env python3
"""ECSS-E-ST-10-04C clause 11.2 on-orbit contamination assessment
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
space environment specification's contamination clause splits sources
into molecular (outgassing, venting, propulsion effluent, leaks -- a
thin-film deposit) and particulate (debris, MLI fragments, handling
residue, paint flakes -- discrete-particle deposit); molecular sources
reach a surface by direct line-of-sight or, in the LEO ram/wake
region, by ambient-scattered return flux at reduced efficiency; and
each sensitive surface carries a contamination-control requirement
(molecular deposition budget, particulate cleanliness level) linked to
the ECSS-Q-ST-70-01 cleanliness and contamination control policy. This
module implements source classification, molecular transport-path
selection, molecular deposition accounting against a surface budget,
and the particulate cleanliness-level linkage check; it does not
define the Q-ST-70-01 cleanliness levels themselves or the mechanical/
venting particulate transport model.
"""

MOLECULAR_SOURCE_TYPES = frozenset(
    {"outgassing", "venting", "propulsion_effluent", "leak"}
)
PARTICULATE_SOURCE_TYPES = frozenset(
    {"debris", "mli_fragment", "handling_residue", "paint_flake"}
)

# Transport efficiency applied to a molecular source's rate before it is
# counted as deposition. Direct line-of-sight is unobstructed (1.0);
# ambient-scattered return flux in the LEO ram/wake region deposits at a
# markedly reduced efficiency.
TRANSPORT_EFFICIENCY = {
    "direct_line_of_sight": 1.0,
    "return_flux": 0.1,
}

NO_TRANSPORT_PATH = "no_transport_path"


def classify_source(source_type):
    """Contamination family for a source type: "molecular" or
    "particulate". Raises ValueError for a source type outside both
    known sets."""
    if source_type in MOLECULAR_SOURCE_TYPES:
        return "molecular"
    if source_type in PARTICULATE_SOURCE_TYPES:
        return "particulate"
    raise ValueError(
        "unrecognized contamination source type %r under "
        "E-ST-10-04C clause 11.2" % (source_type,)
    )


def molecular_transport_path(has_line_of_sight, in_leo_ram_wake_region):
    """Transport path from a molecular source to a surface:
    "direct_line_of_sight" if the source has an unobstructed view
    factor to the surface, "return_flux" if it instead sits in the
    LEO ram/wake region, otherwise NO_TRANSPORT_PATH (the source does
    not reach the surface)."""
    if has_line_of_sight:
        return "direct_line_of_sight"
    if in_leo_ram_wake_region:
        return "return_flux"
    return NO_TRANSPORT_PATH


def molecular_deposition(source_rate_ng_cm2_s, transport_path, exposure_duration_s):
    """Deposited molecular mass (ng/cm^2) for one source-surface pair:
    source_rate_ng_cm2_s x transport efficiency x exposure_duration_s.
    Returns 0.0 for NO_TRANSPORT_PATH. Raises ValueError for a negative
    rate or duration, or an unrecognized transport path."""
    if source_rate_ng_cm2_s < 0:
        raise ValueError("source_rate_ng_cm2_s must be >= 0")
    if exposure_duration_s < 0:
        raise ValueError("exposure_duration_s must be >= 0")
    if transport_path == NO_TRANSPORT_PATH:
        return 0.0
    if transport_path not in TRANSPORT_EFFICIENCY:
        raise ValueError("unrecognized transport path %r" % (transport_path,))
    efficiency = TRANSPORT_EFFICIENCY[transport_path]
    return source_rate_ng_cm2_s * efficiency * exposure_duration_s


def molecular_budget_violations(surface_id, molecular_sources, allowable_budget_ng_cm2):
    """Violation list (empty if compliant) for the molecular deposition
    on one surface. molecular_sources: iterable of dicts with keys
    "source_rate_ng_cm2_s", "transport_path", "exposure_duration_s".
    allowable_budget_ng_cm2: the surface's Q-ST-70-01-linked budget, or
    None if no requirement has been captured yet (itself a finding).
    Does not mutate molecular_sources."""
    total = sum(
        molecular_deposition(
            source["source_rate_ng_cm2_s"],
            source["transport_path"],
            source["exposure_duration_s"],
        )
        for source in molecular_sources
    )
    if allowable_budget_ng_cm2 is None:
        if total > 0:
            return [
                {
                    "issue": "missing_molecular_budget_q_st_70_01",
                    "surface": surface_id,
                    "total_ng_cm2": total,
                }
            ]
        return []
    if total > allowable_budget_ng_cm2:
        return [
            {
                "issue": "molecular_deposition_budget_exceeded",
                "surface": surface_id,
                "total_ng_cm2": total,
                "budget_ng_cm2": allowable_budget_ng_cm2,
            }
        ]
    return []


def particulate_control_violations(surface_id, has_particulate_sources, cleanliness_level):
    """Violation list (empty if compliant) for particulate control on
    one surface. A surface with particulate-generating sources in view
    (has_particulate_sources True) must carry a Q-ST-70-01-linked
    cleanliness_level (any non-empty value); its absence is flagged."""
    if has_particulate_sources and not cleanliness_level:
        return [
            {
                "issue": "missing_cleanliness_level_q_st_70_01",
                "surface": surface_id,
            }
        ]
    return []


def contamination_review(surface):
    """Full clause 11.2 contamination review for one surface.

    surface: {"surface_id": str, "sources": [{"source_type": str, ...
    molecular fields or particulate marker}], "allowable_budget_ng_cm2":
    float | None, "cleanliness_level": str | None}. Each source dict
    for a molecular source_type must also carry "transport_path" (see
    molecular_transport_path) and the fields required by
    molecular_deposition. Returns {"molecular": [...], "particulate":
    [...]}, each a violation list. Raises ValueError for an
    unrecognized source_type."""
    surface_id = surface["surface_id"]
    molecular_sources = []
    has_particulate_sources = False
    for source in surface.get("sources", []):
        category = classify_source(source["source_type"])
        if category == "molecular":
            molecular_sources.append(source)
        else:
            has_particulate_sources = True
    return {
        "molecular": molecular_budget_violations(
            surface_id, molecular_sources, surface.get("allowable_budget_ng_cm2")
        ),
        "particulate": particulate_control_violations(
            surface_id, has_particulate_sources, surface.get("cleanliness_level")
        ),
    }


def is_contamination_compliant(review):
    """True when both categories in a contamination_review result are
    empty -- the surface satisfies clause 11.2 for this assessment."""
    return all(len(violations) == 0 for violations in review.values())
