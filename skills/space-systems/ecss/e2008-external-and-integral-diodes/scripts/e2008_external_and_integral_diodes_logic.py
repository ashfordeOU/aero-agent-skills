#!/usr/bin/env python3
"""Generic specification agreed for external and integral diode acceptance.

Anchor: ECSS-E-ST-20-08C clause 9.4.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The generic specification used for acceptance testing of external and
integral diodes is settled between customer and supplier beforehand.
"Beforehand" is the whole clause: a specification agreed after the first
acceptance activity has run does not govern that activity, it describes
it, and the difference is the difference between acceptance and a
write-up.

Three things have to be true at once, and they fail independently:

    two-sided    both parties recorded agreement; a specification only
                 the supplier signed is a supplier position
    per issue    agreement is given against one issue, so a signature
                 carried across a re-issue is a silent baseline change
    in force     the binding date is the LATER of the two party dates,
                 and it is compared against the EARLIEST acceptance
                 activity, not the latest

Both diode kinds are named here, and the integral one is the one that
gets dropped -- a diode integral to the cell assembly reads as covered
by the assembly's own specification, and the clause puts it here
instead. An activity whose kind the specification does not cover is a
coverage gap even when the activity itself is faultless, because
nothing declares what its pass criteria were.

The party set, the agreed-share minimum and the late-baseline policy
below are declared project policy, not physical constants; a project
may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime
import math

DIODE_KINDS = ("external", "integral")
PARTIES = ("customer", "supplier")

BASELINE_AGREED = "diode-acceptance-baseline-agreed"
BASELINE_NOT_AGREED = "diode-acceptance-baseline-not-agreed"

DEFAULT_BASELINE_POLICY = {
    "min_agreed_share": 1.0,
    "carry_late_agreement": False,
    "require_both_kinds_covered": True,
}

_DATE_FORMAT = "%Y-%m-%d"
_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_sequence(name, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (name, value))
    return list(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_issue(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer issue number, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be one or greater, got %r" % (name, value))
    return value


def _require_share(name, value):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if not 0.0 < value <= 1.0:
        raise ValueError(
            "%s must sit above zero and at or below one, got %r" % (name, value)
        )
    return float(value)


def parse_date(name, value):
    """Parse one calendar date.

    Dates are compared as parsed dates, never as raw strings. A mixed
    set of formats sorted as text can put a baseline settled a year late
    ahead of the work it was meant to govern.
    """
    label = _require_label(name, value)
    try:
        return datetime.datetime.strptime(label, _DATE_FORMAT).date()
    except ValueError:
        raise ValueError(
            "%s must be a calendar date as YYYY-MM-DD, got %r" % (name, value)
        )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    The agreed share is a quotient of two party counts, so a baseline
    that meets the declared minimum exactly can evaluate a unit in the
    last place below it. The comparison absorbs that; the declared
    minimum itself is untouched.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def resolve_policy(policy=None):
    """Merge project policy over the declared defaults and validate it."""
    settings = dict(DEFAULT_BASELINE_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    _require_share("min_agreed_share", settings.get("min_agreed_share"))
    _require_flag("carry_late_agreement", settings.get("carry_late_agreement"))
    _require_flag(
        "require_both_kinds_covered", settings.get("require_both_kinds_covered")
    )
    return settings


def validate_specification(specification):
    """Check the generic specification is identified by issue and coverage."""
    _require_mapping("specification", specification)
    spec_id = _require_label("spec_id", specification.get("spec_id"))
    issue = _require_issue("issue", specification.get("issue"))
    covers = _require_sequence("covers", specification.get("covers") or [])
    cleaned = []
    for kind in covers:
        name = _require_choice("covered diode kind", kind, DIODE_KINDS)
        if name in cleaned:
            raise ValueError("diode kind %r is listed twice in covers" % name)
        cleaned.append(name)
    if not cleaned:
        raise ValueError("specification must cover at least one diode kind")
    return {"spec_id": spec_id, "issue": issue, "covers": cleaned}


def validate_agreement(agreement):
    """Check one party agreement record names a party, an issue and a date."""
    _require_mapping("agreement", agreement)
    party = _require_choice("party", agreement.get("party"), PARTIES)
    issue = _require_issue("agreed_issue", agreement.get("agreed_issue"))
    agreed_on = parse_date("agreed_on", agreement.get("agreed_on"))
    return {"party": party, "agreed_issue": issue, "agreed_on": agreed_on}


def validate_activity(activity):
    """Check one acceptance activity names a kind, a start date and an issue."""
    _require_mapping("activity", activity)
    activity_id = _require_label("activity_id", activity.get("activity_id"))
    kind = _require_choice("diode_kind", activity.get("diode_kind"), DIODE_KINDS)
    started_on = parse_date("started_on", activity.get("started_on"))
    cited_issue = _require_issue("cited_issue", activity.get("cited_issue"))
    return {
        "activity_id": activity_id,
        "diode_kind": kind,
        "started_on": started_on,
        "cited_issue": cited_issue,
    }


def grade_agreement(specification, agreements, policy=None):
    """Grade the two-sided, per-issue agreement and find the binding date."""
    settings = resolve_policy(policy)
    spec = validate_specification(specification)
    records = [validate_agreement(a) for a in _require_sequence("agreements", agreements)]

    seen = set()
    for record in records:
        if record["party"] in seen:
            raise ValueError(
                "party %r appears twice in the agreement record" % record["party"]
            )
        seen.add(record["party"])

    on_issue = [r for r in records if r["agreed_issue"] == spec["issue"]]
    stale = [r for r in records if r["agreed_issue"] != spec["issue"]]
    agreed_parties = sorted(r["party"] for r in on_issue)
    outstanding = [p for p in PARTIES if p not in agreed_parties]
    agreed_share = len(agreed_parties) / len(PARTIES)
    meets_share = _at_least(agreed_share, settings["min_agreed_share"])

    binding_date = max((r["agreed_on"] for r in on_issue), default=None)

    findings = []
    for party in outstanding:
        findings.append(
            "the %s has not recorded agreement to issue %d of %s; a one-sided "
            "record is a party position, not an agreement"
            % (party, spec["issue"], spec["spec_id"])
        )
    for record in stale:
        findings.append(
            "the %s agreed issue %d, not the current issue %d; a signature "
            "carried across a re-issue is a silent baseline change"
            % (record["party"], record["agreed_issue"], spec["issue"])
        )
    return {
        "spec_id": spec["spec_id"],
        "issue": spec["issue"],
        "agreed_parties": agreed_parties,
        "outstanding_parties": outstanding,
        "stale_agreements": [r["party"] for r in stale],
        "agreed_share": agreed_share,
        "meets_agreed_share": meets_share,
        "binding_date": binding_date,
        "findings": findings,
    }


def grade_timing(binding_date, activities):
    """Compare the binding date against the EARLIEST acceptance activity."""
    records = [validate_activity(a) for a in _require_sequence("activities", activities)]
    if not records:
        raise ValueError("activities must hold at least one acceptance activity")
    earliest = min(records, key=lambda r: (r["started_on"], r["activity_id"]))

    if binding_date is None:
        return {
            "earliest_activity": earliest["activity_id"],
            "earliest_start": earliest["started_on"].isoformat(),
            "binding_date": None,
            "lead_days": None,
            "settled_beforehand": False,
            "findings": [
                "no binding agreement date exists, so nothing can be shown to "
                "predate acceptance activity %s" % earliest["activity_id"]
            ],
        }

    lead_days = (earliest["started_on"] - binding_date).days
    settled = lead_days > 0
    findings = []
    if not settled:
        findings.append(
            "the agreement became binding on %s, %d day(s) after acceptance "
            "activity %s started; a specification settled after the work does "
            "not govern it"
            % (binding_date.isoformat(), -lead_days, earliest["activity_id"])
        )
    return {
        "earliest_activity": earliest["activity_id"],
        "earliest_start": earliest["started_on"].isoformat(),
        "binding_date": binding_date.isoformat(),
        "lead_days": lead_days,
        "settled_beforehand": settled,
        "findings": findings,
    }


def grade_coverage(specification, activities, policy=None):
    """Report diode kinds the specification does not cover."""
    settings = resolve_policy(policy)
    spec = validate_specification(specification)
    records = [validate_activity(a) for a in _require_sequence("activities", activities)]
    covered = set(spec["covers"])

    uncovered_kinds = [k for k in DIODE_KINDS if k not in covered]
    uncovered_activities = [
        r["activity_id"] for r in records if r["diode_kind"] not in covered
    ]
    findings = []
    if settings["require_both_kinds_covered"]:
        for kind in uncovered_kinds:
            findings.append(
                "%s does not cover %s diodes, and the clause names both kinds"
                % (spec["spec_id"], kind)
            )
    for activity_id in uncovered_activities:
        findings.append(
            "acceptance activity %s ran on a diode kind %s does not cover, so "
            "nothing declares what its pass criteria were"
            % (activity_id, spec["spec_id"])
        )
    return {
        "covers": spec["covers"],
        "uncovered_kinds": uncovered_kinds,
        "uncovered_activities": uncovered_activities,
        "findings": findings,
    }


def grade_citations(specification, activities):
    """Report every activity citing an issue other than the current one."""
    spec = validate_specification(specification)
    records = [validate_activity(a) for a in _require_sequence("activities", activities)]
    superseded = [
        r["activity_id"] for r in records if r["cited_issue"] != spec["issue"]
    ]
    findings = [
        "acceptance activity %s cites an issue that is not the current issue "
        "%d; the remedy is a re-run or a justification, not a corrected date"
        % (activity_id, spec["issue"])
        for activity_id in superseded
    ]
    return {
        "issue": spec["issue"],
        "superseded_activities": superseded,
        "current_activities": [
            r["activity_id"] for r in records if r["cited_issue"] == spec["issue"]
        ],
        "findings": findings,
    }


def assess_diode_specification_baseline(case):
    """Full clause 9.4.4 roll-up over one diode acceptance baseline."""
    _require_mapping("case", case)
    baseline_id = _require_label("baseline_id", case.get("baseline_id"))
    specification = case.get("specification")
    agreements = case.get("agreements")
    activities = case.get("activities")
    settings = resolve_policy(case.get("policy"))

    agreement = grade_agreement(specification, agreements, settings)
    timing = grade_timing(agreement["binding_date"], activities)
    coverage = grade_coverage(specification, activities, settings)
    citations = grade_citations(specification, activities)

    findings = list(agreement["findings"])
    findings.extend(timing["findings"])
    findings.extend(coverage["findings"])
    findings.extend(citations["findings"])

    blocked = not agreement["meets_agreed_share"]
    if agreement["outstanding_parties"]:
        blocked = True
    if not timing["settled_beforehand"] and not settings["carry_late_agreement"]:
        blocked = True
    if coverage["uncovered_activities"]:
        blocked = True
    if settings["require_both_kinds_covered"] and coverage["uncovered_kinds"]:
        blocked = True
    if citations["superseded_activities"]:
        blocked = True

    return {
        "baseline_id": baseline_id,
        "agreement": agreement,
        "timing": timing,
        "coverage": coverage,
        "citations": citations,
        "verdict": BASELINE_NOT_AGREED if blocked else BASELINE_AGREED,
        "findings": findings,
    }
