"""Identification-form content owed by a supplier whose line holds no approval.

Anchor: ECSS-Q-ST-60-05 clause 6.2.4 (form content expected from suppliers
whose production lines hold no approval at the time the hybrids are used).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Work out which content blocks the form owes. An unapproved line owes the
   ordinary blocks plus the three that stand in for the approval it does not
   have: its approval standing, the compensating controls, and the evidence
   from comparable builds.
2. Validate the submitted form against the block registry - an unrecognised
   block or field is a data error, not extra content.
3. Grade each owed block: complete, partial or absent, separating the fields
   that decide admissibility from the ones that only add confidence.
4. Count the fields actually supplied against the fields owed and report the
   share, treating a present-but-blank field as absent so an empty cell
   cannot buy coverage.
5. Decide admissibility on the deciding fields alone, then list every gap in
   registry order so the supplier is asked once for the whole set.
"""

import math

__all__ = [
    "CONTENT_BLOCKS",
    "BASE_BLOCKS",
    "UNAPPROVED_ONLY_BLOCKS",
    "BLOCK_STATUSES",
    "field_supplied",
    "required_blocks",
    "validate_form",
    "block_report",
    "form_reports",
    "completeness_counts",
    "completeness_ratio",
    "deciding_gaps",
    "supporting_gaps",
    "is_admissible",
    "assess_unapproved_line_form",
]

# The content registry. "fields" is everything the block owes; "deciding" is
# the subset admissibility turns on - the rest raise a finding when absent but
# do not by themselves make the form inadmissible.
CONTENT_BLOCKS = {
    "supplier-identity": {
        "fields": ("supplier-name", "manufacturing-plant", "production-line-reference"),
        "deciding": ("supplier-name", "production-line-reference"),
    },
    "hybrid-definition": {
        "fields": ("part-number", "drawing-issue", "schematic-reference", "package-outline"),
        "deciding": ("part-number", "drawing-issue"),
    },
    "element-list": {
        "fields": (
            "element-part-numbers",
            "element-lot-identification",
            "element-procurement-level",
        ),
        "deciding": ("element-part-numbers", "element-procurement-level"),
    },
    "assembly-process-flow": {
        "fields": (
            "process-step-sequence",
            "process-step-controls",
            "operator-certification-status",
        ),
        "deciding": ("process-step-sequence", "process-step-controls"),
    },
    "screening-and-test-plan": {
        "fields": ("screening-sequence", "test-conditions", "lot-acceptance-criteria"),
        "deciding": ("screening-sequence", "lot-acceptance-criteria"),
    },
    "line-approval-status": {
        "fields": ("approval-state", "approval-authority", "target-approval-date"),
        "deciding": ("approval-state", "target-approval-date"),
    },
    "compensating-controls": {
        "fields": ("added-inspection-points", "customer-witness-points", "delta-screening-plan"),
        "deciding": ("added-inspection-points", "delta-screening-plan"),
    },
    "comparable-build-evidence": {
        "fields": ("comparable-part-history", "line-capability-data", "nonconformance-record"),
        "deciding": ("line-capability-data", "nonconformance-record"),
    },
}

# Blocks every identification form carries, whatever the line's standing.
BASE_BLOCKS = (
    "supplier-identity",
    "hybrid-definition",
    "element-list",
    "assembly-process-flow",
    "screening-and-test-plan",
)

# Blocks owed only when the line is unapproved at the time of use; together
# they are what the form offers in place of the missing approval.
UNAPPROVED_ONLY_BLOCKS = (
    "line-approval-status",
    "compensating-controls",
    "comparable-build-evidence",
)

BLOCK_STATUSES = ("complete", "partial", "absent")


def field_supplied(value):
    """Return True when a form cell actually carries content."""
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        return len(value) > 0
    return True


def required_blocks(line_approved):
    """Return the blocks the form owes, in registry order."""
    if not isinstance(line_approved, bool):
        raise ValueError("line_approved must be a boolean")
    if line_approved:
        return BASE_BLOCKS
    return BASE_BLOCKS + UNAPPROVED_ONLY_BLOCKS


def validate_form(form):
    """Return the submitted form normalised against the block registry."""
    if not isinstance(form, dict):
        raise ValueError("form must be a mapping of block name to field mapping")
    normalised = {}
    for block, cells in form.items():
        if block not in CONTENT_BLOCKS:
            raise ValueError("unknown form content block %r" % (block,))
        if not isinstance(cells, dict):
            raise ValueError("block %r must map field names to values" % (block,))
        known = CONTENT_BLOCKS[block]["fields"]
        clean = {}
        for field, value in cells.items():
            if field not in known:
                raise ValueError("block %r has no field %r" % (block, field))
            clean[field] = value
        normalised[block] = clean
    return normalised


def block_report(block, cells):
    """Return the grading of one content block against the registry."""
    if block not in CONTENT_BLOCKS:
        raise ValueError("unknown form content block %r" % (block,))
    if cells is None:
        cells = {}
    if not isinstance(cells, dict):
        raise ValueError("block %r must map field names to values" % (block,))
    spec = CONTENT_BLOCKS[block]
    supplied = tuple(f for f in spec["fields"] if field_supplied(cells.get(f)))
    absent = tuple(f for f in spec["fields"] if f not in supplied)
    missing_deciding = tuple(f for f in spec["deciding"] if f not in supplied)
    missing_supporting = tuple(f for f in absent if f not in spec["deciding"])
    if not supplied:
        status = "absent"
    elif not absent:
        status = "complete"
    else:
        status = "partial"
    return {
        "block": block,
        "status": status,
        "supplied": supplied,
        "missing_deciding": missing_deciding,
        "missing_supporting": missing_supporting,
        "owed": len(spec["fields"]),
    }


def form_reports(form, line_approved):
    """Return one grading per owed block, in registry order."""
    normalised = validate_form(form)
    return [block_report(b, normalised.get(b)) for b in required_blocks(line_approved)]


def completeness_counts(form, line_approved):
    """Return (fields supplied, fields owed) over the owed blocks."""
    reports = form_reports(form, line_approved)
    supplied = sum(len(r["supplied"]) for r in reports)
    owed = sum(r["owed"] for r in reports)
    return (supplied, owed)


def completeness_ratio(form, line_approved):
    """Return the share of owed fields the form actually carries."""
    supplied, owed = completeness_counts(form, line_approved)
    if owed == 0:
        raise ValueError("the block registry owes no fields; registry is malformed")
    return supplied / float(owed)


def deciding_gaps(form, line_approved):
    """Return (block, field) pairs whose absence makes the form inadmissible."""
    gaps = []
    for report in form_reports(form, line_approved):
        for field in report["missing_deciding"]:
            gaps.append((report["block"], field))
    return tuple(gaps)


def supporting_gaps(form, line_approved):
    """Return (block, field) pairs that are absent but not admissibility gates."""
    gaps = []
    for report in form_reports(form, line_approved):
        for field in report["missing_supporting"]:
            gaps.append((report["block"], field))
    return tuple(gaps)


def is_admissible(form, line_approved):
    """Return True when every deciding field of every owed block is carried."""
    return not deciding_gaps(form, line_approved)


def assess_unapproved_line_form(spec):
    """Run the full clause 6.2.4 form-content assessment.

    spec keys: form (mapping of block to field mapping), line_approved (bool).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("form", "line_approved"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    line_approved = spec["line_approved"]
    if not isinstance(line_approved, bool):
        raise ValueError("line_approved must be a boolean")
    normalised = validate_form(spec["form"])
    owed = required_blocks(line_approved)
    reports = form_reports(normalised, line_approved)
    supplied_count, owed_count = completeness_counts(normalised, line_approved)
    gaps = deciding_gaps(normalised, line_approved)
    soft = supporting_gaps(normalised, line_approved)
    absent_blocks = tuple(r["block"] for r in reports if r["status"] == "absent")
    partial_blocks = tuple(r["block"] for r in reports if r["status"] == "partial")
    not_owed = tuple(b for b in CONTENT_BLOCKS if b in normalised and b not in owed)
    findings = []
    for block in absent_blocks:
        findings.append("content block not carried at all: %s" % block)
    for block, field in gaps:
        if block not in absent_blocks:
            findings.append("deciding field absent: %s / %s" % (block, field))
    for block, field in soft:
        if block not in absent_blocks:
            findings.append("supporting field absent: %s / %s" % (block, field))
    if not_owed:
        findings.append(
            "block(s) supplied that this case does not owe: %s" % ", ".join(sorted(not_owed))
        )
    if not line_approved:
        stand_in = tuple(b for b in UNAPPROVED_ONLY_BLOCKS if b in absent_blocks)
        if stand_in:
            findings.append(
                "the form offers nothing in place of the missing approval: %s"
                % ", ".join(stand_in)
            )
    return {
        "line_approved": line_approved,
        "required_blocks": owed,
        "reports": reports,
        "fields_supplied": supplied_count,
        "fields_owed": owed_count,
        "completeness_ratio": supplied_count / float(owed_count),
        "deciding_gaps": gaps,
        "supporting_gaps": soft,
        "absent_blocks": absent_blocks,
        "partial_blocks": partial_blocks,
        "blocks_not_owed": not_owed,
        "admissible": not gaps,
        "findings": findings,
    }
