"""Content report of an on-board request sequence.

Anchor: ECSS-E-ST-70-41C clause 6.21.8 (report the content of a request
sequence). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the request sequence store and the identifier the report asks for.
2. Validate every entry of that sequence: a whole non-negative release offset
   from the start of the sequence and a whole positive request size.
3. Order the entries the way the report has to present them, by release offset
   and, within one offset, by the load order the sequence was built in.
4. Pack the ordered entries into the fewest content reports a telemetry data
   field of the declared size can carry, entry overhead included.
5. Assemble the report plan and its findings: an unknown identifier, a sequence
   that is still being built, an empty sequence, and an entry no single report
   could ever carry.
"""

__all__ = [
    "STATUS_AVAILABLE",
    "STATUS_UNDER_CONSTRUCTION",
    "REPORTABLE_STATUSES",
    "normalise_entry",
    "order_entries",
    "entry_cost_octets",
    "oversized_entries",
    "pack_entries",
    "assess_sequence_content_report",
]

# A sequence is reportable once it has been loaded and closed. One still being
# built has no settled content, so its report would describe a moving target.
STATUS_AVAILABLE = "available"
STATUS_UNDER_CONSTRUCTION = "under-construction"
REPORTABLE_STATUSES = (STATUS_AVAILABLE,)

# Widest sequence identifier field this model will accept.
MAX_IDENTIFIER_BITS = 32


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


def normalise_entry(entry, index):
    """Return one sequence entry as a validated dict."""
    if not isinstance(entry, dict):
        raise ValueError("entry %d must be a mapping, got %r" % (index, entry))
    for key in ("name", "offset_seconds", "request_octets"):
        if key not in entry:
            raise ValueError("entry %d missing required key '%s'" % (index, key))
    name = entry["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("entry %d name must be a non-empty string" % index)
    return {
        "name": name.strip(),
        "offset_seconds": _require_non_negative_int(
            entry["offset_seconds"], "entry %d offset_seconds" % index
        ),
        "request_octets": _require_positive_int(
            entry["request_octets"], "entry %d request_octets" % index
        ),
        "load_order": index,
    }


def order_entries(entries):
    """Return the entries in the order a content report presents them."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a list or tuple")
    normalised = [normalise_entry(item, i) for i, item in enumerate(entries)]
    seen = set()
    for item in normalised:
        if item["name"] in seen:
            raise ValueError("entry name '%s' appears more than once" % item["name"])
        seen.add(item["name"])
    normalised.sort(key=lambda e: (e["offset_seconds"], e["load_order"]))
    return tuple(normalised)


def entry_cost_octets(entry, entry_overhead_octets):
    """Return the octets one entry occupies inside a content report."""
    overhead = _require_non_negative_int(
        entry_overhead_octets, "entry_overhead_octets"
    )
    octets = _require_positive_int(entry["request_octets"], "request_octets")
    return overhead + octets


def oversized_entries(entries, report_data_octets, entry_overhead_octets):
    """Return the names of entries no single content report could carry."""
    capacity = _require_positive_int(report_data_octets, "report_data_octets")
    return tuple(
        e["name"]
        for e in entries
        if entry_cost_octets(e, entry_overhead_octets) > capacity
    )


def pack_entries(entries, report_data_octets, entry_overhead_octets):
    """Return the ordered entries grouped into successive content reports."""
    capacity = _require_positive_int(report_data_octets, "report_data_octets")
    over = oversized_entries(entries, capacity, entry_overhead_octets)
    if over:
        raise ValueError(
            "entries %s exceed the %d octet content report data field"
            % (", ".join(over), capacity)
        )
    reports = []
    current = []
    used = 0
    for item in entries:
        cost = entry_cost_octets(item, entry_overhead_octets)
        if current and used + cost > capacity:
            reports.append(tuple(current))
            current = []
            used = 0
        current.append(item["name"])
        used += cost
    if current:
        reports.append(tuple(current))
    return tuple(reports)


def assess_sequence_content_report(spec):
    """Assess a clause 6.21.8 request sequence content report.

    spec keys: sequence_store (mapping of identifier -> {status, entries}),
    requested_identifier, report_data_octets, entry_overhead_octets.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "sequence_store",
        "requested_identifier",
        "report_data_octets",
        "entry_overhead_octets",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    store = spec["sequence_store"]
    if not isinstance(store, dict):
        raise ValueError("sequence_store must be a mapping")
    identifier = _require_non_negative_int(
        spec["requested_identifier"], "requested_identifier"
    )
    capacity = _require_positive_int(spec["report_data_octets"], "report_data_octets")
    overhead = _require_non_negative_int(
        spec["entry_overhead_octets"], "entry_overhead_octets"
    )
    if overhead >= capacity:
        raise ValueError(
            "entry overhead %d octets leaves no room inside a %d octet report"
            % (overhead, capacity)
        )

    findings = []
    if identifier not in store:
        return {
            "requested_identifier": identifier,
            "status": "unknown",
            "entry_count": 0,
            "ordered_entries": (),
            "reports": (),
            "report_count": 0,
            "total_octets": 0,
            "reportable": False,
            "findings": [
                "request sequence %d is not held in the sequence store" % identifier
            ],
        }

    record = store[identifier]
    if not isinstance(record, dict) or "status" not in record or "entries" not in record:
        raise ValueError(
            "sequence %d record must be a mapping with 'status' and 'entries'"
            % identifier
        )
    status = record["status"]
    if not isinstance(status, str) or not status.strip():
        raise ValueError("sequence %d status must be a non-empty string" % identifier)
    status = status.strip()

    ordered = order_entries(record["entries"])
    total = sum(entry_cost_octets(e, overhead) for e in ordered)

    if status not in REPORTABLE_STATUSES:
        findings.append(
            "request sequence %d is '%s'; its content is not settled enough to report"
            % (identifier, status)
        )
    if not ordered:
        findings.append(
            "request sequence %d holds no entries; the report carries a header only"
            % identifier
        )

    over = oversized_entries(ordered, capacity, overhead)
    if over:
        findings.append(
            "entries %s each need more than the %d octets a content report carries"
            % (", ".join(over), capacity)
        )
        reports = ()
    else:
        reports = pack_entries(ordered, capacity, overhead)

    return {
        "requested_identifier": identifier,
        "status": status,
        "entry_count": len(ordered),
        "ordered_entries": tuple(e["name"] for e in ordered),
        "reports": reports,
        "report_count": len(reports),
        "total_octets": total,
        "reportable": not findings,
        "findings": findings,
    }
