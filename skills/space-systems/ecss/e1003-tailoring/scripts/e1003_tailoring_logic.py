"""
e1003_tailoring_logic.py
Annex D tailoring method for ECSS-E-ST-10-03C — System Engineering General Requirements.
Reference: ECSS-E-ST-10-03C Annex D (informative), ECSS-M-ST-10C clause 4.
No third-party dependencies. Deterministic, offline.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_PROJECT_CLASSES = ("A", "B", "C", "D")

VALID_VERIFICATION_METHODS = ("T", "A", "I", "R")  # Test, Analysis, Inspection, Review-of-design

APPLICABILITY_APPLICABLE = "A"
APPLICABILITY_NOT_APPLICABLE = "NA"
APPLICABILITY_TAILORED = "T"
APPLICABILITY_CONDITIONAL = "C"

_APPLICABLE_STATUSES = frozenset({
    APPLICABILITY_APPLICABLE,
    APPLICABILITY_TAILORED,
    APPLICABILITY_CONDITIONAL,
})

# ---------------------------------------------------------------------------
# Requirement catalogue — representative subset, paraphrased from E-ST-10-03C.
# Each entry specifies default applicability and verification methods per class.
# Classes absent from a dict key default to "NA" / [].
# ---------------------------------------------------------------------------

_REQUIREMENTS_CATALOGUE: List[Dict] = [
    {
        "id": "REQ-001",
        "clause": "E-ST-10-03C §4.2",
        "title": "Mission objectives documentation",
        "description": (
            "Document the mission objectives and derive top-level system "
            "requirements from them."
        ),
        "default_applicability": {"A": "A", "B": "A", "C": "A", "D": "A"},
        "default_verification": {
            "A": ["R", "I"], "B": ["R", "I"], "C": ["R"], "D": ["R"],
        },
    },
    {
        "id": "REQ-002",
        "clause": "E-ST-10-03C §4.3",
        "title": "System-level requirements baseline",
        "description": (
            "Establish and baseline a complete set of system-level requirements "
            "covering functional, performance, and interface aspects."
        ),
        "default_applicability": {"A": "A", "B": "A", "C": "A", "D": "C"},
        "default_verification": {
            "A": ["R", "I"], "B": ["R", "I"], "C": ["R"], "D": ["R"],
        },
    },
    {
        "id": "REQ-003",
        "clause": "E-ST-10-03C §4.4",
        "title": "Architecture definition",
        "description": (
            "Define the system architecture, decomposing functions to subsystems "
            "and identifying critical interfaces."
        ),
        "default_applicability": {"A": "A", "B": "A", "C": "A", "D": "C"},
        "default_verification": {
            "A": ["R", "A"], "B": ["R", "A"], "C": ["R"], "D": ["R"],
        },
    },
    {
        "id": "REQ-004",
        "clause": "E-ST-10-03C §4.5",
        "title": "Interface requirements definition",
        "description": (
            "Define all external and internal interfaces, document them in "
            "interface control documents, and obtain stakeholder agreement."
        ),
        "default_applicability": {"A": "A", "B": "A", "C": "A", "D": "C"},
        "default_verification": {
            "A": ["R", "I"], "B": ["R", "I"], "C": ["R"], "D": ["I"],
        },
    },
    {
        "id": "REQ-005",
        "clause": "E-ST-10-03C §4.6",
        "title": "System safety requirements",
        "description": (
            "Identify safety-critical functions, derive system safety requirements, "
            "and maintain a safety hazard log."
        ),
        "default_applicability": {"A": "A", "B": "A", "C": "A", "D": "A"},
        "default_verification": {
            "A": ["R", "A", "I"], "B": ["R", "A"], "C": ["R", "A"], "D": ["R"],
        },
    },
    {
        "id": "REQ-006",
        "clause": "E-ST-10-03C §5.2",
        "title": "Configuration management plan",
        "description": (
            "Prepare and maintain a configuration management plan covering "
            "identification, control, status accounting, and auditing."
        ),
        "default_applicability": {"A": "A", "B": "A", "C": "A", "D": "C"},
        "default_verification": {
            "A": ["R", "I"], "B": ["R", "I"], "C": ["R"], "D": ["R"],
        },
    },
    {
        "id": "REQ-007",
        "clause": "E-ST-10-03C §5.3",
        "title": "Risk management process",
        "description": (
            "Implement a risk management process including identification, "
            "assessment, mitigation, and tracking via a risk register."
        ),
        "default_applicability": {"A": "A", "B": "A", "C": "A", "D": "C"},
        "default_verification": {
            "A": ["R", "I"], "B": ["R"], "C": ["R"], "D": ["R"],
        },
    },
    {
        "id": "REQ-008",
        "clause": "E-ST-10-03C §5.4",
        "title": "Verification and validation plan",
        "description": (
            "Prepare a verification and validation plan describing methods, "
            "responsibilities, and success criteria for each requirement."
        ),
        "default_applicability": {"A": "A", "B": "A", "C": "A", "D": "C"},
        "default_verification": {
            "A": ["R", "I"], "B": ["R"], "C": ["R"], "D": ["R"],
        },
    },
    {
        "id": "REQ-009",
        "clause": "E-ST-10-03C §6.2",
        "title": "System design reviews",
        "description": (
            "Conduct formal design reviews at defined project milestones "
            "(e.g. SRR, PDR, CDR) with agreed entry and exit criteria."
        ),
        "default_applicability": {"A": "A", "B": "A", "C": "A", "D": "C"},
        "default_verification": {
            "A": ["R", "I"], "B": ["R", "I"], "C": ["I"], "D": ["I"],
        },
    },
    {
        "id": "REQ-010",
        "clause": "E-ST-10-03C §6.3",
        "title": "Critical items list",
        "description": (
            "Identify and track all system critical items — components or functions "
            "whose failure would result in mission loss or a safety hazard."
        ),
        "default_applicability": {"A": "A", "B": "A", "C": "C", "D": "NA"},
        "default_verification": {
            "A": ["R", "I", "A"], "B": ["R", "A"], "C": ["R"],
        },
    },
    {
        "id": "REQ-011",
        "clause": "E-ST-10-03C §4.5.2",
        "title": "Hardware and software interface control",
        "description": (
            "Define the hardware and software interface in a dedicated control "
            "document, and verify consistency between both sides."
        ),
        "default_applicability": {"A": "A", "B": "A", "C": "A", "D": "C"},
        "default_verification": {
            "A": ["R", "T"], "B": ["R", "T"], "C": ["R"], "D": ["I"],
        },
    },
    {
        "id": "REQ-012",
        "clause": "E-ST-10-03C §4.7",
        "title": "End-of-life disposal planning",
        "description": (
            "Define and document the end-of-life disposal strategy, including "
            "passivation and orbit disposal in line with debris-mitigation guidelines."
        ),
        "default_applicability": {"A": "A", "B": "A", "C": "A", "D": "C"},
        "default_verification": {
            "A": ["A", "R"], "B": ["A", "R"], "C": ["A"], "D": ["R"],
        },
    },
    {
        "id": "REQ-013",
        "clause": "E-ST-10-03C §7.2",
        "title": "Product assurance requirements",
        "description": (
            "Define product assurance requirements and confirm that a product "
            "assurance plan is in place and implemented."
        ),
        "default_applicability": {"A": "A", "B": "A", "C": "A", "D": "C"},
        "default_verification": {
            "A": ["R", "I"], "B": ["R", "I"], "C": ["R"], "D": ["R"],
        },
    },
    {
        "id": "REQ-014",
        "clause": "E-ST-10-03C §4.5.3",
        "title": "Ground segment interface requirements",
        "description": (
            "Define the ground segment interfaces including telemetry, telecommand, "
            "and data-handling protocols in a ground-to-space interface control document."
        ),
        "default_applicability": {"A": "A", "B": "A", "C": "A", "D": "C"},
        "default_verification": {
            "A": ["R", "T"], "B": ["R", "T"], "C": ["R"], "D": ["I"],
        },
    },
    {
        "id": "REQ-015",
        "clause": "E-ST-10-03C §4.2.2",
        "title": "Mission analysis",
        "description": (
            "Perform mission analysis to derive the mission profile, orbit, "
            "environment, and operational scenarios that drive system requirements."
        ),
        "default_applicability": {"A": "A", "B": "A", "C": "A", "D": "A"},
        "default_verification": {
            "A": ["A", "R"], "B": ["A", "R"], "C": ["A"], "D": ["A"],
        },
    },
]

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class TailoringEntry:
    requirement_id: str
    clause: str
    title: str
    applicability: str          # one of "A", "NA", "T", "C"
    verification_methods: List[str]   # subset of ["T", "A", "I", "R"]
    rationale: str = ""


@dataclass
class TailoringMatrix:
    project_class: str
    entries: List[TailoringEntry] = field(default_factory=list)


@dataclass
class ComplianceRow:
    requirement_id: str
    clause: str
    title: str
    applicability: str
    rationale: str


@dataclass
class ComplianceMatrix:
    project_class: str
    rows: List[ComplianceRow] = field(default_factory=list)

    @property
    def applicable_count(self) -> int:
        return sum(1 for r in self.rows if r.applicability in _APPLICABLE_STATUSES)

    @property
    def not_applicable_count(self) -> int:
        return sum(1 for r in self.rows if r.applicability == APPLICABILITY_NOT_APPLICABLE)


@dataclass
class VerificationRow:
    requirement_id: str
    clause: str
    title: str
    verification_methods: List[str]


@dataclass
class VerificationMatrix:
    project_class: str
    rows: List[VerificationRow] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def validate_project_class(project_class: str) -> None:
    """Raise ValueError if project_class is not one of A, B, C, D."""
    if project_class not in VALID_PROJECT_CLASSES:
        raise ValueError(
            f"Invalid project class '{project_class}'. "
            f"Must be one of: {', '.join(VALID_PROJECT_CLASSES)}."
        )


def validate_applicability(status: str) -> None:
    """Raise ValueError if applicability status is not a recognised code."""
    valid = {
        APPLICABILITY_APPLICABLE,
        APPLICABILITY_NOT_APPLICABLE,
        APPLICABILITY_TAILORED,
        APPLICABILITY_CONDITIONAL,
    }
    if status not in valid:
        raise ValueError(
            f"Invalid applicability '{status}'. "
            f"Must be one of: {', '.join(sorted(valid))}."
        )


def validate_verification_methods(methods: List[str]) -> None:
    """Raise ValueError if any method code is not recognised."""
    for m in methods:
        if m not in VALID_VERIFICATION_METHODS:
            raise ValueError(
                f"Invalid verification method '{m}'. "
                f"Must be one of: {', '.join(VALID_VERIFICATION_METHODS)}."
            )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_tailoring_matrix(
    project_class: str,
    overrides: Optional[Dict[str, Dict]] = None,
) -> TailoringMatrix:
    """
    Build the Annex D tailoring matrix for the given project class.

    overrides maps requirement_id to a dict with any of:
        'applicability'       — revised status code
        'verification_methods' — revised list of method codes
        'rationale'           — written justification for the deviation
    Entries absent from overrides retain their catalogue defaults.
    """
    validate_project_class(project_class)
    overrides = overrides or {}

    entries: List[TailoringEntry] = []
    for req in _REQUIREMENTS_CATALOGUE:
        rid = req["id"]
        default_app: str = req["default_applicability"].get(project_class, "NA")
        default_ver: List[str] = list(req["default_verification"].get(project_class, []))

        if rid in overrides:
            ov = overrides[rid]
            app = ov.get("applicability", default_app)
            ver = ov.get("verification_methods", default_ver)
            rationale: str = ov.get("rationale", "Project-specific tailoring.")
            validate_applicability(app)
            validate_verification_methods(ver)
        else:
            app = default_app
            ver = default_ver
            rationale = ""

        entries.append(TailoringEntry(
            requirement_id=rid,
            clause=req["clause"],
            title=req["title"],
            applicability=app,
            verification_methods=ver,
            rationale=rationale,
        ))

    return TailoringMatrix(project_class=project_class, entries=entries)


def generate_compliance_matrix(matrix: TailoringMatrix) -> ComplianceMatrix:
    """Derive the compliance matrix from a completed tailoring matrix."""
    rows = [
        ComplianceRow(
            requirement_id=e.requirement_id,
            clause=e.clause,
            title=e.title,
            applicability=e.applicability,
            rationale=e.rationale,
        )
        for e in matrix.entries
    ]
    return ComplianceMatrix(project_class=matrix.project_class, rows=rows)


def generate_verification_matrix(matrix: TailoringMatrix) -> VerificationMatrix:
    """
    Derive the verification matrix from a tailoring matrix.
    Only applicable requirements (A, T, C) are included — requirements
    categorized as Not Applicable carry no verification obligation.
    """
    rows = [
        VerificationRow(
            requirement_id=e.requirement_id,
            clause=e.clause,
            title=e.title,
            verification_methods=list(e.verification_methods),
        )
        for e in matrix.entries
        if e.applicability in _APPLICABLE_STATUSES
    ]
    return VerificationMatrix(project_class=matrix.project_class, rows=rows)


def check_completeness(matrix: TailoringMatrix) -> List[str]:
    """
    Return a list of completeness findings for the tailoring matrix.
    An empty list indicates the matrix is ready for gate submission.

    Findings raised:
    - Applicable requirement with no verification method assigned.
    - Tailored or Conditional entry with no rationale recorded.
    """
    findings: List[str] = []
    for e in matrix.entries:
        if e.applicability in _APPLICABLE_STATUSES and not e.verification_methods:
            findings.append(
                f"{e.requirement_id}: applicable (status={e.applicability}) "
                f"but no verification method assigned."
            )
        if e.applicability in (APPLICABILITY_TAILORED, APPLICABILITY_CONDITIONAL):
            if not e.rationale.strip():
                findings.append(
                    f"{e.requirement_id}: status={e.applicability} requires a rationale."
                )
    return findings


def summarize_matrix(matrix: TailoringMatrix) -> Dict[str, int]:
    """Return counts of each applicability status across all matrix entries."""
    counts: Dict[str, int] = {
        APPLICABILITY_APPLICABLE: 0,
        APPLICABILITY_NOT_APPLICABLE: 0,
        APPLICABILITY_TAILORED: 0,
        APPLICABILITY_CONDITIONAL: 0,
    }
    for e in matrix.entries:
        if e.applicability in counts:
            counts[e.applicability] += 1
    return counts
