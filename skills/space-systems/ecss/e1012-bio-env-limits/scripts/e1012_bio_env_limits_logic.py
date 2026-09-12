"""
Radiation protection assessment for crewed space missions.

Implements §11.3 (environment identification) and §11.4 (crew dose limit checks)
of ECSS-E-ST-10C — paraphrased into checkable engineering logic.  No verbatim
standard text; clauses cited as anchors only.  Stdlib only; no external deps.
"""

# ---------------------------------------------------------------------------
# Environment taxonomy (§11.3)
# ---------------------------------------------------------------------------

ENVIRONMENT_TYPES = {
    "GCR": (
        "Galactic Cosmic Rays — continuous isotropic background, "
        "primary dose source in deep space and polar/high-inclination LEO"
    ),
    "SPE": (
        "Solar Energetic Particles — transient events during solar flares/CMEs, "
        "high-flux protons and heavier ions reaching crewed orbits with polar-horn access"
    ),
    "TRAPPED_PROTON": (
        "Trapped protons in the inner Van Allen belt and the South Atlantic Anomaly tail, "
        "relevant below ~10 000 km altitude"
    ),
    "TRAPPED_ELECTRON": (
        "Trapped electrons in the inner and outer Van Allen belts, "
        "predominantly between ~1 500 km and ~65 000 km altitude"
    ),
    "NEUTRON": (
        "Secondary neutrons produced by primary radiation interacting with shielding "
        "material; always present as a secondary product in any shielded environment"
    ),
}

# Keyword → environment category mapping for source identification
_SOURCE_KEYWORDS = {
    "gcr": "GCR",
    "galactic": "GCR",
    "cosmic_ray": "GCR",
    "cosmic": "GCR",
    "solar": "SPE",
    "spe": "SPE",
    "sep": "SPE",
    "flare": "SPE",
    "cme": "SPE",
    "proton_belt": "TRAPPED_PROTON",
    "inner_belt": "TRAPPED_PROTON",
    "saa": "TRAPPED_PROTON",
    "electron_belt": "TRAPPED_ELECTRON",
    "outer_belt": "TRAPPED_ELECTRON",
    "neutron": "NEUTRON",
    "albedo": "NEUTRON",
}

# ---------------------------------------------------------------------------
# Dose limit tables (§11.4)
#
# Short-term organ-dose limits (mGy-Eq) paraphrased from ECSS-E-ST-10C §11.4
# and referenced ESA/ICRP crew exposure frameworks.
# ---------------------------------------------------------------------------

SHORT_TERM_ORGAN_LIMITS = {
    "30d": {
        "BFO": 250.0,
        "eye_lens": 1000.0,
        "skin": 1500.0,
    },
    "annual": {
        "BFO": 500.0,
        "eye_lens": 2000.0,
        "skin": 6000.0,
    },
}

VALID_ORGANS = frozenset(SHORT_TERM_ORGAN_LIMITS["30d"].keys())
VALID_PERIODS = frozenset(SHORT_TERM_ORGAN_LIMITS.keys())

# Career BFO effective-dose limits (mSv) indexed by (sex, age_bracket).
# Paraphrased from ECSS-E-ST-10C §11.4 career limit table and ESA astronaut
# medical standards; values representative of publicly documented ESA limits.
_CAREER_BFO_LIMITS = {
    ("M", "25-35"): 1500,
    ("M", "35-45"): 2500,
    ("M", "45-55"): 3000,
    ("M", "55+"): 4000,
    ("F", "25-35"): 1000,
    ("F", "35-45"): 1750,
    ("F", "45-55"): 2500,
    ("F", "55+"): 3000,
}

VALID_SEXES = frozenset({"M", "F"})


# ---------------------------------------------------------------------------
# Environment identification (§11.3)
# ---------------------------------------------------------------------------

def categorize_environment(source_description):
    """
    Map a radiation source description string to one of the five environment
    categories defined in §11.3.

    Returns the category key (e.g. 'GCR', 'SPE').
    Raises TypeError for non-string input.
    Raises ValueError for unrecognized source strings.
    """
    if not isinstance(source_description, str):
        raise TypeError(
            "source_description must be a string, got "
            + type(source_description).__name__
        )
    key = source_description.strip().lower().replace(" ", "_").replace("-", "_")
    if key in _SOURCE_KEYWORDS:
        return _SOURCE_KEYWORDS[key]
    # Partial-match fallback: any keyword that is a substring of the key
    for keyword, category in _SOURCE_KEYWORDS.items():
        if keyword in key:
            return category
    raise ValueError(
        "Unrecognized radiation source: {!r}. Known sources: {}".format(
            source_description, sorted(_SOURCE_KEYWORDS)
        )
    )


def assess_orbit_environments(altitude_km, inclination_deg):
    """
    Determine which radiation environments are applicable to a crewed orbit.

    Rules (§11.3 paraphrase):
    - GCR and NEUTRON: always applicable to crewed missions.
    - TRAPPED_PROTON: applicable at altitude <= 10 000 km (inner belt / SAA).
    - TRAPPED_ELECTRON: applicable at 1 500 km <= altitude <= 65 000 km.
    - SPE: applicable at inclination >= 50° (polar-horn access) or
      altitude > 70 000 km (beyond magnetosphere).

    Returns a sorted list of applicable environment category keys.
    Raises ValueError for out-of-range inputs.
    """
    if not isinstance(altitude_km, (int, float)) or altitude_km <= 0:
        raise ValueError(
            "altitude_km must be a positive number, got {!r}".format(altitude_km)
        )
    if not isinstance(inclination_deg, (int, float)) or not (
        0.0 <= inclination_deg <= 180.0
    ):
        raise ValueError(
            "inclination_deg must be in [0, 180], got {!r}".format(inclination_deg)
        )

    envs = {"GCR", "NEUTRON"}

    if altitude_km <= 10000.0:
        envs.add("TRAPPED_PROTON")

    if 1500.0 <= altitude_km <= 65000.0:
        envs.add("TRAPPED_ELECTRON")

    if inclination_deg >= 50.0 or altitude_km > 70000.0:
        envs.add("SPE")

    return sorted(envs)


# ---------------------------------------------------------------------------
# Age bracket helper
# ---------------------------------------------------------------------------

def age_bracket(age):
    """
    Return the age-bracket string used to look up career BFO limits.

    age must be an int >= 18. Raises ValueError otherwise.
    """
    if not isinstance(age, int) or age < 18:
        raise ValueError(
            "age must be an integer >= 18, got {!r}".format(age)
        )
    if age < 35:
        return "25-35"
    if age < 45:
        return "35-45"
    if age < 55:
        return "45-55"
    return "55+"


# ---------------------------------------------------------------------------
# Career BFO limit (§11.4)
# ---------------------------------------------------------------------------

def career_bfo_limit_mSv(sex, age):
    """
    Return the career BFO effective-dose limit (mSv) for a crew member.

    sex: 'M' or 'F'
    age: integer >= 18
    Raises ValueError for unknown sex or out-of-range age.
    """
    if sex not in VALID_SEXES:
        raise ValueError(
            "sex must be 'M' or 'F', got {!r}".format(sex)
        )
    bracket = age_bracket(age)
    return float(_CAREER_BFO_LIMITS[(sex, bracket)])


# ---------------------------------------------------------------------------
# Dose limit checks (§11.4)
# ---------------------------------------------------------------------------

def check_short_term_dose(organ, dose_mGy_Eq, period):
    """
    Check an organ-equivalent dose against the short-term limit for the given
    accumulation period.

    organ: 'BFO', 'eye_lens', or 'skin'
    dose_mGy_Eq: non-negative float (mGy-Eq)
    period: '30d' or 'annual'

    Returns a dict:
        organ          - str
        period         - str
        dose_mGy_Eq    - float
        limit_mGy_Eq   - float
        compliant      - bool (True when dose <= limit)
        margin_mGy_Eq  - float (positive = headroom; negative = exceedance)

    Raises ValueError for unknown organ, period, or negative dose.
    """
    if organ not in VALID_ORGANS:
        raise ValueError(
            "Unknown organ {!r}. Valid organs: {}".format(
                organ, sorted(VALID_ORGANS)
            )
        )
    if period not in VALID_PERIODS:
        raise ValueError(
            "Unknown period {!r}. Valid periods: {}".format(
                period, sorted(VALID_PERIODS)
            )
        )
    if not isinstance(dose_mGy_Eq, (int, float)) or dose_mGy_Eq < 0:
        raise ValueError(
            "dose_mGy_Eq must be non-negative, got {!r}".format(dose_mGy_Eq)
        )

    limit = SHORT_TERM_ORGAN_LIMITS[period][organ]
    margin = limit - dose_mGy_Eq
    return {
        "organ": organ,
        "period": period,
        "dose_mGy_Eq": float(dose_mGy_Eq),
        "limit_mGy_Eq": limit,
        "compliant": dose_mGy_Eq <= limit,
        "margin_mGy_Eq": margin,
    }


def check_career_bfo_dose(career_dose_mSv, sex, age):
    """
    Check a crew member's accumulated career BFO effective dose against the
    career limit from §11.4.

    career_dose_mSv: non-negative float (mSv)
    sex: 'M' or 'F'
    age: integer >= 18

    Returns a dict:
        career_dose_mSv - float
        limit_mSv       - float
        sex             - str
        age             - int
        compliant       - bool
        margin_mSv      - float (positive = headroom; negative = exceedance)
    """
    if not isinstance(career_dose_mSv, (int, float)) or career_dose_mSv < 0:
        raise ValueError(
            "career_dose_mSv must be non-negative, got {!r}".format(career_dose_mSv)
        )
    limit = career_bfo_limit_mSv(sex, age)
    margin = limit - career_dose_mSv
    return {
        "career_dose_mSv": float(career_dose_mSv),
        "limit_mSv": limit,
        "sex": sex,
        "age": age,
        "compliant": career_dose_mSv <= limit,
        "margin_mSv": margin,
    }


# ---------------------------------------------------------------------------
# Full crew member assessment
# ---------------------------------------------------------------------------

def assess_crew_member(profile):
    """
    Run a full §11.3–11.4 protection assessment for one crew member.

    profile dict keys:
        sex              (str): 'M' or 'F'
        age              (int): current age in years
        career_bfo_mSv   (float): accumulated career BFO effective dose
        doses            (dict): {
            '30d':     {'BFO': float, 'eye_lens': float, 'skin': float},
            'annual':  {'BFO': float, 'eye_lens': float, 'skin': float},
        }

    Returns:
        {
            'findings':     list of non-compliant result dicts,
            'all_compliant': bool,
            'career':       career check result dict,
            'short_term':   list of short-term check result dicts,
        }

    Raises ValueError if required profile keys are absent.
    """
    required = {"sex", "age", "career_bfo_mSv", "doses"}
    missing = required - set(profile.keys())
    if missing:
        raise ValueError(
            "profile is missing required keys: {}".format(sorted(missing))
        )

    career_result = check_career_bfo_dose(
        profile["career_bfo_mSv"], profile["sex"], profile["age"]
    )

    short_term_results = []
    for period, organ_doses in profile["doses"].items():
        for organ, dose in organ_doses.items():
            r = check_short_term_dose(organ, dose, period)
            short_term_results.append(r)

    findings = [r for r in short_term_results if not r["compliant"]]
    if not career_result["compliant"]:
        findings.append(career_result)

    return {
        "findings": findings,
        "all_compliant": len(findings) == 0,
        "career": career_result,
        "short_term": short_term_results,
    }
