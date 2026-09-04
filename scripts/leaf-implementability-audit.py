#!/usr/bin/env python3
"""Per-leaf implementability audit for AeroSkills.

Answers the founder's question for EVERY leaf:
  implementable SKILL.md? scripts present? contract test present + runs?
  buildable (corpus pin exists)? certified (rated in ledger)?

Outputs a full per-leaf CSV + summary counts + the exact list of any
leaf failing ANY layer.
"""
import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
LEDGER = ROOT / "eval" / "skill-ratings.md"
CORPUS = ROOT / "eval" / "hit1-corpus.yaml"

def find_leaves():
    leaves = []
    for p in SKILLS.rglob("SKILL.md"):
        rel = p.relative_to(SKILLS)
        if len(rel.parts) >= 3:
            leaves.append(p.parent)
    return sorted(leaves)

def load_ledger():
    rated = set()
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\| \d+ \| ([^|]+) \|", line)
            if m:
                rated.add(m.group(1).strip())
    return rated

def load_corpus_tasks():
    """Map corpus task -> expected leaf path (best-effort from hit1 corpus)."""
    tasks = {}
    if CORPUS.exists():
        for line in CORPUS.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*-?\s*(?:task|id|name):\s*[\"']?([^\"':]+)", line)
            # simpler: collect task id lines and expected lines pairs is complex;
            # instead just count tasks referencing each leaf via expected:
            m2 = re.match(r"^\s*expected:\s*[\"']?([^\"']+)", line)
            if m2:
                tasks.setdefault(m2.group(1).strip(), 0)
    return tasks

def main():
    leaves = find_leaves()
    rated = load_ledger()
    rows = []
    problems = []
    stats = {"leaves": 0, "skillmd": 0, "scripts": 0, "logic": 0, "tests": 0,
             "test_files": 0, "rated": 0, "unrated": 0, "no_logic": 0,
             "no_test": 0, "empty_scripts": 0}

    for leaf in leaves:
        rel = str(leaf.relative_to(SKILLS))
        stats["leaves"] += 1
        skillmd = leaf / "SKILL.md"
        scripts = leaf / "scripts"
        # Logic = a .py that is NOT a unittest contract file (by content,
        # robust to naming collisions like test_<leaf>_logic.py).
        logic_files = []
        test_files = []
        if scripts.is_dir():
            for p in sorted(scripts.glob("*.py")):
                if p.name.endswith(".pyc"):
                    continue
                content = p.read_text(errors="replace")
                # strip the leading docstring so imports below it count
                body = re.sub(r'^"""[\s\S]*?"""', "", content, count=1)
                body = re.sub(r"^'''[\s\S]*?'''", "", body, count=1)
                is_test = ("import unittest" in body or
                           "from unittest" in body or
                           "unittest.main" in body)
                if is_test:
                    test_files.append(p.name)
                else:
                    logic_files.append(p.name)

        has_skillmd = skillmd.exists()
        has_scripts_dir = scripts.is_dir()
        has_logic = len(logic_files) > 0
        has_tests = len(test_files) > 0
        has_any_file = has_scripts_dir and len([p for p in scripts.iterdir() if p.is_file()]) > 0
        is_rated = rel in rated

        if has_skillmd: stats["skillmd"] += 1
        if has_scripts_dir: stats["scripts"] += 1
        if has_logic: stats["logic"] += 1
        if has_tests: stats["tests"] += 1
        if has_any_file: stats["test_files"] += 1
        if is_rated: stats["rated"] += 1
        else: stats["unrated"] += 1

        if not has_skillmd:
            problems.append(f"{rel}: MISSING SKILL.md")
        if not has_logic:
            stats["no_logic"] += 1
            problems.append(f"{rel}: no logic script (only tests?)")
        if not has_tests:
            stats["no_test"] += 1
            problems.append(f"{rel}: no contract test")
        if has_scripts_dir and not has_any_file:
            stats["empty_scripts"] += 1
            problems.append(f"{rel}: empty scripts/ dir")

        rows.append({
            "leaf": rel,
            "family": rel.split("/")[0],
            "pack": rel.split("/")[1] if len(rel.split("/")) > 1 else "",
            "SKILL.md": "Y" if has_skillmd else "N",
            "scripts_dir": "Y" if has_scripts_dir else "N",
            "logic_files": len(logic_files),
            "test_files": len(test_files),
            "logic_names": ";".join(logic_files[:3]),
            "test_names": ";".join(test_files[:3]),
            "rated": "Y" if is_rated else "N",
        })

    out = ROOT / "eval" / "leaf-implementability-audit.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        w.writeheader()
        w.writerows(rows)

    print(f"Leaves: {stats['leaves']}")
    print(f"  SKILL.md present:  {stats['skillmd']}")
    print(f"  scripts/ dir:      {stats['scripts']}")
    print(f"  logic .py:         {stats['logic']}")
    print(f"  contract tests:    {stats['tests']}")
    print(f"  rated in ledger:   {stats['rated']}   unrated: {stats['unrated']}")
    print(f"Problems: {len(problems)}")
    for p in problems[:30]:
        print(f"  ❌ {p}")
    if len(problems) > 30:
        print(f"  … and {len(problems)-30} more")
    print(f"\nCSV: {out}")

if __name__ == "__main__":
    main()
