"""Stock rotation and lot separation for limited-shelf-life materials.

Anchor: ECSS-Q-ST-70-22 stock-control clause -- limited-shelf-life stock is
issued in rotation and lots are kept separated so the wrong lot cannot be
picked. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate each stock record: identity, material, lot number, receipt and
   expiry dates, storage bin, availability state.
2. Order the issuable stock of a material under the declared rotation policy --
   first-in-first-out on receipt date, or first-expiry-first-out -- with a
   deterministic tie-break so two reviewers get the same sequence.
3. Report where the two orders disagree. A lot received later but expiring
   sooner is exactly the case a receipt-ordered queue strands until it expires.
4. Grade lot separation per bin: mixed materials, commingled lot numbers with
   no divider, and quarantined stock sitting alongside issuable stock.
5. Grade actual picks against the sequence, naming every older lot that was
   passed over, and close with a rotation compliance rate and a disposition.
"""

from datetime import date

__all__ = [
    "POLICIES",
    "AVAILABILITY_STATES",
    "validate_lot",
    "validate_stock",
    "sort_key",
    "issue_sequence",
    "next_issue",
    "policy_conflicts",
    "separation_findings",
    "evaluate_pick",
    "assess_stock_rotation",
]

POLICIES = ("fifo", "fefo")
AVAILABILITY_STATES = ("available", "quarantined", "issued")


def _as_date(value, label):
    """Return an ISO date string or date object as a date, or raise."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string or a date, got %r" % (label, value))
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not a valid ISO date: %r" % (label, value))


def validate_lot(record):
    """Return a normalised stock-lot record."""
    if not isinstance(record, dict):
        raise ValueError("stock record must be a mapping")
    for key in ("id", "material", "lot_number", "bin"):
        value = record.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("stock record needs a non-empty '%s'" % key)
    received = _as_date(record.get("received"), "received")
    expiry = _as_date(record.get("expiry"), "expiry")
    if expiry < received:
        raise ValueError(
            "lot %s expires %s, before it was received %s"
            % (record["id"], expiry.isoformat(), received.isoformat())
        )
    state = record.get("availability", "available")
    if state not in AVAILABILITY_STATES:
        raise ValueError(
            "availability must be one of %s, got %r" % (", ".join(AVAILABILITY_STATES), state)
        )
    quantity = record.get("quantity", 1)
    if not isinstance(quantity, int) or isinstance(quantity, bool):
        raise ValueError("quantity must be an integer, got %r" % (quantity,))
    if quantity < 0:
        raise ValueError("quantity must be non-negative, got %d" % quantity)
    divided = record.get("divided", False)
    if not isinstance(divided, bool):
        raise ValueError("divided must be true or false, got %r" % (divided,))
    return {
        "id": record["id"].strip(),
        "material": record["material"].strip(),
        "lot_number": record["lot_number"].strip(),
        "bin": record["bin"].strip(),
        "received": received,
        "expiry": expiry,
        "availability": state,
        "quantity": quantity,
        "divided": divided,
    }


def validate_stock(records):
    """Return the normalised stock list, rejecting duplicate ids."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("stock must be a non-empty sequence of records")
    seen = set()
    out = []
    for item in records:
        lot = validate_lot(item)
        if lot["id"] in seen:
            raise ValueError("duplicate stock id %r" % lot["id"])
        seen.add(lot["id"])
        out.append(lot)
    return out


def sort_key(lot, policy="fifo"):
    """Return the ordering key of one lot under a rotation policy."""
    if policy not in POLICIES:
        raise ValueError("policy must be one of %s, got %r" % (", ".join(POLICIES), policy))
    norm = lot if isinstance(lot, dict) and isinstance(lot.get("received"), date) \
        else validate_lot(lot)
    if policy == "fifo":
        return (norm["received"], norm["expiry"], norm["lot_number"], norm["id"])
    return (norm["expiry"], norm["received"], norm["lot_number"], norm["id"])


def issue_sequence(stock, material=None, policy="fifo"):
    """Return the issue order of the issuable stock, optionally for one material."""
    lots = validate_stock(stock)
    if material is not None and (not isinstance(material, str) or not material.strip()):
        raise ValueError("material filter must be a non-empty string when given")
    pool = [lot for lot in lots
            if lot["availability"] == "available" and lot["quantity"] > 0
            and (material is None or lot["material"] == material.strip())]
    pool.sort(key=lambda lot: sort_key(lot, policy))
    return [lot["id"] for lot in pool]


def next_issue(stock, material, policy="fifo"):
    """Return the id of the lot that rotation says to issue next, or None."""
    sequence = issue_sequence(stock, material, policy)
    return sequence[0] if sequence else None


def policy_conflicts(stock):
    """Return the lots where receipt order and expiry order disagree."""
    lots = validate_stock(stock)
    conflicts = []
    by_material = {}
    for lot in lots:
        if lot["availability"] != "available" or lot["quantity"] <= 0:
            continue
        by_material.setdefault(lot["material"], []).append(lot)
    for material in sorted(by_material):
        pool = by_material[material]
        fifo = sorted(pool, key=lambda lot: sort_key(lot, "fifo"))
        fefo = sorted(pool, key=lambda lot: sort_key(lot, "fefo"))
        if [lot["id"] for lot in fifo] == [lot["id"] for lot in fefo]:
            continue
        head_fifo = fifo[0]
        head_fefo = fefo[0]
        if head_fifo["id"] != head_fefo["id"]:
            conflicts.append({
                "material": material,
                "fifo_head": head_fifo["id"],
                "fefo_head": head_fefo["id"],
                "detail": "lot %s was received later but expires %s, before lot %s expires %s"
                          % (head_fefo["id"], head_fefo["expiry"].isoformat(),
                             head_fifo["id"], head_fifo["expiry"].isoformat()),
            })
    return conflicts


def separation_findings(stock):
    """Return the lot-separation findings, one per offending bin."""
    lots = validate_stock(stock)
    bins = {}
    for lot in lots:
        bins.setdefault(lot["bin"], []).append(lot)
    findings = []
    for name in sorted(bins):
        held = bins[name]
        materials = sorted({lot["material"] for lot in held})
        if len(materials) > 1:
            findings.append({
                "bin": name,
                "kind": "mixed-material-bin",
                "detail": "bin holds %s" % ", ".join(materials),
            })
        for material in materials:
            same = [lot for lot in held if lot["material"] == material]
            numbers = sorted({lot["lot_number"] for lot in same})
            if len(numbers) > 1 and not all(lot["divided"] for lot in same):
                findings.append({
                    "bin": name,
                    "kind": "commingled-lots",
                    "detail": "bin holds lot numbers %s of %s with no divider"
                              % (", ".join(numbers), material),
                })
        states = {lot["availability"] for lot in held}
        if "quarantined" in states and "available" in states:
            findings.append({
                "bin": name,
                "kind": "quarantine-not-segregated",
                "detail": "bin holds quarantined and issuable stock together",
            })
    return findings


def evaluate_pick(stock, picked_id, policy="fifo"):
    """Grade one pick against the rotation sequence for its material."""
    lots = validate_stock(stock)
    if not isinstance(picked_id, str) or not picked_id.strip():
        raise ValueError("picked_id must be a non-empty string")
    target = None
    for lot in lots:
        if lot["id"] == picked_id.strip():
            target = lot
            break
    if target is None:
        raise ValueError("picked_id %r is not in the stock list" % picked_id)
    if target["availability"] != "available" or target["quantity"] <= 0:
        return {
            "picked_id": target["id"],
            "material": target["material"],
            "compliant": False,
            "passed_over": [],
            "detail": "lot %s is not issuable (%s, quantity %d)"
                      % (target["id"], target["availability"], target["quantity"]),
        }
    sequence = issue_sequence(lots, target["material"], policy)
    position = sequence.index(target["id"])
    passed_over = sequence[:position]
    return {
        "picked_id": target["id"],
        "material": target["material"],
        "compliant": position == 0,
        "passed_over": passed_over,
        "detail": "in rotation" if position == 0 else
                  "out of rotation: %d older lot(s) available" % len(passed_over),
    }


def assess_stock_rotation(stock, picks=None, policy="fifo"):
    """Grade a stock holding for rotation order and lot separation."""
    lots = validate_stock(stock)
    if policy not in POLICIES:
        raise ValueError("policy must be one of %s, got %r" % (", ".join(POLICIES), policy))
    if picks is None:
        picks = []
    if not isinstance(picks, (list, tuple)):
        raise ValueError("picks must be a sequence of lot ids")
    pick_reports = [evaluate_pick(lots, pick, policy) for pick in picks]
    separation = separation_findings(lots)
    conflicts = policy_conflicts(lots)
    out_of_rotation = [report["picked_id"] for report in pick_reports
                       if not report["compliant"]]
    rate = 1.0 if not pick_reports else \
        (len(pick_reports) - len(out_of_rotation)) / float(len(pick_reports))
    if out_of_rotation or separation:
        disposition = "stock-control-non-compliant"
    elif conflicts:
        disposition = "compliant-with-rotation-conflict"
    else:
        disposition = "stock-control-compliant"
    return {
        "policy": policy,
        "sequence": issue_sequence(lots, None, policy),
        "picks": pick_reports,
        "out_of_rotation_ids": out_of_rotation,
        "separation_findings": separation,
        "policy_conflicts": conflicts,
        "rotation_compliance_rate": rate,
        "disposition": disposition,
        "compliant": disposition == "stock-control-compliant",
    }
