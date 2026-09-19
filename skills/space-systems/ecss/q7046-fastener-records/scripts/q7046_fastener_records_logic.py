#!/usr/bin/env python3
"""Records for procured threaded fasteners: certificates and traceability.

Anchor: ECSS-Q-ST-70-46 records clause on threaded fasteners. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

Acceptance of a fastener lot rests on a paper trail, and the trail has
to do two things.

It has to be complete for the criticality bought. A minor fastener owes
a conformity certificate and a dimensional record; a major one owes the
material and mechanical test results behind them; a critical one owes
the heat-treatment record and the embrittlement relief test as well,
because those are the properties nothing downstream can re-measure on a
finished part.

It has to resolve. The delivered lot is declared out of a plating lot,
which came out of a manufacturing lot, which came out of a bar lot,
which came out of a heat. Walking that declaration upwards must reach
exactly one heat: a walk that stops at a node whose parent is not in the
records is a broken chain, a walk that returns to a node it has already
visited is a corrupted record rather than a deep one, and a walk that
reaches two heats means two heats were mixed into one delivery and the
mechanical results of neither one cover it.

Records are also kept for a period after delivery, and that period runs
from delivery rather than from manufacture, because delivery is the date
the receiving organisation can actually evidence.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime

CRITICALITIES = ("critical", "major", "minor")

RECORD_CONFORMITY_CERTIFICATE = "certificate-of-conformity"
RECORD_DIMENSIONAL = "dimensional-inspection-record"
RECORD_MATERIAL_CERTIFICATE = "material-certificate-with-heat-number"
RECORD_MECHANICAL_TEST = "mechanical-test-results"
RECORD_HEAT_TREATMENT = "heat-treatment-record"
RECORD_EMBRITTLEMENT_RELIEF = "embrittlement-relief-test-record"
RECORD_COATING = "coating-process-record"
RECORD_LOT_IDENTITY = "lot-identity-and-marking-record"

RECORD_TYPES = (
    RECORD_CONFORMITY_CERTIFICATE,
    RECORD_DIMENSIONAL,
    RECORD_MATERIAL_CERTIFICATE,
    RECORD_MECHANICAL_TEST,
    RECORD_HEAT_TREATMENT,
    RECORD_EMBRITTLEMENT_RELIEF,
    RECORD_COATING,
    RECORD_LOT_IDENTITY,
)

_REQUIRED_RECORDS = {
    "minor": (
        RECORD_CONFORMITY_CERTIFICATE,
        RECORD_DIMENSIONAL,
        RECORD_LOT_IDENTITY,
    ),
    "major": (
        RECORD_CONFORMITY_CERTIFICATE,
        RECORD_DIMENSIONAL,
        RECORD_LOT_IDENTITY,
        RECORD_MATERIAL_CERTIFICATE,
        RECORD_MECHANICAL_TEST,
    ),
    "critical": (
        RECORD_CONFORMITY_CERTIFICATE,
        RECORD_DIMENSIONAL,
        RECORD_LOT_IDENTITY,
        RECORD_MATERIAL_CERTIFICATE,
        RECORD_MECHANICAL_TEST,
        RECORD_HEAT_TREATMENT,
        RECORD_EMBRITTLEMENT_RELIEF,
        RECORD_COATING,
    ),
}

# Whole years the records are kept after delivery.
_RETENTION_YEARS = {"critical": 20, "major": 10, "minor": 5}

NODE_HEAT = "heat"
NODE_BAR_LOT = "bar-lot"
NODE_MANUFACTURING_LOT = "manufacturing-lot"
NODE_COATING_LOT = "coating-lot"
NODE_DELIVERY_LOT = "delivery-lot"

NODE_KINDS = (
    NODE_HEAT,
    NODE_BAR_LOT,
    NODE_MANUFACTURING_LOT,
    NODE_COATING_LOT,
    NODE_DELIVERY_LOT,
)

CHAIN_RESOLVED = "resolved-to-one-heat"
CHAIN_BROKEN = "broken-chain"
CHAIN_CIRCULAR = "circular-record"
CHAIN_MIXED = "mixed-heats"

VERDICT_COMPLETE = "records-complete"
VERDICT_INCOMPLETE = "records-incomplete"


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_date(name, value):
    if not isinstance(value, datetime.date) or isinstance(value, datetime.datetime):
        raise ValueError("%s must be a datetime.date, got %r" % (name, value))
    return value


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def required_records(criticality):
    """Records the lot owes before acceptance may be signed."""
    _require_choice("criticality", criticality, CRITICALITIES)
    return list(_REQUIRED_RECORDS[criticality])


def missing_records(criticality, records_present):
    """Required records that are not on the file, in the required order."""
    required = required_records(criticality)
    if not isinstance(records_present, (list, tuple, set)):
        raise ValueError("records_present must be a sequence of record names")
    present = set()
    for name in records_present:
        present.add(_require_choice("record name", name, RECORD_TYPES))
    return [name for name in required if name not in present]


def retention_deadline(delivery_date, criticality):
    """Date the records may be destroyed, counted from delivery."""
    delivered = _require_date("delivery_date", delivery_date)
    _require_choice("criticality", criticality, CRITICALITIES)
    years = _RETENTION_YEARS[criticality]
    day = delivered.day
    while True:
        try:
            return datetime.date(delivered.year + years, delivered.month, day)
        except ValueError:
            day -= 1


def _normalise_chain(chain):
    if not isinstance(chain, (list, tuple)):
        raise ValueError("chain must be a sequence of node mappings")
    nodes = {}
    for entry in chain:
        if not isinstance(entry, dict):
            raise ValueError("each chain node must be a mapping, got %r" % (entry,))
        node_id = _require_identifier("node id", entry.get("id"))
        kind = _require_choice("node kind", entry.get("kind"), NODE_KINDS)
        parents = entry.get("parents", [])
        if isinstance(parents, str):
            raise ValueError(
                "node %s declares its parents as a string; a node may have "
                "several parents so the field is a sequence" % node_id
            )
        if not isinstance(parents, (list, tuple)):
            raise ValueError("node %s parents must be a sequence" % node_id)
        for parent in parents:
            _require_identifier("parent id", parent)
        if node_id in nodes:
            raise ValueError("node id %r appears twice in the chain" % node_id)
        if kind == NODE_HEAT and parents:
            raise ValueError(
                "node %s is a heat and cannot itself be declared out of "
                "anything" % node_id
            )
        nodes[node_id] = {"id": node_id, "kind": kind, "parents": list(parents)}
    if not nodes:
        raise ValueError("the traceability chain holds no nodes at all")
    return nodes


def walk_traceability(chain, delivery_lot_id):
    """Walk the declaration upwards and say what it actually resolves to."""
    nodes = _normalise_chain(chain)
    start = _require_identifier("delivery_lot_id", delivery_lot_id)
    if start not in nodes:
        raise ValueError(
            "the delivered lot %r is not declared anywhere in the chain" % start
        )
    heats = set()
    broken = []
    visiting = set()
    visited = set()
    circular = []

    def _visit(node_id):
        if node_id in visiting:
            circular.append(node_id)
            return
        if node_id in visited:
            return
        visiting.add(node_id)
        node = nodes[node_id]
        if node["kind"] == NODE_HEAT:
            heats.add(node_id)
        elif not node["parents"]:
            broken.append(node_id)
        for parent in node["parents"]:
            if parent not in nodes:
                broken.append(parent)
                continue
            _visit(parent)
        visiting.discard(node_id)
        visited.add(node_id)

    _visit(start)
    if circular:
        status = CHAIN_CIRCULAR
    elif broken:
        status = CHAIN_BROKEN
    elif len(heats) > 1:
        status = CHAIN_MIXED
    elif len(heats) == 1:
        status = CHAIN_RESOLVED
    else:
        status = CHAIN_BROKEN
    findings = []
    for node_id in sorted(set(broken)):
        findings.append(
            "the chain stops at %r; its parent is not in the records, so the "
            "walk cannot reach a heat through it" % node_id
        )
    for node_id in sorted(set(circular)):
        findings.append(
            "node %r is declared out of itself through the chain; that is a "
            "corrupted record, not a deep one" % node_id
        )
    if status == CHAIN_MIXED:
        findings.append(
            "the delivered lot resolves to %d heats (%s); the mechanical "
            "results of neither heat cover the parts of the other"
            % (len(heats), ", ".join(sorted(heats)))
        )
    return {
        "delivery_lot_id": start,
        "status": status,
        "heats": sorted(heats),
        "resolved": status == CHAIN_RESOLVED,
        "findings": findings,
        "nodes_walked": len(visited),
    }


def assess_records(case):
    """Whether acceptance may be signed on this lot's paper trail."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    lot_id = _require_identifier("lot_id", case.get("lot_id"))
    criticality = _require_choice(
        "criticality", case.get("criticality"), CRITICALITIES
    )
    delivery_date = _require_date("delivery_date", case.get("delivery_date"))
    present = case.get("records_present", [])
    gaps = missing_records(criticality, present)
    chain = case.get("traceability_chain")
    findings = []
    if gaps:
        findings.append(
            "%d required record(s) are not on the file: %s"
            % (len(gaps), ", ".join(gaps))
        )
    if chain is None:
        trace = None
        findings.append(
            "no traceability chain was declared, so the delivered lot cannot "
            "be resolved to a heat"
        )
    else:
        trace = walk_traceability(chain, lot_id)
        findings.extend(trace["findings"])
    resolved = bool(trace and trace["resolved"])
    complete = not gaps and resolved
    return {
        "lot_id": lot_id,
        "criticality": criticality,
        "required_records": required_records(criticality),
        "missing_records": gaps,
        "traceability": trace,
        "retention_deadline": retention_deadline(delivery_date, criticality),
        "acceptance_signable": complete,
        "verdict": VERDICT_COMPLETE if complete else VERDICT_INCOMPLETE,
        "findings": findings,
    }
