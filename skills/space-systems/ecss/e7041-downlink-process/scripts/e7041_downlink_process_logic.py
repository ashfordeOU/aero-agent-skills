"""Downlink process for one large message.

Anchor: ECSS-E-ST-70-41C clause 6.13.3.3 (the downlink process of the large
packet transfer service). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the message and part sizes and refuse a message that fits inside a
   single part.
2. Lay the message out as an ordered part run: one first part, the
   intermediate parts, one last part, numbered from one with their offsets.
3. Verify the run independently of the layout step: roles, numbering,
   coverage, part sizes and the short-part rule.
4. Claim the transaction identifier against the open set.
5. Truncate the run and build the abort report when the transfer fails.
6. Assemble the downlink assessment.
"""

__all__ = [
    "FIRST_PART",
    "INTERMEDIATE_PART",
    "LAST_PART",
    "MIN_PARTS",
    "ABORT_REASONS",
    "plan_parts",
    "verify_part_run",
    "report_counts",
    "claim_transaction_identifier",
    "abort_downlink",
    "assess_downlink_process",
]

FIRST_PART = "first"
INTERMEDIATE_PART = "intermediate"
LAST_PART = "last"

# A transfer needs a part to open the reassembly and a part to close it.
MIN_PARTS = 2

# Reasons the subservice is able to name in a downlink abort report.
ABORT_REASONS = (
    "source-data-unavailable",
    "store-read-failure",
    "transfer-cancelled",
    "resource-exhausted",
    "part-generation-failure",
)


def _require_positive_int(value, label):
    """Return value as a positive whole count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def plan_parts(message_octets, part_octets):
    """Return the ordered part run for one large message downlink."""
    message = _require_positive_int(message_octets, "message_octets")
    part = _require_positive_int(part_octets, "part_octets")
    if message <= part:
        raise ValueError(
            "a %d octet message fits inside one %d octet part; it is a plain report, "
            "not a large packet transfer downlink" % (message, part)
        )
    count = -(-message // part)
    run = []
    offset = 0
    for sequence in range(1, count + 1):
        octets = part if sequence < count else message - (count - 1) * part
        if sequence == 1:
            role = FIRST_PART
        elif sequence == count:
            role = LAST_PART
        else:
            role = INTERMEDIATE_PART
        run.append(
            {
                "sequence": sequence,
                "part_type": role,
                "offset": offset,
                "octets": octets,
            }
        )
        offset += octets
    return run


def verify_part_run(run, message_octets, part_octets):
    """Return the findings raised by an independent check of a part run."""
    if not isinstance(run, (list, tuple)) or not run:
        raise ValueError("run must be a non-empty sequence of part records")
    message = _require_positive_int(message_octets, "message_octets")
    part = _require_positive_int(part_octets, "part_octets")
    for index, record in enumerate(run):
        if not isinstance(record, dict):
            raise ValueError("run[%d] must be a mapping" % index)
        for key in ("sequence", "part_type", "offset", "octets"):
            if key not in record:
                raise ValueError("run[%d] missing required key '%s'" % (index, key))

    findings = []
    count = len(run)
    if count < MIN_PARTS:
        findings.append(
            "run holds %d part; a transfer needs at least %d" % (count, MIN_PARTS)
        )

    firsts = [r for r in run if r["part_type"] == FIRST_PART]
    lasts = [r for r in run if r["part_type"] == LAST_PART]
    unknown = [r for r in run if r["part_type"] not in
               (FIRST_PART, INTERMEDIATE_PART, LAST_PART)]
    if unknown:
        findings.append("run carries %d part(s) with an unrecognised role" % len(unknown))
    if len(firsts) != 1:
        findings.append("run holds %d first parts; exactly one is expected" % len(firsts))
    elif firsts[0]["sequence"] != 1:
        findings.append(
            "first part carries sequence %d; numbering starts at one"
            % firsts[0]["sequence"]
        )
    if len(lasts) != 1:
        findings.append("run holds %d last parts; exactly one is expected" % len(lasts))
    elif lasts[0]["sequence"] != count:
        findings.append(
            "last part carries sequence %d in a run of %d parts"
            % (lasts[0]["sequence"], count)
        )

    expected_sequence = 1
    expected_offset = 0
    total = 0
    for record in run:
        if record["sequence"] != expected_sequence:
            findings.append(
                "sequence %r breaks the numbering; %d was expected"
                % (record["sequence"], expected_sequence)
            )
        if record["offset"] != expected_offset:
            findings.append(
                "part %r starts at offset %d; %d was expected"
                % (record["sequence"], record["offset"], expected_offset)
            )
        octets = record["octets"]
        if not isinstance(octets, int) or isinstance(octets, bool) or octets <= 0:
            findings.append("part %r carries a non-positive octet count" % record["sequence"])
            octets = 0
        elif octets > part:
            findings.append(
                "part %r carries %d octets, above the %d octet part size"
                % (record["sequence"], octets, part)
            )
        elif octets < part and record["part_type"] != LAST_PART:
            findings.append(
                "part %r is short at %d octets but is not the last part"
                % (record["sequence"], octets)
            )
        total += octets
        expected_sequence += 1
        expected_offset += octets

    if total != message:
        findings.append(
            "part run covers %d octets of a %d octet message" % (total, message)
        )
    return findings


def report_counts(run):
    """Return how many reports of each part role the run emits."""
    if not isinstance(run, (list, tuple)):
        raise ValueError("run must be a sequence of part records")
    counts = {FIRST_PART: 0, INTERMEDIATE_PART: 0, LAST_PART: 0}
    for record in run:
        role = record.get("part_type")
        if role not in counts:
            raise ValueError("unrecognised part role %r" % (role,))
        counts[role] += 1
    return counts


def claim_transaction_identifier(open_identifiers, transaction_id):
    """Return the open identifier set with this transaction added."""
    if not isinstance(open_identifiers, (list, tuple, set, frozenset)):
        raise ValueError("open_identifiers must be a collection")
    if transaction_id is None:
        raise ValueError("transaction_id must be given")
    claimed = set(open_identifiers)
    if transaction_id in claimed:
        raise ValueError(
            "transaction identifier %r is still open; reusing it would merge two "
            "messages at the receiver" % (transaction_id,)
        )
    claimed.add(transaction_id)
    return claimed


def abort_downlink(run, transaction_id, failed_sequence, reason):
    """Return the parts actually sent and the abort report for a failed run."""
    if not isinstance(run, (list, tuple)) or not run:
        raise ValueError("run must be a non-empty sequence of part records")
    sequence = _require_positive_int(failed_sequence, "failed_sequence")
    if sequence > len(run):
        raise ValueError(
            "failed_sequence %d is past the %d parts of the run" % (sequence, len(run))
        )
    if reason not in ABORT_REASONS:
        raise ValueError(
            "abort reason %r is not one of the recognised reasons %s"
            % (reason, ", ".join(ABORT_REASONS))
        )
    sent = [r for r in run if r["sequence"] < sequence]
    return {
        "parts_sent": sent,
        "octets_sent": sum(r["octets"] for r in sent),
        "abort_report": {
            "transaction_id": transaction_id,
            "failed_sequence": sequence,
            "reason": reason,
        },
    }


def assess_downlink_process(spec):
    """Assess a clause 6.13.3.3 downlink of one large message.

    spec keys: message_octets, part_octets, transaction_id, optional
    open_identifiers, optional failure {sequence, reason}.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("message_octets", "part_octets", "transaction_id"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    run = plan_parts(spec["message_octets"], spec["part_octets"])
    findings = verify_part_run(run, spec["message_octets"], spec["part_octets"])
    open_ids = claim_transaction_identifier(
        spec.get("open_identifiers", ()), spec["transaction_id"]
    )

    failure = spec.get("failure")
    aborted = None
    if failure is not None:
        if not isinstance(failure, dict):
            raise ValueError("spec['failure'] must be a mapping")
        for key in ("sequence", "reason"):
            if key not in failure:
                raise ValueError("spec['failure'] missing required key '%s'" % key)
        aborted = abort_downlink(
            run, spec["transaction_id"], failure["sequence"], failure["reason"]
        )
        findings.append(
            "transfer aborted at part %d of %d: %s"
            % (failure["sequence"], len(run), failure["reason"])
        )

    return {
        "part_run": run,
        "part_count": len(run),
        "report_counts": report_counts(run),
        "open_identifiers": open_ids,
        "aborted": aborted,
        "completed": aborted is None and not findings,
        "findings": findings,
    }
