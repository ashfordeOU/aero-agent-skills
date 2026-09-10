#!/usr/bin/env python3
"""ECSS-E-ST-10C pre-tailoring matrix (clause 7) (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
E-ST-10C clause 7 pre-tailors the standard's clause-5 requirements by
space product type (e.g. space segment, ground segment, launch service
segment) before a project runs its own project-specific tailoring pass
under ECSS-S-ST-00-01. A pre-tailoring matrix maps each clause id to a
status per product type: applicable (mandatory), optional (a project
decision, recorded elsewhere), or not_applicable (excluded). This
module validates such a matrix, resolves applicability for a declared
product type, and checks a project's carried-forward requirement
clauses against the resolved sets. It does not perform the further
project-specific tailoring step itself (see the sibling project
tailoring leaf) and does not record the rationale behind optional-
clause decisions.
"""

APPLICABILITY_STATUSES = ("applicable", "optional", "not_applicable")


def validate_pretailoring_matrix(matrix, product_types):
    """Validate a pre-tailoring matrix. matrix is a dict of clause id ->
    dict of product_type -> status. product_types is an iterable of the
    product type names expected to be covered by every clause. Returns
    a dict of clause id -> list of problems; a clause with no problems
    is absent from the returned dict."""
    expected_types = set(product_types)
    report = {}
    for clause_id, entry in matrix.items():
        problems = []
        entry_types = set(entry)
        missing_types = expected_types - entry_types
        for product_type in sorted(missing_types):
            problems.append("missing product type: %s" % product_type)
        unknown_types = entry_types - expected_types
        for product_type in sorted(unknown_types):
            problems.append("unrecognised product type: %r" % (product_type,))
        for product_type, status in entry.items():
            if status not in APPLICABILITY_STATUSES:
                problems.append(
                    "invalid status for %r: %r" % (product_type, status)
                )
        if problems:
            report[clause_id] = problems
    return report


def resolve_applicability(matrix, product_type):
    """Resolve the status of every clause in matrix for one declared
    product_type. Returns a dict of clause id -> status, including only
    clauses whose entry defines a status for product_type."""
    resolved = {}
    for clause_id, entry in matrix.items():
        if product_type in entry:
            resolved[clause_id] = entry[product_type]
    return resolved


def clauses_with_status(matrix, product_type, status):
    """Sorted list of clause ids resolved to status for product_type."""
    resolved = resolve_applicability(matrix, product_type)
    return sorted(
        clause_id for clause_id, clause_status in resolved.items()
        if clause_status == status
    )


def check_pretailoring_compliance(matrix, product_type, referenced_clause_ids):
    """Check a project's carried-forward requirement clause ids against
    the matrix resolved for product_type. referenced_clause_ids is an
    iterable of clause ids the project intends to carry into
    project-specific tailoring. Returns a dict with three sorted lists:
    'missing_mandatory' (applicable clauses with no carried-forward
    requirement), 'out_of_scope' (carried-forward clauses that resolve
    to not_applicable), and 'unknown_clauses' (carried-forward clause
    ids absent from the matrix). Optional clauses are never flagged
    either way."""
    resolved = resolve_applicability(matrix, product_type)
    referenced = set(referenced_clause_ids)

    mandatory = {
        clause_id for clause_id, status in resolved.items()
        if status == "applicable"
    }
    missing_mandatory = sorted(mandatory - referenced)

    out_of_scope = sorted(
        clause_id for clause_id in referenced
        if resolved.get(clause_id) == "not_applicable"
    )

    unknown_clauses = sorted(clause_id for clause_id in referenced if clause_id not in resolved)

    return {
        "missing_mandatory": missing_mandatory,
        "out_of_scope": out_of_scope,
        "unknown_clauses": unknown_clauses,
    }


def is_ready_for_project_tailoring(compliance_report):
    """A pre-tailoring pass is ready to hand off to project-specific
    tailoring only when compliance_report (as returned by
    check_pretailoring_compliance) has no missing mandatory clauses, no
    out-of-scope clauses, and no unknown clauses."""
    return not (
        compliance_report["missing_mandatory"]
        or compliance_report["out_of_scope"]
        or compliance_report["unknown_clauses"]
    )
