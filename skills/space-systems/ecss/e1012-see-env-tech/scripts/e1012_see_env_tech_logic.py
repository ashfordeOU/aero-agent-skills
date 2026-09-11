#!/usr/bin/env python3
"""ECSS-E-ST-10-12C §9.2-9.3 — SEE environments and susceptible technologies.

Paraphrase of the standard's common-knowledge content, not a verbatim copy.
The clause anchor is ECSS-E-ST-10-12C §9.2 (SEE-relevant radiation environments)
and §9.3 with its Table 9-1 analogue (technology family to SEE type mapping).

This module implements the deterministic, checkable logic behind the leaf:
orbit-regime categorization and dominant-particle lookup (§9.2), technology
categorization and applicable-SEE-type mapping (§9.3), destructive-effect
identification, protective-control status checking, and the combined
orbit-by-technology assessment matrix. It does not model particle fluxes —
the environment transport and rate analysis live in the sibling leaves.

Stdlib only. Offline, deterministic.
"""

# --- Orbit regimes (§9.2) ---------------------------------------------------

# Canonical orbit keys with the particle populations that dominate there.
ORBIT_ENVIRONMENTS = {
    "leo": (
        "trapped_protons",
        "heavy_ions",
        "galactic_cosmic_rays",
    ),
    "meo": (
        "trapped_protons",
        "trapped_electrons",
        "heavy_ions",
        "galactic_cosmic_rays",
        "solar_particle_events",
    ),
    "geo": (
        "heavy_ions",
        "galactic_cosmic_rays",
        "solar_particle_events",
    ),
    "heo": (
        "trapped_protons",
        "trapped_electrons",
        "heavy_ions",
        "galactic_cosmic_rays",
        "solar_particle_events",
    ),
    "interplanetary": (
        "heavy_ions",
        "galactic_cosmic_rays",
        "solar_particle_events",
    ),
    "lunar": (
        "heavy_ions",
        "galactic_cosmic_rays",
        "solar_particle_events",
        "secondary_particles",
    ),
}

# Screening severity ranking used when an orbit sweeps through several regimes.
# Higher rank = the more severe regime that must govern the assessment.
# MEO outranks GEO on trapped-proton fluence; interplanetary/lunar outrank the
# magnetically shielded Earth orbits because magnetospheric shielding is absent.
ORBIT_SEVERITY = {
    "leo": 1,
    "geo": 2,
    "meo": 3,
    "heo": 4,
    "interplanetary": 5,
    "lunar": 6,
}

ORBIT_ALIASES = {
    "low_earth_orbit": "leo",
    "low_earth": "leo",
    "medium_earth_orbit": "meo",
    "geostationary": "geo",
    "geosynchronous": "geo",
    "geostationary_earth_orbit": "geo",
    "geosynchronous_earth_orbit": "geo",
    "highly_elliptical_orbit": "heo",
    "highly_elliptical": "heo",
    "interplanetary_space": "interplanetary",
    "deep_space": "interplanetary",
    "heliocentric": "interplanetary",
    "lunar_orbit": "lunar",
    "lunar_surface": "lunar",
    "cislunar": "lunar",
}

# --- SEE types (§9.3) -------------------------------------------------------

# Canonical ordering used whenever a set of SEE types is reported.
SEE_TYPE_ORDER = ("SEU", "SET", "SEFI", "SEL", "SEB", "SEGR", "SEHE")

# Non-destructive effects are correctable or tolerable with mitigation.
NON_DESTRUCTIVE_EFFECTS = frozenset({"SEU", "SET", "SEFI"})

# Destructive effects can permanently damage the device and demand design
# controls (current limiting, derating, lot screening).
DESTRUCTIVE_EFFECTS = frozenset({"SEL", "SEB", "SEGR", "SEHE"})

_ALL_EFFECTS = NON_DESTRUCTIVE_EFFECTS | DESTRUCTIVE_EFFECTS

# --- Technology families (§9.3, Table 9-1 analogue) -------------------------

TECHNOLOGY_SEE_MAP = {
    "cmos": ("SEU", "SET", "SEFI", "SEL"),
    "bicmos": ("SEU", "SET", "SEFI", "SEL"),
    "bipolar": ("SEU", "SET"),
    "linear_bipolar": ("SEU", "SET"),
    "sram": ("SEU", "SEFI"),
    "dram": ("SEU", "SEFI"),
    "flash": ("SEU", "SEFI"),
    "fpga": ("SEU", "SET", "SEFI"),
    "power_mosfet": ("SEB", "SEGR"),
}

TECHNOLOGY_DISPLAY_NAMES = {
    "cmos": "CMOS",
    "bicmos": "BiCMOS",
    "bipolar": "bipolar",
    "linear_bipolar": "linear bipolar",
    "sram": "SRAM",
    "dram": "DRAM",
    "flash": "Flash",
    "fpga": "FPGA",
    "power_mosfet": "power MOSFET",
}

TECHNOLOGY_ALIASES = {
    "complementary_metal_oxide_semiconductor": "cmos",
    "bicmos_process": "bicmos",
    "linear": "linear_bipolar",
    "linear_bipolar_ic": "linear_bipolar",
    "analog_bipolar": "linear_bipolar",
    "static_ram": "sram",
    "dynamic_ram": "dram",
    "flash_memory": "flash",
    "nor_flash": "flash",
    "nand_flash": "flash",
    "field_programmable_gate_array": "fpga",
    "mosfet": "power_mosfet",
    "power_mos": "power_mosfet",
    "power_mosfet_switch": "power_mosfet",
}


class SEEEnvironmentError(ValueError):
    """Invalid or unrecognized input to a SEE environment/technology function."""


def _normalize_key(raw):
    """Lower-case a label and map spaces/hyphens onto underscores."""
    if not isinstance(raw, str):
        raise SEEEnvironmentError("expected a text label, got %r" % (raw,))
    key = raw.strip().lower().replace("-", "_").replace(" ", "_")
    while "__" in key:
        key = key.replace("__", "_")
    return key.strip("_")


def normalize_orbit_key(orbit):
    """Return the canonical orbit key for an orbit label.

    Accepts the canonical keys (LEO, MEO, GEO, HEO, interplanetary, lunar) in
    any letter case and the convenience aliases in ORBIT_ALIASES.

    Raises SEEEnvironmentError for an unrecognized orbit label.
    """
    key = _normalize_key(orbit)
    if key in ORBIT_ENVIRONMENTS:
        return key
    if key in ORBIT_ALIASES:
        return ORBIT_ALIASES[key]
    raise SEEEnvironmentError(
        "Unrecognized orbit regime %r. Known regimes: %s"
        % (orbit, ", ".join(sorted(ORBIT_ENVIRONMENTS)))
    )


def dominant_particles(orbit):
    """Dominant particle populations for an orbit regime (§9.2 environment table).

    Returns a tuple of canonical particle labels. Raises SEEEnvironmentError
    for an unrecognized orbit.
    """
    return ORBIT_ENVIRONMENTS[normalize_orbit_key(orbit)]


def orbit_severity(orbit):
    """Screening severity rank of an orbit regime (higher = more severe)."""
    return ORBIT_SEVERITY[normalize_orbit_key(orbit)]


def most_severe_orbit(orbits):
    """The most severe regime encountered by a mission that sweeps several orbits.

    Returns the canonical key of the highest-severity orbit in the sequence.
    A mission that passes through multiple regimes must be assessed against
    the most severe one encountered.

    Raises SEEEnvironmentError for an empty sequence or an unknown regime.
    """
    if not orbits:
        raise SEEEnvironmentError("orbits must not be empty")
    keys = [normalize_orbit_key(o) for o in orbits]
    return max(keys, key=lambda k: ORBIT_SEVERITY[k])


def normalize_technology_key(technology):
    """Return the canonical technology key for a technology-family label.

    Raises SEEEnvironmentError for a technology family that is not mapped.
    """
    key = _normalize_key(technology)
    if key in TECHNOLOGY_SEE_MAP:
        return key
    if key in TECHNOLOGY_ALIASES:
        return TECHNOLOGY_ALIASES[key]
    raise SEEEnvironmentError(
        "Unrecognized technology family %r. Mapped families: %s"
        % (technology, ", ".join(sorted(TECHNOLOGY_SEE_MAP)))
    )


def technology_display_name(technology):
    """Human-readable display name for a technology family."""
    return TECHNOLOGY_DISPLAY_NAMES[normalize_technology_key(technology)]


def sort_see_types(effects):
    """Sort SEE types into the canonical reporting order.

    Raises SEEEnvironmentError for any unrecognized effect label.
    """
    keys = {normalize_see_type(e) for e in effects}
    return tuple(e for e in SEE_TYPE_ORDER if e in keys)


def normalize_see_type(effect):
    """Normalize and validate one SEE type label (e.g. 'seu' -> 'SEU')."""
    key = _normalize_key(effect).upper()
    if key not in _ALL_EFFECTS:
        raise SEEEnvironmentError(
            "Unrecognized SEE type %r. Known types: %s"
            % (effect, ", ".join(SEE_TYPE_ORDER))
        )
    return key


def categorize_see_severity(effect):
    """Return 'destructive' or 'non_destructive' for a known SEE type.

    Raises SEEEnvironmentError for an unrecognized effect.
    """
    key = normalize_see_type(effect)
    if key in DESTRUCTIVE_EFFECTS:
        return "destructive"
    return "non_destructive"


def applicable_see_types(technology):
    """Applicable SEE types for a technology family (§9.3 table row).

    The mapping is technology-driven, not orbit-driven: every effect in the
    family's row is returned regardless of the mission orbit.

    Raises SEEEnvironmentError for an unrecognized technology family.
    """
    return sort_see_types(TECHNOLOGY_SEE_MAP[normalize_technology_key(technology)])


def destructive_see_types(technology):
    """The destructive SEE types carried by a technology family (possibly empty)."""
    return tuple(
        e for e in applicable_see_types(technology) if e in DESTRUCTIVE_EFFECTS
    )


def requires_protective_control(technology):
    """True when the technology carries at least one destructive SEE type."""
    return bool(destructive_see_types(technology))


def required_controls(technology):
    """Control measures expected for a technology's destructive SEE types.

    Returns a tuple of control labels. Empty for technologies with no
    destructive SEE type.
    """
    controls = []
    destructive = destructive_see_types(technology)
    if "SEL" in destructive:
        controls.append("current_limiting")
    if "SEB" in destructive or "SEGR" in destructive:
        controls.append("voltage_derating")
        controls.append("lot_screening")
    if "SEHE" in destructive:
        controls.append("operating_constraint")
    return tuple(controls)


def assess_technology(tech_spec):
    """Assess one technology entry against the §9.3 susceptibility mapping.

    ``tech_spec`` is either a technology label ('FPGA', 'power MOSFET', ...) or
    a dict with keys:
      technology  — required technology label
      controls    — optional sequence of documented control labels

    Returns a dict:
      technology            — canonical key
      display_name          — human-readable family name
      applicable_see_types  — tuple, §9.3 table row for the family
      destructive_see_types — tuple, destructive subset
      destructive_risk      — True when at least one destructive type applies
      required_controls     — tuple of expected control labels
      documented_controls   — tuple of controls supplied by the caller
      control_ok            — True when no control is required, or when every
                              required control is documented
      missing_controls      — tuple of required controls not documented
      compliant             — False on a destructive-risk control gap
      finding               — None when compliant, else a finding dict

    Raises SEEEnvironmentError for a missing/unrecognized technology family or
    an unknown control label.
    """
    if isinstance(tech_spec, str):
        spec = {"technology": tech_spec}
    elif isinstance(tech_spec, dict):
        spec = tech_spec
    else:
        raise SEEEnvironmentError(
            "technology entry must be a label or a dict, got %r" % (tech_spec,)
        )

    raw_technology = spec.get("technology")
    if raw_technology is None:
        raise SEEEnvironmentError("technology entry missing required key 'technology'")

    key = normalize_technology_key(raw_technology)
    effects = applicable_see_types(key)
    destructive = destructive_see_types(key)
    needed = required_controls(key)

    supplied_raw = spec.get("controls") or ()
    if isinstance(supplied_raw, str):
        supplied_raw = (supplied_raw,)
    documented = tuple(_normalize_key(c) for c in supplied_raw)
    for control in documented:
        if control not in needed:
            raise SEEEnvironmentError(
                "control %r is not expected for technology %s; expected controls: %s"
                % (control, key, ", ".join(needed) if needed else "<none>")
            )

    missing = tuple(c for c in needed if c not in documented)
    control_ok = not needed or not missing
    compliant = control_ok

    finding = None
    if not compliant:
        finding = {
            "issue": "destructive_risk_without_documented_control",
            "technology": key,
            "destructive_see_types": destructive,
            "missing_controls": missing,
        }

    return {
        "technology": key,
        "display_name": TECHNOLOGY_DISPLAY_NAMES[key],
        "applicable_see_types": effects,
        "destructive_see_types": destructive,
        "destructive_risk": bool(destructive),
        "required_controls": needed,
        "documented_controls": documented,
        "control_ok": control_ok,
        "missing_controls": missing,
        "compliant": compliant,
        "finding": finding,
    }


def build_environment_technology_matrix(orbit, technologies):
    """Combined orbit-by-technology assessment matrix (workflow step 5).

    ``technologies`` is a sequence of technology labels or assessment dicts as
    accepted by :func:`assess_technology`.

    Returns a list of row dicts, one per technology, each carrying:
      orbit, orbit_display, dominant_particles, severity_rank, plus every key
      from the technology assessment.

    Raises SEEEnvironmentError for an empty technology inventory, an unknown
    orbit regime, or an invalid technology entry.
    """
    if not technologies:
        raise SEEEnvironmentError(
            "technology inventory must not be empty — list every candidate family"
        )
    orbit_key = normalize_orbit_key(orbit)
    particles = dominant_particles(orbit_key)
    rows = []
    for spec in technologies:
        assessment = assess_technology(spec)
        row = {
            "orbit": orbit_key,
            "orbit_display": orbit_key.upper(),
            "dominant_particles": particles,
            "severity_rank": ORBIT_SEVERITY[orbit_key],
        }
        row.update(assessment)
        rows.append(row)
    return rows


def matrix_findings(rows):
    """Findings from a matrix built by build_environment_technology_matrix.

    Returns the finding dicts of every non-compliant row, in row order. An
    empty list means every technology with destructive SEE risk has its
    controls documented.
    """
    return [row["finding"] for row in rows if not row.get("compliant", True)]


def destructive_technologies(rows):
    """Technologies carrying at least one destructive SEE type, in row order."""
    return [
        row["technology"]
        for row in rows
        if row.get("destructive_risk", False)
    ]
