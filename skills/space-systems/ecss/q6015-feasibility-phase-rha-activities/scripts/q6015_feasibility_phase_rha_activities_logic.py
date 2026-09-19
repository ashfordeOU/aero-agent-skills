"""Feasibility-phase radiation environment definition and first requirement set.

Anchor: ECSS-Q-ST-60-15C clause 4.4.1 (what the feasibility study owes the
radiation hardness assurance thread). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the candidate orbit and place it in an environment regime.
2. Name the environment components that regime actually contributes, so a
   later analysis cannot silently drop one.
3. Accumulate the mission ionising dose behind the feasibility reference
   shielding over the mission duration under a declared solar-activity
   assumption.
4. Apply the feasibility design factor to obtain the first, coarse part-level
   total-dose requirement, and read the single-event linear-energy-transfer
   threshold the regime demands.
5. Grade the feasibility deliverable set and return the findings.
"""

import math

__all__ = [
    "LEO_CEILING_KM",
    "MEO_CEILING_KM",
    "GEO_ALTITUDE_KM",
    "REFERENCE_SHIELDING_MM_AL",
    "ORBIT_REGIMES",
    "ENVIRONMENT_COMPONENTS",
    "REFERENCE_DOSE_RATE_KRAD_PER_YEAR",
    "SOLAR_ACTIVITY_WEIGHT",
    "SEE_LET_THRESHOLD_MEV_CM2_MG",
    "FEASIBILITY_DELIVERABLES",
    "MIN_DESIGN_FACTOR",
    "validate_orbit",
    "categorize_orbit_regime",
    "environment_components",
    "reference_dose_rate",
    "solar_activity_weight",
    "mission_dose_krad",
    "preliminary_tid_requirement_krad",
    "see_let_threshold",
    "missing_feasibility_deliverables",
    "assess_feasibility_phase",
]

LEO_CEILING_KM = 2000.0
MEO_CEILING_KM = 25000.0
GEO_ALTITUDE_KM = 35786.0
GEO_BAND_KM = 500.0
GEO_INCLINATION_LIMIT_DEG = 15.0
INTERPLANETARY_APOGEE_KM = 400000.0
POLAR_INCLINATION_DEG = 55.0

# The feasibility study fixes one reference shielding thickness so that two
# candidate orbits are compared on the same basis.
REFERENCE_SHIELDING_MM_AL = 2.5

ORBIT_REGIMES = (
    "leo-low-inclination",
    "leo-polar",
    "meo",
    "geo",
    "heo-belt-crossing",
    "interplanetary",
)

ENVIRONMENT_COMPONENTS = {
    "leo-low-inclination": ("trapped-protons", "galactic-cosmic-rays"),
    "leo-polar": (
        "trapped-protons",
        "trapped-electrons",
        "solar-particle-events",
        "galactic-cosmic-rays",
    ),
    "meo": (
        "trapped-protons",
        "trapped-electrons",
        "solar-particle-events",
        "galactic-cosmic-rays",
    ),
    "geo": ("trapped-electrons", "solar-particle-events", "galactic-cosmic-rays"),
    "heo-belt-crossing": (
        "trapped-protons",
        "trapped-electrons",
        "solar-particle-events",
        "galactic-cosmic-rays",
    ),
    "interplanetary": ("solar-particle-events", "galactic-cosmic-rays"),
}

# Coarse feasibility dose rates behind the reference shielding, krad(Si)/year.
REFERENCE_DOSE_RATE_KRAD_PER_YEAR = {
    "leo-low-inclination": 0.2,
    "leo-polar": 1.0,
    "meo": 60.0,
    "geo": 10.0,
    "heo-belt-crossing": 35.0,
    "interplanetary": 3.0,
}

# A mission flown through solar minimum sees a harder particle environment for
# the same duration than one flown through solar maximum.
SOLAR_ACTIVITY_WEIGHT = {
    "solar-minimum": 1.3,
    "cycle-averaged": 1.0,
    "solar-maximum": 0.8,
}

# Destructive single-event immunity threshold demanded of parts, MeV*cm2/mg.
SEE_LET_THRESHOLD_MEV_CM2_MG = {
    "leo-low-inclination": 37.0,
    "leo-polar": 60.0,
    "meo": 60.0,
    "geo": 60.0,
    "heo-belt-crossing": 60.0,
    "interplanetary": 60.0,
}

FEASIBILITY_DELIVERABLES = (
    "mission-radiation-environment-definition",
    "preliminary-total-dose-requirement",
    "preliminary-single-event-requirement",
    "radiation-critical-function-list",
    "reference-shielding-assumption-record",
)

# A requirement written without a factor above unity leaves no room at all for
# the environment model uncertainty the feasibility phase still carries.
MIN_DESIGN_FACTOR = 1.0


def _positive_number(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def validate_orbit(perigee_km, apogee_km, inclination_deg):
    """Return the validated (perigee, apogee, inclination) of a candidate orbit."""
    perigee = _positive_number("perigee_km", perigee_km)
    apogee = _positive_number("apogee_km", apogee_km)
    if not isinstance(inclination_deg, (int, float)) or isinstance(inclination_deg, bool):
        raise ValueError("inclination_deg must be a real number")
    inclination = float(inclination_deg)
    if not math.isfinite(inclination):
        raise ValueError("inclination_deg must be finite")
    if inclination < 0.0 or inclination > 180.0:
        raise ValueError("inclination_deg must lie in [0, 180], got %g" % inclination)
    if perigee > apogee:
        raise ValueError("perigee_km %g exceeds apogee_km %g" % (perigee, apogee))
    return (perigee, apogee, inclination)


def categorize_orbit_regime(perigee_km, apogee_km, inclination_deg):
    """Return the environment regime a candidate orbit belongs to."""
    perigee, apogee, inclination = validate_orbit(perigee_km, apogee_km, inclination_deg)
    if apogee > INTERPLANETARY_APOGEE_KM:
        return "interplanetary"
    if apogee <= LEO_CEILING_KM:
        if inclination < POLAR_INCLINATION_DEG:
            return "leo-low-inclination"
        return "leo-polar"
    if perigee <= LEO_CEILING_KM:
        return "heo-belt-crossing"
    if (
        abs(apogee - GEO_ALTITUDE_KM) <= GEO_BAND_KM
        and abs(perigee - GEO_ALTITUDE_KM) <= GEO_BAND_KM
        and inclination <= GEO_INCLINATION_LIMIT_DEG
    ):
        return "geo"
    if apogee <= MEO_CEILING_KM:
        return "meo"
    return "heo-belt-crossing"


def _known_regime(regime):
    if not isinstance(regime, str):
        raise ValueError("regime must be a string, got %r" % (regime,))
    key = regime.strip().lower()
    if key not in ENVIRONMENT_COMPONENTS:
        raise ValueError("unknown environment regime %r" % (regime,))
    return key


def environment_components(regime):
    """Return the environment components a regime contributes."""
    return ENVIRONMENT_COMPONENTS[_known_regime(regime)]


def reference_dose_rate(regime):
    """Return the feasibility dose rate behind the reference shielding."""
    return REFERENCE_DOSE_RATE_KRAD_PER_YEAR[_known_regime(regime)]


def solar_activity_weight(assumption):
    """Return the duration weighting of a declared solar-activity assumption."""
    if not isinstance(assumption, str):
        raise ValueError("solar activity assumption must be a string")
    key = assumption.strip().lower().replace("_", "-").replace(" ", "-")
    if key not in SOLAR_ACTIVITY_WEIGHT:
        raise ValueError(
            "unknown solar-activity assumption %r; expected one of %s"
            % (assumption, ", ".join(sorted(SOLAR_ACTIVITY_WEIGHT)))
        )
    return SOLAR_ACTIVITY_WEIGHT[key]


def mission_dose_krad(regime, duration_years, solar_assumption="cycle-averaged"):
    """Return the mission ionising dose behind the reference shielding."""
    years = _positive_number("duration_years", duration_years)
    return reference_dose_rate(regime) * years * solar_activity_weight(solar_assumption)


def preliminary_tid_requirement_krad(mission_dose, design_factor):
    """Apply the feasibility design factor to obtain the first dose requirement."""
    dose = _positive_number("mission_dose", mission_dose)
    if not isinstance(design_factor, (int, float)) or isinstance(design_factor, bool):
        raise ValueError("design_factor must be a real number")
    factor = float(design_factor)
    if not math.isfinite(factor):
        raise ValueError("design_factor must be finite")
    if factor < MIN_DESIGN_FACTOR and not math.isclose(
        factor, MIN_DESIGN_FACTOR, rel_tol=0.0, abs_tol=1e-12
    ):
        raise ValueError(
            "design_factor must be at least %g, got %g" % (MIN_DESIGN_FACTOR, factor)
        )
    return dose * factor


def see_let_threshold(regime):
    """Return the destructive single-event immunity threshold for a regime."""
    return SEE_LET_THRESHOLD_MEV_CM2_MG[_known_regime(regime)]


def missing_feasibility_deliverables(declared):
    """Return the feasibility deliverables absent from a declared set."""
    if not isinstance(declared, (list, tuple, set, frozenset)):
        raise ValueError("declared deliverables must be a sequence")
    present = set()
    for item in declared:
        if not isinstance(item, str):
            raise ValueError("deliverable must be a string, got %r" % (item,))
        key = item.strip().lower().replace("_", "-").replace(" ", "-")
        if not key:
            raise ValueError("deliverable must not be empty")
        present.add(key)
    return [item for item in FEASIBILITY_DELIVERABLES if item not in present]


def assess_feasibility_phase(spec):
    """Run the clause 4.4.1 feasibility assessment for one candidate mission.

    spec keys: perigee_km, apogee_km, inclination_deg, duration_years,
    design_factor, optional solar_assumption and deliverables.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "perigee_km",
        "apogee_km",
        "inclination_deg",
        "duration_years",
        "design_factor",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    regime = categorize_orbit_regime(
        spec["perigee_km"], spec["apogee_km"], spec["inclination_deg"]
    )
    solar = spec.get("solar_assumption", "cycle-averaged")
    dose = mission_dose_krad(regime, spec["duration_years"], solar)
    requirement = preliminary_tid_requirement_krad(dose, spec["design_factor"])
    missing = missing_feasibility_deliverables(spec.get("deliverables", ()))
    findings = []
    for item in missing:
        findings.append("feasibility deliverable %s is not declared" % item)
    if "trapped-electrons" in ENVIRONMENT_COMPONENTS[regime] and regime != "geo":
        findings.append(
            "regime %s crosses the electron belt; the reference shielding assumption "
            "of %g mm aluminium has to be revisited in the next phase"
            % (regime, REFERENCE_SHIELDING_MM_AL)
        )
    return {
        "regime": regime,
        "environment_components": list(ENVIRONMENT_COMPONENTS[regime]),
        "reference_shielding_mm_al": REFERENCE_SHIELDING_MM_AL,
        "solar_assumption": solar.strip().lower().replace("_", "-").replace(" ", "-"),
        "mission_dose_krad": dose,
        "preliminary_tid_requirement_krad": requirement,
        "see_let_threshold_mev_cm2_mg": see_let_threshold(regime),
        "missing_deliverables": missing,
        "complete": not missing,
        "findings": findings,
    }
