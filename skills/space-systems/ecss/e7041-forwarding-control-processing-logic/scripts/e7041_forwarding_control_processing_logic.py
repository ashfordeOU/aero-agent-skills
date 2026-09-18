"""Processing logic of the real-time forwarding control service.

Anchor: ECSS-E-ST-70-41C clause 6.14.3.3 (the forwarding control processing
logic of a service 14 subservice). Paraphrased into an implementable
procedure; no standard text is reproduced.

Store shape (as held by the forward-control definition step)
------------------------------------------------------------
{apid: {"whole": bool,
        "service_types": {service_type: {"whole": bool, "subtypes": [ints]}}}}

Procedure implemented here
--------------------------
1. Validate the store, the enabled application processes and the subsampling
   rates.
2. For each generated report, resolve the widest definition that covers it and
   remember the level that matched: that level is the subsampling counter key.
3. Apply the enable state of the application process above the definitions.
4. Advance the counter of the matched definition only for an eligible report,
   forwarding the first match and then every nth.
5. Give every report a disposition and a named reason, and tally the stream.
"""

__all__ = [
    "DOWNLINK",
    "STORAGE",
    "REASON_FORWARDED",
    "REASON_NO_DEFINITION",
    "REASON_DISABLED",
    "REASON_SUBSAMPLED",
    "validate_store",
    "validate_rates",
    "validate_report",
    "matching_level",
    "route_report",
    "process_stream",
]

DOWNLINK = "real-time-downlink"
STORAGE = "on-board-storage"

REASON_FORWARDED = "covered by a forward-control definition"
REASON_NO_DEFINITION = "no forward-control definition covers the report"
REASON_DISABLED = "forwarding is disabled for the application process"
REASON_SUBSAMPLED = "subsampled out by the definition rate"


def _require_int(value, label, minimum=None):
    """Return value as a whole number, optionally at or above a minimum."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def validate_store(store):
    """Return the forward-control store after validating its three levels."""
    if not isinstance(store, dict):
        raise ValueError("store must be a mapping of application processes")
    for apid, entry in store.items():
        _require_int(apid, "store key", 0)
        if not isinstance(entry, dict) or "whole" not in entry or "service_types" not in entry:
            raise ValueError(
                "store[%r] must carry 'whole' and 'service_types'" % (apid,)
            )
        if not isinstance(entry["whole"], bool):
            raise ValueError("store[%r]['whole'] must be a boolean" % (apid,))
        services = entry["service_types"]
        if not isinstance(services, dict):
            raise ValueError("store[%r]['service_types'] must be a mapping" % (apid,))
        for stype, service in services.items():
            _require_int(stype, "service type key", 1)
            if not isinstance(service, dict) or "whole" not in service or "subtypes" not in service:
                raise ValueError(
                    "store[%r] service type %r must carry 'whole' and 'subtypes'"
                    % (apid, stype)
                )
            if not isinstance(service["whole"], bool):
                raise ValueError(
                    "store[%r] service type %r 'whole' must be a boolean" % (apid, stype)
                )
            if not isinstance(service["subtypes"], (list, tuple, set, frozenset)):
                raise ValueError(
                    "store[%r] service type %r 'subtypes' must be a collection"
                    % (apid, stype)
                )
            for subtype in service["subtypes"]:
                _require_int(subtype, "message subtype", 1)
    return store


def validate_rates(rates):
    """Return the subsampling rates keyed by definition level."""
    if rates is None:
        return {}
    if not isinstance(rates, dict):
        raise ValueError("subsampling_rates must be a mapping keyed by definition level")
    validated = {}
    for key, value in rates.items():
        if not isinstance(key, tuple) or len(key) != 3:
            raise ValueError(
                "subsampling rate key %r must be an (apid, service_type, subtype) triple"
                % (key,)
            )
        _require_int(value, "subsampling rate for %r" % (key,), 1)
        validated[key] = value
    return validated


def validate_report(report, index=0):
    """Return the validated (apid, service_type, subtype) of a report."""
    if not isinstance(report, dict):
        raise ValueError("reports[%d] must be a mapping" % index)
    for key in ("application_process", "service_type", "message_subtype"):
        if key not in report:
            raise ValueError("reports[%d] missing required key '%s'" % (index, key))
    apid = _require_int(report["application_process"], "reports[%d] application process" % index, 0)
    stype = _require_int(report["service_type"], "reports[%d] service type" % index, 1)
    subtype = _require_int(report["message_subtype"], "reports[%d] message subtype" % index, 1)
    return (apid, stype, subtype)


def matching_level(store, apid, service_type, message_subtype):
    """Return the widest definition level covering the report, or None."""
    entry = store.get(apid)
    if entry is None:
        return None
    if entry["whole"]:
        return (apid, None, None)
    service = entry["service_types"].get(service_type)
    if service is None:
        return None
    if service["whole"]:
        return (apid, service_type, None)
    if message_subtype in set(service["subtypes"]):
        return (apid, service_type, message_subtype)
    return None


def route_report(store, report, enabled, rates, counters, index=0):
    """Return the disposition of one report and update the counter state."""
    apid, stype, subtype = validate_report(report, index)
    if not isinstance(counters, dict):
        raise ValueError("counters must be a mapping")
    level = matching_level(store, apid, stype, subtype)
    if level is None:
        return {
            "application_process": apid,
            "service_type": stype,
            "message_subtype": subtype,
            "disposition": STORAGE,
            "forwarded": False,
            "reason": REASON_NO_DEFINITION,
            "matched_level": None,
        }
    if apid not in set(enabled):
        return {
            "application_process": apid,
            "service_type": stype,
            "message_subtype": subtype,
            "disposition": STORAGE,
            "forwarded": False,
            "reason": REASON_DISABLED,
            "matched_level": level,
        }
    rate = rates.get(level, 1)
    count = counters.get(level, 0)
    counters[level] = count + 1
    # The first matching report goes out, then every rate-th one after it.
    forwarded = count % rate == 0
    return {
        "application_process": apid,
        "service_type": stype,
        "message_subtype": subtype,
        "disposition": DOWNLINK if forwarded else STORAGE,
        "forwarded": forwarded,
        "reason": REASON_FORWARDED if forwarded else REASON_SUBSAMPLED,
        "matched_level": level,
    }


def process_stream(spec):
    """Assess a clause 6.14.3.3 report stream against a forwarding subservice.

    spec keys: store, enabled_application_processes, reports, optional
    subsampling_rates.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("store", "enabled_application_processes", "reports"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    store = validate_store(spec["store"])
    enabled = spec["enabled_application_processes"]
    if not isinstance(enabled, (list, tuple, set, frozenset)):
        raise ValueError("enabled_application_processes must be a collection")
    enabled = set(enabled)
    for apid in enabled:
        _require_int(apid, "enabled application process", 0)
    rates = validate_rates(spec.get("subsampling_rates"))
    reports = spec["reports"]
    if not isinstance(reports, (list, tuple)):
        raise ValueError("spec['reports'] must be a sequence")

    counters = {}
    decisions = []
    per_application = {}
    for index, report in enumerate(reports):
        decision = route_report(store, report, enabled, rates, counters, index)
        decisions.append(decision)
        tally = per_application.setdefault(
            decision["application_process"], {"forwarded": 0, "stored": 0}
        )
        if decision["forwarded"]:
            tally["forwarded"] += 1
        else:
            tally["stored"] += 1

    forwarded = [d for d in decisions if d["forwarded"]]
    findings = []
    if reports and not forwarded:
        findings.append(
            "no report in a stream of %d was forwarded to the real-time downlink"
            % len(reports)
        )
    for apid in sorted(store):
        if apid not in enabled:
            findings.append(
                "application process %d holds forwarding definitions but is disabled"
                % apid
            )
    return {
        "decisions": decisions,
        "forwarded_count": len(forwarded),
        "stored_count": len(decisions) - len(forwarded),
        "per_application_process": per_application,
        "counters": counters,
        "findings": findings,
    }
