"""Character-string parameter definition, encoding and decoding.

Anchor: ECSS-E-ST-70-41C clause 7.3.9 (character-string data type,
seven normative items). Paraphrased into an implementable procedure; no
standard text is reproduced.

What the clause is for. A character-string parameter is the one place in
a packet definition where a human-readable name travels on the wire --
an event text, a file path, a memory-area label. It is a sequence of
octets, one octet per character, drawn from a repertoire fixed in the
mission definition and not carried in the packet.

Two forms exist and they are not interchangeable:

* fixed-length -- the definition states how many characters the field
  holds, every occurrence occupies that many octets, and a value shorter
  than the field is padded to it with a declared pad octet. The padding
  is not part of the value.
* variable-length -- a leading count field states how many characters
  are actually present, and the definition states the maximum. The count
  field has to be wide enough to express that maximum: a count field
  that cannot reach the declared maximum makes the longest legal value
  unrepresentable, and it is a definition defect rather than a run-time
  one.

Where implementations go wrong. Padding with an octet that is itself in
the repertoire makes decoding ambiguous: a fixed-length field padded
with spaces cannot distinguish a value that legitimately ends in spaces
from a shorter one, so the round trip is lossy for exactly the values
nobody tests. A character outside the declared repertoire is refused
rather than substituted, because a substituted character is a silently
wrong value on the ground.

Stdlib only, offline, deterministic.
"""

__all__ = [
    "REPERTOIRES",
    "DEFAULT_PAD_OCTET",
    "repertoire_octets",
    "count_field_capacity",
    "minimum_count_bits",
    "validate_spec",
    "encode_character_string",
    "decode_character_string",
    "field_size_bits",
    "assess_character_string_definition",
]

# Repertoires a mission definition may name. Each maps to the inclusive
# octet range the repertoire admits. One octet carries one character.
REPERTOIRES = {
    "us-ascii": (0x00, 0x7F),
    "ascii-printable": (0x20, 0x7E),
    "ascii-visible": (0x21, 0x7E),
}

DEFAULT_PAD_OCTET = 0x00

_VALID_KINDS = ("fixed", "variable")
_VALID_PACKINGS = ("fixed-envelope", "packed")

# A count field wider than this is not a string length any more; the
# definition has confused a string with a bulk data field.
MAX_COUNT_BITS = 32


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def repertoire_octets(name):
    """Return the inclusive (low, high) octet range of a named repertoire."""
    if not isinstance(name, str):
        raise ValueError("repertoire name must be a string, got %r" % (name,))
    if name not in REPERTOIRES:
        raise ValueError(
            "unknown repertoire %r; the mission definition must name one of %s"
            % (name, ", ".join(sorted(REPERTOIRES)))
        )
    return REPERTOIRES[name]


def count_field_capacity(count_bits):
    """Return the largest character count a count field of this width states."""
    if not _is_int(count_bits):
        raise ValueError("count_bits must be an integer, got %r" % (count_bits,))
    if count_bits < 1:
        raise ValueError("count_bits must be at least 1, got %d" % count_bits)
    if count_bits > MAX_COUNT_BITS:
        raise ValueError(
            "count_bits %d exceeds the %d-bit ceiling; that is a bulk data field, "
            "not a character-string count" % (count_bits, MAX_COUNT_BITS)
        )
    return (1 << count_bits) - 1


def minimum_count_bits(max_length):
    """Return the narrowest count field able to express max_length characters."""
    if not _is_int(max_length):
        raise ValueError("max_length must be an integer, got %r" % (max_length,))
    if max_length < 0:
        raise ValueError("max_length must be non-negative, got %d" % max_length)
    bits = 1
    while (1 << bits) - 1 < max_length:
        bits += 1
        if bits > MAX_COUNT_BITS:
            raise ValueError(
                "max_length %d cannot be counted within %d bits" % (max_length, MAX_COUNT_BITS)
            )
    return bits


def validate_spec(spec):
    """Return a normalised character-string parameter definition.

    Keys: kind ('fixed' or 'variable'), repertoire, pad_octet (fixed only),
    length (fixed) or max_length and count_bits (variable).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    kind = spec.get("kind")
    if kind not in _VALID_KINDS:
        raise ValueError("spec['kind'] must be one of %s, got %r" % (_VALID_KINDS, kind))
    repertoire = spec.get("repertoire", "ascii-printable")
    low, high = repertoire_octets(repertoire)
    out = {"kind": kind, "repertoire": repertoire, "octet_range": (low, high)}
    if kind == "fixed":
        length = spec.get("length")
        if not _is_int(length):
            raise ValueError("a fixed-length definition needs an integer 'length'")
        if length < 1:
            raise ValueError("a fixed-length character string needs length >= 1, got %d" % length)
        pad = spec.get("pad_octet", DEFAULT_PAD_OCTET)
        if not _is_int(pad) or not 0 <= pad <= 0xFF:
            raise ValueError("pad_octet must be an octet value 0..255, got %r" % (pad,))
        out["length"] = length
        out["pad_octet"] = pad
        out["max_length"] = length
        out["count_bits"] = 0
    else:
        max_length = spec.get("max_length")
        if not _is_int(max_length):
            raise ValueError("a variable-length definition needs an integer 'max_length'")
        if max_length < 1:
            raise ValueError("max_length must be at least 1, got %d" % max_length)
        count_bits = spec.get("count_bits")
        if not _is_int(count_bits):
            raise ValueError("a variable-length definition needs an integer 'count_bits'")
        capacity = count_field_capacity(count_bits)
        if capacity < max_length:
            raise ValueError(
                "count field of %d bits reaches %d characters but the definition declares a "
                "maximum of %d; the longest legal value cannot be stated"
                % (count_bits, capacity, max_length)
            )
        if "pad_octet" in spec:
            raise ValueError("a variable-length character string is not padded; drop pad_octet")
        out["max_length"] = max_length
        out["count_bits"] = count_bits
        out["count_capacity"] = capacity
    return out


def _check_characters(text, low, high, repertoire):
    if not isinstance(text, str):
        raise ValueError("text must be a string, got %r" % (type(text).__name__,))
    octets = []
    for index, char in enumerate(text):
        point = ord(char)
        if point < low or point > high:
            raise ValueError(
                "character at index %d (code point %d) is outside the %s repertoire "
                "[%d, %d]; a value is refused, never substituted"
                % (index, point, repertoire, low, high)
            )
        octets.append(point)
    return octets


def encode_character_string(text, spec):
    """Encode a value into the octets the parameter occupies on the wire."""
    definition = validate_spec(spec)
    low, high = definition["octet_range"]
    body = _check_characters(text, low, high, definition["repertoire"])
    if definition["kind"] == "fixed":
        length = definition["length"]
        if len(body) > length:
            raise ValueError(
                "value of %d characters does not fit the fixed field of %d; truncation would "
                "change the value" % (len(body), length)
            )
        pad = definition["pad_octet"]
        return {
            "octets": body + [pad] * (length - len(body)),
            "count": None,
            "padding_octets": length - len(body),
        }
    max_length = definition["max_length"]
    if len(body) > max_length:
        raise ValueError(
            "value of %d characters exceeds the declared maximum of %d"
            % (len(body), max_length)
        )
    return {"octets": list(body), "count": len(body), "padding_octets": 0}


def decode_character_string(octets, spec, count=None):
    """Recover the value from the octets a parameter occupies."""
    definition = validate_spec(spec)
    if not isinstance(octets, (list, tuple)):
        raise ValueError("octets must be a sequence of integers")
    values = []
    for index, item in enumerate(octets):
        if not _is_int(item) or not 0 <= item <= 0xFF:
            raise ValueError("octet at index %d is not a value 0..255: %r" % (index, item))
        values.append(item)
    low, high = definition["octet_range"]
    if definition["kind"] == "fixed":
        if count is not None:
            raise ValueError("a fixed-length field carries no count; its length is the definition")
        length = definition["length"]
        if len(values) != length:
            raise ValueError(
                "fixed field holds %d octets, the definition declares %d" % (len(values), length)
            )
        pad = definition["pad_octet"]
        end = len(values)
        while end > 0 and values[end - 1] == pad:
            end -= 1
        body = values[:end]
        padding = length - end
        ambiguous = low <= pad <= high
    else:
        if count is None:
            raise ValueError("a variable-length field needs its leading count to be decoded")
        if not _is_int(count) or count < 0:
            raise ValueError("count must be a non-negative integer, got %r" % (count,))
        if count > definition["max_length"]:
            raise ValueError(
                "count %d exceeds the declared maximum of %d" % (count, definition["max_length"])
            )
        if count > len(values):
            raise ValueError(
                "count %d states more characters than the %d octets present"
                % (count, len(values))
            )
        body = values[:count]
        padding = 0
        ambiguous = False
    for index, point in enumerate(body):
        if point < low or point > high:
            raise ValueError(
                "octet at index %d (value %d) is outside the %s repertoire"
                % (index, point, definition["repertoire"])
            )
    return {
        "value": "".join(chr(point) for point in body),
        "padding_octets": padding,
        "pad_in_repertoire": ambiguous,
    }


def field_size_bits(spec, packing="fixed-envelope", text=None):
    """Return the bit width the parameter occupies under a packing rule."""
    definition = validate_spec(spec)
    if packing not in _VALID_PACKINGS:
        raise ValueError("packing must be one of %s, got %r" % (_VALID_PACKINGS, packing))
    if definition["kind"] == "fixed":
        return 8 * definition["length"]
    if packing == "fixed-envelope":
        return definition["count_bits"] + 8 * definition["max_length"]
    if text is None:
        raise ValueError("a packed variable-length field needs the value to size it")
    encoded = encode_character_string(text, spec)
    return definition["count_bits"] + 8 * len(encoded["octets"])


def assess_character_string_definition(spec, samples=None):
    """Assess a definition against representative values and report findings."""
    definition = validate_spec(spec)
    findings = []
    low, high = definition["octet_range"]
    if definition["kind"] == "fixed" and low <= definition["pad_octet"] <= high:
        findings.append(
            "pad octet %d lies inside the %s repertoire, so a value ending in that character "
            "cannot be told from padding on decode"
            % (definition["pad_octet"], definition["repertoire"])
        )
    if definition["kind"] == "variable":
        needed = minimum_count_bits(definition["max_length"])
        if definition["count_bits"] > needed + 8:
            findings.append(
                "count field of %d bits is far wider than the %d bits the declared maximum of "
                "%d needs" % (definition["count_bits"], needed, definition["max_length"])
            )
    accepted = []
    rejected = []
    longest = 0
    for sample in samples or []:
        try:
            encoded = encode_character_string(sample, spec)
        except ValueError as exc:
            rejected.append({"value": sample, "reason": str(exc)})
            continue
        accepted.append(encoded)
        longest = max(longest, len(sample))
    if rejected:
        findings.append("%d of %d sample values are refused by the definition"
                        % (len(rejected), len(samples or [])))
    if definition["kind"] == "fixed" and accepted and longest * 2 <= definition["length"]:
        findings.append(
            "the longest sample uses %d of %d octets; over half the field is padding on every "
            "occurrence" % (longest, definition["length"])
        )
    return {
        "definition": definition,
        "envelope_bits": field_size_bits(spec, "fixed-envelope"),
        "accepted": accepted,
        "rejected": rejected,
        "longest_sample": longest,
        "findings": findings,
        "usable": not rejected,
    }
