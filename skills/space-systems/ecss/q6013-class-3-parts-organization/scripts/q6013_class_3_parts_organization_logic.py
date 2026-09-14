#!/usr/bin/env python3
"""Who answers for commercial EEE part control at the lowest assurance class.

Anchor: ECSS-Q-ST-60-13C clause 6.1.2.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

At the lowest assurance class the clause still asks the organization question,
but it asks it of a much smaller team, and reading the highest class's answer
onto it produces a finding on every real project rather than a useful one.

Three things change, and each is a deliberate relaxation rather than an
oversight.

Duties may be combined. One role holding part selection, procurement source
control and the parts list is normal here, not a split accountability. So a
duty counts as covered when at least one role holds it, where the highest
class counts it only when exactly one role does.

Coverage is judged against a floor below unity. The class accepts that a duty
or so is carried by the project's general quality function rather than by a
named parts role, so a gap is reported and survivable -- with one exception.
Part-selection approval is the anchor: a project with nobody able to say yes
to a commercial part has no parts control at this class or any other, so a
missing anchor closes the assessment whatever the coverage arithmetic says.

Independence stops being the test. A parts role sitting inside the design
authority is ordinary at this class and is carried as an advisory rather than
a finding. What replaces it is continuity: a small team's real failure mode is
one person holding everything and then leaving, so a role carrying more duties
than the concentration ceiling with no deputy named is the finding the class
actually needs. Effort is the same argument in numbers -- responsibility
assigned at a fraction of a person that could never exercise it is assignment
on paper.

And the decision has to land somewhere findable. At this class there is no
parts control board minute to fall back on, so the location of the parts
decision record is part of the organization rather than an afterthought.

The policy numbers below are declared project values, not physical constants:
a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PART_SELECTION_AND_APPROVAL = "commercial-part-selection-and-approval"
PROCUREMENT_SOURCE_CONTROL = "procurement-source-control"
INCOMING_ACCEPTANCE_CONTROL = "incoming-acceptance-control"
ALERT_AND_NONCONFORMANCE_DISPOSITION = "alert-and-nonconformance-disposition"
PARTS_LIST_AND_TRACEABILITY_CUSTODY = "parts-list-and-traceability-custody"

REQUIRED_RESPONSIBILITIES = (
    PART_SELECTION_AND_APPROVAL,
    PROCUREMENT_SOURCE_CONTROL,
    INCOMING_ACCEPTANCE_CONTROL,
    ALERT_AND_NONCONFORMANCE_DISPOSITION,
    PARTS_LIST_AND_TRACEABILITY_CUSTODY,
)

ANCHOR_RESPONSIBILITY = PART_SELECTION_AND_APPROVAL

RESPONSIBILITY_NOT_ASSIGNED = "commercial-parts-responsibility-not-assigned"
COVERAGE_BELOW_CLASS_FLOOR = "parts-responsibility-coverage-below-floor"
CONTINUITY_NOT_ASSURED = "parts-responsibility-continuity-not-assured"
EFFORT_BELOW_FLOOR = "parts-responsibility-effort-below-floor"
DECISION_RECORD_NOT_LOCATED = "parts-decision-record-not-located"
ORGANIZATION_MEETS_CLASS_THREE = "parts-organization-meets-class-three"

DEFAULT_RESPONSIBILITY_POLICY = {
    "min_responsibility_coverage": 0.8,
    "min_total_effort_fte": 0.5,
    "max_responsibilities_without_deputy": 2,
    "require_decision_record_location": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_responsibility_policy(policy):
    """Check the responsibility policy is complete and sensible for this class."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    coverage = _require_positive(
        "min_responsibility_coverage", policy.get("min_responsibility_coverage")
    )
    if coverage > 1.0:
        raise ValueError(
            "min_responsibility_coverage %g is above one; no organization can "
            "hold more duties than the clause names" % coverage
        )
    effort = _require_positive("min_total_effort_fte", policy.get("min_total_effort_fte"))
    if effort > float(len(REQUIRED_RESPONSIBILITIES)):
        raise ValueError(
            "min_total_effort_fte %g asks for more people than the clause has "
            "duties; the lowest class does not staff that way" % effort
        )
    ceiling = _require_count(
        "max_responsibilities_without_deputy",
        policy.get("max_responsibilities_without_deputy"),
    )
    if ceiling > len(REQUIRED_RESPONSIBILITIES):
        raise ValueError(
            "max_responsibilities_without_deputy %d is at or above the whole "
            "duty set, so no concentration could ever be flagged" % ceiling
        )
    _require_flag(
        "require_decision_record_location",
        policy.get("require_decision_record_location"),
    )
    return policy


def validate_role_record(role):
    """Read one declared role and the duties it carries."""
    if not isinstance(role, dict):
        raise ValueError("role must be a mapping, got %r" % (role,))
    identifier = _require_label("role id", role.get("id"))
    if not identifier:
        raise ValueError("role id must not be blank")
    duties = role.get("responsibilities")
    if not isinstance(duties, (list, tuple)):
        raise ValueError(
            "responsibilities on %s must be a sequence of duty names" % identifier
        )
    named = []
    for duty in duties:
        label = _require_label("responsibility on %s" % identifier, duty)
        if label not in REQUIRED_RESPONSIBILITIES:
            raise ValueError(
                "unrecognised responsibility %r on %s; the duty names are fixed"
                % (label, identifier)
            )
        if label in named:
            raise ValueError(
                "responsibility %r is listed twice on %s" % (label, identifier)
            )
        named.append(label)
    effort = _require_number("effort_fte on %s" % identifier, role.get("effort_fte"))
    if effort < 0.0 or effort > 1.0:
        raise ValueError(
            "effort_fte on %s must sit between zero and one whole person, got %r"
            % (identifier, role.get("effort_fte"))
        )
    deputy = _require_flag("deputy_named on %s" % identifier, role.get("deputy_named"))
    recorded = _require_flag(
        "recorded_in_project_plan on %s" % identifier,
        role.get("recorded_in_project_plan"),
    )
    embedded = _require_flag(
        "inside_design_authority on %s" % identifier,
        role.get("inside_design_authority"),
    )
    return {
        "id": identifier,
        "responsibilities": tuple(named),
        "effort_fte": effort,
        "deputy_named": deputy,
        "recorded_in_project_plan": recorded,
        "inside_design_authority": embedded,
    }


def validate_roles(roles):
    """Read every declared role, refusing an empty set or a repeated identifier."""
    if not isinstance(roles, (list, tuple)):
        raise ValueError("roles must be a sequence of role records")
    if not roles:
        raise ValueError("no role was declared, so nobody is responsible")
    checked = []
    seen = set()
    for role in roles:
        record = validate_role_record(role)
        if record["id"] in seen:
            raise ValueError("duplicate role id %r in the organization" % record["id"])
        seen.add(record["id"])
        checked.append(record)
    return tuple(checked)


def responsibility_assignment(roles):
    """Map each required duty to the roles that carry it, in record order."""
    checked = validate_roles(roles)
    assignment = {}
    for duty in REQUIRED_RESPONSIBILITIES:
        assignment[duty] = tuple(
            role["id"] for role in checked if duty in role["responsibilities"]
        )
    return assignment


def unassigned_responsibilities(roles):
    """Required duties no declared role carries."""
    assignment = responsibility_assignment(roles)
    return tuple(duty for duty in REQUIRED_RESPONSIBILITIES if not assignment[duty])


def responsibility_coverage(roles):
    """Share of required duties carried by at least one role.

    Combination is permitted at this class, so a duty two roles share counts
    as covered rather than as a split -- the opposite of the highest class.
    """
    assignment = responsibility_assignment(roles)
    covered = sum(1 for duty in REQUIRED_RESPONSIBILITIES if assignment[duty])
    return covered / len(REQUIRED_RESPONSIBILITIES)


def anchor_is_held(roles):
    """True when at least one role may approve a commercial part into the design."""
    assignment = responsibility_assignment(roles)
    return bool(assignment[ANCHOR_RESPONSIBILITY])


def roles_outside_the_project_plan(roles):
    """Declared roles the project plan does not record."""
    checked = validate_roles(roles)
    return tuple(
        role["id"] for role in checked if not role["recorded_in_project_plan"]
    )


def concentrated_roles(roles, policy=DEFAULT_RESPONSIBILITY_POLICY):
    """Roles carrying more duties than the ceiling allows with no deputy named."""
    validate_responsibility_policy(policy)
    checked = validate_roles(roles)
    ceiling = int(policy["max_responsibilities_without_deputy"])
    return tuple(
        role["id"]
        for role in checked
        if len(role["responsibilities"]) > ceiling and not role["deputy_named"]
    )


def total_declared_effort_fte(roles):
    """Declared effort across every role, in whole-person fractions."""
    checked = validate_roles(roles)
    return math.fsum(role["effort_fte"] for role in checked)


def embedded_roles(roles):
    """Roles sitting inside the design authority; ordinary at this class."""
    checked = validate_roles(roles)
    return tuple(role["id"] for role in checked if role["inside_design_authority"])


def assess_parts_responsibility(case, policy=DEFAULT_RESPONSIBILITY_POLICY):
    """Full clause 6.1.2.1 responsibility decision for one declared organization."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_responsibility_policy(policy)

    findings = []
    advisories = []
    result = {
        "anchor_holders": (),
        "responsibility_coverage": None,
        "unassigned_responsibilities": (),
        "concentrated_roles": (),
        "total_declared_effort_fte": None,
        "decision_record_location": None,
        "findings": findings,
        "advisories": advisories,
    }

    roles = case.get("roles")
    if roles is None:
        findings.append(
            "no parts role is declared, so nobody answers for commercial part "
            "control"
        )
        result["verdict"] = RESPONSIBILITY_NOT_ASSIGNED
        return result

    checked = validate_roles(roles)
    unrecorded = roles_outside_the_project_plan(checked)
    if len(unrecorded) == len(checked):
        findings.append(
            "no declared role is recorded in the project plan; responsibility "
            "that lives only in a conversation is not assigned"
        )
        result["verdict"] = RESPONSIBILITY_NOT_ASSIGNED
        return result
    for identifier in unrecorded:
        advisories.append(
            "role %s is not recorded in the project plan; it works today and "
            "is invisible to whoever inherits the project" % identifier
        )

    assignment = responsibility_assignment(checked)
    result["anchor_holders"] = assignment[ANCHOR_RESPONSIBILITY]
    if not anchor_is_held(checked):
        findings.append(
            "no role may approve a commercial part into the design, so there is "
            "no parts control to judge"
        )
        result["verdict"] = RESPONSIBILITY_NOT_ASSIGNED
        return result

    coverage = responsibility_coverage(checked)
    gaps = unassigned_responsibilities(checked)
    result["responsibility_coverage"] = coverage
    result["unassigned_responsibilities"] = gaps
    for duty in gaps:
        findings.append("no declared role carries %s" % duty)
    if not _at_least(coverage, float(policy["min_responsibility_coverage"])):
        findings.append(
            "responsibility coverage is %.3g per cent against the %.3g per cent "
            "floor this class sets"
            % (
                coverage * 100.0,
                float(policy["min_responsibility_coverage"]) * 100.0,
            )
        )
        result["verdict"] = COVERAGE_BELOW_CLASS_FLOOR
        return result
    if gaps:
        advisories.append(
            "%d duty of the %d is carried outside the parts roles; the class "
            "permits it, and the general quality function has to know it owns it"
            % (len(gaps), len(REQUIRED_RESPONSIBILITIES))
        )

    concentrated = concentrated_roles(checked, policy)
    result["concentrated_roles"] = concentrated
    if concentrated:
        for identifier in concentrated:
            findings.append(
                "role %s carries more than %d duties with no deputy named; the "
                "whole of parts control leaves with one person"
                % (identifier, int(policy["max_responsibilities_without_deputy"]))
            )
        result["verdict"] = CONTINUITY_NOT_ASSURED
        return result

    effort = total_declared_effort_fte(checked)
    result["total_declared_effort_fte"] = effort
    if not _at_least(effort, float(policy["min_total_effort_fte"])):
        findings.append(
            "declared effort totals %.3g of a person against the %.3g the class "
            "asks for; responsibility at that fraction is assignment on paper"
            % (effort, float(policy["min_total_effort_fte"]))
        )
        result["verdict"] = EFFORT_BELOW_FLOOR
        return result

    location = _require_label(
        "decision_record_location", case.get("decision_record_location", "")
    )
    result["decision_record_location"] = location
    if policy["require_decision_record_location"] and not location:
        findings.append(
            "no location is stated for the parts decision record; at this class "
            "there is no board minute to fall back on"
        )
        result["verdict"] = DECISION_RECORD_NOT_LOCATED
        return result

    embedded = embedded_roles(checked)
    if embedded:
        advisories.append(
            "role %s sits inside the design authority; ordinary at this class, "
            "and the reason the decision record location matters more here than "
            "it does higher up" % ", ".join(embedded)
        )

    result["verdict"] = ORGANIZATION_MEETS_CLASS_THREE
    return result
