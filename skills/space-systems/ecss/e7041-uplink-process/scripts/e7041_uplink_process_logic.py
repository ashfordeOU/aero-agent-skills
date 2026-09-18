"""Uplink process for a large message received on board.

Anchor: ECSS-E-ST-70-41C clause 6.13.4.3 (the uplink process of the large
packet transfer service). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the receiver configuration and every uplink part record.
2. Walk the part stream, holding at most one open reception per transaction.
3. Apply the acceptance rules: part role against reception state, part number
   against the expected one, octet count against the part size and the
   short-part rule, running total against the reception buffer, arrival time
   against the inter-part timeout.
4. Complete a reception on a valid last part; abort it with a named reason on
   any violation.
5. Abort every reception still open when the stream ends.
"""

__all__ = [
    "FIRST_PART",
    "INTERMEDIATE_PART",
    "LAST_PART",
    "PART_ROLES",
    "ABORT_UNEXPECTED_PART",
    "ABORT_DUPLICATE_FIRST_PART",
    "ABORT_DUPLICATE_PART",
    "ABORT_SEQUENCE_GAP",
    "ABORT_SHORT_PART",
    "ABORT_OVERSIZED_PART",
    "ABORT_BUFFER_OVERFLOW",
    "ABORT_INTER_PART_TIMEOUT",
    "ABORT_INCOMPLETE_AT_END_OF_STREAM",
    "validate_receiver",
    "validate_part_stream",
    "reassemble",
    "assess_uplink_process",
]

FIRST_PART = "first"
INTERMEDIATE_PART = "intermediate"
LAST_PART = "last"
PART_ROLES = (FIRST_PART, INTERMEDIATE_PART, LAST_PART)

ABORT_UNEXPECTED_PART = "unexpected-part-with-no-open-reception"
ABORT_DUPLICATE_FIRST_PART = "first-part-for-an-open-reception"
ABORT_DUPLICATE_PART = "repeated-part-number"
ABORT_SEQUENCE_GAP = "part-number-gap"
ABORT_SHORT_PART = "short-part-before-the-last"
ABORT_OVERSIZED_PART = "part-above-the-part-size"
ABORT_BUFFER_OVERFLOW = "reception-buffer-overflow"
ABORT_INTER_PART_TIMEOUT = "inter-part-timeout"
ABORT_INCOMPLETE_AT_END_OF_STREAM = "incomplete-at-end-of-stream"


def _require_positive_int(value, label):
    """Return value as a positive whole count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _require_positive_real(value, label):
    """Return value as a positive finite duration or instant."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite" % label)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, value))
    return value


def validate_receiver(config):
    """Return the validated (part_octets, buffer_octets, timeout) receiver."""
    if not isinstance(config, dict):
        raise ValueError("receiver configuration must be a mapping")
    for key in ("part_octets", "reception_buffer_octets"):
        if key not in config:
            raise ValueError("receiver configuration missing required key '%s'" % key)
    part = _require_positive_int(config["part_octets"], "part_octets")
    buffer_octets = _require_positive_int(
        config["reception_buffer_octets"], "reception_buffer_octets"
    )
    timeout = config.get("inter_part_timeout_s")
    if timeout is not None:
        timeout = _require_positive_real(timeout, "inter_part_timeout_s")
    return (part, buffer_octets, timeout)


def validate_part_stream(parts):
    """Return the part stream after validating shape, values and time order."""
    if not isinstance(parts, (list, tuple)):
        raise ValueError("parts must be a sequence of uplink part records")
    validated = []
    previous_time = None
    for index, item in enumerate(parts):
        if not isinstance(item, dict):
            raise ValueError("parts[%d] must be a mapping" % index)
        for key in ("transaction_id", "part_type", "sequence", "octets", "time_s"):
            if key not in item:
                raise ValueError("parts[%d] missing required key '%s'" % (index, key))
        if item["part_type"] not in PART_ROLES:
            raise ValueError(
                "parts[%d] carries part role %r, not one of %s"
                % (index, item["part_type"], ", ".join(PART_ROLES))
            )
        sequence = _require_positive_int(item["sequence"], "parts[%d]['sequence']" % index)
        octets = _require_positive_int(item["octets"], "parts[%d]['octets']" % index)
        time_s = item["time_s"]
        if not isinstance(time_s, (int, float)) or isinstance(time_s, bool):
            raise ValueError("parts[%d]['time_s'] must be a real number" % index)
        time_s = float(time_s)
        if time_s != time_s or time_s in (float("inf"), float("-inf")):
            raise ValueError("parts[%d]['time_s'] must be finite" % index)
        if previous_time is not None and time_s < previous_time:
            raise ValueError(
                "parts[%d] arrives at %g, before the previous part at %g"
                % (index, time_s, previous_time)
            )
        previous_time = time_s
        validated.append(
            {
                "transaction_id": item["transaction_id"],
                "part_type": item["part_type"],
                "sequence": sequence,
                "octets": octets,
                "time_s": time_s,
            }
        )
    return validated


def _abort(receptions, outcomes, transaction_id, reason, sequence):
    """Close an open reception with a named abort reason."""
    open_reception = receptions.pop(transaction_id, None)
    accepted = open_reception["parts_accepted"] if open_reception else 0
    outcomes.append(
        {
            "transaction_id": transaction_id,
            "status": "aborted",
            "reason": reason,
            "failed_sequence": sequence,
            "octets": 0,
            "parts_accepted": accepted,
        }
    )


def reassemble(parts, config):
    """Return one outcome record per uplink transaction seen in the stream."""
    part_octets, buffer_octets, timeout = validate_receiver(config)
    stream = validate_part_stream(parts)
    receptions = {}
    outcomes = []

    for part in stream:
        tid = part["transaction_id"]
        role = part["part_type"]
        open_reception = receptions.get(tid)

        if open_reception is None:
            if role != FIRST_PART:
                outcomes.append(
                    {
                        "transaction_id": tid,
                        "status": "aborted",
                        "reason": ABORT_UNEXPECTED_PART,
                        "failed_sequence": part["sequence"],
                        "octets": 0,
                        "parts_accepted": 0,
                    }
                )
                continue
            if part["sequence"] != 1:
                outcomes.append(
                    {
                        "transaction_id": tid,
                        "status": "aborted",
                        "reason": ABORT_SEQUENCE_GAP,
                        "failed_sequence": part["sequence"],
                        "octets": 0,
                        "parts_accepted": 0,
                    }
                )
                continue
            if part["octets"] > part_octets:
                outcomes.append(
                    {
                        "transaction_id": tid,
                        "status": "aborted",
                        "reason": ABORT_OVERSIZED_PART,
                        "failed_sequence": part["sequence"],
                        "octets": 0,
                        "parts_accepted": 0,
                    }
                )
                continue
            if part["octets"] < part_octets:
                outcomes.append(
                    {
                        "transaction_id": tid,
                        "status": "aborted",
                        "reason": ABORT_SHORT_PART,
                        "failed_sequence": part["sequence"],
                        "octets": 0,
                        "parts_accepted": 0,
                    }
                )
                continue
            if part["octets"] > buffer_octets:
                outcomes.append(
                    {
                        "transaction_id": tid,
                        "status": "aborted",
                        "reason": ABORT_BUFFER_OVERFLOW,
                        "failed_sequence": part["sequence"],
                        "octets": 0,
                        "parts_accepted": 0,
                    }
                )
                continue
            receptions[tid] = {
                "expected_sequence": 2,
                "octets": part["octets"],
                "parts_accepted": 1,
                "last_time_s": part["time_s"],
            }
            continue

        if role == FIRST_PART:
            _abort(receptions, outcomes, tid, ABORT_DUPLICATE_FIRST_PART, part["sequence"])
            continue
        if timeout is not None and part["time_s"] - open_reception["last_time_s"] > timeout:
            _abort(receptions, outcomes, tid, ABORT_INTER_PART_TIMEOUT, part["sequence"])
            continue
        if part["sequence"] < open_reception["expected_sequence"]:
            _abort(receptions, outcomes, tid, ABORT_DUPLICATE_PART, part["sequence"])
            continue
        if part["sequence"] > open_reception["expected_sequence"]:
            _abort(receptions, outcomes, tid, ABORT_SEQUENCE_GAP, part["sequence"])
            continue
        if part["octets"] > part_octets:
            _abort(receptions, outcomes, tid, ABORT_OVERSIZED_PART, part["sequence"])
            continue
        if role == INTERMEDIATE_PART and part["octets"] < part_octets:
            _abort(receptions, outcomes, tid, ABORT_SHORT_PART, part["sequence"])
            continue
        if open_reception["octets"] + part["octets"] > buffer_octets:
            _abort(receptions, outcomes, tid, ABORT_BUFFER_OVERFLOW, part["sequence"])
            continue

        open_reception["octets"] += part["octets"]
        open_reception["parts_accepted"] += 1
        open_reception["expected_sequence"] += 1
        open_reception["last_time_s"] = part["time_s"]

        if role == LAST_PART:
            receptions.pop(tid)
            outcomes.append(
                {
                    "transaction_id": tid,
                    "status": "complete",
                    "reason": None,
                    "failed_sequence": None,
                    "octets": open_reception["octets"],
                    "parts_accepted": open_reception["parts_accepted"],
                }
            )

    for tid in sorted(receptions, key=repr):
        open_reception = receptions[tid]
        outcomes.append(
            {
                "transaction_id": tid,
                "status": "aborted",
                "reason": ABORT_INCOMPLETE_AT_END_OF_STREAM,
                "failed_sequence": open_reception["expected_sequence"] - 1,
                "octets": 0,
                "parts_accepted": open_reception["parts_accepted"],
            }
        )
    return outcomes


def assess_uplink_process(spec):
    """Assess a clause 6.13.4.3 uplink part stream against a receiver.

    spec keys: part_octets, reception_buffer_octets, optional
    inter_part_timeout_s, parts.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "parts" not in spec:
        raise ValueError("spec missing required key 'parts'")
    outcomes = reassemble(spec["parts"], spec)
    completed = [o for o in outcomes if o["status"] == "complete"]
    aborted = [o for o in outcomes if o["status"] == "aborted"]
    findings = [
        "transaction %r aborted at part %r: %s"
        % (o["transaction_id"], o["failed_sequence"], o["reason"])
        for o in aborted
    ]
    return {
        "outcomes": outcomes,
        "completed": completed,
        "aborted": aborted,
        "octets_reassembled": sum(o["octets"] for o in completed),
        "clean": not aborted and bool(completed),
        "findings": findings,
    }
