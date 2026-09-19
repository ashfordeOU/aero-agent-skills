"""Telemetry packet user data field sizing and layout.

Anchor: ECSS-E-ST-70-41C clause 7.4.3.2 (requirements on the telemetry packet
user data field). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Resolve the message body of a report subtype into an ordered parameter
   layout and give every parameter its bit offset inside the user data field.
2. Add the spare bits needed to bring the body onto an octet boundary, since
   the field that follows it can only start on one.
3. Add the packet error control field when the mission carries one, at its
   configured width, always as the last thing in the user data field.
4. Combine the user data field with the secondary header to get the packet
   data field, and derive the length field the primary header carries, which
   counts the packet data field octets less one.
5. Check the result against the largest packet the mission allows and report
   every finding instead of silently truncating the body.
"""

__all__ = [
    "OCTET_BITS",
    "DEFAULT_ERROR_CONTROL_BITS",
    "DEFAULT_MAX_PACKET_DATA_FIELD_OCTETS",
    "PRIMARY_HEADER_OCTETS",
    "MAX_SPARE_BITS",
    "validate_bit_count",
    "resolve_body_layout",
    "body_bits",
    "spare_bits_for_alignment",
    "user_data_field_bits",
    "user_data_field_octets",
    "packet_data_field_octets",
    "packet_data_length_field",
    "total_packet_octets",
    "parameter_offsets",
    "assess_user_data_field",
]

OCTET_BITS = 8

# Width of the packet error control field when the mission carries one.
DEFAULT_ERROR_CONTROL_BITS = 16

# Largest packet data field a space packet length field can express.
DEFAULT_MAX_PACKET_DATA_FIELD_OCTETS = 65536

# The packet primary header that sits ahead of the packet data field.
PRIMARY_HEADER_OCTETS = 6

# Spare exists only to reach the next octet boundary, so it is never a whole
# octet wide.
MAX_SPARE_BITS = OCTET_BITS - 1


def validate_bit_count(value, label, allow_zero=True):
    """Return value as a non-negative integer bit count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer number of bits, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    if value == 0 and not allow_zero:
        raise ValueError("%s must be positive" % label)
    return value


def resolve_body_layout(parameters):
    """Return the message body as an ordered list of (name, width_bits)."""
    if isinstance(parameters, (str, bytes)) or not isinstance(parameters, (list, tuple)):
        raise ValueError("parameters must be a sequence of (name, width_bits) pairs")
    layout = []
    seen = set()
    for index, item in enumerate(parameters):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("parameter %d must be a (name, width_bits) pair" % index)
        name, width = item
        if not isinstance(name, str) or not name.strip():
            raise ValueError("parameter %d has no usable name" % index)
        name = name.strip()
        if name in seen:
            raise ValueError("parameter name %r appears twice in the message body" % name)
        seen.add(name)
        validate_bit_count(width, "width of parameter %r" % name, allow_zero=False)
        layout.append((name, width))
    return layout


def body_bits(parameters):
    """Return the total width of the message body in bits."""
    return sum(width for _name, width in resolve_body_layout(parameters))


def parameter_offsets(parameters):
    """Return one record per parameter carrying its bit and octet position."""
    layout = resolve_body_layout(parameters)
    records = []
    offset = 0
    for name, width in layout:
        records.append(
            {
                "name": name,
                "width_bits": width,
                "offset_bits": offset,
                "octet": offset // OCTET_BITS,
                "bit_in_octet": offset % OCTET_BITS,
                "octet_aligned": offset % OCTET_BITS == 0,
            }
        )
        offset += width
    return records


def spare_bits_for_alignment(bits):
    """Return the spare bits needed to reach the next octet boundary."""
    count = validate_bit_count(bits, "bit count")
    return (OCTET_BITS - (count % OCTET_BITS)) % OCTET_BITS


def user_data_field_bits(message_body_bits, error_control_bits=0):
    """Return (total_bits, spare_bits) for the user data field."""
    body = validate_bit_count(message_body_bits, "message body width")
    control = validate_bit_count(error_control_bits, "error control width")
    if control % OCTET_BITS != 0:
        raise ValueError(
            "error control width %d is not a whole number of octets" % control
        )
    spare = spare_bits_for_alignment(body)
    return (body + spare + control, spare)


def user_data_field_octets(message_body_bits, error_control_bits=0):
    """Return the user data field length in whole octets."""
    total, _spare = user_data_field_bits(message_body_bits, error_control_bits)
    if total % OCTET_BITS != 0:
        raise ValueError("user data field is %d bits, not a whole octet count" % total)
    return total // OCTET_BITS


def packet_data_field_octets(secondary_header_octets, user_data_octets):
    """Return the packet data field length: secondary header plus user data."""
    head = validate_bit_count(secondary_header_octets, "secondary header octets")
    body = validate_bit_count(user_data_octets, "user data field octets")
    total = head + body
    if total == 0:
        raise ValueError("packet data field cannot be empty")
    return total


def packet_data_length_field(packet_data_octets):
    """Return the primary header length field: data field octets less one."""
    total = validate_bit_count(packet_data_octets, "packet data field octets")
    if total == 0:
        raise ValueError("a packet data field of zero octets has no length field value")
    return total - 1


def total_packet_octets(packet_data_octets, primary_header_octets=PRIMARY_HEADER_OCTETS):
    """Return the whole packet length including the primary header."""
    head = validate_bit_count(primary_header_octets, "primary header octets")
    return head + validate_bit_count(packet_data_octets, "packet data field octets")


def assess_user_data_field(spec):
    """Run the full clause 7.4.3.2 user data field assessment.

    spec keys: parameters (sequence of (name, width_bits)),
    secondary_header_octets, optional carries_error_control,
    error_control_bits, max_packet_data_field_octets.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("parameters", "secondary_header_octets"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    layout = resolve_body_layout(spec["parameters"])
    body = sum(width for _name, width in layout)

    carries_control = spec.get("carries_error_control", False)
    if not isinstance(carries_control, bool):
        raise ValueError("carries_error_control must be a boolean")
    if carries_control:
        control = spec.get("error_control_bits", DEFAULT_ERROR_CONTROL_BITS)
        validate_bit_count(control, "error control width", allow_zero=False)
    else:
        if "error_control_bits" in spec and spec["error_control_bits"]:
            raise ValueError(
                "error control width given but the mission carries no error "
                "control field"
            )
        control = 0

    total_bits, spare = user_data_field_bits(body, control)
    user_octets = total_bits // OCTET_BITS
    data_field = packet_data_field_octets(spec["secondary_header_octets"], user_octets)
    length_field = packet_data_length_field(data_field)
    packet_octets = total_packet_octets(data_field)

    limit = spec.get("max_packet_data_field_octets", DEFAULT_MAX_PACKET_DATA_FIELD_OCTETS)
    validate_bit_count(limit, "packet data field limit", allow_zero=False)

    findings = []
    if not layout:
        findings.append(
            "message body carries no parameters; the user data field would hold "
            "only spare and error control"
        )
    if spare > MAX_SPARE_BITS:
        raise ValueError("spare of %d bits exceeds the alignment need" % spare)
    if spare:
        findings.append(
            "message body is %d bits, so %d spare bit(s) are added to reach the "
            "next octet boundary" % (body, spare)
        )
    if data_field > limit:
        findings.append(
            "packet data field is %d octets, above the %d-octet mission limit"
            % (data_field, limit)
        )
    unaligned = [rec["name"] for rec in parameter_offsets(spec["parameters"])
                 if not rec["octet_aligned"]]
    return {
        "body_layout": layout,
        "body_bits": body,
        "spare_bits": spare,
        "error_control_bits": control,
        "user_data_field_octets": user_octets,
        "packet_data_field_octets": data_field,
        "packet_data_length_field": length_field,
        "total_packet_octets": packet_octets,
        "parameters_crossing_an_octet_boundary": unaligned,
        "findings": findings,
        "compliant": data_field <= limit and bool(layout),
    }
