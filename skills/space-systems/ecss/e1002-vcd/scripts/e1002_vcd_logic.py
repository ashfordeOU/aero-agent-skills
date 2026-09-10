#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.8.2 and Annex B Verification Control
Document (VCD) logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
VCD is the single record that carries every requirement's verification
method, its applicability, and its closure status through to
completion. Each VCD row records the verification method assigned to
its requirement (review of design, analysis, inspection, test), the
requirement's category (which constrains which methods are permitted),
whether the requirement is applicable to the product under
verification, and a status that must reach "closed" with recorded
closure evidence before the requirement is verified. This module
implements the method-permission check, the applicability-rationale
and applicability/status consistency rules, the closure-evidence
completeness check, and the program-level status roll-up; it does not
define the verification methods themselves (see the method-specific
leaves) or the initial method/level assignment step (see
e10-req-verif-methods).
"""

VERIFICATION_METHODS = frozenset(
    {"review_of_design", "analysis", "inspection", "test"}
)

VERIFICATION_STATUSES = frozenset(
    {"open", "planned", "in_progress", "closed", "not_applicable"}
)

REQUIREMENT_CATEGORIES = frozenset(
    {"functional", "performance", "interface", "safety", "design_constraint"}
)

# Verification methods permitted to close out a requirement of a given
# category. A design_constraint may close on paper (review of design)
# or a documented physical check (inspection); every other category
# must close on a measured or modelled result (test/analysis) because
# review of design and inspection alone do not demonstrate behaviour.
ALLOWED_METHODS_BY_CATEGORY = {
    "functional": frozenset({"test", "analysis"}),
    "performance": frozenset({"test", "analysis"}),
    "interface": frozenset({"inspection", "test", "analysis"}),
    "safety": frozenset({"test", "analysis"}),
    "design_constraint": frozenset({"review_of_design", "inspection", "analysis"}),
}

REQUIRED_ENTRY_FIELDS = ("requirement_id", "category", "method", "applicable", "status")


def validate_verification_method(method):
    """Returns method if it is one of VERIFICATION_METHODS, else raises
    ValueError."""
    if method not in VERIFICATION_METHODS:
        raise ValueError(
            "unrecognized verification method %r under E-ST-10-02C "
            "clause 5.2.8.2" % (method,)
        )
    return method


def validate_verification_status(status):
    """Returns status if it is one of VERIFICATION_STATUSES, else
    raises ValueError."""
    if status not in VERIFICATION_STATUSES:
        raise ValueError("unrecognized VCD status %r" % (status,))
    return status


def allowed_methods_for_category(category):
    """Frozenset of verification methods permitted to close a
    requirement of this category. Raises ValueError for an
    unrecognized category."""
    if category not in REQUIREMENT_CATEGORIES:
        raise ValueError("unrecognized requirement category %r" % (category,))
    return ALLOWED_METHODS_BY_CATEGORY[category]


def method_selection_issues(requirement_id, category, method):
    """Issue list (empty if the recorded method is permitted) for one
    requirement's category/method pair. Raises ValueError if method or
    category is not recognized."""
    validate_verification_method(method)
    allowed = allowed_methods_for_category(category)
    if method not in allowed:
        return [
            {
                "issue": "method_not_permitted_for_category",
                "requirement_id": requirement_id,
                "category": category,
                "method": method,
                "allowed_methods": sorted(allowed),
            }
        ]
    return []


def applicability_issues(requirement_id, applicable, status, rationale):
    """Issue list (empty if consistent) checking that a requirement
    marked not applicable carries a rationale, and that applicability
    and status agree: applicable False must pair with status
    "not_applicable", and status "not_applicable" must pair with
    applicable False. Raises ValueError for an unrecognized status."""
    validate_verification_status(status)
    issues = []
    if not applicable and not rationale:
        issues.append(
            {
                "issue": "missing_applicability_rationale",
                "requirement_id": requirement_id,
            }
        )
    status_says_not_applicable = status == "not_applicable"
    if applicable == status_says_not_applicable:
        issues.append(
            {
                "issue": "applicability_status_mismatch",
                "requirement_id": requirement_id,
                "applicable": applicable,
                "status": status,
            }
        )
    return issues


def closure_issues(requirement_id, status, closure_evidence_ref):
    """Issue list (empty if consistent) checking that a "closed" status
    carries a non-empty closure_evidence_ref. Raises ValueError for an
    unrecognized status."""
    validate_verification_status(status)
    if status == "closed" and not closure_evidence_ref:
        return [
            {
                "issue": "missing_closure_evidence",
                "requirement_id": requirement_id,
            }
        ]
    return []


def evaluate_vcd_entry(entry):
    """Full clause 5.2.8.2 / Annex B row check for one VCD entry.

    entry: {"requirement_id": str, "category": str, "method": str,
    "applicable": bool, "status": str, "rationale": str | None,
    "closure_evidence_ref": str | None}. Returns {"method_selection":
    [...], "applicability": [...], "closure": [...]}, each an issue
    list. Raises ValueError for a missing required field or an
    unrecognized method/category/status."""
    missing = [field for field in REQUIRED_ENTRY_FIELDS if field not in entry]
    if missing:
        raise ValueError(
            "VCD entry missing required field(s): %s" % ", ".join(missing)
        )
    requirement_id = entry["requirement_id"]
    return {
        "method_selection": method_selection_issues(
            requirement_id, entry["category"], entry["method"]
        ),
        "applicability": applicability_issues(
            requirement_id,
            entry["applicable"],
            entry["status"],
            entry.get("rationale"),
        ),
        "closure": closure_issues(
            requirement_id, entry["status"], entry.get("closure_evidence_ref")
        ),
    }


def is_entry_clean(evaluation):
    """True when every issue list in an evaluate_vcd_entry result is
    empty."""
    return all(len(issues) == 0 for issues in evaluation.values())


def vcd_status_rollup(entries):
    """Program-level status roll-up across a non-empty list of VCD
    entries. Returns {"total": int, "applicable_total": int,
    "closed_count": int, "by_status": {status: count, ...},
    "percent_complete": float}. percent_complete is closed_count /
    applicable_total * 100, or 100.0 when applicable_total is zero
    (nothing applicable left to close). Raises ValueError for an empty
    list or an unrecognized status."""
    if not entries:
        raise ValueError("vcd_status_rollup requires at least one entry")
    by_status = {status: 0 for status in VERIFICATION_STATUSES}
    for entry in entries:
        status = validate_verification_status(entry["status"])
        by_status[status] += 1
    total = len(entries)
    applicable_total = total - by_status["not_applicable"]
    closed_count = by_status["closed"]
    percent_complete = (
        100.0 if applicable_total == 0 else (closed_count / applicable_total) * 100.0
    )
    return {
        "total": total,
        "applicable_total": applicable_total,
        "closed_count": closed_count,
        "by_status": by_status,
        "percent_complete": percent_complete,
    }


def is_vcd_complete(rollup):
    """True when every applicable entry in a vcd_status_rollup result
    has reached "closed" -- percent_complete is 100.0."""
    return rollup["percent_complete"] >= 100.0


def vcd_program_review(entries):
    """Full VCD review across a non-empty list of entries: per-entry
    issues from evaluate_vcd_entry keyed by requirement_id, the status
    roll-up, and an overall "compliant" flag that is True only when
    every entry is clean and is_vcd_complete holds. Raises ValueError
    for an empty list or a malformed/unrecognized entry."""
    evaluations = {}
    for entry in entries:
        evaluations[entry["requirement_id"]] = evaluate_vcd_entry(entry)
    rollup = vcd_status_rollup(entries)
    all_clean = all(is_entry_clean(evaluation) for evaluation in evaluations.values())
    return {
        "evaluations": evaluations,
        "rollup": rollup,
        "compliant": all_clean and is_vcd_complete(rollup),
    }
