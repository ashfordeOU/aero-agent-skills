#!/usr/bin/env python3
"""Second multipactor-analysis-level applicability (ECSS-E-ST-20-01C 5.3.2.3.1).

Offline, deterministic, stdlib only.  For each radio-frequency equipment item
the module decides whether the first analysis level (parallel-plate
susceptibility-chart lookup) is sufficient, whether the more detailed second
analysis level applies, or whether the item sits outside the tracked-electron
model of the second level and must be routed to a seeded multipactor-test.

Paraphrased procedure only; the standard clause is the anchor, not the text.
"""

from __future__ import annotations

import math

__all__ = [
    "EQUIPMENT_PROFILES",
    "CHART_BAND_GHZ_MM",
    "DEFAULT_UNIFORMITY_LIMIT",
    "SECOND_LEVEL_PREREQUISITES",
    "normalize_equipment_type",
    "equipment_profile",
    "frequency_gap_product",
    "within_chart_band",
    "field_uniformity_ratio",
    "first_level_outcome",
    "determine_analysis_level",
    "second_level_prerequisites",
    "assess_equipment_item",
    "assess_equipment_inventory",
]

# Validated band of the parallel-plate susceptibility charts, as a
# frequency-gap-product in GHz*mm.  Outside this band the first-level chart
# lookup carries no credible reading and the detailed level takes over.
CHART_BAND_GHZ_MM = (0.1, 100.0)

# Peak-to-mean local field ratio above which the single equivalent-gap model
# behind the first level stops representing the real field distribution.
DEFAULT_UNIFORMITY_LIMIT = 1.20

# Representation tolerance: a difference of decibel quantities or of products
# of floats can land a few units in the last place on the wrong side of an
# inclusive limit.  Absorb that here, never by widening an engineering limit.
COMPARISON_TOLERANCE = 1e-9

SECOND_LEVEL_PREREQUISITES = (
    "secondary_emission_dataset",
    "field_model_id",
    "tracking_solver_validation",
)

_REQUIRED_ITEM_KEYS = (
    "item_id",
    "equipment_type",
    "frequency_ghz",
    "gap_mm",
    "peak_field_v_per_m",
    "mean_field_v_per_m",
)

EQUIPMENT_PROFILES = {
    "uniform-waveguide-section": {
        "family": "guided-wave",
        "chart_representable": True,
        "second_level_admissible": True,
    },
    "coaxial-line-section": {
        "family": "guided-wave",
        "chart_representable": True,
        "second_level_admissible": True,
    },
    "waveguide-iris-filter": {
        "family": "guided-wave",
        "chart_representable": False,
        "second_level_admissible": True,
    },
    "coaxial-connector": {
        "family": "interface",
        "chart_representable": False,
        "second_level_admissible": True,
    },
    "metal-wall-printed-line": {
        "family": "planar",
        "chart_representable": True,
        "second_level_admissible": True,
    },
    "antenna-radiating-aperture": {
        "family": "radiative",
        "chart_representable": False,
        "second_level_admissible": True,
    },
    "rotary-joint": {
        "family": "interface",
        "chart_representable": False,
        "second_level_admissible": True,
    },
    "high-power-switch": {
        "family": "interface",
        "chart_representable": False,
        "second_level_admissible": True,
    },
    # Surfaces where a dielectric is exposed to the radio-frequency field
    # accumulate surface charge; the metal-wall electron-tracking model of the
    # second level does not represent that path, so these route to hardware.
    "dielectric-loaded-resonator": {
        "family": "dielectric-exposed",
        "chart_representable": False,
        "second_level_admissible": False,
    },
    "exposed-dielectric-printed-line": {
        "family": "dielectric-exposed",
        "chart_representable": False,
        "second_level_admissible": False,
    },
}

_ALIASES = {
    "waveguide": "uniform-waveguide-section",
    "waveguide-section": "uniform-waveguide-section",
    "coax": "coaxial-line-section",
    "coaxial-line": "coaxial-line-section",
    "iris-filter": "waveguide-iris-filter",
    "connector": "coaxial-connector",
    "stripline": "metal-wall-printed-line",
    "microstrip": "exposed-dielectric-printed-line",
    "aperture": "antenna-radiating-aperture",
    "switch": "high-power-switch",
}


def _at_least(value, limit):
    """Inclusive >= that absorbs float representation error."""
    return value > limit or math.isclose(
        value, limit, rel_tol=COMPARISON_TOLERANCE, abs_tol=COMPARISON_TOLERANCE
    )


def _positive_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("%s must be finite and positive, got %r" % (label, value))
    return value


def normalize_equipment_type(raw):
    """Fold a free-form equipment-type label onto a known profile key."""
    if not isinstance(raw, str):
        raise ValueError("equipment type must be a string, got %r" % (raw,))
    key = raw.strip().lower().replace("_", "-").replace(" ", "-")
    while "--" in key:
        key = key.replace("--", "-")
    if not key:
        raise ValueError("equipment type must not be blank")
    key = _ALIASES.get(key, key)
    if key not in EQUIPMENT_PROFILES:
        raise ValueError("unknown equipment type %r" % (raw,))
    return key


def equipment_profile(raw):
    """Return a copy of the applicability profile for an equipment type."""
    key = normalize_equipment_type(raw)
    profile = dict(EQUIPMENT_PROFILES[key])
    profile["equipment_type"] = key
    return profile


def frequency_gap_product(frequency_ghz, gap_mm):
    """Frequency-gap-product in GHz*mm for the narrowest gap of the item."""
    freq = _positive_float(frequency_ghz, "frequency_ghz")
    gap = _positive_float(gap_mm, "gap_mm")
    return freq * gap


def within_chart_band(fd_ghz_mm):
    """True when the frequency-gap-product falls inside the validated band."""
    value = _positive_float(fd_ghz_mm, "fd_ghz_mm")
    low, high = CHART_BAND_GHZ_MM
    return _at_least(value, low) and _at_least(high, value)


def field_uniformity_ratio(peak_field_v_per_m, mean_field_v_per_m):
    """Peak-to-mean ratio of the local field across the susceptible gap."""
    peak = _positive_float(peak_field_v_per_m, "peak_field_v_per_m")
    mean = _positive_float(mean_field_v_per_m, "mean_field_v_per_m")
    if peak < mean and not math.isclose(
        peak, mean, rel_tol=COMPARISON_TOLERANCE, abs_tol=COMPARISON_TOLERANCE
    ):
        raise ValueError(
            "peak field %r is below mean field %r" % (peak_field_v_per_m, mean_field_v_per_m)
        )
    return max(peak / mean, 1.0)


def first_level_outcome(margin_db, required_margin_db):
    """Categorize the first-level margin as adequate or as a shortfall."""
    if isinstance(margin_db, bool) or not isinstance(margin_db, (int, float)):
        raise ValueError("margin_db must be a real number, got %r" % (margin_db,))
    if not math.isfinite(float(margin_db)):
        raise ValueError("margin_db must be finite, got %r" % (margin_db,))
    required = _positive_float(required_margin_db, "required_margin_db")
    return "adequate" if _at_least(float(margin_db), required) else "shortfall"


def _validate_item(item):
    if not isinstance(item, dict):
        raise ValueError("equipment item must be a mapping, got %r" % (item,))
    for key in _REQUIRED_ITEM_KEYS:
        if key not in item:
            raise ValueError("equipment item missing required key %r" % (key,))
    if not isinstance(item["item_id"], str) or not item["item_id"].strip():
        raise ValueError("item_id must be a non-blank string")


def determine_analysis_level(item, uniformity_limit=DEFAULT_UNIFORMITY_LIMIT):
    """Route one equipment item to an analysis level, with the drivers."""
    _validate_item(item)
    limit = _positive_float(uniformity_limit, "uniformity_limit")
    profile = equipment_profile(item["equipment_type"])
    fd = frequency_gap_product(item["frequency_ghz"], item["gap_mm"])
    ratio = field_uniformity_ratio(item["peak_field_v_per_m"], item["mean_field_v_per_m"])
    in_band = within_chart_band(fd)

    drivers = []
    if not profile["chart_representable"]:
        drivers.append("geometry-not-chart-representable")
    if not in_band:
        drivers.append("frequency-gap-product-outside-chart-band")
    if not _at_least(limit, ratio):
        drivers.append("field-non-uniformity-above-limit")

    chart_applicable = not drivers
    margin_state = "not-evaluated"
    if chart_applicable:
        margin = item.get("first_level_margin_db")
        required = item.get("required_margin_db")
        if margin is None or required is None:
            drivers.append("first-level-margin-not-on-record")
        else:
            margin_state = first_level_outcome(margin, required)
            if margin_state == "shortfall":
                drivers.append("first-level-margin-shortfall")

    if not drivers:
        level = "first-level-sufficient"
    elif profile["second_level_admissible"]:
        level = "second-level-required"
    else:
        drivers.append("second-level-model-not-admissible")
        level = "multipactor-test-required"

    return {
        "item_id": item["item_id"],
        "equipment_type": profile["equipment_type"],
        "family": profile["family"],
        "frequency_gap_product_ghz_mm": fd,
        "field_uniformity_ratio": ratio,
        "chart_applicable": chart_applicable,
        "first_level_margin_state": margin_state,
        "level": level,
        "drivers": drivers,
    }


def second_level_prerequisites(item):
    """List the second-level inputs that are not yet on record for an item."""
    if not isinstance(item, dict):
        raise ValueError("equipment item must be a mapping, got %r" % (item,))
    missing = []
    for key in SECOND_LEVEL_PREREQUISITES:
        value = item.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(key)
    return missing


def assess_equipment_item(item, uniformity_limit=DEFAULT_UNIFORMITY_LIMIT):
    """Full per-item verdict: analysis level, missing inputs and findings."""
    verdict = determine_analysis_level(item, uniformity_limit=uniformity_limit)
    missing = second_level_prerequisites(item)
    findings = []
    if verdict["level"] == "second-level-required" and missing:
        findings.append("second-level-prerequisite-missing")
    if verdict["level"] == "multipactor-test-required":
        findings.append("route-to-seeded-multipactor-test")
    verdict["missing_prerequisites"] = missing
    verdict["ready_for_second_level"] = (
        verdict["level"] == "second-level-required" and not missing
    )
    verdict["findings"] = findings
    verdict["compliant"] = not findings
    return verdict


def assess_equipment_inventory(items, uniformity_limit=DEFAULT_UNIFORMITY_LIMIT):
    """Aggregate the applicability verdict over a whole equipment inventory."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("inventory must be a list of equipment items")
    if len(items) == 0:
        raise ValueError("inventory must contain at least one equipment item")
    results = [assess_equipment_item(i, uniformity_limit=uniformity_limit) for i in items]
    seen = set()
    for result in results:
        if result["item_id"] in seen:
            raise ValueError("duplicate item_id %r in inventory" % (result["item_id"],))
        seen.add(result["item_id"])
    counts = {
        "first-level-sufficient": 0,
        "second-level-required": 0,
        "multipactor-test-required": 0,
    }
    for result in results:
        counts[result["level"]] += 1
    return {
        "items": results,
        "counts": counts,
        "open_findings": [r["item_id"] for r in results if r["findings"]],
        "compliant": all(r["compliant"] for r in results),
    }
