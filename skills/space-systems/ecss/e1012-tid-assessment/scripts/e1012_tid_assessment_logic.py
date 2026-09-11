"""
TID (Total Ionising Dose) assessment logic — ECSS-E-ST-10-12C §7.5.

Implements §7.5.1 (radiation damage parameters) and §7.5.2
(ionising dose calculation) as deterministic, offline engineering logic.
No third-party dependencies — stdlib only.
"""

# Component categories from §7.5.1 radiation damage parameters.
# Limits are indicative groupings from RHA practice (paraphrased; not
# verbatim ECSS table data). Keys match the four canonical hardness levels.
COMPONENT_CATEGORIES = {
    "standard":      {"max_tid_rad": 5_000},
    "rad_tolerant":  {"max_tid_rad": 30_000},
    "rad_hard":      {"max_tid_rad": 300_000},
    "rad_hardened":  {"max_tid_rad": 1_000_000},
}

# Orbit-specific dose rates (krad/year) indexed by aluminium shielding
# thickness in mm.  Values are representative environment estimates
# (paraphrased from common RHA references) for three canonical orbits.
# Ref: ECSS-E-ST-10-12C §7.5.2 — environment model input.
ORBIT_DOSE_RATE_KRAD_YR = {
    "LEO_500km":    {2: 0.5,  5: 0.3,  10: 0.1},
    "MEO_20200km":  {2: 50.0, 5: 20.0, 10: 8.0},
    "GEO":          {2: 10.0, 5: 5.0,  10: 2.0},
}

VALID_SHIELD_MM = frozenset(ORBIT_DOSE_RATE_KRAD_YR[next(iter(ORBIT_DOSE_RATE_KRAD_YR))])


def compute_tid(orbit: str, shield_mm: float, duration_years: float) -> float:
    """
    Compute accumulated TID in rad(Si) at a component location.

    orbit          — one of the orbit keys in ORBIT_DOSE_RATE_KRAD_YR.
    shield_mm      — aluminium shielding thickness in mm (must be a tabulated value).
    duration_years — mission duration in years (must be positive).

    Ref: ECSS-E-ST-10-12C §7.5.2.
    Raises ValueError for unrecognised orbit, unsupported shielding thickness,
    or non-positive duration.
    """
    if orbit not in ORBIT_DOSE_RATE_KRAD_YR:
        raise ValueError(
            f"Unknown orbit '{orbit}'. Valid options: {sorted(ORBIT_DOSE_RATE_KRAD_YR)}"
        )
    if shield_mm not in VALID_SHIELD_MM:
        raise ValueError(
            f"shield_mm {shield_mm} is not tabulated. "
            f"Valid values: {sorted(VALID_SHIELD_MM)}"
        )
    if duration_years <= 0:
        raise ValueError(
            f"duration_years must be positive; got {duration_years}"
        )

    dose_rate = ORBIT_DOSE_RATE_KRAD_YR[orbit][shield_mm]  # krad/year
    tid_krad = dose_rate * duration_years
    return tid_krad * 1_000.0  # convert to rad(Si)


def assess_component(tid_rad: float, category: str, margin: float = 2.0) -> dict:
    """
    Assess a single component against its TID limit.

    tid_rad  — accumulated TID at the component location (rad).
    category — component hardness category key in COMPONENT_CATEGORIES.
    margin   — design margin factor applied to tid_rad before comparison
               (per §7.5.2 margin requirement; default 2.0).

    Returns a dict:
      required_rad  — tid_rad * margin (the radiation design requirement)
      limit_rad     — category TID limit from §7.5.1 damage parameters
      compliant     — True when required_rad <= limit_rad
      margin_factor — the margin applied

    Raises ValueError for negative TID, unknown category, or non-positive margin.
    """
    if tid_rad < 0:
        raise ValueError(f"tid_rad must be non-negative; got {tid_rad}")
    if category not in COMPONENT_CATEGORIES:
        raise ValueError(
            f"Unknown component category '{category}'. "
            f"Valid options: {sorted(COMPONENT_CATEGORIES)}"
        )
    if margin <= 0:
        raise ValueError(f"margin must be positive; got {margin}")

    limit = COMPONENT_CATEGORIES[category]["max_tid_rad"]
    required = tid_rad * margin
    return {
        "required_rad": required,
        "limit_rad": limit,
        "compliant": required <= limit,
        "margin_factor": margin,
    }


def categorize_component(max_tid_rad: float) -> str:
    """
    Derive the component hardness category from its characterised TID tolerance.

    Selects the tightest category whose limit is >= max_tid_rad, so a component
    that tolerates 6 000 rad is placed in 'rad_tolerant' (limit 30 000), not
    'standard' (limit 5 000).

    Ref: ECSS-E-ST-10-12C §7.5.1 — damage parameter grouping.

    Raises ValueError for non-positive max_tid_rad.
    """
    if max_tid_rad <= 0:
        raise ValueError(f"max_tid_rad must be positive; got {max_tid_rad}")

    for cat, params in sorted(
        COMPONENT_CATEGORIES.items(), key=lambda kv: kv[1]["max_tid_rad"]
    ):
        if max_tid_rad <= params["max_tid_rad"]:
            return cat

    # Exceeds all tabulated thresholds — highest category applies.
    return max(COMPONENT_CATEGORIES, key=lambda k: COMPONENT_CATEGORIES[k]["max_tid_rad"])


def assess_mission(
    components: list,
    orbit: str,
    shield_mm: float,
    duration_years: float,
    margin: float = 2.0,
) -> list:
    """
    Run a full TID assessment for a list of component descriptors.

    components — list of dicts, each with mandatory keys 'name' and 'category'.
    Returns a list of result dicts (one per component) augmenting the
    assess_component output with 'name' and 'tid_rad'.

    Raises ValueError for malformed component entries or invalid orbit/shielding.
    """
    tid = compute_tid(orbit, shield_mm, duration_years)
    results = []
    for comp in components:
        if "name" not in comp:
            raise ValueError("Each component dict must include a 'name' key")
        if "category" not in comp:
            raise ValueError(
                f"Component '{comp.get('name', '?')}' is missing a 'category' key"
            )
        result = assess_component(tid, comp["category"], margin)
        result["name"] = comp["name"]
        result["tid_rad"] = tid
        results.append(result)
    return results
