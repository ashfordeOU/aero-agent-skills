#!/usr/bin/env python3
"""Device validation plan consolidation (ECSS-E-ST-20-40C 5.6.4).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
Validation asks a different question from verification. Verification asks
whether the device was built to the specification; validation asks whether
the finished device does the job it was procured for. Consolidating the
plan at the end of layout means fixing, once and for all, how each of
those needs will be demonstrated on real hardware.

Four things have to agree before the plan is consolidated:

* every need has at least one activity that demonstrates it. A need with
  no activity is the gap the plan exists to close, and it is invisible
  while the activity list is read on its own because every activity in it
  is legitimate;
* the environment each activity runs in can actually demonstrate that
  kind of need. An endurance need demonstrated on a bench cannot be
  demonstrated there, however carefully the activity is written;
* the resources an activity depends on exist. An activity needing a
  flight-representative rig that will not be built is a plan on paper;
* the order is executable. An activity scheduled before something it
  depends on cannot run, and a dependency loop cannot run at all -- the
  loop is the one defect that survives every per-activity check, because
  each activity in it looks perfectly ordered against its own
  predecessor.

Consolidation coverage is the fraction of needs carrying at least one
demonstrable activity, and a figure landing exactly on its goal meets it.
"""

import math

# Kinds of need a validation plan demonstrates.
NEED_KINDS = (
    "functional-use-case",
    "performance-envelope",
    "interface-compatibility",
    "environmental-endurance",
    "operational-procedure",
)

# Environments an activity can run in, from least to most representative.
ENVIRONMENTS = (
    "bench-standalone",
    "board-level",
    "system-representative",
    "flight-representative",
)

# Environments able to demonstrate each kind of need.
SUITABLE_ENVIRONMENTS = {
    "functional-use-case": ENVIRONMENTS,
    "performance-envelope": (
        "board-level",
        "system-representative",
        "flight-representative",
    ),
    "interface-compatibility": (
        "board-level",
        "system-representative",
        "flight-representative",
    ),
    "environmental-endurance": (
        "system-representative",
        "flight-representative",
    ),
    "operational-procedure": (
        "system-representative",
        "flight-representative",
    ),
}

REL_TOL = 1e-12
ABS_TOL = 1e-18

_NEED_KEYS = ("id", "kind", "statement")
_ACTIVITY_KEYS = ("id", "need", "environment", "resources", "depends_on", "slot")


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _slot(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer schedule slot, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (name, value))
    return value


def _fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def normalize_need_kind(value):
    """Fold a need kind onto one of the recognised kinds."""
    key = " ".join(_text("kind", value).lower().replace("_", " ").split())
    key = key.replace(" ", "-")
    aliases = {
        "functional-use-case": "functional-use-case",
        "use-case": "functional-use-case",
        "function": "functional-use-case",
        "performance-envelope": "performance-envelope",
        "performance": "performance-envelope",
        "interface-compatibility": "interface-compatibility",
        "interface": "interface-compatibility",
        "environmental-endurance": "environmental-endurance",
        "endurance": "environmental-endurance",
        "environmental": "environmental-endurance",
        "operational-procedure": "operational-procedure",
        "procedure": "operational-procedure",
    }
    if key in aliases:
        return aliases[key]
    raise ValueError(
        "unknown need kind %r; use one of %s" % (value, ", ".join(NEED_KINDS))
    )


def normalize_environment(value):
    """Fold a validation environment onto one of the recognised ones."""
    key = " ".join(_text("environment", value).lower().replace("_", " ").split())
    key = key.replace(" ", "-")
    aliases = {
        "bench-standalone": "bench-standalone",
        "bench": "bench-standalone",
        "standalone": "bench-standalone",
        "board-level": "board-level",
        "breadboard": "board-level",
        "evaluation-board": "board-level",
        "system-representative": "system-representative",
        "engineering-model": "system-representative",
        "flight-representative": "flight-representative",
        "qualification-model": "flight-representative",
        "flight-model": "flight-representative",
    }
    if key in aliases:
        return aliases[key]
    raise ValueError(
        "unknown validation environment %r; use one of %s"
        % (value, ", ".join(ENVIRONMENTS))
    )


def environments_for(kind):
    """Environments able to demonstrate this kind of need."""
    return SUITABLE_ENVIRONMENTS[normalize_need_kind(kind)]


def environment_can_demonstrate(kind, environment):
    """True when this environment can demonstrate this kind of need."""
    return normalize_environment(environment) in environments_for(kind)


def validate_needs(entries):
    """Check the needs to be validated and return them keyed by identifier."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("needs must be a list")
    resolved = {}
    order = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("needs[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_NEED_KEYS))
        if unknown:
            raise ValueError(
                "needs[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "kind"):
            if key not in entry:
                raise ValueError("needs[%d] missing key: %s" % (index, key))
        need_id = _text("needs[%d].id" % index, entry["id"])
        if need_id in resolved:
            raise ValueError("duplicate need id %r" % need_id)
        resolved[need_id] = {
            "id": need_id,
            "kind": normalize_need_kind(entry["kind"]),
            "statement": _text(
                "needs[%d].statement" % index,
                entry.get("statement", ""),
                allow_empty=True,
            ),
        }
        order.append(need_id)
    return resolved, order


def validate_activities(entries):
    """Check the validation activities and return them keyed by identifier."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("activities must be a list")
    resolved = {}
    order = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("activities[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_ACTIVITY_KEYS))
        if unknown:
            raise ValueError(
                "activities[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "need", "environment"):
            if key not in entry:
                raise ValueError("activities[%d] missing key: %s" % (index, key))
        activity_id = _text("activities[%d].id" % index, entry["id"])
        if activity_id in resolved:
            raise ValueError("duplicate activity id %r" % activity_id)
        resources = entry.get("resources", [])
        if not isinstance(resources, (list, tuple)):
            raise ValueError("activities[%d].resources must be a list" % index)
        depends = entry.get("depends_on", [])
        if not isinstance(depends, (list, tuple)):
            raise ValueError("activities[%d].depends_on must be a list" % index)
        resolved_depends = []
        for position, dependency in enumerate(depends):
            name = _text(
                "activities[%d].depends_on[%d]" % (index, position), dependency
            )
            if name == activity_id:
                raise ValueError("activity %r depends on itself" % activity_id)
            if name in resolved_depends:
                raise ValueError(
                    "activity %r lists dependency %r twice" % (activity_id, name)
                )
            resolved_depends.append(name)
        resolved[activity_id] = {
            "id": activity_id,
            "need": _text("activities[%d].need" % index, entry["need"]),
            "environment": normalize_environment(entry["environment"]),
            "resources": [
                _text("activities[%d].resources[%d]" % (index, position), resource)
                for position, resource in enumerate(resources)
            ],
            "depends_on": resolved_depends,
            "slot": _slot("activities[%d].slot" % index, entry.get("slot", 0)),
        }
        order.append(activity_id)
    return resolved, order


def detect_dependency_cycle(activities):
    """Identifiers taking part in a dependency loop, sorted; empty if none.

    An activity is in a loop when it is reachable from itself through the
    dependency edges the plan actually carries. Activities merely stuck
    behind a loop are not in it, so the finding names the activities that
    have to be re-ordered rather than everything downstream of them.
    """
    edges = {
        a: sorted(set(activities[a]["depends_on"]) & set(activities))
        for a in activities
    }
    looped = []
    for start in sorted(edges):
        seen = set()
        stack = list(edges[start])
        while stack:
            node = stack.pop()
            if node == start:
                looped.append(start)
                break
            if node in seen:
                continue
            seen.add(node)
            stack.extend(edges[node])
    return looped


def consolidation_coverage(needs, activities):
    """Fraction of needs carrying at least one demonstrable activity."""
    if not needs:
        raise ValueError("consolidation coverage needs at least one need")
    demonstrated = set()
    for activity in activities.values():
        need = needs.get(activity["need"])
        if need is None:
            continue
        if environment_can_demonstrate(need["kind"], activity["environment"]):
            demonstrated.add(need["id"])
    return len(demonstrated) / len(needs)


def meets_goal(achieved, goal):
    """True when coverage reaches its goal, exact landings included."""
    achieved = _fraction("achieved", achieved)
    goal = _fraction("goal", goal)
    return achieved > goal or math.isclose(
        achieved, goal, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def evaluate_validation_plan(plan, coverage_goal=1.0):
    """Full 5.6.4 assessment of one consolidated device validation plan.

    Returns the coverage reached, the needs left undemonstrated, the
    findings and the verdict.
    """
    if not isinstance(plan, dict):
        raise ValueError(
            "plan must be a mapping of needs, activities and available resources"
        )
    known = {"needs", "activities", "available_resources"}
    unknown = sorted(set(plan) - known)
    if unknown:
        raise ValueError("unknown plan keys: %s" % ", ".join(unknown))
    for key in ("needs", "activities"):
        if key not in plan:
            raise ValueError("plan missing required key: %s" % key)

    needs, need_order = validate_needs(plan["needs"])
    if not needs:
        raise ValueError("the plan must carry at least one need to validate")
    activities, activity_order = validate_activities(plan["activities"])
    available = plan.get("available_resources", [])
    if not isinstance(available, (list, tuple, set)):
        raise ValueError("available_resources must be a list, tuple or set")
    available = {
        _text("available_resources[%d]" % index, resource)
        for index, resource in enumerate(sorted(available))
    }
    coverage_goal = _fraction("coverage_goal", coverage_goal)

    findings = []
    demonstrated = set()

    for activity_id in activity_order:
        activity = activities[activity_id]
        need = needs.get(activity["need"])
        if need is None:
            findings.append(
                {
                    "code": "activity-against-unknown-need",
                    "activity": activity_id,
                    "detail": "%s demonstrates %r, which the plan does not carry "
                    "as a need" % (activity_id, activity["need"]),
                }
            )
        elif not environment_can_demonstrate(need["kind"], activity["environment"]):
            findings.append(
                {
                    "code": "environment-cannot-demonstrate-need",
                    "activity": activity_id,
                    "need": need["id"],
                    "environment": activity["environment"],
                    "detail": "a %s need cannot be demonstrated at %s; use one of "
                    "%s"
                    % (
                        need["kind"],
                        activity["environment"],
                        ", ".join(environments_for(need["kind"])),
                    ),
                }
            )
        else:
            demonstrated.add(need["id"])

        for resource in activity["resources"]:
            if resource not in available:
                findings.append(
                    {
                        "code": "activity-depends-on-unavailable-resource",
                        "activity": activity_id,
                        "resource": resource,
                        "detail": "%s needs %r, which the plan does not list as "
                        "available" % (activity_id, resource),
                    }
                )

        for dependency in activity["depends_on"]:
            if dependency not in activities:
                findings.append(
                    {
                        "code": "prerequisite-not-in-the-plan",
                        "activity": activity_id,
                        "prerequisite": dependency,
                        "detail": "%s depends on %r, which the plan does not carry"
                        % (activity_id, dependency),
                    }
                )
            elif activity["slot"] <= activities[dependency]["slot"]:
                findings.append(
                    {
                        "code": "activity-scheduled-before-its-prerequisite",
                        "activity": activity_id,
                        "prerequisite": dependency,
                        "detail": "%s runs in slot %d, at or before %s in slot %d"
                        % (
                            activity_id,
                            activity["slot"],
                            dependency,
                            activities[dependency]["slot"],
                        ),
                    }
                )

    looped = detect_dependency_cycle(activities)
    if looped:
        findings.append(
            {
                "code": "dependency-loop-in-the-schedule",
                "activities": looped,
                "detail": "the activities %s depend on each other in a loop and "
                "none of them can start" % ", ".join(looped),
            }
        )

    for need_id in need_order:
        if need_id not in demonstrated:
            findings.append(
                {
                    "code": "need-without-a-demonstrable-activity",
                    "need": need_id,
                    "detail": "%s has no activity able to demonstrate it" % need_id,
                }
            )

    coverage = consolidation_coverage(needs, activities)
    if not meets_goal(coverage, coverage_goal):
        findings.append(
            {
                "code": "consolidation-coverage-goal-missed",
                "achieved": coverage,
                "goal": coverage_goal,
                "detail": "the plan demonstrates %.1f %% of the needs against a "
                "%.1f %% goal" % (100.0 * coverage, 100.0 * coverage_goal),
            }
        )

    return {
        "need_count": len(needs),
        "activity_count": len(activities),
        "coverage": coverage,
        "demonstrated_needs": sorted(demonstrated),
        "undemonstrated_needs": sorted(set(needs) - demonstrated),
        "looped_activities": looped,
        "findings": findings,
        "consolidated": not findings,
    }
