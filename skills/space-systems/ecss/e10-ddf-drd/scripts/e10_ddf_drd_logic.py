#!/usr/bin/env python3
"""ECSS-E-ST-10 Annex G Design Definition File (DDF) DRD structure check
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): Annex G
defines a fixed content-block list for the DDF (introduction; applicable
and reference documents; terms/definitions/abbreviated terms; design
overview; design solution per configuration item; budgets and margins;
interface definition; design justification; an open-points register; and
supporting annexes), and the DDF is re-issued with growing maturity at
each project review milestone (SRR, PDR, CDR, AR). Each block becomes
mandatory from a specific milestone onward and, once mandatory, must
reach a milestone-specific minimum maturity (draft, consolidated,
final); the open-points register must be fully resolved by the AR
closure milestone. This module implements the block catalogue, the
milestone-derived mandatory set, and the structure/maturity/closure
checks; it does not implement the engineering design content itself.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence

MILESTONES: Sequence[str] = ("SRR", "PDR", "CDR", "AR")

MATURITY_LEVELS: Sequence[str] = ("draft", "consolidated", "final")

MIN_MATURITY_BY_MILESTONE: Dict[str, str] = {
    "SRR": "draft",
    "PDR": "consolidated",
    "CDR": "final",
    "AR": "final",
}

# Content-block catalogue for the DDF DRD: block id -> title and the
# milestone from which the block becomes mandatory.
BLOCK_CATALOGUE: Dict[str, Dict[str, str]] = {
    "introduction": {
        "title": "Introduction and document scope",
        "mandatory_from": "SRR",
    },
    "applicable_and_reference_documents": {
        "title": "Applicable and reference documents",
        "mandatory_from": "SRR",
    },
    "terms_definitions_abbreviations": {
        "title": "Terms, definitions and abbreviated terms",
        "mandatory_from": "SRR",
    },
    "design_overview": {
        "title": "Design overview (functional and physical architecture)",
        "mandatory_from": "SRR",
    },
    "open_points_register": {
        "title": "Open-points register (TBD/TBC list and closure plan)",
        "mandatory_from": "SRR",
    },
    "design_solution_per_item": {
        "title": "Design solution per configuration item",
        "mandatory_from": "PDR",
    },
    "budgets_and_margins": {
        "title": "Engineering budgets and margins",
        "mandatory_from": "PDR",
    },
    "interfaces_definition": {
        "title": "Interface definition",
        "mandatory_from": "PDR",
    },
    "design_justification_tradeoffs": {
        "title": "Design justification and trade-off rationale",
        "mandatory_from": "CDR",
    },
    "annexes_supporting_data": {
        "title": "Supporting annexes (drawings, ICDs, budget sheets)",
        "mandatory_from": "CDR",
    },
}


class DDFValidationError(ValueError):
    """Raised when a milestone, maturity level, or input shape is
    outside the DRD structure this module implements."""


@dataclass(frozen=True)
class BlockRecord:
    """Reported state for one DDF content block.

    present: whether the block appears in the DDF under review.
    maturity: one of MATURITY_LEVELS, or None if not reported.
    open_item_count: unresolved TBD/TBC count; meaningful only for the
    open_points_register block.
    """

    present: bool
    maturity: Optional[str] = None
    open_item_count: int = 0


@dataclass(frozen=True)
class DDFAssessment:
    """Result of validating a DDF's structure at a review milestone."""

    milestone: str
    missing_mandatory: List[str] = field(default_factory=list)
    unrecognized_blocks: List[str] = field(default_factory=list)
    insufficient_maturity: List[str] = field(default_factory=list)
    unresolved_open_items_at_closure: int = 0
    compliant: bool = False


def milestone_index(milestone: str) -> int:
    """Position of a review milestone in the SRR->PDR->CDR->AR sequence.
    Raises DDFValidationError for an unrecognized milestone."""
    try:
        return MILESTONES.index(milestone)
    except ValueError as exc:
        raise DDFValidationError(
            "unrecognized review milestone %r" % (milestone,)
        ) from exc


def maturity_index(maturity: str) -> int:
    """Position of a maturity level in the draft->consolidated->final
    sequence. Raises DDFValidationError for an unrecognized level."""
    try:
        return MATURITY_LEVELS.index(maturity)
    except ValueError as exc:
        raise DDFValidationError(
            "unrecognized maturity level %r" % (maturity,)
        ) from exc


def required_blocks_for_milestone(milestone: str) -> List[str]:
    """Content-block ids mandatory at or before the given milestone,
    per BLOCK_CATALOGUE. Raises DDFValidationError for an unrecognized
    milestone."""
    idx = milestone_index(milestone)
    return [
        block_id
        for block_id, spec in BLOCK_CATALOGUE.items()
        if milestone_index(spec["mandatory_from"]) <= idx
    ]


def assess_ddf_structure(
    milestone: str, blocks: Mapping[str, BlockRecord]
) -> DDFAssessment:
    """Validate a DDF's declared content blocks against the Annex G DRD
    structure at the given review milestone.

    blocks maps a content-block id to its reported BlockRecord. A block
    id outside BLOCK_CATALOGUE is flagged as unrecognized rather than
    silently ignored, since the DRD defines a fixed content-block list.
    A mandatory block missing, or present without a maturity at or
    above the milestone's minimum, is a finding. At the AR milestone
    only, a nonzero open_item_count on a present open_points_register
    is a finding. Raises DDFValidationError for an unrecognized
    milestone or maturity level.
    """
    idx = milestone_index(milestone)
    min_maturity_idx = maturity_index(MIN_MATURITY_BY_MILESTONE[milestone])

    unrecognized = sorted(block_id for block_id in blocks if block_id not in BLOCK_CATALOGUE)

    required = required_blocks_for_milestone(milestone)
    missing: List[str] = []
    insufficient: List[str] = []

    for block_id in required:
        record = blocks.get(block_id)
        if record is None or not record.present:
            missing.append(block_id)
            continue
        if record.maturity is None or maturity_index(record.maturity) < min_maturity_idx:
            insufficient.append(block_id)

    unresolved_open_items = 0
    if idx == milestone_index("AR"):
        open_points = blocks.get("open_points_register")
        if open_points is not None and open_points.present:
            unresolved_open_items = open_points.open_item_count

    compliant = (
        not missing
        and not unrecognized
        and not insufficient
        and unresolved_open_items == 0
    )

    return DDFAssessment(
        milestone=milestone,
        missing_mandatory=missing,
        unrecognized_blocks=unrecognized,
        insufficient_maturity=insufficient,
        unresolved_open_items_at_closure=unresolved_open_items,
        compliant=compliant,
    )
