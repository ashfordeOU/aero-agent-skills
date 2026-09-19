"""Component configuration assignments in an SMP Level-2 assembly artefact.

Anchor: ECSS-E-ST-40-08C clause 5.2.6.2 (configuration requirements applied to a
component instance of an assembly). Paraphrased into an implementable procedure;
no standard text is reproduced.

What this module decides
------------------------
An assembly instantiates model types from a catalogue and then *configures* each
instance by assigning values to its fields before the simulator leaves the
building state. Six normative checks decide whether a configuration block is
acceptable:

1. every assignment resolves to a field declared by the instantiated type,
   including a nested structure member or an array element;
2. the resolved field is writeable at configuration time -- an output-only field
   is produced by the model and is not a configuration target;
3. the assigned value is compatible with the declared datatype of the field;
4. the value lies inside the declared range, or is one of the declared literals
   of an enumeration field;
5. no field path is assigned twice in the same configuration block;
6. no configured field is also driven by a field link, because a link would
   overwrite the configured value once the simulator starts.

Structural defects (a malformed type model, a syntactically invalid field path)
raise. Clause non-conformances are returned as findings so a whole configuration
block can be graded in one pass.
"""

import re

__all__ = [
    "CONFIGURABLE_DIRECTIONS",
    "FIELD_DIRECTIONS",
    "INTEGER_DATATYPES",
    "ConfigurationError",
    "apply_configuration",
    "assess_component_configuration",
    "canonical_path",
    "check_value",
    "parse_field_path",
    "resolve_field",
    "value_matches_datatype",
]

FIELD_DIRECTIONS = ("input", "output", "state")

# An output field is written by the model itself; assigning it at configuration
# time would be overwritten on the first update, so it is not a valid target.
CONFIGURABLE_DIRECTIONS = ("input", "state")

# Declared width of the integer primitives the assembly artefact can carry.
INTEGER_DATATYPES = {
    "Int8": (-128, 127),
    "UInt8": (0, 255),
    "Int16": (-32768, 32767),
    "UInt16": (0, 65535),
    "Int32": (-2147483648, 2147483647),
    "UInt32": (0, 4294967295),
    "Int64": (-9223372036854775808, 9223372036854775807),
    "UInt64": (0, 18446744073709551615),
    "Duration": (-9223372036854775808, 9223372036854775807),
}

_SEGMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(?:\[([0-9]+)\])?$")


class ConfigurationError(ValueError):
    """A configuration assignment that clause 5.2.6.2 does not admit."""


def parse_field_path(path):
    """Return the parsed field path as a list of (name, index-or-None) steps."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("field path must be a non-empty string")
    steps = []
    for raw in path.split("."):
        match = _SEGMENT.match(raw)
        if match is None:
            raise ValueError("field path segment %r is not a valid member reference" % raw)
        name, index = match.group(1), match.group(2)
        steps.append((name, None if index is None else int(index)))
    return steps


def canonical_path(steps):
    """Return the canonical text form of a parsed field path."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("steps must be a non-empty sequence of path steps")
    parts = []
    for step in steps:
        if not isinstance(step, (list, tuple)) or len(step) != 2:
            raise ValueError("each step must be a (name, index) pair")
        name, index = step
        parts.append(name if index is None else "%s[%d]" % (name, index))
    return ".".join(parts)


def _field_table(node, where):
    """Return the field table of a type model or of a structure field."""
    if not isinstance(node, dict):
        raise ValueError("%s must be a mapping" % where)
    fields = node.get("fields")
    if not isinstance(fields, dict) or not fields:
        raise ValueError("%s declares no fields" % where)
    return fields


def resolve_field(type_model, path):
    """Resolve a field path against a type model.

    Returns (descriptor, canonical_path_text). Raises ConfigurationError when the
    path names no declared field, indexes a non-array field, or runs off the end
    of a declared array dimension.
    """
    steps = parse_field_path(path)
    node = type_model
    where = "type model"
    descriptor = None
    for depth, (name, index) in enumerate(steps):
        fields = _field_table(node, where)
        if name not in fields:
            raise ConfigurationError(
                "field %r is not declared by %s" % (canonical_path(steps[: depth + 1]), where)
            )
        descriptor = fields[name]
        if not isinstance(descriptor, dict):
            raise ValueError("field %r must be described by a mapping" % name)
        dimensions = descriptor.get("dimensions")
        if index is not None:
            if not dimensions:
                raise ConfigurationError("field %r is not an array and cannot be indexed" % name)
            extent = dimensions[0]
            if not isinstance(extent, int) or isinstance(extent, bool) or extent <= 0:
                raise ValueError("field %r declares a non-positive array extent" % name)
            if index >= extent:
                raise ConfigurationError(
                    "index %d of field %r is outside its declared extent %d"
                    % (index, name, extent)
                )
        elif dimensions and depth == len(steps) - 1:
            descriptor = dict(descriptor)
        if depth < len(steps) - 1:
            if descriptor.get("datatype") != "struct":
                raise ConfigurationError(
                    "field %r is not a structure and has no member %r"
                    % (name, steps[depth + 1][0])
                )
            node = descriptor
            where = "structure field %r" % name
    return descriptor, canonical_path(steps)


def value_matches_datatype(descriptor, value):
    """Return True when the value is admissible for the declared datatype."""
    if not isinstance(descriptor, dict):
        raise ValueError("descriptor must be a mapping")
    datatype = descriptor.get("datatype")
    if not isinstance(datatype, str) or not datatype:
        raise ValueError("descriptor must declare a datatype")
    if isinstance(value, bool):
        return datatype == "Bool"
    if datatype == "Bool":
        return False
    if datatype in INTEGER_DATATYPES:
        return isinstance(value, int)
    if datatype in ("Float32", "Float64"):
        return isinstance(value, (int, float))
    if datatype in ("String8", "Char8"):
        return isinstance(value, str)
    if datatype == "enum":
        return isinstance(value, str)
    if datatype == "struct":
        return False
    raise ValueError("datatype %r is not one of the assembly primitives" % datatype)


def check_value(descriptor, value):
    """Return the value if it satisfies the declared datatype and range."""
    if not value_matches_datatype(descriptor, value):
        raise ConfigurationError(
            "value %r is not compatible with datatype %r"
            % (value, descriptor.get("datatype"))
        )
    datatype = descriptor["datatype"]
    if datatype == "enum":
        literals = descriptor.get("literals")
        if not isinstance(literals, (list, tuple)) or not literals:
            raise ValueError("enumeration field declares no literals")
        if value not in literals:
            raise ConfigurationError("value %r is not a declared enumeration literal" % value)
        return value
    if datatype in INTEGER_DATATYPES:
        low, high = INTEGER_DATATYPES[datatype]
        if value < low or value > high:
            raise ConfigurationError(
                "value %r is outside the representable range of %s" % (value, datatype)
            )
    minimum = descriptor.get("minimum")
    maximum = descriptor.get("maximum")
    if minimum is not None and value < minimum:
        raise ConfigurationError("value %r is below the declared minimum %r" % (value, minimum))
    if maximum is not None and value > maximum:
        raise ConfigurationError("value %r is above the declared maximum %r" % (value, maximum))
    return value


def apply_configuration(type_model, assignments, driven_fields=None):
    """Grade one configuration block against the six clause 5.2.6.2 checks."""
    if not isinstance(type_model, dict):
        raise ValueError("type_model must be a mapping")
    if not isinstance(assignments, dict):
        raise ValueError("assignments must be a mapping of field path to value")
    if type_model.get("abstract"):
        raise ValueError("an abstract type cannot be instantiated or configured")
    driven = set()
    for item in driven_fields or ():
        if not isinstance(item, str):
            raise ValueError("driven field paths must be strings")
        driven.add(canonical_path(parse_field_path(item)))
    values = {}
    findings = []
    seen = {}
    for path in sorted(assignments):
        value = assignments[path]
        try:
            descriptor, resolved = resolve_field(type_model, path)
        except ConfigurationError as exc:
            findings.append("%s: %s" % (path, exc))
            continue
        direction = descriptor.get("direction", "input")
        if direction not in FIELD_DIRECTIONS:
            raise ValueError("field %r declares an unknown direction %r" % (path, direction))
        if direction not in CONFIGURABLE_DIRECTIONS:
            findings.append(
                "%s: an %s field is produced by the model and is not configurable"
                % (path, direction)
            )
            continue
        if resolved in seen:
            findings.append(
                "%s: field path already assigned as %r in the same block" % (path, seen[resolved])
            )
            continue
        try:
            checked = check_value(descriptor, value)
        except ConfigurationError as exc:
            findings.append("%s: %s" % (path, exc))
            continue
        if resolved in driven:
            findings.append(
                "%s: field is driven by a field link, a configured value would be overwritten"
                % path
            )
            continue
        seen[resolved] = path
        values[resolved] = checked
    return {"values": values, "findings": findings, "compliant": not findings}


def assess_component_configuration(spec):
    """Run the clause 5.2.6.2 assessment over every configured instance.

    spec keys: 'catalogue' (type name -> type model), 'instances' (a sequence of
    {'path', 'type', 'configuration', optional 'driven_fields'}).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    catalogue = spec.get("catalogue")
    instances = spec.get("instances")
    if not isinstance(catalogue, dict) or not catalogue:
        raise ValueError("spec['catalogue'] must be a non-empty mapping of type models")
    if not isinstance(instances, (list, tuple)) or not instances:
        raise ValueError("spec['instances'] must be a non-empty sequence")
    reports = []
    findings = []
    configured_total = 0
    for entry in instances:
        if not isinstance(entry, dict):
            raise ValueError("each instance entry must be a mapping")
        for key in ("path", "type", "configuration"):
            if key not in entry:
                raise ValueError("instance entry missing required key %r" % key)
        type_name = entry["type"]
        if type_name not in catalogue:
            raise ValueError("instance %r names undeclared type %r" % (entry["path"], type_name))
        report = apply_configuration(
            catalogue[type_name], entry["configuration"], entry.get("driven_fields")
        )
        report["path"] = entry["path"]
        report["type"] = type_name
        configured_total += len(report["values"])
        for item in report["findings"]:
            findings.append("%s (%s): %s" % (entry["path"], type_name, item))
        reports.append(report)
    return {
        "reports": reports,
        "configured_values": configured_total,
        "findings": findings,
        "compliant": not findings,
    }
