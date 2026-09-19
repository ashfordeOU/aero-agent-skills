#!/usr/bin/env python3
"""Does the Hit@1 claim survive contact with how people actually type?

Why this exists
---------------
Gate 5 asks one question: does each authored query land on its expected leaf?
A corpus can answer yes to that and still be brittle, because the gate never
asks HOW it won. Three ways a green Hit@1 can mean less than it looks:

  * MARGIN. A case that wins by 0.0 is not winning on merit. The router breaks
    ties on ascending skill path, so such a case passes only because the rival
    leaf sorts later in the alphabet; one word anywhere flips it.
  * HYPHENATION. The tokenizer keeps hyphens inside a token, so the tag
    `bearing-stress` is one token and a user typing "bearing stress" never
    touches it. A corpus that writes the compounds the way the documents do is
    testing a spelling real users do not produce.
  * VERBOSITY. Scoring is raw set overlap with no IDF, so every extra word in a
    query adds generic tokens that lift many leaves at once. Long queries and
    short queries are not equally hard, and a corpus written at one length is
    measuring one point on that curve.

This reports all three. It changes nothing and, by default, fails nothing:
these are properties of the evidence, not defects to block a build on, until
someone adopts a threshold.

    python3 tools/router_robustness.py
    python3 tools/router_robustness.py --max-ties 0     # then ties are red

Exit status
-----------
    0  report printed, or --max-ties given and not exceeded
    1  --max-ties given and exceeded

Standard library only; no network; deterministic.
"""

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXPORT = os.path.join(_HERE, "export")
for _p in (_EXPORT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import reference_router  # noqa: E402
import router_coverage as rc  # noqa: E402


def load_cases(eval_dir):
    corpus, frags = rc.collect(eval_dir)
    out = []
    for path in [corpus] + frags:
        name = os.path.basename(path)
        for case in (rc.read_case_file(path).get("tasks") or []):
            if isinstance(case, dict) and case.get("query"):
                out.append((name, case))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo")
    ap.add_argument("--max-ties", type=int, default=None)
    ap.add_argument("--tsv")
    args = ap.parse_args()

    root = rc.repo_root(args.repo)
    index = reference_router.SkillIndex.from_tree(os.path.join(root, "skills"))
    cases = load_cases(os.path.join(root, "eval"))

    bands = [("tie (0.0)", 0.0), ("<=0.5", 0.5), ("<=1.5", 1.5),
             ("<=3.5", 3.5), (">3.5", float("inf"))]
    counts = dict((label, 0) for label, _ in bands)
    ties = []
    hits = 0
    dehyph_hits = 0
    by_len = {}

    for name, case in cases:
        query = case["query"]
        expected = case.get("expected_skill")
        ranked = index.rank(query, top_k=2)
        (top_score, top_path) = ranked[0]
        runner = ranked[1][0] if len(ranked) > 1 else 0.0

        words = len(query.split())
        band = ("1-10" if words <= 10 else "11-20" if words <= 20 else
                "21-30" if words <= 30 else "31-40" if words <= 40 else "41+")
        seen, ok = by_len.get(band, (0, 0))

        won = top_path == expected
        by_len[band] = (seen + 1, ok + (1 if won else 0))
        if won:
            hits += 1
            margin = top_score - runner
            for label, ceiling in bands:
                if margin <= ceiling:
                    counts[label] += 1
                    break
            if margin == 0.0:
                ties.append((name, case.get("id"), expected))
        if index.top1(query.replace("-", " "))[1] == expected:
            dehyph_hits += 1

    total = len(cases)
    print("================= router robustness =================")
    print("cases                                       %6d" % total)
    print("Hit@1 as authored                           %6d  (%6.2f%%)"
          % (hits, 100.0 * hits / max(1, total)))
    print("Hit@1 with hyphens removed from the query   %6d  (%6.2f%%)"
          % (dehyph_hits, 100.0 * dehyph_hits / max(1, total)))
    print("   (how a user types it: 'bearing stress', not 'bearing-stress')")
    print("-----------------------------------------------------")
    print("winning margin over the runner-up:")
    for label, _ in bands:
        print("   %-12s %6d  (%5.2f%% of hits)"
              % (label, counts[label], 100.0 * counts[label] / max(1, hits)))
    print("   a tie is won on ascending skill path, not on merit")
    print("-----------------------------------------------------")
    print("Hit@1 by query length:")
    for band in ("1-10", "11-20", "21-30", "31-40", "41+"):
        if band in by_len:
            seen, ok = by_len[band]
            print("   %-8s %6d cases  %6.2f%%" % (band, seen, 100.0 * ok / seen))
    print("=====================================================")

    if args.tsv:
        with open(args.tsv, "w", encoding="utf-8") as handle:
            handle.write("source\tcase_id\texpected\n")
            for row in ties:
                handle.write("%s\t%s\t%s\n" % row)
        print("wrote %s (%d tie-won cases)" % (args.tsv, len(ties)))

    if args.max_ties is not None and len(ties) > args.max_ties:
        sys.stderr.write(
            "FAIL router-robustness: %d case(s) win only on the path tie-break; "
            "allowed %d.\n" % (len(ties), args.max_ties))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
