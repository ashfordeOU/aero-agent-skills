"""
Rigid-body motion checks for finite element models.
Implements the three-check procedure from ECSS-E-ST-32C §5.4 (paraphrased;
no verbatim standard text reproduced).

Checks
------
1. Mass matrix: assembled total mass vs. reference mass within a fractional tolerance.
2. Strain energy per rigid-body mode: near-zero for each of TX/TY/TZ/RX/RY/RZ.
3. Residual force per rigid-body mode: near-zero for each of TX/TY/TZ/RX/RY/RZ.

All logic is deterministic and offline (stdlib only).
"""

from dataclasses import dataclass
from typing import Dict, List

RB_MODE_LABELS = ("TX", "TY", "TZ", "RX", "RY", "RZ")


@dataclass
class MassCheckResult:
    expected_mass: float
    computed_mass: float
    tolerance_fraction: float
    relative_error: float
    passed: bool
    message: str


@dataclass
class StrainEnergyResult:
    mode_label: str
    strain_energy: float
    threshold: float
    passed: bool
    message: str


@dataclass
class ResidualForceResult:
    mode_label: str
    residual_force: float
    threshold: float
    passed: bool
    message: str


@dataclass
class RigidBodyCheckSummary:
    mass_result: MassCheckResult
    strain_energy_results: List[StrainEnergyResult]
    residual_force_results: List[ResidualForceResult]
    overall_passed: bool
    findings: List[str]


def check_mass_matrix(
    expected_mass: float,
    computed_mass: float,
    tolerance_fraction: float,
) -> MassCheckResult:
    """
    Verify the assembled FEM mass matrix total against the reference mass.

    Parameters
    ----------
    expected_mass       : reference (design) total mass, kg — must be > 0
    computed_mass       : total mass from summing the assembled mass matrix diagonal, kg
    tolerance_fraction  : maximum acceptable relative error, e.g. 0.01 for 1 %
    """
    if expected_mass <= 0.0:
        raise ValueError(f"expected_mass must be positive; got {expected_mass}")
    if computed_mass < 0.0:
        raise ValueError(f"computed_mass must be non-negative; got {computed_mass}")
    if not (0.0 < tolerance_fraction <= 1.0):
        raise ValueError(
            f"tolerance_fraction must be in (0, 1]; got {tolerance_fraction}"
        )

    relative_error = abs(computed_mass - expected_mass) / expected_mass
    passed = relative_error <= tolerance_fraction

    if passed:
        message = (
            f"Mass check PASS: relative error {relative_error:.4e} "
            f"<= tolerance {tolerance_fraction:.4e}"
        )
    else:
        message = (
            f"Mass check FAIL: relative error {relative_error:.4e} "
            f"> tolerance {tolerance_fraction:.4e} — "
            f"check mass items, density tables, and non-structural masses"
        )

    return MassCheckResult(
        expected_mass=expected_mass,
        computed_mass=computed_mass,
        tolerance_fraction=tolerance_fraction,
        relative_error=relative_error,
        passed=passed,
        message=message,
    )


def _validate_mode_label(mode_label: str) -> None:
    if mode_label not in RB_MODE_LABELS:
        raise ValueError(
            f"mode_label must be one of {RB_MODE_LABELS}; got '{mode_label}'"
        )


def _validate_mode_dict(mode_dict: Dict[str, float], label: str) -> None:
    missing = [lbl for lbl in RB_MODE_LABELS if lbl not in mode_dict]
    if missing:
        raise ValueError(f"{label}: missing rigid-body mode labels {missing}")
    extra = [lbl for lbl in mode_dict if lbl not in RB_MODE_LABELS]
    if extra:
        raise ValueError(f"{label}: unrecognized mode labels {extra}")


def check_strain_energy_per_mode(
    mode_label: str,
    strain_energy: float,
    threshold: float,
) -> StrainEnergyResult:
    """
    For one rigid-body displacement mode, verify strain energy is below threshold.

    A correctly modelled free-free structure produces essentially zero internal
    strain energy when a rigid-body displacement is applied.  Non-zero energy
    indicates spurious stiffness (grounded DOFs, conflicting constraints, etc.).

    Parameters
    ----------
    mode_label    : one of TX, TY, TZ, RX, RY, RZ
    strain_energy : computed internal strain energy for the applied displacement, J
    threshold     : acceptance limit, J — must be > 0
    """
    _validate_mode_label(mode_label)
    if strain_energy < 0.0:
        raise ValueError(f"strain_energy must be non-negative; got {strain_energy}")
    if threshold <= 0.0:
        raise ValueError(f"threshold must be positive; got {threshold}")

    passed = strain_energy <= threshold
    if passed:
        message = (
            f"Strain energy PASS [{mode_label}]: "
            f"{strain_energy:.4e} J <= {threshold:.4e} J"
        )
    else:
        message = (
            f"Strain energy FAIL [{mode_label}]: "
            f"{strain_energy:.4e} J > {threshold:.4e} J — "
            f"check for spurious grounding or constraint conflicts"
        )

    return StrainEnergyResult(
        mode_label=mode_label,
        strain_energy=strain_energy,
        threshold=threshold,
        passed=passed,
        message=message,
    )


def check_strain_energy_all_modes(
    mode_energies: Dict[str, float],
    threshold: float,
) -> List[StrainEnergyResult]:
    """
    Run the strain energy check for all six rigid-body modes.

    Parameters
    ----------
    mode_energies : mapping of mode label -> strain energy (J) for all six modes
    threshold     : shared acceptance limit applied to every mode, J
    """
    _validate_mode_dict(mode_energies, "mode_energies")
    return [
        check_strain_energy_per_mode(lbl, mode_energies[lbl], threshold)
        for lbl in RB_MODE_LABELS
    ]


def check_residual_force_per_mode(
    mode_label: str,
    residual_force: float,
    threshold: float,
) -> ResidualForceResult:
    """
    For one rigid-body displacement mode, verify the residual force magnitude
    is below threshold.

    Applying a rigid-body displacement to a properly assembled free-free model
    produces no net internal force.  A non-zero residual indicates a force-balance
    error in the stiffness or constraint assembly.

    Parameters
    ----------
    mode_label     : one of TX, TY, TZ, RX, RY, RZ
    residual_force : magnitude of the residual force vector, N (or N·m for rotation)
    threshold      : acceptance limit — must be > 0
    """
    _validate_mode_label(mode_label)
    if residual_force < 0.0:
        raise ValueError(f"residual_force must be non-negative; got {residual_force}")
    if threshold <= 0.0:
        raise ValueError(f"threshold must be positive; got {threshold}")

    passed = residual_force <= threshold
    if passed:
        message = (
            f"Residual force PASS [{mode_label}]: "
            f"{residual_force:.4e} <= {threshold:.4e}"
        )
    else:
        message = (
            f"Residual force FAIL [{mode_label}]: "
            f"{residual_force:.4e} > {threshold:.4e} — "
            f"check stiffness and constraint assembly for force-balance errors"
        )

    return ResidualForceResult(
        mode_label=mode_label,
        residual_force=residual_force,
        threshold=threshold,
        passed=passed,
        message=message,
    )


def check_residual_forces_all_modes(
    mode_residuals: Dict[str, float],
    threshold: float,
) -> List[ResidualForceResult]:
    """
    Run the residual force check for all six rigid-body modes.

    Parameters
    ----------
    mode_residuals : mapping of mode label -> residual force magnitude for all six modes
    threshold      : shared acceptance limit applied to every mode
    """
    _validate_mode_dict(mode_residuals, "mode_residuals")
    return [
        check_residual_force_per_mode(lbl, mode_residuals[lbl], threshold)
        for lbl in RB_MODE_LABELS
    ]


def aggregate_rigid_body_check(
    mass_result: MassCheckResult,
    strain_energy_results: List[StrainEnergyResult],
    residual_force_results: List[ResidualForceResult],
) -> RigidBodyCheckSummary:
    """
    Combine individual check results into an overall summary.

    The model passes rigid-body checks only when every sub-check passes.
    All failing sub-check messages are collected into the findings list.
    """
    findings: List[str] = []

    if not mass_result.passed:
        findings.append(mass_result.message)

    for r in strain_energy_results:
        if not r.passed:
            findings.append(r.message)

    for r in residual_force_results:
        if not r.passed:
            findings.append(r.message)

    overall_passed = (
        mass_result.passed
        and all(r.passed for r in strain_energy_results)
        and all(r.passed for r in residual_force_results)
    )

    return RigidBodyCheckSummary(
        mass_result=mass_result,
        strain_energy_results=strain_energy_results,
        residual_force_results=residual_force_results,
        overall_passed=overall_passed,
        findings=findings,
    )
