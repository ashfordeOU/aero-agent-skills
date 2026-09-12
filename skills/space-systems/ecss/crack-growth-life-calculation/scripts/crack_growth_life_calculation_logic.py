"""
Crack growth life calculation per ECSS-E-ST-32-01C §7.2.8.

Implements Paris, Walker, and Forman crack growth rate laws with scatter
factors (x3 / x5) and life margin computation.  Stdlib only, no external
dependencies.
"""

import math

# Scatter factors per §7.2.8 data-quality rule
SCATTER_FACTOR_WITH_TEST_DATA = 3.0    # material-specific crack growth data available
SCATTER_FACTOR_WITHOUT_TEST_DATA = 5.0  # handbook or generic data only


def compute_stress_intensity_range(beta, delta_sigma, a):
    """
    Compute stress intensity factor range ΔK = β × Δσ × √(π × a).

    Args:
        beta: geometry/boundary correction factor (dimensionless, > 0)
        delta_sigma: applied stress range [MPa]
        a: crack half-length (consistent length units, > 0)

    Returns:
        ΔK [MPa × sqrt(length units)]

    Raises:
        ValueError: on non-physical inputs
    """
    if beta <= 0:
        raise ValueError(f"beta must be positive, got {beta}")
    if delta_sigma <= 0:
        raise ValueError(f"delta_sigma must be positive, got {delta_sigma}")
    if a <= 0:
        raise ValueError(f"crack size a must be positive, got {a}")
    return beta * delta_sigma * math.sqrt(math.pi * a)


def compute_critical_crack_size(K_Ic, beta, sigma_max):
    """
    Compute critical crack half-length from fracture toughness.

    a_crit = (K_Ic / (β × σ_max))² / π

    Args:
        K_Ic: fracture toughness [MPa√m]
        beta: geometry factor (> 0)
        sigma_max: maximum applied stress [MPa] (> 0)

    Returns:
        Critical crack half-length [m, consistent with K_Ic units]

    Raises:
        ValueError: on non-physical inputs
    """
    if K_Ic <= 0:
        raise ValueError(f"K_Ic must be positive, got {K_Ic}")
    if beta <= 0:
        raise ValueError(f"beta must be positive, got {beta}")
    if sigma_max <= 0:
        raise ValueError(f"sigma_max must be positive, got {sigma_max}")
    return (K_Ic / (beta * sigma_max)) ** 2 / math.pi


def paris_crack_growth_life(C, m, beta, delta_sigma, a_i, a_f):
    """
    Compute crack growth life using the Paris law (analytical closed form).

    da/dN = C × ΔK^m = C × (β × Δσ × √(πa))^m

    For constant β and Δσ the life integral has an exact closed form:
      m ≠ 2: N = [a_f^exp − a_i^exp] / [exp × C × (β × Δσ × √π)^m]
             where exp = (2 − m) / 2
      m = 2: N = ln(a_f / a_i) / [C × (β × Δσ)² × π]

    Args:
        C: Paris coefficient (> 0)
        m: Paris exponent (> 0)
        beta: geometry factor (> 0)
        delta_sigma: stress range [MPa] (> 0)
        a_i: initial crack half-length (> 0, < a_f)
        a_f: final crack half-length (> 0, > a_i)

    Returns:
        N: computed crack growth life [cycles]

    Raises:
        ValueError: on non-physical inputs or non-positive result
    """
    if C <= 0:
        raise ValueError(f"Paris coefficient C must be positive, got {C}")
    if m <= 0:
        raise ValueError(f"Paris exponent m must be positive, got {m}")
    if beta <= 0:
        raise ValueError(f"beta must be positive, got {beta}")
    if delta_sigma <= 0:
        raise ValueError(f"delta_sigma must be positive, got {delta_sigma}")
    if a_i <= 0 or a_f <= 0:
        raise ValueError("Crack sizes a_i and a_f must be positive")
    if a_i >= a_f:
        raise ValueError(
            f"Initial crack a_i={a_i} must be less than final crack a_f={a_f}"
        )

    K_factor = (beta * delta_sigma * math.sqrt(math.pi)) ** m

    if abs(m - 2.0) < 1e-12:
        N = math.log(a_f / a_i) / (C * (beta * delta_sigma) ** 2 * math.pi)
    else:
        exp = (2.0 - m) / 2.0
        N = (a_f ** exp - a_i ** exp) / (exp * C * K_factor)

    if N <= 0:
        raise ValueError(
            f"Computed Paris life N={N} is non-positive; check exponent m={m}"
        )
    return N


def walker_crack_growth_life(C, n, gamma, R, beta, delta_sigma, a_i, a_f,
                              n_steps=1000):
    """
    Compute crack growth life using the Walker law (midpoint-rule integration).

    Walker effective range: ΔK_eff = ΔK / (1−R)^(1−γ)
    da/dN = C × ΔK_eff^n

    Args:
        C: Walker coefficient (> 0)
        n: Walker exponent (> 0)
        gamma: Walker stress-ratio exponent (any real; typically 0 < γ < 1)
        R: stress ratio K_min/K_max (< 1)
        beta: geometry factor (> 0)
        delta_sigma: stress range [MPa] (> 0)
        a_i: initial crack half-length (> 0, < a_f)
        a_f: final crack half-length (> 0, > a_i)
        n_steps: number of integration steps (≥ 10)

    Returns:
        N: computed crack growth life [cycles]

    Raises:
        ValueError: on non-physical inputs
    """
    if C <= 0:
        raise ValueError(f"Walker coefficient C must be positive, got {C}")
    if n <= 0:
        raise ValueError(f"Walker exponent n must be positive, got {n}")
    if R >= 1.0:
        raise ValueError(f"Stress ratio R must be < 1, got {R}")
    if beta <= 0:
        raise ValueError(f"beta must be positive, got {beta}")
    if delta_sigma <= 0:
        raise ValueError(f"delta_sigma must be positive, got {delta_sigma}")
    if a_i <= 0 or a_f <= 0:
        raise ValueError("Crack sizes a_i and a_f must be positive")
    if a_i >= a_f:
        raise ValueError(
            f"Initial crack a_i={a_i} must be less than final crack a_f={a_f}"
        )
    if n_steps < 10:
        raise ValueError("n_steps must be at least 10")

    walker_R_factor = (1.0 - R) ** (1.0 - gamma)
    da = (a_f - a_i) / n_steps
    N = 0.0
    a = a_i

    for _ in range(n_steps):
        a_mid = a + da * 0.5
        dK = compute_stress_intensity_range(beta, delta_sigma, a_mid)
        dK_eff = dK / walker_R_factor
        rate = C * (dK_eff ** n)
        N += da / rate
        a += da

    return N


def forman_crack_growth_life(C, n, R, K_c, beta, delta_sigma, a_i, a_f,
                              n_steps=1000):
    """
    Compute crack growth life using the Forman law (midpoint-rule integration).

    da/dN = C × ΔK^n / ((1−R) × K_c − ΔK)

    The denominator approaches zero as ΔK → (1−R)×K_c; a_f must not exceed
    the crack size at which this limit is reached.

    Args:
        C: Forman coefficient (> 0)
        n: Forman exponent (> 0)
        R: stress ratio (< 1)
        K_c: fracture toughness (same units as ΔK; > 0)
        beta: geometry factor (> 0)
        delta_sigma: stress range [MPa] (> 0)
        a_i: initial crack half-length (> 0, < a_f)
        a_f: final crack half-length (> 0, > a_i)
        n_steps: number of integration steps (≥ 10)

    Returns:
        N: computed crack growth life [cycles]

    Raises:
        ValueError: on non-physical inputs or denominator ≤ 0
    """
    if C <= 0:
        raise ValueError(f"Forman coefficient C must be positive, got {C}")
    if n <= 0:
        raise ValueError(f"Forman exponent n must be positive, got {n}")
    if K_c <= 0:
        raise ValueError(f"K_c must be positive, got {K_c}")
    if R >= 1.0:
        raise ValueError(f"Stress ratio R must be < 1, got {R}")
    if beta <= 0:
        raise ValueError(f"beta must be positive, got {beta}")
    if delta_sigma <= 0:
        raise ValueError(f"delta_sigma must be positive, got {delta_sigma}")
    if a_i <= 0 or a_f <= 0:
        raise ValueError("Crack sizes a_i and a_f must be positive")
    if a_i >= a_f:
        raise ValueError(
            f"Initial crack a_i={a_i} must be less than final crack a_f={a_f}"
        )
    if n_steps < 10:
        raise ValueError("n_steps must be at least 10")

    K_limit = (1.0 - R) * K_c
    da = (a_f - a_i) / n_steps
    N = 0.0
    a = a_i

    for _ in range(n_steps):
        a_mid = a + da * 0.5
        dK = compute_stress_intensity_range(beta, delta_sigma, a_mid)
        denom = K_limit - dK
        if denom <= 0.0:
            raise ValueError(
                f"Forman denominator ≤ 0 at a={a_mid:.6g}: "
                f"ΔK={dK:.4f} ≥ (1−R)×Kc={K_limit:.4f}. "
                "Reduce a_f or check that a_f does not exceed the fracture limit."
            )
        rate = C * (dK ** n) / denom
        N += da / rate
        a += da

    return N


def select_scatter_factor(has_material_specific_data):
    """
    Return the life scatter factor appropriate to the available data quality.

    Returns SCATTER_FACTOR_WITH_TEST_DATA (3.0) when material-specific crack
    growth rate test data is available; SCATTER_FACTOR_WITHOUT_TEST_DATA (5.0)
    when only handbook or generic data is used.
    """
    if has_material_specific_data:
        return SCATTER_FACTOR_WITH_TEST_DATA
    return SCATTER_FACTOR_WITHOUT_TEST_DATA


def apply_scatter(N_computed, scatter_factor):
    """
    Apply a life scatter factor to obtain the design life.

    N_design = N_computed / scatter_factor

    Args:
        N_computed: computed crack growth life [cycles] (> 0)
        scatter_factor: life scatter factor (> 0; typically 3.0 or 5.0)

    Returns:
        N_design: scatter-adjusted design life [cycles]

    Raises:
        ValueError: on non-positive inputs
    """
    if N_computed <= 0:
        raise ValueError(f"N_computed must be positive, got {N_computed}")
    if scatter_factor <= 0:
        raise ValueError(f"scatter_factor must be positive, got {scatter_factor}")
    return N_computed / scatter_factor


def life_margin(N_design, N_required):
    """
    Compute margin of safety on crack growth life.

    MS_life = N_design / N_required − 1

    MS_life ≥ 0 → passes; MS_life < 0 → fracture-control finding.

    Args:
        N_design: scatter-adjusted design life [cycles] (> 0)
        N_required: required service life [cycles] (> 0)

    Returns:
        MS_life: dimensionless margin of safety

    Raises:
        ValueError: on non-positive inputs
    """
    if N_design <= 0:
        raise ValueError(f"N_design must be positive, got {N_design}")
    if N_required <= 0:
        raise ValueError(f"N_required must be positive, got {N_required}")
    return N_design / N_required - 1.0


def full_crack_growth_assessment(
    law,
    law_params,
    beta,
    delta_sigma,
    sigma_max,
    a_i,
    K_Ic,
    N_required,
    has_material_specific_data=True,
):
    """
    Run a complete crack growth life assessment per ECSS-E-ST-32-01C §7.2.8.

    Steps: compute a_crit → integrate chosen law from a_i to a_crit →
    apply scatter → compute life margin.

    Args:
        law: 'paris', 'walker', or 'forman'
        law_params: dict of law-specific coefficients
            Paris  → {'C': float, 'm': float}
            Walker → {'C': float, 'n': float, 'gamma': float, 'R': float}
            Forman → {'C': float, 'n': float, 'R': float}  (K_c taken from K_Ic)
        beta: geometry factor (> 0)
        delta_sigma: stress range [MPa] (> 0)
        sigma_max: maximum applied stress [MPa] (> 0)
        a_i: initial crack half-length (> 0)
        K_Ic: fracture toughness [MPa√m] (> 0; used as K_c for Forman)
        N_required: required service life [cycles] (> 0)
        has_material_specific_data: bool controlling scatter factor selection

    Returns:
        dict with keys:
            a_crit        – critical crack half-length
            N_computed    – raw integrated life [cycles]
            scatter_factor – applied scatter factor
            N_design      – scatter-adjusted design life [cycles]
            MS_life       – margin of safety on life
            passes        – True if MS_life ≥ 0

    Raises:
        ValueError: if a_i ≥ a_crit or unknown law name
    """
    a_crit = compute_critical_crack_size(K_Ic, beta, sigma_max)

    if a_i >= a_crit:
        raise ValueError(
            f"Initial crack a_i={a_i} >= critical size a_crit={a_crit:.6g}. "
            "Structure is at or beyond critical state; redesign required."
        )

    if law == "paris":
        N_computed = paris_crack_growth_life(
            law_params["C"], law_params["m"], beta, delta_sigma, a_i, a_crit
        )
    elif law == "walker":
        N_computed = walker_crack_growth_life(
            law_params["C"], law_params["n"], law_params["gamma"],
            law_params["R"], beta, delta_sigma, a_i, a_crit
        )
    elif law == "forman":
        N_computed = forman_crack_growth_life(
            law_params["C"], law_params["n"], law_params["R"],
            K_Ic, beta, delta_sigma, a_i, a_crit
        )
    else:
        raise ValueError(
            f"Unknown crack growth law: {law!r}. Use 'paris', 'walker', or 'forman'."
        )

    sf = select_scatter_factor(has_material_specific_data)
    N_design = apply_scatter(N_computed, sf)
    MS = life_margin(N_design, N_required)

    return {
        "a_crit": a_crit,
        "N_computed": N_computed,
        "scatter_factor": sf,
        "N_design": N_design,
        "MS_life": MS,
        "passes": MS >= 0.0,
    }
