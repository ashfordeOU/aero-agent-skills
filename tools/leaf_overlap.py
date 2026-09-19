#!/usr/bin/env python3
"""Which leaves cover the same ground? Measure, do not rely on anecdote.

Why this exists
---------------
space-systems/ecss holds 2,534 of the catalogue's leaves in one flat pack, and
the router decides between them on token overlap alone. When two leaves say
nearly the same thing, three bad things follow and none of them is visible from
a green gate:

  * a user's question cannot be routed correctly even in principle, because
    both leaves answer it;
  * an evaluation case for either one can only be made to pass by reaching for
    vocabulary the other happens to lack, which is tuning, not testing;
  * the catalogue claims two capabilities where it has one.

Case authors kept running into these pairs by hand. This finds them by
measurement: Jaccard similarity over each leaf's description+body token set.

Candidate pairs are drawn within a pack and, inside the big packs, within a
standard-designator group (the leading slug segment, e.g. `e5053`), because a
leaf overlaps meaningfully only with its own standard's neighbours and the
all-pairs comparison over 2,534 leaves is 3.2M comparisons for no extra signal.

A high score is NOT a verdict. Two clauses can state opposite rules in almost
identical words -- `e5053-reserved-field-zero` (sender writes zero) and
`-not-zero` (receiver rejects) are a real pair, not a duplicate. This produces
a review list, ranked, and a human decides.

    python3 tools/leaf_overlap.py --top 40
    python3 tools/leaf_overlap.py --min 0.55 --tsv pairs.tsv

Standard library only; no network; deterministic; writes nothing but --tsv.
"""

import argparse
import os
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXPORT = os.path.join(_HERE, "export")
for _p in (_EXPORT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import reference_router  # noqa: E402
import router_coverage as rc  # noqa: E402


def group_key(path):
    """Pack, plus the standard designator when the pack is a large flat one."""
    parts = path.split("/")
    pack = "/".join(parts[:2])
    slug = parts[-1]
    head = slug.split("-")[0]
    # a designator looks like e5053 / q6013 / e20 / do178c
    if any(ch.isdigit() for ch in head):
        return "%s::%s" % (pack, head)
    return pack


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo")
    ap.add_argument("--min", type=float, default=0.55)
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--tsv")
    args = ap.parse_args()

    root = rc.repo_root(args.repo)
    index = reference_router.SkillIndex.from_tree(os.path.join(root, "skills"))

    groups = defaultdict(list)
    for entry in index.entries:
        tokens = entry.description_tokens | entry.body_tokens
        if tokens:
            groups[group_key(entry.path)].append((entry.path, tokens))

    pairs = []
    compared = 0
    for members in groups.values():
        for i in range(len(members)):
            p1, t1 = members[i]
            for j in range(i + 1, len(members)):
                p2, t2 = members[j]
                compared += 1
                inter = len(t1 & t2)
                if not inter:
                    continue
                jac = inter / float(len(t1) + len(t2) - inter)
                if jac >= args.min:
                    pairs.append((jac, p1, p2))

    pairs.sort(reverse=True)
    print("================= leaf overlap =================")
    print("leaves indexed                       %6d" % len(index.entries))
    print("candidate groups                     %6d" % len(groups))
    print("pairs compared                       %6d" % compared)
    print("pairs at Jaccard >= %.2f              %6d" % (args.min, len(pairs)))
    print("================================================")
    for jac, p1, p2 in pairs[:args.top]:
        print("  %.3f  %s" % (jac, p1.split("/")[-1]))
        print("         %s" % p2.split("/")[-1])
    if len(pairs) > args.top:
        print("  ... and %d more at or above the threshold" % (len(pairs) - args.top))

    if args.tsv:
        with open(args.tsv, "w", encoding="utf-8") as handle:
            handle.write("jaccard\tleaf_a\tleaf_b\n")
            for jac, p1, p2 in pairs:
                handle.write("%.4f\t%s\t%s\n" % (jac, p1, p2))
        print("\nwrote %s" % args.tsv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
