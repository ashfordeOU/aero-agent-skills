"""
Deterministic engineering logic for ECSS-E-ST-32C clauses 4.3.10-4.3.12:
electrical conductivity (bonding resistance), lightning protection zone
assignments and provisions, and EMC structural bonding and aperture controls.

No external dependencies — stdlib only.
"""

# Bond resistance limits (ohms) — clause 4.3.10
PRIMARY_BOND_LIMIT_OHMS = 2.5e-3    # primary load-bearing structural joints
SECONDARY_BOND_LIMIT_OHMS = 10.0e-3 # secondary structural joints

# EMC bonding resistance limit (ohms) — clause 4.3.12
EMC_BOND_LIMIT_OHMS = 2.5e-3

# Lightning protection zone definitions — clause 4.3.11
# Maps zone identifier to the set of provisions required on a surface in that zone.
_ZONE_PROVISIONS = {
    "1A": {"strike_receptor", "down_conductor", "diverter_strip"},
    "1B": {"strike_receptor", "down_conductor"},
    "2A": {"down_conductor", "diverter_strip"},
    "2B": {"diverter_strip"},
    "3":  set(),
}

VALID_LIGHTNING_ZONES = set(_ZONE_PROVISIONS.keys())

# Aperture screening parameters — clause 4.3.12
APERTURE_SCREEN_THRESHOLD_MM = 30.0  # apertures wider than this require a screen
SCREEN_MESH_LIMIT_MM = 3.0           # screen mesh opening must not exceed this


# ---------------------------------------------------------------------------
# Electrical conductivity — clause 4.3.10
# ---------------------------------------------------------------------------

def check_bond_resistance(joint_id, resistance_ohms, structure_class):
    """
    Verify that a structural joint's bonding resistance is within the limit
    for its structure class.

    structure_class: 'primary' or 'secondary'

    Returns a dict:
        joint_id        — as supplied
        structure_class — as supplied
        resistance_ohms — as supplied
        limit_ohms      — the applicable limit
        compliant       — True if resistance_ohms <= limit_ohms
        margin_ohms     — limit_ohms - resistance_ohms (negative means exceedance)
    """
    if structure_class == "primary":
        limit = PRIMARY_BOND_LIMIT_OHMS
    elif structure_class == "secondary":
        limit = SECONDARY_BOND_LIMIT_OHMS
    else:
        raise ValueError(
            f"Unknown structure_class '{structure_class}'; must be 'primary' or 'secondary'."
        )

    margin = limit - resistance_ohms
    return {
        "joint_id": joint_id,
        "structure_class": structure_class,
        "resistance_ohms": resistance_ohms,
        "limit_ohms": limit,
        "compliant": resistance_ohms <= limit,
        "margin_ohms": margin,
    }


def categorize_joints(joint_results):
    """
    Separate a list of check_bond_resistance results into compliant and
    non-compliant groups.

    Returns: {"compliant": [...], "non_compliant": [...]}
    """
    groups = {"compliant": [], "non_compliant": []}
    for result in joint_results:
        if result["compliant"]:
            groups["compliant"].append(result)
        else:
            groups["non_compliant"].append(result)
    return groups


# ---------------------------------------------------------------------------
# Lightning protection — clause 4.3.11
# ---------------------------------------------------------------------------

def check_lightning_zone_assignment(surfaces):
    """
    Verify that every external surface has a lightning protection zone assigned.

    surfaces: list of dicts, each with:
        id            — surface identifier (str)
        is_external   — True if the surface is externally exposed (bool)
        lightning_zone — zone string or None

    Returns a list of finding strings (empty list means no issues found).
    """
    findings = []
    for surface in surfaces:
        if not surface.get("is_external", False):
            continue
        zone = surface.get("lightning_zone")
        if not zone:
            findings.append(
                f"Surface '{surface['id']}' is external but has no lightning "
                f"protection zone assigned."
            )
    return findings


def check_lightning_provisions(surface_id, lightning_zone, provisions):
    """
    Verify that the provisions present on a surface satisfy the minimum
    requirements for its lightning protection zone.

    lightning_zone: one of '1A', '1B', '2A', '2B', '3'
    provisions:     list (or set) of provision strings present on the surface

    Returns a dict:
        surface_id     — as supplied
        lightning_zone — as supplied
        adequate       — True if no required provisions are missing
        missing        — sorted list of missing provision strings
    """
    if lightning_zone not in VALID_LIGHTNING_ZONES:
        raise ValueError(
            f"Unrecognized lightning zone '{lightning_zone}'; "
            f"valid zones: {sorted(VALID_LIGHTNING_ZONES)}."
        )

    required = _ZONE_PROVISIONS[lightning_zone]
    present = set(provisions)
    missing = required - present

    return {
        "surface_id": surface_id,
        "lightning_zone": lightning_zone,
        "adequate": len(missing) == 0,
        "missing": sorted(missing),
    }


# ---------------------------------------------------------------------------
# EMC provisions — clause 4.3.12
# ---------------------------------------------------------------------------

def check_emc_bond(joint_id, resistance_ohms):
    """
    Verify that a structural bond used for EMC ground-plane continuity meets
    the EMC bonding resistance limit.

    Returns a dict:
        joint_id        — as supplied
        resistance_ohms — as supplied
        limit_ohms      — EMC_BOND_LIMIT_OHMS
        compliant       — True if resistance_ohms <= limit_ohms
        margin_ohms     — limit_ohms - resistance_ohms
    """
    margin = EMC_BOND_LIMIT_OHMS - resistance_ohms
    return {
        "joint_id": joint_id,
        "resistance_ohms": resistance_ohms,
        "limit_ohms": EMC_BOND_LIMIT_OHMS,
        "compliant": resistance_ohms <= EMC_BOND_LIMIT_OHMS,
        "margin_ohms": margin,
    }


def check_aperture(aperture_id, size_mm, has_screen, screen_mesh_mm=None):
    """
    Verify that an aperture in the structural shell meets the shielding
    control requirement.

    Apertures wider than APERTURE_SCREEN_THRESHOLD_MM require a conductive
    screen. The screen's mesh opening must not exceed SCREEN_MESH_LIMIT_MM.

    aperture_id:    identifier string
    size_mm:        aperture width (mm)
    has_screen:     True if a conductive screen is fitted
    screen_mesh_mm: mesh opening size (mm), required when has_screen is True

    Returns a dict:
        aperture_id       — as supplied
        size_mm           — as supplied
        needs_screen      — True if size_mm > APERTURE_SCREEN_THRESHOLD_MM
        has_adequate_screen — True/False when needs_screen; None when not needed
        compliant         — True if the aperture meets the requirement
        finding           — description string when non-compliant; None otherwise
    """
    needs_screen = size_mm > APERTURE_SCREEN_THRESHOLD_MM

    if not needs_screen:
        return {
            "aperture_id": aperture_id,
            "size_mm": size_mm,
            "needs_screen": False,
            "has_adequate_screen": None,
            "compliant": True,
            "finding": None,
        }

    if not has_screen:
        return {
            "aperture_id": aperture_id,
            "size_mm": size_mm,
            "needs_screen": True,
            "has_adequate_screen": False,
            "compliant": False,
            "finding": (
                f"Aperture '{aperture_id}' ({size_mm:.1f} mm) exceeds the "
                f"{APERTURE_SCREEN_THRESHOLD_MM:.0f} mm threshold and has no "
                f"conductive screen."
            ),
        }

    if screen_mesh_mm is None:
        return {
            "aperture_id": aperture_id,
            "size_mm": size_mm,
            "needs_screen": True,
            "has_adequate_screen": False,
            "compliant": False,
            "finding": (
                f"Aperture '{aperture_id}': screen is present but mesh opening "
                f"size is not specified."
            ),
        }

    adequate = screen_mesh_mm <= SCREEN_MESH_LIMIT_MM
    if adequate:
        return {
            "aperture_id": aperture_id,
            "size_mm": size_mm,
            "needs_screen": True,
            "has_adequate_screen": True,
            "compliant": True,
            "finding": None,
        }

    return {
        "aperture_id": aperture_id,
        "size_mm": size_mm,
        "needs_screen": True,
        "has_adequate_screen": False,
        "compliant": False,
        "finding": (
            f"Aperture '{aperture_id}': screen mesh {screen_mesh_mm:.1f} mm "
            f"exceeds the {SCREEN_MESH_LIMIT_MM:.1f} mm limit."
        ),
    }
