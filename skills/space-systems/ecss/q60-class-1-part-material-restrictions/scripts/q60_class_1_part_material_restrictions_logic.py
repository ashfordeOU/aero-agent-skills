#!/usr/bin/env python3
"""Packaging and material limits on a Class 1 part choice.

Anchor: ECSS-Q-ST-60C clause 4.2.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Two families of limit sit on a Class 1 part choice.

Packaging. A hermetic case keeps the die away from moisture for the
whole mission. A non-hermetic case does not, so it is allowed only on a
justification the customer has agreed, and only when two numbers back
the justification up: a moisture sensitivity level inside the ceiling
the build works to, and a demonstrated damp life that covers the humid
hours the mission asks for with margin on top.

Materials. Some metals are kept out of a flight part outright, at
anything above a trace, because they leave the part and attack what is
around them -- cadmium and zinc sublime in vacuum and plate themselves
onto optics and contacts, mercury embrittles aluminium, unalloyed
magnesium corrodes. Tin is different: tin is wanted, it is the
solderability of the finish. What is restricted is tin that is nearly
pure, because a near-pure tin finish grows whiskers, and a whisker is a
short circuit that appears years after the board was accepted. So tin
is graded against a mass-fraction threshold, not banned, and a finish
over the threshold can be brought back by re-working the finish.

The useful output is not a yes or a no. It is the whisker margin on
each finish, the packaging argument with the number that fails it, and
the list of re-work steps the part needs before it can be bought.

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
    "bare-die-on-substrate",
)

HERMETIC_PACKAGES = frozenset(
    ("hermetic-metal-can", "hermetic-ceramic", "hermetic-glass")
)

RESTRICTED_MATERIALS = (
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

MAX_TIN_MASS_FRACTION = 0.97
TRACE_MASS_FRACTION = 1.0e-4
MAX_MOISTURE_SENSITIVITY_LEVEL = 3
HUMID_LIFE_MARGIN = 2.0

PERMITTED = "class-1-selection-permitted"
PERMITTED_WITH_MITIGATION = "class-1-selection-permitted-with-mitigation"
RESTRICTED = "class-1-selection-restricted"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_fraction(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must sit between 0 and 1, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A mass fraction and a life ratio are both quotients while the
    thresholds they are graded against are decimal literals, so a value
    built to sit exactly on a threshold can land a few units in the last
    place off it. The threshold is never moved; only the comparison
    tolerates the representation error.
    """
    return value >= limit or _equal(value, limit)


def is_hermetic(package_type):
    """Whether the case keeps the die away from moisture on its own."""
    if package_type not in PACKAGE_TYPES:
        raise ValueError("unknown package_type %r" % (package_type,))
    return package_type in HERMETIC_PACKAGES


def tin_whisker_margin(tin_mass_fraction):
    """Distance from the near-pure-tin threshold; negative means over it."""
    fraction = _require_fraction("tin_mass_fraction", tin_mass_fraction)
    return MAX_TIN_MASS_FRACTION - fraction


def assess_finish(finish):
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
    over_threshold = _at_least(fraction, MAX_TIN_MASS_FRACTION)
    if not over_threshold:
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
        "near_pure_tin": over_threshold,
        "mitigation": mitigation,
        "verdict": verdict,
        "acceptable": verdict != RESTRICTED,
    }


def assess_material(material, mass_fraction, deviation_reference=None):
    """Grade one declared material against the outright restrictions."""
    if material not in RESTRICTED_MATERIALS:
        raise ValueError("unknown restricted material %r" % (material,))
    fraction = _require_fraction("mass fraction of %s" % material, mass_fraction)
    present = fraction > TRACE_MASS_FRACTION and not _equal(
        fraction, TRACE_MASS_FRACTION
    )
    approved = deviation_reference is not None
    if approved:
        _require_text("deviation reference for %s" % material, deviation_reference)
    if not present:
        verdict = PERMITTED
    elif approved:
        verdict = PERMITTED_WITH_MITIGATION
    else:
        verdict = RESTRICTED
    return {
        "material": material,
        "mass_fraction": fraction,
        "trace_threshold": TRACE_MASS_FRACTION,
        "present_above_trace": present,
        "deviation_reference": deviation_reference,
        "verdict": verdict,
        "acceptable": verdict != RESTRICTED,
    }


def humid_life_ratio(humid_operating_hours, demonstrated_humid_life_hours):
    """Demonstrated damp life against the humid hours asked for, with margin."""
    required = _require_positive("humid_operating_hours", humid_operating_hours)
    demonstrated = _require_positive(
        "demonstrated_humid_life_hours", demonstrated_humid_life_hours
    )
    return demonstrated / (required * HUMID_LIFE_MARGIN)


def assess_packaging(case):
    """Grade the case style, and for a non-hermetic one the argument behind it."""
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
            "humid_life_ratio": None,
            "verdict": PERMITTED,
            "acceptable": True,
            "findings": findings,
        }
    approved = _require_flag(
        "non_hermetic_justification_approved",
        case.get("non_hermetic_justification_approved"),
    )
    level = case.get("moisture_sensitivity_level")
    if not isinstance(level, int) or isinstance(level, bool):
        raise ValueError(
            "a non-hermetic case needs an integer moisture_sensitivity_level"
        )
    if level < 1 or level > 6:
        raise ValueError("moisture_sensitivity_level must sit in 1..6, got %r" % (level,))
    ratio = humid_life_ratio(
        case.get("humid_operating_hours"),
        case.get("demonstrated_humid_life_hours"),
    )
    if not approved:
        findings.append(
            "the non-hermetic case carries no agreed justification, so the part "
            "cannot be taken to a Class 1 procurement decision"
        )
    if level > MAX_MOISTURE_SENSITIVITY_LEVEL:
        findings.append(
            "moisture sensitivity level %d sits above the level %d ceiling"
            % (level, MAX_MOISTURE_SENSITIVITY_LEVEL)
        )
    if not _at_least(ratio, 1.0):
        findings.append(
            "demonstrated damp life covers only %.3f of the humid hours the "
            "mission asks for once the margin is applied" % ratio
        )
    acceptable = not findings
    return {
        "package_type": package_type,
        "hermetic": False,
        "justification_approved": approved,
        "moisture_sensitivity_level": level,
        "moisture_sensitivity_ceiling": MAX_MOISTURE_SENSITIVITY_LEVEL,
        "humid_life_ratio": ratio,
        "verdict": PERMITTED_WITH_MITIGATION if acceptable else RESTRICTED,
        "acceptable": acceptable,
        "findings": findings,
    }


def assess_part_restrictions(case):
    """Full clause 4.2.2.2 check on a candidate Class 1 part."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    part_reference = _require_text("part_reference", case.get("part_reference"))
    packaging = assess_packaging(case)

    finishes = case.get("finishes")
    if not isinstance(finishes, (list, tuple)) or not finishes:
        raise ValueError("finishes must be a non-empty sequence of finish mappings")
    graded_finishes = [assess_finish(finish) for finish in finishes]
    seen = set()
    for graded in graded_finishes:
        if graded["surface"] in seen:
            raise ValueError("finish surface %s declared twice" % graded["surface"])
        seen.add(graded["surface"])

    declared = case.get("declared_materials", {})
    if not isinstance(declared, dict):
        raise ValueError("declared_materials must be a mapping, got %r" % (declared,))
    stray = set(declared) - set(RESTRICTED_MATERIALS)
    if stray:
        raise ValueError(
            "declared_materials names materials that are not restricted: %s"
            % ", ".join(sorted(stray))
        )
    deviations = case.get("approved_deviations", {})
    if not isinstance(deviations, dict):
        raise ValueError("approved_deviations must be a mapping, got %r" % (deviations,))
    unknown = set(deviations) - set(RESTRICTED_MATERIALS)
    if unknown:
        raise ValueError(
            "approved_deviations names unknown materials: %s"
            % ", ".join(sorted(unknown))
        )
    graded_materials = [
        assess_material(material, declared.get(material, 0.0), deviations.get(material))
        for material in RESTRICTED_MATERIALS
    ]

    findings = list(packaging["findings"])
    required_mitigations = []
    for graded in graded_finishes:
        if graded["verdict"] == RESTRICTED:
            findings.append(
                "%s carries a tin mass fraction of %.4f against a %.2f threshold "
                "and no finish re-work; a whisker short is not screened out later"
                % (graded["surface"], graded["tin_mass_fraction"], graded["threshold"])
            )
            required_mitigations.append(
                "re-work the %s finish or substitute a lead-bearing alloy"
                % graded["surface"]
            )
        elif graded["verdict"] == PERMITTED_WITH_MITIGATION:
            required_mitigations.append(
                "hold the %s finish re-work (%s) as a procurement condition"
                % (graded["surface"], graded["mitigation"])
            )
    for graded in graded_materials:
        if graded["verdict"] == RESTRICTED:
            findings.append(
                "%s is present at a mass fraction of %.5f, above the trace the "
                "restriction allows, with no agreed deviation"
                % (graded["material"], graded["mass_fraction"])
            )
            required_mitigations.append(
                "remove %s from the part or agree a deviation before purchase"
                % graded["material"]
            )
        elif graded["verdict"] == PERMITTED_WITH_MITIGATION:
            required_mitigations.append(
                "carry the agreed %s deviation (%s) into the procurement file"
                % (graded["material"], graded["deviation_reference"])
            )
    if packaging["verdict"] == PERMITTED_WITH_MITIGATION:
        required_mitigations.append(
            "carry the agreed non-hermetic justification into the procurement file"
        )

    blocked = bool(findings)
    if blocked:
        verdict = RESTRICTED
    elif required_mitigations:
        verdict = PERMITTED_WITH_MITIGATION
    else:
        verdict = PERMITTED
    tightest = min(graded_finishes, key=lambda graded: graded["whisker_margin"])
    return {
        "part_reference": part_reference,
        "verdict": verdict,
        "acceptable": verdict != RESTRICTED,
        "packaging": packaging,
        "finishes": graded_finishes,
        "materials": graded_materials,
        "tightest_finish": tightest["surface"],
        "tightest_whisker_margin": tightest["whisker_margin"],
        "required_mitigations": required_mitigations,
        "findings": findings,
    }
