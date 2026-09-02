#!/usr/bin/env python3
"""GD&T basics logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, asme-y14-5: proprietary,
reference-only): geometric dimensioning and tolerancing per ASME Y14.5
expresses design intent on drawings through feature control frames. A
frame reads symbol | tolerance | datum references, for example
position | diameter 0.5 (M) | A | B (M) | C. The symbol picks the
tolerance category: form (flatness, straightness, circularity,
cylindricity), orientation (perpendicularity, parallelism, angularity),
location (position), profile, or runout. The tolerance value defines
the zone width or diameter, and the optional diameter symbol marks a
cylindrical zone. Datum references establish the datum reference
frame (primary, secondary, tertiary) that orients the zone. Material
condition modifiers on the tolerance cell (M = maximum material
condition, L = least material condition, S = regardless of feature
size) change how much tolerance is available: at MMC the stated
tolerance is the whole budget, and any departure of the actual
feature size from the MMC size adds bonus tolerance. Drawings and
published tables are never reproduced here.
"""

import math
import re

FORM_SYMBOLS = ("flatness", "straightness", "circularity", "cylindricity")
ORIENTATION_SYMBOLS = ("perpendicularity", "parallelism", "angularity")
LOCATION_SYMBOLS = ("position",)
PROFILE_SYMBOLS = ("profile",)
RUNOUT_SYMBOLS = ("circular-runout", "total-runout", "runout")

ALL_SYMBOLS = (
    FORM_SYMBOLS + ORIENTATION_SYMBOLS + LOCATION_SYMBOLS
    + PROFILE_SYMBOLS + RUNOUT_SYMBOLS
)

ZONE_TYPES = {
    "flatness": "two parallel planes",
    "straightness": "two parallel lines on a surface or a cylinder for an axis",
    "circularity": "annulus between two concentric circles",
    "cylindricity": "annular space between two coaxial cylinders",
    "perpendicularity": "two parallel planes or a cylinder, oriented to the datum",
    "parallelism": "two parallel planes or a cylinder, parallel to the datum",
    "angularity": "two parallel planes or a cylinder at the basic angle to the datum",
    "position": "cylindrical zone, diameter about the true position",
    "profile": "uniform boundary offset from the true profile",
    "circular-runout": "annular zone in a plane perpendicular to the datum axis",
    "total-runout": "cylindrical or annular zone along the datum axis",
    "runout": "annular zone referenced to the datum axis",
}

MODIFIER_MEANINGS = {
    "M": "maximum material condition (MMC): the stated tolerance applies at the MMC size and grows with departure from MMC",
    "L": "least material condition (LMC): the stated tolerance applies at the LMC size and grows with departure from LMC",
    "S": "regardless of feature size (RFS): no bonus tolerance, the stated tolerance applies at any feature size",
}

_TOL_RE = re.compile(r"^(?P<dia>\u2300?)(?P<value>[0-9]*\.?[0-9]+)(?:\((?P<mod>[MLS])\))?$")
_DATUM_RE = re.compile(r"^(?P<letter>[A-Za-z]{1,2})(?:\((?P<mod>[MLS])\))?$")


def _finite(value, label):
    """Require a finite real number; raise ValueError otherwise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if not math.isfinite(float(value)):
        raise ValueError("%s must be finite, got %r" % (label, value))


def _check_symbol(symbol):
    """Validate a geometric characteristic symbol name."""
    if symbol not in ALL_SYMBOLS:
        raise ValueError(
            "unknown geometric characteristic symbol %r (known: %s)"
            % (symbol, ", ".join(ALL_SYMBOLS))
        )


def parse_feature_control_frame(frame):
    """Parse a feature control frame string into its parts.

    Format: "symbol|tolerance[modifier]|datum[modifier]|..." with the
    pipe as the cell separator, for example
    "position|diameter 0.5(M)|A|B(M)|C" or "flatness|0.2". The
    tolerance cell may carry the diameter symbol and one of the
    material condition modifiers M, L, or S in parentheses; each datum
    cell is a letter (primary, secondary, tertiary) with an optional
    modifier. Form tolerances carry no datum references.

    Returns a dict with keys: symbol, tolerance (float, may be 0.0 for
    zero tolerance at MMC), diameter (bool), modifier (None, "M", "L",
    or "S"), and datums (list of {"letter", "modifier"} dicts).
    Raises ValueError on any malformed cell, unknown symbol, negative
    tolerance, invalid modifier, more than three datums, or a form
    tolerance that references datums.
    """
    if not isinstance(frame, str) or not frame.strip():
        raise ValueError("feature control frame must be a non-empty string: %r" % (frame,))
    cells = [c.strip() for c in frame.split("|")]
    if len(cells) < 2:
        raise ValueError("feature control frame needs symbol and tolerance cells: %r" % (frame,))
    symbol = cells[0].strip().lower()
    _check_symbol(symbol)
    tol_match = _TOL_RE.match(cells[1])
    if not tol_match:
        raise ValueError("malformed tolerance cell %r in %r" % (cells[1], frame))
    tolerance = float(tol_match.group("value"))
    if tolerance < 0.0:
        raise ValueError("tolerance must be non-negative, got %r" % (cells[1],))
    if len(cells) > 5:
        raise ValueError("feature control frame allows at most 3 datum references: %r" % (frame,))
    datums = []
    for cell in cells[2:]:
        m = _DATUM_RE.match(cell)
        if not m:
            raise ValueError("malformed datum cell %r in %r" % (cell, frame))
        datums.append(
            {"letter": m.group("letter").upper(), "modifier": m.group("mod")}
        )
    if symbol in FORM_SYMBOLS and datums:
        raise ValueError(
            "form tolerance %r cannot reference datums: %r" % (symbol, frame)
        )
    return {
        "symbol": symbol,
        "tolerance": tolerance,
        "diameter": bool(tol_match.group("dia")),
        "modifier": tol_match.group("mod"),
        "datums": datums,
    }


def material_condition_modifier(frame):
    """Material condition modifier of the tolerance cell.

    Returns "M", "L", "S", or None when no modifier is shown (the
    default is RFS, regardless of feature size). Raises ValueError on
    malformed input.
    """
    return parse_feature_control_frame(frame)["modifier"]


def modifier_meaning(modifier):
    """Human-readable meaning of a material condition modifier.

    Accepts "M", "L", "S", or None (no modifier shown, defaults to
    RFS). Unknown values raise ValueError.
    """
    if modifier is None:
        return MODIFIER_MEANINGS["S"]
    if modifier not in MODIFIER_MEANINGS:
        raise ValueError("modifier must be M, L, S, or None, got %r" % (modifier,))
    return MODIFIER_MEANINGS[modifier]


def tolerance_zone_type(symbol):
    """Tolerance zone shape implied by a geometric characteristic symbol."""
    _check_symbol(symbol)
    return ZONE_TYPES[symbol]


def tolerance_category(symbol):
    """Categorize a symbol: form, orientation, location, profile, runout."""
    _check_symbol(symbol)
    if symbol in FORM_SYMBOLS:
        return "form"
    if symbol in ORIENTATION_SYMBOLS:
        return "orientation"
    if symbol in LOCATION_SYMBOLS:
        return "location"
    if symbol in PROFILE_SYMBOLS:
        return "profile"
    return "runout"


def mmc_size(limits, part_type):
    """Size of the feature at maximum material condition.

    limits: (lower, upper) size limits in any consistent length unit.
    part_type: "hole" (internal feature, MMC is the smallest hole) or
    "pin" (external feature, MMC is the largest pin). Raises ValueError
    on invalid limits or part type.
    """
    return _boundary_size(limits, part_type, mmc=True)


def lmc_size(limits, part_type):
    """Size of the feature at least material condition.

    limits: (lower, upper) size limits. part_type: "hole" (LMC is the
    largest hole) or "pin" (LMC is the smallest pin).
    """
    return _boundary_size(limits, part_type, mmc=False)


def _boundary_size(limits, part_type, mmc):
    lower, upper = limits
    _finite(lower, "lower limit")
    _finite(upper, "upper limit")
    if lower >= upper:
        raise ValueError("size limits must satisfy lower < upper: %r" % (limits,))
    if part_type not in ("hole", "pin"):
        raise ValueError("part_type must be 'hole' or 'pin', got %r" % (part_type,))
    hole_mmc = lower
    if part_type == "hole":
        return hole_mmc if mmc else upper
    return upper if mmc else lower


def bonus_tolerance_at_mmc(actual_size, mmc_size_value, part_type):
    """Bonus tolerance from the MMC modifier.

    For a hole the MMC size is the smallest hole and the bonus is the
    actual size minus the MMC size; for a pin the MMC size is the
    largest pin and the bonus is the MMC size minus the actual size.
    The bonus is zero at MMC and grows as the feature departs from MMC.
    An actual size beyond the MMC boundary (violating the size limits)
    raises ValueError.
    """
    _finite(actual_size, "actual_size")
    _finite(mmc_size_value, "mmc_size")
    if part_type not in ("hole", "pin"):
        raise ValueError("part_type must be 'hole' or 'pin', got %r" % (part_type,))
    if part_type == "hole":
        if actual_size < mmc_size_value:
            raise ValueError(
                "hole actual size %r below MMC size %r violates the size limits"
                % (actual_size, mmc_size_value)
            )
        return actual_size - mmc_size_value
    if actual_size > mmc_size_value:
        raise ValueError(
            "pin actual size %r above MMC size %r violates the size limits"
            % (actual_size, mmc_size_value)
        )
    return mmc_size_value - actual_size


def bonus_tolerance_at_lmc(actual_size, lmc_size_value, part_type):
    """Bonus tolerance from the LMC modifier.

    For a hole the LMC size is the largest hole and the bonus is the
    LMC size minus the actual size; for a pin the LMC size is the
    smallest pin and the bonus is the actual size minus the LMC size.
    The bonus is zero at LMC and grows as the feature departs from LMC.
    An actual size beyond the LMC boundary raises ValueError.
    """
    _finite(actual_size, "actual_size")
    _finite(lmc_size_value, "lmc_size")
    if part_type not in ("hole", "pin"):
        raise ValueError("part_type must be 'hole' or 'pin', got %r" % (part_type,))
    if part_type == "hole":
        if actual_size > lmc_size_value:
            raise ValueError(
                "hole actual size %r above LMC size %r violates the size limits"
                % (actual_size, lmc_size_value)
            )
        return lmc_size_value - actual_size
    if actual_size < lmc_size_value:
        raise ValueError(
            "pin actual size %r below LMC size %r violates the size limits"
            % (actual_size, lmc_size_value)
        )
    return actual_size - lmc_size_value


def total_tolerance_at_mmc(stated_tolerance, actual_size, mmc_size_value, part_type):
    """Total tolerance budget at MMC: stated tolerance plus bonus."""
    _finite(stated_tolerance, "stated_tolerance")
    if stated_tolerance < 0.0:
        raise ValueError("stated_tolerance must be non-negative, got %r" % (stated_tolerance,))
    return stated_tolerance + bonus_tolerance_at_mmc(
        actual_size, mmc_size_value, part_type
    )


def interpret_feature_control_frame(frame, actual_size=None, mmc_size_value=None,
                                    part_type=None):
    """Full interpretation of a feature control frame.

    Returns a dict with the parsed symbol, tolerance, diameter flag,
    modifier, modifier meaning, zone type, tolerance category, and the
    datum reference list. When the modifier is M and the actual size
    and MMC size are supplied, the dict also carries the bonus
    tolerance and the total tolerance (stated plus bonus).
    """
    parsed = parse_feature_control_frame(frame)
    result = {
        "symbol": parsed["symbol"],
        "tolerance": parsed["tolerance"],
        "diameter": parsed["diameter"],
        "modifier": parsed["modifier"],
        "modifier_meaning": modifier_meaning(parsed["modifier"]),
        "zone_type": tolerance_zone_type(parsed["symbol"]),
        "category": tolerance_category(parsed["symbol"]),
        "datums": parsed["datums"],
    }
    if parsed["modifier"] == "M":
        if actual_size is not None or mmc_size_value is not None:
            if actual_size is None or mmc_size_value is None or part_type is None:
                raise ValueError(
                    "MMC bonus needs actual_size, mmc_size, and part_type together"
                )
            bonus = bonus_tolerance_at_mmc(actual_size, mmc_size_value, part_type)
            result["bonus_tolerance"] = bonus
            result["total_tolerance"] = parsed["tolerance"] + bonus
    return result
