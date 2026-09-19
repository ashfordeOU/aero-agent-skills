#!/usr/bin/env python3
"""Deterministic word-shingle fingerprints (stdlib only, offline).

Shared by the source-index builder (tools/build_verbatim_index.py) and the
no-verbatim gate (tools/verbatim_gate.py) so that both sides of a comparison
are produced by exactly one implementation.

Method: winnowing (Schleimer, Wilkerson & Aiken 2003).

  * text -> lowercase word tokens that begin with a letter (markup,
    punctuation, line breaks and hyphenation noise are discarded, so a copy
    that survived a PDF-to-Markdown round trip still matches). Bare numbers
    are dropped on purpose: clause numbering, page numbers and tables of
    values are not the protected expression, and a run of digits matches
    across unrelated documents by coincidence -- an early run of this gate
    reported seventeen files whose only overlap with a standard was a
    sequence of numbers;
  * a rolling polynomial hash over every window of SHINGLE_N consecutive
    tokens, skipping windows with fewer than MIN_DISTINCT distinct tokens
    (a run of one repeated word carries no authorship);
  * winnowing keeps the minimum hash of every window of WINDOW_W shingles.

Winnowing guarantees that any run of at least WINDOW_W + SHINGLE_N - 1
identical tokens shares at least one selected fingerprint on both sides, so
the gate cannot miss a verbatim run of that length. Shorter runs are still
detected often, but not guaranteed. The stored fingerprint is the low
FP_BITS bits of a 61-bit hash: it is one-way, so an index carries no
recoverable source text.

Everything here is pure stdlib and byte-for-byte deterministic on any
platform: token values come from zlib.crc32 (fixed polynomial, not the
salted built-in hash()).
"""

import re
import zlib
from collections import deque

# Format identity. Bump when any constant below changes: an index built
# under a different identity is rejected by the gate rather than silently
# compared against mismatched fingerprints.
SCHEME = "winnow-alphaword-mindistinct-crc32-poly61-v1"

SHINGLE_N = 9        # tokens per shingle
WINDOW_W = 24        # shingles per winnowing window
MIN_DISTINCT = 5     # distinct tokens a shingle needs to be fingerprinted
GUARANTEE = WINDOW_W + SHINGLE_N - 1  # 32 tokens: guaranteed-detected run

_MOD = (1 << 61) - 1
_BASE = 0x9E3779B1
FP_BITS = 48
FP_MASK = (1 << FP_BITS) - 1

_TOKEN_RE = re.compile(r"[a-z][a-z0-9]*")

# Larger than any real hash (which is taken mod 2**61-1), so a skipped
# window loses every winnowing comparison.
SENTINEL = _MOD


def tokenize(text):
    """Lowercase word tokens beginning with a letter, in order."""
    return _TOKEN_RE.findall(text.lower())


def token_spans(text):
    """[(token, start, end)] over the lowercased text.

    Same tokens tokenize() returns, plus where each one sat. A caller that
    needs to know what SEPARATED two adjacent tokens needs this: the
    tokenizer discards commas, colons, quotes, brackets and hyphens, so a
    flattened list can present as adjacent words that the document never
    wrote in sequence. Offsets index the lowercased text, which is what the
    caller should slice for the separator.
    """
    low = text.lower()
    return [(m.group(0), m.start(), m.end()) for m in _TOKEN_RE.finditer(low)]


def shingle_hashes(tokens, n=SHINGLE_N, min_distinct=MIN_DISTINCT):
    """Rolling polynomial hash of every n-token window (61-bit).

    A window with fewer than min_distinct distinct tokens gets SENTINEL
    instead of a hash: winnowing never selects it, so a stretch of one
    repeated word cannot become a fingerprint on either side.
    """
    if len(tokens) < n:
        return []
    vals = [zlib.crc32(t.encode("utf-8")) + 1 for t in tokens]
    high = pow(_BASE, n - 1, _MOD)
    counts = {}
    for t in tokens[:n]:
        counts[t] = counts.get(t, 0) + 1
    h = 0
    for v in vals[:n]:
        h = (h * _BASE + v) % _MOD
    out = [h if len(counts) >= min_distinct else SENTINEL]
    for i in range(n, len(vals)):
        h = ((h - vals[i - n] * high) * _BASE + vals[i]) % _MOD
        drop = tokens[i - n]
        counts[drop] -= 1
        if not counts[drop]:
            del counts[drop]
        counts[tokens[i]] = counts.get(tokens[i], 0) + 1
        out.append(h if len(counts) >= min_distinct else SENTINEL)
    return out


def winnow(hashes, w=WINDOW_W):
    """Select the minimum hash of every window of w shingles.

    Returns [(shingle_index, fingerprint)], ascending by index, deduplicated.
    Ties inside a window resolve to the rightmost minimum, which is what
    makes the selection stable under insertions elsewhere in the text.
    """
    if not hashes:
        return []
    picked = []
    last = -1
    dq = deque()  # indices, hashes non-decreasing from the left
    for i, h in enumerate(hashes):
        while dq and hashes[dq[-1]] >= h:
            dq.pop()
        dq.append(i)
        while dq[0] <= i - w:
            dq.popleft()
        if i >= w - 1 or i == len(hashes) - 1:
            # `>=` above evicts an earlier equal hash, so the deque holds
            # strictly increasing values and dq[0] is the window minimum,
            # rightmost among equals.
            k = dq[0]
            if hashes[k] == SENTINEL:
                continue
            if k != last:
                picked.append((k, hashes[k] & FP_MASK))
                last = k
    return picked


def fingerprints(text, n=SHINGLE_N, w=WINDOW_W):
    """Winnowed fingerprints of a text: [(shingle_index, fingerprint)]."""
    return winnow(shingle_hashes(tokenize(text), n), w)
