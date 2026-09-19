#!/usr/bin/env python3
"""Leaf slug uniqueness and router-fragment ownership.

WHY THIS EXISTS
Leaf directories are per-standard (skills/<family>/<pack>/<slug>/), but two
downstream namespaces are FLAT and are keyed on the slug alone:

  1. the router corpus, eval/hit1-<slug>.yaml - one directory for the whole
     tree;
  2. the installed skill folder, which the npm installer flattens to
     <frontmatter name>/ (packages/aero-agent-skills/lib/install.js).

So two leaves under different standards that share a slug are not merely
untidy. They contend for one fragment filename: whichever builder writes
second overwrites the first, and the loser becomes unroutable while every
other gate stays green, because no gate compares a fragment's filename with
the leaf it actually describes.

WHAT IT CHECKS (all deterministic, stdlib only, no network)
  A. slug uniqueness    - every leaf slug occurs exactly once in the tree.
  B. name agreement     - frontmatter name equals the directory slug, so a
                          unique directory cannot re-open the collision
                          through the installer's flatten step.
  C. fragment ownership - no leaf is covered by more than one fragment file,
                          and a fragment named for a leaf describes THAT
                          leaf: every expected_skill in hit1-<slug>.yaml
                          resolves to the leaf whose slug names the file.
                          C is the direct test for a silent overwrite.
  D. fragment coverage  - every leaf has exactly one fragment. Reported
                          always, enforced only under --require-fragment:
                          the convention postdates most of the corpus, so a
                          large backlog of leaves is still carried inline in
                          eval/hit1-corpus.yaml instead. Enforcing D by
                          default would make this guard unwireable, and a
                          guard nobody can wire grades nothing. The deficit
                          is printed on every run so it cannot go quiet.

Complements scripts/corpus_naming_check.py (gate 9), which catches one leaf
spelled under several fragment names. This catches the opposite: several
leaves contending for one name. Gate 9's own docstring assumes "the slug is
unique" - A is the check that earns that assumption.

Exit 0 clean, 1 on any violation.
Usage:
  python3 tools/check_slug_uniqueness.py [repo_root] [--require-fragment]
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.M)
EXPECTED_RE = re.compile(r"""^\s*expected_skill:\s*["']([^"']+)["']""", re.M)
AGGREGATE = "hit1-corpus.yaml"


def frontmatter_name(skill_md):
    """Read the frontmatter name without a YAML parser (stdlib only)."""
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    block = text[3:end] if end != -1 else text[3:]
    m = NAME_RE.search(block)
    return m.group(1) if m else None


def collect_leaves(skills_dir):
    """Every skills/<family>/<pack>/<slug>/SKILL.md, as (slug, relpath, name)."""
    leaves = []
    for md in sorted(skills_dir.glob("*/*/*/SKILL.md")):
        rel = md.parent.relative_to(skills_dir).as_posix()
        leaves.append((md.parent.name, rel, frontmatter_name(md)))
    return leaves


def main(argv):
    flags = argv[1:]
    args = [a for a in flags if not a.startswith("--")]
    require_fragment = "--require-fragment" in flags
    repo = pathlib.Path(args[0]) if args else pathlib.Path(__file__).resolve().parent.parent
    skills_dir, eval_dir = repo / "skills", repo / "eval"

    if not skills_dir.is_dir():
        print("FAIL slug-uniqueness: no skills/ under %s" % repo)
        return 1

    leaves = collect_leaves(skills_dir)
    if not leaves:
        print("FAIL slug-uniqueness: no leaves found under %s" % skills_dir)
        return 1

    failures = 0

    # ---- A. slug uniqueness ------------------------------------------------
    by_slug = collections.defaultdict(list)
    for slug, rel, _ in leaves:
        by_slug[slug].append(rel)
    dups = {s: p for s, p in by_slug.items() if len(p) > 1}
    if dups:
        failures += 1
        n = sum(len(p) for p in dups.values())
        print("FAIL slug-uniqueness A: %d slug(s) used by %d leaves" % (len(dups), n))
        for slug, paths in sorted(dups.items()):
            print("  %s" % slug)
            for p in sorted(paths):
                print("    - skills/%s" % p)
        print("  Fix: give all but one a family-qualified slug, and rename its")
        print("       directory, logic module, test module, SKILL.md references")
        print("       and eval/hit1-<slug>.yaml together.")
    else:
        print("PASS slug-uniqueness A: %d leaves, %d distinct slugs"
              % (len(leaves), len(by_slug)))

    # ---- B. frontmatter name agreement -------------------------------------
    mismatched = [(rel, slug, name) for slug, rel, name in leaves if name != slug]
    if mismatched:
        failures += 1
        print("FAIL slug-uniqueness B: %d leaf/leaves whose name is not its directory"
              % len(mismatched))
        for rel, slug, name in sorted(mismatched):
            print("  skills/%s: name=%r dir=%r" % (rel, name, slug))
        print("  Fix: the installer flattens on the frontmatter name, so the")
        print("       name must be the slug or the collision returns on install.")
    else:
        print("PASS slug-uniqueness B: every leaf name equals its directory slug")

    # ---- C/D. router fragments ---------------------------------------------
    if not eval_dir.is_dir():
        print("SKIP slug-uniqueness C/D: no eval/ directory")
        return 1 if failures else 0

    slugs = set(by_slug)
    frags = [f for f in sorted(eval_dir.glob("hit1-*.yaml")) if f.name != AGGREGATE]

    # Same mapping rule as gate 9: the LONGEST leaf slug inside the filename
    # wins, so a short slug that is a substring of a longer one cannot steal
    # a fragment that belongs to the longer leaf.
    covers = collections.defaultdict(list)
    for f in frags:
        hit = max((s for s in slugs if s in f.stem), key=len, default=None)
        if hit:
            covers[hit].append(f.name)

    multi = {s: names for s, names in covers.items() if len(names) > 1}
    misdescribed = []
    for f in frags:
        stem_slug = f.stem[len("hit1-"):]
        if stem_slug not in slugs:
            continue  # legacy wave-* name; gate 9 documents why these stay
        owner = by_slug[stem_slug][0]
        text = f.read_text(encoding="utf-8", errors="replace")
        wrong = sorted({e for e in EXPECTED_RE.findall(text) if e != owner})
        if wrong:
            misdescribed.append((f.name, owner, wrong))

    if multi or misdescribed:
        failures += 1
        print("FAIL slug-uniqueness C: %d leaf/leaves under several fragments, "
              "%d fragment(s) describing another leaf" % (len(multi), len(misdescribed)))
        for slug, names in sorted(multi.items()):
            print("  %s covered by %d fragments:" % (slug, len(names)))
            for n in sorted(names):
                print("    - eval/%s" % n)
        for name, owner, wrong in sorted(misdescribed):
            print("  eval/%s is named for %s but points at:" % (name, owner))
            for w in wrong:
                print("    - %s" % w)
        print("  Fix: one fragment per leaf, named eval/hit1-<slug>.yaml, whose")
        print("       expected_skill is that leaf. A fragment named for one leaf")
        print("       and describing another is an overwritten fragment.")
    else:
        print("PASS slug-uniqueness C: %d fragment(s) map to %d leaf/leaves, "
              "one fragment each, each describing its own leaf"
              % (len(frags), len(covers)))

    # ---- D. coverage --------------------------------------------------------
    uncovered = sorted(slugs - set(covers))
    if uncovered:
        label = "FAIL" if require_fragment else "NOTE"
        print("%s slug-uniqueness D: %d of %d leaves have no eval/hit1-<slug>.yaml fragment"
              % (label, len(uncovered), len(slugs)))
        if require_fragment:
            failures += 1
            for s in uncovered:
                print("  - %s" % by_slug[s][0])
        else:
            for s in uncovered[:10]:
                print("  - %s" % by_slug[s][0])
            if len(uncovered) > 10:
                print("  ... and %d more (run with --require-fragment to list all and fail)"
                      % (len(uncovered) - 10))
    else:
        print("PASS slug-uniqueness D: every leaf has a fragment")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
