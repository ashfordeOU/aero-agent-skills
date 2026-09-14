#!/usr/bin/env python3
"""Why coating attachment is verified after environmental conditioning.

Anchor: ECSS-E-ST-20-08C clause 8.7.11.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A coverglass coating is a thin film carried on a glass body. Every
function the coating has -- the reflection it suppresses, the charge it
bleeds, the ultraviolet it turns back -- exists only while the film is
still attached to that body. Attachment is therefore not a property of
the coating, it is a property of the interface, and the interface is
the part of the article the deposition process never directly proves.

The clause is a purpose clause, and its whole argument is the word
after. A coating adheres when it leaves the coater; that is what a
coater is for. What the mission needs to know is whether it still
adheres once water has had time to reach the interface and once the
glass and the film have pulled against each other across a temperature
swing. Verifying attachment before conditioning answers a question
nobody asked.

Two quantities carry the argument.

The mismatch stress. Glass and coating expand at different rates, so a
temperature excursion loads the interface in shear:

    shear = E * delta_alpha * delta_T / (1 - nu)

with the modulus in GPa, the expansion mismatch in ppm per degree and
the excursion in degrees, giving MPa. Against a declared interfacial
strength that stress leaves a margin of safety, strength over stress
minus one, and a margin at or below zero is an interface the cycling
is expected to open.

The cost of detachment. A detached patch is not a hole; it is bare
glass, which still transmits, just not as well as a coated surface
does, and which no longer bleeds charge. So a detached area fraction
prices out as a transmission the assembly retains,

    retained = coated * (1 - fraction) + bare * fraction

and, separately, as a loss of surface conduction once the detached
fraction breaks the conductive path.

The conditionings, thresholds and floors below are a declared policy,
not a physical constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

HUMIDITY_SOAK = "humidity-soak"
THERMAL_CYCLING = "thermal-cycling"
THERMAL_VACUUM = "thermal-vacuum"
EXTENDED_STORAGE = "extended-storage"

CONDITIONING_OBJECTIVES = {
    EXTENDED_STORAGE: (
        "show the bond has not aged out between coating and flight, so a "
        "shelf-stored lot is not a different lot"
    ),
    HUMIDITY_SOAK: (
        "show water reaching the interface has not undercut the film, which "
        "is the failure a freshly coated article cannot exhibit"
    ),
    THERMAL_CYCLING: (
        "show the expansion mismatch between film and glass has not opened "
        "the interface over the excursions the orbit imposes"
    ),
    THERMAL_VACUUM: (
        "show the bond survives the excursion without the convective path "
        "the ground test enjoyed, and without volatiles it can shed"
    ),
}

RECOGNISED_CONDITIONINGS = tuple(sorted(CONDITIONING_OBJECTIVES))

SHARED_OBJECTIVE = (
    "state what the coverglass still delivers optically and electrically once "
    "the conditioned interface is the one carrying the film"
)

VERIFICATION_NOT_REQUIRED = "adherence-verification-not-required"
VERIFICATION_NOT_PLANNED = "adherence-verification-not-planned"
VERIFICATION_MISSEQUENCED = "adherence-verification-precedes-conditioning"
ADHERENCE_MARGIN_SHORTFALL = "coating-adherence-margin-shortfall"
PURPOSE_ESTABLISHED = "coating-adherence-purpose-established"

DEFAULT_PURPOSE_POLICY = {
    "min_margin_of_safety": 0.0,
    "max_detached_area_fraction": 0.02,
    "min_retained_transmission": 0.95,
    "conduction_break_fraction": 0.30,
    "min_excursion_c": 20.0,
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


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 <= number <= 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_index(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a whole step number, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_purpose_policy(policy):
    """Check a purpose policy is complete and internally consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_number("min_margin_of_safety", policy.get("min_margin_of_safety"))
    detached = _require_fraction(
        "max_detached_area_fraction", policy.get("max_detached_area_fraction")
    )
    _require_fraction(
        "min_retained_transmission", policy.get("min_retained_transmission")
    )
    broken = _require_fraction(
        "conduction_break_fraction", policy.get("conduction_break_fraction")
    )
    if broken <= detached:
        raise ValueError(
            "conduction_break_fraction %g must sit above the %g detached area "
            "already refused on optical grounds" % (broken, detached)
        )
    _require_positive("min_excursion_c", policy.get("min_excursion_c"))
    return policy


def interfacial_shear_stress_mpa(
    coating_modulus_gpa, cte_mismatch_ppm_per_c, excursion_c, poisson_ratio
):
    """Shear the expansion mismatch puts on the coating-to-glass interface."""
    modulus = _require_positive("coating_modulus_gpa", coating_modulus_gpa)
    mismatch = _require_number("cte_mismatch_ppm_per_c", cte_mismatch_ppm_per_c)
    excursion = _require_positive("excursion_c", excursion_c)
    poisson = _require_number("poisson_ratio", poisson_ratio)
    if not 0.0 <= poisson < 0.5:
        raise ValueError(
            "poisson_ratio must sit at or above zero and below one half, got %r"
            % (poisson_ratio,)
        )
    return modulus * abs(mismatch) * excursion * 1.0e-3 / (1.0 - poisson)


def margin_of_safety(interfacial_strength_mpa, applied_shear_mpa):
    """Strength over applied shear, less one: zero is the interface opening."""
    strength = _require_positive(
        "interfacial_strength_mpa", interfacial_strength_mpa
    )
    applied = _require_positive("applied_shear_mpa", applied_shear_mpa)
    return strength / applied - 1.0


def retained_transmission(
    detached_area_fraction, coated_transmission, bare_glass_transmission
):
    """Transmission left once part of the coating has let go of the glass."""
    fraction = _require_fraction(
        "detached_area_fraction", detached_area_fraction
    )
    coated = _require_fraction("coated_transmission", coated_transmission)
    bare = _require_fraction(
        "bare_glass_transmission", bare_glass_transmission
    )
    if bare > coated:
        raise ValueError(
            "bare_glass_transmission %g exceeds the %g coated transmission; a "
            "coating that costs transmission is a mislabelled measurement"
            % (bare, coated)
        )
    return coated * (1.0 - fraction) + bare * fraction


def transmission_loss(
    detached_area_fraction, coated_transmission, bare_glass_transmission
):
    """Transmission the detached fraction costs, against the intact article."""
    coated = _require_fraction("coated_transmission", coated_transmission)
    return coated - retained_transmission(
        detached_area_fraction, coated_transmission, bare_glass_transmission
    )


def charge_control_intact(detached_area_fraction, policy=DEFAULT_PURPOSE_POLICY):
    """True while the conductive coating still has a path across the face."""
    validate_purpose_policy(policy)
    fraction = _require_fraction(
        "detached_area_fraction", detached_area_fraction
    )
    return not _at_least(fraction, float(policy["conduction_break_fraction"]))


def conditioning_inventory(declared_conditionings):
    """Map each declared conditioning to what the adherence check feeds it."""
    if not isinstance(declared_conditionings, (list, tuple)):
        raise ValueError(
            "declared_conditionings must be a sequence of conditioning names"
        )
    grouped = []
    seen = set()
    for entry in declared_conditionings:
        name = _require_label("conditioning", entry)
        if name not in CONDITIONING_OBJECTIVES:
            raise ValueError(
                "unknown conditioning %r; recognised conditionings are %s"
                % (entry, ", ".join(RECOGNISED_CONDITIONINGS))
            )
        if name in seen:
            continue
        seen.add(name)
        grouped.append((name, CONDITIONING_OBJECTIVES[name]))
    grouped.sort()
    if grouped:
        grouped.append(("shared", SHARED_OBJECTIVE))
    return tuple(grouped)


def verification_required(declared_conditionings, excursion_c, policy=DEFAULT_PURPOSE_POLICY):
    """True when a conditioning is declared that the interface must survive."""
    validate_purpose_policy(policy)
    inventory = conditioning_inventory(declared_conditionings)
    if not inventory:
        return False
    names = {name for name, _objective in inventory}
    if names & {HUMIDITY_SOAK, THERMAL_VACUUM, EXTENDED_STORAGE}:
        return True
    excursion = _require_number("excursion_c", excursion_c)
    return _at_least(excursion, float(policy["min_excursion_c"]))


def check_follows_conditioning(sequence):
    """True when the adherence check is scheduled after every conditioning.

    The sequence is a list of step records, each naming a step and the
    order it runs at. A check that precedes a conditioning has measured
    an interface the mission will never fly.
    """
    if not isinstance(sequence, (list, tuple)):
        raise ValueError("sequence must be a list of step records")
    check_step = None
    last_conditioning = None
    seen = set()
    for step in sequence:
        if not isinstance(step, dict):
            raise ValueError("step must be a mapping, got %r" % (step,))
        name = _require_label("step", step.get("step"))
        order = _require_index("order", step.get("order"))
        if order in seen:
            raise ValueError("two steps share order %d" % order)
        seen.add(order)
        if name == "coating-adherence-check":
            if check_step is not None:
                raise ValueError("the adherence check appears twice in the sequence")
            check_step = order
        elif name in CONDITIONING_OBJECTIVES:
            if last_conditioning is None or order > last_conditioning:
                last_conditioning = order
    if check_step is None:
        return False, None, last_conditioning
    if last_conditioning is None:
        return False, check_step, None
    return check_step > last_conditioning, check_step, last_conditioning


def assess_coating_adherence_purpose(case, policy=DEFAULT_PURPOSE_POLICY):
    """Full clause 8.7.11.2.1 judgement for one coated coverglass lot."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_purpose_policy(policy)
    if "declared_conditionings" not in case:
        raise ValueError(
            "case is missing declared_conditionings; an absent declaration is "
            "not an empty one"
        )
    declared = case["declared_conditionings"]
    excursion = _require_number("excursion_c", case.get("excursion_c"))

    findings = []
    inventory = conditioning_inventory(declared)
    result = {
        "conditioning_objectives": inventory,
        "interfacial_shear_mpa": None,
        "margin_of_safety": None,
        "retained_transmission": None,
        "charge_control_intact": None,
        "findings": findings,
    }

    if not verification_required(declared, excursion, policy):
        findings.append(
            "no declared conditioning loads the interface -- the %.1f C "
            "excursion stays under the %.1f C the check is wanted above -- so "
            "the deposited bond is the bond that flies"
            % (excursion, float(policy["min_excursion_c"]))
        )
        result["verdict"] = VERIFICATION_NOT_REQUIRED
        return result

    shear = interfacial_shear_stress_mpa(
        case.get("coating_modulus_gpa"),
        case.get("cte_mismatch_ppm_per_c"),
        excursion,
        case.get("poisson_ratio"),
    )
    result["interfacial_shear_mpa"] = shear
    result["margin_of_safety"] = margin_of_safety(
        case.get("interfacial_strength_mpa"), shear
    )
    fraction = _require_fraction(
        "detached_area_fraction", case.get("detached_area_fraction")
    )
    result["retained_transmission"] = retained_transmission(
        fraction,
        case.get("coated_transmission"),
        case.get("bare_glass_transmission"),
    )
    result["charge_control_intact"] = charge_control_intact(fraction, policy)

    if not case.get("verification_planned", False):
        findings.append(
            "a conditioning is declared but no adherence verification is "
            "planned, so nothing states what the interface retains afterwards"
        )
        result["verdict"] = VERIFICATION_NOT_PLANNED
        return result

    follows, check_step, last_conditioning = check_follows_conditioning(
        case.get("sequence", ())
    )
    if not follows:
        if check_step is None:
            findings.append(
                "the test sequence schedules no adherence check, so the "
                "planned verification has no place to happen"
            )
        elif last_conditioning is None:
            findings.append(
                "the adherence check at step %d has no conditioning before it "
                "in the sequence, so it measures the deposited bond rather "
                "than the conditioned one" % check_step
            )
        else:
            findings.append(
                "the adherence check runs at step %d, ahead of the "
                "conditioning at step %d, so it answers a question about the "
                "coater rather than about the mission"
                % (check_step, last_conditioning)
            )
        result["verdict"] = VERIFICATION_MISSEQUENCED
        return result

    margin_floor = float(policy["min_margin_of_safety"])
    if not _at_least(result["margin_of_safety"], margin_floor):
        findings.append(
            "the %.2f MPa mismatch shear leaves a margin of safety of %.3f "
            "against the declared bond strength, at or under the %.3f floor"
            % (shear, result["margin_of_safety"], margin_floor)
        )
    if not _at_most(fraction, float(policy["max_detached_area_fraction"])):
        findings.append(
            "%.1f%% of the coated area has let go, above the %.1f%% the lot "
            "may carry"
            % (
                fraction * 100.0,
                float(policy["max_detached_area_fraction"]) * 100.0,
            )
        )
    if not _at_least(
        result["retained_transmission"], float(policy["min_retained_transmission"])
    ):
        findings.append(
            "the detached area leaves %.4f transmission, under the %.4f the "
            "optical budget is written at"
            % (
                result["retained_transmission"],
                float(policy["min_retained_transmission"]),
            )
        )
    if not result["charge_control_intact"]:
        findings.append(
            "the detached fraction has broken the conductive path across the "
            "face, so the coverglass no longer bleeds the charge it was "
            "coated to bleed"
        )

    if findings:
        result["verdict"] = ADHERENCE_MARGIN_SHORTFALL
        return result

    result["verdict"] = PURPOSE_ESTABLISHED
    return result
