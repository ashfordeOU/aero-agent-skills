#!/usr/bin/env python3
"""Mounting-base isolator representativeness for an electromagnetic-
compatibility test setup.

Anchor: ECSS-E-ST-20-07C clause 5.2.6.3 (paraphrased into an
implementable procedure; no verbatim standard text).

The clause is a representativeness rule. Where the flight installation
puts isolating hardware between a unit's feet and its mounting panel,
the test setup has to reproduce that hardware rather than bolting the
unit flat onto the bench ground plane. The isolator stack is part of
the chassis return path: removing it lowers the chassis-to-panel
impedance the flight build really has, which understates conducted
emission and misdirects the current division in a susceptibility run.

Offline, deterministic, python3 standard library only.
"""

import math

MOUNTING_CATEGORIES = (
    "hard-mounted",
    "isolator-mounted",
    "stand-off-mounted",
)

# isolator family -> (leaves a direct-current chassis path?,
#                     single-isolator interface resistance in ohm)
ISOLATOR_FAMILIES = {
    "elastomeric": (False, 1.0e9),
    "dielectric-washer": (False, 1.0e10),
    "wire-rope": (True, 5.0e-3),
    "conductive-elastomer": (True, 5.0e-2),
}

COPPER_RESISTIVITY_OHM_M = 1.72e-8
DEFAULT_STRAP_LIMIT_OHM = 2.5e-3
DEFAULT_STRAP_ASPECT_LIMIT = 5.0
DEFAULT_STACK_TOLERANCE = 0.10
CHASSIS_PATH_THRESHOLD_OHM = 1.0
REL_TOL = 1e-9


def _mapping(record, label):
    """Return record as a mapping or raise ValueError."""
    if not isinstance(record, dict):
        raise ValueError(
            "%s must be a mapping, got %s" % (label, type(record).__name__)
        )
    return record


def _number(value, label, minimum=None, strict=False):
    """Return value as a finite float, bounded below, or raise ValueError."""
    if value is None:
        raise ValueError("%s is required" % label)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    val = float(value)
    if math.isnan(val) or math.isinf(val):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None:
        if strict and val <= minimum:
            raise ValueError("%s must be > %g, got %g" % (label, minimum, val))
        if not strict and val < minimum:
            raise ValueError("%s must be >= %g, got %g" % (label, minimum, val))
    return val


def _count(value, label):
    """Return value as a non-negative integer or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be >= 0, got %d" % (label, value))
    return value


def _at_most(value, limit):
    """True when value is under limit, absorbing float representation error.

    A computed resistance or aspect ratio that lands a few ULPs above a
    limit it physically meets must not be graded as an exceedance, so the
    comparison absorbs the representation error instead of widening the
    engineering limit itself.
    """
    return value <= limit or math.isclose(value, limit, rel_tol=REL_TOL)


def categorize_mounting_base(record):
    """Categorize a mounting-base record into one of MOUNTING_CATEGORIES.

    record keys: isolator_count (int, default 0), isolator_family (str or
    None), stack_height_mm (float, required when isolator_count > 0),
    stand_off_height_mm (float, default 0.0).
    """
    rec = _mapping(record, "mounting-base record")
    count = _count(rec.get("isolator_count", 0), "isolator_count")
    family = rec.get("isolator_family")
    stand_off = _number(
        rec.get("stand_off_height_mm", 0.0), "stand_off_height_mm", minimum=0.0
    )
    if count > 0:
        if family is None:
            raise ValueError(
                "isolator_family is required when isolator_count is %d" % count
            )
        if family not in ISOLATOR_FAMILIES:
            raise ValueError(
                "unknown isolator_family %r; known families: %s"
                % (family, ", ".join(sorted(ISOLATOR_FAMILIES)))
            )
        _number(rec.get("stack_height_mm"), "stack_height_mm", minimum=0.0,
                strict=True)
        return "isolator-mounted"
    if family is not None:
        raise ValueError(
            "isolator_family %r declared with isolator_count 0" % (family,)
        )
    if stand_off > 0.0:
        return "stand-off-mounted"
    return "hard-mounted"


def isolator_stack_resistance(family, count):
    """Direct-current resistance of count isolators of family, in parallel."""
    if family not in ISOLATOR_FAMILIES:
        raise ValueError(
            "unknown isolator_family %r; known families: %s"
            % (family, ", ".join(sorted(ISOLATOR_FAMILIES)))
        )
    n = _count(count, "isolator_count")
    if n == 0:
        raise ValueError("isolator_count must be > 0 to form a stack")
    _conducts, single = ISOLATOR_FAMILIES[family]
    return single / float(n)


def stack_provides_chassis_path(family, count):
    """True when the isolator stack still carries a direct-current path."""
    resistance = isolator_stack_resistance(family, count)
    conducts = ISOLATOR_FAMILIES[family][0]
    return bool(conducts) and _at_most(resistance, CHASSIS_PATH_THRESHOLD_OHM)


def bonding_strap_resistance(length_mm, width_mm, thickness_mm,
                             resistivity_ohm_m=COPPER_RESISTIVITY_OHM_M):
    """Direct-current resistance of a flat bonding-strap, in ohm."""
    length = _number(length_mm, "length_mm", minimum=0.0, strict=True)
    width = _number(width_mm, "width_mm", minimum=0.0, strict=True)
    thickness = _number(thickness_mm, "thickness_mm", minimum=0.0, strict=True)
    rho = _number(resistivity_ohm_m, "resistivity_ohm_m", minimum=0.0,
                  strict=True)
    area_m2 = (width * 1.0e-3) * (thickness * 1.0e-3)
    return rho * (length * 1.0e-3) / area_m2


def bonding_strap_aspect_ratio(length_mm, width_mm):
    """Length-to-width ratio of a flat bonding-strap (inductance proxy)."""
    length = _number(length_mm, "length_mm", minimum=0.0, strict=True)
    width = _number(width_mm, "width_mm", minimum=0.0, strict=True)
    return length / width


def check_bonding_strap(strap, limit_ohm=DEFAULT_STRAP_LIMIT_OHM,
                        aspect_limit=DEFAULT_STRAP_ASPECT_LIMIT):
    """Grade a bonding-strap on resistance and length-to-width aspect ratio."""
    rec = _mapping(strap, "bonding_strap")
    limit = _number(limit_ohm, "limit_ohm", minimum=0.0, strict=True)
    aspect_max = _number(aspect_limit, "aspect_limit", minimum=0.0, strict=True)
    resistivity = rec.get("resistivity_ohm_m", COPPER_RESISTIVITY_OHM_M)
    resistance = bonding_strap_resistance(
        rec.get("length_mm"), rec.get("width_mm"), rec.get("thickness_mm"),
        resistivity,
    )
    aspect = bonding_strap_aspect_ratio(rec.get("length_mm"), rec.get("width_mm"))
    findings = []
    if not _at_most(resistance, limit):
        findings.append(
            "bonding-strap-resistance-exceeded: %.6f ohm against %.6f ohm"
            % (resistance, limit)
        )
    if not _at_most(aspect, aspect_max):
        findings.append(
            "bonding-strap-aspect-ratio-exceeded: %.2f against %.2f"
            % (aspect, aspect_max)
        )
    return {
        "resistance_ohm": resistance,
        "aspect_ratio": aspect,
        "findings": findings,
    }


def compare_stack_height(flight_mm, test_mm,
                         tolerance_fraction=DEFAULT_STACK_TOLERANCE):
    """Compare isolator stack heights against a fractional allowance."""
    flight = _number(flight_mm, "flight stack_height_mm", minimum=0.0,
                     strict=True)
    test = _number(test_mm, "test stack_height_mm", minimum=0.0)
    fraction = _number(tolerance_fraction, "tolerance_fraction", minimum=0.0,
                       strict=True)
    if fraction > 1.0:
        raise ValueError(
            "tolerance_fraction must be <= 1.0, got %g" % fraction
        )
    allowed = flight * fraction
    deviation = abs(test - flight)
    return {
        "flight_mm": flight,
        "test_mm": test,
        "deviation_mm": deviation,
        "allowed_mm": allowed,
        "within_tolerance": _at_most(deviation, allowed),
    }


def compare_mounting_base(flight, test,
                          tolerance_fraction=DEFAULT_STACK_TOLERANCE):
    """Compare a flight mounting-base record against the test one."""
    flight_category = categorize_mounting_base(flight)
    test_category = categorize_mounting_base(test)
    findings = []
    result = {
        "flight_category": flight_category,
        "test_category": test_category,
        "findings": findings,
    }
    if flight_category != test_category:
        findings.append(
            "mounting-base-category-mismatch: flight %s against test %s"
            % (flight_category, test_category)
        )
        return result
    if flight_category == "isolator-mounted":
        if flight["isolator_family"] != test["isolator_family"]:
            findings.append(
                "isolator-family-mismatch: flight %s against test %s"
                % (flight["isolator_family"], test["isolator_family"])
            )
        if int(flight["isolator_count"]) != int(test["isolator_count"]):
            findings.append(
                "isolator-count-mismatch: flight %d against test %d"
                % (int(flight["isolator_count"]), int(test["isolator_count"]))
            )
        height = compare_stack_height(
            flight.get("stack_height_mm"), test.get("stack_height_mm"),
            tolerance_fraction,
        )
        result["stack_height"] = height
        if not height["within_tolerance"]:
            findings.append(
                "isolator-stack-height-deviation: %.3f mm against %.3f mm allowed"
                % (height["deviation_mm"], height["allowed_mm"])
            )
    elif flight_category == "stand-off-mounted":
        height = compare_stack_height(
            flight.get("stand_off_height_mm"), test.get("stand_off_height_mm"),
            tolerance_fraction,
        )
        result["stand_off_height"] = height
        if not height["within_tolerance"]:
            findings.append(
                "stand-off-height-deviation: %.3f mm against %.3f mm allowed"
                % (height["deviation_mm"], height["allowed_mm"])
            )
    return result


def assess_mounting_isolator_representation(setup):
    """Full clause 5.2.6.3 representativeness assessment for one unit."""
    rec = _mapping(setup, "setup")
    unit_id = rec.get("unit_id")
    if not isinstance(unit_id, str) or not unit_id.strip():
        raise ValueError("setup requires a non-empty unit_id")
    flight = _mapping(rec.get("flight_mounting_base"), "flight_mounting_base")
    test = _mapping(rec.get("test_mounting_base"), "test_mounting_base")
    tolerance = rec.get("tolerance_fraction", DEFAULT_STACK_TOLERANCE)
    findings = []
    if not bool(rec.get("flight_arrangement_known", False)):
        if not bool(rec.get("declared_worst_case", False)):
            findings.append(
                "flight-mounting-arrangement-unknown: neither captured nor "
                "bounded by a declared worst-case arrangement"
            )
    comparison = compare_mounting_base(flight, test, tolerance)
    findings.extend(comparison["findings"])
    stack_resistance = None
    chassis_path = None
    strap_result = None
    if comparison["test_category"] == "isolator-mounted":
        family = test["isolator_family"]
        count = int(test["isolator_count"])
        stack_resistance = isolator_stack_resistance(family, count)
        chassis_path = stack_provides_chassis_path(family, count)
        strap = rec.get("bonding_strap")
        if strap is None:
            if not chassis_path:
                findings.append(
                    "chassis-reference-path-missing: %s isolator stack leaves "
                    "%.3e ohm and no bonding-strap is fitted"
                    % (family, stack_resistance)
                )
        else:
            strap_result = check_bonding_strap(
                strap,
                rec.get("strap_limit_ohm", DEFAULT_STRAP_LIMIT_OHM),
                rec.get("strap_aspect_limit", DEFAULT_STRAP_ASPECT_LIMIT),
            )
            findings.extend(strap_result["findings"])
    return {
        "unit_id": unit_id,
        "flight_category": comparison["flight_category"],
        "test_category": comparison["test_category"],
        "isolator_stack_resistance_ohm": stack_resistance,
        "chassis_path_through_stack": chassis_path,
        "bonding_strap": strap_result,
        "findings": findings,
        "representative": not findings,
    }
