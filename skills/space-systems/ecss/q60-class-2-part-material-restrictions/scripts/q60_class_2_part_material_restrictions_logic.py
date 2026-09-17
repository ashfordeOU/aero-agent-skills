#!/usr/bin/env python3
"""Packaging and material limits on a Class 2 part choice.

Anchor: ECSS-Q-ST-60C clause 5.2.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Choosing a Class 2 part is limited from two directions at once:

    the case        how long the die is kept away from moisture, which
                    is what a non-hermetic package does not promise on
                    its own
    the content     what the part is made of, because a finish or a
                    plating can grow into, outgas onto or corrode the
                    hardware standing next to it

The Class 2 assurance level does not remove either limit, it changes
what closes them. A non-hermetic case is an available route rather than
an exception, but it is only available against two numbers: a moisture
sensitivity level inside the ceiling the build works to, and a
demonstrated damp life covering the humid hours the mission asks for
with margin on top. A near-pure-tin finish stays restricted, and on
Class 2 it may be carried on an agreed mitigation that removes the
whisker route rather than forcing the part out of the design.

A restricted metal is graded against the trace it is allowed at, not
against its presence. Every real plating carries impurities, so a
presence test refuses parts that are in fact inside the limit while a
trace test answers the question the clause asks.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PACKAGE_STYLES = ("hermetic", "non-hermetic")

TIN_BEARING_FINISHES = ("pure-tin", "tin-lead", "tin-silver-copper", "tin-bismuth")

FINISHES = TIN_BEARING_FINISHES + (
    "gold",
    "nickel-palladium-gold",
    "silver",
    "cadmium",
    "zinc",
)

# Mitigations that actually remove the whisker growth route rather than
# merely recording it. Anything outside this set is a note, not a fix.
WHISKER_MITIGATIONS = (
    "hot-solder-dip-retinning",
    "lead-bearing-solder-reflow",
    "conformal-coat-over-finish",
)

# Metals restricted by trace mass fraction. Cadmium, zinc and mercury
# carry a zero allowance because the mechanism they drive does not need
# a bulk layer; the rest are allowed at an impurity level.
RESTRICTED_METAL_TRACE_LIMITS = {
    "cadmium": 0.0,
    "zinc": 0.0,
    "mercury": 0.0,
    "lithium": 0.005,
    "magnesium": 0.020,
}

# A tin coating leaves the whisker route once enough lead is alloyed in.
MIN_LEAD_MASS_FRACTION = 0.03

DEFAULT_MOISTURE_SENSITIVITY_CEILING = 3
DEFAULT_DAMP_LIFE_MARGIN = 1.5

AXIS_ACCEPTED = "axis-accepted"
AXIS_MITIGATION = "axis-mitigation-required"
AXIS_INCOMPLETE = "axis-evidence-incomplete"
AXIS_REFUSED = "axis-refused"

PART_ACCEPTED = "part-materials-accepted"
PART_MITIGATION = "part-materials-mitigation-required"
PART_INCOMPLETE = "part-materials-evidence-incomplete"
PART_REFUSED = "part-materials-refused"

# Worst verdict wins, so the rollup is a max over this ordering.
_AXIS_SEVERITY = {
    AXIS_ACCEPTED: 0,
    AXIS_MITIGATION: 1,
    AXIS_INCOMPLETE: 2,
    AXIS_REFUSED: 3,
}

_PART_VERDICT_FOR_SEVERITY = {
    0: PART_ACCEPTED,
    1: PART_MITIGATION,
    2: PART_INCOMPLETE,
    3: PART_REFUSED,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_non_negative(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_mass_fraction(name, value):
    value = _require_non_negative(name, value)
    if value > 1.0:
        raise ValueError("%s must not exceed 1.0, got %r" % (name, value))
    return value


def _require_level(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 1 or value > 6:
        raise ValueError("%s must sit between 1 and 6, got %r" % (name, value))
    return value


def _require_reference(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A required damp life is a product of an hour count and a margin, so
    a demonstrated life built to sit exactly on it can land a few units
    in the last place below. The requirement is never lowered; only the
    comparison tolerates the representation error.
    """
    return value >= limit or _equal(value, limit)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _equal(value, limit)


def validate_material_policy(policy):
    """Check a project material policy is usable before anything is graded."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    ceiling = policy.get(
        "moisture_sensitivity_ceiling", DEFAULT_MOISTURE_SENSITIVITY_CEILING
    )
    _require_level("moisture_sensitivity_ceiling", ceiling)
    margin = policy.get("damp_life_margin", DEFAULT_DAMP_LIFE_MARGIN)
    margin = _require_positive("damp_life_margin", margin)
    if margin < 1.0 and not _equal(margin, 1.0):
        raise ValueError("damp_life_margin must not sit below 1.0, got %r" % margin)
    limits = policy.get("restricted_metal_trace_limits", RESTRICTED_METAL_TRACE_LIMITS)
    if not isinstance(limits, dict) or not limits:
        raise ValueError("restricted_metal_trace_limits must be a non-empty mapping")
    for metal, limit in limits.items():
        _require_reference("restricted metal name", metal)
        _require_mass_fraction("trace limit for %s" % metal, limit)
    return {
        "moisture_sensitivity_ceiling": ceiling,
        "damp_life_margin": margin,
        "restricted_metal_trace_limits": dict(limits),
    }


def required_damp_life_hours(mission_humid_hours, margin=DEFAULT_DAMP_LIFE_MARGIN):
    """Damp life a non-hermetic Class 2 part has to demonstrate."""
    hours = _require_non_negative("mission_humid_hours", mission_humid_hours)
    factor = _require_positive("margin", margin)
    if factor < 1.0 and not _equal(factor, 1.0):
        raise ValueError("margin must not sit below 1.0, got %r" % factor)
    return hours * factor


def assess_packaging(part, policy=None):
    """Grade the case style of one candidate part."""
    settings = validate_material_policy(policy or {})
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    style = _require_choice("package_style", part.get("package_style"), PACKAGE_STYLES)
    humid_hours = _require_non_negative(
        "mission_humid_hours", part.get("mission_humid_hours", 0.0)
    )
    required = required_damp_life_hours(humid_hours, settings["damp_life_margin"])
    result = {
        "axis": "packaging",
        "package_style": style,
        "required_damp_life_hours": required,
        "moisture_sensitivity_level": None,
        "moisture_sensitivity_ceiling": settings["moisture_sensitivity_ceiling"],
        "demonstrated_damp_life_hours": None,
        "damp_life_headroom_hours": None,
        "findings": [],
    }
    if style == "hermetic":
        result["verdict"] = AXIS_ACCEPTED
        return result

    level = part.get("moisture_sensitivity_level")
    demonstrated = part.get("demonstrated_damp_life_hours")
    if level is None or demonstrated is None:
        result["verdict"] = AXIS_INCOMPLETE
        result["findings"].append(
            "a non-hermetic case needs both a moisture sensitivity level and a "
            "demonstrated damp life; without them the case is unproven, not allowed"
        )
        return result

    level = _require_level("moisture_sensitivity_level", level)
    demonstrated = _require_non_negative(
        "demonstrated_damp_life_hours", demonstrated
    )
    result["moisture_sensitivity_level"] = level
    result["demonstrated_damp_life_hours"] = demonstrated
    result["damp_life_headroom_hours"] = demonstrated - required

    level_ok = level <= settings["moisture_sensitivity_ceiling"]
    life_ok = _at_least(demonstrated, required)
    if not level_ok:
        result["findings"].append(
            "moisture sensitivity level %d sits above the ceiling of %d this build "
            "works to" % (level, settings["moisture_sensitivity_ceiling"])
        )
    if not life_ok:
        result["findings"].append(
            "demonstrated damp life of %.4g h does not cover the %.4g h the mission "
            "asks for with margin" % (demonstrated, required)
        )
    result["verdict"] = AXIS_ACCEPTED if (level_ok and life_ok) else AXIS_REFUSED
    return result


def assess_finish(finish):
    """Grade one surface finish against the whisker and barred-metal limits."""
    if not isinstance(finish, dict):
        raise ValueError("finish must be a mapping, got %r" % (finish,))
    surface = _require_reference("surface", finish.get("surface"))
    material = _require_choice("material", finish.get("material"), FINISHES)
    mitigation = finish.get("mitigation")
    if mitigation is not None:
        mitigation = _require_reference("mitigation", mitigation)
    result = {
        "axis": "finish",
        "surface": surface,
        "material": material,
        "lead_mass_fraction": None,
        "mitigation": mitigation,
        "findings": [],
    }
    if material in ("cadmium", "zinc"):
        result["verdict"] = AXIS_REFUSED
        result["findings"].append(
            "%s carries a %s finish, which no mitigation buys back on a Class 2 "
            "part" % (surface, material)
        )
        return result
    if material not in TIN_BEARING_FINISHES:
        result["verdict"] = AXIS_ACCEPTED
        return result

    lead = finish.get("lead_mass_fraction")
    if lead is None:
        result["verdict"] = AXIS_INCOMPLETE
        result["findings"].append(
            "%s carries a tin-bearing finish with no lead mass fraction declared; "
            "the whisker question is open, not answered" % surface
        )
        return result
    lead = _require_mass_fraction("lead_mass_fraction", lead)
    result["lead_mass_fraction"] = lead
    if _at_least(lead, MIN_LEAD_MASS_FRACTION):
        result["verdict"] = AXIS_ACCEPTED
        return result
    if mitigation is None:
        result["verdict"] = AXIS_REFUSED
        result["findings"].append(
            "%s is a near-pure-tin finish at a lead mass fraction of %.4g with no "
            "mitigation declared" % (surface, lead)
        )
        return result
    if mitigation not in WHISKER_MITIGATIONS:
        result["verdict"] = AXIS_REFUSED
        result["findings"].append(
            "%s declares %r, which records the near-pure-tin finish rather than "
            "removing the whisker route" % (surface, mitigation)
        )
        return result
    result["verdict"] = AXIS_MITIGATION
    result["findings"].append(
        "%s needs %s applied before the part is fitted" % (surface, mitigation)
    )
    return result


def assess_restricted_metal(entry, policy=None):
    """Grade one declared metal against the trace it is allowed at."""
    settings = validate_material_policy(policy or {})
    if not isinstance(entry, dict):
        raise ValueError("metal entry must be a mapping, got %r" % (entry,))
    metal = _require_reference("metal", entry.get("metal"))
    fraction = _require_mass_fraction(
        "mass_fraction for %s" % metal, entry.get("mass_fraction")
    )
    limits = settings["restricted_metal_trace_limits"]
    result = {
        "axis": "restricted-metal",
        "metal": metal,
        "mass_fraction": fraction,
        "trace_limit": None,
        "findings": [],
    }
    if metal not in limits:
        result["verdict"] = AXIS_ACCEPTED
        return result
    limit = float(limits[metal])
    result["trace_limit"] = limit
    if _at_most(fraction, limit):
        result["verdict"] = AXIS_ACCEPTED
        return result
    result["verdict"] = AXIS_REFUSED
    result["findings"].append(
        "%s reaches a mass fraction of %.4g against a trace allowance of %.4g"
        % (metal, fraction, limit)
    )
    return result


def _rollup(axes):
    severity = max(_AXIS_SEVERITY[axis["verdict"]] for axis in axes)
    return _PART_VERDICT_FOR_SEVERITY[severity]


def assess_part(part, policy=None):
    """Full clause 5.2.2.2 material and packaging check on one Class 2 part."""
    settings = validate_material_policy(policy or {})
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    reference = _require_reference("part_reference", part.get("part_reference"))
    finishes = part.get("finishes")
    if not isinstance(finishes, (list, tuple)) or not finishes:
        raise ValueError("part %s needs a non-empty finishes sequence" % reference)
    metals = part.get("declared_metals", [])
    if not isinstance(metals, (list, tuple)):
        raise ValueError("declared_metals must be a sequence for %s" % reference)

    packaging = assess_packaging(part, settings)
    finish_results = [assess_finish(item) for item in finishes]
    seen = set()
    for item in finish_results:
        if item["surface"] in seen:
            raise ValueError(
                "surface %s is declared twice on %s" % (item["surface"], reference)
            )
        seen.add(item["surface"])
    metal_results = [assess_restricted_metal(item, settings) for item in metals]

    axes = [packaging] + finish_results + metal_results
    findings = []
    for axis in axes:
        findings.extend(axis["findings"])
    mitigations = [
        "%s: %s" % (item["surface"], item["mitigation"])
        for item in finish_results
        if item["verdict"] == AXIS_MITIGATION
    ]
    verdict = _rollup(axes)
    return {
        "part_reference": reference,
        "verdict": verdict,
        "allowed": verdict in (PART_ACCEPTED, PART_MITIGATION),
        "packaging": packaging,
        "finishes": finish_results,
        "restricted_metals": metal_results,
        "required_mitigations": mitigations,
        "refused_axes": [
            axis["axis"] for axis in axes if axis["verdict"] == AXIS_REFUSED
        ],
        "open_evidence": [
            axis["axis"] for axis in axes if axis["verdict"] == AXIS_INCOMPLETE
        ],
        "findings": findings,
    }
