"""Specification-chain evaluation for class 1 hybrid microcircuit procurement.

Anchor: ECSS-Q-ST-60-13C clause 4.6.3 (a hybrid microcircuit is procured
against its dedicated generic specification, with a detail specification for
the type). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the procurement record: a declared procurement class for the
   hybrid, a generic specification, and the constituent elements the hybrid is
   built from.
2. Confirm a generic specification governs the type at all, and that the
   detail specification cites that generic as its parent. A custom hybrid
   always needs the detail specification; a catalogue type may rest on the
   generic alone.
3. Rank every element -- die, chip resistor, chip capacitor, substrate,
   interconnect, package -- by the procurement class it was itself bought at,
   and refuse an element that carries no specification reference.
4. Take the weakest element class as the effective class of the hybrid: an
   assembly cannot be better assured than the poorest part inside it.
5. Return one verdict in precedence order and report the share of elements
   that reach the declared hybrid class.
"""

__all__ = [
    "PROCUREMENT_CLASSES",
    "ELEMENT_KINDS",
    "CHAIN_COMPLETE",
    "GENERIC_SPECIFICATION_MISSING",
    "ELEMENT_SPECIFICATION_MISSING",
    "DETAIL_SPECIFICATION_NOT_DERIVED",
    "ELEMENT_CLASS_SHORTFALL",
    "class_rank",
    "weaker_class",
    "validate_specification",
    "detail_specification_is_derived",
    "validate_element",
    "validate_elements",
    "element_shortfalls",
    "weakest_element_class",
    "effective_hybrid_class",
    "compliant_element_share",
    "assess_hybrid_procurement",
]

# Ordered best first. Rank 1 is the most demanding procurement class.
PROCUREMENT_CLASSES = ("class-1", "class-2", "class-3")

ELEMENT_KINDS = (
    "die",
    "chip-resistor",
    "chip-capacitor",
    "substrate",
    "interconnect",
    "package",
)

CHAIN_COMPLETE = "specification-chain-complete"
GENERIC_SPECIFICATION_MISSING = "generic-specification-missing"
ELEMENT_SPECIFICATION_MISSING = "element-specification-missing"
DETAIL_SPECIFICATION_NOT_DERIVED = "detail-specification-not-derived"
ELEMENT_CLASS_SHORTFALL = "element-class-shortfall"


def class_rank(name):
    """Return the rank of a procurement class, 1 being the most demanding."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("procurement class must be a non-empty string")
    key = name.strip().lower()
    if key not in PROCUREMENT_CLASSES:
        raise ValueError(
            "unknown procurement class %r; declare one of %s"
            % (name, ", ".join(PROCUREMENT_CLASSES))
        )
    return PROCUREMENT_CLASSES.index(key) + 1


def weaker_class(left, right):
    """Return whichever of two procurement classes is the less demanding."""
    return left if class_rank(left) >= class_rank(right) else right


def validate_specification(spec, label, required=True):
    """Return a normalised specification reference, or None when absent."""
    if spec is None:
        if required:
            raise ValueError("%s is required" % label)
        return None
    if not isinstance(spec, dict):
        raise ValueError("%s must be a mapping" % label)
    identifier = spec.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        return None
    record = {"id": identifier.strip()}
    issue = spec.get("issue")
    record["issue"] = issue.strip() if isinstance(issue, str) and issue.strip() else None
    parent = spec.get("parent_generic_specification")
    record["parent_generic_specification"] = (
        parent.strip() if isinstance(parent, str) and parent.strip() else None
    )
    return record


def detail_specification_is_derived(detail, generic):
    """Return whether a detail specification cites this generic as its parent."""
    if not isinstance(detail, dict) or not isinstance(generic, dict):
        raise ValueError("both specifications must be mappings")
    parent = detail.get("parent_generic_specification")
    identifier = generic.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("the generic specification needs a non-empty id")
    if not isinstance(parent, str) or not parent.strip():
        return False
    return parent.strip() == identifier.strip()


def validate_element(element):
    """Return a normalised constituent element record."""
    if not isinstance(element, dict):
        raise ValueError("each element must be a mapping")
    identifier = element.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("each element needs a non-empty 'id'")
    kind = element.get("kind")
    if not isinstance(kind, str) or kind.strip().lower() not in ELEMENT_KINDS:
        raise ValueError(
            "element %s declares kind %r; use one of %s"
            % (identifier, kind, ", ".join(ELEMENT_KINDS))
        )
    record = {"id": identifier.strip(), "kind": kind.strip().lower()}
    record["procurement_class"] = element.get("procurement_class")
    record["rank"] = class_rank(record["procurement_class"])
    spec = element.get("specification")
    record["specification"] = (
        spec.strip() if isinstance(spec, str) and spec.strip() else None
    )
    return record


def validate_elements(elements):
    """Return the validated list of constituent elements."""
    if not isinstance(elements, (list, tuple)) or not elements:
        raise ValueError("elements must be a non-empty sequence of element records")
    records = []
    seen = set()
    for element in elements:
        record = validate_element(element)
        if record["id"] in seen:
            raise ValueError("duplicate element id %r" % (record["id"],))
        seen.add(record["id"])
        records.append(record)
    return records


def element_shortfalls(records, hybrid_class):
    """Return the elements bought at a class weaker than the hybrid's own."""
    limit = class_rank(hybrid_class)
    return [record for record in records if record["rank"] > limit]


def weakest_element_class(records):
    """Return the least demanding procurement class present among the elements."""
    if not records:
        raise ValueError("cannot take the weakest class of an empty element list")
    worst = max(record["rank"] for record in records)
    return PROCUREMENT_CLASSES[worst - 1]


def effective_hybrid_class(hybrid_class, records):
    """Return the class the assembled hybrid can actually claim."""
    return weaker_class(hybrid_class, weakest_element_class(records))


def compliant_element_share(records, hybrid_class):
    """Return the share of elements reaching the declared hybrid class."""
    if not records:
        raise ValueError("cannot take a share of an empty element list")
    limit = class_rank(hybrid_class)
    reaching = sum(1 for record in records if record["rank"] <= limit)
    return float(reaching) / float(len(records))


def assess_hybrid_procurement(case):
    """Run the clause 4.6.3 specification-chain assessment for a hybrid.

    case keys: hybrid_class, generic_specification, optional
    detail_specification, elements, optional custom_type flag.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("hybrid_class", "elements"):
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)
    hybrid_class = case["hybrid_class"]
    limit = class_rank(hybrid_class)
    records = validate_elements(case["elements"])
    custom = case.get("custom_type", True)
    if not isinstance(custom, bool):
        raise ValueError("custom_type must be a boolean")

    generic = validate_specification(
        case.get("generic_specification"), "generic_specification", required=False
    )
    detail = validate_specification(
        case.get("detail_specification"), "detail_specification", required=False
    )

    findings = []
    unspecified = [record["id"] for record in records if record["specification"] is None]
    shortfalls = element_shortfalls(records, hybrid_class)
    derived = None

    if generic is None:
        findings.append(
            "no generic specification governs this hybrid type; there is nothing "
            "for a detail specification or a purchase order to sit under"
        )
    else:
        if custom and detail is None:
            findings.append(
                "a custom hybrid needs a detail specification under generic %s"
                % generic["id"]
            )
        elif detail is not None:
            derived = detail_specification_is_derived(detail, generic)
            if not derived:
                findings.append(
                    "detail specification %s does not cite generic %s as its parent"
                    % (detail["id"], generic["id"])
                )

    for identifier in unspecified:
        findings.append(
            "element %s carries no specification reference of its own" % identifier
        )
    for record in shortfalls:
        findings.append(
            "element %s was bought at %s, weaker than the %s the hybrid claims"
            % (record["id"], record["procurement_class"], hybrid_class)
        )

    if generic is None:
        verdict = GENERIC_SPECIFICATION_MISSING
    elif unspecified:
        verdict = ELEMENT_SPECIFICATION_MISSING
    elif (custom and detail is None) or derived is False:
        verdict = DETAIL_SPECIFICATION_NOT_DERIVED
    elif shortfalls:
        verdict = ELEMENT_CLASS_SHORTFALL
    else:
        verdict = CHAIN_COMPLETE

    return {
        "verdict": verdict,
        "hybrid_class": hybrid_class,
        "hybrid_class_rank": limit,
        "generic_specification": generic,
        "detail_specification": detail,
        "detail_is_derived": derived,
        "element_count": len(records),
        "elements_without_specification": unspecified,
        "element_shortfalls": [record["id"] for record in shortfalls],
        "weakest_element_class": weakest_element_class(records),
        "effective_hybrid_class": effective_hybrid_class(hybrid_class, records),
        "compliant_element_share": compliant_element_share(records, hybrid_class),
        "chain_complete": verdict == CHAIN_COMPLETE,
        "findings": findings,
    }
