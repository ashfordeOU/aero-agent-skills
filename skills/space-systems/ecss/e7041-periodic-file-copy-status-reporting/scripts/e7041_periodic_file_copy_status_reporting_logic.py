"""Periodic status reporting for on-board file copy operations.

Anchor: ECSS-E-ST-70-41C clause 6.23.5.5 (periodic file copy status reporting
of the file management service). Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the reporting function as a small state: enabled or disabled, a
   generation interval in whole on-board time units, and the tick at which
   the current enable started.
2. Enable with a strictly positive interval. Enabling an already-enabled
   function replaces the interval and restarts the schedule from the enable
   tick, so the new cadence is not phase-locked to the old one.
3. Disable without an interval. Disabling an already-disabled function is
   redundant, not an error, but it is reported as such.
4. Compute the generation ticks over a window from the enable tick and the
   interval using whole-number arithmetic only, so the same schedule comes
   out on every platform. The enable tick itself is not a report tick; the
   first report falls one whole interval later.
5. Build the content of one report: every copy operation in the list at that
   tick with its source, target, octets moved, octets remaining and state.
   An empty list still produces a report, carrying zero entries -- silence
   and "nothing is copying" are different messages.
6. Report the window: the generation ticks, the report content at each, the
   number of reports, and findings covering a disabled function, an interval
   longer than the window and a cadence that reports nothing but emptiness.
"""

__all__ = [
    "MIN_INTERVAL",
    "new_reporting_state",
    "validate_interval",
    "enable_periodic_reporting",
    "disable_periodic_reporting",
    "report_ticks",
    "operation_row",
    "build_status_report",
    "reports_over_window",
    "assess_reporting_window",
]

# An interval is a whole number of on-board time units. Zero would ask the
# subservice to report continuously, which is a request for the full rate,
# not a cadence.
MIN_INTERVAL = 1


def _validate_tick(value, label):
    """Return a validated whole on-board time tick."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number of time units, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def validate_interval(interval):
    """Return a validated generation interval in whole time units."""
    if isinstance(interval, bool) or not isinstance(interval, int):
        raise ValueError("interval must be a whole number of time units, got %r" % (interval,))
    if interval < MIN_INTERVAL:
        raise ValueError("interval must be at least %d time unit, got %d" % (MIN_INTERVAL, interval))
    return interval


def new_reporting_state():
    """Return the reporting function in its disabled power-on condition."""
    return {"enabled": False, "interval": None, "enabled_at": None}


def _validate_state(state):
    """Return the validated reporting state."""
    if not isinstance(state, dict):
        raise ValueError("reporting state must be a mapping")
    for field in ("enabled", "interval", "enabled_at"):
        if field not in state:
            raise ValueError("reporting state missing required key '%s'" % field)
    if not isinstance(state["enabled"], bool):
        raise ValueError("reporting state 'enabled' must be a boolean")
    if state["enabled"]:
        validate_interval(state["interval"])
        _validate_tick(state["enabled_at"], "enabled_at")
    return state


def enable_periodic_reporting(state, interval, at_tick):
    """Enable the reporting function, or re-interval it, and return the outcome."""
    _validate_state(state)
    interval = validate_interval(interval)
    at_tick = _validate_tick(at_tick, "at_tick")
    was_enabled = state["enabled"]
    previous = state["interval"]
    state["enabled"] = True
    state["interval"] = interval
    state["enabled_at"] = at_tick
    if not was_enabled:
        return {"outcome": "enabled", "interval": interval, "reason": None}
    if previous == interval:
        return {
            "outcome": "restarted",
            "interval": interval,
            "reason": "already enabled at this interval; the schedule restarts from this tick",
        }
    return {
        "outcome": "re-intervalled",
        "interval": interval,
        "reason": "interval changed from %d to %d; the schedule restarts from this tick"
        % (previous, interval),
    }


def disable_periodic_reporting(state):
    """Disable the reporting function and return the outcome."""
    _validate_state(state)
    if not state["enabled"]:
        return {
            "outcome": "redundant",
            "interval": None,
            "reason": "the reporting function was already disabled",
        }
    interval = state["interval"]
    state["enabled"] = False
    state["interval"] = None
    state["enabled_at"] = None
    return {"outcome": "disabled", "interval": interval, "reason": None}


def report_ticks(enabled_at, interval, window_end):
    """Return the ticks at which reports are generated, up to and including window_end."""
    enabled_at = _validate_tick(enabled_at, "enabled_at")
    interval = validate_interval(interval)
    window_end = _validate_tick(window_end, "window_end")
    if window_end < enabled_at:
        raise ValueError(
            "window_end %d is before the enable tick %d" % (window_end, enabled_at)
        )
    ticks = []
    tick = enabled_at + interval
    while tick <= window_end:
        ticks.append(tick)
        tick += interval
    return ticks


def operation_row(entry):
    """Return the reported row for one copy operation."""
    if not isinstance(entry, dict):
        raise ValueError("copy operation must be a mapping")
    for field in ("source", "target", "octets_total", "octets_copied", "state"):
        if field not in entry:
            raise ValueError("copy operation missing required key '%s'" % field)
    total = entry["octets_total"]
    copied = entry["octets_copied"]
    for label, value in (("octets_total", total), ("octets_copied", copied)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("%s must be a whole non-negative number, got %r" % (label, value))
    if total < 1:
        raise ValueError("octets_total must be positive, got %d" % total)
    if copied > total:
        raise ValueError("octets_copied %d exceeds octets_total %d" % (copied, total))
    if entry["state"] not in ("running", "suspended"):
        raise ValueError("state must be 'running' or 'suspended', got %r" % (entry["state"],))
    return {
        "source": entry["source"],
        "target": entry["target"],
        "octets_total": total,
        "octets_copied": copied,
        "octets_remaining": total - copied,
        "state": entry["state"],
    }


def build_status_report(tick, operations):
    """Return the content of one periodic status report."""
    tick = _validate_tick(tick, "tick")
    if not isinstance(operations, (list, tuple)):
        raise ValueError("operations must be a sequence of copy operations")
    rows = [operation_row(entry) for entry in operations]
    return {
        "tick": tick,
        "entry_count": len(rows),
        "operations": rows,
        "octets_remaining": sum(row["octets_remaining"] for row in rows),
    }


def reports_over_window(state, operations_at_tick, window_end):
    """Return one status report per generation tick across the window."""
    _validate_state(state)
    if not callable(operations_at_tick):
        raise ValueError("operations_at_tick must be callable, taking a tick")
    if not state["enabled"]:
        return []
    ticks = report_ticks(state["enabled_at"], state["interval"], window_end)
    return [build_status_report(tick, operations_at_tick(tick)) for tick in ticks]


def assess_reporting_window(spec):
    """Run a reporting window and report the cadence, the content and the findings.

    spec keys: interval, enabled_at, window_end, operations (a fixed list, or a
    mapping of tick to list), optional enabled (default True).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for field in ("interval", "enabled_at", "window_end", "operations"):
        if field not in spec:
            raise ValueError("spec missing required key '%s'" % field)
    operations = spec["operations"]
    if isinstance(operations, dict):
        def at_tick(tick):
            return operations.get(tick, [])
    elif isinstance(operations, (list, tuple)):
        def at_tick(tick):
            return list(operations)
    else:
        raise ValueError("spec['operations'] must be a sequence or a mapping of tick to sequence")
    state = new_reporting_state()
    findings = []
    if spec.get("enabled", True):
        enable_periodic_reporting(state, spec["interval"], spec["enabled_at"])
    else:
        validate_interval(spec["interval"])
        _validate_tick(spec["enabled_at"], "enabled_at")
        findings.append("the periodic reporting function is disabled; no report is generated")
    reports = reports_over_window(state, at_tick, spec["window_end"])
    window = _validate_tick(spec["window_end"], "window_end") - _validate_tick(
        spec["enabled_at"], "enabled_at"
    )
    if state["enabled"] and not reports:
        findings.append(
            "the interval of %d exceeds the %d time units of the window; no report falls inside it"
            % (state["interval"], window)
        )
    if reports and all(report["entry_count"] == 0 for report in reports):
        findings.append(
            "every report in the window carries zero copy operations; the cadence reports emptiness"
        )
    if reports and reports[-1]["octets_remaining"]:
        findings.append(
            "%d octets are still outstanding at the last report in the window"
            % reports[-1]["octets_remaining"]
        )
    return {
        "state": state,
        "ticks": [report["tick"] for report in reports],
        "reports": reports,
        "report_count": len(reports),
        "findings": findings,
    }
