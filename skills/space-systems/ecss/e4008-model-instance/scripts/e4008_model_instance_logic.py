#!/usr/bin/env python3
"""Requirements on a model Instance in a simulation assembly.

Anchor: ECSS-E-ST-40-08C clause 4.2.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An Instance is one occurrence of a model definition inside an assembly.
The clause carries seven normative items, and each one is a question a
reviewer can answer from the assembly data alone:

    1 the name is a legal identifier and unique among its siblings
    2 the instance carries a description
    3 the model definition it instantiates resolves in the catalogue
    4 every field the definition declares is bound, by value or default
    5 every supplied field value fits its declared type and range
    6 every mandatory reference the definition declares is resolved
    7 the resulting hierarchy path is unique across the assembly

Nothing here is a style preference. An unbound field leaves the
simulator reading whatever the platform happened to leave in memory; a
duplicate path makes two different instances addressable by one name,
and whichever one the scheduler reaches is then an accident of load
order.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import re

NORMATIVE_ITEMS = (
    "instance-name-legal-and-unique-among-siblings",
    "instance-description-present",
    "model-definition-resolved-in-catalogue",
    "declared-fields-all-bound",
    "field-values-fit-declared-type",
    "mandatory-references-resolved",
    "instance-path-unique-in-assembly",
)

FIELD_TYPES = ("integer", "float", "boolean", "string", "enumeration")

INSTANCE_VERDICTS = ("instance-compliant", "instance-non-compliant")
ASSEMBLY_VERDICTS = ("assembly-compliant", "assembly-non-compliant")

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MAX_IDENTIFIER_LENGTH = 64
PATH_SEPARATOR = "/"


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_sequence(name, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence, got %r" % (name, value))
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def is_legal_identifier(name):
    """Whether a name may be used as an instance or field identifier."""
    return (
        isinstance(name, str)
        and 0 < len(name) <= MAX_IDENTIFIER_LENGTH
        and IDENTIFIER_PATTERN.match(name) is not None
    )


def validate_identifier(name, label="identifier"):
    """Return the name, or raise when it cannot address anything."""
    if not is_legal_identifier(name):
        raise ValueError(
            "%s %r is not a legal identifier (letter or underscore first, then "
            "letters, digits or underscores, at most %d characters)"
            % (label, name, MAX_IDENTIFIER_LENGTH)
        )
    return name


def instance_path(parent_path, name):
    """Hierarchy path an instance occupies under its parent."""
    validate_identifier(name, "instance name")
    if parent_path in (None, "", PATH_SEPARATOR):
        return PATH_SEPARATOR + name
    if not isinstance(parent_path, str) or not parent_path.startswith(PATH_SEPARATOR):
        raise ValueError(
            "parent_path must be an absolute path starting with %r, got %r"
            % (PATH_SEPARATOR, parent_path)
        )
    return parent_path.rstrip(PATH_SEPARATOR) + PATH_SEPARATOR + name


def validate_field_declaration(field):
    """Check one field declaration of a model definition is usable."""
    _require_mapping("field declaration", field)
    validate_identifier(field.get("name"), "field name")
    kind = field.get("type")
    if kind not in FIELD_TYPES:
        raise ValueError(
            "field %r declares type %r, expected one of %s"
            % (field.get("name"), kind, ", ".join(FIELD_TYPES))
        )
    if kind == "enumeration":
        values = field.get("values")
        if not isinstance(values, (list, tuple)) or not values:
            raise ValueError(
                "enumeration field %r must declare a non-empty values list"
                % field.get("name")
            )
    if kind in ("integer", "float"):
        low = field.get("minimum")
        high = field.get("maximum")
        for bound_name, bound in (("minimum", low), ("maximum", high)):
            if bound is not None and (
                isinstance(bound, bool) or not isinstance(bound, (int, float))
            ):
                raise ValueError(
                    "field %r %s must be a number, got %r"
                    % (field.get("name"), bound_name, bound)
                )
        if low is not None and high is not None and low > high:
            raise ValueError(
                "field %r declares a minimum above its maximum" % field.get("name")
            )
    return field


def check_field_value(field, value):
    """Whether one supplied value fits the field declaration it binds."""
    validate_field_declaration(field)
    kind = field["type"]
    name = field["name"]
    if kind == "boolean":
        if not isinstance(value, bool):
            return (False, "field %s expects a boolean, got %r" % (name, value))
        return (True, None)
    if kind == "string":
        if not isinstance(value, str):
            return (False, "field %s expects a string, got %r" % (name, value))
        return (True, None)
    if kind == "enumeration":
        if value not in field["values"]:
            return (
                False,
                "field %s expects one of %s, got %r"
                % (name, ", ".join(str(v) for v in field["values"]), value),
            )
        return (True, None)
    if kind == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            return (False, "field %s expects an integer, got %r" % (name, value))
    else:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return (False, "field %s expects a number, got %r" % (name, value))
    low = field.get("minimum")
    high = field.get("maximum")
    if low is not None and value < low:
        return (False, "field %s value %r is below its minimum %r" % (name, value, low))
    if high is not None and value > high:
        return (False, "field %s value %r is above its maximum %r" % (name, value, high))
    return (True, None)


def bind_fields(definition, instance):
    """Work out which declared fields are bound, defaulted, missing or bad."""
    _require_mapping("definition", definition)
    _require_mapping("instance", instance)
    declarations = _require_sequence("definition fields", definition.get("fields", []))
    supplied = instance.get("field_values", {})
    _require_mapping("instance field_values", supplied)
    declared_names = set()
    bound = {}
    defaulted = []
    missing = []
    invalid = []
    for field in declarations:
        validate_field_declaration(field)
        name = field["name"]
        if name in declared_names:
            raise ValueError("definition declares field %r twice" % name)
        declared_names.add(name)
        if name in supplied:
            ok, reason = check_field_value(field, supplied[name])
            if ok:
                bound[name] = supplied[name]
            else:
                invalid.append(reason)
        elif "default" in field:
            ok, reason = check_field_value(field, field["default"])
            if ok:
                bound[name] = field["default"]
                defaulted.append(name)
            else:
                invalid.append("default for %s" % reason)
        else:
            missing.append(name)
    unknown = sorted(set(supplied) - declared_names)
    return {
        "bound": bound,
        "defaulted": defaulted,
        "missing": missing,
        "invalid": invalid,
        "unknown": unknown,
    }


def resolve_references(definition, instance, known_paths=()):
    """Resolve the references a definition declares onto instance paths."""
    _require_mapping("definition", definition)
    _require_mapping("instance", instance)
    declarations = _require_sequence(
        "definition references", definition.get("references", [])
    )
    supplied = instance.get("references", {})
    _require_mapping("instance references", supplied)
    known = set(known_paths)
    resolved = {}
    unresolved = []
    dangling = []
    for reference in declarations:
        _require_mapping("reference declaration", reference)
        name = validate_identifier(reference.get("name"), "reference name")
        mandatory = reference.get("mandatory", True)
        if not isinstance(mandatory, bool):
            raise ValueError(
                "reference %r mandatory flag must be a boolean, got %r"
                % (name, mandatory)
            )
        target = supplied.get(name)
        if target in (None, ""):
            if mandatory:
                unresolved.append(name)
            continue
        if not isinstance(target, str) or not target.startswith(PATH_SEPARATOR):
            raise ValueError(
                "reference %r must target an absolute instance path, got %r"
                % (name, target)
            )
        if known and target not in known:
            dangling.append("%s -> %s" % (name, target))
        else:
            resolved[name] = target
    return {"resolved": resolved, "unresolved": unresolved, "dangling": dangling}


def _item(identifier, satisfied, finding=None):
    return {"item": identifier, "satisfied": satisfied, "finding": finding}


def evaluate_model_instance(instance, catalogue, sibling_names=(), known_paths=()):
    """Grade one Instance against the seven normative items of 4.2.2.2."""
    _require_mapping("instance", instance)
    _require_mapping("catalogue", catalogue)
    siblings = set(sibling_names)
    known = set(known_paths)
    items = []

    name = instance.get("name")
    if not is_legal_identifier(name):
        items.append(
            _item(NORMATIVE_ITEMS[0], False, "instance name %r is not a legal identifier" % (name,))
        )
    elif name in siblings:
        items.append(
            _item(NORMATIVE_ITEMS[0], False, "instance name %r repeats a sibling" % name)
        )
    else:
        items.append(_item(NORMATIVE_ITEMS[0], True))

    description = instance.get("description")
    items.append(
        _item(NORMATIVE_ITEMS[1], True)
        if isinstance(description, str) and description.strip()
        else _item(NORMATIVE_ITEMS[1], False, "instance carries no description")
    )

    definition_name = instance.get("definition")
    definition = catalogue.get(definition_name) if isinstance(definition_name, str) else None
    if definition is None:
        items.append(
            _item(
                NORMATIVE_ITEMS[2],
                False,
                "model definition %r is not in the catalogue" % (definition_name,),
            )
        )
        for identifier in NORMATIVE_ITEMS[3:6]:
            items.append(
                _item(identifier, False, "not assessable without a resolved definition")
            )
        binding = None
        references = None
    else:
        items.append(_item(NORMATIVE_ITEMS[2], True))
        binding = bind_fields(definition, instance)
        if binding["missing"]:
            items.append(
                _item(
                    NORMATIVE_ITEMS[3],
                    False,
                    "fields left unbound with no default: %s"
                    % ", ".join(binding["missing"]),
                )
            )
        elif binding["unknown"]:
            items.append(
                _item(
                    NORMATIVE_ITEMS[3],
                    False,
                    "values supplied for fields the definition never declared: %s"
                    % ", ".join(binding["unknown"]),
                )
            )
        else:
            items.append(_item(NORMATIVE_ITEMS[3], True))
        items.append(
            _item(NORMATIVE_ITEMS[4], True)
            if not binding["invalid"]
            else _item(NORMATIVE_ITEMS[4], False, "; ".join(binding["invalid"]))
        )
        references = resolve_references(definition, instance, known)
        if references["unresolved"]:
            items.append(
                _item(
                    NORMATIVE_ITEMS[5],
                    False,
                    "mandatory references left unresolved: %s"
                    % ", ".join(references["unresolved"]),
                )
            )
        elif references["dangling"]:
            items.append(
                _item(
                    NORMATIVE_ITEMS[5],
                    False,
                    "references point outside the assembly: %s"
                    % ", ".join(references["dangling"]),
                )
            )
        else:
            items.append(_item(NORMATIVE_ITEMS[5], True))

    path = None
    if is_legal_identifier(name):
        path = instance_path(instance.get("parent_path"), name)
        items.append(
            _item(NORMATIVE_ITEMS[6], True)
            if path not in known
            else _item(NORMATIVE_ITEMS[6], False, "path %s is already occupied" % path)
        )
    else:
        items.append(
            _item(NORMATIVE_ITEMS[6], False, "no path without a legal instance name")
        )

    satisfied = sum(1 for entry in items if entry["satisfied"])
    compliant = satisfied == len(NORMATIVE_ITEMS)
    return {
        "name": name,
        "path": path,
        "items": items,
        "satisfied": satisfied,
        "required": len(NORMATIVE_ITEMS),
        "binding": binding,
        "references": references,
        "compliant": compliant,
        "verdict": "instance-compliant" if compliant else "instance-non-compliant",
        "findings": [entry["finding"] for entry in items if entry["finding"]],
    }


def evaluate_assembly_instances(instances, catalogue):
    """Grade every Instance in an assembly, sharing the path and sibling view."""
    _require_sequence("instances", instances)
    _require_mapping("catalogue", catalogue)
    if not instances:
        raise ValueError("an assembly needs at least one instance to review")
    declared_paths = []
    for instance in instances:
        _require_mapping("instance", instance)
        name = instance.get("name")
        if is_legal_identifier(name):
            declared_paths.append(instance_path(instance.get("parent_path"), name))
        else:
            declared_paths.append(None)
    results = []
    seen_paths = set()
    siblings_by_parent = {}
    for instance, path in zip(instances, declared_paths):
        parent = instance.get("parent_path") or PATH_SEPARATOR
        siblings = siblings_by_parent.setdefault(parent, set())
        result = evaluate_model_instance(
            instance,
            catalogue,
            sibling_names=siblings,
            known_paths=seen_paths | set(p for p in declared_paths if p),
        )
        # The path index above lets a reference resolve forward; occupancy of
        # a path is judged only against the instances already placed.
        if path is not None:
            occupied = path in seen_paths
            for entry in result["items"]:
                if entry["item"] == NORMATIVE_ITEMS[6]:
                    entry["satisfied"] = not occupied
                    entry["finding"] = (
                        "path %s is already occupied" % path if occupied else None
                    )
            result["satisfied"] = sum(1 for e in result["items"] if e["satisfied"])
            result["compliant"] = result["satisfied"] == len(NORMATIVE_ITEMS)
            result["verdict"] = (
                "instance-compliant" if result["compliant"] else "instance-non-compliant"
            )
            result["findings"] = [e["finding"] for e in result["items"] if e["finding"]]
            seen_paths.add(path)
        if is_legal_identifier(instance.get("name")):
            siblings.add(instance["name"])
        results.append(result)
    compliant = all(result["compliant"] for result in results)
    return {
        "instances": results,
        "reviewed": len(results),
        "compliant_instances": sum(1 for result in results if result["compliant"]),
        "compliant": compliant,
        "verdict": "assembly-compliant" if compliant else "assembly-non-compliant",
        "findings": [
            "%s: %s" % (result["name"], note)
            for result in results
            for note in result["findings"]
        ],
    }
