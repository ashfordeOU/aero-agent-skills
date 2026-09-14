#!/usr/bin/env python3
"""What a coverglass description has to say, and has to survive.

Anchor: ECSS-E-ST-20-08C clause 8.1.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A coverglass is a transparent shield laid over the cell: it passes the
useful spectrum through to the junction while taking the particle and
ultraviolet environment on itself. The description of one is therefore
a substrate plus a thickness plus an optical claim, and those three are
not independent -- the substrate fixes how much light can get through
an uncoated piece at all, and the thickness fixes what shielding the
areal mass actually buys.

Admissible substrates are fused silica and the glasses that behave like
it: a cerium-doped borosilicate, a borosilicate microsheet, sapphire. A
polymer film is transparent but is not a glass shield of this family,
and a description resting on one is rejected rather than graded.

The optical check is the one worth doing by arithmetic. With no
absorption and no coating, the two air-glass surfaces of a slab pass

    T = 2n / (n**2 + 1)

of the incident light at normal incidence, which for fused silica is
about 0.933. A description claiming more than that with no
antireflective coating declared is describing something that does not
exist, and catching it costs one multiplication.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SUBSTRATE_LIBRARY = {
    "fused-silica": {
        "refractive_index": 1.4585,
        "density_kg_m3": 2200.0,
        "admissible": True,
        "note": "the reference coverglass substrate",
    },
    "ceria-doped-borosilicate": {
        "refractive_index": 1.5200,
        "density_kg_m3": 2550.0,
        "admissible": True,
        "note": "a borosilicate doped to hold the ultraviolet off the adhesive",
    },
    "microsheet-borosilicate": {
        "refractive_index": 1.4740,
        "density_kg_m3": 2360.0,
        "admissible": True,
        "note": "a thin drawn borosilicate sheet",
    },
    "sapphire": {
        "refractive_index": 1.7682,
        "density_kg_m3": 3980.0,
        "admissible": True,
        "note": "a harder substrate bought at a reflection and mass penalty",
    },
    "polymer-film": {
        "refractive_index": 1.5800,
        "density_kg_m3": 1420.0,
        "admissible": False,
        "note": "transparent, but not a glass shield of the coverglass family",
    },
}

COATINGS = (
    "antireflective-coating",
    "conductive-coating",
    "uv-reflective-coating",
)

REQUIRED_FIELDS = ("substrate", "thickness_m", "average_transmittance", "coatings")

DESCRIPTION_INCOMPLETE = "description-incomplete"
SUBSTRATE_NOT_ADMISSIBLE = "substrate-not-admissible"
DESCRIPTION_NON_PHYSICAL = "description-non-physical"
DESCRIPTION_QUERIED = "description-queried"
DESCRIPTION_COMPLETE = "description-complete"

DEFAULT_DESCRIPTION_POLICY = {
    "min_thickness_m": 50.0e-6,
    "max_thickness_m": 500.0e-6,
    "min_average_transmittance": 0.90,
    "coated_transmittance_ceiling": 0.995,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_fraction(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0 or value > 1.0:
        raise ValueError(
            "%s must lie above zero and at most one, got %r" % (name, value)
        )
    return float(value)


def _require_sequence(name, value):
    if isinstance(value, (str, bytes)) or not isinstance(
        value, (list, tuple, set, frozenset)
    ):
        raise ValueError("%s must be a sequence of names, got %r" % (name, value))
    return tuple(value)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A declared transmittance sitting exactly on the ceiling the
    refractive index allows can land a unit in the last place above it
    once the ceiling has been through a division. The ceiling is never
    raised; only the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_description_policy(policy):
    """Check a description policy carries a usable band and ceiling."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    low = _require_positive("min_thickness_m", policy.get("min_thickness_m"))
    high = _require_positive("max_thickness_m", policy.get("max_thickness_m"))
    if high <= low:
        raise ValueError("policy max_thickness_m must exceed min_thickness_m")
    _require_fraction(
        "min_average_transmittance", policy.get("min_average_transmittance")
    )
    _require_fraction(
        "coated_transmittance_ceiling", policy.get("coated_transmittance_ceiling")
    )
    return policy


def substrate_properties(substrate):
    """Look up a declared substrate, rejecting one nobody recognises."""
    if substrate not in SUBSTRATE_LIBRARY:
        raise ValueError(
            "substrate must be one of %s, got %r"
            % (", ".join(sorted(SUBSTRATE_LIBRARY)), substrate)
        )
    return dict(SUBSTRATE_LIBRARY[substrate])


def normalise_coatings(coatings):
    """Order and de-duplicate a declared coating stack, rejecting unknowns."""
    declared = _require_sequence("coatings", coatings)
    seen = []
    for coating in declared:
        if coating not in COATINGS:
            raise ValueError(
                "coating must be one of %s, got %r" % (", ".join(COATINGS), coating)
            )
        if coating not in seen:
            seen.append(coating)
    return tuple(sorted(seen, key=COATINGS.index))


def single_surface_reflectance(refractive_index):
    """Normal-incidence reflectance of one air-substrate surface."""
    n = _require_positive("refractive_index", refractive_index)
    if n < 1.0:
        raise ValueError("refractive_index must be at least one, got %r" % (n,))
    return ((n - 1.0) / (n + 1.0)) ** 2


def uncoated_transmittance_ceiling(refractive_index):
    """Most an uncoated, non-absorbing slab can pass at normal incidence."""
    n = _require_positive("refractive_index", refractive_index)
    if n < 1.0:
        raise ValueError("refractive_index must be at least one, got %r" % (n,))
    return (2.0 * n) / (n * n + 1.0)


def areal_mass_kg_m2(density_kg_m3, thickness_m):
    """Mass the coverglass adds per unit of array area."""
    density = _require_positive("density_kg_m3", density_kg_m3)
    thickness = _require_positive("thickness_m", thickness_m)
    return density * thickness


def shielding_areal_density_g_cm2(areal_mass):
    """The same mass in the unit a shielding curve is read in."""
    mass = _require_positive("areal_mass_kg_m2", areal_mass)
    return mass * 0.1


def piece_mass_kg(areal_mass, length_m, width_m):
    """Mass of one cut coverglass of the declared footprint."""
    mass = _require_positive("areal_mass_kg_m2", areal_mass)
    length = _require_positive("length_m", length_m)
    width = _require_positive("width_m", width_m)
    return mass * length * width


def transmittance_admissibility(
    substrate, average_transmittance, coatings=(), policy=DEFAULT_DESCRIPTION_POLICY
):
    """Hold a declared transmittance against what the substrate allows."""
    validate_description_policy(policy)
    properties = substrate_properties(substrate)
    declared = _require_fraction("average_transmittance", average_transmittance)
    stack = normalise_coatings(coatings)
    ceiling = uncoated_transmittance_ceiling(properties["refractive_index"])
    antireflective = "antireflective-coating" in stack
    findings = []
    if antireflective:
        limit = float(policy["coated_transmittance_ceiling"])
        limit_kind = "coated-ceiling"
    else:
        limit = ceiling
        limit_kind = "uncoated-fresnel-ceiling"
    physical = _at_most(declared, limit)
    if not physical:
        if antireflective:
            findings.append(
                "declared transmittance %.4f exceeds the coated ceiling %.4f; no "
                "coating removes both surface reflections entirely"
                % (declared, limit)
            )
        else:
            findings.append(
                "declared transmittance %.4f exceeds the %.4f an uncoated %s slab "
                "can pass; either an antireflective coating was left out of the "
                "description or the number is wrong" % (declared, limit, substrate)
            )
    floor = float(policy["min_average_transmittance"])
    below_floor = declared < floor and not math.isclose(
        declared, floor, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )
    if below_floor:
        findings.append(
            "declared transmittance %.4f sits below the %.4f floor the description "
            "policy expects of a coverglass" % (declared, floor)
        )
    return {
        "declared": declared,
        "uncoated_ceiling": ceiling,
        "applied_limit": limit,
        "limit_kind": limit_kind,
        "physical": physical,
        "below_floor": below_floor,
        "findings": findings,
    }


def describe_coverglass(case, policy=DEFAULT_DESCRIPTION_POLICY):
    """Full clause 8.1.2 description check with a completeness verdict."""
    validate_description_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    absent = tuple(field for field in REQUIRED_FIELDS if case.get(field) is None)
    if absent:
        return {
            "verdict": DESCRIPTION_INCOMPLETE,
            "missing_fields": absent,
            "substrate": case.get("substrate"),
            "coatings": (),
            "areal_mass_kg_m2": None,
            "shielding_areal_density_g_cm2": None,
            "piece_mass_kg": None,
            "transmittance": None,
            "findings": [
                "the description omits %s, so nothing downstream can be derived"
                % ", ".join(absent)
            ],
        }
    substrate = case["substrate"]
    properties = substrate_properties(substrate)
    stack = normalise_coatings(case["coatings"])
    findings = []
    if not properties["admissible"]:
        findings.append(
            "%s is not a coverglass substrate of the fused-silica family: %s"
            % (substrate, properties["note"])
        )
        return {
            "verdict": SUBSTRATE_NOT_ADMISSIBLE,
            "missing_fields": (),
            "substrate": substrate,
            "coatings": stack,
            "areal_mass_kg_m2": None,
            "shielding_areal_density_g_cm2": None,
            "piece_mass_kg": None,
            "transmittance": None,
            "findings": findings,
        }
    thickness = _require_positive("thickness_m", case["thickness_m"])
    density = case.get("density_kg_m3", properties["density_kg_m3"])
    areal = areal_mass_kg_m2(density, thickness)
    shielding = shielding_areal_density_g_cm2(areal)
    transmittance = transmittance_admissibility(
        substrate, case["average_transmittance"], stack, policy
    )
    findings.extend(transmittance["findings"])
    piece = None
    if case.get("length_m") is not None and case.get("width_m") is not None:
        piece = piece_mass_kg(areal, case["length_m"], case["width_m"])
    thin = thickness < float(policy["min_thickness_m"]) and not math.isclose(
        thickness, float(policy["min_thickness_m"]), rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )
    thick = not _at_most(thickness, float(policy["max_thickness_m"]))
    if thin:
        findings.append(
            "declared thickness %.1f um is below the %.1f um the description policy "
            "treats as a coverglass"
            % (thickness * 1.0e6, float(policy["min_thickness_m"]) * 1.0e6)
        )
    if thick:
        findings.append(
            "declared thickness %.1f um is above the %.1f um the description policy "
            "treats as a coverglass"
            % (thickness * 1.0e6, float(policy["max_thickness_m"]) * 1.0e6)
        )
    result = {
        "missing_fields": (),
        "substrate": substrate,
        "substrate_note": properties["note"],
        "coatings": stack,
        "thickness_m": thickness,
        "areal_mass_kg_m2": areal,
        "shielding_areal_density_g_cm2": shielding,
        "piece_mass_kg": piece,
        "transmittance": transmittance,
        "findings": findings,
    }
    if not transmittance["physical"]:
        result["verdict"] = DESCRIPTION_NON_PHYSICAL
    elif findings:
        result["verdict"] = DESCRIPTION_QUERIED
    else:
        result["verdict"] = DESCRIPTION_COMPLETE
    return result
