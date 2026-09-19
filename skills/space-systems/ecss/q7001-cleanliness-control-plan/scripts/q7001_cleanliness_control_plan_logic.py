"""Contamination and cleanliness control plan: issue it, and keep it current.

Anchor: ECSS-Q-ST-70-01C, the *programme* clause -- the contamination and
cleanliness control plan a project produces and then maintains across the
lifecycle. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Check the plan carries every content area it owes, each pointing at a
   section of the issued document rather than being merely named.
2. Check it covers every lifecycle phase the project passes through, because a
   plan that stops at delivery leaves the launch campaign uncontrolled.
3. Check it is approved, and by the authority the project recognises.
4. Check it is current: its issue date must not predate the last configuration
   change it has to reflect, and its periodic review must not be overdue.
5. Check each declared update trigger names the response and the owner, so a
   trigger is an obligation and not an observation.
6. Grade the plan and report exactly what has to change before it can be
   treated as the controlling document.
"""

import datetime

__all__ = [
    "REQUIRED_CONTENT",
    "LIFECYCLE_PHASES",
    "REQUIRED_TRIGGERS",
    "validate_iso_date",
    "validate_section_map",
    "missing_content",
    "missing_phases",
    "completeness_fraction",
    "approval_findings",
    "currency_findings",
    "review_status",
    "trigger_findings",
    "assess_control_plan",
]

# Content areas a contamination and cleanliness control plan owes, grouped by
# the question each one answers. Paraphrased, project-neutral.
REQUIRED_CONTENT = (
    "scope-and-applicable-documents",
    "organisation-and-responsibilities",
    "cleanliness-levels-and-budget",
    "design-provisions",
    "materials-and-processes-control",
    "facility-and-environment-control",
    "handling-transport-and-storage",
    "cleaning-and-verification-methods",
    "monitoring-and-witness-samples",
    "non-conformance-handling",
)

# Lifecycle phases the plan has to speak to.
LIFECYCLE_PHASES = (
    "design",
    "manufacturing",
    "assembly-integration-and-test",
    "launch-campaign",
    "in-orbit-operations",
)

# Events that oblige the plan to be revisited.
REQUIRED_TRIGGERS = (
    "design-change",
    "cleanliness-level-change",
    "supplier-or-facility-change",
    "cleanliness-non-conformance",
)


def validate_iso_date(value, label):
    """Return an ISO-8601 calendar date as a date object."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO-8601 date string" % label)
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not a valid ISO-8601 date: %r" % (label, value))


def validate_section_map(sections):
    """Return the content areas that point at a real section reference."""
    if not isinstance(sections, dict):
        raise ValueError("sections must be a mapping of content area to reference")
    covered = {}
    for area, reference in sections.items():
        if not isinstance(area, str) or not area.strip():
            raise ValueError("content area name must be a non-empty string")
        if area not in REQUIRED_CONTENT:
            raise ValueError(
                "content area %r is not one of the required areas %s"
                % (area, list(REQUIRED_CONTENT))
            )
        if reference is None or (isinstance(reference, str) and not reference.strip()):
            continue
        if not isinstance(reference, str):
            raise ValueError("section reference for %r must be a string" % area)
        covered[area] = reference.strip()
    return covered


def missing_content(sections):
    """Return the required content areas the plan does not actually carry."""
    covered = validate_section_map(sections)
    return [area for area in REQUIRED_CONTENT if area not in covered]


def missing_phases(covered_phases):
    """Return the lifecycle phases the plan does not speak to."""
    if not isinstance(covered_phases, (list, tuple, set)):
        raise ValueError("covered_phases must be a sequence of phase names")
    covered = set()
    for phase in covered_phases:
        if phase not in LIFECYCLE_PHASES:
            raise ValueError(
                "phase %r is not one of %s" % (phase, list(LIFECYCLE_PHASES))
            )
        covered.add(phase)
    return [phase for phase in LIFECYCLE_PHASES if phase not in covered]


def completeness_fraction(sections, covered_phases):
    """Return the share of required content areas and phases the plan carries."""
    gaps = len(missing_content(sections)) + len(missing_phases(covered_phases))
    total = len(REQUIRED_CONTENT) + len(LIFECYCLE_PHASES)
    return (total - gaps) / total


def approval_findings(plan):
    """Return findings about the plan's approval state."""
    findings = []
    approved_by = plan.get("approved_by")
    if not isinstance(approved_by, str) or not approved_by.strip():
        findings.append("the plan carries no approval authority; it is a draft")
        return findings
    authorities = plan.get("recognised_authorities")
    if authorities is not None:
        if not isinstance(authorities, (list, tuple, set)) or not authorities:
            raise ValueError("recognised_authorities must be a non-empty sequence")
        if approved_by.strip() not in set(authorities):
            findings.append(
                "the plan is approved by %r, who is not a recognised approval "
                "authority for the project" % approved_by.strip()
            )
    if plan.get("approval_date") is None:
        findings.append("the approval carries no date")
    else:
        approval = validate_iso_date(plan["approval_date"], "approval_date")
        issue = validate_iso_date(plan["issue_date"], "issue_date")
        if approval < issue:
            findings.append(
                "the approval predates the issue it approves (%s before %s)"
                % (approval.isoformat(), issue.isoformat())
            )
    return findings


def currency_findings(plan):
    """Return findings about whether the issued plan reflects the current design."""
    issue = validate_iso_date(plan["issue_date"], "issue_date")
    findings = []
    last_change = plan.get("last_configuration_change")
    if last_change is not None:
        change = validate_iso_date(last_change, "last_configuration_change")
        if change > issue:
            findings.append(
                "the plan was issued on %s and the configuration changed on %s; "
                "it no longer reflects the hardware"
                % (issue.isoformat(), change.isoformat())
            )
    return findings


def review_status(plan, as_of):
    """Return the periodic-review state of the plan as of a given date."""
    issue = validate_iso_date(plan["issue_date"], "issue_date")
    today = validate_iso_date(as_of, "as_of")
    if today < issue:
        raise ValueError(
            "as_of %s precedes the issue date %s" % (today.isoformat(), issue.isoformat())
        )
    interval = plan.get("review_interval_days")
    if interval is None:
        return {"applicable": False, "elapsed_days": (today - issue).days,
                "overdue_days": 0, "overdue": False}
    if not isinstance(interval, int) or isinstance(interval, bool) or interval <= 0:
        raise ValueError("review_interval_days must be a positive integer")
    elapsed = (today - issue).days
    overdue_days = elapsed - interval
    return {
        "applicable": True,
        "elapsed_days": elapsed,
        "overdue_days": max(0, overdue_days),
        "overdue": overdue_days > 0,
    }


def trigger_findings(triggers):
    """Return findings about the declared plan-update triggers."""
    if triggers is None:
        triggers = {}
    if not isinstance(triggers, dict):
        raise ValueError("triggers must be a mapping of trigger to its response")
    findings = []
    for name, response in triggers.items():
        if name not in REQUIRED_TRIGGERS:
            raise ValueError(
                "trigger %r is not one of %s" % (name, list(REQUIRED_TRIGGERS))
            )
        if not isinstance(response, dict):
            raise ValueError("response for trigger %r must be a mapping" % name)
        for key in ("action", "owner"):
            value = response.get(key)
            if not isinstance(value, str) or not value.strip():
                findings.append(
                    "trigger %r declares no %s; it records an event rather than "
                    "an obligation" % (name, key)
                )
    for name in REQUIRED_TRIGGERS:
        if name not in triggers:
            findings.append("no plan-update trigger is declared for %r" % name)
    return findings


def assess_control_plan(plan, as_of=None):
    """Grade a contamination and cleanliness control plan.

    plan keys: title, issue, issue_date, sections (mapping), phases (sequence),
    approved_by, approval_date, optional recognised_authorities,
    last_configuration_change, review_interval_days, triggers.
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping")
    for key in ("title", "issue", "issue_date", "sections", "phases"):
        if key not in plan:
            raise ValueError("plan missing required key %r" % key)
    title = plan["title"]
    if not isinstance(title, str) or not title.strip():
        raise ValueError("plan title must be a non-empty string")
    issue_label = plan["issue"]
    if not isinstance(issue_label, str) or not issue_label.strip():
        raise ValueError("plan issue must be a non-empty identifier string")
    content_gaps = missing_content(plan["sections"])
    phase_gaps = missing_phases(plan["phases"])
    findings = []
    for area in content_gaps:
        findings.append("the plan carries no section for %r" % area)
    for phase in phase_gaps:
        findings.append("the plan does not speak to the %r phase" % phase)
    findings.extend(approval_findings(plan))
    findings.extend(currency_findings(plan))
    review = review_status(
        plan, as_of if as_of is not None else plan["issue_date"]
    )
    if review["overdue"]:
        findings.append(
            "the periodic review is %d days overdue" % review["overdue_days"]
        )
    findings.extend(trigger_findings(plan.get("triggers")))
    return {
        "title": title.strip(),
        "issue": issue_label.strip(),
        "content_gaps": content_gaps,
        "phase_gaps": phase_gaps,
        "completeness": completeness_fraction(plan["sections"], plan["phases"]),
        "review": review,
        "controlling": not findings,
        "findings": findings,
    }
