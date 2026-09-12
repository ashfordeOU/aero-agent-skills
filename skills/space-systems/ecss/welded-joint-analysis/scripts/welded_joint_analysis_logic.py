"""
Welded-joint analysis logic — ECSS-E-ST-32C clause 4.6.2.14.

Paraphrased procedure; no verbatim standard text. Cite: ECSS-E-ST-32C §4.6.2.14.
stdlib only; offline; deterministic.
"""

import math

# ---------------------------------------------------------------------------
# Weld quality class table
# Efficiency factors are paraphrased from the ECSS-E-ST-32C §4.6.2.14
# quality-class definitions (not reproduced verbatim).
# ---------------------------------------------------------------------------
WELD_QUALITY_CLASSES = {
    "WQ1": {
        "efficiency": 1.00,
        "inspection": "full volumetric (radiographic or ultrasonic on every weld)",
    },
    "WQ2": {
        "efficiency": 0.85,
        "inspection": "spot volumetric (sampled)",
    },
    "WQ3": {
        "efficiency": 0.70,
        "inspection": "visual and surface examination only",
    },
}

VALID_WELD_TYPES = {"butt", "fillet"}

# Von Mises shear factor: τ_allow = VON_MISES_SHEAR * σ_allow
VON_MISES_SHEAR = 1.0 / math.sqrt(3)  # ≈ 0.5774


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def categorize_weld_quality(quality_class: str) -> dict:
    """
    Return the quality-class record for *quality_class*.

    Raises ValueError for an unrecognized class so callers detect bad input
    before any numeric work begins.
    """
    key = quality_class.strip().upper()
    if key not in WELD_QUALITY_CLASSES:
        raise ValueError(
            f"Unknown weld quality class '{quality_class}'. "
            f"Valid values: {sorted(WELD_QUALITY_CLASSES)}"
        )
    record = dict(WELD_QUALITY_CLASSES[key])
    record["quality_class"] = key
    return record


def compute_weld_throat_area(weld_type: str, length: float, throat_or_leg: float) -> float:
    """
    Return the effective weld throat area (mm² or consistent units).

    Butt weld  : A = length × throat  (throat = plate thickness for full penetration)
    Fillet weld: A = length × 0.707 × leg_size  (45° effective throat)

    Raises ValueError for an unrecognized weld type or non-positive geometry.
    """
    wt = weld_type.strip().lower()
    if wt not in VALID_WELD_TYPES:
        raise ValueError(
            f"Unknown weld type '{weld_type}'. Valid values: {sorted(VALID_WELD_TYPES)}"
        )
    if length <= 0:
        raise ValueError(f"Weld length must be positive; got {length}.")
    if throat_or_leg <= 0:
        raise ValueError(f"Throat/leg dimension must be positive; got {throat_or_leg}.")

    if wt == "butt":
        return length * throat_or_leg
    else:  # fillet
        return length * (math.sqrt(2) / 2.0) * throat_or_leg


def compute_allowable_stresses(parent_ftu: float, quality_class: str, safety_factor: float) -> dict:
    """
    Return allowable normal and shear stresses.

      σ_allow = (F_tu × η) / SF
      τ_allow = VON_MISES_SHEAR × σ_allow

    Raises ValueError for non-positive inputs.
    """
    if parent_ftu <= 0:
        raise ValueError(f"Parent material F_tu must be positive; got {parent_ftu}.")
    if safety_factor <= 0:
        raise ValueError(f"Safety factor must be positive; got {safety_factor}.")

    qc = categorize_weld_quality(quality_class)
    eta = qc["efficiency"]
    sigma_allow = (parent_ftu * eta) / safety_factor
    tau_allow = VON_MISES_SHEAR * sigma_allow

    return {
        "quality_class": qc["quality_class"],
        "efficiency": eta,
        "sigma_allow": sigma_allow,
        "tau_allow": tau_allow,
    }


def compute_applied_stresses(normal_load: float, shear_load: float, weld_area: float) -> dict:
    """
    Return applied normal and shear stress from design loads.

      σ = N / A_weld
      τ = V / A_weld

    Raises ValueError for non-positive weld area.
    """
    if weld_area <= 0:
        raise ValueError(f"Weld area must be positive; got {weld_area}.")

    return {
        "sigma_applied": normal_load / weld_area,
        "tau_applied": shear_load / weld_area,
    }


def compute_margin_of_safety(applied: float, allowable: float) -> float:
    """
    Return MoS = (allowable / applied) - 1.

    Returns math.inf when applied == 0 (trivially passes).
    Raises ValueError when allowable <= 0.
    """
    if allowable <= 0:
        raise ValueError(f"Allowable must be positive; got {allowable}.")
    if applied == 0.0:
        return math.inf
    return (allowable / applied) - 1.0


def check_combined_criterion(
    sigma: float, tau: float, sigma_allow: float, tau_allow: float
) -> dict:
    """
    Evaluate the von Mises interaction ratio.

      R = sqrt((σ/σ_allow)² + (τ/τ_allow)²)
      MoS_combined = (1/R) - 1   [inf when R == 0]
      compliant = R <= 1.0

    Raises ValueError for non-positive allowables or any negative stress component.
    """
    if sigma_allow <= 0:
        raise ValueError(f"sigma_allow must be positive; got {sigma_allow}.")
    if tau_allow <= 0:
        raise ValueError(f"tau_allow must be positive; got {tau_allow}.")
    if sigma < 0:
        raise ValueError(f"Applied normal stress must be >= 0; got {sigma}.")
    if tau < 0:
        raise ValueError(f"Applied shear stress must be >= 0; got {tau}.")

    ratio_sq = (sigma / sigma_allow) ** 2 + (tau / tau_allow) ** 2
    if ratio_sq == 0.0:
        return {"interaction_ratio": 0.0, "mos_combined": math.inf, "compliant": True}

    r = math.sqrt(ratio_sq)
    mos_c = (1.0 / r) - 1.0
    return {
        "interaction_ratio": r,
        "mos_combined": mos_c,
        "compliant": r <= 1.0,
    }


# ---------------------------------------------------------------------------
# Top-level assessment
# ---------------------------------------------------------------------------

def assess_welded_joint(
    weld_type: str,
    quality_class: str,
    weld_length: float,
    throat_or_leg: float,
    parent_ftu: float,
    safety_factor: float,
    normal_load: float,
    shear_load: float,
) -> dict:
    """
    Full welded-joint assessment per ECSS-E-ST-32C §4.6.2.14.

    Parameters
    ----------
    weld_type      : 'butt' or 'fillet'
    quality_class  : 'WQ1', 'WQ2', or 'WQ3'
    weld_length    : mm (or consistent length unit)
    throat_or_leg  : mm — plate throat for butt, leg size for fillet
    parent_ftu     : MPa — parent material ultimate tensile strength
    safety_factor  : dimensionless (> 0)
    normal_load    : N — resultant normal force on the weld plane
    shear_load     : N — resultant shear force on the weld plane (>= 0)

    Returns
    -------
    dict with keys:
      weld_type, quality_class, efficiency, weld_area,
      sigma_allow, tau_allow, sigma_applied, tau_applied,
      mos_normal, mos_shear, mos_combined, interaction_ratio,
      compliant, findings
    """
    allowables = compute_allowable_stresses(parent_ftu, quality_class, safety_factor)
    weld_area = compute_weld_throat_area(weld_type, weld_length, throat_or_leg)
    applied = compute_applied_stresses(normal_load, shear_load, weld_area)

    sigma = applied["sigma_applied"]
    tau = applied["tau_applied"]
    sigma_allow = allowables["sigma_allow"]
    tau_allow = allowables["tau_allow"]

    mos_n = compute_margin_of_safety(abs(sigma), sigma_allow) if sigma != 0 else math.inf
    mos_s = compute_margin_of_safety(abs(tau), tau_allow) if tau != 0 else math.inf
    combined = check_combined_criterion(abs(sigma), abs(tau), sigma_allow, tau_allow)

    findings = []
    if mos_n < 0:
        findings.append(f"Normal MoS = {mos_n:.4f} < 0 — weld fails in normal mode.")
    if mos_s < 0:
        findings.append(f"Shear MoS = {mos_s:.4f} < 0 — weld fails in shear mode.")
    if combined["mos_combined"] < 0:
        findings.append(
            f"Combined MoS = {combined['mos_combined']:.4f} < 0 — "
            f"weld fails von Mises interaction (R = {combined['interaction_ratio']:.4f})."
        )

    compliant = len(findings) == 0

    return {
        "weld_type": weld_type.strip().lower(),
        "quality_class": allowables["quality_class"],
        "efficiency": allowables["efficiency"],
        "weld_area": weld_area,
        "sigma_allow": sigma_allow,
        "tau_allow": tau_allow,
        "sigma_applied": sigma,
        "tau_applied": tau,
        "mos_normal": mos_n,
        "mos_shear": mos_s,
        "mos_combined": combined["mos_combined"],
        "interaction_ratio": combined["interaction_ratio"],
        "compliant": compliant,
        "findings": findings,
    }
