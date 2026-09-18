"""Error End of Packet handling for the SpaceWire CCSDS packet transfer protocol.

Anchor: ECSS-E-ST-50-53C clause 5.5.4.4 -- what the receiving entity does with a
transfer that ends in an error terminator. Paraphrased into an implementable
procedure; no standard text is reproduced.

Two normative obligations are implemented:
  (a) the transfer is discarded whole -- an error terminator says the octets
      already taken in are of unknown extent, so no part of the partial CCSDS
      packet is handed up to the user;
  (b) the discard is reported, so the loss is visible to the entity above rather
      than absorbed into a counter nobody reads.

Discarding is cheap and silent by nature, which is why the reporting obligation
carries the weight here: a link that is nominally up while shredding every
transfer looks identical, from above, to a link with no traffic on it.
"""

__all__ = [
    "NORMAL_END",
    "ERROR_END",
    "NO_END",
    "DELIVER",
    "DISCARD",
    "HEALTHY",
    "SPORADIC",
    "BURST_FAULT",
    "HARD_FAULT",
    "normalize_terminator",
    "validate_octet_count",
    "handle_terminated_transfer",
    "scan_sequence",
    "longest_error_run",
    "diagnose_link",
]

NORMAL_END = "eop"
ERROR_END = "eep"
NO_END = "none"

_TERMINATORS = {
    NORMAL_END: NORMAL_END,
    "end-of-packet": NORMAL_END,
    "normal": NORMAL_END,
    ERROR_END: ERROR_END,
    "error-end-of-packet": ERROR_END,
    "error": ERROR_END,
    NO_END: NO_END,
    "unterminated": NO_END,
    "truncated": NO_END,
}

DELIVER = "deliver"
DISCARD = "discard"

HEALTHY = "healthy"
SPORADIC = "sporadic-errors"
BURST_FAULT = "burst-fault"
HARD_FAULT = "hard-fault"

# A run of error terminations at least this long is a fault in progress rather
# than independent upsets landing near each other.
DEFAULT_BURST_THRESHOLD = 3

# Share of a sequence above which the link is not degraded, it is down.
_HARD_FAULT_SHARE = 0.5


def normalize_terminator(token):
    """Return the canonical terminator name, rejecting anything unrecognised."""
    if not isinstance(token, str):
        raise ValueError("terminator must be a string, got %r" % type(token).__name__)
    key = token.strip().lower()
    if key not in _TERMINATORS:
        raise ValueError(
            "unknown terminator %r; expected one of %s"
            % (token, ", ".join(sorted(set(_TERMINATORS.values()))))
        )
    return _TERMINATORS[key]


def validate_octet_count(count, name="octets_received"):
    """Return a non-negative octet count, rejecting anything else."""
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError("%s must be an integer" % name)
    if count < 0:
        raise ValueError("%s must not be negative, got %d" % (name, count))
    return int(count)


def handle_terminated_transfer(terminator, octets_received):
    """Decide the disposition of one transfer from how it ended.

    Only a normal termination delivers. An error termination and an
    unterminated transfer both discard the whole of what arrived, and both
    report, because in each case the extent of the packet is unknown.
    """
    end = normalize_terminator(terminator)
    octets = validate_octet_count(octets_received)
    if end == NORMAL_END:
        return {
            "terminator": end,
            "disposition": DELIVER,
            "octets_delivered": octets,
            "octets_discarded": 0,
            "report": None,
        }
    if end == ERROR_END:
        report = (
            "transfer ended with an error terminator after %d octet(s); the "
            "partial packet is discarded and not delivered" % octets
        )
    else:
        report = (
            "transfer never terminated after %d octet(s); its extent is unknown "
            "and the partial packet is discarded" % octets
        )
    return {
        "terminator": end,
        "disposition": DISCARD,
        "octets_delivered": 0,
        "octets_discarded": octets,
        "report": report,
    }


def _normalized_sequence(terminators):
    if isinstance(terminators, str):
        raise ValueError("terminators must be a sequence of terminator names, not text")
    if not isinstance(terminators, (list, tuple)):
        raise ValueError("terminators must be a list or tuple")
    if not terminators:
        raise ValueError("terminators must not be empty")
    return [normalize_terminator(t) for t in terminators]


def longest_error_run(terminators):
    """Return the length of the longest unbroken run of error terminations."""
    ends = _normalized_sequence(terminators)
    best = 0
    current = 0
    for end in ends:
        if end == ERROR_END:
            current += 1
            if current > best:
                best = current
        else:
            current = 0
    return best


def scan_sequence(terminators):
    """Count dispositions and reports across a received sequence."""
    ends = _normalized_sequence(terminators)
    total = len(ends)
    errors = sum(1 for end in ends if end == ERROR_END)
    unterminated = sum(1 for end in ends if end == NO_END)
    delivered = total - errors - unterminated
    return {
        "total": total,
        "delivered": delivered,
        "error_terminated": errors,
        "unterminated": unterminated,
        "discarded": errors + unterminated,
        "discard_ratio": float(errors + unterminated) / float(total),
        "longest_error_run": longest_error_run(ends),
        "reports": errors + unterminated,
    }


def diagnose_link(terminators, burst_threshold=DEFAULT_BURST_THRESHOLD):
    """Grade a received sequence and name what the pattern points at.

    Independent upsets scatter; a fault in progress clusters. Separating them
    is what turns a discard counter into something an operator can act on.
    """
    if isinstance(burst_threshold, bool) or not isinstance(burst_threshold, int):
        raise ValueError("burst_threshold must be an integer")
    if burst_threshold < 1:
        raise ValueError("burst_threshold must be at least 1, got %d" % burst_threshold)
    scan = scan_sequence(terminators)
    ratio = scan["discard_ratio"]
    if scan["discarded"] == 0:
        verdict = HEALTHY
    elif ratio >= _HARD_FAULT_SHARE:
        verdict = HARD_FAULT
    elif scan["longest_error_run"] >= burst_threshold:
        verdict = BURST_FAULT
    else:
        verdict = SPORADIC
    findings = []
    if scan["discarded"]:
        findings.append(
            "%d of %d transfer(s) discarded without delivery"
            % (scan["discarded"], scan["total"])
        )
    if verdict == BURST_FAULT:
        findings.append(
            "%d consecutive error terminations; the errors are clustered, which "
            "is a fault in progress rather than independent upsets"
            % scan["longest_error_run"]
        )
    elif verdict == HARD_FAULT:
        findings.append(
            "most of the sequence was discarded; the link is carrying signal but "
            "delivering nothing and is down from the user's side"
        )
    result = dict(scan)
    result["verdict"] = verdict
    result["findings"] = findings
    return result
