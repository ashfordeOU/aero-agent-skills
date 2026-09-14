#!/usr/bin/env python3
"""Surviving an electrostatic discharge shaped like a charged person
touching a protection diode terminal.

Anchor: ECSS-E-ST-20-08C clause 9.6.16. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A person walking across a panel bay carries charge, and the moment a
finger or a tool reaches a diode lead that charge leaves through the
junction. The human body model is the agreed stand-in for that event: a
capacitance charged to a step voltage, discharged through a series
resistance into the device. Four things decide whether a campaign
measured survival or measured something else:

    the network      the capacitance and the series resistance. They are
                     what make the pulse representative of a person;
                     outside their bands the discharge is a different
                     event wearing this event's name
    the step series  a geometric ladder of voltages, each level a fixed
                     ratio above the last. A ladder that climbs too
                     slowly hides the step at which the part gave way
    the pulses       a count at every level, in both polarities, with a
                     recovery interval between them. One pulse per level
                     measures luck, and one polarity leaves the reverse
                     path untested
    the drift        reverse leakage and forward voltage read before and
                     after. A part that still conducts is not a part
                     that survived: a junction damaged by a discharge
                     usually shows up first as leakage that grew

The peak current is the step voltage divided by the series resistance,
the decay constant is the product of resistance and capacitance, and the
stored energy is what the junction has to absorb. All three follow from
the network, so a network inside its bands is the precondition for
anything downstream meaning what it says.

The bands, floors and drift limits below are a declared policy, not
physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

HBM_NOMINAL_CAPACITANCE_F = 100e-12
HBM_NOMINAL_RESISTANCE_OHM = 1500.0

POSITIVE_POLARITY = "positive"
NEGATIVE_POLARITY = "negative"
REQUIRED_POLARITIES = (POSITIVE_POLARITY, NEGATIVE_POLARITY)

# Withstand bands, named by their lower edge in volts. A surviving level
# is grouped into the highest band whose floor it reaches.
HBM_WITHSTAND_BANDS = (
    ("hbm-band-a", 0.0),
    ("hbm-band-b", 250.0),
    ("hbm-band-c", 500.0),
    ("hbm-band-d", 1000.0),
    ("hbm-band-e", 2000.0),
    ("hbm-band-f", 4000.0),
)

HBM_NETWORK_DEFICIENT = "diode-hbm-network-deficient"
HBM_WITHSTAND_DEFICIENT = "diode-hbm-withstand-deficient"
HBM_STRESS_PLAN_DEFICIENT = "diode-hbm-stress-plan-deficient"
HBM_SURVIVAL_ACCEPTED = "diode-hbm-survival-accepted"

HBM_VERDICTS = (
    HBM_NETWORK_DEFICIENT,
    HBM_WITHSTAND_DEFICIENT,
    HBM_STRESS_PLAN_DEFICIENT,
    HBM_SURVIVAL_ACCEPTED,
)

DEFAULT_HBM_POLICY = {
    "min_withstand_voltage_v": 1000.0,
    "min_pulses_per_level": 3,
    "min_step_levels": 3,
    "min_step_ratio": 1.5,
    "min_recovery_interval_s": 1.0,
    "min_network_capacitance_f": 90e-12,
    "max_network_capacitance_f": 110e-12,
    "min_network_resistance_ohm": 1425.0,
    "max_network_resistance_ohm": 1575.0,
    "max_leakage_drift_fraction": 1.0,
    "max_forward_voltage_drift_fraction": 0.05,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-18


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


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


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


def validate_hbm_policy(policy):
    """Check a human body ESD policy is self-consistent before it is used."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("min_withstand_voltage_v", policy.get("min_withstand_voltage_v"))
    _require_count("min_pulses_per_level", policy.get("min_pulses_per_level"))
    _require_count("min_step_levels", policy.get("min_step_levels"))
    ratio = _require_positive("min_step_ratio", policy.get("min_step_ratio"))
    if ratio <= 1.0:
        raise ValueError(
            "min_step_ratio %g must climb above one, or the ladder never rises"
            % (ratio,)
        )
    _require_positive("min_recovery_interval_s", policy.get("min_recovery_interval_s"))
    c_low = _require_positive(
        "min_network_capacitance_f", policy.get("min_network_capacitance_f")
    )
    c_high = _require_positive(
        "max_network_capacitance_f", policy.get("max_network_capacitance_f")
    )
    if not c_low < c_high:
        raise ValueError(
            "min_network_capacitance_f %g must sit below max_network_capacitance_f "
            "%g" % (c_low, c_high)
        )
    r_low = _require_positive(
        "min_network_resistance_ohm", policy.get("min_network_resistance_ohm")
    )
    r_high = _require_positive(
        "max_network_resistance_ohm", policy.get("max_network_resistance_ohm")
    )
    if not r_low < r_high:
        raise ValueError(
            "min_network_resistance_ohm %g must sit below "
            "max_network_resistance_ohm %g" % (r_low, r_high)
        )
    _require_positive(
        "max_leakage_drift_fraction", policy.get("max_leakage_drift_fraction")
    )
    _require_positive(
        "max_forward_voltage_drift_fraction",
        policy.get("max_forward_voltage_drift_fraction"),
    )
    return policy


def hbm_peak_current_a(step_voltage_v, body_resistance_ohm=HBM_NOMINAL_RESISTANCE_OHM):
    """Current the discharge starts at: the step voltage across the body."""
    voltage = _require_positive("step_voltage_v", step_voltage_v)
    resistance = _require_positive("body_resistance_ohm", body_resistance_ohm)
    return voltage / resistance


def hbm_decay_time_constant_s(
    body_resistance_ohm=HBM_NOMINAL_RESISTANCE_OHM,
    body_capacitance_f=HBM_NOMINAL_CAPACITANCE_F,
):
    """How long the discharge takes to fall to a fraction of its peak."""
    resistance = _require_positive("body_resistance_ohm", body_resistance_ohm)
    capacitance = _require_positive("body_capacitance_f", body_capacitance_f)
    return resistance * capacitance


def hbm_stored_energy_j(
    step_voltage_v, body_capacitance_f=HBM_NOMINAL_CAPACITANCE_F
):
    """Energy the charged body holds, and the junction has to absorb."""
    voltage = _require_positive("step_voltage_v", step_voltage_v)
    capacitance = _require_positive("body_capacitance_f", body_capacitance_f)
    return 0.5 * capacitance * voltage * voltage


def hbm_transferred_charge_c(
    step_voltage_v, body_capacitance_f=HBM_NOMINAL_CAPACITANCE_F
):
    """Charge that leaves the body through the diode on one pulse."""
    voltage = _require_positive("step_voltage_v", step_voltage_v)
    capacitance = _require_positive("body_capacitance_f", body_capacitance_f)
    return capacitance * voltage


def step_series_voltages(start_voltage_v, step_ratio, levels):
    """The ladder of step voltages a geometric stress series walks up."""
    start = _require_positive("start_voltage_v", start_voltage_v)
    ratio = _require_positive("step_ratio", step_ratio)
    if ratio <= 1.0:
        raise ValueError(
            "step_ratio %g must climb above one, or the ladder never rises"
            % (ratio,)
        )
    count = _require_count("levels", levels)
    series = []
    voltage = start
    for _ in range(count):
        series.append(voltage)
        voltage = voltage * ratio
    return tuple(series)


def hbm_withstand_band(withstand_voltage_v):
    """Group a surviving step voltage into its declared withstand band."""
    voltage = _require_non_negative("withstand_voltage_v", withstand_voltage_v)
    band = HBM_WITHSTAND_BANDS[0][0]
    for name, floor in HBM_WITHSTAND_BANDS:
        if _at_least(voltage, floor):
            band = name
        else:
            break
    return band


def parameter_drift_fraction(initial_value, final_value):
    """Fractional move of a measured parameter across the stress series."""
    initial = _require_positive("initial_value", initial_value)
    final = _require_non_negative("final_value", final_value)
    return abs(final - initial) / initial


def polarity_coverage(pulse_polarities):
    """Distinct required polarities a stress plan actually exercises."""
    if not isinstance(pulse_polarities, (list, tuple)):
        raise ValueError(
            "pulse_polarities must be a list or tuple, got %r" % (pulse_polarities,)
        )
    if not pulse_polarities:
        raise ValueError("pulse_polarities must name at least one polarity")
    seen = set()
    for entry in pulse_polarities:
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError("pulse_polarities holds a blank entry: %r" % (entry,))
        label = entry.strip().lower()
        if label not in REQUIRED_POLARITIES:
            raise ValueError(
                "pulse_polarities holds an unknown polarity %r" % (entry,)
            )
        seen.add(label)
    return len(seen)


def assess_hbm_survival(case, policy=DEFAULT_HBM_POLICY):
    """Full clause 9.6.16 judgement for one human body ESD campaign."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_hbm_policy(policy)
    plan = case.get("stress_plan")
    if not isinstance(plan, dict):
        raise ValueError("case is missing a stress_plan block")
    response = case.get("device_response")
    if not isinstance(response, dict):
        raise ValueError("case is missing a device_response block")

    capacitance = _require_positive(
        "stress_plan network_capacitance_f", plan.get("network_capacitance_f")
    )
    resistance = _require_positive(
        "stress_plan network_resistance_ohm", plan.get("network_resistance_ohm")
    )
    start_voltage = _require_positive(
        "stress_plan start_voltage_v", plan.get("start_voltage_v")
    )
    ratio = _require_positive("stress_plan step_ratio", plan.get("step_ratio"))
    levels = _require_count("stress_plan step_levels", plan.get("step_levels"))
    pulses = _require_count(
        "stress_plan pulses_per_level", plan.get("pulses_per_level")
    )
    interval = _require_positive(
        "stress_plan recovery_interval_s", plan.get("recovery_interval_s")
    )
    polarities = polarity_coverage(plan.get("pulse_polarities"))

    withstand = _require_positive(
        "device_response withstand_voltage_v", response.get("withstand_voltage_v")
    )
    leakage_drift = parameter_drift_fraction(
        response.get("initial_leakage_a"), response.get("final_leakage_a")
    )
    forward_drift = parameter_drift_fraction(
        response.get("initial_forward_voltage_v"),
        response.get("final_forward_voltage_v"),
    )

    series = step_series_voltages(start_voltage, ratio, levels)
    peak_current = hbm_peak_current_a(withstand, resistance)
    decay = hbm_decay_time_constant_s(resistance, capacitance)
    energy = hbm_stored_energy_j(withstand, capacitance)
    charge = hbm_transferred_charge_c(withstand, capacitance)

    findings = []
    result = {
        "step_series_v": series,
        "top_step_voltage_v": series[-1],
        "withstand_voltage_v": withstand,
        "withstand_band": hbm_withstand_band(withstand),
        "peak_current_a": peak_current,
        "decay_time_constant_s": decay,
        "stored_energy_j": energy,
        "transferred_charge_c": charge,
        "leakage_drift_fraction": leakage_drift,
        "forward_voltage_drift_fraction": forward_drift,
        "polarity_coverage": polarities,
        "findings": findings,
    }

    network_off = False
    if not (
        _at_least(capacitance, float(policy["min_network_capacitance_f"]))
        and _at_most(capacitance, float(policy["max_network_capacitance_f"]))
    ):
        network_off = True
        findings.append(
            "the network holds %.4g F against the %.4g to %.4g F band that makes "
            "the pulse a person rather than a bench artefact"
            % (
                capacitance,
                float(policy["min_network_capacitance_f"]),
                float(policy["max_network_capacitance_f"]),
            )
        )
    if not (
        _at_least(resistance, float(policy["min_network_resistance_ohm"]))
        and _at_most(resistance, float(policy["max_network_resistance_ohm"]))
    ):
        network_off = True
        findings.append(
            "the series resistance is %.1f ohm against the %.1f to %.1f ohm band, "
            "so the peak current does not belong to this model"
            % (
                resistance,
                float(policy["min_network_resistance_ohm"]),
                float(policy["max_network_resistance_ohm"]),
            )
        )
    result["network_in_band"] = not network_off

    withstand_short = not _at_least(
        withstand, float(policy["min_withstand_voltage_v"])
    )
    if withstand_short:
        findings.append(
            "the part held %.1f V against the %.1f V the policy asks a protection "
            "diode to survive"
            % (withstand, float(policy["min_withstand_voltage_v"]))
        )
    leakage_failed = not _at_most(
        leakage_drift, float(policy["max_leakage_drift_fraction"])
    )
    if leakage_failed:
        findings.append(
            "reverse leakage moved %.4f of its starting value against the %.4f "
            "limit, which is junction damage rather than a survival"
            % (leakage_drift, float(policy["max_leakage_drift_fraction"]))
        )
    forward_failed = not _at_most(
        forward_drift, float(policy["max_forward_voltage_drift_fraction"])
    )
    if forward_failed:
        findings.append(
            "the forward voltage moved %.4f of its starting value against the "
            "%.4f limit"
            % (forward_drift, float(policy["max_forward_voltage_drift_fraction"]))
        )

    plan_short = False
    if not _at_least(pulses, float(policy["min_pulses_per_level"])):
        plan_short = True
        findings.append(
            "the plan fires %d pulses per level against the %d that separate a "
            "survival from a single lucky discharge"
            % (pulses, int(policy["min_pulses_per_level"]))
        )
    if polarities < len(REQUIRED_POLARITIES):
        plan_short = True
        findings.append(
            "the plan exercises %d of the %d polarities, leaving one conduction "
            "path of the diode unstressed"
            % (polarities, len(REQUIRED_POLARITIES))
        )
    if not _at_least(levels, float(policy["min_step_levels"])):
        plan_short = True
        findings.append(
            "the ladder has %d levels against the %d needed to locate the step "
            "the part gave way at" % (levels, int(policy["min_step_levels"]))
        )
    if not _at_least(ratio, float(policy["min_step_ratio"])):
        plan_short = True
        findings.append(
            "the ladder climbs by %.3f per level against the %.3f minimum, so the "
            "series ends below the level of interest"
            % (ratio, float(policy["min_step_ratio"]))
        )
    if not _at_least(interval, float(policy["min_recovery_interval_s"])):
        plan_short = True
        findings.append(
            "pulses sit %.3f s apart against the %.3f s the part needs to settle "
            "between them"
            % (interval, float(policy["min_recovery_interval_s"]))
        )

    if network_off:
        result["verdict"] = HBM_NETWORK_DEFICIENT
    elif withstand_short or leakage_failed or forward_failed:
        result["verdict"] = HBM_WITHSTAND_DEFICIENT
    elif plan_short:
        result["verdict"] = HBM_STRESS_PLAN_DEFICIENT
    else:
        result["verdict"] = HBM_SURVIVAL_ACCEPTED
    return result
