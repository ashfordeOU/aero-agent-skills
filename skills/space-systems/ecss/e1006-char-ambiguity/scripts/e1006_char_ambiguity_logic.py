"""
e1006_char_ambiguity_logic.py

ECSS-E-ST-10C §8.2.4 — Requirement ambiguity check.

A requirement is unambiguous when it admits exactly one interpretation:
every reader derives the same meaning from the same text. This module
flags four ambiguity categories and returns structured findings.

Anchor: ECSS-E-ST-10C clause §8.2.4 (paraphrased — no verbatim standard text).
stdlib only; offline; deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Sequence, Tuple


class AmbiguityCategory(str, Enum):
    VAGUE_TERM = "vague_term"
    WEASEL_QUALIFIER = "weasel_qualifier"
    COMPOUND_CONNECTIVE = "compound_connective"
    IMPLICIT_SUBJECT = "implicit_subject"


class Severity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class AmbiguityFinding:
    requirement_id: str
    term: str
    category: AmbiguityCategory
    description: str
    severity: Severity


@dataclass
class AmbiguityResult:
    requirement_id: str
    text: str
    findings: List[AmbiguityFinding] = field(default_factory=list)

    @property
    def is_unambiguous(self) -> bool:
        return len(self.findings) == 0

    @property
    def finding_count(self) -> int:
        return len(self.findings)


# Vague qualitative terms: subjective without a measurable bound.
# Pattern → Severity
_VAGUE_TERMS: List[Tuple[str, Severity]] = [
    (r"\badequate\b", Severity.HIGH),
    (r"\bsufficient\b", Severity.HIGH),
    (r"\bappropriate\b", Severity.HIGH),
    (r"\boptimal\b", Severity.HIGH),
    (r"\boptimum\b", Severity.HIGH),
    (r"\bflexible\b", Severity.MEDIUM),
    (r"\breasonable\b", Severity.HIGH),
    (r"\buser[- ]friendly\b", Severity.HIGH),
    (r"\beasy\b", Severity.MEDIUM),
    (r"\bfast\b", Severity.MEDIUM),
    (r"\bslow\b", Severity.MEDIUM),
    (r"\bgood\b", Severity.MEDIUM),
    (r"\brobust\b", Severity.MEDIUM),
    (r"\bsimple\b", Severity.MEDIUM),
    (r"\bminimize\b", Severity.MEDIUM),
    (r"\bminimise\b", Severity.MEDIUM),
    (r"\bmaximize\b", Severity.MEDIUM),
    (r"\bmaximise\b", Severity.MEDIUM),
    (r"\betc\.?\b", Severity.HIGH),
    (r"\band\s+so\s+on\b", Severity.HIGH),
    (r"\bsupport\b", Severity.LOW),
]

# Weasel qualifiers: escape clauses, placeholders, conditional deferrals.
_WEASEL_QUALIFIERS: List[Tuple[str, Severity]] = [
    (r"\bTBD\b", Severity.HIGH),
    (r"\bTBC\b", Severity.HIGH),
    (r"\bTBR\b", Severity.HIGH),
    (r"\bas\s+required\b", Severity.HIGH),
    (r"\bas\s+necessary\b", Severity.HIGH),
    (r"\bas\s+applicable\b", Severity.MEDIUM),
    (r"\bif\s+required\b", Severity.MEDIUM),
    (r"\bif\s+necessary\b", Severity.MEDIUM),
    (r"\bwhere\s+possible\b", Severity.HIGH),
    (r"\bwhere\s+practicable\b", Severity.HIGH),
    (r"\bto\s+be\s+defined\b", Severity.HIGH),
    (r"\bto\s+be\s+determined\b", Severity.HIGH),
]

# Compound connective "and/or" is inherently ambiguous.
_COMPOUND_CONNECTIVE_RE = re.compile(r"\band/or\b", re.IGNORECASE)

# Implicit subject: text begins with a modal/action verb without a named subject.
_IMPLICIT_SUBJECT_RE = re.compile(
    r"^\s*(shall|should|must|will|may|can|provide|ensure|support|enable|allow|handle)\b",
    re.IGNORECASE,
)


def _scan_pattern_list(
    req_id: str,
    text: str,
    patterns: List[Tuple[str, Severity]],
    category: AmbiguityCategory,
    description_template: str,
) -> List[AmbiguityFinding]:
    findings: List[AmbiguityFinding] = []
    for pattern, severity in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            findings.append(
                AmbiguityFinding(
                    requirement_id=req_id,
                    term=m.group(0),
                    category=category,
                    description=description_template.format(term=m.group(0)),
                    severity=severity,
                )
            )
    return findings


def check_requirement_ambiguity(req_id: str, text: str) -> AmbiguityResult:
    """Return an AmbiguityResult for a single requirement text.

    Raises ValueError for empty req_id or blank text.
    """
    if not req_id or not req_id.strip():
        raise ValueError("req_id must be a non-empty string")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"requirement text for '{req_id}' must be a non-empty string")

    result = AmbiguityResult(requirement_id=req_id, text=text)

    # 1. Vague qualitative terms
    result.findings.extend(
        _scan_pattern_list(
            req_id,
            text,
            _VAGUE_TERMS,
            AmbiguityCategory.VAGUE_TERM,
            "Vague qualitative term '{term}' has no measurable bound; "
            "replace with a specific, verifiable criterion.",
        )
    )

    # 2. Weasel qualifiers
    result.findings.extend(
        _scan_pattern_list(
            req_id,
            text,
            _WEASEL_QUALIFIERS,
            AmbiguityCategory.WEASEL_QUALIFIER,
            "Weasel qualifier '{term}' defers the requirement; "
            "replace with a concrete value or remove the conditional.",
        )
    )

    # 3. Compound connective
    for m in _COMPOUND_CONNECTIVE_RE.finditer(text):
        result.findings.append(
            AmbiguityFinding(
                requirement_id=req_id,
                term=m.group(0),
                category=AmbiguityCategory.COMPOUND_CONNECTIVE,
                description=(
                    "Compound connective 'and/or' is ambiguous; rewrite as two "
                    "separate requirements or use explicit inclusive/exclusive language."
                ),
                severity=Severity.HIGH,
            )
        )

    # 4. Implicit subject
    if _IMPLICIT_SUBJECT_RE.match(text.strip()):
        result.findings.append(
            AmbiguityFinding(
                requirement_id=req_id,
                term=text.strip().split()[0],
                category=AmbiguityCategory.IMPLICIT_SUBJECT,
                description=(
                    "Requirement begins with a modal/action verb without an explicit "
                    "subject; state the system element this requirement applies to."
                ),
                severity=Severity.MEDIUM,
            )
        )

    return result


def check_requirements_batch(
    requirements: Sequence[Tuple[str, str]],
) -> Dict[str, AmbiguityResult]:
    """Check a sequence of (req_id, text) pairs.

    Returns a dict keyed by req_id.
    Raises ValueError on duplicate req_id.
    """
    results: Dict[str, AmbiguityResult] = {}
    for req_id, text in requirements:
        if req_id in results:
            raise ValueError(f"Duplicate requirement id: '{req_id}'")
        results[req_id] = check_requirement_ambiguity(req_id, text)
    return results


def summarize_batch(results: Dict[str, AmbiguityResult]) -> Dict[str, object]:
    """Produce a summary dict for a batch result."""
    total = len(results)
    unambiguous = sum(1 for r in results.values() if r.is_unambiguous)
    flagged = total - unambiguous
    by_category: Dict[str, int] = {}
    for r in results.values():
        for f in r.findings:
            key = f.category.value
            by_category[key] = by_category.get(key, 0) + 1
    return {
        "total_requirements": total,
        "unambiguous": unambiguous,
        "flagged": flagged,
        "findings_by_category": by_category,
    }
