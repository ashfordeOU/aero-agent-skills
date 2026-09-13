"""Purpose of the solar-array thermal-cycling run: fatigue-endurance demonstration.

Anchor: ECSS-E-ST-20-08C clause 5.5.1.3.1 (thermal cycling -- showing that the
components and the assembly processes of a photovoltaic assembly endure the
repeated temperature swings of the mission). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the predicted in-orbit extremes and the extremes the run is driven
   between, and form both temperature swings.
2. Derive the in-orbit cycle count from the orbit period, the mission duration
   and the fraction of orbits that carry an eclipse.
3. Form the cycle equivalence between the in-orbit swing and the wider test
   swing with a Coffin-Manson style exponent, and convert the in-orbit count
   into the number of test cycles that demonstrates the same fatigue exposure.
4. Check the run: the test extremes envelope the predicted extremes with their
   margin, the dwell is long enough for the assembly to stabilise, the
   transition ramp stays under its bound.
5. Check the cycled article carries every component and process family of the
   flight assembly, since a family absent from the article is a family the run
   demonstrates nothing about.
6. Report the derived counts, the achieved cycle margin and every finding; the
   purpose is demonstrated only when the finding list is empty.
"""

import math

__all__ = [
    "MINUTES_PER_YEAR",
    "CYCLE_TOLERANCE",
    "TEMPERATURE_TOLERANCE_K",
    "DEFAULT_FATIGUE_EXPONENT",
    "MIN_DEMONSTRATED_CYCLES",
    "validate_extremes",
    "cycle_range_k",
    "predicted_orbit_cycles",
    "cycle_equivalence_factor",
    "required_test_cycles",
    "ramp_rate_k_per_min",
    "extreme_findings",
    "family_coverage",
    "assess_cycling_purpose",
]

MINUTES_PER_YEAR = 365.25 * 24.0 * 60.0

# A cycle count is the ceiling of a product of floats; an exactly integral
# product must not be bumped to the next cycle by representation error.
CYCLE_TOLERANCE = 1e-9

# An extreme sitting exactly on its required value is compliant: the comparison
# absorbs the representation error, the engineering margin is never relaxed.
TEMPERATURE_TOLERANCE_K = 1e-9

# Crack growth in a solder or weld joint scales with the swing raised to a
# power; two is the conventional starting exponent for a ductile joint.
DEFAULT_FATIGUE_EXPONENT = 2.0

# However favourable the equivalence, a demonstration of one cycle is not a
# demonstration of endurance.
MIN_DEMONSTRATED_CYCLES = 1


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, number))
    return number


def _non_negative(value, label):
    """Return value as a non-negative finite float."""
    number = _real(value, label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, number))
    return number


def validate_extremes(cold_c, hot_c, label="extremes"):
    """Return the validated (cold, hot) temperature pair in degrees Celsius."""
    cold = _real(cold_c, "%s cold limit" % label)
    hot = _real(hot_c, "%s hot limit" % label)
    if hot <= cold:
        raise ValueError(
            "%s hot limit %g must exceed the cold limit %g" % (label, hot, cold)
        )
    return (cold, hot)


def cycle_range_k(cold_c, hot_c, label="extremes"):
    """Return the temperature swing in kelvin between two extremes."""
    cold, hot = validate_extremes(cold_c, hot_c, label)
    return hot - cold


def predicted_orbit_cycles(orbit_period_min, mission_years, eclipse_fraction=1.0):
    """Return the number of in-orbit temperature cycles over the mission."""
    period = _positive(orbit_period_min, "orbit_period_min")
    years = _positive(mission_years, "mission_years")
    fraction = _real(eclipse_fraction, "eclipse_fraction")
    if fraction <= 0.0 or fraction > 1.0:
        raise ValueError(
            "eclipse_fraction must lie in (0, 1], got %g" % fraction
        )
    orbits = years * MINUTES_PER_YEAR / period
    return int(math.ceil(orbits * fraction - CYCLE_TOLERANCE))


def cycle_equivalence_factor(orbit_range_k, test_range_k,
                             exponent=DEFAULT_FATIGUE_EXPONENT):
    """Return how many in-orbit cycles one test cycle stands for."""
    orbit_swing = _positive(orbit_range_k, "orbit_range_k")
    test_swing = _positive(test_range_k, "test_range_k")
    power = _real(exponent, "exponent")
    if power < 1.0:
        raise ValueError("exponent must be at least 1.0, got %g" % power)
    return (test_swing / orbit_swing) ** power


def required_test_cycles(predicted_cycles, equivalence,
                         demonstration_factor=1.0,
                         minimum_cycles=MIN_DEMONSTRATED_CYCLES):
    """Return the test-cycle count that demonstrates the in-orbit exposure."""
    if not isinstance(predicted_cycles, int) or isinstance(predicted_cycles, bool):
        raise ValueError(
            "predicted_cycles must be an integer, got %r" % (predicted_cycles,)
        )
    if predicted_cycles <= 0:
        raise ValueError(
            "predicted_cycles must be strictly positive, got %d" % predicted_cycles
        )
    factor = _positive(equivalence, "equivalence")
    demonstration = _real(demonstration_factor, "demonstration_factor")
    if demonstration < 1.0:
        raise ValueError(
            "demonstration_factor must be at least 1.0, got %g" % demonstration
        )
    if not isinstance(minimum_cycles, int) or isinstance(minimum_cycles, bool):
        raise ValueError("minimum_cycles must be an integer")
    if minimum_cycles < 1:
        raise ValueError("minimum_cycles must be at least 1, got %d" % minimum_cycles)
    raw = predicted_cycles * demonstration / factor
    return max(int(math.ceil(raw - CYCLE_TOLERANCE)), minimum_cycles)


def ramp_rate_k_per_min(range_k, transition_min):
    """Return the transition ramp rate in kelvin per minute."""
    swing = _positive(range_k, "range_k")
    transition = _positive(transition_min, "transition_min")
    return swing / transition


def extreme_findings(predicted, test, margin_k=0.0):
    """Return findings where the test extremes fail to envelope the prediction."""
    predicted_cold, predicted_hot = validate_extremes(
        predicted[0], predicted[1], "predicted"
    )
    test_cold, test_hot = validate_extremes(test[0], test[1], "test")
    margin = _non_negative(margin_k, "margin_k")
    findings = []
    required_hot = predicted_hot + margin
    required_cold = predicted_cold - margin
    if test_hot < required_hot - TEMPERATURE_TOLERANCE_K:
        findings.append(
            "test hot limit %g C does not reach the predicted hot limit plus "
            "margin, %g C" % (test_hot, required_hot)
        )
    if test_cold > required_cold + TEMPERATURE_TOLERANCE_K:
        findings.append(
            "test cold limit %g C does not reach the predicted cold limit minus "
            "margin, %g C" % (test_cold, required_cold)
        )
    return findings


def _normalize_family(name):
    """Return a family name lowered, trimmed and hyphenated."""
    if not isinstance(name, str):
        raise ValueError("family name must be a string, got %r" % (name,))
    cleaned = " ".join(name.strip().lower().replace("_", " ").split())
    if not cleaned:
        raise ValueError("family name must not be empty")
    return cleaned.replace(" ", "-")


def family_coverage(article_families, flight_families):
    """Return (covered, missing) family names for the cycled article."""
    for label, value in (("article_families", article_families),
                         ("flight_families", flight_families)):
        if not isinstance(value, (list, tuple)):
            raise ValueError("%s must be a sequence of names" % label)
    article = [_normalize_family(name) for name in article_families]
    flight = [_normalize_family(name) for name in flight_families]
    if not flight:
        raise ValueError("flight_families must name at least one family")
    covered = [name for name in flight if name in article]
    missing = [name for name in flight if name not in article]
    return (covered, missing)


def assess_cycling_purpose(spec):
    """Run the full clause 5.5.1.3.1 fatigue-endurance demonstration check.

    spec keys: orbit_period_min, mission_years, predicted_extremes_c (pair),
    test_extremes_c (pair), planned_cycles, dwell_min, required_dwell_min,
    flight_families, article_families; optional eclipse_fraction, margin_k,
    fatigue_exponent, demonstration_factor, transition_min,
    max_ramp_k_per_min.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "orbit_period_min",
        "mission_years",
        "predicted_extremes_c",
        "test_extremes_c",
        "planned_cycles",
        "dwell_min",
        "required_dwell_min",
        "flight_families",
        "article_families",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    for key in ("predicted_extremes_c", "test_extremes_c"):
        pair = spec[key]
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("spec['%s'] must be a (cold_c, hot_c) pair" % key)
    planned = spec["planned_cycles"]
    if not isinstance(planned, int) or isinstance(planned, bool):
        raise ValueError("planned_cycles must be an integer, got %r" % (planned,))
    if planned <= 0:
        raise ValueError("planned_cycles must be strictly positive, got %d" % planned)

    orbit_swing = cycle_range_k(
        spec["predicted_extremes_c"][0], spec["predicted_extremes_c"][1], "predicted"
    )
    test_swing = cycle_range_k(
        spec["test_extremes_c"][0], spec["test_extremes_c"][1], "test"
    )
    predicted_cycles = predicted_orbit_cycles(
        spec["orbit_period_min"],
        spec["mission_years"],
        spec.get("eclipse_fraction", 1.0),
    )
    equivalence = cycle_equivalence_factor(
        orbit_swing, test_swing, spec.get("fatigue_exponent", DEFAULT_FATIGUE_EXPONENT)
    )
    required = required_test_cycles(
        predicted_cycles, equivalence, spec.get("demonstration_factor", 1.0)
    )

    findings = list(
        extreme_findings(
            spec["predicted_extremes_c"],
            spec["test_extremes_c"],
            spec.get("margin_k", 0.0),
        )
    )
    if planned < required:
        findings.append(
            "planned %d cycles are short of the %d cycles that demonstrate the "
            "%d in-orbit cycles" % (planned, required, predicted_cycles)
        )
    dwell = _positive(spec["dwell_min"], "dwell_min")
    required_dwell = _positive(spec["required_dwell_min"], "required_dwell_min")
    if dwell < required_dwell - CYCLE_TOLERANCE:
        findings.append(
            "dwell of %g min is below the %g min the assembly needs to stabilise"
            % (dwell, required_dwell)
        )
    ramp = None
    if spec.get("transition_min") is not None:
        ramp = ramp_rate_k_per_min(test_swing, spec["transition_min"])
        bound = spec.get("max_ramp_k_per_min")
        if bound is not None:
            limit = _positive(bound, "max_ramp_k_per_min")
            if ramp > limit + CYCLE_TOLERANCE:
                findings.append(
                    "transition ramp of %g K/min exceeds the %g K/min bound"
                    % (ramp, limit)
                )
    covered, missing = family_coverage(
        spec["article_families"], spec["flight_families"]
    )
    for name in missing:
        findings.append(
            "flight family '%s' is absent from the cycled article" % name
        )
    return {
        "predicted_cycles": predicted_cycles,
        "orbit_range_k": orbit_swing,
        "test_range_k": test_swing,
        "equivalence": equivalence,
        "required_cycles": required,
        "planned_cycles": planned,
        "cycle_margin": planned - required,
        "ramp_rate_k_per_min": ramp,
        "covered_families": covered,
        "missing_families": missing,
        "findings": findings,
        "demonstrated": not findings,
    }
