"""
Requirement-type categorization logic — ECSS-E-ST-10C §6.2.1–6.2.13.

Paraphrase of the ECSS requirement-type taxonomy; no verbatim standard text.
Anchor: ECSS-E-ST-10C §6.2.1 through §6.2.13.

The twelve types defined by the standard are:
  functional, mission, interface, environmental, operational, human_factor,
  ils, physical, pa_induced, configuration, design, verification.

Each requirement must belong to exactly one type.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Type registry  (ECSS-E-ST-10C §6.2.2 – §6.2.13)
# ---------------------------------------------------------------------------

VALID_TYPES: Tuple[str, ...] = (
    "functional",       # §6.2.2
    "mission",          # §6.2.3
    "interface",        # §6.2.4
    "environmental",    # §6.2.5
    "operational",      # §6.2.6
    "human_factor",     # §6.2.7
    "ils",              # §6.2.8
    "physical",         # §6.2.9
    "pa_induced",       # §6.2.10
    "configuration",    # §6.2.11
    "design",           # §6.2.12
    "verification",     # §6.2.13
)

# Aliases that callers may supply; all resolved to a canonical VALID_TYPES key.
_TYPE_ALIASES: Dict[str, str] = {
    "human factor": "human_factor",
    "human-factor": "human_factor",
    "humanfactor": "human_factor",
    "pa induced": "pa_induced",
    "pa-induced": "pa_induced",
    "painduced": "pa_induced",
    "integrated logistic support": "ils",
    "integrated logistics support": "ils",
    "logistic": "ils",
    "logistics": "ils",
}

# Keyword signals used for auto-scoring when no explicit type is supplied.
# These signals are heuristic only; explicit type assignment is authoritative.
_TYPE_SIGNALS: Dict[str, Tuple[str, ...]] = {
    "functional": (
        "shall perform",
        "shall provide",
        "shall compute",
        "shall generate",
        "capability",
        "function shall",
        "behavior shall",
        "shall process",
    ),
    "mission": (
        "orbit",
        "mission life",
        "design lifetime",
        "coverage",
        "revisit time",
        "launch window",
        "duty cycle",
        "mission phase",
        "mission objective",
    ),
    "interface": (
        "interface",
        "shall connect",
        "electrical connector",
        "data bus",
        "rf link",
        "mechanical interface",
        "icd",
        "interoperability",
    ),
    "environmental": (
        "temperature range",
        "radiation dose",
        "vibration",
        "vibration spectrum",
        "acoustic",
        "shock",
        "electromagnetic",
        "emc",
        "magnetic field",
        "humidity",
        "thermal environment",
        "particle fluence",
    ),
    "operational": (
        "operating mode",
        "shall be operated",
        "operating procedure",
        "operational timeline",
        "command sequence",
        "ground operation",
        "launch campaign",
        "commissioning",
        "safe mode",
    ),
    "human_factor": (
        "ergonomic",
        "human factor",
        "human-machine interface",
        "hmi",
        "alarm management",
        "training requirement",
        "usability",
        "workload",
    ),
    "ils": (
        "maintainability",
        "mean time to repair",
        "mttr",
        "spare parts",
        "logistic support",
        "supportability",
        "availability target",
    ),
    "physical": (
        "mass budget",
        "mass shall",
        "dimensional envelope",
        "overall dimensions",
        "volume shall",
        "centre of mass",
        "center of mass",
        "power budget",
        "footprint",
    ),
    "pa_induced": (
        "reliability",
        "safety requirement",
        "eee parts",
        "derating",
        "product assurance",
        "failure rate",
        "fmea",
        "fmeca",
        "pa plan",
        "quality assurance",
    ),
    "configuration": (
        "configuration item",
        "configuration control",
        "baseline",
        "configuration identification",
        "change control board",
        "ccb",
    ),
    "design": (
        "shall use material",
        "material selection",
        "manufacturing process",
        "design standard",
        "design rule",
        "heritage design",
        "shall comply with standard",
        "design constraint",
    ),
    "verification": (
        "shall be verified",
        "shall be tested",
        "shall be inspected",
        "shall be demonstrated",
        "qualification test",
        "acceptance test",
        "verification method",
        "test procedure",
    ),
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RequirementRecord:
    """A single requirement presented for type assignment."""
    req_id: str
    text: str
    explicit_type: Optional[str] = None  # caller-supplied type label; None → auto-score


@dataclass
class TypeResult:
    """Outcome of type assignment for one requirement."""
    req_id: str
    text: str
    assigned_type: Optional[str]
    rationale: str
    error: Optional[str] = None

    @property
    def is_categorized(self) -> bool:
        return self.assigned_type is not None and self.error is None


@dataclass
class BatchReport:
    """Consolidated result from categorizing a list of requirements."""
    results: List[TypeResult] = field(default_factory=list)
    uncategorized_ids: List[str] = field(default_factory=list)

    @property
    def all_categorized(self) -> bool:
        return len(self.uncategorized_ids) == 0

    @property
    def type_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {t: 0 for t in VALID_TYPES}
        for r in self.results:
            if r.assigned_type:
                counts[r.assigned_type] = counts.get(r.assigned_type, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalise_type(raw: str) -> Optional[str]:
    """Return the canonical type key for *raw*, or None if unrecognised."""
    stripped = raw.strip()
    # Direct match (underscore form)
    key = stripped.lower().replace("-", "_")
    if key in VALID_TYPES:
        return key
    # Space-separated alias
    alias_key = stripped.lower()
    if alias_key in _TYPE_ALIASES:
        return _TYPE_ALIASES[alias_key]
    # Hyphen-normalised alias
    hyphen_key = stripped.lower()
    for alias, canonical in _TYPE_ALIASES.items():
        if hyphen_key == alias:
            return canonical
    return None


def _score_text(text: str) -> Dict[str, int]:
    """Score each requirement type by keyword signal matches in *text*."""
    lower = text.lower()
    return {
        req_type: sum(1 for signal in signals if signal in lower)
        for req_type, signals in _TYPE_SIGNALS.items()
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def categorize_requirement(record: RequirementRecord) -> TypeResult:
    """
    Assign exactly one requirement type to *record*.

    Assignment rules (applied in order):
    1. If ``explicit_type`` is provided, validate it and return the canonical
       type. Invalid label → TypeResult with error set.
    2. Otherwise auto-score *text* against _TYPE_SIGNALS. The single
       highest-scoring type wins.
       - Zero score → error (no signal found; explicit type required).
       - Tie between two or more types → error (ambiguous; explicit type required).
    """
    if record.explicit_type is not None:
        canonical = _normalise_type(record.explicit_type)
        if canonical is None:
            return TypeResult(
                req_id=record.req_id,
                text=record.text,
                assigned_type=None,
                rationale="",
                error=(
                    f"Unknown requirement type '{record.explicit_type}'. "
                    f"Valid types: {', '.join(VALID_TYPES)}."
                ),
            )
        return TypeResult(
            req_id=record.req_id,
            text=record.text,
            assigned_type=canonical,
            rationale=f"Caller-supplied type '{record.explicit_type}' resolved to '{canonical}'.",
        )

    # Auto-scoring path
    scores = _score_text(record.text)
    max_score = max(scores.values())

    if max_score == 0:
        return TypeResult(
            req_id=record.req_id,
            text=record.text,
            assigned_type=None,
            rationale="",
            error=(
                "No keyword signal matched any requirement type. "
                "Provide explicit_type to assign this requirement."
            ),
        )

    top_types = [t for t, s in scores.items() if s == max_score]

    if len(top_types) > 1:
        return TypeResult(
            req_id=record.req_id,
            text=record.text,
            assigned_type=None,
            rationale="",
            error=(
                f"Ambiguous: signals match equally for "
                f"{', '.join(sorted(top_types))}. "
                "Provide explicit_type to resolve."
            ),
        )

    winner = top_types[0]
    return TypeResult(
        req_id=record.req_id,
        text=record.text,
        assigned_type=winner,
        rationale=(
            f"Auto-scored: highest signal count for '{winner}' "
            f"(score={max_score})."
        ),
    )


def categorize_batch(records: List[RequirementRecord]) -> BatchReport:
    """
    Categorize a list of requirements and return a consolidated BatchReport.

    Requirements that cannot be assigned a type are listed in
    ``BatchReport.uncategorized_ids``.
    """
    report = BatchReport()
    for record in records:
        result = categorize_requirement(record)
        report.results.append(result)
        if not result.is_categorized:
            report.uncategorized_ids.append(record.req_id)
    return report


def validate_type_coverage(records: List[RequirementRecord]) -> List[str]:
    """
    Return a list of type labels that appear in *records* but are not in
    VALID_TYPES. An empty list means all explicitly-supplied types are valid.
    """
    invalid: List[str] = []
    for record in records:
        if record.explicit_type is not None:
            if _normalise_type(record.explicit_type) is None:
                invalid.append(record.explicit_type)
    return invalid
