#!/usr/bin/env python3
"""Compliance matrix review item for a microwave die design review.

Anchor: ECSS-Q-ST-60-12C clause 7.3.10. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The matrix is the tabulated statement of conformance: one row per
applicable design requirement, each row carrying a conformance state
and the evidence that state rests on. Reviewing it is not reading the
rows -- it is confronting the rows with the requirement list they claim
to answer, and then testing each row for the thing it owes.

A row owes different things depending on what it states.

    compliant            an evidence reference
    partially-compliant  an evidence reference and a departure reference
    non-compliant        a departure reference
    not-applicable       a justification for the exclusion

Three failure modes survive a casual read and are what this review
exists to catch: a requirement with no row at all, a row claiming
conformance against nothing, and a departure that was never raised as
a deviation or waiver.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

CONFORMANCE_STATUSES = (
    "compliant",
    "partially-compliant",
    "non-compliant",
    "not-applicable",
)

STATUSES_NEEDING_EVIDENCE = ("compliant", "partially-compliant")
STATUSES_NEEDING_DEPARTURE = ("partially-compliant", "non-compliant")

VERDICT_ACCEPTED = "compliance-matrix-accepted"
VERDICT_ACTIONED = "compliance-matrix-open-with-actions"
VERDICT_REJECTED = "compliance-matrix-rejected"

_ROW_FIELDS = (
    "requirement_id",
    "status",
    "evidence_ref",
    "departure_ref",
    "justification",
)


def normalize_requirement_id(value):
    """Canonical form of a requirement identifier.

    Matrices are assembled by hand from several sources, so the same
    requirement arrives spelled with stray space and mixed case. The
    canonical form is what coverage is counted on.
    """
    if not isinstance(value, str):
        raise ValueError("requirement_id must be a string, got %r" % (value,))
    canonical = " ".join(value.split()).upper()
    if not canonical:
        raise ValueError("requirement_id must not be blank")
    return canonical


def normalize_status(value):
    """Canonical conformance state, rejecting anything outside the set."""
    if not isinstance(value, str):
        raise ValueError("status must be a string, got %r" % (value,))
    canonical = " ".join(value.split()).lower().replace(" ", "-").replace("_", "-")
    if canonical not in CONFORMANCE_STATUSES:
        raise ValueError(
            "status must be one of %s, got %r"
            % (", ".join(CONFORMANCE_STATUSES), value)
        )
    return canonical


def _optional_text(name, value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("%s must be a string when given, got %r" % (name, value))
    text = " ".join(value.split())
    return text or None


def validate_matrix_row(row):
    """Normalize one matrix row and reject a malformed one."""
    if not isinstance(row, dict):
        raise ValueError("matrix row must be a mapping, got %r" % (row,))
    unknown = set(row) - set(_ROW_FIELDS)
    if unknown:
        raise ValueError(
            "matrix row carries unknown fields: %s" % ", ".join(sorted(unknown))
        )
    return {
        "requirement_id": normalize_requirement_id(row.get("requirement_id")),
        "status": normalize_status(row.get("status")),
        "evidence_ref": _optional_text("evidence_ref", row.get("evidence_ref")),
        "departure_ref": _optional_text("departure_ref", row.get("departure_ref")),
        "justification": _optional_text("justification", row.get("justification")),
    }


def build_matrix(rows):
    """Normalize every row and reject a requirement stated twice."""
    if not isinstance(rows, (list, tuple)):
        raise ValueError("rows must be a list of mappings, got %r" % (rows,))
    if not rows:
        raise ValueError("a compliance matrix with no rows cannot be reviewed")
    matrix = {}
    for row in rows:
        normalized = validate_matrix_row(row)
        key = normalized["requirement_id"]
        if key in matrix:
            raise ValueError(
                "requirement %s is stated twice; a matrix carries one row per "
                "requirement" % key
            )
        matrix[key] = normalized
    return matrix


def coverage_report(applicable_requirement_ids, rows):
    """Confront the rows with the requirement list they claim to answer."""
    if not isinstance(applicable_requirement_ids, (list, tuple)):
        raise ValueError(
            "applicable_requirement_ids must be a list, got %r"
            % (applicable_requirement_ids,)
        )
    if not applicable_requirement_ids:
        raise ValueError("the applicable requirement list must not be empty")
    applicable = []
    for value in applicable_requirement_ids:
        canonical = normalize_requirement_id(value)
        if canonical in applicable:
            raise ValueError(
                "requirement %s is listed twice as applicable" % canonical
            )
        applicable.append(canonical)
    matrix = build_matrix(rows)
    covered = [key for key in applicable if key in matrix]
    uncovered = [key for key in applicable if key not in matrix]
    orphan = sorted(key for key in matrix if key not in applicable)
    return {
        "applicable_count": len(applicable),
        "covered": covered,
        "uncovered": uncovered,
        "orphan": orphan,
        "coverage_fraction": len(covered) / len(applicable),
    }


def evidence_gaps(rows):
    """Rows that state conformance without pointing at anything."""
    matrix = build_matrix(rows)
    return sorted(
        key
        for key, row in matrix.items()
        if row["status"] in STATUSES_NEEDING_EVIDENCE and not row["evidence_ref"]
    )


def unwaived_departures(rows):
    """Rows that depart from a requirement with no deviation or waiver."""
    matrix = build_matrix(rows)
    return sorted(
        key
        for key, row in matrix.items()
        if row["status"] in STATUSES_NEEDING_DEPARTURE and not row["departure_ref"]
    )


def unjustified_exclusions(rows):
    """Rows excluding a requirement without saying why."""
    matrix = build_matrix(rows)
    return sorted(
        key
        for key, row in matrix.items()
        if row["status"] == "not-applicable" and not row["justification"]
    )


def conformance_counts(rows):
    """How the rows are grouped across the conformance states."""
    matrix = build_matrix(rows)
    counts = dict.fromkeys(CONFORMANCE_STATUSES, 0)
    for row in matrix.values():
        counts[row["status"]] += 1
    return counts


def full_conformance_fraction(rows):
    """Share of the rows that state conformance without qualification.

    Excluded requirements are taken out of both halves: a matrix does
    not get credit for a requirement it declared inapplicable, and it is
    not penalised for one either.
    """
    counts = conformance_counts(rows)
    assessed = sum(
        counts[status] for status in CONFORMANCE_STATUSES if status != "not-applicable"
    )
    if assessed == 0:
        raise ValueError(
            "every row is marked not-applicable; there is no conformance to state"
        )
    return counts["compliant"] / assessed


def review_compliance_matrix(case):
    """Full clause 7.3.10 compliance matrix review with a verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    rows = case.get("rows")
    coverage = coverage_report(case.get("applicable_requirement_ids"), rows)
    gaps = evidence_gaps(rows)
    unwaived = unwaived_departures(rows)
    unjustified = unjustified_exclusions(rows)
    counts = conformance_counts(rows)
    findings = []
    actions = []
    if coverage["uncovered"]:
        findings.append(
            "no row answers %s" % ", ".join(coverage["uncovered"])
        )
    if gaps:
        findings.append(
            "conformance stated with no evidence reference for %s" % ", ".join(gaps)
        )
    if unwaived:
        findings.append(
            "departure carried with no deviation or waiver reference for %s"
            % ", ".join(unwaived)
        )
    if coverage["orphan"]:
        actions.append(
            "withdraw or re-baseline the rows against no applicable requirement: %s"
            % ", ".join(coverage["orphan"])
        )
    if unjustified:
        actions.append(
            "justify the exclusion of %s or restore it to the assessed set"
            % ", ".join(unjustified)
        )
    if counts["partially-compliant"]:
        actions.append(
            "carry the %d partially compliant requirement row or rows into the "
            "open work list" % counts["partially-compliant"]
        )
    blocking = bool(coverage["uncovered"] or gaps or unwaived)
    if blocking:
        verdict = VERDICT_REJECTED
    elif actions:
        verdict = VERDICT_ACTIONED
    else:
        verdict = VERDICT_ACCEPTED
    return {
        "verdict": verdict,
        "coverage": coverage,
        "counts": counts,
        "evidence_gaps": gaps,
        "unwaived_departures": unwaived,
        "unjustified_exclusions": unjustified,
        "full_conformance_fraction": full_conformance_fraction(rows),
        "actions": actions,
        "findings": findings,
    }
