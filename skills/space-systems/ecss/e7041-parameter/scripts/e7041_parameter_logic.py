"""On-board control procedure parameter declaration and argument binding.

Anchor: ECSS-E-ST-70-41C clause 6.18.3.2 (the OBCP parameter). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate a procedure's parameter declaration: names, types, widths,
   numeric ranges, enumerated sets and defaults, plus the ordering rule that
   keeps positional binding unambiguous.
2. Bind an argument list -- ordered or keyed by name -- to that declaration,
   applying declared defaults to omitted optional parameters.
3. Check every bound value: type compatibility first, then range or
   enumerated membership.
4. Compute the encoded size of the bound set from the declared widths, not
   from the values, and round up to whole octets.
"""

import math

__all__ = [
    "PARAMETER_TYPES",
    "NUMERIC_TYPES",
    "BITS_PER_OCTET",
    "validate_parameter_definition",
    "validate_declaration",
    "type_accepts",
    "check_value",
    "bind_arguments",
    "encoded_size_bits",
    "encoded_size_octets",
    "assess_obcp_parameters",
]

PARAMETER_TYPES = ("unsigned", "signed", "real", "boolean", "enumerated")
NUMERIC_TYPES = ("unsigned", "signed", "real")
BITS_PER_OCTET = 8


def _require_text(value, label):
    """Return value as a non-empty stripped string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _require_number(value, label):
    """Return value as a finite float, refusing bools and non-numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return result


def type_accepts(parameter_type, value):
    """Return True when a declared type can hold the supplied Python value."""
    if parameter_type not in PARAMETER_TYPES:
        raise ValueError("unknown parameter type %r" % (parameter_type,))
    if parameter_type == "boolean":
        return isinstance(value, bool)
    if isinstance(value, bool):
        # A boolean is not a narrow integer; the declaration says which one
        # the procedure reads and the two are not interchangeable.
        return False
    if parameter_type == "unsigned":
        return isinstance(value, int) and value >= 0
    if parameter_type == "signed":
        return isinstance(value, int)
    if parameter_type == "real":
        return isinstance(value, (int, float))
    return isinstance(value, (int, str))


def validate_parameter_definition(definition):
    """Return a normalised parameter definition."""
    if not isinstance(definition, dict):
        raise ValueError("parameter definition must be a mapping, got %r"
                         % (definition,))
    name = _require_text(definition.get("name"), "parameter name")
    parameter_type = definition.get("type")
    if parameter_type not in PARAMETER_TYPES:
        raise ValueError(
            "parameter %s has type %r, not one of %s"
            % (name, parameter_type, ", ".join(PARAMETER_TYPES))
        )
    bits = definition.get("bits")
    if isinstance(bits, bool) or not isinstance(bits, int):
        raise ValueError("parameter %s must declare an integer width in bits" % name)
    if bits <= 0:
        raise ValueError("parameter %s must declare a positive width, got %d"
                         % (name, bits))
    if parameter_type == "boolean" and bits != 1:
        raise ValueError("boolean parameter %s must declare a width of 1 bit" % name)
    required = definition.get("required", True)
    if not isinstance(required, bool):
        raise ValueError("parameter %s 'required' must be a boolean" % name)
    values = None
    minimum = None
    maximum = None
    if parameter_type == "enumerated":
        values = definition.get("values")
        if not isinstance(values, (list, tuple)) or not values:
            raise ValueError(
                "enumerated parameter %s must declare a non-empty value set" % name
            )
        seen = []
        for value in values:
            if isinstance(value, bool) or not isinstance(value, (int, str)):
                raise ValueError(
                    "enumerated parameter %s takes integer or string values" % name
                )
            if value in seen:
                raise ValueError(
                    "enumerated parameter %s lists %r twice" % (name, value)
                )
            seen.append(value)
        values = list(seen)
    elif parameter_type in NUMERIC_TYPES:
        # An explicit None means "no bound declared", so re-validating an
        # already normalised definition is idempotent.
        if definition.get("minimum") is not None:
            minimum = _require_number(definition["minimum"], "%s minimum" % name)
        if definition.get("maximum") is not None:
            maximum = _require_number(definition["maximum"], "%s maximum" % name)
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError(
                "parameter %s declares minimum %g above maximum %g"
                % (name, minimum, maximum)
            )
        if parameter_type == "unsigned" and minimum is not None and minimum < 0.0:
            raise ValueError(
                "unsigned parameter %s cannot declare a negative minimum" % name
            )
    normalised = {
        "name": name,
        "type": parameter_type,
        "bits": bits,
        "required": required,
        "values": values,
        "minimum": minimum,
        "maximum": maximum,
        "default": None,
        "has_default": False,
    }
    if definition.get("has_default", "default" in definition):
        default = definition.get("default")
        usable, reason = check_value(normalised, default)
        if not usable:
            raise ValueError(
                "parameter %s declares a default that fails its own declaration: %s"
                % (name, reason)
            )
        normalised["default"] = default
        normalised["has_default"] = True
    return normalised


def validate_declaration(declaration):
    """Return the ordered, normalised parameter declaration of a procedure."""
    if not isinstance(declaration, (list, tuple)):
        raise ValueError("declaration must be a sequence of parameter definitions")
    normalised = []
    names = []
    optional_seen = None
    for definition in declaration:
        parameter = validate_parameter_definition(definition)
        if parameter["name"] in names:
            raise ValueError("parameter %s is declared twice" % parameter["name"])
        if parameter["required"] and optional_seen is not None:
            raise ValueError(
                "required parameter %s follows optional parameter %s; positional "
                "binding past that point is ambiguous"
                % (parameter["name"], optional_seen)
            )
        if not parameter["required"]:
            optional_seen = parameter["name"]
        names.append(parameter["name"])
        normalised.append(parameter)
    return normalised


def check_value(parameter, value):
    """Return (usable, reason) for one value against one parameter definition."""
    if not isinstance(parameter, dict) or "type" not in parameter:
        raise ValueError("parameter must be a normalised definition mapping")
    if not type_accepts(parameter["type"], value):
        return (
            False,
            "value %r is not compatible with declared type %s"
            % (value, parameter["type"]),
        )
    if parameter["type"] == "enumerated":
        if value not in parameter["values"]:
            return (
                False,
                "value %r is outside the enumerated set of %s"
                % (value, parameter["name"]),
            )
        return (True, None)
    if parameter["type"] in NUMERIC_TYPES:
        numeric = float(value)
        if parameter["minimum"] is not None and numeric < parameter["minimum"]:
            return (
                False,
                "value %r is below the declared minimum %g of %s"
                % (value, parameter["minimum"], parameter["name"]),
            )
        if parameter["maximum"] is not None and numeric > parameter["maximum"]:
            return (
                False,
                "value %r is above the declared maximum %g of %s"
                % (value, parameter["maximum"], parameter["name"]),
            )
    return (True, None)


def bind_arguments(declaration, arguments):
    """Bind an ordered or named argument list to a parameter declaration."""
    parameters = validate_declaration(declaration)
    findings = []
    supplied = {}
    if isinstance(arguments, dict):
        names = [p["name"] for p in parameters]
        for key, value in arguments.items():
            key_text = _require_text(key, "argument name")
            if key_text not in names:
                findings.append(
                    "argument %s names no declared parameter" % key_text
                )
                continue
            supplied[key_text] = value
    elif isinstance(arguments, (list, tuple)):
        if len(arguments) > len(parameters):
            findings.append(
                "%d arguments supplied for %d declared parameters"
                % (len(arguments), len(parameters))
            )
        for parameter, value in zip(parameters, arguments):
            supplied[parameter["name"]] = value
    else:
        raise ValueError("arguments must be a sequence or a mapping")
    bound = {}
    for parameter in parameters:
        name = parameter["name"]
        if name in supplied:
            value = supplied[name]
            usable, reason = check_value(parameter, value)
            if usable:
                bound[name] = value
            else:
                findings.append(reason)
            continue
        if parameter["has_default"]:
            bound[name] = parameter["default"]
            continue
        if parameter["required"]:
            findings.append("required parameter %s has no argument" % name)
        else:
            findings.append(
                "optional parameter %s was omitted and declares no default" % name
            )
    return {"bound": bound, "findings": findings, "parameters": parameters}


def encoded_size_bits(declaration, bound):
    """Return the encoded width of the bound set, from the declaration."""
    parameters = validate_declaration(declaration)
    if not isinstance(bound, dict):
        raise ValueError("bound must be a mapping of parameter name to value")
    total = 0
    for parameter in parameters:
        if parameter["name"] in bound:
            total += parameter["bits"]
    return total


def encoded_size_octets(declaration, bound):
    """Return the encoded size of the bound set rounded up to whole octets."""
    bits = encoded_size_bits(declaration, bound)
    return (bits + BITS_PER_OCTET - 1) // BITS_PER_OCTET


def assess_obcp_parameters(spec):
    """Run the clause 6.18.3.2 parameter assessment for one start request.

    spec keys: declaration, arguments, optional max_octets budget for the
    parameter area of the start request.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("declaration", "arguments"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    result = bind_arguments(spec["declaration"], spec["arguments"])
    findings = list(result["findings"])
    octets = encoded_size_octets(result["parameters"], result["bound"])
    budget = spec.get("max_octets")
    if budget is not None:
        if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
            raise ValueError("max_octets must be a positive integer, got %r"
                             % (budget,))
        if octets > budget:
            findings.append(
                "the bound parameter set encodes to %d octets, past the %d octets "
                "the start request allows" % (octets, budget)
            )
    return {
        "bound": result["bound"],
        "bound_count": len(result["bound"]),
        "declared_count": len(result["parameters"]),
        "encoded_size_bits": encoded_size_bits(result["parameters"], result["bound"]),
        "encoded_size_octets": octets,
        "findings": findings,
        "usable": not findings,
    }
