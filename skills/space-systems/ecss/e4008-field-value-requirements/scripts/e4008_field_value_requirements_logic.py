"""Applicability of a field-value assignment in a simulation configuration.

Anchor: ECSS-E-ST-40-08 clause 5.2.2.2 (field value requirements -- the single
obligation that a field value supplied by the configuration is applicable to
the field it addresses). Paraphrased into an implementable procedure; no
standard text is reproduced.

The one normative item implemented here
---------------------------------------
A field value is applicable when, and only when, its path resolves on the
declared type of the target instance to a single primitive field, that field
is published and settable at configuration time, every array subscript on the
way is inside the declared multiplicity, the supplied value conforms to the
field's primitive type and to any declared range or allowed set, and no other
assignment in the same configuration already addresses that resolved address.

The item is one item, but it is not one test: the reasons an assignment can be
inapplicable are distinct repairs, so each failure is reported with the reason
that produced it rather than as a bare verdict.
"""

import re

__all__ = [
    "NORMATIVE_ITEM",
    "NORMATIVE_ITEM_COUNT",
    "PRIMITIVE_TYPES",
    "SETTABLE_ACCESS",
    "parse_field_path",
    "build_type_registry",
    "resolve_field",
    "canonical_address",
    "value_conforms_to_field",
    "assess_field_value",
    "assess_field_values",
]

NORMATIVE_ITEM = "field-value-assignment-is-applicable"
NORMATIVE_ITEM_COUNT = 1

PRIMITIVE_TYPES = ("Int32", "Float64", "Bool", "String8")

# Access kinds a configuration may write. An output field is produced by the
# model at run time and a constant field is fixed by the catalogue; neither is
# a legal target for a configured value.
SETTABLE_ACCESS = ("settable", "input", "state")
_ALL_ACCESS = SETTABLE_ACCESS + ("output", "constant", "read-only")

_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_INDEX_RE = re.compile(r"\[(\d+)\]")


def _require_text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty or blank" % label)
    return text


def parse_field_path(path):
    """Return the ordered steps of a field path such as 'state.rate[2]'.

    Each step is ('field', name) or ('index', integer).
    """
    text = _require_text(path, "field path")
    steps = []
    position = 0
    expect_field = True
    while position < len(text):
        if expect_field:
            match = _NAME_RE.match(text, position)
            if not match:
                raise ValueError(
                    "field path %r: expected a field name at offset %d" % (text, position)
                )
            steps.append(("field", match.group(0)))
            position = match.end()
            expect_field = False
            continue
        if text[position] == ".":
            position += 1
            expect_field = True
            continue
        match = _INDEX_RE.match(text, position)
        if not match:
            raise ValueError(
                "field path %r: expected '.' or '[index]' at offset %d" % (text, position)
            )
        steps.append(("index", int(match.group(1))))
        position = match.end()
    if expect_field:
        raise ValueError("field path %r ends with a separator" % text)
    if not steps:
        raise ValueError("field path %r resolved to no steps" % text)
    return steps


def build_type_registry(types):
    """Return a {type name: declaration} registry over the catalogue types."""
    if not isinstance(types, (list, tuple)):
        raise ValueError("types must be a sequence of type declarations")
    if not types:
        raise ValueError("the type registry must declare at least one type")
    registry = {}
    for position, declaration in enumerate(types):
        if not isinstance(declaration, dict):
            raise ValueError("types[%d] must be a mapping" % position)
        name = _require_text(declaration.get("name"), "types[%d]['name']" % position)
        if name in registry:
            raise ValueError("type %r is declared twice" % name)
        fields = declaration.get("fields")
        if not isinstance(fields, (list, tuple)) or not fields:
            raise ValueError("type %r must declare at least one field" % name)
        by_name = {}
        for order, field in enumerate(fields):
            if not isinstance(field, dict):
                raise ValueError("type %r field %d must be a mapping" % (name, order))
            field_name = _require_text(field.get("name"), "type %r field name" % name)
            field_type = _require_text(field.get("type"), "type %r field type" % name)
            if field_name in by_name:
                raise ValueError("type %r declares field %r twice" % (name, field_name))
            multiplicity = field.get("multiplicity", 1)
            if not isinstance(multiplicity, int) or isinstance(multiplicity, bool):
                raise ValueError("field %r multiplicity must be an integer" % field_name)
            if multiplicity < 1:
                raise ValueError("field %r multiplicity must be at least 1" % field_name)
            access = field.get("access", "settable")
            if access not in _ALL_ACCESS:
                raise ValueError(
                    "field %r declares unknown access %r" % (field_name, access)
                )
            published = field.get("published", True)
            if not isinstance(published, bool):
                raise ValueError("field %r 'published' must be a boolean" % field_name)
            record = dict(field)
            record.update({
                "name": field_name,
                "type": field_type,
                "multiplicity": multiplicity,
                "access": access,
                "published": published,
            })
            by_name[field_name] = record
        registry[name] = {"name": name, "fields": by_name}
    for name, declaration in registry.items():
        for field in declaration["fields"].values():
            if field["type"] not in PRIMITIVE_TYPES and field["type"] not in registry:
                raise ValueError(
                    "type %r field %r names unknown type %r"
                    % (name, field["name"], field["type"])
                )
    return registry


def resolve_field(registry, root_type, path):
    """Resolve a field path on a type, returning (descriptor, reason).

    On success ``descriptor`` is the leaf field record and ``reason`` is None.
    On failure ``descriptor`` is None and ``reason`` names what went wrong.
    """
    if not isinstance(registry, dict) or not registry:
        raise ValueError("registry must be the mapping returned by build_type_registry")
    root = _require_text(root_type, "root type")
    if root not in registry:
        raise ValueError("root type %r is not in the registry" % root)
    steps = parse_field_path(path)
    cursor_type = root
    field = None
    needs_subscript = False
    for kind, token in steps:
        if kind == "field":
            if needs_subscript:
                return None, "field %r is an array and needs a subscript" % field["name"]
            if cursor_type in PRIMITIVE_TYPES:
                return None, "path descends into primitive field %r" % field["name"]
            declaration = registry[cursor_type]
            field = declaration["fields"].get(token)
            if field is None:
                return None, "type %r publishes no field %r" % (cursor_type, token)
            cursor_type = field["type"]
            needs_subscript = field["multiplicity"] > 1
        else:
            if field is None or not needs_subscript:
                return None, "subscript %d applied to a field that is not an array" % token
            if token >= field["multiplicity"]:
                return None, (
                    "subscript %d is outside the declared multiplicity %d of field %r"
                    % (token, field["multiplicity"], field["name"])
                )
            needs_subscript = False
    if field is None:
        return None, "path resolved to no field"
    if needs_subscript:
        return None, "field %r is an array and needs a subscript" % field["name"]
    if cursor_type not in PRIMITIVE_TYPES:
        return None, "path stops on structure %r, not on a primitive field" % cursor_type
    descriptor = dict(field)
    descriptor["resolved_type"] = cursor_type
    return descriptor, None


def value_conforms_to_field(value, field):
    """Return a reason string when the value does not fit the field, else None."""
    if not isinstance(field, dict) or "resolved_type" not in field:
        raise ValueError("field must be a resolved field descriptor")
    declared = field["resolved_type"]
    if declared == "Bool":
        if not isinstance(value, bool):
            return "field declares Bool but the value is %s" % type(value).__name__
    elif declared == "Int32":
        if not isinstance(value, int) or isinstance(value, bool):
            return "field declares Int32 but the value is %s" % type(value).__name__
    elif declared == "Float64":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return "field declares Float64 but the value is %s" % type(value).__name__
    else:
        if not isinstance(value, str):
            return "field declares String8 but the value is %s" % type(value).__name__
    allowed = field.get("allowed")
    if allowed is not None:
        if not isinstance(allowed, (list, tuple, set, frozenset)) or not allowed:
            raise ValueError("field 'allowed' must be a non-empty collection")
        if value not in allowed:
            return "value %r is outside the allowed set of field %r" % (value, field["name"])
    minimum = field.get("minimum")
    maximum = field.get("maximum")
    if minimum is not None or maximum is not None:
        if declared not in ("Int32", "Float64"):
            raise ValueError(
                "field %r declares a numeric bound on a %s field"
                % (field["name"], declared)
            )
        if minimum is not None and float(value) < float(minimum):
            return "value %r is below the inclusive minimum %r" % (value, minimum)
        if maximum is not None and float(value) > float(maximum):
            return "value %r is above the inclusive maximum %r" % (value, maximum)
    return None


def canonical_address(root_type, path):
    """Return the normalised address a field path names on a root type."""
    root = _require_text(root_type, "root type")
    parts = []
    for kind, token in parse_field_path(path):
        if kind == "field":
            parts.append("." + token)
        else:
            parts.append("[%d]" % token)
    return root + "".join(parts)


def assess_field_value(assignment, registry, root_type, taken=None):
    """Grade one field-value assignment against the single clause 5.2.2.2 item."""
    if not isinstance(assignment, dict):
        raise ValueError("assignment must be a mapping")
    for key in ("field", "value"):
        if key not in assignment:
            raise ValueError("assignment is missing required key '%s'" % key)
    if taken is None:
        taken = set()
    if not isinstance(taken, set):
        raise ValueError("taken must be a set of already-addressed field paths")

    path = _require_text(assignment["field"], "assignment['field']")
    record = {"field": path, "item": NORMATIVE_ITEM, "applicable": False, "reason": None}

    try:
        descriptor, reason = resolve_field(registry, root_type, path)
    except ValueError as exc:
        record["reason"] = str(exc)
        return record
    if descriptor is None:
        record["reason"] = reason
        return record
    if not descriptor["published"]:
        record["reason"] = "field %r is not published by the type" % descriptor["name"]
        return record
    if descriptor["access"] not in SETTABLE_ACCESS:
        record["reason"] = (
            "field %r has access %r and is not settable from the configuration"
            % (descriptor["name"], descriptor["access"])
        )
        return record

    mismatch = value_conforms_to_field(assignment["value"], descriptor)
    if mismatch:
        record["reason"] = mismatch
        return record

    canonical = canonical_address(root_type, path)
    if canonical in taken:
        record["reason"] = "field %r is already assigned by an earlier value" % path
        return record
    taken.add(canonical)

    record["applicable"] = True
    record["resolved_type"] = descriptor["resolved_type"]
    return record


def assess_field_values(spec):
    """Run the clause 5.2.2.2 assessment over every field value of an instance.

    spec keys: 'types' (type declarations), 'root_type', 'assignments'.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("types", "root_type", "assignments"):
        if key not in spec:
            raise ValueError("spec is missing required key '%s'" % key)
    assignments = spec["assignments"]
    if not isinstance(assignments, (list, tuple)):
        raise ValueError("spec['assignments'] must be a sequence")
    if not assignments:
        raise ValueError("spec['assignments'] must hold at least one assignment")
    registry = build_type_registry(spec["types"])
    taken = set()
    records = [assess_field_value(a, registry, spec["root_type"], taken) for a in assignments]
    findings = [
        "%s: %s" % (r["field"], r["reason"]) for r in records if not r["applicable"]
    ]
    applicable = sum(1 for r in records if r["applicable"])
    return {
        "records": records,
        "assignment_count": len(records),
        "applicable_count": applicable,
        "item_count": NORMATIVE_ITEM_COUNT,
        "findings": findings,
        "compliant": applicable == len(records),
    }
