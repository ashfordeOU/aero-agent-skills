"""
Material selection logic for spacecraft structures under ECSS-E-ST-32 section 4.5.6.

Implements deterministic, offline checks for:
  - Material family categorization
  - Stress-corrosion susceptibility lookup (ECSS-Q-ST-70-32C reference)
  - Space environment compatibility assessment
  - Per-candidate evaluation and selection

No third-party dependencies (stdlib only).
"""

# ---------------------------------------------------------------------------
# Material database
# ---------------------------------------------------------------------------

# Maps material identifier → family
MATERIAL_DATABASE = {
    "al_2024_t3": "metallic",
    "al_7075_t6": "metallic",
    "al_6061_t6": "metallic",
    "ti_6al_4v": "metallic",
    "ti_3al_2_5v": "metallic",
    "inox_316l": "metallic",
    "invar_36": "metallic",
    "cfrp_unidirectional": "composite",
    "cfrp_woven": "composite",
    "gfrp": "composite",
    "si3n4": "ceramic",
    "al2o3": "ceramic",
    "polyimide": "polymer",
    "ptfe": "polymer",
    "peek": "polymer",
}

VALID_FAMILIES = {"metallic", "composite", "ceramic", "polymer"}

# ---------------------------------------------------------------------------
# Stress-corrosion susceptibility matrix (ECSS-Q-ST-70-32C reference)
#
# Rating scale: 1=immune, 2=low susceptibility, 3=medium, 4=high
# Ratings above 2 require design action per ECSS-E-ST-32 section 4.5.6.
# ---------------------------------------------------------------------------

VALID_ENVIRONMENTS = {"vacuum", "dry", "humid", "salt"}

STRESS_CORROSION_MATRIX = {
    ("al_2024_t3", "vacuum"): 1,
    ("al_2024_t3", "dry"):    1,
    ("al_2024_t3", "humid"):  3,
    ("al_2024_t3", "salt"):   4,
    ("al_7075_t6", "vacuum"): 1,
    ("al_7075_t6", "dry"):    1,
    ("al_7075_t6", "humid"):  3,
    ("al_7075_t6", "salt"):   4,
    ("al_6061_t6", "vacuum"): 1,
    ("al_6061_t6", "dry"):    1,
    ("al_6061_t6", "humid"):  2,
    ("al_6061_t6", "salt"):   3,
    ("ti_6al_4v", "vacuum"):  1,
    ("ti_6al_4v", "dry"):     1,
    ("ti_6al_4v", "humid"):   1,
    ("ti_6al_4v", "salt"):    2,
    ("ti_3al_2_5v", "vacuum"): 1,
    ("ti_3al_2_5v", "dry"):    1,
    ("ti_3al_2_5v", "humid"):  1,
    ("ti_3al_2_5v", "salt"):   2,
    ("inox_316l", "vacuum"):  1,
    ("inox_316l", "dry"):     1,
    ("inox_316l", "humid"):   2,
    ("inox_316l", "salt"):    3,
    ("invar_36", "vacuum"):   1,
    ("invar_36", "dry"):      1,
    ("invar_36", "humid"):    2,
    ("invar_36", "salt"):     3,
    ("cfrp_unidirectional", "vacuum"): 1,
    ("cfrp_unidirectional", "dry"):    1,
    ("cfrp_unidirectional", "humid"):  1,
    ("cfrp_unidirectional", "salt"):   1,
    ("cfrp_woven", "vacuum"): 1,
    ("cfrp_woven", "dry"):    1,
    ("cfrp_woven", "humid"):  1,
    ("cfrp_woven", "salt"):   1,
    ("gfrp", "vacuum"): 1,
    ("gfrp", "dry"):    1,
    ("gfrp", "humid"):  2,
    ("gfrp", "salt"):   2,
    ("si3n4", "vacuum"): 1,
    ("si3n4", "dry"):    1,
    ("si3n4", "humid"):  1,
    ("si3n4", "salt"):   1,
    ("al2o3", "vacuum"): 1,
    ("al2o3", "dry"):    1,
    ("al2o3", "humid"):  1,
    ("al2o3", "salt"):   1,
    ("polyimide", "vacuum"): 1,
    ("polyimide", "dry"):    1,
    ("polyimide", "humid"):  1,
    ("polyimide", "salt"):   1,
    ("ptfe", "vacuum"): 1,
    ("ptfe", "dry"):    1,
    ("ptfe", "humid"):  1,
    ("ptfe", "salt"):   1,
    ("peek", "vacuum"): 1,
    ("peek", "dry"):    1,
    ("peek", "humid"):  1,
    ("peek", "salt"):   1,
}

# ---------------------------------------------------------------------------
# Space environment hazard map
#
# Maps hazard → affected material family → severity
# "flag"   – requires resolution before the selection verdict can be ACCEPTABLE
# "verify" – requires confirmation data but does not block alone
# ---------------------------------------------------------------------------

VALID_SPACE_HAZARDS = {"atomic_oxygen", "radiation_dose", "thermal_cycling", "outgassing"}

SPACE_ENVIRONMENT_HAZARDS = {
    "atomic_oxygen": {
        "polymer":   "flag",    # AO erodes polymer surfaces; protect or substitute
        "composite": "verify",  # Matrix resin may degrade; verify protective coating
    },
    "radiation_dose": {
        "polymer": "flag",      # Polymers embrittle under TID; verify dose limit
    },
    "thermal_cycling": {
        "composite": "verify",  # Verify CTE mismatch fatigue at bonded metal interfaces
        "ceramic":   "verify",  # Verify fracture toughness at low temperature
    },
    "outgassing": {
        "polymer":   "flag",    # Must satisfy TML/CVCM per ECSS-Q-ST-70-02
        "composite": "verify",  # Verify resin outgassing data vs adjacent surface limits
    },
}

# ---------------------------------------------------------------------------
# Verdict constants
# ---------------------------------------------------------------------------

VERDICT_ACCEPTABLE     = "ACCEPTABLE"
VERDICT_CONDITIONAL    = "CONDITIONAL"
VERDICT_NOT_ACCEPTABLE = "NOT_ACCEPTABLE"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def categorize_material(material_id):
    """Return the material family for a known material identifier.

    Returns one of: 'metallic', 'composite', 'ceramic', 'polymer'.
    Raises ValueError for an unknown identifier.
    """
    key = material_id.strip().lower()
    if key not in MATERIAL_DATABASE:
        raise ValueError(
            "Unknown material '{}'. Add it to MATERIAL_DATABASE or "
            "correct the identifier.".format(material_id)
        )
    return MATERIAL_DATABASE[key]


def get_stress_corrosion_rating(material_id, environment):
    """Return the stress-corrosion susceptibility rating (1–4) for a material/environment pair.

    Rating scale (ECSS-Q-ST-70-32C reference):
      1 = immune
      2 = low susceptibility
      3 = medium susceptibility — protective coating or redesign required
      4 = high susceptibility — material substitution required

    Raises ValueError for an unknown material or environment.
    """
    mat = material_id.strip().lower()
    env = environment.strip().lower()

    if mat not in MATERIAL_DATABASE:
        raise ValueError("Unknown material '{}'.".format(material_id))
    if env not in VALID_ENVIRONMENTS:
        raise ValueError(
            "Unknown environment '{}'. Valid options: {}.".format(
                environment, sorted(VALID_ENVIRONMENTS)
            )
        )

    key = (mat, env)
    if key not in STRESS_CORROSION_MATRIX:
        raise ValueError(
            "No stress-corrosion data for ({}, {}).".format(mat, env)
        )

    return STRESS_CORROSION_MATRIX[key]


def check_stress_corrosion_acceptability(material_id, environment, max_allowed_rating=2):
    """Evaluate whether a material's stress-corrosion rating clears the design threshold.

    Returns a dict:
      material (str), environment (str), rating (int),
      acceptable (bool), action (str).

    action values:
      'none_required'
      'apply_protective_coating_or_substitute_material'  (rating 3)
      'substitute_material'                               (rating 4)
    """
    rating = get_stress_corrosion_rating(material_id, environment)
    acceptable = rating <= max_allowed_rating

    if acceptable:
        action = "none_required"
    elif rating == 3:
        action = "apply_protective_coating_or_substitute_material"
    else:
        action = "substitute_material"

    return {
        "material":    material_id.strip().lower(),
        "environment": environment.strip().lower(),
        "rating":      rating,
        "acceptable":  acceptable,
        "action":      action,
    }


def check_space_environment_compatibility(material_id, active_hazards):
    """Assess a material against a set of active space environment hazards.

    active_hazards: list of strings drawn from VALID_SPACE_HAZARDS.

    Returns a dict:
      material (str), material_family (str),
      findings (list of dicts), compatible (bool).

    Each finding has: hazard (str), severity ('flag'|'verify'), material_family (str).
    compatible is True when no "flag" findings are present.

    Raises ValueError for an unknown material or an unrecognized hazard.
    """
    mat = material_id.strip().lower()
    if mat not in MATERIAL_DATABASE:
        raise ValueError("Unknown material '{}'.".format(material_id))

    family = MATERIAL_DATABASE[mat]
    findings = []

    for hazard in active_hazards:
        h = hazard.strip().lower()
        if h not in VALID_SPACE_HAZARDS:
            raise ValueError(
                "Unknown space hazard '{}'. Valid options: {}.".format(
                    hazard, sorted(VALID_SPACE_HAZARDS)
                )
            )
        hazard_map = SPACE_ENVIRONMENT_HAZARDS.get(h, {})
        if family in hazard_map:
            findings.append({
                "hazard":          h,
                "severity":        hazard_map[family],
                "material_family": family,
            })

    flags = [f for f in findings if f["severity"] == "flag"]
    return {
        "material":        mat,
        "material_family": family,
        "findings":        findings,
        "compatible":      len(flags) == 0,
    }


def evaluate_material_for_application(material_id, ground_environment, active_space_hazards):
    """Produce a consolidated selection assessment for one material candidate.

    ground_environment:  one of VALID_ENVIRONMENTS (checked during ground processing)
    active_space_hazards: list of strings from VALID_SPACE_HAZARDS

    Returns a dict:
      material (str), material_family (str),
      stress_corrosion (dict), space_compatibility (dict),
      verdict (str: ACCEPTABLE|CONDITIONAL|NOT_ACCEPTABLE),
      findings (list of str).
    """
    sc = check_stress_corrosion_acceptability(material_id, ground_environment)
    space = check_space_environment_compatibility(material_id, active_space_hazards)

    flags   = [f for f in space["findings"] if f["severity"] == "flag"]
    verifies = [f for f in space["findings"] if f["severity"] == "verify"]

    if not sc["acceptable"] and sc["rating"] == 4:
        verdict = VERDICT_NOT_ACCEPTABLE
    elif not sc["acceptable"] or flags:
        verdict = VERDICT_CONDITIONAL
    elif verifies:
        verdict = VERDICT_CONDITIONAL
    else:
        verdict = VERDICT_ACCEPTABLE

    findings = []
    if not sc["acceptable"]:
        findings.append(
            "stress_corrosion_rating_{}: {}".format(sc["rating"], sc["action"])
        )
    for f in space["findings"]:
        findings.append(
            "space_hazard_{}_{}: {} material affected".format(
                f["hazard"], f["severity"], f["material_family"]
            )
        )

    return {
        "material":           sc["material"],
        "material_family":    space["material_family"],
        "stress_corrosion":   sc,
        "space_compatibility": space,
        "verdict":            verdict,
        "findings":           findings,
    }


def select_material(candidates, ground_environment, active_space_hazards):
    """Select the best material from a list of candidates.

    Preference order: ACCEPTABLE > CONDITIONAL > NOT_ACCEPTABLE.
    Returns the result dict of the first candidate that reaches the highest
    attainable verdict, or None if all candidates are NOT_ACCEPTABLE.

    Raises ValueError when the candidate list is empty.
    """
    if not candidates:
        raise ValueError("Candidate list is empty; at least one material is required.")

    results = [
        evaluate_material_for_application(m, ground_environment, active_space_hazards)
        for m in candidates
    ]

    for result in results:
        if result["verdict"] == VERDICT_ACCEPTABLE:
            return result
    for result in results:
        if result["verdict"] == VERDICT_CONDITIONAL:
            return result
    return None
