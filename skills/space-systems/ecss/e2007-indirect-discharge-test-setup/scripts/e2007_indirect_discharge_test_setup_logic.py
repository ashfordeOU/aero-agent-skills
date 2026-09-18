#!/usr/bin/env python3
"""Indirect discharge test setup, ECSS-E-ST-20-07C clause 5.4.12.3.

Paraphrased procedure, no verbatim standard text. The clause does not
build a bench from nothing: the indirect discharge arrangement starts
from the standard equipment configuration and is modified only where
coupling the discharge through a plane rather than into the unit
demands something different. This module turns that into a
deterministic assessment:

  baseline bands + declared deltas -> the bands this bench is graded on
  realized geometry                -> conforming / deviation / nonconforming
  unit footprint + overhang        -> the coupling plane span needed
  bleeder chain + plane capacitance -> bleed time and residual charge

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerances. Band edges and derived spans are floats, so a
# value that exactly meets a bound can land a few units in the last
# place off it. The tolerances absorb that representation error only;
# they never relax a band.
REL_TOL = 1e-12
ABS_TOL = 1e-12

# Time constants the coupling plane has to bleed through before the
# next discharge is fired.
BLEED_MULTIPLE = 5.0

# Residual plane voltage, as a fraction of the charge voltage, above
# which the leftover charge is carried with the run.
RESIDUAL_NOTICE_FRACTION = 1.0e-3

PLANE_TYPES = ("horizontal-coupling-plane", "vertical-coupling-plane")

GEOMETRY_PARAMETERS = (
    "bleeder_resistance_ohm",
    "bond_resistance_ohm",
    "cable_to_plane_separation_m",
    "coupling_plane_distance_m",
    "coupling_plane_overhang_m",
    "insulating_support_thickness_m",
)

CONFORMING = "conforming"
DECLARED_DEVIATION = "declared-deviation"
NONCONFORMING = "nonconforming"

VERDICT_CONFORMING = "setup-conforming"
VERDICT_WITH_DEVIATIONS = "setup-conforming-with-deviations"
VERDICT_NONCONFORMING = "setup-nonconforming"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _word(record, key, where, recognized):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, str):
        raise ValueError("%s: field %r must be a string, got %r" % (where, key, value))
    token = value.strip().lower()
    if token not in recognized:
        raise ValueError(
            "%s: unrecognized %s %r; recognized: %s"
            % (where, key, value, ", ".join(recognized))
        )
    return token


def at_least(value, bound):
    """True when a value reaches a lower bound, absorbing float error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_most(value, bound):
    """True when a value stays under an upper bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def validate_band(band, name):
    """Validate one (minimum, maximum) acceptance band and return it."""
    if not isinstance(band, (tuple, list)) or len(band) != 2:
        raise ValueError("%s: band must be a (minimum, maximum) pair" % name)
    low = _scalar(band[0], "%s.minimum" % name)
    high = _scalar(band[1], "%s.maximum" % name)
    if high <= low:
        raise ValueError(
            "%s: band maximum (%g) must exceed its minimum (%g)" % (name, high, low)
        )
    return (low, high)


def apply_setup_deltas(baseline_bands, deltas):
    """Move the baseline bands by the deltas the indirect setup declares.

    baseline_bands maps a geometry parameter to a (minimum, maximum)
    pair. deltas maps a parameter to {"minimum_delta": x,
    "maximum_delta": y}; either key may be omitted. An unknown parameter
    is refused, and so is a delta that collapses or inverts the band it
    is applied to.
    """
    if not isinstance(baseline_bands, dict) or not baseline_bands:
        raise ValueError("baseline_bands: must be a non-empty mapping")
    if deltas is None:
        deltas = {}
    if not isinstance(deltas, dict):
        raise ValueError("deltas: must be a mapping")

    resolved = {}
    for name, band in baseline_bands.items():
        if name not in GEOMETRY_PARAMETERS:
            raise ValueError(
                "baseline_bands: unknown parameter %r; known: %s"
                % (name, ", ".join(GEOMETRY_PARAMETERS))
            )
        resolved[name] = validate_band(band, name)

    for name, delta in deltas.items():
        if name not in resolved:
            raise ValueError(
                "deltas: %r is not a parameter of this bench; known: %s"
                % (name, ", ".join(sorted(resolved)))
            )
        if not isinstance(delta, dict):
            raise ValueError("deltas[%r]: must be a mapping" % name)
        for key in delta:
            if key not in ("minimum_delta", "maximum_delta"):
                raise ValueError(
                    "deltas[%r]: unknown key %r; use minimum_delta or maximum_delta"
                    % (name, key)
                )
        low, high = resolved[name]
        if "minimum_delta" in delta:
            low = low + _number(delta, "minimum_delta", "deltas[%r]" % name)
        if "maximum_delta" in delta:
            high = high + _number(delta, "maximum_delta", "deltas[%r]" % name)
        if high <= low:
            raise ValueError(
                "deltas[%r]: collapses the band to (%g, %g); a delta may move a "
                "band, not close it" % (name, low, high)
            )
        resolved[name] = (low, high)
    return resolved


def validate_bench(config):
    """Validate a realized indirect discharge bench and return it normalized."""
    where = "bench"
    if not isinstance(config, dict):
        raise ValueError("%s: record must be a mapping" % where)

    plane_type = _word(config, "plane_type", where, PLANE_TYPES)

    positive = (
        "bleeder_resistance_ohm",
        "cable_to_plane_separation_m",
        "charge_voltage_v",
        "coupling_plane_capacitance_f",
        "coupling_plane_distance_m",
        "coupling_plane_overhang_m",
        "coupling_plane_span_m",
        "discharge_interval_s",
        "insulating_support_thickness_m",
        "unit_span_m",
    )
    values = {}
    for key in positive:
        value = _number(config, key, where)
        if value <= 0.0:
            raise ValueError("%s: %s must be > 0, got %g" % (where, key, value))
        values[key] = value

    bond = _number(config, "bond_resistance_ohm", where)
    if bond < 0.0:
        raise ValueError("%s: bond_resistance_ohm must be >= 0, got %g" % (where, bond))
    values["bond_resistance_ohm"] = bond

    count = _number(config, "bleeder_count", where)
    if count < 1.0 or count != math.floor(count):
        raise ValueError(
            "%s: bleeder_count must be a whole number of resistors >= 1, got %g"
            % (where, count)
        )
    values["bleeder_count"] = count

    declared = config.get("declared_deviations", ())
    if isinstance(declared, str) or not isinstance(declared, (tuple, list, set)):
        raise ValueError(
            "%s: declared_deviations must be a sequence of parameter names" % where
        )
    names = set()
    for name in declared:
        if name not in GEOMETRY_PARAMETERS:
            raise ValueError(
                "%s: declared deviation %r is not a graded parameter; graded: %s"
                % (where, name, ", ".join(GEOMETRY_PARAMETERS))
            )
        names.add(name)

    values["plane_type"] = plane_type
    values["declared_deviations"] = frozenset(names)
    return values


def categorize_parameter(value, band, declared_deviation=False):
    """Grade one realized parameter against the band that governs it."""
    low, high = validate_band(band, "band")
    measured = _scalar(value, "value")
    if at_least(measured, low) and at_most(measured, high):
        return CONFORMING
    return DECLARED_DEVIATION if bool(declared_deviation) else NONCONFORMING


def band_margin(value, band):
    """Fractional distance from the nearer band edge, negative when outside."""
    low, high = validate_band(band, "band")
    measured = _scalar(value, "value")
    width = high - low
    return min(measured - low, high - measured) / width


def required_plane_span_m(unit_span_m, overhang_m):
    """Plane span that covers the unit footprint with overhang on both sides."""
    span = _scalar(unit_span_m, "unit_span_m")
    over = _scalar(overhang_m, "overhang_m")
    if span <= 0.0:
        raise ValueError("unit_span_m must be > 0, got %g" % span)
    if over < 0.0:
        raise ValueError("overhang_m must be >= 0, got %g" % over)
    return span + 2.0 * over


def bleeder_time_constant_s(resistance_ohm, count, capacitance_f):
    """Decay constant of the coupling plane through its bleeder chain."""
    ohms = _scalar(resistance_ohm, "resistance_ohm")
    number = _scalar(count, "count")
    cap = _scalar(capacitance_f, "capacitance_f")
    if ohms <= 0.0:
        raise ValueError("resistance_ohm must be > 0, got %g" % ohms)
    if number < 1.0 or number != math.floor(number):
        raise ValueError("count must be a whole number >= 1, got %g" % number)
    if cap <= 0.0:
        raise ValueError("capacitance_f must be > 0, got %g" % cap)
    return ohms * number * cap


def required_bleed_time_s(time_constant_s, multiple=BLEED_MULTIPLE):
    """Time the plane needs to bleed down before the next discharge."""
    tau = _scalar(time_constant_s, "time_constant_s")
    count = _scalar(multiple, "multiple")
    if tau <= 0.0:
        raise ValueError("time_constant_s must be > 0, got %g" % tau)
    if count < 1.0:
        raise ValueError("multiple must be >= 1, got %g" % count)
    return count * tau


def residual_plane_fraction(interval_s, time_constant_s):
    """Fraction of the charge still on the plane when the next event fires."""
    interval = _scalar(interval_s, "interval_s")
    tau = _scalar(time_constant_s, "time_constant_s")
    if interval < 0.0:
        raise ValueError("interval_s must be >= 0, got %g" % interval)
    if tau <= 0.0:
        raise ValueError("time_constant_s must be > 0, got %g" % tau)
    return math.exp(-interval / tau)


def residual_plane_voltage_v(charge_voltage_v, interval_s, time_constant_s):
    """Voltage left on the coupling plane when the next event fires."""
    volts = _scalar(charge_voltage_v, "charge_voltage_v")
    if volts <= 0.0:
        raise ValueError("charge_voltage_v must be > 0, got %g" % volts)
    return volts * residual_plane_fraction(interval_s, time_constant_s)


def governing_parameter(realized, bands):
    """The graded parameter sitting closest to, or furthest outside, its band."""
    if not isinstance(bands, dict) or not bands:
        raise ValueError("bands: must be a non-empty mapping")
    ranked = []
    for name in sorted(bands):
        if name not in realized:
            raise ValueError("realized: missing graded parameter %r" % name)
        ranked.append((band_margin(realized[name], bands[name]), name))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return ranked[0][1]


def assess_indirect_discharge_setup(config, baseline_bands, deltas=None):
    """Full clause 5.4.12.3 assessment of an indirect discharge bench."""
    bench = validate_bench(config)
    bands = apply_setup_deltas(baseline_bands, deltas)

    categories = {}
    findings = []
    for name in sorted(bands):
        category = categorize_parameter(
            bench[name], bands[name], name in bench["declared_deviations"]
        )
        categories[name] = category
        if category == NONCONFORMING:
            low, high = bands[name]
            findings.append(
                "%s is %g, outside its band %g to %g and not declared as a deviation"
                % (name, bench[name], low, high)
            )

    needed_span = required_plane_span_m(
        bench["unit_span_m"], bench["coupling_plane_overhang_m"]
    )
    span_ok = at_least(bench["coupling_plane_span_m"], needed_span)
    if not span_ok:
        findings.append(
            "coupling plane spans %g m, short of the %g m the unit footprint and "
            "its overhang need, so part of the unit is outside the coupled field"
            % (bench["coupling_plane_span_m"], needed_span)
        )

    tau = bleeder_time_constant_s(
        bench["bleeder_resistance_ohm"],
        bench["bleeder_count"],
        bench["coupling_plane_capacitance_f"],
    )
    needed_bleed = required_bleed_time_s(tau)
    bleed_ok = at_least(bench["discharge_interval_s"], needed_bleed)
    if not bleed_ok:
        findings.append(
            "discharge interval %g s is shorter than the %g s the plane needs to "
            "bleed through its chain; the next event starts on a charged plane"
            % (bench["discharge_interval_s"], needed_bleed)
        )

    residual_fraction = residual_plane_fraction(bench["discharge_interval_s"], tau)
    residual_volts = bench["charge_voltage_v"] * residual_fraction

    limitations = []
    deviations = sorted(
        name for name, cat in categories.items() if cat == DECLARED_DEVIATION
    )
    for name in deviations:
        low, high = bands[name]
        limitations.append(
            "%s is %g, outside its band %g to %g but carried as a declared deviation"
            % (name, bench[name], low, high)
        )
    if bleed_ok and residual_fraction > RESIDUAL_NOTICE_FRACTION:
        limitations.append(
            "about %g V is still on the coupling plane when the next event fires, "
            "which the bleed rule allows but the record should carry"
            % residual_volts
        )
    if bench["plane_type"] == "vertical-coupling-plane":
        limitations.append(
            "a vertical plane couples into one face only, so the faces it does "
            "not see are exposed by moving the plane rather than by this run"
        )

    if findings:
        verdict = VERDICT_NONCONFORMING
    elif deviations:
        verdict = VERDICT_WITH_DEVIATIONS
    else:
        verdict = VERDICT_CONFORMING

    return {
        "bench": bench,
        "bands": bands,
        "categories": categories,
        "required_plane_span_m": needed_span,
        "plane_span_is_adequate": span_ok,
        "bleeder_time_constant_s": tau,
        "required_bleed_time_s": needed_bleed,
        "bleed_interval_is_adequate": bleed_ok,
        "residual_plane_fraction": residual_fraction,
        "residual_plane_voltage_v": residual_volts,
        "governing_parameter": governing_parameter(bench, bands),
        "findings": findings,
        "limitations": limitations,
        "verdict": verdict,
    }
