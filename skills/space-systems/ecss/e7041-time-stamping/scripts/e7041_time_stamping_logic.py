"""Storage time-stamping of packets held in an on-board packet store.

Anchor: ECSS-E-ST-70-41C clause 6.15.3.2 (paraphrased into an
implementable procedure; no standard text is reproduced).

The clause carries a single requirement, and everything here follows
from it: every packet a packet store holds is held together with the
on-board time at which it was stored. That storage time, not any time
inside the packet, is what a time-window retrieval selects on.

Why the distinction matters. A packet usually carries its own
generation time in its data field header, and generation time is not
storage time. A report generated during a link outage and stored when
the store was re-enabled has two different times, minutes apart. A
retrieval asking for a window is asking which packets the store took in
during it, so answering from generation time returns a different set --
sometimes an empty one for a window the ground can see was busy.

Encoding. The storage time is written in the on-board CUC form: a
coarse count of whole seconds since the agency epoch and a fine count
of fractional units, the fine field being a chosen number of octets.
The resolution is therefore 2^(-8n) seconds for n fine octets, and the
stamp is the time truncated down to that resolution, never rounded up:
a stamp must not claim a packet was stored later than it was.

Ordering. A store takes packets in arrival order, so the stamps it
writes are non-decreasing. Two packets stored inside the same
resolution step legitimately share a stamp. A stamp that goes backwards
does not: it means the on-board time was stepped by a correction while
the store was filling, and a time-window retrieval over that region
will silently return the wrong set until the discontinuity is known
about.

Stdlib only, offline, deterministic.
"""

COARSE_OCTETS = 4
COARSE_MAX = 2 ** (8 * COARSE_OCTETS) - 1
MIN_FINE_OCTETS = 1
MAX_FINE_OCTETS = 3

FINDING_STAMP_WENT_BACKWARDS = "storage-time-stamp-went-backwards"
FINDING_STAMP_REPEATED = "storage-time-stamp-repeated-inside-one-resolution-step"


def _fine_octets(value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("fine_octets must be an integer, got %r" % (value,))
    if value < MIN_FINE_OCTETS or value > MAX_FINE_OCTETS:
        raise ValueError(
            "fine_octets must be in [%d, %d], got %d"
            % (MIN_FINE_OCTETS, MAX_FINE_OCTETS, value)
        )
    return value


def _seconds(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("%s must be a finite time, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be before the epoch, got %r" % (label, value))
    return float(value)


def fine_units_per_second(fine_octets):
    """How many fine units make one second at this fine-field width."""
    return 2 ** (8 * _fine_octets(fine_octets))


def stamp_resolution_s(fine_octets):
    """Smallest time difference this fine-field width can represent."""
    return 1.0 / fine_units_per_second(fine_octets)


def encode_storage_time(seconds, fine_octets):
    """Encode an on-board time as a (coarse, fine) storage time stamp."""
    value = _seconds("storage time", seconds)
    units = fine_units_per_second(fine_octets)
    total = int(value * units)
    # Truncate downwards: the stamp must never claim a later moment than
    # the one the packet was actually stored at. int() already truncates
    # towards zero, and the time is non-negative, but a product that
    # lands a hair above the true value is pulled back here.
    if total / float(units) > value:
        total -= 1
    coarse, fine = divmod(total, units)
    if coarse > COARSE_MAX:
        raise ValueError(
            "storage time %r overflows the %d-octet coarse field"
            % (seconds, COARSE_OCTETS)
        )
    return coarse, fine


def decode_storage_time(coarse, fine, fine_octets):
    """Decode a (coarse, fine) storage time stamp back into seconds."""
    units = fine_units_per_second(fine_octets)
    if not isinstance(coarse, int) or isinstance(coarse, bool):
        raise ValueError("coarse must be an integer, got %r" % (coarse,))
    if not isinstance(fine, int) or isinstance(fine, bool):
        raise ValueError("fine must be an integer, got %r" % (fine,))
    if coarse < 0 or coarse > COARSE_MAX:
        raise ValueError("coarse must be in [0, %d], got %d" % (COARSE_MAX, coarse))
    if fine < 0 or fine >= units:
        raise ValueError("fine must be in [0, %d], got %d" % (units - 1, fine))
    return coarse + fine / float(units)


def quantisation_error_s(seconds, fine_octets):
    """How much earlier the stamp reads than the time it was taken from."""
    value = _seconds("storage time", seconds)
    coarse, fine = encode_storage_time(value, fine_octets)
    return value - decode_storage_time(coarse, fine, fine_octets)


def stamp_packet(packet, storage_time_s, fine_octets):
    """Attach a storage time stamp to one packet held by a store."""
    if not isinstance(packet, dict):
        raise ValueError("packet must be a mapping")
    packet_id = packet.get("id")
    if not isinstance(packet_id, str) or not packet_id.strip():
        raise ValueError("packet needs a non-empty string id")
    generation_time_s = packet.get("generation_time_s")
    if generation_time_s is not None:
        generation_time_s = _seconds("packet %s generation time" % packet_id,
                                     generation_time_s)
    value = _seconds("packet %s storage time" % packet_id, storage_time_s)
    coarse, fine = encode_storage_time(value, fine_octets)
    return {
        "id": packet_id,
        "generation_time_s": generation_time_s,
        "storage_time_s": decode_storage_time(coarse, fine, fine_octets),
        "storage_time_coarse": coarse,
        "storage_time_fine": fine,
        "fine_octets": _fine_octets(fine_octets),
    }


def stamp_packets(packets, storage_times_s, fine_octets):
    """Stamp a sequence of packets and report any ordering finding."""
    if not isinstance(packets, (list, tuple)) or not packets:
        raise ValueError("packets must be a non-empty list")
    if not isinstance(storage_times_s, (list, tuple)):
        raise ValueError("storage_times_s must be a list")
    if len(packets) != len(storage_times_s):
        raise ValueError(
            "got %d packets and %d storage times" % (len(packets), len(storage_times_s))
        )
    stamped = []
    findings = []
    previous = None
    for packet, storage_time in zip(packets, storage_times_s):
        record = stamp_packet(packet, storage_time, fine_octets)
        if previous is not None:
            if record["storage_time_s"] < previous["storage_time_s"]:
                findings.append(
                    {
                        "id": record["id"],
                        "finding": FINDING_STAMP_WENT_BACKWARDS,
                        "previous_id": previous["id"],
                    }
                )
            elif record["storage_time_s"] == previous["storage_time_s"]:
                findings.append(
                    {
                        "id": record["id"],
                        "finding": FINDING_STAMP_REPEATED,
                        "previous_id": previous["id"],
                    }
                )
        stamped.append(record)
        previous = record
    return {"stamped": stamped, "findings": findings}


def select_by_storage_window(stamped, start_s, end_s):
    """Packets whose storage time falls inside a closed retrieval window."""
    if not isinstance(stamped, (list, tuple)):
        raise ValueError("stamped must be a list")
    start = _seconds("window start", start_s)
    end = _seconds("window end", end_s)
    if end < start:
        raise ValueError("retrieval window ends before it starts")
    selected = []
    for record in stamped:
        if not isinstance(record, dict) or "storage_time_s" not in record:
            raise ValueError("stamped record is missing its storage time")
        if start <= record["storage_time_s"] <= end:
            selected.append(record)
    return selected


def select_by_generation_window(stamped, start_s, end_s):
    """The same window read against generation time, for comparison only."""
    if not isinstance(stamped, (list, tuple)):
        raise ValueError("stamped must be a list")
    start = _seconds("window start", start_s)
    end = _seconds("window end", end_s)
    if end < start:
        raise ValueError("retrieval window ends before it starts")
    selected = []
    for record in stamped:
        generation = record.get("generation_time_s") if isinstance(record, dict) else None
        if generation is None:
            continue
        if start <= generation <= end:
            selected.append(record)
    return selected


def storage_latency_s(record):
    """How long a packet waited between being generated and being stored."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    generation = record.get("generation_time_s")
    if generation is None:
        raise ValueError(
            "packet %r carries no generation time to compare" % (record.get("id"),)
        )
    latency = record["storage_time_s"] - generation
    if latency < 0:
        raise ValueError(
            "packet %r was stamped as stored before it was generated"
            % (record.get("id"),)
        )
    return latency


def assess_storage_time_stamping(packets, storage_times_s, fine_octets, window=None):
    """Stamp a run of packets and grade the stamps a retrieval would use."""
    result = stamp_packets(packets, storage_times_s, fine_octets)
    stamped = result["stamped"]
    report = {
        "stamped": stamped,
        "findings": result["findings"],
        "resolution_s": stamp_resolution_s(fine_octets),
        "monotonic": not any(
            f["finding"] == FINDING_STAMP_WENT_BACKWARDS for f in result["findings"]
        ),
        "packet_count": len(stamped),
    }
    if window is not None:
        if not isinstance(window, (list, tuple)) or len(window) != 2:
            raise ValueError("window must be a (start, end) pair")
        by_storage = select_by_storage_window(stamped, window[0], window[1])
        by_generation = select_by_generation_window(stamped, window[0], window[1])
        report["window"] = {
            "start_s": _seconds("window start", window[0]),
            "end_s": _seconds("window end", window[1]),
            "storage_time_ids": [r["id"] for r in by_storage],
            "generation_time_ids": [r["id"] for r in by_generation],
            "answers_agree": [r["id"] for r in by_storage]
            == [r["id"] for r in by_generation],
        }
    return report
