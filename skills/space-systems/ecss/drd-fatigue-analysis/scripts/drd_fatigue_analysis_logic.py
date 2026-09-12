"""
Fatigue analysis report verification logic — ECSS-E-ST-32C Annex D (DRD-FA).

Implements deterministic, offline engineering logic for:
  - load spectrum validation and loading-type categorization
  - simplified rainflow-compatible cycle extraction from peak-valley sequences
  - log-log S-N curve interpolation / extrapolation
  - Miner's linear damage rule summation
  - scatter factor application and life margin computation
  - full per-location fatigue assessment with compliance verdict

No third-party dependencies (stdlib only).
"""

import math
from typing import List, NamedTuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class LoadCycle(NamedTuple):
    """One stress-amplitude block in a fatigue spectrum."""
    stress_amplitude: float   # MPa, >= 0
    mean_stress: float        # MPa
    count: float              # number of occurrences (may be fractional for half-cycles)


class SNPoint(NamedTuple):
    """Single point on a material S-N curve."""
    stress_amplitude: float   # MPa, > 0
    allowable_cycles: float   # N, > 0


class FatigueSpectrum(NamedTuple):
    """Named collection of load cycles representing one location's history."""
    name: str
    cycles: tuple             # tuple of LoadCycle


class FatigueResult(NamedTuple):
    """Full assessment outcome for one fatigue-critical location."""
    location: str
    total_damage: float       # Miner's D = sum(n_i / N_i)
    life_cycles: float        # predicted failure life in cycles (inf if D == 0)
    required_life: float      # design life requirement in cycles
    scatter_factor: float     # divisor applied to predicted life
    adjusted_life: float      # life_cycles / scatter_factor
    margin: float             # (adjusted_life / required_life) - 1
    compliant: bool           # margin >= 0


# ---------------------------------------------------------------------------
# Spectrum helpers
# ---------------------------------------------------------------------------

VALID_LOADING_TYPES = frozenset(
    {"constant_amplitude", "variable_amplitude", "combined"}
)


def validate_spectrum(spectrum: FatigueSpectrum) -> None:
    """Raise ValueError if any cycle in the spectrum has invalid values."""
    for i, cycle in enumerate(spectrum.cycles):
        if cycle.stress_amplitude < 0:
            raise ValueError(
                f"Cycle {i} in spectrum '{spectrum.name}': "
                f"stress_amplitude must be >= 0, got {cycle.stress_amplitude}"
            )
        if cycle.count < 0:
            raise ValueError(
                f"Cycle {i} in spectrum '{spectrum.name}': "
                f"count must be >= 0, got {cycle.count}"
            )


def categorize_loading(spectrum: FatigueSpectrum) -> str:
    """
    Return the loading-type label for the spectrum:
      'constant_amplitude'  — all active blocks share a single stress level
      'variable_amplitude'  — multiple distinct non-zero amplitude levels
      'combined'            — variable amplitude plus at least one zero-amplitude
                              (rest) block

    An empty spectrum or one composed entirely of zero-amplitude blocks
    returns 'constant_amplitude' (degenerate constant-zero case).
    """
    active = [c for c in spectrum.cycles if c.count > 0]
    if not active:
        return "constant_amplitude"

    amplitudes = {c.stress_amplitude for c in active}
    has_zero = 0.0 in amplitudes
    non_zero_levels = amplitudes - {0.0}

    # All active blocks have zero amplitude → constant at zero
    if not non_zero_levels:
        return "constant_amplitude"
    # Single non-zero amplitude level, no rest blocks → pure constant amplitude
    if len(non_zero_levels) == 1 and not has_zero:
        return "constant_amplitude"
    # Non-zero loading plus at least one zero-amplitude rest block → combined
    if has_zero:
        return "combined"
    # Multiple distinct non-zero amplitude levels, no rest blocks → variable
    return "variable_amplitude"


# ---------------------------------------------------------------------------
# Simplified rainflow-compatible cycle extraction
# ---------------------------------------------------------------------------

def count_cycles_from_peaks(peaks: List[float]) -> List[LoadCycle]:
    """
    Extract half-cycles from a peak-valley sequence.

    Each adjacent (peak[i], peak[i+1]) pair yields one half-cycle:
        amplitude = |peak[i] - peak[i+1]| / 2
        mean      = (peak[i] + peak[i+1]) / 2
        count     = 0.5

    Returns an empty list for sequences shorter than two points.
    This is the range-pair step of a simplified rainflow procedure;
    full rainflow merging of matching half-cycles is not performed here
    because the per-block damage contribution is identical whether
    half-cycles are merged or not when the mean stress is not used.
    """
    if len(peaks) < 2:
        return []
    cycles = []
    for i in range(len(peaks) - 1):
        a, b = peaks[i], peaks[i + 1]
        amplitude = abs(a - b) / 2.0
        mean = (a + b) / 2.0
        cycles.append(LoadCycle(stress_amplitude=amplitude, mean_stress=mean, count=0.5))
    return cycles


# ---------------------------------------------------------------------------
# S-N curve
# ---------------------------------------------------------------------------

def validate_sn_curve(sn_data: List[SNPoint]) -> None:
    """Raise ValueError if the S-N dataset cannot support interpolation."""
    if len(sn_data) < 2:
        raise ValueError(
            f"S-N curve requires at least 2 data points, got {len(sn_data)}"
        )
    for i, pt in enumerate(sn_data):
        if pt.stress_amplitude <= 0:
            raise ValueError(
                f"S-N point {i}: stress_amplitude must be > 0, got {pt.stress_amplitude}"
            )
        if pt.allowable_cycles <= 0:
            raise ValueError(
                f"S-N point {i}: allowable_cycles must be > 0, got {pt.allowable_cycles}"
            )


def interpolate_sn_curve(stress_amplitude: float, sn_data: List[SNPoint]) -> float:
    """
    Return allowable cycles N for the given stress amplitude via log-log
    linear interpolation.  Extrapolates beyond the data range using the
    slope of the nearest endpoint pair.

    Raises ValueError for non-positive stress amplitude or invalid S-N data.
    """
    if stress_amplitude <= 0:
        raise ValueError(
            f"stress_amplitude must be > 0 for S-N lookup, got {stress_amplitude}"
        )
    validate_sn_curve(sn_data)

    # Sort descending by stress (ascending by life)
    pts = sorted(sn_data, key=lambda p: p.stress_amplitude, reverse=True)

    # Exact match check
    for pt in pts:
        if math.isclose(pt.stress_amplitude, stress_amplitude, rel_tol=1e-9):
            return pt.allowable_cycles

    # Build log-log representation: (log_s, log_n)
    log_pts = [
        (math.log10(p.stress_amplitude), math.log10(p.allowable_cycles))
        for p in pts
    ]
    log_s = math.log10(stress_amplitude)

    # Bracketed interpolation
    for i in range(len(log_pts) - 1):
        s_hi, n_lo = log_pts[i]
        s_lo, n_hi = log_pts[i + 1]
        if s_lo <= log_s <= s_hi:
            frac = (log_s - s_lo) / (s_hi - s_lo)
            log_n = n_hi + frac * (n_lo - n_hi)
            return 10.0 ** log_n

    # Extrapolation beyond upper bound (higher stress than any data point)
    if log_s > log_pts[0][0]:
        ds = log_pts[0][0] - log_pts[1][0]
        dn = log_pts[0][1] - log_pts[1][1]
        slope = dn / ds if ds != 0 else 0.0
        log_n = log_pts[0][1] + slope * (log_s - log_pts[0][0])
        return 10.0 ** log_n

    # Extrapolation beyond lower bound (lower stress than any data point)
    n = len(log_pts)
    ds = log_pts[n - 2][0] - log_pts[n - 1][0]
    dn = log_pts[n - 2][1] - log_pts[n - 1][1]
    slope = dn / ds if ds != 0 else 0.0
    log_n = log_pts[n - 1][1] + slope * (log_s - log_pts[n - 1][0])
    return 10.0 ** log_n


# ---------------------------------------------------------------------------
# Miner's rule damage summation
# ---------------------------------------------------------------------------

def compute_miner_damage(spectrum: FatigueSpectrum, sn_data: List[SNPoint]) -> float:
    """
    Compute total Miner's linear damage for the spectrum:
        D = sum(n_i / N_i)

    Cycles with zero amplitude or zero count contribute no damage.
    Returns 0.0 for an empty spectrum or a spectrum of zero-amplitude blocks.
    """
    validate_spectrum(spectrum)
    total_damage = 0.0
    for cycle in spectrum.cycles:
        if cycle.count <= 0 or cycle.stress_amplitude <= 0:
            continue
        n_allowable = interpolate_sn_curve(cycle.stress_amplitude, sn_data)
        total_damage += cycle.count / n_allowable
    return total_damage


# ---------------------------------------------------------------------------
# Life and margin computations
# ---------------------------------------------------------------------------

def apply_scatter_factor(predicted_life: float, scatter_factor: float) -> float:
    """
    Return scatter-factor-adjusted life: predicted_life / scatter_factor.

    ECSS-E-ST-32C requires this divisor (>= 4 for metallic structures) to
    account for material variability and load uncertainty before life is
    compared against the required design life.
    """
    if scatter_factor <= 0:
        raise ValueError(f"scatter_factor must be > 0, got {scatter_factor}")
    if predicted_life < 0:
        raise ValueError(f"predicted_life must be >= 0, got {predicted_life}")
    return predicted_life / scatter_factor


def compute_life_from_damage(total_damage: float, total_applied_cycles: float) -> float:
    """
    Invert Miner's rule to obtain predicted failure life:
        life = total_applied_cycles / total_damage

    Returns float('inf') when total_damage is zero (no fatigue loading).
    """
    if total_damage < 0:
        raise ValueError(f"total_damage must be >= 0, got {total_damage}")
    if total_applied_cycles < 0:
        raise ValueError(
            f"total_applied_cycles must be >= 0, got {total_applied_cycles}"
        )
    if total_damage == 0.0:
        return float("inf")
    return total_applied_cycles / total_damage


def compute_life_margin(adjusted_life: float, required_life: float) -> float:
    """
    Return the fatigue life margin:
        margin = (adjusted_life / required_life) - 1

    A non-negative margin indicates fatigue compliance at this location.
    Raises ValueError when required_life is not positive.
    """
    if required_life <= 0:
        raise ValueError(f"required_life must be > 0, got {required_life}")
    if adjusted_life < 0:
        raise ValueError(f"adjusted_life must be >= 0, got {adjusted_life}")
    return (adjusted_life / required_life) - 1.0


# ---------------------------------------------------------------------------
# Full per-location assessment
# ---------------------------------------------------------------------------

def assess_fatigue_location(
    location: str,
    spectrum: FatigueSpectrum,
    sn_data: List[SNPoint],
    required_life: float,
    scatter_factor: float,
) -> FatigueResult:
    """
    Run the complete fatigue assessment for one critical location and return
    a FatigueResult with all intermediate values and a compliance verdict.

    Steps:
      1. Validate inputs.
      2. Sum Miner's damage over the spectrum.
      3. Invert damage to predict failure life.
      4. Apply scatter factor.
      5. Compute life margin and compliance flag.
    """
    if required_life <= 0:
        raise ValueError(f"required_life must be > 0, got {required_life}")
    if scatter_factor <= 0:
        raise ValueError(f"scatter_factor must be > 0, got {scatter_factor}")

    validate_spectrum(spectrum)

    total_applied = sum(c.count for c in spectrum.cycles if c.count > 0)
    total_damage = compute_miner_damage(spectrum, sn_data)
    life_cycles = compute_life_from_damage(total_damage, total_applied)
    adjusted_life = apply_scatter_factor(life_cycles, scatter_factor)
    margin = compute_life_margin(adjusted_life, required_life)

    return FatigueResult(
        location=location,
        total_damage=total_damage,
        life_cycles=life_cycles,
        required_life=required_life,
        scatter_factor=scatter_factor,
        adjusted_life=adjusted_life,
        margin=margin,
        compliant=(margin >= 0.0),
    )
