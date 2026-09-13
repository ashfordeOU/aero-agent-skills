#!/usr/bin/env python3
"""Supply-impedance control for an electromagnetic measurement campaign.

Anchor: ECSS-E-ST-20-07C clause 5.2.4 -- stabilization networks keep the
impedance presented to the equipment-under-test bounded and repeatable for
the whole measurement campaign. The clause is paraphrased here into an
implementable procedure; no normative text is reproduced.

The module answers four questions that the clause makes checkable:

1. does every energized supply conductor (and its dedicated return) carry a
   line-impedance-stabilization-network at all;
2. what impedance magnitude does a declared network present at each swept
   measurement frequency;
3. does the measured magnitude sit inside the declared tolerance band around
   that modelled magnitude;
4. does the network stay put -- do the calibration checkpoints recorded
   through the campaign stay inside the permitted drift fraction of the
   opening baseline.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Conductor roles recognised on a conducted-measurement bench.
SUPPLY_ROLES = (
    "primary-supply",
    "redundant-supply",
    "supply-return",
    "signal-return",
    "chassis-bond",
)

# Roles that must present a stabilized impedance while energized. A signal
# return and a chassis bond are referenced conductors, not sources, so they
# are outside the clause 5.2.4 stabilization obligation.
STABILIZED_ROLES = ("primary-supply", "redundant-supply", "supply-return")

# Relative slack used only to absorb binary floating-point representation
# error on an exact-boundary comparison. It is NOT an engineering margin and
# must never be widened to make a real exceedance pass.
BOUNDARY_REL_TOL = 1e-12
BOUNDARY_ABS_TOL = 1e-15


def _not_above(value, limit):
    """Return True when value <= limit.

    A difference or ratio assembled from floats can land a few units in the
    last place above a limit it is physically equal to; that representation
    error is absorbed here, at the comparison, rather than by relaxing the
    engineering limit itself.
    """
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=BOUNDARY_REL_TOL, abs_tol=BOUNDARY_ABS_TOL)


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def stabilization_network_impedance(
    damping_resistance_ohm, series_inductance_h, frequency_hz
):
    """Impedance magnitude of a stabilization network at one frequency.

    The network is modelled as its damping resistance in series with the
    defining inductance, so the magnitude is sqrt(R^2 + (2*pi*f*L)^2): flat
    at the damping value near d.c. and rising with frequency once the
    inductive reactance dominates.
    """
    resistance = _require_number(damping_resistance_ohm, "damping_resistance_ohm")
    inductance = _require_number(series_inductance_h, "series_inductance_h")
    frequency = _require_number(frequency_hz, "frequency_hz")
    if resistance < 0.0:
        raise ValueError("damping_resistance_ohm must not be negative")
    if inductance <= 0.0:
        raise ValueError("series_inductance_h must be positive")
    if frequency < 0.0:
        raise ValueError("frequency_hz must not be negative")
    reactance = 2.0 * math.pi * frequency * inductance
    return math.sqrt(resistance * resistance + reactance * reactance)


def relative_deviation(measured_ohm, reference_ohm):
    """Fractional departure of a measured impedance from its reference."""
    measured = _require_number(measured_ohm, "measured_ohm")
    reference = _require_number(reference_ohm, "reference_ohm")
    if measured < 0.0:
        raise ValueError("measured_ohm must not be negative")
    if reference <= 0.0:
        raise ValueError("reference_ohm must be positive")
    return abs(measured - reference) / reference


def within_tolerance(measured_ohm, reference_ohm, tolerance_fraction):
    """True when the measured impedance sits inside the tolerance band."""
    tolerance = _require_number(tolerance_fraction, "tolerance_fraction")
    if tolerance < 0.0 or tolerance > 1.0:
        raise ValueError("tolerance_fraction must lie between 0 and 1")
    return _not_above(relative_deviation(measured_ohm, reference_ohm), tolerance)


def evaluate_line_coverage(lines):
    """Check that every energized source conductor carries a network.

    Each entry is a mapping with 'id', 'role' (one of SUPPLY_ROLES), an
    optional 'energized' flag (default True) and an optional
    'stabilization_network' flag (default False). Returns the stabilized
    ids, the exempt ids and one finding per uncovered conductor.
    """
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("at least one supply conductor must be declared")
    seen = set()
    stabilized = []
    exempt = []
    findings = []
    for entry in lines:
        if not isinstance(entry, dict):
            raise ValueError("each supply conductor must be a mapping")
        line_id = entry.get("id")
        if not line_id or not isinstance(line_id, str):
            raise ValueError("each supply conductor needs a non-empty string 'id'")
        if line_id in seen:
            raise ValueError("duplicate supply conductor id %r" % line_id)
        seen.add(line_id)
        role = entry.get("role")
        if role not in SUPPLY_ROLES:
            raise ValueError(
                "unrecognized conductor role %r (expected one of %s)"
                % (role, ", ".join(SUPPLY_ROLES))
            )
        energized = bool(entry.get("energized", True))
        has_network = bool(entry.get("stabilization_network", False))
        if role not in STABILIZED_ROLES:
            exempt.append({"line": line_id, "reason": "role-not-a-source"})
            continue
        if not energized:
            exempt.append({"line": line_id, "reason": "conductor-de-energized"})
            continue
        if has_network:
            stabilized.append(line_id)
        else:
            findings.append(
                {
                    "line": line_id,
                    "role": role,
                    "finding": "no-stabilization-network",
                }
            )
    return {"stabilized": stabilized, "exempt": exempt, "findings": findings}


def evaluate_frequency_sweep(network, sweep_points, tolerance_fraction):
    """Compare every swept measurement against the modelled network.

    'network' carries 'damping_resistance_ohm' and 'series_inductance_h'.
    Each sweep point carries 'frequency_hz' and 'measured_ohm'. Frequencies
    must be strictly increasing, so a duplicated or reordered sweep record
    is rejected instead of silently averaged.
    """
    if not isinstance(network, dict):
        raise ValueError("network must be a mapping")
    for key in ("damping_resistance_ohm", "series_inductance_h"):
        if key not in network:
            raise ValueError("network is missing required key %r" % key)
    if not isinstance(sweep_points, (list, tuple)) or not sweep_points:
        raise ValueError("the sweep must contain at least one measurement point")
    results = []
    findings = []
    previous_frequency = None
    for point in sweep_points:
        if not isinstance(point, dict):
            raise ValueError("each sweep point must be a mapping")
        for key in ("frequency_hz", "measured_ohm"):
            if key not in point:
                raise ValueError("sweep point is missing required key %r" % key)
        frequency = _require_number(point["frequency_hz"], "frequency_hz")
        if previous_frequency is not None and frequency <= previous_frequency:
            raise ValueError("sweep frequencies must be strictly increasing")
        previous_frequency = frequency
        modelled = stabilization_network_impedance(
            network["damping_resistance_ohm"],
            network["series_inductance_h"],
            frequency,
        )
        deviation = relative_deviation(point["measured_ohm"], modelled)
        compliant = within_tolerance(
            point["measured_ohm"], modelled, tolerance_fraction
        )
        record = {
            "frequency_hz": frequency,
            "modelled_ohm": modelled,
            "measured_ohm": float(point["measured_ohm"]),
            "deviation": deviation,
            "within_tolerance": compliant,
        }
        results.append(record)
        if not compliant:
            findings.append(
                {
                    "frequency_hz": frequency,
                    "deviation": deviation,
                    "finding": "impedance-outside-tolerance-band",
                }
            )
    return {"points": results, "findings": findings}


def evaluate_campaign_drift(checkpoints, drift_tolerance_fraction):
    """Check impedance stability across the recorded campaign checkpoints.

    Each checkpoint carries 'label', an integer 'sequence' and the
    'measured_ohm' reading. The opening checkpoint sets the baseline; every
    later checkpoint is compared against it. A campaign with a single
    checkpoint cannot demonstrate stability and is rejected.
    """
    if not isinstance(checkpoints, (list, tuple)) or len(checkpoints) < 2:
        raise ValueError(
            "campaign stability needs an opening and at least one later checkpoint"
        )
    ordered = []
    previous_sequence = None
    for entry in checkpoints:
        if not isinstance(entry, dict):
            raise ValueError("each checkpoint must be a mapping")
        for key in ("label", "sequence", "measured_ohm"):
            if key not in entry:
                raise ValueError("checkpoint is missing required key %r" % key)
        sequence = entry["sequence"]
        if isinstance(sequence, bool) or not isinstance(sequence, int):
            raise ValueError("checkpoint 'sequence' must be an integer")
        if previous_sequence is not None and sequence <= previous_sequence:
            raise ValueError("checkpoint sequence must be strictly increasing")
        previous_sequence = sequence
        ordered.append(entry)
    baseline = _require_number(ordered[0]["measured_ohm"], "measured_ohm")
    if baseline <= 0.0:
        raise ValueError("baseline measured_ohm must be positive")
    drifts = []
    findings = []
    for entry in ordered[1:]:
        drift = relative_deviation(entry["measured_ohm"], baseline)
        stable = within_tolerance(
            entry["measured_ohm"], baseline, drift_tolerance_fraction
        )
        drifts.append(
            {"label": entry["label"], "drift": drift, "stable": stable}
        )
        if not stable:
            findings.append(
                {
                    "label": entry["label"],
                    "drift": drift,
                    "finding": "impedance-drift-beyond-campaign-allowance",
                }
            )
    return {"baseline_ohm": baseline, "checkpoints": drifts, "findings": findings}


def assess_supply_impedance_control(setup):
    """Aggregate the clause 5.2.4 verdict for one measurement campaign.

    'setup' carries 'lines', 'network', 'sweep_points', 'tolerance_fraction',
    'checkpoints' and 'drift_tolerance_fraction'. The campaign is compliant
    only when coverage, sweep and drift each return no finding.
    """
    if not isinstance(setup, dict):
        raise ValueError("setup must be a mapping")
    required = (
        "lines",
        "network",
        "sweep_points",
        "tolerance_fraction",
        "checkpoints",
        "drift_tolerance_fraction",
    )
    for key in required:
        if key not in setup:
            raise ValueError("setup is missing required key %r" % key)
    coverage = evaluate_line_coverage(setup["lines"])
    sweep = evaluate_frequency_sweep(
        setup["network"], setup["sweep_points"], setup["tolerance_fraction"]
    )
    drift = evaluate_campaign_drift(
        setup["checkpoints"], setup["drift_tolerance_fraction"]
    )
    findings = coverage["findings"] + sweep["findings"] + drift["findings"]
    return {
        "coverage": coverage,
        "sweep": sweep,
        "drift": drift,
        "findings": findings,
        "compliant": not findings,
    }
