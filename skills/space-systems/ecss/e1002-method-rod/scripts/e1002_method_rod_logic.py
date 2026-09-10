#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.2.4 review-of-design verification method
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
review-of-design method closes out a requirement by examining
already-existing design documentation -- drawings, analysis reports,
design descriptions, supplier certificates, or heritage/similarity
records from a qualified prior design -- against the requirement text,
without generating new test or measurement data for this verification
action. This module implements evidence classification, the
safety-critical/heritage-only admissibility rule, the per-requirement
status roll-up across evidence dispositions, and review-of-design
report assembly and completeness checking; it does not implement the
test, analysis, or inspection methods, or the method-selection
precedence across all four methods (see the sibling
e10-req-verif-methods leaf).
"""

DIRECT_EVIDENCE_TYPES = frozenset(
    {"drawing", "analysis_report", "design_description", "supplier_certificate"}
)
HERITAGE_EVIDENCE_TYPES = frozenset({"heritage_data", "similarity_data"})
EVIDENCE_TYPES = DIRECT_EVIDENCE_TYPES | HERITAGE_EVIDENCE_TYPES

DISPOSITIONS = ("compliant", "non_compliant", "open", "not_applicable")

HERITAGE_ONLY_SAFETY_CRITICAL_ISSUE = "heritage_only_evidence_for_safety_critical"
NO_COMPLIANT_EVIDENCE_STATUS = "no_compliant_evidence"


def classify_evidence(evidence_type):
    """Evidence family for one evidence type: "direct" (drawing,
    analysis_report, design_description, supplier_certificate) or
    "heritage" (heritage_data, similarity_data). Raises ValueError for
    an evidence type outside both families."""
    if evidence_type in DIRECT_EVIDENCE_TYPES:
        return "direct"
    if evidence_type in HERITAGE_EVIDENCE_TYPES:
        return "heritage"
    raise ValueError(
        "unrecognized review-of-design evidence type %r under "
        "E-ST-10-02C clause 5.2.2.4" % (evidence_type,)
    )


def check_evidence_admissibility(evidence_items, safety_critical, similarity_assessment_approved=False):
    """Admissibility issue list (empty if admissible) for one
    requirement's evidence set. evidence_items: iterable of dicts with
    an "evidence_type" key. Raises ValueError if evidence_items is
    empty (review of design cannot proceed with zero evidence) or if
    any item carries an unrecognized evidence_type. Flags
    HERITAGE_ONLY_SAFETY_CRITICAL_ISSUE when the requirement is
    safety-critical, every item classifies as heritage evidence (no
    direct evidence at all), and similarity_assessment_approved is
    False. Does not mutate evidence_items."""
    evidence_items = list(evidence_items)
    if not evidence_items:
        raise ValueError("review-of-design requires at least one evidence item")
    categories = [classify_evidence(item["evidence_type"]) for item in evidence_items]
    if safety_critical and not similarity_assessment_approved and "direct" not in categories:
        return [{"issue": HERITAGE_ONLY_SAFETY_CRITICAL_ISSUE}]
    return []


def evidence_rollup_status(evidence_items):
    """Overall requirement status rolled up from a list of dicts each
    carrying a "disposition" key, by precedence: any "non_compliant"
    item -> "non_compliant"; else any "open" item -> "open"; else at
    least one "compliant" item -> "compliant"; else (only
    "not_applicable" items) -> NO_COMPLIANT_EVIDENCE_STATUS. Raises
    ValueError for an empty list or an unrecognized disposition."""
    evidence_items = list(evidence_items)
    if not evidence_items:
        raise ValueError("cannot roll up an empty evidence set")
    dispositions = []
    for item in evidence_items:
        disposition = item["disposition"]
        if disposition not in DISPOSITIONS:
            raise ValueError("unrecognized evidence disposition %r" % (disposition,))
        dispositions.append(disposition)
    if "non_compliant" in dispositions:
        return "non_compliant"
    if "open" in dispositions:
        return "open"
    if "compliant" in dispositions:
        return "compliant"
    return NO_COMPLIANT_EVIDENCE_STATUS


def build_rod_report_entry(requirement):
    """Review-of-design report entry for one requirement dict with
    keys: "id", "evidence" (list of {"evidence_type", "disposition"}),
    "reviewer_id"; optional keys "safety_critical" (default False) and
    "similarity_assessment_approved" (default False). Returns a new
    dict {"id", "reviewer_id", "status", "admissibility_issues"}; does
    not mutate the input. Raises ValueError if "id" is missing, if
    "reviewer_id" is missing or empty, or via check_evidence_admissibility
    / evidence_rollup_status for a malformed evidence set."""
    if "id" not in requirement:
        raise ValueError("requirement is missing an id")
    reviewer_id = requirement.get("reviewer_id")
    if not reviewer_id:
        raise ValueError("review-of-design report entry requires a reviewer_id")
    evidence = requirement.get("evidence", [])
    admissibility_issues = check_evidence_admissibility(
        evidence,
        requirement.get("safety_critical", False),
        requirement.get("similarity_assessment_approved", False),
    )
    status = evidence_rollup_status(evidence)
    return {
        "id": requirement["id"],
        "reviewer_id": reviewer_id,
        "status": status,
        "admissibility_issues": admissibility_issues,
    }


def build_rod_report(requirements):
    """Review-of-design report: one entry per requirement, in input
    order. Raises ValueError on a duplicate requirement id."""
    report = []
    seen_ids = set()
    for requirement in requirements:
        entry = build_rod_report_entry(requirement)
        if entry["id"] in seen_ids:
            raise ValueError("duplicate requirement id: %r" % (entry["id"],))
        seen_ids.add(entry["id"])
        report.append(entry)
    return report


def missing_rod_report_entries(rod_assigned_ids, report):
    """Requirement ids present in rod_assigned_ids but absent from the
    report, in rod_assigned_ids order -- the clause 5.2.2.4 close-out
    completeness check (a requirement's absence from the report is not
    a pass)."""
    reported_ids = {entry["id"] for entry in report}
    return [rid for rid in rod_assigned_ids if rid not in reported_ids]


def is_rod_entry_closed(entry):
    """True when a report entry's rolled-up status is "compliant" and
    it carries no outstanding admissibility issue -- the only
    condition under which clause 5.2.2.4 review of design closes a
    requirement. False for non_compliant, open, NO_COMPLIANT_EVIDENCE_STATUS,
    or a compliant status with an unresolved admissibility issue."""
    return entry["status"] == "compliant" and not entry["admissibility_issues"]
