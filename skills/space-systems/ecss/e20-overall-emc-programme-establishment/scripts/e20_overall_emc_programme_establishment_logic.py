#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.2.1 establishment of the overall
electromagnetic compatibility programme (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires the supplier to set up an
electromagnetic compatibility programme that covers the compatibility
activities at spacecraft level, names who runs them and when they are
established, and applies an interference safety margin policy to the
circuits that carry the risk. This module implements the checkable part
of that clause: mapping a declared activity onto the programme area it
serves, deriving the area set a given mission profile actually requires
(radio frequency payload, ordnance, magnetic sensor, crewed element,
launch-site and launcher exposure), listing the areas and the mandatory
programme elements that are absent, checking each activity names an
owner and an establishment milestone no later than the area allows,
computing the interference safety margin in decibels between a
susceptibility threshold and a predicted interference level, and
comparing it against the margin the circuit category demands. It does
not size a shield, does not predict a coupling path, and does not
write the control plan.
"""

import math

# Programme milestones in chronological order.
PROGRAMME_MILESTONES = ("SRR", "PDR", "CDR", "QR", "AR")

# Spacecraft-level compatibility areas the programme can cover.
PROGRAMME_AREAS = (
    "emission_control",
    "susceptibility_control",
    "grounding_and_bonding",
    "shielding_and_harness_routing",
    "electrostatic_discharge_control",
    "magnetic_cleanliness",
    "radio_frequency_compatibility",
    "electromagnetic_radiation_hazard",
    "lightning_and_launch_site_compatibility",
    "intersystem_compatibility_with_launcher",
)

# Declared activity -> the programme area it serves.
ACTIVITY_AREAS = {
    "conducted_emission_control": "emission_control",
    "radiated_emission_control": "emission_control",
    "conducted_susceptibility_control": "susceptibility_control",
    "radiated_susceptibility_control": "susceptibility_control",
    "grounding_concept_definition": "grounding_and_bonding",
    "bonding_implementation_control": "grounding_and_bonding",
    "shield_termination_rules": "shielding_and_harness_routing",
    "harness_segregation_rules": "shielding_and_harness_routing",
    "electrostatic_discharge_control_measures": "electrostatic_discharge_control",
    "magnetic_moment_control": "magnetic_cleanliness",
    "transmitter_receiver_compatibility": "radio_frequency_compatibility",
    "protected_band_emission_control": "radio_frequency_compatibility",
    "ordnance_radiation_hazard_control": "electromagnetic_radiation_hazard",
    "personnel_radiation_hazard_control": "electromagnetic_radiation_hazard",
    "lightning_protection_provision": "lightning_and_launch_site_compatibility",
    "launch_site_compatibility_survey": "lightning_and_launch_site_compatibility",
    "launcher_intersystem_compatibility": "intersystem_compatibility_with_launcher",
}

# Areas every spacecraft-level programme carries, whatever the payload.
BASELINE_AREAS = frozenset(
    {
        "emission_control",
        "susceptibility_control",
        "grounding_and_bonding",
        "shielding_and_harness_routing",
        "electrostatic_discharge_control",
    }
)

# Mission profile flag -> the areas it pulls into the programme.
PROFILE_AREA_TRIGGERS = {
    "carries_radio_frequency_payload": frozenset({"radio_frequency_compatibility"}),
    "carries_ordnance": frozenset({"electromagnetic_radiation_hazard"}),
    "carries_magnetic_sensor": frozenset({"magnetic_cleanliness"}),
    "crewed_element": frozenset({"electromagnetic_radiation_hazard"}),
    "uses_launch_site_services": frozenset(
        {"lightning_and_launch_site_compatibility"}
    ),
    "has_launcher_interface": frozenset({"intersystem_compatibility_with_launcher"}),
}

# Latest milestone at which an area may still be established without
# forcing a redesign of hardware already committed.
AREA_LATEST_ESTABLISHMENT = {
    "emission_control": "PDR",
    "susceptibility_control": "PDR",
    "grounding_and_bonding": "PDR",
    "shielding_and_harness_routing": "CDR",
    "electrostatic_discharge_control": "CDR",
    "magnetic_cleanliness": "CDR",
    "radio_frequency_compatibility": "CDR",
    "electromagnetic_radiation_hazard": "CDR",
    "lightning_and_launch_site_compatibility": "QR",
    "intersystem_compatibility_with_launcher": "QR",
}

# Programme elements the supplier owes whatever the mission profile.
MANDATORY_PROGRAMME_ELEMENTS = frozenset(
    {
        "emc_control_plan",
        "emc_analysis_approach",
        "emc_verification_programme",
        "interference_critical_point_list",
        "emc_requirement_flowdown",
        "named_emc_authority",
    }
)

# Interference safety margin demanded by the criticality of the victim
# circuit, in decibels.
CIRCUIT_CATEGORY_MARGIN_DB = {
    "electro_explosive_device": 20.0,
    "safety_critical": 20.0,
    "mission_critical": 6.0,
    "standard": 6.0,
}

# A margin computed as a difference of decibel values can land a few
# units in the last place under an exactly-satisfied policy. The
# tolerance absorbs the representation error; the policy is unchanged.
MARGIN_REL_TOL = 1e-9
MARGIN_ABS_TOL = 1e-9


def categorize_programme_activity(activity_kind):
    """Programme area served by a declared compatibility activity.
    Raises ValueError for an activity that is not an E-ST-20C clause
    6.2.1 spacecraft-level compatibility activity."""
    area = ACTIVITY_AREAS.get(activity_kind)
    if area is None:
        raise ValueError(
            "unrecognized compatibility activity %r under "
            "E-ST-20C clause 6.2.1" % (activity_kind,)
        )
    return area


def milestone_index(milestone):
    """Chronological index of a programme milestone. Raises ValueError
    for a milestone outside the programme sequence."""
    try:
        return PROGRAMME_MILESTONES.index(milestone)
    except ValueError:
        raise ValueError(
            "unrecognized programme milestone %r (expected one of %s)"
            % (milestone, ", ".join(PROGRAMME_MILESTONES))
        ) from None


def required_programme_areas(profile):
    """Set of compatibility areas the programme must cover for a mission
    profile. profile: mapping of profile flag to bool. Raises ValueError
    for a non-mapping profile, an unrecognized flag or a non-boolean
    flag value."""
    if not isinstance(profile, dict):
        raise ValueError("profile must be a mapping of flag to bool, got %r" % (profile,))
    areas = set(BASELINE_AREAS)
    for flag, value in profile.items():
        if flag not in PROFILE_AREA_TRIGGERS:
            raise ValueError(
                "unrecognized mission profile flag %r for an EMC programme" % (flag,)
            )
        if not isinstance(value, bool):
            raise ValueError(
                "profile flag %r must be a boolean, got %r" % (flag, value)
            )
        if value:
            areas |= PROFILE_AREA_TRIGGERS[flag]
    return frozenset(areas)


def declared_areas(activities):
    """Set of programme areas covered by the declared activities. Raises
    ValueError for an unrecognized activity."""
    return frozenset(
        categorize_programme_activity(a.get("activity_kind")) for a in activities
    )


def missing_programme_areas(activities, profile):
    """Sorted list of required areas no declared activity covers."""
    return sorted(required_programme_areas(profile) - declared_areas(activities))


def missing_programme_elements(declared_elements):
    """Sorted list of mandatory programme elements absent from the
    declaration. An element present with an empty or None value counts
    as absent. Raises ValueError when the declaration is not a
    mapping."""
    if not isinstance(declared_elements, dict):
        raise ValueError(
            "declared_elements must be a mapping of element to value, got %r"
            % (declared_elements,)
        )
    missing = []
    for element in MANDATORY_PROGRAMME_ELEMENTS:
        value = declared_elements.get(element)
        if value is None:
            missing.append(element)
        elif isinstance(value, str) and not value.strip():
            missing.append(element)
        elif value is False:
            missing.append(element)
    return sorted(missing)


def required_margin_db(circuit_category):
    """Interference safety margin in decibels demanded by the victim
    circuit category. Raises ValueError for an unrecognized category."""
    margin = CIRCUIT_CATEGORY_MARGIN_DB.get(circuit_category)
    if margin is None:
        raise ValueError(
            "unrecognized victim circuit category %r for a margin policy"
            % (circuit_category,)
        )
    return margin


def interference_margin_db(susceptibility_threshold_db, interference_level_db):
    """Interference safety margin: the distance in decibels between the
    level a victim circuit tolerates and the level predicted at its
    terminals. Raises ValueError for a non-numeric input."""
    for label, value in (
        ("susceptibility_threshold_db", susceptibility_threshold_db),
        ("interference_level_db", interference_level_db),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number, got %r" % (label, value))
    return float(susceptibility_threshold_db) - float(interference_level_db)


def margin_meets_policy(margin_db, required_db):
    """True when a computed margin satisfies the policy margin. A margin
    that sits a few units in the last place low purely through decibel
    subtraction still passes; a real shortfall does not. Raises
    ValueError for a negative policy margin."""
    if not isinstance(required_db, (int, float)) or isinstance(required_db, bool):
        raise ValueError("required_db must be a real number, got %r" % (required_db,))
    if required_db < 0.0:
        raise ValueError("required_db must not be negative, got %r" % (required_db,))
    if margin_db >= required_db:
        return True
    return math.isclose(
        margin_db, required_db, rel_tol=MARGIN_REL_TOL, abs_tol=MARGIN_ABS_TOL
    )


def activity_findings(activity):
    """Sorted findings against one declared programme activity.

    activity keys: activity_kind, owner, establishment_milestone. Raises
    ValueError for an unrecognized activity kind or milestone -- those
    are inputs the programme cannot legally carry, not findings."""
    area = categorize_programme_activity(activity.get("activity_kind"))
    milestone = activity.get("establishment_milestone")
    planned = milestone_index(milestone)
    latest = AREA_LATEST_ESTABLISHMENT[area]
    findings = []
    owner = activity.get("owner")
    if not isinstance(owner, str) or not owner.strip():
        findings.append("activity %r names no owner" % (activity.get("activity_kind"),))
    if planned > milestone_index(latest):
        findings.append(
            "area %r is established at %r, later than %r, the last milestone "
            "at which it can still shape the design" % (area, milestone, latest)
        )
    return sorted(findings)


def margin_findings(margin_cases):
    """Sorted findings over the interference safety margin cases the
    programme declares. Each case: point_id, circuit_category,
    susceptibility_threshold_db, interference_level_db."""
    findings = []
    for case in margin_cases:
        required = required_margin_db(case.get("circuit_category"))
        margin = interference_margin_db(
            case.get("susceptibility_threshold_db"),
            case.get("interference_level_db"),
        )
        if not margin_meets_policy(margin, required):
            findings.append(
                "interference point %r holds %.3f dB against a required %.3f dB "
                "for a %s circuit"
                % (
                    case.get("point_id"),
                    margin,
                    required,
                    case.get("circuit_category"),
                )
            )
    return sorted(findings)


def programme_area_coverage(activities, profile):
    """Fraction of the required areas covered by declared activities,
    rounded to six decimals."""
    required = required_programme_areas(profile)
    covered = required & declared_areas(activities)
    return round(len(covered) / float(len(required)), 6)


def aggregate_emc_programme(programme):
    """Full clause 6.2.1 review of a declared EMC programme.

    programme keys: profile, activities, declared_elements, margin_cases
    (optional). Returns a mapping with the uncovered areas, the missing
    programme elements, the per-activity findings, the margin findings,
    the area coverage and the overall establishment flag. The programme
    is established only when every list is empty and the coverage is
    complete."""
    profile = programme.get("profile", {})
    activities = programme.get("activities", [])
    coverage = programme_area_coverage(activities, profile)
    uncovered = missing_programme_areas(activities, profile)
    elements = missing_programme_elements(programme.get("declared_elements", {}))
    per_activity = {}
    for activity in activities:
        findings = activity_findings(activity)
        if findings:
            per_activity.setdefault(activity.get("activity_kind"), []).extend(findings)
    margins = margin_findings(programme.get("margin_cases", []))
    established = (
        not uncovered
        and not elements
        and not per_activity
        and not margins
        and math.isclose(coverage, 1.0, rel_tol=MARGIN_REL_TOL, abs_tol=MARGIN_ABS_TOL)
    )
    return {
        "area_coverage": coverage,
        "uncovered_areas": uncovered,
        "missing_elements": elements,
        "activity_findings": {k: sorted(v) for k, v in per_activity.items()},
        "margin_findings": margins,
        "established": established,
    }
