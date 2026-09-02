#!/usr/bin/env python3
"""Pack inventory for per-domain install (founder directive 2026-08-31).

Reads every skills/**/SKILL.md frontmatter and prints the leaf skills
grouped by domain pack so an installer can install only the pack the
user needs (e.g. only the avionics pack, only the space-systems pack).
Deterministic, offline; stdlib + PyYAML (same pinned dependency as
spec_lint.py / router_eval.py).

Fields read (top-level frontmatter): domain, pack, name.
- A pack router SKILL.md sits at the pack root (rel path has no slash);
  it is validated but not listed as a leaf, and its pack field must
  equal the router folder name.
- A leaf SKILL.md sits under the pack (rel path has a slash); its pack
  field must equal the first path segment.
- domain must be one of the canonical 12-discipline taxonomy
  (research/briefs/05-domain-taxonomy.md section 1).

Exit 0 = inventory printed. Exit 1 = any SKILL.md is missing domain,
pack, or name, a leaf's pack field disagrees with its path, a router's
pack field disagrees with its folder, or domain is not in the taxonomy
(an installer must never silently install an untyped skill).

Usage:
  pack_inventory.py [skills_dir] [--pack NAME] [--domain NAME]

Output: one line per leaf skill path, then a summary line
"packs=N skills=M" (N distinct packs, M leaf skills listed).
"""

import argparse
import pathlib
import sys

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_SKILLS = REPO_ROOT / "skills"

# Canonical 12-discipline taxonomy (research/briefs/05-domain-taxonomy.md
# section 1). domain frontmatter must be one of these; packs are the
# installable subsets that today map 1:1 to a domain.
TAXONOMY_DOMAINS = frozenset(
    {
        "aerodynamics",
        "propulsion",
        "structures",
        "flight-mechanics",
        "gnc-autonomy",
        "avionics",
        "systems-engineering-safety",
        "space-systems",
        "vehicle-design",
        "manufacturing-quality",
        "flight-test-operations",
        "cross-cutting",
    }
)


def load_entries(root):
    entries = []
    for p in sorted(root.rglob("SKILL.md")):
        text = p.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        parts = text.split("---", 2)
        try:
            fm = yaml.safe_load(parts[1])
        except Exception:  # noqa: BLE001
            fm = None
        if not isinstance(fm, dict):
            continue
        entries.append((str(p.parent.relative_to(root)), fm))
    return entries


def main():
    ap = argparse.ArgumentParser(
        description="List domain-pack skills for per-domain install."
    )
    ap.add_argument("skills_dir", nargs="?", type=pathlib.Path, default=DEFAULT_SKILLS)
    ap.add_argument("--pack", default=None, help="only list skills in this pack")
    ap.add_argument("--domain", default=None, help="only list skills in this domain")
    args = ap.parse_args()

    if not args.skills_dir.is_dir():
        print(
            "FAIL pack_inventory: %s is not a directory" % args.skills_dir,
            file=sys.stderr,
        )
        sys.exit(1)

    leaves = []
    fail = 0
    for rel, fm in load_entries(args.skills_dir):
        name = fm.get("name")
        domain = fm.get("domain")
        pack = fm.get("pack")
        if not name or not domain or not pack:
            print(
                "FAIL pack_inventory: %s missing domain/pack/name frontmatter" % rel,
                file=sys.stderr,
            )
            fail = 1
            continue
        if domain not in TAXONOMY_DOMAINS:
            print(
                "FAIL pack_inventory: %s domain '%s' not in taxonomy"
                % (rel, domain),
                file=sys.stderr,
            )
            fail = 1
            continue
        if "/" not in rel:
            if pack != rel:
                print(
                    "FAIL pack_inventory: router %s pack '%s' != router folder '%s'"
                    % (rel, pack, rel),
                    file=sys.stderr,
                )
                fail = 1
            continue  # pack router SKILL.md; validated, not a leaf
        first = rel.split("/", 1)[0]
        if pack != first:
            print(
                "FAIL pack_inventory: %s pack '%s' != path segment '%s'"
                % (rel, pack, first),
                file=sys.stderr,
            )
            fail = 1
            continue
        if args.pack and pack != args.pack:
            continue
        if args.domain and domain != args.domain:
            continue
        leaves.append((pack, rel))

    if fail:
        sys.exit(1)

    for pack, rel in sorted(leaves, key=lambda pair: pair[1]):
        print(rel)
    print("packs=%d skills=%d" % (len({p for p, _ in leaves}), len(leaves)))
    sys.exit(0)


if __name__ == "__main__":
    main()
