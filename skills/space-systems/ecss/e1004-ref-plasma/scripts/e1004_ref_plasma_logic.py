#!/usr/bin/env python3
"""ECSS-E-ST-10-04C Annex H (info) plasma-region reference data
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): Annex H
tabulates order-of-magnitude plasma density and temperature reference
values per space-environment region -- ionosphere, plasmasphere,
auroral, outer magnetosphere, solar wind, magnetosheath, and the
magnetotail/L2 environment -- for use when no mission-specific plasma
model is available. This module implements the reference-value table,
a range-validation check for a candidate density or temperature
against a region's reference range, a log-space interpolation helper
for deriving an intermediate representative value, an orbit-regime to
region source-selection lookup, and a surface-charging screening rule
for the hot, tenuous regions where spacecraft charging is a known
concern. It does not implement a physics-based plasma model or replace
a mission-specific environment specification.
"""

import math
from types import MappingProxyType

# Order-of-magnitude reference ranges per region: (density_cm3 low/high,
# temperature_ev low/high). charging_risk marks a region where the
# combination of low density and high temperature (a hot, tenuous
# plasma) is a recognized spacecraft surface-charging driver.
PLASMA_REGIONS = MappingProxyType(
    {
        "ionosphere": {
            "density_range_cm3": (1.0e3, 1.0e6),
            "temperature_range_ev": (0.03, 0.3),
            "charging_risk": False,
        },
        "plasmasphere": {
            "density_range_cm3": (1.0e1, 1.0e3),
            "temperature_range_ev": (0.2, 2.0),
            "charging_risk": False,
        },
        "auroral": {
            "density_range_cm3": (1.0, 1.0e2),
            "temperature_range_ev": (1.0e2, 1.0e4),
            "charging_risk": True,
        },
        "outer_magnetosphere": {
            "density_range_cm3": (1.0e-2, 1.0),
            "temperature_range_ev": (1.0e2, 1.0e4),
            "charging_risk": True,
        },
        "solar_wind": {
            "density_range_cm3": (1.0, 1.0e1),
            "temperature_range_ev": (1.0, 1.0e2),
            "charging_risk": False,
        },
        "magnetosheath": {
            "density_range_cm3": (1.0, 5.0e1),
            "temperature_range_ev": (1.0e1, 1.0e3),
            "charging_risk": False,
        },
        "magnetotail_l2": {
            "density_range_cm3": (1.0e-2, 1.0),
            "temperature_range_ev": (1.0e2, 1.0e4),
            "charging_risk": True,
        },
    }
)

# Source-selection rule: which reference region applies for a given
# mission orbit regime descriptor.
ORBIT_REGIME_TO_REGION = MappingProxyType(
    {
        "leo_ionosphere": "ionosphere",
        "meo_plasmasphere_crossing": "plasmasphere",
        "auroral_oval_pass": "auroral",
        "geo_outer_magnetosphere": "outer_magnetosphere",
        "interplanetary_solar_wind": "solar_wind",
        "magnetosheath_crossing": "magnetosheath",
        "magnetotail_or_l2": "magnetotail_l2",
    }
)


def plasma_region_reference(region):
    """Reference dict for one Annex H region: a new dict copy with
    "density_range_cm3", "temperature_range_ev", "charging_risk".
    Raises ValueError for a region not in PLASMA_REGIONS."""
    if region not in PLASMA_REGIONS:
        raise ValueError(
            "unrecognized Annex H plasma region %r; known regions: %s"
            % (region, ", ".join(sorted(PLASMA_REGIONS)))
        )
    return dict(PLASMA_REGIONS[region])


def classify_value_against_range(value, lo, hi):
    """Classify value relative to [lo, hi]: "below_range", "within_range"
    (inclusive of both bounds), or "above_range". Raises ValueError for
    a negative value or an inverted range (lo > hi)."""
    if value < 0:
        raise ValueError("value must be >= 0")
    if lo > hi:
        raise ValueError("invalid reference range: lo > hi")
    if value < lo:
        return "below_range"
    if value > hi:
        return "above_range"
    return "within_range"


def validate_density(region, density_cm3):
    """Classify a candidate density (cm^-3) against a region's Annex H
    reference density range. Raises ValueError for an unrecognized
    region or a negative density."""
    ref = plasma_region_reference(region)
    lo, hi = ref["density_range_cm3"]
    return classify_value_against_range(density_cm3, lo, hi)


def validate_temperature(region, temperature_ev):
    """Classify a candidate temperature (eV) against a region's Annex H
    reference temperature range. Raises ValueError for an unrecognized
    region or a negative temperature."""
    ref = plasma_region_reference(region)
    lo, hi = ref["temperature_range_ev"]
    return classify_value_against_range(temperature_ev, lo, hi)


def log_interpolate(lo, hi, fraction):
    """Interpolate between lo and hi in log10 space at the given
    fraction (0.0 returns lo, 1.0 returns hi, 0.5 returns the geometric
    mean). Raises ValueError for lo <= 0, hi <= 0, lo > hi, or a
    fraction outside [0.0, 1.0]."""
    if lo <= 0 or hi <= 0:
        raise ValueError("lo and hi must be > 0 for log-space interpolation")
    if lo > hi:
        raise ValueError("invalid range: lo > hi")
    if fraction < 0.0 or fraction > 1.0:
        raise ValueError("fraction must be within [0.0, 1.0]")
    log_lo = math.log10(lo)
    log_hi = math.log10(hi)
    return 10 ** (log_lo + fraction * (log_hi - log_lo))


def representative_value(region, quantity, fraction=0.5):
    """Log-space representative value for a region's "density" or
    "temperature" reference range at the given fraction (see
    log_interpolate). Raises ValueError for an unrecognized region or
    a quantity other than "density"/"temperature"."""
    ref = plasma_region_reference(region)
    if quantity == "density":
        lo, hi = ref["density_range_cm3"]
    elif quantity == "temperature":
        lo, hi = ref["temperature_range_ev"]
    else:
        raise ValueError('quantity must be "density" or "temperature"')
    return log_interpolate(lo, hi, fraction)


def select_region(orbit_regime):
    """Annex H region key applicable to a mission orbit_regime descriptor
    (see ORBIT_REGIME_TO_REGION). Raises ValueError for an unrecognized
    regime descriptor."""
    if orbit_regime not in ORBIT_REGIME_TO_REGION:
        raise ValueError(
            "unrecognized orbit regime %r; known regimes: %s"
            % (orbit_regime, ", ".join(sorted(ORBIT_REGIME_TO_REGION)))
        )
    return ORBIT_REGIME_TO_REGION[orbit_regime]


def charging_risk_assessment(region, density_cm3, temperature_ev):
    """Surface-charging screening result for one region/density/
    temperature reading.

    Returns {"region": region, "charging_risk_region": bool,
    "density_classification": str, "temperature_classification": str,
    "surface_charging_flag": bool}. surface_charging_flag is True only
    when the region is a recognized charging-risk region (hot, tenuous
    plasma) and the reading is consistent with that condition: density
    not above the reference range and temperature not below it. Raises
    ValueError for an unrecognized region or a negative reading."""
    ref = plasma_region_reference(region)
    density_classification = validate_density(region, density_cm3)
    temperature_classification = validate_temperature(region, temperature_ev)
    risk_region = ref["charging_risk"]
    surface_charging_flag = (
        risk_region
        and density_classification != "above_range"
        and temperature_classification != "below_range"
    )
    return {
        "region": region,
        "charging_risk_region": risk_region,
        "density_classification": density_classification,
        "temperature_classification": temperature_classification,
        "surface_charging_flag": surface_charging_flag,
    }
