#!/usr/bin/env python3
"""Gate 4 helper: flag objective-table blocks typical of proprietary standards.

DO-178C/DO-254 style objective tables ('Table A-1', 'A-1.1' identifiers) are
exactly the 'objective tables, appendix text, multi-line verbatim blocks' that
research/briefs/06-legal-export-control.md section 5.2 forbids reproducing.
A run of >=3 consecutive table-pattern lines flags a copied block.

Usage: verbatim_table_scan.py <dir>...
Exit 0 = no blocks; 1 = blocks found (details on stdout).
"""

import pathlib
import re
import sys

TABLE_LINE = re.compile(r"^\s*(?:Table\s+[A-E]-?\d+|([A-E])-\d+(\.\d+)*\s)")
RUN_MIN = 3


def scan(root):
    bad = 0
    for p in sorted(pathlib.Path(root).rglob("*")):
        if not p.is_file():
            continue
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        run = 0
        for i, line in enumerate(lines, 1):
            if TABLE_LINE.match(line):
                run += 1
            else:
                run = 0
            if run == RUN_MIN:
                start = i - RUN_MIN + 1
                print(
                    "FAIL gate4-no-verbatim: %s:%d objective-table block (lines %d-%d)"
                    % (p, start, start, i)
                )
                bad = 1
                run = 0  # report each block once
    return bad


def main():
    bad = 0
    for root in sys.argv[1:]:
        if scan(root):
            bad = 1
    if bad:
        sys.exit(1)
    print("PASS gate4-table-scan: no objective-table blocks")


if __name__ == "__main__":
    main()
