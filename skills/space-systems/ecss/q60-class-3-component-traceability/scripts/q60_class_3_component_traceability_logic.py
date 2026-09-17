"""Identity traceability for class 3 EEE parts, receipt through to assembly.

Anchor: ECSS-Q-ST-60C clause 6.5.4 (keeping class 3 part identity traceable
from receipt, through storage and kitting, into finished assemblies).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read the identity granularity each receipt record actually supports, from
   nothing at all up to a serialised unit, and check the fields a receipt is
   expected to carry are present.
2. Hold that against the granularity the application demands, and report the
   shortfall in whole identity steps rather than as a yes or no.
3. Guard the programme-assigned receipt batch identifier, because at this class
   it is usually the only identity there is: one identifier must not cover two
   deliveries, and a batch must not be split without a split record.
4. Walk the custody chain backwards from each fitted part through the issue
   that supplied it to the receipt that brought it in, and take the achieved
   granularity as the weakest link on that chain.
5. Reconcile received quantity against issued, scrapped and remaining, and
   name any assembly that consumed parts from a receipt never issued to it.
6. Check the chain runs forward in time, since a record dated after the
   installation it supplied cannot have supplied it.
7. Report the share of fitted parts that reach a receipt at the demanded
   granularity, exactly and as a fraction.
"""

import datetime

__all__ = [
    "IDENTITY_GRANULARITIES",
    "GRANULARITY_ORDER",
    "CUSTODY_STAGES",
    "REQUIRED_RECEIPT_FIELDS",
    "USAGE_GRANULARITY_FLOOR",
    "TRACE_VERDICTS",
    "parse_iso_date",
    "receipt_granularity",
    "missing_receipt_fields",
    "required_granularity",
    "granularity_shortfall",
    "batch_identifier_conflicts",
    "unrecorded_splits",
    "custody_chain",
    "chain_granularity",
    "reconcile_receipt",
    "unsourced_consumptions",
    "out_of_order_records",
    "assembly_verdict",
    "traceable_share",
    "assess_class_3_traceability",
]

# How finely a record lets one delivered unit be named, coarsest first.
IDENTITY_GRANULARITIES = {
    "none": 0,
    "part-number": 1,
    "date-code": 2,
    "receipt-batch": 3,
    "lot": 4,
    "serialised": 5,
}

GRANULARITY_ORDER = (
    "none",
    "part-number",
    "date-code",
    "receipt-batch",
    "lot",
    "serialised",
)

# The custody transitions identity has to survive.
CUSTODY_STAGES = ("receipt", "storage", "kitting", "assembly")

# Fields a class 3 receipt record is expected to carry at goods-in.
REQUIRED_RECEIPT_FIELDS = (
    "receipt_id",
    "part_number",
    "quantity",
    "received_date",
    "receipt_batch",
)

# The floor the application sets on identity granularity.
USAGE_GRANULARITY_FLOOR = {
    "development": "part-number",
    "ground-support": "date-code",
    "flight-non-critical": "receipt-batch",
    "flight-critical": "lot",
}

TRACE_VERDICTS = ("traceable", "shortfall", "broken")


def parse_iso_date(value, label="date"):
    """Return an ISO date string or a date object as a date."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (label, value))


def _text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _key(value):
    text = _text(value)
    return text.upper() if text is not None else None


def receipt_granularity(receipt):
    """Return the finest identity granularity one receipt record supports.

    Each level needs everything under it: a lot identity is only a lot identity
    when the delivery is also named by part number, and a serial list is only
    serialised when it actually covers the delivered quantity.
    """
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be a mapping")
    if _text(receipt.get("part_number")) is None:
        return "none"
    level = "part-number"
    if _text(receipt.get("date_code")) is not None:
        level = "date-code"
    else:
        return level
    if _text(receipt.get("receipt_batch")) is not None:
        level = "receipt-batch"
    else:
        return level
    if _text(receipt.get("lot_id")) is not None:
        level = "lot"
    else:
        return level
    serials = receipt.get("serial_numbers")
    if serials:
        if not isinstance(serials, (list, tuple)):
            raise ValueError("receipt['serial_numbers'] must be a sequence")
        quantity = receipt.get("quantity")
        if isinstance(quantity, int) and not isinstance(quantity, bool):
            if len(set(_key(s) for s in serials)) == quantity:
                level = "serialised"
    return level


def missing_receipt_fields(receipt):
    """Return the expected receipt fields that are absent or empty."""
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be a mapping")
    missing = []
    for field in REQUIRED_RECEIPT_FIELDS:
        value = receipt.get(field)
        if field == "quantity":
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                missing.append(field)
            continue
        if _text(value) is None:
            missing.append(field)
    return tuple(missing)


def required_granularity(usage):
    """Return the identity granularity the application demands."""
    if usage not in USAGE_GRANULARITY_FLOOR:
        raise ValueError(
            "usage must be one of %s, got %r" % (sorted(USAGE_GRANULARITY_FLOOR), usage)
        )
    return USAGE_GRANULARITY_FLOOR[usage]


def granularity_shortfall(achieved, required):
    """Return how many identity steps short the achieved granularity falls."""
    for label, value in (("achieved", achieved), ("required", required)):
        if value not in IDENTITY_GRANULARITIES:
            raise ValueError(
                "%s must be one of %s, got %r"
                % (label, list(GRANULARITY_ORDER), value)
            )
    gap = IDENTITY_GRANULARITIES[required] - IDENTITY_GRANULARITIES[achieved]
    return gap if gap > 0 else 0


def batch_identifier_conflicts(receipts):
    """Return receipt batch identifiers covering more than one delivery.

    Two receipts may share an identifier only when they are the same delivery of
    the same part on the same day. Anything else means one identifier now names
    two populations, and the identity it was created to carry is gone.
    """
    if not isinstance(receipts, (list, tuple)):
        raise ValueError("receipts must be a sequence of receipt records")
    seen = {}
    conflicts = []
    for index, receipt in enumerate(receipts):
        if not isinstance(receipt, dict):
            raise ValueError("receipts[%d] must be a mapping" % index)
        batch = _key(receipt.get("receipt_batch"))
        if batch is None:
            continue
        signature = (
            _key(receipt.get("part_number")),
            parse_iso_date(
                receipt.get("received_date"), "receipts[%d]['received_date']" % index
            ),
        )
        if batch in seen:
            if seen[batch] != signature and batch not in conflicts:
                conflicts.append(batch)
        else:
            seen[batch] = signature
    return tuple(sorted(conflicts))


def unrecorded_splits(issues):
    """Return issue identifiers that split a batch without a split record."""
    if not isinstance(issues, (list, tuple)):
        raise ValueError("issues must be a sequence of issue records")
    offenders = []
    for index, issue in enumerate(issues):
        if not isinstance(issue, dict):
            raise ValueError("issues[%d] must be a mapping" % index)
        if "issue_id" not in issue:
            raise ValueError("issues[%d] missing required key 'issue_id'" % index)
        sub_batch = _text(issue.get("sub_batch"))
        if sub_batch is None:
            continue
        if _text(issue.get("split_record")) is None:
            offenders.append(_text(issue["issue_id"]))
    return tuple(offenders)


def custody_chain(consumption, issues, receipts):
    """Return the custody chain behind one fitted part, and where it breaks.

    The chain runs assembly, kitting, storage, receipt. It is walked backwards:
    the consumption names a receipt, an issue has to connect that receipt to
    that assembly, and the receipt itself has to exist.
    """
    if not isinstance(consumption, dict):
        raise ValueError("consumption must be a mapping")
    for key in ("assembly_id", "receipt_id"):
        if key not in consumption:
            raise ValueError("consumption missing required key '%s'" % key)
    if not isinstance(issues, (list, tuple)):
        raise ValueError("issues must be a sequence of issue records")
    if not isinstance(receipts, (list, tuple)):
        raise ValueError("receipts must be a sequence of receipt records")
    assembly = _key(consumption["assembly_id"])
    receipt_id = _key(consumption["receipt_id"])
    reached = ["assembly"]
    matching_issue = None
    for index, issue in enumerate(issues):
        if not isinstance(issue, dict):
            raise ValueError("issues[%d] must be a mapping" % index)
        if _key(issue.get("receipt_id")) == receipt_id and _key(
            issue.get("to_assembly")
        ) == assembly:
            matching_issue = issue
            break
    if matching_issue is None:
        return {
            "assembly_id": _text(consumption["assembly_id"]),
            "receipt_id": _text(consumption["receipt_id"]),
            "stages_reached": tuple(reached),
            "issue": None,
            "receipt": None,
            "broken_at": "kitting",
            "complete": False,
        }
    reached.append("kitting")
    reached.append("storage")
    matching_receipt = None
    for index, receipt in enumerate(receipts):
        if not isinstance(receipt, dict):
            raise ValueError("receipts[%d] must be a mapping" % index)
        if _key(receipt.get("receipt_id")) == receipt_id:
            matching_receipt = receipt
            break
    if matching_receipt is None:
        return {
            "assembly_id": _text(consumption["assembly_id"]),
            "receipt_id": _text(consumption["receipt_id"]),
            "stages_reached": tuple(reached),
            "issue": matching_issue,
            "receipt": None,
            "broken_at": "receipt",
            "complete": False,
        }
    reached.append("receipt")
    return {
        "assembly_id": _text(consumption["assembly_id"]),
        "receipt_id": _text(consumption["receipt_id"]),
        "stages_reached": tuple(reached),
        "issue": matching_issue,
        "receipt": matching_receipt,
        "broken_at": None,
        "complete": True,
    }


def chain_granularity(chain):
    """Return the identity granularity a chain actually delivers.

    A chain that does not reach the receipt delivers nothing, however good the
    receipt record would have been. A chain whose issue re-batched the parts
    without a split record cannot carry the batch identity through, so it drops
    to the date code.
    """
    if not isinstance(chain, dict):
        raise ValueError("chain must be a mapping")
    if not chain.get("complete"):
        return "none"
    level = receipt_granularity(chain["receipt"])
    issue = chain.get("issue") or {}
    if _text(issue.get("sub_batch")) is not None and _text(
        issue.get("split_record")
    ) is None:
        if IDENTITY_GRANULARITIES[level] > IDENTITY_GRANULARITIES["date-code"]:
            level = "date-code"
    return level


def reconcile_receipt(receipt, issues, scrapped=0):
    """Return the quantity ledger for one receipt.

    Issued plus scrapped can never exceed what was received; a ledger that says
    otherwise is a record error, not a stock level, and it is raised rather
    than reported as a negative remainder.
    """
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be a mapping")
    if "receipt_id" not in receipt:
        raise ValueError("receipt missing required key 'receipt_id'")
    received = receipt.get("quantity")
    if not isinstance(received, int) or isinstance(received, bool) or received <= 0:
        raise ValueError("receipt['quantity'] must be a positive integer")
    if not isinstance(scrapped, int) or isinstance(scrapped, bool) or scrapped < 0:
        raise ValueError("scrapped must be a non-negative integer")
    if not isinstance(issues, (list, tuple)):
        raise ValueError("issues must be a sequence of issue records")
    receipt_id = _key(receipt["receipt_id"])
    issued = 0
    for index, issue in enumerate(issues):
        if not isinstance(issue, dict):
            raise ValueError("issues[%d] must be a mapping" % index)
        if _key(issue.get("receipt_id")) != receipt_id:
            continue
        quantity = issue.get("quantity")
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 0:
            raise ValueError("issues[%d]['quantity'] must be a non-negative integer" % index)
        issued += quantity
    if issued + scrapped > received:
        raise ValueError(
            "receipt %s issued %d and scrapped %d against %d received"
            % (_text(receipt["receipt_id"]), issued, scrapped, received)
        )
    return {
        "receipt_id": _text(receipt["receipt_id"]),
        "received": received,
        "issued": issued,
        "scrapped": scrapped,
        "remaining": received - issued - scrapped,
        "balanced": True,
    }


def unsourced_consumptions(consumptions, issues):
    """Return the fitted parts no issue ever supplied to their assembly."""
    if not isinstance(consumptions, (list, tuple)):
        raise ValueError("consumptions must be a sequence of consumption records")
    if not isinstance(issues, (list, tuple)):
        raise ValueError("issues must be a sequence of issue records")
    supplied = set()
    for index, issue in enumerate(issues):
        if not isinstance(issue, dict):
            raise ValueError("issues[%d] must be a mapping" % index)
        supplied.add((_key(issue.get("receipt_id")), _key(issue.get("to_assembly"))))
    offenders = []
    for index, consumption in enumerate(consumptions):
        if not isinstance(consumption, dict):
            raise ValueError("consumptions[%d] must be a mapping" % index)
        for key in ("assembly_id", "receipt_id"):
            if key not in consumption:
                raise ValueError(
                    "consumptions[%d] missing required key '%s'" % (index, key)
                )
        pair = (_key(consumption["receipt_id"]), _key(consumption["assembly_id"]))
        if pair not in supplied:
            offenders.append(
                "%s consumed %s with no issue record"
                % (_text(consumption["assembly_id"]), _text(consumption["receipt_id"]))
            )
    return tuple(offenders)


def out_of_order_records(chain, consumption):
    """Return the date-order breaks on one custody chain."""
    if not isinstance(chain, dict):
        raise ValueError("chain must be a mapping")
    if not isinstance(consumption, dict):
        raise ValueError("consumption must be a mapping")
    if not chain.get("complete"):
        return ()
    fitted = consumption.get("fitted_date")
    if fitted is None:
        return ()
    fitted_on = parse_iso_date(fitted, "consumption['fitted_date']")
    breaks = []
    issued = (chain.get("issue") or {}).get("issued_date")
    if issued is not None:
        issued_on = parse_iso_date(issued, "issue['issued_date']")
        if issued_on > fitted_on:
            breaks.append(
                "issue to %s is dated after the part was fitted" % chain["assembly_id"]
            )
    received = (chain.get("receipt") or {}).get("received_date")
    if received is not None:
        received_on = parse_iso_date(received, "receipt['received_date']")
        if received_on > fitted_on:
            breaks.append(
                "receipt %s is dated after the part was fitted" % chain["receipt_id"]
            )
    return tuple(breaks)


def assembly_verdict(achieved, required, complete):
    """Return 'traceable', 'shortfall' or 'broken' for one fitted part."""
    if not isinstance(complete, bool):
        raise ValueError("complete must be a bool, got %r" % (complete,))
    if not complete:
        return "broken"
    return "traceable" if granularity_shortfall(achieved, required) == 0 else "shortfall"


def traceable_share(verdicts):
    """Return the share of fitted parts that are fully traceable."""
    if not isinstance(verdicts, (list, tuple)):
        raise ValueError("verdicts must be a sequence of verdict strings")
    total = 0
    good = 0
    for index, verdict in enumerate(verdicts):
        if verdict not in TRACE_VERDICTS:
            raise ValueError(
                "verdicts[%d] must be one of %s, got %r"
                % (index, list(TRACE_VERDICTS), verdict)
            )
        total += 1
        if verdict == "traceable":
            good += 1
    if total == 0:
        return {"numerator": 0, "denominator": 0, "fraction": 0.0}
    return {"numerator": good, "denominator": total, "fraction": good / total}


def assess_class_3_traceability(receipts, issues, consumptions, usage):
    """Run the full clause 6.5.4 assessment over one programme's records."""
    if not isinstance(receipts, (list, tuple)):
        raise ValueError("receipts must be a sequence of receipt records")
    if not isinstance(issues, (list, tuple)):
        raise ValueError("issues must be a sequence of issue records")
    if not isinstance(consumptions, (list, tuple)):
        raise ValueError("consumptions must be a sequence of consumption records")
    demanded = required_granularity(usage)

    findings = []
    for index, receipt in enumerate(receipts):
        if not isinstance(receipt, dict):
            raise ValueError("receipts[%d] must be a mapping" % index)
        missing = missing_receipt_fields(receipt)
        if missing:
            findings.append(
                "receipt %s is missing %s"
                % (_text(receipt.get("receipt_id")) or "<unnamed>", ", ".join(missing))
            )

    for batch in batch_identifier_conflicts(receipts):
        findings.append(
            "receipt batch %s covers more than one delivery and no longer names "
            "one population" % batch
        )
    for issue_id in unrecorded_splits(issues):
        findings.append(
            "issue %s re-batched parts without a split record, so the batch "
            "identity stops there" % issue_id
        )
    for message in unsourced_consumptions(consumptions, issues):
        findings.append(message)

    results = []
    verdicts = []
    for consumption in consumptions:
        chain = custody_chain(consumption, issues, receipts)
        achieved = chain_granularity(chain)
        verdict = assembly_verdict(achieved, demanded, bool(chain["complete"]))
        for message in out_of_order_records(chain, consumption):
            findings.append(message)
        if verdict == "broken":
            findings.append(
                "the chain behind %s on %s breaks at %s"
                % (chain["receipt_id"], chain["assembly_id"], chain["broken_at"])
            )
        elif verdict == "shortfall":
            findings.append(
                "%s reaches only %s identity on %s where %s is demanded"
                % (
                    chain["assembly_id"],
                    achieved,
                    chain["receipt_id"],
                    demanded,
                )
            )
        verdicts.append(verdict)
        results.append(
            {
                "assembly_id": chain["assembly_id"],
                "receipt_id": chain["receipt_id"],
                "stages_reached": chain["stages_reached"],
                "broken_at": chain["broken_at"],
                "achieved_granularity": achieved,
                "required_granularity": demanded,
                "shortfall_steps": granularity_shortfall(achieved, demanded),
                "verdict": verdict,
            }
        )

    ledgers = []
    for receipt in receipts:
        if not isinstance(receipt.get("quantity"), int) or isinstance(
            receipt.get("quantity"), bool
        ):
            continue
        if receipt.get("quantity", 0) <= 0:
            continue
        ledgers.append(
            reconcile_receipt(receipt, issues, receipt.get("scrapped", 0))
        )

    share = traceable_share(verdicts)
    return {
        "usage": usage,
        "required_granularity": demanded,
        "chains": tuple(results),
        "ledgers": tuple(ledgers),
        "traceable_share": share,
        "findings": findings,
        "traceable": not findings,
    }
