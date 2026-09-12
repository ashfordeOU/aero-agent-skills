"""
Verification method selection logic — ECSS-E-ST-32C §4.6.1 / §4.6.2.1
Deterministic, offline, stdlib only.

Implements the method-acceptability table and programme-coverage checks
for selecting and agreeing structural verification methods.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional


class VerificationMethod(str, Enum):
    ANALYSIS = "A"
    TEST = "T"
    REVIEW_OF_DESIGN = "RoD"
    INSPECTION = "I"


class RequirementCategory(str, Enum):
    STRUCTURAL_STRENGTH = "structural_strength"
    STRUCTURAL_STIFFNESS = "structural_stiffness"
    MASS_PROPERTIES = "mass_properties"
    INTERFACE_GEOMETRY = "interface_geometry"
    FUNCTIONAL_PERFORMANCE = "functional_performance"
    ENVIRONMENTAL_QUALIFICATION = "environmental_qualification"
    WORKMANSHIP = "workmanship"


# Methods acceptable for each requirement category (§4.6.2.1).
ACCEPTABLE_METHODS: Dict[RequirementCategory, FrozenSet[VerificationMethod]] = {
    RequirementCategory.STRUCTURAL_STRENGTH: frozenset({
        VerificationMethod.ANALYSIS,
        VerificationMethod.TEST,
    }),
    RequirementCategory.STRUCTURAL_STIFFNESS: frozenset({
        VerificationMethod.ANALYSIS,
        VerificationMethod.TEST,
    }),
    RequirementCategory.MASS_PROPERTIES: frozenset({
        VerificationMethod.ANALYSIS,
        VerificationMethod.TEST,
        VerificationMethod.INSPECTION,
    }),
    RequirementCategory.INTERFACE_GEOMETRY: frozenset({
        VerificationMethod.ANALYSIS,
        VerificationMethod.INSPECTION,
        VerificationMethod.REVIEW_OF_DESIGN,
    }),
    RequirementCategory.FUNCTIONAL_PERFORMANCE: frozenset({
        VerificationMethod.ANALYSIS,
        VerificationMethod.TEST,
        VerificationMethod.REVIEW_OF_DESIGN,
    }),
    RequirementCategory.ENVIRONMENTAL_QUALIFICATION: frozenset({
        VerificationMethod.TEST,
        VerificationMethod.ANALYSIS,
    }),
    RequirementCategory.WORKMANSHIP: frozenset({
        VerificationMethod.INSPECTION,
        VerificationMethod.REVIEW_OF_DESIGN,
    }),
}

# Mandatory methods that must be present in every assignment for the category.
# Empty frozenset means no single method is unconditionally mandatory.
MANDATORY_METHODS: Dict[RequirementCategory, FrozenSet[VerificationMethod]] = {
    RequirementCategory.STRUCTURAL_STRENGTH: frozenset({VerificationMethod.ANALYSIS}),
    RequirementCategory.STRUCTURAL_STIFFNESS: frozenset({VerificationMethod.ANALYSIS}),
    RequirementCategory.MASS_PROPERTIES: frozenset(),
    RequirementCategory.INTERFACE_GEOMETRY: frozenset(),
    RequirementCategory.FUNCTIONAL_PERFORMANCE: frozenset(),
    RequirementCategory.ENVIRONMENTAL_QUALIFICATION: frozenset({VerificationMethod.TEST}),
    RequirementCategory.WORKMANSHIP: frozenset({VerificationMethod.INSPECTION}),
}


@dataclass
class Requirement:
    req_id: str
    category: RequirementCategory
    description: str
    assigned_methods: List[VerificationMethod] = field(default_factory=list)
    rationale: str = ""


@dataclass
class MethodSelectionResult:
    req_id: str
    is_valid: bool
    issues: List[str]
    assigned_methods: List[VerificationMethod]


@dataclass
class ProgrammeCoverageResult:
    total_requirements: int
    covered_requirements: int
    uncovered_requirements: List[str]
    invalid_assignments: List[MethodSelectionResult]
    is_programme_valid: bool
    coverage_percentage: float


def validate_method_selection(req: Requirement) -> MethodSelectionResult:
    """
    Validate the methods assigned to a single requirement.

    Checks:
    - At least one method is assigned.
    - Every assigned method is acceptable for the requirement category.
    - All mandatory methods for the category are present.
    """
    issues: List[str] = []

    if not req.assigned_methods:
        issues.append(
            f"{req.req_id}: no verification method assigned; "
            "at least one method is required before the programme begins"
        )
        return MethodSelectionResult(
            req_id=req.req_id,
            is_valid=False,
            issues=issues,
            assigned_methods=[],
        )

    acceptable = ACCEPTABLE_METHODS.get(req.category, frozenset())
    for method in req.assigned_methods:
        if method not in acceptable:
            issues.append(
                f"{req.req_id}: method {method.value!r} is not acceptable for "
                f"category {req.category.value!r}; "
                f"acceptable methods are {sorted(m.value for m in acceptable)}"
            )

    mandatory = MANDATORY_METHODS.get(req.category, frozenset())
    assigned_set = frozenset(req.assigned_methods)
    for required_method in mandatory:
        if required_method not in assigned_set:
            issues.append(
                f"{req.req_id}: mandatory method {required_method.value!r} is "
                f"absent for category {req.category.value!r}"
            )

    return MethodSelectionResult(
        req_id=req.req_id,
        is_valid=len(issues) == 0,
        issues=issues,
        assigned_methods=list(req.assigned_methods),
    )


def assess_programme_coverage(
    requirements: List[Requirement],
) -> ProgrammeCoverageResult:
    """
    Assess method coverage across the full verification programme.

    A programme is valid only when every requirement has at least one
    assigned method and every assignment passes validate_method_selection.
    """
    if not requirements:
        return ProgrammeCoverageResult(
            total_requirements=0,
            covered_requirements=0,
            uncovered_requirements=[],
            invalid_assignments=[],
            is_programme_valid=False,
            coverage_percentage=0.0,
        )

    uncovered: List[str] = []
    invalid: List[MethodSelectionResult] = []

    for req in requirements:
        if not req.assigned_methods:
            uncovered.append(req.req_id)
        result = validate_method_selection(req)
        if not result.is_valid:
            invalid.append(result)

    covered = len(requirements) - len(uncovered)
    coverage_pct = round((covered / len(requirements)) * 100.0, 2)
    is_valid = len(uncovered) == 0 and len(invalid) == 0

    return ProgrammeCoverageResult(
        total_requirements=len(requirements),
        covered_requirements=covered,
        uncovered_requirements=uncovered,
        invalid_assignments=invalid,
        is_programme_valid=is_valid,
        coverage_percentage=coverage_pct,
    )


def suggest_methods(
    category: RequirementCategory,
) -> List[VerificationMethod]:
    """
    Return methods for a requirement category in recommended priority order.
    Mandatory methods appear first; remaining acceptable methods follow.
    """
    mandatory = MANDATORY_METHODS.get(category, frozenset())
    acceptable = ACCEPTABLE_METHODS.get(category, frozenset())
    ordered: List[VerificationMethod] = sorted(mandatory, key=lambda m: m.value)
    for method in sorted(acceptable - mandatory, key=lambda m: m.value):
        ordered.append(method)
    return ordered


def parse_method(method_str: str) -> VerificationMethod:
    """
    Parse a method token to VerificationMethod.

    Accepts short forms (A, T, I) and long forms (ANALYSIS, TEST,
    REVIEW_OF_DESIGN, INSPECTION, ROD).
    Raises ValueError for unrecognized tokens.
    """
    _MAP: Dict[str, VerificationMethod] = {
        "A": VerificationMethod.ANALYSIS,
        "ANALYSIS": VerificationMethod.ANALYSIS,
        "T": VerificationMethod.TEST,
        "TEST": VerificationMethod.TEST,
        "ROD": VerificationMethod.REVIEW_OF_DESIGN,
        "REVIEW_OF_DESIGN": VerificationMethod.REVIEW_OF_DESIGN,
        "REVIEW OF DESIGN": VerificationMethod.REVIEW_OF_DESIGN,
        "I": VerificationMethod.INSPECTION,
        "INSPECTION": VerificationMethod.INSPECTION,
    }
    key = method_str.strip().upper()
    if key not in _MAP:
        raise ValueError(
            f"Unknown verification method: {method_str!r}. "
            f"Valid tokens: {sorted(_MAP)}"
        )
    return _MAP[key]


def parse_category(category_str: str) -> RequirementCategory:
    """
    Parse a category string to RequirementCategory.
    Raises ValueError for unrecognized categories.
    """
    _MAP: Dict[str, RequirementCategory] = {
        c.value.upper(): c for c in RequirementCategory
    }
    key = category_str.strip().upper()
    if key not in _MAP:
        raise ValueError(
            f"Unknown requirement category: {category_str!r}. "
            f"Valid categories: {sorted(c.value for c in RequirementCategory)}"
        )
    return _MAP[key]
