"""File format specification for a simulator exchange file.

Anchor: ECSS-E-ST-40-08C clause 5.7.2.1 (file format specification).
Paraphrased into an implementable procedure; no standard text is
reproduced. The clause carries one normative item: an exchange file
carries a specification of its own format, and a reader accepts the file
only when that specification is present, complete and one the reader
supports.

What this module does
---------------------
It parses the declaration block of an exchange file supplied as text --
the module never opens a path of its own -- and grades it:

* the block is the first thing in the file and is delimited;
* the required keys are all present, each exactly once;
* the format identifier is the one the reader knows;
* the version is a two-part number the reader's supported range covers,
  with the major part deciding compatibility and the minor part
  deciding whether unknown trailing content may be skipped;
* the character encoding and the line ending are from the declared set;
* the declared section list is non-empty, free of repeats, and every
  section the format requires is in it, in the declared order.
"""

__all__ = [
    "NORMATIVE_ITEM_COUNT",
    "NORMATIVE_ITEMS",
    "FORMAT_IDENTIFIER",
    "REQUIRED_KEYS",
    "SUPPORTED_MAJOR",
    "MIN_SUPPORTED_MINOR",
    "MAX_SUPPORTED_MINOR",
    "SUPPORTED_ENCODINGS",
    "SUPPORTED_LINE_ENDINGS",
    "REQUIRED_SECTIONS",
    "parse_version",
    "version_support",
    "parse_declaration_block",
    "validate_sections",
    "assess_file_format",
]

NORMATIVE_ITEM_COUNT = 1

NORMATIVE_ITEMS = (
    ("FF-01", "the exchange file declares a complete and supported format specification"),
)

FORMAT_IDENTIFIER = "simulator-exchange"

REQUIRED_KEYS = ("format", "version", "encoding", "line_ending", "sections")

SUPPORTED_MAJOR = 2
MIN_SUPPORTED_MINOR = 0
MAX_SUPPORTED_MINOR = 4

SUPPORTED_ENCODINGS = ("utf-8", "utf-16")
SUPPORTED_LINE_ENDINGS = ("lf", "crlf")

REQUIRED_SECTIONS = ("header", "catalogue", "assembly", "schedule")

_BLOCK_OPEN = "#%format-begin"
_BLOCK_CLOSE = "#%format-end"


def _require_text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def parse_version(text):
    """Return the (major, minor) pair of a two-part version string."""
    raw = _require_text(text, "version")
    parts = raw.split(".")
    if len(parts) != 2:
        raise ValueError("version %r must have exactly two dot-separated parts" % (text,))
    numbers = []
    for index, part in enumerate(parts):
        if not part or not part.isdigit():
            raise ValueError(
                "version part %d of %r must be a decimal number" % (index + 1, text)
            )
        if len(part) > 1 and part[0] == "0":
            raise ValueError("version part %d of %r must not be zero padded" % (index + 1, text))
        numbers.append(int(part))
    return (numbers[0], numbers[1])


def version_support(version_text):
    """Return the support verdict for a declared format version."""
    major, minor = parse_version(version_text)
    findings = []
    if major != SUPPORTED_MAJOR:
        findings.append(
            "major version %d is not the supported major version %d" % (major, SUPPORTED_MAJOR)
        )
    elif minor < MIN_SUPPORTED_MINOR:
        findings.append("minor version %d predates the supported range" % minor)
    elif minor > MAX_SUPPORTED_MINOR:
        findings.append(
            "minor version %d is ahead of the supported range, which ends at %d"
            % (minor, MAX_SUPPORTED_MINOR)
        )
    return {
        "major": major,
        "minor": minor,
        "supported": not findings,
        # A newer minor inside the same major is readable with unknown
        # trailing content skipped; a different major never is.
        "forward_readable": major == SUPPORTED_MAJOR,
        "findings": findings,
    }


def parse_declaration_block(text):
    """Return the key/value declaration block found at the head of the file text."""
    if not isinstance(text, str):
        raise ValueError("file text must be a string, got %r" % (type(text).__name__,))
    if not text.strip():
        raise ValueError("file text must not be empty")
    lines = text.replace("\r\n", "\n").split("\n")
    start = None
    for index, line in enumerate(lines):
        if line.strip():
            start = index
            break
    if start is None or lines[start].strip() != _BLOCK_OPEN:
        raise ValueError(
            "the file does not open with the format declaration marker %r" % _BLOCK_OPEN
        )
    entries = []
    closed = False
    for line in lines[start + 1:]:
        stripped = line.strip()
        if stripped == _BLOCK_CLOSE:
            closed = True
            break
        if not stripped:
            continue
        if stripped.startswith("#") and not stripped.startswith("#%"):
            continue
        if ":" not in stripped:
            raise ValueError("declaration line %r is not a key and value pair" % stripped)
        key, value = stripped.split(":", 1)
        entries.append((key.strip().lower(), value.strip()))
    if not closed:
        raise ValueError("the format declaration block is never closed with %r" % _BLOCK_CLOSE)
    block = {}
    repeated = []
    for key, value in entries:
        if not key:
            raise ValueError("a declaration line carries an empty key")
        if key in block:
            repeated.append(key)
        block[key] = value
    return {"block": block, "repeated": sorted(set(repeated)), "entry_count": len(entries)}


def validate_sections(declared):
    """Return the verdict on a declared section list."""
    if isinstance(declared, str):
        names = [part.strip().lower() for part in declared.split(",") if part.strip()]
    elif isinstance(declared, (list, tuple)):
        names = [_require_text(item, "section name").lower() for item in declared]
    else:
        raise ValueError("declared sections must be a comma-separated string or a sequence")
    findings = []
    if not names:
        findings.append("the declared section list is empty")
    seen = []
    repeated = []
    for name in names:
        if name in seen:
            repeated.append(name)
        else:
            seen.append(name)
    if repeated:
        findings.append("section(s) declared more than once: %s" % ", ".join(sorted(set(repeated))))
    missing = [name for name in REQUIRED_SECTIONS if name not in seen]
    if missing:
        findings.append("required section(s) absent: %s" % ", ".join(missing))
    present_required = [name for name in seen if name in REQUIRED_SECTIONS]
    expected_order = [name for name in REQUIRED_SECTIONS if name in seen]
    if present_required != expected_order:
        findings.append(
            "required sections are declared as %s but the format orders them %s"
            % (", ".join(present_required), ", ".join(expected_order))
        )
    return {
        "declared": names,
        "missing": missing,
        "repeated": sorted(set(repeated)),
        "extra": [name for name in seen if name not in REQUIRED_SECTIONS],
        "compliant": not findings,
        "findings": findings,
    }


def assess_file_format(text):
    """Grade the format declaration of an exchange file supplied as text."""
    parsed = parse_declaration_block(text)
    block = parsed["block"]
    findings = []
    if parsed["repeated"]:
        findings.append("declaration key(s) given more than once: %s" % ", ".join(parsed["repeated"]))
    missing_keys = [key for key in REQUIRED_KEYS if key not in block]
    if missing_keys:
        findings.append("declaration key(s) absent: %s" % ", ".join(missing_keys))

    identifier = block.get("format")
    if identifier is not None and identifier.lower() != FORMAT_IDENTIFIER:
        findings.append(
            "format identifier %r is not the one this reader accepts (%r)"
            % (identifier, FORMAT_IDENTIFIER)
        )

    version = None
    if "version" in block:
        try:
            version = version_support(block["version"])
        except ValueError as exc:
            findings.append(str(exc))
        else:
            findings.extend(version["findings"])

    encoding = block.get("encoding")
    if encoding is not None and encoding.lower() not in SUPPORTED_ENCODINGS:
        findings.append(
            "encoding %r is outside the declared set %s"
            % (encoding, ", ".join(SUPPORTED_ENCODINGS))
        )

    line_ending = block.get("line_ending")
    if line_ending is not None and line_ending.lower() not in SUPPORTED_LINE_ENDINGS:
        findings.append(
            "line ending %r is outside the declared set %s"
            % (line_ending, ", ".join(SUPPORTED_LINE_ENDINGS))
        )

    sections = None
    if "sections" in block:
        sections = validate_sections(block["sections"])
        findings.extend(sections["findings"])

    item = {
        "id": NORMATIVE_ITEMS[0][0],
        "title": NORMATIVE_ITEMS[0][1],
        "status": "satisfied" if not findings else "violated",
        "findings": list(findings),
    }
    return {
        "items": [item],
        "item_count": 1,
        "declaration": block,
        "version": version,
        "sections": sections,
        "missing_keys": missing_keys,
        "violations": [] if not findings else [item["id"]],
        "findings": findings,
        "compliant": not findings,
    }
