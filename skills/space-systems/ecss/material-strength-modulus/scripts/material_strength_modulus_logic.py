"""
ECSS E-ST-32C Clauses 4.2.1-4.2.2: Material Strength and Elastic Modulus Properties.
Deterministic, offline, stdlib-only implementation.
"""

import math
from typing import Tuple

# --- Input validation helpers ---

def _require_positive(value: float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def _require_non_negative(value: float, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")


# --- Elastic modulus relationships (Clause 4.2.2) ---

def compute_shear_modulus(youngs_modulus: float, poisson_ratio: float) -> float:
    """
    Derive shear modulus from Young's modulus and Poisson's ratio for an isotropic material.
    G = E / (2 * (1 + nu))

    Args:
        youngs_modulus: Young's modulus E (Pa or consistent unit, must be > 0).
        poisson_ratio: Poisson's ratio nu, must be in the open interval (-1, 0.5).

    Returns:
        Shear modulus G in the same units as E.

    Raises:
        ValueError: if youngs_modulus <= 0 or poisson_ratio outside (-1, 0.5).
    """
    _require_positive(youngs_modulus, "Young's modulus")
    if not (-1.0 < poisson_ratio < 0.5):
        raise ValueError(
            f"Poisson's ratio must be in the open interval (-1, 0.5), got {poisson_ratio}"
        )
    return youngs_modulus / (2.0 * (1.0 + poisson_ratio))


def check_modulus_consistency(
    youngs_modulus: float,
    shear_modulus: float,
    poisson_ratio: float,
    tolerance: float = 0.02,
) -> Tuple[bool, float]:
    """
    Verify that the supplied shear modulus is consistent with G = E/(2(1+nu))
    within a fractional tolerance (default 2 %).

    Returns:
        (is_consistent, relative_error) where relative_error = |G_supplied - G_expected| / G_expected.
    """
    _require_positive(youngs_modulus, "Young's modulus")
    _require_positive(shear_modulus, "shear modulus")
    expected_g = compute_shear_modulus(youngs_modulus, poisson_ratio)
    rel_error = abs(shear_modulus - expected_g) / expected_g
    return rel_error <= tolerance, rel_error


# --- Multiaxial yield criteria ---

def von_mises_equivalent_stress(s1: float, s2: float, s3: float = 0.0) -> float:
    """
    Compute the von Mises equivalent stress for a principal-stress state (s1, s2, s3).
    sigma_vm = sqrt(0.5 * ((s1-s2)^2 + (s2-s3)^2 + (s3-s1)^2))

    A 2D state is obtained by setting s3 = 0 (default).
    """
    return math.sqrt(
        0.5 * ((s1 - s2) ** 2 + (s2 - s3) ** 2 + (s3 - s1) ** 2)
    )


def von_mises_yield_check(
    s1: float, s2: float, s3: float, fty: float
) -> Tuple[bool, float, float]:
    """
    Check whether a 3D principal-stress state satisfies the von Mises yield criterion.

    Args:
        s1, s2, s3: Principal stresses (same units as fty).
        fty: Tensile yield strength allowable (must be > 0).

    Returns:
        (passed, sigma_vm, margin_of_safety)
        margin_of_safety = fty / sigma_vm - 1; positive means compliant.
        Returns inf margin when all stresses are zero.
    """
    _require_positive(fty, "Fty")
    sigma_vm = von_mises_equivalent_stress(s1, s2, s3)
    if sigma_vm == 0.0:
        return True, 0.0, float("inf")
    ms = fty / sigma_vm - 1.0
    return ms >= 0.0, sigma_vm, ms


def tresca_equivalent_stress(s1: float, s2: float, s3: float) -> float:
    """
    Compute the Tresca (maximum-shear-stress) equivalent stress for a principal-stress state.
    sigma_T = max(|s1-s2|, |s2-s3|, |s3-s1|)

    This equals twice the maximum shear stress and is the quantity compared against Fty.
    """
    return max(abs(s1 - s2), abs(s2 - s3), abs(s3 - s1))


def tresca_yield_check(
    s1: float, s2: float, s3: float, fty: float
) -> Tuple[bool, float, float]:
    """
    Check whether a principal-stress state satisfies the Tresca yield criterion.

    Args:
        s1, s2, s3: Principal stresses (same units as fty).
        fty: Tensile yield strength allowable (must be > 0).

    Returns:
        (passed, sigma_tresca, margin_of_safety)
    """
    _require_positive(fty, "Fty")
    sigma_tresca = tresca_equivalent_stress(s1, s2, s3)
    if sigma_tresca == 0.0:
        return True, 0.0, float("inf")
    ms = fty / sigma_tresca - 1.0
    return ms >= 0.0, sigma_tresca, ms


# --- Margin of safety ---

def margin_of_safety(allowable: float, applied: float) -> float:
    """
    Compute the margin of safety: MS = allowable / applied - 1.
    Positive MS indicates the allowable is not exceeded.

    Args:
        allowable: Strength allowable (must be > 0).
        applied:   Applied stress or load intensity (must be > 0).
    """
    _require_positive(allowable, "allowable")
    _require_positive(applied, "applied")
    return allowable / applied - 1.0


# --- Allowable ordering check ---

def check_ftu_fty_ordering(ftu: float, fty: float) -> bool:
    """
    Verify that ultimate tensile strength strictly exceeds tensile yield strength (Ftu > Fty).
    Required for ductile metallic alloys where plastic deformation precedes fracture.
    """
    _require_positive(ftu, "Ftu")
    _require_positive(fty, "Fty")
    return ftu > fty


# --- Environmental knockdown ---

def apply_knockdown_factor(base_allowable: float, knockdown: float) -> float:
    """
    Apply an environmental knockdown factor to a base strength allowable.

    Args:
        base_allowable: Room-temperature, baseline allowable (must be > 0).
        knockdown:      Multiplicative reduction factor in the range (0, 1].
                        1.0 means no reduction; values below 1.0 reduce the allowable.

    Returns:
        Reduced design allowable = base_allowable * knockdown.

    Raises:
        ValueError: if knockdown is not in (0, 1].
    """
    _require_positive(base_allowable, "base allowable")
    if not (0.0 < knockdown <= 1.0):
        raise ValueError(
            f"knockdown must be in the range (0, 1], got {knockdown}"
        )
    return base_allowable * knockdown


# --- Data-source categorization ---

RECOGNIZED_SOURCE_TYPES = frozenset({
    "test-coupon",
    "material-handbook",
    "qualification-database",
    "supplier-datasheet",
})


def categorize_property_source(source_type: str) -> str:
    """
    Categorize a material property data source as accepted or rejected.
    Only sources traceable to recognized provenance types are accepted.

    Returns:
        'accepted' if source_type is a recognized provenance type; 'rejected' otherwise.
    """
    if source_type in RECOGNIZED_SOURCE_TYPES:
        return "accepted"
    return "rejected"


# --- Allowable basis (A-basis / B-basis) ---

def select_allowable_basis(is_fracture_critical: bool) -> str:
    """
    Return the minimum required statistical basis for a given part criticality.

    Fracture-critical or single-load-path elements require A-basis
    (99th-percentile strength, 95 % confidence).
    Non-fracture-critical redundant-load-path elements require at minimum B-basis
    (90th-percentile strength, 95 % confidence).
    """
    return "A-basis" if is_fracture_critical else "B-basis"


# Hierarchy: A-basis > B-basis > unknown
_BASIS_RANK = {"A-basis": 2, "B-basis": 1}


def check_basis_requirement(
    provided_basis: str, is_fracture_critical: bool
) -> Tuple[bool, str]:
    """
    Verify that the provided statistical allowable basis meets the minimum requirement.

    A-basis satisfies requirements for both fracture-critical and non-fracture-critical parts.
    B-basis satisfies only non-fracture-critical requirements.

    Returns:
        (compliant, required_basis) where compliant is True when the provided
        basis meets or exceeds the required level.
    """
    required = select_allowable_basis(is_fracture_critical)
    provided_rank = _BASIS_RANK.get(provided_basis, 0)
    required_rank = _BASIS_RANK.get(required, 0)
    return provided_rank >= required_rank, required
