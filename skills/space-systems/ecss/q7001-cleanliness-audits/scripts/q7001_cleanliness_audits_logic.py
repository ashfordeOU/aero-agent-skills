#!/usr/bin/env python3
"""Contamination-control audits of a cleanroom facility or a supplier.

Anchor: ECSS-Q-ST-70-01C, programme surveillance. The procedure below
is a paraphrase into implementable steps; no standard text is
reproduced.

An audit scores practice, not paperwork. Each practice area carries a
weight because the areas are not equally load bearing: cleaning and
verification method and air-quality monitoring govern whether the
declared cleanliness level is real at all, while consumable control
and documentation matter but cannot by themselves put a deposit on a
surface.

Two vetoes sit above the weighted index. A single area scoring zero
blocks approval however strong the average, and a major finding count
past the declared tolerance does the same. The re-audit interval is an
output of the audit, derived from the index and the contamination
criticality of the hardware, not a calendar habit.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime

# practice area -> weight
PRACTICE_AREAS = {
    "cleaning-and-verification-method": 5,
    "cleanroom-air-quality-monitoring": 5,
    "garmenting-and-personnel-flow": 4,
    "handling-packaging-and-purge": 4,
    "material-and-consumable-control": 3,
    "monitoring-instrument-calibration": 3,
    "training-and-authorisation-records": 3,
    "documentation-and-traceability": 3,
}

SCORE_MIN = 0
SCORE_MAX = 4

SEVERITY_MAJOR = "major"
SEVERITY_MINOR = "minor"
SEVERITY_OBSERVATION = "observation"

FINDING_SEVERITIES = (SEVERITY_MAJOR, SEVERITY_MINOR, SEVERITY_OBSERVATION)

CRITICALITY_CRITICAL = "contamination-critical"
CRITICALITY_SENSITIVE = "contamination-sensitive"
CRITICALITY_STANDARD = "standard"

CRITICALITY_LEVELS = (
    CRITICALITY_CRITICAL,
    CRITICALITY_SENSITIVE,
    CRITICALITY_STANDARD,
)

BASE_REAUDIT_MONTHS = {
    CRITICALITY_CRITICAL: 12,
    CRITICALITY_SENSITIVE: 18,
    CRITICALITY_STANDARD: 24,
}

MIN_REAUDIT_MONTHS = 3

APPROVAL_INDEX = 0.90
CONDITIONAL_INDEX = 0.70

# Majors tolerated before approval is blocked outright.
MAJOR_TOLERANCE = 2

TOL = 1e-9

STATUS_APPROVED = "facility-approved"
STATUS_CONDITIONAL = "facility-approved-with-conditions"
STATUS_SUSPENDED = "facility-suspended"


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_score(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer score, got %r" % (name, value))
    if not (SCORE_MIN <= value <= SCORE_MAX):
        raise ValueError(
            "%s must be between %d and %d, got %r" % (name, SCORE_MIN, SCORE_MAX, value)
        )
    return value


def parse_date(name, value):
    """ISO calendar date, rejected rather than guessed when malformed."""
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string, got %r" % (name, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not an ISO calendar date: %r" % (name, value))


def add_months(start, months):
    """Calendar months on, clamped to the last day of the landing month."""
    if isinstance(months, bool) or not isinstance(months, int) or months < 0:
        raise ValueError("months must be a non-negative integer, got %r" % (months,))
    total = start.month - 1 + months
    year = start.year + total // 12
    month = total % 12 + 1
    day = start.day
    while day > 1:
        try:
            return datetime.date(year, month, day)
        except ValueError:
            day -= 1
    return datetime.date(year, month, 1)


def normalise_scores(scores):
    """Per-area scores, with an unscored or unknown area refused."""
    if not isinstance(scores, dict) or not scores:
        raise ValueError("scores must be a non-empty mapping, got %r" % (scores,))
    out = {}
    for area, value in scores.items():
        if area not in PRACTICE_AREAS:
            raise ValueError("unknown practice area: %r" % (area,))
        out[area] = _require_score("scores[%s]" % area, value)
    return out


def conformity_index(scores):
    """Weighted conformity over the areas that were actually in scope."""
    rows = normalise_scores(scores)
    earned = sum(PRACTICE_AREAS[area] * score for area, score in rows.items())
    possible = sum(PRACTICE_AREAS[area] * SCORE_MAX for area in rows)
    collapsed = tuple(sorted(area for area, score in rows.items() if score == SCORE_MIN))
    weakest = min(rows, key=lambda area: (rows[area], area))
    return {
        "areas_in_scope": tuple(sorted(rows)),
        "areas_not_examined": tuple(sorted(set(PRACTICE_AREAS) - set(rows))),
        "weighted_score": earned,
        "weighted_maximum": possible,
        "index": earned / possible if possible else 0.0,
        "collapsed_areas": collapsed,
        "weakest_area": weakest,
    }


def normalise_finding(finding, index=0):
    """One audit finding, validated rather than defaulted."""
    if not isinstance(finding, dict):
        raise ValueError("finding[%d] must be a mapping, got %r" % (index, finding))
    area = finding.get("area")
    if area not in PRACTICE_AREAS:
        raise ValueError("finding[%d].area is not a practice area: %r" % (index, area))
    return {
        "id": _require_text("finding[%d].id" % index, finding.get("id")),
        "area": area,
        "severity": _require_choice(
            "finding[%d].severity" % index,
            finding.get("severity"),
            FINDING_SEVERITIES,
        ),
    }


def group_findings(findings):
    """Findings counted by severity, keeping the identifiers to act on."""
    if findings is None:
        findings = []
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a list, got %r" % (findings,))
    counts = {severity: 0 for severity in FINDING_SEVERITIES}
    grouped = {severity: [] for severity in FINDING_SEVERITIES}
    seen = set()
    for i, finding in enumerate(findings):
        row = normalise_finding(finding, i)
        if row["id"] in seen:
            raise ValueError("duplicate finding identifier: %r" % row["id"])
        seen.add(row["id"])
        counts[row["severity"]] += 1
        grouped[row["severity"]].append(row["id"])
    return {
        "counts": counts,
        "ids": {s: tuple(grouped[s]) for s in FINDING_SEVERITIES},
        "total": sum(counts.values()),
    }


def reaudit_interval_months(index, criticality, blocked=False):
    """Interval the audit itself sets, floored so it cannot run away."""
    _require_choice("criticality", criticality, CRITICALITY_LEVELS)
    if isinstance(index, bool) or not isinstance(index, (int, float)):
        raise ValueError("index must be a number, got %r" % (index,))
    if not (0.0 - TOL <= index <= 1.0 + TOL):
        raise ValueError("index must lie between 0 and 1, got %r" % (index,))
    base = BASE_REAUDIT_MONTHS[criticality]
    if blocked:
        return MIN_REAUDIT_MONTHS
    if index >= APPROVAL_INDEX - TOL:
        months = base
    elif index >= CONDITIONAL_INDEX - TOL:
        months = base // 2
    else:
        months = base // 4
    return max(MIN_REAUDIT_MONTHS, months)


def audit_contamination_control(case):
    """Full audit outcome: index, findings, approval status and next audit."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    facility = _require_text("facility", case.get("facility"))
    audit_date = parse_date("audit_date", case.get("audit_date"))
    criticality = _require_choice(
        "criticality", case.get("criticality"), CRITICALITY_LEVELS
    )
    conformity = conformity_index(case.get("scores"))
    findings = group_findings(case.get("findings"))
    majors = findings["counts"][SEVERITY_MAJOR]
    reasons = []
    if conformity["collapsed_areas"]:
        reasons.append(
            "practice area(s) scoring zero: %s"
            % ", ".join(conformity["collapsed_areas"])
        )
    if majors > MAJOR_TOLERANCE:
        reasons.append(
            "%d major finding(s), past the tolerance of %d"
            % (majors, MAJOR_TOLERANCE)
        )
    if conformity["index"] < CONDITIONAL_INDEX - TOL:
        reasons.append(
            "conformity index %.4f is below the %.2f needed to let hardware in"
            % (conformity["index"], CONDITIONAL_INDEX)
        )
    conditions = []
    if majors:
        conditions.extend(
            "major finding %s to close before hardware enters" % fid
            for fid in findings["ids"][SEVERITY_MAJOR]
        )
    if findings["counts"][SEVERITY_MINOR]:
        conditions.append(
            "%d minor finding(s) to close on the agreed dates"
            % findings["counts"][SEVERITY_MINOR]
        )
    if conformity["areas_not_examined"]:
        conditions.append(
            "practice area(s) not examined this audit: %s"
            % ", ".join(conformity["areas_not_examined"])
        )
    if reasons:
        status = STATUS_SUSPENDED
    elif conditions or conformity["index"] < APPROVAL_INDEX - TOL:
        status = STATUS_CONDITIONAL
    else:
        status = STATUS_APPROVED
    months = reaudit_interval_months(
        conformity["index"], criticality, blocked=bool(reasons)
    )
    return {
        "facility": facility,
        "audit_date": audit_date.isoformat(),
        "criticality": criticality,
        "conformity": conformity,
        "findings": findings,
        "blocking_reasons": tuple(reasons),
        "conditions": tuple(conditions),
        "hardware_may_enter": status != STATUS_SUSPENDED,
        "reaudit_months": months,
        "reaudit_due": add_months(audit_date, months).isoformat(),
        "status": status,
    }
