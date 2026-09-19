"""Grading of operation calls issued by a simulation configuration.

Anchor: ECSS-E-ST-40-08 clause 5.2.4.2 (operation call requirements -- the
eight obligations a call the configuration makes on a model instance has to
meet). Paraphrased into an implementable procedure; no standard text is
reproduced.

A configuration is an ordered sequence of steps: instances are created and
operations are called on them. The call is therefore graded both on its own
shape -- which operation, which arguments, which directions -- and on its
position in that sequence, because a call on an instance the configuration has
not created yet has nothing to run against.

The eight normative items implemented here
------------------------------------------
a. The operation is declared and published by the target type.
b. The operation is invokable at configuration time rather than only while the
   simulation is running.
c. Every supplied argument names a declared parameter.
d. No parameter receives two arguments.
e. Every in and inout parameter receives a value.
f. No out parameter is given a value; the model produces it.
g. Each supplied value conforms to its parameter's declared type and to its
   declared allowed set or inclusive numeric range.
h. The target instance has already been created at the point the call is
   reached in the configuration sequence.
"""

__all__ = [
    "NORMATIVE_ITEMS",
    "NORMATIVE_ITEM_COUNT",
    "PARAMETER_TYPES",
    "DIRECTIONS",
    "SUPPLIED_DIRECTIONS",
    "build_operation_table",
    "value_conforms_to_type",
    "constraint_violation",
    "assess_operation_call",
    "assess_call_sequence",
]

NORMATIVE_ITEMS = (
    "operation-declared-and-published",
    "operation-invokable-at-configuration",
    "argument-names-a-declared-parameter",
    "no-parameter-bound-twice",
    "in-and-inout-parameters-all-supplied",
    "out-parameter-carries-no-value",
    "argument-value-conforms-to-type-and-constraint",
    "target-instance-created-before-the-call",
)
NORMATIVE_ITEM_COUNT = len(NORMATIVE_ITEMS)

PARAMETER_TYPES = ("Int32", "Float64", "Bool", "String8")

DIRECTIONS = ("in", "out", "inout")
# Directions the caller is obliged to supply a value for.
SUPPLIED_DIRECTIONS = ("in", "inout")


def _require_text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty or blank" % label)
    return text


def build_operation_table(operations):
    """Return a {name: declaration} table over the target type's operations."""
    if not isinstance(operations, (list, tuple)):
        raise ValueError("operations must be a sequence of declarations")
    if not operations:
        raise ValueError("the target type must declare at least one operation")
    table = {}
    for position, spec in enumerate(operations):
        if not isinstance(spec, dict):
            raise ValueError("operations[%d] must be a mapping" % position)
        name = _require_text(spec.get("name"), "operations[%d]['name']" % position)
        if name in table:
            raise ValueError("type declares operation %r twice" % name)
        published = spec.get("published", True)
        invokable = spec.get("invokable_at_configuration", True)
        for label, flag in (("published", published), ("invokable_at_configuration", invokable)):
            if not isinstance(flag, bool):
                raise ValueError("operation %r '%s' must be a boolean" % (name, label))
        parameters = spec.get("parameters", [])
        if not isinstance(parameters, (list, tuple)):
            raise ValueError("operation %r parameters must be a sequence" % name)
        ordered = []
        by_name = {}
        for order, parameter in enumerate(parameters):
            if not isinstance(parameter, dict):
                raise ValueError("operation %r parameter %d must be a mapping" % (name, order))
            p_name = _require_text(parameter.get("name"),
                                   "operation %r parameter name" % name)
            p_type = _require_text(parameter.get("type"),
                                   "operation %r parameter type" % name)
            if p_type not in PARAMETER_TYPES:
                raise ValueError(
                    "operation %r parameter %r declares unsupported type %r"
                    % (name, p_name, p_type)
                )
            direction = parameter.get("direction", "in")
            if direction not in DIRECTIONS:
                raise ValueError(
                    "operation %r parameter %r declares unknown direction %r"
                    % (name, p_name, direction)
                )
            if p_name in by_name:
                raise ValueError("operation %r declares parameter %r twice" % (name, p_name))
            record = dict(parameter)
            record.update({
                "name": p_name,
                "type": p_type,
                "direction": direction,
                "position": order,
            })
            ordered.append(record)
            by_name[p_name] = record
        table[name] = {
            "name": name,
            "published": published,
            "invokable_at_configuration": invokable,
            "parameters": ordered,
            "by_name": by_name,
        }
    return table


def value_conforms_to_type(value, declared):
    """Return True when the value matches the declared parameter type."""
    if declared not in PARAMETER_TYPES:
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
    return None


def _fail(items, findings, item, text):
    items[item] = False
    findings.append(text)


def assess_operation_call(call, table, created=()):
    """Grade one operation call against the eight clause 5.2.4.2 items."""
    if not isinstance(call, dict):
        raise ValueError("call must be a mapping")
    for key in ("target", "operation"):
        if key not in call:
            raise ValueError("call is missing required key '%s'" % key)
    if not isinstance(table, dict) or not table:
        raise ValueError("table must be the mapping returned by build_operation_table")
    if not isinstance(created, (list, tuple, set, frozenset)):
        raise ValueError("created must be a collection of instance paths")

    target = _require_text(call["target"], "call['target']")
    name = _require_text(call["operation"], "call['operation']")
    arguments = call.get("arguments", [])
    if not isinstance(arguments, (list, tuple)):
        raise ValueError("call['arguments'] must be a sequence")

    items = {key: True for key in NORMATIVE_ITEMS}
    findings = []

    if target not in created:
        _fail(items, findings, NORMATIVE_ITEMS[7],
              "instance %r has not been created at the point of this call" % target)

    declaration = table.get(name)
    if declaration is None or not declaration["published"]:
        for key in NORMATIVE_ITEMS[:7]:
            items[key] = False
        findings.append("operation %r is not declared and published by the type" % name)
        satisfied = sum(1 for ok in items.values() if ok)
        return {
            "target": target,
            "operation": name,
            "items": items,
            "findings": findings,
            "satisfied": satisfied,
            "compliant": False,
        }

    if not declaration["invokable_at_configuration"]:
        _fail(items, findings, NORMATIVE_ITEMS[1],
              "operation %r is not invokable at configuration time" % name)

    bound = {}
    for order, argument in enumerate(arguments):
        if not isinstance(argument, dict):
            raise ValueError("call argument %d must be a mapping" % order)
        for key in ("name", "value"):
            if key not in argument:
                raise ValueError("call argument %d is missing '%s'" % (order, key))
        a_name = _require_text(argument["name"], "call argument %d name" % order)
        parameter = declaration["by_name"].get(a_name)
        if parameter is None:
            _fail(items, findings, NORMATIVE_ITEMS[2],
                  "argument %r names no parameter of operation %r" % (a_name, name))
            continue
        if a_name in bound:
            _fail(items, findings, NORMATIVE_ITEMS[3],
                  "parameter %r of operation %r is supplied more than once" % (a_name, name))
            continue
        bound[a_name] = argument["value"]
        if parameter["direction"] == "out":
            _fail(items, findings, NORMATIVE_ITEMS[5],
                  "parameter %r is an out parameter and takes no supplied value" % a_name)
            continue
        if not value_conforms_to_type(argument["value"], parameter["type"]):
            _fail(items, findings, NORMATIVE_ITEMS[6],
                  "parameter %r declares %s but the value is %s"
                  % (a_name, parameter["type"], type(argument["value"]).__name__))
            continue
        violation = constraint_violation(argument["value"], parameter)
        if violation:
            _fail(items, findings, NORMATIVE_ITEMS[6],
                  "parameter %r: %s" % (a_name, violation))

    for parameter in declaration["parameters"]:
        if parameter["direction"] in SUPPLIED_DIRECTIONS and parameter["name"] not in bound:
            _fail(items, findings, NORMATIVE_ITEMS[4],
                  "parameter %r has direction %s and received no value"
                  % (parameter["name"], parameter["direction"]))

    satisfied = sum(1 for ok in items.values() if ok)
    return {
        "target": target,
        "operation": name,
        "bound": bound,
        "items": items,
        "findings": findings,
        "satisfied": satisfied,
        "compliant": satisfied == NORMATIVE_ITEM_COUNT,
    }


def assess_call_sequence(spec):
    """Walk an ordered configuration sequence and grade every operation call.

    spec keys: 'operations' (the target type's operation declarations) and
    'steps', an ordered sequence of {'kind': 'instantiate', 'instance': path}
    and {'kind': 'call', 'target': path, 'operation': name, 'arguments': [...]}
    entries.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("operations", "steps"):
        if key not in spec:
            raise ValueError("spec is missing required key '%s'" % key)
    steps = spec["steps"]
    if not isinstance(steps, (list, tuple)):
        raise ValueError("spec['steps'] must be a sequence")
    if not steps:
        raise ValueError("spec['steps'] must hold at least one step")
    table = build_operation_table(spec["operations"])

    created = set()
    records = []
    for order, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError("steps[%d] must be a mapping" % order)
        kind = step.get("kind")
        if kind == "instantiate":
            instance = _require_text(step.get("instance"), "steps[%d]['instance']" % order)
            if instance in created:
                raise ValueError("instance %r is created twice" % instance)
            created.add(instance)
        elif kind == "call":
            record = assess_operation_call(step, table, created)
            record["step"] = order
            records.append(record)
        else:
            raise ValueError(
                "steps[%d] declares unknown kind %r (expected 'instantiate' or 'call')"
                % (order, kind)
            )
    if not records:
        raise ValueError("spec['steps'] contains no operation call to grade")

    findings = []
    for record in records:
        for text in record["findings"]:
            findings.append("%s.%s: %s" % (record["target"], record["operation"], text))
    satisfied = sum(r["satisfied"] for r in records)
    return {
        "records": records,
        "call_count": len(records),
        "instance_count": len(created),
        "item_count": NORMATIVE_ITEM_COUNT,
        "satisfied": satisfied,
        "graded": NORMATIVE_ITEM_COUNT * len(records),
        "findings": findings,
        "compliant": all(r["compliant"] for r in records),
    }
