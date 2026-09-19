"""Parameter communication between an OBCP and the engine that hosts it.

Anchor: ECSS-E-ST-70-41C clause 6.18.4.7 (paraphrased into an
implementable procedure; no standard text is reproduced).

The clause governs how an on-board control procedure and the OBCP
engine exchange parameters: which parameters a procedure declares, how
an activation request supplies values for them, and which of them the
engine has to keep observable while the procedure runs.

Three ideas carry the whole clause.

Declaration first. A procedure declares its parameter interface before
anybody activates it: a name, a direction, a type, and for an input a
range and optionally a default. An activation cannot invent a
parameter, and the engine cannot guess one.

Binding is by name, not by position. An activation supplies a mapping
of names to values. A name the interface does not declare is a
rejection, not something to drop quietly: it usually means the ground
is holding a different version of the procedure than the one loaded,
and silently ignoring it lets the run continue on the wrong values.

Direction is a permission. An input parameter is written by the
activation and read by the procedure; an output parameter is written
by the procedure and read by the ground; an in-out is both. Supplying
a value for an output-only parameter is a rejection, and so is a
procedure writing to an input-only one. The outputs are what the
engine must make observable while the run is in progress -- a
procedure whose interface declares none is a procedure the ground can
watch only by its completion.

Stdlib only, offline, deterministic.
"""

DIRECTION_IN = "in"
DIRECTION_OUT = "out"
DIRECTION_IN_OUT = "in-out"
DIRECTIONS = (DIRECTION_IN, DIRECTION_OUT, DIRECTION_IN_OUT)

TYPE_INTEGER = "integer"
TYPE_REAL = "real"
TYPE_BOOLEAN = "boolean"
TYPE_ENUMERATED = "enumerated"
TYPES = (TYPE_INTEGER, TYPE_REAL, TYPE_BOOLEAN, TYPE_ENUMERATED)

FINDING_UNKNOWN_PARAMETER = "activation-supplied-an-undeclared-parameter"
FINDING_MANDATORY_MISSING = "mandatory-input-parameter-was-not-supplied"
FINDING_DEFAULT_SUBSTITUTED = "omitted-input-parameter-took-its-declared-default"
FINDING_WRONG_TYPE = "supplied-value-does-not-match-the-declared-type"
FINDING_OUT_OF_RANGE = "supplied-value-falls-outside-the-declared-range"
FINDING_WRITE_TO_INPUT = "procedure-wrote-to-an-input-only-parameter"
FINDING_SUPPLIED_AN_OUTPUT = "activation-supplied-a-value-for-an-output-only-parameter"
FINDING_NO_OBSERVABLE_OUTPUT = "procedure-declares-no-observable-output-parameter"


def _name(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("parameter name must be a non-empty string, got %r" % (value,))
    return value.strip()


def _number(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def _matches_type(declared_type, value):
    if declared_type == TYPE_BOOLEAN:
        return isinstance(value, bool)
    if declared_type == TYPE_INTEGER:
        return isinstance(value, int) and not isinstance(value, bool)
    if declared_type == TYPE_REAL:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, str) and bool(value.strip())


def normalise_parameter(spec):
    """Validate one declared parameter of a procedure's interface."""
    if not isinstance(spec, dict):
        raise ValueError("parameter declaration must be a mapping, got %r" % (spec,))
    name = _name(spec.get("name"))
    direction = spec.get("direction", DIRECTION_IN)
    if direction not in DIRECTIONS:
        raise ValueError(
            "parameter %s has direction %r, expected one of %s"
            % (name, direction, ", ".join(DIRECTIONS))
        )
    declared_type = spec.get("type", TYPE_REAL)
    if declared_type not in TYPES:
        raise ValueError(
            "parameter %s has type %r, expected one of %s"
            % (name, declared_type, ", ".join(TYPES))
        )
    low = spec.get("low")
    high = spec.get("high")
    if declared_type in (TYPE_INTEGER, TYPE_REAL) and low is not None and high is not None:
        low = _number("parameter %s low bound" % name, low)
        high = _number("parameter %s high bound" % name, high)
        if high < low:
            raise ValueError("parameter %s has an inverted range" % name)
    elif (low is None) != (high is None):
        raise ValueError("parameter %s declares only one end of its range" % name)
    permitted = spec.get("permitted")
    if declared_type == TYPE_ENUMERATED:
        if not isinstance(permitted, (list, tuple)) or not permitted:
            raise ValueError("enumerated parameter %s needs a permitted value list" % name)
        permitted = [_name(v) for v in permitted]
    elif permitted is not None:
        raise ValueError("parameter %s is not enumerated but lists permitted values" % name)
    default = spec.get("default")
    mandatory = bool(spec.get("mandatory", default is None))
    if direction == DIRECTION_OUT:
        if default is not None:
            raise ValueError("output parameter %s cannot carry an activation default" % name)
        mandatory = False
    if default is not None and not _matches_type(declared_type, default):
        raise ValueError("parameter %s default does not match its declared type" % name)
    if mandatory and default is not None:
        raise ValueError("parameter %s is mandatory and also carries a default" % name)
    return {
        "name": name,
        "direction": direction,
        "type": declared_type,
        "low": low,
        "high": high,
        "permitted": permitted,
        "default": default,
        "mandatory": mandatory,
    }


def build_interface(declarations):
    """Turn a procedure's declared parameter list into a lookup by name."""
    if not isinstance(declarations, (list, tuple)):
        raise ValueError("declarations must be a list")
    interface = {}
    for spec in declarations:
        parameter = normalise_parameter(spec)
        if parameter["name"] in interface:
            raise ValueError("parameter %s is declared twice" % parameter["name"])
        interface[parameter["name"]] = parameter
    if not interface:
        raise ValueError("a procedure interface must declare at least one parameter")
    return interface


def observable_outputs(interface):
    """The parameters the engine keeps readable while the procedure runs."""
    if not isinstance(interface, dict) or not interface:
        raise ValueError("interface must be a non-empty mapping")
    return sorted(
        name
        for name, p in interface.items()
        if p["direction"] in (DIRECTION_OUT, DIRECTION_IN_OUT)
    )


def check_value(parameter, value):
    """Grade one supplied value against one declared parameter."""
    if not _matches_type(parameter["type"], value):
        return FINDING_WRONG_TYPE
    if parameter["type"] == TYPE_ENUMERATED:
        if value not in parameter["permitted"]:
            return FINDING_OUT_OF_RANGE
        return None
    if parameter["low"] is not None:
        numeric = float(value)
        if numeric < parameter["low"] or numeric > parameter["high"]:
            return FINDING_OUT_OF_RANGE
    return None


def bind_activation(interface, supplied):
    """Bind an activation's supplied arguments onto a declared interface."""
    if not isinstance(interface, dict) or not interface:
        raise ValueError("interface must be a non-empty mapping")
    if not isinstance(supplied, dict):
        raise ValueError("supplied arguments must be a mapping of names to values")
    bound = {}
    findings = []
    for name, value in sorted(supplied.items()):
        key = _name(name)
        parameter = interface.get(key)
        if parameter is None:
            findings.append({"parameter": key, "finding": FINDING_UNKNOWN_PARAMETER})
            continue
        if parameter["direction"] == DIRECTION_OUT:
            findings.append({"parameter": key, "finding": FINDING_SUPPLIED_AN_OUTPUT})
            continue
        problem = check_value(parameter, value)
        if problem is not None:
            findings.append({"parameter": key, "finding": problem})
            continue
        bound[key] = value
    for name, parameter in sorted(interface.items()):
        if name in bound or parameter["direction"] == DIRECTION_OUT:
            continue
        if any(f["parameter"] == name for f in findings):
            continue
        if parameter["default"] is not None:
            bound[name] = parameter["default"]
            findings.append({"parameter": name, "finding": FINDING_DEFAULT_SUBSTITUTED})
        elif parameter["mandatory"]:
            findings.append({"parameter": name, "finding": FINDING_MANDATORY_MISSING})
    return {"bound": bound, "findings": findings}


def check_procedure_writes(interface, writes):
    """Grade the parameters a running procedure tries to write back."""
    if not isinstance(writes, (list, tuple)):
        raise ValueError("writes must be a list of parameter names")
    findings = []
    for name in writes:
        key = _name(name)
        parameter = interface.get(key)
        if parameter is None:
            findings.append({"parameter": key, "finding": FINDING_UNKNOWN_PARAMETER})
        elif parameter["direction"] == DIRECTION_IN:
            findings.append({"parameter": key, "finding": FINDING_WRITE_TO_INPUT})
    return findings


def assess_parameter_communication(declarations, supplied, writes=None):
    """Grade a whole activation: binding, defaults, writes and observability."""
    interface = build_interface(declarations)
    binding = bind_activation(interface, supplied)
    findings = list(binding["findings"])
    if writes is not None:
        findings.extend(check_procedure_writes(interface, writes))
    outputs = observable_outputs(interface)
    if not outputs:
        findings.append({"parameter": None, "finding": FINDING_NO_OBSERVABLE_OUTPUT})
    blocking = [
        f
        for f in findings
        if f["finding"]
        not in (FINDING_DEFAULT_SUBSTITUTED, FINDING_NO_OBSERVABLE_OUTPUT)
    ]
    return {
        "bound": binding["bound"],
        "findings": findings,
        "observable_outputs": outputs,
        "declared_count": len(interface),
        "bound_count": len(binding["bound"]),
        "activation_accepted": not blocking,
    }
