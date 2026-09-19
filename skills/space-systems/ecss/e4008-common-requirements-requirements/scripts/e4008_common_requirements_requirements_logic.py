"""Common obligations carried by every element of a simulation configuration.

Anchor: ECSS-E-ST-40-08 clause 5.1.2 (common requirements -- the five
obligations that apply to every configuration element regardless of what kind
of element it is). Paraphrased into an implementable procedure; no standard
text is reproduced.

The five normative items implemented here
-----------------------------------------
a. The element name is a well-formed identifier: an initial letter or
   underscore, then letters, digits or underscores, within a length bound, and
   not one of the reserved words the configuration language keeps for itself.
b. The name is unique inside its own parent scope. Uniqueness across the whole
   document is neither required nor sufficient: two sibling elements sharing a
   name are ambiguous even when the document holds no other copy.
c. The reference the element carries resolves to a path the model catalogue
   actually publishes.
d. The kind the element declares agrees with the kind of the catalogue target
   the reference resolved to. A resolvable reference to the wrong sort of
   target is a silent mis-wiring, not a naming slip.
e. The element uuid is well-formed and appears once across the configuration.

Every check yields a per-element record naming which of the five items it
satisfied, so a partially compliant element is reported as such rather than
collapsed into a single pass/fail.
"""

import re

__all__ = [
    "IDENTIFIER_MAX_LENGTH",
    "NORMATIVE_ITEM_COUNT",
    "NORMATIVE_ITEMS",
    "RESERVED_WORDS",
    "validate_identifier",
    "validate_uuid",
    "build_catalogue_index",
    "resolve_reference",
    "scope_key",
    "assess_element",
    "assess_configuration",
    "compliance_ratio",
]

IDENTIFIER_MAX_LENGTH = 64

# The five obligations of clause 5.1.2, in the order they are graded.
NORMATIVE_ITEMS = (
    "identifier-well-formed",
    "name-unique-in-parent-scope",
    "reference-resolves-in-catalogue",
    "declared-kind-agrees-with-target",
    "uuid-well-formed-and-unique",
)
NORMATIVE_ITEM_COUNT = len(NORMATIVE_ITEMS)

# Words the configuration language keeps for its own structure; an element may
# not take one as its name even though the character pattern would allow it.
RESERVED_WORDS = frozenset(
    ("assembly", "catalogue", "configuration", "field", "instance",
     "model", "operation", "property", "reference", "schedule", "type")
)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def _require_text(value, label):
    """Return a non-empty stripped string or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty or blank" % label)
    return text


def validate_identifier(name):
    """Return the validated element identifier, or raise ValueError."""
    text = _require_text(name, "element name")
    if len(text) > IDENTIFIER_MAX_LENGTH:
        raise ValueError(
            "element name %r is %d characters, over the %d-character bound"
            % (text, len(text), IDENTIFIER_MAX_LENGTH)
        )
    if not _IDENTIFIER_RE.match(text):
        raise ValueError(
            "element name %r is not a well-formed identifier "
            "(letter or underscore first, then letters, digits, underscores)" % text
        )
    if text.lower() in RESERVED_WORDS:
        raise ValueError("element name %r is a reserved word of the configuration" % text)
    return text


def validate_uuid(value):
    """Return the lower-cased canonical uuid, or raise ValueError."""
    text = _require_text(value, "element uuid").lower()
    if not _UUID_RE.match(text):
        raise ValueError(
            "element uuid %r is not in the 8-4-4-4-12 hexadecimal form" % text
        )
    return text


def build_catalogue_index(catalogue):
    """Return a {path: kind} index over the published catalogue entries."""
    if not isinstance(catalogue, (list, tuple)):
        raise ValueError("catalogue must be a sequence of entries")
    if not catalogue:
        raise ValueError("catalogue must publish at least one entry")
    index = {}
    for position, entry in enumerate(catalogue):
        if not isinstance(entry, dict):
            raise ValueError("catalogue[%d] must be a mapping" % position)
        for key in ("path", "kind"):
            if key not in entry:
                raise ValueError("catalogue[%d] is missing '%s'" % (position, key))
        path = _require_text(entry["path"], "catalogue[%d]['path']" % position)
        kind = _require_text(entry["kind"], "catalogue[%d]['kind']" % position)
        if path in index:
            raise ValueError("catalogue publishes path %r twice" % path)
        index[path] = kind
    return index


def resolve_reference(index, path):
    """Return the catalogue kind at a reference path, or None when unresolved."""
    if not isinstance(index, dict):
        raise ValueError("index must be the mapping returned by build_catalogue_index")
    text = _require_text(path, "reference path")
    return index.get(text)


def scope_key(parent):
    """Return the normalised parent-scope key an element's name is unique within."""
    if parent is None:
        return ""
    if not isinstance(parent, str):
        raise ValueError("parent scope must be a string or None")
    return parent.strip().strip("/")


def _grade(record, item, ok, finding=None):
    """Record the verdict for one normative item on one element."""
    record["items"][item] = bool(ok)
    if not ok and finding:
        record["findings"].append(finding)


def assess_element(element, index, seen_names=None, seen_uuids=None):
    """Grade one configuration element against the five common obligations.

    ``seen_names`` maps a parent-scope key to the set of names already taken in
    it; ``seen_uuids`` is the set of uuids already used. Both are updated in
    place so a caller can walk a document element by element.
    """
    if not isinstance(element, dict):
        raise ValueError("element must be a mapping")
    for key in ("name", "uuid", "reference", "kind"):
        if key not in element:
            raise ValueError("element is missing required key '%s'" % key)
    if seen_names is None:
        seen_names = {}
    if seen_uuids is None:
        seen_uuids = set()
    if not isinstance(seen_names, dict):
        raise ValueError("seen_names must be a mapping of scope key to name set")
    if not isinstance(seen_uuids, set):
        raise ValueError("seen_uuids must be a set")

    parent = scope_key(element.get("parent"))
    record = {
        "name": element["name"],
        "parent": parent,
        "items": {},
        "findings": [],
    }

    try:
        name = validate_identifier(element["name"])
        _grade(record, NORMATIVE_ITEMS[0], True)
    except ValueError as exc:
        name = None
        _grade(record, NORMATIVE_ITEMS[0], False, str(exc))

    taken = seen_names.setdefault(parent, set())
    if name is None:
        _grade(record, NORMATIVE_ITEMS[1], False,
               "name uniqueness cannot be graded for a malformed identifier")
    elif name in taken:
        _grade(record, NORMATIVE_ITEMS[1], False,
               "name %r is already used in parent scope %r" % (name, parent or "<root>"))
    else:
        taken.add(name)
        _grade(record, NORMATIVE_ITEMS[1], True)

    resolved_kind = None
    try:
        resolved_kind = resolve_reference(index, element["reference"])
        if resolved_kind is None:
            _grade(record, NORMATIVE_ITEMS[2], False,
                   "reference %r does not resolve in the catalogue" % element["reference"])
        else:
            _grade(record, NORMATIVE_ITEMS[2], True)
    except ValueError as exc:
        _grade(record, NORMATIVE_ITEMS[2], False, str(exc))

    declared = element["kind"]
    if resolved_kind is None:
        _grade(record, NORMATIVE_ITEMS[3], False,
               "declared kind cannot be compared against an unresolved reference")
    elif not isinstance(declared, str) or declared.strip() != resolved_kind:
        _grade(record, NORMATIVE_ITEMS[3], False,
               "element declares kind %r but the catalogue target is %r"
               % (declared, resolved_kind))
    else:
        _grade(record, NORMATIVE_ITEMS[3], True)

    try:
        uuid_text = validate_uuid(element["uuid"])
        if uuid_text in seen_uuids:
            _grade(record, NORMATIVE_ITEMS[4], False,
                   "uuid %s is used by more than one element" % uuid_text)
        else:
            seen_uuids.add(uuid_text)
            _grade(record, NORMATIVE_ITEMS[4], True)
    except ValueError as exc:
        _grade(record, NORMATIVE_ITEMS[4], False, str(exc))

    record["satisfied"] = sum(1 for ok in record["items"].values() if ok)
    record["compliant"] = record["satisfied"] == NORMATIVE_ITEM_COUNT
    return record


def compliance_ratio(satisfied, total):
    """Return the satisfied fraction of graded items as a float in [0, 1]."""
    for label, value in (("satisfied", satisfied), ("total", total)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer" % label)
        if value < 0:
            raise ValueError("%s must not be negative, got %d" % (label, value))
    if total == 0:
        raise ValueError("total must be positive to form a ratio")
    if satisfied > total:
        raise ValueError("satisfied %d exceeds total %d" % (satisfied, total))
    return satisfied / total


def assess_configuration(config):
    """Walk a configuration and grade every element against clause 5.1.2.

    config keys: 'catalogue' (sequence of {path, kind}) and 'elements'
    (sequence of {name, uuid, reference, kind, optional parent, description}).
    """
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    for key in ("catalogue", "elements"):
        if key not in config:
            raise ValueError("config is missing required key '%s'" % key)
    elements = config["elements"]
    if not isinstance(elements, (list, tuple)):
        raise ValueError("config['elements'] must be a sequence")
    if not elements:
        raise ValueError("config['elements'] must hold at least one element")
    index = build_catalogue_index(config["catalogue"])

    seen_names = {}
    seen_uuids = set()
    records = [assess_element(e, index, seen_names, seen_uuids) for e in elements]

    satisfied = sum(r["satisfied"] for r in records)
    total = NORMATIVE_ITEM_COUNT * len(records)
    findings = []
    for record in records:
        for text in record["findings"]:
            findings.append("%s: %s" % (record["name"], text))
    return {
        "records": records,
        "element_count": len(records),
        "item_count": NORMATIVE_ITEM_COUNT,
        "satisfied": satisfied,
        "graded": total,
        "ratio": compliance_ratio(satisfied, total),
        "findings": findings,
        "compliant": all(r["compliant"] for r in records),
    }
