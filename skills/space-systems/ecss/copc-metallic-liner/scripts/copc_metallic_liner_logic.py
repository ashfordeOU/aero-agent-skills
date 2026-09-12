"""
COPC metallic liner assessment logic — ECSS-E-ST-32 clause 4.5.2.

Implements deterministic, offline checks for a Composite Overwrapped
Pressure Container (COPC) fitted with a metallic liner: liner material
categorization, proof and burst factor validation, thin-wall hoop stress
calculation, liner elasticity at proof pressure, margin of safety at MEOP,
leak-before-burst fracture mechanics, fatigue cycle budget, and burst
capability check.

stdlib only — no third-party dependencies.
"""

import math

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_PROOF_FACTOR: float = 1.1        # minimum proof-to-MEOP pressure ratio
MIN_BURST_FACTOR: float = 1.5        # minimum burst-to-MEOP pressure ratio
FATIGUE_SCATTER_FACTOR: float = 4.0  # minimum cycle life scatter factor
GEOMETRY_FACTOR_Y: float = 1.12      # semi-elliptical surface crack geometry factor

VALID_LINER_MATERIALS: frozenset = frozenset({
    "aluminum_2014",
    "aluminum_2219",
    "aluminum_6061",
    "inconel_718",
    "stainless_316l",
    "stainless_321",
    "titanium_6al4v",
    "titanium_cp4",
})


# ---------------------------------------------------------------------------
# Liner material categorization
# ---------------------------------------------------------------------------

def categorize_liner_material(material: str) -> str:
    """Return the canonical material identifier for *material*.

    Accepted values (case-insensitive): members of VALID_LINER_MATERIALS.
    Raises TypeError for non-string input, ValueError for unrecognized input.
    """
    if not isinstance(material, str):
        raise TypeError(f"material must be a string, got {type(material).__name__!r}")
    canonical = material.strip().lower()
    if canonical not in VALID_LINER_MATERIALS:
        raise ValueError(
            f"Unrecognized liner material {material!r}. "
            f"Must be one of: {sorted(VALID_LINER_MATERIALS)}"
        )
    return canonical


# ---------------------------------------------------------------------------
# Pressure factor checks
# ---------------------------------------------------------------------------

def compute_proof_pressure(meop_mpa: float, proof_factor: float) -> float:
    """Return proof pressure (MPa) = meop_mpa × proof_factor."""
    _require_positive(meop_mpa, "meop_mpa")
    _require_positive(proof_factor, "proof_factor")
    return meop_mpa * proof_factor


def compute_burst_pressure(meop_mpa: float, burst_factor: float) -> float:
    """Return required burst pressure (MPa) = meop_mpa × burst_factor."""
    _require_positive(meop_mpa, "meop_mpa")
    _require_positive(burst_factor, "burst_factor")
    return meop_mpa * burst_factor


def check_proof_factor(proof_factor: float) -> dict:
    """Check proof_factor against MIN_PROOF_FACTOR.

    Returns dict with keys:
      pass (bool), shortfall (float — 0.0 when passing).
    """
    _require_positive(proof_factor, "proof_factor")
    shortfall = max(0.0, MIN_PROOF_FACTOR - proof_factor)
    return {"pass": shortfall == 0.0, "shortfall": shortfall}


def check_burst_factor(burst_factor: float) -> dict:
    """Check burst_factor against MIN_BURST_FACTOR.

    Returns dict with keys:
      pass (bool), shortfall (float — 0.0 when passing).
    """
    _require_positive(burst_factor, "burst_factor")
    shortfall = max(0.0, MIN_BURST_FACTOR - burst_factor)
    return {"pass": shortfall == 0.0, "shortfall": shortfall}


# ---------------------------------------------------------------------------
# Thin-wall hoop stress
# ---------------------------------------------------------------------------

def compute_hoop_stress(
    pressure_mpa: float,
    inner_radius_m: float,
    wall_thickness_m: float,
) -> float:
    """Compute hoop stress (MPa) in a thin-wall cylindrical pressure vessel.

    σ_hoop = P × r / t

    Raises ValueError when inputs are non-positive or the thin-wall assumption
    is violated (t/r ≥ 0.1); thick-wall analysis is required in that case.
    """
    _require_positive(pressure_mpa, "pressure_mpa")
    _require_positive(inner_radius_m, "inner_radius_m")
    _require_positive(wall_thickness_m, "wall_thickness_m")
    if wall_thickness_m >= inner_radius_m / 10.0:
        raise ValueError(
            f"Thin-wall assumption violated: t/r = "
            f"{wall_thickness_m / inner_radius_m:.4f} >= 0.1. "
            "Use thick-wall analysis."
        )
    return pressure_mpa * inner_radius_m / wall_thickness_m


# ---------------------------------------------------------------------------
# Liner elasticity checks
# ---------------------------------------------------------------------------

def check_liner_elasticity_at_proof(
    hoop_stress_mpa: float,
    liner_yield_stress_mpa: float,
) -> dict:
    """Check that the liner remains elastic (no yield) at proof pressure.

    Per ECSS-E-ST-32 clause 4.5.2 the metallic liner must not yield under
    proof pressure. Passes only when hoop_stress < yield_stress (strictly).

    Returns dict with keys:
      pass (bool), margin (float — positive when elastic, negative when yielded).
    """
    _require_positive(hoop_stress_mpa, "hoop_stress_mpa")
    _require_positive(liner_yield_stress_mpa, "liner_yield_stress_mpa")
    margin = liner_yield_stress_mpa / hoop_stress_mpa - 1.0
    return {"pass": hoop_stress_mpa < liner_yield_stress_mpa, "margin": margin}


def check_liner_margin_at_meop(
    hoop_stress_mpa: float,
    liner_yield_stress_mpa: float,
) -> dict:
    """Compute the margin of safety on liner hoop stress at MEOP.

    MS = (yield_stress / hoop_stress) − 1. Positive MS is passing.

    Returns dict with keys:
      pass (bool), margin (float).
    """
    _require_positive(hoop_stress_mpa, "hoop_stress_mpa")
    _require_positive(liner_yield_stress_mpa, "liner_yield_stress_mpa")
    margin = liner_yield_stress_mpa / hoop_stress_mpa - 1.0
    return {"pass": margin > 0.0, "margin": margin}


# ---------------------------------------------------------------------------
# Fracture mechanics — leak-before-burst
# ---------------------------------------------------------------------------

def compute_critical_flaw_depth(
    fracture_toughness_mpa_sqrtm: float,
    hoop_stress_mpa: float,
    geometry_factor: float = GEOMETRY_FACTOR_Y,
) -> float:
    """Compute the fracture-mechanics critical surface-crack half-depth (m).

    a_c = (K_Ic / (Y × σ))² / π

    K_Ic is fracture toughness (MPa·√m), σ is hoop stress (MPa), Y is the
    geometry factor for a semi-elliptical surface crack. Returns a_c in metres.
    """
    _require_positive(fracture_toughness_mpa_sqrtm, "fracture_toughness_mpa_sqrtm")
    _require_positive(hoop_stress_mpa, "hoop_stress_mpa")
    _require_positive(geometry_factor, "geometry_factor")
    return (fracture_toughness_mpa_sqrtm / (geometry_factor * hoop_stress_mpa)) ** 2 / math.pi


def check_leak_before_burst(
    fracture_toughness_mpa_sqrtm: float,
    hoop_stress_mpa: float,
    wall_thickness_m: float,
    geometry_factor: float = GEOMETRY_FACTOR_Y,
) -> dict:
    """Check the leak-before-burst condition for the metallic liner.

    LBB is demonstrated when the critical flaw half-depth (a_c) exceeds the
    liner wall thickness. A surface crack propagates through-wall and creates a
    detectable leak before reaching fracture-critical size.

    Returns dict with keys:
      pass (bool), a_c_m (float — critical flaw depth in metres),
      margin (float — positive when LBB is demonstrated).
    """
    _require_positive(wall_thickness_m, "wall_thickness_m")
    a_c = compute_critical_flaw_depth(
        fracture_toughness_mpa_sqrtm, hoop_stress_mpa, geometry_factor
    )
    margin = a_c / wall_thickness_m - 1.0
    return {"pass": a_c > wall_thickness_m, "a_c_m": a_c, "margin": margin}


# ---------------------------------------------------------------------------
# Fatigue cycle budget
# ---------------------------------------------------------------------------

def check_fatigue_cycle_budget(
    design_cycles: int,
    allowable_cycles: int,
    scatter_factor: float = FATIGUE_SCATTER_FACTOR,
) -> dict:
    """Check that the fatigue cycle budget covers the design life.

    Effective allowable = allowable_cycles / scatter_factor.
    Passes when effective_allowable >= design_cycles.
    Raises ValueError when scatter_factor < FATIGUE_SCATTER_FACTOR (minimum 4.0).

    Returns dict with keys:
      pass (bool), effective_allowable (float), margin (float).
    """
    if design_cycles <= 0:
        raise ValueError(f"design_cycles must be positive (got {design_cycles})")
    if allowable_cycles <= 0:
        raise ValueError(f"allowable_cycles must be positive (got {allowable_cycles})")
    if scatter_factor < FATIGUE_SCATTER_FACTOR:
        raise ValueError(
            f"scatter_factor {scatter_factor} is below the minimum "
            f"{FATIGUE_SCATTER_FACTOR} required by ECSS-E-ST-32 clause 4.5.2"
        )
    effective = allowable_cycles / scatter_factor
    margin = effective / design_cycles - 1.0
    return {"pass": effective >= design_cycles, "effective_allowable": effective, "margin": margin}


# ---------------------------------------------------------------------------
# Burst capability
# ---------------------------------------------------------------------------

def check_burst_capability(
    actual_burst_pressure_mpa: float,
    required_burst_pressure_mpa: float,
) -> dict:
    """Check that actual burst pressure meets or exceeds the required value.

    Returns dict with keys:
      pass (bool), margin (float — positive when passing).
    """
    _require_positive(actual_burst_pressure_mpa, "actual_burst_pressure_mpa")
    _require_positive(required_burst_pressure_mpa, "required_burst_pressure_mpa")
    margin = actual_burst_pressure_mpa / required_burst_pressure_mpa - 1.0
    return {
        "pass": actual_burst_pressure_mpa >= required_burst_pressure_mpa,
        "margin": margin,
    }


# ---------------------------------------------------------------------------
# Top-level assessment
# ---------------------------------------------------------------------------

def assess_copc_metallic(
    liner_material: str,
    meop_mpa: float,
    proof_factor: float,
    burst_factor: float,
    inner_radius_m: float,
    liner_thickness_m: float,
    liner_yield_stress_mpa: float,
    fracture_toughness_mpa_sqrtm: float,
    design_cycles: int,
    allowable_cycles: int,
    actual_burst_pressure_mpa: float,
    fatigue_scatter_factor: float = FATIGUE_SCATTER_FACTOR,
    geometry_factor: float = GEOMETRY_FACTOR_Y,
) -> dict:
    """Run a full COPC metallic liner compliance assessment per ECSS-E-ST-32 clause 4.5.2.

    Raises ValueError for unrecognized liner material or invalid scatter factor.
    Returns dict with keys:
      compliant (bool) — True only when all checks pass,
      liner_material_canonical (str),
      findings (list[str]) — empty when compliant.
    """
    liner_canonical = categorize_liner_material(liner_material)

    findings: list = []

    pf = check_proof_factor(proof_factor)
    if not pf["pass"]:
        findings.append(
            f"Proof factor {proof_factor:.4f} below minimum {MIN_PROOF_FACTOR} "
            f"(shortfall {pf['shortfall']:.4f})"
        )

    bf = check_burst_factor(burst_factor)
    if not bf["pass"]:
        findings.append(
            f"Burst factor {burst_factor:.4f} below minimum {MIN_BURST_FACTOR} "
            f"(shortfall {bf['shortfall']:.4f})"
        )

    proof_pressure = compute_proof_pressure(meop_mpa, proof_factor)
    hoop_at_proof = compute_hoop_stress(proof_pressure, inner_radius_m, liner_thickness_m)
    hoop_at_meop = compute_hoop_stress(meop_mpa, inner_radius_m, liner_thickness_m)

    elas = check_liner_elasticity_at_proof(hoop_at_proof, liner_yield_stress_mpa)
    if not elas["pass"]:
        findings.append(
            f"Liner yields at proof: hoop stress {hoop_at_proof:.2f} MPa >= "
            f"yield {liner_yield_stress_mpa:.2f} MPa (margin {elas['margin']:.4f})"
        )

    ms = check_liner_margin_at_meop(hoop_at_meop, liner_yield_stress_mpa)
    if not ms["pass"]:
        findings.append(
            f"Negative liner margin at MEOP: MS = {ms['margin']:.4f}"
        )

    lbb = check_leak_before_burst(
        fracture_toughness_mpa_sqrtm, hoop_at_meop, liner_thickness_m, geometry_factor
    )
    if not lbb["pass"]:
        findings.append(
            f"LBB not demonstrated: a_c = {lbb['a_c_m'] * 1e3:.3f} mm < "
            f"wall thickness {liner_thickness_m * 1e3:.3f} mm (margin {lbb['margin']:.4f})"
        )

    cyc = check_fatigue_cycle_budget(design_cycles, allowable_cycles, fatigue_scatter_factor)
    if not cyc["pass"]:
        findings.append(
            f"Fatigue cycle budget insufficient: effective allowable "
            f"{cyc['effective_allowable']:.0f} < design cycles {design_cycles} "
            f"(margin {cyc['margin']:.4f})"
        )

    required_burst = compute_burst_pressure(meop_mpa, burst_factor)
    bst = check_burst_capability(actual_burst_pressure_mpa, required_burst)
    if not bst["pass"]:
        findings.append(
            f"Burst capability insufficient: {actual_burst_pressure_mpa:.2f} MPa < "
            f"required {required_burst:.2f} MPa (margin {bst['margin']:.4f})"
        )

    return {
        "compliant": len(findings) == 0,
        "liner_material_canonical": liner_canonical,
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_positive(value: float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive (got {value})")
