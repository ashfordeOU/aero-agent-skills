#!/usr/bin/env python3
"""leaf-audit.py — per-leaf completeness audit across the whole skill tree.

For EVERY leaf SKILL.md under skills/, verify the artifacts that make a
skill implementable / enforceable / verifiable / certifiable:
  A. SKILL.md exists + parseable frontmatter (name, description, what/when)
  B. logic script present (scripts/*.py excluding test_*)
  C. behavior contract test present (scripts/test_*.py)
  D. test file actually imports/runs (compile check)
  E. corpus task(s) exist for this leaf in eval/hit1-*.yaml (Hit@1 coverage)
  F. eval json exists (eval/skill-eval/<leaf>.json or eval/<leaf>.json)
  G. skill is rated (eval/skill-ratings.md row)
  H. description quality: has when+trigger, not just what

Reports:
  --summary   per-family completeness table (default)
  --missing   list every leaf missing any artifact (with which)
  --leaf PATH deep-check one leaf (all gates + file sizes + head of SKILL.md)
  --json      machine-readable output

Exit 0 = every leaf complete; 1 = gaps found.
"""
import argparse
import json
import os
import re
import sys
import glob

REPO = os.path.expanduser("~/AeroSkills")
SKILLS = os.path.join(REPO, "skills")
EVAL = os.path.join(REPO, "eval")
RATINGS = os.path.join(EVAL, "skill-ratings.md")

# corpus task yaml files (wave fragments + main)
CORPUS_FILES = glob.glob(os.path.join(EVAL, "hit1-*.yaml")) + glob.glob(os.path.join(EVAL, "hit1-*.yml"))


def frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    d = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            d[k.strip()] = v.strip().strip('"\'')
    return d


def find_leaves():
    """Return list of (rel_path, leaf_name, dir_path) for every SKILL.md under skills/
    excluding routers at family top-level (those are pack routers, not leaves)."""
    leaves = []
    for root, dirs, files in os.walk(SKILLS):
        if "SKILL.md" in files:
            rel = os.path.relpath(root, SKILLS)
            # a leaf is a SKILL.md whose parent dir name == leaf name AND
            # it has scripts/ or is deeper than family/pack/leaf
            parts = rel.split(os.sep)
            # depth >= 3 (family/pack/leaf) counts as leaf; depth 2 could be pack router
            is_leaf = len(parts) >= 3
            # pack router = family/pack-name with SKILL.md at depth 2
            name = os.path.basename(root)
            leaves.append({"rel": rel, "name": name, "dir": root, "is_leaf": is_leaf})
    return leaves


def corpus_targets():
    """Parse all hit1 yaml files for expected skill names."""
    targets = set()
    for cf in CORPUS_FILES:
        try:
            t = open(cf, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in re.finditer(r"(?:expected|target|skill):\s*[\"']?([\w/.-]+)", t):
            targets.add(m.group(1))
        for m in re.finditer(r"id:\s*[\"']?([\w-]+)", t):
            targets.add(m.group(1))
    return targets


def leaf_leafname_variants(rel: str, name: str):
    """Variants a corpus task may use to reference this leaf."""
    vs = {name, rel, rel.replace("/", "-"), rel.replace("/", "_"), rel.split("/")[-1]}
    return vs


def audit_leaf(leaf: dict, corpus: set, ratings_text: str) -> dict:
    rel, name, d = leaf["rel"], leaf["name"], leaf["dir"]
    res = {"rel": rel, "name": name, "ok": True, "missing": []}

    # A. SKILL.md + frontmatter
    skill_path = os.path.join(d, "SKILL.md")
    skill_text = open(skill_path, encoding="utf-8", errors="replace").read()
    fm = frontmatter(skill_text)
    if not fm:
        res["missing"].append("A:frontmatter")
    for key in ("name", "description"):
        if key not in fm:
            res["missing"].append(f"A:{key}")

    # B. logic script(s)
    # Convention in this tree: logic module is <stem>_logic.py (or plain name),
    # test file is test_<stem>.py / test_<stem>_logic.py / <stem>_test.py.
    # A file is a TEST if it starts with test_ AND its remaining stem matches an
    # existing sibling stem, OR it ends _test.py. A LOGIC module never starts
    # with test_ unless it's the odd <name>_logic.py that has no logic sibling —
    # treat test_<x>_logic.py as test when <x>_logic.py exists as the logic.
    all_py = [f for f in os.listdir(os.path.join(d, "scripts"))
              if f.endswith(".py") and "__pycache__" not in f]
    stems = set()
    for f in all_py:
        stem = f[:-3]
        # strip test_ prefix or _test suffix to get the candidate logic stem
        if stem.startswith("test_"):
            stems.add(stem[len("test_"):])
        elif stem.endswith("_test"):
            stems.add(stem[:-len("_test")])
        else:
            stems.add(stem)
    scripts = []
    tests = []
    for f in all_py:
        stem = f[:-3]
        if stem.endswith("_test"):
            tests.append(f)
        elif stem.startswith("test_"):
            # test_<x> is a test if <x> is a known logic stem (incl. <x>_logic)
            core = stem[len("test_"):]
            if core in stems or core + "_logic" in stems or core in [s + "_logic" for s in stems]:
                tests.append(f)
            else:
                # no matching logic sibling — still count as test if it imports/asserts
                txt = open(os.path.join(d, "scripts", f), encoding="utf-8", errors="replace").read()
                if "def test_" in txt or "assert " in txt or "unittest" in txt:
                    tests.append(f)
                else:
                    scripts.append(f)
        else:
            scripts.append(f)
    if not scripts and not tests:
        res["missing"].append("B:no-scripts")
    if not scripts:
        res["missing"].append("B:no-logic")

    # C. test present
    if not tests:
        res["missing"].append("C:no-test")

    # D. compile check all py
    for pyf in scripts + tests:
        try:
            compile(open(os.path.join(d, "scripts", pyf), encoding="utf-8").read(), pyf, "exec")
        except SyntaxError:
            res["missing"].append(f"D:syntax-{pyf}")

    # E. corpus coverage (leaf referenced by any hit1 yaml?)
    variants = leaf_leafname_variants(rel, name)
    covered = bool(variants & corpus) if corpus else False
    if not covered:
        # second chance: search corpus text for the leaf's name as substring
        found = False
        for cf in CORPUS_FILES:
            t = open(cf, encoding="utf-8", errors="replace").read()
            if name in t:
                found = True
                break
        covered = found
    if not covered:
        res["missing"].append("E:no-corpus")

    # F. eval json
    eval_candidates = [
        os.path.join(EVAL, f"{name}.json"),
        os.path.join(EVAL, "skill-eval", f"{name}.json"),
    ]
    if not any(os.path.exists(c) for c in eval_candidates):
        res["missing"].append("F:no-eval-json")

    # G. rated
    if name not in ratings_text and rel not in ratings_text:
        res["missing"].append("G:not-rated")

    # H. description quality: when/trigger present
    desc = fm.get("description", "")
    if not re.search(r"when|use when|trigger", desc, re.I):
        res["missing"].append("H:desc-no-when")

    res["ok"] = len(res["missing"]) == 0
    res["n_scripts"] = len(scripts)
    res["n_tests"] = len(tests)
    res["skill_size"] = os.path.getsize(skill_path)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", action="store_true", default=True)
    ap.add_argument("--missing", action="store_true")
    ap.add_argument("--leaf", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    leaves = [l for l in find_leaves() if l["is_leaf"]]
    corpus = corpus_targets()
    ratings_text = ""
    if os.path.exists(RATINGS):
        ratings_text = open(RATINGS, encoding="utf-8", errors="replace").read()

    results = [audit_leaf(l, corpus, ratings_text) for l in leaves]
    n_ok = sum(1 for r in results if r["ok"])
    n_total = len(results)

    if args.json:
        print(json.dumps({"total": n_total, "complete": n_ok, "gaps": n_total - n_ok,
                          "results": results}, indent=1))
        return 0 if n_ok == n_total else 1

    if args.leaf:
        leaf = next((r for r in results if r["rel"] == args.leaf or r["name"] == args.leaf), None)
        if not leaf:
            print(f"leaf not found: {args.leaf}")
            return 2
        print(json.dumps(leaf, indent=2))
        return 0 if leaf["ok"] else 1

    print(f"LEAF AUDIT — {n_total} leaves · {n_ok} complete · {n_total - n_ok} with gaps\n")
    if args.missing:
        for r in results:
            if not r["ok"]:
                print(f"  ✗ {r['rel']}: {', '.join(r['missing'])}")
        print()

    # family summary
    fam = {}
    for r in results:
        f = r["rel"].split("/")[0]
        fam.setdefault(f, {"total": 0, "ok": 0})
        fam[f]["total"] += 1
        fam[f]["ok"] += 1 if r["ok"] else 0
    print(f"{'Family':<28}{'Total':>6}{'OK':>6}{'Gaps':>6}  {'Pct':>6}")
    for f in sorted(fam):
        d = fam[f]
        pct = 100 * d["ok"] / d["total"] if d["total"] else 0
        print(f"{f:<28}{d['total']:>6}{d['ok']:>6}{d['total']-d['ok']:>6}  {pct:>5.1f}%")

    return 0 if n_ok == n_total else 1


if __name__ == "__main__":
    sys.exit(main())
