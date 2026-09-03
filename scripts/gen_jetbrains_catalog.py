#!/usr/bin/env python3
"""Generate the JetBrains plugin skill catalog (catalog.json).

Reads the repo's skills/ tree (leaf SKILL.md frontmatter) and emits a
compact JSON list for the IDE catalog browser. The plugin bundle task
copies this into the plugin resources so the tool window works offline.
"""
import json
import pathlib
import sys
import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]  # ~/AeroSkills (scripts/ -> repo root)
OUT = REPO / "packages" / "jetbrains-plugin" / "src" / "main" / "resources" / "catalog" / "catalog.json"

def main() -> int:
    skills_root = REPO / "skills"
    rows = []
    for skill_md in sorted(skills_root.rglob("SKILL.md")):
        rel = skill_md.relative_to(skills_root)
        parts = rel.parts  # family/pack/skill/SKILL.md
        if len(parts) != 4:
            continue  # leaf only: family/pack/skill
        family, pack, skill = parts[0], parts[1], parts[2]
        try:
            text = skill_md.read_text(encoding="utf-8")
            fm = yaml.safe_load(text.split("---", 2)[1]) or {}
        except Exception:
            continue
        name = fm.get("name") or skill
        desc = (fm.get("description") or "")[:220]
        rows.append({"name": f"{pack}/{name}", "family": family, "description": desc})

    out = {"count": len(rows), "source": "https://github.com/ashfordeOU/aero-agent-skills", "skills": rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out), encoding="utf-8")
    print(f"wrote {OUT} ({len(rows)} skills)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
