"""Detail report of a position-based schedule.

Anchor: ECSS-E-ST-70-41C clause 6.22.9.2 (position-based schedule detail
report). Paraphrased into an implementable procedure; no standard text is
reproduced.

Model implemented here
----------------------
A detail report carries, for each scheduled activity it covers, the request
identification, the orbit position, the scheduling group and the full content
of the scheduled request. Because the request content is carried, the report
of a populated schedule does not fit one telemetry packet and has to be split
across a run of report packets. One activity's detail is never split across
two packets, so an activity whose detail cannot fit a packet on its own is a
configuration error rather than something to be fragmented.

Procedure implemented here
--------------------------
1. Validate a scheduled activity and size its detail entry.
2. Select the reported subset by identification, by scheduling group and by
   an orbit position window that may wrap through the origin.
3. Order the selected entries by increasing orbit position.
4. Pack the ordered entries into report packets, opening a new packet when
   the next entry no longer fits, and refuse an entry that fits no packet.
5. Measure the packing against the lower bound the payload alone implies.
6. Assemble the detail report and its findings.
"""

__all__ = [
    "REVOLUTION_DEG",
    "POSITION_TOLERANCE_DEG",
    "DETAIL_ENTRY_FIELDS",
    "SOURCE_ID_BITS",
    "APID_BITS",
    "SEQUENCE_COUNT_BITS",
    "validate_position_deg",
    "validate_detail_activity",
    "detail_entry_octets",
    "position_window_contains",
    "select_detail_entries",
    "order_detail_entries",
    "packet_payload_octets",
    "minimum_packet_count",
    "pack_detail_report",
    "assess_detail_report",
]

REVOLUTION_DEG = 360.0

# Representation tolerance used at a window edge.
POSITION_TOLERANCE_DEG = 1e-9

# The fields a detail entry carries; unlike a summary entry it holds the
# request content as well.
DETAIL_ENTRY_FIELDS = (
    "source_id",
    "apid",
    "sequence_count",
    "position_deg",
    "group",
    "request_octets",
)

SOURCE_ID_BITS = 8
APID_BITS = 11
SEQUENCE_COUNT_BITS = 14


def _require_field_int(value, label, bits):
    """Return value as a whole number fitting a field of the given width."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    ceiling = 1 << bits
    if value < 0 or value >= ceiling:
        raise ValueError(
            "%s value %d falls outside a %d bit field" % (label, value, bits)
        )
    return value


def _require_positive_int(value, label):
    """Return value as a positive whole count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _require_non_negative_int(value, label):
    """Return value as a non-negative whole count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def validate_position_deg(position):
    """Return an orbit position in degrees on the half-open revolution."""
    if isinstance(position, bool) or not isinstance(position, (int, float)):
        raise ValueError("position_deg must be a number, got %r" % (position,))
    value = float(position)
    if value != value:
        raise ValueError("position_deg must be a real number, got a NaN")
    if value < 0.0 or value >= REVOLUTION_DEG:
        raise ValueError(
            "position_deg %r falls outside the half-open revolution [0, %g)"
            % (position, REVOLUTION_DEG)
        )
    return value


def validate_detail_activity(activity):
    """Return the detail entry of one scheduled activity."""
    if not isinstance(activity, dict):
        raise ValueError("activity must be a mapping")
    for key in ("source_id", "apid", "sequence_count", "position_deg", "request_octets"):
        if key not in activity:
            raise ValueError("activity missing required key '%s'" % key)
    group = activity.get("group")
    if group is not None:
        if not isinstance(group, int) or isinstance(group, bool) or group < 1:
            raise ValueError("group must be a positive integer, got %r" % (group,))
    return {
        "source_id": _require_field_int(activity["source_id"], "source_id", SOURCE_ID_BITS),
        "apid": _require_field_int(activity["apid"], "apid", APID_BITS),
        "sequence_count": _require_field_int(
            activity["sequence_count"], "sequence_count", SEQUENCE_COUNT_BITS
        ),
        "position_deg": validate_position_deg(activity["position_deg"]),
        "group": group,
        "request_octets": _require_positive_int(
            activity["request_octets"], "request_octets"
        ),
    }


def detail_entry_octets(entry, entry_overhead_octets):
    """Return the octets one detail entry occupies inside a report packet."""
    overhead = _require_non_negative_int(
        entry_overhead_octets, "entry_overhead_octets"
    )
    if not isinstance(entry, dict) or "request_octets" not in entry:
        raise ValueError("entry must be a mapping carrying 'request_octets'")
    return overhead + _require_positive_int(entry["request_octets"], "request_octets")


def position_window_contains(start_deg, end_deg, position_deg):
    """Return whether an orbit position lies in a window, wrap included."""
    start = validate_position_deg(start_deg)
    end = validate_position_deg(end_deg)
    value = validate_position_deg(position_deg)
    tol = POSITION_TOLERANCE_DEG
    if start <= end:
        return (value >= start - tol) and (value <= end + tol)
    return (value >= start - tol) or (value <= end + tol)


def select_detail_entries(activities, identifications=None, groups=None, window=None):
    """Return the detail entries a report request asks for."""
    if not isinstance(activities, (list, tuple)):
        raise ValueError("activities must be a sequence")

    wanted_ids = None
    if identifications is not None:
        if not isinstance(identifications, (list, tuple, set, frozenset)):
            raise ValueError("identifications must be a sequence or set")
        if not identifications:
            raise ValueError("an identification selection must name at least one request")
        wanted_ids = set()
        for item in identifications:
            if not isinstance(item, (list, tuple)) or len(item) != 3:
                raise ValueError(
                    "an identification must be a (source_id, apid, sequence_count) "
                    "triple, got %r" % (item,)
                )
            wanted_ids.add(tuple(item))

    wanted_groups = None
    if groups is not None:
        if not isinstance(groups, (list, tuple, set, frozenset)):
            raise ValueError("groups must be a sequence or set")
        if not groups:
            raise ValueError("a group selection must name at least one group")
        wanted_groups = set()
        for item in groups:
            if not isinstance(item, int) or isinstance(item, bool) or item < 1:
                raise ValueError("group must be a positive integer, got %r" % (item,))
            wanted_groups.add(item)

    if window is not None:
        if not isinstance(window, (list, tuple)) or len(window) != 2:
            raise ValueError("window must be a (start_deg, end_deg) pair")

    kept = []
    for index, activity in enumerate(activities):
        try:
            entry = validate_detail_activity(activity)
        except ValueError as exc:
            raise ValueError("activities[%d]: %s" % (index, exc))
        ident = (entry["source_id"], entry["apid"], entry["sequence_count"])
        if wanted_ids is not None and ident not in wanted_ids:
            continue
        if wanted_groups is not None and entry["group"] not in wanted_groups:
            continue
        if window is not None and not position_window_contains(
            window[0], window[1], entry["position_deg"]
        ):
            continue
        kept.append(entry)
    return tuple(kept)


def order_detail_entries(entries):
    """Return the entries ordered by increasing orbit position."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence")
    return tuple(
        sorted(
            entries,
            key=lambda e: (
                e["position_deg"],
                e["source_id"],
                e["apid"],
                e["sequence_count"],
            ),
        )
    )


def packet_payload_octets(max_packet_octets, report_header_octets):
    """Return the octets of a report packet left for detail entries."""
    limit = _require_positive_int(max_packet_octets, "max_packet_octets")
    header = _require_non_negative_int(report_header_octets, "report_header_octets")
    if header >= limit:
        raise ValueError(
            "a report header of %d octets leaves no entry room inside a %d octet "
            "packet" % (header, limit)
        )
    return limit - header


def minimum_packet_count(total_entry_octets, payload_octets):
    """Return the packet count the entry payload alone implies."""
    total = _require_non_negative_int(total_entry_octets, "total_entry_octets")
    payload = _require_positive_int(payload_octets, "payload_octets")
    if total == 0:
        return 0
    return -(-total // payload)


def pack_detail_report(entries, max_packet_octets, report_header_octets,
                       entry_overhead_octets):
    """Pack ordered detail entries into report packets.

    Entries keep their order and one entry is never split, so a packet is
    closed as soon as the next entry no longer fits. An entry that does not
    fit an otherwise empty packet is refused.
    """
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence")
    payload = packet_payload_octets(max_packet_octets, report_header_octets)

    packets = []
    current = []
    used = 0
    for index, entry in enumerate(entries):
        size = detail_entry_octets(entry, entry_overhead_octets)
        if size > payload:
            raise ValueError(
                "entry %d needs %d octets but a report packet offers only %d; its "
                "detail cannot be split across packets"
                % (index, size, payload)
            )
        if used + size > payload:
            packets.append(tuple(current))
            current = []
            used = 0
        current.append(entry)
        used += size
    if current:
        packets.append(tuple(current))
    return tuple(packets)


def assess_detail_report(spec):
    """Assess a clause 6.22.9.2 detail report.

    spec keys: activities, max_packet_octets, report_header_octets,
    entry_overhead_octets. Optional keys: identifications, groups, window.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "activities",
        "max_packet_octets",
        "report_header_octets",
        "entry_overhead_octets",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    every = select_detail_entries(spec["activities"])
    seen = set()
    for entry in every:
        ident = (entry["source_id"], entry["apid"], entry["sequence_count"])
        if ident in seen:
            raise ValueError(
                "identification %r appears on two scheduled activities" % (ident,)
            )
        seen.add(ident)

    selected = order_detail_entries(
        select_detail_entries(
            spec["activities"],
            identifications=spec.get("identifications"),
            groups=spec.get("groups"),
            window=spec.get("window"),
        )
    )
    payload = packet_payload_octets(
        spec["max_packet_octets"], spec["report_header_octets"]
    )
    packets = pack_detail_report(
        selected,
        spec["max_packet_octets"],
        spec["report_header_octets"],
        spec["entry_overhead_octets"],
    )

    entry_octets = [
        detail_entry_octets(e, spec["entry_overhead_octets"]) for e in selected
    ]
    total_entry_octets = sum(entry_octets)
    lower_bound = minimum_packet_count(total_entry_octets, payload)

    fills = []
    for packet in packets:
        used = sum(detail_entry_octets(e, spec["entry_overhead_octets"]) for e in packet)
        fills.append(used / float(payload))

    findings = []
    if not selected:
        findings.append(
            "the selection matched no scheduled activity; the detail report is empty"
        )
    if len(packets) > lower_bound:
        findings.append(
            "packing needs %d report packets against a payload lower bound of %d; "
            "the difference is the cost of never splitting an entry"
            % (len(packets), lower_bound)
        )
    if any(len(p) == 1 for p in packets) and len(packets) > 1:
        findings.append(
            "at least one report packet carries a single entry; that entry is close "
            "to the packet payload on its own"
        )
    if spec.get("window") is not None:
        start = validate_position_deg(spec["window"][0])
        end = validate_position_deg(spec["window"][1])
        if start > end:
            findings.append(
                "the position window wraps through the origin of the revolution"
            )

    return {
        "entries": selected,
        "entry_count": len(selected),
        "scheduled_count": len(every),
        "carries_request_content": True,
        "entry_fields": DETAIL_ENTRY_FIELDS,
        "packet_payload_octets": payload,
        "total_entry_octets": total_entry_octets,
        "packet_count": len(packets),
        "minimum_packet_count": lower_bound,
        "packets": packets,
        "packet_fill_ratios": tuple(fills),
        "largest_entry_octets": max(entry_octets) if entry_octets else 0,
        "clean": not findings,
        "findings": findings,
    }
