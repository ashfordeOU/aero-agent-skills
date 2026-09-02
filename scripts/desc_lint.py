#!/usr/bin/env python3
"""Gate 2: description lint (what+when+trigger) for one SKILL.md.

Contract: docs/harness-contract.md gate 2 (brief 03 section 4: descriptions
are the router - this single field dominates selection quality; write for the
orchestrator, not the human). Checks:
- action/what clause (an action verb such as determine/draft/scope/run)
- when-to-use clause (explicit 'Use when ...')
- 'Trigger' keyword followed by >=2 trigger keywords for the discipline
- 50-150 words

Exit 0 = pass; 1 = violation (reasons on stdout).
"""

import pathlib
import re
import sys

import yaml

ACTION_VERBS = re.compile(
    r"\b(produce|determine|draft|plan|size|run|analyze|build|create|configure|"
    r"manage|calculate|evaluate|generate|write|develop|design|compute|validate|"
    r"verify|estimate|implement|deploy|test|troubleshoot|audit|scope|map|convert|"
    r"extract|monitor|automate|review|assess|simulate|model|synthesize|document|"
    r"maintain|calibrate|optimize|derive|allocate|define|execute|perform|support|"
    r"guide|structure|prepare|coordinate|classify|identify)\b",
    re.IGNORECASE,
)
MIN_WORDS = 50
MAX_WORDS = 150
MIN_TRIGGER_KEYWORDS = 2


def main():
    p = pathlib.Path(sys.argv[1])
    text = p.read_text(encoding="utf-8")
    errs = []
    parts = text.split("---", 2)
    fm = None
    if len(parts) < 3:
        errs.append("frontmatter not closed")
    else:
        try:
            fm = yaml.safe_load(parts[1])
        except Exception as e:  # noqa: BLE001
            errs.append("frontmatter yaml error: %s" % e)
    desc = fm.get("description") if isinstance(fm, dict) else None
    if not desc:
        errs.append("no description in frontmatter")
        desc = ""
    n = len(desc.split())
    if not (MIN_WORDS <= n <= MAX_WORDS):
        errs.append("description is %d words, must be %d-%d" % (n, MIN_WORDS, MAX_WORDS))
    if not ACTION_VERBS.search(desc):
        errs.append("no action/what clause (action verb like determine/draft/scope/run)")
    if not re.search(r"use when", desc, re.IGNORECASE):
        errs.append("no when-to-use clause (explicit 'Use when ...')")
    m = re.search(r"trigger", desc, re.IGNORECASE)
    if not m:
        errs.append("no 'Trigger' keyword")
    else:
        after = desc[m.end():]
        keywords = [k.strip(" :,;.") for k in re.split(r"[,;:]", after)]
        keywords = [k for k in keywords if k]
        if len(keywords) < MIN_TRIGGER_KEYWORDS:
            errs.append(
                "fewer than %d trigger keywords after 'Trigger'" % MIN_TRIGGER_KEYWORDS
            )
    if errs:
        for e in errs:
            print("FAIL gate2-desc-lint: %s: %s" % (p, e))
        sys.exit(1)
    print(
        "PASS gate2-desc-lint: %s %d words, action+use-when+trigger ok" % (p, n)
    )


if __name__ == "__main__":
    main()
