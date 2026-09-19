"""Nonconformance control at a space test centre.

Anchor: ECSS-Q-ST-20-07C clause 5.8.2 (control of nonconformances arising at
the test centre), working with the nonconformance control system of
ECSS-Q-ST-10-09. Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Categorize each test-centre anomaly as major or minor from its effect:
   personnel or facility safety, an exceeded article limit, a violated
   specified requirement, or invalidated test conditions.
2. Derive the reporting deadline and the disposition authority that the
   category carries, and decide whether the anomaly was reported in time.
3. Decide the retest scope the anomaly forces: none, the affected phases
   again, or the whole run again.
4. Check the proposed disposition against the ones the category permits and
   against the approval it needs.
5. Aggregate the campaign: a close-out is permitted only when no anomaly is
   still open and no disposition is unapproved.
"""

import math

__all__ = [
    "RATIO_TOLERANCE",
    "HOUR_TOLERANCE",
    "REPORTING_DEADLINE_H",
    "DISPOSITIONS",
    "APPROVAL_NEEDED",
    "overstress_ratio",
    "categorize_severity",
    "reporting_deadline_h",
    "disposition_authority",
    "report_timeliness",
    "retest_scope",
    "validate_disposition",
    "assess_nonconformance",
    "assess_campaign",
]

# Ratio and elapsed-hour comparisons can land a few ULP either side of a limit
# a case is meant to sit exactly on. Absorb representation error here rather
# than relaxing the engineering limit.
RATIO_TOLERANCE = 1e-9
HOUR_TOLERANCE = 1e-9

# Hours from detection within which the anomaly has to reach the customer.
REPORTING_DEADLINE_H = {"major": 24.0, "minor": 120.0}

DISPOSITIONS = ("use-as-is", "repair", "rework", "retest", "scrap")

# Dispositions that leave the article different from its specification need
# the customer's agreement when the anomaly is major.
APPROVAL_NEEDED = ("use-as-is", "repair")


def _bool(nc, key, default=False):
    value = nc.get(key, default)
    if not isinstance(value, bool):
        raise ValueError("'%s' must be a boolean, got %r" % (key, value))
    return value


def _hours(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite" % label)
    if out < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, out))
    return out


def overstress_ratio(applied, limit):
    """Return the ratio of an applied test level to the article's limit."""
    for label, value in (("applied", applied), ("limit", limit)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number, got %r" % (label, value))
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % label)
    if float(limit) <= 0.0:
        raise ValueError("limit must be positive, got %g" % float(limit))
    if float(applied) < 0.0:
        raise ValueError("applied must not be negative, got %g" % float(applied))
    return float(applied) / float(limit)


def _is_overstress(nc):
    """Return True when the anomaly took the article past a stated limit."""
    if "applied_level" in nc and "limit_level" in nc:
        ratio = overstress_ratio(nc["applied_level"], nc["limit_level"])
        return ratio > 1.0 and not math.isclose(
            ratio, 1.0, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
        )
    return _bool(nc, "article_overstressed")


def categorize_severity(nc):
    """Return 'major' or 'minor' for one test-centre anomaly."""
    if not isinstance(nc, dict):
        raise ValueError("nonconformance must be a mapping")
    if _bool(nc, "safety_affected"):
        return "major"
    if _bool(nc, "requirement_violated"):
        return "major"
    if _is_overstress(nc):
        return "major"
    if _bool(nc, "conditions_invalidated"):
        return "major"
    return "minor"


def reporting_deadline_h(severity):
    """Return the hours from detection allowed before the anomaly is reported."""
    if severity not in REPORTING_DEADLINE_H:
        raise ValueError("unknown severity %r" % (severity,))
    return REPORTING_DEADLINE_H[severity]


def disposition_authority(severity):
    """Return the body that owns the disposition decision for a severity."""
    if severity not in REPORTING_DEADLINE_H:
        raise ValueError("unknown severity %r" % (severity,))
    if severity == "major":
        return "customer nonconformance review board"
    return "test centre quality function"


def report_timeliness(detected_h, reported_h, severity):
    """Return the timeliness record of an anomaly report."""
    detected = _hours("detected_h", detected_h)
    reported = _hours("reported_h", reported_h)
    if reported < detected:
        raise ValueError(
            "reported_h %g precedes detected_h %g" % (reported, detected)
        )
    deadline = reporting_deadline_h(severity)
    elapsed = reported - detected
    timely = elapsed < deadline or math.isclose(
        elapsed, deadline, rel_tol=0.0, abs_tol=HOUR_TOLERANCE
    )
    return {
        "elapsed_h": elapsed,
        "deadline_h": deadline,
        "timely": timely,
    }


def retest_scope(nc):
    """Return 'none', 'partial' or 'full' for the retest the anomaly forces."""
    if not isinstance(nc, dict):
        raise ValueError("nonconformance must be a mapping")
    total = nc.get("total_phases", 1)
    if not isinstance(total, int) or isinstance(total, bool) or total < 1:
        raise ValueError("total_phases must be an integer of at least 1")
    affected = nc.get("affected_phases", [])
    if not isinstance(affected, (list, tuple)):
        raise ValueError("affected_phases must be a sequence")
    names = []
    for item in affected:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("each affected phase must be a non-empty string")
        if item not in names:
            names.append(item)
    if len(names) > total:
        raise ValueError(
            "%d affected phases exceed the %d phases of the run" % (len(names), total)
        )
    if _is_overstress(nc):
        return "full"
    if _bool(nc, "conditions_invalidated"):
        if not names:
            raise ValueError(
                "conditions were invalidated but no affected phase is named; "
                "the retest scope cannot be derived"
            )
        return "full" if len(names) == total else "partial"
    return "none"


def validate_disposition(severity, disposition, customer_approved=False):
    """Check a proposed disposition against the severity that governs it."""
    if severity not in REPORTING_DEADLINE_H:
        raise ValueError("unknown severity %r" % (severity,))
    if disposition not in DISPOSITIONS:
        raise ValueError(
            "unknown disposition %r; expected one of %s"
            % (disposition, ", ".join(DISPOSITIONS))
        )
    if not isinstance(customer_approved, bool):
        raise ValueError("customer_approved must be a boolean")
    findings = []
    needs_approval = severity == "major" and disposition in APPROVAL_NEEDED
    if needs_approval and not customer_approved:
        findings.append(
            "a major anomaly dispositioned '%s' needs the customer's agreement"
            % disposition
        )
    return {
        "severity": severity,
        "disposition": disposition,
        "authority": disposition_authority(severity),
        "approval_required": needs_approval,
        "approval_held": customer_approved,
        "acceptable": not findings,
        "findings": findings,
    }


def assess_nonconformance(nc):
    """Assess one test-centre anomaly end to end."""
    if not isinstance(nc, dict):
        raise ValueError("nonconformance must be a mapping")
    for key in ("id", "detected_h", "reported_h", "disposition"):
        if key not in nc:
            raise ValueError("nonconformance missing required key '%s'" % key)
    nc_id = nc["id"]
    if not isinstance(nc_id, str) or not nc_id.strip():
        raise ValueError("nonconformance id must be a non-empty string")
    severity = categorize_severity(nc)
    timeliness = report_timeliness(nc["detected_h"], nc["reported_h"], severity)
    scope = retest_scope(nc)
    disposition = validate_disposition(
        severity, nc["disposition"], _bool(nc, "customer_approved")
    )
    closed = _bool(nc, "closed")
    findings = list(disposition["findings"])
    if not timeliness["timely"]:
        findings.append(
            "%s reported %.2f h after detection, past the %.2f h deadline"
            % (nc_id, timeliness["elapsed_h"], timeliness["deadline_h"])
        )
    if scope != "none" and nc["disposition"] != "retest" and not _bool(
        nc, "retest_performed"
    ):
        findings.append(
            "%s forces a %s retest that is neither dispositioned nor performed"
            % (nc_id, scope)
        )
    if closed and findings:
        findings.append("%s is recorded closed with findings still open" % nc_id)
    return {
        "id": nc_id,
        "severity": severity,
        "authority": disposition["authority"],
        "timeliness": timeliness,
        "retest_scope": scope,
        "disposition": disposition,
        "closed": closed,
        "findings": findings,
        "acceptable": not findings,
    }


def assess_campaign(nonconformances):
    """Aggregate the anomaly records of one test campaign."""
    if not isinstance(nonconformances, (list, tuple)):
        raise ValueError("nonconformances must be a sequence")
    records = [assess_nonconformance(nc) for nc in nonconformances]
    seen = set()
    for record in records:
        if record["id"] in seen:
            raise ValueError("duplicate nonconformance id %r" % record["id"])
        seen.add(record["id"])
    major = [r for r in records if r["severity"] == "major"]
    minor = [r for r in records if r["severity"] == "minor"]
    open_records = [r for r in records if not r["closed"]]
    late = [r for r in records if not r["timeliness"]["timely"]]
    retest_owed = [
        r for r in records if r["retest_scope"] != "none" and not r["acceptable"]
    ]
    findings = []
    for record in records:
        findings.extend(record["findings"])
    if open_records:
        findings.append(
            "%d anomaly record(s) still open at close-out" % len(open_records)
        )
    return {
        "records": records,
        "major_count": len(major),
        "minor_count": len(minor),
        "open_count": len(open_records),
        "late_report_count": len(late),
        "retest_owed_count": len(retest_owed),
        "findings": findings,
        "close_out_permitted": not findings,
    }
