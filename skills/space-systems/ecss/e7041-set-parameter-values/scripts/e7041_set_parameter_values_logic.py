#!/usr/bin/env python3
"""Writing new values into the on-board parameters a request names.

Anchor: ECSS-E-ST-70-41C clause 6.20.4.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause's normative items reduce to seven implementable checks:

    1  the request carries instructions, each pairing a parameter
       identifier with the value to write, plus the application
       process holding them
    2  an instruction that resolves to no parameter of that process
       is refused
    3  an instruction addressing a read-only parameter is refused
    4  an instruction whose value falls outside the parameter's
       effective domain, or does not suit its representation, is
       refused
    5  the instructions that survive are applied even when a sibling
       is refused; nothing already written is withdrawn
    6  a request where no instruction survives fails at start and
       writes nothing at all
    7  the outcome carries applied and refused totals that account
       for every instruction the request carried

The three refusals are kept distinct -- no-such-parameter,
parameter-is-read-only, value-outside-domain -- because the ground
fix differs for each and a single rejection code hides which one it
was.

A parameter named more than once in one request is a ground defect.
The last instruction wins so that two runs of the same request leave
the same state, and the collision is raised as a finding.

The store is never mutated: apply_settings returns a new store and
leaves the one it was given as the pre-request record.

Integer domains come from shifts, never from floating-point
exponentiation: 1 << bits is exact at every width, while a float power
is not correctly rounded and lands a count out at wide widths on some
platforms and not others.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

REPRESENTATIONS = ("unsigned-integer", "signed-integer", "real", "boolean")

INTEGER_REPRESENTATIONS = ("unsigned-integer", "signed-integer")

ACCESS_MODES = ("read-only", "read-write")

REFUSAL_UNKNOWN = "no-such-on-board-parameter"
REFUSAL_READ_ONLY = "parameter-is-read-only"
REFUSAL_OUT_OF_DOMAIN = "value-outside-parameter-domain"

REFUSALS = (REFUSAL_UNKNOWN, REFUSAL_READ_ONLY, REFUSAL_OUT_OF_DOMAIN)

VERDICT_APPLIED = "parameter-set-applied"
VERDICT_PARTIAL = "parameter-set-partially-applied"
VERDICT_FAILED_START = "parameter-set-failed-start"


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
    """Normalize one stored parameter: definition, access mode, value."""
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
        "access": _require_choice(
            "parameter %s access" % owner,
            record.get("access", "read-write"),
            ACCESS_MODES,
        ),
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


def value_suits_parameter(parameter, value):
    """Check a candidate value against representation and effective domain."""
    record = validate_parameter(parameter)
    representation = record["representation"]
    if representation == "boolean":
        if not isinstance(value, bool):
            return {"suits": False, "reason": "value %r is not a boolean" % (value,)}
        return {"suits": True, "reason": None}
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return {"suits": False, "reason": "value %r is not a number" % (value,)}
    if representation in INTEGER_REPRESENTATIONS and not isinstance(value, int):
        return {"suits": False, "reason": "value %r is not a whole number" % (value,)}
    domain = record["domain"]
    if domain["lower"] is not None and value < domain["lower"]:
        return {
            "suits": False,
            "reason": "value %r is below the effective lower bound %r"
            % (value, domain["lower"]),
        }
    if domain["upper"] is not None and value > domain["upper"]:
        return {
            "suits": False,
            "reason": "value %r is above the effective upper bound %r"
            % (value, domain["upper"]),
        }
    return {"suits": True, "reason": None}


def validate_instruction(record, index):
    """Normalize one identifier-and-value pair from the request."""
    if not isinstance(record, dict):
        raise ValueError("instruction %d must be a mapping, got %r" % (index, record))
    if "value" not in record:
        raise ValueError("instruction %d carries no value to write" % index)
    return {
        "parameter_id": _require_identifier(
            "instruction %d parameter_id" % index, record.get("parameter_id")
        ),
        "value": record["value"],
    }


def validate_instructions(instructions):
    """Normalize the instruction list, last writer winning on a collision."""
    if not isinstance(instructions, (list, tuple)):
        raise ValueError("instructions must be a list, got %r" % (instructions,))
    if not instructions:
        raise ValueError(
            "a parameter setting request carries at least one instruction; an "
            "empty request is not a successful no-op"
        )
    normalized = [
        validate_instruction(raw, index) for index, raw in enumerate(instructions)
    ]
    last = {}
    for item in normalized:
        last[item["parameter_id"]] = item
    ordered = []
    emitted = set()
    for item in normalized:
        key = item["parameter_id"]
        if key in emitted:
            continue
        emitted.add(key)
        ordered.append(last[key])
    repeated = [
        key
        for key in emitted
        if sum(1 for item in normalized if item["parameter_id"] == key) > 1
    ]
    return {
        "instructions": ordered,
        "repeated": sorted(repeated),
        "submitted_count": len(normalized),
        "distinct_count": len(ordered),
    }


def screen_instructions(parameters, application_process_id, instructions):
    """Decide each instruction: applicable, or refused with a distinct reason."""
    apid = _require_identifier("application_process_id", application_process_id)
    store = validate_store(parameters)
    request = validate_instructions(instructions)
    index = {
        record["parameter_id"]: record
        for record in store
        if record["application_process_id"] == apid
    }
    applicable = []
    refused = []
    for item in request["instructions"]:
        target = index.get(item["parameter_id"])
        if target is None:
            refused.append(
                {
                    "parameter_id": item["parameter_id"],
                    "refusal": REFUSAL_UNKNOWN,
                    "reason": "application process %s holds no parameter named %s"
                    % (apid, item["parameter_id"]),
                }
            )
            continue
        if target["access"] == "read-only":
            refused.append(
                {
                    "parameter_id": item["parameter_id"],
                    "refusal": REFUSAL_READ_ONLY,
                    "reason": "parameter %s is read-only" % item["parameter_id"],
                }
            )
            continue
        check = value_suits_parameter(target, item["value"])
        if not check["suits"]:
            refused.append(
                {
                    "parameter_id": item["parameter_id"],
                    "refusal": REFUSAL_OUT_OF_DOMAIN,
                    "reason": check["reason"],
                }
            )
            continue
        applicable.append({"parameter": target, "value": item["value"]})
    return {
        "application_process_id": apid,
        "applicable": applicable,
        "refused": refused,
        "repeated": request["repeated"],
        "submitted_count": request["submitted_count"],
        "distinct_count": request["distinct_count"],
    }


def apply_settings(parameters, application_process_id, instructions):
    """Apply what survives screening into a NEW store; never mutate the old."""
    screening = screen_instructions(parameters, application_process_id, instructions)
    store = validate_store(parameters)
    if not screening["applicable"]:
        return {
            "applied": False,
            "store": store,
            "writes": [],
            "refused": screening["refused"],
            "screening": screening,
        }
    pending = {
        item["parameter"]["parameter_id"]: item["value"]
        for item in screening["applicable"]
    }
    apid = screening["application_process_id"]
    new_store = []
    writes = []
    for record in store:
        updated = dict(record)
        if (
            record["application_process_id"] == apid
            and record["parameter_id"] in pending
        ):
            new_value = pending[record["parameter_id"]]
            writes.append(
                {
                    "parameter_id": record["parameter_id"],
                    "previous_value": record["value"],
                    "value": new_value,
                }
            )
            updated["value"] = new_value
        new_store.append(updated)
    order = [item["parameter"]["parameter_id"] for item in screening["applicable"]]
    writes.sort(key=lambda write: order.index(write["parameter_id"]))
    return {
        "applied": True,
        "store": new_store,
        "writes": writes,
        "refused": screening["refused"],
        "screening": screening,
    }


def outcome_accounts_for_request(outcome):
    """Check the applied and refused totals against the instruction count."""
    if not isinstance(outcome, dict):
        raise ValueError("outcome must be a mapping, got %r" % (outcome,))
    screening = outcome.get("screening")
    if not isinstance(screening, dict):
        raise ValueError("outcome carries no screening record")
    applied = len(outcome.get("writes") or [])
    refused = len(outcome.get("refused") or [])
    distinct = screening.get("distinct_count")
    findings = []
    if applied + refused != distinct:
        findings.append(
            "outcome accounts for %d of the %d distinct instructions"
            % (applied + refused, distinct)
        )
    reasons = {item["refusal"] for item in (outcome.get("refused") or [])}
    unknown_reasons = reasons - set(REFUSALS)
    if unknown_reasons:
        findings.append(
            "outcome carries refusal reasons outside the declared set: %s"
            % ", ".join(sorted(unknown_reasons))
        )
    return {"accounted": not findings, "findings": findings}


def assess_set_request(parameters, application_process_id, instructions):
    """Full clause 6.20.4.2 handling: screening, application, accounting."""
    outcome = apply_settings(parameters, application_process_id, instructions)
    screening = outcome["screening"]
    findings = []
    for key in screening["repeated"]:
        findings.append(
            "parameter %s is named more than once; the last instruction wins" % key
        )
    for item in outcome["refused"]:
        findings.append(
            "instruction on %s refused (%s): %s"
            % (item["parameter_id"], item["refusal"], item["reason"])
        )
    accounting = outcome_accounts_for_request(outcome)
    findings.extend(accounting["findings"])
    if not outcome["applied"]:
        findings.append(
            "no instruction survived screening; the request fails at start and "
            "nothing is written"
        )
        verdict = VERDICT_FAILED_START
    elif outcome["refused"]:
        verdict = VERDICT_PARTIAL
    else:
        verdict = VERDICT_APPLIED
    return {
        "verdict": verdict,
        "applied": outcome["applied"],
        "store": outcome["store"],
        "writes": outcome["writes"],
        "written_ids": [write["parameter_id"] for write in outcome["writes"]],
        "refused": outcome["refused"],
        "refused_ids": [item["parameter_id"] for item in outcome["refused"]],
        "applied_count": len(outcome["writes"]),
        "refused_count": len(outcome["refused"]),
        "accounted": accounting["accounted"],
        "findings": findings,
    }
