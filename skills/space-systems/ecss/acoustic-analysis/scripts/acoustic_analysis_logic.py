"""
Acoustic loading response analysis logic — ECSS-E-ST-32C clause 4.6.2.6.

Implements deterministic, checkable engineering procedures for diffuse-acoustic
field analysis: SPL conversion, OASPL aggregation, Schroeder-frequency diffuse-field
check, frequency-regime categorization, acoustic-force computation, margin-of-safety
calculation, acoustic-fatigue risk screening, and compliance aggregation.

stdlib only — no third-party dependencies.
"""

import math

REFERENCE_PRESSURE_PA = 20e-6  # 20 µPa — standard acoustic reference pressure


def spl_to_pressure(spl_db: float) -> float:
    """Return RMS acoustic pressure (Pa) for a given SPL (dB re 20 µPa)."""
    if not isinstance(spl_db, (int, float)):
        raise TypeError("spl_db must be a numeric value")
    return REFERENCE_PRESSURE_PA * (10.0 ** (spl_db / 20.0))


def pressure_to_spl(pressure_pa: float) -> float:
    """Return SPL (dB re 20 µPa) for a given RMS acoustic pressure (Pa)."""
    if not isinstance(pressure_pa, (int, float)):
        raise TypeError("pressure_pa must be a numeric value")
    if pressure_pa <= 0.0:
        raise ValueError("pressure_pa must be strictly positive")
    return 20.0 * math.log10(pressure_pa / REFERENCE_PRESSURE_PA)


def compute_oaspl(spl_values_db: list) -> float:
    """
    Return the overall SPL (dB) from a list of 1/3-octave band SPL values.

    Bands are combined on a linear power scale to avoid arithmetic-mean error.
    Raises ValueError when the list is empty.
    """
    if not spl_values_db:
        raise ValueError("spl_values_db must contain at least one band level")
    linear_sum = sum(10.0 ** (spl / 10.0) for spl in spl_values_db)
    return 10.0 * math.log10(linear_sum)


def categorize_frequency_regime(frequency_hz: float) -> str:
    """
    Return 'low' when frequency_hz < 200 Hz (global-mode dominated),
    or 'high' when frequency_hz >= 200 Hz (local-panel / SEA dominated).

    Raises ValueError for non-positive input.
    """
    if not isinstance(frequency_hz, (int, float)):
        raise TypeError("frequency_hz must be a numeric value")
    if frequency_hz <= 0.0:
        raise ValueError("frequency_hz must be strictly positive")
    return "low" if frequency_hz < 200.0 else "high"


def compute_acoustic_force(spl_db: float, panel_area_m2: float) -> float:
    """
    Return acoustic force (N) on a panel given SPL (dB) and panel area (m²).

    F = p_rms × A, where p_rms is derived from spl_db.
    Raises ValueError for non-positive panel area.
    """
    if panel_area_m2 <= 0.0:
        raise ValueError("panel_area_m2 must be strictly positive")
    return spl_to_pressure(spl_db) * panel_area_m2


def compute_margin_of_safety(allowable: float, response: float) -> float:
    """
    Return margin of safety: MS = (allowable / response) − 1.

    A negative MS indicates structural non-compliance.
    Raises ValueError for non-positive inputs.
    """
    if allowable <= 0.0:
        raise ValueError("allowable must be strictly positive")
    if response <= 0.0:
        raise ValueError("response must be strictly positive")
    return (allowable / response) - 1.0


def check_diffuse_field(
    frequency_hz: float, reverb_time_s: float, volume_m3: float
) -> dict:
    """
    Check whether the diffuse-field assumption holds at frequency_hz.

    Schroeder frequency: f_s = 2000 × √(T60 / V)

    Returns a dict with keys:
      schroeder_frequency_hz  — computed Schroeder frequency
      analysis_frequency_hz   — the supplied frequency
      diffuse_field_valid     — True when frequency_hz > f_s

    Raises ValueError for non-positive inputs.
    """
    if frequency_hz <= 0.0:
        raise ValueError("frequency_hz must be strictly positive")
    if reverb_time_s <= 0.0:
        raise ValueError("reverb_time_s must be strictly positive")
    if volume_m3 <= 0.0:
        raise ValueError("volume_m3 must be strictly positive")

    schroeder_hz = 2000.0 * math.sqrt(reverb_time_s / volume_m3)
    return {
        "schroeder_frequency_hz": schroeder_hz,
        "analysis_frequency_hz": frequency_hz,
        "diffuse_field_valid": frequency_hz > schroeder_hz,
    }


def compute_radiation_efficiency(
    frequency_hz: float, critical_frequency_hz: float
) -> float:
    """
    Return the radiation efficiency σ for a panel.

    Below the critical frequency: σ = √(f / f_c)  (simplified model, σ < 1).
    At or above the critical frequency: σ = 1.0.

    Raises ValueError for non-positive inputs.
    """
    if frequency_hz <= 0.0:
        raise ValueError("frequency_hz must be strictly positive")
    if critical_frequency_hz <= 0.0:
        raise ValueError("critical_frequency_hz must be strictly positive")

    if frequency_hz >= critical_frequency_hz:
        return 1.0
    return math.sqrt(frequency_hz / critical_frequency_hz)


def compute_third_octave_center_frequency(band_number: int) -> float:
    """
    Return the 1/3-octave centre frequency (Hz) for the given ANSI S1.6 band number.

    Reference: f = 1000 × 2^((n − 30) / 3) Hz.
    Band 30 corresponds to 1000 Hz.

    Raises TypeError when band_number is not an integer.
    """
    if not isinstance(band_number, int):
        raise TypeError("band_number must be an integer")
    return 1000.0 * (2.0 ** ((band_number - 30) / 3.0))


def check_acoustic_fatigue_risk(
    oaspl_db: float,
    exposure_duration_s: float,
    threshold_db: float = 140.0,
) -> dict:
    """
    Screen for acoustic fatigue risk.

    Risk is flagged when OASPL ≥ threshold_db AND exposure_duration_s ≥ 60 s.

    Returns a dict with keys:
      oaspl_db               — input OASPL
      exposure_duration_s    — input duration
      threshold_db           — screening threshold used
      exceeds_level          — True when OASPL ≥ threshold_db
      long_exposure          — True when duration ≥ 60 s
      acoustic_fatigue_risk  — True when both conditions are met

    Raises ValueError for non-physical inputs.
    """
    if not isinstance(oaspl_db, (int, float)):
        raise TypeError("oaspl_db must be a numeric value")
    if exposure_duration_s < 0.0:
        raise ValueError("exposure_duration_s must be non-negative")

    exceeds_level = oaspl_db >= threshold_db
    long_exposure = exposure_duration_s >= 60.0
    return {
        "oaspl_db": oaspl_db,
        "exposure_duration_s": exposure_duration_s,
        "threshold_db": threshold_db,
        "exceeds_level": exceeds_level,
        "long_exposure": long_exposure,
        "acoustic_fatigue_risk": exceeds_level and long_exposure,
    }


def aggregate_findings(findings: list) -> dict:
    """
    Aggregate per-surface compliance findings into a summary.

    Each element of findings must be a dict with at minimum:
      surface_id  — unique surface identifier (str or int)
      compliant   — bool

    Returns a dict with keys:
      total_surfaces          — total number of surfaces assessed
      compliant_count         — number of compliant surfaces
      non_compliant_surfaces  — list of surface_id values that are not compliant
      all_compliant           — True when every surface is compliant

    Raises TypeError / ValueError for malformed input.
    """
    if not isinstance(findings, list):
        raise TypeError("findings must be a list of dicts")
    for idx, entry in enumerate(findings):
        if not isinstance(entry, dict):
            raise TypeError(f"findings[{idx}] must be a dict")
        if "surface_id" not in entry:
            raise ValueError(f"findings[{idx}] is missing 'surface_id'")
        if "compliant" not in entry:
            raise ValueError(f"findings[{idx}] is missing 'compliant'")

    non_compliant = [e["surface_id"] for e in findings if not e["compliant"]]
    return {
        "total_surfaces": len(findings),
        "compliant_count": len(findings) - len(non_compliant),
        "non_compliant_surfaces": non_compliant,
        "all_compliant": len(non_compliant) == 0,
    }
