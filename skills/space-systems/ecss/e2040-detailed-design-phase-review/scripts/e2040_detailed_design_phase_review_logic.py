#!/usr/bin/env python3
"""Detailed design phase review (ECSS-E-ST-20-40C 5.5.6).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The detailed design phase review is the gate that closes detailed design
before any layout activity starts on the device. It is not a meeting with
an outcome written afterwards: the outcome follows from three things that
can each be resolved before anyone argues about the verdict.

* The deliverables the review was called on. A deliverable that was never
  issued has not been reviewed, however thoroughly it was discussed, and a
  deliverable issued as a draft has been reviewed against something the
  project has not committed to.
* The review item discrepancies raised against those deliverables. Each
  one carries a severity and a disposition, and it is the pairing that
  matters: a major discrepancy left open blocks the gate no matter how
  many minor ones were closed around it.
* The actions carried out of the review. An action with no owner cannot be
  worked, and an action due before the next gate that is still open turns
  a conditional pass into a fail at that gate rather than at this one.

The verdict is therefore one of three: the gate passes, it passes with
actions carried forward, or it fails. A closure fraction landing exactly
on its threshold is a pass, so the comparison absorbs representation error
instead of failing a review that is exactly on target.
"""

import math

# Severity of a review item discrepancy.
SEVERITIES = ("major", "minor", "comment")

# How a discrepancy was dispositioned at the review.
DISPOSITIONS = ("closed", "accepted-with-action", "open", "rejected")

# States a deliverable can be in when the review is called.
DELIVERABLE_STATES = ("issued", "draft", "not-issued")

# Verdicts the gate can reach.
VERDICTS = ("pass", "pass-with-actions", "fail")

REL_TOL = 1e-12
ABS_TOL = 1e-18

_DELIVERABLE_KEYS = ("id", "title", "state", "required")
_RID_KEYS = ("id", "severity", "disposition", "deliverable", "action")
_ACTION_KEYS = ("id", "owner", "due", "state")
_ACTION_STATES = ("open", "closed")


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def normalize_severity(value):
    """Fold a discrepancy severity onto one of the recognised severities."""
    key = " ".join(_text("severity", value).lower().split())
    aliases = {
        "major": "major",
        "critical": "major",
        "1": "major",
        "minor": "minor",
        "2": "minor",
        "comment": "comment",
        "editorial": "comment",
        "3": "comment",
    }
    if key in aliases:
        return aliases[key]
    raise ValueError(
        "unknown severity %r; use one of %s" % (value, ", ".join(SEVERITIES))
    )


def normalize_disposition(value):
    """Fold a discrepancy disposition onto one of the recognised ones."""
    key = " ".join(_text("disposition", value).lower().replace("_", " ").split())
    key = key.replace(" ", "-")
    aliases = {
        "closed": "closed",
        "agreed-closed": "closed",
        "accepted-with-action": "accepted-with-action",
        "accepted": "accepted-with-action",
        "action": "accepted-with-action",
        "open": "open",
        "unresolved": "open",
        "rejected": "rejected",
        "not-accepted": "rejected",
    }
    if key in aliases:
        return aliases[key]
    raise ValueError(
        "unknown disposition %r; use one of %s" % (value, ", ".join(DISPOSITIONS))
    )


def normalize_deliverable_state(value):
    """Fold a deliverable state onto one of the recognised states."""
    key = " ".join(_text("state", value).lower().replace("_", " ").split())
    key = key.replace(" ", "-")
    aliases = {
        "issued": "issued",
        "released": "issued",
        "approved": "issued",
        "draft": "draft",
        "preliminary": "draft",
        "not-issued": "not-issued",
        "missing": "not-issued",
        "absent": "not-issued",
    }
    if key in aliases:
        return aliases[key]
    raise ValueError(
        "unknown deliverable state %r; use one of %s"
        % (value, ", ".join(DELIVERABLE_STATES))
    )


def validate_deliverables(entries):
    """Check the review deliverables and return them resolved in order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("deliverables must be a list")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("deliverables[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_DELIVERABLE_KEYS))
        if unknown:
            raise ValueError(
                "deliverables[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        if "id" not in entry:
            raise ValueError("deliverables[%d] missing key: id" % index)
        item_id = _text("deliverables[%d].id" % index, entry["id"])
        if item_id in seen:
            raise ValueError("duplicate deliverable id %r" % item_id)
        seen.add(item_id)
        required = entry.get("required", True)
        if not isinstance(required, bool):
            raise ValueError("deliverables[%d].required must be true or false" % index)
        resolved.append(
            {
                "id": item_id,
                "title": _text(
                    "deliverables[%d].title" % index,
                    entry.get("title", ""),
                    allow_empty=True,
                ),
                "state": normalize_deliverable_state(entry.get("state", "issued")),
                "required": required,
            }
        )
    return resolved


def validate_actions(entries):
    """Check the actions carried out of the review, keyed by identifier."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("actions must be a list")
    resolved = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("actions[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_ACTION_KEYS))
        if unknown:
            raise ValueError(
                "actions[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        if "id" not in entry:
            raise ValueError("actions[%d] missing key: id" % index)
        action_id = _text("actions[%d].id" % index, entry["id"])
        if action_id in resolved:
            raise ValueError("duplicate action id %r" % action_id)
        state = _text("actions[%d].state" % index, entry.get("state", "open")).lower()
        if state not in _ACTION_STATES:
            raise ValueError(
                "unknown action state %r; use one of %s"
                % (state, ", ".join(_ACTION_STATES))
            )
        resolved[action_id] = {
            "id": action_id,
            "owner": _text(
                "actions[%d].owner" % index, entry.get("owner", ""), allow_empty=True
            ),
            "due": _text(
                "actions[%d].due" % index, entry.get("due", ""), allow_empty=True
            ),
            "state": state,
        }
    return resolved


def validate_discrepancies(entries):
    """Check the review item discrepancies and return them resolved."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("discrepancies must be a list")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("discrepancies[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_RID_KEYS))
        if unknown:
            raise ValueError(
                "discrepancies[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "severity", "disposition"):
            if key not in entry:
                raise ValueError("discrepancies[%d] missing key: %s" % (index, key))
        rid = _text("discrepancies[%d].id" % index, entry["id"])
        if rid in seen:
            raise ValueError("duplicate discrepancy id %r" % rid)
        seen.add(rid)
        resolved.append(
            {
                "id": rid,
                "severity": normalize_severity(entry["severity"]),
                "disposition": normalize_disposition(entry["disposition"]),
                "deliverable": _text(
                    "discrepancies[%d].deliverable" % index,
                    entry.get("deliverable", ""),
                    allow_empty=True,
                ),
                "action": _text(
                    "discrepancies[%d].action" % index,
                    entry.get("action", ""),
                    allow_empty=True,
                ),
            }
        )
    return resolved


def is_resolved(discrepancy):
    """True when a discrepancy no longer needs the gate to wait for it."""
    return discrepancy["disposition"] in ("closed", "rejected")


def closure_fraction(discrepancies):
    """Fraction of raised discrepancies that no longer hold the gate."""
    if not discrepancies:
        raise ValueError("closure fraction needs at least one discrepancy")
    resolved = sum(1 for d in discrepancies if is_resolved(d))
    return resolved / len(discrepancies)


def blocking_discrepancies(discrepancies):
    """Identifiers of the major discrepancies that are not resolved."""
    return sorted(
        d["id"]
        for d in discrepancies
        if d["severity"] == "major" and not is_resolved(d)
    )


def meets_threshold(achieved, threshold):
    """True when a fraction reaches its threshold, exact landings included."""
    achieved = _fraction("achieved", achieved)
    threshold = _fraction("threshold", threshold)
    return achieved > threshold or math.isclose(
        achieved, threshold, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def evaluate_phase_review(review, closure_threshold=0.9):
    """Full 5.5.6 assessment of one detailed design phase review.

    Returns the closure figures, the findings and the gate verdict.
    """
    if not isinstance(review, dict):
        raise ValueError(
            "review must be a mapping of deliverables, discrepancies and actions"
        )
    known = {"deliverables", "discrepancies", "actions"}
    unknown = sorted(set(review) - known)
    if unknown:
        raise ValueError("unknown review keys: %s" % ", ".join(unknown))
    for key in ("deliverables", "discrepancies"):
        if key not in review:
            raise ValueError("review missing required key: %s" % key)

    deliverables = validate_deliverables(review["deliverables"])
    if not deliverables:
        raise ValueError("the review must be called on at least one deliverable")
    discrepancies = validate_discrepancies(review["discrepancies"])
    actions = validate_actions(review.get("actions", []))
    closure_threshold = _fraction("closure_threshold", closure_threshold)

    findings = []
    blocked = False

    known_ids = {d["id"] for d in deliverables}
    for deliverable in deliverables:
        if not deliverable["required"]:
            continue
        if deliverable["state"] == "not-issued":
            blocked = True
            findings.append(
                {
                    "code": "required-deliverable-not-issued",
                    "deliverable": deliverable["id"],
                    "detail": "%s was not issued, so the review had nothing to "
                    "assess for it" % deliverable["id"],
                }
            )
        elif deliverable["state"] == "draft":
            blocked = True
            findings.append(
                {
                    "code": "required-deliverable-still-draft",
                    "deliverable": deliverable["id"],
                    "detail": "%s was reviewed as a draft, so the gate would close "
                    "on something uncommitted" % deliverable["id"],
                }
            )

    for discrepancy in discrepancies:
        if discrepancy["deliverable"] and discrepancy["deliverable"] not in known_ids:
            findings.append(
                {
                    "code": "discrepancy-against-unknown-deliverable",
                    "discrepancy": discrepancy["id"],
                    "detail": "%s is raised against %r, which the review was not "
                    "called on"
                    % (discrepancy["id"], discrepancy["deliverable"]),
                }
            )
        if discrepancy["disposition"] == "accepted-with-action":
            if not discrepancy["action"]:
                findings.append(
                    {
                        "code": "accepted-discrepancy-without-action",
                        "discrepancy": discrepancy["id"],
                        "detail": "%s was accepted with an action and names none"
                        % discrepancy["id"],
                    }
                )
            elif discrepancy["action"] not in actions:
                findings.append(
                    {
                        "code": "discrepancy-action-not-registered",
                        "discrepancy": discrepancy["id"],
                        "action": discrepancy["action"],
                        "detail": "%s names action %r, which the review did not "
                        "register" % (discrepancy["id"], discrepancy["action"]),
                    }
                )

    for blocker in blocking_discrepancies(discrepancies):
        blocked = True
        findings.append(
            {
                "code": "major-discrepancy-unresolved",
                "discrepancy": blocker,
                "detail": "major discrepancy %s is neither closed nor rejected, so "
                "the gate cannot close" % blocker,
            }
        )

    for action_id in sorted(actions):
        action = actions[action_id]
        if not action["owner"]:
            findings.append(
                {
                    "code": "action-without-owner",
                    "action": action_id,
                    "detail": "action %s has no owner and cannot be worked"
                    % action_id,
                }
            )
        if not action["due"]:
            findings.append(
                {
                    "code": "action-without-due-milestone",
                    "action": action_id,
                    "detail": "action %s has no due milestone, so it cannot be "
                    "carried to a gate" % action_id,
                }
            )

    closure = closure_fraction(discrepancies) if discrepancies else 1.0
    if discrepancies and not meets_threshold(closure, closure_threshold):
        blocked = True
        findings.append(
            {
                "code": "closure-threshold-missed",
                "achieved": closure,
                "threshold": closure_threshold,
                "detail": "%.1f %% of the discrepancies are resolved against a "
                "%.1f %% threshold" % (100.0 * closure, 100.0 * closure_threshold),
            }
        )

    carried = sorted(a for a in actions if actions[a]["state"] == "open")
    if blocked:
        verdict = "fail"
    elif carried or any(
        d["disposition"] == "accepted-with-action" for d in discrepancies
    ):
        verdict = "pass-with-actions"
    else:
        verdict = "pass"

    return {
        "deliverable_count": len(deliverables),
        "discrepancy_count": len(discrepancies),
        "closure_fraction": closure,
        "blocking_discrepancies": blocking_discrepancies(discrepancies),
        "carried_actions": carried,
        "findings": findings,
        "verdict": verdict,
        "layout_may_start": verdict in ("pass", "pass-with-actions"),
    }
