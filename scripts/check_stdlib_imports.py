#!/usr/bin/env python3
"""Gate 3 helper: enforce stdlib-only imports in contract test files.

The gate contract requires the per-skill behavior tests to run with the
stdlib unittest runner only (no external deps, no network). This checker
PARSES the file and rejects any top-level module that is neither in the
stdlib allowlist nor a module belonging to this repository.

Why a parse and not a regex
---------------------------
This checker used to scan with a line-anchored regex. Two faults followed
from that and both are fixed here:

  * the pattern was compiled without re.MULTILINE and then handed the flag
    as finditer's second positional argument, which is `pos`. `^` therefore
    could never match past the start of the file, the scan returned zero
    hits on every input, and the checker printed PASS unconditionally;
  * even repaired, a regex sees text, not code. It cannot tell an import
    from the same words inside a string or a comment, and it reports no
    position that survives a reformat.

ast.walk descends the whole tree, so imports inside functions, methods,
class bodies, `if`/`else` branches and `try`/`except ImportError` fallbacks
are all seen - exactly the places an out-of-contract dependency hides.

Scope of the allowlist
----------------------
STDLIB_ALLOW is deliberately NARROWER than the standard library: modules
such as urllib, http, ssl, ftplib and ctypes are stdlib yet absent, because
the contract is offline-and-dependency-free, not merely dependency-free.
Adding a name here widens what leaf code may reach for, so add only names
that are stdlib AND compatible with an offline run. scripts/gate_no_inference.py
imports STDLIB_ALLOW from this module and reports whether `socket` is still
in it; keep the name and the shape.
"""

import ast
import pathlib
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

# Stdlib modules the corpus genuinely imports that the original allowlist
# omitted. The dead scan above meant none of them was ever consulted, so the
# omission never surfaced. Every name here is in sys.stdlib_module_names and
# none of them opens a socket or a subprocess of its own.
STDLIB_ALLOW.update(
    """
    __future__ ast calendar cmath doctest fractions hmac importlib
    unicodedata zlib
    """.split()
)

# Directory names never searched when resolving a first-party module.
_SKIP_DIRS = frozenset({".git", "__pycache__", "node_modules", ".venv", "venv"})

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

_repo_modules = None  # built lazily; see _is_repo_module


def _iter_imports(tree):
    """Yield (top_level_module, lineno) for every import in the tree.

    ast.walk reaches nested scopes, so conditional and function-local
    imports are covered as well as module-level ones. Package-relative
    imports (`from . import x`) are skipped: by construction they name a
    module inside this repository, never an installed dependency.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0], node.lineno
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            if node.module:
                yield node.module.split(".")[0], node.lineno
        elif isinstance(node, ast.Call):
            # The two dynamic forms that would otherwise walk straight past a
            # static check. Only literal arguments can be resolved; a computed
            # module name is reported as unresolvable rather than waved past.
            name = None
            if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                name = "__import__"
            elif (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "import_module"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "importlib"
            ):
                name = "importlib.import_module"
            if name is None or not node.args:
                continue
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if arg.value:
                    yield arg.value.split(".")[0], node.lineno
            else:
                yield "<computed argument to %s>" % name, node.lineno


def _build_repo_modules():
    """Names importable from inside this repository (modules and packages)."""
    found = set()
    stack = [_REPO_ROOT]
    while stack:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for e in entries:
            if e.is_dir():
                if e.name in _SKIP_DIRS:
                    continue
                if (e / "__init__.py").exists():
                    found.add(e.name)
                stack.append(e)
            elif e.suffix == ".py":
                found.add(e.stem)
    return found


def _is_repo_module(mod, path):
    """True when `mod` names code that ships in this repository.

    The cheap test first: a module or package sitting next to the file under
    test, which is how every leaf reaches its own logic module. Only if that
    misses is the repository-wide index built, and only for a name that has
    already failed the allowlist - so the walk costs nothing on the ordinary
    run where every import is allowlisted or a sibling.
    """
    if (path.parent / (mod + ".py")).exists():
        return True
    if (path.parent / mod / "__init__.py").exists():
        return True
    global _repo_modules
    if _repo_modules is None:
        _repo_modules = _build_repo_modules()
    return mod in _repo_modules


def main():
    if len(sys.argv) != 2:
        print(
            "FAIL gate3-imports: usage: check_stdlib_imports.py <file.py>",
            file=sys.stderr,
        )
        return 2
    p = pathlib.Path(sys.argv[1])
    try:
        src = p.read_text(encoding="utf-8")
    except OSError as exc:
        print(
            "FAIL gate3-imports: %s cannot be read: %s" % (p, exc),
            file=sys.stderr,
        )
        return 2
    try:
        tree = ast.parse(src, filename=str(p))
    except SyntaxError as exc:
        # An unparseable contract test cannot be shown to be stdlib-only, and
        # the check must not degrade to a pass the way the dead scan did.
        print(
            "FAIL gate3-imports: %s does not parse (line %s): %s"
            % (p, exc.lineno, exc.msg),
            file=sys.stderr,
        )
        return 1

    bad = []
    seen = set()
    for mod, lineno in _iter_imports(tree):
        if mod in STDLIB_ALLOW:
            continue
        if not mod.startswith("<") and _is_repo_module(mod, p):
            continue
        if (mod, lineno) in seen:
            continue
        seen.add((mod, lineno))
        bad.append((mod, lineno))

    if bad:
        bad.sort(key=lambda t: (t[1], t[0]))
        detail = ", ".join("%s (line %d)" % (m, n) for m, n in bad)
        print(
            "FAIL gate3-imports: %s imports non-stdlib module(s): %s" % (p, detail),
            file=sys.stderr,
        )
        return 1
    print("PASS gate3-imports: %s stdlib-only" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
