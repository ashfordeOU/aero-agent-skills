"""Identity traceability for class 2 EEE parts, receipt to finished assembly.

Anchor: ECSS-Q-ST-60C clause 5.5.4 (keeping class 2 part identity traceable
from goods receipt, through storage, into finished assemblies). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read the depth of identity each receipt record actually supports, from no
   identity at all up to a serialised one, because a class 2 trail is allowed
   to rest on the lot and date code rather than on the individual part.
2. Read the depth the application demands from the criticality of the function
   the parts go into, and report the shortfall in steps rather than as a bare
   pass or fail.
3. Reconcile every lot: received against issued, scrapped and remaining, so a
   lot that gave out more parts than it ever held is caught.
4. Reject an assembly that consumed a lot never issued to it, because an
   assembly with an unsourced part has no identity trail at all.
5. Detect a storage bin holding more than one lot of the same part number,
   which merges two identities into one and breaks both, and flag a lot held
   past the storage limit.
6. Trace forward from a lot to every assembly it reached, backward from an
   assembly to every lot it drew on, and return one verdict per lot plus the
   share of lots that came out traceable.
"""

import datetime

__all__ = [
    "TRACE_DEPTHS",
    "CRITICALITY_DEPTHS",
    "TRACE_VERDICTS",
    "REQUIRED_RECEIPT_FIELDS",
    "STORAGE_LIMIT_DAYS",
    "parse_iso_date",
    "achieved_depth",
    "required_depth",
    "depth_shortfall",
    "storage_age_days",
    "storage_limit_exceeded",
    "reconcile_lot",
    "mixed_bins",
    "missing_receipt_fields",
    "unsourced_consumptions",
    "forward_trace",
    "backward_trace",
    "lot_verdict",
    "traceable_share",
    "assess_class_2_traceability",
]

# Depths of identity a trail can rest on, weakest first.
TRACE_DEPTHS = ("none", "part-number", "date-code", "lot", "serialised")

_DEPTH_RANK = {name: index for index, name in enumerate(TRACE_DEPTHS)}

# The depth each application criticality demands of a class 2 trail.
CRITICALITY_DEPTHS = {
    "non-critical": "date-code",
    "mission-critical": "lot",
    "safety-critical": "serialised",
}

# Per-lot verdicts, from a complete trail to no identity at all.
TRACE_VERDICTS = (
    "traceable",
    "trace-depth-short",
    "quantity-imbalance",
    "broken-chain",
    "storage-limit-exceeded",
    "incomplete-receipt-record",
    "unidentified",
)

# A receipt record owns the lot identity; without these it owns nothing.
REQUIRED_RECEIPT_FIELDS = (
    "lot_id",
    "part_number",
    "manufacturer",
    "date_code",
    "quantity_received",
    "receipt_date",
    "certificate_reference",
    "bin",
)

# Calendar days a class 2 lot may sit in store before its supporting evidence
# stops carrying the identity forward.
STORAGE_LIMIT_DAYS = 730


def _require_mapping(value, label):
    """Return a validated mapping or raise."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, value))
    return value


def _require_text(value, label):
    """Return a stripped non-empty string or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _require_count(value, label, allow_zero=True):
    """Return a validated non-negative integer or raise."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0 or (not allow_zero and value == 0):
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _require_sequence(value, label):
    """Return a validated sequence or raise."""
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence, got %r" % (label, value))
    return value


def parse_iso_date(value, label="date"):
    """Return an ISO date string or date object as a date."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (label, value))


def _has_text(record, key):
    """Return True when a record carries a non-empty string under key."""
    value = record.get(key)
    return isinstance(value, str) and bool(value.strip())


def achieved_depth(receipt):
    """Return the depth of identity one receipt record actually supports."""
    _require_mapping(receipt, "receipt")
    serials = receipt.get("serial_numbers", [])
    if serials:
        _require_sequence(serials, "serial_numbers")
        quantity = receipt.get("quantity_received")
        if not isinstance(quantity, int) or isinstance(quantity, bool):
            raise ValueError("quantity_received must be an integer for a "
                             "serialised receipt, got %r" % (quantity,))
        if len(serials) == quantity and _has_text(receipt, "lot_id"):
            return "serialised"
    if _has_text(receipt, "lot_id") and _has_text(receipt, "date_code") \
            and _has_text(receipt, "certificate_reference"):
        return "lot"
    if _has_text(receipt, "date_code") and _has_text(receipt, "part_number"):
        return "date-code"
    if _has_text(receipt, "part_number"):
        return "part-number"
    return "none"


def required_depth(criticality):
    """Return the identity depth an application criticality demands."""
    name = _require_text(criticality, "criticality").casefold()
    if name not in CRITICALITY_DEPTHS:
        raise ValueError(
            "criticality must be one of %r, got %r"
            % (sorted(CRITICALITY_DEPTHS), criticality)
        )
    return CRITICALITY_DEPTHS[name]


def depth_shortfall(achieved, required):
    """Return how many depth steps a trail falls short, zero when it is met."""
    for value, label in ((achieved, "achieved"), (required, "required")):
        name = _require_text(value, label).casefold()
        if name not in _DEPTH_RANK:
            raise ValueError(
                "%s must be one of %r, got %r" % (label, list(TRACE_DEPTHS), value)
            )
    return max(0, _DEPTH_RANK[required.casefold()] - _DEPTH_RANK[achieved.casefold()])


def storage_age_days(receipt_date, as_of_date):
    """Return the calendar days a lot has been in store."""
    start = parse_iso_date(receipt_date, "receipt_date")
    end = parse_iso_date(as_of_date, "as_of_date")
    if end < start:
        raise ValueError("as_of_date %s precedes receipt_date %s" % (end, start))
    return (end - start).days


def storage_limit_exceeded(days, limit=STORAGE_LIMIT_DAYS):
    """Return True when a lot has sat in store beyond the limit."""
    held = _require_count(days, "days")
    bound = _require_count(limit, "limit", allow_zero=False)
    return held > bound


def reconcile_lot(receipt, issues, scraps=()):
    """Return the quantity balance of one lot.

    A lot that has issued and scrapped more than it received cannot be
    reconciled, and the imbalance is reported rather than clamped away.
    """
    _require_mapping(receipt, "receipt")
    lot_id = _require_text(receipt.get("lot_id"), "lot_id")
    received = _require_count(receipt.get("quantity_received"),
                              "quantity_received", allow_zero=False)
    issued = 0
    for record in _require_sequence(issues, "issues"):
        _require_mapping(record, "issue record")
        if _require_text(record.get("lot_id"), "lot_id") != lot_id:
            continue
        issued += _require_count(record.get("quantity"), "quantity")
    scrapped = 0
    for record in _require_sequence(scraps, "scraps"):
        _require_mapping(record, "scrap record")
        if _require_text(record.get("lot_id"), "lot_id") != lot_id:
            continue
        scrapped += _require_count(record.get("quantity"), "quantity")
    remaining = received - issued - scrapped
    return {
        "lot_id": lot_id,
        "received": received,
        "issued": issued,
        "scrapped": scrapped,
        "remaining": remaining,
        "balanced": remaining >= 0,
    }


def mixed_bins(receipts):
    """Return the bins holding more than one lot of the same part number."""
    seen = {}
    for receipt in _require_sequence(receipts, "receipts"):
        _require_mapping(receipt, "receipt")
        bin_name = receipt.get("bin")
        if not isinstance(bin_name, str) or not bin_name.strip():
            continue
        part_number = _require_text(receipt.get("part_number"), "part_number")
        lot_id = _require_text(receipt.get("lot_id"), "lot_id")
        seen.setdefault((bin_name.strip(), part_number), set()).add(lot_id)
    mixed = [
        {"bin": key[0], "part_number": key[1], "lots": sorted(lots)}
        for key, lots in seen.items()
        if len(lots) > 1
    ]
    return sorted(mixed, key=lambda item: (item["bin"], item["part_number"]))


def unsourced_consumptions(issues, assemblies):
    """Return the assembly and lot pairs where the lot was never issued."""
    issued = set()
    for record in _require_sequence(issues, "issues"):
        _require_mapping(record, "issue record")
        issued.add((
            _require_text(record.get("assembly_id"), "assembly_id"),
            _require_text(record.get("lot_id"), "lot_id"),
        ))
    broken = []
    for assembly in _require_sequence(assemblies, "assemblies"):
        _require_mapping(assembly, "assembly record")
        assembly_id = _require_text(assembly.get("assembly_id"), "assembly_id")
        for lot_id in _require_sequence(assembly.get("consumed_lots", []),
                                        "consumed_lots"):
            name = _require_text(lot_id, "lot_id")
            if (assembly_id, name) not in issued:
                broken.append({"assembly_id": assembly_id, "lot_id": name})
    return sorted(broken, key=lambda item: (item["assembly_id"], item["lot_id"]))


def forward_trace(lot_id, assemblies):
    """Return every assembly one lot reached, in identifier order."""
    name = _require_text(lot_id, "lot_id")
    reached = set()
    for assembly in _require_sequence(assemblies, "assemblies"):
        _require_mapping(assembly, "assembly record")
        consumed = [
            _require_text(item, "lot_id")
            for item in _require_sequence(assembly.get("consumed_lots", []),
                                          "consumed_lots")
        ]
        if name in consumed:
            reached.add(_require_text(assembly.get("assembly_id"), "assembly_id"))
    return sorted(reached)


def backward_trace(assembly_id, assemblies):
    """Return every lot one assembly drew on, in identifier order."""
    name = _require_text(assembly_id, "assembly_id")
    for assembly in _require_sequence(assemblies, "assemblies"):
        _require_mapping(assembly, "assembly record")
        if _require_text(assembly.get("assembly_id"), "assembly_id") != name:
            continue
        return sorted({
            _require_text(item, "lot_id")
            for item in _require_sequence(assembly.get("consumed_lots", []),
                                          "consumed_lots")
        })
    raise ValueError("assembly %r is not in the assembly records" % assembly_id)


def missing_receipt_fields(receipt):
    """Return the required receipt fields the record does not carry."""
    _require_mapping(receipt, "receipt")
    return [field for field in REQUIRED_RECEIPT_FIELDS
            if receipt.get(field) in (None, "", [])]


def lot_verdict(receipt, balance, shortfall, expired, broken):
    """Return the single verdict one lot's trail earns.

    The verdicts are ordered by how badly the trail is broken: an unidentified
    lot outranks a broken chain, which outranks an imbalance, which outranks a
    storage overrun, an incomplete receipt record and a depth shortfall.
    """
    _require_mapping(receipt, "receipt")
    _require_mapping(balance, "balance")
    if not isinstance(shortfall, int) or isinstance(shortfall, bool):
        raise ValueError("shortfall must be an integer, got %r" % (shortfall,))
    if not _has_text(receipt, "lot_id") or achieved_depth(receipt) == "none":
        return "unidentified"
    if broken:
        return "broken-chain"
    if not balance.get("balanced", False):
        return "quantity-imbalance"
    if expired:
        return "storage-limit-exceeded"
    if missing_receipt_fields(receipt):
        return "incomplete-receipt-record"
    if shortfall > 0:
        return "trace-depth-short"
    return "traceable"


def traceable_share(verdicts):
    """Return the share of lots whose trail came out fully traceable."""
    names = _require_sequence(verdicts, "verdicts")
    if not names:
        raise ValueError("verdicts must name at least one lot")
    for name in names:
        if _require_text(name, "verdict") not in TRACE_VERDICTS:
            raise ValueError(
                "verdict must be one of %r, got %r" % (list(TRACE_VERDICTS), name)
            )
    good = sum(1 for name in names if name == "traceable")
    return good / float(len(names))


def assess_class_2_traceability(receipts, issues=(), assemblies=(), scraps=(),
                                criticality="mission-critical", as_of=None):
    """Run the clause 5.5.4 traceability assessment over a set of lots.

    receipts carry the fields in REQUIRED_RECEIPT_FIELDS plus optional
    serial_numbers; issues carry lot_id, assembly_id and quantity; assemblies
    carry assembly_id and consumed_lots; scraps carry lot_id and quantity.
    """
    _require_sequence(receipts, "receipts")
    if not receipts:
        raise ValueError("receipts must name at least one lot")
    demanded = required_depth(criticality)
    broken = unsourced_consumptions(list(issues), list(assemblies))
    broken_lots = {item["lot_id"] for item in broken}
    reference = as_of if as_of is not None else None
    lots = []
    verdicts = []
    for receipt in receipts:
        _require_mapping(receipt, "receipt")
        depth = achieved_depth(receipt)
        shortfall = depth_shortfall(depth, demanded)
        balance = reconcile_lot(receipt, list(issues), list(scraps))
        if reference is not None and _has_text(receipt, "receipt_date"):
            age = storage_age_days(receipt.get("receipt_date"), reference)
            expired = storage_limit_exceeded(age)
        else:
            age = None
            expired = False
        verdict = lot_verdict(receipt, balance, shortfall, expired,
                              balance["lot_id"] in broken_lots)
        verdicts.append(verdict)
        lots.append({
            "lot_id": balance["lot_id"],
            "achieved_depth": depth,
            "required_depth": demanded,
            "depth_shortfall": shortfall,
            "storage_age_days": age,
            "storage_limit_exceeded": expired,
            "balance": balance,
            "assemblies_reached": forward_trace(balance["lot_id"],
                                                list(assemblies)),
            "verdict": verdict,
        })
    return {
        "required_depth": demanded,
        "lots": lots,
        "mixed_bins": mixed_bins(list(receipts)),
        "unsourced_consumptions": broken,
        "traceable_share": traceable_share(verdicts),
        "all_traceable": all(name == "traceable" for name in verdicts),
    }
