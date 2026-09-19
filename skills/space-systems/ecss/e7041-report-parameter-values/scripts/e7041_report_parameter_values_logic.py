#!/usr/bin/env python3
"""Reporting the current values of the on-board parameters a request names.

Anchor: ECSS-E-ST-70-41C clause 6.20.4.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause's normative items reduce to eight implementable checks:

    1  the request carries a list of parameter identifiers and the
       application process that holds them
    2  an identifier that resolves to no parameter of that process is
       rejected with its own failure notification
    3  the identifiers that do resolve are still reported; one bad
       identifier does not sink the request
    4  a request where nothing resolves fails at start and generates
       no report at all
    5  a repeated identifier collapses to a single entry
    6  each entry carries the parameter identifier and the value read
       at assembly time
    7  a stored value that does not fit the parameter's own
       definition is withheld and raised, not reported
    8  the report carries reported, withheld and unknown counts so a
       receiver can detect a truncated transfer

Entries follow request order, so the nth entry answers the nth
distinct identifier the request carried and a requester can pair them
positionally without matching on names.

Integer domains come from shifts, never from floating-point
exponentiation: 1 << bits is exact at every width, while a float power
is not correctly rounded and lands a count out at wide widths on some
platforms and not others.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

REPRESENTATIONS = ("unsigned-integer", "signed-integer", "real", "boolean")

INTEGER_REPRESENTATIONS = ("unsigned-integer", "signed-integer")

VERDICT_REPORTED = "parameter-value-report-generated"
VERDICT_FAILED_START = "parameter-value-report-failed-start"
VERDICT_DEFECTIVE = "parameter-value-report-defective"


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_positive_integer(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least 1, got %d" % (name, value))
    return value


def _require_number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    return value


def representable_domain(representation, bits=None):
    """Derive the domain a representation can hold, with exact arithmetic."""
    _require_choice("representation", representation, REPRESENTATIONS)
    if representation == "unsigned-integer":
        width = _require_positive_integer("bits", bits)
        return {"lower": 0, "upper": (1 << width) - 1}
    if representation == "signed-integer":
        width = _require_positive_integer("bits", bits)
        if width < 2:
            raise ValueError(
                "a signed-integer parameter needs at least 2 bits, got %d" % width
            )
        half = 1 << (width - 1)
        return {"lower": -half, "upper": half - 1}
    return {"lower": None, "upper": None}


def validate_parameter(record):
    """Normalize one stored parameter: definition plus its current value."""
    if not isinstance(record, dict):
        raise ValueError("parameter must be a mapping, got %r" % (record,))
    apid = _require_identifier(
        "parameter application_process_id", record.get("application_process_id")
    )
    parameter_id = _require_identifier(
        "parameter parameter_id of %s" % apid, record.get("parameter_id")
    )
    owner = "%s/%s" % (apid, parameter_id)
    representation = _require_choice(
        "parameter %s representation" % owner,
        record.get("representation"),
        REPRESENTATIONS,
    )
    parameter = {
        "application_process_id": apid,
        "parameter_id": parameter_id,
        "representation": representation,
    }
    if representation in INTEGER_REPRESENTATIONS:
        parameter["bits"] = _require_positive_integer(
            "parameter %s bits" % owner, record.get("bits")
        )
        domain = representable_domain(representation, parameter["bits"])
    else:
        domain = representable_domain(representation)
    lower = record.get("lower_limit")
    upper = record.get("upper_limit")
    if lower is not None:
        lower = _require_number("parameter %s lower_limit" % owner, lower)
        domain["lower"] = lower if domain["lower"] is None else max(domain["lower"], lower)
    if upper is not None:
        upper = _require_number("parameter %s upper_limit" % owner, upper)
        domain["upper"] = upper if domain["upper"] is None else min(domain["upper"], upper)
    if (
        domain["lower"] is not None
        and domain["upper"] is not None
        and domain["lower"] > domain["upper"]
    ):
        raise ValueError("parameter %s has an empty value domain" % owner)
    parameter["domain"] = domain
    # Carry the declared limits back out so normalizing an already normalized
    # parameter is idempotent. Without them a second pass rebuilds the domain
    # from the representation alone and silently widens it.
    parameter["lower_limit"] = lower
    parameter["upper_limit"] = upper
    if "value" not in record:
        raise ValueError("parameter %s carries no current value" % owner)
    parameter["value"] = record["value"]
    return parameter


def validate_store(parameters):
    """Normalize the store; an identifier is unique per application process."""
    if not isinstance(parameters, (list, tuple)):
        raise ValueError("parameters must be a list, got %r" % (parameters,))
    store = []
    seen = set()
    for raw in parameters:
        record = validate_parameter(raw)
        key = (record["application_process_id"], record["parameter_id"])
        if key in seen:
            raise ValueError(
                "application process %s already holds a parameter named %s" % key
            )
        seen.add(key)
        store.append(record)
    return store


def value_fits(parameter):
    """Check a stored value against the definition it is stored under."""
    record = validate_parameter(parameter)
    representation = record["representation"]
    value = record["value"]
    if representation == "boolean":
        if not isinstance(value, bool):
            return {"fits": False, "reason": "stored value %r is not a boolean" % (value,)}
        return {"fits": True, "reason": None}
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return {"fits": False, "reason": "stored value %r is not a number" % (value,)}
    if representation in INTEGER_REPRESENTATIONS and not isinstance(value, int):
        return {"fits": False, "reason": "stored value %r is not a whole number" % (value,)}
    domain = record["domain"]
    if domain["lower"] is not None and value < domain["lower"]:
        return {
            "fits": False,
            "reason": "stored value %r is below the domain lower bound %r"
            % (value, domain["lower"]),
        }
    if domain["upper"] is not None and value > domain["upper"]:
        return {
            "fits": False,
            "reason": "stored value %r is above the domain upper bound %r"
            % (value, domain["upper"]),
        }
    return {"fits": True, "reason": None}


def validate_request(identifiers):
    """Normalize the requested identifier list and record what repeats."""
    if not isinstance(identifiers, (list, tuple)):
        raise ValueError("requested identifiers must be a list, got %r" % (identifiers,))
    if not identifiers:
        raise ValueError(
            "a parameter value report request names the parameters it wants; an "
            "empty list is not a whole-store sweep"
        )
    ordered = []
    repeated = []
    seen = set()
    for index, raw in enumerate(identifiers):
        value = _require_identifier("requested identifier %d" % index, raw)
        if value in seen:
            if value not in repeated:
                repeated.append(value)
            continue
        seen.add(value)
        ordered.append(value)
    return {"identifiers": ordered, "repeated": repeated, "requested_count": len(ordered)}


def resolve_request(parameters, application_process_id, identifiers):
    """Split the requested identifiers into resolved and unknown, in order."""
    apid = _require_identifier("application_process_id", application_process_id)
    store = validate_store(parameters)
    request = validate_request(identifiers)
    index = {
        record["parameter_id"]: record
        for record in store
        if record["application_process_id"] == apid
    }
    resolved = []
    unknown = []
    for value in request["identifiers"]:
        if value in index:
            resolved.append(index[value])
        else:
            unknown.append(value)
    return {
        "application_process_id": apid,
        "resolved": resolved,
        "unknown": unknown,
        "repeated": request["repeated"],
        "requested_count": request["requested_count"],
        "held_count": len(index),
    }


def failure_notifications(resolution):
    """One notification per unresolved identifier, in request order."""
    if not isinstance(resolution, dict):
        raise ValueError("resolution must be a mapping, got %r" % (resolution,))
    unknown = resolution.get("unknown")
    if not isinstance(unknown, (list, tuple)):
        raise ValueError("resolution unknown must be a list")
    return [
        {
            "application_process_id": resolution.get("application_process_id"),
            "parameter_id": value,
            "failure": "no-such-on-board-parameter",
        }
        for value in unknown
    ]


def value_report_entry(parameter):
    """Report entry for one parameter: identity, representation, value."""
    record = validate_parameter(parameter)
    return {
        "application_process_id": record["application_process_id"],
        "parameter_id": record["parameter_id"],
        "representation": record["representation"],
        "value": record["value"],
    }


def build_value_report(parameters, application_process_id, identifiers):
    """Assemble the value report, or decline to when nothing resolved."""
    resolution = resolve_request(parameters, application_process_id, identifiers)
    notifications = failure_notifications(resolution)
    if not resolution["resolved"]:
        return {
            "generated": False,
            "report": None,
            "notifications": notifications,
            "withheld": [],
            "resolution": resolution,
        }
    entries = []
    withheld = []
    for record in resolution["resolved"]:
        check = value_fits(record)
        if check["fits"]:
            entries.append(value_report_entry(record))
        else:
            withheld.append(
                {"parameter_id": record["parameter_id"], "reason": check["reason"]}
            )
    report = {
        "application_process_id": resolution["application_process_id"],
        "entries": entries,
        "reported_count": len(entries),
        "withheld_count": len(withheld),
        "unknown_count": len(resolution["unknown"]),
        "requested_count": resolution["requested_count"],
    }
    return {
        "generated": True,
        "report": report,
        "notifications": notifications,
        "withheld": withheld,
        "resolution": resolution,
    }


def report_is_complete(report):
    """Check a received report's own totals against what it carries."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping, got %r" % (report,))
    entries = report.get("entries")
    if not isinstance(entries, (list, tuple)):
        raise ValueError("report entries must be a list")
    declared = report.get("reported_count")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared < 0:
        raise ValueError("report reported_count must be a non-negative integer")
    findings = []
    if len(entries) != declared:
        findings.append(
            "report declares %d entries but carries %d" % (declared, len(entries))
        )
    ids = [entry.get("parameter_id") for entry in entries]
    if len(set(ids)) != len(ids):
        findings.append("report carries the same parameter more than once")
    accounted = (
        declared
        + (report.get("withheld_count") or 0)
        + (report.get("unknown_count") or 0)
    )
    requested = report.get("requested_count")
    if isinstance(requested, int) and not isinstance(requested, bool):
        if accounted != requested:
            findings.append(
                "report accounts for %d of the %d identifiers requested"
                % (accounted, requested)
            )
    return {"complete": not findings, "findings": findings}


def assess_value_report(parameters, application_process_id, identifiers):
    """Full clause 6.20.4.1 handling: resolution, report, notifications."""
    outcome = build_value_report(parameters, application_process_id, identifiers)
    resolution = outcome["resolution"]
    findings = []
    for value in resolution["repeated"]:
        findings.append(
            "identifier %r was requested more than once and is reported once" % value
        )
    for notification in outcome["notifications"]:
        findings.append(
            "identifier %r resolves to no parameter of application process %s"
            % (notification["parameter_id"], notification["application_process_id"])
        )
    for item in outcome["withheld"]:
        findings.append(
            "parameter %s is withheld: %s" % (item["parameter_id"], item["reason"])
        )
    if not outcome["generated"]:
        findings.append(
            "no requested identifier resolved; the request fails at start and no "
            "report is generated"
        )
        return {
            "generated": False,
            "report": None,
            "reported_ids": [],
            "withheld_ids": [],
            "unknown_ids": list(resolution["unknown"]),
            "notifications": outcome["notifications"],
            "complete": False,
            "verdict": VERDICT_FAILED_START,
            "findings": findings,
        }
    completeness = report_is_complete(outcome["report"])
    findings.extend(completeness["findings"])
    clean = completeness["complete"] and not outcome["withheld"]
    return {
        "generated": True,
        "report": outcome["report"],
        "reported_ids": [entry["parameter_id"] for entry in outcome["report"]["entries"]],
        "withheld_ids": [item["parameter_id"] for item in outcome["withheld"]],
        "unknown_ids": list(resolution["unknown"]),
        "notifications": outcome["notifications"],
        "complete": completeness["complete"],
        "verdict": VERDICT_REPORTED if clean else VERDICT_DEFECTIVE,
        "findings": findings,
    }
