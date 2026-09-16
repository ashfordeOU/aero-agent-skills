#!/usr/bin/env python3
"""desc-frontload.py — move the routing trigger to the front of leaf
descriptions.

Audit finding (Provencher GPT-6 Astra drop): 71/506 leaf descriptions
carry their "Use when ..." trigger + "Trigger:" keyword list AFTER the
action clause (some past char 300). The deterministic router reads the
full text (immune), but truncating consumers (JetBrains catalog [:220],
LLM-in-context skill hosts) lose the routing signal when the trigger
sits past the truncation point.

Fix: reorder each description to  [Use when ...] [Trigger: ...] [action
clause with method detail]. Pure text reordering — content, word count,
and vocabulary are unchanged, so the 50-150 word contract and the
Hit@1 router scores are preserved (verified after apply).

Structure of a leaf description (observed, uniform):
  <action/what clause>: <method detail...>. [Use when the task is
  <triggers>...] [Produces ...] [Trigger: <keyword list>]

Target:
  Use when the task is <triggers>. <action/what clause>: <method
  detail...>. <Produces ...>. Trigger: <keyword list>.

Usage:
  python3 scripts/desc-frontload.py --dry-run   # show plan only
  python3 scripts/desc-frontload.py             # apply
"""
from __future__ import annotations

import glob
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONT_MAX = 120


def parse_desc(text: str) -> str | None:
    m = re.search(r'^description:\s*"?(.+?)"?\s*$', text, re.M)
    return m.group(1).strip().rstrip('"') if m else None


def front_load(desc: str) -> str:
    """Move the 'Use when ...' sentence to the front.

    Target sentence order:
      [Use when ...] [<action/what clause>: <method detail>] [Produces]
      [Trigger: ...]

    Only the "Use when" sentence moves; everything else keeps its
    relative order (so the Trigger keyword index stays at the end).
    """
    low = desc.lower()
    idx = low.find("use when")
    if idx < 0 or idx <= FRONT_MAX:
        return desc

    # End of the "Use when ..." sentence: find its terminating period.
    # The sentence runs from idx to the next ". " that is followed by
    # either 'Produces', 'Trigger', end-of-string, or a capital-letter
    # new sentence. Simpler: the Use-when sentence is bounded by the
    # next sentence marker after idx that isn't inside an abbreviation.
    end = len(desc)
    for m in re.finditer(r"\.\s+", desc[idx + 8:]):
        cand = idx + 8 + m.start() + 1
        nxt = desc[cand:].lstrip()
        if nxt.startswith(("Produces", "Trigger")) or nxt[:1].isupper():
            end = cand
            break
    use_sent = desc[idx:end].strip()
    rest = (desc[:idx].strip() + " " + desc[end:].strip()).strip()
    new = use_sent + " " + rest if rest else use_sent
    new = re.sub(r"\s+", " ", new).strip()
    return new


def load_only(argv) -> list[str]:
    """Paths this run is allowed to touch. REQUIRED - see module docstring.

    Returns repo-relative paths that exist and sit at depth 4
    (skills/<family>/<standard>/<slug>/SKILL.md). Anything else is refused
    by name rather than skipped quietly, because a caller who listed a
    family router meant something and should be told it did not happen.
    """
    if "--only" not in argv:
        sys.exit("REFUSING: --only <listfile> is required.\n"
                 "  This script rewrites shipped leaf descriptions in place. Run with\n"
                 "  an explicit list of repo-relative SKILL.md paths; there is no\n"
                 "  repo-wide mode (wave 12 rewrote 155 shipped leaves that way).")
    listfile = argv[argv.index("--only") + 1]
    wanted = [l.strip() for l in Path(listfile).read_text().splitlines() if l.strip()]
    bad = []
    ok = []
    for rel in wanted:
        full = ROOT / rel
        if not full.is_file():
            bad.append(f"{rel}: not a file")
        elif len(Path(rel).parts) != 5 or Path(rel).parts[0] != "skills":
            # skills / family / standard / slug / SKILL.md == 5 parts
            bad.append(f"{rel}: not a depth-4 leaf")
        else:
            ok.append(rel)
    if bad:
        print(f"REFUSING: {len(bad)} listed path(s) are not depth-4 leaves:")
        for b in bad[:10]:
            print("  " + b)
        sys.exit(1)
    return ok


def main() -> int:
    dry = "--dry-run" in sys.argv
    only = load_only(sys.argv)
    print(f"scope: {len(only)} leaf/leaves from --only list")
    changed = []
    for rel in only:
        f = str(ROOT / rel)
        path = Path(f)
        text = path.read_text()
        desc = parse_desc(text)
        if not desc:
            continue
        low = desc.lower()
        idx = low.find("use when")
        if idx < 0 or idx <= FRONT_MAX:
            continue
        new_desc = front_load(desc)
        if new_desc == desc:
            continue
        changed.append((f.replace(str(ROOT) + "/", ""), idx, len(desc), new_desc))

    print(f"front-load candidates: {len(changed)}")
    for rel, idx, ln, newd in changed:
        print(f"  {rel} (trigger@{idx}, {ln} chars)")
        if dry:
            print(f"    NEW: {newd[:220]}...")

    if dry or not changed:
        return 0

    # Apply (handle quoted and unquoted frontmatter values)
    applied = 0
    for rel, idx, ln, newd in changed:
        p = ROOT / rel
        text = p.read_text()
        # Find the description line; replace value preserving quote style.
        m = re.search(r'^(description:\s*)(.*)$', text, re.M)
        if not m:
            continue
        prefix = m.group(1)
        oldval = m.group(2).strip()
        quoted = oldval.startswith('"') and oldval.endswith('"')
        safe = newd.replace("\\", "\\\\").replace('"', '\\"')
        # text[:m.start(2)] already ends with the `description: ` prefix
        # (group 1); the replacement must be ONLY the quoted value, or the
        # prefix is duplicated -> `description: description: "..."` which
        # corrupts frontmatter (2026-09-05 incident: 71 leaves hit, reverted).
        replacement = f'"{safe}"'
        text2 = text[:m.start(2)] + replacement + text[m.end(2):]
        p.write_text(text2)
        applied += 1
    print(f"applied {applied} front-load rewrites")
    return 0


if __name__ == "__main__":
    sys.exit(main())
