"""
drd_modal_dynamic_response_logic.py

ECSS-E-ST-32C Annex J — Modal and Dynamic Response Analysis (MDRA) report logic.
Implements deterministic, offline engineering checks for modal completeness,
frequency margins, dynamic amplification, and report field validation.
stdlib only — no third-party dependencies.
"""

import math


# ---------------------------------------------------------------------------
# Mandatory MDRA report fields per ECSS-E-ST-32C Annex J
# ---------------------------------------------------------------------------

REQUIRED_MDRA_FIELDS = [
    "model_description",
    "boundary_conditions",
    "natural_frequencies",
    "mode_shapes",
    "effective_masses",
    "damping_assumptions",
    "dynamic_response_results",
    "frequency_separation_margins",
]


# ---------------------------------------------------------------------------
# Fundamental frequency check
# ---------------------------------------------------------------------------

def check_fundamental_frequency(freq_hz: float, min_freq_hz: float) -> dict:
    """
    Verify that a structural fundamental frequency meets the minimum stiffness
    requirement from the system-level load document.

    Returns a dict:
      pass         — True if freq_hz >= min_freq_hz
      freq_hz      — input frequency
      min_freq_hz  — required minimum
      margin_hz    — freq_hz - min_freq_hz (negative means non-conformance)
    """
    if not isinstance(freq_hz, (int, float)) or freq_hz <= 0:
        raise ValueError(f"freq_hz must be a positive number; got {freq_hz!r}")
    if not isinstance(min_freq_hz, (int, float)) or min_freq_hz <= 0:
        raise ValueError(f"min_freq_hz must be a positive number; got {min_freq_hz!r}")
    margin = freq_hz - min_freq_hz
    return {
        "pass": margin >= 0.0,
        "freq_hz": freq_hz,
        "min_freq_hz": min_freq_hz,
        "margin_hz": margin,
    }


# ---------------------------------------------------------------------------
# Frequency separation margin
# ---------------------------------------------------------------------------

def check_frequency_separation(
    structural_freq_hz: float,
    excitation_freq_hz: float,
    required_margin_ratio: float = 0.10,
) -> dict:
    """
    Check that a structural mode frequency is separated from an excitation
    frequency by at least required_margin_ratio (default 10 %).

    Separation ratio = |f_structure - f_excitation| / f_excitation.

    Returns a dict:
      pass                  — True if separation_ratio >= required_margin_ratio
      structural_freq_hz    — input structural mode frequency
      excitation_freq_hz    — input excitation frequency
      separation_ratio      — computed separation
      required_margin_ratio — threshold applied
    """
    if not isinstance(structural_freq_hz, (int, float)) or structural_freq_hz <= 0:
        raise ValueError(
            f"structural_freq_hz must be a positive number; got {structural_freq_hz!r}"
        )
    if not isinstance(excitation_freq_hz, (int, float)) or excitation_freq_hz <= 0:
        raise ValueError(
            f"excitation_freq_hz must be a positive number; got {excitation_freq_hz!r}"
        )
    if required_margin_ratio < 0:
        raise ValueError(
            f"required_margin_ratio must be >= 0; got {required_margin_ratio!r}"
        )
    separation = abs(structural_freq_hz - excitation_freq_hz) / excitation_freq_hz
    return {
        "pass": separation >= required_margin_ratio,
        "structural_freq_hz": structural_freq_hz,
        "excitation_freq_hz": excitation_freq_hz,
        "separation_ratio": separation,
        "required_margin_ratio": required_margin_ratio,
    }


# ---------------------------------------------------------------------------
# Effective mass fraction and modal completeness
# ---------------------------------------------------------------------------

def compute_effective_mass_fraction(
    effective_masses_kg: list, total_mass_kg: float
) -> float:
    """
    Compute the ratio of the sum of modal effective masses to the total
    structural mass for one translational axis.

    Raises ValueError for non-positive total_mass_kg or any negative entry.
    Slightly above 1.0 is permitted (numerical rounding in FE solvers).
    """
    if not isinstance(effective_masses_kg, (list, tuple)):
        raise TypeError(
            f"effective_masses_kg must be a list or tuple; got {type(effective_masses_kg).__name__!r}"
        )
    if not isinstance(total_mass_kg, (int, float)) or total_mass_kg <= 0:
        raise ValueError(f"total_mass_kg must be a positive number; got {total_mass_kg!r}")
    for i, m in enumerate(effective_masses_kg):
        if m < 0:
            raise ValueError(
                f"effective_masses_kg[{i}] = {m!r} is negative; effective masses must be >= 0"
            )
    return sum(effective_masses_kg) / total_mass_kg


def check_modal_completeness(fraction: float, threshold: float = 0.90) -> dict:
    """
    Check that the effective mass fraction meets the modal completeness
    threshold. Per ECSS-E-ST-32C Annex J the threshold is typically 0.90.

    Returns a dict:
      pass      — True if fraction >= threshold
      fraction  — input effective mass fraction
      threshold — applied threshold
      deficit   — max(0, threshold - fraction)
    """
    if not isinstance(fraction, (int, float)) or not (0 <= fraction <= 1.5):
        raise ValueError(
            f"fraction must be a number in [0, 1.5]; got {fraction!r}"
        )
    if not isinstance(threshold, (int, float)) or not (0 < threshold <= 1.0):
        raise ValueError(f"threshold must be in (0, 1]; got {threshold!r}")
    return {
        "pass": fraction >= threshold,
        "fraction": fraction,
        "threshold": threshold,
        "deficit": max(0.0, threshold - fraction),
    }


# ---------------------------------------------------------------------------
# Mode band assignment
# ---------------------------------------------------------------------------

def categorize_mode(
    freq_hz: float,
    rigid_body_cutoff_hz: float = 0.1,
    high_freq_cutoff_hz: float = 200.0,
) -> str:
    """
    Assign a mode to one of three frequency bands based on its natural
    frequency:
      'rigid-body'    — freq_hz < rigid_body_cutoff_hz
      'flexible'      — rigid_body_cutoff_hz <= freq_hz < high_freq_cutoff_hz
      'high-frequency'— freq_hz >= high_freq_cutoff_hz

    Raises ValueError for non-positive freq_hz or inconsistent cutoff values.
    """
    if not isinstance(freq_hz, (int, float)) or freq_hz <= 0:
        raise ValueError(f"freq_hz must be a positive number; got {freq_hz!r}")
    if rigid_body_cutoff_hz >= high_freq_cutoff_hz:
        raise ValueError(
            f"rigid_body_cutoff_hz ({rigid_body_cutoff_hz}) must be less than "
            f"high_freq_cutoff_hz ({high_freq_cutoff_hz})"
        )
    if freq_hz < rigid_body_cutoff_hz:
        return "rigid-body"
    if freq_hz < high_freq_cutoff_hz:
        return "flexible"
    return "high-frequency"


# ---------------------------------------------------------------------------
# Damping validation
# ---------------------------------------------------------------------------

def validate_damping_ratio(damping_ratio: float) -> dict:
    """
    Confirm that a damping ratio is physically valid for an underdamped
    structural mode (0 < zeta < 1). Emit a high_damping_warning when the
    ratio exceeds 0.05, which requires test-correlation justification for
    space structures.

    Returns a dict:
      valid                — True if underdamped (0 < zeta < 1)
      underdamped          — same as valid
      damping_ratio        — input value
      high_damping_warning — True if valid and damping_ratio > 0.05
    """
    if not isinstance(damping_ratio, (int, float)):
        raise TypeError(
            f"damping_ratio must be a numeric type; got {type(damping_ratio).__name__!r}"
        )
    underdamped = 0.0 < damping_ratio < 1.0
    return {
        "valid": underdamped,
        "underdamped": underdamped,
        "damping_ratio": damping_ratio,
        "high_damping_warning": underdamped and damping_ratio > 0.05,
    }


# ---------------------------------------------------------------------------
# Dynamic amplification factor
# ---------------------------------------------------------------------------

def compute_dynamic_amplification_factor(
    freq_ratio: float, damping_ratio: float
) -> float:
    """
    Compute the steady-state dynamic amplification factor (transmissibility
    magnitude) for a single-DOF system driven by a harmonic base input.

    DAF = 1 / sqrt((1 - r^2)^2 + (2*zeta*r)^2)

    where r = excitation_frequency / natural_frequency (freq_ratio)
    and   zeta = damping_ratio.

    Raises ValueError for non-physical inputs.
    Raises ZeroDivisionError at exact resonance with zero damping.
    """
    if not isinstance(freq_ratio, (int, float)) or freq_ratio < 0:
        raise ValueError(f"freq_ratio must be >= 0; got {freq_ratio!r}")
    if not isinstance(damping_ratio, (int, float)) or not (0 <= damping_ratio < 1):
        raise ValueError(f"damping_ratio must be in [0, 1); got {damping_ratio!r}")
    denom_sq = (1.0 - freq_ratio ** 2) ** 2 + (2.0 * damping_ratio * freq_ratio) ** 2
    if denom_sq == 0.0:
        raise ZeroDivisionError(
            "DAF is undefined at exact resonance (freq_ratio=1.0) with zero damping"
        )
    return 1.0 / math.sqrt(denom_sq)


# ---------------------------------------------------------------------------
# Modal participation factor
# ---------------------------------------------------------------------------

def compute_modal_participation_factor(
    mode_shape: list, mass_vector: list
) -> float:
    """
    Compute the modal participation factor L_r = {phi}^T [M] {1} for a
    lumped-mass model where [M] is a diagonal mass matrix.

    mode_shape   — list of modal displacement components phi_i (length n)
    mass_vector  — list of lumped masses m_i at each DOF (length n, all >= 0)

    Returns L_r = sum(phi_i * m_i).

    Raises ValueError for length mismatch, empty inputs, or negative masses.
    """
    if not mode_shape:
        raise ValueError("mode_shape and mass_vector must not be empty")
    if len(mode_shape) != len(mass_vector):
        raise ValueError(
            f"mode_shape (len={len(mode_shape)}) and mass_vector "
            f"(len={len(mass_vector)}) must have the same length"
        )
    for i, m in enumerate(mass_vector):
        if not isinstance(m, (int, float)) or m < 0:
            raise ValueError(f"mass_vector[{i}] = {m!r} is invalid; masses must be >= 0")
    return sum(phi * m for phi, m in zip(mode_shape, mass_vector))


# ---------------------------------------------------------------------------
# MDRA report field completeness
# ---------------------------------------------------------------------------

def assess_mdra_report_fields(
    report_dict: dict,
    required_fields: list = None,
) -> dict:
    """
    Check that an MDRA report dictionary contains all mandatory top-level
    fields per ECSS-E-ST-32C Annex J.

    Returns a dict:
      complete       — True if no fields are missing
      missing_fields — list of field names absent from report_dict
      present_fields — list of field names found in report_dict
    """
    if required_fields is None:
        required_fields = REQUIRED_MDRA_FIELDS
    if not isinstance(report_dict, dict):
        raise TypeError(
            f"report_dict must be a dict; got {type(report_dict).__name__!r}"
        )
    present = [f for f in required_fields if f in report_dict]
    missing = [f for f in required_fields if f not in report_dict]
    return {
        "complete": len(missing) == 0,
        "missing_fields": missing,
        "present_fields": present,
    }
