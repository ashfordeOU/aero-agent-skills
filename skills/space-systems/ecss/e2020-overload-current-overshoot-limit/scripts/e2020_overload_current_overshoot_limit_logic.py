#!/usr/bin/env python3
"""Current overshoot at the input and output ports on the arrival of an overload.

Anchor: ECSS-E-ST-20-20C clause 5.4.1.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A limiter does not reach its limitation value instantly. When an
overload arrives the branch current runs past the limit value while the
control loop is still closing, and the two ports of the interface do not
see the same excursion. At the output port the capacitance downstream of
the pass element dumps into the fault, so the peak there is set by the
fault path and not by the loop. At the input port the excursion is fed
through the input filter, which both softens it and stores the energy
that lengthens it. The clause bounds what the excursion is allowed to
reach, at both ports, and how long it is allowed to last.

Two quantities, not one
-----------------------
A peak that is high but over in a microsecond and a peak that is modest
but held for a millisecond are different failures. The first is a
di/dt problem for everything sharing the bus; the second is an energy
problem for the pass element and the upstream protection, which may
count it as a genuine overload and act on it. So each port is bounded
twice: by a peak, expressed as a factor on the limitation value, and by
the time the current is allowed to stay above that limitation value
before it settles.

The measurement implemented here
--------------------------------
1. Validate each port waveform as a time-ordered set of samples, and the
   overload onset as an instant inside the sampled span.
2. Take the peak of each port and express it as a ratio and as a
   fractional overshoot above the limitation value.
3. Integrate the time the current spends above the limitation value,
   interpolating the crossings between samples rather than counting
   whole sample intervals.
4. Take the settling time as the last crossing back below the limit,
   measured from the overload onset.
5. Compare the peak with the permitted factor and the settling time with
   the permitted window, at each port and with its own bound.
6. Report the cross-port observation an analyst reads next: an input
   peak above the output peak means the excursion is being fed from the
   input filter rather than from the downstream capacitance.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

WITHIN_BOUND = "overload-overshoot-within-bound"
BEYOND_BOUND = "overload-overshoot-beyond-bound"

PORTS = ("input", "output")

# Conservative defaults when a project does not declare its own bound.
DEFAULT_OVERSHOOT_FACTOR = 1.20

# Peaks, ratios and interpolated crossing instants are all products of
# floats; a value placed exactly on a bound must decide the same way on
# every platform.
_REL_TOL = 1e-9
_ABS_TOL = 1e-15

__all__ = [
    "WITHIN_BOUND",
    "BEYOND_BOUND",
    "PORTS",
    "DEFAULT_OVERSHOOT_FACTOR",
    "validate_waveform",
    "validate_factor",
    "overshoot_bound_a",
    "peak_sample",
    "overshoot_ratio",
    "overshoot_fraction",
    "time_above_threshold_s",
    "last_crossing_below_s",
    "settling_time_s",
    "assess_port",
    "assess_overload_overshoot",
]


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _at_or_below(value, bound):
    """True when value is at or below bound, absorbing representation error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def validate_waveform(samples, label="waveform"):
    """Return a validated list of (time_s, current_a) samples for one port."""
    if not isinstance(samples, (list, tuple)) or len(samples) < 2:
        raise ValueError("%s needs at least two (time_s, current_a) samples" % label)
    points = []
    for index, item in enumerate(samples):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError(
                "%s[%d] must be a (time_s, current_a) pair" % (label, index)
            )
        time_s, current_a = item
        if not _is_finite_number(time_s) or not _is_finite_number(current_a):
            raise ValueError("%s[%d] must hold finite real numbers" % (label, index))
        time_s = float(time_s)
        current_a = float(current_a)
        if current_a < 0.0:
            raise ValueError(
                "%s[%d] current must not be negative, got %g" % (label, index, current_a)
            )
        points.append((time_s, current_a))
    for index in range(1, len(points)):
        if points[index][0] <= points[index - 1][0]:
            raise ValueError(
                "%s sample times must strictly increase (index %d)" % (label, index)
            )
    return points


def validate_factor(factor, label="allowed_factor"):
    """Return a validated overshoot factor, which can never be below unity."""
    if not _is_finite_number(factor):
        raise ValueError("%s must be a finite real number" % label)
    factor = float(factor)
    if factor < 1.0:
        raise ValueError(
            "%s must be at least one; a bound below the limitation value is not an "
            "overshoot bound, got %g" % (label, factor)
        )
    return factor


def overshoot_bound_a(limitation_value_a, allowed_factor):
    """Return the highest current the port is allowed to reach."""
    if not _is_finite_number(limitation_value_a) or float(limitation_value_a) <= 0.0:
        raise ValueError("limitation_value_a must be a positive finite number")
    return float(limitation_value_a) * validate_factor(allowed_factor)


def peak_sample(samples, label="waveform"):
    """Return the (time_s, current_a) of the highest sample; earliest wins ties."""
    points = validate_waveform(samples, label)
    best = points[0]
    for point in points[1:]:
        if point[1] > best[1]:
            best = point
    return best


def overshoot_ratio(peak_current_a, limitation_value_a):
    """Return the peak expressed as a multiple of the limitation value."""
    if not _is_finite_number(peak_current_a) or float(peak_current_a) < 0.0:
        raise ValueError("peak_current_a must be a non-negative finite number")
    if not _is_finite_number(limitation_value_a) or float(limitation_value_a) <= 0.0:
        raise ValueError("limitation_value_a must be a positive finite number")
    return float(peak_current_a) / float(limitation_value_a)


def overshoot_fraction(peak_current_a, limitation_value_a):
    """Return the fractional excess of the peak above the limitation value."""
    ratio = overshoot_ratio(peak_current_a, limitation_value_a)
    return max(0.0, ratio - 1.0)


def _crossing_time(t0, i0, t1, i1, threshold):
    """Return the interpolated instant the segment crosses the threshold."""
    if i1 == i0:
        return t0
    return t0 + (threshold - i0) * (t1 - t0) / (i1 - i0)


def time_above_threshold_s(samples, threshold_a, label="waveform"):
    """Return the total time the port current spends above the threshold."""
    points = validate_waveform(samples, label)
    if not _is_finite_number(threshold_a) or float(threshold_a) < 0.0:
        raise ValueError("threshold_a must be a non-negative finite number")
    threshold = float(threshold_a)
    total = 0.0
    for index in range(1, len(points)):
        t0, i0 = points[index - 1]
        t1, i1 = points[index]
        above0 = i0 > threshold
        above1 = i1 > threshold
        if above0 and above1:
            total += t1 - t0
        elif above0 and not above1:
            total += _crossing_time(t0, i0, t1, i1, threshold) - t0
        elif above1 and not above0:
            total += t1 - _crossing_time(t0, i0, t1, i1, threshold)
    return total


def last_crossing_below_s(samples, threshold_a, label="waveform"):
    """Return the last instant the current falls back to the threshold, or None."""
    points = validate_waveform(samples, label)
    if not _is_finite_number(threshold_a) or float(threshold_a) < 0.0:
        raise ValueError("threshold_a must be a non-negative finite number")
    threshold = float(threshold_a)
    last = None
    for index in range(1, len(points)):
        t0, i0 = points[index - 1]
        t1, i1 = points[index]
        if i0 > threshold and i1 <= threshold:
            last = _crossing_time(t0, i0, t1, i1, threshold)
    if last is None and points[-1][1] > threshold:
        return None
    if last is None:
        return points[0][0]
    return last


def settling_time_s(samples, threshold_a, onset_time_s, label="waveform"):
    """Return the time from overload onset to the last fall back below the limit."""
    points = validate_waveform(samples, label)
    if not _is_finite_number(onset_time_s):
        raise ValueError("onset_time_s must be a finite real number")
    onset = float(onset_time_s)
    if onset < points[0][0] or onset > points[-1][0]:
        raise ValueError(
            "onset_time_s %g s lies outside the sampled span [%g, %g]"
            % (onset, points[0][0], points[-1][0])
        )
    last = last_crossing_below_s(points, threshold_a, label)
    if last is None:
        return None
    return max(0.0, last - onset)


def assess_port(port, samples, limitation_value_a, allowed_factor,
                settling_window_s, onset_time_s):
    """Assess one port against its peak bound and its settling window."""
    if port not in PORTS:
        raise ValueError("port must be one of %s, got %r" % (", ".join(PORTS), port))
    label = "%s_samples" % port
    points = validate_waveform(samples, label)
    if not _is_finite_number(settling_window_s) or float(settling_window_s) <= 0.0:
        raise ValueError("settling_window_s must be a positive finite number")
    limitation = float(limitation_value_a)
    bound = overshoot_bound_a(limitation, allowed_factor)
    peak_time, peak_current = peak_sample(points, label)
    above = time_above_threshold_s(points, limitation, label)
    settling = settling_time_s(points, limitation, onset_time_s, label)
    peak_within = _at_or_below(peak_current, bound)
    if settling is None:
        settles = False
    else:
        settles = _at_or_below(settling, float(settling_window_s))
    findings = []
    if not peak_within:
        findings.append(
            "%s port peaks at %.4f A against a bound of %.4f A"
            % (port, peak_current, bound)
        )
    if settling is None:
        findings.append(
            "%s port current never returns to the limitation value inside the record"
            % (port,)
        )
    elif not settles:
        findings.append(
            "%s port stays above the limitation value for %.6f s against an allowed "
            "%.6f s" % (port, settling, float(settling_window_s))
        )
    return {
        "port": port,
        "limitation_value_a": limitation,
        "allowed_factor": validate_factor(allowed_factor),
        "overshoot_bound_a": bound,
        "peak_current_a": peak_current,
        "peak_time_s": peak_time,
        "overshoot_ratio": overshoot_ratio(peak_current, limitation),
        "overshoot_fraction": overshoot_fraction(peak_current, limitation),
        "time_above_limit_s": above,
        "settling_time_s": settling,
        "settling_window_s": float(settling_window_s),
        "peak_within_bound": peak_within,
        "settles_within_window": settles,
        "compliant": peak_within and settles,
        "findings": findings,
    }


def assess_overload_overshoot(spec):
    """Run the full clause 5.4.1.1.1 overload overshoot assessment.

    spec keys: limitation_value_a, onset_time_s, settling_window_s,
    input_samples, output_samples, optional allowed_factor and the
    per-port overrides input_allowed_factor and output_allowed_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "limitation_value_a",
        "onset_time_s",
        "settling_window_s",
        "input_samples",
        "output_samples",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % (key,))
    if not _is_finite_number(spec["limitation_value_a"]) or float(
        spec["limitation_value_a"]
    ) <= 0.0:
        raise ValueError("limitation_value_a must be a positive finite number")
    limitation = float(spec["limitation_value_a"])
    shared_factor = spec.get("allowed_factor", DEFAULT_OVERSHOOT_FACTOR)
    ports = {}
    for port in PORTS:
        factor = spec.get("%s_allowed_factor" % port, shared_factor)
        ports[port] = assess_port(
            port,
            spec["%s_samples" % port],
            limitation,
            factor,
            spec["settling_window_s"],
            spec["onset_time_s"],
        )
    findings = []
    for port in PORTS:
        findings.extend(ports[port]["findings"])
    observations = []
    if ports["input"]["peak_current_a"] > ports["output"]["peak_current_a"]:
        observations.append(
            "input peak %.4f A exceeds the output peak %.4f A; the excursion is being "
            "fed from the input filter rather than from the downstream capacitance"
            % (ports["input"]["peak_current_a"], ports["output"]["peak_current_a"])
        )
    compliant = not findings
    return {
        "ports": ports,
        "limitation_value_a": limitation,
        "findings": findings,
        "observations": observations,
        "compliant": compliant,
        "verdict": WITHIN_BOUND if compliant else BEYOND_BOUND,
    }
