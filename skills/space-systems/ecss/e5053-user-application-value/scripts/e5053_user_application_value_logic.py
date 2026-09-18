#!/usr/bin/env python3
"""User application value field, ECSS-E-ST-50-53C clause 5.1.6.

Paraphrased requirement, no verbatim standard text. The clause obliges the
CCSDS packet transfer protocol to carry a value chosen by the user
application at the sending end and to hand that same value to the user
application at the receiving end. The protocol gives the value no meaning of
its own; the meaning belongs entirely to the two applications. This module
turns that into a deterministic assessment:

  a value offered by the sending application -> does it fit the field at all
  sent value vs delivered value              -> was the carriage transparent
  delivered value vs the receiving
  application's own assignment               -> does the receiver know what
                                                it has been handed
  a run of transfers                         -> how often carriage altered it

The separation this module keeps is the point of the clause: a value the
transport changed is a transport fault, while a value the transport carried
faithfully that the receiving application does not recognise is an
application agreement fault. Merging them sends every investigation to the
wrong team. stdlib only, offline, deterministic, integer-exact.
"""

from __future__ import annotations

# The field is one octet wide.
VALUE_MIN = 0
VALUE_MAX = 255

TRANSPARENT = "transparent"
ALTERED = "altered"
CARRIAGE_CATEGORIES = (TRANSPARENT, ALTERED)

REGISTERED = "registered"
UNREGISTERED = "unregistered"
MEANING_CATEGORIES = (REGISTERED, UNREGISTERED)


def _integer(value, name):
    """Return value as an int, refusing bools, floats and anything else."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer octet, got %r" % (name, value))
    return int(value)


def validate_user_application_value(value, name="user_application_value"):
    """Validate a value against the width of the field that carries it."""
    octet = _integer(value, name)
    if octet < VALUE_MIN or octet > VALUE_MAX:
        raise ValueError(
            "%s must lie in %d..%d, got %d" % (name, VALUE_MIN, VALUE_MAX, octet)
        )
    return octet


def build_value_registry(assignments=None):
    """Validate an application's own assignment of values to meanings.

    The registry belongs to the pair of applications, never to the transfer
    protocol. An empty registry is legal and means the receiving application
    has declared no meanings at all.
    """
    if assignments is None:
        return {}
    if not isinstance(assignments, dict):
        raise ValueError(
            "assignments must be a mapping of value to meaning, got %r"
            % (assignments,)
        )
    registry = {}
    seen_names = set()
    for key, meaning in assignments.items():
        octet = validate_user_application_value(key, "assignment key")
        if not isinstance(meaning, str) or not meaning.strip():
            raise ValueError(
                "assignment for value %d must name a non-empty meaning" % octet
            )
        name = meaning.strip()
        if name in seen_names:
            raise ValueError(
                "meaning %r is assigned to more than one value" % name
            )
        seen_names.add(name)
        registry[octet] = name
    return registry


def is_registered(value, registry=None):
    """True when the receiving application has declared a meaning."""
    octet = validate_user_application_value(value)
    table = build_value_registry(registry) if not isinstance(registry, dict) else registry
    return octet in table


def resolve_meaning(value, registry=None):
    """The meaning the receiving application gives the value, or None."""
    octet = validate_user_application_value(value)
    table = build_value_registry(registry) if not isinstance(registry, dict) else registry
    return table.get(octet)


def categorize_meaning(value, registry=None):
    """Group a delivered value by whether the receiver knows it."""
    return REGISTERED if is_registered(value, registry) else UNREGISTERED


def categorize_carriage(sent_value, delivered_value):
    """Group one transfer by whether carriage was transparent."""
    sent = validate_user_application_value(sent_value, "sent_value")
    delivered = validate_user_application_value(delivered_value, "delivered_value")
    return TRANSPARENT if sent == delivered else ALTERED


def carriage_report(sent_value, delivered_value):
    """Describe the carriage of one value end to end."""
    sent = validate_user_application_value(sent_value, "sent_value")
    delivered = validate_user_application_value(delivered_value, "delivered_value")
    category = categorize_carriage(sent, delivered)
    return {
        "sent": sent,
        "delivered": delivered,
        "category": category,
        "transparent": category == TRANSPARENT,
        "changed_bits": bin(sent ^ delivered).count("1"),
    }


def summarize_transfers(pairs):
    """Transparency counts, first alteration and altered fraction over a run."""
    if not isinstance(pairs, (list, tuple)):
        raise ValueError("pairs must be a list of (sent, delivered) transfers")
    if len(pairs) == 0:
        raise ValueError("pairs must hold at least one transfer")
    altered = 0
    first_altered = None
    changed_bits = 0
    for index, pair in enumerate(pairs):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError(
                "pairs[%d] must be a (sent, delivered) pair, got %r" % (index, pair)
            )
        report = carriage_report(pair[0], pair[1])
        if not report["transparent"]:
            altered += 1
            changed_bits += report["changed_bits"]
            if first_altered is None:
                first_altered = index
    total = len(pairs)
    return {
        "total": total,
        "altered": altered,
        "transparent": total - altered,
        "first_altered_index": first_altered,
        "altered_fraction": altered / float(total),
        "changed_bits": changed_bits,
    }


def assess_user_application_value(
    sent_value, delivered_value, registry=None, require_registered=False
):
    """Full clause 5.1.6 assessment of one user application value."""
    table = build_value_registry(registry) if not isinstance(registry, dict) else registry
    carriage = carriage_report(sent_value, delivered_value)
    meaning_category = categorize_meaning(carriage["delivered"], table)
    meaning = resolve_meaning(carriage["delivered"], table)

    findings = []
    limitations = []

    if not carriage["transparent"]:
        findings.append(
            "carriage altered the user application value: %d was sent, %d was "
            "delivered, %d bit(s) differ"
            % (carriage["sent"], carriage["delivered"], carriage["changed_bits"])
        )
    if meaning_category == UNREGISTERED:
        message = (
            "delivered value %d has no meaning in the receiving application's "
            "assignment" % carriage["delivered"]
        )
        if require_registered:
            findings.append(message)
        else:
            limitations.append(message)
    limitations.append(
        "the transfer protocol assigns this field no meaning; interpretation "
        "is an agreement between the two applications"
    )

    return {
        "sent": carriage["sent"],
        "delivered": carriage["delivered"],
        "carriage": carriage["category"],
        "changed_bits": carriage["changed_bits"],
        "meaning_category": meaning_category,
        "meaning": meaning,
        "findings": findings,
        "limitations": limitations,
        "verdict": "value-delivered" if not findings else "value-suspect",
    }
