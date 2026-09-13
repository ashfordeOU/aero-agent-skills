"""Purpose of the electron irradiation test: accelerated life of a solar cell.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.11.1 (electron irradiation -- an
accelerated check of how much of a photovoltaic cell's electrical performance
the trapped and solar electron environment takes away over the mission).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Turn the declared annual equivalent electron fluence, the mission duration
   and the design margin into the end-of-life fluence the test has to reach.
2. Check the planned fluence steps: strictly rising, enough of them to trace a
   degradation curve rather than a single before-and-after pair, each carrying
   enough cells to mean something, and the highest reaching the end-of-life
   fluence.
3. Turn the beam flux and the mission mean flux into the acceleration factor,
   and bound it from both sides: below unity the test is not accelerated at
   all, far above the bound the beam outruns the recovery processes the cell
   undergoes in flight and the loss it measures is not the mission's.
4. Apply the logarithmic degradation fit to every declared parameter to predict
   what fraction of short-circuit current, open-circuit voltage and maximum
   power survives the end-of-life fluence.
5. Compare the predicted maximum-power retention with the end-of-life fraction
   the power budget assumes.
6. Report the derived fluence, acceleration, exposure time, per-parameter
   retention, every finding and the verdict; the purpose is served only when
   the finding list is empty.
"""

import math

__all__ = [
    "SECONDS_PER_YEAR",
    "RELATIVE_TOLERANCE",
    "MIN_FLUENCE_LEVELS",
    "MIN_CELLS_PER_LEVEL",
    "MAX_ACCELERATION_FACTOR",
    "end_of_life_fluence",
    "mission_mean_flux",
    "acceleration_factor",
    "exposure_time_s",
    "remaining_fraction",
    "predicted_retention",
    "validate_fluence_levels",
    "coverage_findings",
    "assess_electron_irradiation_purpose",
]

SECONDS_PER_YEAR = 365.25 * 24.0 * 3600.0

# A fluence or an acceleration sitting exactly on a bound is compliant; the
# comparison carries the representation error, the bound itself never moves.
RELATIVE_TOLERANCE = 1e-9

# Two points give a line through a curve; a degradation trend needs three.
MIN_FLUENCE_LEVELS = 3

# One cell at a fluence level is an anecdote about that cell.
MIN_CELLS_PER_LEVEL = 3

# Beyond this the beam deposits the mission's damage faster than the cell's own
# recovery processes run, so the measured loss overstates the flight loss.
MAX_ACCELERATION_FACTOR = 1.0e7


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


def _name(value, label):
    """Return a trimmed, non-empty identifier string."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise ValueError("%s must not be empty" % label)
    return cleaned


def end_of_life_fluence(annual_fluence, mission_years, margin_factor=1.0):
    """Return the equivalent electron fluence the mission accumulates."""
    annual = _positive(annual_fluence, "annual_fluence")
    years = _positive(mission_years, "mission_years")
    margin = _real(margin_factor, "margin_factor")
    if margin < 1.0:
        raise ValueError("margin_factor must be at least 1.0, got %g" % margin)
    return annual * years * margin


def mission_mean_flux(annual_fluence):
    """Return the mean electron flux the mission environment delivers."""
    annual = _positive(annual_fluence, "annual_fluence")
    return annual / SECONDS_PER_YEAR


def acceleration_factor(beam_flux, mean_flux):
    """Return how much faster the beam delivers damage than the environment."""
    beam = _positive(beam_flux, "beam_flux")
    environment = _positive(mean_flux, "mean_flux")
    return beam / environment


def exposure_time_s(fluence, beam_flux):
    """Return the beam time a fluence level takes to accumulate."""
    target = _positive(fluence, "fluence")
    beam = _positive(beam_flux, "beam_flux")
    return target / beam


def remaining_fraction(fluence, coefficient, reference_fluence):
    """Return the fraction of a cell parameter surviving a given fluence."""
    exposure = _non_negative(fluence, "fluence")
    factor = _real(coefficient, "coefficient")
    if not 0.0 < factor < 1.0:
        raise ValueError("coefficient must lie in (0, 1), got %g" % factor)
    reference = _positive(reference_fluence, "reference_fluence")
    loss = factor * math.log10(1.0 + exposure / reference)
    return max(0.0, 1.0 - loss)


def predicted_retention(fluence, parameters):
    """Return the surviving fraction of every declared cell parameter."""
    if not isinstance(parameters, dict) or not parameters:
        raise ValueError("parameters must be a non-empty mapping")
    retention = {}
    for key, fit in parameters.items():
        label = _name(key, "parameter name")
        if not isinstance(fit, dict):
            raise ValueError("fit for '%s' must be a mapping" % label)
        for field in ("coefficient", "reference_fluence"):
            if field not in fit:
                raise ValueError(
                    "fit for '%s' missing key '%s'" % (label, field)
                )
        retention[label] = remaining_fraction(
            fluence, fit["coefficient"], fit["reference_fluence"]
        )
    return retention


def validate_fluence_levels(levels):
    """Return the validated, strictly rising list of planned fluence levels."""
    if not isinstance(levels, (list, tuple)):
        raise ValueError("levels must be a sequence of fluence values")
    values = [_positive(level, "fluence level") for level in levels]
    if not values:
        raise ValueError("levels must name at least one fluence")
    for earlier, later in zip(values, values[1:]):
        if later <= earlier:
            raise ValueError(
                "fluence levels must strictly rise, %g follows %g"
                % (later, earlier)
            )
    return values


def coverage_findings(levels, cells_per_level, required_fluence,
                      min_levels=MIN_FLUENCE_LEVELS,
                      min_cells=MIN_CELLS_PER_LEVEL):
    """Return findings where the planned fluence steps cannot trace the loss."""
    values = validate_fluence_levels(levels)
    if not isinstance(cells_per_level, (list, tuple)):
        raise ValueError("cells_per_level must be a sequence of cell counts")
    if len(cells_per_level) != len(values):
        raise ValueError(
            "cells_per_level has %d entries for %d fluence levels"
            % (len(cells_per_level), len(values))
        )
    for bound, label in ((min_levels, "min_levels"), (min_cells, "min_cells")):
        if not isinstance(bound, int) or isinstance(bound, bool):
            raise ValueError("%s must be an integer, got %r" % (label, bound))
        if bound < 1:
            raise ValueError("%s must be at least 1, got %d" % (label, bound))
    target = _positive(required_fluence, "required_fluence")
    findings = []
    if len(values) < min_levels:
        findings.append(
            "%d fluence levels are planned, under the %d a degradation trend "
            "needs" % (len(values), min_levels)
        )
    for level, count in zip(values, cells_per_level):
        if not isinstance(count, int) or isinstance(count, bool):
            raise ValueError("cell count must be an integer, got %r" % (count,))
        if count < 1:
            raise ValueError("cell count must be at least 1, got %d" % count)
        if count < min_cells:
            findings.append(
                "fluence level %g carries %d cells, under the %d a level needs"
                % (level, count, min_cells)
            )
    highest = values[-1]
    if highest < target * (1.0 - RELATIVE_TOLERANCE):
        findings.append(
            "the highest planned fluence %g falls short of the %g the mission "
            "accumulates, so end of life is never reached" % (highest, target)
        )
    return findings


def assess_electron_irradiation_purpose(spec):
    """Run the full clause 6.4.3.11.1 accelerated-life purpose check.

    spec keys: annual_fluence, mission_years, fluence_levels,
    cells_per_level, beam_flux, parameters (name -> coefficient,
    reference_fluence), required_eol_fraction; optional margin_factor,
    min_levels, min_cells, max_acceleration, power_parameter.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "annual_fluence",
        "mission_years",
        "fluence_levels",
        "cells_per_level",
        "beam_flux",
        "parameters",
        "required_eol_fraction",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    required_eol = _positive(spec["required_eol_fraction"], "required_eol_fraction")
    if required_eol > 1.0:
        raise ValueError(
            "required_eol_fraction must not exceed 1.0, got %g" % required_eol
        )
    power_key = _name(spec.get("power_parameter", "pmax"), "power_parameter")

    target = end_of_life_fluence(
        spec["annual_fluence"], spec["mission_years"], spec.get("margin_factor", 1.0)
    )
    mean_flux = mission_mean_flux(spec["annual_fluence"])
    acceleration = acceleration_factor(spec["beam_flux"], mean_flux)
    findings = list(
        coverage_findings(
            spec["fluence_levels"],
            spec["cells_per_level"],
            target,
            spec.get("min_levels", MIN_FLUENCE_LEVELS),
            spec.get("min_cells", MIN_CELLS_PER_LEVEL),
        )
    )
    ceiling = _positive(
        spec.get("max_acceleration", MAX_ACCELERATION_FACTOR), "max_acceleration"
    )
    if ceiling <= 1.0:
        raise ValueError("max_acceleration must exceed 1.0, got %g" % ceiling)
    if acceleration < 1.0 - RELATIVE_TOLERANCE:
        findings.append(
            "the beam delivers damage at %.3g times the environment rate, so "
            "the run is not an accelerated check at all" % acceleration
        )
    elif acceleration > ceiling * (1.0 + RELATIVE_TOLERANCE):
        findings.append(
            "the acceleration of %.3g exceeds the %.3g bound, so the beam "
            "outruns the recovery the cell sees in flight" % (acceleration, ceiling)
        )
    retention = predicted_retention(target, spec["parameters"])
    if power_key not in retention:
        raise ValueError(
            "parameters must include the power parameter '%s'" % power_key
        )
    power_retention = retention[power_key]
    if power_retention < required_eol * (1.0 - RELATIVE_TOLERANCE):
        findings.append(
            "predicted %s retention of %.4f at end of life falls under the "
            "%.4f the power budget assumes" % (power_key, power_retention,
                                               required_eol)
        )
    levels = validate_fluence_levels(spec["fluence_levels"])
    return {
        "eol_fluence": target,
        "mission_mean_flux": mean_flux,
        "acceleration_factor": acceleration,
        "total_exposure_s": math.fsum(
            exposure_time_s(level, spec["beam_flux"]) for level in levels
        ),
        "fluence_levels": levels,
        "retention": retention,
        "power_retention": power_retention,
        "eol_margin": power_retention - required_eol,
        "findings": findings,
        "purpose_met": not findings,
    }
