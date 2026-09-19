"""Binding and grading of template arguments in a simulation configuration.

Anchor: ECSS-E-ST-40-08 clause 5.2.1.2 (template argument requirements -- the
nine obligations an argument list supplied to a parameterised catalogue element
has to meet before the element can be instantiated). Paraphrased into an
implementable procedure; no standard text is reproduced.

The nine normative items implemented here
-----------------------------------------
a. Every argument names a parameter the template declares.
b. No parameter receives two arguments, whether by position or by name.
c. Every mandatory parameter receives an argument.
d. An optional parameter left unsupplied carries a declared default.
e. Positional arguments are contiguous from the first parameter and all of
   them precede the first named argument.
f. No positional index reaches past the declared parameter list.
g. Each supplied value conforms to the declared parameter type.
h. Each supplied value satisfies the declared constraint: an inclusive numeric
   range, membership of an allowed set, or a string length bound.
i. A value declared as a reference resolves to an element the configuration
   actually holds.

The binder returns the resolved argument map together with a per-item verdict,
so a template that is one default short is distinguishable from one whose
argument list is wired to the wrong parameters.
"""

__all__ = [
    "NORMATIVE_ITEMS",
    "NORMATIVE_ITEM_COUNT",
    "SUPPORTED_TYPES",
    "build_parameter_table",
    "argument_form",
    "value_conforms_to_type",
    "constraint_violation",
    "bind_arguments",
    "assess_template_arguments",
    "satisfied_item_count",
]

NORMATIVE_ITEMS = (
    "argument-names-a-declared-parameter",
    "no-parameter-bound-twice",
    "every-mandatory-parameter-supplied",
    "unsupplied-optional-has-a-default",
    "positional-arguments-contiguous-and-first",
    "positional-index-inside-parameter-list",
    "value-conforms-to-declared-type",
    "value-satisfies-declared-constraint",
    "reference-value-resolves",
)
NORMATIVE_ITEM_COUNT = len(NORMATIVE_ITEMS)

SUPPORTED_TYPES = ("Int32", "Float64", "Bool", "String8", "Reference")


def _require_text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty or blank" % label)
    return text


def build_parameter_table(parameters):
    """Return the ordered parameter list and a name index over it.

    Each parameter is a mapping with 'name' and 'type', optionally 'mandatory'
    (default True), 'default', 'minimum', 'maximum', 'allowed', 'max_length'.
    """
    if not isinstance(parameters, (list, tuple)):
        raise ValueError("parameters must be a sequence of parameter declarations")
    if not parameters:
        raise ValueError("a template must declare at least one parameter")
    ordered = []
    index = {}
    for position, spec in enumerate(parameters):
        if not isinstance(spec, dict):
            raise ValueError("parameters[%d] must be a mapping" % position)
        for key in ("name", "type"):
            if key not in spec:
                raise ValueError("parameters[%d] is missing '%s'" % (position, key))
        name = _require_text(spec["name"], "parameters[%d]['name']" % position)
        declared = _require_text(spec["type"], "parameters[%d]['type']" % position)
        if declared not in SUPPORTED_TYPES:
            raise ValueError(
                "parameters[%d] declares unsupported type %r (supported: %s)"
                % (position, declared, ", ".join(SUPPORTED_TYPES))
            )
        if name in index:
            raise ValueError("template declares parameter %r twice" % name)
        mandatory = spec.get("mandatory", True)
        if not isinstance(mandatory, bool):
            raise ValueError("parameters[%d]['mandatory'] must be a boolean" % position)
        if mandatory and "default" in spec:
            raise ValueError(
                "parameters[%d] %r is mandatory and cannot carry a default" % (position, name)
            )
        record = dict(spec)
        record["name"] = name
        record["type"] = declared
        record["mandatory"] = mandatory
        record["position"] = position
        ordered.append(record)
        index[name] = record
    return ordered, index


def argument_form(argument, order):
    """Return ('positional', index) or ('named', name) for one argument."""
    if not isinstance(argument, dict):
        raise ValueError("argument[%d] must be a mapping" % order)
    has_name = "name" in argument
    has_index = "index" in argument
    if has_name and has_index:
        raise ValueError("argument[%d] gives both a name and a position" % order)
    if not has_name and not has_index:
        raise ValueError("argument[%d] gives neither a name nor a position" % order)
    if "value" not in argument:
        raise ValueError("argument[%d] carries no value" % order)
    if has_index:
        idx = argument["index"]
        if not isinstance(idx, int) or isinstance(idx, bool):
            raise ValueError("argument[%d] position must be an integer" % order)
        if idx < 0:
            raise ValueError("argument[%d] position must not be negative" % order)
        return ("positional", idx)
    return ("named", _require_text(argument["name"], "argument[%d]['name']" % order))


def value_conforms_to_type(value, declared):
    """Return True when the value matches the declared parameter type."""
    if declared not in SUPPORTED_TYPES:
        raise ValueError("unsupported declared type %r" % (declared,))
    if declared == "Bool":
        return isinstance(value, bool)
    if declared == "Int32":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared == "Float64":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, str)


def constraint_violation(value, parameter):
    """Return a finding string when the value breaks a declared constraint."""
    if not isinstance(parameter, dict):
        raise ValueError("parameter must be a mapping")
    allowed = parameter.get("allowed")
    if allowed is not None:
        if not isinstance(allowed, (list, tuple, set, frozenset)) or not allowed:
            raise ValueError("'allowed' must be a non-empty collection")
        if value not in allowed:
            return "value %r is outside the allowed set" % (value,)
    minimum = parameter.get("minimum")
    maximum = parameter.get("maximum")
    if minimum is not None or maximum is not None:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return "a numeric bound was declared but the value is not numeric"
        if minimum is not None and float(value) < float(minimum):
            return "value %r is below the inclusive minimum %r" % (value, minimum)
        if maximum is not None and float(value) > float(maximum):
            return "value %r is above the inclusive maximum %r" % (value, maximum)
    max_length = parameter.get("max_length")
    if max_length is not None:
        if not isinstance(max_length, int) or isinstance(max_length, bool) or max_length < 0:
            raise ValueError("'max_length' must be a non-negative integer")
        if isinstance(value, str) and len(value) > max_length:
            return "value is %d characters, over the %d-character bound" % (
                len(value), max_length
            )
    return None


def _fail(items, findings, item, text):
    items[item] = False
    findings.append(text)


def bind_arguments(parameters, arguments, known_elements=None):
    """Bind an argument list to a parameter table and grade the nine items."""
    ordered, index = build_parameter_table(parameters)
    if not isinstance(arguments, (list, tuple)):
        raise ValueError("arguments must be a sequence")
    if known_elements is None:
        known_elements = ()
    if not isinstance(known_elements, (list, tuple, set, frozenset)):
        raise ValueError("known_elements must be a collection of element paths")

    items = {name: True for name in NORMATIVE_ITEMS}
    findings = []
    bound = {}
    seen_named = False
    expected_position = 0

    for order, argument in enumerate(arguments):
        form, key = argument_form(argument, order)
        value = argument["value"]
        if form == "positional":
            if seen_named:
                _fail(items, findings, NORMATIVE_ITEMS[4],
                      "positional argument at order %d follows a named argument" % order)
            if key != expected_position:
                _fail(items, findings, NORMATIVE_ITEMS[4],
                      "positional argument at order %d targets position %d, expected %d"
                      % (order, key, expected_position))
            expected_position = key + 1
            if key >= len(ordered):
                _fail(items, findings, NORMATIVE_ITEMS[5],
                      "positional argument at order %d reaches past the %d declared parameters"
                      % (order, len(ordered)))
                continue
            parameter = ordered[key]
        else:
            seen_named = True
            parameter = index.get(key)
            if parameter is None:
                _fail(items, findings, NORMATIVE_ITEMS[0],
                      "argument %r names no declared parameter" % key)
                continue

        if parameter["name"] in bound:
            _fail(items, findings, NORMATIVE_ITEMS[1],
                  "parameter %r is bound more than once" % parameter["name"])
            continue
        bound[parameter["name"]] = value

        if not value_conforms_to_type(value, parameter["type"]):
            _fail(items, findings, NORMATIVE_ITEMS[6],
                  "parameter %r declares %s but the value is %s"
                  % (parameter["name"], parameter["type"], type(value).__name__))
            continue

        violation = constraint_violation(value, parameter)
        if violation:
            _fail(items, findings, NORMATIVE_ITEMS[7],
                  "parameter %r: %s" % (parameter["name"], violation))

        if parameter["type"] == "Reference" and value not in known_elements:
            _fail(items, findings, NORMATIVE_ITEMS[8],
                  "parameter %r references %r, which the configuration does not hold"
                  % (parameter["name"], value))

    for parameter in ordered:
        if parameter["name"] in bound:
            continue
        if parameter["mandatory"]:
            _fail(items, findings, NORMATIVE_ITEMS[2],
                  "mandatory parameter %r received no argument" % parameter["name"])
        elif "default" not in parameter:
            _fail(items, findings, NORMATIVE_ITEMS[3],
                  "optional parameter %r was not supplied and declares no default"
                  % parameter["name"])
        else:
            bound[parameter["name"]] = parameter["default"]

    return {
        "bound": bound,
        "items": items,
        "findings": findings,
        "parameter_count": len(ordered),
        "argument_count": len(arguments),
    }


def satisfied_item_count(items):
    """Return how many of the nine normative items are satisfied."""
    if not isinstance(items, dict):
        raise ValueError("items must be the mapping produced by bind_arguments")
    missing = [name for name in NORMATIVE_ITEMS if name not in items]
    if missing:
        raise ValueError("items is missing verdicts for: %s" % ", ".join(missing))
    return sum(1 for name in NORMATIVE_ITEMS if items[name])


def assess_template_arguments(spec):
    """Run the full clause 5.2.1.2 template-argument assessment.

    spec keys: 'parameters', 'arguments', optional 'known_elements'.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("parameters", "arguments"):
        if key not in spec:
            raise ValueError("spec is missing required key '%s'" % key)
    result = bind_arguments(
        spec["parameters"], spec["arguments"], spec.get("known_elements")
    )
    satisfied = satisfied_item_count(result["items"])
    result["satisfied"] = satisfied
    result["item_count"] = NORMATIVE_ITEM_COUNT
    result["compliant"] = satisfied == NORMATIVE_ITEM_COUNT
    return result
