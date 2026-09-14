#!/usr/bin/env python3
"""Coverglass reflectance bandwidth, as a defined quantity.

Anchor: ECSS-E-ST-20-08C clause 8.7.5.4.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A filtered coverglass reflects between two band edges: the cut-on at the
short-wavelength side and the cut-off at the long-wavelength side. This
clause turns that pair into one number. The bandwidth is the span between
the two edges divided by the wavelength at the centre of the band, so it
is a dimensionless ratio rather than a width in nanometres, and two
filters of very different absolute width can carry the same figure.

Making that definition implementable needs three things the bare sentence
leaves open.

The first is the centre. "Centre of the band" is either the arithmetic
mean of the two edges or their geometric mean, and the two are different
wavelengths for every band that is not infinitesimally narrow. The
arithmetic mean is the larger of the two, so it always yields the smaller
bandwidth figure. The gap is negligible for a narrow band and very far
from negligible for a wide one, which is why the convention travels with
the number here and the separation between the two is reported outright.

The second is the unit. The same quantity is written as a fraction in one
document and as a percentage in the next, and a figure of 0.4 and a figure
of 40 describe the same filter. A declaration therefore carries its unit,
and a fraction that could only have been a percentage is refused rather
than silently used.

The third is invertibility. A bandwidth quoted with a centre wavelength is
supposed to reconstruct the edge pair it came from, and under each
convention it does so in closed form -- by halving the span for the
arithmetic centre, and by solving the quadratic in the square root of the
edge ratio for the geometric one. That inverse is what lets a stated
bandwidth, a stated centre and a measured edge pair be checked against one
another instead of taken on trust.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# --- conventions ------------------------------------------------------------

ARITHMETIC_CENTRE = "arithmetic-mean"
GEOMETRIC_CENTRE = "geometric-mean"
CENTRE_CONVENTIONS = (ARITHMETIC_CENTRE, GEOMETRIC_CENTRE)
DEFAULT_CENTRE_CONVENTION = ARITHMETIC_CENTRE

FRACTION_UNIT = "fraction"
PERCENT_UNIT = "percent"
BANDWIDTH_UNITS = (FRACTION_UNIT, PERCENT_UNIT)
DEFAULT_BANDWIDTH_UNIT = FRACTION_UNIT

# An arithmetic-centre bandwidth approaches two only as the cut-on approaches
# zero wavelength, so two is a hard mathematical ceiling for that convention.
ARITHMETIC_BANDWIDTH_CEILING = 2.0

# A geometric-centre bandwidth has no mathematical ceiling, but a declared
# fraction above this one is far more likely to be a percentage that lost its
# unit than a real reflecting band.
IMPLAUSIBLE_FRACTION_CEILING = 2.0

DEFAULT_RELATIVE_TOLERANCE = 1e-9
_ABS_TOL = 1e-12


# --- validation helpers -----------------------------------------------------


def _is_real(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_real(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def validate_centre_convention(convention=DEFAULT_CENTRE_CONVENTION):
    """Return a recognised band-centre convention, or raise."""
    if not isinstance(convention, str):
        raise ValueError("centre convention must be a string, got %r" % (convention,))
    key = convention.strip().lower()
    if key not in CENTRE_CONVENTIONS:
        raise ValueError(
            "unknown band-centre convention %r; expected one of %s"
            % (convention, ", ".join(CENTRE_CONVENTIONS))
        )
    return key


def validate_bandwidth_unit(unit=DEFAULT_BANDWIDTH_UNIT):
    """Return a recognised bandwidth unit, or raise."""
    if not isinstance(unit, str):
        raise ValueError("bandwidth unit must be a string, got %r" % (unit,))
    key = unit.strip().lower()
    if key not in BANDWIDTH_UNITS:
        raise ValueError(
            "unknown bandwidth unit %r; expected one of %s"
            % (unit, ", ".join(BANDWIDTH_UNITS))
        )
    return key


def validate_band_edges(cut_on_nm, cut_off_nm):
    """Validate an edge pair and return it with the span between them."""
    cut_on = _require_positive("cut_on_nm", cut_on_nm)
    cut_off = _require_positive("cut_off_nm", cut_off_nm)
    if cut_off <= cut_on:
        raise ValueError(
            "cut_off_nm %g must lie above cut_on_nm %g; a band of zero or "
            "negative span has no bandwidth" % (cut_off, cut_on)
        )
    return {
        "cut_on_nm": cut_on,
        "cut_off_nm": cut_off,
        "span_nm": cut_off - cut_on,
    }


# --- the definition ---------------------------------------------------------


def band_centre_nm(cut_on_nm, cut_off_nm, convention=DEFAULT_CENTRE_CONVENTION):
    """Wavelength at the centre of the band under the declared convention."""
    key = validate_centre_convention(convention)
    edges = validate_band_edges(cut_on_nm, cut_off_nm)
    if key == ARITHMETIC_CENTRE:
        return 0.5 * (edges["cut_on_nm"] + edges["cut_off_nm"])
    return math.sqrt(edges["cut_on_nm"] * edges["cut_off_nm"])


def fractional_bandwidth(cut_on_nm, cut_off_nm, convention=DEFAULT_CENTRE_CONVENTION):
    """Cut-on to cut-off span divided by the band centre wavelength."""
    edges = validate_band_edges(cut_on_nm, cut_off_nm)
    centre = band_centre_nm(cut_on_nm, cut_off_nm, convention)
    return edges["span_nm"] / centre


def percent_bandwidth(cut_on_nm, cut_off_nm, convention=DEFAULT_CENTRE_CONVENTION):
    """The same quantity written as a percentage of the centre wavelength."""
    return 100.0 * fractional_bandwidth(cut_on_nm, cut_off_nm, convention)


def describe_band(cut_on_nm, cut_off_nm, convention=DEFAULT_CENTRE_CONVENTION):
    """Full bandwidth statement for one edge pair, both conventions shown."""
    key = validate_centre_convention(convention)
    edges = validate_band_edges(cut_on_nm, cut_off_nm)
    arithmetic_centre = 0.5 * (edges["cut_on_nm"] + edges["cut_off_nm"])
    geometric_centre = math.sqrt(edges["cut_on_nm"] * edges["cut_off_nm"])
    arithmetic_bandwidth = edges["span_nm"] / arithmetic_centre
    geometric_bandwidth = edges["span_nm"] / geometric_centre
    centre = arithmetic_centre if key == ARITHMETIC_CENTRE else geometric_centre
    bandwidth = (
        arithmetic_bandwidth if key == ARITHMETIC_CENTRE else geometric_bandwidth
    )
    return {
        "cut_on_nm": edges["cut_on_nm"],
        "cut_off_nm": edges["cut_off_nm"],
        "span_nm": edges["span_nm"],
        "edge_ratio": edges["cut_off_nm"] / edges["cut_on_nm"],
        "centre_convention": key,
        "centre_nm": centre,
        "fractional_bandwidth": bandwidth,
        "percent_bandwidth": 100.0 * bandwidth,
        "arithmetic_centre_nm": arithmetic_centre,
        "geometric_centre_nm": geometric_centre,
        "arithmetic_fractional_bandwidth": arithmetic_bandwidth,
        "geometric_fractional_bandwidth": geometric_bandwidth,
        "centre_convention_separation": (
            geometric_bandwidth - arithmetic_bandwidth
        )
        / arithmetic_bandwidth,
    }


# --- declarations and the inverse -------------------------------------------


def normalise_bandwidth_declaration(
    value, unit=DEFAULT_BANDWIDTH_UNIT, convention=DEFAULT_CENTRE_CONVENTION
):
    """Turn a declared bandwidth into a fraction of the centre wavelength."""
    key = validate_centre_convention(convention)
    unit_key = validate_bandwidth_unit(unit)
    declared = _require_positive("bandwidth value", value)
    fraction = declared / 100.0 if unit_key == PERCENT_UNIT else declared
    if unit_key == FRACTION_UNIT and fraction > IMPLAUSIBLE_FRACTION_CEILING:
        raise ValueError(
            "a bandwidth of %g declared as a fraction is above the %g ceiling; "
            "it reads as a percentage that lost its unit"
            % (fraction, IMPLAUSIBLE_FRACTION_CEILING)
        )
    if key == ARITHMETIC_CENTRE and fraction >= ARITHMETIC_BANDWIDTH_CEILING:
        raise ValueError(
            "a bandwidth of %g against an arithmetic band centre would put the "
            "cut-on at or below zero wavelength" % (fraction,)
        )
    return fraction


def band_edges_from_bandwidth(
    value,
    centre_nm,
    convention=DEFAULT_CENTRE_CONVENTION,
    unit=DEFAULT_BANDWIDTH_UNIT,
):
    """Reconstruct the edge pair a bandwidth and a band centre describe.

    Arithmetic centre: the span is the bandwidth times the centre, and the
    edges sit half a span either side of it.

    Geometric centre: writing ``u`` for the square root of the edge ratio,
    the bandwidth is ``u - 1/u``, so ``u`` is the positive root of
    ``u**2 - B*u - 1 = 0`` and the edges are the centre divided and
    multiplied by it.
    """
    key = validate_centre_convention(convention)
    fraction = normalise_bandwidth_declaration(value, unit, key)
    centre = _require_positive("centre_nm", centre_nm)
    if key == ARITHMETIC_CENTRE:
        half_span = 0.5 * fraction * centre
        cut_on = centre - half_span
        cut_off = centre + half_span
    else:
        root = 0.5 * (fraction + math.sqrt(fraction * fraction + 4.0))
        cut_on = centre / root
        cut_off = centre * root
    return validate_band_edges(cut_on, cut_off)


def check_band_statement(
    statement,
    convention=DEFAULT_CENTRE_CONVENTION,
    relative_tolerance=DEFAULT_RELATIVE_TOLERANCE,
):
    """Check that an edge pair, a stated centre and a stated bandwidth agree.

    The edges are the measurement, so they are the reference; the centre
    and the bandwidth are optional and are only checked when they are
    present. A statement whose three numbers cannot all be true at once is
    reported field by field rather than as one opaque disagreement.
    """
    key = validate_centre_convention(convention)
    if not isinstance(statement, dict):
        raise ValueError("statement must be a mapping, got %r" % (statement,))
    if not _is_real(relative_tolerance) or relative_tolerance <= 0.0:
        raise ValueError(
            "relative_tolerance must be a finite positive number, got %r"
            % (relative_tolerance,)
        )
    described = describe_band(
        statement.get("cut_on_nm"), statement.get("cut_off_nm"), key
    )

    findings = []
    checks = {}

    stated_centre = statement.get("centre_nm")
    if stated_centre is not None:
        stated_centre = _require_positive("statement centre_nm", stated_centre)
        agrees = math.isclose(
            stated_centre,
            described["centre_nm"],
            rel_tol=relative_tolerance,
            abs_tol=_ABS_TOL,
        )
        checks["centre_nm"] = {
            "stated": stated_centre,
            "derived": described["centre_nm"],
            "agrees": agrees,
            "relative_difference": (stated_centre - described["centre_nm"])
            / described["centre_nm"],
        }
        if not agrees:
            findings.append(
                "the stated centre %.4f nm is not the %s of the two edges, "
                "which is %.4f nm"
                % (stated_centre, key, described["centre_nm"])
            )

    stated_bandwidth = statement.get("bandwidth")
    if stated_bandwidth is not None:
        fraction = normalise_bandwidth_declaration(
            stated_bandwidth, statement.get("bandwidth_unit", DEFAULT_BANDWIDTH_UNIT), key
        )
        agrees = math.isclose(
            fraction,
            described["fractional_bandwidth"],
            rel_tol=relative_tolerance,
            abs_tol=_ABS_TOL,
        )
        checks["bandwidth"] = {
            "stated_fraction": fraction,
            "derived_fraction": described["fractional_bandwidth"],
            "agrees": agrees,
            "relative_difference": (fraction - described["fractional_bandwidth"])
            / described["fractional_bandwidth"],
        }
        if not agrees:
            findings.append(
                "the stated bandwidth %.6f does not match the %.6f the edge "
                "pair gives under the %s convention"
                % (fraction, described["fractional_bandwidth"], key)
            )

    return {
        "band": described,
        "checks": checks,
        "consistent": not findings,
        "findings": findings,
    }
