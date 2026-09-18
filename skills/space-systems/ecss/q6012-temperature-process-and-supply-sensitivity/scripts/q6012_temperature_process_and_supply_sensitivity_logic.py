#!/usr/bin/env python3
"""Temperature, process and supply sensitivity of an MMIC design.

Anchor: ECSS-Q-ST-60-12C clause 7.2.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A monolithic microwave integrated circuit is delivered against a
specification window, but the die that flies sits at a temperature it
did not see on the bench, comes from a lot the design was not simulated
on, and runs off a rail that moves inside its regulation band. The
performance spread those three axes produce is what clause 7.2.6 asks
the designer to evaluate, so the axes are handled one at a time and then
combined.

Axis excursions
    temperature   a deterministic swing: the die will actually reach
                  both ends of the declared envelope, so both ends are
                  carried, never a distribution about the mean
    process       a statistical spread: lot-to-lot and wafer-to-wafer
                  variation quoted as a sigma on the foundry parameter
    supply        deterministic when the rail is a specified tolerance
                  band, statistical only when the regulation has been
                  measured as a distribution

Combination method follows the bases, not preference
    worst-case-arithmetic        every contribution added at its
                                 extreme; the only honest method when
                                 no axis carries a distribution
    root-sum-square              admissible only when every axis is an
                                 independent measured distribution
    hybrid-worst-case-plus-rss   deterministic axes added arithmetically
                                 and statistical axes root-sum-squared
                                 on top; the usual MMIC case, because
                                 temperature is never statistical

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

AXES = ("temperature", "process", "supply")

TEMPERATURE_BASES = (
    "measured-over-temperature",
    "model-extrapolated",
    "room-temperature-only",
)
PROCESS_BASES = (
    "multi-lot-statistics",
    "single-lot-statistics",
    "foundry-nominal-only",
)
SUPPLY_BASES = (
    "regulated-measured",
    "specified-tolerance",
    "unbounded-rail",
)

BASES_BY_AXIS = {
    "temperature": TEMPERATURE_BASES,
    "process": PROCESS_BASES,
    "supply": SUPPLY_BASES,
}

# Only these bases describe an independent distribution that may be
# root-sum-squared. Everything else is a bound and is added arithmetically.
STATISTICAL_BASES = frozenset({"multi-lot-statistics", "regulated-measured"})

WORST_CASE_METHOD = "worst-case-arithmetic"
RSS_METHOD = "root-sum-square"
HYBRID_METHOD = "hybrid-worst-case-plus-rss"
COMBINATION_METHODS = (WORST_CASE_METHOD, RSS_METHOD, HYBRID_METHOD)

DEFAULT_PROCESS_COVERAGE_SIGMA = 3.0

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


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A margin is a difference of two numbers that were each built by a
    chain of multiplications and a square root, so a case that sits
    exactly on the specification edge can land a few units in the last
    place on the wrong side. The specification is never widened; only
    the comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def axis_basis_is_statistical(axis, basis):
    """Whether this axis basis describes a distribution that may be RSS-ed."""
    _require_choice("axis", axis, AXES)
    _require_choice("%s basis" % axis, basis, BASES_BY_AXIS[axis])
    if axis == "temperature":
        # The die really does reach both ends of its envelope; there is
        # no distribution to root-sum-square, whatever the data basis.
        return False
    return basis in STATISTICAL_BASES


def temperature_excursions_k(t_min_c, t_max_c, t_reference_c):
    """Cold and hot excursions in kelvin from the characterisation point."""
    t_min = _require_number("t_min_c", t_min_c)
    t_max = _require_number("t_max_c", t_max_c)
    t_ref = _require_number("t_reference_c", t_reference_c)
    if t_max <= t_min:
        raise ValueError(
            "t_max_c %g must be above t_min_c %g; the envelope is empty"
            % (t_max, t_min)
        )
    if t_ref < t_min or t_ref > t_max:
        raise ValueError(
            "t_reference_c %g sits outside the envelope %g..%g; the nominal "
            "performance was characterised at a temperature the part never sees"
            % (t_ref, t_min, t_max)
        )
    return (t_min - t_ref, t_max - t_ref)


def supply_excursions_v(v_min_v, v_max_v, v_nominal_v):
    """Low and high rail excursions in volt from the nominal rail."""
    v_min = _require_positive("v_min_v", v_min_v)
    v_max = _require_positive("v_max_v", v_max_v)
    v_nom = _require_positive("v_nominal_v", v_nominal_v)
    if v_max <= v_min:
        raise ValueError(
            "v_max_v %g must be above v_min_v %g; the rail band is empty"
            % (v_max, v_min)
        )
    if v_nom < v_min or v_nom > v_max:
        raise ValueError(
            "v_nominal_v %g sits outside the rail band %g..%g" % (v_nom, v_min, v_max)
        )
    return (v_min - v_nom, v_max - v_nom)


def process_excursions_sigma(process_sigma, coverage_sigma=DEFAULT_PROCESS_COVERAGE_SIGMA):
    """Low and high process excursions in sigma of the foundry parameter."""
    sigma = _require_non_negative("process_sigma", process_sigma)
    coverage = _require_positive("coverage_sigma", coverage_sigma)
    reach = coverage * sigma
    return (-reach, reach)


def axis_contribution(sensitivity, excursions):
    """Signed low and high performance deltas one axis contributes.

    The sensitivity may be negative, so the cold end of an excursion can
    be the high end of the contribution; the pair is returned ordered.
    """
    slope = _require_number("sensitivity", sensitivity)
    if not isinstance(excursions, (tuple, list)) or len(excursions) != 2:
        raise ValueError("excursions must be a low/high pair, got %r" % (excursions,))
    low = _require_number("excursion low", excursions[0])
    high = _require_number("excursion high", excursions[1])
    if high < low:
        raise ValueError("excursion pair is inverted: %g then %g" % (low, high))
    a = slope * low
    b = slope * high
    return (min(a, b), max(a, b))


def select_combination_method(bases):
    """Pick the combination method the declared bases actually permit."""
    if not isinstance(bases, dict):
        raise ValueError("bases must be a mapping, got %r" % (bases,))
    missing = set(AXES) - set(bases)
    if missing:
        raise ValueError("bases is missing an axis: %s" % ", ".join(sorted(missing)))
    flags = [axis_basis_is_statistical(axis, bases[axis]) for axis in AXES]
    if all(flags):
        return RSS_METHOD
    if not any(flags):
        return WORST_CASE_METHOD
    return HYBRID_METHOD


def combine_contributions(contributions, method):
    """Fold the per-axis low/high pairs into one low/high spread.

    contributions maps an axis name to {"pair": (low, high),
    "statistical": bool}. Root-sum-square is refused outright when any
    axis is a bound rather than a distribution, because squaring a bound
    and taking a root understates a value the part will genuinely reach.
    """
    _require_choice("method", method, COMBINATION_METHODS)
    if not isinstance(contributions, dict) or not contributions:
        raise ValueError("contributions must be a non-empty mapping")
    deterministic_low = 0.0
    deterministic_high = 0.0
    statistical_low_sq = 0.0
    statistical_high_sq = 0.0
    for axis, entry in contributions.items():
        _require_choice("contribution axis", axis, AXES)
        if not isinstance(entry, dict):
            raise ValueError("contribution for %s must be a mapping" % axis)
        pair = entry.get("pair")
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise ValueError("contribution for %s needs a low/high pair" % axis)
        low = _require_number("%s low contribution" % axis, pair[0])
        high = _require_number("%s high contribution" % axis, pair[1])
        if high < low:
            raise ValueError("contribution for %s is inverted" % axis)
        statistical = entry.get("statistical")
        if not isinstance(statistical, bool):
            raise ValueError("contribution for %s needs a boolean statistical flag" % axis)
        if statistical and method != WORST_CASE_METHOD:
            statistical_low_sq += low * low
            statistical_high_sq += high * high
        else:
            deterministic_low += low
            deterministic_high += high
    if method == RSS_METHOD and (deterministic_low != 0.0 or deterministic_high != 0.0):
        raise ValueError(
            "root-sum-square was requested while an axis is a bound rather than "
            "a distribution; use the hybrid method"
        )
    return (
        deterministic_low - math.sqrt(statistical_low_sq),
        deterministic_high + math.sqrt(statistical_high_sq),
    )


def performance_window(nominal_value, spread_low, spread_high):
    """Absolute performance window the spread puts around the nominal."""
    nominal = _require_number("nominal_value", nominal_value)
    low = _require_number("spread_low", spread_low)
    high = _require_number("spread_high", spread_high)
    if high < low:
        raise ValueError("spread pair is inverted: %g then %g" % (low, high))
    return (nominal + low, nominal + high)


def rank_contributors(contributions):
    """Axes ordered by the share of the arithmetic spread each one owns."""
    if not isinstance(contributions, dict) or not contributions:
        raise ValueError("contributions must be a non-empty mapping")
    swings = {}
    for axis, entry in contributions.items():
        _require_choice("contribution axis", axis, AXES)
        pair = entry.get("pair") if isinstance(entry, dict) else None
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise ValueError("contribution for %s needs a low/high pair" % axis)
        low = _require_number("%s low contribution" % axis, pair[0])
        high = _require_number("%s high contribution" % axis, pair[1])
        swings[axis] = abs(high - low)
    total = sum(swings.values())
    ranked = []
    for axis in sorted(swings, key=lambda a: (-swings[a], a)):
        share = 0.0 if total == 0.0 else swings[axis] / total
        ranked.append({"axis": axis, "swing": swings[axis], "share": share})
    return ranked


def corner_matrix(monotone_sensitivities=True):
    """Corner combinations the simulation has to cover.

    A monotone response is bounded by its extremes, so the cold/hot,
    slow/fast and low/high rail corners plus the nominal point are
    enough. A response that turns over inside the envelope is not, and
    the full three-level grid on all three axes is carried instead.
    """
    if not isinstance(monotone_sensitivities, bool):
        raise ValueError(
            "monotone_sensitivities must be a boolean, got %r" % (monotone_sensitivities,)
        )
    levels = {
        "temperature": ("cold", "nominal", "hot"),
        "process": ("slow", "nominal", "fast"),
        "supply": ("low", "nominal", "high"),
    }
    if not monotone_sensitivities:
        corners = []
        for t in levels["temperature"]:
            for p in levels["process"]:
                for s in levels["supply"]:
                    corners.append({"temperature": t, "process": p, "supply": s})
        return corners
    nominal = {"temperature": "nominal", "process": "nominal", "supply": "nominal"}
    corners = [dict(nominal)]
    for axis in AXES:
        for level in (levels[axis][0], levels[axis][2]):
            corner = dict(nominal)
            corner[axis] = level
            corners.append(corner)
    extreme_low = {"temperature": "cold", "process": "slow", "supply": "low"}
    extreme_high = {"temperature": "hot", "process": "fast", "supply": "high"}
    corners.append(extreme_low)
    corners.append(extreme_high)
    return corners


def evaluate_sensitivity(case):
    """Full clause 7.2.6 spread evaluation with a specification verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    bases = case.get("bases")
    if not isinstance(bases, dict):
        raise ValueError("case needs a bases mapping for the three axes")
    sensitivities = case.get("sensitivities")
    if not isinstance(sensitivities, dict):
        raise ValueError("case needs a sensitivities mapping for the three axes")
    missing = set(AXES) - set(sensitivities)
    if missing:
        raise ValueError(
            "sensitivities is missing an axis: %s" % ", ".join(sorted(missing))
        )

    excursions = {
        "temperature": temperature_excursions_k(
            case.get("t_min_c"), case.get("t_max_c"), case.get("t_reference_c")
        ),
        "supply": supply_excursions_v(
            case.get("v_min_v"), case.get("v_max_v"), case.get("v_nominal_v")
        ),
        "process": process_excursions_sigma(
            case.get("process_sigma"),
            case.get("coverage_sigma", DEFAULT_PROCESS_COVERAGE_SIGMA),
        ),
    }

    findings = []
    contributions = {}
    for axis in AXES:
        statistical = axis_basis_is_statistical(axis, bases[axis])
        contributions[axis] = {
            "pair": axis_contribution(sensitivities[axis], excursions[axis]),
            "statistical": statistical,
            "basis": bases[axis],
        }
    if bases["process"] == "foundry-nominal-only":
        findings.append(
            "process spread rests on a foundry nominal with no lot statistics; "
            "the sigma carried here is an assumption, not measured data"
        )
    if bases["supply"] == "unbounded-rail":
        findings.append(
            "the supply rail has no declared regulation band; the excursion "
            "used is a placeholder until the rail is specified"
        )
    if bases["temperature"] == "room-temperature-only":
        findings.append(
            "the temperature sensitivity was taken at room temperature only; "
            "the slope over the envelope is extrapolated, not characterised"
        )

    method = select_combination_method(bases)
    spread_low, spread_high = combine_contributions(contributions, method)
    nominal = _require_number("nominal_value", case.get("nominal_value"))
    window_low, window_high = performance_window(nominal, spread_low, spread_high)
    ranked = rank_contributors(contributions)

    spec_low = case.get("spec_min")
    spec_high = case.get("spec_max")
    result = {
        "combination_method": method,
        "excursions": excursions,
        "contributions": {a: contributions[a]["pair"] for a in AXES},
        "spread_low": spread_low,
        "spread_high": spread_high,
        "total_spread": window_high - window_low,
        "window_low": window_low,
        "window_high": window_high,
        "ranked_contributors": ranked,
        "dominant_axis": ranked[0]["axis"],
        "corner_matrix": corner_matrix(bool(case.get("monotone_sensitivities", True))),
        "findings": findings,
    }
    if spec_low is None and spec_high is None:
        result.update(
            {
                "low_margin": None,
                "high_margin": None,
                "compliant": None,
                "verdict": "spread-not-graded",
            }
        )
        findings.append(
            "no specification window supplied; the spread is quantified but "
            "not yet graded against a requirement"
        )
        return result
    if spec_low is not None:
        spec_low = _require_number("spec_min", spec_low)
    if spec_high is not None:
        spec_high = _require_number("spec_max", spec_high)
    if spec_low is not None and spec_high is not None and spec_high < spec_low:
        raise ValueError("spec_max %g is below spec_min %g" % (spec_high, spec_low))
    low_margin = None
    high_margin = None
    compliant = True
    if spec_low is not None:
        low_margin = window_low - spec_low
        compliant = compliant and _at_least(low_margin, 0.0)
    if spec_high is not None:
        high_margin = spec_high - window_high
        compliant = compliant and _at_least(high_margin, 0.0)
    result.update(
        {
            "low_margin": low_margin,
            "high_margin": high_margin,
            "compliant": compliant,
            "verdict": (
                "spread-within-specification" if compliant
                else "spread-exceeds-specification"
            ),
        }
    )
    if not compliant:
        findings.append(
            "the %s window %.4f..%.4f leaves the specification; %s owns %.0f%% "
            "of the spread"
            % (
                method,
                window_low,
                window_high,
                ranked[0]["axis"],
                100.0 * ranked[0]["share"],
            )
        )
    return result
