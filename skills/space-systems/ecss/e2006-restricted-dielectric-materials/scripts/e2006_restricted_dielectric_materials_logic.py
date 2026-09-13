#!/usr/bin/env python3
"""ECSS-E-ST-20-06C clause 6.3.3.6 -- restricted dielectric materials.

Deterministic, offline, stdlib-only support for the rule that certain highly
insulating materials are kept off spacecraft external surfaces unless a
three-dimensional charging simulation shows the installed item is safe.

The module answers three questions in order:

1. is the item restricted at all -- either because its material family sits in
   the restricted-dielectric register, or because its measured bulk or surface
   resistivity is above the threshold that makes any unregistered material
   restricted in its own right, with a negligible exposed area as the only
   exemption;
2. does a waiver exist and is it the right kind of waiver -- a
   three-dimensional charging simulation, not a one- or two-dimensional
   reduction, covering the item geometry, bounding the worst-case environment
   and including the eclipse-entry case;
3. does the waiver actually clear the item -- the predicted differential
   potential between the dielectric surface and structure must stay at or
   below the discharge-onset threshold.

Potentials are in volts, resistivities in ohm-metre (bulk) and ohm per square
(surface), areas in square metres. Thresholds are module constants so a
project can re-baseline them without editing the procedure.
"""

import math

# Material families kept off external surfaces unless waived, with the nominal
# resistivities that put them there.
RESTRICTED_REGISTER = {
    "uncoated-polyimide-film": {
        "bulk_resistivity_ohm_m": 1.0e16,
        "surface_resistivity_ohm_sq": 1.0e16,
    },
    "uncoated-fused-silica-cover": {
        "bulk_resistivity_ohm_m": 1.0e16,
        "surface_resistivity_ohm_sq": 1.0e15,
    },
    "polytetrafluoroethylene-sheet": {
        "bulk_resistivity_ohm_m": 1.0e18,
        "surface_resistivity_ohm_sq": 1.0e17,
    },
    "uncoated-glass-fibre-laminate": {
        "bulk_resistivity_ohm_m": 1.0e14,
        "surface_resistivity_ohm_sq": 1.0e14,
    },
    "unconditioned-silicone-adhesive": {
        "bulk_resistivity_ohm_m": 1.0e13,
        "surface_resistivity_ohm_sq": 1.0e14,
    },
}

# An unregistered material becomes restricted once it is this insulating.
RESTRICTED_BULK_RESISTIVITY_OHM_M = 1.0e12
RESTRICTED_SURFACE_RESISTIVITY_OHM_SQ = 1.0e13

# Exposed area below which a restricted material is not a charge collector
# worth waiving; one square centimetre in the module default.
NEGLIGIBLE_AREA_M2 = 1.0e-4

# Differential potential between a dielectric surface and structure at which
# an electrostatic discharge is credible.
DISCHARGE_ONSET_V = 400.0

# Absolute tolerance in volts absorbing the representation error of a
# difference of potentials, so a prediction exactly on the onset threshold is
# not read as over it.
POTENTIAL_TOLERANCE_V = 1.0e-6

EXPOSURES = ("external", "internal")
DIMENSIONALITIES = ("one-dimensional", "two-dimensional", "three-dimensional")
REQUIRED_DIMENSIONALITY = "three-dimensional"


def _text(record, key, label):
    """Return a non-empty stripped string field."""
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s needs a non-empty '%s'" % (label, key))
    return value.strip()


def _boolean(record, key, label):
    """Return a boolean field, rejecting truthy stand-ins such as 'yes'."""
    if key not in record:
        raise ValueError("%s missing required '%s'" % (label, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s '%s' must be a boolean, got %r" % (label, key, value))
    return value


def _finite(record, key, label, minimum=None, strict=False, default=None):
    """Return a finite float field, enforcing an optional lower bound."""
    if key not in record or record[key] is None:
        if default is None:
            raise ValueError("%s missing required '%s'" % (label, key))
        return float(default)
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s '%s' must be numeric, got %r" % (label, key, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s '%s' must be finite, got %r" % (label, key, value))
    if minimum is not None:
        if strict and value <= minimum:
            raise ValueError("%s '%s' must be > %g, got %r" % (label, key, minimum, value))
        if not strict and value < minimum:
            raise ValueError("%s '%s' must be >= %g, got %r" % (label, key, minimum, value))
    return value


def registered_restriction(material):
    """Return the register entry for a material family, or None."""
    if not isinstance(material, str) or not material.strip():
        raise ValueError("material must be a non-empty name")
    entry = RESTRICTED_REGISTER.get(material.strip().lower())
    if entry is None:
        return None
    return dict(entry, material=material.strip().lower())


def normalize_item(item):
    """Normalize one external-surface item record."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    name = _text(item, "name", "item")
    label = "item '%s'" % name
    material = _text(item, "material", label).lower()
    exposure = item.get("exposure", "external")
    if exposure not in EXPOSURES:
        raise ValueError(
            "%s exposure %r is not one of %s" % (label, exposure, list(EXPOSURES))
        )
    area = _finite(item, "exposed_area_m2", label, minimum=0.0, default=0.0)
    if exposure == "internal" and area > 0.0:
        raise ValueError("%s is internal but declares an exposed area" % label)
    registered = registered_restriction(material)
    bulk_default = registered["bulk_resistivity_ohm_m"] if registered else 0.0
    surface_default = registered["surface_resistivity_ohm_sq"] if registered else 0.0
    bulk = _finite(item, "bulk_resistivity_ohm_m", label, minimum=0.0,
                   default=bulk_default)
    surface = _finite(item, "surface_resistivity_ohm_sq", label, minimum=0.0,
                      default=surface_default)
    return {
        "name": name,
        "material": material,
        "exposure": exposure,
        "exposed_area_m2": area,
        "bulk_resistivity_ohm_m": bulk,
        "surface_resistivity_ohm_sq": surface,
        "registered": registered is not None,
    }


def restriction_reasons(normalized):
    """Return why this item is a restricted external dielectric, if it is."""
    reasons = []
    if normalized["exposure"] != "external":
        return reasons
    if normalized["exposed_area_m2"] <= NEGLIGIBLE_AREA_M2:
        return reasons
    if normalized["registered"]:
        reasons.append(
            "material '%s' sits in the restricted-dielectric register"
            % normalized["material"]
        )
    if normalized["bulk_resistivity_ohm_m"] > RESTRICTED_BULK_RESISTIVITY_OHM_M:
        reasons.append(
            "bulk resistivity %.3g ohm-metre is above the %.3g ohm-metre threshold"
            % (normalized["bulk_resistivity_ohm_m"], RESTRICTED_BULK_RESISTIVITY_OHM_M)
        )
    if normalized["surface_resistivity_ohm_sq"] > RESTRICTED_SURFACE_RESISTIVITY_OHM_SQ:
        reasons.append(
            "surface resistivity %.3g ohm per square is above the %.3g ohm per "
            "square threshold"
            % (
                normalized["surface_resistivity_ohm_sq"],
                RESTRICTED_SURFACE_RESISTIVITY_OHM_SQ,
            )
        )
    return reasons


def is_restricted_dielectric(item):
    """True when the item is a restricted dielectric on an external surface."""
    return bool(restriction_reasons(normalize_item(item)))


def differential_potential_v(surface_potential_v, structure_potential_v):
    """Magnitude of the surface-to-structure potential difference."""
    values = {"surface": surface_potential_v, "structure": structure_potential_v}
    surface = _finite(values, "surface", "potential")
    structure = _finite(values, "structure", "potential")
    return abs(surface - structure)


def within_discharge_onset(differential_v, onset_v=None):
    """True when a differential potential stays at or below the onset."""
    limit = DISCHARGE_ONSET_V if onset_v is None else _finite(
        {"onset": onset_v}, "onset", "onset", minimum=0.0, strict=True
    )
    value = _finite({"d": differential_v}, "d", "differential potential", minimum=0.0)
    return value <= limit or math.isclose(
        value, limit, rel_tol=0.0, abs_tol=POTENTIAL_TOLERANCE_V
    )


def validate_charging_waiver(waiver):
    """Normalize a charging-simulation waiver record, rejecting unknown fields."""
    if not isinstance(waiver, dict):
        raise ValueError("waiver must be a mapping")
    dimensionality = waiver.get("dimensionality")
    if dimensionality not in DIMENSIONALITIES:
        raise ValueError(
            "waiver dimensionality %r is not one of %s"
            % (dimensionality, list(DIMENSIONALITIES))
        )
    modelled = waiver.get("items_modelled", [])
    if not isinstance(modelled, (list, tuple)):
        raise ValueError("waiver 'items_modelled' must be a list")
    names = []
    for entry in modelled:
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError("waiver 'items_modelled' entries must be names")
        names.append(entry.strip())
    environment = _text(waiver, "environment_case", "waiver")
    bounds = _boolean(waiver, "environment_bounds_worst_case", "waiver")
    eclipse = _boolean(waiver, "eclipse_entry_covered", "waiver")
    surface_v = _finite(waiver, "surface_potential_v", "waiver")
    structure_v = _finite(waiver, "structure_potential_v", "waiver", default=0.0)
    onset = waiver.get("discharge_onset_v")
    onset_v = DISCHARGE_ONSET_V if onset is None else _finite(
        waiver, "discharge_onset_v", "waiver", minimum=0.0, strict=True
    )
    return {
        "dimensionality": dimensionality,
        "items_modelled": names,
        "environment_case": environment,
        "environment_bounds_worst_case": bounds,
        "eclipse_entry_covered": eclipse,
        "surface_potential_v": surface_v,
        "structure_potential_v": structure_v,
        "differential_potential_v": differential_potential_v(surface_v, structure_v),
        "discharge_onset_v": onset_v,
    }


def waiver_findings(normalized_waiver, normalized_item):
    """Return the open findings against a waiver for one restricted item."""
    if normalized_waiver is None:
        return [
            "item '%s' is a restricted external dielectric with no "
            "three-dimensional charging-simulation waiver" % normalized_item["name"]
        ]
    findings = []
    if normalized_waiver["dimensionality"] != REQUIRED_DIMENSIONALITY:
        findings.append(
            "waiver is a %s reduction; the clause is cleared only by a %s "
            "simulation"
            % (normalized_waiver["dimensionality"], REQUIRED_DIMENSIONALITY)
        )
    if normalized_item["name"] not in normalized_waiver["items_modelled"]:
        findings.append(
            "item '%s' is not part of the modelled geometry" % normalized_item["name"]
        )
    if not normalized_waiver["environment_bounds_worst_case"]:
        findings.append(
            "environment case '%s' does not bound the worst case"
            % normalized_waiver["environment_case"]
        )
    if not normalized_waiver["eclipse_entry_covered"]:
        findings.append("waiver does not cover the eclipse-entry case")
    if not within_discharge_onset(
        normalized_waiver["differential_potential_v"],
        normalized_waiver["discharge_onset_v"],
    ):
        findings.append(
            "predicted differential potential %.3f V exceeds the %.3f V "
            "discharge-onset threshold"
            % (
                normalized_waiver["differential_potential_v"],
                normalized_waiver["discharge_onset_v"],
            )
        )
    return findings


def evaluate_item(item, waiver=None):
    """Decide whether one item may be carried on the external surface."""
    normalized = normalize_item(item)
    reasons = restriction_reasons(normalized)
    normalized_waiver = (
        validate_charging_waiver(waiver) if waiver is not None else None
    )
    if not reasons:
        return {
            "item": normalized,
            "restricted": False,
            "restriction_reasons": [],
            "waiver": normalized_waiver,
            "findings": [],
            "permitted": True,
        }
    findings = waiver_findings(normalized_waiver, normalized)
    return {
        "item": normalized,
        "restricted": True,
        "restriction_reasons": reasons,
        "waiver": normalized_waiver,
        "findings": findings,
        "permitted": not findings,
    }


def evaluate_external_dielectrics(items):
    """Run the clause 6.3.3.6 evaluation across an external-surface inventory."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("items must be a list")
    if len(items) == 0:
        raise ValueError("inventory needs at least one item")
    results = []
    seen = set()
    for entry in items:
        if not isinstance(entry, dict):
            raise ValueError("inventory entries must be mappings")
        waiver = entry.get("waiver")
        result = evaluate_item(entry, waiver)
        name = result["item"]["name"]
        if name in seen:
            raise ValueError("duplicate item name '%s'" % name)
        seen.add(name)
        results.append(result)
    restricted = [r for r in results if r["restricted"]]
    barred = [r for r in results if not r["permitted"]]
    return {
        "items": results,
        "restricted_count": len(restricted),
        "barred_items": [r["item"]["name"] for r in barred],
        "findings": [f for r in barred for f in r["findings"]],
        "compliant": not barred,
    }
