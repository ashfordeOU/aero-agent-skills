#!/usr/bin/env python3
"""Resistivity measurement owed whenever a coverglass carries a conductive coating.

Anchor: ECSS-E-ST-20-08C clause 8.7.7. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The clause is conditional, and the condition is the whole difficulty. A
plain coverglass owes nothing here. A coverglass whose stack includes a
conductive layer owes a resistivity measurement, and the obligation
follows the build state rather than the test plan -- a lot that changed
from a bare anti-reflection stack to one carrying a transparent
conducting oxide acquires the obligation on the day the stack changed,
not on the day someone remembers to add the test.

Two failure directions matter and they are not symmetric. Declaring the
measurement unnecessary on a stack nobody characterised treats an
unknown as a zero, and the coverglass that ships is the one whose charge
bleed path was never demonstrated. Declaring it necessary on a stack
that plainly has no conductive layer only costs bench time.

Reduction routes for the measurement itself:

    concentric-ring     two coaxial electrodes, k = 2 pi / ln(Do / Di)
    four-point-collinear  four in-line probes, k = pi / ln(2)

Both turn a measured resistance into a sheet resistance in ohms per
square, which is the quantity a drawing ceiling is written against,
because a surface resistivity does not depend on the size of the square.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

KNOWN_CONDUCTIVE_COATINGS = (
    "indium-tin-oxide",
    "tin-oxide",
    "antimony-tin-oxide",
    "aluminium-doped-zinc-oxide",
)

KNOWN_NON_CONDUCTIVE_COATINGS = (
    "magnesium-fluoride",
    "silicon-dioxide",
    "titanium-dioxide",
    "tantalum-pentoxide",
    "aluminium-oxide",
)

CONCENTRIC_RING = "concentric-ring"
FOUR_POINT_COLLINEAR = "four-point-collinear"
REDUCTION_ROUTES = (CONCENTRIC_RING, FOUR_POINT_COLLINEAR)

# Collinear four-point correction for a thin film on an insulating
# substrate, valid while the probe span is small against the specimen.
FOUR_POINT_THIN_FILM_FACTOR = math.pi / math.log(2.0)

# The probe span has to stay under this share of the smallest specimen
# dimension before the semi-infinite thin-film factor applies.
MAX_PROBE_SPAN_SHARE = 0.2

# Oxide coating resistivity moves with adsorbed moisture, so the ambient
# is part of the measurement rather than a note beside it.
AMBIENT_HUMIDITY_BAND_PERCENT = (30.0, 60.0)

OBLIGATION_NOT_TRIGGERED = "resistivity-measurement-not-required"
OBLIGATION_MET = "resistivity-measurement-satisfied"
OBLIGATION_OUTSTANDING = "resistivity-measurement-outstanding"

REQUIRED_MEASUREMENT_EVIDENCE = (
    "ambient_humidity_percent",
    "probe_current_band_a",
    "reduction_route",
    "site_readings",
    "surface_resistivity_ceiling_ohm_per_square",
)

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A geometry factor is a ratio of logarithms and a ceiling is written
    in round numbers, so a value that should land on a limit can miss it
    by a few units in the last place. The limit is never relaxed; only
    the comparison tolerates the representation error, which is why no
    caller uses a bare >= on a derived float.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def layer_is_conductive(layer):
    """Whether one declared coating layer conducts.

    An explicit declaration wins. Otherwise the material is looked up.
    A material in neither list and with nothing declared raises, because
    reading an uncharacterised layer as insulating is the reading that
    lets an obligation disappear quietly.
    """
    if not isinstance(layer, dict):
        raise ValueError("coating layer must be a mapping, got %r" % (layer,))
    declared = layer.get("conductive")
    if isinstance(declared, bool):
        return declared
    if declared is not None:
        raise ValueError(
            "layer conductive flag must be true or false, got %r" % (declared,)
        )
    material = layer.get("material")
    if not isinstance(material, str) or not material:
        raise ValueError("coating layer must name a material, got %r" % (material,))
    if material in KNOWN_CONDUCTIVE_COATINGS:
        return True
    if material in KNOWN_NON_CONDUCTIVE_COATINGS:
        return False
    raise ValueError(
        "coating material %r is in neither the conductive nor the "
        "non-conductive list and declares no conductivity; characterise the "
        "layer rather than reading it as insulating" % (material,)
    )


def conductive_layers(coating_stack):
    """Names of the layers in the stack that conduct."""
    if coating_stack is None:
        raise ValueError(
            "coating_stack must be given; an absent stack is not the same as a "
            "bare coverglass"
        )
    if not isinstance(coating_stack, (list, tuple)):
        raise ValueError(
            "coating_stack must be a sequence of layers, got %r" % (coating_stack,)
        )
    found = []
    for layer in coating_stack:
        if layer_is_conductive(layer):
            found.append(layer.get("material", "undeclared-material"))
    return tuple(found)


def measurement_required(coating_stack):
    """Whether clause 8.7.7 obliges a resistivity measurement on this build."""
    return bool(conductive_layers(coating_stack))


def concentric_ring_geometry_factor(inner_diameter_mm, outer_diameter_mm):
    """Geometry factor of a two-electrode concentric ring fixture."""
    inner = _require_positive("inner_diameter_mm", inner_diameter_mm)
    outer = _require_positive("outer_diameter_mm", outer_diameter_mm)
    if not outer > inner:
        raise ValueError(
            "outer electrode diameter %g mm must sit outside the inner %g mm"
            % (outer, inner)
        )
    return 2.0 * math.pi / math.log(outer / inner)


def probe_span_within_specimen(probe_spacing_mm, probe_count, specimen_span_mm):
    """Whether the probe array is small enough for the thin-film factor.

    The collinear correction assumes the film continues well beyond the
    probes. On a coverglass that assumption has to be checked against the
    article rather than assumed from the instrument.
    """
    spacing = _require_positive("probe_spacing_mm", probe_spacing_mm)
    span = _require_positive("specimen_span_mm", specimen_span_mm)
    if not isinstance(probe_count, int) or isinstance(probe_count, bool):
        raise ValueError("probe_count must be a whole number, got %r" % (probe_count,))
    if probe_count < 2:
        raise ValueError("probe_count must be at least two, got %d" % probe_count)
    probe_span = spacing * (probe_count - 1)
    return _at_most(probe_span / span, MAX_PROBE_SPAN_SHARE)


def sheet_resistance_from_concentric_ring(
    resistance_ohm, inner_diameter_mm, outer_diameter_mm
):
    """Sheet resistance in ohms per square from a concentric-ring reading."""
    resistance = _require_positive("resistance_ohm", resistance_ohm)
    factor = concentric_ring_geometry_factor(inner_diameter_mm, outer_diameter_mm)
    return resistance * factor


def sheet_resistance_from_four_point(voltage_v, current_a, correction_factor=None):
    """Sheet resistance in ohms per square from a collinear four-point reading."""
    voltage = _require_non_negative("voltage_v", voltage_v)
    current = _require_positive("current_a", current_a)
    if correction_factor is None:
        factor = FOUR_POINT_THIN_FILM_FACTOR
    else:
        factor = _require_positive("correction_factor", correction_factor)
    return voltage / current * factor


def site_sheet_resistance(site, route):
    """Reduce one measurement site by the route its fixture implies."""
    if not isinstance(site, dict):
        raise ValueError("site reading must be a mapping, got %r" % (site,))
    if route == CONCENTRIC_RING:
        return sheet_resistance_from_concentric_ring(
            site.get("resistance_ohm"),
            site.get("inner_diameter_mm"),
            site.get("outer_diameter_mm"),
        )
    if route == FOUR_POINT_COLLINEAR:
        return sheet_resistance_from_four_point(
            site.get("voltage_v"),
            site.get("current_a"),
            site.get("correction_factor"),
        )
    raise ValueError(
        "unknown reduction route %r; routes are %s"
        % (route, ", ".join(REDUCTION_ROUTES))
    )


def reduce_site_readings(site_readings, route):
    """Sheet resistance of every site, in the order the sites were read."""
    if not isinstance(site_readings, (list, tuple)) or not site_readings:
        raise ValueError(
            "site_readings must be a non-empty sequence, got %r" % (site_readings,)
        )
    return tuple(site_sheet_resistance(site, route) for site in site_readings)


def site_spread_ratio(values):
    """Largest site over the smallest, a measure of coating evenness."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("values must be a non-empty sequence, got %r" % (values,))
    lowest = min(values)
    highest = max(values)
    if lowest <= 0.0:
        raise ValueError("a sheet resistance of %r cannot carry a spread" % (lowest,))
    return highest / lowest


def current_within_band(current_a, band):
    """Whether the drive current sits inside the electrometer's usable band."""
    if not isinstance(band, dict):
        raise ValueError(
            "probe_current_band_a must be a mapping with minimum_a and maximum_a"
        )
    low = _require_positive("probe current minimum_a", band.get("minimum_a"))
    high = _require_positive("probe current maximum_a", band.get("maximum_a"))
    if not high > low:
        raise ValueError(
            "probe current maximum_a %g must sit above minimum_a %g" % (high, low)
        )
    value = _require_positive("current_a", current_a)
    return _at_least(value, low) and _at_most(value, high)


def humidity_within_band(humidity_percent):
    """Whether the ambient was inside the band the measurement is valid over."""
    value = _require_non_negative("ambient_humidity_percent", humidity_percent)
    low, high = AMBIENT_HUMIDITY_BAND_PERCENT
    return _at_least(value, low) and _at_most(value, high)


def missing_measurement_evidence(case):
    """Required measurement inputs the record has not brought."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    return tuple(
        name for name in REQUIRED_MEASUREMENT_EVIDENCE if case.get(name) is None
    )


def assess_surface_resistivity(case):
    """Full clause 8.7.7 judgement of one coverglass build and its record."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    conducting = conductive_layers(case.get("coating_stack"))
    required = bool(conducting)

    if not required:
        return {
            "measurement_required": False,
            "conductive_layers": (),
            "site_sheet_resistance_ohm_per_square": (),
            "worst_sheet_resistance_ohm_per_square": None,
            "verdict": OBLIGATION_NOT_TRIGGERED,
            "accepted": True,
            "findings": [],
        }

    absent = missing_measurement_evidence(case)
    if absent:
        return {
            "measurement_required": True,
            "conductive_layers": conducting,
            "site_sheet_resistance_ohm_per_square": (),
            "worst_sheet_resistance_ohm_per_square": None,
            "verdict": OBLIGATION_OUTSTANDING,
            "accepted": False,
            "findings": [
                "the stack carries a conductive layer (%s) so a resistivity "
                "measurement is owed, and the record is missing: %s"
                % (", ".join(conducting), ", ".join(absent))
            ],
        }

    route = case.get("reduction_route")
    values = reduce_site_readings(case.get("site_readings"), route)
    ceiling = _require_positive(
        "surface_resistivity_ceiling_ohm_per_square",
        case.get("surface_resistivity_ceiling_ohm_per_square"),
    )
    worst = max(values)
    findings = []

    if not _at_most(worst, ceiling):
        findings.append(
            "worst site reads %.3g ohm per square against a ceiling of %.3g; the "
            "coating cannot bleed charge fast enough at that site"
            % (worst, ceiling)
        )

    if not humidity_within_band(case.get("ambient_humidity_percent")):
        findings.append(
            "ambient humidity %.1f%% sits outside the %.0f%% to %.0f%% band the "
            "measurement is valid over; an oxide coating reads a different "
            "resistivity on a dry day"
            % (
                float(case.get("ambient_humidity_percent")),
                AMBIENT_HUMIDITY_BAND_PERCENT[0],
                AMBIENT_HUMIDITY_BAND_PERCENT[1],
            )
        )

    band = case.get("probe_current_band_a")
    for index, site in enumerate(case.get("site_readings")):
        current = site.get("current_a")
        if current is not None and not current_within_band(current, band):
            findings.append(
                "site %d drives %.3g A, outside the electrometer band; the "
                "reading is an instrument artefact rather than a coating figure"
                % (index, float(current))
            )

    if route == FOUR_POINT_COLLINEAR:
        spacing = case.get("probe_spacing_mm")
        specimen = case.get("specimen_span_mm")
        if spacing is not None and specimen is not None:
            if not probe_span_within_specimen(
                spacing, int(case.get("probe_count", 4)), specimen
            ):
                findings.append(
                    "the probe array spans too much of the specimen for the "
                    "thin-film correction; shorten the span or reduce through "
                    "a fixture-specific factor"
                )

    spread = site_spread_ratio(values) if len(values) > 1 else 1.0
    accepted = not findings
    return {
        "measurement_required": True,
        "conductive_layers": conducting,
        "reduction_route": route,
        "site_sheet_resistance_ohm_per_square": values,
        "worst_sheet_resistance_ohm_per_square": worst,
        "site_spread_ratio": spread,
        "surface_resistivity_ceiling_ohm_per_square": ceiling,
        "verdict": OBLIGATION_MET if accepted else OBLIGATION_OUTSTANDING,
        "accepted": accepted,
        "findings": findings,
    }
