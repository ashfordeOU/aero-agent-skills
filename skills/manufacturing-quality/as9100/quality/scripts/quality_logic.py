#!/usr/bin/env python3
"""AS9100 aerospace quality management logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, as9100: gated):
AS9100 is the aviation, space, and defense QMS standard: ISO 9001:2015
plus aerospace clauses — operational risk, configuration management,
product safety, counterfeit prevention, external providers, and special
processes. Audits demonstrate the QMS against those clauses with
evidence artifacts; corrective action closes a nonconformance only
when containment, root cause, and corrective action are recorded.
"""

# Clause numbers and area names as listed in standards-map.yaml
# (applicability) — names, not verbatim clause text.
CLAUSE_BY_FOCUS = {
    "operational-risk": ("8.1.1", "operational risk"),
    "configuration-management": ("8.1.2", "configuration management"),
    "product-safety": ("8.1.3", "product safety"),
    "counterfeit-prevention": ("8.1.4", "counterfeit prevention"),
    "external-provider": ("8.4.1", "external providers"),
    "special-process": ("8.5.1.3", "special processes"),
}

# Minimum evidence artifact names per clause (paraphrase-level, common
# audit practice; confirm the exact evidence set with the organization's
# QMS documentation and the auditor's plan).
EVIDENCE_BY_FOCUS = {
    "operational-risk": [
        "risk register for products and projects",
        "risk treatment records",
    ],
    "configuration-management": [
        "configuration baseline records",
        "change control records",
    ],
    "product-safety": [
        "product safety plan",
        "safety escalation and reporting records",
    ],
    "counterfeit-prevention": [
        "counterfeit prevention procedure",
        "supplier counterfeit declarations",
        "suspect-part quarantine records",
    ],
    "external-provider": [
        "approved supplier list",
        "purchase order requirements flow-down",
        "supplier performance records",
    ],
    "special-process": [
        "special process approvals",
        "operator and equipment qualifications",
    ],
}


def scope_clause(focus):
    """Map an audit focus area to its AS9100 aerospace clause."""
    if focus not in CLAUSE_BY_FOCUS:
        raise ValueError("unknown audit focus: %r" % (focus,))
    return CLAUSE_BY_FOCUS[focus]


def audit_evidence_required(focus):
    """Minimum evidence artifacts expected for an audit of that clause."""
    if focus not in EVIDENCE_BY_FOCUS:
        raise ValueError("unknown audit focus: %r" % (focus,))
    return list(EVIDENCE_BY_FOCUS[focus])


def corrective_action_closure(
    nonconformance, containment, root_cause, corrective_action
):
    """A nonconformance closes only when the record carries the
    nonconformance itself, containment, a root cause, and a corrective
    action (paraphrase of the corrective-action discipline)."""
    required = (nonconformance, containment, root_cause, corrective_action)
    return all(isinstance(v, str) and v.strip() for v in required)
