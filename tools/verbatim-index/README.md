# No-verbatim source-text index

The corpus paraphrases standards and never reproduces them
(`research/briefs/06-legal-export-control.md` section 5.2). Gate 4 enforces
that rule. This directory holds the part of the gate that compares the
repository against the actual text of a standard.

## What the gate checks, and what it admits it does not

`tools/verbatim_gate.py` reports one of three states for every standards
family that appears in `standards-map.yaml` and is cited by a leaf:

| state | meaning |
|---|---|
| `SOURCE` / `SOURCE+MARKERS` | the family's source documents were read at index-build time; every scanned file is compared against their text |
| `MARKERS-ONLY` | only publisher boilerplate, licence/DRM lines and store URLs are matched — a pasted page is caught, a retyped paragraph is not |
| `UNCHECKED` | neither is available; the gate says so instead of passing silently |

The coverage line names the families in each state and the number of leaves
in each. `--strict` turns an `UNCHECKED` family into a failure; `--json`
prints the whole report as data.

Before 2026-09-19 the gate was fifteen grep patterns naming RTCA, SAE, IAQG
and EUROCAE — four publishers covering 216 of the 3,021 leaves. The other
2,805 leaves, ECSS above all, were scanned by patterns that could not match
their sources, and the run still printed PASS.

## How the source-text check works

`tools/build_verbatim_index.py` reads the source documents once, at build
time, and writes `verbatim-index/<family>.idx`: truncated 48-bit hashes of
9-word shingles, winnowed (Schleimer, Wilkerson & Aiken 2003) so that any
run of 32 or more identical words shares at least one fingerprint with the
index. The hashes are one-way and only about 8% of shingles survive
winnowing, so the index carries no recoverable text — which is why it can
live in a public repository while the standards themselves cannot, and why
the gate needs no access to the sources at run time.

Three deliberate exclusions keep the check on prose and off data:

* bare numbers are not tokenised — clause numbering, page numbers and
  tables of values are not the protected expression;
* a 9-word window with fewer than 5 distinct words is never fingerprinted;
* a phrase found in more than `--max-df` (default 3) of the source
  documents is dropped — the shared vocabulary of a standards series
  (milestone lists, defined terms, the foreword every document carries) is
  not one document's authorship. That recurring front matter is caught by
  the gate's marker patterns instead.

One shared fingerprint is a `WARN`; two or more (a run of roughly fifty
words or longer) is a `FAIL`. `--min-fingerprints 1` fails on any match.

## Rebuilding an index

Keep the source documents outside the repository. PDFs are read through
poppler's `pdftotext`; pre-extracted `.txt` needs no external binary.

    python3 tools/build_verbatim_index.py --family ecss --sources <source dir>
    python3 tools/build_verbatim_index.py --family ecss --sources <source dir> --check

`--check` rebuilds in memory and exits non-zero if the committed index no
longer matches the sources. The build is deterministic: the same documents
always produce the same bytes. `verbatim-index/<family>.manifest.json` is
the same header in readable form — one row per source document with its
SHA-256, so what the index was built from is auditable without the sources.

Adding a family: give it an entry in `FAMILIES` in `tools/verbatim_gate.py`
(the `publisher` pattern must match the publisher field in
`standards-map.yaml`), then build an index under the same key. A family
with no source text must state why it has no markers, so that an omission
is a recorded decision rather than an empty list.

## Tests

    python3 tools/test_verbatim_gate.py

33 tests: fingerprint determinism across processes, the 32-word detection
guarantee, number and repeated-word suppression, index round-trip and
determinism, the document-frequency filter, the register-to-family mapping
(every publisher in `standards-map.yaml` must resolve to a family), and the
gate end to end over a throwaway tree — clean pass, marker hit, source-text
hit, `UNCHECKED` reporting and `--strict`. unittest prints its summary on
stderr; capture both streams.
