"""Tracing the execution of an on-board control procedure.

Anchor: ECSS-E-ST-70-41C clause 6.18.4.8 (paraphrased into an
implementable procedure; no standard text is reproduced).

The clause covers what the OBCP engine records about a procedure while
it runs so that the ground can afterwards say what the procedure
actually did, in what order, and when.

Tracing is per procedure and switchable. The engine keeps a trace for
the procedures whose tracing is on, and switching it on while a
procedure is already running produces a trace that begins in the
middle. That is a usable trace only if the reader knows where it
began; read as if it were complete it says the procedure started at
whatever step happens to be first.

Granularity is a filter, not a volume knob. Each execution event
carries a level -- the procedure entering and leaving, a block being
entered, an individual step running. A trace configured at a coarse
level records the coarse events and silently omits the finer ones, so
the question a trace can answer is fixed at configuration time, not at
retrieval time.

The trace is bounded. A finite buffer meets a long run in one of two
ways: the oldest records are overwritten, or recording stops at the
brim. Both lose events and they lose different ones -- the first loses
the beginning, the second loses the end. Only the second leaves the
retained run contiguous, which is why a trace that dropped its oldest
records cannot be read as a straight sequence without saying so.

A trace is reconstructable when it begins at the run's first event and
has no hole in it. Anything else is evidence, but evidence with a
stated gap.

Stdlib only, offline, deterministic.
"""

LEVEL_PROCEDURE = "procedure"
LEVEL_BLOCK = "block"
LEVEL_STEP = "step"
LEVEL_RANK = {LEVEL_PROCEDURE: 0, LEVEL_BLOCK: 1, LEVEL_STEP: 2}

OVERFLOW_DROP_OLDEST = "drop-oldest"
OVERFLOW_STOP_TRACING = "stop-tracing"
OVERFLOW_POLICIES = (OVERFLOW_DROP_OLDEST, OVERFLOW_STOP_TRACING)

FINDING_TRACING_DISABLED = "tracing-was-off-so-the-run-left-no-trace"
FINDING_TRACE_STARTED_MID_RUN = "tracing-was-switched-on-after-the-run-began"
FINDING_OLDEST_RECORDS_DROPPED = "trace-buffer-wrapped-and-dropped-its-oldest-records"
FINDING_TRACING_STOPPED_AT_BRIM = "tracing-stopped-when-the-trace-buffer-filled"
FINDING_GRANULARITY_OMITS_EVENTS = "configured-granularity-omits-finer-execution-events"
FINDING_UNLOADED_PROCEDURE = "tracing-configured-for-a-procedure-that-is-not-loaded"
FINDING_TIME_WENT_BACKWARDS = "trace-record-times-are-not-non-decreasing"


def _identifier(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _time(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be before the epoch, got %r" % (label, value))
    return float(value)


def level_rank(level):
    """Position of an execution level from coarsest to finest."""
    if level not in LEVEL_RANK:
        raise ValueError(
            "level must be one of %s, got %r" % (", ".join(LEVEL_RANK), level)
        )
    return LEVEL_RANK[level]


def normalise_configuration(spec):
    """Validate one procedure's trace configuration."""
    if not isinstance(spec, dict):
        raise ValueError("trace configuration must be a mapping, got %r" % (spec,))
    procedure_id = _identifier("procedure id", spec.get("procedure_id"))
    granularity = spec.get("granularity", LEVEL_STEP)
    level_rank(granularity)
    capacity = spec.get("capacity", 64)
    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise ValueError("capacity must be an integer, got %r" % (capacity,))
    if capacity < 1:
        raise ValueError("capacity must be at least one record, got %d" % capacity)
    policy = spec.get("overflow", OVERFLOW_DROP_OLDEST)
    if policy not in OVERFLOW_POLICIES:
        raise ValueError(
            "overflow policy must be one of %s, got %r"
            % (", ".join(OVERFLOW_POLICIES), policy)
        )
    enabled_from = spec.get("enabled_from_index")
    if enabled_from is not None:
        if isinstance(enabled_from, bool) or not isinstance(enabled_from, int):
            raise ValueError("enabled_from_index must be an integer, got %r" % (enabled_from,))
        if enabled_from < 0:
            raise ValueError("enabled_from_index must not be negative")
    return {
        "procedure_id": procedure_id,
        "enabled": bool(spec.get("enabled", True)),
        "granularity": granularity,
        "capacity": capacity,
        "overflow": policy,
        "enabled_from_index": enabled_from,
    }


def normalise_event(event, index):
    """Validate one execution event offered to the trace."""
    if not isinstance(event, dict):
        raise ValueError("execution event %d must be a mapping" % index)
    return {
        "index": index,
        "event_id": _identifier("event %d identifier" % index, event.get("event_id")),
        "level": event.get("level", LEVEL_STEP),
        "time_s": _time("event %d time" % index, event.get("time_s", 0.0)),
    }


def selected_events(configuration, events):
    """The events this configuration's granularity and switch-on admit."""
    limit = level_rank(configuration["granularity"])
    start = configuration["enabled_from_index"] or 0
    chosen = []
    for index, raw in enumerate(events):
        event = normalise_event(raw, index)
        if level_rank(event["level"]) > limit:
            continue
        if index < start:
            continue
        chosen.append(event)
    return chosen


def apply_capacity(records, capacity, policy):
    """Fit a run of trace records into a bounded buffer."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list")
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
        raise ValueError("capacity must be a positive integer, got %r" % (capacity,))
    if policy not in OVERFLOW_POLICIES:
        raise ValueError("unknown overflow policy %r" % (policy,))
    if len(records) <= capacity:
        return {"retained": list(records), "lost": 0, "overflowed": False}
    if policy == OVERFLOW_DROP_OLDEST:
        retained = list(records[len(records) - capacity:])
    else:
        retained = list(records[:capacity])
    return {
        "retained": retained,
        "lost": len(records) - capacity,
        "overflowed": True,
    }


def trace_run(configuration, events):
    """Produce the trace a configuration yields for one run of events."""
    config = normalise_configuration(configuration)
    if not isinstance(events, (list, tuple)) or not events:
        raise ValueError("a run must offer at least one execution event")
    findings = []
    if not config["enabled"]:
        return {
            "configuration": config,
            "records": [],
            "offered": 0,
            "lost": 0,
            "findings": [{"finding": FINDING_TRACING_DISABLED}],
        }
    chosen = selected_events(config, events)
    previous = None
    for event in chosen:
        if previous is not None and event["time_s"] < previous:
            findings.append(
                {"finding": FINDING_TIME_WENT_BACKWARDS, "event_id": event["event_id"]}
            )
        previous = event["time_s"]
    limit = level_rank(config["granularity"])
    omitted = [
        raw
        for index, raw in enumerate(events)
        if level_rank(normalise_event(raw, index)["level"]) > limit
    ]
    if omitted:
        findings.append(
            {"finding": FINDING_GRANULARITY_OMITS_EVENTS, "omitted": len(omitted)}
        )
    if (config["enabled_from_index"] or 0) > 0:
        findings.append({"finding": FINDING_TRACE_STARTED_MID_RUN})
    fitted = apply_capacity(chosen, config["capacity"], config["overflow"])
    if fitted["overflowed"]:
        if config["overflow"] == OVERFLOW_DROP_OLDEST:
            findings.append({"finding": FINDING_OLDEST_RECORDS_DROPPED})
        else:
            findings.append({"finding": FINDING_TRACING_STOPPED_AT_BRIM})
    records = []
    for sequence, event in enumerate(fitted["retained"]):
        records.append(
            {
                "sequence": sequence,
                "procedure_id": config["procedure_id"],
                "event_id": event["event_id"],
                "level": event["level"],
                "time_s": event["time_s"],
                "run_index": event["index"],
            }
        )
    return {
        "configuration": config,
        "records": records,
        "offered": len(chosen),
        "lost": fitted["lost"],
        "findings": findings,
    }


def trace_coverage(trace, events):
    """Fraction of the run's execution events the trace actually holds."""
    if not isinstance(trace, dict) or "records" not in trace:
        raise ValueError("trace must be a trace_run result")
    if not isinstance(events, (list, tuple)) or not events:
        raise ValueError("events must be the non-empty run the trace came from")
    return len(trace["records"]) / float(len(events))


def is_reconstructable(trace, events):
    """True when the trace begins at the run's first event and has no hole."""
    records = trace["records"] if isinstance(trace, dict) else None
    if records is None:
        raise ValueError("trace must be a trace_run result")
    if not records:
        return False
    if records[0]["run_index"] != 0:
        return False
    if records[-1]["run_index"] != len(events) - 1:
        return False
    for earlier, later in zip(records, records[1:]):
        if later["run_index"] != earlier["run_index"] + 1:
            return False
    return True


def assess_tracing(configuration, events, loaded_procedures=None):
    """Grade a procedure's trace configuration against one run."""
    trace = trace_run(configuration, events)
    config = trace["configuration"]
    findings = list(trace["findings"])
    if loaded_procedures is not None:
        if not isinstance(loaded_procedures, (list, tuple, set)):
            raise ValueError("loaded_procedures must be a collection of identifiers")
        if config["procedure_id"] not in set(loaded_procedures):
            findings.append(
                {
                    "finding": FINDING_UNLOADED_PROCEDURE,
                    "procedure_id": config["procedure_id"],
                }
            )
    return {
        "procedure_id": config["procedure_id"],
        "records": trace["records"],
        "record_count": len(trace["records"]),
        "lost": trace["lost"],
        "coverage": trace_coverage(trace, events),
        "reconstructable": is_reconstructable(trace, events),
        "findings": findings,
    }
