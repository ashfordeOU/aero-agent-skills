#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.4.1 -- supplier electromagnetic compatibility
verification plan and verification report.

Deterministic, offline, stdlib only. The module implements the paired
document check the clause anchors: the plan is the forward-looking
document that declares what will be verified, how and when; the report
is the backward-looking document that records what was executed and how
each activity was dispositioned. The two are checked as a pair --
mandatory content per document, activity traceability in both
directions, issue-date ordering around the campaign, closure of a
non-compliant activity, and the share of the requirement set the closed
activities actually cover.

No verbatim standard text is reproduced; the clause is the anchor only.
"""

import datetime
import math

# Mandatory content of each document. The two sets are deliberately
# disjoint: the plan owes approach and criteria, the report owes
# as-run evidence and disposition.
PLAN_SECTIONS = (
    "verification-approach",
    "verification-matrix",
    "activity-schedule",
    "facility-and-setup",
    "pass-fail-criteria",
    "deviation-handling",
)
REPORT_SECTIONS = (
    "as-run-configuration",
    "measured-results",
    "deviation-record",
    "disposition-and-conclusion",
    "evidence-index",
)

# Admissible verification methods for an activity in the plan.
METHODS = (
    "measurement",
    "analysis",
    "similarity",
    "inspection",
    "review-of-design",
)

# Admissible dispositions for a report entry.
RESULTS = (
    "compliant",
    "non-compliant",
    "compliant-with-deviation",
)

# The declared requirement-set shares are decimal percentages that are
# summed; a sum of such values carries representation error, so the
# coverage comparison absorbs it at this tolerance. The engineering
# target itself is never relaxed.
SHARE_TOLERANCE = 1e-9


def _parse_day(value, label):
    """Return an ISO calendar date, rejecting anything unparseable."""
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string (got %r)" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not a valid ISO date: %r" % (label, value))


def _positive_share(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number (got %r)" % (label, value))
    share = float(value)
    if math.isnan(share) or math.isinf(share):
        raise ValueError("%s must be finite (got %r)" % (label, value))
    if share < 0.0 or share > 100.0:
        raise ValueError("%s must lie in 0..100 percent (got %r)" % (label, value))
    return share


def normalise_plan_activity(record):
    """Canonicalise one planned verification activity from the plan."""
    if not isinstance(record, dict):
        raise ValueError("plan activity record must be a mapping (got %r)" % (record,))
    ident = str(record.get("id", "")).strip()
    if not ident:
        raise ValueError("plan activity needs a non-empty id")
    requirement = str(record.get("requirement", "")).strip()
    if not requirement:
        raise ValueError("plan activity %r names no requirement" % ident)
    method = record.get("method")
    if method not in METHODS:
        raise ValueError(
            "plan activity %r has unknown method %r (expected one of %s)"
            % (ident, method, ", ".join(METHODS))
        )
    share = _positive_share(record.get("share_percent"), "share_percent of %r" % ident)
    planned_day = _parse_day(record.get("planned_day"), "planned_day of %r" % ident)
    return {
        "id": ident,
        "requirement": requirement,
        "method": method,
        "share_percent": share,
        "planned_day": planned_day,
    }


def build_activity_index(records):
    """Index the planned activities by id, rejecting a repeated id."""
    if records is None:
        raise ValueError("verification plan declares no activity list")
    index = {}
    for record in records:
        activity = normalise_plan_activity(record)
        if activity["id"] in index:
            raise ValueError("duplicate plan activity id %r" % activity["id"])
        index[activity["id"]] = activity
    if not index:
        raise ValueError("verification plan declares no activity")
    return index


def normalise_report_entry(record):
    """Canonicalise one as-run entry from the verification report."""
    if not isinstance(record, dict):
        raise ValueError("report entry record must be a mapping (got %r)" % (record,))
    ident = str(record.get("id", "")).strip()
    if not ident:
        raise ValueError("report entry needs a non-empty id")
    activity = str(record.get("activity", "")).strip()
    if not activity:
        raise ValueError("report entry %r names no plan activity" % ident)
    result = record.get("result")
    if result not in RESULTS:
        raise ValueError(
            "report entry %r has unknown result %r (expected one of %s)"
            % (ident, result, ", ".join(RESULTS))
        )
    executed_day = _parse_day(record.get("executed_day"), "executed_day of %r" % ident)
    deviation = record.get("deviation")
    if deviation is not None:
        deviation = str(deviation).strip()
        if not deviation:
            raise ValueError("report entry %r carries an empty deviation reference" % ident)
    retest_of = record.get("retest_of")
    if retest_of is not None:
        retest_of = str(retest_of).strip()
        if not retest_of:
            raise ValueError("report entry %r carries an empty retest_of reference" % ident)
        if retest_of == ident:
            raise ValueError("report entry %r declares itself as its own predecessor" % ident)
    return {
        "id": ident,
        "activity": activity,
        "result": result,
        "executed_day": executed_day,
        "deviation": deviation,
        "retest_of": retest_of,
    }


def build_entry_list(records):
    """Normalise every report entry, rejecting a repeated entry id."""
    if records is None:
        raise ValueError("verification report declares no entry list")
    entries = []
    seen = set()
    for record in records:
        entry = normalise_report_entry(record)
        if entry["id"] in seen:
            raise ValueError("duplicate report entry id %r" % entry["id"])
        seen.add(entry["id"])
        entries.append(entry)
    if not entries:
        raise ValueError("verification report declares no entry")
    return entries


def missing_document_sections(declared, kind):
    """Return the mandatory sections the named document does not declare."""
    if kind == "plan":
        required = PLAN_SECTIONS
    elif kind == "report":
        required = REPORT_SECTIONS
    else:
        raise ValueError(
            "unknown document kind %r (expected 'plan' or 'report')" % (kind,)
        )
    if declared is None:
        raise ValueError("%s document declares no section list" % kind)
    seen = set()
    for item in declared:
        name = str(item).strip().lower()
        if not name:
            raise ValueError("%s document carries an empty section name" % kind)
        seen.add(name)
    return [section for section in required if section not in seen]


def trace_activities(activity_index, entries):
    """Trace the plan into the report and the report back into the plan."""
    reported = {}
    orphan = []
    for entry in entries:
        if entry["activity"] not in activity_index:
            orphan.append(entry["id"])
        else:
            reported.setdefault(entry["activity"], []).append(entry)
    untraced = sorted(ident for ident in activity_index if ident not in reported)
    return {
        "untraced": untraced,
        "orphan": sorted(orphan),
        "reported": reported,
    }


def governing_entry(entries_for_activity):
    """The entry that settles an activity: latest executed, id as tie-break."""
    if not entries_for_activity:
        raise ValueError("no report entry for the activity")
    return sorted(
        entries_for_activity, key=lambda e: (e["executed_day"], e["id"])
    )[-1]


def closure_review(activity_index, reported, entry_ids):
    """Decide which activities are closed and collect the closure findings."""
    closed = []
    findings = []
    for ident in sorted(reported):
        entries = reported[ident]
        for entry in sorted(entries, key=lambda e: e["id"]):
            if entry["result"] == "compliant-with-deviation" and not entry["deviation"]:
                findings.append(
                    "entry %s accepts activity %s with a deviation but names no "
                    "deviation record" % (entry["id"], ident)
                )
            if entry["retest_of"] is not None and entry["retest_of"] not in entry_ids:
                findings.append(
                    "entry %s is a repeat of %s, which is not an entry in the report"
                    % (entry["id"], entry["retest_of"])
                )
        settled = governing_entry(entries)
        if settled["result"] == "non-compliant":
            findings.append(
                "activity %s is left non-compliant by entry %s with no later "
                "repeat and no accepted deviation" % (ident, settled["id"])
            )
        elif settled["result"] == "compliant-with-deviation" and not settled["deviation"]:
            continue
        else:
            closed.append(ident)
    return {"closed": sorted(closed), "findings": findings}


def coverage_percent(activity_index, closed_ids):
    """Sum the declared requirement-set share of the closed activities."""
    total = 0.0
    for ident in sorted(closed_ids):
        if ident not in activity_index:
            raise ValueError("closed activity %r is not in the plan" % ident)
        total += activity_index[ident]["share_percent"]
    return total


def meets_coverage_target(percent, target):
    """Compare an accumulated share against the demanded coverage.

    The accumulated value is a sum of decimal percentages, so a case that
    is compliant in engineering terms can land a few units in the last
    place below the target (33.4 + 33.3 + 33.3 sums to 99.99999999999999,
    not 100.0). That representation error is absorbed here; the target
    itself is never lowered.
    """
    if isinstance(percent, bool) or not isinstance(percent, (int, float)):
        raise ValueError("accumulated coverage must be a number (got %r)" % (percent,))
    target = _positive_share(target, "coverage target")
    value = float(percent)
    if math.isnan(value):
        raise ValueError("accumulated coverage must be a real number")
    if value >= target:
        return True
    return math.isclose(value, target, rel_tol=0.0, abs_tol=SHARE_TOLERANCE)


def schedule_findings(
    plan_issue_day,
    report_issue_day,
    entries,
    data_package_day,
    minimum_plan_lead_days=0,
):
    """Check the two issue dates against the campaign and the review gate."""
    if isinstance(minimum_plan_lead_days, bool) or not isinstance(
        minimum_plan_lead_days, int
    ):
        raise ValueError(
            "minimum plan lead must be a whole number of days (got %r)"
            % (minimum_plan_lead_days,)
        )
    if minimum_plan_lead_days < 0:
        raise ValueError("minimum plan lead cannot be negative")
    if not entries:
        raise ValueError("no report entry to place against the issue dates")
    plan_day = _parse_day(plan_issue_day, "plan issue date")
    report_day = _parse_day(report_issue_day, "report issue date")
    package_day = _parse_day(data_package_day, "review data-package date")
    first = min(entry["executed_day"] for entry in entries)
    last = max(entry["executed_day"] for entry in entries)
    findings = []
    lead = (first - plan_day).days
    if lead < 0:
        findings.append(
            "plan issued %s, after the first activity ran on %s"
            % (plan_day.isoformat(), first.isoformat())
        )
    elif lead < minimum_plan_lead_days:
        findings.append(
            "plan issued %d day(s) before the first activity, less than the %d "
            "day(s) demanded" % (lead, minimum_plan_lead_days)
        )
    if report_day < last:
        findings.append(
            "report issued %s, before the last activity ran on %s"
            % (report_day.isoformat(), last.isoformat())
        )
    if report_day > package_day:
        findings.append(
            "report issued %s, after the review data-package date %s"
            % (report_day.isoformat(), package_day.isoformat())
        )
    return findings


def review_verification_documents(plan, report, coverage_target=100.0):
    """Aggregate the clause 6.4.1 review of the plan and report pair."""
    if not isinstance(plan, dict) or not isinstance(report, dict):
        raise ValueError("plan and report must each be a mapping")
    activity_index = build_activity_index(plan.get("activities"))
    entries = build_entry_list(report.get("entries"))
    entry_ids = set(entry["id"] for entry in entries)
    plan_gaps = missing_document_sections(plan.get("sections"), "plan")
    report_gaps = missing_document_sections(report.get("sections"), "report")
    trace = trace_activities(activity_index, entries)
    closure = closure_review(activity_index, trace["reported"], entry_ids)
    covered = coverage_percent(activity_index, closure["closed"])
    schedule = schedule_findings(
        plan.get("issue_day"),
        report.get("issue_day"),
        entries,
        report.get("data_package_day"),
        plan.get("minimum_lead_days", 0),
    )
    coverage_ok = meets_coverage_target(covered, coverage_target)
    compliant = not (
        plan_gaps
        or report_gaps
        or trace["untraced"]
        or trace["orphan"]
        or closure["findings"]
        or schedule
    ) and coverage_ok
    return {
        "plan_section_gaps": plan_gaps,
        "report_section_gaps": report_gaps,
        "untraced_activities": trace["untraced"],
        "orphan_entries": trace["orphan"],
        "closure_findings": closure["findings"],
        "closed_activities": closure["closed"],
        "schedule_findings": schedule,
        "coverage_percent": covered,
        "coverage_target": float(coverage_target),
        "coverage_met": coverage_ok,
        "compliant": compliant,
    }
