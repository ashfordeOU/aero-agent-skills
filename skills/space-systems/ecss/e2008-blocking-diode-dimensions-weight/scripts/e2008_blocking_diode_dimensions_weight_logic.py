#!/usr/bin/env python3
"""Dimensions and weight verification of a blocking diode.

Anchor: ECSS-E-ST-20-08C clause 12.6.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A blocking diode is bought to a control drawing and then mounted into a
space on the panel that it does not own. Four families of feature decide
whether the part that arrived is the part the layout was drawn around:

    lateral outline     the length and width the string layout, the
                        keep-out reservation and the bonding footprint
                        were drawn to
    thickness           the stack height under the coverglass or the
                        potting, and the term the mass follows most
                        directly
    terminal geometry   the two metallised pads the attachments land
                        on -- large enough to be bonded, and large
                        enough to pass the whole string current without
                        turning the joint into the hot spot
    interconnector      where each attachment point actually sits
    placement           against where the drawing put it

A blocking diode differs from a protection diode here in one way that
changes the arithmetic: it sits in series with the string, so both
terminals carry the full string current and both pads are judged, one
at a time, against the same duty. A generous anode does not excuse a
starved cathode.

Each dimensional feature is judged inside its own plus and minus band,
because a diode running long is a different layout problem from one
running short and both differ from one that fits.

The attachment offsets are not judged one axis at a time. A point that
is inside band on each axis separately can still sit outside the round
zone the drawing allows, so the two offsets are combined into one
diametrical true-position value and that value is what is compared.

That same true-position value then grows the measured outline into the
keep-out envelope the layout has to reserve. A part can measure inside
every band and still not fit, because the reservation has to hold the
body wherever the placement tolerance is free to put it.

Mass is not an independent measurement. Outline, thickness and the
declared material density already imply it, so a weighed mass that
disagrees with the implied mass means one of the two came off a
different part.

The coverage floor, current-density ceiling, true-position zone and
mass tolerance below are a declared policy, not a physical constant: a
project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Feature states a measured dimension can occupy (categorized, not scored).
STATE_IN_BAND = "in-band"
STATE_UNDER_BAND = "under-band"
STATE_OVER_BAND = "over-band"

# The dimensional features clause 12.6.2 puts a band on.
DIMENSIONAL_FEATURES = ("length_mm", "width_mm", "thickness_mm")

# Both terminals of a series blocking diode carry the whole string current.
TERMINALS = ("anode", "cathode")

BLOCKING_DIODE_DIMENSIONS_CONFORMING = "blocking-diode-dimensions-conforming"
BLOCKING_DIODE_OUTLINE_OUT_OF_BAND = "blocking-diode-outline-out-of-band"
BLOCKING_DIODE_TERMINAL_GEOMETRY_INADEQUATE = (
    "blocking-diode-terminal-geometry-inadequate"
)
BLOCKING_DIODE_ATTACHMENT_OUT_OF_POSITION = (
    "blocking-diode-attachment-out-of-position"
)
BLOCKING_DIODE_KEEP_OUT_EXCEEDED = "blocking-diode-keep-out-envelope-exceeded"
BLOCKING_DIODE_MASS_INCONSISTENT = "blocking-diode-mass-inconsistent"

DEFAULT_BLOCKING_DIODE_DIMENSION_POLICY = {
    "min_terminal_coverage_fraction": 0.12,
    "max_terminal_current_density_a_per_mm2": 1.5,
    "max_true_position_diameter_mm": 0.25,
    "max_mass_deviation_fraction": 0.05,
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


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number <= 0.0 or number > 1.0:
        raise ValueError("%s must be above 0 and at most 1, got %r" % (name, value))
    return number


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


def validate_blocking_diode_dimension_policy(policy):
    """Check a dimensional acceptance policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction(
        "min_terminal_coverage_fraction",
        policy.get("min_terminal_coverage_fraction"),
    )
    _require_positive(
        "max_terminal_current_density_a_per_mm2",
        policy.get("max_terminal_current_density_a_per_mm2"),
    )
    _require_positive(
        "max_true_position_diameter_mm",
        policy.get("max_true_position_diameter_mm"),
    )
    mass_tolerance = _require_positive(
        "max_mass_deviation_fraction", policy.get("max_mass_deviation_fraction")
    )
    if mass_tolerance >= 1.0:
        raise ValueError(
            "max_mass_deviation_fraction %g admits a part of any mass"
            % (mass_tolerance,)
        )
    return policy


def band_limits(nominal, minus_tol, plus_tol):
    """The low and high limit a drawn feature is allowed to occupy."""
    centre = _require_positive("nominal", nominal)
    minus = _require_non_negative("minus_tol", minus_tol)
    plus = _require_non_negative("plus_tol", plus_tol)
    low = centre - minus
    if low <= 0.0:
        raise ValueError(
            "minus_tol %g takes the %g nominal to or below zero" % (minus, centre)
        )
    return (low, centre + plus)


def feature_state(measured, nominal, minus_tol, plus_tol):
    """Name where a measured feature sits: under, inside or over its band."""
    value = _require_positive("measured", measured)
    low, high = band_limits(nominal, minus_tol, plus_tol)
    if not _at_least(value, low):
        return STATE_UNDER_BAND
    if not _at_most(value, high):
        return STATE_OVER_BAND
    return STATE_IN_BAND


def deviation_fraction(measured, nominal):
    """Signed departure of a measurement from its nominal, as a fraction."""
    value = _require_number("measured", measured)
    centre = _require_positive("nominal", nominal)
    return (value - centre) / centre


def footprint_area_mm2(length_mm, width_mm):
    """The lateral area the blocking diode occupies on the layout."""
    length = _require_positive("length_mm", length_mm)
    width = _require_positive("width_mm", width_mm)
    return length * width


def terminal_coverage_fraction(pad_area_mm2, footprint_mm2):
    """Share of the diode footprint one metallised terminal pad covers."""
    pad = _require_positive("pad_area_mm2", pad_area_mm2)
    footprint = _require_positive("footprint_mm2", footprint_mm2)
    if not _at_most(pad, footprint):
        raise ValueError(
            "terminal pad %g mm2 exceeds the %g mm2 footprint it sits on; one "
            "of the two measurements is wrong" % (pad, footprint)
        )
    return pad / footprint


def terminal_current_density(current_a, pad_area_mm2):
    """String current the terminal has to pass, per unit of pad area."""
    current = _require_positive("current_a", current_a)
    pad = _require_positive("pad_area_mm2", pad_area_mm2)
    return current / pad


def combined_terminal_coverage(pads, footprint_mm2):
    """Coverage of both pads together, refused if they cannot both fit."""
    if not isinstance(pads, dict):
        raise ValueError("pads must be a mapping of terminal to pad area")
    total = 0.0
    for terminal in TERMINALS:
        if terminal not in pads:
            raise ValueError("pad area for the %s terminal is missing" % (terminal,))
        total += _require_positive("%s pad_area_mm2" % (terminal,), pads[terminal])
    footprint = _require_positive("footprint_mm2", footprint_mm2)
    if not _at_most(total, footprint):
        raise ValueError(
            "the two terminal pads total %g mm2 on a %g mm2 footprint; they "
            "cannot both be on the part as measured" % (total, footprint)
        )
    return total / footprint


def true_position_diameter_mm(offset_x_mm, offset_y_mm):
    """Two axis offsets combined into the round zone the point really needs."""
    dx = _require_number("offset_x_mm", offset_x_mm)
    dy = _require_number("offset_y_mm", offset_y_mm)
    return 2.0 * math.hypot(dx, dy)


def worst_true_position_mm(offsets):
    """Largest true-position value across every declared attachment point."""
    if not isinstance(offsets, (list, tuple)):
        raise ValueError("offsets must be a sequence of (x, y) pairs")
    if not offsets:
        raise ValueError("at least one attachment point offset is required")
    values = []
    for pair in offsets:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("each attachment offset must be an (x, y) pair")
        values.append(true_position_diameter_mm(pair[0], pair[1]))
    return max(values)


def keep_out_envelope_mm(length_mm, width_mm, true_position_mm):
    """Outline grown by the placement freedom the layout has to reserve."""
    length = _require_positive("length_mm", length_mm)
    width = _require_positive("width_mm", width_mm)
    zone = _require_non_negative("true_position_mm", true_position_mm)
    return (length + zone, width + zone)


def implied_mass_mg(length_mm, width_mm, thickness_mm, density_g_cm3):
    """Mass the outline, thickness and material density already promise."""
    volume_mm3 = footprint_area_mm2(length_mm, width_mm) * _require_positive(
        "thickness_mm", thickness_mm
    )
    density = _require_positive("density_g_cm3", density_g_cm3)
    # 1 mm3 at 1 g/cm3 weighs exactly 1 mg, so the conversion is the product.
    return volume_mm3 * density


def mass_deviation_fraction(measured_mg, implied_mg):
    """How far the weighed mass stands from the mass the geometry implies."""
    measured = _require_positive("measured_mg", measured_mg)
    implied = _require_positive("implied_mg", implied_mg)
    return (measured - implied) / implied


def assess_blocking_diode_dimensions(
    case, policy=DEFAULT_BLOCKING_DIODE_DIMENSION_POLICY
):
    """Full clause 12.6.2 judgement for one blocking diode measurement sheet."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_blocking_diode_dimension_policy(policy)

    drawing = case.get("drawing")
    if not isinstance(drawing, dict):
        raise ValueError("case is missing a drawing block")
    measured = case.get("measured")
    if not isinstance(measured, dict):
        raise ValueError("case is missing a measured block")
    duty = case.get("duty")
    if not isinstance(duty, dict):
        raise ValueError("case is missing a duty block")

    findings = []
    states = {}
    deviations = {}
    for feature in DIMENSIONAL_FEATURES:
        band = drawing.get(feature)
        if not isinstance(band, dict):
            raise ValueError("drawing is missing the %s band" % (feature,))
        value = measured.get(feature)
        if value is None:
            raise ValueError("measured sheet is missing %s" % (feature,))
        state = feature_state(
            value, band.get("nominal"), band.get("minus_tol"), band.get("plus_tol")
        )
        states[feature] = state
        deviations[feature] = deviation_fraction(value, band.get("nominal"))
        if state != STATE_IN_BAND:
            findings.append(
                "%s measures %.4f mm and sits %s of its drawn band"
                % (feature, float(value), state.replace("-", " "))
            )

    footprint = footprint_area_mm2(measured["length_mm"], measured["width_mm"])

    pads = measured.get("terminal_pad_area_mm2")
    if not isinstance(pads, dict):
        raise ValueError("measured sheet is missing the terminal pad areas")
    combined = combined_terminal_coverage(pads, footprint)

    string_current = _require_positive(
        "string_current_a", duty.get("string_current_a")
    )
    coverage_floor = float(policy["min_terminal_coverage_fraction"])
    density_ceiling = float(policy["max_terminal_current_density_a_per_mm2"])

    coverages = {}
    densities = {}
    terminal_ok = True
    for terminal in TERMINALS:
        pad_area = pads[terminal]
        coverage = terminal_coverage_fraction(pad_area, footprint)
        coverages[terminal] = coverage
        if not _at_least(coverage, coverage_floor):
            terminal_ok = False
            findings.append(
                "the %s pad covers %.4f of the footprint against the %.4f floor "
                "an attachment needs" % (terminal, coverage, coverage_floor)
            )
        density = terminal_current_density(string_current, pad_area)
        densities[terminal] = density
        if not _at_most(density, density_ceiling):
            terminal_ok = False
            findings.append(
                "the %s pad passes %.4f A/mm2 against the %.4f A/mm2 ceiling, so "
                "that terminal is the hot spot" % (terminal, density, density_ceiling)
            )

    true_position = worst_true_position_mm(
        measured.get("interconnector_offsets_mm", [])
    )
    position_zone = float(policy["max_true_position_diameter_mm"])
    position_met = _at_most(true_position, position_zone)
    if not position_met:
        findings.append(
            "the worst attachment point needs a %.4f mm zone against the %.4f mm "
            "the drawing allows" % (true_position, position_zone)
        )

    envelope_length, envelope_width = keep_out_envelope_mm(
        measured["length_mm"], measured["width_mm"], true_position
    )
    keep_out_length = _require_positive(
        "keep_out_length_mm", drawing.get("keep_out_length_mm")
    )
    keep_out_width = _require_positive(
        "keep_out_width_mm", drawing.get("keep_out_width_mm")
    )
    envelope_met = _at_most(envelope_length, keep_out_length) and _at_most(
        envelope_width, keep_out_width
    )
    if not envelope_met:
        findings.append(
            "the grown envelope of %.4f by %.4f mm does not sit inside the "
            "%.4f by %.4f mm keep-out the layout reserved"
            % (envelope_length, envelope_width, keep_out_length, keep_out_width)
        )

    implied = implied_mass_mg(
        measured["length_mm"],
        measured["width_mm"],
        measured["thickness_mm"],
        drawing.get("material_density_g_cm3"),
    )
    mass_deviation = mass_deviation_fraction(measured.get("mass_mg"), implied)
    mass_tolerance = float(policy["max_mass_deviation_fraction"])
    mass_met = _at_most(abs(mass_deviation), mass_tolerance)
    if not mass_met:
        findings.append(
            "the weighed %.4f mg departs from the %.4f mg the outline implies by "
            "%.4f, beyond the %.4f crosscheck tolerance"
            % (float(measured["mass_mg"]), implied, mass_deviation, mass_tolerance)
        )

    result = {
        "feature_states": states,
        "feature_deviations": deviations,
        "footprint_area_mm2": footprint,
        "terminal_coverage_fraction": coverages,
        "combined_terminal_coverage_fraction": combined,
        "terminal_current_density_a_per_mm2": densities,
        "terminal_geometry_met": terminal_ok,
        "worst_true_position_mm": true_position,
        "true_position_met": position_met,
        "keep_out_envelope_mm": (envelope_length, envelope_width),
        "keep_out_envelope_met": envelope_met,
        "implied_mass_mg": implied,
        "mass_deviation_fraction": mass_deviation,
        "mass_consistent": mass_met,
        "findings": findings,
    }

    if any(state != STATE_IN_BAND for state in states.values()):
        result["verdict"] = BLOCKING_DIODE_OUTLINE_OUT_OF_BAND
    elif not terminal_ok:
        result["verdict"] = BLOCKING_DIODE_TERMINAL_GEOMETRY_INADEQUATE
    elif not position_met:
        result["verdict"] = BLOCKING_DIODE_ATTACHMENT_OUT_OF_POSITION
    elif not envelope_met:
        result["verdict"] = BLOCKING_DIODE_KEEP_OUT_EXCEEDED
    elif not mass_met:
        result["verdict"] = BLOCKING_DIODE_MASS_INCONSISTENT
    else:
        result["verdict"] = BLOCKING_DIODE_DIMENSIONS_CONFORMING
    return result
