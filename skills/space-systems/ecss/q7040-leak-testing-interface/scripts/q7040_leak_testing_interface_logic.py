#!/usr/bin/env python3
"""Leak test of a brazed pressurised assembly.

Anchor: the inspection provisions of the ECSS brazing standard covering
leak testing of pressurised brazements. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The requirement is set by the mission, not by the instrument. A
permitted pressure drop over an enclosed volume held for a given time
is an allowable throughput:

    Q_allow [mbar l/s] = dP [mbar] * V [l] / t [s]

Through a brazing defect the flow is molecular, so a rate scales with
the inverse square root of the molar mass. Converting a rate measured
in one gas to another multiplies by sqrt(M_from / M_to); the two
directions are reciprocal because the same physical path is being
described twice.

A pressure-decay rig cannot beat the floor its own instrumentation
sets:

    Q_floor [mbar l/s] = gauge_resolution [mbar] * V [l] / t_test [s]

A method is accepted only when its floor sits a declared margin below
the tracer-equivalent allowable rate, and the least onerous adequate
method is taken.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Molar masses in g/mol.
GAS_MOLAR_MASS = {
    "helium": 4.0026,
    "hydrogen": 2.0159,
    "nitrogen": 28.0134,
    "oxygen": 31.9988,
    "argon": 39.948,
    "xenon": 131.293,
}

BUBBLE_IMMERSION = "bubble-immersion"
PRESSURE_DECAY = "pressure-decay"
TRACER_SNIFFER_PROBE = "tracer-sniffer-probe"
TRACER_VACUUM_HOOD = "tracer-vacuum-hood"

# Least onerous first; the walk stops at the first adequate method.
LEAK_TEST_METHODS = (
    BUBBLE_IMMERSION,
    PRESSURE_DECAY,
    TRACER_SNIFFER_PROBE,
    TRACER_VACUUM_HOOD,
)

# Nominal detection floor of each method in mbar l/s. Pressure decay is
# only nominal here: its real floor is computed from the rig.
METHOD_NOMINAL_FLOOR = {
    BUBBLE_IMMERSION: 1.0e-3,
    PRESSURE_DECAY: 1.0e-4,
    TRACER_SNIFFER_PROBE: 1.0e-7,
    TRACER_VACUUM_HOOD: 1.0e-9,
}

TRACER_METHODS = (TRACER_SNIFFER_PROBE, TRACER_VACUUM_HOOD)

DEFAULT_DETECTION_MARGIN = 10.0

_REL_TOL = 1e-9
_ABS_TOL = 1e-18


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


def _require_gas(name, value):
    if value not in GAS_MOLAR_MASS:
        raise ValueError(
            "%s must be one of %s, got %r"
            % (name, ", ".join(sorted(GAS_MOLAR_MASS)), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    Both sides are products and quotients of measured quantities, so a
    rate placed deliberately on the limit can read a few units in the
    last place above it. The limit is never raised; only the comparison
    tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def allowable_throughput(pressure_drop_mbar, volume_l, hold_time_s):
    """Allowable leak rate in mbar l/s from the loss the mission permits."""
    drop = _require_positive("pressure_drop_mbar", pressure_drop_mbar)
    volume = _require_positive("volume_l", volume_l)
    hold = _require_positive("hold_time_s", hold_time_s)
    return drop * volume / hold


def species_conversion_factor(from_gas, to_gas):
    """Multiplier taking a rate measured in one gas into another gas."""
    _require_gas("from_gas", from_gas)
    _require_gas("to_gas", to_gas)
    return math.sqrt(GAS_MOLAR_MASS[from_gas] / GAS_MOLAR_MASS[to_gas])


def convert_rate(rate, from_gas, to_gas):
    """Rate through the same defect expressed in a different gas."""
    value = _require_non_negative("rate", rate)
    return value * species_conversion_factor(from_gas, to_gas)


def pressure_decay_detection_floor(gauge_resolution_mbar, volume_l, test_duration_s):
    """Smallest rate a pressure-decay rig can resolve, from its own numbers."""
    resolution = _require_positive("gauge_resolution_mbar", gauge_resolution_mbar)
    volume = _require_positive("volume_l", volume_l)
    duration = _require_positive("test_duration_s", test_duration_s)
    return resolution * volume / duration


def method_floor(method, rig=None):
    """Detection floor of a method, computed for a pressure-decay rig."""
    if method not in METHOD_NOMINAL_FLOOR:
        raise ValueError(
            "method must be one of %s, got %r"
            % (", ".join(LEAK_TEST_METHODS), method)
        )
    if method == PRESSURE_DECAY and rig is not None:
        if not isinstance(rig, dict):
            raise ValueError("rig must be a mapping, got %r" % (rig,))
        return pressure_decay_detection_floor(
            rig.get("gauge_resolution_mbar"),
            rig.get("volume_l"),
            rig.get("test_duration_s"),
        )
    return METHOD_NOMINAL_FLOOR[method]


def select_leak_test_method(
    allowable_tracer_rate, detection_margin=DEFAULT_DETECTION_MARGIN, rig=None
):
    """Least onerous method whose floor clears the rate with the margin."""
    allowable = _require_positive("allowable_tracer_rate", allowable_tracer_rate)
    margin = _require_positive("detection_margin", detection_margin)
    required_floor = allowable / margin
    considered = []
    for method in LEAK_TEST_METHODS:
        floor = method_floor(method, rig)
        considered.append({"method": method, "floor": floor})
        if _at_most(floor, required_floor):
            return {
                "method": method,
                "floor": floor,
                "required_floor": required_floor,
                "considered": considered,
                "findings": [],
            }
    return {
        "method": None,
        "floor": None,
        "required_floor": required_floor,
        "considered": considered,
        "findings": [
            "no available method reaches a floor of %.3e mbar l/s; tighten the "
            "margin, lengthen the test or subdivide the assembly"
            % required_floor
        ],
    }


def evaluate_leak_test(case):
    """Full leak-test requirement, method choice and measured-rate verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    service_gas = _require_gas("service_gas", case.get("service_gas"))
    tracer_gas = _require_gas("tracer_gas", case.get("tracer_gas", "helium"))
    margin = _require_positive(
        "detection_margin", case.get("detection_margin", DEFAULT_DETECTION_MARGIN)
    )
    volume_l = _require_positive("volume_l", case.get("volume_l"))
    allowable_service = allowable_throughput(
        case.get("pressure_drop_mbar"), volume_l, case.get("hold_time_s")
    )
    allowable_tracer = convert_rate(allowable_service, service_gas, tracer_gas)

    rig = case.get("pressure_decay_rig")
    if rig is not None:
        if not isinstance(rig, dict):
            raise ValueError("pressure_decay_rig must be a mapping, got %r" % (rig,))
        rig = dict(rig)
        rig.setdefault("volume_l", volume_l)

    selection = select_leak_test_method(allowable_tracer, margin, rig)
    findings = list(selection["findings"])

    measured_tracer_rate = case.get("measured_tracer_rate")
    if measured_tracer_rate is None:
        measured_service = None
        compliant = None
        verdict = "leak-rate-not-measured"
        findings.append(
            "no measured tracer rate supplied; the requirement is fixed but "
            "the assembly is not yet proven tight"
        )
    else:
        measured_service = convert_rate(
            measured_tracer_rate, tracer_gas, service_gas
        )
        compliant = _at_most(measured_service, allowable_service)
        verdict = "leak-rate-within-allowable" if compliant else "leak-rate-exceeded"
        if not compliant:
            findings.append(
                "measured %.3e mbar l/s in %s against an allowable %.3e"
                % (measured_service, service_gas, allowable_service)
            )
        if selection["method"] in TRACER_METHODS and tracer_gas == service_gas:
            findings.append(
                "the tracer and the service gas are the same; a background "
                "reading cannot be separated from the leak"
            )

    return {
        "service_gas": service_gas,
        "tracer_gas": tracer_gas,
        "allowable_service_rate": allowable_service,
        "allowable_tracer_rate": allowable_tracer,
        "detection_margin": margin,
        "required_floor": selection["required_floor"],
        "method": selection["method"],
        "method_floor": selection["floor"],
        "measured_service_rate": measured_service,
        "compliant": compliant,
        "verdict": verdict,
        "findings": findings,
    }
