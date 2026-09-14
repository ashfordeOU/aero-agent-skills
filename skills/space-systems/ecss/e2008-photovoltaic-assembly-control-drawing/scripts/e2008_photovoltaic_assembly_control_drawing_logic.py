#!/usr/bin/env python3
"""Source control drawing content for a complete photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C Annex A. The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

A source control drawing is not a picture of an assembly. It is the document
that says which characteristics of that assembly the supplier is not free to
change, and a characteristic the drawing shows without controlling is a
characteristic the supplier may change without telling anyone.

Three questions decide the package.

Is every content block the annex calls for actually on the drawing?
    A block can be absent, present but left open -- a box drawn with TBD in
    it, a note promising a later issue -- or present and specified. Only the
    third one controls anything, and the three outcomes are not two.

Is every dimension shown also toleranced?
    A nominal with no tolerance band is a drawn intention, not a control. A
    band so wide it admits every part the supplier could make is a note
    wearing a tolerance's clothes.

Does every constituent item the assembly is built from cite a drawing that
exists at the issue cited?
    A complete photovoltaic assembly is an assembly of items that each carry
    their own drawing. Citing a draft, a cancelled or a superseded issue
    leaves the constituent uncontrolled however complete the top drawing is.

Blocks do not weigh the same, so completeness is weighted by how much of the
assembly each block controls rather than counted.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "REQUIRED_CONTENT_BLOCKS",
    "BLOCK_WEIGHTS",
    "DRAWING_ISSUE_STATES",
    "MAX_RELATIVE_TOLERANCE",
    "BLOCK_SPECIFIED",
    "BLOCK_OPEN",
    "BLOCK_ABSENT",
    "CITED_CURRENT",
    "CITED_OFF_ISSUE",
    "CITED_NOT_GOVERNING",
    "DRAWING_RELEASABLE",
    "DRAWING_OPEN_ITEMS",
    "DRAWING_NOT_RELEASABLE",
    "content_block_state",
    "dimension_control",
    "constituent_drawing_standing",
    "completeness_share",
    "audit_photovoltaic_assembly_drawing",
]

# The content blocks Annex A expects on the assembly source control drawing,
# with how much of the assembly each one actually controls.
REQUIRED_CONTENT_BLOCKS = (
    ("assembly-identification", 3),
    ("outline-and-envelope-dimensions", 3),
    ("constituent-item-list", 3),
    ("interconnection-and-terminal-arrangement", 3),
    ("electrical-output-at-reference-conditions", 3),
    ("mass-and-mass-distribution", 2),
    ("marking-and-traceability", 2),
    ("acceptance-and-screening-reference", 2),
    ("handling-and-storage-constraint", 1),
)

BLOCK_WEIGHTS = dict(REQUIRED_CONTENT_BLOCKS)

DRAWING_ISSUE_STATES = ("released", "draft", "superseded", "cancelled")

# A band wider than this share of the nominal admits anything the supplier
# could plausibly deliver, so it records an intention rather than a control.
MAX_RELATIVE_TOLERANCE = 0.10

BLOCK_SPECIFIED = "specified"
BLOCK_OPEN = "open"
BLOCK_ABSENT = "absent"

CITED_CURRENT = "cited-at-released-issue"
CITED_OFF_ISSUE = "cited-off-issue"
CITED_NOT_GOVERNING = "cited-drawing-not-governing"

DRAWING_RELEASABLE = "drawing-releasable"
DRAWING_OPEN_ITEMS = "drawing-releasable-with-open-items"
DRAWING_NOT_RELEASABLE = "drawing-not-releasable"

# Shares and tolerance ratios are quotients of measured quantities compared
# with written bounds, so a value physically on a bound can evaluate a few
# units in the last place past it. The comparisons absorb that; the bounds
# stay as written.
_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _label(name, value):
    """Return a non-empty stripped string, or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _flag(name, value):
    """Return a boolean, or raise."""
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _real(name, value, allow_zero=True):
    """Return a finite non-negative float, or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    if not allow_zero and value == 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return value


def _count(name, value):
    """Return a non-negative integer, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _at_least(value, bound):
    """True when value is at or above bound, absorbing representation error."""
    return value > bound or math.isclose(
        value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, bound):
    """True when value is at or below bound, absorbing representation error."""
    return value < bound or math.isclose(
        value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def content_block_state(record):
    """Resolve one content block into specified, open or absent.

    record keys: block, present, specified, optional open_items.
    """
    if not isinstance(record, dict):
        raise ValueError("content block record must be a mapping")
    for key in ("block", "present", "specified"):
        if key not in record:
            raise ValueError("content block record missing required key '%s'" % key)
    block = _label("block", record["block"])
    present = _flag("present", record["present"])
    specified = _flag("specified", record["specified"])
    open_items = _count("open_items", record.get("open_items", 0))
    findings = []

    if not present:
        findings.append(
            "content block '%s' is not on the drawing at all; nothing about it "
            "is controlled" % block
        )
        return {
            "block": block,
            "state": BLOCK_ABSENT,
            "open_items": open_items,
            "findings": findings,
        }
    if not specified:
        findings.append(
            "content block '%s' is drawn but left unspecified; a box with no "
            "value in it controls nothing" % block
        )
        return {
            "block": block,
            "state": BLOCK_OPEN,
            "open_items": open_items,
            "findings": findings,
        }
    if open_items:
        findings.append(
            "content block '%s' is specified and carries %d open item(s) still "
            "to be closed" % (block, open_items)
        )
        return {
            "block": block,
            "state": BLOCK_OPEN,
            "open_items": open_items,
            "findings": findings,
        }
    return {
        "block": block,
        "state": BLOCK_SPECIFIED,
        "open_items": 0,
        "findings": findings,
    }


def dimension_control(dimension):
    """Decide whether a dimension shown on the drawing is actually controlled.

    dimension keys: name, nominal, optional tolerance, optional reference.
    """
    if not isinstance(dimension, dict):
        raise ValueError("dimension must be a mapping")
    for key in ("name", "nominal"):
        if key not in dimension:
            raise ValueError("dimension missing required key '%s'" % key)
    name = _label("dimension name", dimension["name"])
    nominal = _real("nominal", dimension["nominal"], allow_zero=False)
    reference = _flag("reference", dimension.get("reference", False))
    raw_tolerance = dimension.get("tolerance", None)
    findings = []

    if reference:
        findings.append(
            "dimension '%s' is carried for reference; it informs the reader "
            "and controls no part" % name
        )
        return {
            "name": name,
            "nominal": nominal,
            "tolerance": None,
            "relative_tolerance": None,
            "controlled": False,
            "over_wide": False,
            "reference": True,
            "findings": findings,
        }

    if raw_tolerance is None:
        findings.append(
            "dimension '%s' is shown at %.4f with no tolerance band; a nominal "
            "alone is an intention, not a control" % (name, nominal)
        )
        return {
            "name": name,
            "nominal": nominal,
            "tolerance": None,
            "relative_tolerance": None,
            "controlled": False,
            "over_wide": False,
            "reference": False,
            "findings": findings,
        }

    tolerance = _real("tolerance", raw_tolerance, allow_zero=True)
    if tolerance == 0.0:
        findings.append(
            "dimension '%s' carries a zero-width band; no part can be made to "
            "it and no part can be rejected against it" % name
        )
        return {
            "name": name,
            "nominal": nominal,
            "tolerance": 0.0,
            "relative_tolerance": 0.0,
            "controlled": False,
            "over_wide": False,
            "reference": False,
            "findings": findings,
        }

    relative = tolerance / nominal
    over_wide = not _at_most(relative, MAX_RELATIVE_TOLERANCE)
    if over_wide:
        findings.append(
            "dimension '%s' carries a band of %.4f on a nominal of %.4f, wider "
            "than the %.0f%% a control is worth" % (
                name, tolerance, nominal, MAX_RELATIVE_TOLERANCE * 100.0
            )
        )
    return {
        "name": name,
        "nominal": nominal,
        "tolerance": tolerance,
        "relative_tolerance": relative,
        "lower": nominal - tolerance,
        "upper": nominal + tolerance,
        "controlled": not over_wide,
        "over_wide": over_wide,
        "reference": False,
        "findings": findings,
    }


def constituent_drawing_standing(item):
    """Resolve how far a cited constituent item drawing governs.

    item keys: item, drawing, issue_state, cited_issue, released_issue.
    """
    if not isinstance(item, dict):
        raise ValueError("constituent item must be a mapping")
    for key in ("item", "drawing", "issue_state", "cited_issue", "released_issue"):
        if key not in item:
            raise ValueError("constituent item missing required key '%s'" % key)
    name = _label("item", item["item"])
    drawing = _label("drawing", item["drawing"])
    state = item["issue_state"]
    if state not in DRAWING_ISSUE_STATES:
        raise ValueError(
            "issue_state must be one of %s, got %r" % (DRAWING_ISSUE_STATES, state)
        )
    cited = _label("cited_issue", item["cited_issue"])
    released = _label("released_issue", item["released_issue"])
    findings = []

    if state == "draft":
        findings.append(
            "constituent '%s' cites drawing %s at a draft issue; a draft binds "
            "no supplier" % (name, drawing)
        )
        return {
            "item": name,
            "drawing": drawing,
            "standing": CITED_NOT_GOVERNING,
            "findings": findings,
        }
    if state == "cancelled":
        findings.append(
            "constituent '%s' cites drawing %s after it was cancelled; the "
            "citation points at nothing" % (name, drawing)
        )
        return {
            "item": name,
            "drawing": drawing,
            "standing": CITED_NOT_GOVERNING,
            "findings": findings,
        }
    if state == "superseded":
        findings.append(
            "constituent '%s' cites drawing %s at superseded issue %s; the step "
            "to issue %s needs dispositioning" % (name, drawing, cited, released)
        )
        return {
            "item": name,
            "drawing": drawing,
            "standing": CITED_OFF_ISSUE,
            "findings": findings,
        }
    if cited != released:
        findings.append(
            "constituent '%s' cites drawing %s at issue %s while issue %s is "
            "the released one" % (name, drawing, cited, released)
        )
        return {
            "item": name,
            "drawing": drawing,
            "standing": CITED_OFF_ISSUE,
            "findings": findings,
        }
    return {
        "item": name,
        "drawing": drawing,
        "standing": CITED_CURRENT,
        "findings": findings,
    }


def completeness_share(block_results):
    """Weight the specified blocks by how much of the assembly each controls."""
    if not isinstance(block_results, (list, tuple)):
        raise ValueError("block_results must be a sequence of graded blocks")
    total = float(sum(BLOCK_WEIGHTS.values()))
    if total <= 0.0:
        raise ValueError("the required content block set carries no weight")
    earned = 0.0
    for result in block_results:
        weight = BLOCK_WEIGHTS.get(result.get("block"))
        if weight is None:
            continue
        if result.get("state") == BLOCK_SPECIFIED:
            earned += float(weight)
    return earned / total


def audit_photovoltaic_assembly_drawing(spec):
    """Audit a complete photovoltaic assembly source control drawing package.

    spec keys: drawing, content_blocks, dimensions, constituent_items,
    optional required_completeness_share.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("drawing", "content_blocks", "dimensions", "constituent_items"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    drawing = _label("drawing", spec["drawing"])

    for key in ("content_blocks", "dimensions", "constituent_items"):
        if not isinstance(spec[key], (list, tuple)):
            raise ValueError("spec['%s'] must be a sequence" % key)

    required_share = spec.get("required_completeness_share", 1.0)
    if isinstance(required_share, bool) or not isinstance(
        required_share, (int, float)
    ):
        raise ValueError("required_completeness_share must be a real number")
    required_share = float(required_share)
    if not math.isfinite(required_share) or not 0.0 <= required_share <= 1.0:
        raise ValueError(
            "required_completeness_share must lie in [0, 1], got %r"
            % (spec.get("required_completeness_share"),)
        )

    blocks = [content_block_state(record) for record in spec["content_blocks"]]
    seen = set()
    for result in blocks:
        if result["block"] in seen:
            raise ValueError(
                "content block '%s' is graded twice on drawing %s"
                % (result["block"], drawing)
            )
        seen.add(result["block"])

    findings = []
    missing = []
    for block, _weight in REQUIRED_CONTENT_BLOCKS:
        if block not in seen:
            missing.append(block)
            findings.append(
                "content block '%s' is required by the annex and the drawing "
                "package says nothing about it" % block
            )

    dimensions = [dimension_control(item) for item in spec["dimensions"]]
    if not dimensions:
        raise ValueError("a source control drawing showing no dimension is an input error")
    constituents = [constituent_drawing_standing(item) for item in spec["constituent_items"]]
    if not constituents:
        raise ValueError("a complete assembly built from no constituent item is an input error")

    for result in blocks + dimensions + constituents:
        findings.extend(result["findings"])

    absent_blocks = [r["block"] for r in blocks if r["state"] == BLOCK_ABSENT]
    open_blocks = [r["block"] for r in blocks if r["state"] == BLOCK_OPEN]
    uncontrolled = [
        d["name"] for d in dimensions if not d["controlled"] and not d["reference"]
    ]
    over_wide = [d["name"] for d in dimensions if d["over_wide"]]
    not_governing = [
        c["item"] for c in constituents if c["standing"] == CITED_NOT_GOVERNING
    ]
    off_issue = [c["item"] for c in constituents if c["standing"] == CITED_OFF_ISSUE]

    share = completeness_share(blocks)
    share_met = _at_least(share, required_share)
    if not share_met:
        findings.append(
            "weighted content completeness is %.4f against a required %.4f"
            % (share, required_share)
        )

    blocking = bool(missing or absent_blocks or uncontrolled or not_governing) or not share_met
    conditional = bool(open_blocks or off_issue)

    if blocking:
        verdict = DRAWING_NOT_RELEASABLE
    elif conditional:
        verdict = DRAWING_OPEN_ITEMS
    else:
        verdict = DRAWING_RELEASABLE

    return {
        "drawing": drawing,
        "blocks": blocks,
        "dimensions": dimensions,
        "constituents": constituents,
        "missing_blocks": missing,
        "absent_blocks": absent_blocks,
        "open_blocks": open_blocks,
        "uncontrolled_dimensions": uncontrolled,
        "over_wide_dimensions": over_wide,
        "not_governing_constituents": not_governing,
        "off_issue_constituents": off_issue,
        "completeness_share": share,
        "required_completeness_share": required_share,
        "verdict": verdict,
        "findings": findings,
    }
