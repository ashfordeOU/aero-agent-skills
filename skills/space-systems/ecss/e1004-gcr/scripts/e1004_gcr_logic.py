#!/usr/bin/env python3
"""ECSS-E-ST-10-04C clause 9.2.3 galactic cosmic ray (GCR) model
selection and solar modulation logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): GCR
flux is a background of galactic protons and heavier ions whose flux
at a given epoch is suppressed by solar activity (modulation), so flux
is highest at solar minimum and lowest at solar maximum. SEE analyses
need the full heavy-ion species set evaluated at the solar-minimum
worst case; dose analyses need a narrower species set integrated over
the mission's solar-cycle exposure. This module implements the
model-selection, species-coverage, solar-condition classification,
solar-modulation scaling, and compliance logic; it does not implement
geomagnetic shielding of the incident flux (see the sibling
e1004-stormer leaf) or the radiation environment specification roll-up
(see the sibling e1004-rad-env-spec leaf).
"""

MODEL_BY_ANALYSIS_TYPE = {
    "see": "CREME96-class heavy-ion spectra model",
    "dose": "Badhwar-ONeill-class integral dose/LET model",
}

REQUIRED_MAX_SPECIES_Z = {
    "see": 92,
    "dose": 28,
}

WORST_CASE_SOLAR_CONDITION = {
    "see": "solar_minimum",
    "dose": "mission_cycle_average",
}

SOLAR_MIN_POTENTIAL_MV = 500.0
SOLAR_MAX_POTENTIAL_MV = 1100.0


def select_gcr_model(analysis_type):
    """Reference GCR model name for one analysis type ("see" or
    "dose"). Raises ValueError for an unknown analysis type."""
    if analysis_type not in MODEL_BY_ANALYSIS_TYPE:
        raise ValueError("unknown analysis type: %r" % (analysis_type,))
    return MODEL_BY_ANALYSIS_TYPE[analysis_type]


def required_max_species_z(analysis_type):
    """Minimum maximum-ion-charge-number coverage required for one
    analysis type. Raises ValueError for an unknown analysis type."""
    if analysis_type not in REQUIRED_MAX_SPECIES_Z:
        raise ValueError("unknown analysis type: %r" % (analysis_type,))
    return REQUIRED_MAX_SPECIES_Z[analysis_type]


def species_coverage_adequate(analysis_type, species_max_z):
    """True when species_max_z meets or exceeds the minimum ion
    species coverage required for analysis_type."""
    return species_max_z >= required_max_species_z(analysis_type)


def worst_case_solar_condition(analysis_type):
    """Solar condition (or exposure treatment) required for one
    analysis type: solar minimum for SEE worst-case peak flux, the
    full mission solar-cycle exposure for cumulative dose. Raises
    ValueError for an unknown analysis type."""
    if analysis_type not in WORST_CASE_SOLAR_CONDITION:
        raise ValueError("unknown analysis type: %r" % (analysis_type,))
    return WORST_CASE_SOLAR_CONDITION[analysis_type]


def classify_solar_condition(modulation_potential):
    """Classify a solar modulation potential (MV) into "solar_minimum"
    (at or below the solar-minimum reference potential),
    "solar_maximum" (at or above the solar-maximum reference
    potential), or "intermediate". Raises ValueError when the
    potential is not positive."""
    if modulation_potential <= 0:
        raise ValueError("modulation potential must be positive")
    if modulation_potential <= SOLAR_MIN_POTENTIAL_MV:
        return "solar_minimum"
    if modulation_potential >= SOLAR_MAX_POTENTIAL_MV:
        return "solar_maximum"
    return "intermediate"


def modulation_scale_factor(modulation_potential):
    """Scale factor applied to the solar-minimum reference GCR flux to
    obtain the flux at an arbitrary modulation potential: inversely
    proportional to the potential, normalized so the solar-minimum
    reference potential itself gives a factor of 1.0. Raises
    ValueError when the potential is not positive."""
    if modulation_potential <= 0:
        raise ValueError("modulation potential must be positive")
    return SOLAR_MIN_POTENTIAL_MV / modulation_potential


def apply_solar_modulation(reference_flux, modulation_potential):
    """Flux at modulation_potential obtained by scaling the
    solar-minimum reference_flux by modulation_scale_factor(). Raises
    ValueError when reference_flux is negative."""
    if reference_flux < 0:
        raise ValueError("reference flux must not be negative")
    return reference_flux * modulation_scale_factor(modulation_potential)


def assess_gcr_case(case):
    """Full GCR model-selection and compliance assessment for one case
    dict. Required keys: id, analysis_type, species_max_z,
    modulation_potential, reference_flux. Returns a new dict; does not
    mutate the input. Raises ValueError when 'id' is missing or
    analysis_type is unknown."""
    if "id" not in case:
        raise ValueError("GCR case is missing an id")
    analysis_type = case["analysis_type"]
    model = select_gcr_model(analysis_type)
    species_max_z = case["species_max_z"]
    species_ok = species_coverage_adequate(analysis_type, species_max_z)
    solar_condition = classify_solar_condition(case["modulation_potential"])
    required_condition = worst_case_solar_condition(analysis_type)
    scaled_flux = apply_solar_modulation(
        case["reference_flux"], case["modulation_potential"]
    )
    condition_ok = (
        required_condition != "solar_minimum" or solar_condition == "solar_minimum"
    )
    return {
        "id": case["id"],
        "analysis_type": analysis_type,
        "model": model,
        "species_max_z": species_max_z,
        "species_coverage_adequate": species_ok,
        "solar_condition": solar_condition,
        "required_solar_condition": required_condition,
        "solar_condition_adequate": condition_ok,
        "scaled_flux": scaled_flux,
        "compliant": species_ok and condition_ok,
    }


def build_gcr_assessment(cases):
    """Assessment record: one assess_gcr_case() result per case, in
    input order. Raises ValueError on a duplicate case id."""
    record = []
    seen_ids = set()
    for case in cases:
        assessment = assess_gcr_case(case)
        if assessment["id"] in seen_ids:
            raise ValueError("duplicate GCR case id: %r" % (assessment["id"],))
        seen_ids.add(assessment["id"])
        record.append(assessment)
    return record


def noncompliant_items(record):
    """Case ids in the record that are not compliant, in record
    order -- these cannot support the radiation environment
    specification as-is."""
    return [entry["id"] for entry in record if not entry["compliant"]]


def all_compliant(record):
    """True when every entry in the assessment record is compliant."""
    return len(noncompliant_items(record)) == 0
