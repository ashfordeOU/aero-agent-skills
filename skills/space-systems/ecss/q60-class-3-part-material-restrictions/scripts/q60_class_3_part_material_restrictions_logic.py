#!/usr/bin/env python3
"""Packaging and material limits on a Class 3 part choice.

Anchor: ECSS-Q-ST-60C clause 6.2.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Class 3 is where non-hermetic parts are actually chosen, so the clause
is not a ban on plastic. It is the set of conditions under which a
plastic-encapsulated part can be taken to a flight build, plus the
material limits that hold whatever the case is made of.

Packaging. A hermetic case keeps the die away from moisture on its own
and closes the question. A non-hermetic case does not: the mould
compound takes up water on the shelf and in the workshop, and the water
flashes to steam at reflow and lifts the die pad. What controls that is
not a pass or a fail but a budget. Each moisture sensitivity level
carries a floor life -- the hours the part may sit outside a dry pack
before it has to be baked again -- and the exposure already spent is
measured against it. Damp air spends the budget faster than the rated
condition does, so the exposure is accelerated by the humidity it was
actually held in. A part whose budget is spent is not rejected; it is
baked, and the bake has to be on record.

Materials. Some metals are kept out of a flight part outright at
anything above a trace, because they leave the part and attack what is
around them. Tin is not one of them: tin is wanted, it is the
solderability of the finish. What is restricted is tin that is nearly
pure, because a near-pure finish grows whiskers years after acceptance
and no incoming test finds them. Tin is therefore graded against a mass
fraction and a finish over the threshold can be brought back by
re-working it.

Organics are the third limit and the one a hermetic case does not
escape. An encapsulant, a conformal coat or a die attach that loses too
much of itself in vacuum, or that condenses what it loses onto a cold
surface, contaminates optics and detectors far from the part it came
from. Total mass loss and condensable volatile fraction are graded
separately, because a material can pass one and fail the other.

The useful output is not permitted or not. It is the floor-life budget
left, the whisker margin on each finish, the tighter of the two
outgassing margins on each organic, and the list of bakes, re-works and
agreed deviations the part carries into its procurement file.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PACKAGE_TYPES = (
    "hermetic-metal-can",
    "hermetic-ceramic",
    "hermetic-glass",
    "non-hermetic-plastic-moulded",
    "non-hermetic-encapsulated",
    "non-hermetic-chip-scale",
)

HERMETIC_PACKAGES = frozenset(
    ("hermetic-metal-can", "hermetic-ceramic", "hermetic-glass")
)

MOISTURE_FLOOR_LIFE_HOURS = {
    1: float("inf"),
    2: 8760.0,
    3: 168.0,
    4: 72.0,
    5: 48.0,
    6: 6.0,
}

RATED_RELATIVE_HUMIDITY = 60.0

MAX_TIN_MASS_FRACTION = 0.97
TRACE_MASS_FRACTION = 1.0e-4

MAX_TOTAL_MASS_LOSS_PERCENT = 1.0
MAX_COLLECTED_VOLATILE_PERCENT = 0.1

RESTRICTED_METALS = (
    "cadmium",
    "zinc",
    "mercury",
    "unalloyed-magnesium",
    "radioactive-isotope",
)

TIN_MITIGATIONS = (
    "none",
    "hot-solder-dip",
    "re-tinning-with-lead-bearing-alloy",
    "lead-bearing-alloy-substitution",
)

ACCEPTED_TIN_MITIGATIONS = frozenset(
    (
        "hot-solder-dip",
        "re-tinning-with-lead-bearing-alloy",
        "lead-bearing-alloy-substitution",
    )
)

PERMITTED = "class-3-selection-permitted"
PERMITTED_WITH_MITIGATION = "class-3-selection-permitted-with-mitigation"
RESTRICTED = "class-3-selection-restricted"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_fraction(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must sit between 0 and 1, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A consumption ratio and a mass fraction are quotients while the
    limits they are graded against are decimal literals, so a value
    built to sit exactly on a limit can land a few units in the last
    place off it. The limit is never moved; only the comparison
    tolerates the representation error.
    """
    return value >= limit or _equal(value, limit)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _equal(value, limit)


def is_hermetic(package_type):
    """Whether the case keeps the die away from moisture on its own."""
    if package_type not in PACKAGE_TYPES:
        raise ValueError("unknown package_type %r" % (package_type,))
    return package_type in HERMETIC_PACKAGES


def rated_floor_life(moisture_sensitivity_level):
    """Hours the part may sit outside a dry pack before it is baked again."""
    level = moisture_sensitivity_level
    if not isinstance(level, int) or isinstance(level, bool):
        raise ValueError("moisture sensitivity level must be an integer, got %r" % (level,))
    if level not in MOISTURE_FLOOR_LIFE_HOURS:
        raise ValueError(
            "moisture sensitivity level must sit in %s, got %r"
            % (", ".join(str(key) for key in sorted(MOISTURE_FLOOR_LIFE_HOURS)), level)
        )
    return MOISTURE_FLOOR_LIFE_HOURS[level]


def humidity_acceleration(relative_humidity):
    """How much faster damp air spends the floor-life budget.

    At or under the rated condition the budget is spent at its nominal
    rate; above it the exposure counts in proportion.
    """
    humidity = _require_non_negative("relative_humidity", relative_humidity)
    if humidity > 100.0:
        raise ValueError("relative_humidity must not exceed 100, got %r" % (relative_humidity,))
    if _at_most(humidity, RATED_RELATIVE_HUMIDITY):
        return 1.0
    return humidity / RATED_RELATIVE_HUMIDITY


def floor_life_consumption(
    moisture_sensitivity_level, exposure_hours, relative_humidity=RATED_RELATIVE_HUMIDITY
):
    """Share of the floor-life budget already spent, humidity accelerated."""
    life = rated_floor_life(moisture_sensitivity_level)
    exposure = _require_non_negative("exposure_hours", exposure_hours)
    factor = humidity_acceleration(relative_humidity)
    if math.isinf(life):
        return 0.0
    return exposure * factor / life


def assess_moisture_control(case):
    """Grade the case style and, for a non-hermetic one, the damp budget."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    package_type = case.get("package_type")
    hermetic = is_hermetic(package_type)
    findings = []
    if hermetic:
        return {
            "package_type": package_type,
            "hermetic": True,
            "moisture_sensitivity_level": None,
            "floor_life_consumption": None,
            "budget_remaining": None,
            "bake_required": False,
            "verdict": PERMITTED,
            "acceptable": True,
            "findings": findings,
        }
    level = case.get("moisture_sensitivity_level")
    consumption = floor_life_consumption(
        level,
        case.get("floor_exposure_hours"),
        case.get("storage_relative_humidity", RATED_RELATIVE_HUMIDITY),
    )
    dry_pack = _require_flag("dry_packed_on_delivery", case.get("dry_packed_on_delivery"))
    bake_recorded = _require_flag("bake_recorded", case.get("bake_recorded", False))
    bake_required = _at_least(consumption, 1.0)
    if not dry_pack and rated_floor_life(level) != float("inf"):
        findings.append(
            "a level %d part was delivered outside a dry pack, so the exposure "
            "it arrived with is unknown rather than zero" % level
        )
    if bake_required and not bake_recorded:
        findings.append(
            "the floor-life budget is spent (%.3f of it used) and no bake is on "
            "record before assembly" % consumption
        )
    acceptable = not findings
    if not acceptable:
        verdict = RESTRICTED
    elif bake_required or not _equal(consumption, 0.0):
        verdict = PERMITTED_WITH_MITIGATION
    else:
        verdict = PERMITTED
    return {
        "package_type": package_type,
        "hermetic": False,
        "moisture_sensitivity_level": level,
        "rated_floor_life_hours": rated_floor_life(level),
        "floor_life_consumption": consumption,
        "budget_remaining": 1.0 - consumption,
        "bake_required": bake_required,
        "bake_recorded": bake_recorded,
        "verdict": verdict,
        "acceptable": acceptable,
        "findings": findings,
    }


def assess_tin_finish(finish):
    """Grade one surface finish against the near-pure-tin restriction."""
    if not isinstance(finish, dict):
        raise ValueError("finish must be a mapping, got %r" % (finish,))
    surface = _require_text("finish surface", finish.get("surface"))
    fraction = _require_fraction(
        "tin_mass_fraction on %s" % surface, finish.get("tin_mass_fraction")
    )
    mitigation = finish.get("mitigation", "none")
    if mitigation not in TIN_MITIGATIONS:
        raise ValueError(
            "mitigation on %s must be one of %s, got %r"
            % (surface, ", ".join(TIN_MITIGATIONS), mitigation)
        )
    margin = MAX_TIN_MASS_FRACTION - fraction
    near_pure = _at_least(fraction, MAX_TIN_MASS_FRACTION)
    if not near_pure:
        verdict = PERMITTED
    elif mitigation in ACCEPTED_TIN_MITIGATIONS:
        verdict = PERMITTED_WITH_MITIGATION
    else:
        verdict = RESTRICTED
    return {
        "surface": surface,
        "tin_mass_fraction": fraction,
        "threshold": MAX_TIN_MASS_FRACTION,
        "whisker_margin": margin,
        "near_pure_tin": near_pure,
        "mitigation": mitigation,
        "verdict": verdict,
        "acceptable": verdict != RESTRICTED,
    }


def assess_outgassing(entry):
    """Grade one organic against the mass-loss and condensable limits."""
    if not isinstance(entry, dict):
        raise ValueError("outgassing entry must be a mapping, got %r" % (entry,))
    material = _require_text("outgassing material", entry.get("material"))
    total_mass_loss = _require_non_negative(
        "total_mass_loss_percent of %s" % material, entry.get("total_mass_loss_percent")
    )
    condensable = _require_non_negative(
        "collected_volatile_percent of %s" % material,
        entry.get("collected_volatile_percent"),
    )
    mass_loss_ok = _at_most(total_mass_loss, MAX_TOTAL_MASS_LOSS_PERCENT)
    condensable_ok = _at_most(condensable, MAX_COLLECTED_VOLATILE_PERCENT)
    mass_loss_margin = MAX_TOTAL_MASS_LOSS_PERCENT - total_mass_loss
    condensable_margin = MAX_COLLECTED_VOLATILE_PERCENT - condensable
    binding = (
        "total-mass-loss"
        if mass_loss_margin / MAX_TOTAL_MASS_LOSS_PERCENT
        <= condensable_margin / MAX_COLLECTED_VOLATILE_PERCENT
        else "collected-volatile-condensable-material"
    )
    return {
        "material": material,
        "total_mass_loss_percent": total_mass_loss,
        "collected_volatile_percent": condensable,
        "total_mass_loss_margin": mass_loss_margin,
        "collected_volatile_margin": condensable_margin,
        "binding_limit": binding,
        "verdict": PERMITTED if mass_loss_ok and condensable_ok else RESTRICTED,
        "acceptable": mass_loss_ok and condensable_ok,
    }


def assess_restricted_metal(metal, mass_fraction, deviation_reference=None):
    """Grade one declared metal against the trace it is allowed at."""
    if metal not in RESTRICTED_METALS:
        raise ValueError("unknown restricted metal %r" % (metal,))
    fraction = _require_fraction("mass fraction of %s" % metal, mass_fraction)
    present = fraction > TRACE_MASS_FRACTION and not _equal(
        fraction, TRACE_MASS_FRACTION
    )
    approved = deviation_reference is not None
    if approved:
        _require_text("deviation reference for %s" % metal, deviation_reference)
    if not present:
        verdict = PERMITTED
    elif approved:
        verdict = PERMITTED_WITH_MITIGATION
    else:
        verdict = RESTRICTED
    return {
        "metal": metal,
        "mass_fraction": fraction,
        "trace_threshold": TRACE_MASS_FRACTION,
        "present_above_trace": present,
        "deviation_reference": deviation_reference,
        "verdict": verdict,
        "acceptable": verdict != RESTRICTED,
    }


def assess_part_restrictions(case):
    """Full clause 6.2.2.2 check on a candidate Class 3 part."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    part_reference = _require_text("part_reference", case.get("part_reference"))
    moisture = assess_moisture_control(case)

    finishes = case.get("finishes")
    if not isinstance(finishes, (list, tuple)) or not finishes:
        raise ValueError("finishes must be a non-empty sequence of finish mappings")
    graded_finishes = [assess_tin_finish(finish) for finish in finishes]
    seen = set()
    for graded in graded_finishes:
        if graded["surface"] in seen:
            raise ValueError("finish surface %s declared twice" % graded["surface"])
        seen.add(graded["surface"])

    organics = case.get("organics", [])
    if not isinstance(organics, (list, tuple)):
        raise ValueError("organics must be a sequence of outgassing mappings")
    graded_organics = [assess_outgassing(entry) for entry in organics]
    if not moisture["hermetic"] and not graded_organics:
        raise ValueError(
            "a non-hermetic part carries an encapsulant, so at least one "
            "outgassing entry is required"
        )

    declared = case.get("declared_metals", {})
    if not isinstance(declared, dict):
        raise ValueError("declared_metals must be a mapping, got %r" % (declared,))
    stray = set(declared) - set(RESTRICTED_METALS)
    if stray:
        raise ValueError(
            "declared_metals names metals that are not restricted: %s"
            % ", ".join(sorted(stray))
        )
    deviations = case.get("approved_deviations", {})
    if not isinstance(deviations, dict):
        raise ValueError("approved_deviations must be a mapping, got %r" % (deviations,))
    unknown = set(deviations) - set(RESTRICTED_METALS)
    if unknown:
        raise ValueError(
            "approved_deviations names unknown metals: %s" % ", ".join(sorted(unknown))
        )
    graded_metals = [
        assess_restricted_metal(metal, declared.get(metal, 0.0), deviations.get(metal))
        for metal in RESTRICTED_METALS
    ]

    findings = list(moisture["findings"])
    mitigations = []
    if moisture["verdict"] == PERMITTED_WITH_MITIGATION:
        if moisture["bake_required"]:
            mitigations.append(
                "hold the recorded bake of %s as an assembly condition" % part_reference
            )
        else:
            mitigations.append(
                "track the remaining floor life of %.3f on %s through assembly"
                % (moisture["budget_remaining"], part_reference)
            )
    for graded in graded_finishes:
        if graded["verdict"] == RESTRICTED:
            findings.append(
                "%s carries a tin mass fraction of %.4f against a %.2f threshold "
                "and no finish re-work; a whisker short is not screened out later"
                % (graded["surface"], graded["tin_mass_fraction"], graded["threshold"])
            )
            mitigations.append(
                "re-work the %s finish or substitute a lead-bearing alloy"
                % graded["surface"]
            )
        elif graded["verdict"] == PERMITTED_WITH_MITIGATION:
            mitigations.append(
                "hold the %s finish re-work (%s) as a procurement condition"
                % (graded["surface"], graded["mitigation"])
            )
    for graded in graded_organics:
        if not graded["acceptable"]:
            findings.append(
                "%s fails the %s limit, so it contaminates surfaces far from the "
                "part it sits on" % (graded["material"], graded["binding_limit"])
            )
            mitigations.append(
                "substitute or vacuum-bake %s before it enters the build"
                % graded["material"]
            )
    for graded in graded_metals:
        if graded["verdict"] == RESTRICTED:
            findings.append(
                "%s is present at a mass fraction of %.5f, above the trace the "
                "restriction allows, with no agreed deviation"
                % (graded["metal"], graded["mass_fraction"])
            )
            mitigations.append(
                "remove %s from the part or agree a deviation before purchase"
                % graded["metal"]
            )
        elif graded["verdict"] == PERMITTED_WITH_MITIGATION:
            mitigations.append(
                "carry the agreed %s deviation (%s) into the procurement file"
                % (graded["metal"], graded["deviation_reference"])
            )

    if findings:
        verdict = RESTRICTED
    elif mitigations:
        verdict = PERMITTED_WITH_MITIGATION
    else:
        verdict = PERMITTED
    tightest = min(graded_finishes, key=lambda graded: graded["whisker_margin"])
    return {
        "part_reference": part_reference,
        "verdict": verdict,
        "acceptable": verdict != RESTRICTED,
        "moisture": moisture,
        "finishes": graded_finishes,
        "organics": graded_organics,
        "metals": graded_metals,
        "tightest_finish": tightest["surface"],
        "tightest_whisker_margin": tightest["whisker_margin"],
        "required_mitigations": mitigations,
        "findings": findings,
    }
