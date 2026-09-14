#!/usr/bin/env python3
"""Dispatch of ordered coverglasses with the agreed documentation set.

Anchor: ECSS-E-ST-20-08C clause 8.10. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Two arms have to close before a coverglass shipment leaves, and grading
only the first of them is the failure this check exists to catch.

    hardware arm        the glass itself: pieces drawn from batches, each
                        batch carrying one coverglass type and a count,
                        each order line asking for a type and a quantity
    documentation arm   the documentation set the order AGREED would
                        travel with the hardware. Agreed is the operative
                        word: the set is named by the order, so what has
                        to accompany a shipment is an order-level fact
                        and not a fixed list

A count that reaches the ordered quantity therefore proves nothing on its
own. The quantity can be made up entirely from batches whose agreed
documents are absent, written to a superseded issue, unsigned, or issued
against some other batch, and a pure counting check passes all four.

A coverglass is ordered by type, which raises a substitution question.
A line may be filled from another type only when the order named that
type as permitted for it; anything else delivers an article the order did
not buy, however well the count reconciles. Exact type is therefore spent
before any permitted alternative, so a scarce type is not consumed by a
line that had its own stock standing by.

Finally a partial dispatch is a decision, not an accident. The order
declares the fraction of a line below which a partial delivery is refused
outright; a line that clears that floor without being complete still
goes, and is still named as partial.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

__all__ = [
    "BATCH_HELD",
    "BATCH_RELEASABLE",
    "DELIVERY_HELD",
    "DELIVERY_RELEASABLE",
    "DOCUMENT_KINDS",
    "DOC_ACCEPTED",
    "DOC_ISSUE_SUPERSEDED",
    "DOC_MISSING",
    "DOC_UNSIGNED",
    "FILL_TOLERANCE",
    "LINE_COMPLETE",
    "LINE_PARTIAL",
    "LINE_REFUSED",
    "allocate_batches_to_lines",
    "assess_batch",
    "assess_batches",
    "document_state_for_batch",
    "evaluate_delivery",
    "normalize_document_kind",
    "normalize_type",
    "validate_document",
    "validate_documents",
    "validate_order",
    "validate_order_line",
]

# The kinds an order may name as its agreed accompanying set. The order
# chooses the subset; the standard does not hand every shipment the same
# paperwork, which is precisely why the set is read from the order.
DOCUMENT_KINDS = (
    "certificate-of-conformity",
    "acceptance-test-report",
    "batch-traceability-record",
    "packing-list",
)

DOC_ACCEPTED = "document-accepted"
DOC_MISSING = "document-missing-for-batch"
DOC_ISSUE_SUPERSEDED = "document-issue-superseded"
DOC_UNSIGNED = "document-unsigned"

BATCH_RELEASABLE = "batch-releasable"
BATCH_HELD = "batch-held"

LINE_COMPLETE = "line-complete"
LINE_PARTIAL = "line-partial-within-floor"
LINE_REFUSED = "line-below-partial-delivery-floor"

DELIVERY_RELEASABLE = "delivery-releasable"
DELIVERY_HELD = "delivery-held"

# A fill fraction is a ratio of two small integers, but the declared floor
# arrives as a decimal literal. Comparing them without a tolerance makes a
# line that exactly meets its floor pass on one platform and fail on
# another, so the comparison absorbs representation error by name and the
# declared floor stays exactly as declared.
FILL_TOLERANCE = 1e-9


def _identifier(value, label):
    """Return a trimmed non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _count(value, label, allow_zero=False):
    """Return an integer count, refusing a bool or a float."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    floor = 0 if allow_zero else 1
    if value < floor:
        raise ValueError("%s must be at least %d, got %d" % (label, floor, value))
    return value


def _flag(value, label):
    """Return a validated boolean."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def normalize_type(value, label="coverglass_type"):
    """Return a trimmed, lowercased coverglass type designation."""
    return _identifier(value, label).lower()


def normalize_document_kind(kind, label="document kind"):
    """Return a recognized document kind, refusing anything else."""
    if not isinstance(kind, str):
        raise ValueError("%s must be a string, got %r" % (label, kind))
    cleaned = kind.strip().lower()
    if cleaned not in DOCUMENT_KINDS:
        raise ValueError(
            "unrecognized %s %r; recognized: %s"
            % (label, kind, ", ".join(DOCUMENT_KINDS))
        )
    return cleaned


def validate_order_line(line, label="order line"):
    """Return one validated order line with its permitted substitutions."""
    if not isinstance(line, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("line_id", "coverglass_type", "ordered_count"):
        if key not in line:
            raise ValueError("%s missing required key '%s'" % (label, key))
    permitted = line.get("permitted_substitute_types", ())
    if isinstance(permitted, str) or not isinstance(permitted, (list, tuple)):
        raise ValueError(
            "%s permitted_substitute_types must be a sequence, got %r"
            % (label, permitted)
        )
    wanted = normalize_type(line["coverglass_type"], "%s coverglass_type" % label)
    subs = []
    for index, entry in enumerate(permitted):
        value = normalize_type(entry, "%s permitted_substitute_types[%d]" % (label, index))
        if value == wanted:
            raise ValueError(
                "%s names its own type %r as a substitution" % (label, wanted)
            )
        if value not in subs:
            subs.append(value)
    return {
        "line_id": _identifier(line["line_id"], "%s line_id" % label),
        "coverglass_type": wanted,
        "ordered_count": _count(line["ordered_count"], "%s ordered_count" % label),
        "permitted_substitute_types": tuple(subs),
    }


def validate_order(order):
    """Return the validated order, its agreed document set and its floor."""
    if not isinstance(order, dict):
        raise ValueError("order must be a mapping")
    for key in ("order_id", "lines", "agreed_document_kinds", "partial_delivery_floor"):
        if key not in order:
            raise ValueError("order missing required key '%s'" % key)
    floor = order["partial_delivery_floor"]
    if isinstance(floor, bool) or not isinstance(floor, (int, float)):
        raise ValueError("partial_delivery_floor must be a number, got %r" % (floor,))
    floor = float(floor)
    if not 0.0 <= floor <= 1.0:
        raise ValueError(
            "partial_delivery_floor must lie between 0 and 1, got %r" % (floor,)
        )
    agreed_raw = order["agreed_document_kinds"]
    if isinstance(agreed_raw, str) or not isinstance(agreed_raw, (list, tuple)):
        raise ValueError("agreed_document_kinds must be a sequence of kinds")
    agreed = []
    for index, kind in enumerate(agreed_raw):
        value = normalize_document_kind(kind, "agreed_document_kinds[%d]" % index)
        if value in agreed:
            raise ValueError("agreed_document_kinds names %s twice" % value)
        agreed.append(value)
    if not agreed:
        raise ValueError("an order must agree at least one accompanying document kind")
    lines_raw = order["lines"]
    if not isinstance(lines_raw, (list, tuple)) or not lines_raw:
        raise ValueError("order must carry at least one line")
    lines = []
    seen = set()
    for index, line in enumerate(lines_raw):
        entry = validate_order_line(line, "order line[%d]" % index)
        if entry["line_id"] in seen:
            raise ValueError("order line %s appears twice" % entry["line_id"])
        seen.add(entry["line_id"])
        lines.append(entry)
    return {
        "order_id": _identifier(order["order_id"], "order_id"),
        "lines": tuple(lines),
        "agreed_document_kinds": tuple(agreed),
        "partial_delivery_floor": floor,
    }


def validate_document(document, label="document"):
    """Return one validated accompanying document record."""
    if not isinstance(document, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("document_id", "kind", "issue", "governing_issue", "signed",
                "covers_batch_ids"):
        if key not in document:
            raise ValueError("%s missing required key '%s'" % (label, key))
    covers_raw = document["covers_batch_ids"]
    if isinstance(covers_raw, str) or not isinstance(covers_raw, (list, tuple)):
        raise ValueError("%s covers_batch_ids must be a sequence" % label)
    covers = []
    for index, batch_id in enumerate(covers_raw):
        value = _identifier(batch_id, "%s covers_batch_ids[%d]" % (label, index))
        if value not in covers:
            covers.append(value)
    return {
        "document_id": _identifier(document["document_id"], "%s document_id" % label),
        "kind": normalize_document_kind(document["kind"], "%s kind" % label),
        "issue": _count(document["issue"], "%s issue" % label),
        "governing_issue": _count(
            document["governing_issue"], "%s governing_issue" % label
        ),
        "signed": _flag(document["signed"], "%s signed" % label),
        "covers_batch_ids": tuple(covers),
    }


def validate_documents(documents):
    """Return every validated document, refusing a repeated identifier."""
    if not isinstance(documents, (list, tuple)):
        raise ValueError("documents must be a sequence of document records")
    out = []
    seen = set()
    for index, document in enumerate(documents):
        entry = validate_document(document, "documents[%d]" % index)
        if entry["document_id"] in seen:
            raise ValueError("document %s appears twice" % entry["document_id"])
        seen.add(entry["document_id"])
        out.append(entry)
    return tuple(out)


def document_state_for_batch(kind, batch_id, documents):
    """Say how one agreed document kind stands for one shipped batch.

    A document is read for what it covers and how it stands, never for
    merely existing. A record of the right kind that names some other
    batch is not this batch's record, and a record written to an issue the
    governing one has replaced is a record of an article built to a rule
    set nobody is working to any more.
    """
    kind = normalize_document_kind(kind)
    batch_id = _identifier(batch_id, "batch_id")
    candidates = [
        d for d in documents
        if d["kind"] == kind and batch_id in d["covers_batch_ids"]
    ]
    if not candidates:
        return {
            "kind": kind,
            "document_id": None,
            "state": DOC_MISSING,
            "reason": "no %s covers batch %s" % (kind, batch_id),
        }
    # Prefer the record that stands, so a superseded duplicate alongside a
    # current one does not hold a batch the current record already clears.
    ranked = sorted(
        candidates,
        key=lambda d: (
            0 if (d["issue"] >= d["governing_issue"] and d["signed"]) else 1,
            0 if d["issue"] >= d["governing_issue"] else 1,
            0 if d["signed"] else 1,
            d["document_id"],
        ),
    )
    best = ranked[0]
    if best["issue"] < best["governing_issue"]:
        return {
            "kind": kind,
            "document_id": best["document_id"],
            "state": DOC_ISSUE_SUPERSEDED,
            "reason": "%s %s is at issue %d, superseded by issue %d"
                      % (kind, best["document_id"], best["issue"],
                         best["governing_issue"]),
        }
    if not best["signed"]:
        return {
            "kind": kind,
            "document_id": best["document_id"],
            "state": DOC_UNSIGNED,
            "reason": "%s %s is unsigned" % (kind, best["document_id"]),
        }
    return {
        "kind": kind,
        "document_id": best["document_id"],
        "state": DOC_ACCEPTED,
        "reason": None,
    }


def assess_batch(batch, documents, agreed_kinds, label="batch"):
    """Disposition one shipped batch against the agreed document set."""
    if not isinstance(batch, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("batch_id", "coverglass_type", "piece_count"):
        if key not in batch:
            raise ValueError("%s missing required key '%s'" % (label, key))
    batch_id = _identifier(batch["batch_id"], "%s batch_id" % label)
    coverglass_type = normalize_type(
        batch["coverglass_type"], "%s coverglass_type" % label
    )
    piece_count = _count(batch["piece_count"], "%s piece_count" % label)
    states = tuple(
        document_state_for_batch(kind, batch_id, documents) for kind in agreed_kinds
    )
    reasons = tuple(
        "batch %s: %s" % (batch_id, s["reason"])
        for s in states if s["state"] != DOC_ACCEPTED
    )
    accepted = sum(1 for s in states if s["state"] == DOC_ACCEPTED)
    return {
        "batch_id": batch_id,
        "coverglass_type": coverglass_type,
        "piece_count": piece_count,
        "document_states": states,
        "documents_accepted": accepted,
        "documents_agreed": len(states),
        "documentation_fraction": accepted / float(len(states)),
        "disposition": BATCH_RELEASABLE if not reasons else BATCH_HELD,
        "releasable": not reasons,
        "reasons": reasons,
    }


def assess_batches(batches, documents, agreed_kinds):
    """Disposition every shipped batch, refusing a repeated batch id."""
    if not isinstance(batches, (list, tuple)) or not batches:
        raise ValueError("batches must be a non-empty sequence of shipped batches")
    kinds = tuple(normalize_document_kind(k) for k in agreed_kinds)
    if not kinds:
        raise ValueError("at least one agreed document kind is required")
    out = []
    seen = set()
    for index, batch in enumerate(batches):
        entry = assess_batch(batch, documents, kinds, "batches[%d]" % index)
        if entry["batch_id"] in seen:
            raise ValueError("batch %s is offered twice" % entry["batch_id"])
        seen.add(entry["batch_id"])
        out.append(entry)
    return tuple(out)


def allocate_batches_to_lines(assessed, order):
    """Fill each order line from the releasable batches, exact type first.

    Exact type is spent before any permitted alternative so that a scarce
    type is not consumed by a line that had its own stock standing by. A
    type the line never named is never drawn on: that is a different
    article, not a substitution.
    """
    validated = validate_order(order)
    remaining = {b["batch_id"]: b["piece_count"] for b in assessed if b["releasable"]}
    by_id = {b["batch_id"]: b for b in assessed}
    lines = []
    for line in validated["lines"]:
        wanted = line["ordered_count"]
        shipped = 0
        drawn = []
        substituted = []
        for stage, types in (
            ("exact", (line["coverglass_type"],)),
            ("substitute", line["permitted_substitute_types"]),
        ):
            for batch_id in sorted(remaining):
                if shipped >= wanted:
                    break
                if remaining[batch_id] <= 0:
                    continue
                batch = by_id[batch_id]
                if batch["coverglass_type"] not in types:
                    continue
                take = min(remaining[batch_id], wanted - shipped)
                remaining[batch_id] -= take
                shipped += take
                drawn.append({"batch_id": batch_id, "piece_count": take})
                if stage == "substitute":
                    substituted.append(
                        {"batch_id": batch_id, "piece_count": take,
                         "coverglass_type": batch["coverglass_type"]}
                    )
        fill = shipped / float(wanted)
        if shipped >= wanted:
            state = LINE_COMPLETE
        elif fill + FILL_TOLERANCE >= validated["partial_delivery_floor"]:
            state = LINE_PARTIAL
        else:
            state = LINE_REFUSED
        lines.append(
            {
                "line_id": line["line_id"],
                "coverglass_type": line["coverglass_type"],
                "ordered_count": wanted,
                "shipped_count": shipped,
                "short_count": max(0, wanted - shipped),
                "fill_fraction": fill,
                "drawn_from": tuple(drawn),
                "substituted_from": tuple(substituted),
                "state": state,
                "accepted": state != LINE_REFUSED,
            }
        )
    surplus = tuple(
        {"batch_id": batch_id, "piece_count": left}
        for batch_id, left in sorted(remaining.items())
        if left > 0
    )
    return {"lines": tuple(lines), "surplus": surplus}


def evaluate_delivery(spec):
    """Run the clause 8.10 dispatch check over one offered shipment.

    spec keys: shipment_id, order, documents, batches.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("shipment_id", "order", "documents", "batches"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    shipment_id = _identifier(spec["shipment_id"], "shipment_id")
    order = validate_order(spec["order"])
    documents = validate_documents(spec["documents"])
    assessed = assess_batches(spec["batches"], documents, order["agreed_document_kinds"])
    allocation = allocate_batches_to_lines(assessed, order)

    findings = []
    for batch in assessed:
        findings.extend(batch["reasons"])
    for line in allocation["lines"]:
        if line["state"] == LINE_REFUSED:
            findings.append(
                "order line %s ships %d of %d ordered coverglasses, below the "
                "declared partial-delivery floor"
                % (line["line_id"], line["shipped_count"], line["ordered_count"])
            )
    for entry in allocation["surplus"]:
        findings.append(
            "shipment %s offers %d coverglass(es) from batch %s that no line of "
            "order %s asks for"
            % (shipment_id, entry["piece_count"], entry["batch_id"], order["order_id"])
        )

    ordered_total = sum(l["ordered_count"] for l in allocation["lines"])
    shipped_total = sum(l["shipped_count"] for l in allocation["lines"])
    held = tuple(b["batch_id"] for b in assessed if not b["releasable"])
    return {
        "shipment_id": shipment_id,
        "order_id": order["order_id"],
        "agreed_document_kinds": order["agreed_document_kinds"],
        "batches": assessed,
        "lines": allocation["lines"],
        "surplus": allocation["surplus"],
        "held_batch_ids": held,
        "substituted_line_ids": tuple(
            l["line_id"] for l in allocation["lines"] if l["substituted_from"]
        ),
        "ordered_total": ordered_total,
        "shipped_total": shipped_total,
        "shipment_fill_fraction": shipped_total / float(ordered_total),
        "partial": shipped_total < ordered_total,
        "findings": tuple(findings),
        "verdict": DELIVERY_RELEASABLE if not findings else DELIVERY_HELD,
        "accepted": not findings,
    }
