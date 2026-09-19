"""Reporting the execution status of on-board control procedures.

Anchor: ECSS-E-ST-70-41C clause 6.18.4.5 (paraphrased into an
implementable procedure; no standard text is reproduced).

What this job is. Knowing the execution status of every procedure
aboard is one thing; getting that knowledge to the ground inside a
telemetry packet is another, and it is the second one clause 6.18.4.5
is about. The report has to say which procedures it covers, it has to
fit the packets the link can carry, and it has to be readable as a
whole even when it arrives as several packets.

Three decisions make the report:

  which procedures  -- all of them, a named subset the ground asked
                       for, or only the ones whose status changed since
                       the last report. Each answers a different
                       operational question, and a report that does not
                       say which of the three it is cannot be read: an
                       absent procedure might be unchanged, might be
                       unasked-for, might be gone.
  what order        -- whatever order is chosen, it has to be the same
                       order every time. A report whose entry order
                       drifts cannot be diffed against the last one,
                       which is the main thing anybody does with it.
  how many packets  -- an entry costs a fixed number of octets, a
                       packet carries a header plus as many entries as
                       fit, and a report longer than one packet becomes
                       a numbered sequence rather than a truncation.

The truncation trap. The tempting failure is to fill one packet and
stop. The report then looks complete -- it has a header, it has
entries, it parses -- and the procedures that fell off the end are
indistinguishable from procedures that are not aboard. Splitting into a
counted sequence is what makes a partial arrival visible as one.

Stdlib only, offline, deterministic.
"""

STATUS_NOT_LOADED = "not-loaded"
STATUS_LOADED_INACTIVE = "loaded-inactive"
STATUS_ACTIVE_RUNNING = "active-running"
STATUS_ACTIVE_SUSPENDED = "active-suspended"
STATUS_TERMINATED_COMPLETED = "terminated-completed"
STATUS_TERMINATED_ABORTED = "terminated-aborted"

VALID_STATUSES = (
    STATUS_NOT_LOADED,
    STATUS_LOADED_INACTIVE,
    STATUS_ACTIVE_RUNNING,
    STATUS_ACTIVE_SUSPENDED,
    STATUS_TERMINATED_COMPLETED,
    STATUS_TERMINATED_ABORTED,
)

SCOPE_ALL = "all-procedures"
SCOPE_REQUESTED = "requested-subset"
SCOPE_CHANGED = "changed-since-last-report"
VALID_SCOPES = (SCOPE_ALL, SCOPE_REQUESTED, SCOPE_CHANGED)

# A cadence is a product of an integer octet count and a possibly
# fractional report rate, so a cadence that lands exactly on its budget
# can sit a few units in the last place either side of it.
RATE_TOLERANCE = 1.0e-12


def _integer(label, value, minimum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


def _positive_number(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return float(value)


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def validate_status(status):
    """Validate an execution status name and return it."""
    if status not in VALID_STATUSES:
        raise ValueError(
            "unknown execution status %r (expected one of %s)"
            % (status, ", ".join(VALID_STATUSES))
        )
    return status


def validate_entry(entry):
    """Validate one reportable procedure record."""
    if not isinstance(entry, dict):
        raise ValueError("status entry must be a mapping")
    proc_id = _text("procedure id", entry.get("id"))
    return {
        "id": proc_id,
        "version": _integer("procedure %s version" % proc_id,
                            entry.get("version", 1), 1),
        "status": validate_status(entry.get("status")),
    }


def validate_population(procedures):
    """Validate the procedures a report could cover, in their own order."""
    if not isinstance(procedures, list) or not procedures:
        raise ValueError("procedures must be a non-empty list")
    entries = []
    seen = set()
    for procedure in procedures:
        entry = validate_entry(procedure)
        if entry["id"] in seen:
            raise ValueError("duplicate procedure id %r" % (entry["id"],))
        seen.add(entry["id"])
        entries.append(entry)
    return entries


def select_all(procedures):
    """Every procedure aboard, in the store's own order."""
    return validate_population(procedures)


def select_requested(procedures, requested_ids):
    """The named subset, in the order the ground asked for it."""
    entries = validate_population(procedures)
    if not isinstance(requested_ids, (list, tuple)) or not requested_ids:
        raise ValueError("requested_ids must be a non-empty list")
    catalogue = {entry["id"]: entry for entry in entries}
    chosen = []
    seen = set()
    for raw in requested_ids:
        name = _text("requested procedure id", raw)
        if name not in catalogue:
            raise ValueError(
                "the report was asked for procedure %s, which is not aboard"
                % name
            )
        if name in seen:
            raise ValueError("procedure %s was requested twice" % name)
        seen.add(name)
        chosen.append(catalogue[name])
    return chosen


def select_changed(procedures, previous_statuses):
    """Only the procedures whose status differs from the last report."""
    entries = validate_population(procedures)
    if not isinstance(previous_statuses, dict):
        raise ValueError("previous_statuses must be a mapping")
    for name, status in previous_statuses.items():
        _text("previous status id", name)
        validate_status(status)
    return [
        entry for entry in entries
        if previous_statuses.get(entry["id"]) != entry["status"]
    ]


def select_entries(procedures, scope, requested_ids=None,
                   previous_statuses=None):
    """Choose the report's content under one declared scope."""
    if scope not in VALID_SCOPES:
        raise ValueError(
            "unknown report scope %r (expected one of %s)"
            % (scope, ", ".join(VALID_SCOPES))
        )
    if scope == SCOPE_ALL:
        return select_all(procedures)
    if scope == SCOPE_REQUESTED:
        if requested_ids is None:
            raise ValueError(
                "a requested-subset report needs the list of ids it covers"
            )
        return select_requested(procedures, requested_ids)
    if previous_statuses is None:
        raise ValueError(
            "a changed-since-last-report needs the previous statuses to "
            "compare against; without them nothing can be known to have "
            "changed"
        )
    return select_changed(procedures, previous_statuses)


def validate_packet_spec(spec):
    """Validate the telemetry packet geometry a report has to fit."""
    if not isinstance(spec, dict):
        raise ValueError("packet spec must be a mapping")
    max_octets = _integer("max_packet_octets", spec.get("max_packet_octets"), 1)
    header = _integer("header_octets", spec.get("header_octets", 0), 0)
    entry = _integer("entry_octets", spec.get("entry_octets"), 1)
    if header + entry > max_octets:
        raise ValueError(
            "a packet of %d octets cannot carry a %d octet header plus even "
            "one %d octet entry" % (max_octets, header, entry)
        )
    return {
        "max_packet_octets": max_octets,
        "header_octets": header,
        "entry_octets": entry,
    }


def entries_per_packet(spec):
    """How many entries one telemetry packet can carry."""
    working = validate_packet_spec(spec)
    return (working["max_packet_octets"] - working["header_octets"]) // \
        working["entry_octets"]


def packet_octets(spec, entry_count):
    """Octets one packet occupies when it carries this many entries."""
    working = validate_packet_spec(spec)
    count = _integer("entry_count", entry_count, 0)
    if count > entries_per_packet(working):
        raise ValueError(
            "%d entries do not fit a packet that carries %d"
            % (count, entries_per_packet(working))
        )
    return working["header_octets"] + count * working["entry_octets"]


def partition_report(entries, spec):
    """Split a report into a counted sequence of telemetry packets."""
    if not isinstance(entries, list):
        raise ValueError("entries must be a list")
    working = validate_packet_spec(spec)
    per_packet = entries_per_packet(working)
    checked = [validate_entry(entry) for entry in entries]
    if not checked:
        # An empty report is still a report: one packet saying nothing
        # changed, which is not the same as no packet at all.
        return [{
            "sequence_number": 1,
            "sequence_count": 1,
            "entries": [],
            "octets": packet_octets(working, 0),
        }]
    chunks = [
        checked[start:start + per_packet]
        for start in range(0, len(checked), per_packet)
    ]
    return [
        {
            "sequence_number": index + 1,
            "sequence_count": len(chunks),
            "entries": chunk,
            "octets": packet_octets(working, len(chunk)),
        }
        for index, chunk in enumerate(chunks)
    ]


def build_status_report(procedures, spec, scope=SCOPE_ALL, requested_ids=None,
                        previous_statuses=None):
    """Build a complete, packetized execution status report."""
    entries = select_entries(procedures, scope, requested_ids,
                             previous_statuses)
    packets = partition_report(entries, spec)
    grouped = {}
    for entry in entries:
        grouped.setdefault(entry["status"], []).append(entry["id"])
    return {
        "scope": scope,
        "entries": entries,
        "entry_count": len(entries),
        "packets": packets,
        "packet_count": len(packets),
        "total_octets": sum(p["octets"] for p in packets),
        "grouped_by_status": grouped,
        "counts_by_status": {
            status: len(grouped.get(status, [])) for status in VALID_STATUSES
        },
        "fits_one_packet": len(packets) == 1,
        "covered_ids": [entry["id"] for entry in entries],
    }


def assess_reporting_cadence(report, reports_per_hour,
                             downlink_octets_per_hour):
    """Grade how often this report can be sent against the downlink budget."""
    if not isinstance(report, dict) or "total_octets" not in report:
        raise ValueError("report must be a built status report")
    rate = _positive_number("reports_per_hour", reports_per_hour)
    budget = _positive_number("downlink_octets_per_hour",
                              downlink_octets_per_hour)
    demand = report["total_octets"] * rate
    within = demand - budget <= abs(budget) * RATE_TOLERANCE
    affordable = budget / float(report["total_octets"]) \
        if report["total_octets"] else None
    return {
        "reports_per_hour": rate,
        "octets_per_report": report["total_octets"],
        "octets_per_hour": demand,
        "budget_octets_per_hour": budget,
        "margin_octets_per_hour": budget - demand,
        "within_budget": within,
        "max_affordable_reports_per_hour": affordable,
        "packets_per_hour": report["packet_count"] * rate,
    }
