#!/usr/bin/env python3
"""The clause-obligation binding a leaf may declare in its front matter.

    clauses:
      - standard: ECSS-E-ST-50C Rev.2
        clause: 5.6.11.8
        items: [a, b]
        relation: implements

A citation says which clause a leaf is about. A binding says which lettered
items of that clause the leaf makes a practitioner discharge, and how:

    implements  the leaf makes the practitioner DO the item
    verifies    the leaf makes the practitioner CHECK that the item was met

`cites-clause` is reserved and refused. A leaf that only cites a clause says
so in its prose; a binding is a claim about obligations, and a claim with no
obligation in it is the defect this key exists to remove.

ONE MODULE, TWO READERS
-----------------------
The key is read by scripts/spec_lint.py (gate 1, which parses front matter
with PyYAML) and by tools/obligations/obligations_gate.py (stdlib only, like
every tool here). Both call validate() below, so the two refuse the same
things for the same reasons. A rule written twice drifts; this one is written
once.

The stdlib reader, read_clauses(), is deliberately narrow: it reads the one
shape documented above and refuses anything else by name rather than guessing.
test_obligations.py cross-checks it against PyYAML and against the two other
front-matter readers in this repository whenever they can be imported, so a
binding cannot mean one thing to the gate and another to a host.

YAML TYPES THE READER KEEPS
---------------------------
An unquoted `clause: 5.10` is the NUMBER 5.1 to YAML, and `clause: 5` is an
integer. validate() refuses both with the fix (quote it), because a clause
number that has been through a float has lost a digit nobody can recover.
Likewise `items: [no]` is a boolean. The reader resolves those scalars the way
PyYAML does so that the gate and the lint see the same value.

stdlib only; Python 3.9 through 3.14.
"""

import re
from collections import namedtuple

RELATIONS = ("implements", "verifies")
RESERVED_RELATIONS = ("cites-clause",)
ENTRY_KEYS = ("standard", "clause", "items", "relation")

# An ECSS designation with its issue letter, and its revision when it has
# one: ECSS-E-ST-50C Rev.2, ECSS-E-ST-70-41C, ECSS-Q-ST-20C Rev.2 Corr.1.
STANDARD_RE = re.compile(
    r"^ECSS-[A-Z]-(?:ST|AS|HB|TM)-\d{2}(?:-\d{2})*[A-Z]"
    r"(?: Rev\.\d+)?(?: Corr\.\d+)?$")
# The same designation written with the spaced revision the ESA export uses
# ("Rev. 2"). Recognised only to say how to fix it.
_SPACED_REV_RE = re.compile(r"\b(Rev|Corr)\.\s+(\d+)")
# A dotted clause number: 5, 5.3, 5.6.11.8.
CLAUSE_RE = re.compile(r"^\d+(?:\.\d+)*$")
# An item letter. ECSS letters items a..z and then aa, bb, cc, ... .
ITEM_RE = re.compile(r"^([a-z])\1?$")

Item = namedtuple("Item", "standard clause item relation entry")
Refusal = namedtuple("Refusal", "subject reason")


def item_label(standard, clause, item):
    """The locator a writer reads and the Obligations table carries."""
    return "%s %s%s" % (standard, clause, item)


def standard_problem(value):
    """None when value is a well-formed designation, else the reason."""
    if not isinstance(value, str):
        return "standard must be text, got %r" % (value,)
    if STANDARD_RE.match(value):
        return None
    fixed = _SPACED_REV_RE.sub(r"\1.\2", re.sub(r"\s+", " ", value.strip()))
    if fixed != value and STANDARD_RE.match(fixed):
        return ("standard %r: write the revision without a space, as %r"
                % (value, fixed))
    return ("standard %r is not an ECSS designation with its issue letter "
            "(and revision, when it has one), e.g. 'ECSS-E-ST-50C Rev.2'"
            % (value,))


def clause_problem(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return "clause must be a dotted clause number, got %r" % (value,)
    if not isinstance(value, str):
        return ("clause was read as the number %r, not as text: quote it "
                "(clause: \"5.10\") -- YAML reads an unquoted 5.10 as 5.1 "
                "and the lost digit cannot be recovered" % (value,))
    if CLAUSE_RE.match(value):
        return None
    if re.match(r"^\d+(?:\.\d+)*[a-z]{1,2}$", value):
        return ("clause %r carries an item letter: the clause goes in "
                "clause, the letters in items" % (value,))
    return "clause %r is not a dotted clause number, e.g. 5.6.11.8" % (value,)


def item_problem(value):
    if isinstance(value, bool):
        return ("item was read as the boolean %r: quote it -- YAML reads "
                "yes/no/on/off as true or false" % (value,))
    if not isinstance(value, str) or not ITEM_RE.match(value):
        return ("item %r is not an item letter (a..z, or a doubled letter "
                "such as aa)" % (value,))
    return None


def _as_written(entry):
    """The items an entry declares, spelled as written, for a refusal line.

    A refusal must name the item even when the entry around it is broken,
    so this renders whatever the entry carries rather than what validates.
    """
    std = entry.get("standard", "?")
    clause = entry.get("clause", "?")
    letters = entry.get("items")
    if isinstance(letters, list) and letters:
        return ", ".join(item_label(std, clause, x) for x in letters)
    return "%s %s" % (std, clause)


def validate(value):
    """Validate an already-parsed `clauses` value.

    Returns (items, refusals). `items` holds every item whose standard,
    clause and letter are well formed -- including those whose entry is
    refused for another reason (a reserved relation, a duplicate), so a
    caller matching table rows does not report the same defect twice.
    Each Item carries `relation` (None when the relation was refused).
    Every refusal's subject names the entry and the item(s) it declares.
    """
    refusals = []
    items = []
    if value is None:
        return items, [Refusal("clauses", "declared with no entries: omit "
                               "the key, or bind at least one clause")]
    if not isinstance(value, list):
        return items, [Refusal("clauses", "must be a list of mappings "
                               "(standard, clause, items, relation), got %s"
                               % type(value).__name__)]
    if not value:
        return items, [Refusal("clauses", "is an empty list: omit the key, "
                               "or bind at least one clause")]
    seen = {}
    for i, entry in enumerate(value):
        where = "clauses[%d]" % i
        if not isinstance(entry, dict):
            refusals.append(Refusal(where, "an entry must be a mapping with "
                                    "standard, clause, items and relation; "
                                    "got %r" % (entry,)))
            continue
        subject = "%s (%s)" % (where, _as_written(entry))
        extra = sorted(str(k) for k in entry if k not in ENTRY_KEYS)
        missing = [k for k in ENTRY_KEYS if k not in entry]
        if extra:
            refusals.append(Refusal(subject, "unknown key(s) %s: an entry "
                                    "carries exactly standard, clause, "
                                    "items and relation" % ", ".join(extra)))
        if missing:
            refusals.append(Refusal(subject, "missing key(s) %s"
                                    % ", ".join(missing)))
        std = entry.get("standard")
        clause = entry.get("clause")
        letters = entry.get("items")
        relation = entry.get("relation")
        std_bad = standard_problem(std) if "standard" in entry else "missing"
        clause_bad = clause_problem(clause) if "clause" in entry else "missing"
        if "standard" in entry and std_bad:
            refusals.append(Refusal(subject, std_bad))
        if "clause" in entry and clause_bad:
            refusals.append(Refusal(subject, clause_bad))
        good_letters = []
        if "items" in entry:
            if not isinstance(letters, list):
                refusals.append(Refusal(subject, "items must be a list of "
                                        "item letters, e.g. items: [a, b]; "
                                        "got %r" % (letters,)))
            elif not letters:
                refusals.append(Refusal(subject, "items is empty: a binding "
                                        "names at least one item"))
            else:
                for letter in letters:
                    bad = item_problem(letter)
                    if bad:
                        refusals.append(Refusal(subject, bad))
                    else:
                        good_letters.append(letter)
        rel_ok = False
        if "relation" in entry:
            if relation in RESERVED_RELATIONS:
                refusals.append(Refusal(subject, "relation %r is reserved and "
                                        "refused: a binding says whether the "
                                        "leaf implements or verifies each "
                                        "item" % (relation,)))
            elif relation not in RELATIONS:
                refusals.append(Refusal(subject, "unknown relation %r: use "
                                        "implements or verifies"
                                        % (relation,)))
            else:
                rel_ok = True
        if std_bad or clause_bad:
            continue
        for letter in good_letters:
            key = (std, clause, letter)
            label = item_label(std, clause, letter)
            if key in seen:
                where_twice = (("twice in %s" % where) if seen[key] == where
                               else "in %s and %s" % (seen[key], where))
                refusals.append(Refusal(label, "declared %s: declare each "
                                        "item once, with the relation of the "
                                        "step that anchors it" % where_twice))
                continue
            seen[key] = where
            items.append(Item(std, clause, letter,
                              relation if rel_ok else None, i))
    return items, refusals


# ---------------------------------------------------------------------------
# the stdlib reader
# ---------------------------------------------------------------------------

class BindingSyntaxError(ValueError):
    """The `clauses` block is not in the one shape this reader accepts."""


_BOOL_TRUE = ("yes", "Yes", "YES", "true", "True", "TRUE", "on", "On", "ON")
_BOOL_FALSE = ("no", "No", "NO", "false", "False", "FALSE", "off", "Off", "OFF")
_INT_RE = re.compile(r"^[-+]?(?:0|[1-9][0-9_]*)$")
_FLOAT_RE = re.compile(r"^[-+]?[0-9][0-9_]*\.[0-9_]*(?:[eE][-+][0-9]+)?$")
_TOP_KEY_RE = re.compile(r"^(\"[^\"]*\"|'[^']*'|[^\s:#'\"][^:#]*?)\s*:(?:\s|$)")
_NESTED_CLAUSES_RE = re.compile(r"^[ \t]+clauses\s*:\s*(?:#.*)?$")
_ENTRY_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:(?:\s+(.*))?$")


def _strip_comment(text):
    """Drop a ` # comment` that sits outside quotes."""
    quote = None
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
            return text[:i].rstrip()
    return text.rstrip()


def _split_flow(body):
    parts, buf, quote = [], [], None
    for ch in body:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
        elif ch in "[]{}":
            raise BindingSyntaxError("nested collections are not accepted "
                                     "inside a flow list")
        elif ch == ",":
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    last = "".join(buf).strip()
    if last or parts:
        parts.append(last)
    if any(p == "" for p in parts):
        raise BindingSyntaxError("empty element in a flow list")
    return parts


def scalar(text):
    """Resolve one scalar the way PyYAML's safe loader resolves it here."""
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] == "'":
        return text[1:-1].replace("''", "'")
    if len(text) >= 2 and text[0] == text[-1] == '"':
        body = text[1:-1]
        if "\\" in body.replace('\\"', "").replace("\\\\", ""):
            raise BindingSyntaxError("escape sequences are not accepted in "
                                     "a binding value: %r" % text)
        return body.replace('\\"', '"').replace("\\\\", "\\")
    if text[:1] in ("'", '"'):
        raise BindingSyntaxError("unterminated quoted value: %r" % text)
    if text.startswith("[") or text.endswith("]"):
        if not (text.startswith("[") and text.endswith("]")):
            raise BindingSyntaxError("unterminated flow list: %r" % text)
        inner = text[1:-1].strip()
        return [scalar(p) for p in _split_flow(inner)] if inner else []
    if text.startswith("{") or text[:1] in ("&", "*", "!", "|", ">", "%", "@", "`"):
        raise BindingSyntaxError("value %r uses YAML this reader does not "
                                 "accept in a binding" % text)
    if text in ("", "~", "null", "Null", "NULL"):
        return None
    if text in _BOOL_TRUE:
        return True
    if text in _BOOL_FALSE:
        return False
    if _INT_RE.match(text):
        return int(text.replace("_", ""))
    if _FLOAT_RE.match(text):
        return float(text.replace("_", ""))
    return text


def front_matter_lines(text):
    """(front matter lines, index of the closing fence) or (None, None).

    The fence is a line that is exactly `---`, which is what every leaf in
    this corpus writes."""
    lines = text.split("\n")
    if not lines or lines[0].rstrip() != "---":
        return None, None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            return lines[1:i], i
    return None, None


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _meaningful(line):
    s = line.strip()
    return bool(s) and not s.startswith("#")


def read_clauses(front):
    """Read the top-level `clauses` key from front matter lines.

    Returns (present, value). Raises BindingSyntaxError, naming the front
    matter line, when the key is present in a shape this reader refuses.
    """
    heads = []
    for n, line in enumerate(front):
        m = _TOP_KEY_RE.match(line)
        if m and m.group(1).strip("'\"") == "clauses":
            heads.append(n)
        elif _NESTED_CLAUSES_RE.match(line):
            raise BindingSyntaxError(
                "front matter line %d: clauses is nested under another key; "
                "a binding is a top-level key, or no host will read it"
                % (n + 2))
    if not heads:
        return False, None
    if len(heads) > 1:
        raise BindingSyntaxError(
            "clauses is declared %d times (front matter lines %s); YAML keeps "
            "only the last, so the others would be silently discarded"
            % (len(heads), ", ".join(str(h + 2) for h in heads)))
    start = heads[0]
    after = _strip_comment(front[start].split(":", 1)[1]).strip()
    if after:
        if after == "[]":
            return True, []
        raise BindingSyntaxError(
            "front matter line %d: write clauses as a block list, one "
            "'- standard: ...' entry per clause (see docs/OBLIGATIONS.md), not "
            "inline" % (start + 2))
    block = []
    for n in range(start + 1, len(front)):
        line = front[n]
        if not line.strip():
            continue
        lead = line[: len(line) - len(line.lstrip(" \t"))]
        if "\t" in lead:
            raise BindingSyntaxError("front matter line %d: tab indentation "
                                     "(YAML indents with spaces)" % (n + 2))
        if _indent(line) == 0 and not line.startswith(("- ", "#")):
            break
        block.append((n + 2, line))
    rows = [(n, l) for n, l in block if _meaningful(l)]
    if not rows:
        return True, None
    dash = _indent(rows[0][1])
    entries = []
    current = None
    key_col = None
    for lineno, line in rows:
        ind = _indent(line)
        body = line[ind:]
        if ind == dash and (body.startswith("- ") or body == "-"):
            rest = body[1:]
            if not rest.strip():
                raise BindingSyntaxError("front matter line %d: an entry "
                                         "starts on its own line; write "
                                         "'- standard: ...'" % lineno)
            key_col = ind + 1 + (len(rest) - len(rest.lstrip(" ")))
            rest = rest.strip()
            m = _ENTRY_KEY_RE.match(rest)
            if m is None:
                entries.append(scalar(_strip_comment(rest)))
                current = None
                continue
            current = {}
            entries.append(current)
            _put(current, m, lineno)
            continue
        if current is None or ind != key_col:
            raise BindingSyntaxError(
                "front matter line %d: unexpected indentation under clauses "
                "(each entry's keys line up under its first key)" % lineno)
        m = _ENTRY_KEY_RE.match(body.rstrip())
        if m is None:
            raise BindingSyntaxError("front matter line %d: expected "
                                     "'key: value'" % lineno)
        _put(current, m, lineno)
    return True, entries


def _put(entry, m, lineno):
    key, raw = m.group(1), m.group(2)
    if raw is not None and _strip_comment(raw) != raw.rstrip():
        # PyYAML drops a trailing comment; tools/evidence/frontmatter.py keeps
        # it as part of the value. A binding that means one thing to one
        # reader and another to the next is refused rather than read.
        raise BindingSyntaxError("front matter line %d: a trailing comment "
                                 "on a binding line; the repository's "
                                 "readers disagree about it, so put the "
                                 "comment on its own line" % lineno)
    if key in entry:
        raise BindingSyntaxError("front matter line %d: key %r appears twice "
                                 "in one entry; YAML keeps only the last"
                                 % (lineno, key))
    if raw is None or not raw.strip():
        raise BindingSyntaxError("front matter line %d: %s has no value on "
                                 "its line; write it inline, e.g. "
                                 "items: [a, b]" % (lineno, key))
    entry[key] = scalar(_strip_comment(raw))


def read_leaf(text):
    """(present, value, syntax_refusals) for a whole SKILL.md text."""
    front, _end = front_matter_lines(text)
    if front is None:
        return False, None, []
    try:
        present, value = read_clauses(front)
    except BindingSyntaxError as exc:
        return True, None, [Refusal("clauses", "malformed binding: %s" % exc)]
    return present, value, []
