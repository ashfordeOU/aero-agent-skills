"""Validation rules applied to a simulator exchange file.

Anchor: ECSS-E-ST-40-08C clause 5.7.2.2 (validation rules). Paraphrased
into an implementable procedure; no standard text is reproduced. The
clause carries two normative items.

Items implemented here
----------------------
VR-01 -- structural validation. Every entry carries the fields its kind
requires, each field holds a value of the declared type, and nothing
outside the declared field set is smuggled in. This is the pass that
can be made without looking at any other entry.

VR-02 -- referential validation. Identifiers are unique across the
whole file, every reference resolves to an entry that exists and is of
the kind the reference expects, and the reference graph carries no
cycle. This is the pass that needs the whole file in hand.

The two passes are kept apart deliberately: a structurally broken entry
cannot be resolved against, so its referential findings would be noise.
Entries that fail structure are excluded from the reference graph and
reported as such rather than being silently dropped.
"""

__all__ = [
    "NORMATIVE_ITEM_COUNT",
    "NORMATIVE_ITEMS",
    "ENTRY_KINDS",
    "FIELD_TYPES",
    "REFERENCE_TARGETS",
    "validate_identifier",
    "validate_entry_structure",
    "validate_structure_pass",
    "validate_reference_pass",
    "detect_reference_cycles",
    "assess_validation_rules",
]

NORMATIVE_ITEM_COUNT = 2

NORMATIVE_ITEMS = (
    ("VR-01", "every entry is structurally complete and correctly typed"),
    ("VR-02", "identifiers are unique and every reference resolves without a cycle"),
)

# Each kind declares its required fields and the type each one holds.
ENTRY_KINDS = {
    "model": {
        "required": ("id", "kind", "name", "type_ref"),
        "optional": ("parent_ref", "description"),
    },
    "type": {
        "required": ("id", "kind", "name"),
        "optional": ("base_ref", "description"),
    },
    "link": {
        "required": ("id", "kind", "source_ref", "target_ref"),
        "optional": ("description",),
    },
    "schedule_entry": {
        "required": ("id", "kind", "name", "model_ref", "period_ticks"),
        "optional": ("description",),
    },
}

FIELD_TYPES = {
    "id": "identifier",
    "kind": "kind",
    "name": "text",
    "description": "text",
    "type_ref": "identifier",
    "parent_ref": "identifier",
    "base_ref": "identifier",
    "source_ref": "identifier",
    "target_ref": "identifier",
    "model_ref": "identifier",
    "period_ticks": "positive_integer",
}

# The kind each reference field has to point at.
REFERENCE_TARGETS = {
    "type_ref": "type",
    "parent_ref": "model",
    "base_ref": "type",
    "source_ref": "model",
    "target_ref": "model",
    "model_ref": "model",
}


def validate_identifier(value, label="identifier"):
    """Return the validated identifier token."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if text != value:
        raise ValueError("%s must not carry leading or trailing blanks: %r" % (label, value))
    if not text:
        raise ValueError("%s must not be empty" % label)
    if len(text) > 128:
        raise ValueError("%s must be at most 128 characters, got %d" % (label, len(text)))
    if not (text[0].isalpha() or text[0] == "_"):
        raise ValueError("%s must start with a letter or underscore: %r" % (label, value))
    for char in text:
        if not (char.isalnum() or char in "_./"):
            raise ValueError(
                "%s may only carry letters, digits, underscore, dot and slash: %r"
                % (label, value)
            )
    return text


def _type_ok(field, value):
    expected = FIELD_TYPES[field]
    if expected == "identifier":
        try:
            validate_identifier(value, field)
        except ValueError:
            return False
        return True
    if expected == "kind":
        return isinstance(value, str) and value.strip().lower() in ENTRY_KINDS
    if expected == "text":
        return isinstance(value, str) and bool(value.strip())
    # positive_integer
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def validate_entry_structure(entry, position=0):
    """Return the structural findings of one entry."""
    if not isinstance(entry, dict):
        raise ValueError("entry at position %d must be a mapping" % position)
    findings = []
    kind_value = entry.get("kind")
    if not isinstance(kind_value, str) or kind_value.strip().lower() not in ENTRY_KINDS:
        return {
            "position": position,
            "id": entry.get("id"),
            "kind": None,
            "compliant": False,
            "findings": ["entry at position %d declares an unknown kind %r"
                         % (position, kind_value)],
        }
    kind = kind_value.strip().lower()
    schema = ENTRY_KINDS[kind]
    allowed = set(schema["required"]) | set(schema["optional"])
    for field in schema["required"]:
        if field not in entry:
            findings.append(
                "entry at position %d of kind %r is missing the field %r"
                % (position, kind, field)
            )
    for field in sorted(entry):
        if field not in allowed:
            findings.append(
                "entry at position %d of kind %r carries the undeclared field %r"
                % (position, kind, field)
            )
            continue
        if not _type_ok(field, entry[field]):
            findings.append(
                "entry at position %d field %r does not hold a %s"
                % (position, field, FIELD_TYPES[field])
            )
    identifier = entry.get("id") if isinstance(entry.get("id"), str) else None
    return {
        "position": position,
        "id": identifier,
        "kind": kind,
        "compliant": not findings,
        "findings": findings,
    }


def validate_structure_pass(entries):
    """Return the structural verdict over every entry in the file."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a list or tuple")
    if not entries:
        raise ValueError("entries must not be empty")
    results = [validate_entry_structure(entry, index) for index, entry in enumerate(entries)]
    findings = []
    for result in results:
        findings.extend(result["findings"])
    return {
        "results": results,
        "sound": [r for r in results if r["compliant"]],
        "unsound_positions": [r["position"] for r in results if not r["compliant"]],
        "compliant": not findings,
        "findings": findings,
    }


def detect_reference_cycles(edges):
    """Return the identifiers taking part in a reference cycle."""
    if not isinstance(edges, dict):
        raise ValueError("edges must be a mapping of identifier to referenced identifiers")
    colour = {}
    cyclic = set()

    def walk(node, stack):
        colour[node] = "grey"
        stack.append(node)
        for target in edges.get(node, ()):
            if target not in edges:
                continue
            state = colour.get(target, "white")
            if state == "white":
                walk(target, stack)
            elif state == "grey":
                start = stack.index(target)
                for member in stack[start:]:
                    cyclic.add(member)
        stack.pop()
        colour[node] = "black"

    for node in sorted(edges):
        if colour.get(node, "white") == "white":
            walk(node, [])
    return sorted(cyclic)


def validate_reference_pass(entries, structure=None):
    """Return the referential verdict over the structurally sound entries."""
    report = structure if structure is not None else validate_structure_pass(entries)
    if not isinstance(report, dict) or "results" not in report:
        raise ValueError("structure report must come from validate_structure_pass")
    findings = []
    by_id = {}
    duplicates = []
    sound_positions = set(r["position"] for r in report["sound"])
    for result in report["results"]:
        if result["position"] not in sound_positions:
            continue
        identifier = result["id"]
        if identifier in by_id:
            duplicates.append(identifier)
            findings.append(
                "identifier %r is declared by entries at positions %d and %d"
                % (identifier, by_id[identifier]["position"], result["position"])
            )
            continue
        by_id[identifier] = result
    unresolved = []
    kind_mismatch = []
    edges = dict((identifier, []) for identifier in by_id)
    for result in report["results"]:
        if result["position"] not in sound_positions:
            continue
        entry = entries[result["position"]]
        owner = result["id"]
        if owner not in by_id or by_id[owner]["position"] != result["position"]:
            continue
        for field, expected_kind in REFERENCE_TARGETS.items():
            if field not in entry:
                continue
            target = entry[field]
            if target not in by_id:
                unresolved.append((owner, field, target))
                findings.append(
                    "entry %r field %r references %r, which no entry declares"
                    % (owner, field, target)
                )
                continue
            actual_kind = by_id[target]["kind"]
            if actual_kind != expected_kind:
                kind_mismatch.append((owner, field, target, actual_kind))
                findings.append(
                    "entry %r field %r must reference a %r but %r is a %r"
                    % (owner, field, expected_kind, target, actual_kind)
                )
                continue
            edges[owner].append(target)
    cycles = detect_reference_cycles(edges)
    if cycles:
        findings.append("reference cycle through: %s" % ", ".join(cycles))
    if report["unsound_positions"]:
        findings.append(
            "entries at position(s) %s were excluded from the reference pass because "
            "they failed structural validation"
            % ", ".join(str(p) for p in report["unsound_positions"])
        )
    return {
        "identifiers": sorted(by_id),
        "duplicates": sorted(set(d for d in duplicates if d is not None)),
        "unresolved": unresolved,
        "kind_mismatch": kind_mismatch,
        "cycles": cycles,
        "excluded_positions": list(report["unsound_positions"]),
        "compliant": not findings,
        "findings": findings,
    }


def assess_validation_rules(entries):
    """Grade an exchange file body against the two normative items."""
    structure = validate_structure_pass(entries)
    references = validate_reference_pass(entries, structure)
    items = [
        {
            "id": "VR-01",
            "title": NORMATIVE_ITEMS[0][1],
            "status": "satisfied" if structure["compliant"] else "violated",
            "findings": list(structure["findings"]),
        },
        {
            "id": "VR-02",
            "title": NORMATIVE_ITEMS[1][1],
            "status": "satisfied" if references["compliant"] else "violated",
            "findings": list(references["findings"]),
        },
    ]
    findings = structure["findings"] + references["findings"]
    return {
        "items": items,
        "item_count": len(items),
        "structure": structure,
        "references": references,
        "violations": [i["id"] for i in items if i["status"] == "violated"],
        "findings": findings,
        "compliant": not findings,
    }
