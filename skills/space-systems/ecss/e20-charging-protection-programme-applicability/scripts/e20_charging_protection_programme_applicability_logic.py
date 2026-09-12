#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.3.4.1 charging protection programme
applicability (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires a charging protection
programme to be produced for the spacecraft and agreed with the
customer before the preliminary design review. This module implements
the checkable part of that clause: mapping a mission orbit onto its
charging environment regime, collecting the design drivers that make a
programme applicable, deriving the section list those drivers demand,
reporting the sections the programme on record does not carry, ordering
the project milestone at which customer approval is placed against the
preliminary design review, and checking the calendar lead between that
approval and the review against a required minimum. It does not run a
charging simulation, does not size a bleed path, and does not replace
the environment specification the programme is built on.
"""

import math

# Relative tolerance that absorbs floating-point representation error
# when a quantity sits exactly on a limit. It widens no requirement: it
# only stops a value mathematically equal to the limit from reading as
# a shortfall a few ULPs out.
LIMIT_REL_TOL = 1e-9

# Orbit to charging environment regime. "benign" is the only regime
# that does not on its own make a charging protection programme
# applicable.
ORBIT_CHARGING_REGIMES = {
    "geo": "severe_surface_and_internal",
    "gto": "severe_surface_and_internal",
    "meo": "severe_internal",
    "heo_belt_crossing": "severe_internal",
    "polar_leo": "auroral_surface",
    "sun_synchronous_leo": "auroral_surface",
    "interplanetary": "moderate_surface",
    "lunar_orbit": "moderate_surface",
    "equatorial_low_leo": "benign",
}

INTERNAL_CHARGING_REGIMES = frozenset(
    {"severe_internal", "severe_surface_and_internal"}
)

# Array or bus voltage at or above which array-plasma interaction makes
# the programme applicable regardless of orbit, in volts.
HIGH_VOLTAGE_THRESHOLD_V = 55.0

# Exposed external dielectric area fraction at or above which surface
# charging is a design driver in a non-benign regime.
DIELECTRIC_AREA_FRACTION_THRESHOLD = 0.10

# Mission duration at or above which cumulative exposure is itself a
# driver in a non-benign regime, in years.
LONG_DURATION_THRESHOLD_YEARS = 5.0

BASE_PROGRAMME_SECTIONS = frozenset(
    {
        "environment_definition",
        "surface_charging_analysis",
        "esd_design_rules",
        "grounding_and_bonding_scheme",
        "material_selection_and_surface_treatment",
        "verification_and_test_plan",
        "schedule_and_milestones",
        "responsibilities_and_interfaces",
    }
)
INTERNAL_CHARGING_SECTION = "internal_charging_analysis"
HIGH_VOLTAGE_SECTION = "array_plasma_interaction_analysis"
NON_APPLICABILITY_SECTION = "non_applicability_justification"

# Project review sequence used to place the approval milestone.
PROJECT_MILESTONE_SEQUENCE = (
    "mdr",
    "prr",
    "srr",
    "pdr",
    "cdr",
    "qr",
    "ar",
    "frr",
    "orr",
)

DEFAULT_MINIMUM_APPROVAL_LEAD_DAYS = 30.0


def _meets_lower_limit(value, limit):
    """True when value is at or above limit, treating a value equal to
    the limit within LIMIT_REL_TOL as meeting it."""
    return value >= limit or math.isclose(value, limit, rel_tol=LIMIT_REL_TOL)


def charging_environment_regime(orbit):
    """Charging environment regime for a mission orbit. Raises
    ValueError for an orbit with no regime on record -- an unmapped
    orbit is a finding, not a benign default."""
    try:
        return ORBIT_CHARGING_REGIMES[orbit]
    except KeyError:
        raise ValueError(
            "no charging environment regime on record for orbit %r under "
            "E-ST-20C clause 6.3.4.1" % (orbit,)
        )


def programme_applicability(mission):
    """Applicability of a charging protection programme to one mission.

    mission: {"mission_id", "orbit", "bus_voltage_v",
    "exposed_dielectric_area_fraction", "duration_years",
    "has_ungrounded_conductive_element"}. Returns
    {"regime", "applicable", "drivers"} with drivers sorted. Raises
    ValueError through charging_environment_regime, or for a negative
    voltage, a duration that is not positive, or an area fraction
    outside the unit interval."""
    regime = charging_environment_regime(mission["orbit"])
    voltage = mission["bus_voltage_v"]
    if voltage < 0:
        raise ValueError("bus_voltage_v must be >= 0")
    fraction = mission["exposed_dielectric_area_fraction"]
    if not 0.0 <= fraction <= 1.0:
        raise ValueError(
            "exposed_dielectric_area_fraction must be within 0.0..1.0"
        )
    duration = mission["duration_years"]
    if duration <= 0:
        raise ValueError("duration_years must be > 0")
    drivers = []
    if regime != "benign":
        drivers.append("charging_environment_regime")
        if _meets_lower_limit(fraction, DIELECTRIC_AREA_FRACTION_THRESHOLD):
            drivers.append("exposed_external_dielectric")
        if _meets_lower_limit(duration, LONG_DURATION_THRESHOLD_YEARS):
            drivers.append("long_duration_exposure")
    if _meets_lower_limit(voltage, HIGH_VOLTAGE_THRESHOLD_V):
        drivers.append("high_voltage_array_interaction")
    if mission["has_ungrounded_conductive_element"]:
        drivers.append("ungrounded_conductive_element")
    return {
        "regime": regime,
        "applicable": bool(drivers),
        "drivers": sorted(drivers),
    }


def required_programme_sections(applicability):
    """Section set the programme must carry for one applicability
    result. A mission with no driver still owes a written
    non-applicability justification -- silence is not a waiver. Raises
    ValueError for an applicability mapping with no regime."""
    if "regime" not in applicability:
        raise ValueError("applicability mapping needs a 'regime' entry")
    if not applicability["applicable"]:
        return frozenset({NON_APPLICABILITY_SECTION})
    sections = set(BASE_PROGRAMME_SECTIONS)
    if applicability["regime"] in INTERNAL_CHARGING_REGIMES:
        sections.add(INTERNAL_CHARGING_SECTION)
    if "high_voltage_array_interaction" in applicability["drivers"]:
        sections.add(HIGH_VOLTAGE_SECTION)
    return frozenset(sections)


def missing_programme_sections(declared_sections, required):
    """Sorted list of required sections the programme does not carry. A
    section present with a value of None or an empty string counts as
    absent -- a named but unwritten heading is not a section. Raises
    ValueError when declared_sections is not a mapping."""
    if not hasattr(declared_sections, "get"):
        raise ValueError("declared_sections must be a mapping")
    return sorted(
        section
        for section in required
        if declared_sections.get(section) in (None, "")
    )


def milestone_index(milestone):
    """Position of a project review in the milestone sequence. Raises
    ValueError for a review that is not in the sequence."""
    try:
        return PROJECT_MILESTONE_SEQUENCE.index(milestone)
    except ValueError:
        raise ValueError(
            "unrecognized project milestone %r" % (milestone,)
        )


def approval_lead_days(approval_day, review_day):
    """Calendar lead in days between the approval date and the review
    date, both given as day numbers on the project calendar. A negative
    result means approval falls after the review."""
    return review_day - approval_day


def approval_timing_findings(approval_record, minimum_lead_days=None):
    """Findings (empty when the approval is placed correctly) for the
    customer approval of the programme.

    approval_record: {"approval_milestone", "approval_day",
    "review_day", "customer_approved"}. Clause 6.3.4.1 wants the
    agreement in hand before the preliminary design review, so an
    approval milestone at or after that review is a finding, an
    approval that is recorded but not granted is a finding, and a
    calendar lead below the required minimum is a finding. Raises
    ValueError through milestone_index or for a negative minimum
    lead."""
    if minimum_lead_days is None:
        minimum_lead_days = DEFAULT_MINIMUM_APPROVAL_LEAD_DAYS
    if minimum_lead_days < 0:
        raise ValueError("minimum_lead_days must be >= 0")
    findings = []
    index = milestone_index(approval_record["approval_milestone"])
    pdr_index = milestone_index("pdr")
    if index >= pdr_index:
        findings.append(
            {
                "issue": "approval_milestone_not_before_pdr",
                "approval_milestone": approval_record["approval_milestone"],
            }
        )
    lead = approval_lead_days(
        approval_record["approval_day"], approval_record["review_day"]
    )
    if not _meets_lower_limit(lead, minimum_lead_days):
        findings.append(
            {
                "issue": "approval_lead_below_minimum",
                "lead_days": lead,
                "minimum_lead_days": minimum_lead_days,
            }
        )
    if not approval_record["customer_approved"]:
        findings.append({"issue": "customer_approval_not_granted"})
    return findings


def assess_charging_protection_programme(case, minimum_lead_days=None):
    """Aggregate clause 6.3.4.1 review of one mission's charging
    protection programme.

    case: {"mission" (mission mapping), "declared_sections" (mapping),
    "approval_record" (mapping)}. The approval check is skipped for a
    mission with no applicability driver, since there is no programme
    to approve -- only the written justification. Returns the
    applicability result, the two finding lists and a compliant flag
    that is true only when both lists are empty. Raises ValueError
    through the per-step checks."""
    applicability = programme_applicability(case["mission"])
    required = required_programme_sections(applicability)
    absent = missing_programme_sections(case["declared_sections"], required)
    section_findings = []
    if absent:
        section_findings.append(
            {
                "issue": "missing_programme_section",
                "missing": absent,
            }
        )
    timing_findings = []
    if applicability["applicable"]:
        timing_findings = approval_timing_findings(
            case["approval_record"], minimum_lead_days
        )
    return {
        "mission_id": case["mission"]["mission_id"],
        "regime": applicability["regime"],
        "applicable": applicability["applicable"],
        "drivers": applicability["drivers"],
        "required_sections": sorted(required),
        "section_findings": section_findings,
        "timing_findings": timing_findings,
        "compliant": not (section_findings or timing_findings),
    }
