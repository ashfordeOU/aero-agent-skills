#!/usr/bin/env python3
"""Content of the nonconformance report, and the board that has to see it.

Anchor: ECSS-Q-ST-10-09 Annex A, the normative data item fixing what a
nonconformance report carries: the blocks every report holds, the extra
blocks the proposed disposition path brings with it, and whether the
report is settled by the internal review board or has to be put to the
customer board. The procedure below is a paraphrase into implementable
steps; no standard text is reproduced.

Four things follow from what the report is for.

The report is filled in stages, not at once. At raising it has to say
what was found, on what item, against which requirement and in what
category; at the board it has to add the cause, the proposed disposition
and the justification; at closure it has to add the implementation and
verification record and the closing authority. Grading a report at
raising against the closure blocks refuses every honest report.

The disposition path brings its own blocks. Accepting an item as it
stands and repairing it both leave the product off the requirement, so
each owes a technical justification and a statement of the effect on
interfaces and lifetime; rework owes its procedure and the reinspection
that followed; scrap owes the authorisation and the segregation record;
a return owes the supplier authorisation and the request raised on them.

The board follows the content, not the habit. A major nonconformance, a
safety effect, or a disposition that leaves the product off the
requirement puts the report to the customer board; everything else is
settled internally. The routing is derived from the report, so it cannot
be quietly downgraded.

A customer board leaves a trace. A report closed on a customer route
with no recorded customer approval is not closed, whatever its status
field says.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

NCR_IDENTIFIER_AND_DATE = "nonconformance-identifier-and-raising-date"
AFFECTED_ITEM_AND_CONFIGURATION = "affected-item-and-configuration-status"
DESCRIPTION_AND_DETECTION_POINT = "nonconformance-description-and-detection-point"
REQUIREMENT_NOT_MET = "requirement-not-met"
CATEGORY_AND_SAFETY_EFFECT = "category-and-safety-effect"
CAUSE_ANALYSIS = "cause-analysis"
PROPOSED_DISPOSITION = "proposed-disposition"
DISPOSITION_JUSTIFICATION = "disposition-justification"
IMPLEMENTATION_AND_VERIFICATION = "implementation-and-verification-record"
CLOSURE_AUTHORITY_AND_DATE = "closure-authority-and-date"
CUSTOMER_APPROVAL_RECORD = "customer-approval-record"

ACCEPTANCE_TECHNICAL_JUSTIFICATION = "acceptance-technical-justification"
EFFECT_ON_INTERFACES_AND_LIFETIME = "effect-on-interfaces-and-lifetime"
REPAIR_PROCEDURE_REFERENCE = "repair-procedure-reference"
REPAIR_REQUALIFICATION_EVIDENCE = "repair-requalification-evidence"
REWORK_PROCEDURE_REFERENCE = "rework-procedure-reference"
REINSPECTION_AND_RETEST_RECORD = "reinspection-and-retest-record"
SCRAP_AUTHORISATION_AND_SEGREGATION = "scrap-authorisation-and-segregation-record"
SUPPLIER_RETURN_AUTHORISATION = "supplier-return-authorisation"
SUPPLIER_CORRECTIVE_ACTION_REQUEST = "supplier-corrective-action-request-reference"

STAGE_AT_RAISING = "at-raising"
STAGE_AT_BOARD = "at-board"
STAGE_AT_CLOSURE = "at-closure"
RECOGNISED_STAGES = (STAGE_AT_RAISING, STAGE_AT_BOARD, STAGE_AT_CLOSURE)

RAISING_BLOCKS = (
    NCR_IDENTIFIER_AND_DATE,
    AFFECTED_ITEM_AND_CONFIGURATION,
    DESCRIPTION_AND_DETECTION_POINT,
    REQUIREMENT_NOT_MET,
    CATEGORY_AND_SAFETY_EFFECT,
)

BOARD_BLOCKS = (
    CAUSE_ANALYSIS,
    PROPOSED_DISPOSITION,
    DISPOSITION_JUSTIFICATION,
)

CLOSURE_BLOCKS = (
    IMPLEMENTATION_AND_VERIFICATION,
    CLOSURE_AUTHORITY_AND_DATE,
)

DISPOSITION_USE_AS_IS = "use-as-is"
DISPOSITION_REPAIR = "repair"
DISPOSITION_REWORK = "rework"
DISPOSITION_SCRAP = "scrap"
DISPOSITION_RETURN_TO_SUPPLIER = "return-to-supplier"

DISPOSITION_PATH_BLOCKS = {
    DISPOSITION_USE_AS_IS: (
        ACCEPTANCE_TECHNICAL_JUSTIFICATION,
        EFFECT_ON_INTERFACES_AND_LIFETIME,
    ),
    DISPOSITION_REPAIR: (
        REPAIR_PROCEDURE_REFERENCE,
        EFFECT_ON_INTERFACES_AND_LIFETIME,
        REPAIR_REQUALIFICATION_EVIDENCE,
    ),
    DISPOSITION_REWORK: (
        REWORK_PROCEDURE_REFERENCE,
        REINSPECTION_AND_RETEST_RECORD,
    ),
    DISPOSITION_SCRAP: (SCRAP_AUTHORISATION_AND_SEGREGATION,),
    DISPOSITION_RETURN_TO_SUPPLIER: (
        SUPPLIER_RETURN_AUTHORISATION,
        SUPPLIER_CORRECTIVE_ACTION_REQUEST,
    ),
}

DISPOSITIONS_LEAVING_THE_REQUIREMENT = (DISPOSITION_USE_AS_IS, DISPOSITION_REPAIR)

CATEGORY_MINOR = "minor-nonconformance"
CATEGORY_MAJOR = "major-nonconformance"
RECOGNISED_CATEGORIES = (CATEGORY_MINOR, CATEGORY_MAJOR)

BOARD_INTERNAL = "internal-nonconformance-review-board"
BOARD_CUSTOMER = "customer-nonconformance-review-board"

NCR_NOT_RAISED = "nonconformance-report-not-raised"
DISPOSITION_NOT_PROPOSED = "nonconformance-report-disposition-not-proposed"
BASE_CONTENT_INCOMPLETE = "nonconformance-report-base-content-incomplete"
PATH_CONTENT_MISSING = "nonconformance-report-disposition-path-content-missing"
CUSTOMER_APPROVAL_MISSING = "nonconformance-report-customer-approval-missing"
READY_FOR_INTERNAL_BOARD = "nonconformance-report-ready-for-internal-board"
READY_FOR_CUSTOMER_BOARD = "nonconformance-report-ready-for-customer-board"
COMPLETE_FOR_CLOSURE = "nonconformance-report-complete-for-closure"

DEFAULT_NCR_DRD_POLICY = {
    "min_block_coverage": 1.0,
    "customer_board_on_major": True,
    "customer_board_on_safety_effect": True,
    "require_customer_approval_record": True,
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


def validate_ncr_drd_policy(policy):
    """Check the data-item policy the report is graded against."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction("min_block_coverage", policy.get("min_block_coverage"))
    major = _require_flag(
        "customer_board_on_major", policy.get("customer_board_on_major")
    )
    safety = _require_flag(
        "customer_board_on_safety_effect", policy.get("customer_board_on_safety_effect")
    )
    if not major and not safety:
        raise ValueError(
            "a policy routing neither a major nonconformance nor a safety "
            "effect to the customer board leaves no customer route at all"
        )
    _require_flag(
        "require_customer_approval_record",
        policy.get("require_customer_approval_record"),
    )
    return policy


def validate_report_identity(report):
    """Check the report names itself, its category and where it has got to."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping, got %r" % (report,))

    stage = _require_label("stage", report.get("stage"))
    if stage not in RECOGNISED_STAGES:
        raise ValueError("unrecognised stage %r; the stages are fixed" % stage)

    category = _require_label("category", report.get("category"))
    if category not in RECOGNISED_CATEGORIES:
        raise ValueError("unrecognised category %r; the categories are fixed" % category)

    disposition = report.get("proposed_disposition")
    if disposition is not None:
        disposition = _require_label("proposed_disposition", disposition)
        if disposition and disposition not in DISPOSITION_PATH_BLOCKS:
            raise ValueError(
                "unrecognised disposition %r; the disposition paths are fixed"
                % disposition
            )
        disposition = disposition or None

    return {
        "ncr_identifier": _require_label(
            "ncr_identifier", report.get("ncr_identifier", "")
        ),
        "affected_item": _require_label(
            "affected_item", report.get("affected_item", "")
        ),
        "stage": stage,
        "category": category,
        "safety_effect": _require_flag(
            "safety_effect", report.get("safety_effect", False)
        ),
        "proposed_disposition": disposition,
    }


def validate_block_record(block):
    """Read one content block: present, and pointing at something readable."""
    if not isinstance(block, dict):
        raise ValueError("block must be a mapping, got %r" % (block,))
    name = _require_label("block", block.get("block"))
    known = set(RAISING_BLOCKS) | set(BOARD_BLOCKS) | set(CLOSURE_BLOCKS)
    known.add(CUSTOMER_APPROVAL_RECORD)
    for path_blocks in DISPOSITION_PATH_BLOCKS.values():
        known.update(path_blocks)
    if name not in known:
        raise ValueError(
            "unrecognised content block %r; the data item fixes the block names"
            % name
        )
    return {
        "block": name,
        "present": _require_flag("present on %s" % name, block.get("present")),
        "entry_reference": _require_label(
            "entry_reference on %s" % name, block.get("entry_reference", "")
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


def block_is_filled(record):
    """True when a block is present and points at something readable."""
    checked = validate_block_record(record)
    return checked["present"] and bool(checked["entry_reference"])


def board_required(identity, policy=None):
    """Derive the review board the report has to be put to."""
    policy = validate_ncr_drd_policy(policy or DEFAULT_NCR_DRD_POLICY)
    if policy["customer_board_on_major"] and identity["category"] == CATEGORY_MAJOR:
        return BOARD_CUSTOMER
    if policy["customer_board_on_safety_effect"] and identity["safety_effect"]:
        return BOARD_CUSTOMER
    if identity["proposed_disposition"] in DISPOSITIONS_LEAVING_THE_REQUIREMENT:
        return BOARD_CUSTOMER
    return BOARD_INTERNAL


def base_blocks_for_stage(stage):
    """Blocks every report carries by the stage it has reached."""
    if stage not in RECOGNISED_STAGES:
        raise ValueError("unrecognised stage %r" % (stage,))
    blocks = list(RAISING_BLOCKS)
    if stage in (STAGE_AT_BOARD, STAGE_AT_CLOSURE):
        blocks.extend(BOARD_BLOCKS)
    if stage == STAGE_AT_CLOSURE:
        blocks.extend(CLOSURE_BLOCKS)
    return tuple(blocks)


def path_blocks_for(disposition):
    """Extra blocks the proposed disposition path brings with it."""
    if disposition is None:
        return ()
    if disposition not in DISPOSITION_PATH_BLOCKS:
        raise ValueError("unrecognised disposition %r" % (disposition,))
    return DISPOSITION_PATH_BLOCKS[disposition]


def customer_blocks_for(identity, policy=None):
    """The customer trace a closed customer-route report has to carry."""
    policy = validate_ncr_drd_policy(policy or DEFAULT_NCR_DRD_POLICY)
    if not policy["require_customer_approval_record"]:
        return ()
    if identity["stage"] != STAGE_AT_CLOSURE:
        return ()
    if board_required(identity, policy) != BOARD_CUSTOMER:
        return ()
    return (CUSTOMER_APPROVAL_RECORD,)


def required_blocks(identity, policy=None):
    """Every block the report owes at the stage and on the path it is on."""
    policy = validate_ncr_drd_policy(policy or DEFAULT_NCR_DRD_POLICY)
    ordered = list(base_blocks_for_stage(identity["stage"]))
    if identity["stage"] in (STAGE_AT_BOARD, STAGE_AT_CLOSURE):
        ordered.extend(path_blocks_for(identity["proposed_disposition"]))
    ordered.extend(customer_blocks_for(identity, policy))
    seen = []
    for name in ordered:
        if name not in seen:
            seen.append(name)
    return tuple(seen)


def missing_blocks(blocks, names):
    """Named blocks the report does not carry, or carries unfilled."""
    declared = block_index(blocks)
    missing = []
    for name in names:
        record = declared.get(name)
        if record is None or not block_is_filled(record):
            missing.append(name)
    return tuple(missing)


def content_coverage(blocks, identity, policy=None):
    """Share of every owed block, base and path, the report actually fills."""
    owed = required_blocks(identity, policy)
    if not owed:
        return 1.0
    absent = missing_blocks(blocks, owed)
    return (len(owed) - len(absent)) / float(len(owed))


def base_content_coverage(blocks, identity):
    """Share of the stage blocks the report fills; the gated figure."""
    owed = base_blocks_for_stage(identity["stage"])
    if not owed:
        return 1.0
    absent = missing_blocks(blocks, owed)
    return (len(owed) - len(absent)) / float(len(owed))


def assess_nonconformance_report_drd(case):
    """Grade a nonconformance report against its Annex A data item."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    policy = validate_ncr_drd_policy(case.get("policy") or DEFAULT_NCR_DRD_POLICY)

    findings = []
    advisories = []
    result = {
        "ncr_identifier": None,
        "stage": None,
        "board": None,
        "required_blocks": (),
        "missing_base_blocks": (),
        "missing_path_blocks": (),
        "content_coverage": 0.0,
        "base_content_coverage": 0.0,
        "verdict": None,
        "findings": findings,
        "advisories": advisories,
    }

    report = case.get("report")
    if report is None:
        findings.append(
            "no nonconformance report has been raised, so there is no data "
            "item to grade"
        )
        result["verdict"] = NCR_NOT_RAISED
        return result

    identity = validate_report_identity(report)
    result["ncr_identifier"] = identity["ncr_identifier"]
    result["stage"] = identity["stage"]
    if not identity["ncr_identifier"] or not identity["affected_item"]:
        findings.append(
            "the report carries no identifier or names no affected item, so "
            "nothing could be tracked against it"
        )
        result["verdict"] = NCR_NOT_RAISED
        return result

    blocks = report.get("content_blocks")
    if blocks is None:
        raise ValueError("the report declares no content_blocks to assess")
    checked = validate_blocks(blocks)

    if (
        identity["stage"] in (STAGE_AT_BOARD, STAGE_AT_CLOSURE)
        and identity["proposed_disposition"] is None
    ):
        findings.append(
            "the report has reached the board stage with no disposition "
            "proposed, so no path content can be owed of it yet"
        )
        result["verdict"] = DISPOSITION_NOT_PROPOSED
        return result

    board = board_required(identity, policy)
    owed = required_blocks(identity, policy)
    base_owed = base_blocks_for_stage(identity["stage"])
    path_owed = (
        path_blocks_for(identity["proposed_disposition"])
        if identity["stage"] in (STAGE_AT_BOARD, STAGE_AT_CLOSURE)
        else ()
    )
    customer_owed = customer_blocks_for(identity, policy)

    missing_base = missing_blocks(checked, base_owed)
    missing_path = missing_blocks(checked, path_owed)
    missing_customer = missing_blocks(checked, customer_owed)
    coverage = content_coverage(checked, identity, policy)

    result["board"] = board
    result["required_blocks"] = owed
    result["missing_base_blocks"] = missing_base
    result["missing_path_blocks"] = missing_path
    result["content_coverage"] = coverage

    if board == BOARD_CUSTOMER and identity["stage"] != STAGE_AT_CLOSURE:
        advisories.append(
            "the report routes to the customer board, so its disposition "
            "cannot be settled internally"
        )

    base_coverage = base_content_coverage(checked, identity)
    result["base_content_coverage"] = base_coverage
    if not _at_least(base_coverage, float(policy["min_block_coverage"])):
        for name in missing_base:
            findings.append(
                "the report does not fill the %s block its stage owes" % name
            )
        findings.append(
            "stage block coverage is %.3g per cent against the %.3g per cent "
            "the data item demands"
            % (base_coverage * 100.0, float(policy["min_block_coverage"]) * 100.0)
        )
        result["verdict"] = BASE_CONTENT_INCOMPLETE
        return result
    for name in missing_base:
        advisories.append(
            "the %s block its stage owes is unfilled, inside the coverage the "
            "policy tolerates" % name
        )

    if missing_path:
        for name in missing_path:
            findings.append(
                "the %s disposition owes the %s block and the report does not "
                "fill it" % (identity["proposed_disposition"], name)
            )
        result["verdict"] = PATH_CONTENT_MISSING
        return result

    if missing_customer:
        findings.append(
            "the report is closed on the customer route with no customer "
            "approval recorded against it"
        )
        result["verdict"] = CUSTOMER_APPROVAL_MISSING
        return result

    if identity["stage"] == STAGE_AT_CLOSURE:
        result["verdict"] = COMPLETE_FOR_CLOSURE
        return result

    result["verdict"] = (
        READY_FOR_CUSTOMER_BOARD if board == BOARD_CUSTOMER else READY_FOR_INTERNAL_BOARD
    )
    return result
