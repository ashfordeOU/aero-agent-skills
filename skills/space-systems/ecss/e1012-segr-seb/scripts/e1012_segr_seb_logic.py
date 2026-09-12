"""
Deterministic offline logic for SEGR and SEB destructive rate prediction.
Implements the procedure described in ECSS-E-ST-10-12C §9.4.1.6 (paraphrased).

SEGR = Single Event Gate Rupture (power MOSFETs only)
SEB  = Single Event Burnout (power MOSFETs and bipolar transistors)
"""

import math

SECONDS_PER_DAY = 86400.0

DEVICE_TYPES = frozenset({"power_mosfet", "bipolar_transistor"})
EFFECT_TYPES = frozenset({"SEGR", "SEB"})
ORBIT_REGIMES = frozenset({"geo", "meo", "leo_polar", "leo_equatorial", "interplanetary"})

_ORBIT_TABLE = {
    "geo": {
        "description": "Geostationary — outside magnetosphere, full galactic cosmic-ray spectrum",
        "flux_scale": 1.0,
    },
    "meo": {
        "description": "Medium Earth Orbit — elevated trapped proton and ion flux",
        "flux_scale": 1.8,
    },
    "leo_polar": {
        "description": "LEO polar — solar particle event exposure, SAA proton contribution",
        "flux_scale": 0.7,
    },
    "leo_equatorial": {
        "description": "LEO equatorial — largely shielded by geomagnetic field",
        "flux_scale": 0.15,
    },
    "interplanetary": {
        "description": "Interplanetary cruise — unattenuated GCR plus solar particle events",
        "flux_scale": 1.2,
    },
}


def validate_weibull_params(sigma_sat: float, let_th: float, w: float, s: float) -> None:
    """Raise ValueError if any Weibull parameter is physically invalid."""
    if sigma_sat <= 0.0:
        raise ValueError(f"sigma_sat must be positive, got {sigma_sat}")
    if let_th < 0.0:
        raise ValueError(f"let_th must be non-negative, got {let_th}")
    if w <= 0.0:
        raise ValueError(f"w (width) must be positive, got {w}")
    if s <= 0.0:
        raise ValueError(f"s (shape) must be positive, got {s}")


def weibull_cross_section(
    let: float,
    sigma_sat: float,
    let_th: float,
    w: float,
    s: float,
) -> float:
    """
    Weibull cross-section σ(LET) for a single LET value (MeV·cm²/mg).

    Returns σ in cm² per device.  Zero for LET ≤ LET_th.
    """
    validate_weibull_params(sigma_sat, let_th, w, s)
    if let <= let_th:
        return 0.0
    return sigma_sat * (1.0 - math.exp(-((let - let_th) / w) ** s))


def check_bias_margin(v_applied: float, v_threshold: float) -> dict:
    """
    Evaluate whether the applied bias is within the characterisation threshold.

    Returns a dict with:
      above_threshold (bool): True if v_applied >= v_threshold
      margin_fraction (float): (v_threshold - v_applied) / v_threshold
        positive means safe side, negative means extrapolating above test bias
    """
    if v_threshold <= 0.0:
        raise ValueError(f"v_threshold must be positive, got {v_threshold}")
    margin = (v_threshold - v_applied) / v_threshold
    return {
        "above_threshold": v_applied >= v_threshold,
        "margin_fraction": margin,
    }


def compute_rate_heavy_ion(
    let_spectrum: list,
    sigma_sat: float,
    let_th: float,
    w: float,
    s: float,
) -> float:
    """
    Integrate σ(LET) × φ(LET) over the differential LET spectrum using the
    trapezoidal rule.

    let_spectrum: list of (LET_MeVcm2mg, differential_flux) tuples, at least
    2 points.  The differential flux is expressed per unit LET and per day,
    i.e. ions / (cm² · day · (MeV·cm²/mg)), which is the spectrum convention
    used throughout this pack.  Integrating that flux against a cross-section
    in cm² therefore yields the rate directly in events/device/day; no further
    time conversion is applied here.

    Returns rate in events/device/day.
    """
    if len(let_spectrum) < 2:
        raise ValueError("let_spectrum must contain at least 2 points for integration")
    for let_val, flux_val in let_spectrum:
        if let_val < 0.0:
            raise ValueError(f"LET values must be non-negative, got {let_val}")
        if flux_val < 0.0:
            raise ValueError(f"Flux values must be non-negative, got {flux_val}")
    validate_weibull_params(sigma_sat, let_th, w, s)

    rate = 0.0
    for i in range(len(let_spectrum) - 1):
        let_a, flux_a = let_spectrum[i]
        let_b, flux_b = let_spectrum[i + 1]
        sigma_a = weibull_cross_section(let_a, sigma_sat, let_th, w, s)
        sigma_b = weibull_cross_section(let_b, sigma_sat, let_th, w, s)
        d_let = abs(let_b - let_a)
        rate += 0.5 * (sigma_a * flux_a + sigma_b * flux_b) * d_let
    return rate


def categorize_device(device_type: str) -> dict:
    """
    Return the set of destructive SEE effects applicable to the device type.

    power_mosfet  → SEGR and SEB
    bipolar_transistor → SEB only
    """
    if device_type not in DEVICE_TYPES:
        raise ValueError(
            f"Unknown device_type '{device_type}'. Must be one of {sorted(DEVICE_TYPES)}"
        )
    if device_type == "power_mosfet":
        return {"device_type": device_type, "applicable_effects": ["SEGR", "SEB"]}
    return {"device_type": device_type, "applicable_effects": ["SEB"]}


def categorize_orbit_environment(orbit: str) -> dict:
    """
    Return a representative flux scale factor and description for a given orbit.

    orbit must be one of: geo, meo, leo_polar, leo_equatorial, interplanetary.
    """
    if orbit not in ORBIT_REGIMES:
        raise ValueError(
            f"Unknown orbit regime '{orbit}'. Must be one of {sorted(ORBIT_REGIMES)}"
        )
    return dict(_ORBIT_TABLE[orbit])


def scale_spectrum(let_spectrum: list, scale: float) -> list:
    """
    Return a new LET spectrum with every flux value multiplied by scale.

    Does not modify let_spectrum in-place.
    """
    if scale < 0.0:
        raise ValueError(f"scale must be non-negative, got {scale}")
    return [(let_val, flux_val * scale) for let_val, flux_val in let_spectrum]


def margin_to_requirement(rate_day: float, requirement: float) -> float:
    """
    Return log₁₀(requirement / rate_day).

    Positive value → rate is below requirement (passing).
    Negative value → rate exceeds requirement (failing).
    Returns +inf when rate_day is zero (immune device).
    """
    if requirement <= 0.0:
        raise ValueError(f"requirement must be positive, got {requirement}")
    if rate_day < 0.0:
        raise ValueError(f"rate_day must be non-negative, got {rate_day}")
    if rate_day == 0.0:
        return float("inf")
    return math.log10(requirement / rate_day)


def assess_seb(
    device_type: str,
    vds_applied: float,
    vds_test: float,
    let_spectrum: list,
    sigma_sat: float,
    let_th: float,
    w: float,
    s: float,
    rate_requirement: float = 1e-7,
    design_margin: float = 10.0,
) -> dict:
    """
    Full SEB assessment for a single power device.

    Returns a result dict containing:
      device_type, effect, weibull_params, bias_check,
      rate_per_device_s, rate_per_device_day, rate_requirement,
      effective_requirement (rate_requirement / design_margin),
      passes_rate_req (bool), log10_margin (float).
    """
    if device_type not in DEVICE_TYPES:
        raise ValueError(
            f"device_type must be one of {sorted(DEVICE_TYPES)}, got '{device_type}'"
        )
    if rate_requirement <= 0.0:
        raise ValueError(f"rate_requirement must be positive, got {rate_requirement}")
    if design_margin <= 0.0:
        raise ValueError(f"design_margin must be positive, got {design_margin}")

    bias = check_bias_margin(vds_applied, vds_test)
    # The LET spectrum carries a per-day differential flux, so the integral is
    # already events/device/day.  The per-second figure is the derived one.
    rate_day = compute_rate_heavy_ion(let_spectrum, sigma_sat, let_th, w, s)
    rate_s = rate_day / SECONDS_PER_DAY
    effective_req = rate_requirement / design_margin
    passes = rate_day <= effective_req
    log10_m = margin_to_requirement(rate_day, effective_req)

    return {
        "device_type": device_type,
        "effect": "SEB",
        "weibull_params": {"sigma_sat": sigma_sat, "let_th": let_th, "w": w, "s": s},
        "bias_check": bias,
        "rate_per_device_s": rate_s,
        "rate_per_device_day": rate_day,
        "rate_requirement": rate_requirement,
        "effective_requirement": effective_req,
        "passes_rate_req": passes,
        "log10_margin": log10_m,
    }


def assess_segr(
    device_type: str,
    vgs_applied: float,
    vgs_test: float,
    let_spectrum: list,
    sigma_sat: float,
    let_th: float,
    w: float,
    s: float,
    rate_requirement: float = 1e-7,
    design_margin: float = 10.0,
) -> dict:
    """
    Full SEGR assessment for a power MOSFET.

    SEGR applies to power_mosfet only.  Raises ValueError for other device types.
    Returns the same structure as assess_seb with effect='SEGR'.
    """
    if device_type != "power_mosfet":
        raise ValueError(
            f"SEGR applies to power_mosfet only, got '{device_type}'"
        )
    if rate_requirement <= 0.0:
        raise ValueError(f"rate_requirement must be positive, got {rate_requirement}")
    if design_margin <= 0.0:
        raise ValueError(f"design_margin must be positive, got {design_margin}")

    bias = check_bias_margin(vgs_applied, vgs_test)
    # The LET spectrum carries a per-day differential flux, so the integral is
    # already events/device/day.  The per-second figure is the derived one.
    rate_day = compute_rate_heavy_ion(let_spectrum, sigma_sat, let_th, w, s)
    rate_s = rate_day / SECONDS_PER_DAY
    effective_req = rate_requirement / design_margin
    passes = rate_day <= effective_req
    log10_m = margin_to_requirement(rate_day, effective_req)

    return {
        "device_type": device_type,
        "effect": "SEGR",
        "weibull_params": {"sigma_sat": sigma_sat, "let_th": let_th, "w": w, "s": s},
        "bias_check": bias,
        "rate_per_device_s": rate_s,
        "rate_per_device_day": rate_day,
        "rate_requirement": rate_requirement,
        "effective_requirement": effective_req,
        "passes_rate_req": passes,
        "log10_margin": log10_m,
    }
