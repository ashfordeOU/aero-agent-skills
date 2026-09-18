#!/usr/bin/env python3
"""Representativeness of the source interface used to test a load on its own.

Anchor: ECSS-E-ST-20-20C clause 5.3.4.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A user equipment is nearly always tested before it ever meets the power
subsystem it will fly with. On the bench it is fed from whatever supply
the test rack happens to carry, and that supply is usually a far harder
source than the protected branch the unit will actually sit behind. The
clause recommends that a load tested on its own be fed through an
interface that represents the limiter it will face: same limit value,
same trip-off delay, comparable series impedance and inductance, the
same undervoltage behaviour, and the same latching character.

What the representativeness actually buys
-----------------------------------------
Behind a real latching current limiter an inrush above the limit does
not draw its natural peak. The branch is held at the limit value, the
output collapses towards whatever the load is pulling, and the whole
event has a deadline: the trip-off delay. A load that charges its input
capacitance happily from a stiff bench supply can fail to finish that
same charge inside the delay once a limiter is in the path, and the
bench test says nothing about it.

The comparison implemented here
-------------------------------
1. Validate the flight-side interface and the bench-side interface as
   complete, self-consistent source descriptions.
2. For every numeric parameter, form the deviation of the bench value
   from the flight value relative to the flight value, and compare it
   with the tolerance the project allows for that parameter.
3. Compare the discrete character flags -- whether the source latches
   off and whether it inhibits retrigger -- which either match or do
   not; there is no tolerance on them.
4. Recognise the hard laboratory supply as its own finding: a bench
   limit far above the flight limit, or a source that never trips,
   cannot reproduce a limitation event at any tolerance.
5. Fold in the load itself. A load whose inrush stays under the flight
   limit never provokes limitation, so the interface matters less; a
   load whose inrush exceeds it is exactly the case the bench has to
   reproduce.
6. Decide whether the standalone test evidence transfers to the
   integrated system, and name every reason it does not.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

VERDICT_REPRESENTATIVE = "representative-limiter-interface"
VERDICT_NOT_REPRESENTATIVE = "non-representative-test-source"

# Relative tolerances a project is assumed to allow on each parameter of
# the bench interface unless it declares its own. The limit value and the
# undervoltage threshold are held tightest because the load behaviour
# hinges directly on them; the parasitic series terms are allowed to be
# looser because a bench harness is never the flight harness.
DEFAULT_TOLERANCES = {
    "current_limit_a": 0.10,
    "trip_off_delay_s": 0.20,
    "source_impedance_ohm": 0.50,
    "source_inductance_h": 0.50,
    "undervoltage_trip_v": 0.05,
}

NUMERIC_PARAMETERS = (
    "current_limit_a",
    "trip_off_delay_s",
    "source_impedance_ohm",
    "source_inductance_h",
    "undervoltage_trip_v",
)

FLAG_PARAMETERS = ("latching", "retrigger_inhibited")

# Parameters that must be strictly positive; the two parasitic series
# terms are allowed to be declared as zero for an ideal source.
STRICTLY_POSITIVE = (
    "nominal_voltage_v",
    "current_limit_a",
    "trip_off_delay_s",
    "undervoltage_trip_v",
)
NON_NEGATIVE = ("source_impedance_ohm", "source_inductance_h")

# A bench limit this many times the flight limit can no longer reproduce
# the limitation event whatever the stated tolerance says.
HARD_SOURCE_FACTOR = 3.0

# Deviations and tolerances are both ratios of floats; a bench value sitting
# exactly on its tolerance must read as inside it on every platform.
_REL_TOL = 1e-9
_ABS_TOL = 1e-12

__all__ = [
    "VERDICT_REPRESENTATIVE",
    "VERDICT_NOT_REPRESENTATIVE",
    "DEFAULT_TOLERANCES",
    "NUMERIC_PARAMETERS",
    "FLAG_PARAMETERS",
    "HARD_SOURCE_FACTOR",
    "validate_interface",
    "validate_tolerances",
    "relative_deviation",
    "compare_parameter",
    "compare_flag",
    "is_hard_source",
    "required_envelope",
    "limitation_expected",
    "assess_representativeness",
    "assess_standalone_load_test",
]


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _within(value, bound):
    """True when value is at or below bound, absorbing representation error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def validate_interface(spec, label="interface"):
    """Return a validated copy of a source-interface description."""
    if not isinstance(spec, dict):
        raise ValueError("%s must be a mapping" % label)
    out = {}
    for key in STRICTLY_POSITIVE + NON_NEGATIVE:
        if key not in spec:
            raise ValueError("%s is missing '%s'" % (label, key))
        value = spec[key]
        if not _is_finite_number(value):
            raise ValueError("%s['%s'] must be a finite real number" % (label, key))
        value = float(value)
        if key in STRICTLY_POSITIVE and value <= 0.0:
            raise ValueError(
                "%s['%s'] must be positive, got %g" % (label, key, value)
            )
        if key in NON_NEGATIVE and value < 0.0:
            raise ValueError(
                "%s['%s'] must not be negative, got %g" % (label, key, value)
            )
        out[key] = value
    for key in FLAG_PARAMETERS:
        if key not in spec:
            raise ValueError("%s is missing '%s'" % (label, key))
        value = spec[key]
        if not isinstance(value, bool):
            raise ValueError("%s['%s'] must be a boolean" % (label, key))
        out[key] = value
    if out["undervoltage_trip_v"] >= out["nominal_voltage_v"]:
        raise ValueError(
            "%s undervoltage threshold %g V is not below the nominal %g V"
            % (label, out["undervoltage_trip_v"], out["nominal_voltage_v"])
        )
    return out


def validate_tolerances(tolerances=None):
    """Return the tolerance set to apply, defaults filled in."""
    out = dict(DEFAULT_TOLERANCES)
    if tolerances is None:
        return out
    if not isinstance(tolerances, dict):
        raise ValueError("tolerances must be a mapping")
    for key, value in tolerances.items():
        if key not in DEFAULT_TOLERANCES:
            raise ValueError("unknown tolerance parameter '%s'" % (key,))
        if not _is_finite_number(value):
            raise ValueError("tolerance '%s' must be a finite real number" % (key,))
        value = float(value)
        if value < 0.0:
            raise ValueError("tolerance '%s' must not be negative" % (key,))
        out[key] = value
    return out


def relative_deviation(reference, candidate):
    """Return the magnitude of the bench deviation relative to the flight value."""
    if not _is_finite_number(reference) or not _is_finite_number(candidate):
        raise ValueError("reference and candidate must be finite real numbers")
    reference = float(reference)
    candidate = float(candidate)
    if reference < 0.0 or candidate < 0.0:
        raise ValueError("interface parameters must not be negative")
    if reference == 0.0:
        return 0.0 if candidate == 0.0 else float("inf")
    return abs(candidate - reference) / reference


def compare_parameter(name, reference, candidate, tolerance):
    """Compare one numeric parameter of the bench interface against flight."""
    if name not in DEFAULT_TOLERANCES:
        raise ValueError("unknown interface parameter '%s'" % (name,))
    if not _is_finite_number(tolerance) or float(tolerance) < 0.0:
        raise ValueError("tolerance must be a finite non-negative number")
    deviation = relative_deviation(reference, candidate)
    tolerance = float(tolerance)
    return {
        "parameter": name,
        "flight_value": float(reference),
        "bench_value": float(candidate),
        "deviation": deviation,
        "tolerance": tolerance,
        "within_tolerance": _within(deviation, tolerance),
    }


def compare_flag(name, reference, candidate):
    """Compare one discrete character flag; a flag matches or it does not."""
    if name not in FLAG_PARAMETERS:
        raise ValueError("unknown interface flag '%s'" % (name,))
    if not isinstance(reference, bool) or not isinstance(candidate, bool):
        raise ValueError("interface flags must be booleans")
    return {
        "parameter": name,
        "flight_value": reference,
        "bench_value": candidate,
        "matches": reference == candidate,
    }


def is_hard_source(flight, bench, hard_factor=HARD_SOURCE_FACTOR):
    """True when the bench supply cannot reproduce a limitation event at all."""
    flight = validate_interface(flight, "flight_interface")
    bench = validate_interface(bench, "bench_interface")
    if not _is_finite_number(hard_factor) or float(hard_factor) <= 1.0:
        raise ValueError("hard_factor must be a finite number above one")
    hard_factor = float(hard_factor)
    if not bench["latching"]:
        return True
    ceiling = flight["current_limit_a"] * hard_factor
    return bench["current_limit_a"] > ceiling and not math.isclose(
        bench["current_limit_a"], ceiling, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def required_envelope(flight, tolerances=None):
    """Return the acceptable band for every numeric parameter of the bench source."""
    flight = validate_interface(flight, "flight_interface")
    tolerances = validate_tolerances(tolerances)
    envelope = {}
    for name in NUMERIC_PARAMETERS:
        reference = flight[name]
        span = reference * tolerances[name]
        envelope[name] = (reference - span, reference + span)
    return envelope


def limitation_expected(flight, load_inrush_current_a):
    """True when the load inrush reaches the flight limit and provokes limitation."""
    flight = validate_interface(flight, "flight_interface")
    if not _is_finite_number(load_inrush_current_a):
        raise ValueError("load_inrush_current_a must be a finite real number")
    inrush = float(load_inrush_current_a)
    if inrush < 0.0:
        raise ValueError("load_inrush_current_a must not be negative")
    limit = flight["current_limit_a"]
    if math.isclose(inrush, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return True
    return inrush > limit


def assess_representativeness(flight, bench, tolerances=None,
                              hard_factor=HARD_SOURCE_FACTOR):
    """Compare a bench source interface with the flight limiter interface."""
    flight = validate_interface(flight, "flight_interface")
    bench = validate_interface(bench, "bench_interface")
    tolerances = validate_tolerances(tolerances)
    comparisons = [
        compare_parameter(name, flight[name], bench[name], tolerances[name])
        for name in NUMERIC_PARAMETERS
    ]
    flags = [compare_flag(name, flight[name], bench[name]) for name in FLAG_PARAMETERS]
    hard = is_hard_source(flight, bench, hard_factor)
    findings = []
    for record in comparisons:
        if not record["within_tolerance"]:
            findings.append(
                "%s deviates by %.1f%% against an allowed %.1f%%"
                % (
                    record["parameter"].replace("_", "-"),
                    100.0 * record["deviation"],
                    100.0 * record["tolerance"],
                )
            )
    for record in flags:
        if not record["matches"]:
            findings.append(
                "%s differs: flight %s, bench %s"
                % (
                    record["parameter"].replace("_", "-"),
                    record["flight_value"],
                    record["bench_value"],
                )
            )
    if hard:
        findings.append(
            "bench supply is a hard source and cannot reproduce a limitation event"
        )
    representative = not findings
    return {
        "comparisons": comparisons,
        "flags": flags,
        "hard_source": hard,
        "findings": findings,
        "representative": representative,
        "verdict": VERDICT_REPRESENTATIVE if representative else VERDICT_NOT_REPRESENTATIVE,
        "envelope": required_envelope(flight, tolerances),
    }


def assess_standalone_load_test(spec):
    """Run the full clause 5.3.4.1.1 standalone-load-test assessment.

    spec keys: flight_interface, bench_interface, load_inrush_current_a,
    load_steady_current_a, optional tolerances and hard_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "flight_interface",
        "bench_interface",
        "load_inrush_current_a",
        "load_steady_current_a",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % (key,))
    flight = validate_interface(spec["flight_interface"], "flight_interface")
    bench = validate_interface(spec["bench_interface"], "bench_interface")
    for key in ("load_inrush_current_a", "load_steady_current_a"):
        if not _is_finite_number(spec[key]):
            raise ValueError("%s must be a finite real number" % (key,))
        if float(spec[key]) < 0.0:
            raise ValueError("%s must not be negative" % (key,))
    inrush = float(spec["load_inrush_current_a"])
    steady = float(spec["load_steady_current_a"])
    if steady > inrush and not math.isclose(
        steady, inrush, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "load_steady_current_a %g A exceeds the declared inrush %g A"
            % (steady, inrush)
        )
    report = assess_representativeness(
        flight, bench, spec.get("tolerances"), spec.get("hard_factor", HARD_SOURCE_FACTOR)
    )
    findings = list(report["findings"])
    limit = flight["current_limit_a"]
    if steady > limit and not math.isclose(
        steady, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        findings.append(
            "steady demand %g A sits above the flight limit %g A; the branch never "
            "reaches a stable state" % (steady, limit)
        )
    provokes = limitation_expected(flight, inrush)
    if provokes and not report["representative"]:
        findings.append(
            "load inrush reaches the flight limit, so the limitation event is the "
            "case the bench has to reproduce and does not"
        )
    evidence_transfers = not findings
    return {
        "representativeness": report,
        "limitation_expected": provokes,
        "load_inrush_current_a": inrush,
        "load_steady_current_a": steady,
        "findings": findings,
        "evidence_transfers": evidence_transfers,
        "verdict": VERDICT_REPRESENTATIVE if evidence_transfers else VERDICT_NOT_REPRESENTATIVE,
    }
