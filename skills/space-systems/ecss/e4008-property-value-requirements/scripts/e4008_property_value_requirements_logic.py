"""Grading of property values supplied by a simulation configuration.

Anchor: ECSS-E-ST-40-08 clause 5.2.3.2 (property value requirements -- the
five obligations a configured property value has to meet). Paraphrased into an
implementable procedure; no standard text is reproduced.

A property differs from a field: it is reached through an accessor pair rather
than directly, it carries an access kind of its own, and it may be backed by a
field that the same configuration can also address. Those three differences
are what the five items below are about.

The five normative items implemented here
-----------------------------------------
a. The property is declared by the target type and published to the
   configuration.
b. The declared access permits a write from the configuration: a read-only
   property has no setter to call, whatever its backing field allows.
c. The supplied value conforms to the property's declared type.
d. The supplied value satisfies the declared constraint: membership of an
   allowed set, an inclusive numeric range, or a string length bound.
e. The property receives exactly one value, and the configuration does not
   also write the field that backs it -- the order in which a setter call and
   a direct field write would be applied is not determined, so configuring
   both leaves the initial state ambiguous.
"""

__all__ = [
    "NORMATIVE_ITEMS",
    "NORMATIVE_ITEM_COUNT",
    "PROPERTY_TYPES",
    "ACCESS_KINDS",
    "WRITABLE_ACCESS",
    "build_property_table",
    "access_permits_write",
    "value_conforms_to_type",
    "constraint_violation",
    "assess_property_value",
    "assess_property_values",
]

NORMATIVE_ITEMS = (
    "property-declared-and-published",
    "access-permits-configuration-write",
    "value-conforms-to-declared-type",
    "value-satisfies-declared-constraint",
    "single-value-and-no-backing-field-conflict",
)
NORMATIVE_ITEM_COUNT = len(NORMATIVE_ITEMS)

PROPERTY_TYPES = ("Int32", "Float64", "Bool", "String8")

ACCESS_KINDS = ("readOnly", "writeOnly", "readWrite")
WRITABLE_ACCESS = ("writeOnly", "readWrite")


def _require_text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty or blank" % label)
    return text


def build_property_table(properties):
    """Return a {name: declaration} table over the published properties."""
    if not isinstance(properties, (list, tuple)):
        raise ValueError("properties must be a sequence of declarations")
    if not properties:
        raise ValueError("the target type must declare at least one property")
    table = {}
    for position, spec in enumerate(properties):
        if not isinstance(spec, dict):
            raise ValueError("properties[%d] must be a mapping" % position)
        for key in ("name", "type", "access"):
            if key not in spec:
                raise ValueError("properties[%d] is missing '%s'" % (position, key))
        name = _require_text(spec["name"], "properties[%d]['name']" % position)
        declared = _require_text(spec["type"], "properties[%d]['type']" % position)
        access = _require_text(spec["access"], "properties[%d]['access']" % position)
        if declared not in PROPERTY_TYPES:
            raise ValueError(
                "property %r declares unsupported type %r (supported: %s)"
                % (name, declared, ", ".join(PROPERTY_TYPES))
            )
        if access not in ACCESS_KINDS:
            raise ValueError(
                "property %r declares unknown access %r (known: %s)"
                % (name, access, ", ".join(ACCESS_KINDS))
            )
        if name in table:
            raise ValueError("type declares property %r twice" % name)
        published = spec.get("published", True)
        if not isinstance(published, bool):
            raise ValueError("property %r 'published' must be a boolean" % name)
        backing = spec.get("backing_field")
        if backing is not None:
            backing = _require_text(backing, "property %r backing field" % name)
        record = dict(spec)
        record.update({
            "name": name,
            "type": declared,
            "access": access,
            "published": published,
            "backing_field": backing,
        })
        table[name] = record
    return table


def access_permits_write(access):
    """Return True when a configuration may write a property of this access."""
    text = _require_text(access, "access")
    if text not in ACCESS_KINDS:
        raise ValueError("unknown access kind %r" % text)
    return text in WRITABLE_ACCESS


def value_conforms_to_type(value, declared):
    """Return True when the value matches the declared property type."""
    if declared not in PROPERTY_TYPES:
        raise ValueError("unsupported declared type %r" % (declared,))
    if declared == "Bool":
        return isinstance(value, bool)
    if declared == "Int32":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared == "Float64":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, str)


def constraint_violation(value, declaration):
    """Return a finding string when the value breaks a declared constraint."""
    if not isinstance(declaration, dict):
        raise ValueError("declaration must be a mapping")
    allowed = declaration.get("allowed")
    if allowed is not None:
        if not isinstance(allowed, (list, tuple, set, frozenset)) or not allowed:
            raise ValueError("'allowed' must be a non-empty collection")
        if value not in allowed:
            return "value %r is outside the allowed set" % (value,)
    minimum = declaration.get("minimum")
    maximum = declaration.get("maximum")
    if minimum is not None or maximum is not None:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return "a numeric bound was declared but the value is not numeric"
        if minimum is not None and float(value) < float(minimum):
            return "value %r is below the inclusive minimum %r" % (value, minimum)
        if maximum is not None and float(value) > float(maximum):
            return "value %r is above the inclusive maximum %r" % (value, maximum)
    max_length = declaration.get("max_length")
    if max_length is not None:
        if not isinstance(max_length, int) or isinstance(max_length, bool) or max_length < 0:
            raise ValueError("'max_length' must be a non-negative integer")
        if isinstance(value, str) and len(value) > max_length:
            return "value is %d characters, over the %d-character bound" % (
                len(value), max_length
            )
    return None


def assess_property_value(assignment, table, seen=None, configured_fields=()):
    """Grade one property value against the five clause 5.2.3.2 items.

    ``seen`` is the set of property names already given a value and is updated
    in place. ``configured_fields`` is the set of field paths the same
    configuration writes directly.
    """
    if not isinstance(assignment, dict):
        raise ValueError("assignment must be a mapping")
    for key in ("property", "value"):
        if key not in assignment:
            raise ValueError("assignment is missing required key '%s'" % key)
    if not isinstance(table, dict) or not table:
        raise ValueError("table must be the mapping returned by build_property_table")
    if seen is None:
        seen = set()
    if not isinstance(seen, set):
        raise ValueError("seen must be a set of property names")
    if not isinstance(configured_fields, (list, tuple, set, frozenset)):
        raise ValueError("configured_fields must be a collection of field paths")

    name = _require_text(assignment["property"], "assignment['property']")
    value = assignment["value"]
    items = {key: True for key in NORMATIVE_ITEMS}
    findings = []

    declaration = table.get(name)
    if declaration is None or not declaration["published"]:
        items[NORMATIVE_ITEMS[0]] = False
        findings.append("property %r is not declared and published by the type" % name)
        for key in NORMATIVE_ITEMS[1:]:
            items[key] = False
        return {
            "property": name,
            "items": items,
            "findings": findings,
            "satisfied": 0,
            "compliant": False,
        }

    if not access_permits_write(declaration["access"]):
        items[NORMATIVE_ITEMS[1]] = False
        findings.append(
            "property %r has access %r and offers no setter to the configuration"
            % (name, declaration["access"])
        )

    if not value_conforms_to_type(value, declaration["type"]):
        items[NORMATIVE_ITEMS[2]] = False
        findings.append(
            "property %r declares %s but the value is %s"
            % (name, declaration["type"], type(value).__name__)
        )
    else:
        violation = constraint_violation(value, declaration)
        if violation:
            items[NORMATIVE_ITEMS[3]] = False
            findings.append("property %r: %s" % (name, violation))

    if name in seen:
        items[NORMATIVE_ITEMS[4]] = False
        findings.append("property %r is given a value more than once" % name)
    else:
        seen.add(name)
        backing = declaration["backing_field"]
        if backing is not None and backing in configured_fields:
            items[NORMATIVE_ITEMS[4]] = False
            findings.append(
                "property %r and its backing field %r are both configured; "
                "the applied order is not determined" % (name, backing)
            )

    satisfied = sum(1 for ok in items.values() if ok)
    return {
        "property": name,
        "items": items,
        "findings": findings,
        "satisfied": satisfied,
        "compliant": satisfied == NORMATIVE_ITEM_COUNT,
    }


def assess_property_values(spec):
    """Run the clause 5.2.3.2 assessment over every property value supplied.

    spec keys: 'properties', 'assignments', optional 'configured_fields'.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("properties", "assignments"):
        if key not in spec:
            raise ValueError("spec is missing required key '%s'" % key)
    assignments = spec["assignments"]
    if not isinstance(assignments, (list, tuple)):
        raise ValueError("spec['assignments'] must be a sequence")
    if not assignments:
        raise ValueError("spec['assignments'] must hold at least one assignment")
    table = build_property_table(spec["properties"])
    configured_fields = spec.get("configured_fields", ())
    seen = set()
    records = [
        assess_property_value(a, table, seen, configured_fields) for a in assignments
    ]
    findings = []
    for record in records:
        findings.extend(record["findings"])
    satisfied = sum(r["satisfied"] for r in records)
    return {
        "records": records,
        "assignment_count": len(records),
        "item_count": NORMATIVE_ITEM_COUNT,
        "satisfied": satisfied,
        "graded": NORMATIVE_ITEM_COUNT * len(records),
        "findings": findings,
        "compliant": all(r["compliant"] for r in records),
    }
