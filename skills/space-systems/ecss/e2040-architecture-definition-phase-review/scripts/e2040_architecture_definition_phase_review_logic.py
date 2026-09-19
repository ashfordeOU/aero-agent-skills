#!/usr/bin/env python3
"""Architecture definition phase review (ECSS-E-ST-20-40C clause 5.3.4).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
This gate authorises detailed design and the verification work that runs
beside it. Unlike the gate that closed the definition phase, it is driven
by exit criteria rather than by a data-item package, and it inherits
actions from the review before it.

* the phase has a fixed list of exit criteria: the architecture
  documented, the partitioning justified, the verification plan
  updated, the validation plan updated, the budgets allocated and the
  interfaces agreed. Each is met, partially met or not met, and each
  carries evidence;
* a criterion asserted met with no evidence reference is a claim, not a
  criterion. It reads identically to a satisfied one on the minutes;
* a partially met criterion is only carryable while an action actually
  references it. A partial with no action is a not-met with a softer
  word on it;
* actions carried over from the definition review do not vanish at this
  gate. One still open past its due date is the finding that says the
  previous gate's conditions were never honoured, and authorising on
  top of it stacks two phases of debt;
* satisfaction is a weighted count -- met counts one, partially met
  counts a half -- so it is a fraction that lands on a threshold only
  by arithmetic accident and the comparison absorbs that.
"""

import datetime
import math

# Exit criteria the architecture definition phase has to satisfy.
EXIT_CRITERIA = (
    "architecture-documented",
    "partitioning-justified",
    "verification-plan-updated",
    "validation-plan-updated",
    "budgets-allocated",
    "interfaces-agreed",
)

_CRITERION_ALIASES = {
    "architecture documented": "architecture-documented",
    "architecture description": "architecture-documented",
    "partitioning justified": "partitioning-justified",
    "partitioning rationale": "partitioning-justified",
    "verification plan updated": "verification-plan-updated",
    "verification plan": "verification-plan-updated",
    "validation plan updated": "validation-plan-updated",
    "validation plan": "validation-plan-updated",
    "budgets allocated": "budgets-allocated",
    "resource budgets": "budgets-allocated",
    "interfaces agreed": "interfaces-agreed",
    "interface agreements": "interfaces-agreed",
}

CRITERION_STATES = ("met", "partially-met", "not-met")

_STATE_ALIASES = {
    "met": "met",
    "satisfied": "met",
    "complete": "met",
    "partially-met": "partially-met",
    "partially met": "partially-met",
    "partial": "partially-met",
    "not-met": "not-met",
    "not met": "not-met",
    "outstanding": "not-met",
}

STATE_WEIGHT = {"met": 1.0, "partially-met": 0.5, "not-met": 0.0}

ACTION_STATES = ("closed", "open")

_ACTION_ALIASES = {
    "closed": "closed",
    "done": "closed",
    "complete": "closed",
    "open": "open",
    "in work": "open",
    "outstanding": "open",
}

REL_TOL = 1e-12
ABS_TOL = 1e-18

_REVIEW_REQUIRED_KEYS = ("criteria", "gate_date")
_REVIEW_OPTIONAL_KEYS = ("actions", "carried_actions", "satisfaction_threshold")
_CRITERION_KEYS = ("criterion", "state", "evidence")
_ACTION_KEYS = ("id", "state", "due", "against", "origin")


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _key(name, value):
    return " ".join(_text(name, value).lower().replace("_", " ").split())


def _fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def parse_date(name, value):
    """Read an ISO calendar date, refusing anything that is not one."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _text(name, value)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (name, value))


def normalize_criterion(value):
    """Fold an exit criterion name onto one of the six the phase owes."""
    key = _key("criterion", value)
    folded = key.replace(" ", "-")
    if folded in EXIT_CRITERIA:
        return folded
    if key in _CRITERION_ALIASES:
        return _CRITERION_ALIASES[key]
    raise ValueError(
        "unknown exit criterion %r; use one of %s" % (value, ", ".join(EXIT_CRITERIA))
    )


def normalize_state(value):
    """Fold a criterion state onto met, partially-met or not-met."""
    key = _key("state", value)
    if key in _STATE_ALIASES:
        return _STATE_ALIASES[key]
    raise ValueError(
        "unknown criterion state %r; use one of %s" % (value, ", ".join(CRITERION_STATES))
    )


def normalize_action_state(value):
    """Fold an action state onto closed or open."""
    key = _key("action state", value)
    if key in _ACTION_ALIASES:
        return _ACTION_ALIASES[key]
    raise ValueError(
        "unknown action state %r; use one of %s" % (value, ", ".join(ACTION_STATES))
    )


def validate_criteria(entries):
    """Check the exit criteria and return them keyed by criterion."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("criteria must be a list")
    resolved = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("criteria[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_CRITERION_KEYS))
        if unknown:
            raise ValueError("criteria[%d] has unknown keys: %s" % (index, ", ".join(unknown)))
        for key in ("criterion", "state"):
            if key not in entry:
                raise ValueError("criteria[%d] missing key: %s" % (index, key))
        name = normalize_criterion(entry["criterion"])
        if name in resolved:
            raise ValueError("duplicate exit criterion %r" % name)
        resolved[name] = {
            "criterion": name,
            "state": normalize_state(entry["state"]),
            "evidence": _text(
                "criteria[%d].evidence" % index, entry.get("evidence", ""), allow_empty=True
            ),
        }
    return resolved


def validate_actions(entries, where="actions"):
    """Check an action list and return it resolved in declared order."""
    if entries is None:
        return []
    if not isinstance(entries, (list, tuple)):
        raise ValueError("%s must be a list" % where)
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("%s[%d] must be a mapping" % (where, index))
        unknown = sorted(set(entry) - set(_ACTION_KEYS))
        if unknown:
            raise ValueError("%s[%d] has unknown keys: %s" % (where, index, ", ".join(unknown)))
        for key in ("id", "state"):
            if key not in entry:
                raise ValueError("%s[%d] missing key: %s" % (where, index, key))
        action_id = _text("%s[%d].id" % (where, index), entry["id"])
        if action_id in seen:
            raise ValueError("duplicate action id %r in %s" % (action_id, where))
        seen.add(action_id)
        due = entry.get("due")
        against = entry.get("against")
        resolved.append(
            {
                "id": action_id,
                "state": normalize_action_state(entry["state"]),
                "due": parse_date("%s[%d].due" % (where, index), due) if due else None,
                "against": normalize_criterion(against) if against else "",
                "origin": _text(
                    "%s[%d].origin" % (where, index), entry.get("origin", ""), allow_empty=True
                ),
            }
        )
    return resolved


def criteria_satisfaction(criteria):
    """Weighted satisfaction across every criterion the phase owes."""
    if not criteria:
        raise ValueError("criteria_satisfaction needs at least one criterion")
    total = 0.0
    for name in EXIT_CRITERIA:
        entry = criteria.get(name)
        if entry is not None:
            total += STATE_WEIGHT[entry["state"]]
    return total / len(EXIT_CRITERIA)


def meets_satisfaction_threshold(achieved, threshold):
    """True when satisfaction reaches the threshold, exact landings included."""
    achieved = _fraction("achieved", achieved)
    threshold = _fraction("threshold", threshold)
    return achieved > threshold or math.isclose(
        achieved, threshold, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def missing_criteria(criteria):
    """Exit criteria the phase owes and the review did not address."""
    return [name for name in EXIT_CRITERIA if name not in criteria]


def conduct_architecture_review(review):
    """Full clause 5.3.4 gate decision on one architecture definition review.

    Returns the resolved criteria, the satisfaction fraction, the findings
    and whether detailed design and verification work may start.
    """
    if not isinstance(review, dict):
        raise ValueError("review must be a mapping of criteria, actions and the gate date")
    known = set(_REVIEW_REQUIRED_KEYS) | set(_REVIEW_OPTIONAL_KEYS)
    unknown = sorted(set(review) - known)
    if unknown:
        raise ValueError("unknown review keys: %s" % ", ".join(unknown))
    missing = [key for key in _REVIEW_REQUIRED_KEYS if key not in review]
    if missing:
        raise ValueError("review missing required keys: %s" % ", ".join(missing))

    criteria = validate_criteria(review["criteria"])
    gate_date = parse_date("gate_date", review["gate_date"])
    actions = validate_actions(review.get("actions"), "actions")
    carried = validate_actions(review.get("carried_actions"), "carried_actions")

    findings = []
    blocking = False
    conditional = False

    for name in missing_criteria(criteria):
        findings.append(
            {
                "code": "exit-criterion-not-addressed",
                "criterion": name,
                "detail": "the review does not address %s, so the gate is decided over "
                "a gap" % name,
            }
        )
        blocking = True

    actioned = {a["against"] for a in actions if a["against"]}
    for name in EXIT_CRITERIA:
        entry = criteria.get(name)
        if entry is None:
            continue
        if entry["state"] == "not-met":
            findings.append(
                {
                    "code": "exit-criterion-not-met",
                    "criterion": name,
                    "detail": "%s is not met, which stops authorisation of detailed "
                    "design" % name,
                }
            )
            blocking = True
        elif entry["state"] == "partially-met":
            conditional = True
            if name not in actioned:
                findings.append(
                    {
                        "code": "partial-criterion-without-action",
                        "criterion": name,
                        "detail": "%s is partially met and no action references it, so "
                        "the partial is a not-met with a softer word on it" % name,
                    }
                )
                blocking = True
        if not entry["evidence"]:
            findings.append(
                {
                    "code": "criterion-without-evidence",
                    "criterion": name,
                    "state": entry["state"],
                    "detail": "%s is reported %s with no evidence reference behind it"
                    % (name, entry["state"]),
                }
            )
            blocking = True

    for action in actions:
        if action["state"] == "open":
            conditional = True
            if action["due"] is None:
                findings.append(
                    {
                        "code": "new-action-without-due-date",
                        "action": action["id"],
                        "detail": "action %s is raised open with no due date" % action["id"],
                    }
                )
                blocking = True
            elif action["due"] < gate_date:
                findings.append(
                    {
                        "code": "new-action-due-before-the-gate",
                        "action": action["id"],
                        "detail": "action %s is raised at this gate already past its due "
                        "date" % action["id"],
                    }
                )
                blocking = True

    for action in carried:
        if action["state"] == "open":
            if action["due"] is not None and action["due"] < gate_date:
                findings.append(
                    {
                        "code": "carried-action-overdue",
                        "action": action["id"],
                        "due": action["due"].isoformat(),
                        "detail": "action %s carried from the previous review is still "
                        "open past its due date, so authorising here stacks two phases "
                        "of debt" % action["id"],
                    }
                )
                blocking = True
            else:
                conditional = True
                findings.append(
                    {
                        "code": "carried-action-still-open",
                        "action": action["id"],
                        "detail": "action %s carried from the previous review is still "
                        "open at this gate" % action["id"],
                    }
                )

    satisfaction = criteria_satisfaction(criteria) if criteria else 0.0
    threshold = review.get("satisfaction_threshold")
    if threshold is not None:
        threshold_value = _fraction("satisfaction_threshold", threshold)
        if not meets_satisfaction_threshold(satisfaction, threshold_value):
            findings.append(
                {
                    "code": "satisfaction-threshold-missed",
                    "achieved": satisfaction,
                    "threshold": threshold_value,
                    "detail": "exit criteria reach %.1f %% against a %.1f %% threshold"
                    % (100.0 * satisfaction, 100.0 * threshold_value),
                }
            )
            blocking = True

    if blocking:
        verdict = "not-authorized"
    elif conditional or findings:
        verdict = "authorized-with-actions"
    else:
        verdict = "authorized-to-proceed"

    return {
        "criteria": criteria,
        "missing_criteria": missing_criteria(criteria),
        "criteria_satisfaction": satisfaction,
        "open_action_count": sum(1 for a in actions + carried if a["state"] == "open"),
        "findings": findings,
        "verdict": verdict,
        "detailed_design_may_start": verdict != "not-authorized",
    }
