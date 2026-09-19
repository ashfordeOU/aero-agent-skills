#!/usr/bin/env python3
"""The quality and safety management system a space test centre operates.

Anchor: ECSS-Q-ST-20-07 clause 5.1, the requirement that a test centre
establishes and keeps a quality and safety management system: a declared
scope, documented processes covering the test services the centre sells,
and a continual-improvement loop that closes what it opens. The procedure
below is a paraphrase into implementable steps; no standard text is
reproduced.

Four things follow from what the management system is for.

A scope that does not name a service the centre performs leaves that
service outside the system. Scope is therefore taken against the services
actually offered, not against the scope statement reading back to itself,
because a scope graded against its own wording is always complete.

A service in scope is covered when an approved process describes it. A
draft process, or a process nobody approved, is a plan to cover the
service rather than coverage of it, and a process past its review age is
covering the service with wording the centre no longer stands behind.

Continual improvement is a loop, not a register. An improvement action
raised and never closed, or closed with its effectiveness never verified,
leaves the loop open; a loop whose actions all sit open is a stalled loop
regardless of how many were raised.

Management review is the cadence that keeps the other three honest. A
review older than the interval the centre declared means the system is
running without anyone standing over it.

The policy numbers below are declared centre values, not physical
constants: a centre substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PROCESS_DRAFT = "draft"
PROCESS_APPROVED = "approved"
PROCESS_WITHDRAWN = "withdrawn"
RECOGNISED_PROCESS_STATES = (PROCESS_DRAFT, PROCESS_APPROVED, PROCESS_WITHDRAWN)

REQUIRED_PROCESS_FIELDS = (
    "process_id",
    "state",
    "covers_services",
    "approved_on_day",
    "last_reviewed_day",
)

REQUIRED_ACTION_FIELDS = (
    "action_id",
    "raised_on_day",
    "closed_on_day",
    "effectiveness_verified",
)

SYSTEM_ABSENT = "management-system-absent"
SCOPE_INCOMPLETE = "management-system-scope-incomplete"
PROCESS_COVERAGE_INSUFFICIENT = "management-system-process-coverage-insufficient"
PROCESS_APPROVAL_BROKEN = "management-system-process-approval-broken"
IMPROVEMENT_LOOP_STALLED = "management-system-improvement-loop-stalled"
MANAGEMENT_REVIEW_STALE = "management-system-management-review-stale"
SYSTEM_ESTABLISHED = "management-system-established"

DEFAULT_SYSTEM_POLICY = {
    "min_process_coverage": 1.0,
    "min_improvement_closure": 0.5,
    "process_review_interval_days": 730,
    "management_review_interval_days": 365,
    "require_effectiveness_verification": True,
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


def _require_day(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number != int(number):
        raise ValueError("%s must be a whole non-negative day, got %r" % (name, value))
    return int(number)


def _require_interval(name, value):
    number = _require_number(name, value)
    if number <= 0.0 or number != int(number):
        raise ValueError("%s must be a whole positive day count, got %r" % (name, value))
    return int(number)


def _require_token(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty identifier, got %r" % (name, value))
    return value.strip()


def _require_token_list(name, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence of identifiers, got %r" % (name, value))
    out = []
    for index, item in enumerate(value):
        out.append(_require_token("%s[%d]" % (name, index), item))
    return out


def at_least(value, bound):
    """Return True when value reaches bound, absorbing representation error."""
    left = _require_number("value", value)
    right = _require_number("bound", bound)
    return left > right or math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def validate_system_policy(policy):
    """Return the validated management-system policy."""
    if not isinstance(policy, dict):
        raise ValueError("system policy must be a mapping")
    merged = dict(DEFAULT_SYSTEM_POLICY)
    for key in policy:
        if key not in DEFAULT_SYSTEM_POLICY:
            raise ValueError("unrecognised system policy key '%s'" % key)
    merged.update(policy)
    validated = {
        "min_process_coverage": _require_fraction(
            "min_process_coverage", merged["min_process_coverage"]
        ),
        "min_improvement_closure": _require_fraction(
            "min_improvement_closure", merged["min_improvement_closure"]
        ),
        "process_review_interval_days": _require_interval(
            "process_review_interval_days", merged["process_review_interval_days"]
        ),
        "management_review_interval_days": _require_interval(
            "management_review_interval_days", merged["management_review_interval_days"]
        ),
    }
    flag = merged["require_effectiveness_verification"]
    if not isinstance(flag, bool):
        raise ValueError("require_effectiveness_verification must be a boolean")
    validated["require_effectiveness_verification"] = flag
    if validated["process_review_interval_days"] < validated["management_review_interval_days"]:
        raise ValueError(
            "a process review interval shorter than the management review interval "
            "would review the wording more often than the system that owns it"
        )
    return validated


def validate_process(process):
    """Return one validated documented-process record."""
    if not isinstance(process, dict):
        raise ValueError("a documented process must be a mapping, got %r" % (process,))
    for field in REQUIRED_PROCESS_FIELDS:
        if field not in process:
            raise ValueError("documented process missing field '%s'" % field)
    state = _require_token("state", process["state"])
    if state not in RECOGNISED_PROCESS_STATES:
        raise ValueError("unrecognised process state '%s'" % state)
    approved_on = process["approved_on_day"]
    if approved_on is not None:
        approved_on = _require_day("approved_on_day", approved_on)
    reviewed_on = process["last_reviewed_day"]
    if reviewed_on is not None:
        reviewed_on = _require_day("last_reviewed_day", reviewed_on)
    if state == PROCESS_APPROVED and approved_on is None:
        raise ValueError(
            "process '%s' is approved with no approval day" % process["process_id"]
        )
    return {
        "process_id": _require_token("process_id", process["process_id"]),
        "state": state,
        "covers_services": _require_token_list(
            "covers_services", process["covers_services"]
        ),
        "approved_on_day": approved_on,
        "last_reviewed_day": reviewed_on,
    }


def validate_improvement_action(action):
    """Return one validated continual-improvement action record."""
    if not isinstance(action, dict):
        raise ValueError("an improvement action must be a mapping, got %r" % (action,))
    for field in REQUIRED_ACTION_FIELDS:
        if field not in action:
            raise ValueError("improvement action missing field '%s'" % field)
    raised = _require_day("raised_on_day", action["raised_on_day"])
    closed = action["closed_on_day"]
    if closed is not None:
        closed = _require_day("closed_on_day", closed)
        if closed < raised:
            raise ValueError(
                "improvement action '%s' closes before it was raised"
                % action["action_id"]
            )
    verified = action["effectiveness_verified"]
    if not isinstance(verified, bool):
        raise ValueError("effectiveness_verified must be a boolean")
    if verified and closed is None:
        raise ValueError(
            "improvement action '%s' verifies an effectiveness it never closed"
            % action["action_id"]
        )
    return {
        "action_id": _require_token("action_id", action["action_id"]),
        "raised_on_day": raised,
        "closed_on_day": closed,
        "effectiveness_verified": verified,
    }


def validate_system(system):
    """Return the validated management-system record."""
    if not isinstance(system, dict):
        raise ValueError("management system must be a mapping")
    for field in ("established", "declared_scope", "services_offered", "processes",
                  "improvement_actions", "last_management_review_day", "as_of_day"):
        if field not in system:
            raise ValueError("management system missing field '%s'" % field)
    established = system["established"]
    if not isinstance(established, bool):
        raise ValueError("established must be a boolean")
    as_of_day = _require_day("as_of_day", system["as_of_day"])
    last_review = system["last_management_review_day"]
    if last_review is not None:
        last_review = _require_day("last_management_review_day", last_review)
        if last_review > as_of_day:
            raise ValueError("the management review is dated after the assessment day")
    services = _require_token_list("services_offered", system["services_offered"])
    if len(set(services)) != len(services):
        raise ValueError("services_offered lists the same service twice")
    scope = _require_token_list("declared_scope", system["declared_scope"])
    if len(set(scope)) != len(scope):
        raise ValueError("declared_scope lists the same service twice")
    if not isinstance(system["processes"], (list, tuple)):
        raise ValueError("processes must be a sequence")
    processes = [validate_process(item) for item in system["processes"]]
    seen = set()
    for process in processes:
        if process["process_id"] in seen:
            raise ValueError("process '%s' is registered twice" % process["process_id"])
        seen.add(process["process_id"])
    if not isinstance(system["improvement_actions"], (list, tuple)):
        raise ValueError("improvement_actions must be a sequence")
    actions = [validate_improvement_action(item) for item in system["improvement_actions"]]
    action_ids = set()
    for action in actions:
        if action["action_id"] in action_ids:
            raise ValueError("improvement action '%s' is registered twice" % action["action_id"])
        action_ids.add(action["action_id"])
        if action["closed_on_day"] is not None and action["closed_on_day"] > as_of_day:
            raise ValueError(
                "improvement action '%s' closes after the assessment day" % action["action_id"]
            )
    return {
        "validated_system": True,
        "established": established,
        "declared_scope": scope,
        "services_offered": services,
        "processes": processes,
        "improvement_actions": actions,
        "last_management_review_day": last_review,
        "as_of_day": as_of_day,
    }


def _as_system(system):
    """Return the record already validated, validating a raw one first."""
    if isinstance(system, dict) and system.get("validated_system"):
        return system
    return validate_system(system)


def scope_gaps(system):
    """Return the offered services the declared scope never names."""
    record = _as_system(system)
    declared = set(record["declared_scope"])
    return [name for name in record["services_offered"] if name not in declared]


def scope_overreach(system):
    """Return the scoped services the centre does not actually offer."""
    record = _as_system(system)
    offered = set(record["services_offered"])
    return [name for name in record["declared_scope"] if name not in offered]


def approved_processes(system):
    """Return the processes that carry an approval."""
    record = _as_system(system)
    return [p for p in record["processes"] if p["state"] == PROCESS_APPROVED]


def services_in_scope(system):
    """Return the services that are both offered and inside the declared scope."""
    record = _as_system(system)
    declared = set(record["declared_scope"])
    return [name for name in record["services_offered"] if name in declared]


def uncovered_services(system):
    """Return the in-scope services no approved process describes."""
    record = _as_system(system)
    covered = set()
    for process in approved_processes(record):
        covered.update(process["covers_services"])
    return [name for name in services_in_scope(record) if name not in covered]


def process_coverage(system):
    """Return the fraction of in-scope services an approved process covers."""
    record = _as_system(system)
    scoped = services_in_scope(record)
    if not scoped:
        return 0.0
    missing = len(uncovered_services(record))
    return (len(scoped) - missing) / float(len(scoped))


def unapproved_processes_in_use(system):
    """Return the process ids covering a scoped service without an approval."""
    record = _as_system(system)
    scoped = set(services_in_scope(record))
    out = []
    for process in record["processes"]:
        if process["state"] == PROCESS_APPROVED:
            continue
        if process["state"] == PROCESS_WITHDRAWN:
            continue
        if scoped.intersection(process["covers_services"]):
            out.append(process["process_id"])
    return out


def processes_past_review(system, policy=None):
    """Return the approved process ids whose review is older than the interval."""
    record = _as_system(system)
    rules = validate_system_policy(policy or {})
    limit = rules["process_review_interval_days"]
    out = []
    for process in approved_processes(record):
        reviewed = process["last_reviewed_day"]
        if reviewed is None:
            out.append(process["process_id"])
            continue
        if record["as_of_day"] - reviewed > limit:
            out.append(process["process_id"])
    return out


def open_improvement_actions(system):
    """Return the improvement actions with no closure day."""
    record = _as_system(system)
    return [a for a in record["improvement_actions"] if a["closed_on_day"] is None]


def unverified_closures(system):
    """Return the closed improvement actions whose effectiveness was never verified."""
    record = _as_system(system)
    return [
        a["action_id"]
        for a in record["improvement_actions"]
        if a["closed_on_day"] is not None and not a["effectiveness_verified"]
    ]


def improvement_closure(system, policy=None):
    """Return the fraction of improvement actions closed to the policy's standard."""
    record = _as_system(system)
    rules = validate_system_policy(policy or {})
    actions = record["improvement_actions"]
    if not actions:
        return 0.0
    closed = 0
    for action in actions:
        if action["closed_on_day"] is None:
            continue
        if rules["require_effectiveness_verification"] and not action["effectiveness_verified"]:
            continue
        closed += 1
    return closed / float(len(actions))


def management_review_is_current(system, policy=None):
    """Return True when the management review sits inside its interval."""
    record = _as_system(system)
    rules = validate_system_policy(policy or {})
    last = record["last_management_review_day"]
    if last is None:
        return False
    return record["as_of_day"] - last <= rules["management_review_interval_days"]


def assess_management_system(case):
    """Run the full clause 5.1 management-system assessment.

    case keys: system (the management-system record) and optional policy.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    if "system" not in case:
        raise ValueError("case missing required key 'system'")
    rules = validate_system_policy(case.get("policy") or {})
    record = validate_system(case["system"])

    gaps = scope_gaps(record)
    overreach = scope_overreach(record)
    coverage = process_coverage(record)
    uncovered = uncovered_services(record)
    unapproved = unapproved_processes_in_use(record)
    stale_processes = processes_past_review(record, rules)
    closure = improvement_closure(record, rules)
    open_actions = [a["action_id"] for a in open_improvement_actions(record)]
    unverified = unverified_closures(record)
    review_current = management_review_is_current(record, rules)

    findings = []
    advisories = []

    if not record["established"]:
        verdict = SYSTEM_ABSENT
        findings.append("no quality and safety management system has been established")
    elif gaps:
        verdict = SCOPE_INCOMPLETE
        findings.append(
            "the declared scope does not name %d offered service(s): %s"
            % (len(gaps), ", ".join(gaps))
        )
    elif unapproved:
        verdict = PROCESS_APPROVAL_BROKEN
        findings.append(
            "%d process(es) cover a scoped service without an approval: %s"
            % (len(unapproved), ", ".join(unapproved))
        )
    elif not at_least(coverage, rules["min_process_coverage"]):
        verdict = PROCESS_COVERAGE_INSUFFICIENT
        findings.append(
            "documented-process coverage %.3f is under the required %.3f; uncovered: %s"
            % (coverage, rules["min_process_coverage"], ", ".join(uncovered) or "none")
        )
    elif not at_least(closure, rules["min_improvement_closure"]):
        verdict = IMPROVEMENT_LOOP_STALLED
        findings.append(
            "continual-improvement closure %.3f is under the required %.3f with %d action(s) open"
            % (closure, rules["min_improvement_closure"], len(open_actions))
        )
    elif not review_current:
        verdict = MANAGEMENT_REVIEW_STALE
        findings.append(
            "the management review is older than the %d day interval the centre declared"
            % rules["management_review_interval_days"]
        )
    else:
        verdict = SYSTEM_ESTABLISHED

    if overreach:
        advisories.append(
            "the declared scope names %d service(s) the centre does not offer: %s"
            % (len(overreach), ", ".join(overreach))
        )
    if stale_processes:
        advisories.append(
            "%d approved process(es) are past their review age: %s"
            % (len(stale_processes), ", ".join(stale_processes))
        )
    if unverified:
        advisories.append(
            "%d closed improvement action(s) never had their effectiveness verified: %s"
            % (len(unverified), ", ".join(unverified))
        )

    return {
        "verdict": verdict,
        "established": record["established"],
        "scope_gaps": gaps,
        "scope_overreach": overreach,
        "process_coverage": coverage,
        "uncovered_services": uncovered,
        "unapproved_processes": unapproved,
        "processes_past_review": stale_processes,
        "improvement_closure": closure,
        "open_actions": open_actions,
        "unverified_closures": unverified,
        "management_review_current": review_current,
        "findings": findings,
        "advisories": advisories,
        "policy": rules,
    }
