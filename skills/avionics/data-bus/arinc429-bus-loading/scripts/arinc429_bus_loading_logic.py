"""ARINC 429 transmit bus loading budget (pure stdlib, deterministic).

Every transmitted ARINC 429 word occupies 36 bit-times on the bus, 32
data bits plus the 4-bit gap between words, regardless of label
content. A label rate schedule therefore sums into a total word rate,
the word rate times 36 bits per word gives the bus load in bits per
second, and the load over the link rate gives the percent utilization
of the 100 kbps (or 12.5 kbps) bus. This module budgets that schedule:
it totals the per-label rates, computes the load and utilization,
compares the schedule against the word-per-second capacity (about
2778 words per second at 100 kbps) and reports the verdict and the
headroom against the common 80 percent design guideline.

The word construction, parity and coding concerns of the word format
belong to the sibling arinc429-protocol leaf; this module only sums a
schedule and prices its bus occupancy.
"""

BITS_PER_WORD = 36.0          # 32 data bits plus the 4-bit gap
RATE_100_KBPS = 100000.0      # high-speed ARINC 429 link rate
RATE_12_5_KBPS = 12500.0      # low-speed ARINC 429 link rate
DESIGN_GUIDELINE_PCT = 80.0   # common headroom design guideline


def _rate_values(label_rates):
    """Return the rates as a list of floats from a list or a dict.

    Accepts either a list of label rates in labels per second or a
    dict mapping a label (str or int) to its rate. Raises ValueError
    on an empty schedule or a negative rate.
    """
    values = list(label_rates.values()) if isinstance(label_rates, dict) else list(label_rates)
    if len(values) == 0:
        raise ValueError("the label rate schedule is empty")
    for rate in values:
        if rate < 0:
            raise ValueError("label rates must be non-negative, got %r" % (rate,))
    return [float(rate) for rate in values]


def total_word_rate(label_rates):
    """Sum the per-label rates into the total words per second.

    label_rates is a list of rates in labels per second or a dict
    {label: rate}. Raises ValueError on an empty schedule or any
    negative rate.
    """
    rates = _rate_values(label_rates)
    return sum(rates)


def bus_load_bps(total_words_per_s, bits_per_word=BITS_PER_WORD):
    """Convert the total word rate into a bus load in bits per second.

    Each ARINC 429 word occupies bits_per_word bit-times, 36 by
    default. Raises ValueError when the word rate is negative or the
    bits per word is not positive.
    """
    if total_words_per_s < 0:
        raise ValueError("total words per second must be non-negative, got %r" % (total_words_per_s,))
    if bits_per_word <= 0:
        raise ValueError("bits per word must be positive, got %r" % (bits_per_word,))
    return float(total_words_per_s) * float(bits_per_word)


def percent_utilization(bus_load_bps, link_rate_bps=RATE_100_KBPS):
    """Percent of the link rate occupied by the bus load.

    Returns load / link * 100. Raises ValueError when the load is
    negative or the link rate is not positive.
    """
    if bus_load_bps < 0:
        raise ValueError("bus load must be non-negative, got %r" % (bus_load_bps,))
    if link_rate_bps <= 0:
        raise ValueError("link rate must be positive, got %r" % (link_rate_bps,))
    return float(bus_load_bps) / float(link_rate_bps) * 100.0


def word_capacity(link_rate_bps=RATE_100_KBPS, bits_per_word=BITS_PER_WORD):
    """Word-per-second capacity of the link, link rate over bits per word.

    About 2777.8 words per second at 100 kbps and 347.2 words per
    second at 12.5 kbps with the default 36 bit-times per word.
    Raises ValueError when the link rate or bits per word is not
    positive.
    """
    if link_rate_bps <= 0:
        raise ValueError("link rate must be positive, got %r" % (link_rate_bps,))
    if bits_per_word <= 0:
        raise ValueError("bits per word must be positive, got %r" % (bits_per_word,))
    return float(link_rate_bps) / float(bits_per_word)


def capacity_verdict(total_words_per_s, link_rate_bps=RATE_100_KBPS):
    """Verdict dict for a total word rate against the link capacity.

    Returns {capacity_wps, utilization_pct, verdict, headroom_pct}
    with verdict OVER when the utilization exceeds 100 percent and
    FITS otherwise, and headroom_pct the unused margin against the
    80 percent design guideline (0 when at or beyond the guideline).
    Raises ValueError when the word rate is negative or the link
    rate is not positive.
    """
    if total_words_per_s < 0:
        raise ValueError("total words per second must be non-negative, got %r" % (total_words_per_s,))
    if link_rate_bps <= 0:
        raise ValueError("link rate must be positive, got %r" % (link_rate_bps,))
    capacity_wps = word_capacity(link_rate_bps)
    utilization_pct = percent_utilization(bus_load_bps(total_words_per_s), link_rate_bps)
    verdict = "OVER" if utilization_pct > 100.0 else "FITS"
    headroom_pct = max(0.0, DESIGN_GUIDELINE_PCT - utilization_pct)
    return {
        "capacity_wps": capacity_wps,
        "utilization_pct": utilization_pct,
        "verdict": verdict,
        "headroom_pct": headroom_pct,
    }


def bus_loading_summary(label_rates, link_rate_bps=RATE_100_KBPS):
    """Full bus loading budget for a label rate schedule.

    label_rates is a list of rates in labels per second or a dict
    {label: rate}. Returns {total_words_per_s, load_bps,
    utilization_pct, capacity_wps, verdict, headroom_pct}. Raises
    ValueError on an empty schedule, a negative rate, or a link
    rate that is not positive.
    """
    rates = _rate_values(label_rates)
    if link_rate_bps <= 0:
        raise ValueError("link rate must be positive, got %r" % (link_rate_bps,))
    total = sum(rates)
    load_bps = bus_load_bps(total)
    utilization_pct = percent_utilization(load_bps, link_rate_bps)
    capacity_wps = word_capacity(link_rate_bps)
    verdict = "OVER" if utilization_pct > 100.0 else "FITS"
    headroom_pct = max(0.0, DESIGN_GUIDELINE_PCT - utilization_pct)
    return {
        "total_words_per_s": total,
        "load_bps": load_bps,
        "utilization_pct": utilization_pct,
        "capacity_wps": capacity_wps,
        "verdict": verdict,
        "headroom_pct": headroom_pct,
    }
