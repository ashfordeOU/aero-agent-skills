#!/usr/bin/env python3
"""User-lot acceptance-testing logic (ECSS-Q-ST-60-05 clause 8.3.3).

Deterministic, offline, stdlib-only helpers that size and grade the
acceptance testing a buyer performs on each delivered batch of dies:

- size the sample and read the acceptance number from the lot-size
  schedule, collapsing to full inspection on a small batch,
- disposition a batch from the nonconforming count found in its sample,
- compute the exact probability that a batch carrying a given defective
  population would still be accepted by that plan,
- reconcile a receiving log so every delivery carries its own record and
  no lot identifier is stretched across two deliveries.

Anchor: ECSS-Q-ST-60-05 clause 8.3.3 (paraphrased procedure only).
"""

import fractions
import math

# Attribute sampling schedule: (largest lot the band covers, sample size,
# acceptance number). The last band is open ended. A sample larger than
# the batch collapses to full inspection.
SAMPLING_SCHEDULE = (
    (8, 8, 0),
    (25, 13, 0),
    (50, 20, 0),
    (150, 32, 1),
    (500, 50, 2),
    (1200, 80, 3),
    (math.inf, 125, 5),
)


def _as_int(value, field):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (field, value))
    return value


def _as_count(value, field):
    number = _as_int(value, field)
    if number < 0:
        raise ValueError("%s must be >= 0, got %r" % (field, value))
    return number


def sampling_plan_for_lot(lot_size):
    """Sample size and acceptance number a delivered batch earns.

    Raises ValueError on a non-integer or empty batch - a delivery of no
    dies has nothing to sample and is a receiving error, not a lot.
    """
    size = _as_int(lot_size, "lot_size")
    if size < 1:
        raise ValueError("lot_size must be >= 1, got %r" % (lot_size,))
    for upper, sample, acceptance in SAMPLING_SCHEDULE:
        if size <= upper:
            effective = min(sample, size)
            return {
                "lot_size": size,
                "sample_size": effective,
                "acceptance_number": acceptance,
                "full_inspection": effective == size,
            }
    raise ValueError("no sampling band covers a lot of %d" % (size,))


def disposition_sample(lot_size, nonconforming_found, sample_size=None):
    """Accept or reject one delivered batch from its sample result.

    sample_size overrides the schedule only to record what was actually
    inspected; it may never be larger than the batch, and the
    nonconforming count may never exceed what was inspected.
    """
    plan = sampling_plan_for_lot(lot_size)
    if sample_size is not None:
        inspected = _as_count(sample_size, "sample_size")
        if inspected < 1:
            raise ValueError("sample_size must be >= 1, got %r" % (sample_size,))
        if inspected > plan["lot_size"]:
            raise ValueError(
                "sample_size %d exceeds the delivered batch of %d"
                % (inspected, plan["lot_size"])
            )
        plan = dict(plan)
        plan["sample_size"] = inspected
        plan["full_inspection"] = inspected == plan["lot_size"]
    found = _as_count(nonconforming_found, "nonconforming_found")
    if found > plan["sample_size"]:
        raise ValueError(
            "nonconforming_found %d exceeds the %d dies inspected"
            % (found, plan["sample_size"])
        )
    short_sample = plan["sample_size"] < min(
        sampling_plan_for_lot(plan["lot_size"])["sample_size"], plan["lot_size"]
    )
    accepted = found <= plan["acceptance_number"] and not short_sample
    result = dict(plan)
    result.update(
        {
            "nonconforming_found": found,
            "short_sample": short_sample,
            "accepted": accepted,
        }
    )
    return result


def acceptance_probability(lot_size, sample_size, nonconforming_in_lot, acceptance_number):
    """Exact probability this plan accepts a batch with that defect count.

    Hypergeometric, summed over the acceptable sample outcomes with
    integer binomials and exact rational arithmetic, so the value is
    identical on every platform.
    """
    size = _as_int(lot_size, "lot_size")
    if size < 1:
        raise ValueError("lot_size must be >= 1, got %r" % (lot_size,))
    inspected = _as_count(sample_size, "sample_size")
    if inspected < 1 or inspected > size:
        raise ValueError(
            "sample_size must be between 1 and the lot size, got %r" % (sample_size,)
        )
    defective = _as_count(nonconforming_in_lot, "nonconforming_in_lot")
    if defective > size:
        raise ValueError(
            "nonconforming_in_lot %d exceeds the lot size %d" % (defective, size)
        )
    acceptance = _as_count(acceptance_number, "acceptance_number")
    total = math.comb(size, inspected)
    favourable = 0
    for found in range(0, min(acceptance, inspected, defective) + 1):
        favourable += math.comb(defective, found) * math.comb(
            size - defective, inspected - found
        )
    return float(fractions.Fraction(favourable, total))


def validate_delivery(record):
    """Normalize one receiving-log entry.

    record keys: delivery_id, lot_id, lot_size, and either a
    nonconforming_found count (with an optional sample_size) or None to
    say the delivery was received without a user-lot test.
    """
    if not isinstance(record, dict):
        raise ValueError("delivery record must be a mapping, got %r" % (record,))
    delivery_id = record.get("delivery_id")
    if not isinstance(delivery_id, str) or not delivery_id.strip():
        raise ValueError(
            "delivery_id must be a non-empty string, got %r" % (delivery_id,)
        )
    lot_id = record.get("lot_id")
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("lot_id must be a non-empty string, got %r" % (lot_id,))
    size = _as_int(record.get("lot_size"), "lot_size")
    if size < 1:
        raise ValueError("lot_size must be >= 1, got %r" % (size,))
    found = record.get("nonconforming_found")
    sample_size = record.get("sample_size")
    if found is not None:
        found = _as_count(found, "nonconforming_found")
    if sample_size is not None:
        sample_size = _as_count(sample_size, "sample_size")
    return {
        "delivery_id": delivery_id.strip(),
        "lot_id": lot_id.strip(),
        "lot_size": size,
        "nonconforming_found": found,
        "sample_size": sample_size,
        "tested": found is not None,
    }


def normalize_receiving_log(records):
    """Validate a receiving log, rejecting a repeated delivery identifier."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("receiving log must be a non-empty list")
    normalized = []
    seen = set()
    for record in records:
        item = validate_delivery(record)
        if item["delivery_id"] in seen:
            raise ValueError(
                "duplicate receiving-log entry for delivery %r"
                % (item["delivery_id"],)
            )
        seen.add(item["delivery_id"])
        normalized.append(item)
    return normalized


def evaluate_delivery(record):
    """Grade one normalized delivery against its own sampling plan."""
    plan = sampling_plan_for_lot(record["lot_size"])
    reasons = []
    if not record["tested"]:
        reasons.append(
            "delivery received with no user-lot test: %d dies owed a sample of %d"
            % (record["lot_size"], plan["sample_size"])
        )
        outcome = dict(plan)
        outcome.update(
            {
                "delivery_id": record["delivery_id"],
                "lot_id": record["lot_id"],
                "nonconforming_found": None,
                "short_sample": True,
                "accepted": False,
                "reasons": reasons,
            }
        )
        return outcome
    outcome = disposition_sample(
        record["lot_size"], record["nonconforming_found"], record["sample_size"]
    )
    outcome["delivery_id"] = record["delivery_id"]
    outcome["lot_id"] = record["lot_id"]
    if outcome["short_sample"]:
        reasons.append(
            "only %d dies inspected, the schedule asks for %d"
            % (outcome["sample_size"], plan["sample_size"])
        )
    if outcome["nonconforming_found"] > outcome["acceptance_number"]:
        reasons.append(
            "%d nonconforming found against an acceptance number of %d"
            % (outcome["nonconforming_found"], outcome["acceptance_number"])
        )
    outcome["reasons"] = reasons
    return outcome


def assess_user_lot_testing(deliveries):
    """Grade a whole clause 8.3.3 receiving log.

    Returns a report dict with per-delivery outcomes, the deliveries that
    carry no test, the lot identifiers reused across deliveries and the
    findings. conforming is True only when findings is empty.
    """
    normalized = normalize_receiving_log(deliveries)
    outcomes = [evaluate_delivery(item) for item in normalized]
    outcomes.sort(key=lambda o: o["delivery_id"])
    findings = []
    untested = sorted(o["delivery_id"] for o in outcomes if o["nonconforming_found"] is None)
    counts = {}
    for item in normalized:
        counts[item["lot_id"]] = counts.get(item["lot_id"], 0) + 1
    reused = sorted(lot for lot, seen in counts.items() if seen > 1)
    for lot in reused:
        findings.append(
            "lot identifier %s appears on %d deliveries: one batch's evidence "
            "cannot cover another" % (lot, counts[lot])
        )
    for outcome in outcomes:
        if outcome["reasons"]:
            findings.append(
                "delivery %s rejected: %s"
                % (outcome["delivery_id"], "; ".join(outcome["reasons"]))
            )
    return {
        "deliveries": len(outcomes),
        "outcomes": outcomes,
        "untested_deliveries": untested,
        "reused_lot_ids": reused,
        "accepted_deliveries": sorted(
            o["delivery_id"] for o in outcomes if o["accepted"] and not o["reasons"]
        ),
        "findings": findings,
        "conforming": not findings,
    }


def format_user_lot_report(report):
    """Render a user-lot assessment as deterministic plain-text lines."""
    lines = [
        "user-lot acceptance testing: %s"
        % ("CONFORMING" if report["conforming"] else "NOT CONFORMING"),
        "deliveries=%d accepted=%d untested=%d reused-lot-ids=%d"
        % (
            report["deliveries"],
            len(report["accepted_deliveries"]),
            len(report["untested_deliveries"]),
            len(report["reused_lot_ids"]),
        ),
    ]
    for item in report["outcomes"]:
        lines.append(
            "  %s lot=%s n=%d sample=%d c=%d found=%s accepted=%s"
            % (
                item["delivery_id"],
                item["lot_id"],
                item["lot_size"],
                item["sample_size"],
                item["acceptance_number"],
                "none" if item["nonconforming_found"] is None
                else "%d" % item["nonconforming_found"],
                "yes" if item["accepted"] else "no",
            )
        )
    for finding in report["findings"]:
        lines.append("  FINDING: %s" % finding)
    return "\n".join(lines)
