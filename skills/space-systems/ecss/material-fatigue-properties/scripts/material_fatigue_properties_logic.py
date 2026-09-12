"""
Material fatigue properties logic for space structures.
Implements deterministic, offline checks for ECSS-E-ST-32C clause 4.2.3.
stdlib only — no external dependencies.
"""

import math

MIN_TEST_POINTS = 6        # recommended minimum coupon count for a qualified dataset
MIN_R_RATIO_VARIANTS = 2   # minimum distinct stress ratios for full coverage
FATIGUE_RATIO_LOW = 0.35   # lower plausibility bound for f = endurance_limit / sigma_ult
FATIGUE_RATIO_HIGH = 0.55  # upper plausibility bound


class FatigueDataError(ValueError):
    """Raised when fatigue data is missing, inconsistent, or physically invalid."""


def compute_stress_parameters(sigma_max, sigma_min):
    """
    Return (sigma_a, sigma_m, R) for a load cycle defined by peak stresses.

    sigma_a  — stress amplitude = (sigma_max - sigma_min) / 2
    sigma_m  — mean stress      = (sigma_max + sigma_min) / 2
    R        — stress ratio     = sigma_min / sigma_max  (1.0 when sigma_max == 0)

    Raises FatigueDataError when sigma_max < sigma_min.
    """
    if sigma_max < sigma_min:
        raise FatigueDataError(
            f"sigma_max ({sigma_max}) must be >= sigma_min ({sigma_min})"
        )
    sigma_a = (sigma_max - sigma_min) / 2.0
    sigma_m = (sigma_max + sigma_min) / 2.0
    R = 1.0 if sigma_max == 0.0 else sigma_min / sigma_max
    return sigma_a, sigma_m, R


def goodman_equivalent_amplitude(sigma_a, sigma_m, sigma_ult):
    """
    Return the fully-reversed equivalent amplitude via the linear Goodman relation:
        sigma_a_eq = sigma_a / (1 - sigma_m / sigma_ult)

    Raises FatigueDataError when sigma_ult <= 0 or sigma_m >= sigma_ult.
    """
    if sigma_ult <= 0.0:
        raise FatigueDataError(f"sigma_ult must be positive; got {sigma_ult}")
    if sigma_m >= sigma_ult:
        raise FatigueDataError(
            f"Mean stress {sigma_m} equals or exceeds ultimate strength {sigma_ult}; "
            "cycle is statically failed — fatigue life is undefined"
        )
    return sigma_a / (1.0 - sigma_m / sigma_ult)


def gerber_equivalent_amplitude(sigma_a, sigma_m, sigma_ult):
    """
    Return the fully-reversed equivalent amplitude via the parabolic Gerber relation:
        sigma_a_eq = sigma_a / (1 - (sigma_m / sigma_ult)^2)

    Less conservative than Goodman in the tensile mean-stress region.
    Raises FatigueDataError when sigma_ult <= 0 or sigma_m >= sigma_ult.
    """
    if sigma_ult <= 0.0:
        raise FatigueDataError(f"sigma_ult must be positive; got {sigma_ult}")
    if sigma_m >= sigma_ult:
        raise FatigueDataError(
            f"Mean stress {sigma_m} equals or exceeds ultimate strength {sigma_ult}; "
            "cycle is statically failed — fatigue life is undefined"
        )
    return sigma_a / (1.0 - (sigma_m / sigma_ult) ** 2)


def evaluate_sn_life(sigma_a, sn_data):
    """
    Estimate fatigue life N (cycles) by log-log interpolation/extrapolation
    of an S-N dataset.

    sn_data : list of (stress_amplitude, cycles) pairs; at least 2 entries required.
    sigma_a : applied (or equivalent) stress amplitude.

    Uses piecewise log-log linear interpolation.  When sigma_a falls outside
    the tested range, the nearest two-point segment is extrapolated; the caller
    is responsible for flagging extrapolated results.

    Raises FatigueDataError for degenerate inputs (< 2 points, non-positive values).
    """
    if len(sn_data) < 2:
        raise FatigueDataError(
            f"S-N dataset must contain at least 2 points; got {len(sn_data)}"
        )
    if sigma_a <= 0.0:
        raise FatigueDataError(f"Stress amplitude must be positive; got {sigma_a}")

    pairs = sorted(sn_data, key=lambda p: p[0], reverse=True)  # high stress first

    for s, n in pairs:
        if s <= 0.0 or n <= 0.0:
            raise FatigueDataError(
                f"All S-N data entries must have positive values; found (s={s}, n={n})"
            )

    # Interpolation: find the bracketing segment
    for i in range(len(pairs) - 1):
        s1, n1 = pairs[i]
        s2, n2 = pairs[i + 1]
        if s2 <= sigma_a <= s1:
            return _log_log_interp(s1, n1, s2, n2, sigma_a)

    # Extrapolation: use the closest end segment
    if sigma_a > pairs[0][0]:
        s1, n1 = pairs[0]
        s2, n2 = pairs[1]
    else:
        s1, n1 = pairs[-2]
        s2, n2 = pairs[-1]

    return _log_log_interp(s1, n1, s2, n2, sigma_a)


def _log_log_interp(s1, n1, s2, n2, s):
    """Perform one-segment log-log linear interpolation/extrapolation."""
    log_s1, log_n1 = math.log10(s1), math.log10(n1)
    log_s2, log_n2 = math.log10(s2), math.log10(n2)
    if log_s1 == log_s2:
        return n1
    slope = (log_n2 - log_n1) / (log_s2 - log_s1)
    log_n = log_n1 + slope * (math.log10(s) - log_s1)
    return 10.0 ** log_n


def apply_scatter_factor(n_mean, scatter_factor):
    """
    Return the design fatigue allowable N_design = N_mean / scatter_factor.

    Raises FatigueDataError when scatter_factor <= 0 or n_mean <= 0.
    """
    if scatter_factor <= 0.0:
        raise FatigueDataError(
            f"Scatter factor must be positive; got {scatter_factor}"
        )
    if n_mean <= 0.0:
        raise FatigueDataError(f"Mean fatigue life must be positive; got {n_mean}")
    return n_mean / scatter_factor


def categorize_dataset(num_points, num_r_ratio_variants, has_runout_data):
    """
    Categorize a fatigue dataset as 'qualified', 'provisional', or 'insufficient'.

    Rules (paraphrased from ECSS-E-ST-32C §4.2.3 guidance):
      insufficient : num_points < 3
      qualified    : num_points >= MIN_TEST_POINTS and
                     num_r_ratio_variants >= MIN_R_RATIO_VARIANTS and
                     has_runout_data is True
      provisional  : everything in between

    Returns (category: str, findings: list[str]).
    """
    if num_points < 3:
        return "insufficient", [
            f"Too few test points ({num_points}); a minimum of 3 is required before any use"
        ]

    findings = []
    if num_points < MIN_TEST_POINTS:
        findings.append(
            f"Point count {num_points} is below the recommended minimum of "
            f"{MIN_TEST_POINTS}; engineering acceptance justification required"
        )
    if num_r_ratio_variants < MIN_R_RATIO_VARIANTS:
        findings.append(
            f"Only {num_r_ratio_variants} stress-ratio variant(s) tested; "
            f"at least {MIN_R_RATIO_VARIANTS} are recommended to bound the design loading"
        )
    if not has_runout_data:
        findings.append(
            "No run-out data available; the endurance limit is not experimentally confirmed"
        )

    if findings:
        return "provisional", findings
    return "qualified", []


def check_record_completeness(record):
    """
    Verify that a material fatigue record contains all mandatory fields.

    Required keys: 'material', 'sigma_ult', 'endurance_limit',
                   'scatter_factor', 'sn_data', 'r_ratio_variants'.

    Returns (is_complete: bool, missing_fields: list[str]).
    """
    required = {
        "material", "sigma_ult", "endurance_limit",
        "scatter_factor", "sn_data", "r_ratio_variants",
    }
    missing = [f for f in sorted(required) if f not in record or record[f] is None]
    return (len(missing) == 0), missing


def compute_fatigue_ratio(endurance_limit, sigma_ult):
    """
    Return the fatigue ratio f = endurance_limit / sigma_ult.

    Expected band for metallic space-structure alloys: 0.35 – 0.55.
    Values outside this band should be flagged for review.

    Raises FatigueDataError when sigma_ult <= 0 or endurance_limit < 0.
    """
    if sigma_ult <= 0.0:
        raise FatigueDataError(f"sigma_ult must be positive; got {sigma_ult}")
    if endurance_limit < 0.0:
        raise FatigueDataError(
            f"endurance_limit must be non-negative; got {endurance_limit}"
        )
    return endurance_limit / sigma_ult


def assess_material_fatigue(record):
    """
    Full fatigue-property assessment for one material record.

    record keys (all mandatory):
        material         : str — material identifier
        sigma_ult        : float — ultimate tensile strength (MPa)
        endurance_limit  : float — endurance limit at R = -1 (MPa)
        scatter_factor   : float — scatter factor to apply to mean life
        sn_data          : list of (sigma_a, N) tuples
        r_ratio_variants : int   — number of distinct R-ratios tested
        has_runout_data  : bool  — optional, defaults to False

    Returns a dict with keys:
        complete      : bool
        missing_fields: list[str]
        category      : str or None
        findings      : list[str]
        fatigue_ratio : float or None
    """
    complete, missing = check_record_completeness(record)
    result = {
        "complete": complete,
        "missing_fields": missing,
        "category": None,
        "findings": [],
        "fatigue_ratio": None,
    }

    if not complete:
        result["findings"].append(
            f"Record is incomplete; missing fields: {missing}"
        )
        return result

    if record["sigma_ult"] <= 0.0:
        result["findings"].append(
            f"sigma_ult must be positive; got {record['sigma_ult']}"
        )
        return result

    if record["scatter_factor"] <= 0.0:
        result["findings"].append(
            f"scatter_factor must be positive; got {record['scatter_factor']}"
        )
        return result

    sn_data = record["sn_data"] or []
    n_pts = len(sn_data)
    n_r = record["r_ratio_variants"]
    has_runout = record.get("has_runout_data", False)

    category, cat_findings = categorize_dataset(n_pts, n_r, has_runout)
    result["category"] = category
    result["findings"].extend(cat_findings)

    fatigue_ratio = compute_fatigue_ratio(
        record["endurance_limit"], record["sigma_ult"]
    )
    result["fatigue_ratio"] = fatigue_ratio

    if not (FATIGUE_RATIO_LOW <= fatigue_ratio <= FATIGUE_RATIO_HIGH):
        result["findings"].append(
            f"Fatigue ratio {fatigue_ratio:.3f} is outside the expected band "
            f"[{FATIGUE_RATIO_LOW}, {FATIGUE_RATIO_HIGH}]; verify data entry"
        )

    return result
