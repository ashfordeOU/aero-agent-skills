"""e1006_char_justification_logic.py — ECSS-E-ST-10C §8.2.2 requirement justification checker.

Verifies that each requirement entry carries a recorded justification (rationale)
and a traceable source reference.  Stdlib only, deterministic, offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Set

VALID_SOURCE_KINDS: frozenset = frozenset({
    "stakeholder_need",
    "mission_objective",
    "standard_clause",
    "derived",
    "safety_argument",
    "interface_requirement",
    "operational_concept",
})


@dataclass(frozen=True)
class Requirement:
    req_id: str
    text: str
    justification: str
    justification_source: str
    source_kind: str  # must be one of VALID_SOURCE_KINDS


@dataclass(frozen=True)
class JustificationFinding:
    req_id: str
    verdict: str   # "compliant" | "non-compliant"
    reason: str    # empty string when compliant


@dataclass
class JustificationReport:
    findings: List[JustificationFinding] = field(default_factory=list)

    @property
    def compliant_count(self) -> int:
        return sum(1 for f in self.findings if f.verdict == "compliant")

    @property
    def non_compliant_count(self) -> int:
        return sum(1 for f in self.findings if f.verdict == "non-compliant")

    @property
    def is_fully_compliant(self) -> bool:
        return self.non_compliant_count == 0


def check_requirement_justification(req: Requirement) -> JustificationFinding:
    """Return a finding for a single requirement's justification record."""
    if not req.req_id or not req.req_id.strip():
        return JustificationFinding(
            req_id="<missing-id>",
            verdict="non-compliant",
            reason="requirement id is absent",
        )

    req_id = req.req_id.strip()
    reasons: List[str] = []

    if not req.justification or not req.justification.strip():
        reasons.append("justification field is absent or empty")

    if not req.justification_source or not req.justification_source.strip():
        reasons.append("justification source reference is absent or empty")
    elif req.source_kind not in VALID_SOURCE_KINDS:
        reasons.append(
            "source_kind '{}' is not a recognised category "
            "(expected one of: {})".format(
                req.source_kind, ", ".join(sorted(VALID_SOURCE_KINDS))
            )
        )

    if reasons:
        return JustificationFinding(
            req_id=req_id,
            verdict="non-compliant",
            reason="; ".join(reasons),
        )

    return JustificationFinding(req_id=req_id, verdict="compliant", reason="")


def assess_justification_set(requirements: List[Requirement]) -> JustificationReport:
    """Assess justification completeness for a list of requirements.

    Raises ValueError when the input list is empty.
    Flags duplicate requirement IDs as non-compliant.
    """
    if not requirements:
        raise ValueError("requirement set must not be empty")

    report = JustificationReport()
    seen_ids: Set[str] = set()

    for req in requirements:
        req_id = (req.req_id or "").strip()
        if req_id and req_id in seen_ids:
            report.findings.append(
                JustificationFinding(
                    req_id=req_id,
                    verdict="non-compliant",
                    reason="duplicate requirement id",
                )
            )
            continue
        if req_id:
            seen_ids.add(req_id)
        report.findings.append(check_requirement_justification(req))

    return report
