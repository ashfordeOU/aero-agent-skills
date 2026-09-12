"""
COPC non-metallic liner assessment logic — ECSS-E-ST-32 clause 4.5.3.

Implements deterministic, offline checks for a Composite Overwrapped
Pressure Container (COPC) fitted with a homogeneous non-metallic liner:
liner material categorization, proof/burst factor checks, permeation
rate check, load-sharing ratio, liner-fluid compatibility, and cyclic
fatigue life validation.

stdlib only — no third-party dependencies.
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_PROOF_FACTOR = 1.1   # minimum proof-to-MEOP ratio
MIN_BURST_FACTOR = 1.5   # minimum burst-to-MEOP ratio
MAX_LINER_LOAD_SHARE = 0.20  # flag when liner carries > 20 % of combined stiffness

VALID_LINER_TYPES = frozenset({"thermoplastic", "thermoset", "elastomer"})

# Engineering compatibility table (paraphrased; not verbatim ECSS text).
# A fluid absent from a liner's set is flagged as unconfirmed-compatible.
_COMPATIBLE_FLUIDS: dict = {
    "thermoplastic": frozenset({"nitrogen", "helium", "air", "water", "dry_nitrogen"}),
    "thermoset":     frozenset({"nitrogen", "helium", "air", "water", "dry_nitrogen",
                                "hydrazine", "monomethylhydrazine"}),
    "elastomer":     frozenset({"nitrogen", "helium", "air", "dry_nitrogen"}),
}


# ---------------------------------------------------------------------------
# Liner material categorization
# ---------------------------------------------------------------------------

def categorize_liner_material(material: str) -> str:
    """Return the canonical liner category for *material*.

    Accepted values (case-insensitive): thermoplastic, thermoset, elastomer.
    Raises ValueError for any unrecognized input.
    """
    if not isinstance(material, str):
        raise TypeError(f"material must be a string, got {type(material).__name__!r}")
    canonical = material.strip().lower()
    if canonical not in VALID_LINER_TYPES:
        raise ValueError(
            f"Unrecognized liner material {material!r}. "
            f"Must be one of: {sorted(VALID_LINER_TYPES)}"
        )
    return canonical


# ---------------------------------------------------------------------------
# Pressure factor checks
# ---------------------------------------------------------------------------

def compute_proof_pressure(meop: float, proof_factor: float) -> float:
    """Return proof pressure = meop * proof_factor (same pressure unit as meop)."""
    _require_positive(meop, "meop")
    _require_positive(proof_factor, "proof_factor")
    return meop * proof_factor


def compute_burst_pressure(meop: float, burst_factor: float) -> float:
    """Return burst pressure = meop * burst_factor (same pressure unit as meop)."""
    _require_positive(meop, "meop")
    _require_positive(burst_factor, "burst_factor")
    return meop * burst_factor


def check_proof_factor(proof_factor: float) -> dict:
    """Check proof_factor against the minimum required value.

    Returns dict with keys:
      pass (bool), shortfall (float, 0.0 when passing).
    """
    _require_positive(proof_factor, "proof_factor")
    shortfall = max(0.0, MIN_PROOF_FACTOR - proof_factor)
    return {"pass": shortfall == 0.0, "shortfall": shortfall}


def check_burst_factor(burst_factor: float) -> dict:
    """Check burst_factor against the minimum required value.

    Returns dict with keys:
      pass (bool), shortfall (float, 0.0 when passing).
    """
    _require_positive(burst_factor, "burst_factor")
    shortfall = max(0.0, MIN_BURST_FACTOR - burst_factor)
    return {"pass": shortfall == 0.0, "shortfall": shortfall}


# ---------------------------------------------------------------------------
# Permeation rate check
# ---------------------------------------------------------------------------

def check_permeation_rate(rate: float, limit: float) -> dict:
    """Check liner gas permeation rate against the project allowable limit.

    Both *rate* and *limit* must be in the same units (e.g. g/day).
    Returns dict with keys:
      pass (bool), exceedance (float, 0.0 when passing).
    """
    if rate < 0:
        raise ValueError(f"Permeation rate cannot be negative (got {rate})")
    _require_positive(limit, "limit")
    exceedance = max(0.0, rate - limit)
    return {"pass": exceedance == 0.0, "exceedance": exceedance}


# ---------------------------------------------------------------------------
# Load-sharing ratio
# ---------------------------------------------------------------------------

def compute_load_share_ratio(liner_stiffness: float, overwrap_stiffness: float) -> float:
    """Return the fraction of combined axial stiffness carried by the liner.

    liner_stiffness and overwrap_stiffness must be in the same units (e.g. N/m).
    Raises ValueError for negative inputs or zero total stiffness.
    """
    if liner_stiffness < 0:
        raise ValueError(f"liner_stiffness cannot be negative (got {liner_stiffness})")
    _require_positive(overwrap_stiffness, "overwrap_stiffness")
    total = liner_stiffness + overwrap_stiffness
    return liner_stiffness / total


def check_load_share_ratio(ratio: float) -> dict:
    """Flag when the liner load-share ratio exceeds MAX_LINER_LOAD_SHARE.

    Returns dict with keys:
      pass (bool), excess (float, 0.0 when passing).
    """
    if ratio < 0 or ratio > 1:
        raise ValueError(f"ratio must be in [0, 1] (got {ratio})")
    excess = max(0.0, ratio - MAX_LINER_LOAD_SHARE)
    return {"pass": excess == 0.0, "excess": excess}


# ---------------------------------------------------------------------------
# Liner-fluid compatibility
# ---------------------------------------------------------------------------

def check_liner_compatibility(liner_type: str, fluid: str) -> dict:
    """Check whether *fluid* is confirmed compatible with *liner_type*.

    Returns dict with keys:
      compatible (bool), liner (str), fluid (str).
    Raises ValueError for unrecognized liner type.
    """
    canonical_liner = categorize_liner_material(liner_type)
    canonical_fluid = fluid.strip().lower()
    compatible = canonical_fluid in _COMPATIBLE_FLUIDS[canonical_liner]
    return {
        "compatible": compatible,
        "liner": canonical_liner,
        "fluid": canonical_fluid,
    }


# ---------------------------------------------------------------------------
# Cyclic fatigue life
# ---------------------------------------------------------------------------

def check_cyclic_life(
    cycles_required: int,
    cycles_demonstrated: int,
    safety_factor: float = 4.0,
) -> dict:
    """Check that demonstrated fatigue cycles cover required cycles * safety_factor.

    Returns dict with keys:
      pass (bool), required_with_factor (float), deficit (float, 0.0 when passing).
    """
    if cycles_required <= 0:
        raise ValueError(f"cycles_required must be positive (got {cycles_required})")
    if cycles_demonstrated < 0:
        raise ValueError(
            f"cycles_demonstrated cannot be negative (got {cycles_demonstrated})"
        )
    if safety_factor < 1.0:
        raise ValueError(f"safety_factor must be >= 1.0 (got {safety_factor})")
    required = cycles_required * safety_factor
    deficit = max(0.0, required - cycles_demonstrated)
    return {
        "pass": deficit == 0.0,
        "required_with_factor": required,
        "deficit": deficit,
    }


# ---------------------------------------------------------------------------
# Top-level assessment
# ---------------------------------------------------------------------------

def assess_copc_nonmetallic(
    liner_type: str,
    meop: float,
    proof_factor: float,
    burst_factor: float,
    permeation_rate: float,
    permeation_limit: float,
    liner_stiffness: float,
    overwrap_stiffness: float,
    fluid: str,
    cycles_required: int,
    cycles_demonstrated: int,
    fatigue_safety_factor: float = 4.0,
) -> dict:
    """Run a full COPC non-metallic liner compliance assessment.

    Returns dict with keys:
      compliant (bool) — True only when all checks pass,
      liner_category (str),
      load_share_ratio (float),
      findings (list[str]) — empty when compliant.
    """
    findings: list = []

    # Liner categorization
    try:
        liner_cat = categorize_liner_material(liner_type)
    except (TypeError, ValueError) as exc:
        return {"compliant": False, "liner_category": None,
                "load_share_ratio": None, "findings": [str(exc)]}

    # Proof factor
    pf = check_proof_factor(proof_factor)
    if not pf["pass"]:
        findings.append(
            f"Proof factor {proof_factor:.4f} below minimum {MIN_PROOF_FACTOR} "
            f"(shortfall {pf['shortfall']:.4f})"
        )

    # Burst factor
    bf = check_burst_factor(burst_factor)
    if not bf["pass"]:
        findings.append(
            f"Burst factor {burst_factor:.4f} below minimum {MIN_BURST_FACTOR} "
            f"(shortfall {bf['shortfall']:.4f})"
        )

    # Permeation
    perm = check_permeation_rate(permeation_rate, permeation_limit)
    if not perm["pass"]:
        findings.append(
            f"Permeation rate {permeation_rate} exceeds limit {permeation_limit} "
            f"(exceedance {perm['exceedance']})"
        )

    # Load-sharing ratio
    lsr = compute_load_share_ratio(liner_stiffness, overwrap_stiffness)
    lsr_check = check_load_share_ratio(lsr)
    if not lsr_check["pass"]:
        findings.append(
            f"Liner load-share ratio {lsr:.4f} exceeds maximum {MAX_LINER_LOAD_SHARE} "
            f"(excess {lsr_check['excess']:.4f}); verify overwrap design"
        )

    # Liner-fluid compatibility
    compat = check_liner_compatibility(liner_cat, fluid)
    if not compat["compatible"]:
        findings.append(
            f"Liner type '{liner_cat}' not confirmed compatible with fluid '{fluid.strip().lower()}'"
        )

    # Cyclic fatigue life
    cyc = check_cyclic_life(cycles_required, cycles_demonstrated, fatigue_safety_factor)
    if not cyc["pass"]:
        findings.append(
            f"Demonstrated cycles {cycles_demonstrated} below required "
            f"{cyc['required_with_factor']:.0f} "
            f"(deficit {cyc['deficit']:.0f})"
        )

    return {
        "compliant": len(findings) == 0,
        "liner_category": liner_cat,
        "load_share_ratio": lsr,
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_positive(value: float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive (got {value})")
