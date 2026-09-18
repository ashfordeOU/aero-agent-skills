"""Simultaneous support of telemetry sources generating at differing rates.

Anchor: ECSS-E-ST-50C clause 5.5.6 (the telemetry system carries data from
sources of different rates at the same time, each at its own rate).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each source: packet size, generation period, maximum latency.
2. Compute per-source demand and the offered load grossed up by the
   transport overhead factor, and compare it with the downlink capacity.
3. Apportion the slots of one downlink cycle in proportion to demand by
   largest remainder, so the slots sum exactly to the cycle.
4. Report any source apportioned zero slots: it is not carried at all.
5. Derive each source's service interval, end-to-end latency and buffer
   depth from the apportionment, and screen the latency against its limit.
"""

import math

__all__ = [
    "RATE_TOLERANCE_BPS",
    "LATENCY_TOLERANCE_S",
    "validate_source",
    "validate_source_set",
    "source_demand_bps",
    "offered_load_bps",
    "fits_capacity",
    "apportion_slots",
    "service_interval_s",
    "end_to_end_latency_s",
    "buffer_depth_bits",
    "demand_spread",
    "assess_rate_coexistence",
]

# Capacity and latency comparisons are sums against declared bounds: an exact
# equality can land a few ULPs on the wrong side. Absorb the representation
# error here instead of relaxing the engineering limit.
RATE_TOLERANCE_BPS = 1e-9
LATENCY_TOLERANCE_S = 1e-9


def _require_text(value, label):
    """Return a non-empty stripped string or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _require_positive(value, label):
    """Return a positive finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def validate_source(source):
    """Return a normalised telemetry source record."""
    if not isinstance(source, dict):
        raise ValueError("source must be a mapping, got %r" % (source,))
    for key in ("name", "packet_bits", "generation_period_s", "max_latency_s"):
        if key not in source:
            raise ValueError("source missing required key '%s'" % key)
    packet_bits = source["packet_bits"]
    if not isinstance(packet_bits, int) or isinstance(packet_bits, bool):
        raise ValueError("packet_bits must be an integer, got %r" % (packet_bits,))
    if packet_bits <= 0:
        raise ValueError("packet_bits must be positive, got %d" % packet_bits)
    return {
        "name": _require_text(source["name"], "name"),
        "packet_bits": packet_bits,
        "generation_period_s": _require_positive(
            source["generation_period_s"], "generation_period_s"
        ),
        "max_latency_s": _require_positive(source["max_latency_s"], "max_latency_s"),
    }


def validate_source_set(sources):
    """Return the validated source list; names must be unique and non-empty."""
    if isinstance(sources, dict) or not isinstance(sources, (list, tuple)):
        raise ValueError("sources must be a sequence of source mappings")
    if not sources:
        raise ValueError("the source set must not be empty")
    records = [validate_source(item) for item in sources]
    seen = set()
    for record in records:
        if record["name"] in seen:
            raise ValueError("duplicate source name '%s'" % record["name"])
        seen.add(record["name"])
    return records


def source_demand_bps(source):
    """Return the payload rate one source offers, in bit/s."""
    record = validate_source(source)
    return record["packet_bits"] / record["generation_period_s"]


def offered_load_bps(sources, overhead_factor=1.0):
    """Return the overhead-grossed offered load of the whole source set."""
    records = validate_source_set(sources)
    factor = _require_positive(overhead_factor, "overhead_factor")
    if factor < 1.0:
        raise ValueError("overhead_factor must be at least 1.0, got %g" % factor)
    payload = math.fsum(
        r["packet_bits"] / r["generation_period_s"] for r in records
    )
    return payload * factor


def fits_capacity(offered_bps, capacity_bps):
    """Return True when the offered load fits the downlink capacity."""
    offered = _require_positive(offered_bps, "offered_bps")
    capacity = _require_positive(capacity_bps, "capacity_bps")
    if math.isclose(offered, capacity, rel_tol=0.0, abs_tol=RATE_TOLERANCE_BPS):
        return True
    return offered < capacity


def apportion_slots(sources, slots_per_cycle):
    """Apportion the cycle's slots in proportion to demand, by largest remainder."""
    records = validate_source_set(sources)
    if not isinstance(slots_per_cycle, int) or isinstance(slots_per_cycle, bool):
        raise ValueError("slots_per_cycle must be an integer")
    if slots_per_cycle < len(records):
        raise ValueError(
            "slots_per_cycle %d cannot serve %d sources; the cycle needs at least one "
            "slot per source" % (slots_per_cycle, len(records))
        )
    demands = dict(
        (r["name"], r["packet_bits"] / r["generation_period_s"]) for r in records
    )
    total = math.fsum(demands.values())
    exact = dict((name, demands[name] / total * slots_per_cycle) for name in demands)
    floors = dict((name, int(math.floor(exact[name]))) for name in exact)
    assigned = sum(floors.values())
    remainder = slots_per_cycle - assigned
    order = sorted(
        exact, key=lambda name: (-(exact[name] - floors[name]), name)
    )
    allocation = dict(floors)
    index = 0
    while remainder > 0:
        allocation[order[index % len(order)]] += 1
        remainder -= 1
        index += 1
    return allocation


def service_interval_s(allocated_slots, slots_per_cycle, cycle_duration_s):
    """Return the mean interval between two services of one source, in seconds."""
    if not isinstance(allocated_slots, int) or isinstance(allocated_slots, bool):
        raise ValueError("allocated_slots must be an integer")
    if not isinstance(slots_per_cycle, int) or isinstance(slots_per_cycle, bool):
        raise ValueError("slots_per_cycle must be an integer")
    if slots_per_cycle <= 0:
        raise ValueError("slots_per_cycle must be positive, got %d" % slots_per_cycle)
    if allocated_slots <= 0:
        raise ValueError(
            "a source apportioned %d slots is never served; it is not carried"
            % allocated_slots
        )
    if allocated_slots > slots_per_cycle:
        raise ValueError(
            "allocated_slots %d exceeds the %d slots in the cycle"
            % (allocated_slots, slots_per_cycle)
        )
    duration = _require_positive(cycle_duration_s, "cycle_duration_s")
    return duration / allocated_slots


def end_to_end_latency_s(generation_period_s, interval_s):
    """Return the age bound of the oldest datum when a source is finally served."""
    period = _require_positive(generation_period_s, "generation_period_s")
    interval = _require_positive(interval_s, "interval_s")
    return period + interval


def buffer_depth_bits(source, interval_s):
    """Return the buffer a source needs to ride out one service interval."""
    record = validate_source(source)
    interval = _require_positive(interval_s, "interval_s")
    packets = int(math.ceil(interval / record["generation_period_s"]))
    if packets < 1:
        packets = 1
    return packets * record["packet_bits"]


def demand_spread(sources):
    """Return the ratio of the fastest to the slowest source demand."""
    records = validate_source_set(sources)
    demands = [r["packet_bits"] / r["generation_period_s"] for r in records]
    return max(demands) / min(demands)


def assess_rate_coexistence(spec):
    """Run the full clause 5.5.6 mixed-rate coexistence assessment.

    spec keys: sources, capacity_bps, slots_per_cycle, cycle_duration_s,
    optional overhead_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("sources", "capacity_bps", "slots_per_cycle", "cycle_duration_s"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    records = validate_source_set(spec["sources"])
    overhead = spec.get("overhead_factor", 1.0)
    capacity = _require_positive(spec["capacity_bps"], "capacity_bps")
    cycle_duration = _require_positive(spec["cycle_duration_s"], "cycle_duration_s")
    slots = spec["slots_per_cycle"]

    offered = offered_load_bps(records, overhead)
    within = fits_capacity(offered, capacity)
    allocation = apportion_slots(records, slots)
    spread = demand_spread(records)

    findings = []
    if not within:
        findings.append(
            "offered load %.6g bit/s exceeds the downlink capacity %.6g bit/s; the "
            "sources cannot be carried simultaneously" % (offered, capacity)
        )

    per_source = {}
    for record in records:
        name = record["name"]
        allocated = allocation[name]
        if allocated <= 0:
            findings.append(
                "source '%s' is apportioned no slot in the cycle; it is served at no "
                "rate at all" % name
            )
            per_source[name] = {
                "slots": allocated,
                "service_interval_s": None,
                "latency_s": None,
                "buffer_bits": None,
                "meets_latency": False,
            }
            continue
        interval = service_interval_s(allocated, slots, cycle_duration)
        latency = end_to_end_latency_s(record["generation_period_s"], interval)
        buffer_bits = buffer_depth_bits(record, interval)
        meets = latency < record["max_latency_s"] or math.isclose(
            latency, record["max_latency_s"], rel_tol=0.0, abs_tol=LATENCY_TOLERANCE_S
        )
        if not meets:
            findings.append(
                "source '%s' is served every %.6g s, giving %.6g s latency against a "
                "%.6g s limit" % (name, interval, latency, record["max_latency_s"])
            )
        per_source[name] = {
            "slots": allocated,
            "service_interval_s": interval,
            "latency_s": latency,
            "buffer_bits": buffer_bits,
            "meets_latency": meets,
        }

    return {
        "offered_load_bps": offered,
        "capacity_bps": capacity,
        "within_capacity": within,
        "allocation": allocation,
        "per_source": per_source,
        "demand_spread": spread,
        "compliant": not findings,
        "findings": findings,
    }
