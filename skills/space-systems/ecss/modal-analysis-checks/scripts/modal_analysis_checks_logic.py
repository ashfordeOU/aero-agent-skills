"""
Modal analysis checks per ECSS-E-ST-32C §5.7.

Checks performed:
  - Rigid-body mode count (expect exactly 6 for an unconstrained FE model).
  - Rigid-body mode frequencies (all below the near-zero threshold).
  - Cumulative effective mass fraction per translational axis meets the
    programme threshold (typically ≥ 0.90).
  - First elastic-mode frequency meets each stated minimum-frequency
    requirement.

No third-party libraries — stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Mode:
    mode_number: int
    frequency_hz: float
    eff_mass_x: float   # translational effective mass, X axis
    eff_mass_y: float   # translational effective mass, Y axis
    eff_mass_z: float   # translational effective mass, Z axis
    eff_mass_rx: float  # rotational effective mass, RX axis
    eff_mass_ry: float  # rotational effective mass, RY axis
    eff_mass_rz: float  # rotational effective mass, RZ axis


@dataclass
class FrequencyRequirement:
    label: str       # e.g. "lateral" or "axial"
    min_hz: float    # minimum acceptable first elastic-mode frequency


@dataclass
class ModalCheckConfig:
    total_mass: float                              # structural total mass, kg
    rigid_body_freq_threshold_hz: float = 0.01    # modes below this → rigid-body
    effective_mass_fraction_threshold: float = 0.90
    frequency_requirements: List[FrequencyRequirement] = field(default_factory=list)


@dataclass
class CheckResult:
    passed: bool
    message: str
    value: Optional[float] = None
    limit: Optional[float] = None


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------

_TRANSLATIONAL_AXES = ('x', 'y', 'z')
_ROTATIONAL_AXES = ('rx', 'ry', 'rz')
_ALL_AXES = _TRANSLATIONAL_AXES + _ROTATIONAL_AXES

_AXIS_ATTR: Dict[str, str] = {
    'x':  'eff_mass_x',
    'y':  'eff_mass_y',
    'z':  'eff_mass_z',
    'rx': 'eff_mass_rx',
    'ry': 'eff_mass_ry',
    'rz': 'eff_mass_rz',
}


def identify_rigid_body_modes(modes: List[Mode], threshold_hz: float) -> List[Mode]:
    """Return modes whose frequency is strictly below *threshold_hz*."""
    if threshold_hz <= 0:
        raise ValueError("threshold_hz must be positive")
    return [m for m in modes if m.frequency_hz < threshold_hz]


def identify_elastic_modes(modes: List[Mode], threshold_hz: float) -> List[Mode]:
    """Return modes at or above *threshold_hz* (elastic / flexible modes)."""
    if threshold_hz <= 0:
        raise ValueError("threshold_hz must be positive")
    return [m for m in modes if m.frequency_hz >= threshold_hz]


def check_rigid_body_mode_count(
    modes: List[Mode],
    threshold_hz: float,
    expected_count: int = 6,
) -> CheckResult:
    """
    Verify that the FE model yields exactly *expected_count* rigid-body modes.

    For a free-free (unconstrained) model the expected count is 6.
    A grounded or constrained model may have fewer; pass *expected_count*
    accordingly.
    """
    rb_modes = identify_rigid_body_modes(modes, threshold_hz)
    count = len(rb_modes)
    passed = count == expected_count
    return CheckResult(
        passed=passed,
        message=(
            f"Rigid-body mode count: {count} "
            f"(expected {expected_count})"
        ),
        value=float(count),
        limit=float(expected_count),
    )


def check_rigid_body_frequencies(
    modes: List[Mode],
    threshold_hz: float,
) -> List[CheckResult]:
    """
    Confirm every rigid-body mode has a frequency below *threshold_hz*.
    Returns one CheckResult per rigid-body mode found.
    """
    rb_modes = identify_rigid_body_modes(modes, threshold_hz)
    results: List[CheckResult] = []
    for m in rb_modes:
        passed = m.frequency_hz < threshold_hz
        results.append(CheckResult(
            passed=passed,
            message=(
                f"Mode {m.mode_number}: rigid-body frequency "
                f"{m.frequency_hz:.6f} Hz < {threshold_hz} Hz"
            ),
            value=m.frequency_hz,
            limit=threshold_hz,
        ))
    return results


def compute_cumulative_effective_mass_fractions(
    modes: List[Mode],
    axis: str,
    total_mass: float,
) -> List[Tuple[int, float]]:
    """
    Compute the running cumulative effective mass fraction for *axis*.

    Modes are processed in ascending mode-number order.
    Returns [(mode_number, cumulative_fraction), ...].
    """
    if total_mass <= 0:
        raise ValueError("total_mass must be strictly positive")
    axis_key = axis.lower()
    if axis_key not in _AXIS_ATTR:
        raise ValueError(
            f"Unknown axis '{axis}'. Valid axes: {sorted(_AXIS_ATTR)}"
        )
    attr = _AXIS_ATTR[axis_key]
    cumulative = 0.0
    output: List[Tuple[int, float]] = []
    for m in sorted(modes, key=lambda m: m.mode_number):
        cumulative += getattr(m, attr)
        output.append((m.mode_number, cumulative / total_mass))
    return output


def check_effective_mass_fraction(
    modes: List[Mode],
    axis: str,
    total_mass: float,
    threshold: float,
) -> CheckResult:
    """
    Check that the final cumulative effective mass fraction for *axis* meets
    *threshold* (e.g. 0.90 for a 90 % criterion).
    """
    fractions = compute_cumulative_effective_mass_fractions(modes, axis, total_mass)
    if not fractions:
        return CheckResult(
            passed=False,
            message=f"No modes available to evaluate effective mass fraction for axis {axis}",
            value=None,
            limit=threshold,
        )
    _, final_fraction = fractions[-1]
    passed = final_fraction >= threshold
    return CheckResult(
        passed=passed,
        message=(
            f"Axis {axis.upper()}: cumulative effective mass fraction "
            f"{final_fraction:.4f} vs threshold {threshold:.2f}"
        ),
        value=final_fraction,
        limit=threshold,
    )


def check_minimum_frequency(
    modes: List[Mode],
    req: FrequencyRequirement,
    rigid_body_threshold_hz: float,
) -> CheckResult:
    """
    Verify that the lowest elastic-mode frequency satisfies *req*.
    Rigid-body modes (below *rigid_body_threshold_hz*) are excluded before
    the comparison so a near-zero rigid-body frequency does not trip the
    check.
    """
    elastic = identify_elastic_modes(modes, rigid_body_threshold_hz)
    if not elastic:
        return CheckResult(
            passed=False,
            message=f"No elastic modes found; cannot evaluate '{req.label}' requirement",
            value=None,
            limit=req.min_hz,
        )
    first = min(elastic, key=lambda m: m.frequency_hz)
    passed = first.frequency_hz >= req.min_hz
    return CheckResult(
        passed=passed,
        message=(
            f"'{req.label}': first elastic mode {first.frequency_hz:.4f} Hz "
            f">= minimum {req.min_hz:.4f} Hz"
        ),
        value=first.frequency_hz,
        limit=req.min_hz,
    )


# ---------------------------------------------------------------------------
# Aggregated runner
# ---------------------------------------------------------------------------

def run_all_checks(
    modes: List[Mode],
    config: ModalCheckConfig,
) -> Dict[str, List[CheckResult]]:
    """
    Execute all modal analysis checks and return results grouped by check name.
    Raises ValueError for obviously invalid inputs rather than silently
    producing misleading results.
    """
    if not modes:
        raise ValueError("'modes' must contain at least one Mode entry")
    if config.total_mass <= 0:
        raise ValueError("config.total_mass must be strictly positive")

    results: Dict[str, List[CheckResult]] = {}

    results['rigid_body_count'] = [
        check_rigid_body_mode_count(modes, config.rigid_body_freq_threshold_hz)
    ]

    results['rigid_body_frequencies'] = check_rigid_body_frequencies(
        modes, config.rigid_body_freq_threshold_hz
    )

    for axis in _TRANSLATIONAL_AXES:
        results[f'effective_mass_fraction_{axis}'] = [
            check_effective_mass_fraction(
                modes, axis, config.total_mass,
                config.effective_mass_fraction_threshold,
            )
        ]

    freq_results: List[CheckResult] = []
    for req in config.frequency_requirements:
        freq_results.append(
            check_minimum_frequency(modes, req, config.rigid_body_freq_threshold_hz)
        )
    results['frequency_requirements'] = freq_results

    return results


def summarize(results: Dict[str, List[CheckResult]]) -> Tuple[bool, List[str]]:
    """
    Collapse check results into (all_passed, failure_messages).
    """
    failures: List[str] = []
    for check_name, check_list in results.items():
        for cr in check_list:
            if not cr.passed:
                failures.append(f"[{check_name}] {cr.message}")
    return len(failures) == 0, failures
