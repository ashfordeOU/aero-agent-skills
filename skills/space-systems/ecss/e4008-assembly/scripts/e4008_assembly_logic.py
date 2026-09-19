#!/usr/bin/env python3
"""Check an SMP assembly artefact before a simulator is built from it.

Anchor: ECSS-E-ST-40-08C clause 5.2.10. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The assembly is the artefact that turns a catalogue of model types into
a running simulator: it names the instances, says where each one sits in
the composition tree, and sets the field values that configure them. It
is read once, while the simulator is still being built, so every defect
in it is a defect the simulator carries for the whole run.

The clause's normative items reduce to five implementable checks:

    1  every instance names a catalogue the assembly declared and that
       was actually supplied to the build
    2  every instance resolves to a type that catalogue declares
    3  instance paths are unique and each parent path resolves, so the
       composition tree is a tree and not a set of loose fragments
    4  every field value targets a field the type declares, that field
       is writable, and the value fits the field's declared type
    5  every container on an instantiated type ends up with a child
       count inside its declared multiplicity bounds

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

VERDICT_BUILDABLE = "assembly-buildable"
VERDICT_REJECTED = "assembly-rejected"

FINDING_CATALOGUE_UNDECLARED = "catalogue-not-declared"
FINDING_CATALOGUE_MISSING = "catalogue-not-supplied"
FINDING_TYPE_UNRESOLVED = "type-not-in-catalogue"
FINDING_PATH_DUPLICATE = "instance-path-duplicate"
FINDING_PARENT_UNRESOLVED = "parent-path-unresolved"
FINDING_CONTAINER_UNKNOWN = "container-not-on-parent-type"
FINDING_FIELD_UNKNOWN = "field-not-on-type"
FINDING_FIELD_READ_ONLY = "field-not-writable"
FINDING_VALUE_TYPE = "value-type-mismatch"
FINDING_VALUE_RANGE = "value-out-of-type-range"
FINDING_MULTIPLICITY_LOW = "container-below-lower-bound"
FINDING_MULTIPLICITY_HIGH = "container-above-upper-bound"

INTEGER_RANGES = {
    "Int8": (-128, 127),
    "Int16": (-32768, 32767),
    "Int32": (-2147483648, 2147483647),
    "Int64": (-9223372036854775808, 9223372036854775807),
    "UInt8": (0, 255),
    "UInt16": (0, 65535),
    "UInt32": (0, 4294967295),
    "UInt64": (0, 18446744073709551615),
    "Duration": (-9223372036854775808, 9223372036854775807),
    "DateTime": (-9223372036854775808, 9223372036854775807),
}

FLOAT_TYPES = ("Float32", "Float64")
FLOAT32_MAX = 3.4028234663852886e38

PRIMITIVE_TYPES = tuple(sorted(INTEGER_RANGES)) + FLOAT_TYPES + ("Bool", "String8")

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_sequence(name, value):
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list, got %r" % (name, value))
    return list(value)


def _require_name(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    cleaned = value.strip()
    if "/" in cleaned:
        raise ValueError("%s must not contain a path separator, got %r" % (label, value))
    return cleaned


def _not_above(value, limit):
    """value <= limit, absorbing float representation error at the bound."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _finding(code, detail):
    return {"code": code, "detail": detail}


def value_fits_type(type_name, value):
    """Report whether a configured value is admissible for a field type.

    Returns (fits, code) where code is None on success and names the
    reason otherwise. A boolean is never accepted as an integer: the
    assembly is a configuration record and a silently widened bool is a
    configuration error the simulator cannot see later.
    """
    if type_name not in PRIMITIVE_TYPES:
        raise ValueError(
            "field type must be one of %s, got %r"
            % (", ".join(PRIMITIVE_TYPES), type_name)
        )
    if type_name == "Bool":
        return (isinstance(value, bool), None if isinstance(value, bool) else FINDING_VALUE_TYPE)
    if type_name == "String8":
        return (isinstance(value, str), None if isinstance(value, str) else FINDING_VALUE_TYPE)
    if type_name in INTEGER_RANGES:
        if not isinstance(value, int) or isinstance(value, bool):
            return (False, FINDING_VALUE_TYPE)
        low, high = INTEGER_RANGES[type_name]
        if value < low or value > high:
            return (False, FINDING_VALUE_RANGE)
        return (True, None)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return (False, FINDING_VALUE_TYPE)
    number = float(value)
    if not math.isfinite(number):
        return (False, FINDING_VALUE_RANGE)
    if type_name == "Float32" and not _not_above(abs(number), FLOAT32_MAX):
        return (False, FINDING_VALUE_RANGE)
    return (True, None)


def validate_catalogues(catalogues):
    """Check the supplied catalogue set is well formed before it is used."""
    _require_mapping("catalogues", catalogues)
    for catalogue_name, types in catalogues.items():
        _require_name("catalogue name", catalogue_name)
        _require_mapping("catalogue %s" % catalogue_name, types)
        for type_name, spec in types.items():
            _require_name("type name", type_name)
            _require_mapping("type %s" % type_name, spec)
            fields = _require_mapping("type %s fields" % type_name, spec.get("fields", {}))
            for field_name, field_spec in fields.items():
                _require_name("field name", field_name)
                _require_mapping("field %s" % field_name, field_spec)
                if field_spec.get("type") not in PRIMITIVE_TYPES:
                    raise ValueError(
                        "field %s.%s declares an unknown type %r"
                        % (type_name, field_name, field_spec.get("type"))
                    )
            containers = _require_mapping(
                "type %s containers" % type_name, spec.get("containers", {})
            )
            for container_name, bounds in containers.items():
                _require_name("container name", container_name)
                _require_mapping("container %s" % container_name, bounds)
                lower = bounds.get("lower", 0)
                upper = bounds.get("upper")
                if not isinstance(lower, int) or isinstance(lower, bool) or lower < 0:
                    raise ValueError(
                        "container %s.%s lower bound must be a non-negative integer"
                        % (type_name, container_name)
                    )
                if upper is not None:
                    if not isinstance(upper, int) or isinstance(upper, bool):
                        raise ValueError(
                            "container %s.%s upper bound must be an integer or None"
                            % (type_name, container_name)
                        )
                    if upper < lower:
                        raise ValueError(
                            "container %s.%s upper bound is below its lower bound"
                            % (type_name, container_name)
                        )
    return catalogues


def instance_path(parent_path, name):
    """Composition path of an instance under its parent."""
    cleaned = _require_name("instance name", name)
    if parent_path is None:
        return cleaned
    if not isinstance(parent_path, str) or not parent_path.strip():
        raise ValueError("parent path must be a non-empty string or None")
    return "%s/%s" % (parent_path.strip(), cleaned)


def resolve_type(catalogues, catalogue_name, type_name):
    """Look a type up in one catalogue, or return None when absent."""
    _require_mapping("catalogues", catalogues)
    types = catalogues.get(catalogue_name)
    if not isinstance(types, dict):
        return None
    spec = types.get(type_name)
    return spec if isinstance(spec, dict) else None


def evaluate_assembly(assembly, catalogues):
    """Full clause 5.2.10 assembly check with a build verdict."""
    _require_mapping("assembly", assembly)
    validate_catalogues(catalogues)
    declared = _require_sequence(
        "assembly catalogues", assembly.get("catalogues", [])
    )
    declared_set = set()
    for entry in declared:
        declared_set.add(_require_name("declared catalogue", entry))
    instances = _require_sequence("assembly instances", assembly.get("instances", []))
    if not instances:
        raise ValueError("an assembly with no instances cannot build a simulator")

    findings = []
    resolved = {}
    order = []
    container_children = {}

    for raw in instances:
        _require_mapping("instance", raw)
        name = _require_name("instance name", raw.get("name"))
        parent = raw.get("parent")
        path = instance_path(parent, name)
        if path in resolved:
            findings.append(_finding(FINDING_PATH_DUPLICATE, path))
            continue
        catalogue_name = _require_name("instance catalogue", raw.get("catalogue"))
        type_name = _require_name("instance type", raw.get("type"))
        if catalogue_name not in declared_set:
            findings.append(
                _finding(FINDING_CATALOGUE_UNDECLARED, "%s -> %s" % (path, catalogue_name))
            )
        elif catalogue_name not in catalogues:
            findings.append(
                _finding(FINDING_CATALOGUE_MISSING, "%s -> %s" % (path, catalogue_name))
            )
        spec = resolve_type(catalogues, catalogue_name, type_name)
        if spec is None:
            findings.append(
                _finding(FINDING_TYPE_UNRESOLVED, "%s -> %s" % (path, type_name))
            )
        resolved[path] = {
            "path": path,
            "name": name,
            "parent": parent,
            "type": type_name,
            "catalogue": catalogue_name,
            "spec": spec,
            "container": raw.get("container"),
            "field_values": _require_mapping(
                "instance %s field_values" % path, raw.get("field_values", {})
            ),
        }
        order.append(path)

    for path in order:
        item = resolved[path]
        parent = item["parent"]
        if parent is None:
            continue
        parent_item = resolved.get(parent)
        if parent_item is None:
            findings.append(_finding(FINDING_PARENT_UNRESOLVED, "%s -> %s" % (path, parent)))
            continue
        container = item["container"]
        parent_spec = parent_item["spec"] or {}
        containers = parent_spec.get("containers", {})
        if container is None or container not in containers:
            findings.append(
                _finding(FINDING_CONTAINER_UNKNOWN, "%s -> %s" % (path, container))
            )
            continue
        container_children.setdefault((parent, container), []).append(path)

    for path in order:
        item = resolved[path]
        spec = item["spec"]
        if spec is None:
            continue
        fields = spec.get("fields", {})
        for field_name in sorted(item["field_values"]):
            value = item["field_values"][field_name]
            field_spec = fields.get(field_name)
            if field_spec is None:
                findings.append(
                    _finding(FINDING_FIELD_UNKNOWN, "%s.%s" % (path, field_name))
                )
                continue
            if not field_spec.get("writable", True):
                findings.append(
                    _finding(FINDING_FIELD_READ_ONLY, "%s.%s" % (path, field_name))
                )
                continue
            fits, code = value_fits_type(field_spec["type"], value)
            if not fits:
                findings.append(_finding(code, "%s.%s" % (path, field_name)))

    for path in order:
        item = resolved[path]
        spec = item["spec"]
        if spec is None:
            continue
        for container_name in sorted(spec.get("containers", {})):
            bounds = spec["containers"][container_name]
            count = len(container_children.get((path, container_name), []))
            lower = bounds.get("lower", 0)
            upper = bounds.get("upper")
            if count < lower:
                findings.append(
                    _finding(
                        FINDING_MULTIPLICITY_LOW,
                        "%s.%s has %d of at least %d" % (path, container_name, count, lower),
                    )
                )
            if upper is not None and count > upper:
                findings.append(
                    _finding(
                        FINDING_MULTIPLICITY_HIGH,
                        "%s.%s has %d of at most %d" % (path, container_name, count, upper),
                    )
                )

    unused = sorted(declared_set - {item["catalogue"] for item in resolved.values()})
    return {
        "verdict": VERDICT_BUILDABLE if not findings else VERDICT_REJECTED,
        "buildable": not findings,
        "instance_count": len(resolved),
        "paths": sorted(resolved),
        "findings": findings,
        "finding_codes": sorted({entry["code"] for entry in findings}),
        "unused_catalogues": unused,
    }
