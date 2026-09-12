"""
Buckling analysis logic for ECSS-E-ST-32C Annex M structural buckling report.

Implements deterministic procedures for:
  - Member geometry categorization (column, flat plate, shell)
  - Effective length factor resolution from boundary conditions
  - Euler and Johnson column critical stress
  - Flat plate critical stress
  - Knock-down factor application
  - Margin of safety evaluation

Reference: ECSS-E-ST-32C Annex M (paraphrased; no verbatim standard text).
"""

import math

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_MEMBER_CATEGORIES = {"column", "flat_plate", "shell"}

# Effective length factors for standard column boundary conditions.
# Source: classical beam-column theory, cited in ECSS-E-ST-32C Annex M.
BOUNDARY_CONDITION_K = {
    "pin-pin": 1.0,
    "fix-fix": 0.5,
    "fix-pin": 0.6991,   # theoretical value ≈ 0.699
    "fix-free": 2.0,
    "fix-guided": 1.0,
}


# ---------------------------------------------------------------------------
# Member categorization
# ---------------------------------------------------------------------------

def categorize_member(geometry_type: str) -> str:
    """
    Confirm the geometry type is a recognized structural category.
    Returns the category string unchanged if valid; raises ValueError otherwise.
    The three valid categories are: 'column', 'flat_plate', 'shell'.
    """
    candidate = geometry_type.lower().strip()
    if candidate not in VALID_MEMBER_CATEGORIES:
        raise ValueError(
            f"Unknown member geometry '{geometry_type}'. "
            f"Valid categories: {sorted(VALID_MEMBER_CATEGORIES)}."
        )
    return candidate


# ---------------------------------------------------------------------------
# Effective length factor
# ---------------------------------------------------------------------------

def effective_length_factor(boundary_condition: str) -> float:
    """
    Return the effective length factor K for a column from its boundary
    condition description.  Raises ValueError for unrecognised conditions.
    """
    key = boundary_condition.lower().strip()
    if key not in BOUNDARY_CONDITION_K:
        raise ValueError(
            f"Unknown boundary condition '{boundary_condition}'. "
            f"Valid options: {sorted(BOUNDARY_CONDITION_K)}."
        )
    return BOUNDARY_CONDITION_K[key]


# ---------------------------------------------------------------------------
# Slenderness and transition
# ---------------------------------------------------------------------------

def slenderness_ratio(K: float, L: float, r: float) -> float:
    """
    Compute the column slenderness ratio KL/r.
    All arguments must be strictly positive.
    """
    if K <= 0:
        raise ValueError("Effective length factor K must be positive.")
    if L <= 0:
        raise ValueError("Column length L must be positive.")
    if r <= 0:
        raise ValueError("Radius of gyration r must be positive.")
    return K * L / r


def transition_slenderness(E: float, sigma_y: float) -> float:
    """
    Compute the slenderness ratio at the Euler/Johnson transition:
        (KL/r)_t = pi * sqrt(2E / sigma_y)
    Members above this value are in the Euler range; below it, Johnson range.
    """
    if E <= 0:
        raise ValueError("Elastic modulus E must be positive.")
    if sigma_y <= 0:
        raise ValueError("Yield stress sigma_y must be positive.")
    return math.pi * math.sqrt(2.0 * E / sigma_y)


# ---------------------------------------------------------------------------
# Critical stress formulae
# ---------------------------------------------------------------------------

def euler_critical_stress(E: float, KL_r: float) -> float:
    """
    Euler critical compressive stress for long (slender) columns:
        sigma_cr = pi^2 * E / (KL/r)^2
    Valid for slenderness ratios at or above the Euler/Johnson transition.
    """
    if E <= 0:
        raise ValueError("Elastic modulus E must be positive.")
    if KL_r <= 0:
        raise ValueError("Slenderness ratio KL/r must be positive.")
    return (math.pi ** 2 * E) / (KL_r ** 2)


def johnson_critical_stress(E: float, sigma_y: float, KL_r: float) -> float:
    """
    Johnson parabolic critical compressive stress for intermediate columns:
        sigma_cr = sigma_y * [1 - sigma_y * (KL/r)^2 / (4 * pi^2 * E)]
    Valid for slenderness ratios below the Euler/Johnson transition.
    """
    if E <= 0:
        raise ValueError("Elastic modulus E must be positive.")
    if sigma_y <= 0:
        raise ValueError("Yield stress sigma_y must be positive.")
    if KL_r <= 0:
        raise ValueError("Slenderness ratio KL/r must be positive.")
    return sigma_y * (1.0 - sigma_y * KL_r ** 2 / (4.0 * math.pi ** 2 * E))


def select_column_formula(
    E: float, sigma_y: float, K: float, L: float, r: float
) -> dict:
    """
    Determine the governing column buckling formula (Euler or Johnson),
    compute the theoretical critical stress, and return all intermediate values.

    Returns:
        regime       : "euler" or "johnson"
        K            : effective length factor used
        KL_r         : slenderness ratio
        KL_r_transition: transition slenderness
        sigma_cr     : theoretical critical stress (before knock-down)
    """
    kl_r = slenderness_ratio(K, L, r)
    kl_r_t = transition_slenderness(E, sigma_y)
    if kl_r >= kl_r_t:
        sigma_cr = euler_critical_stress(E, kl_r)
        regime = "euler"
    else:
        sigma_cr = johnson_critical_stress(E, sigma_y, kl_r)
        regime = "johnson"
    return {
        "regime": regime,
        "K": K,
        "KL_r": kl_r,
        "KL_r_transition": kl_r_t,
        "sigma_cr": sigma_cr,
    }


def flat_plate_critical_stress(
    E: float, nu: float, t: float, b: float, k: float
) -> float:
    """
    Flat plate buckling critical stress:
        sigma_cr = k * pi^2 * E / [12(1 - nu^2)] * (t/b)^2
    k  : plate buckling coefficient (from aspect-ratio charts)
    nu : Poisson's ratio, must be in [0, 0.5)
    t  : plate thickness
    b  : plate width (loaded edge)
    """
    if E <= 0:
        raise ValueError("Elastic modulus E must be positive.")
    if not (0.0 <= nu < 0.5):
        raise ValueError("Poisson ratio nu must be in [0, 0.5).")
    if t <= 0:
        raise ValueError("Plate thickness t must be positive.")
    if b <= 0:
        raise ValueError("Plate width b must be positive.")
    if k <= 0:
        raise ValueError("Plate buckling coefficient k must be positive.")
    return k * math.pi ** 2 * E / (12.0 * (1.0 - nu ** 2)) * (t / b) ** 2


# ---------------------------------------------------------------------------
# Knock-down factor
# ---------------------------------------------------------------------------

def apply_knockdown(sigma_cr: float, knockdown: float) -> float:
    """
    Reduce the theoretical critical stress by the knock-down factor gamma:
        sigma_cr_reduced = gamma * sigma_cr
    gamma must be in (0, 1].  A value of 1.0 means no knock-down applied.
    """
    if not (0.0 < knockdown <= 1.0):
        raise ValueError(
            f"Knock-down factor must be in (0, 1]; got {knockdown}."
        )
    if sigma_cr < 0.0:
        raise ValueError("Theoretical critical stress sigma_cr must be non-negative.")
    return knockdown * sigma_cr


# ---------------------------------------------------------------------------
# Margin of safety
# ---------------------------------------------------------------------------

def margin_of_safety(sigma_cr_reduced: float, sigma_applied: float) -> float:
    """
    Compute the buckling margin of safety:
        MS = sigma_cr_reduced / sigma_applied - 1
    A non-negative MS indicates the member does not buckle under the applied load.
    sigma_applied must be strictly positive (compressive load in the member).
    """
    if sigma_cr_reduced < 0.0:
        raise ValueError("Reduced critical stress must be non-negative.")
    if sigma_applied <= 0.0:
        raise ValueError("Applied stress must be strictly positive.")
    return sigma_cr_reduced / sigma_applied - 1.0


def is_buckling_compliant(ms: float) -> bool:
    """Return True when the margin of safety indicates no buckling (MS >= 0)."""
    return ms >= 0.0


# ---------------------------------------------------------------------------
# End-to-end check helpers
# ---------------------------------------------------------------------------

def check_column(
    E: float,
    sigma_y: float,
    boundary_condition: str,
    L: float,
    r: float,
    sigma_applied: float,
    knockdown: float = 1.0,
) -> dict:
    """
    Complete column buckling check from inputs to compliance verdict.

    Returns a dict with all intermediate values:
        boundary_condition, K, KL_r, KL_r_transition, regime,
        sigma_cr_theoretical, knockdown, sigma_cr_reduced,
        sigma_applied, MS, compliant.
    """
    K = effective_length_factor(boundary_condition)
    formula = select_column_formula(E, sigma_y, K, L, r)
    sigma_cr_red = apply_knockdown(formula["sigma_cr"], knockdown)
    ms = margin_of_safety(sigma_cr_red, sigma_applied)
    return {
        "boundary_condition": boundary_condition,
        "K": K,
        "KL_r": formula["KL_r"],
        "KL_r_transition": formula["KL_r_transition"],
        "regime": formula["regime"],
        "sigma_cr_theoretical": formula["sigma_cr"],
        "knockdown": knockdown,
        "sigma_cr_reduced": sigma_cr_red,
        "sigma_applied": sigma_applied,
        "MS": ms,
        "compliant": is_buckling_compliant(ms),
    }


def check_flat_plate(
    E: float,
    nu: float,
    t: float,
    b: float,
    k: float,
    sigma_applied: float,
    knockdown: float = 1.0,
) -> dict:
    """
    Complete flat plate buckling check from inputs to compliance verdict.

    Returns a dict with:
        sigma_cr_theoretical, knockdown, sigma_cr_reduced,
        sigma_applied, MS, compliant.
    """
    sigma_cr = flat_plate_critical_stress(E, nu, t, b, k)
    sigma_cr_red = apply_knockdown(sigma_cr, knockdown)
    ms = margin_of_safety(sigma_cr_red, sigma_applied)
    return {
        "sigma_cr_theoretical": sigma_cr,
        "knockdown": knockdown,
        "sigma_cr_reduced": sigma_cr_red,
        "sigma_applied": sigma_applied,
        "MS": ms,
        "compliant": is_buckling_compliant(ms),
    }
