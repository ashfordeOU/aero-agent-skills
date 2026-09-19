#!/usr/bin/env python3
"""Quality and safety planning for a space test centre.

Anchor: ECSS-Q-ST-20-07 clause 5.3.2, the requirement that a test centre
plans its quality and safety: objectives it can be measured against,
resources planned against what the objectives need, and management
programmes that carry the objectives to their milestones. The procedure
below is a paraphrase into implementable steps; no standard text is
reproduced.

Four things follow from what the plan is for.

An objective nobody can measure is an intention. A metric name, a finite
numeric target and a direction saying which way is better are what turn
it into something the centre can be held to, and an objective missing
any of those is counted as unmeasurable rather than as merely unmet.

Attainment depends on the direction. A defect rate of two against a
target of five is attained; an on-time delivery of two against a target
of five is not. The comparison is made once, in one place, and the
exact-equality case is settled with a tolerance so the same objective
does not pass on one host and fail on another.

Resource planning is taken against what the objectives need, not against
what the centre happens to have. A resource planned below its
requirement is a shortfall whose size matters, so the coverage ratio and
the named resources are both reported.

A programme is the vehicle an objective travels in. An objective no
approved programme carries has nobody driving it, and a programme
carrying an objective that does not exist is pointing at nothing - the
two are reported apart because one needs a programme and the other
needs a correction.

The policy numbers below are declared centre values, not physical
constants: a centre substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

HIGHER_IS_BETTER = "higher-is-better"
LOWER_IS_BETTER = "lower-is-better"
RECOGNISED_DIRECTIONS = (HIGHER_IS_BETTER, LOWER_IS_BETTER)

PROGRAMME_DRAFT = "draft"
PROGRAMME_APPROVED = "approved"
PROGRAMME_CLOSED = "closed"
RECOGNISED_PROGRAMME_STATES = (PROGRAMME_DRAFT, PROGRAMME_APPROVED, PROGRAMME_CLOSED)

REQUIRED_OBJECTIVE_FIELDS = (
    "objective_id",
    "metric",
    "target",
    "direction",
    "achieved",
    "owner",
    "due_day",
)

REQUIRED_RESOURCE_FIELDS = ("resource_id", "required_units", "planned_units")

REQUIRED_PROGRAMME_FIELDS = ("programme_id", "state", "covers_objectives", "milestones")

PLAN_ABSENT = "quality-and-safety-plan-absent"
OBJECTIVES_UNMEASURABLE = "quality-and-safety-objectives-unmeasurable"
OBJECTIVES_UNOWNED = "quality-and-safety-objectives-unowned"
RESOURCES_UNDER_PLANNED = "quality-and-safety-resources-under-planned"
OBJECTIVES_UNCOVERED = "quality-and-safety-objectives-uncovered"
PLAN_ESTABLISHED = "quality-and-safety-plan-established"

DEFAULT_PLANNING_POLICY = {
    "min_resource_coverage": 1.0,
    "min_objective_attainment": 0.8,
    "require_objective_owner": True,
    "require_programme_milestones": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_day(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number != int(number):
        raise ValueError("%s must be a whole non-negative day, got %r" % (name, value))
    return int(number)


def _require_token(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty identifier, got %r" % (name, value))
    return value.strip()


def _require_token_list(name, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence of identifiers, got %r" % (name, value))
    return [_require_token("%s[%d]" % (name, i), item) for i, item in enumerate(value)]


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def at_least(value, bound):
    """Return True when value reaches bound, absorbing representation error."""
    left = _require_number("value", value)
    right = _require_number("bound", bound)
    return left > right or math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def at_most(value, bound):
    """Return True when value stays at or under bound, absorbing representation error."""
    left = _require_number("value", value)
    right = _require_number("bound", bound)
    return left < right or math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def validate_planning_policy(policy):
    """Return the validated quality and safety planning policy."""
    if not isinstance(policy, dict):
        raise ValueError("planning policy must be a mapping")
    for key in policy:
        if key not in DEFAULT_PLANNING_POLICY:
            raise ValueError("unrecognised planning policy key '%s'" % key)
    merged = dict(DEFAULT_PLANNING_POLICY)
    merged.update(policy)
    return {
        "min_resource_coverage": _require_fraction(
            "min_resource_coverage", merged["min_resource_coverage"]
        ),
        "min_objective_attainment": _require_fraction(
            "min_objective_attainment", merged["min_objective_attainment"]
        ),
        "require_objective_owner": _require_flag(
            "require_objective_owner", merged["require_objective_owner"]
        ),
        "require_programme_milestones": _require_flag(
            "require_programme_milestones", merged["require_programme_milestones"]
        ),
    }


def validate_objective(objective):
    """Return one validated quality or safety objective."""
    if not isinstance(objective, dict):
        raise ValueError("an objective must be a mapping, got %r" % (objective,))
    for field in REQUIRED_OBJECTIVE_FIELDS:
        if field not in objective:
            raise ValueError("objective missing field '%s'" % field)
    objective_id = _require_token("objective_id", objective["objective_id"])
    direction = objective["direction"]
    if direction is not None:
        direction = _require_token("direction", direction)
        if direction not in RECOGNISED_DIRECTIONS:
            raise ValueError("unrecognised objective direction '%s'" % direction)
    metric = objective["metric"]
    if metric is not None:
        metric = _require_token("metric", metric)
    target = objective["target"]
    if target is not None:
        target = _require_number("target of '%s'" % objective_id, target)
    achieved = objective["achieved"]
    if achieved is not None:
        achieved = _require_number("achieved of '%s'" % objective_id, achieved)
    owner = objective["owner"]
    if owner is not None:
        owner = _require_token("owner", owner)
    return {
        "objective_id": objective_id,
        "metric": metric,
        "target": target,
        "direction": direction,
        "achieved": achieved,
        "owner": owner,
        "due_day": _require_day("due_day", objective["due_day"]),
    }


def validate_resource(resource):
    """Return one validated planned resource line."""
    if not isinstance(resource, dict):
        raise ValueError("a resource line must be a mapping, got %r" % (resource,))
    for field in REQUIRED_RESOURCE_FIELDS:
        if field not in resource:
            raise ValueError("resource line missing field '%s'" % field)
    resource_id = _require_token("resource_id", resource["resource_id"])
    required_units = _require_number(
        "required_units of '%s'" % resource_id, resource["required_units"]
    )
    if required_units <= 0.0:
        raise ValueError("resource '%s' requires a positive quantity" % resource_id)
    return {
        "resource_id": resource_id,
        "required_units": required_units,
        "planned_units": _require_non_negative(
            "planned_units of '%s'" % resource_id, resource["planned_units"]
        ),
    }


def validate_programme(programme):
    """Return one validated management programme."""
    if not isinstance(programme, dict):
        raise ValueError("a management programme must be a mapping, got %r" % (programme,))
    for field in REQUIRED_PROGRAMME_FIELDS:
        if field not in programme:
            raise ValueError("management programme missing field '%s'" % field)
    state = _require_token("state", programme["state"])
    if state not in RECOGNISED_PROGRAMME_STATES:
        raise ValueError("unrecognised programme state '%s'" % state)
    return {
        "programme_id": _require_token("programme_id", programme["programme_id"]),
        "state": state,
        "covers_objectives": _require_token_list(
            "covers_objectives", programme["covers_objectives"]
        ),
        "milestones": _require_token_list("milestones", programme["milestones"]),
    }


def validate_plan(plan):
    """Return the validated quality and safety plan."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping")
    for field in ("established", "objectives", "resources", "programmes"):
        if field not in plan:
            raise ValueError("plan missing field '%s'" % field)
    for name in ("objectives", "resources", "programmes"):
        if not isinstance(plan[name], (list, tuple)):
            raise ValueError("%s must be a sequence" % name)
    objectives = [validate_objective(item) for item in plan["objectives"]]
    resources = [validate_resource(item) for item in plan["resources"]]
    programmes = [validate_programme(item) for item in plan["programmes"]]
    for label, rows, key in (
        ("objective", objectives, "objective_id"),
        ("resource", resources, "resource_id"),
        ("programme", programmes, "programme_id"),
    ):
        seen = set()
        for row in rows:
            if row[key] in seen:
                raise ValueError("%s '%s' is registered twice" % (label, row[key]))
            seen.add(row[key])
    return {
        "validated_plan": True,
        "established": _require_flag("established", plan["established"]),
        "objectives": objectives,
        "resources": resources,
        "programmes": programmes,
        "objective_ids": {o["objective_id"] for o in objectives},
    }


def _as_plan(plan):
    """Return the record already validated, validating a raw one first."""
    if isinstance(plan, dict) and plan.get("validated_plan"):
        return plan
    return validate_plan(plan)


def objective_is_measurable(objective):
    """Return True when the objective carries a metric, target and direction."""
    record = validate_objective(objective)
    return (
        record["metric"] is not None
        and record["target"] is not None
        and record["direction"] is not None
    )


def unmeasurable_objectives(plan):
    """Return the objective ids that cannot be measured as written."""
    record = _as_plan(plan)
    return [
        o["objective_id"] for o in record["objectives"] if not objective_is_measurable(o)
    ]


def unowned_objectives(plan):
    """Return the objective ids with nobody named against them."""
    record = _as_plan(plan)
    return [o["objective_id"] for o in record["objectives"] if o["owner"] is None]


def objective_is_attained(objective):
    """Return True when a measurable objective reached its target."""
    record = validate_objective(objective)
    if not objective_is_measurable(record):
        raise ValueError(
            "objective '%s' is not measurable and cannot be attained" % record["objective_id"]
        )
    if record["achieved"] is None:
        return False
    if record["direction"] == HIGHER_IS_BETTER:
        return at_least(record["achieved"], record["target"])
    return at_most(record["achieved"], record["target"])


def objective_attainment(plan):
    """Return the fraction of measurable objectives that reached their target."""
    record = _as_plan(plan)
    measurable = [o for o in record["objectives"] if objective_is_measurable(o)]
    if not measurable:
        return 0.0
    attained = sum(1 for o in measurable if objective_is_attained(o))
    return attained / float(len(measurable))


def unattained_objectives(plan):
    """Return the measurable objective ids that did not reach their target."""
    record = _as_plan(plan)
    return [
        o["objective_id"]
        for o in record["objectives"]
        if objective_is_measurable(o) and not objective_is_attained(o)
    ]


def resource_coverage(plan):
    """Return the fraction of required resource units the plan actually plans."""
    record = _as_plan(plan)
    if not record["resources"]:
        return 0.0
    required = sum(r["required_units"] for r in record["resources"])
    planned = sum(min(r["planned_units"], r["required_units"]) for r in record["resources"])
    return planned / required


def resource_shortfalls(plan):
    """Return (resource id, shortfall) for every under-planned resource line."""
    record = _as_plan(plan)
    out = []
    for resource in record["resources"]:
        if not at_least(resource["planned_units"], resource["required_units"]):
            out.append((resource["resource_id"], resource["required_units"] - resource["planned_units"]))
    return out


def uncovered_objectives(plan, policy=None):
    """Return the objective ids no approved programme carries."""
    record = _as_plan(plan)
    rules = validate_planning_policy(policy or {})
    carried = set()
    for programme in record["programmes"]:
        if programme["state"] != PROGRAMME_APPROVED:
            continue
        if rules["require_programme_milestones"] and not programme["milestones"]:
            continue
        carried.update(programme["covers_objectives"])
    return [o["objective_id"] for o in record["objectives"] if o["objective_id"] not in carried]


def dangling_programme_references(plan):
    """Return (programme id, objective id) for every reference at no objective."""
    record = _as_plan(plan)
    known = record["objective_ids"]
    out = []
    for programme in record["programmes"]:
        for objective_id in programme["covers_objectives"]:
            if objective_id not in known:
                out.append((programme["programme_id"], objective_id))
    return out


def assess_planning(case):
    """Run the full clause 5.3.2 quality and safety planning assessment.

    case keys: plan (the planning record) and optional policy.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    if "plan" not in case:
        raise ValueError("case missing required key 'plan'")
    rules = validate_planning_policy(case.get("policy") or {})
    record = validate_plan(case["plan"])

    unmeasurable = unmeasurable_objectives(record)
    unowned = unowned_objectives(record) if rules["require_objective_owner"] else []
    coverage = resource_coverage(record)
    shortfalls = resource_shortfalls(record)
    uncovered = uncovered_objectives(record, rules)
    dangling = dangling_programme_references(record)
    attainment = objective_attainment(record) if not unmeasurable else 0.0
    unattained = unattained_objectives(record)

    findings = []
    advisories = []

    if not record["established"] or not record["objectives"]:
        verdict = PLAN_ABSENT
        findings.append("no quality and safety plan has been established")
    elif unmeasurable:
        verdict = OBJECTIVES_UNMEASURABLE
        findings.append(
            "%d objective(s) carry no metric, target or direction: %s"
            % (len(unmeasurable), ", ".join(unmeasurable))
        )
    elif unowned:
        verdict = OBJECTIVES_UNOWNED
        findings.append(
            "%d objective(s) have nobody named against them: %s"
            % (len(unowned), ", ".join(unowned))
        )
    elif not at_least(coverage, rules["min_resource_coverage"]):
        verdict = RESOURCES_UNDER_PLANNED
        findings.append(
            "resource coverage %.3f is under the required %.3f; short: %s"
            % (
                coverage,
                rules["min_resource_coverage"],
                ", ".join("%s(%g)" % pair for pair in shortfalls) or "none",
            )
        )
    elif uncovered:
        verdict = OBJECTIVES_UNCOVERED
        findings.append(
            "%d objective(s) are carried by no approved programme: %s"
            % (len(uncovered), ", ".join(uncovered))
        )
    else:
        verdict = PLAN_ESTABLISHED

    if dangling:
        advisories.append(
            "%d programme reference(s) point at no objective: %s"
            % (len(dangling), ", ".join("%s->%s" % pair for pair in dangling))
        )
    if unattained and not unmeasurable:
        advisories.append(
            "%d objective(s) have not reached their target: %s"
            % (len(unattained), ", ".join(unattained))
        )
    if not unmeasurable and not at_least(attainment, rules["min_objective_attainment"]):
        advisories.append(
            "objective attainment %.3f is under the %.3f the centre set itself"
            % (attainment, rules["min_objective_attainment"])
        )

    return {
        "verdict": verdict,
        "established": record["established"],
        "unmeasurable_objectives": unmeasurable,
        "unowned_objectives": unowned,
        "resource_coverage": coverage,
        "resource_shortfalls": shortfalls,
        "uncovered_objectives": uncovered,
        "dangling_programme_references": dangling,
        "objective_attainment": attainment,
        "unattained_objectives": unattained,
        "findings": findings,
        "advisories": advisories,
        "policy": rules,
    }
