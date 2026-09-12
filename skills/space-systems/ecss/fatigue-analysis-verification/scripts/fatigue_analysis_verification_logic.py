"""
Fatigue analysis verification logic per ECSS-E-ST-32C clause 4.6.2.8.

Implements load spectrum validation, S-N curve lookup, Miner's rule
damage summation, scatter factor application, and pass/fail determination.
stdlib only — no external dependencies.
"""


class FatigueError(Exception):
    """Raised for invalid inputs or unsupported materials."""


# S-N curve data per material: (S_ref [MPa], N_ref [cycles], exponent b)
# Power-law model: N_f = N_ref * (S_ref / S)^(1/b)
_SN_CURVES = {
    "Al2024-T3":  (420.0, 1_000_000.0, 0.10),
    "Ti-6Al-4V":  (550.0, 1_000_000.0, 0.08),
    "steel-4340": (700.0, 1_000_000.0, 0.09),
    "CFRP-UD":    (600.0, 1_000_000.0, 0.07),
}

# Endurance limits [MPa]: stress at or below this value → no damage (None = no limit)
_ENDURANCE_LIMITS = {
    "Al2024-T3":  None,
    "Ti-6Al-4V":  None,
    "steel-4340": 350.0,
    "CFRP-UD":    None,
}


def list_supported_materials():
    """Return the list of material identifiers with S-N data."""
    return list(_SN_CURVES.keys())


def validate_load_spectrum(spectrum):
    """
    Validate a load spectrum: a list of dicts with keys 'stress_range' and 'n_cycles'.
    Each stress_range and n_cycles must be strictly positive.
    Returns the validated spectrum or raises FatigueError.
    """
    if not spectrum:
        raise FatigueError("Load spectrum must not be empty.")
    for i, block in enumerate(spectrum):
        s = block.get("stress_range")
        n = block.get("n_cycles")
        if s is None or n is None:
            raise FatigueError(
                f"Block {i}: missing required key 'stress_range' or 'n_cycles'."
            )
        if s <= 0:
            raise FatigueError(
                f"Block {i}: stress_range must be strictly positive, got {s}."
            )
        if n <= 0:
            raise FatigueError(
                f"Block {i}: n_cycles must be strictly positive, got {n}."
            )
    return spectrum


def get_sn_parameters(material):
    """
    Return (S_ref, N_ref, b) for the given material identifier.
    Raises FatigueError for unknown materials.
    """
    if material not in _SN_CURVES:
        raise FatigueError(
            f"Unknown material '{material}'. "
            f"Supported: {list(_SN_CURVES.keys())}"
        )
    return _SN_CURVES[material]


def cycles_to_failure(material, stress_range):
    """
    Compute cycles to failure N_f via the power-law S-N model:
        N_f = N_ref * (S_ref / stress_range)^(1/b)

    Returns float('inf') when stress_range is at or below the material's
    endurance limit (no damage accumulates below that threshold).
    Raises FatigueError for non-positive stress_range or unknown material.
    """
    if stress_range <= 0:
        raise FatigueError(
            f"stress_range must be strictly positive, got {stress_range}."
        )
    S_ref, N_ref, b = get_sn_parameters(material)
    endurance = _ENDURANCE_LIMITS.get(material)
    if endurance is not None and stress_range <= endurance:
        return float("inf")
    return N_ref * (S_ref / stress_range) ** (1.0 / b)


def miner_damage(material, spectrum):
    """
    Compute Palmgren-Miner cumulative damage for a load spectrum:
        D = sum(n_i / N_f_i)  for all blocks with finite N_f_i

    Validates the spectrum before computing. Returns a float.
    """
    validate_load_spectrum(spectrum)
    D = 0.0
    for block in spectrum:
        Nf = cycles_to_failure(material, block["stress_range"])
        if Nf != float("inf"):
            D += block["n_cycles"] / Nf
    return D


def apply_scatter_factor(damage, scatter_factor):
    """
    Return design damage = damage * scatter_factor.
    Raises FatigueError when scatter_factor is not strictly positive.
    """
    if scatter_factor <= 0:
        raise FatigueError(
            f"scatter_factor must be strictly positive, got {scatter_factor}."
        )
    return damage * scatter_factor


def verify_fatigue(material, spectrum, scatter_factor):
    """
    Run the complete ECSS-E-ST-32C §4.6.2.8 fatigue verification sequence.

    Returns a dict:
        {
            "material":      str,
            "raw_damage":    float,   # Miner sum without scatter
            "design_damage": float,   # raw_damage * scatter_factor
            "scatter_factor": float,
            "pass":          bool,    # True when design_damage < 1.0
            "margin":        float,   # 1/design_damage - 1  (positive => pass)
        }

    Raises FatigueError on invalid inputs (bad material, bad spectrum,
    non-positive scatter_factor).
    """
    if scatter_factor <= 0:
        raise FatigueError(
            f"scatter_factor must be strictly positive, got {scatter_factor}."
        )
    raw = miner_damage(material, spectrum)
    design = apply_scatter_factor(raw, scatter_factor)
    passed = design < 1.0
    margin = (1.0 / design - 1.0) if design > 0.0 else float("inf")
    return {
        "material": material,
        "raw_damage": raw,
        "design_damage": design,
        "scatter_factor": scatter_factor,
        "pass": passed,
        "margin": margin,
    }
