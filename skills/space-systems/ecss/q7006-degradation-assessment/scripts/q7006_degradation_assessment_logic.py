"""Particle and UV radiation testing: degradation against the criteria.

Anchor: ECSS-Q-ST-70-06C, the evaluation clause of particle and UV
radiation testing for space materials (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Degradation is the signed movement of a property in the direction
   that hurts. Solar absorptance degrades upwards, transmittance,
   emittance and tensile strength downwards, so the sign convention has
   to be carried with the property and not assumed.
2. The measured change is worth nothing without the uncertainty quoted
   against it. The figure compared with a criterion is the worst case:
   the measured degradation plus its expanded uncertainty. A change
   smaller than that uncertainty is not a measured change at all.
3. A test is almost never run to the mission end-of-life fluence or UV
   dose. The tested degradation is extrapolated along a growth model --
   proportional, square-root, or already saturated -- and the model is a
   declared input, not something inferred from two points.
4. An extrapolation stretched far past the tested exposure is a
   modelling statement, not a measurement. Past a factor limit it is
   reported as such so the reviewer can ask for more beam time instead
   of quietly accepting a number nobody measured.
5. The material is accepted only when both the end-of-test and the
   end-of-life worst cases sit inside their criteria.

Stdlib only, offline, deterministic.
"""

import math

DIRECTIONS = ("increase-is-degradation", "decrease-is-degradation")

GROWTH_MODELS = ("linear", "square-root", "saturated")

# An extrapolation stretched further than this past the tested exposure
# is reported as a modelling statement.
MAX_EXTRAPOLATION_FACTOR = 10.0

# Degradations and criteria are built from decimal literals, so a value
# sitting exactly on a limit can land a few units in the last place past
# it. This tolerance absorbs that representation error only; no criterion
# is ever relaxed.
CRITERION_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None):
    """Return value as a float, raising on anything that is not a number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    val = float(value)
    if minimum is not None and val < minimum - CRITERION_TOLERANCE:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return val


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def _direction(value):
    direction = _text("direction", value)
    if direction not in DIRECTIONS:
        raise ValueError("unknown degradation direction %r" % (direction,))
    return direction


def degradation_delta(initial, exposed, direction):
    """Signed movement of a property in the direction that hurts."""
    start = _numeric("initial", initial)
    end = _numeric("exposed", exposed)
    if _direction(direction) == "increase-is-degradation":
        return end - start
    return start - end


def relative_degradation(initial, exposed, direction):
    """Degradation as a fraction of the pristine value."""
    start = _numeric("initial", initial)
    if abs(start) <= CRITERION_TOLERANCE:
        raise ValueError("relative degradation needs a non-zero pristine value")
    return degradation_delta(start, exposed, direction) / abs(start)


def worst_case_degradation(delta, expanded_uncertainty):
    """Degradation plus the expanded uncertainty quoted against it."""
    value = _numeric("delta", delta)
    unc = _numeric("expanded_uncertainty", expanded_uncertainty, 0.0)
    return value + unc


def change_is_measurable(delta, expanded_uncertainty):
    """True when the movement stands clear of its own uncertainty."""
    value = abs(_numeric("delta", delta))
    unc = _numeric("expanded_uncertainty", expanded_uncertainty, 0.0)
    return value + CRITERION_TOLERANCE >= unc


def extrapolation_factor(test_exposure, eol_exposure):
    """How far past the tested exposure the mission end-of-life sits."""
    tested = _numeric("test_exposure", test_exposure, 0.0)
    eol = _numeric("eol_exposure", eol_exposure, 0.0)
    if tested <= 0.0:
        raise ValueError("test_exposure must be greater than zero")
    return eol / tested


def extrapolate_degradation(delta_test, test_exposure, eol_exposure, model):
    """Grow a tested degradation out to the mission end-of-life exposure."""
    value = _numeric("delta_test", delta_test)
    factor = extrapolation_factor(test_exposure, eol_exposure)
    shape = _text("model", model)
    if shape not in GROWTH_MODELS:
        raise ValueError("unknown growth model %r" % (shape,))
    if shape == "saturated":
        return value
    if shape == "square-root":
        return value * math.sqrt(factor)
    return value * factor


def margin_to_criterion(value, criterion):
    """How much room is left between a degradation and its criterion."""
    return _numeric("criterion", criterion) - _numeric("value", value)


def meets_criterion(value, criterion):
    """True when a degradation sits at or inside its criterion."""
    return (
        _numeric("value", value)
        <= _numeric("criterion", criterion) + CRITERION_TOLERANCE
    )


def assess_degradation(record):
    """Assess one irradiated property against its acceptance criteria."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")

    name = _text("property", record.get("property"))
    direction = _direction(record.get("direction"))
    initial = _numeric("pristine_value", record.get("pristine_value"))
    exposed = _numeric("exposed_value", record.get("exposed_value"))
    unc = _numeric(
        "expanded_uncertainty", record.get("expanded_uncertainty", 0.0), 0.0
    )
    acceptance = _numeric("acceptance_criterion", record.get("acceptance_criterion"))
    eol_criterion = _numeric(
        "end_of_life_criterion", record.get("end_of_life_criterion", acceptance)
    )
    model = _text("growth_model", record.get("growth_model", "linear"))
    if model not in GROWTH_MODELS:
        raise ValueError("unknown growth model %r" % (model,))

    delta = degradation_delta(initial, exposed, direction)
    worst_case = worst_case_degradation(delta, unc)

    findings = []
    if not change_is_measurable(delta, unc):
        findings.append("change-inside-the-measurement-uncertainty")

    factor = extrapolation_factor(
        record.get("test_exposure"), record.get("end_of_life_exposure")
    )
    delta_eol = extrapolate_degradation(
        delta,
        record.get("test_exposure"),
        record.get("end_of_life_exposure"),
        model,
    )
    worst_case_eol = worst_case_degradation(delta_eol, unc)

    if factor > MAX_EXTRAPOLATION_FACTOR + CRITERION_TOLERANCE:
        findings.append("extrapolation-beyond-the-tested-exposure-limit")

    if not meets_criterion(worst_case, acceptance):
        findings.append("end-of-test-degradation-exceeds-the-acceptance-criterion")
        if meets_criterion(delta, acceptance):
            findings.append("acceptance-criterion-met-only-without-the-uncertainty")

    if not meets_criterion(worst_case_eol, eol_criterion):
        findings.append("end-of-life-degradation-exceeds-its-criterion")
        if meets_criterion(delta_eol, eol_criterion):
            findings.append("end-of-life-criterion-met-only-without-the-uncertainty")

    exceeded = [
        f for f in findings
        if f.endswith("exceeds-the-acceptance-criterion")
        or f.endswith("exceeds-its-criterion")
    ]

    return {
        "property": name,
        "direction": direction,
        "degradation": delta,
        "relative_degradation": relative_degradation(initial, exposed, direction),
        "worst_case_degradation": worst_case,
        "extrapolation_factor": factor,
        "growth_model": model,
        "end_of_life_degradation": delta_eol,
        "worst_case_end_of_life": worst_case_eol,
        "acceptance_margin": margin_to_criterion(worst_case, acceptance),
        "end_of_life_margin": margin_to_criterion(worst_case_eol, eol_criterion),
        "findings": findings,
        "accepted": not exceeded,
    }
