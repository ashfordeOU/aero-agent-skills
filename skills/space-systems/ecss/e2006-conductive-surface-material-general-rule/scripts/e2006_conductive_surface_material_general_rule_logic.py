#!/usr/bin/env python3
"""Conductive outer-surface material general rule (ECSS-E-ST-20-06C, 6.3.3.2).

Deterministic, offline, standard-library-only implementation of the general
material rule for spacecraft outer surfaces: an exposed material has to bleed
its collected charge away well enough that the potential it reaches stays
under the permitted ceiling.

The module converts a bulk resistivity and a coating thickness into the two
drain paths available to an exposed surface (through the thickness to a
grounded backing, or laterally to a grounded edge), computes the potential
each path leaves on the surface for a worst-case charging current density,
picks the governing path, and grades the material against the ceiling, the
maximum allowable resistivity and the charge-decay time constant.

Paraphrased procedure only; the standard is cited as an anchor and no
standard text is reproduced.
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Physical constants and named limits
# ---------------------------------------------------------------------------

#: Permittivity of free space (F/m).
VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12

#: Highest surface potential an exposed material may reach relative to
#: structure before the general rule is violated (volts).
DEFAULT_SURFACE_POTENTIAL_CEILING_V = 100.0

#: Worst-case net charging current density collected by an exposed surface in
#: a severe environment (A/m^2).
DEFAULT_CHARGING_CURRENT_DENSITY_A_PER_M2 = 1.0e-6

#: Longest acceptable charge-decay time constant for an outer material (s).
DEFAULT_DECAY_TIME_LIMIT_S = 3600.0

#: Shape factor of a uniformly charged sheet drained at its grounded edge.
GEOMETRY_FACTOR_GROUNDED_EDGE = 0.5

#: Tolerances that absorb floating-point representation error at an exactly
#: compliant limit. They never widen the engineering limit itself.
LIMIT_REL_TOL = 1e-9
LIMIT_ABS_TOL = 1e-15

# ---------------------------------------------------------------------------
# Conduction regimes (bulk resistivity, ohm-metre)
# ---------------------------------------------------------------------------

METALLIC_MAX_OHM_M = 1.0e-2
STATIC_DISSIPATIVE_MAX_OHM_M = 1.0e5
PARTIALLY_DISSIPATIVE_MAX_OHM_M = 1.0e9

REGIME_METALLIC = "metallic-conductor"
REGIME_STATIC_DISSIPATIVE = "static-dissipative"
REGIME_PARTIALLY_DISSIPATIVE = "partially-dissipative"
REGIME_INSULATING = "insulating-dielectric"

DRAIN_PATHS = (
    "through-thickness-to-backing",
    "lateral-to-grounded-edge",
    "both-paths-available",
)

FINDING_ABOVE_CEILING = "surface-potential-above-ceiling"
FINDING_SLOW_DECAY = "charge-decay-time-above-limit"
FINDING_NOT_BONDED = "outer-material-not-bonded-to-structure"


def _within_limit(value, limit):
    """True when value does not exceed limit, absorbing representation error."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=LIMIT_REL_TOL, abs_tol=LIMIT_ABS_TOL)


def _require_positive(value, field):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (field, value))
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite, got %r" % (field, value))
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (field, value))
    return number


def _require_non_negative(value, field):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (field, value))
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite, got %r" % (field, value))
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (field, value))
    return number


def sheet_resistance_from_bulk(bulk_resistivity_ohm_m, thickness_m):
    """Sheet resistance of a uniform layer: rho / t (ohm per square)."""
    rho = _require_positive(bulk_resistivity_ohm_m, "bulk_resistivity_ohm_m")
    thickness = _require_positive(thickness_m, "thickness_m")
    return rho / thickness


def through_thickness_potential(
    current_density_a_per_m2, bulk_resistivity_ohm_m, thickness_m
):
    """Ohmic drop across the layer to a grounded backing: J * rho * t (volts)."""
    current = _require_non_negative(
        current_density_a_per_m2, "current_density_a_per_m2"
    )
    rho = _require_positive(bulk_resistivity_ohm_m, "bulk_resistivity_ohm_m")
    thickness = _require_positive(thickness_m, "thickness_m")
    return current * rho * thickness


def lateral_potential(
    current_density_a_per_m2,
    sheet_resistance_ohm_per_square,
    characteristic_length_m,
    geometry_factor=GEOMETRY_FACTOR_GROUNDED_EDGE,
):
    """Potential rise of a sheet drained at its grounded edge.

    V = k * J * R_sheet * L^2, with L the distance from the furthest point of
    the surface to the nearest grounded edge.
    """
    current = _require_non_negative(
        current_density_a_per_m2, "current_density_a_per_m2"
    )
    sheet = _require_positive(
        sheet_resistance_ohm_per_square, "sheet_resistance_ohm_per_square"
    )
    length = _require_positive(characteristic_length_m, "characteristic_length_m")
    factor = _require_positive(geometry_factor, "geometry_factor")
    return factor * current * sheet * length * length


def max_allowable_bulk_resistivity(
    ceiling_v, current_density_a_per_m2, thickness_m
):
    """Highest bulk resistivity that still satisfies the ceiling (ohm-metre)."""
    ceiling = _require_positive(ceiling_v, "ceiling_v")
    current = _require_positive(current_density_a_per_m2, "current_density_a_per_m2")
    thickness = _require_positive(thickness_m, "thickness_m")
    return ceiling / (current * thickness)


def charge_decay_time_constant(bulk_resistivity_ohm_m, relative_permittivity):
    """Dielectric relaxation time: rho * eps0 * eps_r (seconds)."""
    rho = _require_positive(bulk_resistivity_ohm_m, "bulk_resistivity_ohm_m")
    eps_r = _require_positive(relative_permittivity, "relative_permittivity")
    if eps_r < 1.0:
        raise ValueError(
            "relative_permittivity must be at least 1.0, got %r" % (relative_permittivity,)
        )
    return rho * VACUUM_PERMITTIVITY_F_PER_M * eps_r


def categorize_conduction_regime(bulk_resistivity_ohm_m):
    """Bucket a bulk resistivity into its conduction regime."""
    rho = _require_positive(bulk_resistivity_ohm_m, "bulk_resistivity_ohm_m")
    if _within_limit(rho, METALLIC_MAX_OHM_M):
        return REGIME_METALLIC
    if _within_limit(rho, STATIC_DISSIPATIVE_MAX_OHM_M):
        return REGIME_STATIC_DISSIPATIVE
    if _within_limit(rho, PARTIALLY_DISSIPATIVE_MAX_OHM_M):
        return REGIME_PARTIALLY_DISSIPATIVE
    return REGIME_INSULATING


def normalize_material(record):
    """Validate one outer-surface material record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("material record must be a mapping, got %r" % (type(record),))
    surface_id = record.get("surface_id")
    if not isinstance(surface_id, str) or not surface_id.strip():
        raise ValueError("surface_id must be a non-empty string")
    material_name = record.get("material_name")
    if not isinstance(material_name, str) or not material_name.strip():
        raise ValueError("material_name must be a non-empty string for %s" % surface_id)
    drain_path = record.get("drain_path")
    if drain_path not in DRAIN_PATHS:
        raise ValueError(
            "unknown drain_path %r for %s; expected one of %s"
            % (drain_path, surface_id, ", ".join(DRAIN_PATHS))
        )
    grounded = record.get("grounded_to_structure", False)
    if not isinstance(grounded, bool):
        raise ValueError("grounded_to_structure must be a boolean for %s" % surface_id)
    eps_r = _require_positive(
        record.get("relative_permittivity", 1.0), "relative_permittivity"
    )
    if eps_r < 1.0:
        raise ValueError("relative_permittivity must be at least 1.0 for %s" % surface_id)
    return {
        "surface_id": surface_id.strip(),
        "material_name": material_name.strip(),
        "drain_path": drain_path,
        "grounded_to_structure": grounded,
        "bulk_resistivity_ohm_m": _require_positive(
            record.get("bulk_resistivity_ohm_m"), "bulk_resistivity_ohm_m"
        ),
        "thickness_m": _require_positive(record.get("thickness_m"), "thickness_m"),
        "characteristic_length_m": _require_positive(
            record.get("characteristic_length_m", 1.0), "characteristic_length_m"
        ),
        "relative_permittivity": eps_r,
    }


def evaluate_surface_material(
    record,
    ceiling_v=DEFAULT_SURFACE_POTENTIAL_CEILING_V,
    current_density_a_per_m2=DEFAULT_CHARGING_CURRENT_DENSITY_A_PER_M2,
    decay_limit_s=DEFAULT_DECAY_TIME_LIMIT_S,
):
    """Grade one outer-surface material against the general conduction rule."""
    material = normalize_material(record)
    ceiling = _require_positive(ceiling_v, "ceiling_v")
    current = _require_non_negative(
        current_density_a_per_m2, "current_density_a_per_m2"
    )
    decay_limit = _require_positive(decay_limit_s, "decay_limit_s")

    rho = material["bulk_resistivity_ohm_m"]
    thickness = material["thickness_m"]
    sheet = sheet_resistance_from_bulk(rho, thickness)
    v_normal = through_thickness_potential(current, rho, thickness)
    v_lateral = lateral_potential(
        current, sheet, material["characteristic_length_m"]
    )

    if material["drain_path"] == "through-thickness-to-backing":
        governing_path = "through-thickness-to-backing"
        governing_v = v_normal
    elif material["drain_path"] == "lateral-to-grounded-edge":
        governing_path = "lateral-to-grounded-edge"
        governing_v = v_lateral
    else:
        # Both drains exist in parallel: charge leaves by the easier route, so
        # the lower of the two potentials governs.
        if v_normal <= v_lateral:
            governing_path = "through-thickness-to-backing"
            governing_v = v_normal
        else:
            governing_path = "lateral-to-grounded-edge"
            governing_v = v_lateral

    tau = charge_decay_time_constant(rho, material["relative_permittivity"])
    findings = []
    if not _within_limit(governing_v, ceiling):
        findings.append(FINDING_ABOVE_CEILING)
    if not _within_limit(tau, decay_limit):
        findings.append(FINDING_SLOW_DECAY)
    if not material["grounded_to_structure"]:
        findings.append(FINDING_NOT_BONDED)

    return {
        "surface_id": material["surface_id"],
        "material_name": material["material_name"],
        "conduction_regime": categorize_conduction_regime(rho),
        "sheet_resistance_ohm_per_square": sheet,
        "through_thickness_potential_v": v_normal,
        "lateral_potential_v": v_lateral,
        "governing_drain_path": governing_path,
        "governing_potential_v": governing_v,
        "ceiling_v": ceiling,
        "potential_margin_v": ceiling - governing_v,
        "max_allowable_bulk_resistivity_ohm_m": max_allowable_bulk_resistivity(
            ceiling, current, thickness
        )
        if current > 0.0
        else float("inf"),
        "charge_decay_time_constant_s": tau,
        "decay_limit_s": decay_limit,
        "findings": findings,
        "compliant": len(findings) == 0,
        "anchor": "ECSS-E-ST-20-06C 6.3.3.2",
    }


def assess_outer_surface_inventory(
    records,
    ceiling_v=DEFAULT_SURFACE_POTENTIAL_CEILING_V,
    current_density_a_per_m2=DEFAULT_CHARGING_CURRENT_DENSITY_A_PER_M2,
    decay_limit_s=DEFAULT_DECAY_TIME_LIMIT_S,
):
    """Grade a whole outer-surface material inventory."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple")
    if len(records) == 0:
        raise ValueError("records must not be empty")
    results = []
    seen = set()
    for record in records:
        result = evaluate_surface_material(
            record,
            ceiling_v=ceiling_v,
            current_density_a_per_m2=current_density_a_per_m2,
            decay_limit_s=decay_limit_s,
        )
        if result["surface_id"] in seen:
            raise ValueError("duplicate surface_id %r" % result["surface_id"])
        seen.add(result["surface_id"])
        results.append(result)
    worst = max(results, key=lambda r: r["governing_potential_v"])
    return {
        "results": results,
        "compliant_count": sum(1 for r in results if r["compliant"]),
        "non_compliant": [r["surface_id"] for r in results if not r["compliant"]],
        "worst_surface_id": worst["surface_id"],
        "worst_potential_v": worst["governing_potential_v"],
        "compliant": all(r["compliant"] for r in results),
    }


def format_material_report(assessment):
    """Render a deterministic plain-text outer-surface material report."""
    if not isinstance(assessment, dict) or "results" not in assessment:
        raise ValueError("assessment must come from assess_outer_surface_inventory")
    lines = ["ECSS-E-ST-20-06C 6.3.3.2 conductive outer-surface material rule"]
    for result in assessment["results"]:
        lines.append(
            "%s (%s) %s V via %s [%s]"
            % (
                result["surface_id"],
                result["material_name"],
                ("%.3g" % result["governing_potential_v"]),
                result["governing_drain_path"],
                result["conduction_regime"],
            )
        )
        for finding in result["findings"]:
            lines.append("    finding: %s" % finding)
    lines.append(
        "worst=%s at %.3g V compliant=%s"
        % (
            assessment["worst_surface_id"],
            assessment["worst_potential_v"],
            str(assessment["compliant"]).lower(),
        )
    )
    return "\n".join(lines)
