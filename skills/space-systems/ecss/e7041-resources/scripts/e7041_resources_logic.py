"""Resource sizing for the downlink of large messages.

Anchor: ECSS-E-ST-70-41C clause 6.13.3.2 (resources the downlink of large
messages reserves). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate the declared resources: transaction slots, buffer pool, part size.
2. Validate each demand entry and round its message size up to whole parts to
   obtain the octets the transaction reserves while it is in progress.
3. Sweep the transaction windows as an ordered event list to find the peak
   number of simultaneous transactions and the peak reserved octets, with a
   release taking effect before an admission at the same instant.
4. Replay the demand in arrival order against the declared resources, naming
   the resource that was exhausted for every refusal.
5. Assemble the verdict and its findings.
"""

__all__ = [
    "reserved_octets",
    "validate_resources",
    "validate_demand",
    "peak_simultaneous",
    "admit_in_arrival_order",
    "assess_downlink_resources",
]


def _require_positive_int(value, label):
    """Return value as a positive whole count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _require_real(value, label):
    """Return value as a finite real instant."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite" % label)
    return value


def reserved_octets(message_octets, part_octets):
    """Return the octets a transaction reserves, rounded up to whole parts."""
    message = _require_positive_int(message_octets, "message_octets")
    part = _require_positive_int(part_octets, "part_octets")
    return -(-message // part) * part


def validate_resources(spec):
    """Return the validated (slots, buffer_octets, part_octets) declaration."""
    if not isinstance(spec, dict):
        raise ValueError("resource declaration must be a mapping")
    for key in ("transaction_slots", "buffer_pool_octets", "part_octets"):
        if key not in spec:
            raise ValueError("resource declaration missing required key '%s'" % key)
    slots = _require_positive_int(spec["transaction_slots"], "transaction_slots")
    pool = _require_positive_int(spec["buffer_pool_octets"], "buffer_pool_octets")
    part = _require_positive_int(spec["part_octets"], "part_octets")
    return (slots, pool, part)


def validate_demand(demand, part_octets):
    """Return the demand as records carrying their part-rounded footprint."""
    if not isinstance(demand, (list, tuple)):
        raise ValueError("demand must be a sequence of transaction records")
    records = []
    for index, item in enumerate(demand):
        if not isinstance(item, dict):
            raise ValueError("demand[%d] must be a mapping" % index)
        for key in ("transaction_id", "message_octets", "start", "end"):
            if key not in item:
                raise ValueError("demand[%d] missing required key '%s'" % (index, key))
        start = _require_real(item["start"], "demand[%d]['start']" % index)
        end = _require_real(item["end"], "demand[%d]['end']" % index)
        if end < start:
            raise ValueError(
                "demand[%d] ends at %g before it starts at %g" % (index, end, start)
            )
        octets = reserved_octets(item["message_octets"], part_octets)
        records.append(
            {
                "transaction_id": item["transaction_id"],
                "message_octets": int(item["message_octets"]),
                "reserved_octets": octets,
                "start": start,
                "end": end,
            }
        )
    return records


def peak_simultaneous(records):
    """Return the peak simultaneous transaction count and reserved octets."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence")
    events = []
    for record in records:
        # A release at an instant is applied before an admission at the same
        # instant, so the ordering key puts -1 (release) ahead of +1 (admit).
        events.append((record["end"], -1, record["reserved_octets"]))
        events.append((record["start"], 1, record["reserved_octets"]))
    events.sort(key=lambda e: (e[0], e[1]))
    count = 0
    octets = 0
    peak_count = 0
    peak_octets = 0
    peak_count_at = None
    peak_octets_at = None
    for instant, delta, size in events:
        count += delta
        octets += delta * size
        if count > peak_count:
            peak_count = count
            peak_count_at = instant
        if octets > peak_octets:
            peak_octets = octets
            peak_octets_at = instant
    return {
        "peak_transactions": peak_count,
        "peak_transactions_at": peak_count_at,
        "peak_reserved_octets": peak_octets,
        "peak_reserved_octets_at": peak_octets_at,
    }


def admit_in_arrival_order(records, transaction_slots, buffer_pool_octets):
    """Return an admission decision per transaction, in arrival order."""
    slots = _require_positive_int(transaction_slots, "transaction_slots")
    pool = _require_positive_int(buffer_pool_octets, "buffer_pool_octets")
    ordered = sorted(records, key=lambda r: r["start"])
    active = []
    decisions = []
    for record in ordered:
        active = [a for a in active if a["end"] > record["start"]]
        used_octets = sum(a["reserved_octets"] for a in active)
        if len(active) >= slots:
            reason = "no free transaction slot"
        elif used_octets + record["reserved_octets"] > pool:
            reason = "buffer pool exhausted"
        else:
            reason = None
        if reason is None:
            active.append(record)
        decisions.append(
            {
                "transaction_id": record["transaction_id"],
                "reserved_octets": record["reserved_octets"],
                "admitted": reason is None,
                "refused_because": reason,
            }
        )
    return decisions


def assess_downlink_resources(spec):
    """Assess a clause 6.13.3.2 downlink resource declaration against a demand.

    spec keys: transaction_slots, buffer_pool_octets, part_octets, demand.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "demand" not in spec:
        raise ValueError("spec missing required key 'demand'")
    slots, pool, part = validate_resources(spec)
    records = validate_demand(spec["demand"], part)
    peaks = peak_simultaneous(records)
    decisions = admit_in_arrival_order(records, slots, pool)

    findings = []
    if peaks["peak_transactions"] > slots:
        findings.append(
            "peak of %d simultaneous transactions exceeds the %d declared slots"
            % (peaks["peak_transactions"], slots)
        )
    if peaks["peak_reserved_octets"] > pool:
        findings.append(
            "peak reservation of %d octets exceeds the %d octet buffer pool"
            % (peaks["peak_reserved_octets"], pool)
        )
    for record in records:
        if record["reserved_octets"] > pool:
            findings.append(
                "transaction %r reserves %d octets, more than the whole %d octet pool"
                % (record["transaction_id"], record["reserved_octets"], pool)
            )
    refused = [d["transaction_id"] for d in decisions if not d["admitted"]]

    return {
        "transaction_slots": slots,
        "buffer_pool_octets": pool,
        "part_octets": part,
        "records": records,
        "peak_transactions": peaks["peak_transactions"],
        "peak_transactions_at": peaks["peak_transactions_at"],
        "peak_reserved_octets": peaks["peak_reserved_octets"],
        "peak_reserved_octets_at": peaks["peak_reserved_octets_at"],
        "decisions": decisions,
        "refused": refused,
        "sufficient": not findings and not refused,
        "findings": findings,
    }
