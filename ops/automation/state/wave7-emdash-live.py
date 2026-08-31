#!/usr/bin/env python3
"""Em-dash scan of the LIVE published tree: skills/, README.md, STANDARDS.md,
NOTICE, docs/ (excluding dated plans/), eval/ (excluding dated wave fragments).
Matches the wave close-out scope."""
import pathlib
import sys

root = pathlib.Path("/Users/enterprisehq/AeroSkills")
hits = []
check = []
check.append(root / "skills")
check.append(root / "README.md")
check.append(root / "STANDARDS.md")
check.append(root / "NOTICE")
for d in (root / "docs", root / "eval"):
    if d.is_dir():
        for p in d.rglob("*"):
            if p.is_file() and p.suffix in (".md", ".py", ".yaml", ".yml", ".sh"):
                if "plans" in p.parts:
                    continue
                if "hit1-wave" in p.name and p.parent == root / "eval":
                    continue  # dated historical fragments
                check.append(p)
for p in check:
    if p.is_dir():
        for f in p.rglob("*"):
            if f.is_file() and f.suffix in (".md", ".py", ".yaml", ".yml", ".sh"):
                text = f.read_text(encoding="utf-8", errors="replace")
                if "\u2014" in text:
                    hits.append((str(f.relative_to(root)), text.count("\u2014")))
    elif p.is_file():
        text = p.read_text(encoding="utf-8", errors="replace")
        if "\u2014" in text:
            hits.append((str(p.relative_to(root)), text.count("\u2014")))
if hits:
    for p, n in hits:
        print(f"EMDASH {n}x {p}")
    sys.exit(1)
print("em dashes: 0 in live published tree (skills/ + README + STANDARDS + NOTICE + live docs + live eval)")
