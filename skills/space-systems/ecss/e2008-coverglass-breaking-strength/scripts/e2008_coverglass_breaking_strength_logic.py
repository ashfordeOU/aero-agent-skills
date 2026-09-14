#!/usr/bin/env python3
"""Breaking strength of a coverglass against its control drawing limit.

Anchor: ECSS-E-ST-20-08C clause 8.7.15. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A coverglass is a brittle plate. It does not have a strength the way a
metal has a yield point: it has a distribution of strengths set by the
flaw population its cutting and polishing left behind, and the plate
breaks at the largest flaw the stress field happens to find. The clause
asks for the mechanical strength of the coverglass to be held against
the limits its control drawing fixes, and the only honest way to do
that on a brittle distribution is to convert every break load into a
stress for the fixture that produced it, fit the distribution, and
compare a low-probability allowable -- not the arithmetic mean -- with
the drawing value.

Bend fixtures handled

    three-point-bend   sigma = 3 F L / (2 b h^2)
    four-point-bend    sigma = 3 F a / (b h^2), a the load offset arm
    ring-on-ring       equibiaxial plate formula, needs Poisson's ratio

A mean break stress well above the drawing minimum can sit on a sample
set whose weakest decile is under it. The Weibull modulus is what says
which of those two situations the lot is in, so the fit is part of the
acceptance, not a report appendix.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

THREE_POINT_BEND = "three-point-bend"
FOUR_POINT_BEND = "four-point-bend"
RING_ON_RING = "ring-on-ring"

BEND_FIXTURES = (THREE_POINT_BEND, FOUR_POINT_BEND, RING_ON_RING)

REQUIRED_GEOMETRY_BY_FIXTURE = {
    THREE_POINT_BEND: ("support_span_mm", "width_mm", "thickness_mm"),
    FOUR_POINT_BEND: (
        "load_span_mm",
        "support_span_mm",
        "thickness_mm",
        "width_mm",
    ),
    RING_ON_RING: (
        "load_ring_diameter_mm",
        "poisson_ratio",
        "specimen_diameter_mm",
        "support_ring_diameter_mm",
        "thickness_mm",
    ),
}

#: Fewer broken articles than this cannot support a two-parameter fit.
MIN_BROKEN_SAMPLES = 10

#: A modulus under this means the flaw population is out of control even
#: when the allowable happens to clear the drawing value.
MIN_WEIBULL_MODULUS = 3.0

#: Failure probability the design allowable is quoted at.
DESIGN_FAILURE_PROBABILITY = 0.01

LOT_ACCEPTED = "breaking-strength-accepted"
LOT_NOT_ACCEPTED = "breaking-strength-not-accepted"

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


def _require_fraction(name, value, upper=1.0):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > upper:
        raise ValueError(
            "%s must lie between zero and %g, got %r" % (name, upper, value)
        )
    return float(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A design allowable is the product of a logarithm, a least-squares
    slope and a fractional power, none of which are correctly rounded.
    The limit is never relaxed; only the comparison tolerates the few
    units in the last place the platform's libm contributes, which is
    why no caller here uses a bare >= on a derived float.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def required_geometry(fixture):
    """Geometry the named bend fixture owes before a load becomes a stress."""
    if fixture not in REQUIRED_GEOMETRY_BY_FIXTURE:
        raise ValueError(
            "unknown bend fixture %r; handled fixtures are %s"
            % (fixture, ", ".join(BEND_FIXTURES))
        )
    return tuple(sorted(REQUIRED_GEOMETRY_BY_FIXTURE[fixture]))


def missing_geometry(fixture, geometry):
    """Geometry keys the fixture needs and the submission has not brought."""
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be a mapping, got %r" % (geometry,))
    return tuple(
        name for name in required_geometry(fixture) if geometry.get(name) is None
    )


def three_point_bend_stress_mpa(load_n, support_span_mm, width_mm, thickness_mm):
    """Outer-fibre stress a centre load puts into a rectangular coupon."""
    load = _require_positive("load_n", load_n)
    span = _require_positive("support_span_mm", support_span_mm)
    width = _require_positive("width_mm", width_mm)
    thickness = _require_positive("thickness_mm", thickness_mm)
    return (3.0 * load * span) / (2.0 * width * thickness * thickness)


def four_point_bend_stress_mpa(
    load_n, support_span_mm, load_span_mm, width_mm, thickness_mm
):
    """Outer-fibre stress in the uniform-moment span of a four-point rig."""
    load = _require_positive("load_n", load_n)
    support_span = _require_positive("support_span_mm", support_span_mm)
    load_span = _require_positive("load_span_mm", load_span_mm)
    width = _require_positive("width_mm", width_mm)
    thickness = _require_positive("thickness_mm", thickness_mm)
    if not support_span > load_span:
        raise ValueError(
            "support_span_mm %g must exceed load_span_mm %g"
            % (support_span, load_span)
        )
    arm = (support_span - load_span) / 2.0
    return (3.0 * load * arm) / (width * thickness * thickness)


def ring_on_ring_stress_mpa(
    load_n,
    support_ring_diameter_mm,
    load_ring_diameter_mm,
    specimen_diameter_mm,
    thickness_mm,
    poisson_ratio,
):
    """Equibiaxial stress a concentric ring pair puts into a disc.

    The ring pair loads an area rather than a line, so it samples far
    more of the flaw population than a bend bar does and usually returns
    a lower strength for the same glass. That is a property of the test,
    not a defect in the lot.
    """
    load = _require_positive("load_n", load_n)
    support = _require_positive("support_ring_diameter_mm", support_ring_diameter_mm)
    inner = _require_positive("load_ring_diameter_mm", load_ring_diameter_mm)
    specimen = _require_positive("specimen_diameter_mm", specimen_diameter_mm)
    thickness = _require_positive("thickness_mm", thickness_mm)
    nu = _require_fraction("poisson_ratio", poisson_ratio, upper=0.5)
    if not support > inner:
        raise ValueError(
            "support_ring_diameter_mm %g must exceed load_ring_diameter_mm %g"
            % (support, inner)
        )
    if not specimen >= support:
        raise ValueError(
            "specimen_diameter_mm %g must be at least the support ring %g"
            % (specimen, support)
        )
    term = (
        (1.0 - nu) * (support * support - inner * inner) / (2.0 * specimen * specimen)
        + (1.0 + nu) * math.log(support / inner)
    )
    return (3.0 * load) / (2.0 * math.pi * thickness * thickness) * term


def break_stress_mpa(fixture, load_n, geometry):
    """Convert one recorded break load into a stress for its fixture."""
    absent = missing_geometry(fixture, geometry)
    if absent:
        raise ValueError(
            "%s fixture is missing geometry: %s" % (fixture, ", ".join(absent))
        )
    if fixture == THREE_POINT_BEND:
        return three_point_bend_stress_mpa(
            load_n,
            geometry["support_span_mm"],
            geometry["width_mm"],
            geometry["thickness_mm"],
        )
    if fixture == FOUR_POINT_BEND:
        return four_point_bend_stress_mpa(
            load_n,
            geometry["support_span_mm"],
            geometry["load_span_mm"],
            geometry["width_mm"],
            geometry["thickness_mm"],
        )
    return ring_on_ring_stress_mpa(
        load_n,
        geometry["support_ring_diameter_mm"],
        geometry["load_ring_diameter_mm"],
        geometry["specimen_diameter_mm"],
        geometry["thickness_mm"],
        geometry["poisson_ratio"],
    )


def median_rank_probabilities(count):
    """Plotting positions for an ordered sample set, (i - 0.5) / n."""
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError("count must be an integer, got %r" % (count,))
    if count < 2:
        raise ValueError("count must be at least two to rank, got %d" % count)
    return tuple((index + 0.5) / count for index in range(count))


def fit_weibull(stresses_mpa):
    """Two-parameter Weibull fit by least squares on the ranked sample set.

    Returns the modulus and the characteristic strength, the stress at
    which about 63 per cent of the population has broken.
    """
    if not isinstance(stresses_mpa, (list, tuple)):
        raise ValueError(
            "stresses_mpa must be a sequence of break stresses, got %r"
            % (stresses_mpa,)
        )
    values = sorted(
        _require_positive("break stress %d" % index, value)
        for index, value in enumerate(stresses_mpa)
    )
    if len(values) < MIN_BROKEN_SAMPLES:
        raise ValueError(
            "a Weibull fit needs at least %d broken articles, got %d"
            % (MIN_BROKEN_SAMPLES, len(values))
        )
    if math.isclose(values[0], values[-1], rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        raise ValueError(
            "every recorded break stress is the same value; the sample set "
            "carries no distribution to fit"
        )
    probabilities = median_rank_probabilities(len(values))
    xs = [math.log(value) for value in values]
    ys = [math.log(-math.log(1.0 - p)) for p in probabilities]
    n = float(len(values))
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    variance = sum((x - mean_x) ** 2 for x in xs)
    if variance <= 0.0:
        raise ValueError("break stresses have no spread; the fit is undefined")
    modulus = covariance / variance
    if modulus <= 0.0:
        raise ValueError(
            "fitted Weibull modulus %g is not positive; the sample set is not "
            "a strength distribution" % modulus
        )
    intercept = mean_y - modulus * mean_x
    characteristic = math.exp(-intercept / modulus)
    return {
        "modulus": modulus,
        "characteristic_strength_mpa": characteristic,
        "sample_count": len(values),
        "ordered_stresses_mpa": tuple(values),
    }


def design_allowable_mpa(modulus, characteristic_strength_mpa, failure_probability):
    """Stress at which the fitted population reaches a chosen break risk."""
    m = _require_positive("modulus", modulus)
    scale = _require_positive(
        "characteristic_strength_mpa", characteristic_strength_mpa
    )
    probability = _require_fraction("failure_probability", failure_probability)
    if probability <= 0.0 or probability >= 1.0:
        raise ValueError(
            "failure_probability must sit strictly between zero and one, got %r"
            % (failure_probability,)
        )
    return scale * math.exp(math.log(-math.log(1.0 - probability)) / m)


def mean_stress_mpa(stresses_mpa):
    """Arithmetic mean of the break stresses, reported but never the verdict."""
    if not isinstance(stresses_mpa, (list, tuple)) or not stresses_mpa:
        raise ValueError(
            "stresses_mpa must be a non-empty sequence, got %r" % (stresses_mpa,)
        )
    values = [
        _require_positive("break stress %d" % index, value)
        for index, value in enumerate(stresses_mpa)
    ]
    return sum(values) / float(len(values))


def assess_breaking_strength(case):
    """Full clause 8.7.15 judgement of one coverglass lot."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    fixture = case.get("bend_fixture")
    if fixture not in BEND_FIXTURES:
        raise ValueError(
            "bend_fixture must be one of %s, got %r"
            % (", ".join(BEND_FIXTURES), fixture)
        )
    geometry = case.get("geometry")
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be a mapping, got %r" % (geometry,))
    loads = case.get("break_loads_n")
    if not isinstance(loads, (list, tuple)) or not loads:
        raise ValueError(
            "break_loads_n must be a non-empty sequence, got %r" % (loads,)
        )
    drawing_minimum = _require_positive(
        "drawing_minimum_strength_mpa", case.get("drawing_minimum_strength_mpa")
    )
    probability = case.get("design_failure_probability", DESIGN_FAILURE_PROBABILITY)

    stresses = [break_stress_mpa(fixture, load, geometry) for load in loads]
    fit = fit_weibull(stresses)
    allowable = design_allowable_mpa(
        fit["modulus"], fit["characteristic_strength_mpa"], probability
    )
    mean = mean_stress_mpa(stresses)
    weakest = min(stresses)

    findings = []
    if not _at_least(allowable, drawing_minimum):
        findings.append(
            "design allowable %.1f MPa is below the %.1f MPa the control drawing "
            "fixes; the lot does not meet the mechanical strength limit"
            % (allowable, drawing_minimum)
        )
    if not _at_least(fit["modulus"], MIN_WEIBULL_MODULUS):
        findings.append(
            "Weibull modulus %.2f is below %.1f; the flaw population is too "
            "scattered for the drawing limit to mean anything on this lot"
            % (fit["modulus"], MIN_WEIBULL_MODULUS)
        )
    if not _at_least(weakest, drawing_minimum):
        findings.append(
            "weakest article broke at %.1f MPa, under the %.1f MPa drawing "
            "minimum; record it against the lot even though the fit may clear"
            % (weakest, drawing_minimum)
        )

    mean_hides_tail = _at_least(mean, drawing_minimum) and not _at_least(
        allowable, drawing_minimum
    )
    accepted = not findings
    return {
        "bend_fixture": fixture,
        "sample_count": fit["sample_count"],
        "break_stresses_mpa": tuple(stresses),
        "mean_strength_mpa": mean,
        "weakest_strength_mpa": weakest,
        "weibull_modulus": fit["modulus"],
        "characteristic_strength_mpa": fit["characteristic_strength_mpa"],
        "design_failure_probability": float(probability),
        "design_allowable_mpa": allowable,
        "drawing_minimum_strength_mpa": drawing_minimum,
        "mean_hides_weak_tail": mean_hides_tail,
        "verdict": LOT_ACCEPTED if accepted else LOT_NOT_ACCEPTED,
        "accepted": accepted,
        "findings": findings,
    }
