#!/usr/bin/env python3
"""Corpus fragment naming coherence.

leaf-create-gate.sh resolves corpus coverage with
    ls eval/hit1-*"$LEAF_NAME"*.yaml
a glob wildcarded on BOTH sides, so every invented prefix satisfies it. That is
why 14 concurrent builders could file the same corpus under three different
names (hit1-e2008-*, hit1-w0913-e2008-*, hit1-wave-e2008-*) without a single
gate going red.

Loosening the glob would break the legacy hit1-wave1-* / hit1-wave2-* fragments,
whose names predate the slug convention. So this check does not mandate a name -
it fails when ONE leaf is covered by fragments under MORE THAN ONE spelling,
which is the defect itself and cannot be produced by legacy naming.

Exit 0 clean, 1 on any leaf with multiple spellings.
"""
from __future__ import annotations
import pathlib, re, sys, collections

def main() -> int:
    repo = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent
    evald, skills = repo / "eval", repo / "skills"
    if not evald.is_dir():
        print("PASS corpus-naming: no eval/ dir"); return 0

    leaves = {p.parent.name for p in skills.glob("*/*/*/SKILL.md")}
    frags = sorted(evald.glob("hit1-*.yaml"))

    # Longest leaf slug contained in the filename wins, so
    # hit1-wave-e2008-esd-test-process maps to e2008-esd-test-process, not a
    # shorter leaf that happens to be a substring of it.
    covers: dict[str, list[str]] = collections.defaultdict(list)
    for f in frags:
        stem = f.stem
        hit = max((s for s in leaves if s in stem), key=len, default=None)
        if hit:
            covers[hit].append(f.name)

    bad = {leaf: names for leaf, names in covers.items() if len(names) > 1}
    if bad:
        print(f"FAIL corpus-naming: {len(bad)} leaf/leaves covered under more than one spelling")
        for leaf, names in sorted(bad.items()):
            print(f"  {leaf}")
            for n in sorted(names):
                print(f"    - eval/{n}")
        print("  Fix: one fragment per leaf. The slug is unique, so the slug is the name:")
        print("       eval/hit1-<slug>.yaml")
        return 1

    print(f"PASS corpus-naming: {len(frags)} fragment(s) cover {len(covers)} leaf/leaves, "
          f"one spelling each")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
