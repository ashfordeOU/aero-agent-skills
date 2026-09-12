"""
Background assessment basis logic — ECSS-E-ST-10-12C §10.1–10.3.

Paraphrased from ECSS-E-ST-10-12C; no verbatim standard text reproduced.
Encodes the §10.2 orbit-environment taxonomy and the §10.3 / Table 10-1
sensor-technology taxonomy.  All functions are deterministic and offline.
"""

# ---------------------------------------------------------------------------
# §10.2  Orbit → relevant background environments
# ---------------------------------------------------------------------------

ORBIT_ENVIRONMENTS = {
    "LEO": [
        "trapped_electrons",
        "trapped_protons",
        "cosmic_rays_gcr",
        "solar_energetic_particles",
        "albedo_neutrons",
    ],
    "MEO": [
        "trapped_electrons",
        "trapped_protons",
        "cosmic_rays_gcr",
        "solar_energetic_particles",
    ],
    "HEO": [
        "trapped_electrons",
        "trapped_protons",
        "cosmic_rays_gcr",
        "solar_energetic_particles",
    ],
    "GEO": [
        "trapped_electrons_outer_belt",
        "cosmic_rays_gcr",
        "solar_energetic_particles",
    ],
    "INTERPLANETARY": [
        "cosmic_rays_gcr",
        "solar_energetic_particles",
    ],
    "DEEP_SPACE": [
        "cosmic_rays_gcr",
    ],
}

# ---------------------------------------------------------------------------
# §10.3 / Table 10-1  Sensor-technology taxonomy
# ---------------------------------------------------------------------------

SENSOR_TECHNOLOGIES = {
    "silicon_semiconductor": {
        "variants": ["photodiode", "ccd", "cmos_aps"],
        "background_mechanism": "direct_ionization_and_charge_deposition",
        "energy_range_kev": (0.1, 20000.0),
    },
    "scintillator": {
        "variants": ["nai", "csi", "bgo", "labr3"],
        "background_mechanism": "scintillation_from_particle_interactions",
        "energy_range_kev": (1.0, 10000.0),
    },
    "proportional_counter": {
        "variants": ["xe_gas", "ar_gas", "p10_gas"],
        "background_mechanism": "gas_ionization_by_particles",
        "energy_range_kev": (0.1, 100.0),
    },
    "germanium_solid_state": {
        "variants": ["hpge", "lege"],
        "background_mechanism": "direct_ionization_high_resolution",
        "energy_range_kev": (1.0, 10000.0),
    },
    "cdte_family": {
        "variants": ["cdte", "cdznte"],
        "background_mechanism": "direct_ionization_compound_semiconductor",
        "energy_range_kev": (10.0, 3000.0),
    },
    "neutron_detector": {
        "variants": ["he3_tube", "li_glass", "bf3_tube"],
        "background_mechanism": "nuclear_reactions_neutron_capture",
        "energy_range_kev": None,
    },
    "microchannel_plate": {
        "variants": ["mcp_single", "mcp_stack"],
        "background_mechanism": "direct_particle_hits_secondary_emission",
        "energy_range_kev": (0.01, 100.0),
    },
}

# Reverse lookup: variant name → family key
_VARIANT_TO_FAMILY = {
    variant: family
    for family, info in SENSOR_TECHNOLOGIES.items()
    for variant in info["variants"]
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_orbit_types():
    """Return the list of recognized orbit-type labels (§10.2)."""
    return list(ORBIT_ENVIRONMENTS.keys())


def list_sensor_families():
    """Return the list of recognized sensor-technology family keys (Table 10-1)."""
    return list(SENSOR_TECHNOLOGIES.keys())


def get_environments(orbit_type: str) -> list:
    """
    Return the relevant background environments for *orbit_type*.

    Parameters
    ----------
    orbit_type : str
        One of the orbit labels defined in §10.2 (case-insensitive).

    Returns
    -------
    list of str
        Relevant environment identifiers for that orbit.

    Raises
    ------
    ValueError
        When *orbit_type* is not in the §10.2 taxonomy.
    """
    key = orbit_type.upper()
    if key not in ORBIT_ENVIRONMENTS:
        raise ValueError(
            f"Unrecognized orbit type '{orbit_type}'. "
            f"Expected one of: {list(ORBIT_ENVIRONMENTS)}"
        )
    return list(ORBIT_ENVIRONMENTS[key])


def get_sensor_info(family_key: str) -> dict:
    """
    Return the technology-info dict for *family_key*.

    Parameters
    ----------
    family_key : str
        One of the Table 10-1 family keys.

    Returns
    -------
    dict
        Copy of the family entry (variants, background_mechanism, energy_range_kev).

    Raises
    ------
    ValueError
        When *family_key* is not in the Table 10-1 taxonomy.
    """
    if family_key not in SENSOR_TECHNOLOGIES:
        raise ValueError(
            f"Unrecognized sensor family '{family_key}'. "
            f"Expected one of: {list(SENSOR_TECHNOLOGIES)}"
        )
    return dict(SENSOR_TECHNOLOGIES[family_key])


def lookup_family_by_variant(variant: str) -> str:
    """
    Return the sensor-family key for a given variant name.

    Example: 'ccd' → 'silicon_semiconductor'.

    Parameters
    ----------
    variant : str
        Variant name (case-insensitive) from Table 10-1.

    Returns
    -------
    str
        Family key for that variant.

    Raises
    ------
    ValueError
        When the variant is not in the Table 10-1 taxonomy.
    """
    key = variant.lower()
    if key not in _VARIANT_TO_FAMILY:
        raise ValueError(
            f"Variant '{variant}' not found in Table 10-1 taxonomy. "
            f"Known variants: {sorted(_VARIANT_TO_FAMILY)}"
        )
    return _VARIANT_TO_FAMILY[key]


def build_assessment_basis(orbit_type: str, family_key: str) -> dict:
    """
    Build and return the complete assessment-basis record.

    The record contains all fields required before quantitative background
    calculations may proceed (§10.3 prerequisite gate).

    Parameters
    ----------
    orbit_type : str
        Orbit label (case-insensitive).
    family_key : str
        Sensor-technology family key from Table 10-1.

    Returns
    -------
    dict with keys:
        orbit_type          : normalized upper-case orbit label
        environments        : list of relevant background environments
        sensor_family       : family key
        background_mechanism: primary response mechanism for that family
        energy_range_kev    : (min, max) tuple or None
        complete            : bool — True when all mandatory fields are present

    Raises
    ------
    ValueError
        When either input is not in the respective taxonomy.
    """
    envs = get_environments(orbit_type)
    info = get_sensor_info(family_key)

    record = {
        "orbit_type": orbit_type.upper(),
        "environments": envs,
        "sensor_family": family_key,
        "background_mechanism": info["background_mechanism"],
        "energy_range_kev": info["energy_range_kev"],
        "complete": True,
    }
    mandatory = ["orbit_type", "environments", "sensor_family", "background_mechanism"]
    for field in mandatory:
        val = record.get(field)
        if not val:
            record["complete"] = False
            break
    return record


def check_basis_complete(record: dict) -> bool:
    """
    Return True only when the basis record carries all four mandatory fields
    and the environments list is non-empty.

    Parameters
    ----------
    record : dict
        Assessment-basis record as returned by build_assessment_basis.

    Returns
    -------
    bool
    """
    required = ["orbit_type", "environments", "sensor_family", "background_mechanism"]
    for field in required:
        val = record.get(field)
        if not val:
            return False
    if not isinstance(record.get("environments"), list):
        return False
    if len(record["environments"]) == 0:
        return False
    return True
