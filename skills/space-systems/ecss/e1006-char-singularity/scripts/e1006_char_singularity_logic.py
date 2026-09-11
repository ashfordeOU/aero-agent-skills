"""
e1006_char_singularity_logic.py

Singularity check for ECSS-E-ST-10-06C §8.2.7.
Each requirement statement must express exactly one requirement.
Compound statements violate singularity and must be split.

stdlib only — no third-party dependencies.
"""

import re
from dataclasses import dataclass, field
from typing import List


# ---------------------------------------------------------------------------
# Violation patterns
# Each entry: (pattern_id, compiled_regex, description, recommendation)
# ---------------------------------------------------------------------------

_VIOLATION_CHECKS = [
    (
        "multiple-shall",
        re.compile(r"\bshall\b.*\bshall\b", re.IGNORECASE | re.DOTALL),
        (
            "Statement contains more than one 'shall', indicating that "
            "multiple requirements have been merged into one statement."
        ),
        "Split into separate statements, each with a single 'shall' clause.",
    ),
    (
        "and-shall",
        re.compile(r"\band\s+shall\b", re.IGNORECASE),
        (
            "'and shall' explicitly joins two modal clauses, confirming "
            "two independent requirements in one statement."
        ),
        "Separate each 'and shall' clause into its own requirement statement.",
    ),
    (
        "as-well-as",
        re.compile(r"\bas\s+well\s+as\b", re.IGNORECASE),
        (
            "'as well as' is an additive conjunction that embeds a "
            "secondary requirement obligation."
        ),
        "Replace 'as well as' with a separate requirement statement.",
    ),
    (
        "in-addition-to",
        re.compile(r"\bin\s+addition\s+to\b", re.IGNORECASE),
        (
            "'in addition to' introduces a secondary requirement, "
            "violating singularity."
        ),
        "Express the additional requirement as a standalone statement.",
    ),
    (
        "shall-list",
        re.compile(r"\bshall\s*:", re.IGNORECASE),
        (
            "'shall:' introduces a list where each item is likely a "
            "separate requirement; the entire construct bundles multiple "
            "obligations under one modal."
        ),
        (
            "Expand each list item into its own 'shall' statement, "
            "each with a unique identifier."
        ),
    ),
    (
        "compound-predicate",
        re.compile(
            r"\bshall\b[^.;:]*\band\b[^.;:]*"
            r"\b(?:be|have|provide|ensure|perform|maintain|support|allow|"
            r"enable|contain|include|transmit|receive|store|process|generate|"
            r"report|monitor|control|verify|validate|detect|measure|record|"
            r"display|output|compute|calculate|allocate|manage|handle|"
            r"execute|initiate|terminate|send|accept|reject)\b",
            re.IGNORECASE,
        ),
        (
            "'and' joins a second action verb after 'shall', suggesting "
            "two independent requirement predicates have been merged."
        ),
        (
            "Extract the second predicate into a separate requirement "
            "statement so each 'shall' clause stands alone."
        ),
    ),
]

# Pattern IDs that are definitive (not heuristic).
_DEFINITIVE_PATTERNS = {"multiple-shall", "and-shall", "as-well-as", "in-addition-to", "shall-list"}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SingularityViolation:
    pattern_id: str
    description: str
    recommendation: str


@dataclass
class SingularityResult:
    statement: str
    compliant: bool
    violations: List[SingularityViolation] = field(default_factory=list)
    shall_count: int = 0


# ---------------------------------------------------------------------------
# Core check
# ---------------------------------------------------------------------------

def _count_shall(text: str) -> int:
    return len(re.findall(r"\bshall\b", text, re.IGNORECASE))


def check_singularity(statement: str) -> SingularityResult:
    """
    Check a single requirement statement for singularity violations.

    Raises ValueError for non-string input or empty/whitespace-only string.
    Returns a SingularityResult; compliant is True when no violations are found.
    """
    if not isinstance(statement, str):
        raise ValueError(
            f"statement must be a str, got {type(statement).__name__}"
        )
    stripped = statement.strip()
    if not stripped:
        raise ValueError("statement must not be empty or whitespace-only")

    shall_count = _count_shall(stripped)
    violations: List[SingularityViolation] = []

    for pattern_id, regex, description, recommendation in _VIOLATION_CHECKS:
        if regex.search(stripped):
            violations.append(
                SingularityViolation(
                    pattern_id=pattern_id,
                    description=description,
                    recommendation=recommendation,
                )
            )

    # When a definitive pattern fires, suppress the compound-predicate heuristic
    # to avoid a redundant lower-confidence message alongside a stronger signal.
    has_definitive = any(v.pattern_id in _DEFINITIVE_PATTERNS for v in violations)
    if has_definitive:
        violations = [
            v for v in violations if v.pattern_id != "compound-predicate"
        ]

    return SingularityResult(
        statement=stripped,
        compliant=len(violations) == 0,
        violations=violations,
        shall_count=shall_count,
    )


# ---------------------------------------------------------------------------
# Batch check
# ---------------------------------------------------------------------------

def check_requirement_set(statements: list) -> List[SingularityResult]:
    """
    Check a list of requirement statements for singularity.

    Raises TypeError if statements is not a list.
    Raises ValueError if the list is empty.
    Per-statement errors (empty string, non-string) propagate as ValueError.
    Returns one SingularityResult per input statement, in input order.
    """
    if not isinstance(statements, list):
        raise TypeError(
            f"statements must be a list, got {type(statements).__name__}"
        )
    if len(statements) == 0:
        raise ValueError("statements list must not be empty")
    return [check_singularity(s) for s in statements]


# ---------------------------------------------------------------------------
# Summary helper
# ---------------------------------------------------------------------------

def summary(results: List[SingularityResult]) -> dict:
    """
    Summarise a list of SingularityResult objects.

    Returns a dict with:
      total               — total number of statements checked
      compliant_count     — number of statements with no violations
      non_compliant_count — number of statements with one or more violations
      non_compliant_indices — list of zero-based indices of non-compliant statements
    """
    if not isinstance(results, list):
        raise TypeError("results must be a list of SingularityResult")
    non_compliant_indices = [i for i, r in enumerate(results) if not r.compliant]
    return {
        "total": len(results),
        "compliant_count": len(results) - len(non_compliant_indices),
        "non_compliant_count": len(non_compliant_indices),
        "non_compliant_indices": non_compliant_indices,
    }
