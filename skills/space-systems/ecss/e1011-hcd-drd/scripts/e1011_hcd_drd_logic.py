#!/usr/bin/env python3
"""ECSS-E-ST-10-11C Annex A HCD process plan DRD validation
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
human factors engineering standard's normative Annex A defines a
Document Requirements Definition (DRD) for the Human-Centred Design
(HCD) process plan. The DRD mandates seven content sections — scope,
context-of-use description, stakeholder inventory, HCD activity
schedule, evaluation plan, HFE staffing, and requirements traceability
— each with required fields. HCD activities must be linked to project
milestones and to a responsible HFE practitioner. Evaluation events
are categorized as either formative (iterative design feedback) or
summative (final acceptance verification), each with success criteria.
HFE practitioners must carry a documented competency statement.
Traceability mappings link each HCD activity to at least one
requirement identifier. This module validates these structural and
content obligations; it does not replicate the DRD table itself.
"""

MANDATORY_SECTIONS = frozenset({
    "scope",
    "context_of_use",
    "stakeholder_inventory",
    "activity_schedule",
    "evaluation_plan",
    "hfe_staffing",
    "requirements_traceability",
})

SECTION_REQUIRED_FIELDS = {
    "scope": frozenset({"document_title", "applicable_standard"}),
    "context_of_use": frozenset({"mission_phases", "crew_roles", "environment_description"}),
    "stakeholder_inventory": frozenset({"users", "operators"}),
    "activity_schedule": frozenset({"activities"}),
    "evaluation_plan": frozenset({"events"}),
    "hfe_staffing": frozenset({"practitioners"}),
    "requirements_traceability": frozenset({"mappings"}),
}

VALID_EVALUATION_TYPES = frozenset({"formative", "summative"})


def check_mandatory_sections(plan):
    """Return a list of violation dicts for every mandatory section
    absent from plan. plan: a dict keyed by section name. Returns []
    when all mandatory sections are present."""
    if not isinstance(plan, dict):
        raise TypeError("plan must be a dict")
    violations = []
    for section in sorted(MANDATORY_SECTIONS):
        if section not in plan:
            violations.append({
                "issue": "missing_mandatory_section",
                "section": section,
            })
    return violations


def check_section_fields(section_name, section_data):
    """Return a list of violation dicts for every required field absent
    from section_data. section_name: one of the keys in
    SECTION_REQUIRED_FIELDS. section_data: a dict with the section's
    content. Raises ValueError for an unrecognized section_name. Returns
    [] when all required fields are present."""
    if section_name not in SECTION_REQUIRED_FIELDS:
        raise ValueError(
            "unrecognized section name %r; expected one of %s"
            % (section_name, sorted(SECTION_REQUIRED_FIELDS))
        )
    if not isinstance(section_data, dict):
        raise TypeError("section_data must be a dict for section %r" % (section_name,))
    required = SECTION_REQUIRED_FIELDS[section_name]
    violations = []
    for field in sorted(required):
        if field not in section_data or section_data[field] in (None, "", [], {}):
            violations.append({
                "issue": "missing_required_field",
                "section": section_name,
                "field": field,
            })
    return violations


def check_activity_schedule(activities):
    """Return a list of violation dicts for activities missing a
    milestone reference or a responsible_practitioner field. activities:
    an iterable of dicts, each representing one HCD activity. Returns []
    when all activities carry both fields."""
    violations = []
    for idx, activity in enumerate(activities):
        name = activity.get("name") or ("activity[%d]" % idx)
        if not activity.get("milestone"):
            violations.append({
                "issue": "activity_missing_milestone",
                "activity": name,
            })
        if not activity.get("responsible_practitioner"):
            violations.append({
                "issue": "activity_missing_responsible_practitioner",
                "activity": name,
            })
    return violations


def check_evaluation_events(events):
    """Return a list of violation dicts for evaluation events with an
    unrecognized type or empty success_criteria. events: an iterable of
    dicts, each representing one evaluation event. Valid types are
    'formative' and 'summative'. Returns [] when all events conform."""
    violations = []
    for idx, event in enumerate(events):
        name = event.get("name") or ("event[%d]" % idx)
        ev_type = event.get("type")
        if ev_type not in VALID_EVALUATION_TYPES:
            violations.append({
                "issue": "evaluation_event_invalid_type",
                "event": name,
                "type_given": ev_type,
                "valid_types": sorted(VALID_EVALUATION_TYPES),
            })
        if not event.get("success_criteria"):
            violations.append({
                "issue": "evaluation_event_missing_success_criteria",
                "event": name,
            })
    return violations


def check_hfe_staffing(practitioners):
    """Return a list of violation dicts for HFE practitioners without a
    competency field. practitioners: an iterable of dicts, each
    representing one practitioner. Returns [] when every practitioner
    carries a non-empty competency statement."""
    violations = []
    for idx, practitioner in enumerate(practitioners):
        name = practitioner.get("name") or ("practitioner[%d]" % idx)
        if not practitioner.get("competency"):
            violations.append({
                "issue": "hfe_practitioner_missing_competency",
                "practitioner": name,
            })
    return violations


def check_traceability_mappings(mappings):
    """Return a list of violation dicts for traceability entries missing
    an activity_id or a requirement_id. mappings: an iterable of dicts.
    Returns [] when every mapping links an activity to a requirement."""
    violations = []
    for idx, mapping in enumerate(mappings):
        label = "mapping[%d]" % idx
        if not mapping.get("activity_id"):
            violations.append({
                "issue": "traceability_mapping_missing_activity_id",
                "mapping": label,
            })
        if not mapping.get("requirement_id"):
            violations.append({
                "issue": "traceability_mapping_missing_requirement_id",
                "mapping": label,
            })
    return violations


def validate_hcd_plan(plan):
    """Full DRD compliance check for an HCD process plan.

    plan: dict keyed by section name; each value is a dict with that
    section's content. Returns a dict with keys "missing_sections",
    "field_violations", "activity_violations", "evaluation_violations",
    "staffing_violations", "traceability_violations", each a list of
    violation dicts. Raises TypeError if plan is not a dict."""
    result = {
        "missing_sections": check_mandatory_sections(plan),
        "field_violations": [],
        "activity_violations": [],
        "evaluation_violations": [],
        "staffing_violations": [],
        "traceability_violations": [],
    }

    for section_name in SECTION_REQUIRED_FIELDS:
        section_data = plan.get(section_name)
        if section_data is None:
            continue
        result["field_violations"].extend(
            check_section_fields(section_name, section_data)
        )

    if "activity_schedule" in plan and isinstance(plan["activity_schedule"], dict):
        activities = plan["activity_schedule"].get("activities") or []
        result["activity_violations"] = check_activity_schedule(activities)

    if "evaluation_plan" in plan and isinstance(plan["evaluation_plan"], dict):
        events = plan["evaluation_plan"].get("events") or []
        result["evaluation_violations"] = check_evaluation_events(events)

    if "hfe_staffing" in plan and isinstance(plan["hfe_staffing"], dict):
        practitioners = plan["hfe_staffing"].get("practitioners") or []
        result["staffing_violations"] = check_hfe_staffing(practitioners)

    if "requirements_traceability" in plan and isinstance(
        plan["requirements_traceability"], dict
    ):
        mappings = plan["requirements_traceability"].get("mappings") or []
        result["traceability_violations"] = check_traceability_mappings(mappings)

    return result


def is_plan_compliant(validation_result):
    """True when every violation list in a validate_hcd_plan result is
    empty — the plan satisfies the Annex A DRD for this assessment."""
    return all(len(v) == 0 for v in validation_result.values())
