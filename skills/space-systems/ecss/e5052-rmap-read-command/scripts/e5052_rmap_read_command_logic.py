"""Read-command construction and grading for SpaceWire RMAP.

Anchor: ECSS-E-ST-50-52C clause 5.8.2.4 (requirements on the read command).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise and validate a read-command specification: routing, key,
   transaction identifier, extended-plus-base address, requested length and
   the option flags.
2. Pack the option flags into the instruction byte a read carries, and unpack
   a captured byte back into the same options.
3. Size both halves of the transaction: the command, which carries no payload
   and no payload check byte, and the reply, which carries the returned bytes
   and closes with one.
4. Derive the address span the read covers and the share of the link traffic
   that is actually returned data.
5. Grade the option combination and, when a reply record is supplied, check
   that the reply agrees with the command it answers.
"""

__all__ = [
    "PACKET_TYPE_COMMAND",
    "MAX_DATA_LENGTH",
    "MAX_BASE_ADDRESS",
    "MAX_EXTENDED_ADDRESS",
    "MAX_TRANSACTION_ID",
    "COMMAND_HEADER_BYTES",
    "REPLY_HEADER_BYTES",
    "REPLY_ADDRESS_LENGTHS",
    "REGION_MEMORY",
    "REGION_PORT",
    "REGIONS",
    "reply_address_length_code",
    "padded_reply_address",
    "validate_read_command",
    "instruction_byte",
    "decode_instruction_byte",
    "read_command_size",
    "read_reply_size",
    "address_span",
    "returned_data_share",
    "check_reply",
    "assess_read_command",
]

PACKET_TYPE_COMMAND = 0b01

MAX_DATA_LENGTH = (1 << 24) - 1
MAX_BASE_ADDRESS = (1 << 32) - 1
MAX_EXTENDED_ADDRESS = (1 << 8) - 1
MAX_TRANSACTION_ID = (1 << 16) - 1

# target address, protocol id, instruction, key, initiator address, two
# identifier bytes, extended address, four address bytes, three length bytes
# and the header check byte.
COMMAND_HEADER_BYTES = 16

# initiator address, protocol id, instruction, status, target address, two
# identifier bytes, one reserved byte, three length bytes and the header check
# byte.
REPLY_HEADER_BYTES = 12

REPLY_ADDRESS_LENGTHS = (0, 4, 8, 12)

# A read that walks consecutive locations belongs to a memory region; a read
# that pulls repeatedly from one location belongs to a port-style register.
REGION_MEMORY = "memory"
REGION_PORT = "port"
REGIONS = (REGION_MEMORY, REGION_PORT)


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
    if not isinstance(reply_address, (bytes, bytearray, list, tuple)):
        raise ValueError("reply_address must be a sequence of path bytes or None")
    path = list(reply_address)
    for item in path:
        _require_int(item, "reply address byte", minimum=0, maximum=255)
    if not path:
        return 0
    groups = (len(path) + 3) // 4
    if groups > len(REPLY_ADDRESS_LENGTHS) - 1:
        raise ValueError(
            "reply address of %d bytes exceeds the %d-byte field"
            % (len(path), REPLY_ADDRESS_LENGTHS[-1]))
    return groups


def padded_reply_address(reply_address):
    """Return the reply-address path left-padded with leading zero bytes."""
    code = reply_address_length_code(reply_address)
    width = REPLY_ADDRESS_LENGTHS[code]
    if width == 0:
        return []
    path = list(reply_address)
    return [0] * (width - len(path)) + path


def validate_read_command(spec):
    """Return a normalised read-command specification."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if spec.get("data"):
        raise ValueError("a read command carries no payload; remove 'data'")
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
        "data_length": _require_int(
            spec.get("data_length"), "data_length", 1, MAX_DATA_LENGTH),
        "verify": _require_bool(spec.get("verify", False), "verify"),
        "acknowledge": _require_bool(spec.get("acknowledge", True), "acknowledge"),
        "increment": _require_bool(spec.get("increment", True), "increment"),
    }
    region = spec.get("region")
    if region is not None and region not in REGIONS:
        raise ValueError("region must be one of %s, got %r" % (", ".join(REGIONS), region))
    norm["region"] = region
    norm["reply_address"] = list(spec.get("reply_address") or [])
    norm["reply_address_code"] = reply_address_length_code(norm["reply_address"])
    return norm


def instruction_byte(spec):
    """Return the packed instruction byte for a read command."""
    norm = validate_read_command(spec)
    value = PACKET_TYPE_COMMAND << 6
    value |= 0 << 5                       # read rather than write
    value |= (1 if norm["verify"] else 0) << 4
    value |= (1 if norm["acknowledge"] else 0) << 3
    value |= (1 if norm["increment"] else 0) << 2
    value |= norm["reply_address_code"] & 0b11
    return value


def decode_instruction_byte(value):
    """Return the option record carried by a packed read instruction byte."""
    _require_int(value, "instruction byte", 0, 255)
    if (value >> 6) & 0b11 != PACKET_TYPE_COMMAND:
        raise ValueError("instruction byte does not mark a command packet")
    if (value >> 5) & 1:
        raise ValueError("instruction byte marks a write, not a read")
    return {
        "verify": bool((value >> 4) & 1),
        "acknowledge": bool((value >> 3) & 1),
        "increment": bool((value >> 2) & 1),
        "reply_address_code": value & 0b11,
    }


def read_command_size(spec):
    """Return the bytes the read command itself puts on the link."""
    norm = validate_read_command(spec)
    return COMMAND_HEADER_BYTES + REPLY_ADDRESS_LENGTHS[norm["reply_address_code"]]


def read_reply_size(spec):
    """Return the bytes the reply carrying the requested data occupies."""
    norm = validate_read_command(spec)
    if not norm["acknowledge"]:
        return 0
    return REPLY_HEADER_BYTES + norm["data_length"] + 1


def address_span(spec):
    """Return the inclusive (first, last) base address the read covers."""
    norm = validate_read_command(spec)
    first = norm["address"]
    if not norm["increment"]:
        return (first, first)
    return (first, first + norm["data_length"] - 1)


def returned_data_share(spec):
    """Return the fraction of the transaction's bytes that is returned data."""
    norm = validate_read_command(spec)
    total = read_command_size(norm) + read_reply_size(norm)
    if total <= 0:
        raise ValueError("a transaction with no bytes on the link has no data share")
    return float(norm["data_length"]) / float(total)


def check_reply(spec, reply):
    """Return the findings raised by a reply against the command it answers."""
    norm = validate_read_command(spec)
    if not isinstance(reply, dict):
        raise ValueError("reply must be a mapping")
    status = _require_int(reply.get("status", 0), "reply status", 0, 255)
    returned = _require_int(reply.get("data_length", 0), "reply data_length", 0, MAX_DATA_LENGTH)
    identifier = _require_int(
        reply.get("transaction_id", norm["transaction_id"]),
        "reply transaction_id", 0, MAX_TRANSACTION_ID)
    findings = []
    if not norm["acknowledge"]:
        findings.append("a reply was received for a command that asked for none")
    if identifier != norm["transaction_id"]:
        findings.append(
            "reply identifier %d does not match the command identifier %d"
            % (identifier, norm["transaction_id"]))
    if status == 0:
        if returned != norm["data_length"]:
            findings.append(
                "successful reply returned %d bytes against the %d requested"
                % (returned, norm["data_length"]))
    elif returned != 0:
        findings.append(
            "reply reports status %d yet still carries %d data bytes" % (status, returned))
    return findings


def assess_read_command(spec, reply=None):
    """Grade a read-command specification, and a reply when one is supplied."""
    norm = validate_read_command(spec)
    findings = []
    if not norm["acknowledge"]:
        findings.append(
            "read asks for no reply, so the requested data has nowhere to be returned")
    if norm["verify"]:
        findings.append(
            "verify-before-write is set on a read, where there is nothing to verify")
    first, last = address_span(norm)
    if norm["increment"] and last > MAX_BASE_ADDRESS:
        findings.append(
            "incrementing read from %d for %d bytes runs past the four-byte address field"
            % (first, norm["data_length"]))
    if norm["region"] == REGION_PORT and norm["increment"]:
        findings.append(
            "incrementing read aimed at a port-style register walks away from the register")
    if norm["region"] == REGION_MEMORY and not norm["increment"] and norm["data_length"] > 1:
        findings.append(
            "non-incrementing read of %d bytes from a memory region returns one location "
            "repeatedly" % norm["data_length"])
    record = {
        "instruction_byte": instruction_byte(norm),
        "command_bytes": read_command_size(norm),
        "reply_bytes": read_reply_size(norm),
        "data_length": norm["data_length"],
        "address_first": first,
        "address_last": last,
        "reply_address_code": norm["reply_address_code"],
        "padded_reply_address": padded_reply_address(norm["reply_address"]),
        "returned_data_share": returned_data_share(norm),
        "findings": findings,
    }
    if reply is not None:
        reply_findings = check_reply(norm, reply)
        record["reply_findings"] = reply_findings
        findings = findings + reply_findings
        record["findings"] = findings
    record["acceptable"] = not findings
    return record
