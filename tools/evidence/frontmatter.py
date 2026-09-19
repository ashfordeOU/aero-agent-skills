#!/usr/bin/env python3
"""A deliberately small YAML front-matter reader.

The shipped gates parse front matter with PyYAML.  Anything that ships in this
repository is stdlib-only, so this module reads the narrow subset of YAML the
corpus actually uses: a mapping of scalars, one level of nested mappings, flow
sequences of scalars, and block sequences whose items are scalars or single-
level mappings.  It is not a YAML implementation and does not pretend to be.

tests/test_frontmatter.py cross-checks it against PyYAML over a sample of real
SKILL.md files whenever PyYAML happens to be importable, so the parser is
graded by something that does not share its own logic.  Where PyYAML is
absent the cross-check skips rather than passing vacuously.
"""

import re

_TRUE = ("true", "yes", "on")
_FALSE = ("false", "no", "off")


class FrontmatterError(ValueError):
    pass


def _scalar(text):
    text = text.strip()
    if text == "" or text == "~" or text.lower() == "null":
        return None
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        body = text[1:-1]
        if text[0] == '"':
            body = body.replace('\\"', '"').replace("\\\\", "\\").replace("\\n", "\n")
        else:
            body = body.replace("''", "'")
        return body
    low = text.lower()
    if low in _TRUE:
        return True
    if low in _FALSE:
        return False
    if re.fullmatch(r"[+-]?\d+", text):
        return int(text)
    if re.fullmatch(r"[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?", text):
        return float(text)
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_scalar(part) for part in _split_flow(inner)]
    return text


def _split_flow(text):
    """Split a flow sequence body on commas that sit outside quotes."""
    parts, buf, quote = [], [], None
    for ch in text:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            continue
        if ch == ",":
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    parts.append("".join(buf))
    return [p for p in (p.strip() for p in parts) if p != ""]


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _quoted_scalar_is_closed(text, quote):
    """True once an accumulated quoted scalar has met its closing quote."""
    text = text.strip()
    if len(text) < 2 or text[0] != quote:
        return True
    index = 1
    while index < len(text):
        char = text[index]
        if quote == '"' and char == "\\":
            index += 2
            continue
        if char == quote:
            return True
        index += 1
    return False


def parse_block(lines, base_indent):
    """Parse a block of 'key: value' lines at base_indent into a mapping."""
    result = {}
    index = 0
    while index < len(lines):
        raw = lines[index]
        if not raw.strip() or raw.lstrip().startswith("#"):
            index += 1
            continue
        if _indent(raw) < base_indent:
            break
        if _indent(raw) > base_indent:
            raise FrontmatterError("unexpected indent: %r" % raw)
        match = re.match(r"^\s*([^:#]+?)\s*:\s*(.*)$", raw)
        if not match:
            raise FrontmatterError("not a key: %r" % raw)
        key, rest = match.group(1), match.group(2)
        if rest.strip() and not rest.strip().startswith("#"):
            stripped = rest.strip()
            quote = stripped[0] if stripped[0] in ("'", '"') else None
            if quote and not _quoted_scalar_is_closed(stripped, quote):
                # A quoted scalar wrapped over several lines: 97 leaves in
                # this corpus write their description that way.  YAML folds
                # the breaks to single spaces.
                parts = [stripped]
                index += 1
                while index < len(lines):
                    nxt = lines[index].strip()
                    parts.append(nxt)
                    index += 1
                    if _quoted_scalar_is_closed(" ".join(parts), quote):
                        break
                result[key] = _scalar(" ".join(parts))
                continue
            result[key] = _scalar(rest)
            index += 1
            continue
        # Value is a nested block or a block sequence.
        index += 1
        child, consumed = _collect(lines[index:], base_indent)
        index += consumed
        result[key] = child
    return result


def _collect(lines, parent_indent):
    """Collect the child block that follows a bare 'key:' line.

    A block sequence may be indented under its key or sit flush with it -
    both are valid YAML, and this corpus uses both (3,023 leaves indent the
    standards list, 10 do not).  A collector that only understood the common
    style would refuse ten real files.
    """
    body = []
    consumed = 0
    for raw in lines:
        if not raw.strip():
            body.append(raw)
            consumed += 1
            continue
        indent = _indent(raw)
        if indent <= parent_indent:
            if indent == parent_indent and raw.lstrip().startswith("- "):
                body.append(raw)
                consumed += 1
                continue
            break
        body.append(raw)
        consumed += 1
    meaningful = [ln for ln in body if ln.strip() and not ln.lstrip().startswith("#")]
    if not meaningful:
        return None, consumed
    first = meaningful[0]
    child_indent = _indent(first)
    if first.lstrip().startswith("- "):
        return _sequence(meaningful, child_indent), consumed
    return parse_block(meaningful, child_indent), consumed


def _sequence(lines, indent):
    items = []
    current = None
    for raw in lines:
        if _indent(raw) == indent and raw.lstrip().startswith("- "):
            payload = raw.lstrip()[2:]
            if re.match(r"^[^:#]+:\s*(.*)$", payload) and not payload.strip().startswith(("'", '"')):
                key, _, rest = payload.partition(":")
                current = {key.strip(): _scalar(rest)}
                items.append(current)
            else:
                items.append(_scalar(payload))
                current = None
        elif current is not None and _indent(raw) > indent:
            key, _, rest = raw.strip().partition(":")
            current[key.strip()] = _scalar(rest)
        elif raw.strip():
            raise FrontmatterError("unparsable sequence line: %r" % raw)
    return items


def split(text):
    """Split a SKILL.md into (frontmatter_text, body_text)."""
    if not text.startswith("---"):
        raise FrontmatterError("no opening front-matter fence")
    end = text.find("\n---", 3)
    if end == -1:
        raise FrontmatterError("front matter is not closed")
    head = text[text.find("\n") + 1 : end]
    tail = text[end + 4 :]
    if tail.startswith("\n"):
        tail = tail[1:]
    return head, tail


def parse(text):
    """Parse a SKILL.md.  Returns (mapping, body_text)."""
    head, body = split(text)
    lines = head.split("\n")
    meaningful = [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]
    if not meaningful:
        return {}, body
    return parse_block(meaningful, _indent(meaningful[0])), body
