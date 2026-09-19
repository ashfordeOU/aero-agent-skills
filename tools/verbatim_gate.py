#!/usr/bin/env python3
"""Gate 4 -- no-verbatim, family-aware.

The corpus paraphrases standards; it never reproduces them. This gate is
what enforces that, and it now states its own coverage instead of implying
it is complete.

Two independent checks, plus a coverage statement:

  1. MARKERS. Publisher boilerplate, licence/DRM lines and store URLs that
     only appear in a file if a page of a standard was pasted into it.
     Cheap, and available for every publisher that stamps its documents.
     A marker check alone says nothing about the body text of a standard,
     so a family with markers and no source text is reported as
     markers-only, never as covered.

  2. SOURCE TEXT. Where the source documents of a family are available at
     build time, tools/build_verbatim_index.py distils them into one-way
     shingle fingerprints (tools/verbatim-index/<family>.idx) and this gate
     compares every scanned file against them. This is the only check that
     actually reads the standard's prose.

     Any run of at least 32 identical words shares at least one fingerprint
     (winnowing guarantees it). One shared fingerprint is reported as a
     WARN: on this corpus the one-fingerprint matches are all lists of
     defined terms -- review milestones, verification stages, organ names --
     which are the vocabulary of the field, not authorship. Two or more
     shared fingerprints mean a run of roughly fifty words or longer and
     FAIL the gate. --min-fingerprints 1 makes every match fail.

  3. COVERAGE. Every standards family present in the corpus is listed with
     the number of leaves that cite it and the check it received. A family
     with neither source text nor markers reports UNCHECKED -- it never
     reports PASS. `--strict` turns any UNCHECKED family into a failure.

stdlib only, offline, deterministic. Objective-table blocks are a separate
runner (scripts/verbatim_table_scan.py), kept as is.
"""

import sys

# Leave nothing behind: a gate run must not litter the tree with
# __pycache__ (the public-safety audit reads the working tree).
sys.dont_write_bytecode = True

import argparse
import json
import os
import pathlib
import re
import struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verbatim_shingle as vs  # noqa: E402

MAGIC = b"AEROVBX1"
REC = 8
FP_BYTES = 6

# --------------------------------------------------------------------------
# Families. A family is a publisher whose text the corpus could reproduce.
# `publisher` matches the publisher field of standards-map.yaml, in order --
# the first hit wins, so joint entries ("IAQG (develops) / SAE (publishes)",
# "ARINC (AEEC; published via SAE ITC)") must precede the plain SAE row.
#
# `markers` are lines that only a pasted page carries. They are matched
# case-insensitively, as the shell gate matched them before. `no_markers`
# records WHY a family has none, so the omission is a stated fact rather
# than an empty list nobody notices.
# --------------------------------------------------------------------------
GENERIC_MARKERS = [
    r"Electronic License Agreement",
    r"PROPRIETARY AND CONFIDENTIAL",
    r"This document is licensed to",
    r"not for redistribution",
    r"single-user license",
    r"DRM-protected",
]

FAMILIES = [
    {
        "key": "rtca", "label": "RTCA / EUROCAE", "publisher": r"RTCA",
        "markers": [
            r"Copyright.*RTCA,? ?(Inc|International|Europe)",
            r"RTCA, Inc.*All Rights Reserved",
            r"All [Rr]ights [Rr]eserved.*RTCA",
            r"RTCA proprietary information",
            r"Copyright.*EUROCAE",
            r"standards\.rtca\.org",
        ],
    },
    {
        "key": "iaqg", "label": "IAQG (published by SAE)", "publisher": r"IAQG",
        "markers": [r"Copyright.*IAQG", r"Copyright.*SAE International",
                    r"sae\.org/standards/content"],
    },
    {
        "key": "arinc", "label": "ARINC / AEEC (published by SAE ITC)",
        "publisher": r"ARINC",
        "markers": [r"Copyright.*ARINC", r"ARINC Industry Activities",
                    r"sae\.org/standards/content"],
    },
    {
        "key": "sae", "label": "SAE International", "publisher": r"SAE International",
        "markers": [r"Copyright.*SAE International", r"sae\.org/standards/content"],
    },
    {
        "key": "asme", "label": "ASME", "publisher": r"ASME",
        "markers": [r"Copyright.*ASME", r"ASME.*All Rights Reserved",
                    r"asme\.org/codes-standards"],
    },
    {
        "key": "aia", "label": "AIA (sold via Accuris/Techstreet)", "publisher": r"AIA",
        "markers": [r"Copyright.*Aerospace Industries Association",
                    r"store\.accuristech\.com", r"techstreet\.com"],
    },
    {
        "key": "ata", "label": "ATA / A4A",
        "publisher": r"Air Transport Association",
        "markers": [r"Copyright.*(Air Transport Association|Airlines for America)",
                    r"airlines\.org/product"],
    },
    {
        "key": "ecss", "label": "ECSS / ESA",
        "publisher": r"European Cooperation for Space Standardization",
        # Front-matter of every ECSS document. A citation such as
        # "ECSS-E-ST-20-07C clause 4.2" is normal corpus content and is
        # deliberately NOT a marker; these lines are not.
        "markers": [
            r"ECSS Secretariat",
            r"ESA-ESTEC",
            r"Requirements & Standards Division",
            r"for the members of ECSS",
            r"ECSS does not provide any warranty",
            r"No ECSS document may be reproduced",
        ],
    },
    {
        "key": "easa", "label": "EASA", "publisher": r"EASA",
        "markers": [r"Copyright.*EASA",
                    r"European Union Aviation Safety Agency.*All rights reserved"],
    },
    {
        "key": "faa", "label": "FAA (14 CFR)", "publisher": r"FAA",
        "markers": [],
        "no_markers": "US Government work: the source carries no copyright "
                      "or licence boilerplate to match",
    },
    {
        "key": "dod", "label": "US DoD (MIL-STD)", "publisher": r"US DoD",
        "markers": [],
        "no_markers": "US Government work: the source carries no copyright "
                      "or licence boilerplate to match",
    },
    {
        "key": "usgov", "label": "US Government (DDTC / BIS)",
        "publisher": r"US Government \(DDTC",
        "markers": [],
        "no_markers": "US Government work: the source carries no copyright "
                      "or licence boilerplate to match",
    },
    {
        "key": "nasa", "label": "NACA / NASA", "publisher": r"NACA",
        "markers": [],
        "no_markers": "US Government work: the source carries no copyright "
                      "or licence boilerplate to match",
    },
    {
        "key": "mcp", "label": "MCP working group (open spec)",
        "publisher": r"MCP Skills-over-MCP",
        "markers": [],
        "no_markers": "open specification, published without licence "
                      "boilerplate to match",
    },
]

SCAN_FILES = ["README.md", "STANDARDS.md", "NOTICE"]
SCAN_DIRS = ["skills", "docs"]
SKIP_SUFFIXES = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip",
                 ".ico", ".woff", ".woff2", ".idx"}


# --------------------------------------------------------------------------
# standards-map.yaml: the register. Parsed with a small reader rather than a
# third-party YAML module -- the gate ships stdlib-only.
# --------------------------------------------------------------------------
def read_register(path):
    entries, cur, in_list = [], None, False
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not in_list:
            if raw.rstrip() == "standards:":
                in_list = True
            continue
        m = re.match(r"^  - (\w[\w_]*): (.*)$", raw)
        if m:
            if cur:
                entries.append(cur)
            cur = {m.group(1): m.group(2).strip().strip('"')}
            continue
        m = re.match(r"^    (\w[\w_]*): (.*)$", raw)
        if m and cur is not None:
            cur[m.group(1)] = m.group(2).strip().strip('"')
    if cur:
        entries.append(cur)
    return {e["id"]: e for e in entries if "id" in e}


def family_of(publisher):
    for fam in FAMILIES:
        if re.search(fam["publisher"], publisher):
            return fam["key"]
    return None


# --------------------------------------------------------------------------
# Source-text index
# --------------------------------------------------------------------------
class SourceIndex:
    def __init__(self, path):
        raw = path.read_bytes()
        if raw[:8] != MAGIC:
            raise ValueError("%s: not a verbatim index" % path.name)
        hlen = struct.unpack(">I", raw[8:12])[0]
        self.header = json.loads(raw[12:12 + hlen].decode("utf-8"))
        self.body = raw[12 + hlen:]
        self.count = self.header["record_count"]
        if len(self.body) != self.count * REC:
            raise ValueError("%s: truncated index" % path.name)
        if self.header.get("scheme") != vs.SCHEME:
            raise ValueError("%s: built under scheme %r, this gate speaks %r"
                             % (path.name, self.header.get("scheme"), vs.SCHEME))
        self.docs = [d["name"] for d in self.header["docs"]]

    def lookup(self, fp):
        """Document name holding this fingerprint, or None."""
        target = fp.to_bytes(FP_BYTES, "big")
        lo, hi = 0, self.count
        body = self.body
        while lo < hi:
            mid = (lo + hi) // 2
            off = mid * REC
            if body[off:off + FP_BYTES] < target:
                lo = mid + 1
            else:
                hi = mid
        off = lo * REC
        if lo < self.count and body[off:off + FP_BYTES] == target:
            return self.docs[struct.unpack(">H", body[off + FP_BYTES:off + REC])[0]]
        return None


# --------------------------------------------------------------------------
def run_is_flattened(low, spans, pos, n=None):
    """True when every gap inside this token run carries punctuation.

    The tokenizer drops the separators, so a YAML tag array, a Trigger
    keyword list or a Python dict of keys is handed to the index as one
    long sentence. That sentence exists in no document: the words are
    adjacent only because the commas were stripped, and matching it is not
    reproduction. Prose cannot look like this -- nine consecutive words
    with no plain space anywhere between them would have to be a single
    hyphenated compound -- so excluding these runs costs the gate no real
    detection. A copied sentence keeps its spaces and still fails.
    """
    n = n or vs.SHINGLE_N
    if pos < 0 or pos + n > len(spans):
        return False
    for i in range(pos, pos + n - 1):
        if not low[spans[i][2]:spans[i + 1][1]].strip():
            return False          # a plain space or newline: real adjacency
    return True


def iter_scan_files(root):
    for name in SCAN_FILES:
        p = root / name
        if p.is_file():
            yield p
    for d in SCAN_DIRS:
        base = root / d
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file() and p.suffix.lower() not in SKIP_SUFFIXES:
                yield p


def leaf_families(root, register):
    """{family_key: leaf count}, plus leaves whose ids the register lacks."""
    counts, unmapped, leaves = {}, {}, 0
    unchecked_leaf_ids = []
    per_leaf = []
    for p in sorted((root / "skills").glob("*/*/*/SKILL.md")):
        leaves += 1
        head = re.match(r"^---\n(.*?)\n---\n", p.read_text(encoding="utf-8",
                                                           errors="replace"), re.S)
        fm = head.group(1) if head else ""
        ids = [s.strip("\"'") for s in re.findall(r"^\s*-\s*id:\s*(\S+)", fm, re.M)]
        fams = set()
        if not ids:
            unchecked_leaf_ids.append(str(p.relative_to(root)))
        for sid in ids:
            ent = register.get(sid)
            if ent is None:
                unmapped[sid] = unmapped.get(sid, 0) + 1
                fams.add(None)
                continue
            fams.add(family_of(ent.get("publisher", "")))
        for f in fams:
            if f is not None:
                counts[f] = counts.get(f, 0) + 1
        per_leaf.append((str(p.relative_to(root)), fams))
    return counts, unmapped, leaves, per_leaf, unchecked_leaf_ids


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-fingerprints", type=int, default=2, metavar="N",
                    help="source-text matches needed in one file before it "
                         "fails; fewer are reported as WARN (default 2)")
    ap.add_argument("--strict", action="store_true",
                    help="fail when any family in the corpus is UNCHECKED")
    ap.add_argument("--json", dest="as_json", action="store_true",
                    help="machine-readable coverage report on stdout")
    ap.add_argument("--quiet", action="store_true",
                    help="only the verdict and coverage lines")
    a = ap.parse_args()

    root = pathlib.Path(__file__).resolve().parents[1]
    map_path = root / "standards-map.yaml"
    if not map_path.is_file():
        # Without the register there is no list of families, so there is no
        # coverage to state. Refusing is the point of this gate: an
        # ungradeable tree must not print PASS.
        print("FAIL gate4-no-verbatim: standards-map.yaml is missing, so the "
              "gate cannot say which families it covers", file=sys.stderr)
        return 1
    register = read_register(map_path)
    counts, unmapped, leaf_total, per_leaf, no_ids = leaf_families(root, register)

    idx_dir = root / "tools" / "verbatim-index"
    indexes = {}
    for fam in FAMILIES:
        p = idx_dir / ("%s.idx" % fam["key"])
        if p.is_file():
            indexes[fam["key"]] = SourceIndex(p)

    # one alternation as a pre-filter, then per-pattern attribution
    pats = [(None, p) for p in GENERIC_MARKERS]
    for fam in FAMILIES:
        pats += [(fam["key"], p) for p in fam.get("markers", [])]
    combined = re.compile("|".join("(?:%s)" % p for _, p in pats), re.I)
    singles = [(k, re.compile(p, re.I)) for k, p in pats]

    marker_hits, source_hits = [], []
    flattened_hits = []
    scanned = 0
    for p in iter_scan_files(root):
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        rel = str(p.relative_to(root))
        if combined.search(text):
            for lineno, line in enumerate(text.splitlines(), 1):
                for key, rx in singles:
                    if rx.search(line):
                        marker_hits.append((rel, lineno, key or "generic",
                                            rx.pattern))
        if indexes:
            fps = vs.fingerprints(text)
            if fps:
                low = text.lower()
                spans = vs.token_spans(text)
                per_family = {}
                for pos, fp in fps:
                    for key, si in indexes.items():
                        doc = si.lookup(fp)
                        if doc:
                            if run_is_flattened(low, spans, pos):
                                flattened_hits.append(
                                    (rel, key, pos, doc,
                                     " ".join(t for t, _, _ in
                                              spans[pos:pos + vs.SHINGLE_N])))
                                continue
                            e = per_family.setdefault(key, {"n": 0, "docs": {},
                                                            "first": pos})
                            e["n"] += 1
                            e["docs"][doc] = e["docs"].get(doc, 0) + 1
                for key, e in sorted(per_family.items()):
                    source_hits.append((rel, key, e["n"], e["first"],
                                        sorted(e["docs"], key=lambda d: -e["docs"][d])))

    # ---- coverage -------------------------------------------------------
    rows = []
    for fam in FAMILIES:
        n = counts.get(fam["key"], 0)
        if n == 0:
            continue
        has_src = fam["key"] in indexes
        has_mark = bool(fam.get("markers"))
        if has_src:
            status = "SOURCE+MARKERS" if has_mark else "SOURCE"
        elif has_mark:
            status = "MARKERS-ONLY"
        else:
            status = "UNCHECKED"
        rows.append({
            "family": fam["key"], "label": fam["label"], "leaves": n,
            "status": status,
            "source_documents": (indexes[fam["key"]].header["source_documents"]
                                 if has_src else 0),
            "reason": ("" if has_src or has_mark
                       else fam.get("no_markers", "no source text, no markers")),
        })

    src_fams = [r for r in rows if r["status"].startswith("SOURCE")]
    mark_fams = [r for r in rows if r["status"] == "MARKERS-ONLY"]
    unchk_fams = [r for r in rows if r["status"] == "UNCHECKED"]

    src_keys = {r["family"] for r in src_fams}
    ok_keys = src_keys | {r["family"] for r in mark_fams}
    leaves_src = sum(1 for _, f in per_leaf if f and all(x in src_keys for x in f))
    leaves_unchk = sum(1 for _, f in per_leaf if not f or any(x not in ok_keys for x in f))

    fails = [h for h in source_hits if h[2] >= a.min_fingerprints]
    warns = [h for h in source_hits if h[2] < a.min_fingerprints]

    if a.as_json:
        print(json.dumps({
            "leaves": leaf_total, "files_scanned": scanned, "families": rows,
            "leaves_source_checked": leaves_src,
            "leaves_unchecked_family": leaves_unchk,
            "unmapped_standard_ids": unmapped,
            "marker_hits": marker_hits,
            "min_fingerprints": a.min_fingerprints,
            "source_hits": [{"file": f, "family": k, "fingerprints": n,
                             "first_shingle": pos, "source_documents": d,
                             "verdict": "FAIL" if n >= a.min_fingerprints
                                        else "WARN"}
                            for f, k, n, pos, d in source_hits],
            "flattened_runs_excluded": [
                {"file": f, "family": k, "first_shingle": p,
                 "source_document": d, "run": r}
                for f, k, p, d, r in flattened_hits],
        }, indent=2, sort_keys=True))
    elif not a.quiet:
        print("gate4-no-verbatim coverage (leaf counts from SKILL.md frontmatter "
              "against standards-map.yaml)")
        for r in rows:
            extra = ""
            if r["source_documents"]:
                extra = " (%d source documents)" % r["source_documents"]
            elif r["reason"]:
                extra = " (%s)" % r["reason"]
            print("  %-14s %-38s leaves=%-5d %s%s"
                  % (r["family"], r["label"], r["leaves"], r["status"], extra))
        for sid, n in sorted(unmapped.items()):
            print("  %-14s %-38s leaves=%-5d UNMAPPED (id absent from "
                  "standards-map.yaml)" % ("-", sid, n))

    out = sys.stderr if a.as_json else sys.stdout
    print("COVERAGE gate4-no-verbatim: families=%d source-checked=%d (leaves %d) "
          "markers-only=%d (leaves %d) unchecked=%d (leaves %d); "
          "leaves fully source-checked=%d of %d; leaves with an unchecked or "
          "unmapped standard=%d; files scanned=%d; source-text FAIL=%d WARN=%d; "
          "flattened-list runs excluded=%d"
          % (len(rows), len(src_fams), sum(r["leaves"] for r in src_fams),
             len(mark_fams), sum(r["leaves"] for r in mark_fams),
             len(unchk_fams), sum(r["leaves"] for r in unchk_fams),
             leaves_src, leaf_total, leaves_unchk, scanned,
             len(fails), len(warns), len(flattened_hits)), file=out)
    for rel, key, pos, doc, run in flattened_hits:
        print("INFO gate4-no-verbatim: %s word ~%d matches %s but every gap in "
              "the run carries punctuation -- a flattened list, not a "
              "sentence; excluded (%s: %s)"
              % (rel, pos, key, doc, run), file=out)

    # ---- verdict --------------------------------------------------------
    for rel, lineno, key, pat in marker_hits:
        print("FAIL gate4-no-verbatim: %s:%d %s marker /%s/"
              % (rel, lineno, key, pat), file=sys.stderr)
    for rel, key, n, pos, docs in fails:
        print("FAIL gate4-no-verbatim: %s reproduces %s source text "
              "(%d fingerprints, first at word ~%d, source: %s)"
              % (rel, key, n, pos, docs[0]), file=sys.stderr)
    for rel, key, n, pos, docs in warns:
        print("WARN gate4-no-verbatim: %s shares a short run with %s source "
              "text (%d fingerprint, at word ~%d, source: %s) -- under the "
              "%d needed to fail; check it is a term list, not prose"
              % (rel, key, n, pos, docs[0], a.min_fingerprints), file=sys.stderr)
    for rel in no_ids:
        print("WARN gate4-no-verbatim: %s declares no standards id, so no "
              "family owns it" % rel, file=sys.stderr)

    if marker_hits or fails:
        print("FAIL gate4-no-verbatim: %d marker hit(s), %d source-text hit(s)"
              % (len(marker_hits), len(fails)), file=sys.stderr)
        return 1
    if a.strict and (unchk_fams or unmapped):
        print("FAIL gate4-no-verbatim --strict: %d family/families UNCHECKED, "
              "%d unmapped standard id(s)" % (len(unchk_fams), len(unmapped)),
              file=sys.stderr)
        return 1
    print("PASS gate4-no-verbatim: 0 markers, 0 failing source-text matches in "
          "%d file(s); %d short-run WARN(s); %d family/families UNCHECKED "
          "(listed above, not counted as pass)"
          % (scanned, len(warns), len(unchk_fams)), file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
