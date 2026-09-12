"""
ECSS-E-ST-10-12C §8.3–8.4 — DD-relevant environments and susceptible technologies.

Implements deterministic, offline logic for:
  - Categorizing orbital particle environments by displacement-damage (DD) relevance
  - Mapping component technologies to DD susceptibility tiers
  - Determining which items require a NIEL-based analysis
  - Checking DD analysis coverage across a design item list
  - Mapping the full DD scope for a mission orbit + technology set
"""

# ── Environment registry (§8.3) ───────────────────────────────────────────────
# Keys are canonical snake_case names used throughout this module.
ENVIRONMENT_DD_RELEVANCE = {
    "trapped_protons":      "HIGH",
    "solar_proton_event":   "HIGH",
    "galactic_cosmic_rays": "MODERATE",
    "trapped_electrons":    "LOW",
    "bremsstrahlung":       "NEGLIGIBLE",
}

_ENV_ALIASES = {
    "spe":               "solar_proton_event",
    "solar_protons":     "solar_proton_event",
    "gcr":               "galactic_cosmic_rays",
    "cosmic_rays":       "galactic_cosmic_rays",
    "electrons":         "trapped_electrons",
    "belt_electrons":    "trapped_electrons",
    "belt_protons":      "trapped_protons",
    "protons":           "trapped_protons",
    "x_ray":             "bremsstrahlung",
}

# ── Technology registry (§8.4) ────────────────────────────────────────────────
TECHNOLOGY_DD_SUSCEPTIBILITY = {
    "solar_cell_si":           "CRITICAL",
    "solar_cell_gaas":         "CRITICAL",
    "solar_cell_multijunction": "CRITICAL",
    "ccd":                     "HIGH",
    "bipolar_transistor":      "HIGH",
    "bipolar_ic":              "HIGH",
    "optocoupler":             "HIGH",
    "photodiode":              "HIGH",
    "laser_diode":             "HIGH",
    "phototransistor":         "HIGH",
    "power_mosfet":            "MODERATE",
    "jfet":                    "MODERATE",
    "cmos_digital":            "LOW",
    "mosfet_digital":          "LOW",
    "sram_cmos":               "LOW",
    "passive":                 "NONE",
    "resistor":                "NONE",
    "capacitor":               "NONE",
    "inductor":                "NONE",
}

_TECH_ALIASES = {
    "si_solar_cell":        "solar_cell_si",
    "gaas_solar_cell":      "solar_cell_gaas",
    "mjc":                  "solar_cell_multijunction",
    "multi_junction":       "solar_cell_multijunction",
    "bipolar":              "bipolar_transistor",
    "bjt":                  "bipolar_transistor",
    "opto":                 "optocoupler",
    "pdiode":               "photodiode",
    "ldio":                 "laser_diode",
    "ld":                   "laser_diode",
    "mosfet":               "mosfet_digital",
    "cmos":                 "cmos_digital",
}

# Tiers that require a dedicated NIEL-based DD analysis
DD_ANALYSIS_REQUIRED_TIERS = frozenset({"CRITICAL", "HIGH"})
# Tiers that require analysis only when the orbit has a HIGH-relevance environment
DD_ANALYSIS_CONDITIONAL_TIERS = frozenset({"MODERATE"})

VALID_TIERS = frozenset({"CRITICAL", "HIGH", "MODERATE", "LOW", "NONE", "NEGLIGIBLE"})

# ── Orbit → environment mapping ───────────────────────────────────────────────
ORBIT_ENVIRONMENTS = {
    "LEO":           ["trapped_protons", "trapped_electrons", "galactic_cosmic_rays"],
    "MEO":           ["trapped_protons", "trapped_electrons", "galactic_cosmic_rays"],
    "GEO":           ["solar_proton_event", "trapped_electrons", "galactic_cosmic_rays"],
    "HEO":           ["trapped_protons", "trapped_electrons", "solar_proton_event",
                      "galactic_cosmic_rays"],
    "INTERPLANETARY": ["solar_proton_event", "galactic_cosmic_rays"],
    "LUNAR":         ["solar_proton_event", "galactic_cosmic_rays"],
    "SSO":           ["trapped_protons", "trapped_electrons", "galactic_cosmic_rays"],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise_env(env_name):
    key = env_name.strip().lower().replace(" ", "_").replace("-", "_")
    return _ENV_ALIASES.get(key, key)


def _normalise_tech(tech_name):
    key = tech_name.strip().lower().replace(" ", "_").replace("-", "_")
    return _TECH_ALIASES.get(key, key)


# ── Public API ────────────────────────────────────────────────────────────────

def get_environment_dd_relevance(env_name):
    """Return the DD relevance tier string for a particle environment.

    Raises ValueError for unrecognised environment names.
    """
    key = _normalise_env(env_name)
    if key not in ENVIRONMENT_DD_RELEVANCE:
        raise ValueError(
            f"Unknown DD environment: {env_name!r}. "
            f"Known environments: {sorted(ENVIRONMENT_DD_RELEVANCE)}"
        )
    return ENVIRONMENT_DD_RELEVANCE[key]


def get_technology_dd_susceptibility(tech_name):
    """Return the DD susceptibility tier string for a component technology.

    Raises ValueError for unrecognised technology names.
    """
    key = _normalise_tech(tech_name)
    if key not in TECHNOLOGY_DD_SUSCEPTIBILITY:
        raise ValueError(
            f"Unknown technology: {tech_name!r}. "
            f"Known technologies: {sorted(TECHNOLOGY_DD_SUSCEPTIBILITY)}"
        )
    return TECHNOLOGY_DD_SUSCEPTIBILITY[key]


def requires_dd_analysis(susceptibility_tier, orbit_has_high_env=False):
    """Return True when a component tier mandates a NIEL-based DD analysis.

    Args:
        susceptibility_tier: one of VALID_TIERS.
        orbit_has_high_env: True when the mission orbit contains at least one
            HIGH-relevance environment; used for MODERATE-tier conditional check.

    Raises ValueError for unrecognised tier strings.
    """
    if susceptibility_tier not in VALID_TIERS:
        raise ValueError(
            f"Unknown susceptibility tier: {susceptibility_tier!r}. "
            f"Valid tiers: {sorted(VALID_TIERS)}"
        )
    if susceptibility_tier in DD_ANALYSIS_REQUIRED_TIERS:
        return True
    if susceptibility_tier in DD_ANALYSIS_CONDITIONAL_TIERS:
        return bool(orbit_has_high_env)
    return False


def get_orbit_environments(orbit):
    """Return the list of DD-relevant environment names for an orbit type.

    Raises ValueError for unrecognised orbit identifiers.
    """
    key = orbit.strip().upper()
    if key not in ORBIT_ENVIRONMENTS:
        raise ValueError(
            f"Unknown orbit type: {orbit!r}. "
            f"Known orbits: {sorted(ORBIT_ENVIRONMENTS)}"
        )
    return list(ORBIT_ENVIRONMENTS[key])


def orbit_has_high_relevance_environment(orbit):
    """Return True when the orbit contains at least one HIGH-relevance environment."""
    envs = get_orbit_environments(orbit)
    return any(ENVIRONMENT_DD_RELEVANCE.get(e) == "HIGH" for e in envs)


def check_dd_analysis_coverage(design_items, orbit=None):
    """Check that every DD-susceptible item has dd_analysis_assigned=True.

    Args:
        design_items: list of dicts, each with keys:
            - name (str): item identifier
            - technology (str): must be a recognised technology name
            - dd_analysis_assigned (bool): whether analysis has been assigned
        orbit: optional orbit string; used to evaluate MODERATE-tier items.
            If None, MODERATE items are treated as not requiring analysis.

    Returns dict with keys:
        - covered: list of item names with adequate coverage
        - missing: list of item names requiring analysis but missing it
        - errors: list of (name, message) tuples for items with unknown technologies
    """
    high_env = orbit_has_high_relevance_environment(orbit) if orbit else False

    covered = []
    missing = []
    errors = []

    for item in design_items:
        name = item.get("name", "<unnamed>")
        tech = item.get("technology", "")
        assigned = bool(item.get("dd_analysis_assigned", False))

        try:
            tier = get_technology_dd_susceptibility(tech)
            needed = requires_dd_analysis(tier, orbit_has_high_env=high_env)
            if needed and not assigned:
                missing.append(name)
            else:
                covered.append(name)
        except ValueError as exc:
            errors.append((name, str(exc)))

    return {"covered": covered, "missing": missing, "errors": errors}


def map_mission_dd_scope(orbit, technologies):
    """Produce the complete DD scope map for a mission.

    Args:
        orbit: orbit type string (e.g. "LEO", "GEO").
        technologies: list of technology name strings.

    Returns dict with keys:
        - orbit: str
        - environments: list of (env_name, relevance_tier) tuples
        - high_relevance_environments: list of env names with HIGH tier
        - technologies: list of (tech_name, susceptibility_tier, needs_analysis) tuples
        - analysis_required_count: int — number of technologies requiring analysis
        - errors: list of (tech_name, message) for unrecognised technologies
    """
    try:
        env_names = get_orbit_environments(orbit)
    except ValueError as exc:
        return {"orbit": orbit, "error": str(exc)}

    envs = [(e, ENVIRONMENT_DD_RELEVANCE.get(e, "UNKNOWN")) for e in env_names]
    high_envs = [e for e, r in envs if r == "HIGH"]
    has_high = bool(high_envs)

    tech_rows = []
    errors = []
    analysis_count = 0

    for tech in technologies:
        try:
            susc = get_technology_dd_susceptibility(tech)
            needed = requires_dd_analysis(susc, orbit_has_high_env=has_high)
            if needed:
                analysis_count += 1
            tech_rows.append((tech, susc, needed))
        except ValueError as exc:
            errors.append((tech, str(exc)))

    return {
        "orbit": orbit,
        "environments": envs,
        "high_relevance_environments": high_envs,
        "technologies": tech_rows,
        "analysis_required_count": analysis_count,
        "errors": errors,
    }
