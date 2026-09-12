"""
Fracture control programme setup logic — ECSS-E-ST-32C clause 5.1.

Deterministic, offline, stdlib-only. Implements:
  - Programme trigger check (catastrophic-hazard presence)
  - Item categorization (fracture-critical vs. non-fracture-critical)
  - FCB charter role check
  - Tailoring completeness check
  - Full programme-setup audit
"""

from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HAZARD_CATEGORIES = frozenset({"CATASTROPHIC", "CRITICAL", "MARGINAL", "NEGLIGIBLE"})

FRACTURE_CRITICAL_TRIGGER_HAZARDS = frozenset({"CATASTROPHIC"})

REQUIRED_FCB_ROLES = frozenset({"chair", "structural_lead", "qa_representative"})

MISSION_RISK_CATEGORIES = frozenset({"CAT-1", "CAT-2", "CAT-3"})


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class StructuralItem:
    item_id: str
    description: str
    hazard_category: str          # must be in HAZARD_CATEGORIES
    is_pressurised: bool = False
    has_rotating_parts: bool = False

    def validate(self) -> None:
        if not self.item_id:
            raise ValueError("item_id must not be empty")
        if self.hazard_category not in HAZARD_CATEGORIES:
            raise ValueError(
                f"Unknown hazard category '{self.hazard_category}' for item "
                f"'{self.item_id}'. Must be one of {sorted(HAZARD_CATEGORIES)}."
            )


@dataclass
class SubtierSupplier:
    supplier_id: str
    has_own_fcb: bool = False
    has_upward_delegation: bool = False

    def fcb_covered(self) -> bool:
        return self.has_own_fcb or self.has_upward_delegation


@dataclass
class ProgrammeSpec:
    items: List[StructuralItem] = field(default_factory=list)
    fcb_roles_present: List[str] = field(default_factory=list)
    subtier_suppliers: List[SubtierSupplier] = field(default_factory=list)
    tailoring_ref: Optional[str] = None
    mission_risk_category: Optional[str] = None
    tailoring_approved: bool = False


@dataclass
class ProgrammeSetupResult:
    programme_required: bool
    triggering_item_ids: List[str]
    fracture_critical_item_ids: List[str]
    non_fracture_critical_item_ids: List[str]
    fcb_findings: List[str]
    subtier_findings: List[str]
    tailoring_findings: List[str]

    def is_compliant(self) -> bool:
        return (
            self.programme_required
            and not self.fcb_findings
            and not self.subtier_findings
            and not self.tailoring_findings
        )


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def validate_items(items: List[StructuralItem]) -> None:
    """Raise ValueError for any item with an unrecognised hazard category."""
    for item in items:
        item.validate()


def programme_triggered(items: List[StructuralItem]) -> bool:
    """
    Return True if any item carries a CATASTROPHIC hazard category.
    Raises ValueError if any item has an unrecognised hazard category.
    """
    validate_items(items)
    return any(
        item.hazard_category in FRACTURE_CRITICAL_TRIGGER_HAZARDS
        for item in items
    )


def triggering_items(items: List[StructuralItem]) -> List[str]:
    """Return the item IDs that cause the programme to be triggered."""
    validate_items(items)
    return [
        item.item_id
        for item in items
        if item.hazard_category in FRACTURE_CRITICAL_TRIGGER_HAZARDS
    ]


def categorize_items(
    items: List[StructuralItem],
) -> tuple:
    """
    Split items into (fracture_critical_ids, non_fracture_critical_ids).

    Fracture-critical = CATASTROPHIC hazard, OR pressurised, OR has rotating parts.
    Returns two lists of item IDs.
    """
    validate_items(items)
    fracture_critical: List[str] = []
    non_fracture_critical: List[str] = []
    for item in items:
        if (
            item.hazard_category in FRACTURE_CRITICAL_TRIGGER_HAZARDS
            or item.is_pressurised
            or item.has_rotating_parts
        ):
            fracture_critical.append(item.item_id)
        else:
            non_fracture_critical.append(item.item_id)
    return fracture_critical, non_fracture_critical


def check_fcb_charter(roles_present: List[str]) -> List[str]:
    """
    Return a list of missing mandatory FCB role names.
    An empty list means the FCB charter satisfies the minimum requirement.
    """
    normalised = frozenset(r.strip().lower() for r in roles_present)
    return sorted(REQUIRED_FCB_ROLES - normalised)


def check_subtier_coverage(suppliers: List[SubtierSupplier]) -> List[str]:
    """
    Return supplier IDs that have no FCB coverage (neither their own FCB
    nor a documented upward delegation).
    """
    return [s.supplier_id for s in suppliers if not s.fcb_covered()]


def check_tailoring(
    tailoring_ref: Optional[str],
    mission_risk_category: Optional[str],
    tailoring_approved: bool,
) -> List[str]:
    """
    Return a list of tailoring findings.
    Expects a non-empty tailoring document reference, a recognised mission
    risk category, and approval flag set to True.
    """
    findings: List[str] = []
    if not tailoring_ref:
        findings.append("tailoring_ref missing: no tailoring document reference recorded")
    if mission_risk_category not in MISSION_RISK_CATEGORIES:
        findings.append(
            f"mission_risk_category '{mission_risk_category}' not recognised; "
            f"must be one of {sorted(MISSION_RISK_CATEGORIES)}"
        )
    if not tailoring_approved:
        findings.append(
            "tailoring_approved is False: tailoring decisions lack documented approval"
        )
    return findings


def run_programme_setup_check(spec: ProgrammeSpec) -> ProgrammeSetupResult:
    """
    Execute the full programme-setup audit against a ProgrammeSpec.
    Returns a ProgrammeSetupResult capturing trigger status, item split,
    FCB findings, sub-tier findings, and tailoring findings.
    """
    validate_items(spec.items)

    required = programme_triggered(spec.items)
    trigger_ids = triggering_items(spec.items)
    fc_ids, nfc_ids = categorize_items(spec.items)

    if not required:
        return ProgrammeSetupResult(
            programme_required=False,
            triggering_item_ids=[],
            fracture_critical_item_ids=[],
            non_fracture_critical_item_ids=[i.item_id for i in spec.items],
            fcb_findings=[],
            subtier_findings=[],
            tailoring_findings=[],
        )

    fcb_findings = check_fcb_charter(spec.fcb_roles_present)
    subtier_findings = check_subtier_coverage(spec.subtier_suppliers)
    tailoring_findings = check_tailoring(
        spec.tailoring_ref,
        spec.mission_risk_category,
        spec.tailoring_approved,
    )

    return ProgrammeSetupResult(
        programme_required=True,
        triggering_item_ids=trigger_ids,
        fracture_critical_item_ids=fc_ids,
        non_fracture_critical_item_ids=nfc_ids,
        fcb_findings=fcb_findings,
        subtier_findings=subtier_findings,
        tailoring_findings=tailoring_findings,
    )
