"""
Aerothermodynamic and aeroelastic test logic for ECSS-E-ST-32C §4.6.3.23–4.6.3.24.

All functions are deterministic and offline (stdlib only).
"""

_AEROTHERMO_TYPES = {"aerothermodynamic", "thermal-only"}
_AEROELASTIC_TYPES = {"flutter-clearance", "divergence-check", "control-reversal"}
_VALID_CATEGORIES = {"aerothermodynamic", "aeroelastic"}


class AeroTestError(ValueError):
    """Raised when an input violates a test-logic precondition."""


def categorize_test_item(test_type: str) -> str:
    """Return the primary category ('aerothermodynamic' or 'aeroelastic') for a test type.

    Raises AeroTestError for unrecognized or uncategorized test types.
    """
    normalized = test_type.strip().lower()
    if normalized in _AEROTHERMO_TYPES:
        return "aerothermodynamic"
    if normalized in _AEROELASTIC_TYPES:
        return "aeroelastic"
    raise AeroTestError(
        f"Unrecognized test type '{test_type}'. Must be one of: "
        + ", ".join(sorted(_AEROTHERMO_TYPES | _AEROELASTIC_TYPES))
    )


def compute_heat_flux_margin(applied_flux: float, allowable_flux: float) -> float:
    """Return the heat-flux margin factor: (allowable / applied) - 1.

    A non-negative margin means the test item is within the allowable envelope.
    Raises AeroTestError if either input is non-positive.
    """
    if applied_flux <= 0:
        raise AeroTestError(f"applied_flux must be positive, got {applied_flux}")
    if allowable_flux <= 0:
        raise AeroTestError(f"allowable_flux must be positive, got {allowable_flux}")
    return (allowable_flux / applied_flux) - 1.0


def check_temperature_limit(peak_temp_K: float, allowable_temp_K: float) -> dict:
    """Check whether peak temperature is within the material allowable.

    Returns a dict with keys 'pass' (bool), 'peak_temp_K', 'allowable_temp_K',
    and 'excess_K' (negative means margin, positive means exceedance).
    Raises AeroTestError for non-positive inputs.
    """
    if peak_temp_K <= 0:
        raise AeroTestError(f"peak_temp_K must be positive, got {peak_temp_K}")
    if allowable_temp_K <= 0:
        raise AeroTestError(f"allowable_temp_K must be positive, got {allowable_temp_K}")
    excess = peak_temp_K - allowable_temp_K
    return {
        "pass": peak_temp_K <= allowable_temp_K,
        "peak_temp_K": peak_temp_K,
        "allowable_temp_K": allowable_temp_K,
        "excess_K": excess,
    }


def compute_flutter_speed_margin(
    flutter_onset_speed: float,
    design_limit_speed: float,
    required_margin_factor: float = 1.15,
) -> dict:
    """Check whether the flutter onset speed meets the required margin over the design limit.

    Returns a dict with keys 'pass' (bool), 'actual_factor', 'required_factor',
    'flutter_onset_speed', and 'design_limit_speed'.
    Raises AeroTestError for non-positive inputs or factor ≤ 1.
    """
    if flutter_onset_speed <= 0:
        raise AeroTestError(f"flutter_onset_speed must be positive, got {flutter_onset_speed}")
    if design_limit_speed <= 0:
        raise AeroTestError(f"design_limit_speed must be positive, got {design_limit_speed}")
    if required_margin_factor <= 1.0:
        raise AeroTestError(f"required_margin_factor must be > 1.0, got {required_margin_factor}")
    actual_factor = flutter_onset_speed / design_limit_speed
    return {
        "pass": actual_factor >= required_margin_factor,
        "actual_factor": actual_factor,
        "required_factor": required_margin_factor,
        "flutter_onset_speed": flutter_onset_speed,
        "design_limit_speed": design_limit_speed,
    }


def check_damping_ratio(measured_damping: float, min_required_damping: float) -> dict:
    """Verify that measured modal damping meets the minimum structural damping floor.

    Returns a dict with keys 'pass' (bool), 'measured', 'required', and 'margin'.
    A zero or negative measured damping indicates instability — result is always fail.
    Raises AeroTestError if min_required_damping is negative.
    """
    if min_required_damping < 0:
        raise AeroTestError(f"min_required_damping must be >= 0, got {min_required_damping}")
    margin = measured_damping - min_required_damping
    return {
        "pass": measured_damping >= min_required_damping,
        "measured": measured_damping,
        "required": min_required_damping,
        "margin": margin,
    }


def compute_dynamic_pressure_stability_factor(
    critical_dynamic_pressure: float,
    design_dynamic_pressure: float,
) -> float:
    """Return the dynamic-pressure stability factor: critical_dp / design_dp.

    A factor >= 1.0 means the structure is stable at the design condition.
    Raises AeroTestError for non-positive inputs.
    """
    if critical_dynamic_pressure <= 0:
        raise AeroTestError(
            f"critical_dynamic_pressure must be positive, got {critical_dynamic_pressure}"
        )
    if design_dynamic_pressure <= 0:
        raise AeroTestError(
            f"design_dynamic_pressure must be positive, got {design_dynamic_pressure}"
        )
    return critical_dynamic_pressure / design_dynamic_pressure


def compute_combined_thermal_structural_utilization(
    thermal_utilization: float,
    structural_utilization: float,
) -> dict:
    """Compute the combined utilization for a simultaneous thermal-structural test.

    Uses SRSS (square-root-sum-of-squares) for interaction; interaction > 1.0 is a finding.
    Raises AeroTestError if either utilization is negative.
    """
    if thermal_utilization < 0:
        raise AeroTestError(f"thermal_utilization must be >= 0, got {thermal_utilization}")
    if structural_utilization < 0:
        raise AeroTestError(f"structural_utilization must be >= 0, got {structural_utilization}")
    interaction = (thermal_utilization ** 2 + structural_utilization ** 2) ** 0.5
    return {
        "pass": interaction <= 1.0,
        "interaction": interaction,
        "thermal_utilization": thermal_utilization,
        "structural_utilization": structural_utilization,
    }


def validate_test_sequence(phases: list) -> dict:
    """Validate that a list of test phase names forms an acceptable sequence.

    Acceptable phase names: 'pre-test-inspection', 'aerothermodynamic-load',
    'aeroelastic-sweep', 'peak-heat-flux', 'flutter-dip', 'post-test-inspection'.
    The sequence must start with 'pre-test-inspection' and end with 'post-test-inspection'.
    Returns a dict with 'valid' (bool) and 'findings' (list of str).
    """
    valid_phases = {
        "pre-test-inspection",
        "aerothermodynamic-load",
        "aeroelastic-sweep",
        "peak-heat-flux",
        "flutter-dip",
        "post-test-inspection",
    }
    findings = []
    if not phases:
        findings.append("Test sequence is empty.")
        return {"valid": False, "findings": findings}
    if phases[0] != "pre-test-inspection":
        findings.append(f"Sequence must begin with 'pre-test-inspection', got '{phases[0]}'.")
    if phases[-1] != "post-test-inspection":
        findings.append(f"Sequence must end with 'post-test-inspection', got '{phases[-1]}'.")
    for phase in phases:
        if phase not in valid_phases:
            findings.append(f"Unrecognized phase '{phase}'.")
    return {"valid": len(findings) == 0, "findings": findings}
