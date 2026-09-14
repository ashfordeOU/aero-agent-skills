#!/usr/bin/env python3
"""Adapting the single-junction capacitance method to a multijunction cell.

Anchor: ECSS-E-ST-20-08C clause 11.1.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The capacitance method of the preceding clauses is written for one
junction: one depletion region, one bias, one capacitance. A
multijunction cell is not that device. It is a monolithic series stack
of two, three or more sub-cell junctions joined by tunnel junctions, and
the two terminals a meter clips onto see the stack, never a sub-cell.

Three consequences follow, and between them they are why the method has
to be adapted rather than merely repeated.

    Series summation      The sub-cell capacitances add as reciprocals,
                          so the terminal reading sits below the
                          smallest of them. A three-junction stack does
                          not read three times anything; it reads less
                          than its stingiest sub-cell.

    Bias partition        Series capacitors carry equal charge, so the
                          applied terminal bias divides in proportion to
                          the reciprocal capacitances. The sub-cell that
                          dominates the reading is also the one taking
                          most of the bias, and a single-junction
                          extraction that attributes the whole terminal
                          bias to one junction is wrong by the rest of
                          the partition.

    Tunnel junction loss  The tunnel junctions add series resistance
                          that the single-junction method never had to
                          budget for. Above the corner that resistance
                          sets with the stack capacitance, the measured
                          capacitance rolls off and the meter reports a
                          smaller device than it has.

A stack whose reading is dominated by one sub-cell also cannot be
resolved into its parts at the terminals at all: the remaining sub-cells
contribute too little of the reciprocal sum to be separable, and the
honest answer is a dedicated single-junction coupon rather than a
cleverer fit.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SERIES_SUMMATION = "series-stack-reciprocal-summation"
BIAS_PARTITION = "per-subcell-bias-partition"
CORNER_FREQUENCY_MARGIN = "tunnel-junction-corner-frequency-margin"
DOMINANT_SUBCELL_IDENTIFICATION = "dominant-subcell-identification"

REQUIRED_ADAPTATIONS = (
    SERIES_SUMMATION,
    BIAS_PARTITION,
    CORNER_FREQUENCY_MARGIN,
    DOMINANT_SUBCELL_IDENTIFICATION,
)

MIN_SUBCELLS_FOR_ADAPTATION = 2
MAX_DOMINANT_SHARE = 0.9
MAX_FREQUENCY_FRACTION_OF_CORNER = 0.1
MAX_FORWARD_BIAS_FRACTION = 0.3

ADAPTATION_ADEQUATE = "multijunction-adaptation-adequate"
ADAPTATION_NOT_ADEQUATE = "multijunction-adaptation-not-adequate"

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


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A reciprocal share or a frequency margin is a quotient of floats that
    can land a few units in the last place either side of a written
    limit. The limit is never relaxed; only the comparison tolerates the
    representation error, which is why no caller uses a bare >= on a
    derived float.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_subcells(subcells):
    """Reduce a declared sub-cell stack to named, usable junctions.

    Each sub-cell brings a name, the capacitance of its own depletion
    region and its own built-in voltage. A stack with a repeated name
    cannot be reported against, so it is refused at the input.
    """
    if not isinstance(subcells, (list, tuple)) or not subcells:
        raise ValueError(
            "sub-cell stack must be a non-empty sequence, got %r" % (subcells,)
        )
    stack = []
    names = set()
    for index, subcell in enumerate(subcells):
        if not isinstance(subcell, dict):
            raise ValueError(
                "sub-cell %d must be a mapping, got %r" % (index, subcell)
            )
        name = subcell.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("sub-cell %d must carry a name, got %r" % (index, name))
        if name in names:
            raise ValueError("sub-cell name %r appears more than once" % name)
        names.add(name)
        stack.append(
            {
                "name": name,
                "capacitance_f": _require_positive(
                    "sub-cell %s capacitance_f" % name, subcell.get("capacitance_f")
                ),
                "built_in_voltage_v": _require_positive(
                    "sub-cell %s built_in_voltage_v" % name,
                    subcell.get("built_in_voltage_v"),
                ),
            }
        )
    return tuple(stack)


def adaptation_required(subcells):
    """Whether the stack is deep enough to need the method adapted at all."""
    return len(validate_subcells(subcells)) >= MIN_SUBCELLS_FOR_ADAPTATION


def series_capacitance_f(subcells):
    """Terminal capacitance of the stack, reciprocals summed in series."""
    stack = validate_subcells(subcells)
    total = 0.0
    for subcell in stack:
        total += 1.0 / subcell["capacitance_f"]
    return 1.0 / total


def reciprocal_shares(subcells):
    """Share of the reciprocal sum each sub-cell contributes.

    This is the quantity that decides everything downstream: it is both
    the sub-cell's weight in the terminal reading and its share of the
    applied bias.
    """
    stack = validate_subcells(subcells)
    total = sum(1.0 / subcell["capacitance_f"] for subcell in stack)
    return tuple(
        {
            "name": subcell["name"],
            "share": (1.0 / subcell["capacitance_f"]) / total,
        }
        for subcell in stack
    )


def dominant_subcell(subcells):
    """The sub-cell that governs the terminal reading.

    The smallest capacitance holds the largest reciprocal share, so it
    both sets the terminal value and takes the largest slice of bias.
    """
    shares = reciprocal_shares(subcells)
    return max(shares, key=lambda entry: entry["share"])


def subcell_bias_partition(subcells, terminal_bias_v):
    """How an applied terminal bias divides across the series stack."""
    bias = _require_number("terminal_bias_v", terminal_bias_v)
    return tuple(
        {"name": entry["name"], "bias_voltage_v": entry["share"] * bias}
        for entry in reciprocal_shares(subcells)
    )


def single_junction_bias_error_fraction(subcells):
    """Bias a one-junction extraction misattributes to the dominant cell.

    Treating the stack as one junction hands the whole terminal bias to
    the dominant sub-cell. The rest of the partition is the error, and
    it is not small on a balanced stack.
    """
    return 1.0 - dominant_subcell(subcells)["share"]


def tunnel_corner_frequency_hz(series_resistance_ohm, terminal_capacitance_f):
    """Frequency above which the tunnel-junction resistance hides the stack."""
    resistance = _require_positive(
        "tunnel_junction_series_resistance_ohm", series_resistance_ohm
    )
    capacitance = _require_positive(
        "terminal_capacitance_f", terminal_capacitance_f
    )
    return 1.0 / (2.0 * math.pi * resistance * capacitance)


def frequency_margin(test_frequency_hz, corner_frequency_hz):
    """Test frequency expressed as a fraction of the roll-off corner."""
    frequency = _require_positive("test_frequency_hz", test_frequency_hz)
    corner = _require_positive("corner_frequency_hz", corner_frequency_hz)
    return frequency / corner


def forward_bias_exceedances(subcells, terminal_bias_v):
    """Sub-cells the partition pushes too far forward to stay depleted."""
    stack = {entry["name"]: entry for entry in validate_subcells(subcells)}
    offenders = []
    for entry in subcell_bias_partition(subcells, terminal_bias_v):
        ceiling = MAX_FORWARD_BIAS_FRACTION * stack[entry["name"]]["built_in_voltage_v"]
        if not _at_most(entry["bias_voltage_v"], ceiling):
            offenders.append(
                {
                    "name": entry["name"],
                    "bias_voltage_v": entry["bias_voltage_v"],
                    "forward_ceiling_v": ceiling,
                }
            )
    return tuple(offenders)


def missing_adaptations(declared):
    """Required adaptations the campaign has not declared it applied."""
    if declared is None:
        applied = ()
    elif isinstance(declared, (list, tuple, set, frozenset)):
        applied = tuple(declared)
    else:
        raise ValueError(
            "declared adaptations must be a sequence of names, got %r" % (declared,)
        )
    for name in applied:
        if name not in REQUIRED_ADAPTATIONS:
            raise ValueError(
                "unknown adaptation %r; required adaptations are %s"
                % (name, ", ".join(REQUIRED_ADAPTATIONS))
            )
    return tuple(name for name in REQUIRED_ADAPTATIONS if name not in applied)


def assess_multijunction_adaptation(case):
    """Full clause 11.1.5 judgement of a multijunction capacitance run."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    stack = validate_subcells(case.get("subcells"))
    terminal_capacitance = series_capacitance_f(stack)
    shares = reciprocal_shares(stack)
    dominant = dominant_subcell(stack)
    terminal_bias = _require_number("terminal_bias_v", case.get("terminal_bias_v"))
    partition = subcell_bias_partition(stack, terminal_bias)
    corner = tunnel_corner_frequency_hz(
        case.get("tunnel_junction_series_resistance_ohm"), terminal_capacitance
    )
    margin = frequency_margin(case.get("test_frequency_hz"), corner)
    exceedances = forward_bias_exceedances(stack, terminal_bias)
    absent = missing_adaptations(case.get("declared_adaptations"))
    bias_error = single_junction_bias_error_fraction(stack)

    findings = []

    if len(stack) < MIN_SUBCELLS_FOR_ADAPTATION:
        findings.append(
            "stack declares %d junction; the single-junction method applies "
            "unchanged and this clause is not the one to work from" % len(stack)
        )

    if absent:
        findings.append(
            "single-junction method carried over without %s" % ", ".join(absent)
        )

    if not _at_most(dominant["share"], MAX_DOMINANT_SHARE):
        findings.append(
            "sub-cell %s holds %.1f%% of the reciprocal sum, above the %.0f%% "
            "ceiling; the remaining junctions are not separable at the terminals "
            "and want a dedicated single-junction coupon"
            % (dominant["name"], dominant["share"] * 100.0, MAX_DOMINANT_SHARE * 100.0)
        )

    if not _at_most(margin, MAX_FREQUENCY_FRACTION_OF_CORNER):
        findings.append(
            "test frequency sits at %.3f of the tunnel-junction corner, above the "
            "%.2f ceiling; the reading is rolling off rather than reporting the stack"
            % (margin, MAX_FREQUENCY_FRACTION_OF_CORNER)
        )

    if exceedances:
        findings.append(
            "terminal bias of %.3f V drives %s past its forward ceiling once the "
            "partition is applied"
            % (terminal_bias, ", ".join(entry["name"] for entry in exceedances))
        )

    adequate = not findings
    return {
        "subcell_count": len(stack),
        "adaptation_required": len(stack) >= MIN_SUBCELLS_FOR_ADAPTATION,
        "terminal_capacitance_f": terminal_capacitance,
        "reciprocal_shares": shares,
        "dominant_subcell": dominant,
        "bias_partition": partition,
        "single_junction_bias_error_fraction": bias_error,
        "tunnel_corner_frequency_hz": corner,
        "frequency_margin": margin,
        "forward_bias_exceedances": exceedances,
        "missing_adaptations": absent,
        "verdict": ADAPTATION_ADEQUATE if adequate else ADAPTATION_NOT_ADEQUATE,
        "adequate": adequate,
        "findings": findings,
    }
