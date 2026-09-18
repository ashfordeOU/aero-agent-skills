"""Write-command construction and grading for SpaceWire RMAP.

Anchor: ECSS-E-ST-50-52C clause 5.8.2.3 (requirements on the write command).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise and validate a write-command specification: the option flags
   (verify-before-write, acknowledge, increment address), the destination and
   reply routing, the transaction identifier, the extended-plus-base address
   and the data length.
2. Pack the option flags and the reply-address length code into the single
   instruction byte the command carries, and unpack it again so a captured
   byte can be read back into the same option record.
3. Size the command packet: fixed header fields, the padded reply-address
   field, the data payload and the two check bytes.
4. Compute the byte-wise check value over the header and over the data with
   the reflected polynomial the protocol uses.
5. Grade the combination of options a reviewer would question: a verified
   write that does not fit the target buffer, a verified write that asks for
   no reply, a verified write aimed at one non-incrementing address, and an
   address span that wraps the base address field.
"""

__all__ = [
    "PACKET_TYPE_COMMAND",
    "MAX_DATA_LENGTH",
    "MAX_BASE_ADDRESS",
    "MAX_EXTENDED_ADDRESS",
    "MAX_TRANSACTION_ID",
    "FIXED_HEADER_BYTES",
    "CHECK_POLYNOMIAL_REFLECTED",
    "REPLY_ADDRESS_LENGTHS",
    "reply_address_length_code",
    "padded_reply_address",
    "check_value",
    "validate_write_command",
    "instruction_byte",
    "decode_instruction_byte",
    "header_bytes",
    "write_packet_size",
    "address_span",
    "assess_write_command",
]

# Bit pattern that marks a packet as a command rather than a reply.
PACKET_TYPE_COMMAND = 0b01

# The data-length field is three bytes wide and the address field four.
MAX_DATA_LENGTH = (1 << 24) - 1
MAX_BASE_ADDRESS = (1 << 32) - 1
MAX_EXTENDED_ADDRESS = (1 << 8) - 1
MAX_TRANSACTION_ID = (1 << 16) - 1

# target address, protocol id, instruction, key, initiator address,
# two identifier bytes, extended address, four address bytes, three length
# bytes and the header check byte.
FIXED_HEADER_BYTES = 16

# Byte-wise check polynomial in reflected form, applied least significant bit
# first with a zero initial value.
CHECK_POLYNOMIAL_REFLECTED = 0xE0

# The reply-address field is carried in whole groups of four bytes.
REPLY_ADDRESS_LENGTHS = (0, 4, 8, 12)


def _require_int(value, label, minimum=None, maximum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer" % label)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be at most %d, got %d" % (label, maximum, value))
    return value


def _require_bool(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean" % label)
    return value


def reply_address_length_code(reply_address):
    """Return the two-bit code describing the padded reply-address field."""
    if reply_address is None:
        return 0
    if isinstance(reply_address, (bytes, bytearray)):
        path = list(reply_address)
    elif isinstance(reply_address, (list, tuple)):
        path = list(reply_address)
    else:
        raise ValueError("reply_address must be a sequence of path bytes or None")
    for item in path:
        _require_int(item, "reply address byte", minimum=0, maximum=255)
    if not path:
        return 0
    groups = (len(path) + 3) // 4
    if groups > len(REPLY_ADDRESS_LENGTHS) - 1:
        raise ValueError(
            "reply address of %d bytes exceeds the %d-byte field"
            % (len(path), REPLY_ADDRESS_LENGTHS[-1])
        )
    return groups


def padded_reply_address(reply_address):
    """Return the reply-address path left-padded with leading zero bytes."""
    code = reply_address_length_code(reply_address)
    width = REPLY_ADDRESS_LENGTHS[code]
    if width == 0:
        return []
    path = list(reply_address)
    return [0] * (width - len(path)) + path


def check_value(data):
    """Return the byte-wise check value over a sequence of bytes."""
    if isinstance(data, (bytes, bytearray)):
        payload = list(data)
    elif isinstance(data, (list, tuple)):
        payload = list(data)
    else:
        raise ValueError("data must be a sequence of bytes")
    crc = 0
    for item in payload:
        _require_int(item, "data byte", minimum=0, maximum=255)
        crc ^= item
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ CHECK_POLYNOMIAL_REFLECTED
            else:
                crc >>= 1
    return crc & 0xFF


def validate_write_command(spec):
    """Return a normalised write-command specification."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    norm = {
        "target_logical_address": _require_int(
            spec.get("target_logical_address", 254), "target_logical_address", 0, 255),
        "initiator_logical_address": _require_int(
            spec.get("initiator_logical_address", 254), "initiator_logical_address", 0, 255),
        "destination_key": _require_int(spec.get("destination_key", 0), "destination_key", 0, 255),
        "transaction_id": _require_int(
            spec.get("transaction_id", 0), "transaction_id", 0, MAX_TRANSACTION_ID),
        "extended_address": _require_int(
            spec.get("extended_address", 0), "extended_address", 0, MAX_EXTENDED_ADDRESS),
        "address": _require_int(spec.get("address", 0), "address", 0, MAX_BASE_ADDRESS),
        "verify": _require_bool(spec.get("verify", False), "verify"),
        "acknowledge": _require_bool(spec.get("acknowledge", True), "acknowledge"),
        "increment": _require_bool(spec.get("increment", True), "increment"),
    }
    if "data" in spec and spec["data"] is not None:
        data = spec["data"]
        if isinstance(data, (bytes, bytearray, list, tuple)):
            payload = list(data)
        else:
            raise ValueError("data must be a sequence of bytes")
        for item in payload:
            _require_int(item, "data byte", minimum=0, maximum=255)
        norm["data"] = payload
        length = len(payload)
        if "data_length" in spec and spec["data_length"] is not None:
            declared = _require_int(spec["data_length"], "data_length", 1, MAX_DATA_LENGTH)
            if declared != length:
                raise ValueError(
                    "data_length %d does not match the %d supplied data bytes"
                    % (declared, length))
    else:
        norm["data"] = None
        length = _require_int(spec.get("data_length"), "data_length", 1, MAX_DATA_LENGTH)
    if length < 1:
        raise ValueError("a write command must carry at least one data byte")
    if length > MAX_DATA_LENGTH:
        raise ValueError("data_length %d exceeds the three-byte field" % length)
    norm["data_length"] = length
    norm["reply_address"] = list(spec.get("reply_address") or [])
    norm["reply_address_code"] = reply_address_length_code(norm["reply_address"])
    if "verify_buffer_bytes" in spec and spec["verify_buffer_bytes"] is not None:
        norm["verify_buffer_bytes"] = _require_int(
            spec["verify_buffer_bytes"], "verify_buffer_bytes", 0, MAX_DATA_LENGTH)
    return norm


def instruction_byte(spec):
    """Return the packed instruction byte for a write command."""
    norm = validate_write_command(spec)
    value = PACKET_TYPE_COMMAND << 6
    value |= 1 << 5                       # write rather than read
    value |= (1 if norm["verify"] else 0) << 4
    value |= (1 if norm["acknowledge"] else 0) << 3
    value |= (1 if norm["increment"] else 0) << 2
    value |= norm["reply_address_code"] & 0b11
    return value


def decode_instruction_byte(value):
    """Return the option record carried by a packed instruction byte."""
    _require_int(value, "instruction byte", 0, 255)
    packet_type = (value >> 6) & 0b11
    if packet_type != PACKET_TYPE_COMMAND:
        raise ValueError("instruction byte does not mark a command packet")
    if not (value >> 5) & 1:
        raise ValueError("instruction byte marks a read, not a write")
    return {
        "verify": bool((value >> 4) & 1),
        "acknowledge": bool((value >> 3) & 1),
        "increment": bool((value >> 2) & 1),
        "reply_address_code": value & 0b11,
    }


def header_bytes(spec):
    """Return how many bytes the command header occupies, check byte included."""
    norm = validate_write_command(spec)
    return FIXED_HEADER_BYTES + REPLY_ADDRESS_LENGTHS[norm["reply_address_code"]]


def write_packet_size(spec):
    """Return the total bytes the write command puts on the link."""
    norm = validate_write_command(spec)
    return header_bytes(norm) + norm["data_length"] + 1


def address_span(spec):
    """Return the inclusive (first, last) base address the write touches."""
    norm = validate_write_command(spec)
    first = norm["address"]
    if not norm["increment"]:
        return (first, first)
    return (first, first + norm["data_length"] - 1)


def assess_write_command(spec):
    """Grade a write-command specification against the clause."""
    norm = validate_write_command(spec)
    findings = []
    first, last = address_span(norm)
    if norm["increment"] and last > MAX_BASE_ADDRESS:
        findings.append(
            "incrementing write from %d for %d bytes runs past the four-byte "
            "address field" % (first, norm["data_length"]))
    if norm["verify"]:
        limit = norm.get("verify_buffer_bytes")
        if limit is not None and norm["data_length"] > limit:
            findings.append(
                "verified write of %d bytes exceeds the %d-byte verify buffer of "
                "the target" % (norm["data_length"], limit))
        if not norm["acknowledge"]:
            findings.append(
                "verified write asks for no reply, so the verification outcome "
                "cannot be reported back")
        if not norm["increment"]:
            findings.append(
                "verified write to a single non-incrementing address rewrites the "
                "same location for every data byte")
    record = {
        "instruction_byte": instruction_byte(norm),
        "header_bytes": header_bytes(norm),
        "packet_bytes": write_packet_size(norm),
        "data_length": norm["data_length"],
        "address_first": first,
        "address_last": last,
        "reply_address_code": norm["reply_address_code"],
        "padded_reply_address": padded_reply_address(norm["reply_address"]),
        "findings": findings,
        "acceptable": not findings,
    }
    if norm["data"] is not None:
        record["data_check_value"] = check_value(norm["data"])
    return record
