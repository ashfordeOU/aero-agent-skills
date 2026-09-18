"""Target SpaceWire address field construction and validation.

Anchor: ECSS-E-ST-50-53 clause 5.3.1 (the target SpaceWire address field that
leads a packet). Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Categorize every byte of the field by value alone: null padding, path
   address, logical address, or a reserved value that may not be sent.
2. Parse the field positionally - a leading null run, then the path bytes,
   then at most one logical address - refusing an interior null, a reserved
   byte and anything after the logical address.
3. Build a field from a port list and an optional logical address, prepending
   null padding only when an alignment is asked for.
4. Report the field length and whether it is a whole multiple of the declared
   alignment.
5. Consume one hop the way a router does: take the leading significant byte,
   refuse when it is not a path address, and return the remaining field.
6. Walk the whole route and grade the field against its declared intent.
"""

__all__ = [
    "NULL_BYTE",
    "PATH_ADDRESS_MIN",
    "PATH_ADDRESS_MAX",
    "LOGICAL_ADDRESS_MIN",
    "LOGICAL_ADDRESS_MAX",
    "RESERVED_BYTE",
    "PAD_ALIGNMENT",
    "BYTE_CATEGORIES",
    "categorize_byte",
    "validate_field",
    "validate_path",
    "validate_logical_address",
    "build_address_field",
    "parse_address_field",
    "strip_leading_padding",
    "field_length",
    "alignment_remainder",
    "is_aligned",
    "is_direct",
    "consume_hop",
    "route_packet",
    "assess_target_address_field",
]

# The null byte is padding; it is discarded on the way and is meaningful only
# in the leading run of the field.
NULL_BYTE = 0

# Path addresses name the output port of the next router.
PATH_ADDRESS_MIN = 1
PATH_ADDRESS_MAX = 31

# Logical addresses name the target node itself.
LOGICAL_ADDRESS_MIN = 32
LOGICAL_ADDRESS_MAX = 254

# The top byte value is reserved and may not be sent in the field.
RESERVED_BYTE = 255

# Alignment the initiator may pad the field up to.
PAD_ALIGNMENT = 4

BYTE_CATEGORIES = ("null", "path", "logical", "reserved")


def _int(value, label):
    """Return value as an int, rejecting bools and non-integers."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, type(value).__name__))
    return int(value)


def categorize_byte(value, label="address byte"):
    """Return the category a single field byte falls in, by value alone."""
    byte = _int(value, label)
    if byte < 0 or byte > RESERVED_BYTE:
        raise ValueError("%s %d is outside the byte range 0..%d" % (label, byte, RESERVED_BYTE))
    if byte == NULL_BYTE:
        return "null"
    if PATH_ADDRESS_MIN <= byte <= PATH_ADDRESS_MAX:
        return "path"
    if LOGICAL_ADDRESS_MIN <= byte <= LOGICAL_ADDRESS_MAX:
        return "logical"
    return "reserved"


def validate_field(field):
    """Return the field as a list of validated byte values."""
    if isinstance(field, (str, bytes, bytearray)):
        if isinstance(field, (bytes, bytearray)):
            return [int(b) for b in field]
        raise ValueError("address field must be a sequence of byte values, not text")
    if not isinstance(field, (list, tuple)):
        raise ValueError("address field must be a sequence of byte values")
    out = []
    for index, value in enumerate(field):
        byte = _int(value, "address field byte %d" % index)
        if byte < 0 or byte > RESERVED_BYTE:
            raise ValueError(
                "address field byte %d is %d, outside 0..%d" % (index, byte, RESERVED_BYTE)
            )
        out.append(byte)
    return out


def validate_path(ports):
    """Return the validated path-address list naming one output port per hop."""
    if ports is None:
        return []
    if not isinstance(ports, (list, tuple)):
        raise ValueError("port list must be a sequence")
    out = []
    for index, value in enumerate(ports):
        port = _int(value, "port %d" % index)
        if not PATH_ADDRESS_MIN <= port <= PATH_ADDRESS_MAX:
            raise ValueError(
                "port %d is %d, outside the path-address range %d..%d"
                % (index, port, PATH_ADDRESS_MIN, PATH_ADDRESS_MAX)
            )
        out.append(port)
    return out


def validate_logical_address(address):
    """Return the validated logical address, or None when there is not one."""
    if address is None:
        return None
    value = _int(address, "logical address")
    if not LOGICAL_ADDRESS_MIN <= value <= LOGICAL_ADDRESS_MAX:
        raise ValueError(
            "logical address %d is outside %d..%d"
            % (value, LOGICAL_ADDRESS_MIN, LOGICAL_ADDRESS_MAX)
        )
    return value


def build_address_field(ports, logical_address=None, align_to=None):
    """Assemble the target address field from a route and an optional address."""
    path = validate_path(ports)
    logical = validate_logical_address(logical_address)
    body = list(path)
    if logical is not None:
        body.append(logical)
    if align_to is None:
        return body
    alignment = _int(align_to, "alignment")
    if alignment < 1:
        raise ValueError("alignment must be at least 1, got %d" % alignment)
    remainder = len(body) % alignment
    if remainder == 0:
        return body
    return [NULL_BYTE] * (alignment - remainder) + body


def strip_leading_padding(field):
    """Return the field with its leading null padding removed."""
    bytes_ = validate_field(field)
    index = 0
    while index < len(bytes_) and bytes_[index] == NULL_BYTE:
        index += 1
    return bytes_[index:]


def parse_address_field(field):
    """Parse the field positionally into padding, path and logical address."""
    bytes_ = validate_field(field)
    padding = 0
    path = []
    logical = None
    seen_significant = False
    for index, byte in enumerate(bytes_):
        category = categorize_byte(byte, "address field byte %d" % index)
        if category == "reserved":
            raise ValueError(
                "address field byte %d is the reserved value %d and may not be sent"
                % (index, byte)
            )
        if category == "null":
            if seen_significant:
                raise ValueError(
                    "address field byte %d is a null inside the route; padding leads the "
                    "field and a later null terminates the route early" % index
                )
            padding += 1
            continue
        seen_significant = True
        if logical is not None:
            raise ValueError(
                "address field byte %d follows the logical address; the route ends there"
                % index
            )
        if category == "path":
            path.append(byte)
        else:
            logical = byte
    return {
        "padding": padding,
        "path": path,
        "logical_address": logical,
        "length": len(bytes_),
    }


def field_length(field):
    """Return the number of bytes the field occupies, padding included."""
    return len(validate_field(field))


def alignment_remainder(field, align_to=PAD_ALIGNMENT):
    """Return the field length modulo the declared alignment."""
    alignment = _int(align_to, "alignment")
    if alignment < 1:
        raise ValueError("alignment must be at least 1, got %d" % alignment)
    return field_length(field) % alignment


def is_aligned(field, align_to=PAD_ALIGNMENT):
    """True when the field length is a whole multiple of the alignment."""
    return alignment_remainder(field, align_to) == 0


def is_direct(field):
    """True when the field carries no path bytes, so the target is attached."""
    return not parse_address_field(field)["path"]


def consume_hop(field):
    """Consume one router hop and return (port, remaining field)."""
    bytes_ = strip_leading_padding(field)
    if not bytes_:
        raise ValueError("address field is exhausted; no hop left to consume")
    leading = bytes_[0]
    category = categorize_byte(leading, "leading address byte")
    if category != "path":
        raise ValueError(
            "leading address byte %d is a %s address, not a path address; a router "
            "cannot forward on it" % (leading, category)
        )
    return leading, bytes_[1:]


def route_packet(field, hops=None):
    """Walk the route, returning the ports taken and the residue at the end."""
    remaining = validate_field(field)
    if hops is None:
        limit = len(parse_address_field(remaining)["path"])
    else:
        limit = _int(hops, "hops")
    if limit < 0:
        raise ValueError("hop count must not be negative, got %d" % limit)
    ports = []
    for _ in range(limit):
        port, remaining = consume_hop(remaining)
        ports.append(port)
    return {
        "ports": ports,
        "remaining": remaining,
        "hops": len(ports),
        "residue": parse_address_field(remaining),
    }


def assess_target_address_field(spec):
    """Grade a target address field against the route it is meant to carry."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "field" not in spec:
        raise ValueError("spec missing required key 'field'")
    parsed = parse_address_field(spec["field"])
    findings = []
    alignment = spec.get("align_to", PAD_ALIGNMENT)
    require_alignment = bool(spec.get("require_alignment", False))
    aligned = is_aligned(spec["field"], alignment)
    if require_alignment and not aligned:
        findings.append(
            "field is %d bytes, which is not a whole multiple of the %d-byte alignment "
            "the initiator requires" % (parsed["length"], _int(alignment, "alignment"))
        )
    directly_attached = spec.get("target_directly_attached")
    if directly_attached is not None:
        if not isinstance(directly_attached, bool):
            raise ValueError("target_directly_attached must be a boolean")
        if not parsed["path"] and not directly_attached:
            findings.append(
                "field carries no path bytes but the target is not directly attached"
            )
        if parsed["path"] and directly_attached:
            findings.append(
                "field carries %d path byte(s) for a directly attached target"
                % len(parsed["path"])
            )
    expected_hops = spec.get("expected_hops")
    if expected_hops is not None:
        wanted = _int(expected_hops, "expected_hops")
        if wanted < 0:
            raise ValueError("expected_hops must not be negative, got %d" % wanted)
        if len(parsed["path"]) != wanted:
            findings.append(
                "field routes %d hop(s) but the route declares %d"
                % (len(parsed["path"]), wanted)
            )
    if spec.get("require_logical_address") and parsed["logical_address"] is None:
        findings.append("field ends on a path address but a logical target address is required")
    walk = route_packet(spec["field"], len(parsed["path"]))
    return {
        "parsed": parsed,
        "route": walk,
        "aligned": aligned,
        "alignment_remainder": alignment_remainder(spec["field"], alignment),
        "direct": not parsed["path"],
        "findings": findings,
        "compliant": not findings,
    }
