#!/usr/bin/env python3
"""Freewheeling provision for the current a limiter interrupts.

Anchor: ECSS-E-ST-20-20C clause 5.2.7.7.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A current limiter that opens does not stop the current in the load and
the harness -- inductance keeps it flowing, and the energy already
stored in that inductance has to circulate somewhere. If the design
offers no return path, the only path left is the switching element
itself, which then takes the whole inductive kick across its terminals.
The clause asks for a deliberate path, so the work is to size the
energy, categorize the path that was declared, and show the switch
survives what remains.

Return-path provisions, best to weakest
    active-clamp           a driven clamp that holds a chosen voltage
    switch-clamp           a passive avalanche or transient clamp
    load-freewheel-diode   a diode across the inductive load
    no-path                nothing declared; the switch takes the energy

Two numbers decide the case. The peak voltage the switching element
sees is the bus plus whatever the path holds across the inductance
while the current decays. The decay time is how long the current takes
to reach the residual level, and it has to finish before the limiter is
allowed to reclose, or the next attempt starts on a pre-loaded
inductance.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PROVISIONS = (
    "active-clamp",
    "switch-clamp",
    "load-freewheel-diode",
    "no-path",
)

# Provisions that actually circulate the current somewhere other than
# through the switching element.
CIRCULATING_PROVISIONS = ("active-clamp", "switch-clamp", "load-freewheel-diode")

VERDICT_COMPLIANT = "freewheeling-provision-adequate"
VERDICT_MARGINAL = "freewheeling-provision-marginal"
VERDICT_NON_COMPLIANT = "freewheeling-provision-inadequate"

# Fraction of the initial current the decay must fall below before the
# transient counts as finished. An exponential decay never reaches zero,
# so the criterion is a residual level, not an instant.
DEFAULT_RESIDUAL_FRACTION = 0.02

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


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


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A peak voltage is built from a chain of multiplications and a
    logarithm, so a case meant to sit exactly on its standoff rating can
    land a few units in the last place above it. The rating is never
    raised; only the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def circuit_inductance_h(
    load_inductance_h, harness_length_m, harness_inductance_h_per_m
):
    """Inductance the interrupted current actually flows through.

    The load and the harness are in series on the interrupted branch, and
    the harness figure is a go-and-return loop value per metre of run.
    """
    load = _require_non_negative("load_inductance_h", load_inductance_h)
    length = _require_non_negative("harness_length_m", harness_length_m)
    per_m = _require_non_negative(
        "harness_inductance_h_per_m", harness_inductance_h_per_m
    )
    total = load + length * per_m
    if total <= 0.0:
        raise ValueError(
            "total circuit inductance is zero; an interruption case needs "
            "some inductance on the branch"
        )
    return total


def stored_energy_j(inductance_h, current_a):
    """Energy trapped in the inductance at the instant the limiter opens."""
    inductance = _require_positive("inductance_h", inductance_h)
    current = _require_non_negative("current_a", current_a)
    return 0.5 * inductance * current * current


def clamp_decay_time_s(inductance_h, current_a, clamp_voltage_v):
    """Time for a constant-voltage clamp to bring the current to zero.

    A clamp that holds a fixed voltage across the inductance forces a
    constant di/dt, so the current ramps down linearly and reaches zero
    in L*I/V.
    """
    inductance = _require_positive("inductance_h", inductance_h)
    current = _require_non_negative("current_a", current_a)
    clamp = _require_positive("clamp_voltage_v", clamp_voltage_v)
    return inductance * current / clamp


def diode_decay_time_s(
    inductance_h,
    load_resistance_ohm,
    residual_fraction=DEFAULT_RESIDUAL_FRACTION,
):
    """Time for a load freewheel loop to fall to the residual fraction.

    The diode returns the current into the load resistance, so the decay
    is exponential with a time constant L/R and never reaches zero. The
    transient counts as finished at the declared residual level.
    """
    inductance = _require_positive("inductance_h", inductance_h)
    resistance = _require_positive("load_resistance_ohm", load_resistance_ohm)
    fraction = _require_positive("residual_fraction", residual_fraction)
    if fraction >= 1.0:
        raise ValueError(
            "residual_fraction must be below one, got %r" % (residual_fraction,)
        )
    tau = inductance / resistance
    return tau * math.log(1.0 / fraction)


def peak_switch_voltage_v(
    provision, bus_voltage_v, clamp_voltage_v=None, diode_drop_v=None
):
    """Voltage the switching element stands off while the current decays.

    With a circulating path the switch sees the bus plus whatever the
    path holds. With no path at all the inductance drives the switch into
    its own avalanche, so the peak is the avalanche level and the energy
    goes into the die.
    """
    _require_choice("provision", provision, PROVISIONS)
    bus = _require_positive("bus_voltage_v", bus_voltage_v)
    if provision == "no-path":
        return None
    if provision == "load-freewheel-diode":
        if diode_drop_v is None:
            raise ValueError("load-freewheel-diode provision needs diode_drop_v")
        return bus + _require_non_negative("diode_drop_v", diode_drop_v)
    if clamp_voltage_v is None:
        raise ValueError("%s provision needs clamp_voltage_v" % provision)
    return bus + _require_positive("clamp_voltage_v", clamp_voltage_v)


def path_decay(case):
    """Decay time and energy destination for the declared return path."""
    provision = _require_choice("provision", case.get("provision"), PROVISIONS)
    inductance = circuit_inductance_h(
        case.get("load_inductance_h", 0.0),
        case.get("harness_length_m", 0.0),
        case.get("harness_inductance_h_per_m", 0.0),
    )
    current = _require_positive("limitation_current_a", case.get("limitation_current_a"))
    energy = stored_energy_j(inductance, current)
    residual = case.get("residual_fraction", DEFAULT_RESIDUAL_FRACTION)
    if provision == "no-path":
        return {
            "provision": provision,
            "inductance_h": inductance,
            "stored_energy_j": energy,
            "decay_time_s": None,
            "energy_destination": "switching-element-avalanche",
        }
    if provision == "load-freewheel-diode":
        decay = diode_decay_time_s(
            inductance, case.get("load_resistance_ohm"), residual
        )
        destination = "load-resistance"
    else:
        decay = clamp_decay_time_s(inductance, current, case.get("clamp_voltage_v"))
        destination = "clamp-element"
    return {
        "provision": provision,
        "inductance_h": inductance,
        "stored_energy_j": energy,
        "decay_time_s": decay,
        "energy_destination": destination,
    }


def standoff_margin(peak_voltage_v, standoff_rating_v):
    """Ratio of the switch standoff rating to the peak it has to hold."""
    peak = _require_positive("peak_voltage_v", peak_voltage_v)
    rating = _require_positive("standoff_rating_v", standoff_rating_v)
    return rating / peak


def assess_freewheeling_provision(case):
    """Full clause 5.2.7.7.1 assessment with a verdict and findings.

    The verdict is the worst of three checks: a path exists, the switch
    stands off the peak with the required margin, and the decay finishes
    before the limiter is allowed to reclose.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    decay = path_decay(case)
    provision = decay["provision"]
    bus = _require_positive("bus_voltage_v", case.get("bus_voltage_v"))
    rating = _require_positive(
        "standoff_rating_v", case.get("switch_standoff_rating_v")
    )
    required_margin = _require_positive(
        "required_standoff_margin", case.get("required_standoff_margin", 1.5)
    )
    findings = []
    result = dict(decay)
    result["bus_voltage_v"] = bus

    if provision == "no-path":
        result.update(
            {
                "peak_switch_voltage_v": None,
                "standoff_margin": None,
                "decay_fits_dead_time": None,
                "verdict": VERDICT_NON_COMPLIANT,
                "compliant": False,
            }
        )
        findings.append(
            "no circulating path is declared; the %.4g J trapped in %.4g H "
            "is dumped into the switching element"
            % (decay["stored_energy_j"], decay["inductance_h"])
        )
        result["findings"] = findings
        return result

    peak = peak_switch_voltage_v(
        provision,
        bus,
        clamp_voltage_v=case.get("clamp_voltage_v"),
        diode_drop_v=case.get("diode_drop_v"),
    )
    margin = standoff_margin(peak, rating)
    standoff_ok = _at_least(margin, required_margin)
    if not standoff_ok:
        findings.append(
            "standoff margin %.3f is below the required %.3f: the switch "
            "holds %.1f V of a %.1f V rating"
            % (margin, required_margin, peak, rating)
        )

    dead_time = case.get("reclosure_dead_time_s")
    if dead_time is None:
        decay_ok = None
        findings.append(
            "no reclosure dead time supplied; the decay of %.4g s is not "
            "shown to finish before the limiter retries" % decay["decay_time_s"]
        )
    else:
        dead_time = _require_positive("reclosure_dead_time_s", dead_time)
        decay_ok = _at_most(decay["decay_time_s"], dead_time)
        if not decay_ok:
            findings.append(
                "decay of %.4g s outlasts the %.4g s reclosure dead time; the "
                "retry starts on a pre-loaded inductance"
                % (decay["decay_time_s"], dead_time)
            )

    if standoff_ok and decay_ok is True:
        verdict = VERDICT_COMPLIANT
        compliant = True
    elif standoff_ok and decay_ok is None:
        verdict = VERDICT_MARGINAL
        compliant = None
    else:
        verdict = VERDICT_NON_COMPLIANT
        compliant = False

    result.update(
        {
            "peak_switch_voltage_v": peak,
            "standoff_margin": margin,
            "decay_fits_dead_time": decay_ok,
            "verdict": verdict,
            "compliant": compliant,
            "findings": findings,
        }
    )
    return result
