#!/usr/bin/env python3
"""Wave-8 close: verify every router description is <=1024 chars and 50-150
words (gate 1 spec-lint MAX_DESC + gate 2 desc-lint word bounds), and report
the max leaf description length. Exit 0 = all within budget."""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
skills = ROOT / "skills"

def desc_of(path):
    txt = path.read_text(encoding="utf-8")
    parts = txt.split("---", 2)
    if len(parts) < 3:
        return None
    import yaml
    fm = yaml.safe_load(parts[1])
    return fm.get("description") if isinstance(fm, dict) else None

fail = 0
routers = sorted(p for p in skills.glob("*/SKILL.md"))
for p in routers:
    d = desc_of(p)
    if d is None:
        print(f"FAIL {p}: no description")
        fail = 1
        continue
    n = len(d)
    w = len(d.split())
    flag = "OK" if n <= 1024 and 50 <= w <= 150 else "OVER"
    if flag == "OVER":
        fail = 1
    print(f"{flag} router {p.parent.name}: chars={n} words={w}")

max_leaf = 0
max_leaf_path = ""
for p in skills.rglob("*/SKILL.md"):
    if p.parent == skills:
        continue  # routers only
    d = desc_of(p)
    if d is None:
        continue
    if len(d) > max_leaf:
        max_leaf = len(d)
        max_leaf_path = str(p)
print(f"max leaf desc: {max_leaf} chars ({max_leaf_path})")
sys.exit(0 if fail == 0 else 1)
