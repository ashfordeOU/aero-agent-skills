#!/usr/bin/env python3
"""Build a one-way fingerprint index of a standards family's source text.

BUILD-TIME tool. It is the only step that ever reads a standards document;
the gate (tools/verbatim_gate.py) reads the index it writes and never needs
the source again. Offline, deterministic, no network.

What lands in the repository is an index of truncated 48-bit hashes of
9-word shingles. It carries no recoverable text: the hash is one-way and
only ~8% of shingles survive winnowing. It lets the gate answer one
question -- "does this repository file reproduce a long run of the source?"
-- without the repository holding the source.

A fingerprint found in more than --max-df of the source documents is
dropped: a phrase that recurs across a whole standards series is that
series' shared vocabulary (milestone lists, defined terms, the foreword
every document carries), not one document's authorship, and indexing it
turns legitimate corpus prose red. The recurring front matter is caught by
the marker patterns in the gate instead.

Usage:
    tools/build_verbatim_index.py --family ecss --sources <dir> [--out <dir>]
    tools/build_verbatim_index.py --family ecss --sources <dir> --check

  --sources   directory of source documents (.pdf and/or .txt, searched
              recursively). Keep it OUTSIDE the repository.
  --check     rebuild in memory and compare against the committed index;
              non-zero exit when they differ (use in CI once sources are
              available to the runner).

PDF text extraction shells out to `pdftotext` (poppler) when the input is a
PDF -- a local binary, no network, no third-party Python import. Pre-extract
to .txt yourself if you would rather not have that dependency.

Index format (tools/verbatim-index/<family>.idx):
    magic   b"AEROVBX1"
    uint32  header length, big-endian
    header  UTF-8 JSON: scheme, shingle_n, window_w, fp_bits, guarantee,
            max_df, record_count, dropped_above_max_df,
            docs[] (name, sha256, tokens, fingerprints)
    records record_count * 8 bytes, ascending: 6-byte fingerprint
            (big-endian) + 2-byte index into docs[]
A fingerprint seen in several documents is stored once, against the first
document (documents are processed in sorted name order), so the record
count is the distinct-fingerprint count.
"""

import sys

# Leave nothing behind: a gate run must not litter the tree with
# __pycache__ (the public-safety audit reads the working tree).
sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import struct
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verbatim_shingle as vs  # noqa: E402

MAGIC = b"AEROVBX1"
REC = 8            # 6-byte fingerprint + 2-byte doc index
FP_BYTES = 6
MAX_DOCS = 0xFFFF


def extract_text(path):
    """Return the plain text of one source document, or None."""
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".pdf":
        exe = shutil.which("pdftotext")
        if not exe:
            return None
        out = subprocess.run(
            [exe, "-q", "-enc", "UTF-8", str(path), "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
        )
        if out.returncode != 0:
            return None
        return out.stdout.decode("utf-8", errors="replace")
    return None


def build(family, sources, max_df=3):
    src = pathlib.Path(sources)
    docs = sorted(
        [p for p in src.rglob("*") if p.is_file()
         and p.suffix.lower() in (".pdf", ".txt")],
        key=lambda p: p.name,
    )
    if not docs:
        raise SystemExit("FAIL: no .pdf or .txt source document under %s" % sources)
    if len(docs) > MAX_DOCS:
        raise SystemExit("FAIL: %d source documents exceeds the %d the format holds"
                         % (len(docs), MAX_DOCS))

    first = {}
    df = {}
    meta = []
    skipped = []
    for p in docs:
        text = extract_text(p)
        if text is None:
            skipped.append(p.name)
            continue
        toks = vs.tokenize(text)
        fps = vs.winnow(vs.shingle_hashes(toks))
        idx = len(meta)
        for fp in {f for _, f in fps}:
            first.setdefault(fp, idx)
            df[fp] = df.get(fp, 0) + 1
        meta.append({
            "name": p.name,                       # file name only, never a path
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "tokens": len(toks),
            "fingerprints": len(fps),
        })
    if not meta:
        raise SystemExit("FAIL: no source document could be read as text "
                         "(install poppler's pdftotext, or pre-extract to .txt)")

    kept = sorted(fp for fp, n in df.items() if n <= max_df)
    header = {
        "family": family,
        "scheme": vs.SCHEME,
        "shingle_n": vs.SHINGLE_N,
        "window_w": vs.WINDOW_W,
        "fp_bits": vs.FP_BITS,
        "guarantee_tokens": vs.GUARANTEE,
        "max_df": max_df,
        "record_count": len(kept),
        "dropped_above_max_df": len(df) - len(kept),
        "source_documents": len(meta),
        "source_tokens": sum(d["tokens"] for d in meta),
        "docs": meta,
    }
    blob = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    body = bytearray()
    for fp in kept:
        body += fp.to_bytes(FP_BYTES, "big") + struct.pack(">H", first[fp])
    return MAGIC + struct.pack(">I", len(blob)) + blob + bytes(body), header, skipped


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--family", required=True,
                    help="family key, e.g. ecss (must match verbatim_gate.py)")
    ap.add_argument("--sources", required=True,
                    help="directory of source documents, kept outside the repo")
    ap.add_argument("--out", default=None,
                    help="output directory (default: tools/verbatim-index/)")
    ap.add_argument("--max-df", type=int, default=3,
                    help="drop a fingerprint found in more than this many "
                         "source documents (default 3)")
    ap.add_argument("--check", action="store_true",
                    help="compare a fresh build against the committed index")
    a = ap.parse_args()

    out_dir = pathlib.Path(a.out) if a.out else \
        pathlib.Path(__file__).resolve().parent / "verbatim-index"
    idx_path = out_dir / ("%s.idx" % a.family)
    man_path = out_dir / ("%s.manifest.json" % a.family)

    data, header, skipped = build(a.family, a.sources, a.max_df)
    for name in skipped:
        print("WARN: unreadable, not indexed: %s" % name)

    if a.check:
        if not idx_path.exists():
            print("FAIL: %s does not exist" % idx_path.name)
            return 1
        if idx_path.read_bytes() == data:
            print("PASS verbatim-index %s: committed index matches the sources "
                  "(%d docs, %d fingerprints)"
                  % (a.family, header["source_documents"], header["record_count"]))
            return 0
        print("FAIL verbatim-index %s: committed index differs from a fresh build "
              "of the sources" % a.family)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    idx_path.write_bytes(data)
    man_path.write_text(json.dumps(header, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print("wrote %s (%d bytes): %d documents, %d source tokens, %d fingerprints "
          "(%d dropped as shared across more than %d documents), "
          "guaranteed run >= %d tokens"
          % (idx_path.name, len(data), header["source_documents"],
             header["source_tokens"], header["record_count"],
             header["dropped_above_max_df"], header["max_df"],
             header["guarantee_tokens"]))
    print("wrote %s" % man_path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
