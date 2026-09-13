#!/usr/bin/env python3
"""Maximum permitted surface potential (ECSS-E-ST-20-06C 6.2.1).

Deterministic, offline, stdlib-only support logic for the two ceilings that
clause 6.2.1 puts on an external spacecraft surface:

* a critical differential-surface-potential ceiling, set by the material
  family -- above it a surface discharge initiates along the dielectric face
  and across the triple-point, largely independently of thickness;
* a dielectric-breakdown-field ceiling on the field inside the layer, which
  becomes a potential ceiling once multiplied by the layer thickness.

The permitted potential is the lower of the two, divided by the mission
safety-factor and then lowered further by any mission override. Which of the
two ceilings binds is reported, because it decides whether thickening the
layer buys margin at all.

Comparisons at a ceiling use a relative tolerance so a surface sitting
exactly on the limit reads compliant; the limit itself is never widened.
"""

import math

__all__ = [
    "MATERIAL_CEILINGS",
    "BINDING_SOURCES",
    "VERDICTS",
    "MARGINAL_RATIO",
    "REL_TOL",
    "material_ceilings",
    "internal_field",
    "potential_at_field",
    "minimum_thickness_for_potential",
    "permitted_surface_potential",
    "potential_margin",
    "within_ceiling",
    "discharge_onset_verdict",
    "evaluate_surface",
    "evaluate_surface_set",
]

# Per-material-family ceilings used by the clause-6.2.1 screening.
#   absolute_potential_ceiling_v      - spacecraft-frame potential ceiling
#   differential_potential_ceiling_v  - critical potential to a neighbour
#   breakdown_field_v_per_m           - bulk dielectric field ceiling
MATERIAL_CEILINGS = {
    "polyimide-film": {
        "absolute_potential_ceiling_v": 10000.0,
        "differential_potential_ceiling_v": 500.0,
        "breakdown_field_v_per_m": 1.0e7,
    },
    "ptfe-film": {
        "absolute_potential_ceiling_v": 10000.0,
        "differential_potential_ceiling_v": 400.0,
        "breakdown_field_v_per_m": 6.0e6,
    },
    "fused-silica-reflector": {
        "absolute_potential_ceiling_v": 12000.0,
        "differential_potential_ceiling_v": 1000.0,
        "breakdown_field_v_per_m": 2.0e7,
    },
    "borosilicate-coverglass": {
        "absolute_potential_ceiling_v": 12000.0,
        "differential_potential_ceiling_v": 800.0,
        "breakdown_field_v_per_m": 1.5e7,
    },
    "anodized-aluminium": {
        "absolute_potential_ceiling_v": 8000.0,
        "differential_potential_ceiling_v": 300.0,
        "breakdown_field_v_per_m": 5.0e6,
    },
    "conductive-black-paint": {
        "absolute_potential_ceiling_v": 8000.0,
        "differential_potential_ceiling_v": 200.0,
        "breakdown_field_v_per_m": 3.0e6,
    },
}

BINDING_SOURCES = (
    "dielectric-breakdown-field",
    "critical-differential-potential",
    "mission-override",
)

VERDICTS = ("compliant", "marginal", "discharge-onset")

# A predicted potential above this fraction of the permitted ceiling is
# reported as marginal rather than comfortably compliant.
MARGINAL_RATIO = 0.8

REL_TOL = 1.0e-9


# --- validation helpers ---------------------------------------------------


def _real(value, label):
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    out = _real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, out))
    return out


def _non_negative(value, label):
    out = _real(value, label)
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (label, out))
    return out


# --- primitives -----------------------------------------------------------


def material_ceilings(family):
    """Return a copy of the three ceilings for one material family."""
    if not isinstance(family, str) or not family.strip():
        raise ValueError("material family must be a non-empty string, got %r" % (family,))
    key = family.strip().lower()
    if key not in MATERIAL_CEILINGS:
        raise ValueError(
            "unknown material family %r; known: %s"
            % (family, ", ".join(sorted(MATERIAL_CEILINGS)))
        )
    return dict(MATERIAL_CEILINGS[key])


def internal_field(potential_v, thickness_m):
    """Field inside the layer produced by a potential across it (V/m)."""
    potential = _non_negative(potential_v, "potential_v")
    thickness = _positive(thickness_m, "thickness_m")
    return potential / thickness


def potential_at_field(field_v_per_m, thickness_m):
    """Potential a given field sustains across the layer thickness (V)."""
    field = _positive(field_v_per_m, "field_v_per_m")
    thickness = _positive(thickness_m, "thickness_m")
    return field * thickness


def minimum_thickness_for_potential(potential_v, field_v_per_m, safety_factor=1.0):
    """Least thickness (m) whose field-derived ceiling covers a potential."""
    potential = _positive(potential_v, "potential_v")
    field = _positive(field_v_per_m, "field_v_per_m")
    factor = _positive(safety_factor, "safety_factor")
    if factor < 1.0:
        raise ValueError("safety_factor must be >= 1.0, got %r" % (factor,))
    return potential * factor / field


def permitted_surface_potential(
    family, thickness_m, safety_factor=1.0, mission_override_v=None
):
    """Maximum permitted surface potential and the ceiling that binds it."""
    ceilings = material_ceilings(family)
    thickness = _positive(thickness_m, "thickness_m")
    factor = _positive(safety_factor, "safety_factor")
    if factor < 1.0:
        raise ValueError("safety_factor must be >= 1.0, got %r" % (factor,))

    field_derived_v = potential_at_field(ceilings["breakdown_field_v_per_m"], thickness)
    critical_v = ceilings["differential_potential_ceiling_v"]

    if field_derived_v <= critical_v:
        binding = "dielectric-breakdown-field"
        raw = field_derived_v
    else:
        binding = "critical-differential-potential"
        raw = critical_v

    permitted = raw / factor

    override_applied = False
    if mission_override_v is not None:
        override = _positive(mission_override_v, "mission_override_v")
        # An override can only tighten the ceiling, never raise it.
        if override < permitted:
            permitted = override
            binding = "mission-override"
            override_applied = True

    return {
        "family": family.strip().lower(),
        "thickness_m": thickness,
        "field_derived_potential_v": field_derived_v,
        "critical_potential_v": critical_v,
        "absolute_potential_ceiling_v": ceilings["absolute_potential_ceiling_v"],
        "breakdown_field_v_per_m": ceilings["breakdown_field_v_per_m"],
        "safety_factor": factor,
        "override_applied": override_applied,
        "binding_source": binding,
        "permitted_potential_v": permitted,
        "thickening_buys_margin": binding == "dielectric-breakdown-field",
    }


def within_ceiling(value, ceiling, rel_tol=REL_TOL):
    """True when value <= ceiling, absorbing representation error at equality."""
    v = _real(value, "value")
    c = _real(ceiling, "ceiling")
    if v <= c:
        return True
    return math.isclose(v, c, rel_tol=rel_tol, abs_tol=0.0)


def potential_margin(permitted_v, predicted_v):
    """Fraction of the permitted ceiling still unused (negative = exceeded)."""
    permitted = _positive(permitted_v, "permitted_v")
    predicted = _non_negative(predicted_v, "predicted_v")
    return (permitted - predicted) / permitted


def discharge_onset_verdict(permitted_v, predicted_v):
    """Grade a predicted potential against the permitted ceiling."""
    permitted = _positive(permitted_v, "permitted_v")
    predicted = _non_negative(predicted_v, "predicted_v")
    if not within_ceiling(predicted, permitted):
        return "discharge-onset"
    ratio = predicted / permitted
    if ratio > MARGINAL_RATIO and not math.isclose(
        ratio, MARGINAL_RATIO, rel_tol=REL_TOL, abs_tol=0.0
    ):
        return "marginal"
    return "compliant"


# --- surface and set evaluation -------------------------------------------


def evaluate_surface(surface):
    """Full clause-6.2.1 verdict for one external surface record."""
    if not isinstance(surface, dict):
        raise ValueError("surface must be a mapping, got %r" % (type(surface).__name__,))
    name = surface.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("surface needs a non-empty 'name'")
    if surface.get("predicted_potential_v") is None:
        raise ValueError(
            "surface %r has no predicted_potential_v; an ungraded surface is an "
            "open finding, not a pass" % (name,)
        )

    ceiling = permitted_surface_potential(
        surface.get("material_family"),
        surface.get("thickness_m"),
        surface.get("safety_factor", 1.0),
        surface.get("mission_override_v"),
    )
    predicted = _non_negative(surface["predicted_potential_v"], "predicted_potential_v")
    field = internal_field(predicted, ceiling["thickness_m"])

    potential_ok = within_ceiling(predicted, ceiling["permitted_potential_v"])
    field_ok = within_ceiling(field, ceiling["breakdown_field_v_per_m"])
    verdict = discharge_onset_verdict(ceiling["permitted_potential_v"], predicted)

    findings = []
    if not potential_ok:
        findings.append(
            "%s: predicted potential %.1f V above permitted %.1f V (bound by %s)"
            % (name, predicted, ceiling["permitted_potential_v"], ceiling["binding_source"])
        )
    if not field_ok:
        findings.append(
            "%s: internal-field %.3e V/m above breakdown ceiling %.3e V/m"
            % (name, field, ceiling["breakdown_field_v_per_m"])
        )

    result = dict(ceiling)
    result.update(
        {
            "name": name,
            "predicted_potential_v": predicted,
            "internal_field_v_per_m": field,
            "potential_ok": potential_ok,
            "field_ok": field_ok,
            "margin_fraction": potential_margin(
                ceiling["permitted_potential_v"], predicted
            ),
            "verdict": verdict,
            "compliant": potential_ok and field_ok,
            "findings": findings,
        }
    )
    return result


def evaluate_surface_set(surfaces):
    """Aggregate the clause-6.2.1 verdict over a set of external surfaces."""
    if not isinstance(surfaces, (list, tuple)) or not surfaces:
        raise ValueError("surfaces must be a non-empty list of surface mappings")
    seen = set()
    results = []
    for surface in surfaces:
        result = evaluate_surface(surface)
        if result["name"] in seen:
            raise ValueError("duplicate surface name %r" % (result["name"],))
        seen.add(result["name"])
        results.append(result)

    worst = min(results, key=lambda r: r["margin_fraction"])
    binding_mix = {}
    for r in results:
        binding_mix[r["binding_source"]] = binding_mix.get(r["binding_source"], 0) + 1
    open_findings = [f for r in results for f in r["findings"]]
    return {
        "surface_count": len(results),
        "compliant_count": sum(1 for r in results if r["compliant"]),
        "marginal_count": sum(1 for r in results if r["verdict"] == "marginal"),
        "onset_count": sum(1 for r in results if r["verdict"] == "discharge-onset"),
        "binding_mix": binding_mix,
        "worst_surface": worst["name"],
        "worst_margin_fraction": worst["margin_fraction"],
        "set_compliant": not open_findings,
        "open_findings": open_findings,
        "surfaces": results,
    }
