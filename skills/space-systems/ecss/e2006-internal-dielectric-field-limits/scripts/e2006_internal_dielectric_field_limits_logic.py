#!/usr/bin/env python3
"""ECSS-E-ST-20-06C clause 9.2.3 -- internal dielectric field limits.

Deterministic, offline, stdlib-only implementation of the clause 9.2.3
check: the electric field inside a solid insulating material stays at or
below a stated cap, derated for the material's operating temperature,
unless a qualification demonstration for that application supports a
higher level.

Paraphrased procedure only -- no standard text is reproduced. The clause
anchor is ECSS-E-ST-20-06C 9.2.3.
"""

from __future__ import annotations

import math

#: Qualified insulating materials.
#:   base_cap_v_per_m -- the default internal-field cap at or below the knee
#:   knee_temperature_c -- derating starts above this temperature
#:   service_temperature_c -- upper qualified service temperature
#:   floor_factor -- derating factor reached at the service temperature
MATERIAL_PROPERTIES = {
    "polyimide-film": {
        "base_cap_v_per_m": 2.0e7,
        "knee_temperature_c": 120.0,
        "service_temperature_c": 200.0,
        "floor_factor": 0.60,
    },
    "ptfe-wire-insulation": {
        "base_cap_v_per_m": 1.6e7,
        "knee_temperature_c": 100.0,
        "service_temperature_c": 200.0,
        "floor_factor": 0.50,
    },
    "epoxy-glass-laminate": {
        "base_cap_v_per_m": 1.2e7,
        "knee_temperature_c": 80.0,
        "service_temperature_c": 130.0,
        "floor_factor": 0.55,
    },
    "silicone-encapsulant": {
        "base_cap_v_per_m": 8.0e6,
        "knee_temperature_c": 70.0,
        "service_temperature_c": 150.0,
        "floor_factor": 0.45,
    },
    "polyethylene-cable-dielectric": {
        "base_cap_v_per_m": 1.4e7,
        "knee_temperature_c": 60.0,
        "service_temperature_c": 90.0,
        "floor_factor": 0.50,
    },
}

#: Insulator geometries the field computation understands.
GEOMETRIES = frozenset({"planar", "coaxial"})

#: Lowest temperature the qualified-material data is stated for.
MIN_TEMPERATURE_C = -180.0

#: Relative tolerance absorbing the float error of a computed quotient.
#: The engineering cap is unchanged; only the representation error of the
#: field division is forgiven exactly at the boundary.
FIELD_REL_TOL = 1e-9


def categorize_insulating_material(material):
    """Return the normalized key of a qualified insulating material.

    Raises ValueError for a blank, non-string or uncategorized material.
    """
    if not isinstance(material, str):
        raise ValueError("insulating material must be a string, got %r" % (material,))
    key = material.strip().lower()
    if not key:
        raise ValueError("insulating material must not be blank")
    if key not in MATERIAL_PROPERTIES:
        raise ValueError("uncategorized insulating material %r" % (material,))
    return key


def _finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite" % label)
    return out


def planar_internal_field(potential_v, thickness_m):
    """Uniform field (V/m) inside a planar insulating wall."""
    potential = _finite_number(potential_v, "potential_v")
    thickness = _finite_number(thickness_m, "thickness_m")
    if potential < 0.0:
        raise ValueError("potential_v must not be negative")
    if thickness <= 0.0:
        raise ValueError("thickness_m must be positive")
    return potential / thickness


def coaxial_internal_field(potential_v, inner_radius_m, outer_radius_m):
    """Peak field (V/m) at the inner conductor of a coaxial insulator."""
    potential = _finite_number(potential_v, "potential_v")
    r_in = _finite_number(inner_radius_m, "inner_radius_m")
    r_out = _finite_number(outer_radius_m, "outer_radius_m")
    if potential < 0.0:
        raise ValueError("potential_v must not be negative")
    if r_in <= 0.0:
        raise ValueError("inner_radius_m must be positive")
    if r_out <= r_in:
        raise ValueError("outer_radius_m must exceed inner_radius_m")
    return potential / (r_in * math.log(r_out / r_in))


def internal_field(item):
    """Dispatch the field computation on the item geometry."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping, got %r" % (item,))
    geometry = item.get("geometry")
    if not isinstance(geometry, str) or geometry.strip().lower() not in GEOMETRIES:
        raise ValueError("unrecognized insulator geometry %r" % (geometry,))
    geometry = geometry.strip().lower()
    if geometry == "planar":
        return planar_internal_field(item.get("potential_v"), item.get("thickness_m"))
    return coaxial_internal_field(
        item.get("potential_v"),
        item.get("inner_radius_m"),
        item.get("outer_radius_m"),
    )


def temperature_derating_factor(material, temperature_c):
    """Derating factor applied to the base cap at an operating temperature.

    Unity at or below the material knee, falling linearly to the floor
    factor at the upper qualified service temperature. Above that service
    temperature the material is outside its envelope: an error, not a pass.
    """
    key = categorize_insulating_material(material)
    props = MATERIAL_PROPERTIES[key]
    temperature = _finite_number(temperature_c, "temperature_c")
    if temperature < MIN_TEMPERATURE_C:
        raise ValueError(
            "temperature_c %.1f is below the stated data floor %.1f"
            % (temperature, MIN_TEMPERATURE_C)
        )
    knee = props["knee_temperature_c"]
    service = props["service_temperature_c"]
    if temperature > service:
        raise ValueError(
            "temperature_c %.1f exceeds the qualified service temperature "
            "%.1f for %s" % (temperature, service, key)
        )
    if temperature <= knee:
        return 1.0
    floor = props["floor_factor"]
    span = service - knee
    return 1.0 - (1.0 - floor) * (temperature - knee) / span


def derated_default_cap(material, temperature_c):
    """Material base cap (V/m) after temperature derating."""
    key = categorize_insulating_material(material)
    factor = temperature_derating_factor(key, temperature_c)
    return MATERIAL_PROPERTIES[key]["base_cap_v_per_m"] * factor


def validate_demonstration(record, material, temperature_c, baseline_cap_v_per_m):
    """Validate a qualification record offered to raise the cap.

    The record must name the same insulating material, cover the item
    operating temperature, carry a test evidence reference, and state a
    level strictly above the derated baseline. Returns the demonstrated
    level (V/m). Raises ValueError on any unmet condition.
    """
    if not isinstance(record, dict):
        raise ValueError("demonstration record must be a mapping, got %r" % (record,))
    key = categorize_insulating_material(material)
    rec_material = categorize_insulating_material(record.get("material"))
    if rec_material != key:
        raise ValueError(
            "demonstration names material %s, item uses %s" % (rec_material, key)
        )
    evidence = record.get("evidence_ref")
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError("demonstration record needs a non-blank evidence_ref")
    t_min = _finite_number(record.get("temperature_min_c"), "temperature_min_c")
    t_max = _finite_number(record.get("temperature_max_c"), "temperature_max_c")
    if t_max <= t_min:
        raise ValueError("demonstration temperature_max_c must exceed temperature_min_c")
    temperature = _finite_number(temperature_c, "temperature_c")
    if temperature < t_min or temperature > t_max:
        raise ValueError(
            "demonstration covers %.1f..%.1f C, item runs at %.1f C"
            % (t_min, t_max, temperature)
        )
    level = _finite_number(record.get("demonstrated_cap_v_per_m"), "demonstrated_cap_v_per_m")
    if level <= 0.0:
        raise ValueError("demonstrated_cap_v_per_m must be positive")
    baseline = _finite_number(baseline_cap_v_per_m, "baseline_cap_v_per_m")
    if level <= baseline:
        raise ValueError(
            "demonstrated level %.4g V/m does not exceed the derated default "
            "%.4g V/m; it supports no higher level" % (level, baseline)
        )
    return level


def allowable_field(material, temperature_c, demonstration=None):
    """Return (cap_v_per_m, basis) for an insulating item."""
    baseline = derated_default_cap(material, temperature_c)
    if demonstration is None:
        return baseline, "derated-default"
    level = validate_demonstration(demonstration, material, temperature_c, baseline)
    return level, "application-demonstration"


def field_within_cap(field_v_per_m, cap_v_per_m):
    """True when a computed field is at or below the cap.

    The field is a quotient of floats, so an insulator physically sitting
    on its cap can land a few units in the last place above it; that
    representation error is absorbed here, never by raising the cap.
    """
    if field_v_per_m <= cap_v_per_m:
        return True
    return math.isclose(field_v_per_m, cap_v_per_m, rel_tol=FIELD_REL_TOL)


def assess_dielectric_item(item):
    """Assess one insulating item against clause 9.2.3.

    Returns a mapping with the computed field, the cap and its basis, the
    utilization ratio and a ``findings`` list empty only when compliant.
    """
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping, got %r" % (item,))
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("insulating item needs a non-blank string id")
    material = categorize_insulating_material(item.get("material"))
    temperature = _finite_number(item.get("temperature_c"), "temperature_c")
    field = internal_field(item)
    baseline = derated_default_cap(material, temperature)

    findings = []
    demonstration = item.get("demonstration")
    if demonstration is None:
        cap, basis = baseline, "derated-default"
    else:
        try:
            cap = validate_demonstration(demonstration, material, temperature, baseline)
            basis = "application-demonstration"
        except ValueError as exc:
            cap, basis = baseline, "derated-default"
            findings.append("demonstration rejected: %s" % exc)

    if not field_within_cap(field, cap):
        findings.append(
            "internal field %.4g V/m exceeds the %s cap %.4g V/m"
            % (field, basis, cap)
        )

    return {
        "item_id": item_id.strip(),
        "material": material,
        "geometry": str(item.get("geometry")).strip().lower(),
        "temperature_c": temperature,
        "field_v_per_m": field,
        "cap_v_per_m": cap,
        "cap_basis": basis,
        "derated_default_cap_v_per_m": baseline,
        "utilization": field / cap,
        "margin_v_per_m": cap - field,
        "compliant": not findings,
        "findings": findings,
    }


def assess_dielectric_set(items):
    """Assess a set of insulating items; roll up a campaign verdict."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("items must be a list")
    if not items:
        raise ValueError("insulating item set must not be empty")
    results = []
    seen = set()
    for item in items:
        result = assess_dielectric_item(item)
        if result["item_id"] in seen:
            raise ValueError("item id %s repeats in the set" % result["item_id"])
        seen.add(result["item_id"])
        results.append(result)
    non_compliant = [r["item_id"] for r in results if not r["compliant"]]
    worst = max(results, key=lambda r: r["utilization"])
    return {
        "item_count": len(results),
        "items": results,
        "non_compliant_items": non_compliant,
        "worst_item_id": worst["item_id"],
        "worst_utilization": worst["utilization"],
        "compliant": not non_compliant,
    }


def summarize_assessment(report):
    """Render a one-line summary of an assessment report."""
    if not isinstance(report, dict) or "items" not in report:
        raise ValueError("summary needs an assessment report mapping")
    verdict = "COMPLIANT" if report["compliant"] else "NON-COMPLIANT"
    return "clause 9.2.3 %s: %d item(s), worst utilization %.3f on %s" % (
        verdict,
        report["item_count"],
        report["worst_utilization"],
        report["worst_item_id"],
    )
