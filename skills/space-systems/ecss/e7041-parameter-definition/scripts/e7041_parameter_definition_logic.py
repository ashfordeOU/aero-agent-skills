#!/usr/bin/env python3
"""The on-board parameter definition the parameter management service uses.

Anchor: ECSS-E-ST-70-41C clause 6.20.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Two normative items carry the clause, and both exist so that a later
report or set request can be answered:

    1  every parameter the service handles is named by a parameter
       identifier that is unique within its application process; the
       same name under another application process is another
       parameter
    2  every definition declares how its value is represented, so a
       value carried by a request can be checked against it before it
       is reported or written

Representations handled here:

    unsigned-integer   width in bits; domain 0 .. 2**bits - 1
    signed-integer     width in bits, two's complement; domain
                       -2**(bits-1) .. 2**(bits-1) - 1
    real               a floating point value; domain bounded only by
                       declared engineering limits
    boolean            exactly the two boolean values
    enumerated         exactly the declared codes
    octet-string       a bytes value no longer than the declared
                       length

Integer domains are derived with shifts, never with floating-point
exponentiation: 1 << bits is exact at every width, while a float power
is not correctly rounded and lands a count out at wide widths on some
platforms and not others.

Engineering limits are narrower than the representation, never wider.
The domain a value must satisfy is the intersection of the two, and a
value is decided against that intersection plus the representation's
own membership rule.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

REPRESENTATIONS = (
    "unsigned-integer",
    "signed-integer",
    "real",
    "boolean",
    "enumerated",
    "octet-string",
)

INTEGER_REPRESENTATIONS = ("unsigned-integer", "signed-integer")

NUMERIC_REPRESENTATIONS = ("unsigned-integer", "signed-integer", "real")

ACCESS_MODES = ("read-only", "read-write")

VERDICT_SOUND = "parameter-catalogue-sound"
VERDICT_UNSOUND = "parameter-catalogue-unsound"


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


def validate_parameter_definition(record):
    """Normalize one on-board parameter definition."""
    if not isinstance(record, dict):
        raise ValueError("definition must be a mapping, got %r" % (record,))
    apid = _require_identifier(
        "definition application_process_id", record.get("application_process_id")
    )
    parameter_id = _require_identifier(
        "definition parameter_id of %s" % apid, record.get("parameter_id")
    )
    owner = "%s/%s" % (apid, parameter_id)
    representation = _require_choice(
        "definition %s representation" % owner,
        record.get("representation"),
        REPRESENTATIONS,
    )
    definition = {
        "application_process_id": apid,
        "parameter_id": parameter_id,
        "representation": representation,
        "access": _require_choice(
            "definition %s access" % owner,
            record.get("access", "read-write"),
            ACCESS_MODES,
        ),
    }
    if representation in INTEGER_REPRESENTATIONS:
        definition["bits"] = _require_positive_integer(
            "definition %s bits" % owner, record.get("bits")
        )
        definition["representable"] = representable_domain(
            representation, definition["bits"]
        )
    elif representation == "enumerated":
        codes = record.get("codes")
        if not isinstance(codes, (list, tuple)) or not codes:
            raise ValueError(
                "definition %s must declare at least one enumerated code" % owner
            )
        seen = []
        for code in codes:
            value = _require_identifier("definition %s code" % owner, code)
            if value in seen:
                raise ValueError("definition %s repeats code %r" % (owner, value))
            seen.append(value)
        definition["codes"] = seen
        definition["representable"] = {"lower": None, "upper": None}
    elif representation == "octet-string":
        definition["length"] = _require_positive_integer(
            "definition %s length" % owner, record.get("length")
        )
        definition["representable"] = {"lower": None, "upper": None}
    else:
        definition["representable"] = representable_domain(representation)
    definition["limits"] = validate_limits(record, definition, owner)
    # Carry the declared limits back out so normalizing an already normalized
    # definition is idempotent. Without them a second pass rebuilds the
    # effective domain from the representation alone and silently widens it.
    definition["lower_limit"] = definition["limits"]["lower"]
    definition["upper_limit"] = definition["limits"]["upper"]
    definition["effective"] = effective_domain(definition)
    return definition


def validate_limits(record, definition, owner):
    """Read declared engineering limits and keep them inside the representation."""
    lower = record.get("lower_limit")
    upper = record.get("upper_limit")
    if lower is None and upper is None:
        return {"lower": None, "upper": None}
    if definition["representation"] not in NUMERIC_REPRESENTATIONS:
        raise ValueError(
            "definition %s declares engineering limits on a %s parameter"
            % (owner, definition["representation"])
        )
    if lower is not None:
        lower = _require_number("definition %s lower_limit" % owner, lower)
    if upper is not None:
        upper = _require_number("definition %s upper_limit" % owner, upper)
    if lower is not None and upper is not None and lower > upper:
        raise ValueError(
            "definition %s lower_limit %r is above its upper_limit %r"
            % (owner, lower, upper)
        )
    representable = definition["representable"]
    if representable["lower"] is not None:
        if lower is not None and lower < representable["lower"]:
            raise ValueError(
                "definition %s lower_limit %r falls below what %d bits can hold"
                % (owner, lower, definition["bits"])
            )
        if upper is not None and upper > representable["upper"]:
            raise ValueError(
                "definition %s upper_limit %r exceeds what %d bits can hold"
                % (owner, upper, definition["bits"])
            )
    return {"lower": lower, "upper": upper}


def effective_domain(definition):
    """Intersect the representable domain with the declared limits."""
    representable = definition["representable"]
    limits = definition["limits"]
    lower = representable["lower"]
    if limits["lower"] is not None:
        lower = limits["lower"] if lower is None else max(lower, limits["lower"])
    upper = representable["upper"]
    if limits["upper"] is not None:
        upper = limits["upper"] if upper is None else min(upper, limits["upper"])
    return {"lower": lower, "upper": upper}


def validate_catalogue(definitions):
    """Normalize a catalogue; an identifier is unique per application process."""
    if not isinstance(definitions, (list, tuple)):
        raise ValueError("definitions must be a list, got %r" % (definitions,))
    catalogue = []
    seen = set()
    for raw in definitions:
        record = validate_parameter_definition(raw)
        key = (record["application_process_id"], record["parameter_id"])
        if key in seen:
            raise ValueError(
                "application process %s already holds a parameter named %s" % key
            )
        seen.add(key)
        catalogue.append(record)
    return catalogue


def value_belongs(definition, value):
    """Decide whether a candidate value belongs to a parameter definition."""
    record = validate_parameter_definition(definition)
    representation = record["representation"]
    if representation == "boolean":
        if not isinstance(value, bool):
            return _rejected(record, "value %r is not a boolean" % (value,))
        return _accepted(record)
    if representation == "enumerated":
        if not isinstance(value, str) or value not in record["codes"]:
            return _rejected(
                record, "value %r is not one of the declared codes" % (value,)
            )
        return _accepted(record)
    if representation == "octet-string":
        if not isinstance(value, (bytes, bytearray)):
            return _rejected(record, "value %r is not a byte sequence" % (value,))
        if len(value) > record["length"]:
            return _rejected(
                record,
                "value is %d bytes, longer than the declared %d"
                % (len(value), record["length"]),
            )
        return _accepted(record)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return _rejected(record, "value %r is not a number" % (value,))
    if representation in INTEGER_REPRESENTATIONS and not isinstance(value, int):
        return _rejected(record, "value %r is not a whole number" % (value,))
    domain = record["effective"]
    if domain["lower"] is not None and value < domain["lower"]:
        return _rejected(
            record, "value %r is below the effective lower bound %r"
            % (value, domain["lower"])
        )
    if domain["upper"] is not None and value > domain["upper"]:
        return _rejected(
            record, "value %r is above the effective upper bound %r"
            % (value, domain["upper"])
        )
    return _accepted(record)


def _accepted(record):
    return {
        "parameter_id": record["parameter_id"],
        "application_process_id": record["application_process_id"],
        "belongs": True,
        "reason": None,
    }


def _rejected(record, reason):
    return {
        "parameter_id": record["parameter_id"],
        "application_process_id": record["application_process_id"],
        "belongs": False,
        "reason": reason,
    }


def assess_catalogue(definitions):
    """Full clause 6.20.3 handling over a whole parameter catalogue."""
    catalogue = validate_catalogue(definitions)
    findings = []
    narrowed = []
    for record in catalogue:
        owner = "%s/%s" % (record["application_process_id"], record["parameter_id"])
        if record["representation"] == "real" and (
            record["limits"]["lower"] is None or record["limits"]["upper"] is None
        ):
            findings.append(
                "parameter %s is real with no bounded engineering domain; any "
                "finite value will be accepted" % owner
            )
        if record["effective"] != record["representable"]:
            narrowed.append(owner)
    per_process = {}
    for record in catalogue:
        per_process.setdefault(record["application_process_id"], []).append(
            record["parameter_id"]
        )
    return {
        "catalogue": catalogue,
        "parameter_count": len(catalogue),
        "application_process_count": len(per_process),
        "parameters_per_process": per_process,
        "narrowed_by_limits": narrowed,
        "writable_count": sum(
            1 for record in catalogue if record["access"] == "read-write"
        ),
        "sound": not findings,
        "verdict": VERDICT_SOUND if not findings else VERDICT_UNSOUND,
        "findings": findings,
    }
