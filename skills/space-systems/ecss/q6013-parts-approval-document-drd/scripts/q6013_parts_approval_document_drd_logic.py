#!/usr/bin/env python3
"""Content of the parts approval document put to the customer.

Anchor: ECSS-Q-ST-60-13C Annex D, the data item fixing what the parts
approval document has to contain when a commercial part is submitted for
customer agreement before it may be procured. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The document is a request, not a report: it asks the customer to accept
a part the standard would otherwise not permit. Four things follow.

A required block with no reference behind it is not submitted. The part
identity, the intended application and quantity, the operating
environment, the evaluation evidence, the radiation evidence, the
reliability basis, the risk assessment, the mitigation and the
procurement and traceability plan each have to point at something a
reviewer can read.

Evidence is weighed, not counted. Each block carries a strength between
nothing and complete, and the submission's evidence strength is the
weighted mean of the blocks that bear evidence, so a thorough radiation
campaign does not pay for an absent reliability basis.

The bar moves with the risk. The application criticality and the
environment severity combine into a risk index, and the evidence the
submission has to reach rises with that index: the same evidence that
approves a part in a benign housekeeping circuit does not approve it on
a single-string critical function.

A shortfall the mitigation closes is a condition, not a refusal. A
submission short of the bar but carrying a mitigation the customer can
check earns a conditional recommendation, which is the answer the data
item exists to make possible.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PART_IDENTITY_AND_MANUFACTURER = "part-identity-and-manufacturer"
INTENDED_APPLICATION_AND_QUANTITY = "intended-application-and-quantity"
OPERATING_ENVIRONMENT_AND_PROFILE = "operating-environment-and-mission-profile"
EVALUATION_AND_TEST_EVIDENCE = "evaluation-and-test-evidence"
RADIATION_EVIDENCE = "radiation-evidence"
RELIABILITY_AND_FAILURE_RATE_BASIS = "reliability-and-failure-rate-basis"
RISK_ASSESSMENT = "risk-assessment"
MITIGATION_AND_CONTROLS = "mitigation-and-controls"
PROCUREMENT_AND_TRACEABILITY_PLAN = "procurement-and-traceability-plan"

REQUIRED_CONTENT_BLOCKS = (
    PART_IDENTITY_AND_MANUFACTURER,
    INTENDED_APPLICATION_AND_QUANTITY,
    OPERATING_ENVIRONMENT_AND_PROFILE,
    EVALUATION_AND_TEST_EVIDENCE,
    RADIATION_EVIDENCE,
    RELIABILITY_AND_FAILURE_RATE_BASIS,
    RISK_ASSESSMENT,
    MITIGATION_AND_CONTROLS,
    PROCUREMENT_AND_TRACEABILITY_PLAN,
)

EVIDENCE_BEARING_BLOCKS = {
    EVALUATION_AND_TEST_EVIDENCE: 3.0,
    RADIATION_EVIDENCE: 3.0,
    RELIABILITY_AND_FAILURE_RATE_BASIS: 2.0,
    RISK_ASSESSMENT: 1.0,
}

CRITICALITY_HOUSEKEEPING = "housekeeping-function"
CRITICALITY_REDUNDANT_PAYLOAD = "redundant-payload-function"
CRITICALITY_SINGLE_STRING_PAYLOAD = "single-string-payload-function"
CRITICALITY_MISSION_CRITICAL = "mission-critical-function"

CRITICALITY_WEIGHTS = {
    CRITICALITY_HOUSEKEEPING: 0.4,
    CRITICALITY_REDUNDANT_PAYLOAD: 0.6,
    CRITICALITY_SINGLE_STRING_PAYLOAD: 0.8,
    CRITICALITY_MISSION_CRITICAL: 1.0,
}

ENVIRONMENT_BENIGN = "pressurised-benign"
ENVIRONMENT_LOW_EARTH_ORBIT = "low-earth-orbit"
ENVIRONMENT_GEOSTATIONARY = "geostationary-orbit"
ENVIRONMENT_DEEP_SPACE = "deep-space-or-high-dose"

ENVIRONMENT_WEIGHTS = {
    ENVIRONMENT_BENIGN: 0.4,
    ENVIRONMENT_LOW_EARTH_ORBIT: 0.6,
    ENVIRONMENT_GEOSTATIONARY: 0.8,
    ENVIRONMENT_DEEP_SPACE: 1.0,
}

DOCUMENT_NOT_SUBMITTED = "parts-approval-document-not-submitted"
CONTENT_COVERAGE_SHORT = "parts-approval-document-content-coverage-short"
EVIDENCE_INSUFFICIENT_FOR_RISK = "parts-approval-document-evidence-insufficient"
MITIGATION_NOT_PROPOSED = "parts-approval-document-mitigation-not-proposed"
APPROVAL_RECOMMENDED_WITH_CONDITIONS = "parts-approval-recommended-with-conditions"
APPROVAL_RECOMMENDED = "parts-approval-recommended"

DEFAULT_APPROVAL_DRD_POLICY = {
    "min_content_coverage": 1.0,
    "base_required_evidence": 0.45,
    "risk_evidence_span": 0.5,
    "conditional_shortfall_allowance": 0.15,
    "require_mitigation_when_short": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_approval_drd_policy(policy):
    """Check the data-item policy the submission is graded against."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    base = _require_fraction("base_required_evidence", policy.get("base_required_evidence"))
    span = _require_fraction("risk_evidence_span", policy.get("risk_evidence_span"))
    if base + span > 1.0:
        raise ValueError(
            "base_required_evidence %g plus risk_evidence_span %g demands more "
            "evidence than complete, so no submission could pass" % (base, span)
        )
    _require_fraction("min_content_coverage", policy.get("min_content_coverage"))
    _require_fraction(
        "conditional_shortfall_allowance",
        policy.get("conditional_shortfall_allowance"),
    )
    _require_flag(
        "require_mitigation_when_short", policy.get("require_mitigation_when_short")
    )
    return policy


def validate_submission_identity(submission):
    """Check the submission names a part, a document and an application."""
    if not isinstance(submission, dict):
        raise ValueError("submission must be a mapping, got %r" % (submission,))
    criticality = _require_label(
        "application_criticality", submission.get("application_criticality")
    )
    if criticality not in CRITICALITY_WEIGHTS:
        raise ValueError(
            "unrecognised application criticality %r; the categories are fixed"
            % criticality
        )
    environment = _require_label(
        "operating_environment", submission.get("operating_environment")
    )
    if environment not in ENVIRONMENT_WEIGHTS:
        raise ValueError(
            "unrecognised operating environment %r; the categories are fixed"
            % environment
        )
    return {
        "document_reference": _require_label(
            "document_reference", submission.get("document_reference")
        ),
        "issue": _require_label("issue", submission.get("issue")),
        "part_identifier": _require_label(
            "part_identifier", submission.get("part_identifier", "")
        ),
        "application_criticality": criticality,
        "operating_environment": environment,
    }


def validate_block_record(block):
    """Read one content block: present, referenced, and how strong it is."""
    if not isinstance(block, dict):
        raise ValueError("block must be a mapping, got %r" % (block,))
    name = _require_label("block", block.get("block"))
    if name not in REQUIRED_CONTENT_BLOCKS:
        raise ValueError(
            "unrecognised content block %r; the data item fixes the block names"
            % name
        )
    return {
        "block": name,
        "present": _require_flag("present on %s" % name, block.get("present")),
        "evidence_reference": _require_label(
            "evidence_reference on %s" % name, block.get("evidence_reference", "")
        ),
        "strength": _require_fraction(
            "strength on %s" % name, block.get("strength", 0.0)
        ),
    }


def validate_blocks(blocks):
    """Read every declared block, refusing a block declared twice."""
    if not isinstance(blocks, (list, tuple)):
        raise ValueError("blocks must be a sequence of block records")
    checked = []
    seen = set()
    for block in blocks:
        record = validate_block_record(block)
        if record["block"] in seen:
            raise ValueError("content block %r is declared twice" % record["block"])
        seen.add(record["block"])
        checked.append(record)
    return tuple(checked)


def block_index(blocks):
    """Map each declared block name to its record."""
    return {record["block"]: record for record in validate_blocks(blocks)}


def block_is_supported(record):
    """True when a block is present and points at something readable."""
    checked = validate_block_record(record)
    return checked["present"] and bool(checked["evidence_reference"])


def absent_blocks(blocks):
    """Required blocks the submission does not carry at all."""
    declared = block_index(blocks)
    return tuple(name for name in REQUIRED_CONTENT_BLOCKS if name not in declared)


def unsupported_blocks(blocks):
    """Declared blocks that are absent in fact or point at nothing."""
    return tuple(
        record["block"]
        for record in validate_blocks(blocks)
        if not block_is_supported(record)
    )


def content_coverage(blocks):
    """Share of the required blocks that are present and referenced."""
    declared = block_index(blocks)
    supported = sum(
        1
        for name in REQUIRED_CONTENT_BLOCKS
        if name in declared and block_is_supported(declared[name])
    )
    return supported / float(len(REQUIRED_CONTENT_BLOCKS))


def risk_index(identity):
    """Combine application criticality and environment severity into a risk."""
    criticality = CRITICALITY_WEIGHTS[identity["application_criticality"]]
    environment = ENVIRONMENT_WEIGHTS[identity["operating_environment"]]
    return criticality * environment


def required_evidence_strength(identity, policy=None):
    """Evidence the submission has to reach for the risk it carries."""
    policy = validate_approval_drd_policy(policy or DEFAULT_APPROVAL_DRD_POLICY)
    base = float(policy["base_required_evidence"])
    span = float(policy["risk_evidence_span"])
    return base + span * risk_index(identity)


def evidence_strength(blocks):
    """Weighted mean strength of the blocks that bear evidence."""
    declared = block_index(blocks)
    total_weight = 0.0
    weighted = 0.0
    for name, weight in EVIDENCE_BEARING_BLOCKS.items():
        total_weight += weight
        record = declared.get(name)
        if record is None or not block_is_supported(record):
            continue
        weighted += weight * record["strength"]
    if total_weight == 0.0:
        return 0.0
    return weighted / total_weight


def evidence_shortfall(blocks, identity, policy=None):
    """How far the held evidence falls below what the risk demands."""
    policy = validate_approval_drd_policy(policy or DEFAULT_APPROVAL_DRD_POLICY)
    required = required_evidence_strength(identity, policy)
    held = evidence_strength(blocks)
    if _at_least(held, required):
        return 0.0
    return required - held


def mitigation_is_proposed(blocks):
    """True when the submission carries a mitigation a reviewer can check."""
    declared = block_index(blocks)
    record = declared.get(MITIGATION_AND_CONTROLS)
    if record is None or not block_is_supported(record):
        return False
    return record["strength"] > 0.0


def assess_parts_approval_document_drd(case):
    """Grade a parts approval submission against its Annex D data item."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    policy = validate_approval_drd_policy(
        case.get("policy") or DEFAULT_APPROVAL_DRD_POLICY
    )

    findings = []
    advisories = []
    result = {
        "document_reference": None,
        "issue": None,
        "part_identifier": None,
        "content_coverage": 0.0,
        "absent_blocks": (),
        "unsupported_blocks": (),
        "risk_index": None,
        "required_evidence_strength": None,
        "evidence_strength": None,
        "evidence_shortfall": None,
        "mitigation_proposed": False,
        "verdict": None,
        "findings": findings,
        "advisories": advisories,
    }

    submission = case.get("submission")
    if submission is None:
        findings.append(
            "no parts approval document is submitted, so the customer has "
            "been asked to agree to nothing in particular"
        )
        result["verdict"] = DOCUMENT_NOT_SUBMITTED
        return result

    identity = validate_submission_identity(submission)
    result["document_reference"] = identity["document_reference"]
    result["issue"] = identity["issue"]
    result["part_identifier"] = identity["part_identifier"]
    if not identity["document_reference"] or not identity["issue"]:
        findings.append(
            "the submission carries no reference or no issue label, so no "
            "agreement could be recorded against it"
        )
        result["verdict"] = DOCUMENT_NOT_SUBMITTED
        return result

    blocks = submission.get("content_blocks")
    if blocks is None:
        raise ValueError("the submission declares no content_blocks to assess")
    checked = validate_blocks(blocks)

    coverage = content_coverage(checked)
    absent = absent_blocks(checked)
    unsupported = unsupported_blocks(checked)
    index = risk_index(identity)
    required = required_evidence_strength(identity, policy)
    held = evidence_strength(checked)
    shortfall = evidence_shortfall(checked, identity, policy)
    mitigation = mitigation_is_proposed(checked)

    result["content_coverage"] = coverage
    result["absent_blocks"] = absent
    result["unsupported_blocks"] = unsupported
    result["risk_index"] = index
    result["required_evidence_strength"] = required
    result["evidence_strength"] = held
    result["evidence_shortfall"] = shortfall
    result["mitigation_proposed"] = mitigation

    for name in absent:
        findings.append("the submission has no %s block at all" % name)
    for name in unsupported:
        findings.append(
            "the submission opens a %s block that is absent in fact or points "
            "at nothing a reviewer can read" % name
        )

    if not _at_least(coverage, float(policy["min_content_coverage"])):
        findings.append(
            "content coverage is %.3g per cent against the %.3g per cent the "
            "data item demands"
            % (coverage * 100.0, float(policy["min_content_coverage"]) * 100.0)
        )
        result["verdict"] = CONTENT_COVERAGE_SHORT
        return result

    if shortfall <= 0.0:
        result["verdict"] = APPROVAL_RECOMMENDED
        return result

    allowance = float(policy["conditional_shortfall_allowance"])
    if not _at_most(shortfall, allowance):
        findings.append(
            "evidence strength %.3g falls %.3g below the %.3g the risk index "
            "%.3g demands, further than a condition can close"
            % (held, shortfall, required, index)
        )
        result["verdict"] = EVIDENCE_INSUFFICIENT_FOR_RISK
        return result

    if policy["require_mitigation_when_short"] and not mitigation:
        findings.append(
            "evidence strength %.3g falls %.3g short and the submission "
            "proposes no mitigation the customer could attach a condition to"
            % (held, shortfall)
        )
        result["verdict"] = MITIGATION_NOT_PROPOSED
        return result

    advisories.append(
        "evidence strength %.3g falls %.3g short of the %.3g the risk demands; "
        "the mitigation is the condition of the agreement"
        % (held, shortfall, required)
    )
    result["verdict"] = APPROVAL_RECOMMENDED_WITH_CONDITIONS
    return result
