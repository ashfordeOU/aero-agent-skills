#!/usr/bin/env python3
"""Surviving the switching transients a protection diode meets on the
ground and again in orbit.

Anchor: ECSS-E-ST-20-08C clause 9.6.17. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Nothing on an array switches cleanly. A harness has stray inductance, a
switch interrupts a current in a finite time, and the product of the two
appears across whatever is nearest -- which, by design, is the
protection diode. The same mechanism runs twice in a part's life: during
ground handling, where connectors are made and broken by hand and the
count is small but the slew is uncontrolled, and in orbit, where a
sequencer switches strings thousands of times under a current the array
actually carries.

Four quantities decide whether the part comes through:

    the overshoot   the stray inductance times the rate the current is
                    interrupted at. It adds to the rail the diode
                    already stands off, and it is the number that
                    reaches breakdown first
    the standoff    the reverse voltage rating, derated. A rating used
                    at its face value is not a margin, it is a hope, so
                    the peak is held against the derated figure
    the energy      the field the switched string was holding, half L I
                    squared, delivered into the junction in microseconds
    the excursion   the peak clamp power -- that peak voltage carried at
                    the switched current -- through the transient thermal
                    impedance of the package. It is a temperature step,
                    not a steady state, and it lands on top of the case

The event plan matters as much as the physics. Ground handling pulses do
not fill an in-orbit requirement and in-orbit pulses do not fill a ground
handling one: they differ in slew rate, in current and in how many times
they happen, so each category carries its own count.

The floors, limits and derating cap below are a declared policy, not
physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

GROUND_HANDLING = "ground-handling"
IN_ORBIT_SWITCHING = "in-orbit-switching"
SWITCHING_EVENT_CATEGORIES = (GROUND_HANDLING, IN_ORBIT_SWITCHING)

SWITCHING_BREAKDOWN_RISK = "diode-switching-breakdown-risk"
SWITCHING_EXCURSION_EXCESSIVE = "diode-switching-junction-excursion-excessive"
SWITCHING_EVENT_PLAN_DEFICIENT = "protection-diode-switching-event-plan-deficient"
SWITCHING_SURVIVAL_ACCEPTED = "protection-diode-switching-survival-accepted"

SWITCHING_VERDICTS = (
    SWITCHING_BREAKDOWN_RISK,
    SWITCHING_EXCURSION_EXCESSIVE,
    SWITCHING_EVENT_PLAN_DEFICIENT,
    SWITCHING_SURVIVAL_ACCEPTED,
)

DEFAULT_SWITCHING_POLICY = {
    "max_derating_factor": 0.75,
    "min_standoff_margin_fraction": 0.10,
    "max_junction_excursion_k": 25.0,
    "max_peak_junction_temperature_c": 125.0,
    "min_ground_handling_pulses": 10,
    "min_in_orbit_switching_pulses": 50,
    "min_recovery_interval_s": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


def _require_derating_factor(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 1.0:
        raise ValueError(
            "%s must be a derating factor above zero and at most one, got %r"
            % (name, value)
        )
    return number


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


def validate_switching_policy(policy):
    """Check a switching transient policy is self-consistent before use."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_derating_factor("max_derating_factor", policy.get("max_derating_factor"))
    margin = _require_number(
        "min_standoff_margin_fraction", policy.get("min_standoff_margin_fraction")
    )
    if not 0.0 <= margin < 1.0:
        raise ValueError(
            "min_standoff_margin_fraction %g must sit from zero up to but below "
            "one" % (margin,)
        )
    _require_positive(
        "max_junction_excursion_k", policy.get("max_junction_excursion_k")
    )
    _require_number(
        "max_peak_junction_temperature_c",
        policy.get("max_peak_junction_temperature_c"),
    )
    _require_count(
        "min_ground_handling_pulses", policy.get("min_ground_handling_pulses")
    )
    _require_count(
        "min_in_orbit_switching_pulses", policy.get("min_in_orbit_switching_pulses")
    )
    _require_positive("min_recovery_interval_s", policy.get("min_recovery_interval_s"))
    return policy


def inductive_overshoot_v(stray_inductance_h, current_slew_a_per_s):
    """Voltage the stray inductance throws up as the current is broken."""
    inductance = _require_positive("stray_inductance_h", stray_inductance_h)
    slew = _require_positive("current_slew_a_per_s", current_slew_a_per_s)
    return inductance * slew


def transient_peak_voltage_v(
    standing_voltage_v, stray_inductance_h, current_slew_a_per_s
):
    """Peak the diode actually sees: the rail plus the overshoot on top."""
    standing = _require_positive("standing_voltage_v", standing_voltage_v)
    return standing + inductive_overshoot_v(stray_inductance_h, current_slew_a_per_s)


def absorbed_pulse_energy_j(stray_inductance_h, switched_current_a):
    """Field energy the switched string dumps into the junction."""
    inductance = _require_positive("stray_inductance_h", stray_inductance_h)
    current = _require_positive("switched_current_a", switched_current_a)
    return 0.5 * inductance * current * current


def peak_clamp_power_w(peak_voltage_v, switched_current_a):
    """Power the junction carries at the instant the clamp takes over."""
    peak = _require_positive("peak_voltage_v", peak_voltage_v)
    current = _require_positive("switched_current_a", switched_current_a)
    return peak * current


def clamp_duration_s(absorbed_energy_j, peak_power_w):
    """How long the clamp lasts: the energy emptied at that peak power."""
    energy = _require_positive("absorbed_energy_j", absorbed_energy_j)
    power = _require_positive("peak_power_w", peak_power_w)
    return 2.0 * energy / power


def junction_excursion_k(peak_power_w, transient_thermal_impedance_k_per_w):
    """Temperature step that pulse produces through the package."""
    power = _require_positive("peak_power_w", peak_power_w)
    impedance = _require_positive(
        "transient_thermal_impedance_k_per_w", transient_thermal_impedance_k_per_w
    )
    return power * impedance


def derated_standoff_v(reverse_standoff_v, derating_factor):
    """Reverse rating the design is allowed to use, not the face value."""
    standoff = _require_positive("reverse_standoff_v", reverse_standoff_v)
    factor = _require_derating_factor("derating_factor", derating_factor)
    return standoff * factor


def standoff_margin_fraction(peak_voltage_v, derated_standoff_voltage_v):
    """Share of the derated standoff still unused at the transient peak."""
    peak = _require_positive("peak_voltage_v", peak_voltage_v)
    derated = _require_positive(
        "derated_standoff_voltage_v", derated_standoff_voltage_v
    )
    return (derated - peak) / derated


def event_pulse_counts(event_plan):
    """Pulses the plan places in each recognised switching category."""
    if not isinstance(event_plan, (list, tuple)):
        raise ValueError("event_plan must be a list or tuple, got %r" % (event_plan,))
    if not event_plan:
        raise ValueError("event_plan must hold at least one switching event")
    counts = dict((name, 0) for name in SWITCHING_EVENT_CATEGORIES)
    for entry in event_plan:
        if not isinstance(entry, dict):
            raise ValueError("event_plan holds a non-mapping entry: %r" % (entry,))
        category = entry.get("category")
        if not isinstance(category, str) or not category.strip():
            raise ValueError("event_plan entry is missing a category: %r" % (entry,))
        label = category.strip().lower()
        if label not in counts:
            raise ValueError(
                "event_plan names an unrecognised switching category %r" % (category,)
            )
        counts[label] += _require_count("event_plan pulse_count", entry.get("pulse_count"))
    return counts


def assess_switching_survival(case, policy=DEFAULT_SWITCHING_POLICY):
    """Full clause 9.6.17 judgement for one switching transient campaign."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_switching_policy(policy)
    circuit = case.get("circuit")
    if not isinstance(circuit, dict):
        raise ValueError("case is missing a circuit block")
    device = case.get("device")
    if not isinstance(device, dict):
        raise ValueError("case is missing a device block")
    plan = case.get("event_plan")
    if plan is None:
        raise ValueError("case is missing an event_plan block")

    standing = _require_positive(
        "circuit standing_voltage_v", circuit.get("standing_voltage_v")
    )
    inductance = _require_positive(
        "circuit stray_inductance_h", circuit.get("stray_inductance_h")
    )
    slew = _require_positive(
        "circuit current_slew_a_per_s", circuit.get("current_slew_a_per_s")
    )
    current = _require_positive(
        "circuit switched_current_a", circuit.get("switched_current_a")
    )
    interval = _require_positive(
        "circuit recovery_interval_s", circuit.get("recovery_interval_s")
    )

    standoff = _require_positive(
        "device reverse_standoff_v", device.get("reverse_standoff_v")
    )
    factor = _require_derating_factor(
        "device derating_factor", device.get("derating_factor")
    )
    impedance = _require_positive(
        "device transient_thermal_impedance_k_per_w",
        device.get("transient_thermal_impedance_k_per_w"),
    )
    case_temperature = _require_number(
        "device case_temperature_c", device.get("case_temperature_c")
    )

    overshoot = inductive_overshoot_v(inductance, slew)
    peak = transient_peak_voltage_v(standing, inductance, slew)
    derated = derated_standoff_v(standoff, factor)
    margin = standoff_margin_fraction(peak, derated)
    energy = absorbed_pulse_energy_j(inductance, current)
    power = peak_clamp_power_w(peak, current)
    duration = clamp_duration_s(energy, power)
    excursion = junction_excursion_k(power, impedance)
    peak_junction = case_temperature + excursion
    counts = event_pulse_counts(plan)

    findings = []
    result = {
        "overshoot_v": overshoot,
        "transient_peak_v": peak,
        "derated_standoff_v": derated,
        "standoff_margin_fraction": margin,
        "absorbed_energy_j": energy,
        "peak_clamp_power_w": power,
        "clamp_duration_s": duration,
        "junction_excursion_k": excursion,
        "peak_junction_temperature_c": peak_junction,
        "pulse_counts": counts,
        "findings": findings,
    }

    breakdown = not _at_least(
        margin, float(policy["min_standoff_margin_fraction"])
    )
    if breakdown:
        findings.append(
            "the %.2f V transient leaves %.4f of the %.2f V derated standoff "
            "against the %.4f the design has to keep, so the junction is taken "
            "into breakdown by the overshoot"
            % (
                peak,
                margin,
                derated,
                float(policy["min_standoff_margin_fraction"]),
            )
        )

    thermal = False
    if not _at_most(excursion, float(policy["max_junction_excursion_k"])):
        thermal = True
        findings.append(
            "one pulse steps the junction %.3f K against the %.3f K limit"
            % (excursion, float(policy["max_junction_excursion_k"]))
        )
    if not _at_most(
        peak_junction, float(policy["max_peak_junction_temperature_c"])
    ):
        thermal = True
        findings.append(
            "the step lands the junction at %.2f C against the %.2f C ceiling"
            % (
                peak_junction,
                float(policy["max_peak_junction_temperature_c"]),
            )
        )

    plan_short = False
    if not _at_most(factor, float(policy["max_derating_factor"])):
        plan_short = True
        findings.append(
            "the design uses %.3f of the reverse rating against the %.3f the "
            "derating policy allows"
            % (factor, float(policy["max_derating_factor"]))
        )
    if not _at_least(
        counts[GROUND_HANDLING], float(policy["min_ground_handling_pulses"])
    ):
        plan_short = True
        findings.append(
            "the plan fires %d %s pulses against the %d required; in-orbit pulses "
            "do not fill this count"
            % (
                counts[GROUND_HANDLING],
                GROUND_HANDLING,
                int(policy["min_ground_handling_pulses"]),
            )
        )
    if not _at_least(
        counts[IN_ORBIT_SWITCHING], float(policy["min_in_orbit_switching_pulses"])
    ):
        plan_short = True
        findings.append(
            "the plan fires %d %s pulses against the %d required; ground handling "
            "pulses do not fill this count"
            % (
                counts[IN_ORBIT_SWITCHING],
                IN_ORBIT_SWITCHING,
                int(policy["min_in_orbit_switching_pulses"]),
            )
        )
    if not _at_least(interval, float(policy["min_recovery_interval_s"])):
        plan_short = True
        findings.append(
            "pulses sit %.3f s apart against the %.3f s the junction needs to "
            "shed one step before the next"
            % (interval, float(policy["min_recovery_interval_s"]))
        )

    if breakdown:
        result["verdict"] = SWITCHING_BREAKDOWN_RISK
    elif thermal:
        result["verdict"] = SWITCHING_EXCURSION_EXCESSIVE
    elif plan_short:
        result["verdict"] = SWITCHING_EVENT_PLAN_DEFICIENT
    else:
        result["verdict"] = SWITCHING_SURVIVAL_ACCEPTED
    return result
