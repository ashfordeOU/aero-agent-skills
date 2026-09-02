#!/usr/bin/env python3
"""Wave-16 close check: every family router description <= 1024 chars (yaml-verified)."""
import pathlib
import sys
import yaml

ROOT = pathlib.Path("<AEROSKILLS-ROOT>")
SKILLS = ROOT / "skills"

fail = False
for fam in sorted(p.name for p in SKILLS.iterdir() if p.is_dir()):
    p = SKILLS / fam / "SKILL.md"
    if not p.exists():
        print(f"FAIL: no router at {p}")
        fail = True
        continue
    text = p.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    fm = yaml.safe_load(parts[1]) if len(parts) >= 3 else {}
    desc = fm.get("description", "")
    n = len(desc)
    status = "OK" if n <= 1024 else "TOO_LONG"
    if n > 1024:
        fail = True
    print(f"{fam}: desc_len={n} {status}")

if fail:
    print("FAIL: one or more router descriptions exceed 1024 chars")
    sys.exit(1)
print("PASS: all router descriptions <= 1024 chars")
