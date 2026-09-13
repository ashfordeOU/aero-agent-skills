#!/usr/bin/env python3
"""Critical intermodulation products -- ECSS-E-ST-20C clause 7.4.3.

Deterministic, offline, stdlib-only logic that enumerates the
intermodulation products of a transmit carrier-plan and reports which of
them land inside a sensitive receive-band or a protected-band.

Model
-----
A product is an integer coefficient per carrier, m = (m1 .. mn):

    f_product = sum_i m_i * f_i            (Hz, must be strictly positive)
    order     = sum_i |m_i|                (drives product amplitude)
    signed    = sum_i m_i                  (1 -> near-carrier product)

A coefficient set and its sign-flipped mirror describe the same physical
line. The pair is resolved on the sign of the weighted sum: the member with
a strictly positive sum is the physical line, its mirror is dropped, and a
zero sum is a direct-current beat rather than a spectral line.
"""

import math
from math import comb

# Product frequencies are coefficient-weighted sums of large float
# frequencies, so a line that physically sits exactly on a band edge can
# land a few ULPs outside it. This tolerance absorbs that representation
# error only -- it never widens the band (1 mHz against MHz-wide bands).
FREQ_TOL_HZ = 1e-3

MIN_CARRIERS = 2
MAX_CARRIERS = 8
MIN_ORDER = 3
MAX_SUPPORTED_ORDER = 15
# Upper bound on the lattice points the enumeration may visit. A request
# above it is refused, never truncated: a short search under-reports
# critical products, which reads as a clean result.
MAX_SEARCH_POINTS = 2000000
BAND_KINDS = ("receive", "protected")


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(value, label):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (label, value))
    return float(value)


def _require_positive(value, label):
    number = _require_number(value, label)
    if number <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return number


def validate_carrier_frequencies(frequencies_hz):
    """Normalise the transmit carrier frequencies, raising on bad input."""
    if not isinstance(frequencies_hz, (list, tuple)):
        raise ValueError("carrier frequencies must be a list or tuple")
    if not (MIN_CARRIERS <= len(frequencies_hz) <= MAX_CARRIERS):
        raise ValueError(
            "carrier count must be between %d and %d, got %d"
            % (MIN_CARRIERS, MAX_CARRIERS, len(frequencies_hz))
        )
    clean = [
        _require_positive(f, "carrier_frequencies_hz[%d]" % i)
        for i, f in enumerate(frequencies_hz)
    ]
    if len(set(clean)) != len(clean):
        raise ValueError("carrier frequencies must be distinct")
    return clean


def validate_victim_band(band):
    """Normalise one victim-band record, raising ValueError on bad input."""
    if not isinstance(band, dict):
        raise ValueError("victim band must be a mapping, got %s" % (type(band).__name__,))
    name = band.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("victim band needs a non-empty 'name'")
    kind = band.get("kind", "receive")
    if kind not in BAND_KINDS:
        raise ValueError(
            "%s.kind must be one of %s, got %r" % (name, "|".join(BAND_KINDS), kind)
        )
    f_low = _require_positive(band.get("f_low_hz"), "%s.f_low_hz" % name)
    f_high = _require_number(band.get("f_high_hz"), "%s.f_high_hz" % name)
    if f_high <= f_low:
        raise ValueError(
            "%s band edges inverted: f_high_hz %r must exceed f_low_hz %r"
            % (name, f_high, f_low)
        )
    guard = _require_number(band.get("guard_hz", 0.0), "%s.guard_hz" % name)
    if guard < 0.0:
        raise ValueError("%s.guard_hz must be >= 0, got %r" % (name, guard))
    return {
        "name": name,
        "kind": kind,
        "f_low_hz": f_low,
        "f_high_hz": f_high,
        "guard_hz": guard,
        "widened_low_hz": f_low - guard,
        "widened_high_hz": f_high + guard,
    }


def intermodulation_order(coefficients):
    """Sum of the absolute coefficients; the amplitude driver."""
    coeffs = _validated_coefficients(coefficients)
    return sum(abs(c) for c in coeffs)


def signed_coefficient_sum(coefficients):
    """Signed sum; a value of 1 marks a near-carrier product."""
    return sum(_validated_coefficients(coefficients))


def _validated_coefficients(coefficients):
    if not isinstance(coefficients, (list, tuple)) or not coefficients:
        raise ValueError("coefficients must be a non-empty list or tuple")
    for index, coeff in enumerate(coefficients):
        if isinstance(coeff, bool) or not isinstance(coeff, int):
            raise ValueError(
                "coefficients[%d] must be an int, got %r" % (index, coeff)
            )
    return list(coefficients)


def product_frequency_hz(carrier_frequencies_hz, coefficients):
    """Coefficient-weighted sum of the carrier frequencies."""
    coeffs = _validated_coefficients(coefficients)
    if len(coeffs) != len(carrier_frequencies_hz):
        raise ValueError(
            "coefficient count %d does not match carrier count %d"
            % (len(coeffs), len(carrier_frequencies_hz))
        )
    return sum(c * f for c, f in zip(coeffs, carrier_frequencies_hz))


def mirror_coefficients(coefficients):
    """The sign-flipped partner, which describes the same physical line."""
    return tuple(-c for c in _validated_coefficients(coefficients))


def is_physical_product(carrier_frequencies_hz, coefficients):
    """True for the member of the mirror pair that has a real frequency.

    The mirror of a product has the negated frequency, so exactly one of the
    pair survives this test; a zero-frequency (direct-current) set survives
    neither.
    """
    return product_frequency_hz(carrier_frequencies_hz, coefficients) > FREQ_TOL_HZ


def lattice_point_count(carrier_count, max_order):
    """Integer coefficient sets with absolute-coefficient sum <= max_order.

    Closed form for the number of lattice points inside the L1 ball; used to
    refuse an enumeration that would explode, before any work is done.
    """
    if not isinstance(carrier_count, int) or isinstance(carrier_count, bool):
        raise ValueError("carrier_count must be an int, got %r" % (carrier_count,))
    if not isinstance(max_order, int) or isinstance(max_order, bool):
        raise ValueError("max_order must be an int, got %r" % (max_order,))
    if carrier_count < 1 or max_order < 0:
        raise ValueError(
            "carrier_count must be >= 1 and max_order >= 0, got %r and %r"
            % (carrier_count, max_order)
        )
    return sum(
        2 ** j * comb(carrier_count, j) * comb(max_order, j)
        for j in range(0, min(carrier_count, max_order) + 1)
    )


def enumerate_coefficient_sets(
    carrier_count, max_order, min_order=MIN_ORDER, odd_order_only=True
):
    """Every coefficient set with order in [min_order, max_order].

    Both members of each sign-flipped pair are returned; the pair is resolved
    later, on the sign of the product frequency, because which member is the
    physical line depends on the carrier frequencies and not on the
    coefficients alone.
    """
    if not isinstance(carrier_count, int) or isinstance(carrier_count, bool):
        raise ValueError("carrier_count must be an int, got %r" % (carrier_count,))
    if not (MIN_CARRIERS <= carrier_count <= MAX_CARRIERS):
        raise ValueError(
            "carrier_count must be between %d and %d, got %d"
            % (MIN_CARRIERS, MAX_CARRIERS, carrier_count)
        )
    for label, value in (("max_order", max_order), ("min_order", min_order)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an int, got %r" % (label, value))
    if min_order < MIN_ORDER:
        raise ValueError(
            "min_order must be >= %d (lower orders are not products), got %d"
            % (MIN_ORDER, min_order)
        )
    if max_order > MAX_SUPPORTED_ORDER:
        raise ValueError(
            "max_order above %d is not supported, got %d"
            % (MAX_SUPPORTED_ORDER, max_order)
        )
    if max_order < min_order:
        raise ValueError(
            "max_order %d is below min_order %d" % (max_order, min_order)
        )
    points = lattice_point_count(carrier_count, max_order)
    if points > MAX_SEARCH_POINTS:
        raise ValueError(
            "screening %d carriers to order %d visits %d coefficient sets, above "
            "the %d bound; reduce carrier_count or max_order rather than "
            "truncating the search"
            % (carrier_count, max_order, points, MAX_SEARCH_POINTS)
        )
    results = []

    def walk(prefix, budget):
        position = len(prefix)
        if position == carrier_count:
            order = sum(abs(c) for c in prefix)
            if order < min_order:
                return
            if odd_order_only and order % 2 == 0:
                return
            results.append(tuple(prefix))
            return
        for coeff in range(-budget, budget + 1):
            walk(prefix + [coeff], budget - abs(coeff))

    walk([], max_order)
    results.sort(key=lambda c: (sum(abs(x) for x in c), c))
    return results


def frequency_margin_hz(frequency_hz, band):
    """Distance to the nearest widened band edge; 0.0 when inside the band."""
    record = band if "widened_low_hz" in band else validate_victim_band(band)
    freq = _require_number(frequency_hz, "frequency_hz")
    low = record["widened_low_hz"]
    high = record["widened_high_hz"]
    if freq < low - FREQ_TOL_HZ:
        return low - freq
    if freq > high + FREQ_TOL_HZ:
        return freq - high
    return 0.0


def band_hit(frequency_hz, band):
    """True when the product lands inside the guard-band-widened victim band."""
    record = band if "widened_low_hz" in band else validate_victim_band(band)
    freq = _require_number(frequency_hz, "frequency_hz")
    return (
        freq >= record["widened_low_hz"] - FREQ_TOL_HZ
        and freq <= record["widened_high_hz"] + FREQ_TOL_HZ
    )


def screen_intermodulation_products(
    carrier_frequencies_hz, victim_bands, max_order, min_order=MIN_ORDER,
    odd_order_only=True,
):
    """Every (product, victim band) hit, ranked by order then margin."""
    carriers = validate_carrier_frequencies(carrier_frequencies_hz)
    bands = [validate_victim_band(b) for b in victim_bands]
    if not bands:
        raise ValueError("victim_bands must contain at least one band")
    names = [b["name"] for b in bands]
    if len(set(names)) != len(names):
        raise ValueError("victim band names must be unique")
    sets = enumerate_coefficient_sets(
        len(carriers), max_order, min_order=min_order, odd_order_only=odd_order_only
    )
    hits = []
    for coeffs in sets:
        freq = product_frequency_hz(carriers, coeffs)
        if freq <= FREQ_TOL_HZ:
            continue  # the mirror of an enumerated set, or a direct-current beat
        for band in bands:
            if band_hit(freq, band):
                hits.append(
                    {
                        "coefficients": coeffs,
                        "order": sum(abs(c) for c in coeffs),
                        "signed_sum": sum(coeffs),
                        "frequency_hz": freq,
                        "band": band["name"],
                        "band_kind": band["kind"],
                        "margin_hz": frequency_margin_hz(freq, band),
                        "near_carrier": abs(sum(coeffs)) == 1,
                    }
                )
    hits.sort(key=lambda h: (h["order"], h["margin_hz"], h["frequency_hz"], h["band"]))
    return hits


def lowest_critical_order(hits, band_name=None):
    """Lowest intermodulation-order that hits any band, or a named band."""
    selected = [h for h in hits if band_name is None or h["band"] == band_name]
    if not selected:
        return None
    return min(h["order"] for h in selected)


def summarize_screening(carrier_frequencies_hz, victim_bands, max_order, **kwargs):
    """Per-band critical-product summary plus the system-level driver order."""
    hits = screen_intermodulation_products(
        carrier_frequencies_hz, victim_bands, max_order, **kwargs
    )
    bands = [validate_victim_band(b) for b in victim_bands]
    per_band = []
    for band in bands:
        band_hits = [h for h in hits if h["band"] == band["name"]]
        per_band.append(
            {
                "name": band["name"],
                "kind": band["kind"],
                "hit_count": len(band_hits),
                "lowest_order": lowest_critical_order(band_hits),
                "critical_products": band_hits[:5],
                "critical": bool(band_hits),
            }
        )
    return {
        "carrier_count": len(validate_carrier_frequencies(carrier_frequencies_hz)),
        "max_order_screened": max_order,
        "hits": hits,
        "bands": per_band,
        "lowest_critical_order": lowest_critical_order(hits),
        "critical": bool(hits),
    }
