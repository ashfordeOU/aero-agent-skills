"""Read-modify-write command construction and grading for SpaceWire RMAP.

Anchor: ECSS-E-ST-50-52C clause 5.8.2.5 (requirements on the read-modify-write
command). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Normalise and validate a read-modify-write specification: the data field
   holds an operand followed by a mask of the same width, so its length is
   even and bounded, and the operation touches one address only.
2. Split the data field into operand and mask, and check the option-bit
   combination that identifies the command among the other command codes.
3. Apply the merge the target performs: every masked bit is taken from the
   operand and every unmasked bit is left as it was found.
4. Size both halves of the transaction: the command carries operand and mask,
   the reply carries the content found before the merge, which is half the
   command data length.
5. Grade the operation a reviewer would question: an all-zero mask that
   changes nothing, an all-ones mask that a plain write would do more
   cheaply, an operand carrying bits the mask discards, and an address that
   is not aligned to the operand width.
"""

__all__ = [
    "PACKET_TYPE_COMMAND",
    "RMW_OPTION_BITS",
    "MIN_DATA_LENGTH",
    "MAX_DATA_LENGTH",
    "MAX_BASE_ADDRESS",
    "MAX_EXTENDED_ADDRESS",
    "MAX_TRANSACTION_ID",
    "COMMAND_HEADER_BYTES",
    "REPLY_HEADER_BYTES",
    "REPLY_ADDRESS_LENGTHS",
    "permitted_data_lengths",
    "reply_address_length_code",
    "validate_rmw_command",
    "split_operand_and_mask",
    "operand_width",
    "reply_data_length",
    "instruction_byte",
    "decode_instruction_byte",
    "command_size",
    "reply_size",
    "masked_merge",
    "bits_selected",
    "mask_selectivity",
    "bits_changed",
    "assess_rmw_command",
]

PACKET_TYPE_COMMAND = 0b01

# The four option bits that pick the read-modify-write out of the command
# codes: not a plain write, verification set, a reply owed, and the single
# address walked as one operand.
RMW_OPTION_BITS = (0, 1, 1, 1)

# Operand and mask are carried side by side, each between one and four bytes.
MIN_DATA_LENGTH = 2
MAX_DATA_LENGTH = 8

MAX_BASE_ADDRESS = (1 << 32) - 1
MAX_EXTENDED_ADDRESS = (1 << 8) - 1
MAX_TRANSACTION_ID = (1 << 16) - 1

COMMAND_HEADER_BYTES = 16
REPLY_HEADER_BYTES = 12
REPLY_ADDRESS_LENGTHS = (0, 4, 8, 12)


def _require_int(value, label, minimum=None, maximum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer" % label)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be at most %d, got %d" % (label, maximum, value))
    return value


def _byte_list(value, label):
    if not isinstance(value, (bytes, bytearray, list, tuple)):
        raise ValueError("%s must be a sequence of bytes" % label)
    items = list(value)
    for item in items:
        _require_int(item, "%s byte" % label, minimum=0, maximum=255)
    return items


def permitted_data_lengths():
    """Return the data-field lengths a read-modify-write may carry."""
    return tuple(n for n in range(MIN_DATA_LENGTH, MAX_DATA_LENGTH + 1) if n % 2 == 0)


def reply_address_length_code(reply_address):
    """Return the two-bit code describing the padded reply-address field."""
    if reply_address is None:
        return 0
    path = _byte_list(reply_address, "reply_address")
    if not path:
        return 0
    groups = (len(path) + 3) // 4
    if groups > len(REPLY_ADDRESS_LENGTHS) - 1:
        raise ValueError(
            "reply address of %d bytes exceeds the %d-byte field"
            % (len(path), REPLY_ADDRESS_LENGTHS[-1]))
    return groups


def validate_rmw_command(spec):
    """Return a normalised read-modify-write specification."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    data = _byte_list(spec.get("data", []), "data")
    if not data:
        raise ValueError("a read-modify-write command must carry an operand and a mask")
    if len(data) % 2 != 0:
        raise ValueError(
            "data field of %d bytes is odd; operand and mask have equal width" % len(data))
    if len(data) not in permitted_data_lengths():
        raise ValueError(
            "data field of %d bytes is outside the permitted lengths %s"
            % (len(data), permitted_data_lengths()))
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
        "data": data,
        "data_length": len(data),
    }
    if "declared_data_length" in spec and spec["declared_data_length"] is not None:
        declared = _require_int(
            spec["declared_data_length"], "declared_data_length", MIN_DATA_LENGTH,
            MAX_DATA_LENGTH)
        if declared != len(data):
            raise ValueError(
                "declared_data_length %d does not match the %d supplied data bytes"
                % (declared, len(data)))
    norm["reply_address"] = list(spec.get("reply_address") or [])
    norm["reply_address_code"] = reply_address_length_code(norm["reply_address"])
    if "original" in spec and spec["original"] is not None:
        original = _byte_list(spec["original"], "original")
        if len(original) != len(data) // 2:
            raise ValueError(
                "original content of %d bytes does not match the %d-byte operand width"
                % (len(original), len(data) // 2))
        norm["original"] = original
    return norm


def operand_width(spec):
    """Return the operand width in bytes."""
    norm = validate_rmw_command(spec)
    return norm["data_length"] // 2


def split_operand_and_mask(spec):
    """Return the (operand, mask) byte lists carried in the data field."""
    norm = validate_rmw_command(spec)
    width = norm["data_length"] // 2
    return (norm["data"][:width], norm["data"][width:])


def reply_data_length(spec):
    """Return how many bytes of previous content the reply returns."""
    return operand_width(spec)


def instruction_byte(spec):
    """Return the packed instruction byte for a read-modify-write command."""
    norm = validate_rmw_command(spec)
    write_bit, verify_bit, reply_bit, increment_bit = RMW_OPTION_BITS
    value = PACKET_TYPE_COMMAND << 6
    value |= write_bit << 5
    value |= verify_bit << 4
    value |= reply_bit << 3
    value |= increment_bit << 2
    value |= norm["reply_address_code"] & 0b11
    return value


def decode_instruction_byte(value):
    """Return the reply-path code of a byte that marks a read-modify-write."""
    _require_int(value, "instruction byte", 0, 255)
    if (value >> 6) & 0b11 != PACKET_TYPE_COMMAND:
        raise ValueError("instruction byte does not mark a command packet")
    bits = ((value >> 5) & 1, (value >> 4) & 1, (value >> 3) & 1, (value >> 2) & 1)
    if bits != RMW_OPTION_BITS:
        raise ValueError(
            "option bits %s are not the read-modify-write combination %s"
            % (bits, RMW_OPTION_BITS))
    return {"reply_address_code": value & 0b11}


def command_size(spec):
    """Return the bytes the command puts on the link."""
    norm = validate_rmw_command(spec)
    return (COMMAND_HEADER_BYTES + REPLY_ADDRESS_LENGTHS[norm["reply_address_code"]]
            + norm["data_length"] + 1)


def reply_size(spec):
    """Return the bytes the reply carrying the previous content occupies."""
    return REPLY_HEADER_BYTES + reply_data_length(spec) + 1


def masked_merge(original, operand, mask):
    """Return the content the target writes back after the merge."""
    old = _byte_list(original, "original")
    new = _byte_list(operand, "operand")
    selector = _byte_list(mask, "mask")
    if not old:
        raise ValueError("original content must carry at least one byte")
    if len(old) != len(new) or len(old) != len(selector):
        raise ValueError(
            "original, operand and mask must be the same width (%d, %d, %d)"
            % (len(old), len(new), len(selector)))
    return [(o & (~m & 0xFF)) | (n & m) for o, n, m in zip(old, new, selector)]


def bits_selected(mask):
    """Return how many bits the mask selects."""
    selector = _byte_list(mask, "mask")
    return sum(bin(item).count("1") for item in selector)


def mask_selectivity(mask):
    """Return the fraction of the operand width the mask selects."""
    selector = _byte_list(mask, "mask")
    if not selector:
        raise ValueError("mask must carry at least one byte")
    return float(bits_selected(selector)) / float(8 * len(selector))


def bits_changed(original, operand, mask):
    """Return how many bits the merge actually flips."""
    old = _byte_list(original, "original")
    merged = masked_merge(old, operand, mask)
    return sum(bin(o ^ m).count("1") for o, m in zip(old, merged))


def assess_rmw_command(spec):
    """Grade a read-modify-write specification against the clause."""
    norm = validate_rmw_command(spec)
    operand, mask = split_operand_and_mask(norm)
    width = len(operand)
    findings = []
    selected = bits_selected(mask)
    if selected == 0:
        findings.append(
            "mask selects no bits, so the command reads the location and writes it back "
            "unchanged")
    if selected == 8 * width:
        findings.append(
            "mask selects every bit, so a plain write would do the same work without the "
            "read half of the transaction")
    discarded = [n & (~m & 0xFF) for n, m in zip(operand, mask)]
    if any(discarded):
        findings.append(
            "operand carries bits outside the mask that the target discards")
    if norm["address"] % width != 0:
        findings.append(
            "address %d is not aligned to the %d-byte operand width"
            % (norm["address"], width))
    record = {
        "operand": operand,
        "mask": mask,
        "operand_width": width,
        "data_length": norm["data_length"],
        "reply_data_length": reply_data_length(norm),
        "instruction_byte": instruction_byte(norm),
        "command_bytes": command_size(norm),
        "reply_bytes": reply_size(norm),
        "bits_selected": selected,
        "mask_selectivity": mask_selectivity(mask),
        "findings": findings,
    }
    if "original" in norm:
        record["merged"] = masked_merge(norm["original"], operand, mask)
        record["bits_changed"] = bits_changed(norm["original"], operand, mask)
    record["acceptable"] = not findings
    return record
