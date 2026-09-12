"""
Damage tolerance assessment logic — ECSS-E-ST-32C clause 4.3.8.

Deterministic, offline checks for:
- Approach categorization (safe-life vs fail-safe)
- Crack growth bounding (safe-life path)
- Fail-safe redundancy (fail-safe path)
- Residual strength verification (both paths)
- Fracture control interface flag (ECSS-E-ST-32-01C)

No third-party dependencies; stdlib only.
"""

SAFE_LIFE = "safe-life"
FAIL_SAFE = "fail-safe"
_VALID_APPROACHES = frozenset({SAFE_LIFE, FAIL_SAFE})

# Residual strength requirement: damaged structure must carry at least this
# fraction of design-ultimate load (paraphrased from E-ST-32C § 4.3.8).
RESIDUAL_STRENGTH_FRACTION = 0.70

# Fracture control trigger: K ratio at or above this threshold requires
# a formal fracture-control plan per ECSS-E-ST-32-01C.
FRACTURE_CONTROL_K_RATIO_THRESHOLD = 0.90


def categorize_approach(approach: str) -> str:
    """Return canonical approach name or raise ValueError for unrecognised input."""
    key = approach.strip().lower()
    if key not in _VALID_APPROACHES:
        raise ValueError(
            f"Unknown damage tolerance approach '{approach}'. "
            f"Valid values: {sorted(_VALID_APPROACHES)}"
        )
    return key


def compute_final_crack_size(
    initial_flaw_mm: float,
    growth_rate_mm_per_cycle: float,
    design_cycles: int,
) -> float:
    """
    Return estimated crack half-length after linear growth over the design life.

    Uses a simplified Paris-law surrogate: a_final = a0 + da/dN * N.
    Callers requiring cycle-by-cycle integration should replace this with
    a higher-fidelity model; the interface (inputs/outputs) is unchanged.
    """
    if initial_flaw_mm < 0:
        raise ValueError("initial_flaw_mm must be non-negative")
    if growth_rate_mm_per_cycle < 0:
        raise ValueError("growth_rate_mm_per_cycle must be non-negative")
    if design_cycles < 0:
        raise ValueError("design_cycles must be non-negative")
    return initial_flaw_mm + growth_rate_mm_per_cycle * design_cycles


def check_safe_life(
    initial_flaw_mm: float,
    growth_rate_mm_per_cycle: float,
    design_cycles: int,
    critical_flaw_mm: float,
) -> dict:
    """
    Safe-life check: verify crack does not reach the critical flaw size
    within the design service life.

    Returns:
      final_crack_mm     — projected crack size at end of life
      critical_flaw_mm   — fracture-critical flaw size for the element
      passes             — True when final_crack_mm < critical_flaw_mm
      margin             — (critical - final) / critical; positive means pass
    """
    if critical_flaw_mm <= 0:
        raise ValueError("critical_flaw_mm must be positive")
    final = compute_final_crack_size(
        initial_flaw_mm, growth_rate_mm_per_cycle, design_cycles
    )
    margin = (critical_flaw_mm - final) / critical_flaw_mm
    return {
        "final_crack_mm": final,
        "critical_flaw_mm": critical_flaw_mm,
        "passes": final < critical_flaw_mm,
        "margin": margin,
    }


def check_residual_strength(
    residual_strength_N: float,
    design_ultimate_N: float,
    required_fraction: float = RESIDUAL_STRENGTH_FRACTION,
) -> dict:
    """
    Verify that the damaged structure's residual strength meets the required
    fraction of design-ultimate load (paraphrased from E-ST-32C § 4.3.8).

    Returns:
      required_N          — minimum acceptable residual strength
      residual_strength_N — actual residual strength after damage
      passes              — True when residual_strength_N >= required_N
      margin_of_safety    — (residual / required) - 1; positive means pass
    """
    if design_ultimate_N <= 0:
        raise ValueError("design_ultimate_N must be positive")
    if not (0 < required_fraction <= 1.0):
        raise ValueError("required_fraction must be in (0, 1]")
    required_N = design_ultimate_N * required_fraction
    mos = (residual_strength_N / required_N) - 1.0
    return {
        "required_N": required_N,
        "residual_strength_N": residual_strength_N,
        "passes": residual_strength_N >= required_N,
        "margin_of_safety": mos,
    }


def check_fail_safe_redundancy(
    num_load_paths: int,
    capacity_per_path_N: float,
    design_ultimate_N: float,
) -> dict:
    """
    Fail-safe check: verify that after loss of the worst-case single load
    path the surviving paths collectively carry the design-ultimate load.

    Returns:
      surviving_paths        — number of paths after one-path failure
      surviving_capacity_N   — total capacity of surviving paths
      design_ultimate_N      — required load to be carried
      passes                 — True when surviving_capacity_N >= design_ultimate_N
      margin_of_safety       — (surviving / required) - 1; positive means pass
    """
    if num_load_paths < 2:
        raise ValueError(
            f"Fail-safe design requires at least 2 load paths; got {num_load_paths}. "
            "A monolithic single-path structure cannot satisfy the fail-safe approach."
        )
    if capacity_per_path_N <= 0:
        raise ValueError("capacity_per_path_N must be positive")
    if design_ultimate_N <= 0:
        raise ValueError("design_ultimate_N must be positive")
    surviving = num_load_paths - 1
    surviving_capacity = surviving * capacity_per_path_N
    mos = (surviving_capacity / design_ultimate_N) - 1.0
    return {
        "surviving_paths": surviving,
        "surviving_capacity_N": surviving_capacity,
        "design_ultimate_N": design_ultimate_N,
        "passes": surviving_capacity >= design_ultimate_N,
        "margin_of_safety": mos,
    }


def flag_fracture_control(
    K_applied_MPa_sqrt_m: float,
    K_ic_MPa_sqrt_m: float,
    threshold: float = FRACTURE_CONTROL_K_RATIO_THRESHOLD,
) -> dict:
    """
    Determine whether a formal fracture-control plan per ECSS-E-ST-32-01C
    is required.

    A structure is flagged when K_applied / K_ic >= threshold.

    Returns:
      K_ratio                  — applied / toughness ratio
      requires_fracture_control — True when flagged
      threshold                — the trigger threshold used
    """
    if K_ic_MPa_sqrt_m <= 0:
        raise ValueError("K_ic_MPa_sqrt_m must be positive")
    if K_applied_MPa_sqrt_m < 0:
        raise ValueError("K_applied_MPa_sqrt_m must be non-negative")
    ratio = K_applied_MPa_sqrt_m / K_ic_MPa_sqrt_m
    return {
        "K_ratio": ratio,
        "requires_fracture_control": ratio >= threshold,
        "threshold": threshold,
    }


def assess_structure(structure: dict) -> dict:
    """
    Full damage tolerance assessment for one structural element.

    Required keys in `structure`:
      name                    — element identifier (str)
      approach                — "safe-life" or "fail-safe" (str)
      residual_strength_N     — residual strength after design damage state (float)
      design_ultimate_N       — design-ultimate load (float)
      K_applied_MPa_sqrt_m    — applied stress-intensity factor (float)
      K_ic_MPa_sqrt_m         — material fracture toughness (float)

    Additional keys for safe-life:
      initial_flaw_mm, growth_rate_mm_per_cycle, design_cycles, critical_flaw_mm

    Additional keys for fail-safe:
      num_load_paths, capacity_per_path_N

    Returns an assessment dict with per-check sub-dicts, a findings list, and
    an overall `passes` flag (True only when findings is empty).
    """
    approach = categorize_approach(structure["approach"])
    results: dict = {
        "name": structure["name"],
        "approach": approach,
        "findings": [],
    }

    if approach == SAFE_LIFE:
        sl = check_safe_life(
            structure["initial_flaw_mm"],
            structure["growth_rate_mm_per_cycle"],
            structure["design_cycles"],
            structure["critical_flaw_mm"],
        )
        results["safe_life"] = sl
        if not sl["passes"]:
            results["findings"].append(
                f"Safe-life: crack reaches {sl['final_crack_mm']:.3f} mm, "
                f"exceeds critical {sl['critical_flaw_mm']:.3f} mm "
                f"(margin {sl['margin']:.3f})"
            )
    else:
        fs = check_fail_safe_redundancy(
            structure["num_load_paths"],
            structure["capacity_per_path_N"],
            structure["design_ultimate_N"],
        )
        results["fail_safe"] = fs
        if not fs["passes"]:
            results["findings"].append(
                f"Fail-safe: surviving capacity {fs['surviving_capacity_N']:.1f} N "
                f"< design ultimate {fs['design_ultimate_N']:.1f} N "
                f"(MoS {fs['margin_of_safety']:.3f})"
            )

    rs = check_residual_strength(
        structure["residual_strength_N"],
        structure["design_ultimate_N"],
    )
    results["residual_strength"] = rs
    if not rs["passes"]:
        results["findings"].append(
            f"Residual strength: {rs['residual_strength_N']:.1f} N "
            f"< required {rs['required_N']:.1f} N "
            f"(MoS {rs['margin_of_safety']:.3f})"
        )

    fc = flag_fracture_control(
        structure["K_applied_MPa_sqrt_m"],
        structure["K_ic_MPa_sqrt_m"],
    )
    results["fracture_control"] = fc
    if fc["requires_fracture_control"]:
        results["findings"].append(
            f"Fracture control required (K ratio {fc['K_ratio']:.3f} >= "
            f"{fc['threshold']}); interface to ECSS-E-ST-32-01C."
        )

    results["passes"] = len(results["findings"]) == 0
    return results
