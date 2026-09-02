#!/usr/bin/env python3
"""ARINC 664 Part 7 AFDX network sizing and timing logic (paraphrase, summary only).

Common-knowledge summary (ARINC 664 Part 7, Avionics Full-Duplex Switched
Ethernet, proprietary ARINC standard not yet in standards-map.yaml; the
closest existing map entry is arinc-429, the data-bus family sibling):
AFDX is deterministic switched Ethernet for civil avionics. End systems
transmit virtual links (VLs) over full-duplex 100 Mbps links into a
switched network, typically dual redundant over two independent networks
(A and B). Each VL is a unidirectional logical path defined by a
bandwidth allocation gap (BAG) of 1, 2, 4, 8, 16, 32, 64, or 128 ms and
a maximum frame size between 64 and 1518 bytes. The VL bandwidth is
max_frame_bytes * 8 / bag_seconds. No VL set may oversubscribe the
100 Mbps link. The exact Part 7 configuration rules, timing budgets, and
integrity mechanisms are standard data in the current revision and are
NOT reproduced here; this module implements the sizing and timing
helpers used for a typical VL configuration table.

Worked anchors (verified by test_arinc664_afdx_logic.py):
- vl_bandwidth(4, 1518) -> 3036000.0 bps (3.036 Mbps)
- vl_bandwidth(128, 1518) -> 94875.0 bps
- link_utilization(30 x (4 ms, 1518)) -> 0.9108
- link_utilization(33 x (4 ms, 1518)) raises ValueError (100.188 Mbps > 100 Mbps)
- transmission_time(1518) -> 1.2144e-4 s (121.44 us); transmission_time(64) -> 5.12e-6 s
- jitter_slack(420.0, 500.0) -> 80.0; jitter_slack(620.0, 500.0) -> -120.0
- end_to_end_latency_us(1518, 2, 150.0) -> 542.88 us
- largest_bag_for_bandwidth(1000000.0, 1518) -> 8 ms (1.518 Mbps >= 1 Mbps)
- largest_bag_for_bandwidth(13000000.0, 1518) raises ValueError (above the 12.144 Mbps 1 ms capacity)
"""

LEGAL_BAGS = (1, 2, 4, 8, 16, 32, 64, 128)
MIN_FRAME = 64
MAX_FRAME = 1518
DEFAULT_LINK_RATE = 100_000_000.0  # 100 Mbps AFDX link


def _number(value, name):
    """Return float(value) for real numbers; raise ValueError otherwise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    return float(value)


def _require_int(value, name, lo, hi):
    """Return value when it is an int in [lo, hi]; raise ValueError otherwise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if not (lo <= value <= hi):
        raise ValueError("%s %d out of range [%d, %d]" % (name, value, lo, hi))
    return value


def _require_bag(bag_ms):
    """Validate a BAG: an integer power of two from 1 to 128 ms."""
    bag_ms = _require_int(bag_ms, "bag_ms", 1, 128)
    if bag_ms not in LEGAL_BAGS:
        raise ValueError(
            "bag_ms %d is not a legal BAG (1, 2, 4, 8, 16, 32, 64, or 128 ms)"
            % (bag_ms,)
        )
    return bag_ms


def _require_frame(max_frame_bytes):
    """Validate an AFDX maximum frame size: 64-1518 bytes."""
    return _require_int(max_frame_bytes, "max_frame_bytes", MIN_FRAME, MAX_FRAME)


def vl_bandwidth(bag_ms, max_frame_bytes):
    """Bandwidth of one virtual link in bits per second.

    rate = max_frame_bytes * 8 / (bag_ms / 1000). The BAG must be a
    power of two from 1 to 128 ms and the frame size must be 64-1518
    bytes; ValueError is raised otherwise. Worked anchors: (4 ms, 1518)
    -> 3036000.0 bps, (128 ms, 1518) -> 94875.0 bps.
    """
    bag_ms = _require_bag(bag_ms)
    frame = _require_frame(max_frame_bytes)
    return frame * 8 / (bag_ms / 1000.0)


def link_utilization(vl_specs, link_rate_bps=DEFAULT_LINK_RATE):
    """Fraction of the link capacity consumed by a set of virtual links.

    vl_specs is an iterable of (bag_ms, max_frame_bytes) pairs, one per
    virtual link. The sum of VL bandwidths must not exceed the link rate
    (100 Mbps default); an oversubscribed set raises ValueError. Returns
    the utilization fraction. Worked anchor: 30 VLs of (4 ms, 1518) ->
    0.9108; 33 such VLs raise ValueError (100.188 Mbps does not fit).
    """
    link_rate = _number(link_rate_bps, "link_rate_bps")
    if link_rate <= 0.0:
        raise ValueError("link_rate_bps must be positive, got %r" % (link_rate,))
    total = 0.0
    for spec in vl_specs:
        try:
            bag_ms, max_frame_bytes = spec
        except (TypeError, ValueError):
            raise ValueError(
                "vl_specs entry %r is not a (bag_ms, max_frame_bytes) pair" % (spec,)
            )
        total += vl_bandwidth(bag_ms, max_frame_bytes)
    if total > link_rate:
        raise ValueError(
            "virtual link set needs %.0f bps but the link carries %.0f bps "
            "(oversubscribed)" % (total, link_rate)
        )
    return total / link_rate


def transmission_time(frame_bytes, link_rate_bps=DEFAULT_LINK_RATE):
    """Serialization time of one frame on the link, in seconds.

    t = frame_bytes * 8 / link_rate. Worked anchors: 1518 bytes at
    100 Mbps -> 1.2144e-4 s (121.44 us); 64 bytes -> 5.12e-6 s.
    """
    frame = _require_frame(frame_bytes)
    link_rate = _number(link_rate_bps, "link_rate_bps")
    if link_rate <= 0.0:
        raise ValueError("link_rate_bps must be positive, got %r" % (link_rate,))
    return frame * 8 / link_rate


def jitter_slack(measured_max_jitter_us, jitter_budget_us):
    """Slack between the measured maximum jitter and the budget, in us.

    A positive slack is compliant; a negative slack is a violation.
    Worked anchors: (420.0, 500.0) -> 80.0; (620.0, 500.0) -> -120.0.
    """
    measured = _number(measured_max_jitter_us, "measured_max_jitter_us")
    budget = _number(jitter_budget_us, "jitter_budget_us")
    if measured < 0.0:
        raise ValueError(
            "measured_max_jitter_us must be non-negative, got %r" % (measured,)
        )
    if budget <= 0.0:
        raise ValueError("jitter_budget_us must be positive, got %r" % (budget,))
    return budget - measured


def end_to_end_latency_us(frame_bytes, switch_count, switch_delay_us,
                          link_rate_bps=DEFAULT_LINK_RATE):
    """Worst-case one-way latency of a frame, in us.

    The frame is serialized by the transmitting end system, forwarded
    store-and-forward by each switch, and serialized again into the
    receiving end system: total = 2 * transmission_time + switch_count *
    switch_delay. Worked anchor: 1518 bytes through 2 switches at 150 us
    each -> 2 * 121.44 + 300 = 542.88 us.
    """
    tx_us = transmission_time(frame_bytes, link_rate_bps) * 1e6
    switch_count = _require_int(switch_count, "switch_count", 0, 100)
    delay = _number(switch_delay_us, "switch_delay_us")
    if delay < 0.0:
        raise ValueError("switch_delay_us must be non-negative, got %r" % (delay,))
    return 2 * tx_us + switch_count * delay


def largest_bag_for_bandwidth(bandwidth_bps, max_frame_bytes):
    """Largest legal BAG (ms) whose VL bandwidth still meets the requirement.

    Returns the largest BAG in (1, 2, 4, 8, 16, 32, 64, 128) ms such that
    vl_bandwidth(bag, max_frame_bytes) >= bandwidth_bps, conserving link
    capacity; raises ValueError when even the 1 ms BAG is insufficient
    (the frame size caps the VL at max_frame_bytes * 8000 bps). Worked
    anchors: (1e6, 1518) -> 8 ms; (12e6, 1518) -> 1 ms; (13e6, 1518)
    raises ValueError.
    """
    needed = _number(bandwidth_bps, "bandwidth_bps")
    frame = _require_frame(max_frame_bytes)
    if needed <= 0.0:
        raise ValueError("bandwidth_bps must be positive, got %r" % (needed,))
    max_rate = vl_bandwidth(1, frame)
    if needed > max_rate:
        raise ValueError(
            "bandwidth %.0f bps exceeds the %.0f bps capacity of a 1 ms BAG "
            "at %d bytes" % (needed, max_rate, frame)
        )
    chosen = LEGAL_BAGS[0]
    for bag in LEGAL_BAGS:
        if vl_bandwidth(bag, frame) >= needed:
            chosen = bag
    return chosen
