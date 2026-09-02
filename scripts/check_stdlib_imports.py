#!/usr/bin/env python3
"""Gate 3 helper: enforce stdlib-only imports in contract test files.

The gate contract requires the per-skill behavior tests to run with the
stdlib unittest runner only (no external deps, no network). This checker
parses import statements and rejects any top-level module that is neither
in the stdlib allowlist nor a sibling module next to the test file.
"""

import pathlib
import re
import sys

STDLIB_ALLOW = set(
    """
    abc argparse asyncio base64 bisect builtins collections concurrent
    contextlib copy csv dataclasses datetime decimal enum errno faulthandler
    functools gc glob hashlib heapq inspect io itertools json logging math
    mmap multiprocessing os pathlib pickle pprint queue random re select
    shlex shutil signal socket sqlite3 stat statistics string struct subprocess
    sys tempfile textwrap threading time timeit traceback types typing unittest
    uuid weakref xml zoneinfo
    """.split()
)

IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)")


def main():
    p = pathlib.Path(sys.argv[1])
    src = p.read_text(encoding="utf-8")
    bad = []
    for m in IMPORT_RE.finditer(src, re.MULTILINE):
        mod = m.group(1)
        if mod in STDLIB_ALLOW:
            continue
        if (p.parent / (mod + ".py")).exists():
            continue
        bad.append(mod)
    if bad:
        print(
            "FAIL gate3-imports: %s imports non-stdlib module(s): %s"
            % (p, ", ".join(sorted(set(bad)))),
            file=sys.stderr,
        )
        sys.exit(1)
    print("PASS gate3-imports: %s stdlib-only" % p)
    sys.exit(0)


if __name__ == "__main__":
    main()
