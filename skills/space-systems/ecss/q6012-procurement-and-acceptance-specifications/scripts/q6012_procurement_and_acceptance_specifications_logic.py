#!/usr/bin/env python3
"""Content of the buying document and its companion acceptance document.

Anchor: ECSS-Q-ST-60-12C clause 9. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Two documents are written together and neither works alone. The
procurement specification says what is being bought -- which die, on which
approved application, to which electrical limits, marked and delivered
how. The batch acceptance specification says how each delivered lot is
proved against that, with its lot definition, sampling, tests, sequence,
accept and reject criteria and data package.

The pair is checked as a pair. An item belongs to one document, except for
the few that both have to carry, which then have to say the same thing.
The buying document also has to point at the acceptance document it
invokes, otherwise the lot arrives with nothing that governs its testing.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PROCUREMENT_CONTENT_ITEMS = (
    "die-identification",
    "electrical-parameter-limits",
    "usage-condition-envelope",
    "approved-application-reference",
    "marking-and-traceability",
    "packing-and-handling",
    "acceptance-specification-reference",
    "nonconformance-handling",
)

ACCEPTANCE_CONTENT_ITEMS = (
    "die-identification",
    "lot-definition",
    "sampling-plan",
    "electrical-acceptance-tests",
    "environmental-acceptance-tests",
    "accept-reject-criteria",
    "acceptance-test-sequence",
    "data-package-content",
    "lot-rejection-handling",
)

# Items both documents may carry, and must then carry identically.
SHARED_CONTENT_ITEMS = (
    "die-identification",
    "electrical-parameter-limits",
    "usage-condition-envelope",
)

SPECIFICATION_SET_RELEASABLE = "specification-set-releasable"
SPECIFICATION_SET_INCOMPLETE = "specification-set-incomplete"

DEFAULT_SPECIFICATION_POLICY = {
    "min_sample_fraction": 0.05,
    "min_sample_count": 5,
    "max_accept_fraction": 0.1,
}

_CEIL_TOL = 1e-9


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_fraction(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if not 0.0 <= value < 1.0:
        raise ValueError("%s must sit in [0, 1), got %r" % (name, value))
    return float(value)


def _require_positive_int(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive integer, got %r" % (name, value))
    return value


def _require_non_negative_int(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a non-negative integer, got %r" % (name, value))
    return value


def is_stated(value):
    """Whether a content item actually says something.

    A heading with nothing under it is not content. An empty string, a
    whitespace string, an empty list or an absent value are all the same
    defect: the item is listed and unstated.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def validate_specification_policy(policy):
    """Check a sampling policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction("min_sample_fraction", policy.get("min_sample_fraction"))
    _require_fraction("max_accept_fraction", policy.get("max_accept_fraction"))
    _require_positive_int("min_sample_count", policy.get("min_sample_count"))
    return policy


def validate_document(document, label):
    """Normalise one specification document: an identifier and its content."""
    if not isinstance(document, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, document))
    document_id = document.get("document_id")
    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError("%s document_id must be a non-empty string" % label)
    content = document.get("content")
    if not isinstance(content, dict):
        raise ValueError("%s content must be a mapping" % label)
    for key in content:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("%s content has a non-string item name" % label)
    return {"document_id": document_id, "content": dict(content)}


def content_gaps(document, required_items, label):
    """Required items a document omits, and items it lists but never states."""
    normalised = validate_document(document, label)
    content = normalised["content"]
    absent = [item for item in required_items if item not in content]
    unstated = [
        item
        for item in required_items
        if item in content and not is_stated(content[item])
    ]
    return {"absent": absent, "unstated": unstated}


def misallocated_items(procurement, acceptance):
    """Items written into the document they do not belong to."""
    proc = validate_document(procurement, "procurement specification")
    acc = validate_document(acceptance, "acceptance specification")
    shared = set(SHARED_CONTENT_ITEMS)
    findings = []
    for item in ACCEPTANCE_CONTENT_ITEMS:
        if item not in shared and item in proc["content"]:
            findings.append(
                {"item": item, "found_in": "procurement", "belongs_to": "acceptance"}
            )
    for item in PROCUREMENT_CONTENT_ITEMS:
        if item not in shared and item in acc["content"]:
            findings.append(
                {"item": item, "found_in": "acceptance", "belongs_to": "procurement"}
            )
    return findings


def conflicting_shared_items(procurement, acceptance):
    """Shared items the two documents state differently."""
    proc = validate_document(procurement, "procurement specification")
    acc = validate_document(acceptance, "acceptance specification")
    conflicts = []
    for item in SHARED_CONTENT_ITEMS:
        if item in proc["content"] and item in acc["content"]:
            if proc["content"][item] != acc["content"][item]:
                conflicts.append(
                    {
                        "item": item,
                        "procurement_value": proc["content"][item],
                        "acceptance_value": acc["content"][item],
                    }
                )
    return conflicts


def cross_reference_findings(procurement, acceptance):
    """Whether the buying document actually invokes the acceptance document."""
    proc = validate_document(procurement, "procurement specification")
    acc = validate_document(acceptance, "acceptance specification")
    reference = proc["content"].get("acceptance-specification-reference")
    findings = []
    if not is_stated(reference):
        findings.append(
            "the procurement specification does not invoke an acceptance "
            "specification"
        )
    elif reference != acc["document_id"]:
        findings.append(
            "the procurement specification invokes %r but the acceptance "
            "specification supplied is %r" % (reference, acc["document_id"])
        )
    return findings


def required_sample_size(lot_size, policy=None):
    """Smallest sample a lot of this size may be accepted on."""
    policy = DEFAULT_SPECIFICATION_POLICY if policy is None else policy
    validate_specification_policy(policy)
    lot_size = _require_positive_int("lot_size", lot_size)
    proportional = math.ceil(lot_size * policy["min_sample_fraction"] - _CEIL_TOL)
    return min(lot_size, max(policy["min_sample_count"], proportional))


def validate_sampling_plan(plan):
    """Normalise a lot sampling plan, raising on an incoherent one."""
    if not isinstance(plan, dict):
        raise ValueError("sampling plan must be a mapping, got %r" % (plan,))
    lot_size = _require_positive_int("lot_size", plan.get("lot_size"))
    sample_size = _require_positive_int("sample_size", plan.get("sample_size"))
    accept_number = _require_non_negative_int(
        "accept_number", plan.get("accept_number")
    )
    if sample_size > lot_size:
        raise ValueError(
            "sample_size %d exceeds the lot size %d" % (sample_size, lot_size)
        )
    if accept_number >= sample_size:
        raise ValueError(
            "accept_number %d does not discriminate against a sample of %d"
            % (accept_number, sample_size)
        )
    return {
        "lot_size": lot_size,
        "sample_size": sample_size,
        "accept_number": accept_number,
        "sampling_fraction": sample_size / lot_size,
        "accept_fraction": accept_number / sample_size,
    }


def sampling_plan_findings(plan, policy=None):
    """Where a coherent sampling plan still falls short of the policy."""
    policy = DEFAULT_SPECIFICATION_POLICY if policy is None else policy
    validate_specification_policy(policy)
    normalised = validate_sampling_plan(plan)
    needed = required_sample_size(normalised["lot_size"], policy)
    findings = []
    if normalised["sample_size"] < needed:
        findings.append(
            "a lot of %d needs a sample of %d, the plan draws %d"
            % (normalised["lot_size"], needed, normalised["sample_size"])
        )
    if normalised["accept_fraction"] > policy["max_accept_fraction"] + _CEIL_TOL:
        findings.append(
            "the accept number allows %.3f of the sample to fail, above the "
            "policy ceiling %.3f"
            % (normalised["accept_fraction"], policy["max_accept_fraction"])
        )
    return findings


def assess_specification_set(case, policy=None):
    """Full clause 9 check of the buying and acceptance documents as a pair."""
    policy = DEFAULT_SPECIFICATION_POLICY if policy is None else policy
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    procurement = case.get("procurement")
    acceptance = case.get("acceptance")
    proc_gaps = content_gaps(
        procurement, PROCUREMENT_CONTENT_ITEMS, "procurement specification"
    )
    acc_gaps = content_gaps(
        acceptance, ACCEPTANCE_CONTENT_ITEMS, "acceptance specification"
    )
    misallocated = misallocated_items(procurement, acceptance)
    conflicts = conflicting_shared_items(procurement, acceptance)
    findings = list(cross_reference_findings(procurement, acceptance))
    for item in proc_gaps["absent"]:
        findings.append("the procurement specification omits %s" % item)
    for item in proc_gaps["unstated"]:
        findings.append("the procurement specification lists %s but states it as empty" % item)
    for item in acc_gaps["absent"]:
        findings.append("the acceptance specification omits %s" % item)
    for item in acc_gaps["unstated"]:
        findings.append("the acceptance specification lists %s but states it as empty" % item)
    for entry in misallocated:
        findings.append(
            "%s is written into the %s document but belongs to the %s document"
            % (entry["item"], entry["found_in"], entry["belongs_to"])
        )
    for entry in conflicts:
        findings.append(
            "%s is stated differently by the two documents" % entry["item"]
        )
    plan = case.get("sampling_plan")
    plan_summary = None
    if plan is None:
        findings.append("no lot sampling plan was supplied with the acceptance document")
    else:
        plan_summary = validate_sampling_plan(plan)
        findings.extend(sampling_plan_findings(plan, policy))
    total_required = len(PROCUREMENT_CONTENT_ITEMS) + len(ACCEPTANCE_CONTENT_ITEMS)
    missing = (
        len(proc_gaps["absent"])
        + len(proc_gaps["unstated"])
        + len(acc_gaps["absent"])
        + len(acc_gaps["unstated"])
    )
    return {
        "procurement_gaps": proc_gaps,
        "acceptance_gaps": acc_gaps,
        "misallocated_items": misallocated,
        "conflicting_items": conflicts,
        "sampling_plan": plan_summary,
        "completeness_fraction": (total_required - missing) / total_required,
        "findings": findings,
        "verdict": (
            SPECIFICATION_SET_RELEASABLE if not findings else SPECIFICATION_SET_INCOMPLETE
        ),
    }
