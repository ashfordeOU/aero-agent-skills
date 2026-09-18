#!/usr/bin/env python3
"""Circuit stability analysis for an MMIC gain stage.

Anchor: ECSS-Q-ST-60-12C clause 7.2.8. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An amplifier that oscillates is not a degraded amplifier, it is a
different circuit: the output is a tone the design never asked for, the
bias walks, and the failure is usually found on the integrated unit
rather than on the die. Clause 7.2.8 asks for a demonstration that the
circuit cannot oscillate anywhere in its operating envelope, and the
demonstration is built from the two-port scattering parameters at every
frequency the analysis covers.

Quantities built from the scattering matrix
    delta          the determinant, s11*s22 - s12*s21
    rollett k      (1 - |s11|^2 - |s22|^2 + |delta|^2) / (2|s12*s21|)
    geometric mu   the distance from the centre of the reflection plane
                   to the nearest point that would sustain oscillation;
                   above one means no passive termination can do it

Unconditional stability needs k above one AND |delta| below one, which
is the same statement as mu above one. Where that fails the device is
not necessarily unusable: it is conditionally stable, and the design has
to show that the terminations it will really see sit in the stable
region, which is the part of the plane the stability circle cuts off.

Span matters as much as the numbers. A stage is usually most dangerous
well below its operating band, where the device has far more gain than
the design needs and the matching networks no longer control the
terminations, so the analysed span reaches decades below the band and a
multiple above it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import cmath
import math

UNCONDITIONALLY_STABLE = "unconditionally-stable"
MARGINALLY_STABLE = "marginally-stable"
POTENTIALLY_UNSTABLE = "potentially-unstable"
STABILITY_CATEGORIES = (
    UNCONDITIONALLY_STABLE,
    MARGINALLY_STABLE,
    POTENTIALLY_UNSTABLE,
)

LOAD_PLANE = "load"
SOURCE_PLANE = "source"
PLANES = (LOAD_PLANE, SOURCE_PLANE)

STABLE_OVER_SPAN = "unconditionally-stable-over-span"
ENVELOPE_CLEAR = "conditionally-stable-envelope-clear"
OSCILLATION_RISK = "oscillation-risk"
SPAN_INSUFFICIENT = "analysis-span-insufficient"

DEFAULT_DECADES_BELOW = 2.0
DEFAULT_FACTOR_ABOVE = 2.0

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
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _close(a, b):
    return math.isclose(a, b, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    Every quantity here is built through complex multiplication and a
    square root, so a case that sits exactly on a bound can land a few
    units in the last place on the wrong side. The bound is never
    relaxed; only the comparison tolerates the representation error.
    """
    return value >= limit or _close(value, limit)


def _at_most(value, limit):
    return value <= limit or _close(value, limit)


def as_reflection(value, name="reflection coefficient"):
    """Accept a complex value or a (magnitude, angle-in-degree) pair."""
    if isinstance(value, complex):
        if not (math.isfinite(value.real) and math.isfinite(value.imag)):
            raise ValueError("%s must be finite, got %r" % (name, value))
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return complex(_require_number(name, value), 0.0)
    if isinstance(value, (tuple, list)) and len(value) == 2:
        magnitude = _require_non_negative("%s magnitude" % name, value[0])
        angle_deg = _require_number("%s angle" % name, value[1])
        return cmath.rect(magnitude, math.radians(angle_deg))
    raise ValueError(
        "%s must be complex or a (magnitude, angle-in-degree) pair, got %r"
        % (name, value)
    )


def validate_s_parameters(s):
    """Normalise a two-port scattering matrix to four complex entries."""
    if not isinstance(s, dict):
        raise ValueError("s parameters must be a mapping, got %r" % (s,))
    out = {}
    for key in ("s11", "s12", "s21", "s22"):
        if key not in s:
            raise ValueError("s parameters are missing %s" % key)
        out[key] = as_reflection(s[key], key)
    if abs(out["s12"] * out["s21"]) == 0.0:
        raise ValueError(
            "s12*s21 is zero; a device with no reverse path has no stability "
            "factor, and a measured MMIC never reads exactly zero"
        )
    return out


def determinant(s):
    """Determinant of the scattering matrix."""
    s = validate_s_parameters(s)
    return s["s11"] * s["s22"] - s["s12"] * s["s21"]


def rollett_k(s):
    """Rollett stability factor of the two-port."""
    s = validate_s_parameters(s)
    delta_mag = abs(determinant(s))
    numerator = (
        1.0 - abs(s["s11"]) ** 2 - abs(s["s22"]) ** 2 + delta_mag ** 2
    )
    return numerator / (2.0 * abs(s["s12"] * s["s21"]))


def mu_factor(s, plane=LOAD_PLANE):
    """Geometric stability factor in one reflection plane.

    The load-plane factor is the distance from the centre of the load
    reflection plane to the nearest point of the unstable region, so a
    value above one says no passive load can sustain oscillation.
    """
    _require_choice("plane", plane, PLANES)
    s = validate_s_parameters(s)
    delta = determinant(s)
    if plane == LOAD_PLANE:
        near, far = s["s11"], s["s22"]
    else:
        near, far = s["s22"], s["s11"]
    denominator = abs(far - delta * near.conjugate()) + abs(s["s12"] * s["s21"])
    if denominator == 0.0:
        raise ValueError("the %s-plane mu factor is undefined for this matrix" % plane)
    return (1.0 - abs(near) ** 2) / denominator


def stability_category(s):
    """Group the two-port by what a passive termination could do to it.

    A device sitting on the boundary is reported as marginal rather than
    forced to one side: the factor is built from complex products and a
    square root, so which side of one it lands on at the boundary is a
    property of the arithmetic, not of the circuit.
    """
    s = validate_s_parameters(s)
    k = rollett_k(s)
    delta_mag = abs(determinant(s))
    if _close(k, 1.0) or _close(delta_mag, 1.0):
        return MARGINALLY_STABLE
    if k > 1.0 and delta_mag < 1.0:
        return UNCONDITIONALLY_STABLE
    return POTENTIALLY_UNSTABLE


def stability_circle(s, plane=LOAD_PLANE):
    """Centre and radius of the stability circle in one reflection plane."""
    _require_choice("plane", plane, PLANES)
    s = validate_s_parameters(s)
    delta = determinant(s)
    if plane == LOAD_PLANE:
        own, other = s["s22"], s["s11"]
    else:
        own, other = s["s11"], s["s22"]
    denominator = abs(own) ** 2 - abs(delta) ** 2
    if denominator == 0.0:
        raise ValueError(
            "the %s-plane stability circle degenerates to a line for this matrix"
            % plane
        )
    centre = (own - delta * other.conjugate()).conjugate() / denominator
    radius = abs(s["s12"] * s["s21"] / denominator)
    # The centre of the plane is a matched termination, which is stable
    # whenever the port it faces is not already reflecting gain back.
    origin_is_stable = abs(other) < 1.0 or _close(abs(other), 1.0)
    return {
        "plane": plane,
        "centre": centre,
        "radius": radius,
        "origin_is_stable": origin_is_stable,
        "encircles_origin": abs(centre) < radius,
    }


def termination_is_stable(gamma, circle):
    """Whether one presented reflection coefficient sits in the stable part."""
    gamma = as_reflection(gamma, "termination")
    if abs(gamma) > 1.0 and not _close(abs(gamma), 1.0):
        raise ValueError(
            "termination magnitude %.4f exceeds one; a passive termination "
            "cannot reflect more than it receives" % abs(gamma)
        )
    if not isinstance(circle, dict):
        raise ValueError("circle must be a mapping, got %r" % (circle,))
    centre = circle.get("centre")
    if not isinstance(centre, complex):
        raise ValueError("circle needs a complex centre, got %r" % (centre,))
    radius = _require_non_negative("circle radius", circle.get("radius"))
    distance = abs(gamma - centre)
    if _close(distance, radius):
        # The circle itself is the locus that sustains oscillation, so a
        # termination landing on it does not pass, whichever side the
        # arithmetic happens to put it.
        return False
    inside = distance < radius
    origin_inside = bool(circle.get("encircles_origin"))
    origin_stable = bool(circle.get("origin_is_stable"))
    same_side_as_origin = inside == origin_inside
    return same_side_as_origin if origin_stable else not same_side_as_origin


def required_analysis_span_hz(
    band_low_hz,
    band_high_hz,
    decades_below=DEFAULT_DECADES_BELOW,
    factor_above=DEFAULT_FACTOR_ABOVE,
):
    """Frequency reach the stability analysis has to cover, both ways."""
    low = _require_positive("band_low_hz", band_low_hz)
    high = _require_positive("band_high_hz", band_high_hz)
    if high < low:
        raise ValueError("band_high_hz %g is below band_low_hz %g" % (high, low))
    decades = _require_non_negative("decades_below", decades_below)
    factor = _require_number("factor_above", factor_above)
    if factor < 1.0:
        raise ValueError("factor_above must be at least one, got %r" % (factor,))
    return {
        "required_low_hz": low / (10.0 ** decades),
        "required_high_hz": high * factor,
    }


def span_coverage(
    analysed_low_hz,
    analysed_high_hz,
    band_low_hz,
    band_high_hz,
    decades_below=DEFAULT_DECADES_BELOW,
    factor_above=DEFAULT_FACTOR_ABOVE,
):
    """Whether the analysed frequencies reach far enough on both sides."""
    low = _require_positive("analysed_low_hz", analysed_low_hz)
    high = _require_positive("analysed_high_hz", analysed_high_hz)
    if high < low:
        raise ValueError(
            "analysed_high_hz %g is below analysed_low_hz %g" % (high, low)
        )
    required = required_analysis_span_hz(
        band_low_hz, band_high_hz, decades_below, factor_above
    )
    covers_low = _at_most(low, required["required_low_hz"])
    covers_high = _at_least(high, required["required_high_hz"])
    findings = []
    if not covers_low:
        findings.append(
            "the analysis stops at %.4g Hz but has to reach %.4g Hz; the "
            "low-frequency region where the device has its most surplus gain "
            "is unexamined" % (low, required["required_low_hz"])
        )
    if not covers_high:
        findings.append(
            "the analysis stops at %.4g Hz but has to reach %.4g Hz; an "
            "out-of-band resonance above the band is unexamined"
            % (high, required["required_high_hz"])
        )
    result = dict(required)
    result.update(
        {
            "covers_low": covers_low,
            "covers_high": covers_high,
            "compliant": bool(covers_low and covers_high),
            "findings": findings,
        }
    )
    return result


def analyze_point(point, load_terminations=(), source_terminations=()):
    """Stability of one analysed frequency against the presented terminations."""
    if not isinstance(point, dict):
        raise ValueError("point must be a mapping, got %r" % (point,))
    frequency = _require_positive("frequency_hz", point.get("frequency_hz"))
    s = validate_s_parameters(point.get("s"))
    category = stability_category(s)
    result = {
        "frequency_hz": frequency,
        "k": rollett_k(s),
        "delta_magnitude": abs(determinant(s)),
        "mu_load": mu_factor(s, LOAD_PLANE),
        "mu_source": mu_factor(s, SOURCE_PLANE),
        "category": category,
        "unstable_terminations": [],
        "findings": [],
    }
    if category == UNCONDITIONALLY_STABLE:
        return result
    for plane, gammas in (
        (LOAD_PLANE, load_terminations),
        (SOURCE_PLANE, source_terminations),
    ):
        if not isinstance(gammas, (list, tuple)):
            raise ValueError("%s terminations must be a sequence" % plane)
        if not gammas:
            continue
        circle = stability_circle(s, plane)
        for gamma in gammas:
            if not termination_is_stable(gamma, circle):
                value = as_reflection(gamma, "termination")
                result["unstable_terminations"].append(
                    {"plane": plane, "gamma": value, "frequency_hz": frequency}
                )
                result["findings"].append(
                    "at %.4g Hz a %s termination of magnitude %.3f falls in the "
                    "unstable region" % (frequency, plane, abs(value))
                )
    if not load_terminations and not source_terminations:
        result["findings"].append(
            "at %.4g Hz the device is %s and no termination envelope was "
            "declared, so nothing bounds what the matching networks present"
            % (frequency, category)
        )
    return result


def analyze_stability(case):
    """Full clause 7.2.8 stability demonstration with a verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    points = case.get("points")
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("case needs a non-empty sequence of analysed points")
    load_terminations = case.get("load_terminations", ())
    source_terminations = case.get("source_terminations", ())

    analysed = []
    last_frequency = None
    for point in points:
        result = analyze_point(point, load_terminations, source_terminations)
        if last_frequency is not None and not result["frequency_hz"] > last_frequency:
            raise ValueError(
                "analysed points must be in increasing frequency order; %g Hz "
                "follows %g Hz" % (result["frequency_hz"], last_frequency)
            )
        last_frequency = result["frequency_hz"]
        analysed.append(result)

    findings = []
    for result in analysed:
        findings.extend(result["findings"])

    coverage = span_coverage(
        analysed[0]["frequency_hz"],
        analysed[-1]["frequency_hz"],
        case.get("band_low_hz"),
        case.get("band_high_hz"),
        case.get("decades_below", DEFAULT_DECADES_BELOW),
        case.get("factor_above", DEFAULT_FACTOR_ABOVE),
    )
    findings.extend(coverage["findings"])

    unstable = [
        entry for result in analysed for entry in result["unstable_terminations"]
    ]
    not_unconditional = [
        result for result in analysed if result["category"] != UNCONDITIONALLY_STABLE
    ]
    worst = min(analysed, key=lambda r: r["mu_load"])

    if not coverage["compliant"]:
        verdict = SPAN_INSUFFICIENT
    elif unstable:
        verdict = OSCILLATION_RISK
    elif not not_unconditional:
        verdict = STABLE_OVER_SPAN
    elif load_terminations or source_terminations:
        verdict = ENVELOPE_CLEAR
    else:
        verdict = OSCILLATION_RISK

    return {
        "verdict": verdict,
        "stable": verdict in (STABLE_OVER_SPAN, ENVELOPE_CLEAR),
        "points": analysed,
        "span": coverage,
        "unstable_terminations": unstable,
        "worst_frequency_hz": worst["frequency_hz"],
        "worst_mu_load": worst["mu_load"],
        "unconditional_everywhere": not not_unconditional,
        "findings": findings,
    }
