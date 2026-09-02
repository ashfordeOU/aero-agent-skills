#!/usr/bin/env python3
import pathlib, sys
for fam in ["flight-test-operations", "manufacturing-quality", "propulsion", "systems-engineering-safety"]:
    p = pathlib.Path("<AEROSKILLS-ROOT>/skills") / fam / "SKILL.md"
    txt = p.read_text(encoding="utf-8")
    # extract frontmatter description value (single-line double-quoted)
    import re
    m = re.search(r'(?m)^description:\s*"([^"]*)"', txt)
    if m:
        print(f"{fam}: desc_len={len(m.group(1))}")
    else:
        # multiline description fallback
        print(f"{fam}: desc not single-line quoted")
