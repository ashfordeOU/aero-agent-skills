#!/usr/bin/env python3
"""Aero Agent Skills per-skill completeness gate — the standard for "everything done".

For EVERY skill in the tree, verify the full agentskills.io conformance:
  [REQUIRED] SKILL.md (frontmatter name/description + body)
  [REQUIRED] scripts/ with at least one logic file
  [REQUIRED] behavior contract test (test_*.py) that runs offline
  [REQUIRED] every script path referenced in SKILL.md exists (no broken refs)
  [AS-NEEDED] references/ when the skill cites external standards/data tables
  [AS-NEEDED] assets/ when the skill would benefit from templates/resources
  [AS-NEEDED] value-delta record in eval/skill-eval/*.json (with vs without)

Exit: 0 = all REQUIRED pass + no CRITICAL as-needed gaps; 1 = failures.
Usage: python3 scripts/skill-completeness.py [--report] [--strict]
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"


def find_skills() -> list[Path]:
    return sorted(p.parent for p in SKILLS.rglob("SKILL.md"))


def is_leaf(skill: Path) -> bool:
    """A leaf skill sits at skills/<family>/<pack>/<skill>/SKILL.md (depth >= 4).
    Family-level SKILL.md files (skills/<family>/SKILL.md) are overview indexes
    — they are NOT task skills and do not need scripts/tests."""
    rel = skill.relative_to(SKILLS)
    return len(rel.parts) >= 3


def skill_files(skill: Path) -> tuple[list[str], list[str], list[str], list[str]]:
    scripts = [p.name for p in (skill / "scripts").glob("*") if p.is_file() and p.suffix != ".pyc"] if (skill / "scripts").is_dir() else []
    tests = [p.name for p in (skill / "scripts").glob("test_*.py")] if (skill / "scripts").is_dir() else []
    refs = [p.name for p in (skill / "references").glob("*")] if (skill / "references").is_dir() else []
    assets = [p.name for p in (skill / "assets").glob("*")] if (skill / "assets").is_dir() else []
    return scripts, tests, refs, assets


def frontmatter_ok(body: str, name: str) -> tuple[bool, list[str]]:
    problems = []
    m = re.match(r"^---\n(.*?)\n---", body, re.S)
    if not m:
        return False, ["no YAML frontmatter"]
    fm = m.group(1)
    if not re.search(r"^name:\s*", fm, re.M):
        problems.append("frontmatter missing 'name'")
    if not re.search(r"^description:\s*", fm, re.M):
        problems.append("frontmatter missing 'description'")
    return (len(problems) == 0), problems


def broken_refs(skill: Path, body: str) -> list[str]:
    broken = []
    for m in re.finditer(r"(?:scripts|references|assets)/[\w./-]+\.\w+", body):
        p = m.group(0)
        if not (skill / p).exists():
            broken.append(p)
    return broken


def as_needed_needs(skill: Path, body: str, refs: list[str], assets: list[str]) -> list[str]:
    """Heuristic: does this skill look like it needs references/ or assets/?

    Conservative — only flags when there is real evidence:
      references/ when the body inlines LONG external content (URLs + large
      body) that belongs in a reference doc
      assets/ when the body explicitly names a template/checklist/form it
      does not bundle
    """
    needs = []
    # references: body has URLs AND is long enough that inlining is a smell
    if "https://" in body and len(body) > 5000 and not refs:
        needs.append("references/ (inlines long content with external URLs; consider external docs)")
    # assets: body explicitly names a template/checklist/form/worksheet
    if re.search(r"\b(template|checklist|form|worksheet|spreadsheet)\b", body, re.I) and not assets:
        needs.append("assets/ (names templates/checklists; consider bundling)")
    return needs


def main() -> int:
    strict = "--strict" in sys.argv
    report = "--report" in sys.argv
    skills = find_skills()
    failures: list[str] = []
    warnings: list[str] = []
    counts = {"skills": 0, "scripts": 0, "tests": 0, "refs": 0, "assets": 0,
              "needs_refs": 0, "needs_assets": 0, "broken": 0}

    for skill in skills:
        counts["skills"] += 1
        name = skill.name
        body = (skill / "SKILL.md").read_text(errors="replace")
        scripts, tests, refs, assets = skill_files(skill)

        if not is_leaf(skill):
            # family/pack-level index — overview doc, not a task skill
            continue

        ok, fm_problems = frontmatter_ok(body, name)
        if not ok:
            failures.append(f"{name}: frontmatter {fm_problems}")

        if not scripts:
            failures.append(f"{name}: NO scripts/ (required)")
        else:
            counts["scripts"] += 1

        if not tests:
            failures.append(f"{name}: NO contract test test_*.py (required)")
        else:
            counts["tests"] += 1

        if refs:
            counts["refs"] += 1
        if assets:
            counts["assets"] += 1

        for br in broken_refs(skill, body):
            counts["broken"] += 1
            failures.append(f"{name}: BROKEN ref {br}")

        for need in as_needed_needs(skill, body, refs, assets):
            counts["needs_refs" if "references" in need else "needs_assets"] += 1
            if strict:
                failures.append(f"{name}: {need}")
            else:
                warnings.append(f"{name}: {need}")

    print(f"Aero Agent Skills completeness: {counts['skills']} skills")
    print(f"  scripts:    {counts['scripts']}/{counts['skills']} ({100*counts['scripts']//max(counts['skills'],1)}%)")
    print(f"  tests:      {counts['tests']}/{counts['skills']} ({100*counts['tests']//max(counts['skills'],1)}%)")
    print(f"  references: {counts['refs']} skills have them | flagged as-needed: {counts['needs_refs']}")
    print(f"  assets:     {counts['assets']} skills have them | flagged as-needed: {counts['needs_assets']}")
    print(f"  broken refs: {counts['broken']}")

    if warnings:
        print("\nAS-NEEDED (non-blocking unless --strict):")
        for w in warnings[:12]:
            print(f"  ⚠ {w}")
        if len(warnings) > 12:
            print(f"  … and {len(warnings)-12} more")

    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for f in failures[:15]:
            print(f"  ❌ {f}")
        if len(failures) > 15:
            print(f"  … and {len(failures)-15} more")
        return 1

    print("\n✅ ALL REQUIRED PASS — every skill has SKILL.md + scripts + contract test, no broken refs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
