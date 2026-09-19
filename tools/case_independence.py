#!/usr/bin/env python3
"""Are the router cases independent of the leaves they grade?

Why this exists
---------------
Hit@1 is only evidence if the queries are written the way a user would ask.
A query assembled out of the expected leaf's own sentences will route to that
leaf whatever the router does, because it is a near-copy of the document it is
being matched against. Such a case cannot fail, so it measures nothing, and a
corpus of them reports a high Hit@1 that means nothing at all. Nothing in the
harness could previously see the difference: gate 5 asks only whether a case
lands, never whether it was capable of not landing.

This measures, for every case, the LONGEST RUN OF CONSECUTIVE TOKENS the query
shares with its expected leaf's own text (description plus body). A handful of
shared words is ordinary -- the case and the leaf are about the same subject
and use the same vocabulary. A long verbatim run is not: it is the leaf's own
prose pasted back in as a question.

The default threshold is 6. A run that long is no longer shared terminology,
it is a shared sentence fragment. Authored cases are held to 4 by the item-8
brief; the gate sits looser than the brief on purpose, so that a borderline
phrase is a review note rather than a build break.

This CHANGES NOTHING. It reads eval/ and skills/ and prints a report.

Usage
-----
    python3 tools/case_independence.py                  # report
    python3 tools/case_independence.py --max-run 6      # set the threshold
    python3 tools/case_independence.py --fail-over 0    # red if any exceed
    python3 tools/case_independence.py --tsv FILE       # every case, scored

Exit status
-----------
    0  report printed, or --fail-over given and not exceeded
    1  --fail-over given and exceeded

Standard library only; no network; deterministic.
"""

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXPORT_DIR = os.path.join(_HERE, "export")
if _EXPORT_DIR not in sys.path:
    sys.path.insert(0, _EXPORT_DIR)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import reference_router  # noqa: E402
import router_coverage as rc  # noqa: E402
import yaml_subset  # noqa: E402


def leaf_text(skills_root, leaf):
    """The leaf's own words: description plus body, as one token list."""
    path = os.path.join(skills_root, leaf, "SKILL.md")
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    front, body = yaml_subset.read_frontmatter(text)
    desc = (front or {}).get("description") or ""
    return reference_router.tokenize(desc + " " + body)


def longest_run(query_tokens, leaf_tokens):
    """Longest run of consecutive query tokens appearing, in order, in the leaf.

    Classic DP for longest common substring over token sequences. The leaf
    body runs to a few thousand tokens and a query to a few dozen, so the
    table is small; only the previous row is kept.
    """
    if not query_tokens or not leaf_tokens:
        return 0, ""
    positions = {}
    for j, tok in enumerate(leaf_tokens):
        positions.setdefault(tok, []).append(j)
    prev = {}
    best, best_end = 0, -1
    for i, tok in enumerate(query_tokens):
        cur = {}
        for j in positions.get(tok, ()):
            run = prev.get(j - 1, 0) + 1
            cur[j] = run
            if run > best:
                best, best_end = run, i
        prev = cur
    if best == 0:
        return 0, ""
    return best, " ".join(query_tokens[best_end - best + 1:best_end + 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo")
    ap.add_argument("--max-run", type=int, default=6)
    ap.add_argument("--fail-over", type=int, default=None)
    ap.add_argument("--tsv")
    args = ap.parse_args()

    root = rc.repo_root(args.repo)
    skills_root = os.path.join(root, "skills")
    corpus_path, frag_paths = rc.collect(os.path.join(root, "eval"))

    cache = {}
    rows = []
    for source in [corpus_path] + frag_paths:
        for case in (rc.read_case_file(source).get("tasks") or []):
            if not isinstance(case, dict):
                continue
            leaf = case.get("expected_skill") or ""
            if leaf not in cache:
                cache[leaf] = leaf_text(skills_root, leaf)
            qt = reference_router.tokenize(case.get("query") or "")
            run, phrase = longest_run(qt, cache[leaf])
            rows.append((run, os.path.relpath(source, root),
                         case.get("id") or "?", leaf, len(qt), phrase))

    rows.sort(key=lambda r: (-r[0], r[1], r[2]))
    over = [r for r in rows if r[0] > args.max_run]

    print("=============== case independence ===============")
    print("cases examined                        %6d" % len(rows))
    print("longest shared run with the leaf's own text:")
    buckets = {}
    for r in rows:
        key = min(r[0], 10)
        buckets[key] = buckets.get(key, 0) + 1
    for key in sorted(buckets):
        label = "%d" % key if key < 10 else "10+"
        print("   run %-4s %6d  (%5.2f%%)"
              % (label, buckets[key], 100.0 * buckets[key] / max(1, len(rows))))
    print("-------------------------------------------------")
    print("over threshold (run > %d)              %6d" % (args.max_run, len(over)))
    print("=================================================")

    for run, source, cid, leaf, _n, phrase in over[:25]:
        print("  run=%-3d %-34s %s" % (run, cid, leaf))
        print("          \"%s\"" % phrase)
    if len(over) > 25:
        print("  ... and %d more" % (len(over) - 25))

    if args.tsv:
        with open(args.tsv, "w", encoding="utf-8") as handle:
            handle.write("run\tsource\tcase_id\texpected\tquery_tokens\tphrase\n")
            for r in rows:
                handle.write("%d\t%s\t%s\t%s\t%d\t%s\n" % r)
        print("\nwrote %s" % args.tsv)

    if args.fail_over is not None and len(over) > args.fail_over:
        sys.stderr.write(
            "FAIL case-independence: %d case(s) share a run of more than %d "
            "consecutive tokens with the leaf they grade; allowed %d.\n"
            % (len(over), args.max_run, args.fail_over))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
