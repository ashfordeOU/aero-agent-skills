"""
Fatigue and fracture test logic per ECSS-E-ST-32C clause 4.6.3.11.

Deterministic, offline procedures for:
- Load spectrum validation
- Miner's-rule cumulative damage calculation
- Test life derivation (design life multiplied by scatter factor)
- Crack-detection capability lookup by inspection method
- Test specimen outcome assessment
- Residual-strength check after sustained fatigue damage
"""

import math

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MINER_DAMAGE_LIMIT = 1.0

DEFAULT_SCATTER_FACTOR_METAL = 4.0
DEFAULT_SCATTER_FACTOR_COMPOSITE = 6.0

# Minimum detectable crack length [mm] by inspection method.
# Values are indicative engineering thresholds for planning purposes.
DETECTION_THRESHOLD_MM = {
    "eddy_current":      0.1,
    "dye_penetrant":     0.2,
    "magnetic_particle": 0.3,
    "ultrasonic":        0.5,
    "radiographic":      0.5,
    "visual":            3.0,
}

# Fraction of initial strength lost per unit of Miner damage (linear model).
_RESIDUAL_STRENGTH_KNOCKDOWN = 0.1


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SpectrumError(ValueError):
    """Raised when a load spectrum fails validation or is missing S-N data."""


class TestPlanError(ValueError):
    """Raised when test plan parameters are outside acceptable bounds."""


# ---------------------------------------------------------------------------
# Spectrum validation
# ---------------------------------------------------------------------------

def validate_spectrum(blocks):
    """
    Validate a fatigue load spectrum.

    Parameters
    ----------
    blocks : list[dict]
        Each dict must contain:
          'stress_mpa' (float > 0) — peak stress amplitude in MPa
          'cycles'     (int > 0)   — number of cycles at this stress level

    Returns
    -------
    dict with keys:
        'valid'           : bool
        'block_count'     : int
        'total_cycles'    : int
        'peak_stress_mpa' : float
        'issues'          : list[str] — empty when valid

    Raises
    ------
    SpectrumError
        If blocks is empty, a required key is missing, or any value is
        non-positive.
    """
    if not blocks:
        raise SpectrumError("Spectrum must contain at least one load block.")

    issues = []
    total_cycles = 0
    peak_stress = 0.0

    for i, block in enumerate(blocks):
        if "stress_mpa" not in block or "cycles" not in block:
            raise SpectrumError(
                f"Block {i} is missing 'stress_mpa' or 'cycles'."
            )
        s = block["stress_mpa"]
        n = block["cycles"]
        if s <= 0:
            raise SpectrumError(
                f"Block {i}: 'stress_mpa' must be > 0, got {s}."
            )
        if n <= 0:
            raise SpectrumError(
                f"Block {i}: 'cycles' must be > 0, got {n}."
            )
        total_cycles += n
        if s > peak_stress:
            peak_stress = s

    if len(blocks) < 2:
        issues.append(
            "Single-block spectrum — a multi-block spectrum is recommended "
            "to represent realistic mission loading variation."
        )

    return {
        "valid": len(issues) == 0,
        "block_count": len(blocks),
        "total_cycles": total_cycles,
        "peak_stress_mpa": peak_stress,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Miner's rule damage
# ---------------------------------------------------------------------------

def compute_miner_damage(blocks, sn_pairs):
    """
    Compute cumulative Miner's rule damage D = sum(n_i / N_i).

    Parameters
    ----------
    blocks : list[dict]
        Each dict has 'stress_mpa' (float) and 'cycles' (int).
    sn_pairs : list[dict]
        Each dict has 'stress_mpa' (float) and 'n_failure' (int),
        defining discrete S-N curve points.  Every stress level in
        blocks must appear in sn_pairs.

    Returns
    -------
    dict with keys:
        'damage'           : float — Miner's sum D
        'failed'           : bool  — True when D >= MINER_DAMAGE_LIMIT
        'per_block_damage' : list[float]

    Raises
    ------
    TestPlanError  if any n_failure entry is <= 0.
    SpectrumError  if a block stress level has no matching S-N entry.
    """
    sn_map = {}
    for entry in sn_pairs:
        s = entry["stress_mpa"]
        nf = entry["n_failure"]
        if nf <= 0:
            raise TestPlanError(
                f"S-N entry at {s} MPa has n_failure={nf} (must be > 0)."
            )
        sn_map[s] = nf

    total_damage = 0.0
    per_block = []

    for block in blocks:
        s = block["stress_mpa"]
        n = block["cycles"]
        if s not in sn_map:
            raise SpectrumError(
                f"No S-N data for stress level {s} MPa — extend the S-N "
                f"curve to cover this level before computing damage."
            )
        d = n / sn_map[s]
        per_block.append(d)
        total_damage += d

    return {
        "damage": total_damage,
        "failed": total_damage >= MINER_DAMAGE_LIMIT,
        "per_block_damage": per_block,
    }


# ---------------------------------------------------------------------------
# Test life derivation
# ---------------------------------------------------------------------------

def derive_test_life(required_mission_cycles, scatter_factor):
    """
    Derive the test life by applying the scatter factor to the design life.

    test_cycles = ceil(required_mission_cycles * scatter_factor)

    Parameters
    ----------
    required_mission_cycles : int   — design fatigue life in cycles
    scatter_factor          : float — multiplier >= 1.0

    Returns
    -------
    dict with keys:
        'test_cycles'    : int
        'scatter_factor' : float

    Raises
    ------
    TestPlanError if required_mission_cycles <= 0 or scatter_factor < 1.0.
    """
    if required_mission_cycles <= 0:
        raise TestPlanError(
            f"required_mission_cycles must be > 0, got {required_mission_cycles}."
        )
    if scatter_factor < 1.0:
        raise TestPlanError(
            f"scatter_factor must be >= 1.0, got {scatter_factor}."
        )

    test_cycles = math.ceil(required_mission_cycles * scatter_factor)
    return {
        "test_cycles": test_cycles,
        "scatter_factor": scatter_factor,
    }


# ---------------------------------------------------------------------------
# Crack detection capability
# ---------------------------------------------------------------------------

def check_crack_detection(method, crack_size_mm):
    """
    Determine whether an inspection method can detect a crack of a given size.

    Parameters
    ----------
    method        : str   — key from DETECTION_THRESHOLD_MM
    crack_size_mm : float — size of crack to detect in mm (must be > 0)

    Returns
    -------
    dict with keys:
        'detectable'    : bool
        'method'        : str
        'threshold_mm'  : float
        'crack_size_mm' : float

    Raises
    ------
    TestPlanError if the method is not recognised or crack_size_mm <= 0.
    """
    if method not in DETECTION_THRESHOLD_MM:
        raise TestPlanError(
            f"Unknown inspection method '{method}'. "
            f"Recognised methods: {sorted(DETECTION_THRESHOLD_MM)}."
        )
    if crack_size_mm <= 0:
        raise TestPlanError(
            f"crack_size_mm must be > 0, got {crack_size_mm}."
        )

    threshold = DETECTION_THRESHOLD_MM[method]
    return {
        "detectable": crack_size_mm >= threshold,
        "method": method,
        "threshold_mm": threshold,
        "crack_size_mm": crack_size_mm,
    }


# ---------------------------------------------------------------------------
# Specimen outcome assessment
# ---------------------------------------------------------------------------

def evaluate_specimen_outcome(
    cycles_completed,
    cycles_required,
    crack_detected,
    damage_tolerance_mode,
):
    """
    Assess whether a fatigue test specimen passes the test.

    Standard mode (damage_tolerance_mode=False):
        Pass requires cycles_completed >= cycles_required AND no crack
        detected before cycles_required.  A crack appearing at or after
        cycles_required is acceptable.

    Damage-tolerance mode (damage_tolerance_mode=True):
        The structure is permitted to develop a crack, but it must still
        survive to cycles_required.  Pass requires
        cycles_completed >= cycles_required regardless of crack timing.

    Parameters
    ----------
    cycles_completed      : int  — cycles actually completed before end or crack
    cycles_required       : int  — minimum test life per test plan (must be > 0)
    crack_detected        : bool — crack found at any point during the test
    damage_tolerance_mode : bool — True enables the damage-tolerance pass criterion

    Returns
    -------
    dict with keys:
        'passed'  : bool
        'margin'  : int  — cycles_completed - cycles_required
        'finding' : str

    Raises
    ------
    TestPlanError if cycles_completed < 0 or cycles_required <= 0.
    """
    if cycles_completed < 0:
        raise TestPlanError(
            f"cycles_completed cannot be negative, got {cycles_completed}."
        )
    if cycles_required <= 0:
        raise TestPlanError(
            f"cycles_required must be > 0, got {cycles_required}."
        )

    margin = cycles_completed - cycles_required
    survived = cycles_completed >= cycles_required

    if damage_tolerance_mode:
        passed = survived
        if passed:
            finding = (
                "Damage-tolerance mode: specimen survived to required life"
                + (" with crack detected." if crack_detected else " with no crack detected.")
            )
        else:
            finding = (
                f"Damage-tolerance mode: specimen reached only {cycles_completed} "
                f"of {cycles_required} required cycles"
                + (" (crack detected)." if crack_detected else " (no crack).")
            )
    else:
        if not crack_detected:
            passed = survived
            finding = (
                "No crack detected; specimen survived the required test life."
                if passed
                else (
                    f"No crack detected but only {cycles_completed} of "
                    f"{cycles_required} required cycles completed."
                )
            )
        elif not survived:
            passed = False
            finding = (
                f"Crack detected at {cycles_completed} cycles, before required "
                f"life of {cycles_required} cycles."
            )
        else:
            passed = True
            finding = (
                f"Crack detected at or after required life ({cycles_required} cycles); "
                "specimen passed."
            )

    return {
        "passed": passed,
        "margin": margin,
        "finding": finding,
    }


# ---------------------------------------------------------------------------
# Residual strength after fatigue
# ---------------------------------------------------------------------------

def check_residual_strength(initial_strength_mpa, limit_load_mpa, miner_damage):
    """
    Verify residual load-carrying capacity after accumulated fatigue damage.

    Model: residual_strength = initial_strength * (1 - k * D)
    where k = _RESIDUAL_STRENGTH_KNOCKDOWN and D is the Miner damage index.

    Pass criterion: residual_strength > limit_load_mpa.

    Parameters
    ----------
    initial_strength_mpa : float — undamaged ultimate strength [MPa] (must be > 0)
    limit_load_mpa       : float — design limit load [MPa] (must be > 0)
    miner_damage         : float — Miner's cumulative damage D (0 <= D < 1.0)

    Returns
    -------
    dict with keys:
        'residual_strength_mpa' : float
        'passes'                : bool
        'margin_mpa'            : float

    Raises
    ------
    TestPlanError if any input is out of the valid range.
    """
    if initial_strength_mpa <= 0:
        raise TestPlanError(
            f"initial_strength_mpa must be > 0, got {initial_strength_mpa}."
        )
    if limit_load_mpa <= 0:
        raise TestPlanError(
            f"limit_load_mpa must be > 0, got {limit_load_mpa}."
        )
    if miner_damage < 0:
        raise TestPlanError(
            f"miner_damage cannot be negative, got {miner_damage}."
        )
    if miner_damage >= MINER_DAMAGE_LIMIT:
        raise TestPlanError(
            f"miner_damage={miner_damage} >= {MINER_DAMAGE_LIMIT}: "
            "structure has already failed by Miner's criterion before the "
            "residual-strength check can be applied."
        )

    residual = initial_strength_mpa * (1.0 - _RESIDUAL_STRENGTH_KNOCKDOWN * miner_damage)
    margin = residual - limit_load_mpa

    return {
        "residual_strength_mpa": residual,
        "passes": residual > limit_load_mpa,
        "margin_mpa": margin,
    }
