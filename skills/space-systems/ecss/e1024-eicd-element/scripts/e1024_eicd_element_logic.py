#!/usr/bin/env python3
"""ECSS-E-ST-10-24C §5.8.3 EICD at space segment element level
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system engineering standard's §5.8.3 requires an External Interface
Control Document (EICD) for every boundary between space segment elements
and for every boundary between a space segment element and the launch
vehicle. Each EICD record carries a unique identifier, both parties of
the interface named, a set of characteristics grouped by physical medium
family (mechanical, electrical, thermal, data, RF), applicable requirement
references, and a verification provision entry for every declared
characteristic. This module implements interface-type categorization,
EICD field-completeness checking, physical-medium family coverage
verification, and characteristic-to-verification linkage checking; it
does not define the requirement content or verification acceptance
criteria themselves.
"""

VALID_INTERFACE_TYPES = frozenset({"element_to_element", "element_to_launcher"})

CHARACTERISTIC_FAMILIES = frozenset({"mechanical", "electrical", "thermal", "data", "rf"})

REQUIRED_EICD_FIELDS = (
    "interface_id",
    "interface_type",
    "provider_element_id",
    "consumer_element_id",
    "characteristics",
    "requirement_refs",
    "verification_provisions",
)


def categorize_interface(interface_type):
    """Category for a space segment interface type: "element_to_element"
    when the boundary is between two space segment elements, or
    "element_to_launcher" when the boundary is between a space segment
    element and the launch vehicle. Raises ValueError for any type
    outside these two groups."""
    if interface_type in VALID_INTERFACE_TYPES:
        return interface_type
    raise ValueError(
        "unrecognized interface type %r under E-ST-10-24C §5.8.3; "
        "expected one of %s" % (interface_type, sorted(VALID_INTERFACE_TYPES))
    )


def check_eicd_completeness(eicd):
    """List of required field names that are missing or empty in the EICD
    dict. An empty list means all required fields are present and
    non-empty. Does not mutate eicd."""
    missing = []
    for field in REQUIRED_EICD_FIELDS:
        val = eicd.get(field)
        if val is None or val == "" or val == [] or val == {}:
            missing.append(field)
    return missing


def check_characteristic_families(characteristics, required_families):
    """Set of family names from required_families not covered by any
    entry in characteristics. Each characteristic dict must carry a
    "family" key. An empty set means all required families are present.
    Does not mutate characteristics or required_families."""
    covered = set()
    for char in characteristics:
        fam = char.get("family")
        if fam in required_families:
            covered.add(fam)
    return set(required_families) - covered


def check_verification_linkage(characteristics, verification_provisions):
    """List of characteristic IDs that carry no linked verification
    provision. Each characteristic dict must have a "char_id" key; each
    verification provision dict must have a "char_id" key naming the
    characteristic it addresses. A characteristic with no matching
    provision is a traceability gap. Does not mutate its arguments."""
    covered = set()
    for vp in verification_provisions:
        char_id = vp.get("char_id")
        if char_id is not None:
            covered.add(char_id)
    unlinked = []
    for char in characteristics:
        char_id = char.get("char_id")
        if char_id is not None and char_id not in covered:
            unlinked.append(char_id)
    return unlinked


def eicd_element_review(eicd):
    """Full §5.8.3 EICD element-level review for one EICD record.

    eicd: dict with keys as listed in REQUIRED_EICD_FIELDS, plus an
    optional "required_families" iterable restricting which physical
    medium families must be covered (defaults to all
    CHARACTERISTIC_FAMILIES when absent). Each "characteristics" entry
    is a dict with "char_id" (str) and "family" (str) keys. Each
    "verification_provisions" entry is a dict with a "char_id" key
    referencing the characteristic it verifies.

    Returns a dict:
      "missing_fields"          — list of required field names absent or empty
      "uncategorized_type"      — True if interface_type is not recognized
      "uncovered_families"      — sorted list of required families with no entry
      "unlinked_characteristics"— list of char_id values with no provision

    Does not mutate eicd."""
    result = {
        "missing_fields": [],
        "uncategorized_type": False,
        "uncovered_families": [],
        "unlinked_characteristics": [],
    }

    result["missing_fields"] = check_eicd_completeness(eicd)

    interface_type = eicd.get("interface_type")
    try:
        categorize_interface(interface_type)
    except (ValueError, TypeError):
        result["uncategorized_type"] = True

    characteristics = eicd.get("characteristics") or []
    required_families = eicd.get("required_families") or CHARACTERISTIC_FAMILIES
    uncovered = check_characteristic_families(characteristics, required_families)
    result["uncovered_families"] = sorted(uncovered)

    verification_provisions = eicd.get("verification_provisions") or []
    result["unlinked_characteristics"] = check_verification_linkage(
        characteristics, verification_provisions
    )

    return result


def is_eicd_compliant(review):
    """True when all findings in an eicd_element_review result are
    empty — the EICD satisfies §5.8.3 for this assessment."""
    return (
        not review["missing_fields"]
        and not review["uncategorized_type"]
        and not review["uncovered_families"]
        and not review["unlinked_characteristics"]
    )
