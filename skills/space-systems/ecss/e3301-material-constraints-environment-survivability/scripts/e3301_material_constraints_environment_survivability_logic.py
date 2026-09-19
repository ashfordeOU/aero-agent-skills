#!/usr/bin/env python3
"""Material constraints and environment survivability for a mechanism.

Anchor: ECSS-E-ST-33-01C clauses 4.5.2.2 to 4.5.2.10. The procedure
below is a paraphrase into implementable steps; no standard text is
reproduced.

Once a material has passed selection it still has to survive where it
sits and harm nothing around it. Seven constraints are carried here,
and they fail in different ways:

    fungus            a nutrient material left untreated through humid
                      ground storage grows something that bridges
                      contacts and holds moisture against surfaces
    flammability      a limiting oxygen index that does not stand clear
                      of the oxygen it will sit in is a propagation
                      path, and the margin is what matters, not the
                      index alone
    hazard            an unstable material is out; a toxic one is out
                      of a habitable volume unless it is contained
    stray light       a reflective surface inside an optical path is a
                      performance failure long before it is a
                      contamination one
    radiation         the degradation threshold has to stand above the
                      mission dose multiplied by its design margin
    atomic oxygen     recession depth is erosion yield times fluence,
                      and an exposed polymer in low orbit erodes at a
                      rate that is easy to compute and easy to forget
    fluid             every wetted pair is checked against the fluid it
                      touches, not against the fluid the system is
                      named after

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CONSTRAINTS = (
    "fungus",
    "flammability",
    "hazardous-material",
    "stray-light",
    "radiation",
    "atomic-oxygen",
    "fluid-compatibility",
)

CONTAINMENT_LEVELS = ("none", "vented-enclosure", "sealed-containment")

DEFAULT_CONSTRAINT_POLICY = {
    "required_oxygen_index_margin_points": 5.0,
    "radiation_design_margin": 2.0,
    "require_fungus_treatment_in_humid_storage": True,
    "toxic_needs_sealed_containment_when_habitable": True,
    "unstable_materials_prohibited": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_positive(name, value):
    value = _require_non_negative(name, value)
    if value == 0.0:
        raise ValueError("%s must be greater than zero" % name)
    return value


def _require_percentage(name, value):
    value = _require_number(name, value)
    if not 0.0 <= value <= 100.0:
        raise ValueError("%s must lie between 0 and 100, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    value = _require_number(name, value)
    if not 0.0 <= value <= 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_constraint_policy(policy):
    """Check the constraint policy states every limit the grading needs."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_non_negative(
        "required_oxygen_index_margin_points",
        policy.get("required_oxygen_index_margin_points"),
    )
    margin = _require_positive(
        "radiation_design_margin", policy.get("radiation_design_margin")
    )
    if margin < 1.0:
        raise ValueError("radiation_design_margin must be at least unity")
    for flag in (
        "require_fungus_treatment_in_humid_storage",
        "toxic_needs_sealed_containment_when_habitable",
        "unstable_materials_prohibited",
    ):
        _require_bool("policy %s" % flag, policy.get(flag))
    return policy


def assess_fungus(is_nutrient, treated, humid_storage, policy=DEFAULT_CONSTRAINT_POLICY):
    """Grade a material against the fungus-resistance constraint."""
    validate_constraint_policy(policy)
    nutrient = _require_bool("is_nutrient", is_nutrient)
    is_treated = _require_bool("treated", treated)
    humid = _require_bool("humid_storage", humid_storage)
    if not nutrient:
        return {"constraint": "fungus", "acceptable": True, "findings": []}
    if not humid:
        return {
            "constraint": "fungus",
            "acceptable": True,
            "findings": [
                "nutrient material accepted only because no humid ground "
                "storage is declared"
            ],
        }
    if is_treated or not policy["require_fungus_treatment_in_humid_storage"]:
        return {
            "constraint": "fungus",
            "acceptable": True,
            "findings": ["nutrient material carried against a fungus treatment"],
        }
    return {
        "constraint": "fungus",
        "acceptable": False,
        "findings": [
            "fungus-nutrient material is untreated and sees humid ground storage"
        ],
    }


def oxygen_index_margin_points(
    limiting_oxygen_index_percent, environment_oxygen_percent
):
    """Percentage points by which the index stands clear of the atmosphere."""
    index = _require_percentage(
        "limiting_oxygen_index_percent", limiting_oxygen_index_percent
    )
    ambient = _require_percentage(
        "environment_oxygen_percent", environment_oxygen_percent
    )
    return index - ambient


def assess_flammability(
    limiting_oxygen_index_percent,
    environment_oxygen_percent,
    policy=DEFAULT_CONSTRAINT_POLICY,
):
    """Grade a material against the atmosphere it is expected to sit in."""
    validate_constraint_policy(policy)
    margin = oxygen_index_margin_points(
        limiting_oxygen_index_percent, environment_oxygen_percent
    )
    required = policy["required_oxygen_index_margin_points"]
    acceptable = _at_least(margin, required)
    findings = []
    if not acceptable:
        findings.append(
            "limiting oxygen index stands only %.1f points above the "
            "atmosphere against a required %.1f" % (margin, required)
        )
    return {
        "constraint": "flammability",
        "margin_points": margin,
        "acceptable": acceptable,
        "findings": findings,
    }


def assess_hazardous_material(
    toxic, unstable, containment, habitable_volume, policy=DEFAULT_CONSTRAINT_POLICY
):
    """Grade a material against the toxic and unstable prohibitions."""
    validate_constraint_policy(policy)
    is_toxic = _require_bool("toxic", toxic)
    is_unstable = _require_bool("unstable", unstable)
    _require_choice("containment", containment, CONTAINMENT_LEVELS)
    habitable = _require_bool("habitable_volume", habitable_volume)
    findings = []
    acceptable = True
    if is_unstable and policy["unstable_materials_prohibited"]:
        acceptable = False
        findings.append("unstable material is prohibited outright")
    if is_toxic:
        if habitable and policy["toxic_needs_sealed_containment_when_habitable"]:
            if containment != "sealed-containment":
                acceptable = False
                findings.append(
                    "toxic material in a habitable volume is carried at "
                    "containment level %s" % containment
                )
            else:
                findings.append(
                    "toxic material carried in a habitable volume behind sealed "
                    "containment"
                )
        else:
            findings.append("toxic material carried outside a habitable volume")
    return {
        "constraint": "hazardous-material",
        "acceptable": acceptable,
        "findings": findings,
    }


def assess_stray_light(in_optical_path, reflectance, max_reflectance):
    """Grade a surface that sits where scattered light reaches a detector."""
    inside = _require_bool("in_optical_path", in_optical_path)
    value = _require_fraction("reflectance", reflectance)
    limit = _require_fraction("max_reflectance", max_reflectance)
    if not inside:
        return {"constraint": "stray-light", "acceptable": True, "findings": []}
    acceptable = _at_most(value, limit)
    findings = []
    if not acceptable:
        findings.append(
            "surface in the optical path reflects %.4f against a limit of %.4f"
            % (value, limit)
        )
    return {
        "constraint": "stray-light",
        "acceptable": acceptable,
        "findings": findings,
    }


def radiation_capability_ratio(
    degradation_threshold_krad, mission_dose_krad, policy=DEFAULT_CONSTRAINT_POLICY
):
    """Threshold over the dose the design has to be good for."""
    validate_constraint_policy(policy)
    threshold = _require_positive(
        "degradation_threshold_krad", degradation_threshold_krad
    )
    dose = _require_positive("mission_dose_krad", mission_dose_krad)
    return threshold / (dose * policy["radiation_design_margin"])


def assess_radiation(
    degradation_threshold_krad, mission_dose_krad, policy=DEFAULT_CONSTRAINT_POLICY
):
    """Grade a material against the dose it accumulates, with its margin."""
    ratio = radiation_capability_ratio(
        degradation_threshold_krad, mission_dose_krad, policy
    )
    acceptable = _at_least(ratio, 1.0)
    findings = []
    if not acceptable:
        findings.append(
            "radiation capability ratio %.4f is below unity against a design "
            "margin of %.2f" % (ratio, policy["radiation_design_margin"])
        )
    return {
        "constraint": "radiation",
        "capability_ratio": ratio,
        "acceptable": acceptable,
        "findings": findings,
    }


def atomic_oxygen_recession_m(erosion_yield_m3_per_atom, fluence_atoms_per_m2):
    """Thickness lost to atomic oxygen: erosion yield times fluence."""
    yield_value = _require_non_negative(
        "erosion_yield_m3_per_atom", erosion_yield_m3_per_atom
    )
    fluence = _require_non_negative("fluence_atoms_per_m2", fluence_atoms_per_m2)
    return yield_value * fluence


def assess_atomic_oxygen(
    erosion_yield_m3_per_atom, fluence_atoms_per_m2, allowable_recession_m,
    protected=False,
):
    """Grade an exposed material against its atomic-oxygen budget."""
    recession = atomic_oxygen_recession_m(
        erosion_yield_m3_per_atom, fluence_atoms_per_m2
    )
    allowable = _require_positive("allowable_recession_m", allowable_recession_m)
    is_protected = _require_bool("protected", protected)
    within = _at_most(recession, allowable)
    findings = []
    acceptable = within or is_protected
    if not within and is_protected:
        findings.append(
            "bare recession %.4g m exceeds the allowable %.4g m and is carried "
            "by a protective coating" % (recession, allowable)
        )
    elif not within:
        findings.append(
            "recession %.4g m exceeds the allowable %.4g m and no protective "
            "coating is declared" % (recession, allowable)
        )
    return {
        "constraint": "atomic-oxygen",
        "recession_m": recession,
        "acceptable": acceptable,
        "findings": findings,
    }


def assess_fluid_compatibility(wetted_fluids, incompatible_fluids):
    """Grade a wetted material against every fluid it actually touches."""
    if not isinstance(wetted_fluids, (list, tuple)):
        raise ValueError("wetted_fluids must be a sequence")
    if not isinstance(incompatible_fluids, (list, tuple)):
        raise ValueError("incompatible_fluids must be a sequence")
    for fluid in list(wetted_fluids) + list(incompatible_fluids):
        if not isinstance(fluid, str) or not fluid.strip():
            raise ValueError("fluid names must be non-empty strings")
    banned = set(incompatible_fluids)
    clashes = [f for f in wetted_fluids if f in banned]
    findings = []
    if clashes:
        findings.append(
            "material is wetted by %s, which it is not compatible with"
            % ", ".join(sorted(set(clashes)))
        )
    return {
        "constraint": "fluid-compatibility",
        "clashes": sorted(set(clashes)),
        "acceptable": not clashes,
        "findings": findings,
    }


def assess_material_constraints(case, policy=DEFAULT_CONSTRAINT_POLICY):
    """Full verdict across clauses 4.5.2.2 to 4.5.2.10 for one material."""
    validate_constraint_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    name = case.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("case name must be a non-empty string")
    results = [
        assess_fungus(
            case.get("is_fungus_nutrient", False),
            case.get("fungus_treated", False),
            case.get("humid_ground_storage", False),
            policy,
        ),
        assess_flammability(
            case.get("limiting_oxygen_index_percent"),
            case.get("environment_oxygen_percent"),
            policy,
        ),
        assess_hazardous_material(
            case.get("toxic", False),
            case.get("unstable", False),
            case.get("containment", "none"),
            case.get("habitable_volume", False),
            policy,
        ),
        assess_stray_light(
            case.get("in_optical_path", False),
            case.get("reflectance", 0.0),
            case.get("max_reflectance", 1.0),
        ),
        assess_radiation(
            case.get("degradation_threshold_krad"),
            case.get("mission_dose_krad"),
            policy,
        ),
        assess_atomic_oxygen(
            case.get("erosion_yield_m3_per_atom", 0.0),
            case.get("atomic_oxygen_fluence_atoms_per_m2", 0.0),
            case.get("allowable_recession_m", 1.0),
            case.get("atomic_oxygen_protected", False),
        ),
        assess_fluid_compatibility(
            case.get("wetted_fluids", []),
            case.get("incompatible_fluids", []),
        ),
    ]
    findings = []
    violated = []
    for result in results:
        findings.extend(result["findings"])
        if not result["acceptable"]:
            violated.append(result["constraint"])
    compliant = not violated
    return {
        "name": name,
        "constraints": {r["constraint"]: r for r in results},
        "violated": violated,
        "compliant": compliant,
        "verdict": "constraints-met" if compliant else "constraints-violated",
        "findings": findings,
    }
