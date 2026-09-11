"""
ECSS-E-ST-10-11C §4.6.3 — HFE safety requirements.

Provides deterministic checks for hazard criticality categorization and
human-error prevention measure coverage of spacecraft operations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet, List, Set


class CriticalityLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# Minimum human-error prevention measures required at each criticality level.
REQUIRED_MEASURES: Dict[CriticalityLevel, Set[str]] = {
    CriticalityLevel.CRITICAL: {
        "confirmation_step",
        "interlock",
        "reversibility_check",
        "crew_notification",
        "dual_verification",
    },
    CriticalityLevel.HIGH: {
        "confirmation_step",
        "interlock",
        "reversibility_check",
        "crew_notification",
    },
    CriticalityLevel.MEDIUM: {
        "confirmation_step",
        "reversibility_check",
    },
    CriticalityLevel.LOW: set(),
}

# Levels that require operator-interface safeguards (state cues + go/no-go criteria).
INTERFACE_REQUIRED_LEVELS: FrozenSet[CriticalityLevel] = frozenset(
    {CriticalityLevel.CRITICAL, CriticalityLevel.HIGH}
)


@dataclass
class OperationRecord:
    name: str
    criticality: str          # One of CriticalityLevel values (case-insensitive)
    reversible: bool
    measures: List[str]       # Human-error prevention measures on record
    has_state_cues: bool      # Interface carries hazardous-state indication
    has_go_nogo_criteria: bool


@dataclass
class SafetyFinding:
    operation: str
    finding_type: str   # MISSING_MEASURE | MISSING_STATE_CUES | MISSING_GO_NOGO | IRREVERSIBLE_UNDERPROTECTED
    details: str


def parse_criticality(value: str) -> CriticalityLevel:
    """Parse a criticality string; raise ValueError for unknown values."""
    normalised = value.strip().upper()
    try:
        return CriticalityLevel(normalised)
    except ValueError:
        valid = [c.value for c in CriticalityLevel]
        raise ValueError(
            f"Unknown criticality level: '{value}'. Must be one of {valid}."
        )


def check_required_measures(op: OperationRecord) -> List[SafetyFinding]:
    """Return a finding for each measure required at op's criticality level that is absent."""
    crit = parse_criticality(op.criticality)
    required: Set[str] = REQUIRED_MEASURES[crit]
    present: Set[str] = set(op.measures)
    findings: List[SafetyFinding] = []
    for measure in sorted(required - present):
        findings.append(SafetyFinding(
            operation=op.name,
            finding_type="MISSING_MEASURE",
            details=(
                f"Measure '{measure}' required for {crit.value} criticality "
                f"but not present."
            ),
        ))
    return findings


def check_interface_requirements(op: OperationRecord) -> List[SafetyFinding]:
    """
    For CRITICAL and HIGH operations, verify the operator interface provides
    state cues and go/no-go criteria.
    """
    crit = parse_criticality(op.criticality)
    findings: List[SafetyFinding] = []
    if crit not in INTERFACE_REQUIRED_LEVELS:
        return findings
    if not op.has_state_cues:
        findings.append(SafetyFinding(
            operation=op.name,
            finding_type="MISSING_STATE_CUES",
            details=(
                f"{crit.value} operation requires clear state cues on the "
                f"operator interface (visual or auditory hazardous-state indication)."
            ),
        ))
    if not op.has_go_nogo_criteria:
        findings.append(SafetyFinding(
            operation=op.name,
            finding_type="MISSING_GO_NOGO",
            details=(
                f"{crit.value} operation requires documented go/no-go criteria."
            ),
        ))
    return findings


def check_irreversibility_protection(op: OperationRecord) -> List[SafetyFinding]:
    """
    An irreversible CRITICAL or HIGH operation must carry the full CRITICAL
    protection set regardless of nominal criticality level.
    """
    crit = parse_criticality(op.criticality)
    if op.reversible or crit not in INTERFACE_REQUIRED_LEVELS:
        return []
    full_set: Set[str] = REQUIRED_MEASURES[CriticalityLevel.CRITICAL]
    present: Set[str] = set(op.measures)
    missing = full_set - present
    if not missing:
        return []
    return [SafetyFinding(
        operation=op.name,
        finding_type="IRREVERSIBLE_UNDERPROTECTED",
        details=(
            f"Irreversible {crit.value} operation must carry the full CRITICAL "
            f"protection set. Missing: {sorted(missing)}."
        ),
    )]


def assess_operation(op: OperationRecord) -> List[SafetyFinding]:
    """Run all HFE safety checks on a single operation record."""
    findings: List[SafetyFinding] = []
    findings.extend(check_required_measures(op))
    findings.extend(check_interface_requirements(op))
    findings.extend(check_irreversibility_protection(op))
    return findings


def assess_catalogue(operations: List[OperationRecord]) -> Dict[str, List[SafetyFinding]]:
    """
    Assess every operation in a catalogue.
    Returns {operation_name: [SafetyFinding, ...]} for all operations;
    an empty list means the operation is compliant.
    """
    return {op.name: assess_operation(op) for op in operations}


def is_compliant(findings: List[SafetyFinding]) -> bool:
    """True when an operation carries no safety findings."""
    return len(findings) == 0
