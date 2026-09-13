#!/usr/bin/env python3
"""Tether insulation continuity over service life (ECSS-E-ST-20-06C, 10.2.4).

Offline, deterministic, stdlib-only. The module grades the dielectric jacket
of a tether segment: it categorizes observed defects by how far they go
through the wall, erodes the as-built wall over the mission fluence, computes
the dielectric withstand of what remains, and checks the acceptance
measurements (insulation resistance, defect density, pinhole leakage).

Anchor: ECSS-E-ST-20-06C clause 10.2.4 (paraphrased into an implementable
procedure; no verbatim standard text).
"""

import math

# Defect taxonomy: how far the defect goes through the jacket wall.
DEFECT_DEPTH_FAMILY = {
    "pinhole": "through-thickness",
    "crack": "through-thickness",
    "cut-through": "through-thickness",
    "abrasion-scuff": "partial-thickness",
    "delamination": "partial-thickness",
    "thermal-blister": "partial-thickness",
}

# Jacket materials: atomic-oxygen erosion yield (cm^3 per incident atom) and
# dielectric strength (kV/mm).
JACKET_MATERIAL = {
    "polyimide": {"erosion_yield_cm3_per_atom": 3.0e-24, "dielectric_kv_per_mm": 150.0},
    "ptfe": {"erosion_yield_cm3_per_atom": 1.0e-24, "dielectric_kv_per_mm": 60.0},
    "fep": {"erosion_yield_cm3_per_atom": 2.0e-25, "dielectric_kv_per_mm": 80.0},
    "silicone": {"erosion_yield_cm3_per_atom": 5.0e-25, "dielectric_kv_per_mm": 20.0},
}

REL_TOL = 1e-9
ABS_TOL = 1e-12

CM_TO_MM = 10.0


def _positive(name, value):
    """Return value as a finite float strictly greater than zero."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (name, value))
    return out


def _non_negative(name, value):
    """Return value as a finite float that is not negative."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (name, value))
    return out


def within_limit(value, limit):
    """True when value does not exceed limit, absorbing float representation
    error exactly at the boundary; the limit itself is never widened."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_least(value, minimum):
    """True when value meets minimum, absorbing float representation error
    exactly at the boundary; the minimum itself is never lowered."""
    if value >= minimum:
        return True
    return math.isclose(value, minimum, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def categorize_defect(kind):
    """Map a jacket defect type onto through-thickness or partial-thickness."""
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("defect kind must be a non-empty string, got %r" % (kind,))
    key = kind.strip().lower()
    if key not in DEFECT_DEPTH_FAMILY:
        raise ValueError(
            "uncategorized defect kind %r; known kinds: %s"
            % (kind, ", ".join(sorted(DEFECT_DEPTH_FAMILY)))
        )
    return DEFECT_DEPTH_FAMILY[key]


def jacket_properties(material):
    """Return the erosion-yield and dielectric-strength of a jacket material."""
    if not isinstance(material, str) or not material.strip():
        raise ValueError("jacket material must be a non-empty string, got %r" % (material,))
    key = material.strip().lower()
    if key not in JACKET_MATERIAL:
        raise ValueError(
            "uncategorized jacket material %r; known: %s"
            % (material, ", ".join(sorted(JACKET_MATERIAL)))
        )
    return dict(JACKET_MATERIAL[key])


def eroded_depth_mm(fluence_atoms_per_cm2, erosion_yield_cm3_per_atom):
    """Atomic-oxygen recession of the jacket over the mission, in mm."""
    fluence = _non_negative("fluence_atoms_per_cm2", fluence_atoms_per_cm2)
    yield_ = _non_negative("erosion_yield_cm3_per_atom", erosion_yield_cm3_per_atom)
    return fluence * yield_ * CM_TO_MM


def remaining_thickness_mm(as_built_mm, eroded_mm, abrasion_allowance_mm=0.0):
    """End-of-life wall left after erosion and the booked abrasion allowance.

    Clamped at zero: a consumed wall is a breach, reported by the caller, not
    a negative thickness carried into the dielectric model.
    """
    as_built = _positive("as_built_mm", as_built_mm)
    eroded = _non_negative("eroded_mm", eroded_mm)
    abrasion = _non_negative("abrasion_allowance_mm", abrasion_allowance_mm)
    left = as_built - eroded - abrasion
    return left if left > 0.0 else 0.0


def breakdown_voltage_v(thickness_mm, dielectric_kv_per_mm):
    """Dielectric withstand of a wall of the given thickness, in volts."""
    t = _non_negative("thickness_mm", thickness_mm)
    strength = _positive("dielectric_kv_per_mm", dielectric_kv_per_mm)
    return t * strength * 1000.0


def dielectric_margin(applied_v, breakdown_v, required_factor):
    """Withstand divided by the required voltage (applied x factor)."""
    applied = _positive("applied_v", applied_v)
    withstand = _non_negative("breakdown_v", breakdown_v)
    factor = _positive("required_factor", required_factor)
    return withstand / (applied * factor)


def defect_density_per_m(defect_count, segment_length_m):
    """Number of recorded defects per metre of jacketed tether."""
    if not isinstance(defect_count, int) or isinstance(defect_count, bool):
        raise ValueError("defect_count must be an int, got %r" % (defect_count,))
    if defect_count < 0:
        raise ValueError("defect_count must be >= 0, got %r" % (defect_count,))
    length = _positive("segment_length_m", segment_length_m)
    return defect_count / length


def leakage_current_a(exposed_area_mm2, plasma_current_density_a_per_m2):
    """Current collected by bare conductor exposed through the jacket."""
    area_mm2 = _non_negative("exposed_area_mm2", exposed_area_mm2)
    density = _non_negative("plasma_current_density_a_per_m2", plasma_current_density_a_per_m2)
    return area_mm2 * 1e-6 * density


def evaluate_defect(defect, as_built_mm, allowed_depth_fraction):
    """Grade one recorded defect against the jacket wall of its segment."""
    if not isinstance(defect, dict):
        raise ValueError("defect must be a mapping, got %r" % (type(defect).__name__,))
    family = categorize_defect(defect.get("kind"))
    as_built = _positive("as_built_mm", as_built_mm)
    allowed = _positive("allowed_depth_fraction", allowed_depth_fraction)
    if allowed > 1.0:
        raise ValueError("allowed_depth_fraction must be <= 1.0, got %r" % (allowed_depth_fraction,))
    area = _non_negative("area_mm2", defect.get("area_mm2", 0.0))

    findings = []
    depth_fraction = None
    if family == "through-thickness":
        findings.append(
            "%s is a through-thickness continuity break (%.4f mm^2 exposed)"
            % (defect.get("kind"), area)
        )
    else:
        depth = _non_negative("depth_mm", defect.get("depth_mm"))
        if depth > as_built:
            raise ValueError(
                "partial-thickness depth %r exceeds the as-built wall %r" % (depth, as_built)
            )
        depth_fraction = depth / as_built
        if not within_limit(depth_fraction, allowed):
            findings.append(
                "%s consumes %.4f of the wall, above the allowed %.4f"
                % (defect.get("kind"), depth_fraction, allowed)
            )
    return {
        "kind": defect.get("kind"),
        "family": family,
        "exposed_area_mm2": area if family == "through-thickness" else 0.0,
        "depth_fraction": depth_fraction,
        "findings": findings,
        "compliant": not findings,
    }


def assess_insulation_continuity(config):
    """Grade one jacketed tether segment against clause 10.2.4.

    config keys: material, as_built_thickness_mm, segment_length_m,
    applied_voltage_v, required_factor, fluence_atoms_per_cm2, and optionally
    abrasion_allowance_mm, allowed_depth_fraction, defects,
    measured_insulation_resistance_ohm, min_insulation_resistance_ohm,
    max_defect_density_per_m, plasma_current_density_a_per_m2,
    leakage_budget_a.
    """
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping, got %r" % (type(config).__name__,))
    props = jacket_properties(config.get("material"))
    as_built = _positive("as_built_thickness_mm", config.get("as_built_thickness_mm"))
    length = _positive("segment_length_m", config.get("segment_length_m"))
    applied = _positive("applied_voltage_v", config.get("applied_voltage_v"))
    factor = _positive("required_factor", config.get("required_factor"))
    allowed_fraction = config.get("allowed_depth_fraction", 0.25)

    defects = config.get("defects", [])
    if not isinstance(defects, list):
        raise ValueError("config['defects'] must be a list when present")
    defect_reports = [evaluate_defect(d, as_built, allowed_fraction) for d in defects]

    eroded = eroded_depth_mm(
        config.get("fluence_atoms_per_cm2", 0.0), props["erosion_yield_cm3_per_atom"]
    )
    remaining = remaining_thickness_mm(
        as_built, eroded, config.get("abrasion_allowance_mm", 0.0)
    )
    withstand = breakdown_voltage_v(remaining, props["dielectric_kv_per_mm"])
    margin = dielectric_margin(applied, withstand, factor)

    findings = [f for rep in defect_reports for f in rep["findings"]]
    if remaining <= 0.0:
        findings.append("end-of-life wall fully consumed: insulation breach")
    if not at_least(margin, 1.0):
        findings.append("dielectric margin %.4f is below 1.0 at end of life" % margin)

    density = defect_density_per_m(len(defect_reports), length)
    max_density = config.get("max_defect_density_per_m")
    if max_density is not None:
        limit = _positive("max_defect_density_per_m", max_density)
        if not within_limit(density, limit):
            findings.append(
                "defect-density %.4f /m exceeds the limit %.4f /m" % (density, limit)
            )

    exposed = sum(rep["exposed_area_mm2"] for rep in defect_reports)
    leakage = leakage_current_a(exposed, config.get("plasma_current_density_a_per_m2", 0.0))
    budget = config.get("leakage_budget_a")
    if budget is not None:
        allowed_leak = _positive("leakage_budget_a", budget)
        if not within_limit(leakage, allowed_leak):
            findings.append(
                "pinhole leakage-current %.6g A exceeds budget %.6g A" % (leakage, allowed_leak)
            )

    minimum_ir = config.get("min_insulation_resistance_ohm")
    measured_ir = config.get("measured_insulation_resistance_ohm")
    if minimum_ir is None:
        findings.append("no minimum insulation-resistance on record for this segment")
    elif measured_ir is None:
        findings.append("no measured insulation-resistance on record for this segment")
    else:
        minimum = _positive("min_insulation_resistance_ohm", minimum_ir)
        measured = _non_negative("measured_insulation_resistance_ohm", measured_ir)
        if not at_least(measured, minimum):
            findings.append(
                "insulation-resistance %.6g ohm is below the minimum %.6g ohm"
                % (measured, minimum)
            )

    return {
        "defects": defect_reports,
        "eroded_depth_mm": eroded,
        "remaining_thickness_mm": remaining,
        "breakdown_voltage_v": withstand,
        "dielectric_margin": margin,
        "defect_density_per_m": density,
        "exposed_area_mm2": exposed,
        "leakage_current_a": leakage,
        "findings": findings,
        "compliant": not findings,
    }
