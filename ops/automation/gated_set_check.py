#!/usr/bin/env python3
"""gated_set_check.py — enumeration-completeness guard logic.

Reads the canonical standards-map.yaml (repo root) live, derives the gated
set (gated: true entries) and the map total, then scans the three
enumeration docs (docs/FAQ.md, docs/glossary.md,
marketing/positioning-1pager.md) for numeric gated-set / map-coverage COUNT
claims. Any claimed count that contradicts canonical -> exit 1 with the
evidence; all clean -> exit 0.

See gated-set-check.sh for scope rationale. Nothing here hardcodes the
standard names or counts — they are read from standards-map.yaml.
"""

import os
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover - CI installs pyyaml; local fallback
    yaml = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # ops/automation -> repo root
MAP_PATH = os.path.join(REPO_ROOT, "standards-map.yaml")

TARGET_DOCS = [
    "docs/FAQ.md",
    "docs/glossary.md",
    "marketing/positioning-1pager.md",
]

# Word-form numbers that could plausibly appear in count claims.
WORD_TO_INT = {
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16,
}
NUM_ALT = r"(?:\d+|" + "|".join(WORD_TO_INT) + r")"


def to_int(token: str) -> int:
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    return WORD_TO_INT[token]


def load_map() -> tuple:
    """Return (total_standards, gated_short_names). Read live, never
    hardcoded. Short name = the name field up to its first ':'
    (e.g. 'DO-178C: Software Considerations...' -> 'DO-178C')."""
    if yaml is None:
        print(f"FAIL gated-set-check: PyYAML unavailable (needed for {MAP_PATH})")
        sys.exit(2)
    with open(MAP_PATH, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    standards = data.get("standards", [])
    total = len(standards)
    gated = []
    for entry in standards:
        if entry.get("gated") is True:
            name = entry.get("name", "")
            short = name.split(":", 1)[0].strip()
            if short:
                gated.append(short)
    return total, gated


def scan_claims(path: str, gated_count: int, map_total: int) -> list:
    """Return list of FAIL lines for one doc file."""
    fails = []
    if not os.path.isfile(path):
        return fails
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            # R1: '<N> gated standards' / 'gated set of <N> standards'
            for m in re.finditer(
                rf"\b({NUM_ALT})\s+gated\s+standards?\b|"
                rf"gated\s+set\s+of\s+({NUM_ALT})\s+standards?\b",
                line, re.IGNORECASE,
            ):
                token = m.group(1) or m.group(2)
                claimed = to_int(token)
                if claimed != gated_count:
                    fails.append(
                        f"  {path}:{lineno}: gated-set count claim '{token}' "
                        f"!= canonical {gated_count} gated standards"
                    )
            # R2: '<covers|maps|spans> <N> standards' (map-coverage claim)
            for m in re.finditer(
                rf"\b(?:covers?|maps?|spans?)\s+({NUM_ALT})\s+standards?\b",
                line, re.IGNORECASE,
            ):
                claimed = to_int(m.group(1))
                if claimed != map_total:
                    fails.append(
                        f"  {path}:{lineno}: map-coverage count claim "
                        f"'{m.group(1)}' != canonical {map_total} map standards"
                    )
            # R3: 'all <N> of the gated standards'
            for m in re.finditer(
                rf"\ball\s+({NUM_ALT})\s+of\s+the\s+gated\s+standards?\b",
                line, re.IGNORECASE,
            ):
                claimed = to_int(m.group(1))
                if claimed != gated_count:
                    fails.append(
                        f"  {path}:{lineno}: 'all {m.group(1)} of the gated "
                        f"standards' != canonical {gated_count} gated standards"
                    )
    return fails


def main() -> int:
    docs_root = sys.argv[1] if len(sys.argv) > 1 else REPO_ROOT
    map_total, gated = load_map()
    gated_count = len(gated)
    print(
        f"gated-set-check: map {MAP_PATH} -> {map_total} standards, "
        f"{gated_count} gated ({', '.join(sorted(gated))})"
    )

    all_fails = []
    for rel in TARGET_DOCS:
        all_fails.extend(scan_claims(os.path.join(docs_root, rel),
                                     gated_count, map_total))

    if all_fails:
        print("FAIL gated-set-check: enumeration count claims contradict standards-map.yaml:")
        for f in all_fails:
            print(f)
        return 1
    print(
        f"PASS gated-set-check: no stale gated-set/map-coverage count claims "
        f"in {', '.join(TARGET_DOCS)} (canonical: {gated_count} gated / {map_total} map)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
