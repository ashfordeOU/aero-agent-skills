#!/usr/bin/env python3
"""Generation and update of the multipactor verification plan.

Anchor: ECSS-E-ST-20-01C clause 4.2.1 (the multipactor verification plan is
produced no later than the equipment qualification review and is kept
updated as the design and verification baseline evolves). Paraphrased into
an implementable procedure; no verbatim standard text.

Stdlib only, offline, deterministic.

Procedure implemented here:

1. resolve a named project review to its position in the milestone
   sequence, so "issued no later than the equipment qualification review"
   becomes a comparable index rather than a string;
2. evaluate the baseline issue of the plan against that due milestone and
   report the slip in reviews when it is late;
3. evaluate the release state of the plan: a plan that reached its due
   milestone still in draft has not been issued, whatever its date;
4. validate the revision history -- unique identifiers, non-decreasing
   dates, a single latest revision;
5. categorize every configuration change event as one that forces a plan
   update or one that does not, with the reason recorded;
6. measure how long each update-forcing event has stayed outside the plan,
   against the agreed response window, and mark the overdue ones;
7. trace update-forcing events into the plan change log and take the
   traceability fraction;
8. aggregate into a plan-level verdict.

The milestone sequence, the response window and the event catalogue below
are project-replaceable defaults expressing the clause intent, not a
reproduction of any table of the standard.
"""

import math
from datetime import date

# A traceability fraction landing exactly on the required minimum is
# compliant; the comparison absorbs floating-point representation error
# instead of moving the engineering requirement.
TRACE_REL_TOL = 1e-9
TRACE_ABS_TOL = 1e-12

# Ordered project reviews. Position, not name, decides "no later than".
MILESTONE_SEQUENCE = ("srr", "pdr", "cdr", "eqr", "trr", "qr", "ar", "frr")

MILESTONE_ALIASES = {
    "srr": "srr",
    "system-requirements-review": "srr",
    "pdr": "pdr",
    "preliminary-design-review": "pdr",
    "cdr": "cdr",
    "critical-design-review": "cdr",
    "eqr": "eqr",
    "equipment-qualification-review": "eqr",
    "trr": "trr",
    "test-readiness-review": "trr",
    "qr": "qr",
    "qualification-review": "qr",
    "ar": "ar",
    "acceptance-review": "ar",
    "frr": "frr",
    "flight-readiness-review": "frr",
}

# Clause 4.2.1 anchor: the baseline plan is due by the equipment
# qualification review.
BASELINE_ISSUE_MILESTONE = "eqr"

# Days allowed between a plan-forcing change event and the plan revision
# that absorbs it.
DEFAULT_RESPONSE_WINDOW_DAYS = 30

# Every plan-forcing event has to be traced; the minimum is configurable so
# a project can run a graded review, never so it can waive the rule quietly.
DEFAULT_MIN_TRACEABILITY = 1.0

PLAN_STATES = ("draft", "under-review", "approved", "superseded")
RELEASED_STATES = ("approved",)

# kind -> (forces a plan update, reason)
CHANGE_EVENT_KINDS = {
    "rf-power-increase": (
        True,
        "raises the operating level every multipactor margin was derived at",
    ),
    "gap-geometry-change": (
        True,
        "moves the frequency-gap-product of at least one critical gap",
    ),
    "electrode-material-change": (
        True,
        "changes the secondary-electron-yield of a critical surface",
    ),
    "venting-path-change": (
        True,
        "changes the pressure history the discharge risk is assessed against",
    ),
    "multipactor-test-failure": (
        True,
        "invalidates the verification route recorded for the item",
    ),
    "analysis-margin-erosion": (
        True,
        "drops a recorded margin toward the required threshold",
    ),
    "susceptibility-model-revision": (
        True,
        "changes the threshold the analysis was closed against",
    ),
    "verification-method-change": (
        True,
        "replaces the agreed route for a multipactor-critical item",
    ),
    "waiver-granted": (
        True,
        "records an accepted deviation the plan has to carry",
    ),
    "unit-configuration-change": (
        True,
        "alters the item list the plan covers",
    ),
    "editorial-correction": (False, "no technical content of the plan changes"),
    "document-reformat": (False, "presentation only"),
    "contact-detail-update": (False, "administrative data only"),
    "cross-reference-renumbering": (False, "pointer maintenance only"),
}


def canonical_milestone(raw):
    """Resolve a review name or acronym to its canonical code."""
    if not isinstance(raw, str):
        raise ValueError("milestone must be a string, got %r" % (raw,))
    key = raw.strip().lower()
    if not key:
        raise ValueError("milestone must not be empty")
    if key not in MILESTONE_ALIASES:
        raise ValueError(
            "unrecognized milestone %r; known: %s"
            % (raw, ", ".join(sorted(MILESTONE_ALIASES)))
        )
    return MILESTONE_ALIASES[key]


def milestone_index(raw):
    """Position of a review in the project sequence (earlier = smaller)."""
    return MILESTONE_SEQUENCE.index(canonical_milestone(raw))


def parse_iso_date(raw):
    """Parse an ISO-8601 calendar date, refusing anything else."""
    if isinstance(raw, date):
        return raw
    if not isinstance(raw, str):
        raise ValueError("date must be an ISO-8601 string, got %r" % (raw,))
    try:
        return date.fromisoformat(raw.strip())
    except ValueError:
        raise ValueError("date %r is not a valid ISO-8601 calendar date" % (raw,))


def days_between(earlier, later):
    """Whole days from earlier to later; negative when later precedes it."""
    return (parse_iso_date(later) - parse_iso_date(earlier)).days


def evaluate_baseline_issue(issue_milestone, due_milestone=BASELINE_ISSUE_MILESTONE):
    """Compare the milestone the plan was first issued at with its due one."""
    issued_at = canonical_milestone(issue_milestone)
    due_at = canonical_milestone(due_milestone)
    slip = MILESTONE_SEQUENCE.index(issued_at) - MILESTONE_SEQUENCE.index(due_at)
    return {
        "issued_at": issued_at,
        "due_at": due_at,
        "slip_reviews": max(0, slip),
        "on_time": slip <= 0,
    }


def evaluate_release_state(state, issue_evaluation):
    """A plan still in draft at its due review has not been issued."""
    if not isinstance(state, str):
        raise ValueError("plan state must be a string, got %r" % (state,))
    key = state.strip().lower()
    if key not in PLAN_STATES:
        raise ValueError(
            "unrecognized plan state %r; known: %s" % (state, ", ".join(PLAN_STATES))
        )
    released = key in RELEASED_STATES
    findings = []
    if key == "superseded":
        findings.append("plan revision is superseded; assess the current revision")
    elif not released:
        findings.append(
            "plan is %s, not approved: the clause 4.2.1 issue is not discharged" % key
        )
    if released and not issue_evaluation["on_time"]:
        findings.append(
            "plan approved but first issued %d review(s) after the %s"
            % (issue_evaluation["slip_reviews"], issue_evaluation["due_at"])
        )
    return {"state": key, "released": released, "findings": findings}


def categorize_change_event(kind):
    """Decide whether a configuration change forces a plan update."""
    if not isinstance(kind, str):
        raise ValueError("change event kind must be a string, got %r" % (kind,))
    key = kind.strip().lower()
    if not key:
        raise ValueError("change event kind must not be empty")
    if key not in CHANGE_EVENT_KINDS:
        raise ValueError(
            "unrecognized change event kind %r; known: %s"
            % (kind, ", ".join(sorted(CHANGE_EVENT_KINDS)))
        )
    forces_update, reason = CHANGE_EVENT_KINDS[key]
    return {
        "kind": key,
        "forces_update": forces_update,
        "category": "plan-update-forcing" if forces_update else "no-plan-impact",
        "reason": reason,
    }


def validate_revision_history(revisions):
    """Check revision identifiers are unique and dates non-decreasing."""
    if not isinstance(revisions, (list, tuple)):
        raise ValueError("revisions must be a list of records")
    if not revisions:
        raise ValueError("revision history is empty; a plan has at least one issue")
    seen = set()
    previous = None
    ordered = []
    for index, record in enumerate(revisions):
        if not isinstance(record, dict):
            raise ValueError("revision[%d] must be a mapping" % index)
        identifier = record.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("revision[%d] has no identifier" % index)
        identifier = identifier.strip()
        if identifier in seen:
            raise ValueError("duplicate revision identifier %r" % identifier)
        seen.add(identifier)
        issued = parse_iso_date(record.get("date"))
        if previous is not None and issued < previous:
            raise ValueError(
                "revision %r dated %s precedes the previous revision (%s)"
                % (identifier, issued.isoformat(), previous.isoformat())
            )
        previous = issued
        ordered.append({"id": identifier, "date": issued})
    return {
        "count": len(ordered),
        "first": ordered[0],
        "latest": ordered[-1],
        "revision_ids": [item["id"] for item in ordered],
    }


def select_pending_updates(events, plan_revision_date, assessment_date,
                           response_window_days=DEFAULT_RESPONSE_WINDOW_DAYS):
    """Update-forcing events not yet absorbed by the latest plan revision."""
    if not isinstance(events, (list, tuple)):
        raise ValueError("events must be a list of records")
    if not isinstance(response_window_days, int) or isinstance(response_window_days, bool):
        raise ValueError("response window must be an integer number of days")
    if response_window_days < 0:
        raise ValueError("response window must not be negative")
    revised_on = parse_iso_date(plan_revision_date)
    assessed_on = parse_iso_date(assessment_date)
    if assessed_on < revised_on:
        raise ValueError("assessment date precedes the plan revision date")
    pending = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError("event[%d] must be a mapping" % index)
        identifier = event.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("event[%d] has no identifier" % index)
        category = categorize_change_event(event.get("kind"))
        raised_on = parse_iso_date(event.get("date"))
        if not category["forces_update"]:
            continue
        if raised_on <= revised_on:
            continue
        days_open = (assessed_on - raised_on).days
        pending.append(
            {
                "id": identifier.strip(),
                "kind": category["kind"],
                "reason": category["reason"],
                "raised_on": raised_on.isoformat(),
                "days_open": days_open,
                "overdue": days_open > response_window_days,
            }
        )
    pending.sort(key=lambda item: (-item["days_open"], item["id"]))
    return pending


def trace_events_to_change_log(events, change_log_refs,
                               minimum_fraction=DEFAULT_MIN_TRACEABILITY):
    """Fraction of update-forcing events named in the plan change log."""
    if not isinstance(change_log_refs, (list, tuple, set, frozenset)):
        raise ValueError("change log references must be a collection")
    if not isinstance(minimum_fraction, (int, float)) or isinstance(minimum_fraction, bool):
        raise ValueError("minimum traceability fraction must be numeric")
    if not 0.0 <= float(minimum_fraction) <= 1.0:
        raise ValueError("minimum traceability fraction must lie in [0, 1]")
    logged = {str(ref).strip() for ref in change_log_refs if str(ref).strip()}
    forcing = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError("event[%d] must be a mapping" % index)
        if categorize_change_event(event.get("kind"))["forces_update"]:
            identifier = event.get("id")
            if not isinstance(identifier, str) or not identifier.strip():
                raise ValueError("event[%d] has no identifier" % index)
            forcing.append(identifier.strip())
    untraced = sorted(item for item in forcing if item not in logged)
    traced = sorted(item for item in forcing if item in logged)
    total = len(forcing)
    fraction = 1.0 if total == 0 else len(traced) / total
    minimum = float(minimum_fraction)
    meets = fraction >= minimum or math.isclose(
        fraction, minimum, rel_tol=TRACE_REL_TOL, abs_tol=TRACE_ABS_TOL
    )
    return {
        "forcing_events": total,
        "traced": traced,
        "untraced": untraced,
        "fraction": fraction,
        "minimum_fraction": minimum,
        "meets_minimum": meets,
    }


def assess_verification_plan(plan, events=(), assessment_date=None,
                             due_milestone=BASELINE_ISSUE_MILESTONE,
                             response_window_days=DEFAULT_RESPONSE_WINDOW_DAYS,
                             minimum_traceability=DEFAULT_MIN_TRACEABILITY):
    """Plan-level verdict: issued on time, released, current, traceable."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping")
    history = validate_revision_history(plan.get("revisions"))
    issue = evaluate_baseline_issue(plan.get("issue_milestone"), due_milestone)
    release = evaluate_release_state(plan.get("state"), issue)
    latest_date = history["latest"]["date"]
    assessed_on = parse_iso_date(assessment_date or latest_date)
    pending = select_pending_updates(
        events, latest_date, assessed_on, response_window_days
    )
    traceability = trace_events_to_change_log(
        events, plan.get("change_log", ()), minimum_traceability
    )
    findings = list(release["findings"])
    if not issue["on_time"] and release["released"] is False:
        findings.append(
            "baseline plan is %d review(s) late against the %s"
            % (issue["slip_reviews"], issue["due_at"])
        )
    overdue = [item for item in pending if item["overdue"]]
    for item in overdue:
        findings.append(
            "change event %s (%s) has been open %d days, beyond the %d-day window"
            % (item["id"], item["kind"], item["days_open"], response_window_days)
        )
    for item in pending:
        if not item["overdue"]:
            findings.append(
                "change event %s (%s) is not yet in the plan (open %d days)"
                % (item["id"], item["kind"], item["days_open"])
            )
    for identifier in traceability["untraced"]:
        findings.append("change event %s is absent from the plan change log" % identifier)
    if pending and not overdue:
        status = "update-due"
    elif overdue:
        status = "update-overdue"
    else:
        status = "current"
    compliant = (
        issue["on_time"]
        and release["released"]
        and status == "current"
        and traceability["meets_minimum"]
    )
    return {
        "issue": issue,
        "release": release,
        "history": history,
        "pending_updates": pending,
        "traceability": traceability,
        "status": status,
        "findings": findings,
        "compliant": compliant,
    }
