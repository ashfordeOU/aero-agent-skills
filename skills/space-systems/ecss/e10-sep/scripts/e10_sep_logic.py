#!/usr/bin/env python3
"""ECSS-E-ST-10C §5.1 system engineering plan (SEP) logic (paraphrase).

Pure stdlib, no network. Unit conventions: this module carries no
physical units; its inputs are string enums and version tags. Lower-
level plan types are one of product-assurance-plan, aiv-plan,
risk-management-plan, configuration-management-plan,
software-management-plan. Review gates are one of MDR, PRR, SRR, PDR,
CDR, QR, AR, FRR, CRR, ER. Unknown plan types, review gates, or
maintenance-trigger events raise ValueError.

This module is a deterministic paraphrase of ECSS-E-ST-10C clause 5.1
practice: the SEP is produced once and then maintained across the
project lifecycle, every lower-level plan must stay baseline-consistent
with the SEP, and the SE function assembles a defined support package
from the SEP to back the project manager (PM) at each review gate.
"""

LOWER_LEVEL_PLANS = {
    "product-assurance-plan",
    "aiv-plan",
    "risk-management-plan",
    "configuration-management-plan",
    "software-management-plan",
}

MAINTENANCE_TRIGGERS = {
    "phase-transition": True,
    "requirements-baseline-change": True,
    "review-gate-approaching": True,
    "organization-change": True,
    "routine-status-report": False,
}

REVIEW_GATES = {"MDR", "PRR", "SRR", "PDR", "CDR", "QR", "AR", "FRR", "CRR", "ER"}

CORE_SUPPORT_ITEMS = [
    "SE task status vs. SEP plan",
    "WBS and schedule status",
    "risk register status",
    "organisation and interface status",
]

GATE_EXTRA_ITEMS = {
    "MDR": ["mission feasibility SE approach"],
    "PRR": ["preliminary requirement baseline status"],
    "SRR": ["system requirement baseline status"],
    "PDR": ["design baseline consistency with SEP"],
    "CDR": ["design baseline consistency with SEP", "AIV plan consistency with SEP"],
    "QR": ["verification closure status"],
    "AR": ["verification closure status", "acceptance data package status"],
    "FRR": ["verification closure status", "operational readiness status"],
    "CRR": ["operations handover status"],
    "ER": ["disposal plan consistency with SEP"],
}


def sep_maintenance_trigger(event):
    """Return whether a lifecycle event requires the SEP to be updated.

    Accepts phase-transition, requirements-baseline-change,
    review-gate-approaching, organization-change, and
    routine-status-report (case-insensitive). Unknown events raise
    ValueError. Returns a bool: True when the SEP must be revised and
    rebaselined before the event closes.
    """
    if not isinstance(event, str):
        raise ValueError("event must be a string, got %r" % (event,))
    key = event.strip().lower()
    if key not in MAINTENANCE_TRIGGERS:
        raise ValueError(
            "unknown maintenance-trigger event %r; expected one of %s"
            % (event, ", ".join(sorted(MAINTENANCE_TRIGGERS)))
        )
    return MAINTENANCE_TRIGGERS[key]


def lower_plan_consistency(plan_type, sep_baseline, plan_baseline):
    """Return the consistency verdict for a lower-level plan vs. the SEP.

    plan_type must be one of LOWER_LEVEL_PLANS (case-insensitive).
    sep_baseline and plan_baseline are the baseline tags each plan was
    last issued against. Returns a dict with 'plan_type', 'consistent'
    (bool), and 'status' ('consistent' when the tags match, otherwise
    'inconsistent-update-required'). Unknown plan types raise
    ValueError.
    """
    if not isinstance(plan_type, str):
        raise ValueError("plan_type must be a string, got %r" % (plan_type,))
    key = plan_type.strip().lower()
    if key not in LOWER_LEVEL_PLANS:
        raise ValueError(
            "unknown lower-level plan type %r; expected one of %s"
            % (plan_type, ", ".join(sorted(LOWER_LEVEL_PLANS)))
        )
    consistent = sep_baseline == plan_baseline
    return {
        "plan_type": key,
        "consistent": consistent,
        "status": "consistent" if consistent else "inconsistent-update-required",
    }


def review_support_package(review_gate):
    """Return the SEP-derived support items for a project review gate.

    Accepts MDR, PRR, SRR, PDR, CDR, QR, AR, FRR, CRR, ER
    (case-insensitive). Unknown gates raise ValueError. Returns a fresh
    list combining the core support items every review needs from the
    SEP plus the items specific to that gate.
    """
    if not isinstance(review_gate, str):
        raise ValueError("review_gate must be a string, got %r" % (review_gate,))
    key = review_gate.strip().upper()
    if key not in REVIEW_GATES:
        raise ValueError(
            "unknown review gate %r; expected one of %s"
            % (review_gate, ", ".join(sorted(REVIEW_GATES)))
        )
    return list(CORE_SUPPORT_ITEMS) + list(GATE_EXTRA_ITEMS[key])


def sep_status_verdict(sep_baseline, plans, review_gate):
    """Build the SEP status verdict for a set of lower-level plans and a gate.

    plans is a non-empty list of (plan_type, plan_baseline) pairs.
    Returns a dict with 'plan_verdicts' (per-plan consistency verdicts),
    'support_package' (the review_support_package for review_gate), and
    'status' ('sep-consistent' when every plan is consistent with
    sep_baseline, otherwise 'sep-update-required'). Empty or malformed
    plans raise ValueError.
    """
    if not isinstance(plans, list) or not plans:
        raise ValueError(
            "plans must be a non-empty list of (plan_type, plan_baseline) pairs"
        )
    plan_verdicts = []
    for entry in plans:
        if not isinstance(entry, (tuple, list)) or len(entry) != 2:
            raise ValueError(
                "each plan entry must be a (plan_type, plan_baseline) pair, got %r"
                % (entry,)
            )
        plan_type, plan_baseline = entry
        plan_verdicts.append(
            lower_plan_consistency(plan_type, sep_baseline, plan_baseline)
        )
    support_package = review_support_package(review_gate)
    all_consistent = all(v["consistent"] for v in plan_verdicts)
    return {
        "plan_verdicts": plan_verdicts,
        "support_package": support_package,
        "status": "sep-consistent" if all_consistent else "sep-update-required",
    }


if __name__ == "__main__":
    import doctest

    doctest.testmod()
