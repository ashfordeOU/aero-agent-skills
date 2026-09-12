"""
Composite material characterization logic per ECSS-E-ST-32C clause 5.6
and CMH-17 (Composite Materials Handbook).

Implements coupon test validation, specimen count checking, A/B-basis
allowable computation (k-factor tolerance-limit method), knockdown
factor application, margin of safety calculation, material
categorization, test matrix completeness checking, and translation
efficiency verification.

All logic is deterministic and offline (stdlib only).
"""

import math
import statistics

# ---------------------------------------------------------------------------
# Reference tables
# ---------------------------------------------------------------------------

VALID_COUPON_TESTS = {
    "fiber_tensile_longitudinal",
    "fiber_tensile_transverse",
    "fiber_compression_longitudinal",
    "fiber_compression_transverse",
    "in_plane_shear",
    "interlaminar_shear_strength",
    "open_hole_tensile",
    "open_hole_compression",
    "filled_hole_tensile",
    "filled_hole_compression",
    "bearing_strength",
    "short_beam_shear",
}

# Minimum required test types for a complete overwrap characterization
REQUIRED_TESTS_OVERWRAP = {
    "fiber_tensile_longitudinal",
    "fiber_tensile_transverse",
    "fiber_compression_longitudinal",
    "fiber_compression_transverse",
    "in_plane_shear",
    "interlaminar_shear_strength",
}

# CMH-17 minimum specimen counts per basis level
MIN_SPECIMENS = {
    "A": 25,
    "B": 18,
    "S": 5,
}

# One-sided tolerance-limit k-factors (normal distribution, 95 % confidence)
# (k_B for B-basis 90th-percentile lower bound,
#  k_A for A-basis 99th-percentile lower bound)
# None indicates the value is not tabulated (insufficient n for that basis).
_K_TABLE = {
    18:  (2.208, None),
    20:  (2.125, None),
    25:  (1.986, 3.158),
    30:  (1.895, 2.950),
    40:  (1.798, 2.710),
    50:  (1.754, 2.580),
    100: (1.661, 2.328),
    200: (1.601, 2.187),
    300: (1.577, 2.138),
}

FIBER_CATEGORIES = {
    "carbon":  "high_modulus_fiber",
    "glass":   "glass_fiber",
    "aramid":  "aramid_fiber",
    "basalt":  "glass_fiber",
}

MATRIX_CATEGORIES = {
    "epoxy":         "thermoset",
    "bmi":           "thermoset",
    "cyanate_ester": "thermoset",
    "peek":          "thermoplastic",
    "pekk":          "thermoplastic",
    "polyamide":     "thermoplastic",
}

# Translation efficiency threshold below which a processing finding is raised
_MIN_TRANSLATION_EFFICIENCY = 0.85


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize_test_type(raw: str) -> str:
    return raw.lower().strip().replace("-", "_").replace(" ", "_")


def _lookup_k_factor(n: int, basis: str) -> float:
    """
    Return the k-factor for the given sample size and basis level.
    Interpolates linearly between tabulated values.
    Raises ValueError when n is below the minimum or the value is not
    tabulated for the requested basis.
    """
    sorted_ns = sorted(_K_TABLE.keys())
    col = 0 if basis == "B" else 1

    if n < sorted_ns[0]:
        raise ValueError(
            f"n={n} is below the minimum tabulated value ({sorted_ns[0]}) "
            f"for {basis}-basis k-factor lookup."
        )

    if n >= sorted_ns[-1]:
        val = _K_TABLE[sorted_ns[-1]][col]
        if val is None:
            raise ValueError(
                f"A-basis k-factor is not tabulated for n={n}; minimum n for A-basis is 25."
            )
        return val

    for i in range(len(sorted_ns) - 1):
        n_lo, n_hi = sorted_ns[i], sorted_ns[i + 1]
        if n_lo <= n <= n_hi:
            k_lo = _K_TABLE[n_lo][col]
            k_hi = _K_TABLE[n_hi][col]
            if k_lo is None or k_hi is None:
                raise ValueError(
                    f"A-basis k-factor is not tabulated for n={n}; minimum n for A-basis is 25."
                )
            t = (n - n_lo) / (n_hi - n_lo)
            return k_lo + t * (k_hi - k_lo)

    raise ValueError(f"k-factor lookup failed unexpectedly for n={n}, basis={basis}.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_coupon_test_type(test_type: str) -> dict:
    """
    Confirm that a coupon test type string is a recognized characterization
    test for composite material allowables work.

    Returns a dict with:
      valid (bool)        — True if the test type is in the recognized set
      test_type (str)     — normalized form of the input
      recognized (bool)   — same as valid (kept for symmetry with other checks)
    """
    if not isinstance(test_type, str) or not test_type.strip():
        raise ValueError("test_type must be a non-empty string.")
    normalized = _normalize_test_type(test_type)
    valid = normalized in VALID_COUPON_TESTS
    return {"valid": valid, "test_type": normalized, "recognized": valid}


def check_specimen_count(basis: str, count: int) -> dict:
    """
    Verify that the specimen count meets the CMH-17 minimum for the
    requested statistical basis level.

    basis:  "A", "B", or "S"
    count:  number of specimens tested (non-negative integer)

    Returns a dict with:
      sufficient (bool)       — True when count >= minimum
      basis (str)             — echoed input
      specimen_count (int)    — echoed input
      minimum_required (int)  — CMH-17 minimum for this basis
      shortfall (int)         — specimens still needed (0 when sufficient)
    """
    if basis not in MIN_SPECIMENS:
        raise ValueError(
            f"basis must be one of {list(MIN_SPECIMENS.keys())}, got '{basis}'."
        )
    if not isinstance(count, int) or count < 0:
        raise ValueError("count must be a non-negative integer.")

    minimum = MIN_SPECIMENS[basis]
    sufficient = count >= minimum
    return {
        "sufficient": sufficient,
        "basis": basis,
        "specimen_count": count,
        "minimum_required": minimum,
        "shortfall": max(0, minimum - count),
    }


def compute_basis_value(specimens: list, basis: str) -> dict:
    """
    Compute a statistical allowable (A-basis or B-basis) from coupon
    strength data using the CMH-17 k-factor tolerance-limit method.

    specimens:  list of float strength values (any consistent unit)
    basis:      "A" or "B"

    Raises ValueError when the specimen count is below the CMH-17 minimum
    for the requested basis, when the basis is not "A" or "B", or when
    the specimen list is empty.

    Returns a dict with:
      basis (str)          — echoed input
      basis_value (float)  — statistical allowable = mean - k * std_dev
      mean (float)         — sample mean
      std_dev (float)      — sample standard deviation
      k_factor (float)     — k-factor used
      n (int)              — specimen count
    """
    if basis not in ("A", "B"):
        raise ValueError(
            f"basis must be 'A' or 'B' for statistical computation; got '{basis}'."
        )
    if not isinstance(specimens, (list, tuple)) or len(specimens) == 0:
        raise ValueError("specimens must be a non-empty sequence of numeric values.")

    n = len(specimens)
    count_check = check_specimen_count(basis, n)
    if not count_check["sufficient"]:
        raise ValueError(
            f"Insufficient specimens for {basis}-basis: have {n}, "
            f"need {count_check['minimum_required']}."
        )

    values = [float(v) for v in specimens]
    mean = statistics.mean(values)
    std_dev = statistics.stdev(values)
    k = _lookup_k_factor(n, basis)
    basis_value = mean - k * std_dev

    return {
        "basis": basis,
        "basis_value": round(basis_value, 4),
        "mean": round(mean, 4),
        "std_dev": round(std_dev, 4),
        "k_factor": round(k, 4),
        "n": n,
    }


def apply_knockdown_factor(allowable: float, knockdown: float) -> dict:
    """
    Multiply a statistical allowable by a knockdown factor to produce a
    design allowable.  Knockdown factors account for environmental
    conditioning (wet-hot), manufacturing variability, and damage state.

    allowable:  positive statistical allowable (e.g., B-basis value)
    knockdown:  multiplicative factor in (0, 1]

    Returns a dict with:
      statistical_allowable (float)  — echoed input
      knockdown_factor (float)       — echoed input
      design_allowable (float)       — product of allowable * knockdown
    """
    if not isinstance(allowable, (int, float)) or allowable <= 0:
        raise ValueError("allowable must be a positive number.")
    if not isinstance(knockdown, (int, float)) or not (0 < knockdown <= 1.0):
        raise ValueError("knockdown must be in the range (0, 1].")

    return {
        "statistical_allowable": round(float(allowable), 4),
        "knockdown_factor": knockdown,
        "design_allowable": round(float(allowable) * knockdown, 4),
    }


def compute_margin_of_safety(design_allowable: float, applied_stress: float) -> dict:
    """
    Compute the structural margin of safety:
        MoS = (design_allowable / applied_stress) - 1

    A non-negative MoS means the element is within design limits.

    Returns a dict with:
      design_allowable (float)  — echoed input
      applied_stress (float)    — echoed input
      margin_of_safety (float)  — MoS value (negative = overstressed)
      passes (bool)             — True when MoS >= 0
    """
    if not isinstance(design_allowable, (int, float)) or design_allowable <= 0:
        raise ValueError("design_allowable must be a positive number.")
    if not isinstance(applied_stress, (int, float)) or applied_stress <= 0:
        raise ValueError("applied_stress must be a positive number.")

    mos = (design_allowable / applied_stress) - 1.0
    return {
        "design_allowable": design_allowable,
        "applied_stress": applied_stress,
        "margin_of_safety": round(mos, 4),
        "passes": mos >= 0.0,
    }


def categorize_material(fiber_type: str, matrix_type: str) -> dict:
    """
    Categorize a composite material into recognized fiber and matrix
    families.  Returns the composite system identifier when both families
    are recognized, or marks the result as unrecognized when either input
    is unknown — without raising an error so the caller can decide how to
    handle novel systems.

    Returns a dict with:
      fiber_type (str)       — normalized input
      matrix_type (str)      — normalized input
      fiber_category (str|None)   — recognized fiber family, or None
      matrix_category (str|None)  — recognized matrix family, or None
      recognized (bool)      — True when both families are known
      composite_system (str|None) — "fiber_category/matrix_category" or None
    """
    if not isinstance(fiber_type, str) or not fiber_type.strip():
        raise ValueError("fiber_type must be a non-empty string.")
    if not isinstance(matrix_type, str) or not matrix_type.strip():
        raise ValueError("matrix_type must be a non-empty string.")

    f_key = fiber_type.lower().strip()
    m_key = matrix_type.lower().strip()
    fiber_cat = FIBER_CATEGORIES.get(f_key)
    matrix_cat = MATRIX_CATEGORIES.get(m_key)
    recognized = fiber_cat is not None and matrix_cat is not None

    return {
        "fiber_type": f_key,
        "matrix_type": m_key,
        "fiber_category": fiber_cat,
        "matrix_category": matrix_cat,
        "recognized": recognized,
        "composite_system": f"{fiber_cat}/{matrix_cat}" if recognized else None,
    }


def check_allowables_completeness(tested_types: list) -> dict:
    """
    Verify that a set of tested coupon types covers every property in the
    minimum required test matrix for composite overwrap characterization.

    tested_types:  list of test-type strings (normalized internally)

    Returns a dict with:
      complete (bool)        — True when all required types are covered
      tested_count (int)     — number of distinct normalized types provided
      required_count (int)   — number of types in the required set
      missing (list[str])    — required types absent from tested_types
      extra (list[str])      — tested types beyond the required set
    """
    if not isinstance(tested_types, (list, tuple)):
        raise ValueError("tested_types must be a list of test-type strings.")

    tested_set = {_normalize_test_type(t) for t in tested_types}
    missing = REQUIRED_TESTS_OVERWRAP - tested_set
    extra = tested_set - REQUIRED_TESTS_OVERWRAP

    return {
        "complete": len(missing) == 0,
        "tested_count": len(tested_set),
        "required_count": len(REQUIRED_TESTS_OVERWRAP),
        "missing": sorted(missing),
        "extra": sorted(extra),
    }


def compute_translation_efficiency(dry_fiber_strength: float, laminate_strength: float) -> dict:
    """
    Compute the fiber-strength translation efficiency of a wound or
    prepreg laminate — the ratio of measured laminate strength to the
    dry-fiber reference value.

    Values below 0.85 indicate that the manufacturing process is not
    converting fiber strength to laminate strength at an acceptable rate,
    and the root cause must be investigated before allowables are released.

    Returns a dict with:
      dry_fiber_strength (float)      — echoed input
      laminate_strength (float)       — echoed input
      translation_efficiency (float)  — ratio (laminate / dry-fiber)
      acceptable (bool)               — True when efficiency >= 0.85
    """
    if not isinstance(dry_fiber_strength, (int, float)) or dry_fiber_strength <= 0:
        raise ValueError("dry_fiber_strength must be a positive number.")
    if not isinstance(laminate_strength, (int, float)) or laminate_strength <= 0:
        raise ValueError("laminate_strength must be a positive number.")

    efficiency = laminate_strength / dry_fiber_strength
    return {
        "dry_fiber_strength": dry_fiber_strength,
        "laminate_strength": laminate_strength,
        "translation_efficiency": round(efficiency, 4),
        "acceptable": efficiency >= _MIN_TRANSLATION_EFFICIENCY,
    }
