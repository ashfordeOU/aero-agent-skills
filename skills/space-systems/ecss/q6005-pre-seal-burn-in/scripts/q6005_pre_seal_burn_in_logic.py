"""Pre-seal burn-in: a powered thermal soak run with the package still open.

Anchor: ECSS-Q-ST-60-05 clause 10.3.3 (the biased thermal soak applied to a
hybrid circuit before its package is closed, so that whatever the soak
precipitates can be seen and repaired without breaking a seal).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The soak is worth what it delivers at the reference condition, not what
  the chamber log says in hours. A cooler chamber run for the nominal time
  delivers less stress, and the Arrhenius relation between the two is the
  conversion everyone actually means when they say a soak was equivalent.
* The band is a band. Too cool and the soak precipitates nothing; too hot
  and it damages the assembly it was supposed to sort, and with the package
  open there is no lid holding anything down.
* Bias is what makes it burn-in rather than a bake. An unbiased soak
  precipitates a different and much smaller set of defects.
* Interruptions accumulate up to a point. A short break leaves the unit hot
  and the soak continues; a long one lets it return to ambient, and the
  hours before it no longer form part of a continuous soak.
* Electrical drift across the soak is the result, not the chamber log. A
  parameter that moved more than the allowance moved because something in
  the assembly is unstable, and that is the unit the soak was run to find.
* The package stays open throughout. The value of doing this before the seal
  is that the repair costs nothing to reach, and a unit sealed mid-soak has
  thrown that away.
* The condition index is weighted credit over total weight, and it gates the
  result rather than averaging into it: a soak that missed a mandatory
  condition is invalid rather than a pass with reservations.
"""

from __future__ import annotations

import math

# Absolute zero, for the Arrhenius arithmetic that has to run in kelvin.
KELVIN_OFFSET = 273.15

# Boltzmann's constant in electronvolts per kelvin.
BOLTZMANN_EV_PER_K = 8.617333262e-5

# The condition a soak is converted to before its duration is judged.
REFERENCE_TEMPERATURE_C = 125.0

# Activation energy used when a programme names none of its own.
DEFAULT_ACTIVATION_ENERGY_EV = 0.7

# Chamber band an open-package soak is run inside.
MINIMUM_STRESS_TEMPERATURE_C = 100.0
MAXIMUM_STRESS_TEMPERATURE_C = 150.0

# Equivalent hours at the reference condition a soak has to deliver.
MINIMUM_EQUIVALENT_HOURS = 24.0

# A break longer than this lets the unit return to ambient, and the hours
# before it stop forming part of one continuous soak.
MAXIMUM_INTERRUPTION_HOURS = 4.0

# Fractional movement a monitored parameter may show across the soak.
DEFAULT_DRIFT_LIMIT = 0.10

# Soak conditions and the share of the burn-in argument each supplies.
SOAK_CONDITIONS = {
    "package-open-throughout-the-soak": 1.0,
    "bias-applied-at-the-specified-condition": 1.0,
    "chamber-temperature-inside-the-permitted-band": 1.0,
    "equivalent-duration-delivered": 1.0,
    "pre-and-post-soak-electrical-measurement": 1.0,
    "chamber-temperature-continuously-recorded": 0.8,
    "interruptions-logged-with-their-duration": 0.6,
}

# Conditions without which there is no soak to grade.
MANDATORY_SOAK_CONDITIONS = (
    "package-open-throughout-the-soak",
    "bias-applied-at-the-specified-condition",
    "chamber-temperature-inside-the-permitted-band",
    "equivalent-duration-delivered",
    "pre-and-post-soak-electrical-measurement",
)

CONDITION_STATE_CREDIT = {
    "met-and-recorded": 1.0,
    "met-not-recorded": 0.6,
    "not-met": 0.0,
}

# Condition index a readable burn-in has to reach.
ACCEPTANCE_INDEX = 0.85

# Durations and acceleration factors are computed; a case meant to sit on a
# bound can land a few units in the last place away from it.
BURN_IN_TOLERANCE = 1e-9

VERDICTS = (
    "pre-seal-burn-in-passed",
    "pre-seal-burn-in-passed-with-open-actions",
    "unit-rejected-on-pre-seal-burn-in",
    "pre-seal-burn-in-invalid",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    """Return ``value`` as a strictly positive finite float or raise."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _non_negative(value, label):
    """Return ``value`` as a finite float at or above zero or raise."""
    number = _real(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _kelvin(value, label):
    """Return a celsius reading as kelvin, rejecting anything below zero K."""
    number = _real(value, label)
    kelvin = number + KELVIN_OFFSET
    if kelvin <= 0.0:
        raise ValueError("%s must be above absolute zero, got %r" % (label, value))
    return kelvin


def temperature_inside_band(temperature_c):
    """True while a chamber setting sits inside the open-package soak band."""
    temperature = _real(temperature_c, "temperature_c")
    return (
        temperature >= MINIMUM_STRESS_TEMPERATURE_C - BURN_IN_TOLERANCE
        and temperature <= MAXIMUM_STRESS_TEMPERATURE_C + BURN_IN_TOLERANCE
    )


def acceleration_factor(
    stress_temperature_c,
    reference_temperature_c=None,
    activation_energy_ev=None,
):
    """How much faster the stress condition ages the part than the reference."""
    stress_k = _kelvin(stress_temperature_c, "stress_temperature_c")
    reference_k = _kelvin(
        REFERENCE_TEMPERATURE_C
        if reference_temperature_c is None
        else reference_temperature_c,
        "reference_temperature_c",
    )
    energy = _positive(
        DEFAULT_ACTIVATION_ENERGY_EV
        if activation_energy_ev is None
        else activation_energy_ev,
        "activation_energy_ev",
    )
    exponent = (energy / BOLTZMANN_EV_PER_K) * (1.0 / reference_k - 1.0 / stress_k)
    return math.exp(exponent)


def equivalent_reference_hours(
    duration_hours,
    stress_temperature_c,
    reference_temperature_c=None,
    activation_energy_ev=None,
):
    """Hours at the reference condition a soak at the stress condition buys."""
    hours = _non_negative(duration_hours, "duration_hours")
    factor = acceleration_factor(
        stress_temperature_c, reference_temperature_c, activation_energy_ev
    )
    return hours * factor


def continuous_soak_segments(segments):
    """Validate the soak log and keep only the run after the last long break.

    Each segment names the hours the unit spent biased at a temperature and
    the hours of break that followed it. A break longer than the permitted
    interruption lets the unit return to ambient, so the hours before it are
    no longer part of one continuous soak.
    """
    if not isinstance(segments, (list, tuple)) or len(segments) == 0:
        raise ValueError("a soak must carry at least one segment")
    kept = []
    restarts = 0
    for raw in segments:
        if not isinstance(raw, dict):
            raise ValueError("segment must be a mapping, got %r" % (type(raw).__name__,))
        hours = _positive(raw.get("hours"), "hours")
        temperature = _real(raw.get("temperature_c"), "temperature_c")
        gap = _non_negative(raw.get("interruption_hours", 0.0), "interruption_hours")
        kept.append({"hours": hours, "temperature_c": temperature, "interruption_hours": gap})
        if gap > MAXIMUM_INTERRUPTION_HOURS + BURN_IN_TOLERANCE:
            kept = []
            restarts += 1
    return {"segments": kept, "restart_count": restarts}


def delivered_equivalent_hours(segments, reference_temperature_c=None, activation_energy_ev=None):
    """Equivalent reference hours the continuous part of a soak delivered."""
    continuous = continuous_soak_segments(segments)
    total = 0.0
    for segment in continuous["segments"]:
        total += equivalent_reference_hours(
            segment["hours"],
            segment["temperature_c"],
            reference_temperature_c,
            activation_energy_ev,
        )
    return total


def duration_is_sufficient(equivalent_hours, minimum_hours=None):
    """True while a soak delivered the equivalent hours the programme asks."""
    delivered = _non_negative(equivalent_hours, "equivalent_hours")
    floor = _positive(
        MINIMUM_EQUIVALENT_HOURS if minimum_hours is None else minimum_hours,
        "minimum_hours",
    )
    return delivered >= floor - BURN_IN_TOLERANCE


def parameter_drift_fraction(before, after):
    """Fractional movement of a monitored parameter across the soak."""
    start = _real(before, "before")
    end = _real(after, "after")
    if abs(start) <= 0.0:
        raise ValueError("a pre-soak reading of zero gives no drift fraction")
    return abs(end - start) / abs(start)


def drift_within_limit(before, after, limit=None):
    """True while a parameter moved no more than the allowance across the soak."""
    allowance = _positive(
        DEFAULT_DRIFT_LIMIT if limit is None else limit, "limit"
    )
    return parameter_drift_fraction(before, after) <= allowance + BURN_IN_TOLERANCE


def condition_weight(name):
    """Share of the burn-in argument one soak condition supplies."""
    if name not in SOAK_CONDITIONS:
        raise ValueError(
            "unknown soak condition %r (known: %s)"
            % (name, ", ".join(sorted(SOAK_CONDITIONS)))
        )
    return SOAK_CONDITIONS[name]


def condition_state_credit(state):
    """Credit a soak-condition state earns."""
    if state not in CONDITION_STATE_CREDIT:
        raise ValueError(
            "unknown condition state %r (known: %s)"
            % (state, ", ".join(sorted(CONDITION_STATE_CREDIT)))
        )
    return CONDITION_STATE_CREDIT[state]


def assess_condition(name, state):
    """Grade one soak condition into a credit and its findings."""
    weight = condition_weight(name)
    credit = condition_state_credit(state)
    mandatory = name in MANDATORY_SOAK_CONDITIONS
    findings = []
    if state == "not-met":
        findings.append("soak-condition-not-met")
    elif state == "met-not-recorded":
        findings.append("soak-condition-not-recorded")
    mandatory_missing = mandatory and state == "not-met"
    if mandatory_missing:
        findings.append("mandatory-soak-condition-not-met")
    return {
        "condition": name,
        "state": state,
        "mandatory": mandatory,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "mandatory_missing": mandatory_missing,
        "findings": findings,
    }


def condition_index(records):
    """Weighted credit of a set of graded soak conditions over total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError(
            "records must be a list or tuple, got %r" % (type(records).__name__,)
        )
    if len(records) == 0:
        raise ValueError("a soak must carry at least one condition")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total condition weight must be positive")
    return earned / total_weight


def assess_pre_seal_burn_in(
    unit_id,
    segments,
    parameters=(),
    conditions=None,
    minimum_hours=None,
    drift_limit=None,
    activation_energy_ev=None,
):
    """Grade one pre-seal burn-in run and name a single verdict."""
    if not isinstance(unit_id, str) or not unit_id.strip():
        raise ValueError("unit_id must be a non-empty string, got %r" % (unit_id,))
    if conditions is None:
        conditions = {}
    if not isinstance(conditions, dict):
        raise ValueError(
            "conditions must be a mapping, got %r" % (type(conditions).__name__,)
        )
    for name in conditions:
        condition_weight(name)  # validation only
    if not isinstance(parameters, (list, tuple)):
        raise ValueError(
            "parameters must be a list or tuple, got %r" % (type(parameters).__name__,)
        )

    continuous = continuous_soak_segments(segments)
    delivered = delivered_equivalent_hours(
        segments, REFERENCE_TEMPERATURE_C, activation_energy_ev
    )
    sufficient = duration_is_sufficient(delivered, minimum_hours)
    # The band is read over every declared segment, not only the continuous
    # tail: a chamber that left the band did so whether or not the soak was
    # later restarted, and the assembly was there for it.
    out_of_band = sorted(
        {
            _real(raw.get("temperature_c"), "temperature_c")
            for raw in segments
            if not temperature_inside_band(raw.get("temperature_c"))
        }
    )

    states = dict(conditions)
    states["equivalent-duration-delivered"] = "met-and-recorded" if sufficient else "not-met"
    if out_of_band:
        states["chamber-temperature-inside-the-permitted-band"] = "not-met"
    elif "chamber-temperature-inside-the-permitted-band" not in states:
        states["chamber-temperature-inside-the-permitted-band"] = "met-and-recorded"

    condition_records = []
    for name in sorted(SOAK_CONDITIONS):
        state = states.get(name, "not-met")
        if not isinstance(state, str):
            raise ValueError("condition state must be a string, got %r" % (state,))
        condition_records.append(assess_condition(name, state))
    index = condition_index(condition_records)

    findings = []
    for record in condition_records:
        for finding in record["findings"]:
            findings.append(
                {"item": record["condition"], "finding": finding, "detail": record["state"]}
            )
    if continuous["restart_count"]:
        findings.append(
            {
                "item": "soak-log",
                "finding": "soak-restarted-after-a-long-interruption",
                "detail": "%d restart(s)" % (continuous["restart_count"],),
            }
        )
    for temperature in out_of_band:
        findings.append(
            {
                "item": "chamber",
                "finding": "chamber-temperature-outside-the-band",
                "detail": "%.1f C" % (temperature,),
            }
        )

    seen = set()
    parameter_records = []
    drifted = []
    for raw in parameters:
        if not isinstance(raw, dict):
            raise ValueError("parameter must be a mapping, got %r" % (type(raw).__name__,))
        name = raw.get("parameter")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("parameter name must be a non-empty string, got %r" % (name,))
        if name in seen:
            raise ValueError("duplicate monitored parameter %r" % (name,))
        seen.add(name)
        fraction = parameter_drift_fraction(raw.get("before"), raw.get("after"))
        within = drift_within_limit(raw.get("before"), raw.get("after"), drift_limit)
        parameter_records.append(
            {"parameter": name, "drift_fraction": fraction, "within_limit": within}
        )
        if not within:
            drifted.append(name)
            findings.append(
                {
                    "item": name,
                    "finding": "parameter-drift-over-allowance",
                    "detail": "%.4f" % (fraction,),
                }
            )

    invalid = (
        any(record["mandatory_missing"] for record in condition_records)
        or index < ACCEPTANCE_INDEX - BURN_IN_TOLERANCE
    )
    if invalid:
        verdict = "pre-seal-burn-in-invalid"
    elif drifted:
        verdict = "unit-rejected-on-pre-seal-burn-in"
    elif findings:
        verdict = "pre-seal-burn-in-passed-with-open-actions"
    else:
        verdict = "pre-seal-burn-in-passed"

    return {
        "unit_id": unit_id,
        "delivered_equivalent_hours": delivered,
        "duration_sufficient": sufficient,
        "restart_count": continuous["restart_count"],
        "out_of_band_temperatures": out_of_band,
        "condition_records": condition_records,
        "condition_index": index,
        "parameter_records": parameter_records,
        "drifted_parameters": sorted(drifted),
        "findings": findings,
        "verdict": verdict,
        "unit_passed": verdict
        in ("pre-seal-burn-in-passed", "pre-seal-burn-in-passed-with-open-actions"),
    }
