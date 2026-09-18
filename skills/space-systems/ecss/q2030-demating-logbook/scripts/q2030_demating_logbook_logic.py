"""Connector (de-)mating logbook and mating-cycle control.

Anchor: ECSS-Q-ST-20-30 Annex B (informative), the worked (de-)mating logbook.
The example is used here as the house format for the connector mating record:
every mate and demate of a connector is entered against the connector, and the
sheet carries a countdown of the mating cycles the connector has left against
the maximum its qualification allows. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the entry fields the worked example prints and which of them every
   entry must carry.
2. Validate a submitted log: a known operation, an ISO date, entries for one
   connector in non-decreasing date order, and mate and demate alternating
   from a mate, so a demate with no matching mate is refused rather than
   counted.
3. Count the mating cycles a connector has consumed -- one per mate -- and
   subtract them from the declared maximum to give the remaining-cycle
   countdown the sheet exists to show.
4. Grade every connector against its maximum with integer arithmetic only, so
   the approaching-limit band falls on the same entry on every machine.
5. Render the maximum-cycle control table, one aligned row per connector, and
   report the findings: a connector over its maximum, a connector left in a
   state the integration flow did not expect, and a connector with no maximum
   declared anywhere.
"""

from datetime import date

__all__ = [
    "EVENT_FIELDS",
    "MANDATORY_EVENT_FIELDS",
    "OPERATIONS",
    "DEFAULT_MAXIMUM_CYCLES",
    "WARNING_NUMERATOR",
    "WARNING_DENOMINATOR",
    "normalise_identifier",
    "parse_day",
    "validate_event",
    "validate_log",
    "mating_cycles",
    "connector_state",
    "cycles_remaining",
    "cycle_status",
    "connector_rows",
    "render_control_table",
    "assess_demating_logbook",
]

# The entry as the worked example prints it, in that order.
EVENT_FIELDS = (
    "connector_id",
    "event_date",
    "operation",
    "operator",
    "remark",
)

# Everything but the free-text remark identifies the entry.
MANDATORY_EVENT_FIELDS = (
    "connector_id",
    "event_date",
    "operation",
    "operator",
)

# The two operations the logbook records. Nothing else consumes a cycle.
OPERATIONS = ("mate", "demate")

# Cycles allowed by a connector whose qualification declares no other figure.
DEFAULT_MAXIMUM_CYCLES = 10

# The approaching-limit band opens at four fifths of the maximum. Held as an
# integer ratio so the band edge lands on the same cycle on every machine.
WARNING_NUMERATOR = 4
WARNING_DENOMINATOR = 5


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def parse_day(value, label):
    """Return an ISO day; raise on anything that is not one."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (label, value))


def _positive_integer(value, label):
    """Return a positive integer; raise on anything else."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("%s must be an integer of at least 1, got %r" % (label, value))
    return value


def validate_event(event, position=0):
    """Return one normalised logbook entry; raise on a malformed one."""
    if not isinstance(event, dict):
        raise ValueError("events[%d] must be a mapping" % position)
    unknown = sorted(key for key in event if key not in EVENT_FIELDS)
    if unknown:
        raise ValueError(
            "events[%d] carries fields the logbook has no place for: %s"
            % (position, ", ".join(unknown))
        )
    result = {}
    for field in MANDATORY_EVENT_FIELDS:
        if field not in event or event[field] is None:
            raise ValueError("events[%d] leaves %s blank" % (position, field))
    result["connector_id"] = normalise_identifier(
        event["connector_id"], "events[%d].connector_id" % position
    )
    result["event_date"] = parse_day(event["event_date"], "events[%d].event_date" % position)
    operation = normalise_identifier(event["operation"], "events[%d].operation" % position)
    if operation not in OPERATIONS:
        raise ValueError(
            "events[%d].operation must be one of %s, got %r"
            % (position, ", ".join(OPERATIONS), operation)
        )
    result["operation"] = operation
    result["operator"] = normalise_identifier(
        event["operator"], "events[%d].operator" % position
    )
    remark = event.get("remark")
    result["remark"] = None if remark is None else str(remark).strip()
    return result


def validate_log(events):
    """Return the normalised entries grouped per connector, in entry order.

    Raises when a connector's entries run backwards in time, when a demate has
    no mate before it, or when a connector is mated twice without a demate.
    """
    if not isinstance(events, (list, tuple)):
        raise ValueError("events must be a sequence of logbook entries")
    grouped = {}
    order = []
    for position, event in enumerate(events):
        entry = validate_event(event, position)
        connector = entry["connector_id"]
        if connector not in grouped:
            grouped[connector] = []
            order.append(connector)
        previous = grouped[connector]
        if previous and entry["event_date"] < previous[-1]["event_date"]:
            raise ValueError(
                "events[%d] for %s is dated %s, before the entry above it dated %s"
                % (
                    position,
                    connector,
                    entry["event_date"].isoformat(),
                    previous[-1]["event_date"].isoformat(),
                )
            )
        expected = "mate" if (not previous or previous[-1]["operation"] == "demate") else "demate"
        if entry["operation"] != expected:
            raise ValueError(
                "events[%d] records a %s for %s where the log expects a %s"
                % (position, entry["operation"], connector, expected)
            )
        previous.append(entry)
    return {"order": tuple(order), "grouped": grouped}


def mating_cycles(entries):
    """Return the mating cycles consumed by one connector's entries."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence of normalised entries")
    used = 0
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or "operation" not in entry:
            raise ValueError("entries[%d] must be a normalised entry mapping" % index)
        if entry["operation"] == "mate":
            used += 1
    return used


def connector_state(entries):
    """Return 'mated' or 'demated' for one connector's entries."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence of normalised entries")
    if not entries:
        return "demated"
    last = entries[-1]
    if not isinstance(last, dict) or "operation" not in last:
        raise ValueError("the last entry must be a normalised entry mapping")
    return "mated" if last["operation"] == "mate" else "demated"


def cycles_remaining(used, maximum):
    """Return the mating cycles a connector has left; never below zero."""
    if isinstance(used, bool) or not isinstance(used, int) or used < 0:
        raise ValueError("used must be a non-negative integer, got %r" % (used,))
    maximum = _positive_integer(maximum, "maximum")
    remaining = maximum - used
    return remaining if remaining > 0 else 0


def cycle_status(used, maximum):
    """Return the control band a connector sits in against its maximum."""
    if isinstance(used, bool) or not isinstance(used, int) or used < 0:
        raise ValueError("used must be a non-negative integer, got %r" % (used,))
    maximum = _positive_integer(maximum, "maximum")
    if used > maximum:
        return "exceeded"
    if used == maximum:
        return "at-limit"
    if used * WARNING_DENOMINATOR >= WARNING_NUMERATOR * maximum:
        return "approaching-limit"
    return "within-limit"


def connector_rows(log, maxima=None, default_maximum=DEFAULT_MAXIMUM_CYCLES):
    """Return one control row per connector, in the order first entered."""
    if not isinstance(log, dict) or "order" not in log or "grouped" not in log:
        raise ValueError("log must be the mapping returned by validate_log")
    if maxima is None:
        maxima = {}
    if not isinstance(maxima, dict):
        raise ValueError("maxima must be a mapping of connector id to cycle maximum")
    default_maximum = _positive_integer(default_maximum, "default_maximum")
    normalised_maxima = {}
    for key, value in maxima.items():
        normalised_maxima[normalise_identifier(key, "maxima key")] = _positive_integer(
            value, "maxima[%r]" % key
        )
    rows = []
    for connector in log["order"]:
        entries = log["grouped"][connector]
        declared = connector in normalised_maxima
        maximum = normalised_maxima.get(connector, default_maximum)
        used = mating_cycles(entries)
        rows.append(
            {
                "connector_id": connector,
                "cycles_used": used,
                "maximum_cycles": maximum,
                "maximum_declared": declared,
                "cycles_remaining": cycles_remaining(used, maximum),
                "state": connector_state(entries),
                "status": cycle_status(used, maximum),
                "entry_count": len(entries),
                "last_entry_date": entries[-1]["event_date"] if entries else None,
            }
        )
    return rows


def render_control_table(rows):
    """Return the maximum-cycle control table as aligned lines."""
    if not isinstance(rows, (list, tuple)):
        raise ValueError("rows must be a sequence of control rows")
    headers = ("CONNECTOR", "USED", "MAX", "LEFT", "STATE", "STATUS")
    table = [headers]
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or "connector_id" not in row:
            raise ValueError("rows[%d] must be a control row mapping" % index)
        table.append(
            (
                row["connector_id"],
                str(row["cycles_used"]),
                str(row["maximum_cycles"]),
                str(row["cycles_remaining"]),
                row["state"],
                row["status"],
            )
        )
    widths = [max(len(cell[column]) for cell in table) for column in range(len(headers))]
    lines = []
    for cell in table:
        lines.append(
            "  ".join(cell[column].ljust(widths[column]) for column in range(len(headers))).rstrip()
        )
    return tuple(lines)


def assess_demating_logbook(events, maxima=None, default_maximum=DEFAULT_MAXIMUM_CYCLES,
                            expected_final_state=None):
    """Grade a (de-)mating logbook and its maximum-cycle control table."""
    log = validate_log(events)
    rows = connector_rows(log, maxima, default_maximum)
    if expected_final_state is None:
        expected_final_state = {}
    if not isinstance(expected_final_state, dict):
        raise ValueError("expected_final_state must be a mapping of connector id to state")
    expected = {}
    for key, value in expected_final_state.items():
        state = normalise_identifier(value, "expected_final_state[%r]" % key)
        if state not in ("mated", "demated"):
            raise ValueError(
                "expected_final_state[%r] must be 'mated' or 'demated', got %r" % (key, value)
            )
        expected[normalise_identifier(key, "expected_final_state key")] = state
    findings = []
    for row in rows:
        if row["status"] == "exceeded":
            findings.append(
                "%s has consumed %d mating cycles against a maximum of %d"
                % (row["connector_id"], row["cycles_used"], row["maximum_cycles"])
            )
        elif row["status"] == "at-limit":
            findings.append(
                "%s has consumed its last allowed mating cycle (%d of %d)"
                % (row["connector_id"], row["cycles_used"], row["maximum_cycles"])
            )
        if not row["maximum_declared"]:
            findings.append(
                "%s has no declared mating-cycle maximum; the default of %d was applied"
                % (row["connector_id"], row["maximum_cycles"])
            )
        wanted = expected.get(row["connector_id"])
        if wanted is not None and wanted != row["state"]:
            findings.append(
                "%s is left %s while the flow expects it %s"
                % (row["connector_id"], row["state"], wanted)
            )
    return {
        "connectors": rows,
        "connector_count": len(rows),
        "event_count": sum(row["entry_count"] for row in rows),
        "rendered": render_control_table(rows),
        "findings": findings,
        "verdict": "cycle-control-conformant" if not findings else "cycle-control-nonconformant",
    }
