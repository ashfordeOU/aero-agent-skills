"""Content audit of a component control plan against its deliverable description.

Anchor: ECSS-Q-ST-60C Annex A (the content a component control plan has to
carry, covering the component engineering organization, the controls it
operates and the schedules it commits to). Paraphrased into an implementable
audit; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Every required section belongs to a group: the general front matter, the
   organization, the controls, or the schedules. The group is what makes the
   audit more than a checklist.
2. Each section is credited by how far it got — absent, outlined, or written
   through — rather than by whether a heading exists.
3. Each group has to clear its own floor. A plan with twenty pages of
   procurement control and a paragraph on who signs anything is not a
   submittable plan, and a single weighted total would let the strong group
   carry the weak one.
4. The plan as a whole has to clear a higher floor on top of the group
   floors, so clearing every group by a hair is not enough.
5. Mandatory sections fail the plan by their absence, whatever either floor
   reads.
6. The schedules group carries an ordering obligation the others do not: the
   committed milestones have to run in a sequence that can actually happen,
   with the preliminary list before the selection freeze, the freeze before
   the long-lead release, and the final list before delivery closes.

Both floors are judged at the boundary under a named tolerance, so a plan
sitting exactly on one is not failed by float representation alone.
"""

import math

__all__ = [
    "GROUPS",
    "DRD_SECTIONS",
    "SECTION_STATES",
    "STATE_CREDIT",
    "GROUP_FLOOR",
    "OVERALL_FLOOR",
    "ACTIONS_FLOOR",
    "COMPLETENESS_TOLERANCE",
    "REQUIRED_MILESTONE_ORDER",
    "VERDICTS",
    "normalize_token",
    "sections_in_group",
    "group_weight",
    "mandatory_sections",
    "validate_section",
    "validate_sections",
    "group_completeness",
    "overall_completeness",
    "missing_mandatory_sections",
    "validate_milestones",
    "milestone_order_findings",
    "plan_verdict",
    "assess_component_control_plan",
]

# The four groups the deliverable's content falls into.
GROUPS = ("general", "organization", "controls", "schedules")

# The content a component control plan is expected to carry.
DRD_SECTIONS = {
    "purpose-and-scope": {"group": "general", "weight": 2.0, "mandatory": True},
    "applicable-and-reference-documents": {
        "group": "general",
        "weight": 1.0,
        "mandatory": True,
    },
    "definitions-and-abbreviations": {
        "group": "general",
        "weight": 1.0,
        "mandatory": False,
    },
    "component-engineering-organization": {
        "group": "organization",
        "weight": 2.0,
        "mandatory": True,
    },
    "responsibilities-and-authority": {
        "group": "organization",
        "weight": 2.0,
        "mandatory": True,
    },
    "component-control-board-operation": {
        "group": "organization",
        "weight": 3.0,
        "mandatory": True,
    },
    "supplier-and-subcontractor-flowdown": {
        "group": "organization",
        "weight": 1.0,
        "mandatory": False,
    },
    "component-selection-and-approval-process": {
        "group": "controls",
        "weight": 3.0,
        "mandatory": True,
    },
    "declared-component-list-management": {
        "group": "controls",
        "weight": 3.0,
        "mandatory": True,
    },
    "procurement-and-source-control": {
        "group": "controls",
        "weight": 2.0,
        "mandatory": True,
    },
    "incoming-inspection-and-test-control": {
        "group": "controls",
        "weight": 2.0,
        "mandatory": True,
    },
    "radiation-hardness-assurance-control": {
        "group": "controls",
        "weight": 2.0,
        "mandatory": True,
    },
    "pure-tin-and-finish-control": {
        "group": "controls",
        "weight": 2.0,
        "mandatory": True,
    },
    "nonconformance-and-alert-handling": {
        "group": "controls",
        "weight": 2.0,
        "mandatory": True,
    },
    "electrostatic-discharge-control": {
        "group": "controls",
        "weight": 2.0,
        "mandatory": True,
    },
    "derating-and-worst-case-policy": {
        "group": "controls",
        "weight": 2.0,
        "mandatory": False,
    },
    "traceability-storage-and-handling-control": {
        "group": "controls",
        "weight": 2.0,
        "mandatory": False,
    },
    "component-milestone-schedule": {
        "group": "schedules",
        "weight": 2.0,
        "mandatory": True,
    },
    "declared-list-submission-schedule": {
        "group": "schedules",
        "weight": 2.0,
        "mandatory": True,
    },
    "long-lead-procurement-schedule": {
        "group": "schedules",
        "weight": 2.0,
        "mandatory": False,
    },
}

# How far a section got, in the auditor's vocabulary.
SECTION_STATES = ("absent", "outline", "complete")

# What each state is worth against the section's weight.
STATE_CREDIT = {"absent": 0.0, "outline": 0.5, "complete": 1.0}

# Every group clears its own floor; the plan then clears a higher one.
GROUP_FLOOR = 0.75
OVERALL_FLOOR = 0.85

# Below this the plan is not a draft with gaps, it is an outline.
ACTIONS_FLOOR = 0.60

# Completeness is a quotient of floats; a plan sitting exactly on a floor
# must not be failed on representation alone.
COMPLETENESS_TOLERANCE = 1e-9

# The order the committed milestones have to run in.
REQUIRED_MILESTONE_ORDER = (
    "preliminary-declared-list-submission",
    "component-selection-freeze",
    "long-lead-procurement-release",
    "final-declared-list-submission",
    "component-delivery-complete",
)

VERDICTS = ("submittable", "submittable-with-actions", "not-submittable")


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _non_negative_int(value, label):
    """Return a whole count that may be zero but never negative."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def normalize_token(value, label="token"):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def _validate_group(value):
    """Return a recognized content group token."""
    token = normalize_token(value, "group")
    if token not in GROUPS:
        raise ValueError(
            "group '%s' is not recognized; expected one of %s"
            % (token, ", ".join(GROUPS))
        )
    return token


def sections_in_group(group):
    """Return the required sections belonging to one group, sorted."""
    token = _validate_group(group)
    return sorted(k for k, v in DRD_SECTIONS.items() if v["group"] == token)


def group_weight(group):
    """Return the total weight a group's sections carry."""
    token = _validate_group(group)
    return sum(v["weight"] for v in DRD_SECTIONS.values() if v["group"] == token)


def mandatory_sections():
    """Return the sections whose absence fails the plan, sorted."""
    return sorted(k for k, v in DRD_SECTIONS.items() if v["mandatory"])


def validate_section(section):
    """Return one validated section entry of the submitted plan."""
    if not isinstance(section, dict):
        raise ValueError("section must be a mapping")
    for key in ("section", "state"):
        if key not in section:
            raise ValueError("section missing required key '%s'" % key)
    token = normalize_token(section["section"], "section")
    if token not in DRD_SECTIONS:
        raise ValueError(
            "section '%s' is not required content of this deliverable; expected "
            "one of %s" % (token, ", ".join(sorted(DRD_SECTIONS)))
        )
    state = normalize_token(section["state"], "state")
    if state not in SECTION_STATES:
        raise ValueError(
            "state '%s' is not recognized; expected one of %s"
            % (state, ", ".join(SECTION_STATES))
        )
    spec = DRD_SECTIONS[token]
    return {
        "section": token,
        "group": spec["group"],
        "state": state,
        "weight": spec["weight"],
        "mandatory": spec["mandatory"],
        "credit": STATE_CREDIT[state],
    }


def validate_sections(sections):
    """Return every required section, with anything unsubmitted marked absent."""
    if not isinstance(sections, (list, tuple)):
        raise ValueError("sections must be a list")
    validated = {}
    for entry in sections:
        item = validate_section(entry)
        if item["section"] in validated:
            raise ValueError("section '%s' submitted more than once" % item["section"])
        validated[item["section"]] = item
    for token, spec in DRD_SECTIONS.items():
        if token not in validated:
            validated[token] = {
                "section": token,
                "group": spec["group"],
                "state": "absent",
                "weight": spec["weight"],
                "mandatory": spec["mandatory"],
                "credit": 0.0,
            }
    return validated


def group_completeness(validated):
    """Return the completeness fraction of every group, as a mapping."""
    if not isinstance(validated, dict) or not validated:
        raise ValueError("validated sections must be a non-empty mapping")
    earned = {group: 0.0 for group in GROUPS}
    available = {group: 0.0 for group in GROUPS}
    for item in validated.values():
        earned[item["group"]] += item["weight"] * item["credit"]
        available[item["group"]] += item["weight"]
    result = {}
    for group in GROUPS:
        if available[group] <= 0.0:
            raise ValueError("group '%s' carries no weight" % group)
        result[group] = earned[group] / available[group]
    return result


def overall_completeness(validated):
    """Return the completeness fraction of the plan as a whole."""
    if not isinstance(validated, dict) or not validated:
        raise ValueError("validated sections must be a non-empty mapping")
    earned = 0.0
    available = 0.0
    for item in validated.values():
        earned += item["weight"] * item["credit"]
        available += item["weight"]
    if available <= 0.0:
        raise ValueError("required sections carry no weight")
    return earned / available


def missing_mandatory_sections(validated):
    """Return the mandatory sections that are absent, sorted."""
    if not isinstance(validated, dict):
        raise ValueError("validated sections must be a mapping")
    return sorted(
        token
        for token, item in validated.items()
        if item["mandatory"] and item["state"] == "absent"
    )


def validate_milestones(milestones):
    """Return the submitted milestones as a token to day mapping.

    An unknown milestone, a milestone given twice, or a day that is not a
    whole non-negative number is a defect in the plan, not something to
    silently resolve.
    """
    if not isinstance(milestones, (list, tuple)):
        raise ValueError("milestones must be a list")
    schedule = {}
    for entry in milestones:
        if not isinstance(entry, dict):
            raise ValueError("each milestone must be a mapping")
        for key in ("milestone", "day"):
            if key not in entry:
                raise ValueError("milestone missing required key '%s'" % key)
        token = normalize_token(entry["milestone"], "milestone")
        if token not in REQUIRED_MILESTONE_ORDER:
            raise ValueError(
                "milestone '%s' is not one the plan has to commit; expected one "
                "of %s" % (token, ", ".join(REQUIRED_MILESTONE_ORDER))
            )
        if token in schedule:
            raise ValueError("milestone '%s' given more than once" % token)
        schedule[token] = _non_negative_int(entry["day"], "day")
    return schedule


def milestone_order_findings(milestones):
    """Return every way the committed milestones cannot happen, sorted.

    A milestone that is missing is reported once; a pair that runs backwards
    is reported against the later of the two.
    """
    schedule = (
        milestones
        if isinstance(milestones, dict)
        else validate_milestones(milestones)
    )
    findings = []
    for token in REQUIRED_MILESTONE_ORDER:
        if token not in schedule:
            findings.append("milestone-not-committed-%s" % token)
    present = [t for t in REQUIRED_MILESTONE_ORDER if t in schedule]
    for earlier, later in zip(present, present[1:]):
        if schedule[later] < schedule[earlier]:
            findings.append("milestone-out-of-sequence-%s" % later)
    return sorted(findings)


def _at_or_above(value, floor):
    """Return whether a value meets a floor, tolerant at the boundary."""
    return value > floor or math.isclose(
        value, floor, rel_tol=0.0, abs_tol=COMPLETENESS_TOLERANCE
    )


def plan_verdict(groups, overall, missing, schedule_findings):
    """Return the verdict a plan's completeness and defects earn."""
    if not isinstance(groups, dict) or set(groups) != set(GROUPS):
        raise ValueError("groups must carry a fraction for every group")
    if not isinstance(missing, (list, tuple)):
        raise ValueError("missing must be a list")
    if not isinstance(schedule_findings, (list, tuple)):
        raise ValueError("schedule_findings must be a list")
    if isinstance(overall, bool) or not isinstance(overall, (int, float)):
        raise ValueError("overall must be a number, got %r" % (overall,))
    total = float(overall)
    if not math.isfinite(total) or total < 0.0 or total > 1.0:
        raise ValueError("overall must lie between zero and one, got %r" % (overall,))

    blocking = bool(missing) or bool(schedule_findings)
    floors_met = all(_at_or_above(groups[g], GROUP_FLOOR) for g in GROUPS)
    floors_met = floors_met and _at_or_above(total, OVERALL_FLOOR)

    if not blocking and floors_met:
        return "submittable"
    if _at_or_above(total, ACTIONS_FLOOR):
        return "submittable-with-actions"
    return "not-submittable"


def assess_component_control_plan(plan):
    """Audit one component control plan against its required content.

    plan keys: document_id, sections (a list of {section, state} entries) and
    milestones (a list of {milestone, day} entries).
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping")
    for key in ("document_id", "sections", "milestones"):
        if key not in plan:
            raise ValueError("plan missing required key '%s'" % key)

    document_id = _require_text(plan["document_id"], "document_id")
    validated = validate_sections(plan["sections"])
    groups = group_completeness(validated)
    overall = overall_completeness(validated)
    missing = missing_mandatory_sections(validated)
    schedule = validate_milestones(plan["milestones"])
    schedule_findings = milestone_order_findings(schedule)
    verdict = plan_verdict(groups, overall, missing, schedule_findings)

    weak_groups = sorted(g for g in GROUPS if not _at_or_above(groups[g], GROUP_FLOOR))

    findings = []
    for token in missing:
        findings.append(
            "plan '%s' omits the mandatory section '%s'" % (document_id, token)
        )
    for group in weak_groups:
        findings.append(
            "the %s group of plan '%s' reaches %.3f against the %.2f floor"
            % (group, document_id, groups[group], GROUP_FLOOR)
        )
    for token in schedule_findings:
        findings.append("the schedule of plan '%s' shows %s" % (document_id, token))
    if not _at_or_above(overall, OVERALL_FLOOR) and not weak_groups:
        findings.append(
            "plan '%s' clears every group floor but reaches only %.3f overall "
            "against the %.2f required" % (document_id, overall, OVERALL_FLOOR)
        )

    actions = []
    for token in missing:
        actions.append("write-the-missing-section-%s" % token)
    for group in weak_groups:
        actions.append("deepen-the-%s-group-to-its-floor" % group)
    for token in schedule_findings:
        actions.append("repair-the-schedule-%s" % token)

    return {
        "document_id": document_id,
        "sections": validated,
        "group_completeness": groups,
        "overall_completeness": overall,
        "weak_groups": weak_groups,
        "missing_mandatory": missing,
        "milestones": schedule,
        "schedule_findings": schedule_findings,
        "verdict": verdict,
        "submittable_as_drafted": verdict == "submittable",
        "findings": findings,
        "actions": actions,
    }
