#!/usr/bin/env python3
"""Antenna-port spurious-emission limit logic (ECSS-E-ST-20-07C clause 4.2.6).

Deterministic, offline, Python standard library only.

Clause 4.2.6 asks the supplier to define the spurious-emission limits that
apply at an antenna port so that co-located radio-frequency equipment stays
compatible. This module turns that obligation into a checkable procedure:

1. a declared limit is normalised into ordered, non-overlapping
   frequency-segments (an emission mask);
2. the mask is checked for coverage over every victim receiver passband and
   at every carrier harmonic that lands inside one;
3. the worst declared limit overlapping a victim passband is propagated
   through the antenna-to-antenna isolation to the victim antenna port;
4. the coupled level is compared with the victim susceptibility threshold and
   the resulting compatibility margin is checked against the programme
   requirement;
5. a failing pair reports the isolation it would actually need.

Levels are decibels referred to one milliwatt (dBm), isolation is in decibels
(dB), frequencies are in hertz (Hz). No standard text is reproduced.
"""

import math

__all__ = [
    "DEFAULT_REQUIRED_MARGIN_DB",
    "DEFAULT_MAX_HARMONIC_ORDER",
    "MARGIN_TOLERANCE_DB",
    "normalize_emission_mask",
    "mask_limit_dbm",
    "mask_coverage_gaps",
    "worst_limit_in_band_dbm",
    "harmonic_frequencies",
    "coupled_level_dbm",
    "compatibility_margin_db",
    "required_isolation_db",
    "evaluate_antenna_pair",
    "assess_antenna_port_spurious_emissions",
]

# Programme default for the intersystem compatibility margin, in dB.
DEFAULT_REQUIRED_MARGIN_DB = 6.0

# Highest carrier harmonic considered by default.
DEFAULT_MAX_HARMONIC_ORDER = 5

# Decibel comparisons are sums and differences of floats; a pair that is
# physically exactly on the required margin can land a few ULPs low. This
# tolerance absorbs that representation error. It does NOT relax the
# engineering requirement: 1e-9 dB is far below any measurable quantity.
MARGIN_TOLERANCE_DB = 1e-9

# Two frequencies closer together than this are the same frequency.
FREQUENCY_TOLERANCE_HZ = 1e-6


def _as_float(value, label):
    """Coerce to float or raise ValueError naming the offending field."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _meets(value, required):
    """True when value >= required, absorbing float representation error."""
    return value > required or math.isclose(
        value, required, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE_DB
    )


def normalize_emission_mask(segments):
    """Normalise a declared emission mask into ordered frequency-segments.

    segments: iterable of mappings with f_low_hz, f_high_hz, limit_dbm.
    Returns a tuple of dicts sorted by f_low_hz.

    Raises ValueError when the mask is empty, a segment is malformed, or two
    segments overlap (an overlap means the frequency has two contradictory
    declared limits, so there is no limit at all).
    """
    if segments is None:
        raise ValueError("emission mask is required")
    items = list(segments)
    if not items:
        raise ValueError("emission mask must declare at least one segment")
    out = []
    for index, seg in enumerate(items):
        if not isinstance(seg, dict):
            raise ValueError("mask segment %d must be a mapping" % index)
        for key in ("f_low_hz", "f_high_hz", "limit_dbm"):
            if key not in seg:
                raise ValueError("mask segment %d missing '%s'" % (index, key))
        low = _as_float(seg["f_low_hz"], "mask segment %d f_low_hz" % index)
        high = _as_float(seg["f_high_hz"], "mask segment %d f_high_hz" % index)
        limit = _as_float(seg["limit_dbm"], "mask segment %d limit_dbm" % index)
        if low <= 0.0:
            raise ValueError(
                "mask segment %d f_low_hz must be positive, got %r" % (index, low)
            )
        if high <= low:
            raise ValueError(
                "mask segment %d f_high_hz (%r) must exceed f_low_hz (%r)"
                % (index, high, low)
            )
        out.append({"f_low_hz": low, "f_high_hz": high, "limit_dbm": limit})
    out.sort(key=lambda s: (s["f_low_hz"], s["f_high_hz"]))
    for first, second in zip(out, out[1:]):
        if second["f_low_hz"] < first["f_high_hz"] - FREQUENCY_TOLERANCE_HZ:
            raise ValueError(
                "mask segments overlap between %r Hz and %r Hz; the declared "
                "limit is ambiguous there"
                % (second["f_low_hz"], first["f_high_hz"])
            )
    return tuple(out)


def mask_limit_dbm(mask, frequency_hz):
    """Declared limit at one frequency, or None when the mask does not cover it.

    Segment bounds are inclusive. Raises ValueError on a non-positive or
    non-numeric frequency.
    """
    freq = _as_float(frequency_hz, "frequency_hz")
    if freq <= 0.0:
        raise ValueError("frequency_hz must be positive, got %r" % (freq,))
    covering = [
        seg["limit_dbm"]
        for seg in mask
        if seg["f_low_hz"] - FREQUENCY_TOLERANCE_HZ
        <= freq
        <= seg["f_high_hz"] + FREQUENCY_TOLERANCE_HZ
    ]
    if not covering:
        return None
    return max(covering)


def mask_coverage_gaps(mask, band_low_hz, band_high_hz):
    """Parts of [band_low_hz, band_high_hz] the mask leaves undeclared.

    Returns a list of (gap_low_hz, gap_high_hz) tuples, empty when the band is
    fully covered. Abutting segments leave no gap.

    Raises ValueError on a non-positive or inverted band.
    """
    low = _as_float(band_low_hz, "band_low_hz")
    high = _as_float(band_high_hz, "band_high_hz")
    if low <= 0.0:
        raise ValueError("band_low_hz must be positive, got %r" % (low,))
    if high <= low:
        raise ValueError(
            "band_high_hz (%r) must exceed band_low_hz (%r)" % (high, low)
        )
    gaps = []
    cursor = low
    for seg in mask:
        if seg["f_high_hz"] <= cursor + FREQUENCY_TOLERANCE_HZ:
            continue
        if seg["f_low_hz"] >= high - FREQUENCY_TOLERANCE_HZ:
            break
        if seg["f_low_hz"] > cursor + FREQUENCY_TOLERANCE_HZ:
            gaps.append((cursor, min(seg["f_low_hz"], high)))
        cursor = max(cursor, seg["f_high_hz"])
        if cursor >= high - FREQUENCY_TOLERANCE_HZ:
            break
    if cursor < high - FREQUENCY_TOLERANCE_HZ:
        gaps.append((cursor, high))
    return gaps


def worst_limit_in_band_dbm(mask, band_low_hz, band_high_hz):
    """Highest declared limit of any segment overlapping the band.

    Raises ValueError on an invalid band, or when no segment overlaps it at
    all (the caller must treat an uncovered band as a coverage finding, not
    as a number).
    """
    low = _as_float(band_low_hz, "band_low_hz")
    high = _as_float(band_high_hz, "band_high_hz")
    if high <= low:
        raise ValueError(
            "band_high_hz (%r) must exceed band_low_hz (%r)" % (high, low)
        )
    overlapping = [
        seg["limit_dbm"]
        for seg in mask
        if seg["f_high_hz"] > low + FREQUENCY_TOLERANCE_HZ
        and seg["f_low_hz"] < high - FREQUENCY_TOLERANCE_HZ
    ]
    if not overlapping:
        raise ValueError(
            "no declared mask segment overlaps the band %r-%r Hz" % (low, high)
        )
    return max(overlapping)


def harmonic_frequencies(carrier_hz, max_order=DEFAULT_MAX_HARMONIC_ORDER):
    """Carrier harmonics as [(order, frequency_hz)] for orders 2..max_order.

    Raises ValueError on a non-positive carrier or an order below 2.
    """
    carrier = _as_float(carrier_hz, "carrier_hz")
    if carrier <= 0.0:
        raise ValueError("carrier_hz must be positive, got %r" % (carrier,))
    if isinstance(max_order, bool) or not isinstance(max_order, int):
        raise ValueError("max_order must be an integer, got %r" % (max_order,))
    if max_order < 2:
        raise ValueError("max_order must be at least 2, got %r" % (max_order,))
    return [(order, carrier * order) for order in range(2, max_order + 1)]


def coupled_level_dbm(limit_dbm, isolation_db):
    """Level reaching the victim antenna port: declared limit less isolation.

    Raises ValueError on a negative isolation, which no passive coupling path
    between two antenna ports can produce.
    """
    limit = _as_float(limit_dbm, "limit_dbm")
    isolation = _as_float(isolation_db, "isolation_db")
    if isolation < 0.0:
        raise ValueError(
            "isolation_db must be non-negative, got %r" % (isolation,)
        )
    return limit - isolation


def compatibility_margin_db(coupled_dbm, susceptibility_dbm):
    """Margin between the victim susceptibility threshold and the coupled level."""
    coupled = _as_float(coupled_dbm, "coupled_dbm")
    threshold = _as_float(susceptibility_dbm, "susceptibility_dbm")
    return threshold - coupled


def required_isolation_db(limit_dbm, susceptibility_dbm, required_margin_db):
    """Isolation an antenna pair needs to reach the required margin.

    Raises ValueError on a negative required margin.
    """
    limit = _as_float(limit_dbm, "limit_dbm")
    threshold = _as_float(susceptibility_dbm, "susceptibility_dbm")
    margin = _as_float(required_margin_db, "required_margin_db")
    if margin < 0.0:
        raise ValueError(
            "required_margin_db must be non-negative, got %r" % (margin,)
        )
    return limit - threshold + margin


def _victim_band(victim):
    for key in ("port_id", "band_low_hz", "band_high_hz", "susceptibility_dbm"):
        if key not in victim:
            raise ValueError("victim entry missing '%s'" % key)
    low = _as_float(victim["band_low_hz"], "victim band_low_hz")
    high = _as_float(victim["band_high_hz"], "victim band_high_hz")
    if low <= 0.0:
        raise ValueError("victim band_low_hz must be positive, got %r" % (low,))
    if high <= low:
        raise ValueError(
            "victim band_high_hz (%r) must exceed band_low_hz (%r)" % (high, low)
        )
    return low, high


def evaluate_antenna_pair(
    emitter,
    victim,
    isolation_db,
    required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
):
    """Evaluate one emitter antenna-port against one victim antenna-port.

    emitter: mapping with port_id, carrier_hz, mask (normalised segments).
    victim:  mapping with port_id, band_low_hz, band_high_hz,
             susceptibility_dbm.

    Returns a result mapping whose status is one of:
      "undeclared" - the mask leaves part of the victim passband unspecified
      "compliant"  - the margin reaches the required value
      "exceeded"   - the margin falls short

    Raises ValueError on malformed input.
    """
    for key in ("port_id", "carrier_hz", "mask"):
        if key not in emitter:
            raise ValueError("emitter entry missing '%s'" % key)
    low, high = _victim_band(victim)
    mask = emitter["mask"]
    required = _as_float(required_margin_db, "required_margin_db")
    if required < 0.0:
        raise ValueError(
            "required_margin_db must be non-negative, got %r" % (required,)
        )
    threshold = _as_float(victim["susceptibility_dbm"], "susceptibility_dbm")
    isolation = _as_float(isolation_db, "isolation_db")
    if isolation < 0.0:
        raise ValueError(
            "isolation_db must be non-negative, got %r" % (isolation,)
        )
    result = {
        "emitter_port": emitter["port_id"],
        "victim_port": victim["port_id"],
        "band_low_hz": low,
        "band_high_hz": high,
        "isolation_db": isolation,
        "required_margin_db": required,
    }
    gaps = mask_coverage_gaps(mask, low, high)
    if gaps:
        result.update(
            {
                "status": "undeclared",
                "coverage_gaps_hz": gaps,
                "limit_dbm": None,
                "coupled_dbm": None,
                "margin_db": None,
                "finding": (
                    "no spurious-emission limit declared over %d span(s) of the "
                    "victim passband" % len(gaps)
                ),
            }
        )
        return result
    limit = worst_limit_in_band_dbm(mask, low, high)
    coupled = coupled_level_dbm(limit, isolation)
    margin = compatibility_margin_db(coupled, threshold)
    needed = required_isolation_db(limit, threshold, required)
    result.update(
        {
            "coverage_gaps_hz": [],
            "limit_dbm": limit,
            "coupled_dbm": coupled,
            "margin_db": margin,
            "required_isolation_db": needed,
            "isolation_shortfall_db": max(0.0, needed - isolation),
        }
    )
    if _meets(margin, required):
        result["status"] = "compliant"
        result["finding"] = None
    else:
        result["status"] = "exceeded"
        result["finding"] = (
            "coupled spurious level exceeds the victim threshold budget by "
            "%.3f dB" % (required - margin)
        )
    return result


def assess_antenna_port_spurious_emissions(
    emitters,
    victims,
    isolation_db_map,
    required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
    max_harmonic_order=DEFAULT_MAX_HARMONIC_ORDER,
):
    """Full clause 4.2.6 assessment over a set of antenna ports.

    emitters: iterable of mappings with port_id, carrier_hz and either a
              normalised 'mask' or a raw 'mask_segments' list.
    victims:  iterable of victim mappings (see evaluate_antenna_pair).
    isolation_db_map: mapping keyed by (emitter_port, victim_port).

    Returns a mapping with per-pair results, harmonic findings and an overall
    'compatible' verdict. Raises ValueError on empty sets, duplicate port
    identifiers or a missing isolation entry.
    """
    emitter_list = list(emitters or [])
    victim_list = list(victims or [])
    if not emitter_list:
        raise ValueError("at least one emitter antenna port is required")
    if not victim_list:
        raise ValueError("at least one victim antenna port is required")
    if not isinstance(isolation_db_map, dict):
        raise ValueError("isolation_db_map must be a mapping")

    prepared = []
    seen_emitters = set()
    for emitter in emitter_list:
        if "port_id" not in emitter:
            raise ValueError("emitter entry missing 'port_id'")
        port = emitter["port_id"]
        if port in seen_emitters:
            raise ValueError("duplicate emitter port_id %r" % (port,))
        seen_emitters.add(port)
        mask = emitter.get("mask")
        if mask is None:
            mask = normalize_emission_mask(emitter.get("mask_segments"))
        carrier = _as_float(emitter.get("carrier_hz"), "carrier_hz")
        if carrier <= 0.0:
            raise ValueError("carrier_hz must be positive, got %r" % (carrier,))
        prepared.append(
            {"port_id": port, "carrier_hz": carrier, "mask": mask}
        )

    seen_victims = set()
    for victim in victim_list:
        _victim_band(victim)
        port = victim["port_id"]
        if port in seen_victims:
            raise ValueError("duplicate victim port_id %r" % (port,))
        seen_victims.add(port)

    pair_results = []
    harmonic_findings = []
    for emitter in prepared:
        harmonics = harmonic_frequencies(
            emitter["carrier_hz"], max_harmonic_order
        )
        for victim in victim_list:
            key = (emitter["port_id"], victim["port_id"])
            if key not in isolation_db_map:
                raise ValueError(
                    "no antenna-to-antenna isolation declared for pair %r" % (key,)
                )
            pair_results.append(
                evaluate_antenna_pair(
                    emitter,
                    victim,
                    isolation_db_map[key],
                    required_margin_db,
                )
            )
            low, high = _victim_band(victim)
            for order, freq in harmonics:
                if low <= freq <= high and mask_limit_dbm(emitter["mask"], freq) is None:
                    harmonic_findings.append(
                        {
                            "emitter_port": emitter["port_id"],
                            "victim_port": victim["port_id"],
                            "order": order,
                            "frequency_hz": freq,
                            "finding": (
                                "harmonic order %d falls in the victim passband "
                                "with no declared limit" % order
                            ),
                        }
                    )

    undeclared = [r for r in pair_results if r["status"] == "undeclared"]
    exceeded = [r for r in pair_results if r["status"] == "exceeded"]
    return {
        "pairs": pair_results,
        "harmonic_findings": harmonic_findings,
        "undeclared_pairs": undeclared,
        "exceeded_pairs": exceeded,
        "required_margin_db": _as_float(required_margin_db, "required_margin_db"),
        "compatible": not undeclared and not exceeded and not harmonic_findings,
    }
