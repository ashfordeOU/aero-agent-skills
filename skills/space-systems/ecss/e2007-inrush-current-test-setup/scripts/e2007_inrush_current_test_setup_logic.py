#!/usr/bin/env python3
"""Inrush-current test setup, ECSS-E-ST-20-07C clause 5.4.4.3.

Paraphrased procedure, no verbatim standard text. The clause does not
describe a bench from nothing: the inrush arrangement starts from the
standard equipment configuration and is modified by the deltas the
inrush measurement itself needs. This module turns that into a
deterministic assessment:

  baseline bands + declared deltas -> the bands this bench is graded on
  realized geometry                -> conforming / deviation / nonconforming
  probe and oscilloscope bandwidth -> chain rise time against the surge
  chain bandwidth                  -> sample rate and record length needed

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerances. Band edges, rise times and sample rates are
# floats, so a value that exactly meets a bound can land a few units in
# the last place off it. The tolerances absorb that representation error
# only; they never relax a band.
REL_TOL = 1e-12
ABS_TOL = 1e-12

# Rise time to bandwidth product of a single-pole measurement chain.
RISE_BANDWIDTH_PRODUCT = 0.35

# The chain must be this much faster than the surge it is capturing
# before the recorded rise time is the unit's rather than the bench's.
CHAIN_SPEED_FACTOR = 3.0

# Samples per chain rise time, and the settling multiple the record has
# to span, before the captured trace can be read as a transient.
SAMPLES_PER_RISE_TIME = 5.0
RECORD_SETTLING_MULTIPLE = 5.0

PROBE_TYPES = ("current-probe", "current-shunt")

GEOMETRY_PARAMETERS = (
    "bond_resistance_ohm",
    "lead_height_m",
    "lead_length_m",
    "probe_to_connector_m",
    "source_impedance_ohm",
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
    """Move the baseline bands by the deltas the inrush setup declares.

    baseline_bands maps a geometry parameter to a (minimum, maximum) pair.
    deltas maps a parameter to {"minimum_delta": x, "maximum_delta": y};
    either key may be omitted. An unknown parameter is refused, and so is
    a delta that collapses or inverts the band it is applied to.
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
    """Validate a realized inrush bench and return it normalized."""
    where = "bench"
    if not isinstance(config, dict):
        raise ValueError("%s: record must be a mapping" % where)

    probe_type = _word(config, "probe_type", where, PROBE_TYPES)

    positive = (
        "bus_voltage_v",
        "lead_length_m",
        "lead_height_m",
        "probe_to_connector_m",
        "probe_bandwidth_hz",
        "recorder_bandwidth_hz",
        "sample_rate_hz",
        "record_length_s",
    )
    values = {}
    for key in positive:
        value = _number(config, key, where)
        if value <= 0.0:
            raise ValueError("%s: %s must be > 0, got %g" % (where, key, value))
        values[key] = value

    for key in ("bond_resistance_ohm", "source_impedance_ohm"):
        value = _number(config, key, where)
        if value < 0.0:
            raise ValueError("%s: %s must be >= 0, got %g" % (where, key, value))
        values[key] = value

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

    values["probe_type"] = probe_type
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


def chain_rise_time_s(probe_bandwidth_hz, recorder_bandwidth_hz):
    """Rise time of the probe and recorder in series, added in quadrature."""
    probe = _scalar(probe_bandwidth_hz, "probe_bandwidth_hz")
    recorder = _scalar(recorder_bandwidth_hz, "recorder_bandwidth_hz")
    if probe <= 0.0:
        raise ValueError("probe_bandwidth_hz must be > 0, got %g" % probe)
    if recorder <= 0.0:
        raise ValueError("recorder_bandwidth_hz must be > 0, got %g" % recorder)
    probe_rise = RISE_BANDWIDTH_PRODUCT / probe
    recorder_rise = RISE_BANDWIDTH_PRODUCT / recorder
    return math.sqrt(probe_rise * probe_rise + recorder_rise * recorder_rise)


def chain_bandwidth_hz(probe_bandwidth_hz, recorder_bandwidth_hz):
    """Bandwidth of the probe and recorder in series."""
    return RISE_BANDWIDTH_PRODUCT / chain_rise_time_s(
        probe_bandwidth_hz, recorder_bandwidth_hz
    )


def required_chain_bandwidth_hz(surge_rise_time_s, speed_factor=CHAIN_SPEED_FACTOR):
    """Chain bandwidth needed before the recorded edge is the unit's own."""
    rise = _scalar(surge_rise_time_s, "surge_rise_time_s")
    factor = _scalar(speed_factor, "speed_factor")
    if rise <= 0.0:
        raise ValueError("surge_rise_time_s must be > 0, got %g" % rise)
    if factor < 1.0:
        raise ValueError("speed_factor must be >= 1, got %g" % factor)
    return factor * RISE_BANDWIDTH_PRODUCT / rise


def required_sample_rate_hz(chain_bandwidth, samples_per_rise=SAMPLES_PER_RISE_TIME):
    """Sample rate that puts enough points on one chain rise time."""
    bandwidth = _scalar(chain_bandwidth, "chain_bandwidth")
    samples = _scalar(samples_per_rise, "samples_per_rise")
    if bandwidth <= 0.0:
        raise ValueError("chain_bandwidth must be > 0, got %g" % bandwidth)
    if samples < 1.0:
        raise ValueError("samples_per_rise must be >= 1, got %g" % samples)
    return samples * bandwidth / RISE_BANDWIDTH_PRODUCT


def required_record_length_s(settling_time_constant_s, multiple=RECORD_SETTLING_MULTIPLE):
    """Record length that spans the surge and its settling."""
    tau = _scalar(settling_time_constant_s, "settling_time_constant_s")
    count = _scalar(multiple, "multiple")
    if tau <= 0.0:
        raise ValueError("settling_time_constant_s must be > 0, got %g" % tau)
    if count < 1.0:
        raise ValueError("multiple must be >= 1, got %g" % count)
    return count * tau


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


def assess_inrush_setup(
    config,
    baseline_bands,
    deltas=None,
    surge_rise_time_s=1.0e-5,
    settling_time_constant_s=1.0e-3,
):
    """Full clause 5.4.4.3 assessment of an inrush-current bench."""
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

    rise = chain_rise_time_s(
        bench["probe_bandwidth_hz"], bench["recorder_bandwidth_hz"]
    )
    bandwidth = RISE_BANDWIDTH_PRODUCT / rise
    needed_bandwidth = required_chain_bandwidth_hz(surge_rise_time_s)
    bandwidth_ok = at_least(bandwidth, needed_bandwidth)
    if not bandwidth_ok:
        findings.append(
            "measurement chain reaches %g Hz, below the %g Hz a %g s surge edge "
            "needs; the recorded rise time would be the bench's own"
            % (bandwidth, needed_bandwidth, float(surge_rise_time_s))
        )

    needed_rate = required_sample_rate_hz(bandwidth)
    rate_ok = at_least(bench["sample_rate_hz"], needed_rate)
    if not rate_ok:
        findings.append(
            "sample rate %g Hz puts fewer than %g points on the %g s chain rise "
            "time; %g Hz is needed"
            % (bench["sample_rate_hz"], SAMPLES_PER_RISE_TIME, rise, needed_rate)
        )

    needed_record = required_record_length_s(settling_time_constant_s)
    record_ok = at_least(bench["record_length_s"], needed_record)
    if not record_ok:
        findings.append(
            "record length %g s ends before the surge has settled; %g s is needed"
            % (bench["record_length_s"], needed_record)
        )

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
    if bench["probe_type"] == "current-shunt" and bench["source_impedance_ohm"] <= 0.0:
        limitations.append(
            "a shunt in a source of zero declared impedance adds the only series "
            "resistance the surge sees, so the captured peak is the bench's limit"
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
        "chain_rise_time_s": rise,
        "chain_bandwidth_hz": bandwidth,
        "required_chain_bandwidth_hz": needed_bandwidth,
        "required_sample_rate_hz": needed_rate,
        "required_record_length_s": needed_record,
        "bandwidth_is_adequate": bandwidth_ok,
        "sample_rate_is_adequate": rate_ok,
        "record_length_is_adequate": record_ok,
        "governing_parameter": governing_parameter(bench, bands),
        "findings": findings,
        "limitations": limitations,
        "verdict": verdict,
    }
