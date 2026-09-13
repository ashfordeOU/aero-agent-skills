#!/usr/bin/env python3
"""Delivery of ordered photovoltaic assembly hardware with its documentation.

Anchor: ECSS-E-ST-20-08C clause 5.8. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Ordered photovoltaic assembly (PVA) hardware does not ship on its own. It
ships together with the documentation package the preceding clause already
demanded, and a delivery is only releasable when both halves line up:

    quantity        the serials actually shippable against the quantity the
                    order asked for, with a partial shipment allowed only on
                    a declared project policy
    documentation   every required document present, at issued status, and
                    citing the lot that is physically leaving the building
    hardware        each serial dispositioned from its conformance state and
                    from the build standard it was actually built to

The three arms are measured separately and only then folded into one lot
verdict, because a full crate with a draft certificate and a complete
document set covering the wrong lot are different failures with different
recoveries.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REQUIRED_DELIVERY_DOCUMENTS = (
    "as-built-configuration-record",
    "certificate-of-conformity",
    "acceptance-test-report",
    "non-conformance-record",
    "parts-and-materials-list",
    "handling-and-storage-instruction",
)

DOCUMENT_STATUSES = ("issued", "draft", "withdrawn")

CONFORMANCE_STATES = (
    "conforming",
    "waived-non-conformance",
    "open-non-conformance",
)

DOCUMENT_RELEASED = "document-released"
DOCUMENT_NOT_ISSUED = "document-not-issued"
DOCUMENT_LOT_MISMATCH = "document-lot-mismatch"

ITEM_SHIPPABLE = "item-shippable"
ITEM_SHIPPABLE_ON_WAIVER = "item-shippable-on-waiver"
ITEM_HELD = "item-held"

DELIVERY_RELEASABLE = "delivery-releasable"
DELIVERY_HELD = "delivery-held"

DEFAULT_DELIVERY_POLICY = {
    "allow_partial_delivery": True,
    "min_delivered_fraction": 0.90,
    "require_full_documentation": True,
    "conformance_disposition": {
        "conforming": ITEM_SHIPPABLE,
        "waived-non-conformance": ITEM_SHIPPABLE_ON_WAIVER,
        "open-non-conformance": ITEM_HELD,
    },
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A delivered share is a ratio of two counts and the policy limit is a
    round percentage, so a shipment meant to sit exactly on the limit can
    land a few units in the last place below it. The limit is never
    lowered; only the comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _is_declared(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return True


def _clean_text(name, value):
    if not _is_declared(value) or not isinstance(value, str):
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def validate_delivery_policy(policy):
    """Check a delivery policy declares a usable release rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    if not isinstance(policy.get("allow_partial_delivery"), bool):
        raise ValueError("policy allow_partial_delivery must be a boolean")
    if not isinstance(policy.get("require_full_documentation"), bool):
        raise ValueError("policy require_full_documentation must be a boolean")
    fraction = _require_fraction(
        "min_delivered_fraction", policy.get("min_delivered_fraction")
    )
    if fraction <= 0.0:
        raise ValueError(
            "min_delivered_fraction must be greater than zero, got %r" % (fraction,)
        )
    table = policy.get("conformance_disposition")
    if not isinstance(table, dict):
        raise ValueError("policy conformance_disposition must be a mapping")
    missing = set(CONFORMANCE_STATES) - set(table)
    if missing:
        raise ValueError(
            "policy conformance_disposition is missing states: %s"
            % ", ".join(sorted(missing))
        )
    for state in CONFORMANCE_STATES:
        _require_choice(
            "policy conformance_disposition[%s]" % state,
            table[state],
            (ITEM_SHIPPABLE, ITEM_SHIPPABLE_ON_WAIVER, ITEM_HELD),
        )
    return policy


def required_delivery_documents():
    """Documents that travel with the ordered hardware."""
    return REQUIRED_DELIVERY_DOCUMENTS


def assess_delivery_document(document, lot_reference):
    """Verdict for one document in the delivery package."""
    if not isinstance(document, dict):
        raise ValueError("document must be a mapping, got %r" % (document,))
    lot = _clean_text("lot_reference", lot_reference)
    name = _require_choice(
        "document name", document.get("name"), REQUIRED_DELIVERY_DOCUMENTS
    )
    status = _require_choice(
        "document status", document.get("status"), DOCUMENT_STATUSES
    )
    cited = _clean_text("document lot_reference", document.get("lot_reference"))
    findings = []
    if status != "issued":
        verdict = DOCUMENT_NOT_ISSUED
        findings.append("%s is at %s status rather than issued" % (name, status))
    elif cited != lot:
        verdict = DOCUMENT_LOT_MISMATCH
        findings.append("%s cites lot %s while lot %s is shipping" % (name, cited, lot))
    else:
        verdict = DOCUMENT_RELEASED
    return {
        "name": name,
        "status": status,
        "cited_lot": cited,
        "verdict": verdict,
        "findings": findings,
    }


def documentation_status(package, lot_reference, policy=DEFAULT_DELIVERY_POLICY):
    """How much of the required documentation package is actually released."""
    validate_delivery_policy(policy)
    if not isinstance(package, (list, tuple)):
        raise ValueError("documentation package must be a sequence, got %r" % (package,))
    records = [assess_delivery_document(entry, lot_reference) for entry in package]
    seen = [record["name"] for record in records]
    duplicates = sorted({name for name in seen if seen.count(name) > 1})
    if duplicates:
        raise ValueError(
            "documentation package repeats a document: %s" % ", ".join(duplicates)
        )
    released = [
        record["name"] for record in records if record["verdict"] == DOCUMENT_RELEASED
    ]
    absent = sorted(set(REQUIRED_DELIVERY_DOCUMENTS) - set(seen))
    findings = []
    for record in records:
        findings.extend(record["findings"])
    for name in absent:
        findings.append("%s is absent from the delivery package" % name)
    fraction = len(released) / float(len(REQUIRED_DELIVERY_DOCUMENTS))
    complete = not absent and len(released) == len(REQUIRED_DELIVERY_DOCUMENTS)
    return {
        "document_records": records,
        "absent_documents": absent,
        "released_documents": sorted(released),
        "released_fraction": fraction,
        "complete": complete,
        "accepted": complete or not policy["require_full_documentation"],
        "findings": findings,
    }


def assess_delivery_item(item, build_standard, policy=DEFAULT_DELIVERY_POLICY):
    """Disposition one serialised item offered for shipment."""
    validate_delivery_policy(policy)
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping, got %r" % (item,))
    lot_standard = _clean_text("build_standard", build_standard)
    serial = _clean_text("item serial", item.get("serial"))
    state = _require_choice(
        "item conformance", item.get("conformance"), CONFORMANCE_STATES
    )
    item_standard = _clean_text("item build_standard", item.get("build_standard"))
    findings = []
    verdict = policy["conformance_disposition"][state]
    if verdict != ITEM_SHIPPABLE:
        findings.append(
            "serial %s carries a %s and is dispositioned %s" % (serial, state, verdict)
        )
    if item_standard != lot_standard:
        verdict = ITEM_HELD
        findings.append(
            "serial %s was built to %s while the lot ships to %s"
            % (serial, item_standard, lot_standard)
        )
    return {
        "serial": serial,
        "conformance": state,
        "build_standard": item_standard,
        "verdict": verdict,
        "findings": findings,
    }


def reconcile_delivery_quantity(
    ordered_quantity, shippable_count, policy=DEFAULT_DELIVERY_POLICY
):
    """Hold the shippable serials against the quantity that was ordered."""
    validate_delivery_policy(policy)
    ordered = _require_count("ordered_quantity", ordered_quantity)
    if ordered == 0:
        raise ValueError("ordered_quantity must be greater than zero")
    shippable = _require_count("shippable_count", shippable_count)
    fraction = shippable / float(ordered)
    complete = _at_least(fraction, 1.0)
    over_delivery = shippable > ordered
    required = float(policy["min_delivered_fraction"])
    findings = []
    if over_delivery:
        findings.append(
            "%d serials are offered against an order for %d" % (shippable, ordered)
        )
    if complete:
        acceptable = True
    elif not policy["allow_partial_delivery"]:
        acceptable = False
        findings.append(
            "%d of %d serials are shippable and partial delivery is not allowed"
            % (shippable, ordered)
        )
    else:
        acceptable = _at_least(fraction, required)
        if not acceptable:
            findings.append(
                "delivered share %.4f falls below the accepted partial share %.4f"
                % (fraction, required)
            )
    return {
        "ordered_quantity": ordered,
        "shippable_count": shippable,
        "delivered_fraction": fraction,
        "required_fraction": required,
        "complete": complete,
        "over_delivery": over_delivery,
        "acceptable": acceptable,
        "findings": findings,
    }


def assess_delivery(case, policy=DEFAULT_DELIVERY_POLICY):
    """Full clause 5.8 sweep over one PVA delivery lot and its package."""
    validate_delivery_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    lot = _clean_text("case lot_reference", case.get("lot_reference"))
    standard = _clean_text("case build_standard", case.get("build_standard"))
    items = case.get("items")
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("case items must be a non-empty sequence of mappings")
    records = [assess_delivery_item(item, standard, policy) for item in items]
    serials = [record["serial"] for record in records]
    repeated = sorted({s for s in serials if serials.count(s) > 1})
    if repeated:
        raise ValueError("case repeats a serial: %s" % ", ".join(repeated))
    documents = documentation_status(case.get("documentation"), lot, policy)
    shippable = [
        record
        for record in records
        if record["verdict"] in (ITEM_SHIPPABLE, ITEM_SHIPPABLE_ON_WAIVER)
    ]
    quantity = reconcile_delivery_quantity(
        case.get("ordered_quantity"), len(shippable), policy
    )
    grouped = {}
    for record in records:
        grouped.setdefault(record["verdict"], []).append(record["serial"])
    findings = list(quantity["findings"]) + list(documents["findings"])
    for record in records:
        findings.extend(record["findings"])
    held = [record["serial"] for record in records if record["verdict"] == ITEM_HELD]
    releasable = quantity["acceptable"] and documents["accepted"]
    return {
        "verdict": DELIVERY_RELEASABLE if releasable else DELIVERY_HELD,
        "lot_reference": lot,
        "build_standard": standard,
        "item_records": records,
        "grouped_by_verdict": grouped,
        "documentation": documents,
        "quantity": quantity,
        "held_serials": held,
        "shippable_count": len(shippable),
        "findings": findings,
    }
