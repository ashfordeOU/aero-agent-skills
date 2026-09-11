#!/usr/bin/env python3
"""ECSS-E-ST-10-12C §4 radiation evaluation framework — effect-type
categorisation, stage-activity lookup, parameter-unit validation, and
evaluation-completeness checking (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
radiation evaluation standard's §4 defines which radiation effect types
apply to a component, which evaluation activities are required at each
project phase (stage-activity table), and the parameters and units used
to quantify the radiation environment and its effects. Radiation effects
are grouped by physical mechanism — total ionising dose (cumulative
charge deposition), displacement damage (atomic lattice disruption),
single-event effects (single-particle-induced upsets or damage), and
enhanced low dose rate sensitivity (a bipolar-specific TID variant).
This module implements effect-type categorisation, per-stage required-
activity lookup, parameter-unit validation, and evaluation-completeness
gap checking; it does not implement the numerical radiation environment
models themselves.
"""

# ------------------------------------------------------------------ #
# Radiation effect categories (§4 Table 4-1 paraphrase)              #
# ------------------------------------------------------------------ #

# TID: cumulative ionisation deposited in a material over the mission
TOTAL_IONISING_DOSE_TYPES = frozenset({
    "tid",
    "total_ionising_dose",
    "tid_silicon",
    "tid_gaas",
})

# DD: cumulative atomic displacement from non-ionising energy loss
DISPLACEMENT_DAMAGE_TYPES = frozenset({
    "dd",
    "displacement_damage",
    "dd_proton",
    "dd_neutron",
    "dd_electron",
})

# SEE: single-particle event causing functional or destructive effect
SINGLE_EVENT_EFFECT_TYPES = frozenset({
    "see",    # generic single event effect reference
    "seu",    # single event upset — bit flip
    "sel",    # single event latchup
    "set",    # single event transient
    "sefi",   # single event functional interrupt
    "sehe",   # single event hard error
})

# ELDRS: enhanced low dose rate sensitivity (bipolar-device TID variant)
ENHANCED_LOW_DOSE_RATE_TYPES = frozenset({
    "eldrs",
    "enhanced_low_dose_rate_sensitivity",
})

EFFECT_CATEGORIES = {
    "total_ionising_dose": TOTAL_IONISING_DOSE_TYPES,
    "displacement_damage": DISPLACEMENT_DAMAGE_TYPES,
    "single_event_effect": SINGLE_EVENT_EFFECT_TYPES,
    "enhanced_low_dose_rate": ENHANCED_LOW_DOSE_RATE_TYPES,
}

# ------------------------------------------------------------------ #
# Stage-activity table (§4 Table 4-1 paraphrase)                     #
# ------------------------------------------------------------------ #

_PHASE_A_ACTIVITIES = frozenset({
    "environment_scoping",
    "preliminary_sensitivity_screening",
})

_PHASE_B_ACTIVITIES = frozenset({
    "environment_estimate",
    "technology_screening",
    "preliminary_shielding_study",
    "candidate_component_list",
})

_PHASE_CD_ACTIVITIES = frozenset({
    "detailed_environment_specification",
    "component_radiation_analysis",
    "shielding_analysis",
    "radiation_test_programme",
    "qualification_evidence",
    "radiation_design_margin_verification",
})

_PHASE_E_ACTIVITIES = frozenset({
    "in_flight_monitoring",
    "anomaly_radiation_assessment",
    "residual_margin_verification",
})

_PHASE_F_ACTIVITIES = frozenset({
    "end_of_life_dose_verification",
})

STAGE_REQUIRED_ACTIVITIES = {
    "phase_a":  _PHASE_A_ACTIVITIES,
    "phase_b":  _PHASE_B_ACTIVITIES,
    "phase_cd": _PHASE_CD_ACTIVITIES,
    "phase_e":  _PHASE_E_ACTIVITIES,
    "phase_f":  _PHASE_F_ACTIVITIES,
}

# ------------------------------------------------------------------ #
# Parameter / unit table (§4 Table 4-2 paraphrase)                   #
# ------------------------------------------------------------------ #

PARAMETER_UNITS = {
    # TID parameters
    "total_ionising_dose":       frozenset({"rad_si", "gy_si", "krad_si"}),
    # DD parameters
    "niel_dose":                 frozenset({"mev_g", "mev_cm2_g"}),
    "proton_fluence_equivalent": frozenset({"cm2_inverse", "protons_cm2"}),
    # SEE parameters
    "let_threshold":             frozenset({"mev_cm2_mg"}),
    "saturation_cross_section":  frozenset({"cm2", "cm2_device", "cm2_bit"}),
    "event_rate":                frozenset({"events_device_s", "events_bit_s", "upsets_day"}),
    # ELDRS parameters — same unit as TID but distinct parameter name
    # to force explicit identification of the low-dose-rate variant
    "eldrs_sensitivity_dose":    frozenset({"rad_si", "gy_si"}),
}


# ------------------------------------------------------------------ #
# Core functions                                                      #
# ------------------------------------------------------------------ #

def categorize_effect(effect_type):
    """Radiation effect category for an effect type: one of
    "total_ionising_dose", "displacement_damage", "single_event_effect",
    "enhanced_low_dose_rate". Raises ValueError for an unrecognized type."""
    for category, members in EFFECT_CATEGORIES.items():
        if effect_type in members:
            return category
    raise ValueError(
        "unrecognized radiation effect type %r under "
        "ECSS-E-ST-10-12C §4" % (effect_type,)
    )


def stage_required_activities(stage):
    """Frozenset of evaluation activities required at a given project
    stage (Table 4-1 paraphrase). Raises ValueError for an unknown stage.
    Valid stages: phase_a, phase_b, phase_cd, phase_e, phase_f."""
    if stage not in STAGE_REQUIRED_ACTIVITIES:
        raise ValueError(
            "unknown project stage %r; expected one of %s"
            % (stage, sorted(STAGE_REQUIRED_ACTIVITIES))
        )
    return frozenset(STAGE_REQUIRED_ACTIVITIES[stage])


def validate_parameter_unit(parameter, unit):
    """True when unit is an accepted unit for parameter (Table 4-2
    paraphrase). Raises ValueError for an unknown parameter. Returns
    False (does not raise) when the parameter is known but the unit is
    not listed."""
    if parameter not in PARAMETER_UNITS:
        raise ValueError(
            "unknown parameter %r; not listed in the §4 radiation "
            "evaluation parameter table" % (parameter,)
        )
    return unit in PARAMETER_UNITS[parameter]


def evaluation_gaps(stage, activities_performed):
    """Sorted list of activities required at stage but absent from
    activities_performed. An empty list means the stage is fully covered.
    Raises ValueError for an unknown stage."""
    required = stage_required_activities(stage)
    return sorted(required - frozenset(activities_performed))


def full_evaluation_review(component_record):
    """Full §4 principle review for one component record.

    component_record: {
      "component_id": str,
      "project_stage": str,
      "effect_types": [str, ...],
      "activities_performed": [str, ...],
      "parameters": [{"parameter": str, "unit": str, "value": float}, ...]
    }

    Returns {"categorization_errors": [...], "activity_gaps": [...],
    "parameter_unit_issues": [...]}. Each list is empty when compliant
    for that dimension. Raises ValueError for an unknown project_stage.
    Does not mutate component_record."""
    component_id = component_record["component_id"]

    categorization_errors = []
    for et in component_record.get("effect_types", []):
        try:
            categorize_effect(et)
        except ValueError as exc:
            categorization_errors.append(
                {
                    "component": component_id,
                    "effect_type": et,
                    "issue": str(exc),
                }
            )

    activity_gaps = evaluation_gaps(
        component_record["project_stage"],
        component_record.get("activities_performed", []),
    )

    parameter_unit_issues = []
    for entry in component_record.get("parameters", []):
        pname = entry["parameter"]
        unit = entry["unit"]
        try:
            if not validate_parameter_unit(pname, unit):
                parameter_unit_issues.append(
                    {
                        "component": component_id,
                        "parameter": pname,
                        "unit": unit,
                        "issue": "invalid_unit_for_parameter",
                    }
                )
        except ValueError as exc:
            parameter_unit_issues.append(
                {
                    "component": component_id,
                    "parameter": pname,
                    "unit": unit,
                    "issue": str(exc),
                }
            )

    return {
        "categorization_errors": categorization_errors,
        "activity_gaps": activity_gaps,
        "parameter_unit_issues": parameter_unit_issues,
    }


def is_evaluation_compliant(review):
    """True when all three dimensions of a full_evaluation_review result
    are empty — the component record satisfies §4 for this assessment."""
    return all(len(v) == 0 for v in review.values())
