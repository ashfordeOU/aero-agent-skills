#!/usr/bin/env python3
"""Corpus fragment naming coherence, with a stated denominator.

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

DENOMINATOR (2026-09-19). A leaf can only be compared when at least one fragment
names it. Leaves with no fragment are not evidence of coherence, they are the
absence of evidence - and until now they passed silently, so a run that graded
half the tree printed the same PASS a run over the whole tree would print. Every
run now states what it graded, what it could not grade, and why. A run that
graded ZERO leaves prints EMPTY, never PASS, and fails under --strict.

Scope note: fragment COVERAGE (every leaf should have a fragment) is
leaf-create-gate.sh's contract, not this gate's. The uncovered remainder is
reported here as a WARN with its exact count so the number is visible, and
--strict rejects only a zero denominator, not an incomplete one.

Usage: corpus_naming_check.py [repo_root] [--strict]
Exit 0 clean or EMPTY, 1 on a multi-spelling leaf (or on EMPTY with --strict).
"""
from __future__ import annotations
import collections
import pathlib
import sys

LEAF_GLOB = "*/*/*/SKILL.md"  # domain / sub-domain / leaf


def main() -> int:
    argv = sys.argv[1:]
    strict = "--strict" in argv
    positional = [a for a in argv if not a.startswith("-")]
    repo = pathlib.Path(positional[0]) if positional else pathlib.Path(__file__).resolve().parent.parent
    evald, skills = repo / "eval", repo / "skills"

    leaves = {p.parent.name for p in skills.glob(LEAF_GLOB)}
    # SKILL.md files that sit at another depth are domain/pack index skills.
    # They are not leaves and are never graded here; count them so the gap
    # between "SKILL.md files in the tree" and "leaves graded" is not a mystery.
    off_depth = sum(1 for p in skills.rglob("SKILL.md")
                    if len(p.relative_to(skills).parts) != 4)

    if not evald.is_dir():
        print("corpus-naming denominator report (what this gate graded, and what it could not)")
        print("  leaf skills discovered ............... %d   (skills/%s)" % (len(leaves), LEAF_GLOB))
        print("  corpus fragments discovered .......... 0   (there is no eval/ directory)")
        print("  LEAVES GRADED (denominator) .......... 0")
        print("EMPTY corpus-naming: denominator 0 - no eval/ directory exists, so not one leaf "
              "could be compared. This run verified NOTHING; a green here is not evidence of "
              "naming coherence. Re-run with --strict to make a zero denominator a failure.")
        return 1 if strict else 0

    frags = sorted(evald.glob("hit1-*.yaml"))

    # Longest leaf slug contained in the filename wins, so
    # hit1-wave-e2008-esd-test-process maps to e2008-esd-test-process, not a
    # shorter leaf that happens to be a substring of it.
    covers: dict[str, list[str]] = collections.defaultdict(list)
    unmapped: list[str] = []
    for f in frags:
        stem = f.stem
        hit = max((s for s in leaves if s in stem), key=len, default=None)
        if hit:
            covers[hit].append(f.name)
        else:
            unmapped.append(f.name)

    graded = len(covers)
    ungraded = len(leaves) - graded
    bad = {leaf: names for leaf, names in covers.items() if len(names) > 1}
    pct = (100.0 * graded / len(leaves)) if leaves else 0.0

    print("corpus-naming denominator report (what this gate graded, and what it could not)")
    print("  leaf skills discovered ............... %d   (skills/%s)" % (len(leaves), LEAF_GLOB))
    print("  SKILL.md outside leaf depth .......... %d   (domain/pack index skills, never graded)" % off_depth)
    print("  corpus fragments discovered .......... %d   (eval/hit1-*.yaml)" % len(frags))
    print("  fragments naming no known leaf ....... %d   (unattributable, so they graded nothing)" % len(unmapped))
    print("  LEAVES GRADED (denominator) .......... %d   (%.1f%% of leaves; at least one fragment to compare)"
          % (graded, pct))
    print("  leaves NOT gradeable ................. %d   (no fragment names them; nothing to compare)" % ungraded)
    print("  leaves under more than one spelling .. %d" % len(bad))
    if unmapped:
        print("  fragments naming no known leaf:")
        for n in sorted(unmapped)[:10]:
            print("    - eval/%s" % n)
        if len(unmapped) > 10:
            print("    ... and %d more" % (len(unmapped) - 10))

    if bad:
        print("FAIL corpus-naming: %d leaf/leaves covered under more than one spelling" % len(bad))
        for leaf, names in sorted(bad.items()):
            print("  %s" % leaf)
            for n in sorted(names):
                print("    - eval/%s" % n)
        print("  Fix: one fragment per leaf. The slug is unique, so the slug is the name:")
        print("       eval/hit1-<slug>.yaml")
        return 1

    if graded == 0:
        print("EMPTY corpus-naming: denominator 0 - %d leaf skill(s) and %d fragment(s) exist, but not "
              "one leaf had a fragment to compare. This run verified NOTHING; a green here is not "
              "evidence of naming coherence. Re-run with --strict to make a zero denominator a failure."
              % (len(leaves), len(frags)))
        return 1 if strict else 0

    if ungraded:
        print("WARN corpus-naming: %d of %d leaves (%.1f%%) have no corpus fragment, so this gate says "
              "nothing about them. Coverage is leaf-create-gate.sh's contract, not this gate's; --strict "
              "here rejects only a ZERO denominator."
              % (ungraded, len(leaves), 100.0 * ungraded / len(leaves)))
    if unmapped:
        print("WARN corpus-naming: %d fragment(s) name no known leaf and graded nothing; each is either "
              "an aggregate file or an orphan left by a rename." % len(unmapped))
    print("PASS corpus-naming: %d of %d leaf/leaves graded, one spelling each "
          "(%d fragment(s), %d unattributable)" % (graded, len(leaves), len(frags), len(unmapped)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
