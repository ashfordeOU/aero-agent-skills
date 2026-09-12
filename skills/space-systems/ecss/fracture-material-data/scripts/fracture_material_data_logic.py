"""
Fracture material data derivation utilities — ECSS-E-ST-32C §7.2.5.

Covers KIC specimen validity, Paris-law crack growth, threshold derivation,
data-source categorization, and limited-data knockdowns.
Stdlib only; deterministic; no external dependencies.

Unit convention (must be consistent across a single call):
  KIC, delta_Kth  — MPa·√m
  sigma_ys        — MPa
  B, a            — m  (same unit system as KIC/σys gives m)
  da/dN           — m/cycle  (C must be in matching units)
"""

import math

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

DATA_SOURCE_TYPES = frozenset(["test-derived", "handbook", "limited"])

REGION_THRESHOLD = "threshold"
REGION_PARIS = "paris"
REGION_NEAR_KIC = "near-kic"

MIN_PARIS_DATA_POINTS = 3

HANDBOOK_KNOCKDOWN = 0.90
LIMITED_DATA_KNOCKDOWN = 0.85
DEFAULT_WALKER_EXPONENT = 0.5


# ---------------------------------------------------------------------------
# 1. KIC specimen validity
# ---------------------------------------------------------------------------

def validate_kic_specimen(B: float, a: float, KIC: float, sigma_ys: float) -> dict:
    """
    Check whether a fracture-toughness test result satisfies the plane-strain
    validity criterion (ASTM E399 / ECSS-E-ST-32C §7.2.5):

        B  ≥  2.5 × (KIC / σys)²
        a  ≥  2.5 × (KIC / σys)²

    Parameters
    ----------
    B        : float  Specimen thickness (m)
    a        : float  Crack length / ligament (m)
    KIC      : float  Measured conditional toughness KQ (MPa·√m)
    sigma_ys : float  0.2% proof stress (MPa)

    Returns
    -------
    dict
        is_valid        bool   — True if both B and a meet the criterion
        criterion_value float  — minimum required B and a (m)
        margin_B        float  — B / criterion_value − 1  (negative → invalid)
        margin_a        float  — a / criterion_value − 1  (negative → invalid)
    """
    if B <= 0 or a <= 0:
        raise ValueError("B and a must be positive.")
    if KIC <= 0:
        raise ValueError("KIC must be positive.")
    if sigma_ys <= 0:
        raise ValueError("sigma_ys must be positive.")

    criterion_value = 2.5 * (KIC / sigma_ys) ** 2
    margin_B = B / criterion_value - 1.0
    margin_a = a / criterion_value - 1.0

    return {
        "is_valid": (margin_B >= 0.0) and (margin_a >= 0.0),
        "criterion_value": criterion_value,
        "margin_B": margin_B,
        "margin_a": margin_a,
    }


# ---------------------------------------------------------------------------
# 2. Paris-law crack growth rate
# ---------------------------------------------------------------------------

def paris_crack_growth_rate(delta_K: float, C: float, n: float,
                             delta_Kth: float = 0.0) -> float:
    """
    Compute da/dN from the Paris law.

        da/dN = C × ΔK^n   for  ΔK > ΔKth
        da/dN = 0           for  ΔK ≤ ΔKth  (threshold — no growth)

    Parameters
    ----------
    delta_K   : float  Stress-intensity-factor range (MPa·√m)
    C         : float  Paris coefficient (m/cycle / (MPa·√m)^n)
    n         : float  Paris exponent
    delta_Kth : float  Threshold ΔKth (MPa·√m); default 0

    Returns
    -------
    float  da/dN (m/cycle)
    """
    if delta_K < 0:
        raise ValueError("delta_K must be non-negative.")
    if C <= 0:
        raise ValueError("C must be positive.")
    if n <= 0:
        raise ValueError("n must be positive.")
    if delta_Kth < 0:
        raise ValueError("delta_Kth must be non-negative.")

    if delta_K <= delta_Kth:
        return 0.0
    return C * (delta_K ** n)


# ---------------------------------------------------------------------------
# 3. Threshold adjustment for load ratio R
# ---------------------------------------------------------------------------

def threshold_for_r_ratio(delta_Kth_R0: float, R: float,
                           walker_exponent: float = DEFAULT_WALKER_EXPONENT) -> float:
    """
    Adjust the threshold ΔKth from R = 0 to an arbitrary load ratio using
    Walker-type scaling:

        ΔKth(R) = ΔKth(R=0) × (1 − R_eff)^γ

    R_eff = max(R, 0): compressive cycles (R < 0) do not open the crack, so
    the threshold is not reduced below the R = 0 value.

    Parameters
    ----------
    delta_Kth_R0   : float  Threshold at R = 0 (MPa·√m)
    R              : float  Load ratio Kmin/Kmax; must be < 1
    walker_exponent: float  γ exponent (default 0.5)

    Returns
    -------
    float  Adjusted ΔKth (MPa·√m)
    """
    if delta_Kth_R0 <= 0:
        raise ValueError("delta_Kth_R0 must be positive.")
    if R >= 1.0:
        raise ValueError("R must be less than 1.0.")

    R_eff = max(R, 0.0)
    return delta_Kth_R0 * ((1.0 - R_eff) ** walker_exponent)


# ---------------------------------------------------------------------------
# 4. Data source categorization
# ---------------------------------------------------------------------------

def categorize_data_source(source_type: str) -> str:
    """
    Confirm that a material data source belongs to a recognised category.

    Accepted categories:
        'test-derived' — full coupon campaign for the flight material lot
        'handbook'     — qualified reference source (e.g. MMPDS)
        'limited'      — too few data points for a statistically sound fit

    Input is normalised (stripped, lower-cased) before matching.

    Returns the normalised source type string; raises ValueError if unknown.
    """
    normalised = source_type.strip().lower()
    if normalised not in DATA_SOURCE_TYPES:
        raise ValueError(
            f"Unrecognised data source '{source_type}'. "
            f"Allowed: {sorted(DATA_SOURCE_TYPES)}"
        )
    return normalised


# ---------------------------------------------------------------------------
# 5. Crack growth region
# ---------------------------------------------------------------------------

def crack_growth_region(delta_K: float, delta_Kth: float, KIC: float,
                         R: float = 0.0,
                         near_kic_fraction: float = 0.8) -> str:
    """
    Determine the crack growth region for an applied ΔK.

    Regions:
        REGION_THRESHOLD — ΔK ≤ ΔKth                     (negligible growth)
        REGION_PARIS     — ΔKth < ΔK, Kmax < f·KIC       (stable Paris growth)
        REGION_NEAR_KIC  — Kmax ≥ f·KIC                   (rapid growth)

    where Kmax = ΔK / (1 − R) and f = near_kic_fraction.

    Parameters
    ----------
    delta_K          : float  Applied ΔK (MPa·√m)
    delta_Kth        : float  Threshold ΔKth (MPa·√m)
    KIC              : float  Plane-strain fracture toughness (MPa·√m)
    R                : float  Load ratio (default 0)
    near_kic_fraction: float  Fraction of KIC that triggers near-KIC regime

    Returns
    -------
    str  One of REGION_THRESHOLD, REGION_PARIS, REGION_NEAR_KIC
    """
    if delta_K < 0:
        raise ValueError("delta_K must be non-negative.")
    if delta_Kth < 0:
        raise ValueError("delta_Kth must be non-negative.")
    if KIC <= 0:
        raise ValueError("KIC must be positive.")
    if R >= 1.0:
        raise ValueError("R must be less than 1.0.")

    if delta_K <= delta_Kth:
        return REGION_THRESHOLD

    Kmax = delta_K / (1.0 - R)
    if Kmax >= near_kic_fraction * KIC:
        return REGION_NEAR_KIC
    return REGION_PARIS


# ---------------------------------------------------------------------------
# 6. Paris-law parameter derivation (linear regression in log–log space)
# ---------------------------------------------------------------------------

def derive_paris_parameters(delta_K_data: list, da_dn_data: list) -> dict:
    """
    Fit Paris-law parameters (C, n) from (ΔK, da/dN) coupon data via linear
    least-squares regression in log–log space:

        log10(da/dN) = log10(C) + n · log10(ΔK)

    Requires at least MIN_PARIS_DATA_POINTS (3) data pairs. All values must
    be strictly positive.

    Parameters
    ----------
    delta_K_data : list of float  ΔK values (MPa·√m), > 0
    da_dn_data   : list of float  da/dN values (m/cycle), > 0

    Returns
    -------
    dict
        C         float  — Paris coefficient
        n         float  — Paris exponent
        r_squared float  — coefficient of determination of the log–log fit
        n_points  int    — number of data points used
    """
    if len(delta_K_data) != len(da_dn_data):
        raise ValueError("delta_K_data and da_dn_data must have equal length.")
    if len(delta_K_data) < MIN_PARIS_DATA_POINTS:
        raise ValueError(
            f"At least {MIN_PARIS_DATA_POINTS} data points required; "
            f"got {len(delta_K_data)}."
        )
    for v in delta_K_data:
        if v <= 0:
            raise ValueError("All delta_K values must be strictly positive.")
    for v in da_dn_data:
        if v <= 0:
            raise ValueError("All da_dn values must be strictly positive.")

    n_pts = len(delta_K_data)
    x = [math.log10(v) for v in delta_K_data]
    y = [math.log10(v) for v in da_dn_data]

    sum_x = sum(x)
    sum_y = sum(y)
    sum_xx = sum(xi * xi for xi in x)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))

    denom = n_pts * sum_xx - sum_x ** 2
    if abs(denom) < 1e-15:
        raise ValueError("All ΔK values are identical; cannot fit a slope.")

    slope = (n_pts * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n_pts

    C_fit = 10.0 ** intercept
    n_fit = slope

    y_mean = sum_y / n_pts
    ss_tot = sum((yi - y_mean) ** 2 for yi in y)
    y_pred = [intercept + slope * xi for xi in x]
    ss_res = sum((yi - yp) ** 2 for yi, yp in zip(y, y_pred))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

    return {
        "C": C_fit,
        "n": n_fit,
        "r_squared": r_squared,
        "n_points": n_pts,
    }


# ---------------------------------------------------------------------------
# 7. Knockdown application
# ---------------------------------------------------------------------------

def apply_knockdown(value: float, source_type: str) -> float:
    """
    Apply a conservative knockdown factor to KIC or ΔKth based on data source.

    Knockdown factors (ECSS-E-ST-32C §7.2.5 limited-data guidance):
        test-derived → 1.00  (no knockdown)
        handbook     → 0.90
        limited      → 0.85

    Parameters
    ----------
    value       : float  KIC or ΔKth value (MPa·√m)
    source_type : str    One of the recognised source category strings

    Returns
    -------
    float  Conservatively adjusted value (MPa·√m)
    """
    normalised = categorize_data_source(source_type)
    knockdown_map = {
        "test-derived": 1.0,
        "handbook": HANDBOOK_KNOCKDOWN,
        "limited": LIMITED_DATA_KNOCKDOWN,
    }
    return value * knockdown_map[normalised]


# ---------------------------------------------------------------------------
# 8. Consolidated material record
# ---------------------------------------------------------------------------

def summarise_material_record(name: str, KIC: float, delta_Kth: float,
                               paris_C: float, paris_n: float,
                               source_type: str,
                               R_ratio: float = 0.0) -> dict:
    """
    Build a consolidated, fully adjusted material data record.

    Steps applied:
        1. Validate inputs and categorize data source.
        2. Apply R-ratio Walker adjustment to ΔKth.
        3. Apply source knockdown to both KIC and the adjusted ΔKth.
        4. Collect any advisory warnings into a list.

    Parameters
    ----------
    name        : str    Material identifier
    KIC         : float  Measured KIC (MPa·√m)
    delta_Kth   : float  Threshold at R = 0 (MPa·√m)
    paris_C     : float  Paris coefficient
    paris_n     : float  Paris exponent
    source_type : str    Data source category
    R_ratio     : float  Design load ratio (default 0)

    Returns
    -------
    dict
        name              str    — material identifier
        KIC_adjusted      float  — KIC after knockdown
        delta_Kth_adjusted float — ΔKth after R adjustment and knockdown
        paris_C           float  — Paris C (unchanged; fit from data)
        paris_n           float  — Paris n (unchanged)
        source_type       str    — normalised source category
        warnings          list   — advisory strings; empty = no issues
    """
    if not name:
        raise ValueError("Material name must not be empty.")
    if KIC <= 0 or delta_Kth <= 0 or paris_C <= 0 or paris_n <= 0:
        raise ValueError(
            "KIC, delta_Kth, paris_C, and paris_n must all be positive."
        )

    normalised_source = categorize_data_source(source_type)
    warnings = []

    KIC_adjusted = apply_knockdown(KIC, normalised_source)
    delta_Kth_R = threshold_for_r_ratio(delta_Kth, R_ratio)
    delta_Kth_adjusted = apply_knockdown(delta_Kth_R, normalised_source)

    if normalised_source == "limited":
        warnings.append(
            "Limited data: knockdown applied; seek additional test data."
        )
    if normalised_source == "handbook":
        warnings.append(
            "Handbook data: verify applicability to the flight material lot."
        )
    if R_ratio > 0.5:
        warnings.append(
            f"High R ratio ({R_ratio:.2f}): threshold significantly reduced."
        )

    return {
        "name": name,
        "KIC_adjusted": KIC_adjusted,
        "delta_Kth_adjusted": delta_Kth_adjusted,
        "paris_C": paris_C,
        "paris_n": paris_n,
        "source_type": normalised_source,
        "warnings": warnings,
    }
