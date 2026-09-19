"""A deliberately small YAML reader for the two file shapes this bundle needs.

This is NOT a general YAML implementation and must not be used as one. It
exists so the evidence bundle depends on the Python standard library alone:
an outside reviewer can run the router evidence with a stock `python3` and
nothing installed.

It reads exactly two shapes.

1. SKILL.md front matter -- a block mapping whose values are single-line
   plain scalars, single- or double-quoted scalars (which may be wrapped
   across several lines the way PyYAML's emitter wraps them), a nested
   mapping, a block sequence (indented or not, as YAML allows both) or an
   inline flow sequence such as `tags: [a, b, c]`. Keys may be quoted.

2. A router case file -- a block mapping with a `tasks:` sequence whose items
   are mappings of quoted or plain scalars.

Anything outside that subset raises `YamlSubsetError` rather than guessing.
Silence would be worse than a stack trace here: this code decides what text
the router scores, so a value it mis-reads becomes a wrong Hit@1 number.

Equivalence with PyYAML's `safe_load` on the two shapes above was checked
field by field over the whole tree when the bundle was generated; the
procedure is in README.md under "How this bundle was produced".
"""

import re

__all__ = ["YamlSubsetError", "load_mapping", "read_frontmatter", "read_tasks"]


class YamlSubsetError(ValueError):
    """Raised when input uses YAML this reader deliberately does not cover."""


_KEY_RE = re.compile(
    r"^(?P<indent> *)(?P<key>\"[^\"]*\"|'[^']*'|[A-Za-z0-9_.-]+):(?P<rest>.*)$")
_DASH_RE = re.compile(r"^(?P<indent> *)- ")

# Double-quoted escape sequences, YAML 1.1 core set.
_ESCAPES = {
    "0": "\0", "a": "\a", "b": "\b", "t": "\t", "\t": "\t", "n": "\n",
    "v": "\v", "f": "\f", "r": "\r", "e": "\x1b", " ": " ", '"': '"',
    "/": "/", "\\": "\\", "N": "\x85", "_": "\xa0",
    "L": "\u2028", "P": "\u2029",
}


def _decode_double(text):
    """Decode escape sequences inside an already-folded double-quoted scalar."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        i += 1
        if i >= n:
            raise YamlSubsetError("trailing backslash in double-quoted scalar")
        esc = text[i]
        if esc in ("x", "u", "U"):
            width = {"x": 2, "u": 4, "U": 8}[esc]
            digits = text[i + 1:i + 1 + width]
            if len(digits) != width:
                raise YamlSubsetError("truncated \\%s escape" % esc)
            out.append(chr(int(digits, 16)))
            i += 1 + width
            continue
        if esc not in _ESCAPES:
            raise YamlSubsetError("unsupported escape \\%s" % esc)
        out.append(_ESCAPES[esc])
        i += 1
    return "".join(out)


def _trailing_backslashes(text):
    count = 0
    while count < len(text) and text[len(text) - 1 - count] == "\\":
        count += 1
    return count


def _indent_of(line):
    return len(line) - len(line.lstrip(" "))


def _next_content(lines, i):
    """Index of the next line that is neither blank nor a whole-line comment."""
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped and not stripped.startswith("#"):
            return i
        i += 1
    return None


def _scan_quoted(lines, line_no, start_col, quote):
    """Read a quoted scalar whose opening quote is at `start_col`.

    Returns (value, next_line_no). Handles the folding PyYAML's emitter
    produces when it wraps a long scalar: a line break folds to one space,
    and a break escaped by a trailing backslash folds to nothing.
    """
    pieces = []
    i = line_no
    col = start_col + 1
    closed = False
    while i < len(lines):
        line = lines[i]
        j = col
        end = None
        while j < len(line):
            ch = line[j]
            if quote == '"' and ch == "\\":
                j += 2
                continue
            if ch == quote:
                if quote == "'" and j + 1 < len(line) and line[j + 1] == "'":
                    j += 2
                    continue
                end = j
                break
            j += 1
        if end is None:
            pieces.append(line[col:])
            i += 1
            col = 0
            continue
        pieces.append(line[col:end])
        tail = line[end + 1:].strip()
        if tail and not tail.startswith("#"):
            raise YamlSubsetError("unexpected text after a quoted scalar on "
                                  "line %d: %r" % (i + 1, tail))
        closed = True
        break
    if not closed:
        raise YamlSubsetError("unterminated quoted scalar on line %d"
                              % (line_no + 1))

    folded = pieces[0]
    for piece in pieces[1:]:
        left = folded.rstrip(" \t")
        right = piece.strip(" \t")
        if right == "":
            raise YamlSubsetError("blank line inside a quoted scalar is not "
                                  "supported")
        if quote == '"' and _trailing_backslashes(left) % 2 == 1:
            folded = left[:-1] + right
        else:
            folded = left + " " + right
    if quote == '"':
        return _decode_double(folded), i + 1
    return folded.replace("''", "'"), i + 1


def _split_flow_items(body):
    """Split the inside of a flow sequence on top-level commas."""
    items = []
    buf = []
    depth = 0
    quote = None
    i = 0
    while i < len(body):
        ch = body[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < len(body):
                buf.append(body[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch in "[{":
            depth += 1
            buf.append(ch)
        elif ch in "]}":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            items.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    if quote:
        raise YamlSubsetError("unterminated quote inside a flow sequence")
    tail = "".join(buf)
    if tail.strip():
        items.append(tail)
    return [item.strip() for item in items]


def _plain_scalar(text):
    """Convert a single-line plain scalar to the value PyYAML would produce."""
    value = text.strip()
    cut = value.find(" #")
    if cut >= 0:
        value = value[:cut].rstrip()
    if value in ("", "~", "null", "Null", "NULL"):
        return None
    if value in ("true", "True", "TRUE", "yes", "Yes", "on", "On"):
        return True
    if value in ("false", "False", "FALSE", "no", "No", "off", "Off"):
        return False
    try:
        return int(value)
    except ValueError:
        return value


def _unquote(text):
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        inner = text[1:-1]
        return _decode_double(inner) if text[0] == '"' else inner.replace("''", "'")
    return _plain_scalar(text)


def _scalar_from_rest(lines, line_no, rest_col, rest):
    """Read the value that follows `key:` or `- `, possibly wrapping lines."""
    stripped = rest.lstrip()
    if stripped[:1] in ("'", '"'):
        col = rest_col + (len(rest) - len(stripped))
        return _scan_quoted(lines, line_no, col, stripped[0])
    if stripped.startswith("["):
        if not stripped.rstrip().endswith("]"):
            raise YamlSubsetError("multi-line flow sequence is not supported")
        return [_unquote(item) for item in
                _split_flow_items(stripped.rstrip()[1:-1])], line_no + 1
    if stripped.startswith("{"):
        raise YamlSubsetError("flow mapping is not supported")
    return _plain_scalar(stripped), line_no + 1


def _parse_mapping(lines, start, indent):
    """Parse a block mapping at column `indent`. Returns (dict, next line)."""
    mapping = {}
    i = start
    while True:
        at = _next_content(lines, i)
        if at is None:
            return mapping, len(lines)
        line = lines[at]
        here = _indent_of(line)
        if here < indent or _DASH_RE.match(line):
            return mapping, at
        if here > indent:
            raise YamlSubsetError("unexpected indent on line %d: %r"
                                  % (at + 1, line))
        match = _KEY_RE.match(line)
        if not match:
            raise YamlSubsetError("line %d is outside the supported subset: %r"
                                  % (at + 1, line))
        key = _unquote(match.group("key"))
        rest = match.group("rest")
        if rest.strip() == "" or rest.strip().startswith("#"):
            child = _next_content(lines, at + 1)
            if child is None:
                mapping[key] = None
                return mapping, len(lines)
            child_indent = _indent_of(lines[child])
            is_dash = bool(_DASH_RE.match(lines[child]))
            if child_indent > indent:
                if is_dash:
                    mapping[key], i = _parse_sequence(lines, child, child_indent)
                else:
                    mapping[key], i = _parse_mapping(lines, child, child_indent)
            elif child_indent == indent and is_dash:
                # A block sequence may sit at the same column as its key.
                mapping[key], i = _parse_sequence(lines, child, child_indent)
            else:
                mapping[key] = None
                i = at + 1
            continue
        mapping[key], i = _scalar_from_rest(lines, at, match.start("rest"), rest)
    return mapping, i


def _parse_sequence(lines, start, indent):
    """Parse a block sequence at column `indent`. Returns (list, next line)."""
    sequence = []
    i = start
    while True:
        at = _next_content(lines, i)
        if at is None:
            return sequence, len(lines)
        line = lines[at]
        here = _indent_of(line)
        if here < indent or not _DASH_RE.match(line):
            return sequence, at
        if here > indent:
            raise YamlSubsetError("unexpected indent on line %d: %r"
                                  % (at + 1, line))
        item_col = here + 2
        rest = line[item_col:]
        if _KEY_RE.match(" " * item_col + rest):
            # "- key: value" opens a mapping; re-align the line and recurse.
            shifted = list(lines)
            shifted[at] = " " * item_col + rest
            item, i = _parse_mapping(shifted, at, item_col)
            sequence.append(item)
            continue
        value, i = _scalar_from_rest(lines, at, item_col, rest)
        sequence.append(value)
    return sequence, i


def load_mapping(text):
    """Load a document that is a block mapping. Returns a dict."""
    lines = text.split("\n")
    start = 0
    while start < len(lines):
        stripped = lines[start].strip()
        if not stripped or stripped.startswith("#") or stripped == "---":
            start += 1
            continue
        break
    value, _ = _parse_mapping(lines, start, 0)
    if not isinstance(value, dict):
        raise YamlSubsetError("document is not a mapping")
    return value


def read_frontmatter(skill_text):
    """Split a SKILL.md into (front matter mapping, body text).

    The split is the same one the repository's own gate uses
    (`text.split("---", 2)`), so the body returned here is the body the gate
    scores, character for character.
    """
    if not skill_text.startswith("---"):
        return None, ""
    parts = skill_text.split("---", 2)
    body = parts[2] if len(parts) >= 3 else ""
    try:
        front = load_mapping(parts[1])
    except YamlSubsetError:
        return None, body
    if not isinstance(front, dict) or not front:
        return None, body
    return front, body


def read_tasks(text):
    """Read a router case file; returns the list under its `tasks:` key."""
    doc = load_mapping(text)
    tasks = doc.get("tasks")
    if not isinstance(tasks, list):
        raise YamlSubsetError("no 'tasks' sequence in this file")
    return tasks
