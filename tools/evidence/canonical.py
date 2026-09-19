#!/usr/bin/env python3
"""Canonical encoding and content digests for evidence records.

Everything an evidence record seals is hashed through ONE encoding, so a
verifier who was never present when the verdict was issued computes the same
digest from the same bytes.

json-c14n/1
-----------
* UTF-8, no byte-order mark.
* Object keys are strings, sorted by Unicode code point.
* No insignificant whitespace: separators are exactly "," and ":".
* ensure_ascii is off: a character is emitted as itself, never as an escape.
* Binary floats are REJECTED.  A float has no language-independent textual
  form, so every measurement a checker compares against a threshold travels
  as a decimal STRING produced by num() and read back with parse_num().
  int and bool pass through untouched.
* Non-finite values cannot appear, which follows from the float ban.

The file written to disk is pretty-printed for a human reader; the digest is
always taken over the canonical encoding of the parsed object, never over the
pretty bytes.  Reformatting a record on disk therefore cannot break its seal,
and re-ordering keys cannot forge one.
"""

import hashlib
import json

CANONICALIZATION = "json-c14n/1"
DIGEST_ALGORITHM = "sha256"


class CanonicalError(ValueError):
    """The object cannot be canonically encoded."""


def _check(node, path="$"):
    if isinstance(node, bool) or node is None or isinstance(node, int):
        return
    if isinstance(node, float):
        raise CanonicalError(
            "%s: binary float %r is not canonically encodable - carry the "
            "measurement as a decimal string via canonical.num()" % (path, node)
        )
    if isinstance(node, str):
        return
    if isinstance(node, (list, tuple)):
        for i, item in enumerate(node):
            _check(item, "%s[%d]" % (path, i))
        return
    if isinstance(node, dict):
        for key, value in node.items():
            if not isinstance(key, str):
                raise CanonicalError("%s: non-string key %r" % (path, key))
            _check(value, "%s.%s" % (path, key))
        return
    raise CanonicalError("%s: %s is not encodable" % (path, type(node).__name__))


def canonical_bytes(obj):
    """Return the json-c14n/1 encoding of obj."""
    _check(obj)
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def digest(obj):
    """Return 'sha256:<hex>' over the canonical encoding of obj."""
    return "%s:%s" % (DIGEST_ALGORITHM, hashlib.sha256(canonical_bytes(obj)).hexdigest())


def digest_bytes(data):
    """Return 'sha256:<hex>' over raw bytes."""
    return "%s:%s" % (DIGEST_ALGORITHM, hashlib.sha256(data).hexdigest())


def digest_file(path):
    """Return 'sha256:<hex>' over a file read in binary."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return "%s:%s" % (DIGEST_ALGORITHM, h.hexdigest())


def num(value):
    """Encode a finite real measurement as a shortest-round-trip decimal string."""
    f = float(value)
    if f != f or f in (float("inf"), float("-inf")):
        raise CanonicalError("non-finite measurement: %r" % (value,))
    return repr(f)


def parse_num(text):
    """Read back a string produced by num()."""
    return float(text)


def dumps_pretty(obj):
    """Human-readable serialisation for a record on disk."""
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
