#!/usr/bin/env python3
"""Design and verification phase review (ECSS-E-ST-20-40C clause 5.4.6).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The clause puts a gate at the end of the design and verification phase.
Three things carry it, and the verdict is only sound when all three are
read together:

* the deliverables the review required. A deliverable has a state, not
  just a presence: a required document presented as a draft has been
  shown, not delivered;
* the actions the review raised. An open critical action holds the
  phase whatever else is clean; open major actions are weighed against
  the tolerance the board set; minor ones ride along with the verdict;
* the exit criteria the review set. Met, unmet and unassessed stay
  distinct, because folding the unassessed in with the met closes a
  phase on silence and folding them in with the unmet hides how much of
  the gate was looked at.

The verdict has three outcomes -- proceed, proceed with actions, repeat
the review -- and the middle one carries the actions the board attached
to the release.
"""

import math

RELEASED = "released"
DRAFT = "draft"
ABSENT = "absent"
DELIVERABLE_STATES = (RELEASED, DRAFT, ABSENT)
_DELIVERABLE_STATE_ALIASES = {
    "released": RELEASED,
    "issued": RELEASED,
    "approved": RELEASED,
    "delivered": RELEASED,
    "draft": DRAFT,
    "preliminary": DRAFT,
    "shown": DRAFT,
    "absent": ABSENT,
    "missing": ABSENT,
    "not presented": ABSENT,
}

CRITICAL = "critical"
MAJOR = "major"
MINOR = "minor"
ACTION_SEVERITIES = (CRITICAL, MAJOR, MINOR)
_SEVERITY_ALIASES = {
    "critical": CRITICAL,
    "blocking": CRITICAL,
    "showstopper": CRITICAL,
    "cat1": CRITICAL,
    "major": MAJOR,
    "significant": MAJOR,
    "cat2": MAJOR,
    "minor": MINOR,
    "editorial": MINOR,
    "cat3": MINOR,
}

OPEN = "open"
CLOSED = "closed"
ACTION_STATUSES = (OPEN, CLOSED)
_ACTION_STATUS_ALIASES = {
    "open": OPEN,
    "raised": OPEN,
    "outstanding": OPEN,
    "in work": OPEN,
    "closed": CLOSED,
    "done": CLOSED,
    "accepted": CLOSED,
    "withdrawn": CLOSED,
}

MET = "met"
UNMET = "unmet"
UNASSESSED = "unassessed"
CRITERION_OUTCOMES = (MET, UNMET, UNASSESSED)
_CRITERION_ALIASES = {
    "met": MET,
    "pass": MET,
    "satisfied": MET,
    "unmet": UNMET,
    "fail": UNMET,
    "not met": UNMET,
    "unassessed": UNASSESSED,
    "not assessed": UNASSESSED,
    "open": UNASSESSED,
    "tbd": UNASSESSED,
}

PROCEED = "proceed"
PROCEED_WITH_ACTIONS = "proceed-with-actions"
REPEAT_REVIEW = "repeat-review"
VERDICTS = (PROCEED, PROCEED_WITH_ACTIONS, REPEAT_REVIEW)

REL_TOL = 1e-12
ABS_TOL = 1e-18

_DELIVERABLE_KEYS = ("id", "state", "required")
_ACTION_KEYS = ("id", "severity", "status", "subject")
_CRITERION_KEYS = ("id", "outcome", "mandatory")
_REVIEW_REQUIRED_KEYS = ("deliverables", "criteria")
_REVIEW_OPTIONAL_KEYS = ("actions", "major_action_tolerance", "criteria_threshold")


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _flag(name, value, default=True):
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
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


def meets_criteria_threshold(achieved, threshold):
    """True when the criteria met reach the threshold, exact landings included."""
    achieved = _fraction("achieved", achieved)
    threshold = _fraction("threshold", threshold)
    return achieved > threshold or math.isclose(
        achieved, threshold, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def _fold(name, value, aliases, recognised):
    key = " ".join(_text(name, value).lower().replace("_", " ").split())
    if key in aliases:
        return aliases[key]
    hyphenated = key.replace(" ", "-")
    if hyphenated in aliases:
        return aliases[hyphenated]
    raise ValueError("unknown %s %r; use one of %s" % (name, value, ", ".join(recognised)))


def normalize_deliverable_state(value):
    """Fold a deliverable state spelling onto released, draft or absent."""
    return _fold("deliverable state", value, _DELIVERABLE_STATE_ALIASES, DELIVERABLE_STATES)


def normalize_severity(value):
    """Fold an action severity spelling onto critical, major or minor."""
    return _fold("action severity", value, _SEVERITY_ALIASES, ACTION_SEVERITIES)


def normalize_action_status(value):
    """Fold an action status spelling onto open or closed."""
    return _fold("action status", value, _ACTION_STATUS_ALIASES, ACTION_STATUSES)


def normalize_criterion_outcome(value):
    """Fold an exit criterion outcome onto met, unmet or unassessed."""
    return _fold("criterion outcome", value, _CRITERION_ALIASES, CRITERION_OUTCOMES)


def validate_deliverables(records):
    """Check the deliverable list and return it resolved in declared order."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("deliverables must be a list")
    resolved = []
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("deliverables[%d] must be a mapping" % index)
        unknown = sorted(set(record) - set(_DELIVERABLE_KEYS))
        if unknown:
            raise ValueError(
                "deliverables[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        if "id" not in record:
            raise ValueError("deliverables[%d] missing key: id" % index)
        item_id = _text("deliverables[%d].id" % index, record["id"])
        if item_id in seen:
            raise ValueError("duplicate deliverable id %r" % item_id)
        seen.add(item_id)
        resolved.append(
            {
                "id": item_id,
                "state": normalize_deliverable_state(record.get("state", ABSENT)),
                "required": _flag(
                    "deliverables[%d].required" % index, record.get("required"), True
                ),
            }
        )
    return resolved


def validate_actions(records):
    """Check the action list and return it resolved in declared order."""
    if records is None:
        return []
    if not isinstance(records, (list, tuple)):
        raise ValueError("actions must be a list")
    resolved = []
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("actions[%d] must be a mapping" % index)
        unknown = sorted(set(record) - set(_ACTION_KEYS))
        if unknown:
            raise ValueError(
                "actions[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "severity"):
            if key not in record:
                raise ValueError("actions[%d] missing key: %s" % (index, key))
        action_id = _text("actions[%d].id" % index, record["id"])
        if action_id in seen:
            raise ValueError("duplicate action id %r" % action_id)
        seen.add(action_id)
        resolved.append(
            {
                "id": action_id,
                "severity": normalize_severity(record["severity"]),
                "status": normalize_action_status(record.get("status", OPEN)),
                "subject": _text(
                    "actions[%d].subject" % index,
                    record.get("subject", ""),
                    allow_empty=True,
                ),
            }
        )
    return resolved


def validate_criteria(records):
    """Check the exit criteria and return them resolved in declared order."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("criteria must be a list")
    resolved = []
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("criteria[%d] must be a mapping" % index)
        unknown = sorted(set(record) - set(_CRITERION_KEYS))
        if unknown:
            raise ValueError(
                "criteria[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        if "id" not in record:
            raise ValueError("criteria[%d] missing key: id" % index)
        criterion_id = _text("criteria[%d].id" % index, record["id"])
        if criterion_id in seen:
            raise ValueError("duplicate criterion id %r" % criterion_id)
        seen.add(criterion_id)
        resolved.append(
            {
                "id": criterion_id,
                "outcome": normalize_criterion_outcome(
                    record.get("outcome", UNASSESSED)
                ),
                "mandatory": _flag(
                    "criteria[%d].mandatory" % index, record.get("mandatory"), True
                ),
            }
        )
    return resolved


def open_actions_by_severity(actions):
    """Count of open actions at each severity."""
    counts = {severity: 0 for severity in ACTION_SEVERITIES}
    for action in actions:
        if action["status"] == OPEN:
            counts[action["severity"]] += 1
    return counts


def criteria_met_fraction(criteria):
    """Fraction of exit criteria assessed as met."""
    if not criteria:
        raise ValueError("criteria_met_fraction needs at least one exit criterion")
    return sum(1 for c in criteria if c["outcome"] == MET) / len(criteria)


def unassessed_criteria(criteria):
    """Exit criterion ids nobody assessed."""
    return sorted(c["id"] for c in criteria if c["outcome"] == UNASSESSED)


def blocking_deliverables(deliverables):
    """Required deliverables not presented in a released state, as (id, state)."""
    return sorted(
        (d["id"], d["state"])
        for d in deliverables
        if d["required"] and d["state"] != RELEASED
    )


def review_verdict(deliverables, actions, criteria, major_action_tolerance=0):
    """Derive the three-way gate verdict from the three inputs together."""
    tolerance = _count("major_action_tolerance", major_action_tolerance)
    counts = open_actions_by_severity(actions)
    mandatory_short = [
        c["id"] for c in criteria if c["mandatory"] and c["outcome"] != MET
    ]
    if (
        counts[CRITICAL] > 0
        or blocking_deliverables(deliverables)
        or mandatory_short
        or counts[MAJOR] > tolerance
    ):
        return REPEAT_REVIEW
    if counts[MAJOR] > 0 or counts[MINOR] > 0:
        return PROCEED_WITH_ACTIONS
    return PROCEED


def evaluate_phase_review(review):
    """Full clause 5.4.6 assessment of one design and verification phase review.

    Returns the open-action counts, the criteria fraction, the findings and
    the verdict.
    """
    if not isinstance(review, dict):
        raise ValueError(
            "review must be a mapping of deliverables, actions and criteria"
        )
    known = set(_REVIEW_REQUIRED_KEYS) | set(_REVIEW_OPTIONAL_KEYS)
    unknown = sorted(set(review) - known)
    if unknown:
        raise ValueError("unknown review keys: %s" % ", ".join(unknown))
    absent = [key for key in _REVIEW_REQUIRED_KEYS if key not in review]
    if absent:
        raise ValueError("review missing required keys: %s" % ", ".join(absent))

    deliverables = validate_deliverables(review["deliverables"])
    if not deliverables:
        raise ValueError("review must carry at least one deliverable")
    actions = validate_actions(review.get("actions"))
    criteria = validate_criteria(review["criteria"])
    if not criteria:
        raise ValueError("review must carry at least one exit criterion")
    tolerance = _count(
        "major_action_tolerance", review.get("major_action_tolerance", 0)
    )

    findings = []
    for item_id, state in blocking_deliverables(deliverables):
        code = (
            "required-deliverable-absent"
            if state == ABSENT
            else "required-deliverable-not-released"
        )
        findings.append(
            {
                "code": code,
                "deliverable": item_id,
                "state": state,
                "detail": "required deliverable %s is %s at the gate"
                % (item_id, state),
            }
        )

    counts = open_actions_by_severity(actions)
    for action in actions:
        if action["status"] == OPEN and action["severity"] == CRITICAL:
            findings.append(
                {
                    "code": "open-critical-action",
                    "action": action["id"],
                    "detail": "critical action %s is open, so the phase cannot close"
                    % action["id"],
                }
            )
    if counts[MAJOR] > tolerance:
        findings.append(
            {
                "code": "open-major-actions-past-tolerance",
                "open_major": counts[MAJOR],
                "tolerance": tolerance,
                "detail": "%d major actions are open against a tolerance of %d"
                % (counts[MAJOR], tolerance),
            }
        )

    for criterion in criteria:
        if criterion["outcome"] == UNASSESSED:
            findings.append(
                {
                    "code": "exit-criterion-unassessed",
                    "criterion": criterion["id"],
                    "detail": "exit criterion %s was not assessed, so it is neither "
                    "met nor failed" % criterion["id"],
                }
            )
        elif criterion["outcome"] == UNMET and criterion["mandatory"]:
            findings.append(
                {
                    "code": "mandatory-exit-criterion-unmet",
                    "criterion": criterion["id"],
                    "detail": "mandatory exit criterion %s is not met"
                    % criterion["id"],
                }
            )

    met_fraction = criteria_met_fraction(criteria)
    threshold = review.get("criteria_threshold")
    if threshold is not None:
        threshold_value = _fraction("criteria_threshold", threshold)
        if not meets_criteria_threshold(met_fraction, threshold_value):
            findings.append(
                {
                    "code": "criteria-met-below-threshold",
                    "achieved": met_fraction,
                    "threshold": threshold_value,
                    "detail": "%.1f %% of the exit criteria are met against a "
                    "%.1f %% threshold"
                    % (100.0 * met_fraction, 100.0 * threshold_value),
                }
            )

    verdict = review_verdict(deliverables, actions, criteria, tolerance)
    return {
        "verdict": verdict,
        "deliverable_count": len(deliverables),
        "blocking_deliverables": blocking_deliverables(deliverables),
        "open_actions": counts,
        "unassessed_criteria": unassessed_criteria(criteria),
        "criteria_met_fraction": met_fraction,
        "findings": findings,
        "detailed_design_may_start": verdict != REPEAT_REVIEW,
    }
