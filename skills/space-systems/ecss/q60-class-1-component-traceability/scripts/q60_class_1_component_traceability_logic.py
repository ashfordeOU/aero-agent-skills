"""Identity traceability for highest-assurance EEE parts, receipt to assembly.

Anchor: ECSS-Q-ST-60C clause 4.5.4 (keeping class 1 part identity traceable
at goods receipt, through storage and kitting, into finished assemblies).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the receipt records that own each lot identity, and the issue and
   assembly records that claim to draw on them.
2. Reconcile each lot: received quantity against issued, scrapped and remaining,
   so a lot that has given out more parts than it ever held is caught.
3. Reject an assembly that consumed a lot never issued to it, because an
   assembly with an unsourced part has no identity trail at all.
4. Detect a storage bin holding more than one lot of the same part number,
   which merges two identities into one and breaks both.
5. Flag a lot held past its storage limit, where the identity survives but the
   solderability evidence behind it does not.
6. Trace forward from a lot to every assembly it reached, and backward from an
   assembly to every lot it drew on.
"""

import datetime

__all__ = [
    "TRACE_VERDICTS",
    "REQUIRED_RECEIPT_FIELDS",
    "parse_iso_date",
    "storage_age_days",
    "storage_expired",
    "reconcile_lot",
    "mixed_bins",
    "forward_trace",
    "backward_trace",
    "lot_verdict",
    "assess_traceability",
]

# Per-lot verdicts, from a complete trail to no identity at all.
TRACE_VERDICTS = (
    "traceable",
    "quantity-imbalance",
    "broken-chain",
    "storage-limit-exceeded",
    "unidentified",
)

# A receipt record owns the identity; without these it owns nothing.
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


def storage_age_days(receipt_date, as_of_date):
    """Return the calendar days a lot has been in store."""
    start = parse_iso_date(receipt_date, "receipt_date")
    end = parse_iso_date(as_of_date, "as_of_date")
    if end < start:
        raise ValueError("as_of_date %s precedes receipt_date %s" % (end, start))
    return (end - start).days


def storage_expired(receipt_date, as_of_date, storage_limit_days):
    """Return True when the lot has been held longer than its storage limit.

    A lot sitting exactly on its limit is still inside it; the limit is the
    last day the stored evidence is good for, not the first day it is not.
    """
    if (
        not isinstance(storage_limit_days, int)
        or isinstance(storage_limit_days, bool)
        or storage_limit_days <= 0
    ):
        raise ValueError("storage_limit_days must be a positive integer")
    return storage_age_days(receipt_date, as_of_date) > storage_limit_days


def _validate_receipt(receipt, index):
    """Return a normalised receipt record."""
    if not isinstance(receipt, dict):
        raise ValueError("receipt[%d] must be a mapping" % index)
    for field in REQUIRED_RECEIPT_FIELDS:
        if field not in receipt or receipt[field] in (None, ""):
            raise ValueError(
                "receipt[%d] missing required identity field '%s'" % (index, field)
            )
    quantity = receipt["quantity_received"]
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        raise ValueError(
            "receipt[%d]['quantity_received'] must be a positive integer" % index
        )
    limit = receipt.get("storage_limit_days", 730)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        raise ValueError(
            "receipt[%d]['storage_limit_days'] must be a positive integer" % index
        )
    scrapped = receipt.get("quantity_scrapped", 0)
    if not isinstance(scrapped, int) or isinstance(scrapped, bool) or scrapped < 0:
        raise ValueError(
            "receipt[%d]['quantity_scrapped'] must be a non-negative integer" % index
        )
    remaining = receipt.get("quantity_remaining")
    if remaining is not None and (
        not isinstance(remaining, int) or isinstance(remaining, bool) or remaining < 0
    ):
        raise ValueError(
            "receipt[%d]['quantity_remaining'] must be a non-negative integer or None"
            % index
        )
    return {
        "lot_id": str(receipt["lot_id"]).strip(),
        "part_number": str(receipt["part_number"]).strip().upper(),
        "manufacturer": str(receipt["manufacturer"]).strip(),
        "date_code": str(receipt["date_code"]).strip(),
        "quantity_received": quantity,
        "quantity_scrapped": scrapped,
        "quantity_remaining": remaining,
        "receipt_date": parse_iso_date(receipt["receipt_date"], "receipt_date"),
        "certificate_reference": str(receipt["certificate_reference"]).strip(),
        "bin": str(receipt["bin"]).strip(),
        "storage_limit_days": limit,
    }


def _validate_issue(issue, index):
    """Return a normalised issue record."""
    if not isinstance(issue, dict):
        raise ValueError("issue[%d] must be a mapping" % index)
    for key in ("lot_id", "assembly_id", "quantity_issued"):
        if key not in issue:
            raise ValueError("issue[%d] missing required key '%s'" % (index, key))
    quantity = issue["quantity_issued"]
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        raise ValueError(
            "issue[%d]['quantity_issued'] must be a positive integer" % index
        )
    return {
        "lot_id": str(issue["lot_id"]).strip(),
        "assembly_id": str(issue["assembly_id"]).strip(),
        "quantity_issued": quantity,
    }


def _validate_assembly(assembly, index):
    """Return a normalised assembly record."""
    if not isinstance(assembly, dict):
        raise ValueError("assembly[%d] must be a mapping" % index)
    for key in ("assembly_id", "consumed"):
        if key not in assembly:
            raise ValueError("assembly[%d] missing required key '%s'" % (index, key))
    consumed = assembly["consumed"]
    if not isinstance(consumed, dict) or not consumed:
        raise ValueError(
            "assembly[%d]['consumed'] must be a non-empty mapping of lot to quantity"
            % index
        )
    normalised = {}
    for lot_id, quantity in consumed.items():
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            raise ValueError(
                "assembly[%d] consumed quantity for %r must be a positive integer"
                % (index, lot_id)
            )
        normalised[str(lot_id).strip()] = quantity
    return {
        "assembly_id": str(assembly["assembly_id"]).strip(),
        "consumed": normalised,
    }


def reconcile_lot(quantity_received, quantity_issued, quantity_scrapped,
                  quantity_remaining):
    """Return the reconciliation of one lot's quantities.

    Everything received is still somewhere: issued to an assembly, scrapped, or
    on the shelf. A shortfall means parts left the lot with no record, which is
    the identity break the clause exists to prevent.
    """
    values = (
        quantity_received,
        quantity_issued,
        quantity_scrapped,
        quantity_remaining,
    )
    for value in values:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("quantities must be non-negative integers, got %r" % (value,))
    if quantity_received <= 0:
        raise ValueError("quantity_received must be a positive integer")
    accounted = quantity_issued + quantity_scrapped + quantity_remaining
    return {
        "quantity_received": quantity_received,
        "quantity_accounted": accounted,
        "difference": accounted - quantity_received,
        "balanced": accounted == quantity_received,
    }


def mixed_bins(receipts):
    """Return the bins holding more than one lot of the same part number."""
    if not isinstance(receipts, (list, tuple)):
        raise ValueError("receipts must be a sequence of receipt records")
    seen = {}
    for index, receipt in enumerate(receipts):
        record = _validate_receipt(receipt, index)
        key = (record["bin"], record["part_number"])
        seen.setdefault(key, set()).add(record["lot_id"])
    mixed = [
        {"bin": key[0], "part_number": key[1], "lot_ids": tuple(sorted(lots))}
        for key, lots in seen.items()
        if len(lots) > 1
    ]
    return tuple(sorted(mixed, key=lambda item: (item["bin"], item["part_number"])))


def forward_trace(lot_id, assemblies):
    """Return every assembly that consumed the named lot."""
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("lot_id must be a non-empty string")
    if not isinstance(assemblies, (list, tuple)):
        raise ValueError("assemblies must be a sequence of assembly records")
    target = lot_id.strip()
    reached = []
    for index, assembly in enumerate(assemblies):
        record = _validate_assembly(assembly, index)
        if target in record["consumed"] and record["assembly_id"] not in reached:
            reached.append(record["assembly_id"])
    return tuple(sorted(reached))


def backward_trace(assembly_id, assemblies):
    """Return every lot the named assembly drew on."""
    if not isinstance(assembly_id, str) or not assembly_id.strip():
        raise ValueError("assembly_id must be a non-empty string")
    if not isinstance(assemblies, (list, tuple)):
        raise ValueError("assemblies must be a sequence of assembly records")
    target = assembly_id.strip()
    lots = set()
    found = False
    for index, assembly in enumerate(assemblies):
        record = _validate_assembly(assembly, index)
        if record["assembly_id"] == target:
            found = True
            lots.update(record["consumed"])
    if not found:
        raise ValueError("assembly %r appears in no assembly record" % assembly_id)
    return tuple(sorted(lots))


def lot_verdict(balanced, chain_intact, within_storage_limit):
    """Return the per-lot verdict from the three checks that decide it."""
    for flag in (balanced, chain_intact, within_storage_limit):
        if not isinstance(flag, bool):
            raise ValueError("verdict inputs must be bools, got %r" % (flag,))
    if not chain_intact:
        return "broken-chain"
    if not balanced:
        return "quantity-imbalance"
    if not within_storage_limit:
        return "storage-limit-exceeded"
    return "traceable"


def assess_traceability(receipts, issues, assemblies, as_of_date):
    """Run the full clause 4.5.4 identity-trail assessment over a programme."""
    if not isinstance(receipts, (list, tuple)) or not receipts:
        raise ValueError("receipts must be a non-empty sequence of receipt records")
    if not isinstance(issues, (list, tuple)):
        raise ValueError("issues must be a sequence of issue records")
    if not isinstance(assemblies, (list, tuple)):
        raise ValueError("assemblies must be a sequence of assembly records")
    as_of = parse_iso_date(as_of_date, "as_of_date")

    receipt_records = [_validate_receipt(r, i) for i, r in enumerate(receipts)]
    known_lots = {}
    for record in receipt_records:
        if record["lot_id"] in known_lots:
            raise ValueError(
                "lot %s is owned by more than one receipt record" % record["lot_id"]
            )
        known_lots[record["lot_id"]] = record

    issue_records = [_validate_issue(entry, i) for i, entry in enumerate(issues)]
    assembly_records = [_validate_assembly(a, i) for i, a in enumerate(assemblies)]

    issued_by_lot = {}
    issued_pairs = set()
    findings = []
    for entry in issue_records:
        if entry["lot_id"] not in known_lots:
            findings.append(
                "issue to %s draws on lot %s, which no receipt record owns"
                % (entry["assembly_id"], entry["lot_id"])
            )
            continue
        issued_by_lot[entry["lot_id"]] = (
            issued_by_lot.get(entry["lot_id"], 0) + entry["quantity_issued"]
        )
        issued_pairs.add((entry["lot_id"], entry["assembly_id"]))

    unsourced = []
    for record in assembly_records:
        for lot_id, quantity in sorted(record["consumed"].items()):
            if (lot_id, record["assembly_id"]) not in issued_pairs:
                unsourced.append(
                    {
                        "assembly_id": record["assembly_id"],
                        "lot_id": lot_id,
                        "quantity": quantity,
                    }
                )
                findings.append(
                    "assembly %s consumed %d part(s) of lot %s that were never "
                    "issued to it"
                    % (record["assembly_id"], quantity, lot_id)
                )

    broken_lots = {item["lot_id"] for item in unsourced}
    bins = mixed_bins(receipts)
    for entry in bins:
        findings.append(
            "bin %s holds lots %s of the same part number, merging two identities"
            % (entry["bin"], ", ".join(entry["lot_ids"]))
        )

    lots = []
    for record in receipt_records:
        issued = issued_by_lot.get(record["lot_id"], 0)
        scrapped = record["quantity_scrapped"]
        remaining = record["quantity_remaining"]
        if remaining is None:
            # No stores count was supplied, so the shelf is taken to hold what
            # the receipt has not given out. An over-issue leaves nothing.
            remaining = max(0, record["quantity_received"] - issued - scrapped)
        reconciliation = reconcile_lot(
            record["quantity_received"], issued, scrapped, remaining
        )
        expired = storage_expired(
            record["receipt_date"], as_of, record["storage_limit_days"]
        )
        chain_intact = record["lot_id"] not in broken_lots
        verdict = lot_verdict(
            reconciliation["balanced"], chain_intact, not expired
        )
        if not reconciliation["balanced"]:
            findings.append(
                "lot %s accounts for %d part(s) against %d received"
                % (
                    record["lot_id"],
                    reconciliation["quantity_accounted"],
                    record["quantity_received"],
                )
            )
        if expired:
            findings.append(
                "lot %s has been in store %d days against a %d day limit"
                % (
                    record["lot_id"],
                    storage_age_days(record["receipt_date"], as_of),
                    record["storage_limit_days"],
                )
            )
        lots.append(
            {
                "lot_id": record["lot_id"],
                "part_number": record["part_number"],
                "manufacturer": record["manufacturer"],
                "date_code": record["date_code"],
                "certificate_reference": record["certificate_reference"],
                "bin": record["bin"],
                "quantity_received": record["quantity_received"],
                "quantity_issued": issued,
                "quantity_scrapped": scrapped,
                "quantity_remaining": remaining,
                "reconciliation": reconciliation,
                "storage_age_days": storage_age_days(record["receipt_date"], as_of),
                "storage_limit_days": record["storage_limit_days"],
                "within_storage_limit": not expired,
                "assemblies_reached": forward_trace(record["lot_id"], assemblies),
                "verdict": verdict,
            }
        )

    traceable = [lot for lot in lots if lot["verdict"] == "traceable"]
    return {
        "as_of": as_of.isoformat(),
        "lots": lots,
        "lot_count": len(lots),
        "traceable_lot_count": len(traceable),
        "traceable_quantity": sum(lot["quantity_received"] for lot in traceable),
        "untraceable_quantity": sum(
            lot["quantity_received"] for lot in lots if lot["verdict"] != "traceable"
        ),
        "mixed_bins": bins,
        "unsourced_consumption": tuple(
            (item["assembly_id"], item["lot_id"]) for item in unsourced
        ),
        "findings": findings,
        "trail_complete": not findings,
    }
