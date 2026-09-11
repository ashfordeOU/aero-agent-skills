#!/usr/bin/env python3
"""ECSS-E-ST-10-11C §4.7.4 architecture complements assessment
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
human factors standard requires that a crewed spacecraft zone provides
four categories of architecture complement — handrails spaced within
a crew-reachable limit, restraints at every designated workstation,
mobility aids forming a continuous translation path, and stowage items
within the anthropometric reach envelope; each category is assessed
independently, and the zone is compliant only when all four are clear.
This module implements complement-type validation, handrail-spacing
checks, workstation-restraint coverage, mobility-path continuity, and
stowage-reach evaluation; it does not define crew population parameters
or compute view factors.
"""

COMPLEMENT_TYPES = frozenset({"handrail", "restraint", "mobility_aid", "stowage"})

RESTRAINT_SUBTYPES = frozenset({"foot_restraint", "body_restraint", "tether_point"})

# Maximum allowed gap between adjacent handrail elements (mm). Derived
# from microgravity-ergonomics population reach data.
HANDRAIL_MAX_SPACING_MM = 500.0

# Maximum allowed single gap in a mobility-aid translation path (mm).
MOBILITY_GAP_MAX_MM = 500.0

# Maximum stowage access distance from the crew reference point (mm).
# Based on seated/restrained functional-reach anthropometric data.
REACH_ENVELOPE_MAX_MM = 710.0


def categorize_complement(complement_type):
    """Architecture complement category: one of 'handrail', 'restraint',
    'mobility_aid', 'stowage'. Raises ValueError for an unrecognized
    type."""
    if complement_type in COMPLEMENT_TYPES:
        return complement_type
    raise ValueError(
        "unrecognized architecture complement type %r under "
        "E-ST-10-11C §4.7.4" % (complement_type,)
    )


def check_handrail_spacing(spacing_mm):
    """True if spacing_mm is at or within the handrail gap limit.
    Raises ValueError for a negative value."""
    if spacing_mm < 0:
        raise ValueError("spacing_mm must be >= 0")
    return spacing_mm <= HANDRAIL_MAX_SPACING_MM


def check_workstation_restraint(restraint_types):
    """True if at least one recognized restraint subtype is present.
    restraint_types: iterable of str. Does not raise on empty input."""
    return any(r in RESTRAINT_SUBTYPES for r in restraint_types)


def check_stowage_reach(distance_mm):
    """True if distance_mm is within the anthropometric reach envelope.
    Raises ValueError for a negative value."""
    if distance_mm < 0:
        raise ValueError("distance_mm must be >= 0")
    return distance_mm <= REACH_ENVELOPE_MAX_MM


def check_mobility_path_continuity(gap_distances_mm):
    """Check that no single gap in a mobility-aid path exceeds the limit.
    gap_distances_mm: iterable of float gap distances between adjacent aids.
    Returns (is_continuous: bool, max_gap_mm: float).
    Raises ValueError if any gap distance is negative."""
    max_gap = 0.0
    for d in gap_distances_mm:
        if d < 0:
            raise ValueError("gap distance must be >= 0")
        if d > max_gap:
            max_gap = d
    return max_gap <= MOBILITY_GAP_MAX_MM, max_gap


def handrail_violations(zone_id, handrail_spacings_mm):
    """Violation list for handrail spacing in a zone.
    handrail_spacings_mm: list of float gap distances between adjacent elements.
    Does not mutate the input list."""
    violations = []
    for i, spacing in enumerate(handrail_spacings_mm):
        if not check_handrail_spacing(spacing):
            violations.append(
                {
                    "issue": "handrail_spacing_exceeds_limit",
                    "zone": zone_id,
                    "gap_index": i,
                    "spacing_mm": spacing,
                    "limit_mm": HANDRAIL_MAX_SPACING_MM,
                }
            )
    return violations


def restraint_violations(workstation_id, restraint_types):
    """Violation list for workstation restraint coverage.
    restraint_types: list of restraint type strings at the workstation."""
    if not check_workstation_restraint(restraint_types):
        return [{"issue": "missing_workstation_restraint", "workstation": workstation_id}]
    return []


def stowage_violations(zone_id, stowage_items):
    """Violation list for stowage reach in a zone.
    stowage_items: list of dicts with 'item_id' (str) and 'distance_mm' (float).
    Does not mutate stowage_items."""
    violations = []
    for item in stowage_items:
        if not check_stowage_reach(item["distance_mm"]):
            violations.append(
                {
                    "issue": "stowage_outside_reach_envelope",
                    "zone": zone_id,
                    "item_id": item["item_id"],
                    "distance_mm": item["distance_mm"],
                    "limit_mm": REACH_ENVELOPE_MAX_MM,
                }
            )
    return violations


def mobility_path_violations(zone_id, gap_distances_mm):
    """Violation list for mobility-aid path continuity in a zone.
    gap_distances_mm: list of float gap distances between adjacent aids."""
    is_continuous, max_gap = check_mobility_path_continuity(gap_distances_mm)
    if not is_continuous:
        return [
            {
                "issue": "mobility_path_gap_exceeds_limit",
                "zone": zone_id,
                "max_gap_mm": max_gap,
                "limit_mm": MOBILITY_GAP_MAX_MM,
            }
        ]
    return []


def arch_complements_review(zone):
    """Full §4.7.4 architecture complements review for one zone.

    zone: {
        "zone_id": str,
        "handrail_spacings_mm": [float, ...],
        "workstations": [{"workstation_id": str, "restraint_types": [str, ...]}, ...],
        "mobility_path_gaps_mm": [float, ...],
        "stowage_items": [{"item_id": str, "distance_mm": float}, ...],
    }
    Returns {"handrail": [...], "restraint": [...], "mobility": [...], "stowage": [...]},
    each a list of violation dicts. Raises ValueError for an unknown complement
    type if one is explicitly validated via categorize_complement."""
    zone_id = zone["zone_id"]

    handrail_v = handrail_violations(zone_id, zone.get("handrail_spacings_mm", []))

    restraint_v = []
    for ws in zone.get("workstations", []):
        restraint_v.extend(
            restraint_violations(ws["workstation_id"], ws.get("restraint_types", []))
        )

    mobility_v = mobility_path_violations(zone_id, zone.get("mobility_path_gaps_mm", []))
    stowage_v = stowage_violations(zone_id, zone.get("stowage_items", []))

    return {
        "handrail": handrail_v,
        "restraint": restraint_v,
        "mobility": mobility_v,
        "stowage": stowage_v,
    }


def is_complements_compliant(review):
    """True when all categories in an arch_complements_review result are
    empty — the zone satisfies §4.7.4 for this assessment."""
    return all(len(v) == 0 for v in review.values())
