"""Deduced-type parameter resolution inside a packet layout.

Anchor: ECSS-E-ST-70-41C clause 7.3.12 (deduced data type, three
normative items). Paraphrased into an implementable procedure; no
standard text is reproduced.

What the clause is for. Almost every parameter in a packet has its type
fixed in the definition: this field is a 16-bit unsigned integer, that
one is an eight-character string. A deduced parameter does not. Its
type is settled while the packet is being read, from the value of
another field in the same packet -- the parameter identifier that
precedes a value in a housekeeping report, the type code that precedes
a payload in a memory-load command.

Three conditions make the deduction possible, and all three are
structural rather than numeric:

* the deducing field comes earlier in the packet than the field whose
  type it settles, so its value is already in hand when the reader
  arrives at the deduced field;
* every value the deducing field can take maps to exactly one known
  type, because the reader has no second chance -- an unmapped value
  leaves it unable to say how many bits to consume, and the rest of
  the packet is lost, not just that one parameter;
* the type each value maps to is itself known, with a size the reader
  can act on.

The consequence people miss. A deduced field does not make one
parameter uncertain, it makes the remainder of the packet uncertain.
Every field after it has moved, so a single unmapped selector value
turns a readable packet into an unreadable one. That is why the
coverage of the mapping over the selector's value space is worth
measuring at review time, not at run time.

Chains are allowed. A deduced field may itself deduce a later one, as
long as each link resolves before it is needed. A cycle, or a selector
that sits after what it selects, does not resolve at all.

Stdlib only, offline, deterministic.
"""

__all__ = [
    "FIELD_KINDS",
    "validate_catalogue",
    "type_size_bits",
    "validate_layout",
    "mapping_coverage",
    "resolve_selector_value",
    "resolve_layout",
    "assess_deduced_layout",
]

FIELD_KINDS = ("fixed", "selector", "deduced")


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def validate_catalogue(catalogue):
    """Return a normalised map of type name to its size in bits."""
    if not isinstance(catalogue, dict) or not catalogue:
        raise ValueError("catalogue must be a non-empty mapping of type name to size in bits")
    out = {}
    for name, size in catalogue.items():
        if not isinstance(name, str) or not name:
            raise ValueError("catalogue keys must be non-empty type names, got %r" % (name,))
        if not _is_int(size):
            raise ValueError("type %r must carry an integer size in bits" % (name,))
        if size < 1:
            raise ValueError("type %r must occupy at least one bit, got %d" % (name, size))
        out[name] = size
    return out


def type_size_bits(type_name, catalogue):
    """Return the bit width of a named type from the catalogue."""
    known = validate_catalogue(catalogue)
    if type_name not in known:
        raise ValueError(
            "type %r is not in the catalogue; a deduced field cannot be sized against a type "
            "the reader does not know" % (type_name,)
        )
    return known[type_name]


def validate_layout(fields):
    """Return a normalised, position-checked packet layout.

    Each field is a mapping with 'name' and 'kind'. A fixed field carries
    'size_bits'. A selector field carries 'size_bits' and 'values' (the
    values it can take). A deduced field carries 'deduced_from' (the name of
    its selector) and 'mapping' (selector value to type name).
    """
    if not isinstance(fields, (list, tuple)) or not fields:
        raise ValueError("a layout must be a non-empty ordered sequence of fields")
    seen = {}
    out = []
    for index, field in enumerate(fields):
        if not isinstance(field, dict):
            raise ValueError("field at position %d must be a mapping" % index)
        name = field.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("field at position %d needs a non-empty 'name'" % index)
        if name in seen:
            raise ValueError(
                "field name %r appears twice, at positions %d and %d; a selector reference "
                "would be ambiguous" % (name, seen[name], index)
            )
        kind = field.get("kind")
        if kind not in FIELD_KINDS:
            raise ValueError(
                "field %r has kind %r; expected one of %s" % (name, kind, FIELD_KINDS)
            )
        record = {"name": name, "kind": kind, "position": index}
        if kind in ("fixed", "selector"):
            size = field.get("size_bits")
            if not _is_int(size) or size < 1:
                raise ValueError("field %r needs an integer 'size_bits' of at least 1" % name)
            record["size_bits"] = size
        if kind == "selector":
            values = field.get("values")
            if not isinstance(values, (list, tuple, set, frozenset)) or not values:
                raise ValueError("selector %r needs a non-empty 'values' collection" % name)
            normalised = []
            for value in values:
                if not _is_int(value) or value < 0:
                    raise ValueError(
                        "selector %r admits non-negative integer values only, got %r"
                        % (name, value)
                    )
                if value >= (1 << record["size_bits"]):
                    raise ValueError(
                        "selector %r admits value %d, which does not fit its %d bits"
                        % (name, value, record["size_bits"])
                    )
                normalised.append(value)
            record["values"] = sorted(set(normalised))
        if kind == "deduced":
            source = field.get("deduced_from")
            if not isinstance(source, str) or not source:
                raise ValueError("deduced field %r needs a 'deduced_from' field name" % name)
            if source not in seen:
                raise ValueError(
                    "deduced field %r is settled by %r, which does not appear before it; the "
                    "reader has not seen that value yet when it reaches this field"
                    % (name, source)
                )
            mapping = field.get("mapping")
            if not isinstance(mapping, dict) or not mapping:
                raise ValueError(
                    "deduced field %r needs a non-empty 'mapping' from selector value to type"
                    % name
                )
            normalised_map = {}
            for value, type_name in mapping.items():
                if not _is_int(value) or value < 0:
                    raise ValueError(
                        "mapping of %r is keyed by non-negative integers, got %r" % (name, value)
                    )
                if not isinstance(type_name, str) or not type_name:
                    raise ValueError(
                        "mapping of %r must name a type for value %r" % (name, value)
                    )
                normalised_map[value] = type_name
            record["deduced_from"] = source
            record["mapping"] = normalised_map
        out.append(record)
        seen[name] = index
    return out


def mapping_coverage(selector_bits, mapping):
    """Return how much of a selector's value space the mapping settles."""
    if not _is_int(selector_bits) or selector_bits < 1:
        raise ValueError("selector_bits must be an integer of at least 1")
    if not isinstance(mapping, dict):
        raise ValueError("mapping must be a mapping of selector value to type name")
    space = 1 << selector_bits
    covered = len([value for value in mapping if 0 <= value < space])
    return {"space": space, "covered": covered, "fraction": covered / float(space)}


def resolve_selector_value(field, selector_value, catalogue):
    """Return the type and size a selector value settles for a deduced field."""
    if field["kind"] != "deduced":
        raise ValueError("field %r is not a deduced field" % field["name"])
    if not _is_int(selector_value) or selector_value < 0:
        raise ValueError("selector value must be a non-negative integer, got %r"
                         % (selector_value,))
    mapping = field["mapping"]
    if selector_value not in mapping:
        raise ValueError(
            "selector value %d settles no type for %r; the reader cannot tell how many bits "
            "to consume, so every field after this one is lost as well"
            % (selector_value, field["name"])
        )
    type_name = mapping[selector_value]
    return {"type": type_name, "size_bits": type_size_bits(type_name, catalogue)}


def resolve_layout(fields, selector_values, catalogue):
    """Resolve every deduced field of a layout and size the whole packet."""
    layout = validate_layout(fields)
    known = validate_catalogue(catalogue)
    if not isinstance(selector_values, dict):
        raise ValueError("selector_values must be a mapping of field name to value")
    resolved = []
    total_bits = 0
    for field in layout:
        if field["kind"] in ("fixed", "selector"):
            entry = {"name": field["name"], "kind": field["kind"],
                     "size_bits": field["size_bits"], "type": None}
            if field["kind"] == "selector":
                if field["name"] not in selector_values:
                    raise ValueError(
                        "selector %r has no value in this packet; nothing downstream of it "
                        "can be resolved" % field["name"]
                    )
                value = selector_values[field["name"]]
                if value not in field["values"]:
                    raise ValueError(
                        "selector %r took value %r, which its definition does not admit"
                        % (field["name"], value)
                    )
                entry["value"] = value
        else:
            source = field["deduced_from"]
            if source not in selector_values:
                raise ValueError(
                    "deduced field %r needs the value of %r, which this packet does not carry"
                    % (field["name"], source)
                )
            settled = resolve_selector_value(field, selector_values[source], known)
            entry = {"name": field["name"], "kind": "deduced",
                     "size_bits": settled["size_bits"], "type": settled["type"],
                     "deduced_from": source}
        total_bits += entry["size_bits"]
        resolved.append(entry)
    return {"fields": resolved, "total_bits": total_bits,
            "total_octets": (total_bits + 7) // 8,
            "octet_aligned": total_bits % 8 == 0}


def assess_deduced_layout(fields, catalogue, selector_samples=None):
    """Assess a layout for the structural conditions a deduction depends on."""
    layout = validate_layout(fields)
    known = validate_catalogue(catalogue)
    findings = []
    selectors = {f["name"]: f for f in layout if f["kind"] == "selector"}
    deduced = [f for f in layout if f["kind"] == "deduced"]
    if not deduced:
        findings.append("the layout declares no deduced field; clause 7.3.12 does not apply")
    coverage = {}
    for field in deduced:
        source = field["deduced_from"]
        if source not in selectors:
            findings.append(
                "deduced field %r is settled by %r, which is not a selector field"
                % (field["name"], source)
            )
            continue
        selector = selectors[source]
        report = mapping_coverage(selector["size_bits"], field["mapping"])
        coverage[field["name"]] = report
        admitted = set(selector["values"])
        unmapped = sorted(admitted - set(field["mapping"]))
        if unmapped:
            findings.append(
                "selector %r admits %s, for which %r settles no type; a packet carrying one "
                "of those values is unreadable from that field onwards"
                % (source, ", ".join(str(v) for v in unmapped), field["name"])
            )
        unknown_types = sorted({t for t in field["mapping"].values() if t not in known})
        if unknown_types:
            findings.append(
                "mapping of %r names %s, absent from the catalogue"
                % (field["name"], ", ".join(unknown_types))
            )
        stale = sorted(set(field["mapping"]) - admitted)
        if stale:
            findings.append(
                "mapping of %r settles types for %s, which selector %r never takes"
                % (field["name"], ", ".join(str(v) for v in stale), source)
            )
    sized = []
    for sample in selector_samples or []:
        try:
            sized.append(resolve_layout(fields, sample, catalogue))
        except ValueError as exc:
            findings.append("a sample selector set does not resolve: %s" % exc)
    widths = sorted({record["total_bits"] for record in sized})
    if len(widths) > 1:
        variable = True
    else:
        variable = False
    return {
        "deduced_fields": [f["name"] for f in deduced],
        "coverage": coverage,
        "resolved_samples": sized,
        "distinct_widths_bits": widths,
        "variable_length_packet": variable,
        "findings": findings,
        "resolvable": not findings,
    }
