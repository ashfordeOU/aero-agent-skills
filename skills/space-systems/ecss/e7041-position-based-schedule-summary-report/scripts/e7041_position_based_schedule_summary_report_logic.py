"""Summary report of a position-based schedule.

Anchor: ECSS-E-ST-70-41C clause 6.22.9.1 (position-based schedule summary
report). Paraphrased into an implementable procedure; no standard text is
reproduced.

Model implemented here
----------------------
A summary report carries one entry per scheduled activity. An entry holds the
identification of the scheduled request and the orbit position the activity is
scheduled at, together with its scheduling group; it never carries the request
content itself, which is what separates the summary report from the detail
report of the neighbouring clause.

Procedure implemented here
--------------------------
1. Validate an orbit position and a request identification.
2. Reduce a scheduled activity to its summary entry, dropping the request.
3. Select the reported subset by scheduling group and by an orbit position
   window that may wrap through the origin.
4. Order the entries by increasing orbit position, breaking ties on the
   identification so the report is reproducible.
5. Size the report from its entry count.
6. Assemble the summary report and its findings.
"""

__all__ = [
    "REVOLUTION_DEG",
    "POSITION_TOLERANCE_DEG",
    "SUMMARY_ENTRY_FIELDS",
    "APID_BITS",
    "SEQUENCE_COUNT_BITS",
    "SOURCE_ID_BITS",
    "validate_position_deg",
    "validate_identification",
    "summary_entry",
    "position_window_contains",
    "select_activities",
    "order_summary_entries",
    "summary_report_octets",
    "build_summary_report",
]

# One full revolution of the orbit position axis, in degrees.
REVOLUTION_DEG = 360.0

# Representation tolerance used at a window edge, so a position that lands on
# a bound is inside the window whichever way the float rounded.
POSITION_TOLERANCE_DEG = 1e-9

# The only fields a summary entry carries.
SUMMARY_ENTRY_FIELDS = ("source_id", "apid", "sequence_count", "position_deg", "group")

# Packet identification field widths the identification is checked against.
SOURCE_ID_BITS = 8
APID_BITS = 11
SEQUENCE_COUNT_BITS = 14


def _require_non_negative_int(value, label, bits):
    """Return value as a whole number that fits a field of the given width."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    ceiling = 1 << bits
    if value < 0 or value >= ceiling:
        raise ValueError(
            "%s value %d falls outside a %d bit field" % (label, value, bits)
        )
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


def validate_identification(activity):
    """Return the (source, application process, sequence count) identification."""
    if not isinstance(activity, dict):
        raise ValueError("activity must be a mapping")
    for key in ("source_id", "apid", "sequence_count"):
        if key not in activity:
            raise ValueError("activity missing identification key '%s'" % key)
    return (
        _require_non_negative_int(activity["source_id"], "source_id", SOURCE_ID_BITS),
        _require_non_negative_int(activity["apid"], "apid", APID_BITS),
        _require_non_negative_int(
            activity["sequence_count"], "sequence_count", SEQUENCE_COUNT_BITS
        ),
    )


def summary_entry(activity):
    """Return the summary entry of one scheduled activity.

    The request content is deliberately dropped: a summary entry identifies
    the scheduled request and says where on the orbit it sits, nothing more.
    """
    source_id, apid, sequence_count = validate_identification(activity)
    if "position_deg" not in activity:
        raise ValueError("activity missing required key 'position_deg'")
    group = activity.get("group")
    if group is not None:
        if not isinstance(group, int) or isinstance(group, bool) or group < 1:
            raise ValueError("group must be a positive integer, got %r" % (group,))
    return {
        "source_id": source_id,
        "apid": apid,
        "sequence_count": sequence_count,
        "position_deg": validate_position_deg(activity["position_deg"]),
        "group": group,
    }


def position_window_contains(start_deg, end_deg, position_deg):
    """Return whether an orbit position lies in a window, wrap included.

    A window whose start is greater than its end wraps through the origin of
    the revolution and contains the two arcs either side of it.
    """
    start = validate_position_deg(start_deg)
    end = validate_position_deg(end_deg)
    value = validate_position_deg(position_deg)
    tol = POSITION_TOLERANCE_DEG
    if start <= end:
        return (value >= start - tol) and (value <= end + tol)
    return (value >= start - tol) or (value <= end + tol)


def select_activities(activities, groups=None, window=None):
    """Return the subset of activities a summary request asks for."""
    if not isinstance(activities, (list, tuple)):
        raise ValueError("activities must be a sequence")
    if groups is not None:
        if not isinstance(groups, (list, tuple, set, frozenset)):
            raise ValueError("groups must be a sequence or set")
        if not groups:
            raise ValueError("a group selection must name at least one group")
        wanted = set()
        for item in groups:
            if not isinstance(item, int) or isinstance(item, bool) or item < 1:
                raise ValueError("group must be a positive integer, got %r" % (item,))
            wanted.add(item)
    else:
        wanted = None
    if window is not None:
        if not isinstance(window, (list, tuple)) or len(window) != 2:
            raise ValueError("window must be a (start_deg, end_deg) pair")

    kept = []
    for index, activity in enumerate(activities):
        try:
            entry = summary_entry(activity)
        except ValueError as exc:
            raise ValueError("activities[%d]: %s" % (index, exc))
        if wanted is not None and entry["group"] not in wanted:
            continue
        if window is not None and not position_window_contains(
            window[0], window[1], entry["position_deg"]
        ):
            continue
        kept.append(entry)
    return tuple(kept)


def order_summary_entries(entries):
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


def summary_report_octets(entry_count, header_octets, entry_octets):
    """Return the octets a summary report of this many entries occupies."""
    if not isinstance(entry_count, int) or isinstance(entry_count, bool):
        raise ValueError("entry_count must be an integer, got %r" % (entry_count,))
    if entry_count < 0:
        raise ValueError("entry_count must not be negative, got %d" % entry_count)
    for label, value in (("header_octets", header_octets), ("entry_octets", entry_octets)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer, got %r" % (label, value))
        if value <= 0:
            raise ValueError("%s must be positive, got %d" % (label, value))
    return header_octets + entry_count * entry_octets


def build_summary_report(spec):
    """Build a clause 6.22.9.1 summary report.

    spec keys: activities. Optional keys: groups, window, header_octets,
    entry_octets.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "activities" not in spec:
        raise ValueError("spec missing required key 'activities'")

    all_entries = select_activities(spec["activities"])
    seen = {}
    for entry in all_entries:
        ident = (entry["source_id"], entry["apid"], entry["sequence_count"])
        if ident in seen:
            raise ValueError(
                "identification %r appears on two scheduled activities" % (ident,)
            )
        seen[ident] = entry

    selected = select_activities(
        spec["activities"], groups=spec.get("groups"), window=spec.get("window")
    )
    ordered = order_summary_entries(selected)

    findings = []
    if not ordered:
        findings.append(
            "the selection matched no scheduled activity; the summary report is empty"
        )
    if spec.get("window") is not None:
        start = validate_position_deg(spec["window"][0])
        end = validate_position_deg(spec["window"][1])
        if start > end:
            findings.append(
                "the position window wraps through the origin of the revolution"
            )
    ungrouped = [e for e in ordered if e["group"] is None]
    if ungrouped and spec.get("groups") is not None:
        findings.append(
            "%d selected activities carry no scheduling group" % len(ungrouped)
        )

    octets = None
    if spec.get("header_octets") is not None and spec.get("entry_octets") is not None:
        octets = summary_report_octets(
            len(ordered), spec["header_octets"], spec["entry_octets"]
        )

    positions = [e["position_deg"] for e in ordered]
    return {
        "entries": ordered,
        "entry_count": len(ordered),
        "scheduled_count": len(all_entries),
        "carries_request_content": False,
        "entry_fields": SUMMARY_ENTRY_FIELDS,
        "first_position_deg": positions[0] if positions else None,
        "last_position_deg": positions[-1] if positions else None,
        "report_octets": octets,
        "clean": not findings,
        "findings": findings,
    }
