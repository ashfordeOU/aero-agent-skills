#!/usr/bin/env python3
"""Spread-spectrum operating-frequency selection, ECSS-E-ST-20-07C clause 5.2.7.3.

Paraphrased procedure, no verbatim standard text. When the unit-under-test
transmits with a spreading technique, the emission is not a single carrier and
the test cannot simply be run "at the operating frequency". The clause obliges
the test plan to state which operating frequencies the unit is exercised on.
This module turns that into a deterministic selection:

  declared unit  -> validated spreading mode, chip rate, hop set, tuning band
  tuning band    -> occupied bandwidth -> low / mid / high tune points
  hop set        -> representative hop channels
  hop dwell      -> receiver dwell the selection needs to stay observable

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Frequency comparison tolerance. Tune points are differences and midpoints of
# float frequencies, so an exactly-satisfied separation can land a few units in
# the last place short. The tolerance absorbs that representation error only;
# it never relaxes a separation requirement.
TOL = 1e-9

MODE_DIRECT_SEQUENCE = "direct-sequence"
MODE_FREQUENCY_HOPPING = "frequency-hopping"
MODE_HYBRID = "hybrid"
RECOGNIZED_MODES = (MODE_DIRECT_SEQUENCE, MODE_FREQUENCY_HOPPING, MODE_HYBRID)

# Null-to-null main-lobe width of a direct-sequence spectrum is twice the
# chip rate; that is the band a single tune point actually occupies.
MAIN_LOBE_CHIP_RATE_FACTOR = 2.0

# Low, mid and high tune points across a tunable band.
DEFAULT_TUNE_POINT_COUNT = 3

# Representative hop channels taken from a declared hop set.
DEFAULT_HOP_POINT_COUNT = 3

# Receiver dwell must reach this multiple of one full hop revisit period
# before every declared channel is seen inside a single measurement.
DEFAULT_DWELL_MARGIN_FACTOR = 1.0

CATEGORY_USABLE = "usable"
CATEGORY_MARGINAL = "marginal"
CATEGORY_REJECTED = "rejected"
CATEGORIES = (CATEGORY_USABLE, CATEGORY_MARGINAL, CATEGORY_REJECTED)


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


def _positive(record, key, where):
    value = _number(record, key, where)
    if value <= 0.0:
        raise ValueError("%s: field %r must be > 0, got %g" % (where, key, value))
    return value


def at_least(value, requirement, tol=TOL):
    """True when value meets the requirement, absorbing float error only."""
    if value >= requirement:
        return True
    return math.isclose(value, requirement, rel_tol=0.0, abs_tol=tol)


def normalize_mode(mode):
    """Return the recognized spreading-mode designation for a raw string."""
    if not isinstance(mode, str):
        raise ValueError("spreading mode must be a string, got %r" % (mode,))
    key = mode.strip().lower()
    if key not in RECOGNIZED_MODES:
        raise ValueError(
            "unrecognized spreading mode %r; recognized: %s"
            % (mode, ", ".join(RECOGNIZED_MODES))
        )
    return key


def validate_tuning_band(band):
    """Validate the declared tunable band and return it as (low, high) hertz."""
    where = "tuning_band"
    if not isinstance(band, dict):
        raise ValueError("%s: record must be a mapping" % where)
    low = _positive(band, "low_hz", where)
    high = _positive(band, "high_hz", where)
    if high <= low:
        raise ValueError(
            "%s: high_hz %g must exceed low_hz %g" % (where, high, low)
        )
    return (low, high)


def validate_hop_set(channels, band):
    """Validate a declared hop set and return it sorted, deduplicated."""
    where = "hop_set"
    if not isinstance(channels, (list, tuple)):
        raise ValueError("%s: hop channels must be a list" % where)
    if len(channels) < 2:
        raise ValueError(
            "%s: a hopping declaration needs at least two channels, got %d"
            % (where, len(channels))
        )
    low, high = band
    seen = []
    for index, raw in enumerate(channels):
        tag = "%s[%d]" % (where, index)
        value = _positive({"channel_hz": raw}, "channel_hz", tag)
        if value < low or value > high:
            raise ValueError(
                "%s: channel %g Hz falls outside the declared tuning band "
                "%g-%g Hz" % (tag, value, low, high)
            )
        for other in seen:
            if math.isclose(value, other, rel_tol=0.0, abs_tol=TOL):
                raise ValueError(
                    "%s: duplicate hop channel %g Hz in the declared set"
                    % (tag, value)
                )
        seen.append(value)
    return tuple(sorted(seen))


def validate_spread_spectrum_unit(unit):
    """Validate the declared spread-spectrum emitter and normalize it.

    Required for every mode: mode, tuning_band.
    direct-sequence and hybrid additionally require chip_rate_hz.
    frequency-hopping and hybrid additionally require hop_channels_hz,
    hop_dwell_s and, for a pure hopper, channel_bandwidth_hz.
    """
    where = "unit"
    if not isinstance(unit, dict):
        raise ValueError("%s: record must be a mapping" % where)
    mode = normalize_mode(unit.get("mode"))
    band = validate_tuning_band(unit.get("tuning_band"))

    chip_rate = None
    if mode in (MODE_DIRECT_SEQUENCE, MODE_HYBRID):
        chip_rate = _positive(unit, "chip_rate_hz", where)

    channel_bandwidth = None
    hop_channels = None
    hop_dwell = None
    if mode in (MODE_FREQUENCY_HOPPING, MODE_HYBRID):
        hop_channels = validate_hop_set(unit.get("hop_channels_hz"), band)
        hop_dwell = _positive(unit, "hop_dwell_s", where)
        if mode == MODE_FREQUENCY_HOPPING:
            channel_bandwidth = _positive(unit, "channel_bandwidth_hz", where)

    return {
        "mode": mode,
        "tuning_band_hz": band,
        "chip_rate_hz": chip_rate,
        "channel_bandwidth_hz": channel_bandwidth,
        "hop_channels_hz": hop_channels,
        "hop_dwell_s": hop_dwell,
    }


def occupied_bandwidth_hz(unit):
    """Band a single emission event occupies, from the validated declaration."""
    mode = unit["mode"]
    if mode in (MODE_DIRECT_SEQUENCE, MODE_HYBRID):
        return MAIN_LOBE_CHIP_RATE_FACTOR * unit["chip_rate_hz"]
    return unit["channel_bandwidth_hz"]


def select_tune_points(band, occupied_bw_hz, count=DEFAULT_TUNE_POINT_COUNT):
    """Return evenly spaced tune points that keep the occupied band inside.

    The lowest and highest tune points are pulled half an occupied bandwidth
    inside the band edges, so the emission itself never straddles the edge.
    """
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError("count must be an integer, got %r" % (count,))
    if count < 2:
        raise ValueError("count must be >= 2 to bracket a band, got %d" % count)
    low, high = band
    bw = _positive({"v": occupied_bw_hz}, "v", "occupied_bandwidth_hz")
    span = high - low
    if span <= bw:
        raise ValueError(
            "tuning band %g-%g Hz is narrower than the occupied bandwidth "
            "%g Hz; no tune point fits inside the edges" % (low, high, bw)
        )
    first = low + bw / 2.0
    last = high - bw / 2.0
    step = (last - first) / float(count - 1)
    return tuple(first + step * index for index in range(count))


def select_hop_channels(channels, count=DEFAULT_HOP_POINT_COUNT):
    """Return representative channels: lowest, nearest the centre, highest."""
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError("count must be an integer, got %r" % (count,))
    if count < 1:
        raise ValueError("count must be >= 1, got %d" % count)
    ordered = tuple(sorted(channels))
    if count > len(ordered):
        raise ValueError(
            "asked for %d representative channels but the declared set holds "
            "only %d" % (count, len(ordered))
        )
    if count == 1:
        return (ordered[0],)
    if count == 2:
        return (ordered[0], ordered[-1])
    centre = (ordered[0] + ordered[-1]) / 2.0
    picked = [ordered[0], ordered[-1]]
    interior = [c for c in ordered[1:-1]]
    while len(picked) < count and interior:
        nearest = min(interior, key=lambda c: (abs(c - centre), c))
        picked.append(nearest)
        interior.remove(nearest)
    return tuple(sorted(picked))


def separation_findings(frequencies, occupied_bw_hz):
    """Report adjacent tune points whose occupied spectra would overlap."""
    ordered = sorted(frequencies)
    findings = []
    for index in range(1, len(ordered)):
        gap = ordered[index] - ordered[index - 1]
        if not at_least(gap, occupied_bw_hz):
            findings.append(
                "tune points %g Hz and %g Hz are %g Hz apart, short of the "
                "%g Hz occupied bandwidth"
                % (ordered[index - 1], ordered[index], gap, occupied_bw_hz)
            )
    return findings


def hop_revisit_period_s(hop_dwell_s, channel_count):
    """Time for a hopper to visit every declared channel once."""
    dwell = _positive({"v": hop_dwell_s}, "v", "hop_dwell_s")
    if not isinstance(channel_count, int) or isinstance(channel_count, bool):
        raise ValueError("channel_count must be an integer, got %r" % (channel_count,))
    if channel_count < 1:
        raise ValueError("channel_count must be >= 1, got %d" % channel_count)
    return dwell * float(channel_count)


def required_receiver_dwell_s(
    hop_dwell_s, channel_count, margin_factor=DEFAULT_DWELL_MARGIN_FACTOR
):
    """Receiver dwell a hopping emission needs before it is observable."""
    margin = _positive({"v": margin_factor}, "v", "margin_factor")
    return hop_revisit_period_s(hop_dwell_s, channel_count) * margin


def assess_receiver_dwell(declared_dwell_s, required_dwell_s):
    """Compare a declared receiver dwell against the dwell the hop set needs."""
    declared = _positive({"v": declared_dwell_s}, "v", "receiver_dwell_s")
    required = _positive({"v": required_dwell_s}, "v", "required_dwell_s")
    adequate = at_least(declared, required)
    return {
        "receiver_dwell_s": declared,
        "required_dwell_s": required,
        "adequate": adequate,
        "shortfall_s": 0.0 if adequate else required - declared,
    }


def plan_spread_spectrum_frequency_selection(
    unit,
    receiver_dwell_s=None,
    tune_point_count=DEFAULT_TUNE_POINT_COUNT,
    hop_point_count=DEFAULT_HOP_POINT_COUNT,
    dwell_margin_factor=DEFAULT_DWELL_MARGIN_FACTOR,
):
    """Full clause 5.2.7.3 operating-frequency selection for one emitter."""
    declared = validate_spread_spectrum_unit(unit)
    bandwidth = occupied_bandwidth_hz(declared)
    tune_points = select_tune_points(
        declared["tuning_band_hz"], bandwidth, tune_point_count
    )
    findings = list(separation_findings(tune_points, bandwidth))
    limitations = []

    hop_points = None
    dwell = None
    if declared["hop_channels_hz"] is not None:
        channels = declared["hop_channels_hz"]
        hop_points = select_hop_channels(channels, min(hop_point_count, len(channels)))
        if len(channels) > hop_point_count:
            limitations.append(
                "%d declared hop channels reduced to %d representative channels"
                % (len(channels), len(hop_points))
            )
        required = required_receiver_dwell_s(
            declared["hop_dwell_s"], len(channels), dwell_margin_factor
        )
        if receiver_dwell_s is None:
            limitations.append(
                "no receiver dwell declared; the selection needs at least "
                "%g s to see every hop channel" % required
            )
        else:
            dwell = assess_receiver_dwell(receiver_dwell_s, required)
            if not dwell["adequate"]:
                findings.append(
                    "receiver dwell %g s is %g s short of the %g s hop revisit "
                    "period" % (
                        dwell["receiver_dwell_s"],
                        dwell["shortfall_s"],
                        dwell["required_dwell_s"],
                    )
                )

    if findings:
        category = CATEGORY_REJECTED
    elif limitations:
        category = CATEGORY_MARGINAL
    else:
        category = CATEGORY_USABLE

    return {
        "unit": declared,
        "occupied_bandwidth_hz": bandwidth,
        "tune_points_hz": tune_points,
        "hop_points_hz": hop_points,
        "receiver_dwell": dwell,
        "findings": findings,
        "limitations": limitations,
        "category": category,
        "verdict": "selection-usable" if not findings else "selection-rejected",
    }
