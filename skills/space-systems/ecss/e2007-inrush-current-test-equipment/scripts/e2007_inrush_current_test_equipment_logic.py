#!/usr/bin/env python3
"""Inrush-current test equipment, ECSS-E-ST-20-07C 5.4.4.2.

Paraphrased requirement, no verbatim standard text. The clause names the
items a switch-on surge measurement needs -- an oscilloscope, a current
probe, a spike generator to prove the chain and something to keep the
record on -- and this module decides whether the items actually declared
for a bench can capture the surge that is expected:

  expected surge  -> rise time and peak the measurement has to follow
  requirements    -> chain bandwidth from the rise time, sample rate from
                     the bandwidth, record depth from the capture window,
                     probe peak rating and low-corner ceiling from the
                     allowed droop, generator rise time that still proves
                     the chain
  inventory       -> each declared item compared with its requirement and
                     categorized adequate, marginal or inadequate
  reduction       -> governing shortfall and the bench verdict

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Relative tolerance for comparing a declared capability with a derived
# requirement. It absorbs representation error only; it never relaxes a
# requirement.
REL_TOL = 1e-12

# Rise-time / bandwidth product of a Gaussian-response measurement chain.
# A chain of bandwidth B follows an edge no faster than this over B.
RISE_TIME_BANDWIDTH_PRODUCT = 0.35

# Samples per cycle of the chain bandwidth the record needs so the peak is
# not lost between samples.
DEFAULT_OVERSAMPLE_FACTOR = 5.0

# Headroom the current probe rating carries over the expected peak.
DEFAULT_PROBE_MARGIN = 1.5

# Droop the probe may show across the pulse before the recorded peak is
# understated, as a fraction of the peak.
DEFAULT_DROOP_FRACTION = 0.05

# The spike generator has to produce an edge at least this much faster than
# the chain it is proving, so the chain and not the source sets the rise.
DEFAULT_GENERATOR_RISE_FACTOR = 0.5

# A declared capability inside this fraction of its requirement is reported
# as marginal rather than adequate.
DEFAULT_MARGINAL_FRACTION = 0.1

ITEM_OSCILLOSCOPE = "oscilloscope"
ITEM_CURRENT_PROBE = "current-probe"
ITEM_SPIKE_GENERATOR = "spike-generator"
ITEM_RECORDING_MEDIUM = "recording-medium"
REQUIRED_ITEMS = (
    ITEM_OSCILLOSCOPE,
    ITEM_CURRENT_PROBE,
    ITEM_SPIKE_GENERATOR,
    ITEM_RECORDING_MEDIUM,
)

FITNESS_ADEQUATE = "adequate"
FITNESS_MARGINAL = "marginal"
FITNESS_INADEQUATE = "inadequate"

VERDICT_FIT = "bench-fit"
VERDICT_UNFIT = "bench-unfit"


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


def _positive(value, name):
    number = _scalar(value, name)
    if number <= 0.0:
        raise ValueError("%s must be > 0, got %g" % (name, number))
    return number


def normalize_item(item):
    """Return the recognized bench item for a raw item name."""
    if not isinstance(item, str):
        raise ValueError("bench item must be a string, got %r" % (item,))
    key = item.strip().lower()
    if key not in REQUIRED_ITEMS:
        raise ValueError(
            "unrecognized bench item %r; recognized: %s"
            % (item, ", ".join(REQUIRED_ITEMS))
        )
    return key


def required_bandwidth_hz(rise_time_s, product=RISE_TIME_BANDWIDTH_PRODUCT):
    """Chain bandwidth needed to follow an edge of the expected rise time."""
    rise = _positive(rise_time_s, "rise_time_s")
    factor = _positive(product, "product")
    return factor / rise


def required_sample_rate_hz(bandwidth_hz, oversample=DEFAULT_OVERSAMPLE_FACTOR):
    """Sample rate that keeps the peak from falling between samples."""
    bandwidth = _positive(bandwidth_hz, "bandwidth_hz")
    factor = _scalar(oversample, "oversample")
    if factor < 2.0:
        raise ValueError("oversample must be >= 2, got %g" % factor)
    return bandwidth * factor


def required_record_points(window_s, sample_rate_hz):
    """Record depth the capture window occupies at the required rate."""
    window = _positive(window_s, "window_s")
    rate = _positive(sample_rate_hz, "sample_rate_hz")
    product = window * rate
    # Shave a relative epsilon so a product that lands a few units in the
    # last place above a whole number does not buy a spurious extra point.
    return int(math.ceil(product - abs(product) * REL_TOL))


def probe_rating_requirement_a(expected_peak_a, margin=DEFAULT_PROBE_MARGIN):
    """Peak current the probe must be rated for, with headroom."""
    peak = _positive(expected_peak_a, "expected_peak_a")
    factor = _scalar(margin, "margin")
    if factor < 1.0:
        raise ValueError("margin must be >= 1, got %g" % factor)
    return peak * factor


def probe_low_corner_ceiling_hz(pulse_duration_s, droop_fraction=DEFAULT_DROOP_FRACTION):
    """Highest low-frequency corner the probe may have for the allowed droop.

    A probe behaves as a single-pole high pass at its low corner, so across
    a pulse of duration t the recorded amplitude falls by roughly
    2 * pi * f_low * t. Holding that fall to the allowed fraction bounds
    the corner from above.
    """
    duration = _positive(pulse_duration_s, "pulse_duration_s")
    droop = _scalar(droop_fraction, "droop_fraction")
    if not 0.0 < droop < 1.0:
        raise ValueError("droop_fraction must lie in (0, 1), got %g" % droop)
    return droop / (2.0 * math.pi * duration)


def generator_rise_time_ceiling_s(
    chain_rise_time_s, factor=DEFAULT_GENERATOR_RISE_FACTOR
):
    """Slowest generator edge that still proves the chain, not the source."""
    rise = _positive(chain_rise_time_s, "chain_rise_time_s")
    share = _scalar(factor, "factor")
    if not 0.0 < share <= 1.0:
        raise ValueError("factor must lie in (0, 1], got %g" % share)
    return rise * share


def derive_requirements(surge, oversample=DEFAULT_OVERSAMPLE_FACTOR):
    """Turn the expected surge into the capability each item must carry."""
    if not isinstance(surge, dict):
        raise ValueError("surge: record must be a mapping")
    rise = _number(surge, "rise_time_s", "surge")
    if rise <= 0.0:
        raise ValueError("surge: rise_time_s must be > 0, got %g" % rise)
    peak = _number(surge, "peak_current_a", "surge")
    if peak <= 0.0:
        raise ValueError("surge: peak_current_a must be > 0, got %g" % peak)
    duration = _number(surge, "pulse_duration_s", "surge")
    if duration <= rise:
        raise ValueError(
            "surge: pulse_duration_s %g must exceed rise_time_s %g" % (duration, rise)
        )
    window = (
        _number(surge, "capture_window_s", "surge")
        if "capture_window_s" in surge
        else duration * 10.0
    )
    if window < duration:
        raise ValueError(
            "surge: capture_window_s %g must reach the pulse duration %g"
            % (window, duration)
        )
    margin = (
        _number(surge, "probe_margin", "surge")
        if "probe_margin" in surge
        else DEFAULT_PROBE_MARGIN
    )
    droop = (
        _number(surge, "droop_fraction", "surge")
        if "droop_fraction" in surge
        else DEFAULT_DROOP_FRACTION
    )
    bandwidth = required_bandwidth_hz(rise)
    rate = required_sample_rate_hz(bandwidth, oversample)
    return {
        "rise_time_s": rise,
        "peak_current_a": peak,
        "pulse_duration_s": duration,
        "capture_window_s": window,
        "bandwidth_hz": bandwidth,
        "sample_rate_hz": rate,
        "record_points": required_record_points(window, rate),
        "probe_rating_a": probe_rating_requirement_a(peak, margin),
        "probe_low_corner_ceiling_hz": probe_low_corner_ceiling_hz(duration, droop),
        "generator_peak_a": peak,
        "generator_rise_time_ceiling_s": generator_rise_time_ceiling_s(rise),
    }


def categorize_capability(
    available, required, marginal_fraction=DEFAULT_MARGINAL_FRACTION
):
    """Grade a capability that must reach or beat its requirement."""
    have = _scalar(available, "available")
    need = _positive(required, "required")
    fraction = _scalar(marginal_fraction, "marginal_fraction")
    if not 0.0 <= fraction < 1.0:
        raise ValueError("marginal_fraction must lie in [0, 1), got %g" % fraction)
    if have < need and not math.isclose(have, need, rel_tol=REL_TOL, abs_tol=0.0):
        return FITNESS_INADEQUATE
    if have <= need * (1.0 + fraction):
        return FITNESS_MARGINAL
    return FITNESS_ADEQUATE


def categorize_ceiling(
    available, ceiling, marginal_fraction=DEFAULT_MARGINAL_FRACTION
):
    """Grade a capability that must stay at or under a derived ceiling."""
    have = _scalar(available, "available")
    limit = _positive(ceiling, "ceiling")
    fraction = _scalar(marginal_fraction, "marginal_fraction")
    if not 0.0 <= fraction < 1.0:
        raise ValueError("marginal_fraction must lie in [0, 1), got %g" % fraction)
    if have > limit and not math.isclose(have, limit, rel_tol=REL_TOL, abs_tol=0.0):
        return FITNESS_INADEQUATE
    if have >= limit * (1.0 - fraction):
        return FITNESS_MARGINAL
    return FITNESS_ADEQUATE


def assess_equipment(
    surge,
    inventory,
    oversample=DEFAULT_OVERSAMPLE_FACTOR,
    marginal_fraction=DEFAULT_MARGINAL_FRACTION,
):
    """Full clause 5.4.4.2 fitness judgement on a declared inrush bench."""
    requirements = derive_requirements(surge, oversample)
    if not isinstance(inventory, dict):
        raise ValueError("inventory: record must be a mapping")
    declared = {}
    for raw_name, record in inventory.items():
        name = normalize_item(raw_name)
        if name in declared:
            raise ValueError("inventory: item %r declared twice" % name)
        if not isinstance(record, dict):
            raise ValueError("inventory[%s]: record must be a mapping" % name)
        declared[name] = record

    checks = []
    findings = []
    limitations = []

    for name in REQUIRED_ITEMS:
        if name not in declared:
            findings.append("required item not declared: %s" % name)

    def add(item, quantity, available, required, sense):
        grade = (
            categorize_ceiling(available, required, marginal_fraction)
            if sense == "ceiling"
            else categorize_capability(available, required, marginal_fraction)
        )
        checks.append(
            {
                "item": item,
                "quantity": quantity,
                "available": available,
                "required": required,
                "sense": sense,
                "fitness": grade,
            }
        )
        if grade == FITNESS_INADEQUATE:
            findings.append(
                "%s %s is %g against a requirement of %g" % (item, quantity, available, required)
            )
        elif grade == FITNESS_MARGINAL:
            limitations.append(
                "%s %s is %g, barely meeting %g" % (item, quantity, available, required)
            )

    if ITEM_OSCILLOSCOPE in declared:
        scope = declared[ITEM_OSCILLOSCOPE]
        add(
            ITEM_OSCILLOSCOPE,
            "bandwidth_hz",
            _number(scope, "bandwidth_hz", "oscilloscope"),
            requirements["bandwidth_hz"],
            "floor",
        )
        add(
            ITEM_OSCILLOSCOPE,
            "sample_rate_hz",
            _number(scope, "sample_rate_hz", "oscilloscope"),
            requirements["sample_rate_hz"],
            "floor",
        )

    if ITEM_CURRENT_PROBE in declared:
        probe = declared[ITEM_CURRENT_PROBE]
        add(
            ITEM_CURRENT_PROBE,
            "peak_rating_a",
            _number(probe, "peak_rating_a", "current-probe"),
            requirements["probe_rating_a"],
            "floor",
        )
        add(
            ITEM_CURRENT_PROBE,
            "bandwidth_hz",
            _number(probe, "bandwidth_hz", "current-probe"),
            requirements["bandwidth_hz"],
            "floor",
        )
        add(
            ITEM_CURRENT_PROBE,
            "low_corner_hz",
            _number(probe, "low_corner_hz", "current-probe"),
            requirements["probe_low_corner_ceiling_hz"],
            "ceiling",
        )

    if ITEM_SPIKE_GENERATOR in declared:
        generator = declared[ITEM_SPIKE_GENERATOR]
        add(
            ITEM_SPIKE_GENERATOR,
            "peak_output_a",
            _number(generator, "peak_output_a", "spike-generator"),
            requirements["generator_peak_a"],
            "floor",
        )
        add(
            ITEM_SPIKE_GENERATOR,
            "rise_time_s",
            _number(generator, "rise_time_s", "spike-generator"),
            requirements["generator_rise_time_ceiling_s"],
            "ceiling",
        )

    if ITEM_RECORDING_MEDIUM in declared:
        medium = declared[ITEM_RECORDING_MEDIUM]
        add(
            ITEM_RECORDING_MEDIUM,
            "record_points",
            _number(medium, "record_points", "recording-medium"),
            float(requirements["record_points"]),
            "floor",
        )

    governing = None
    for check in checks:
        if check["fitness"] != FITNESS_INADEQUATE:
            continue
        if check["sense"] == "ceiling":
            shortfall = check["available"] / check["required"]
        else:
            shortfall = check["required"] / check["available"] if check["available"] > 0.0 else float("inf")
        if governing is None or shortfall > governing[0]:
            governing = (shortfall, check)

    return {
        "requirements": requirements,
        "checks": checks,
        "missing_items": [n for n in REQUIRED_ITEMS if n not in declared],
        "governing_shortfall": governing[1] if governing else None,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_FIT if not findings else VERDICT_UNFIT,
    }
