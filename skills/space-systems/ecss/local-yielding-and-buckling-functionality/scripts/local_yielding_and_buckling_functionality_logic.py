"""
Local yielding control and buckling resistance logic.
Implements checks for ECSS-E-ST-32 clauses 4.3.3 (local yielding) and
4.3.4 (buckling resistance) at item and sub-item level.
All values in SI base units (Pa, m) unless otherwise stated.
"""

import math


# ---------------------------------------------------------------------------
# Local Yielding — clause 4.3.3
# ---------------------------------------------------------------------------

def von_mises_stress(sigma_x, sigma_y, tau_xy):
    """
    Compute the von Mises equivalent stress from a 2-D stress state.

    Args:
        sigma_x: Normal stress in x-direction (Pa).
        sigma_y: Normal stress in y-direction (Pa).
        tau_xy:  Shear stress in the xy-plane (Pa).

    Returns:
        Von Mises equivalent stress (Pa, non-negative).
    """
    return math.sqrt(
        sigma_x**2 - sigma_x * sigma_y + sigma_y**2 + 3.0 * tau_xy**2
    )


def check_local_yielding(sigma_vm, yield_strength):
    """
    Check local yielding at limit load per ECSS-E-ST-32 clause 4.3.3.

    Local plastic deformation is permissible when the von Mises stress does
    not exceed the material yield strength at limit load.

    Args:
        sigma_vm:      Von Mises equivalent stress at the stress-raiser (Pa).
        yield_strength: Material 0.2 % proof / yield strength (Pa, > 0).

    Returns:
        dict with keys:
            yield_ratio      -- sigma_vm / yield_strength
            margin_of_safety -- yield_strength / sigma_vm - 1  (inf if sigma_vm == 0)
            status           -- 'permissible' (ratio <= 1) or 'exceeded'

    Raises:
        ValueError: if yield_strength <= 0 or sigma_vm < 0.
    """
    if yield_strength <= 0.0:
        raise ValueError("yield_strength must be positive, got {}".format(yield_strength))
    if sigma_vm < 0.0:
        raise ValueError("von Mises stress must be non-negative, got {}".format(sigma_vm))

    ratio = sigma_vm / yield_strength
    if sigma_vm == 0.0:
        ms = float("inf")
    else:
        ms = yield_strength / sigma_vm - 1.0

    return {
        "yield_ratio": ratio,
        "margin_of_safety": ms,
        "status": "permissible" if ratio <= 1.0 else "exceeded",
    }


# ---------------------------------------------------------------------------
# Plate Buckling — clause 4.3.4
# ---------------------------------------------------------------------------

def plate_buckling_critical_stress(k, E, nu, t, b):
    """
    Compute the elastic plate buckling critical stress using the Euler plate
    formula.  Applies to flat plates under uniform edge compression.

    sigma_cr = k * pi^2 * E / (12 * (1 - nu^2)) * (t / b)^2

    Args:
        k:  Buckling coefficient (dimensionless; depends on boundary
            conditions and plate aspect ratio a/b).
        E:  Young's modulus (Pa, > 0).
        nu: Poisson's ratio (dimensionless, in open interval (0, 0.5)).
        t:  Plate thickness (m, > 0).
        b:  Width of the loaded (compressed) edge (m, > 0).

    Returns:
        Critical buckling stress (Pa).

    Raises:
        ValueError: for physically invalid inputs.
    """
    if k <= 0.0:
        raise ValueError("buckling coefficient k must be positive, got {}".format(k))
    if E <= 0.0:
        raise ValueError("Young's modulus E must be positive, got {}".format(E))
    if not (0.0 < nu < 0.5):
        raise ValueError(
            "Poisson's ratio nu must be in (0, 0.5), got {}".format(nu)
        )
    if t <= 0.0:
        raise ValueError("plate thickness t must be positive, got {}".format(t))
    if b <= 0.0:
        raise ValueError("loaded-edge width b must be positive, got {}".format(b))

    return k * math.pi**2 * E / (12.0 * (1.0 - nu**2)) * (t / b)**2


def buckling_margin_of_safety(sigma_cr, sigma_applied):
    """
    Compute the buckling margin of safety.

    MS = sigma_cr / sigma_applied - 1

    Args:
        sigma_cr:      Elastic critical buckling stress (Pa, > 0).
        sigma_applied: Applied compressive stress magnitude (Pa, >= 0).

    Returns:
        Margin of safety (float); positive means stable, negative means buckled.
        Returns +inf when sigma_applied == 0.

    Raises:
        ValueError: if sigma_cr <= 0 or sigma_applied < 0.
    """
    if sigma_cr <= 0.0:
        raise ValueError("sigma_cr must be positive, got {}".format(sigma_cr))
    if sigma_applied < 0.0:
        raise ValueError(
            "sigma_applied must be non-negative, got {}".format(sigma_applied)
        )
    if sigma_applied == 0.0:
        return float("inf")
    return sigma_cr / sigma_applied - 1.0


def check_plate_buckling(sigma_cr, sigma_applied):
    """
    Check whether a plate remains stable under applied compressive stress.

    Args:
        sigma_cr:      Critical buckling stress (Pa).
        sigma_applied: Applied compressive stress (Pa).

    Returns:
        dict with keys:
            margin_of_safety -- MS = sigma_cr / sigma_applied - 1
            status           -- 'stable' (MS >= 0) or 'buckled'
    """
    ms = buckling_margin_of_safety(sigma_cr, sigma_applied)
    return {
        "margin_of_safety": ms,
        "status": "stable" if ms >= 0.0 else "buckled",
    }


# ---------------------------------------------------------------------------
# Combined-Load Buckling Interaction — clause 4.3.4
# ---------------------------------------------------------------------------

# R is a sum of two floating-point powers; a load case placed exactly on the
# unit circle (e.g. sigma/sigma_cr = tau/tau_cr = sqrt(0.5)) can round to
# R = 1.0 + ~2.2e-16 instead of exactly 1.0. This tolerance absorbs that
# IEEE-754 round-off only — it is not a relaxation of the R <= 1.0 criterion.
INTERACTION_TOLERANCE = 1e-12


def combined_load_interaction(sigma_axial, sigma_cr_axial, tau, tau_cr, m=2, n=2):
    """
    Evaluate the combined-load buckling interaction for axial compression
    plus in-plane shear.

    Interaction index R = (sigma_axial / sigma_cr_axial)^m + (tau / tau_cr)^n

    R <= 1.0 + INTERACTION_TOLERANCE is stable (MS >= 0); otherwise buckled
    (MS < 0). The tolerance (see INTERACTION_TOLERANCE) exists solely to
    absorb floating-point round-off for load cases that sit exactly on the
    unit circle; it does not relax the R <= 1.0 engineering criterion.

    Args:
        sigma_axial:    Applied axial compressive stress (Pa, >= 0).
        sigma_cr_axial: Critical axial buckling stress (Pa, > 0).
        tau:            Applied shear stress magnitude (Pa, >= 0).
        tau_cr:         Critical shear buckling stress (Pa, > 0).
        m:              Interaction exponent for axial term (default 2).
        n:              Interaction exponent for shear term (default 2).

    Returns:
        dict with keys:
            interaction_index -- R
            margin_of_safety  -- 1 / R - 1  (inf if R == 0), clamped to 0.0
                                  when R is within INTERACTION_TOLERANCE
                                  above 1.0
            status            -- 'stable' (R <= 1 + tolerance) or 'buckled'

    Raises:
        ValueError: for invalid critical stresses or negative applied stresses.
    """
    if sigma_cr_axial <= 0.0:
        raise ValueError(
            "sigma_cr_axial must be positive, got {}".format(sigma_cr_axial)
        )
    if tau_cr <= 0.0:
        raise ValueError("tau_cr must be positive, got {}".format(tau_cr))
    if sigma_axial < 0.0:
        raise ValueError(
            "sigma_axial must be non-negative, got {}".format(sigma_axial)
        )
    if tau < 0.0:
        raise ValueError("tau must be non-negative, got {}".format(tau))

    R = (sigma_axial / sigma_cr_axial) ** m + (tau / tau_cr) ** n
    is_stable = R <= 1.0 + INTERACTION_TOLERANCE
    if R > 0.0:
        ms = 1.0 / R - 1.0
        # Round-off can push R just above 1.0 for a stable case; clamp MS
        # to 0.0 rather than reporting a spurious negative margin.
        if is_stable and ms < 0.0:
            ms = 0.0
    else:
        ms = float("inf")
    return {
        "interaction_index": R,
        "margin_of_safety": ms,
        "status": "stable" if is_stable else "buckled",
    }


# ---------------------------------------------------------------------------
# Crippling Stress — sub-element empirical check
# ---------------------------------------------------------------------------

def crippling_stress_angle_section(F_tu, t, b_effective):
    """
    Estimate the crippling stress for a thin-walled angle sub-element using a
    simplified empirical power-law relationship drawn from structural handbooks
    (not verbatim ECSS text).

    F_cc ≈ F_tu * (t / b_effective)^0.75

    Valid only when t / b_effective <= 1 (thin-wall assumption).

    Args:
        F_tu:        Material ultimate tensile strength (Pa, > 0).
        t:           Sub-element thickness (m, > 0).
        b_effective: Sub-element effective width between supports (m, > 0).

    Returns:
        Crippling stress F_cc (Pa).

    Raises:
        ValueError: for non-positive inputs or t/b > 1 (non-thin-wall).
    """
    if F_tu <= 0.0:
        raise ValueError("F_tu must be positive, got {}".format(F_tu))
    if t <= 0.0:
        raise ValueError("t must be positive, got {}".format(t))
    if b_effective <= 0.0:
        raise ValueError("b_effective must be positive, got {}".format(b_effective))

    ratio = t / b_effective
    if ratio > 1.0:
        raise ValueError(
            "t/b ratio {} > 1 violates the thin-wall assumption".format(ratio)
        )

    return F_tu * (ratio ** 0.75)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate_buckling_checks(checks):
    """
    Aggregate a list of individual buckling or yielding check results.

    Each element of `checks` must be a dict containing at least a
    'margin_of_safety' key (float).

    Args:
        checks: Non-empty list of result dicts from check_plate_buckling,
                check_local_yielding, combined_load_interaction, etc.

    Returns:
        dict with keys:
            overall_status  -- 'all_stable' if every MS >= 0, else 'has_failures'
            governing_margin -- minimum margin of safety across all checks
            n_checks        -- total number of checks
            n_failures      -- number of checks where MS < 0

    Raises:
        ValueError: if checks is empty.
    """
    if not checks:
        raise ValueError("checks list must not be empty")

    margins = [c["margin_of_safety"] for c in checks]
    n_failures = sum(1 for m in margins if m < 0.0)
    return {
        "overall_status": "all_stable" if n_failures == 0 else "has_failures",
        "governing_margin": min(margins),
        "n_checks": len(checks),
        "n_failures": n_failures,
    }
