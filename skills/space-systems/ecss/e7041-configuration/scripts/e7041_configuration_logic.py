"""Downlink configuration of a large packet transfer subservice.

Anchor: ECSS-E-ST-70-41C clause 6.13.3.1 (configuration of the downlink of
large messages). Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Validate the telemetry packet limit and the per-part report overhead, and
   derive the usable part payload from them.
2. Compare the configured part size with that payload and carry the effective
   part size forward, recording any reduction as a finding.
3. Count the parts the declared largest message needs (ceiling division), the
   octets its last part carries and how full that last part is.
4. Derive the ceiling of the part sequence number field and the largest
   message the configuration can therefore support.
5. Validate the transaction identifier pool against the identifier field width
   and the configured concurrency.
6. Assemble the configuration verdict and its findings.
"""

__all__ = [
    "MIN_PARTS_FOR_TRANSFER",
    "usable_part_octets",
    "max_numbered_parts",
    "part_count",
    "last_part_octets",
    "last_part_fill_ratio",
    "largest_supported_message_octets",
    "validate_transaction_identifiers",
    "assess_downlink_configuration",
]

# A transaction that resolves to a single part is a plain report: the downlink
# process needs a first part and a last part before it is a transfer at all.
MIN_PARTS_FOR_TRANSFER = 2

# Widest sequence or identifier field this configuration model will accept.
MAX_FIELD_BITS = 32


def _require_positive_int(value, label):
    """Return value as a positive whole octet/bit count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _require_non_negative_int(value, label):
    """Return value as a non-negative whole count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def usable_part_octets(max_packet_octets, part_report_overhead_octets):
    """Return the octets of a downlink part report left for message data."""
    limit = _require_positive_int(max_packet_octets, "max_packet_octets")
    overhead = _require_non_negative_int(
        part_report_overhead_octets, "part_report_overhead_octets"
    )
    if overhead >= limit:
        raise ValueError(
            "part report overhead %d octets leaves no data room inside a %d octet packet"
            % (overhead, limit)
        )
    return limit - overhead


def max_numbered_parts(part_number_bits):
    """Return how many parts a sequence number field of this width can address."""
    bits = _require_positive_int(part_number_bits, "part_number_bits")
    if bits > MAX_FIELD_BITS:
        raise ValueError(
            "part_number_bits %d exceeds the %d bit model limit" % (bits, MAX_FIELD_BITS)
        )
    # Part numbering starts at one, so the all-zero code point is not a part.
    return (1 << bits) - 1


def part_count(message_octets, part_octets):
    """Return the number of parts a message of this size occupies."""
    message = _require_positive_int(message_octets, "message_octets")
    part = _require_positive_int(part_octets, "part_octets")
    return -(-message // part)


def last_part_octets(message_octets, part_octets):
    """Return the octets the final part of the message actually carries."""
    message = _require_positive_int(message_octets, "message_octets")
    part = _require_positive_int(part_octets, "part_octets")
    count = part_count(message, part)
    return message - (count - 1) * part


def last_part_fill_ratio(message_octets, part_octets):
    """Return the occupancy of the final part as a fraction of the part size."""
    part = _require_positive_int(part_octets, "part_octets")
    return last_part_octets(message_octets, part) / float(part)


def largest_supported_message_octets(part_octets, max_parts):
    """Return the largest message the part size and sequence field can carry."""
    part = _require_positive_int(part_octets, "part_octets")
    parts = _require_positive_int(max_parts, "max_parts")
    return part * parts


def validate_transaction_identifiers(identifiers, identifier_bits):
    """Return the identifier pool as a sorted tuple after validating it."""
    bits = _require_positive_int(identifier_bits, "identifier_bits")
    if bits > MAX_FIELD_BITS:
        raise ValueError(
            "identifier_bits %d exceeds the %d bit model limit" % (bits, MAX_FIELD_BITS)
        )
    if not isinstance(identifiers, (list, tuple)) or not identifiers:
        raise ValueError("identifiers must be a non-empty sequence")
    ceiling = 1 << bits
    seen = set()
    for index, item in enumerate(identifiers):
        if not isinstance(item, int) or isinstance(item, bool):
            raise ValueError("identifiers[%d] must be an integer, got %r" % (index, item))
        if item < 0 or item >= ceiling:
            raise ValueError(
                "identifiers[%d] value %d falls outside a %d bit identifier field"
                % (index, item, bits)
            )
        if item in seen:
            raise ValueError("identifier %d appears more than once in the pool" % item)
        seen.add(item)
    return tuple(sorted(seen))


def assess_downlink_configuration(spec):
    """Assess a clause 6.13.3.1 downlink configuration.

    spec keys: max_packet_octets, part_report_overhead_octets,
    configured_part_octets, largest_message_octets, part_number_bits,
    identifier_bits, transaction_identifiers, concurrent_transactions.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "max_packet_octets",
        "part_report_overhead_octets",
        "configured_part_octets",
        "largest_message_octets",
        "part_number_bits",
        "identifier_bits",
        "transaction_identifiers",
        "concurrent_transactions",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    usable = usable_part_octets(
        spec["max_packet_octets"], spec["part_report_overhead_octets"]
    )
    configured = _require_positive_int(
        spec["configured_part_octets"], "configured_part_octets"
    )
    concurrency = _require_positive_int(
        spec["concurrent_transactions"], "concurrent_transactions"
    )
    findings = []

    effective = configured
    if configured > usable:
        effective = usable
        findings.append(
            "configured part size %d octets exceeds the %d octets a part report can "
            "carry; effective part size reduced to %d" % (configured, usable, usable)
        )

    largest_message = _require_positive_int(
        spec["largest_message_octets"], "largest_message_octets"
    )
    parts_needed = part_count(largest_message, effective)
    tail_octets = last_part_octets(largest_message, effective)
    tail_fill = last_part_fill_ratio(largest_message, effective)

    ceiling_parts = max_numbered_parts(spec["part_number_bits"])
    supported = largest_supported_message_octets(effective, ceiling_parts)

    if parts_needed > ceiling_parts:
        findings.append(
            "largest message needs %d parts but the part sequence number field "
            "numbers at most %d" % (parts_needed, ceiling_parts)
        )
    if parts_needed < MIN_PARTS_FOR_TRANSFER:
        findings.append(
            "largest message fits in %d part; it does not need the large packet "
            "transfer downlink" % parts_needed
        )

    pool = validate_transaction_identifiers(
        spec["transaction_identifiers"], spec["identifier_bits"]
    )
    if len(pool) < concurrency:
        findings.append(
            "identifier pool holds %d identifiers for %d concurrent transactions"
            % (len(pool), concurrency)
        )

    return {
        "usable_part_octets": usable,
        "configured_part_octets": configured,
        "effective_part_octets": effective,
        "parts_needed": parts_needed,
        "last_part_octets": tail_octets,
        "last_part_fill_ratio": tail_fill,
        "max_numbered_parts": ceiling_parts,
        "largest_supported_message_octets": supported,
        "identifier_pool": pool,
        "concurrent_transactions": concurrency,
        "compliant": not findings,
        "findings": findings,
    }
