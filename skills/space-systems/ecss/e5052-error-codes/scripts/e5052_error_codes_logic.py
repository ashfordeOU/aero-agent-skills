"""Status and error code handling for SpaceWire RMAP transactions.

Anchor: ECSS-E-ST-50-52C clause 5.6 (error codes). Paraphrased into an
implementable procedure; the registry below carries our own short slugs and
our own wording, and no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold a registry of the status values a reply can carry: a short slug, the
   fault family it belongs to, and whether the condition still leaves a
   working path for a reply to travel back on.
2. Decide, from the set of conditions a target observed while receiving a
   command, which single status it reports -- detection has a precedence, and
   the first condition on that order is the one the reply carries.
3. Decide whether a reply is sent at all: a command whose header cannot be
   trusted, or one that never asked for a reply, produces none.
4. Check a reply for self-consistency: a non-zero status carries no returned
   data, and a value outside the registry is reserved rather than free.
5. Summarise a run of transactions by fault family so a campaign can be read
   without going through every record.
"""

__all__ = [
    "STATUS_SUCCESS",
    "FAMILY_SUCCESS",
    "FAMILY_ROUTING",
    "FAMILY_AUTHORISATION",
    "FAMILY_COMMAND",
    "FAMILY_DATA",
    "FAMILY_RESERVED",
    "FAMILIES",
    "STATUS_REGISTRY",
    "DETECTION_ORDER",
    "SILENT_CONDITION",
    "known_status_codes",
    "status_slug",
    "status_family",
    "is_reserved_status",
    "is_success",
    "validate_observation",
    "detect_status",
    "reply_is_sent",
    "check_reply_consistency",
    "grade_transaction",
    "summarise_transactions",
]

STATUS_SUCCESS = 0

FAMILY_SUCCESS = "success"
FAMILY_ROUTING = "routing-fault"
FAMILY_AUTHORISATION = "authorisation-fault"
FAMILY_COMMAND = "command-fault"
FAMILY_DATA = "data-fault"
FAMILY_RESERVED = "reserved"
FAMILIES = (
    FAMILY_SUCCESS,
    FAMILY_ROUTING,
    FAMILY_AUTHORISATION,
    FAMILY_COMMAND,
    FAMILY_DATA,
    FAMILY_RESERVED,
)

# Our own slugs and our own one-line paraphrases of each reported outcome.
STATUS_REGISTRY = {
    0: ("command-completed", FAMILY_SUCCESS,
        "the command was carried out and any requested data is returned"),
    1: ("unspecified-failure", FAMILY_COMMAND,
        "the command failed for a reason the target cannot place more precisely"),
    2: ("unused-command-code", FAMILY_COMMAND,
        "the option-bit combination is not one of the defined commands"),
    3: ("rejected-destination-key", FAMILY_AUTHORISATION,
        "the key carried by the command is not the one this target accepts"),
    4: ("data-check-value-mismatch", FAMILY_DATA,
        "the payload check value does not agree with the payload received"),
    5: ("payload-shorter-than-declared", FAMILY_DATA,
        "the packet ended before the declared number of payload bytes arrived"),
    6: ("payload-longer-than-declared", FAMILY_DATA,
        "more payload bytes arrived than the declared length allowed for"),
    7: ("packet-terminated-in-error", FAMILY_DATA,
        "the packet was closed with an error marker by the network"),
    8: ("reserved-eight", FAMILY_RESERVED,
        "value kept aside; a target must not report it"),
    9: ("verify-buffer-overrun", FAMILY_COMMAND,
        "a verified write asked for more bytes than the verify buffer holds"),
    10: ("command-not-available", FAMILY_AUTHORISATION,
         "the command is not implemented here, or not permitted on this target"),
    11: ("read-modify-write-length-invalid", FAMILY_COMMAND,
         "the read-modify-write data field is not an operand and mask of equal width"),
    12: ("unknown-target-address", FAMILY_ROUTING,
         "the logical address in the command does not belong to this target"),
}

# Condition tokens in the order a target settles on one of them. The first
# condition present is the one reported; later conditions are consequences.
DETECTION_ORDER = (
    ("header_check_failed", None),
    ("unknown_target_address", 12),
    ("rejected_destination_key", 3),
    ("unused_command_code", 2),
    ("command_not_available", 10),
    ("read_modify_write_length_invalid", 11),
    ("verify_buffer_overrun", 9),
    ("payload_shorter_than_declared", 5),
    ("payload_longer_than_declared", 6),
    ("packet_terminated_in_error", 7),
    ("data_check_value_mismatch", 4),
    ("unspecified_failure", 1),
)

# A header that cannot be trusted leaves no safe way to build a reply, so the
# command is dropped without one.
SILENT_CONDITION = "header_check_failed"

_CONDITION_TOKENS = tuple(name for name, _ in DETECTION_ORDER)


def _require_int(value, label, minimum=None, maximum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer" % label)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be at most %d, got %d" % (label, maximum, value))
    return value


def known_status_codes():
    """Return the status values the registry carries, in numeric order."""
    return tuple(sorted(STATUS_REGISTRY))


def status_slug(code):
    """Return the short slug for a status value."""
    _require_int(code, "status code", 0, 255)
    entry = STATUS_REGISTRY.get(code)
    if entry is None:
        return "reserved-%d" % code
    return entry[0]


def status_family(code):
    """Return the fault family a status value belongs to."""
    _require_int(code, "status code", 0, 255)
    entry = STATUS_REGISTRY.get(code)
    if entry is None:
        return FAMILY_RESERVED
    return entry[1]


def is_reserved_status(code):
    """Return whether a status value is kept aside rather than reportable."""
    return status_family(code) == FAMILY_RESERVED


def is_success(code):
    """Return whether a status value reports a completed command."""
    _require_int(code, "status code", 0, 255)
    return code == STATUS_SUCCESS


def validate_observation(observation):
    """Return a normalised set of observed condition flags."""
    if not isinstance(observation, dict):
        raise ValueError("observation must be a mapping of condition flags")
    normalised = {}
    for key, value in observation.items():
        if key not in _CONDITION_TOKENS:
            raise ValueError("unknown condition token %r" % (key,))
        if not isinstance(value, bool):
            raise ValueError("condition %r must be a boolean" % (key,))
        normalised[key] = value
    for token in _CONDITION_TOKENS:
        normalised.setdefault(token, False)
    return normalised


def detect_status(observation):
    """Return the status a target reports for a set of observed conditions.

    Returns None when the header itself could not be trusted, because then no
    reply is built at all.
    """
    flags = validate_observation(observation)
    for token, code in DETECTION_ORDER:
        if flags[token]:
            return code
    return STATUS_SUCCESS


def reply_is_sent(observation, acknowledge_requested=True):
    """Return whether the target puts a reply on the link."""
    flags = validate_observation(observation)
    if not isinstance(acknowledge_requested, bool):
        raise ValueError("acknowledge_requested must be a boolean")
    if flags[SILENT_CONDITION]:
        return False
    return acknowledge_requested


def check_reply_consistency(status, returned_data_length):
    """Return the findings raised by a reply's status and returned length."""
    _require_int(status, "status", 0, 255)
    _require_int(returned_data_length, "returned_data_length", 0)
    findings = []
    if is_reserved_status(status):
        findings.append(
            "status %d is kept aside and must not be reported by a target" % status)
    if status != STATUS_SUCCESS and returned_data_length != 0:
        findings.append(
            "status %d reports a failure yet the reply carries %d data bytes"
            % (status, returned_data_length))
    return findings


def grade_transaction(record):
    """Grade one transaction record against the observed conditions."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    observation = validate_observation(record.get("observation", {}))
    acknowledge = record.get("acknowledge_requested", True)
    expected = detect_status(observation)
    sent = reply_is_sent(observation, acknowledge)
    findings = []
    reported = record.get("reported_status")
    returned = record.get("returned_data_length", 0)
    if sent:
        if reported is None:
            findings.append("a reply was owed but no status was captured")
        else:
            _require_int(reported, "reported_status", 0, 255)
            if reported != expected:
                findings.append(
                    "target reported status %d (%s) where the observed conditions call "
                    "for %d (%s)" % (reported, status_slug(reported),
                                     expected, status_slug(expected)))
            findings.extend(check_reply_consistency(reported, returned))
    elif reported is not None:
        findings.append(
            "a reply carrying status %d was captured where none should have been sent"
            % reported)
    return {
        "expected_status": expected,
        "expected_slug": None if expected is None else status_slug(expected),
        "family": None if expected is None else status_family(expected),
        "reply_sent": sent,
        "findings": findings,
        "consistent": not findings,
    }


def summarise_transactions(records):
    """Return per-family counts and the findings across a run of transactions."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of transaction records")
    counts = dict((family, 0) for family in FAMILIES)
    silent = 0
    findings = []
    graded = []
    for index, record in enumerate(records):
        result = grade_transaction(record)
        graded.append(result)
        if result["family"] is None:
            silent += 1
        else:
            counts[result["family"]] += 1
        for finding in result["findings"]:
            findings.append("record %d: %s" % (index, finding))
    return {
        "graded": graded,
        "family_counts": counts,
        "dropped_without_reply": silent,
        "findings": findings,
        "consistent": not findings,
    }
