#!/usr/bin/env python3
"""Build a pruned COPY of the repository that every gate passes on.

A negative control needs two runs: a GREEN baseline and a RED mutant. The
mutation is the only difference between them, so the baseline has to be green
for the red to mean anything. This module builds that baseline.

The fixture is a real copy of real files (gate scripts, standards map, leaf
skills, corpus fragments, claims ledger, number register), pruned to three
leaf skills so a control costs seconds instead of the ~90s a single sweep
costs over the full corpus. It is written into a temporary directory; the
working tree is never touched.

Four deliberate departures from a byte-for-byte copy, each one recorded here
because a departure that is not written down becomes a lie later:

  1. Only three leaves (plus their pack routers) are copied. Removing
     competitors can only make the router's job easier, so a corpus task that
     was top-1 in the full tree is still top-1 here.
  2. The Hit@1 corpus is assembled from the three leaves' own corpus
     fragments instead of copying the 1,754-task corpus, whose tasks point at
     leaves this fixture does not carry.
  3. The three release version files are set to the band implied by
     docs/metrics.json. The working tree is currently NOT aligned (see the
     README), and an already-red baseline proves nothing.
  4. One extra document is added under docs/ carrying a truthful, resolvable
     figure taken from the number register, so the brief-audit gate has
     something to grade. Without it that gate passes vacuously.
  5. Each pack router's sub-skill table is pruned to the leaves the fixture
     carries. Gate 1 resolves cross-references as of 2026-09-19, so a router
     copied whole indexes leaves that departure 1 removed and reports 342
     unresolved references before any mutation is applied. The rows are the
     fixture's own doing; a leaf reference anywhere but a table row aborts
     the build rather than being edited away.

WHAT A GATE NEEDS IS DECLARED, AND THE DECLARATION IS AUDITED
-------------------------------------------------------------
Until 2026-09-19 the copy set was a flat hand-written list. When gate 4 was
rewritten to call tools/verbatim_gate.py, that list was not updated: the
fixture carried the gate script but none of its helpers, so the no-verbatim
BASELINE exited 2 with "can't open file ... tools/verbatim_gate.py" and the
mutant exited 2 for exactly the same reason. No red was attributable to the
mutation, and the suite reported the gate as merely "DID NOT FAIL".

A copy list that silently omits a dependency is the same defect class as a
gate that prints PASS over a set it never read, so two things changed:

  * GATE_DEPENDENCIES declares, per gate, what that gate needs beyond the
    blanket copies. The declaration is the contract and is copied verbatim.
  * audit_gate_dependencies() then re-derives each gate's dependency closure
    from the Makefile recipe and the gate's own source text, and refuses to
    build a fixture that is missing anything it finds. An omission now aborts
    the build with the gate and the path named, instead of producing a
    quietly-red baseline.

The audit is a completeness check on the declaration, not a replacement for
it: it can only see statically-visible references, so a gate that resolves a
path purely at run time (scripts/verify-independence.py walks the tree for
claims ledgers) is invisible to it and must be declared by hand.

stdlib only, no network.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# What the fixture carries
# ---------------------------------------------------------------------------

# (leaf path under skills/, its corpus fragment under eval/)
KEPT_LEAVES = [
    ("flight-mechanics/performance/breguet-range", "hit1-wave1-breguet-range.yaml"),
    ("aerodynamics/cfd/cfd-turbulence-modeling", "hit1-wave1-cfd-turbulence-modeling.yaml"),
    ("gnc-autonomy/control/root-locus-design", "hit1-wave2-root-locus-design.yaml"),
    # An ECSS leaf, carried for gate 4 specifically. The other three map to
    # SAE / EASA / FAA / NASA, families the gate can only check with
    # publisher markers, so without this one the source-text half of the
    # gate -- the half the 2026-09-19 rewrite was for, covering the ECSS
    # leaves that are most of the corpus -- never executed in the fixture at
    # all and the coverage line read "leaves fully source-checked=0 of 3".
    ("space-systems/ecss/e2007-bonding-resistance-measurement",
     "hit1-e2007-bonding-resistance-measurement.yaml"),
]

# The leaf the per-leaf mutations are applied to.
PRIMARY_LEAF = KEPT_LEAVES[0][0]

# Single files copied verbatim.
COPY_FILES = [
    "Makefile",
    "standards-map.yaml",
    "README.md",
    "STANDARDS.md",
    "NOTICE",
    ".claude-plugin/plugin.json",
    "packages/aero-agent-skills/package.json",
    "packages/jetbrains-plugin/build.gradle.kts",
    "ops/ecss-program/claims-ledger.md",
    "ops/automation/state/stars-latest.json",
]

# Files the fixture may build for itself when the tree does not carry them.
#
# `ops/ecss-program/claims-ledger.md` is internal programme state and the
# public export drops the whole directory. The fixture needs A claims
# ledger to prove gate 6 can go red; it does not need THAT one. Synthesizing
# keeps the control meaningful on an export without pulling internal notes
# into the public tree.
#
# The rows must PASS gate 6 as written (deterministic verifiers, distinct
# from their generators) so the baseline is green and only the mutation is
# red.
_SYNTHETIC_CLAIMS_LEDGER = """\
# Claims ledger (verifier independence) — synthesized fixture copy

Built by tools/negative_controls/fixture.py because the tree being graded
does not carry ops/ecss-program/claims-ledger.md. The public export excludes
that directory; gate 6 needs a ledger of this SHAPE, not this content.

| id | scope | date | leaves | evidence | generator | verification | verifier | verdict |
|---|---|---|---|---|---|---|---|---|
| fx-1 | fixture tranche one | 2026-01-01 | 1 | skills/ | Claude Code (CCD session) | deterministic | leaf unit tests + spec_lint + make validate (deterministic) | PASS |
| fx-2 | fixture tranche two | 2026-01-02 | 1 | skills/ | Claude Code (CCD session) | deterministic | aero-lane-harvest.py: desc_lint + content-policy + make attest (deterministic) | PASS |
| fx-3 | fixture tranche three | 2026-01-03 | 1 | skills/ | orchestrator (LLM) | deterministic | repo gate battery, no model on the path (deterministic) | PASS |
"""

def _synth_claims_ledger(repo):
    return _SYNTHETIC_CLAIMS_LEDGER


def _synth_stars_snapshot(repo):
    """A stars snapshot that AGREES with the register it is built beside.

    `number-snapshot.sh --offline` re-checks each recorded `live` value
    against the register's `stars`. A stub with invented figures would make
    the clean fixture red, and then every control is VOID for a reason that
    has nothing to do with the gate under test. Deriving it from the
    register makes the baseline green by construction.

    numbers.yaml is present in the public export -- only
    ops/automation/state/ is dropped -- so this works on both trees.
    Parsed with a narrow regex rather than PyYAML: the fixture is stdlib
    only, and the `tracked:` block is a flat list of scalars.
    """
    import json
    import re as _re

    reg = repo / "ops/automation/numbers.yaml"
    entries = []
    if reg.is_file():
        text = reg.read_text(encoding="utf-8", errors="replace")
        block = _re.search(r"^tracked:\s*$(.*?)^\w", text, _re.M | _re.S)
        if block:
            for chunk in _re.split(r"^  - ", block.group(1), flags=_re.M)[1:]:
                def field(name, default=None):
                    m = _re.search(r"^\s*%s:\s*(.+?)\s*$" % name, chunk, _re.M)
                    return m.group(1).strip().strip('"') if m else default
                ident, repo_name = field("id"), field("repo")
                stars = field("stars")
                if not (ident and repo_name and stars and stars.isdigit()):
                    continue
                tol = field("tolerance_pct", "1")
                entries.append({
                    "id": ident,
                    "repo": repo_name,
                    "expected": int(stars),
                    "live": int(stars),          # agrees by construction
                    "within_tolerance": True,
                    "tolerance_pct": int(tol) if tol.isdigit() else 1,
                    "tolerance_abs": None,
                })
    return json.dumps({
        "schema": "aeroskills-stars-snapshot/v1",
        # Fixed, not now(): the fixture must be byte-identical run to run or
        # the determinism work upstream is undone here.
        "timestamp_utc": "2026-01-01T00:00:00+00:00",
        "as_of": "2026-01-01",
        "register": "numbers.yaml",
        "mode": "synthesized-fixture",
        "tracked": entries,
    }, indent=2, sort_keys=True) + "\n"


# Files the fixture builds for itself when the tree legitimately lacks them.
# INVARIANT: every fixture input that lives under a path the public export
# excludes must appear here, or the suite cannot run on an export -- and a
# suite that cannot run must not report success, so the publish blocks.
# The export currently drops: ops/ecss-program, ops/automation/state,
# ops/automation/test, docs/MAINTENANCE_AND_HANDOVER.md, context.
SYNTHESIZED_IF_ABSENT = {
    "ops/ecss-program/claims-ledger.md": _synth_claims_ledger,
    "ops/automation/state/stars-latest.json": _synth_stars_snapshot,
}

# Whole directories copied verbatim.
COPY_DIRS = ["scripts", "docs", "research"]

# ops/automation minus its 187-file snapshot archive (one snapshot is enough).
OPS_AUTOMATION = "ops/automation"

# Gate entry points and their helpers. The runner re-hashes these against the
# working tree so a control can never grade a paraphrase of a gate.
GATE_SOURCES = [
    "Makefile",
    "scripts/gate-spec-lint.sh",
    "scripts/spec_lint.py",
    "scripts/gate-desc-lint.sh",
    "scripts/desc_lint.py",
    "scripts/gate-pytest-contract.sh",
    "scripts/check_stdlib_imports.py",
    "scripts/gate-no-verbatim.sh",
    "scripts/verbatim_table_scan.py",
    "tools/verbatim_gate.py",
    "tools/verbatim_shingle.py",
    "scripts/gate_no_inference.py",
    "tools/check_slug_uniqueness.py",
    "tools/router_coverage.py",
    "scripts/gate-hit1-corpus.sh",
    "scripts/router_eval.py",
    "scripts/gate-verify-independence.sh",
    "scripts/verify-independence.py",
    "scripts/release-manager.py",
    "scripts/portability_check.py",
    "scripts/corpus_naming_check.py",
    "ops/automation/number-snapshot.sh",
    "ops/automation/number_snapshot.py",
    "ops/automation/brief-audit.sh",
    "ops/automation/number_audit.py",
    "ops/automation/content-policy-sweep.sh",
]

# What a gate needs BEYOND the blanket copies above, declared per gate.
#
# The declaration lives next to the gate name so that adding a gate, or
# rewriting one to call a new helper, has an obvious place to record the
# requirement. Entries may be files or directories; both are copied verbatim.
# audit_gate_dependencies() below re-derives the same closure from the
# Makefile and the gate sources and refuses to build if anything a gate
# statically reaches is absent from the fixture.
GATE_DEPENDENCIES = {
    # Gate 4 was fifteen greps in a shell script until 2026-09-19. It is now
    # a Python runner with a shingle index, and needs all three of these:
    # the runner the gate script execs, the shingle module that runner
    # imports, and the index directory it reads. (tools/build_verbatim_index.py
    # is NOT here: the gate only names it in prose, and a declaration that
    # lists what a gate mentions is no more honest than one that omits what
    # a gate runs.)
    "no-verbatim": [
        "tools/verbatim_gate.py",
        "tools/verbatim_shingle.py",
        "tools/verbatim-index",
    ],
    # Gates 11 and 12 live under tools/, which is not blanket-copied the way
    # scripts/ is, so each names the module the Makefile execs.
    "slug-uniqueness": [
        "tools/check_slug_uniqueness.py",
    ],
    "figure-audit": [
        "tools/figure_audit.py",
    ],
    "router-coverage-structure": [
        "tools/router_coverage.py",
        # router_coverage imports the reference router and the stdlib YAML
        # subset reader from the export package; without them the gate cannot
        # start, and a baseline that dies for a missing import would void
        # every control in the suite.
        "tools/export",
    ],
}

# Paths a gate reaches that the fixture deliberately does NOT carry. Each
# entry needs a reason, because an unexplained exemption is how the
# no-verbatim omission survived: it simply was not in anybody's list.
PRUNED_BY_DESIGN = {
    # ops/automation/state/ is copied with ONE snapshot (stars-latest.json)
    # instead of all 187; the gate only ever reads the latest.
}

CLAIM_DOC = "docs/negative-control-register-claim.md"

IGNORED_NAMES = {"__pycache__", ".git", ".DS_Store", ".pytest_cache"}


class FixtureError(RuntimeError):
    """The fixture could not be built as specified (never guessed around)."""


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _ignore(_dirname, names):
    return {n for n in names if n in IGNORED_NAMES or n.endswith(".pyc")}


def _copy_file(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FixtureError("expected file missing from the tree: %s" % src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _copy_dir(src: Path, dst: Path) -> None:
    if not src.is_dir():
        raise FixtureError("expected directory missing from the tree: %s" % src)
    shutil.copytree(src, dst, ignore=_ignore, symlinks=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def leaf_logic_module(fixture: Path, leaf: str = PRIMARY_LEAF) -> Path:
    """The leaf's stdlib logic module (the one its contract test imports)."""
    scripts = fixture / "skills" / leaf / "scripts"
    mods = sorted(p for p in scripts.glob("*.py") if not p.name.startswith("test_"))
    if not mods:
        raise FixtureError("leaf %s ships no logic module" % leaf)
    return mods[0]


def leaf_contract_test(fixture: Path, leaf: str = PRIMARY_LEAF) -> Path:
    scripts = fixture / "skills" / leaf / "scripts"
    tests = sorted(scripts.glob("test_*.py"))
    if not tests:
        raise FixtureError("leaf %s ships no contract test" % leaf)
    return tests[0]


def first_public_function(module: Path) -> str:
    tree = ast.parse(module.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            return node.name
    raise FixtureError("no public top-level function in %s" % module)


def register_stars(fixture: Path, repo_id: str = "ajhcs") -> int:
    """The `stars` figure recorded for one tracked repo in the register.

    Read line-wise rather than with a YAML parser: shipped code here is
    stdlib only.
    """
    text = (fixture / "ops/automation/numbers.yaml").read_text(encoding="utf-8")
    seen = False
    for line in text.splitlines():
        if re.match(r"^\s*-?\s*id:\s*%s\s*$" % re.escape(repo_id), line):
            seen = True
            continue
        if seen:
            m = re.match(r"^\s*stars:\s*(\d+)\s*$", line)
            if m:
                return int(m.group(1))
            if re.match(r"^\s*-\s*id:\s*", line):
                break
    raise FixtureError("no stars figure for '%s' in ops/automation/numbers.yaml" % repo_id)


# ---------------------------------------------------------------------------
# dependency closure: what a gate actually reaches
# ---------------------------------------------------------------------------

_SEG = r"[A-Za-z0-9_.-]+"
# `$repo_root/`, `${REPO}/`, `$auto_dir/` -- blanked so the path that follows
# is seen standalone.
_SHELL_VAR = re.compile(r"\$\{?[A-Za-z_][A-Za-z0-9_]*\}?/")
# A bare or quoted relative path with a known extension, e.g.
# `tools/verbatim_gate.py`, `number_audit.py`, `docs/metrics.json`.
_FILE_REF = re.compile(
    r"(?<![A-Za-z0-9_./-])((?:%s/)*%s\.(?:py|sh|ya?ml|json|md|mjs|kts))" % (_SEG, _SEG)
)
# Any multi-segment relative path, which is how directories are named.
_PATH_REF = re.compile(r"(?<![A-Za-z0-9_./-])((?:%s/)+%s)" % (_SEG, _SEG))
# pathlib composition: `root / "tools" / "verbatim-index"`.
_PATH_JOIN = re.compile(r'((?:/\s*"%s"\s*)+)' % _SEG)
_QUOTED_SEG = re.compile(r'"(%s)"' % _SEG)
# A sibling module import inside a gate helper.
_PY_IMPORT = re.compile(r"(?m)^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)")

# A script in COMMAND position - either behind an interpreter
# (`python3 "$repo_root/tools/verbatim_gate.py"`) or run directly at the
# head of a command, which is how a Makefile recipe invokes a gate script
# (`\t@scripts/gate-no-verbatim.sh`).
_EXEC_PATH = r"(?:\$\{?[A-Za-z_][A-Za-z0-9_]*\}?/)?[A-Za-z0-9_./-]+\.(?:py|sh)"
_EXEC_INTERP = re.compile(
    r"""\b(?:python3?|bash|sh|exec|source)\s+(?:-\S+\s+)*["']?(%s)""" % _EXEC_PATH
)
_EXEC_DIRECT = re.compile(
    r"""(?:^|[;&|(]|\$\()[ \t]*[@+-]*[ \t]*["']?(%s)""" % _EXEC_PATH, re.M
)

_FOLLOWABLE = {".py", ".sh"}


def _strip_py_docstrings(text: str) -> str:
    """Blank out module/class/function docstrings, nothing else.

    A docstring that MENTIONS another script is prose, not a dependency:
    scripts/corpus_naming_check.py explains what leaf-create-gate.sh does,
    and following that mention dragged in example paths the fixture has no
    reason to carry. Embedded code held in a triple-quoted string (the
    runner inside scripts/portability_check.py) is deliberately kept.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text
    kill = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            kill.update(range(first.lineno - 1, (first.end_lineno or first.lineno)))
    lines = text.splitlines(keepends=True)
    return "".join("\n" if i in kill else ln for i, ln in enumerate(lines))


def _strip_prose(text: str, src_rel: str) -> str:
    """Remove what a gate says from what a gate runs.

    Whole-line `#` comments go (the fifteen-grep history at the top of
    gate-no-verbatim.sh names every helper it no longer calls); trailing
    comments are left alone because `#` is ordinary text inside a shell
    glob or string.
    """
    if src_rel.endswith(".py"):
        text = _strip_py_docstrings(text)
    return "\n".join(
        "" if ln.lstrip().startswith("#") else ln for ln in text.splitlines()
    )


def gate_recipe(makefile: Path, target: str) -> str:
    """The recipe lines of one make target (the tab-indented block)."""
    lines = makefile.read_text(encoding="utf-8").splitlines()
    out, seen = [], False
    for line in lines:
        if re.match(r"^%s:" % re.escape(target), line):
            seen = True
            continue
        if not seen:
            continue
        if line.startswith("\t"):
            out.append(line)
        elif line.strip() == "":
            continue
        else:
            break
    return "\n".join(out)


def _resolve(repo: Path, ref: str, parent: Path) -> "str | None":
    """A referenced token as a repo-relative path, or None if it is not one."""
    ref = _SHELL_VAR.sub("", ref.strip().strip("\"'")).rstrip("/")
    if not ref or ref == "." or ref.startswith("/") or ".." in ref.split("/"):
        return None
    # A bare filename in a script almost always means "next to me".
    for cand in (ref, (parent / ref).as_posix()):
        if cand and (repo / cand).exists():
            return cand
    return None


def _executed(repo: Path, text: str, src_rel: str) -> set:
    """Scripts this source RUNS, as opposed to scripts it talks about.

    Following a mention rather than a call is what dragged
    scripts/leaf-create-gate.sh, and then that script's own example paths,
    into the corpus-naming gate's requirements. corpus_naming_check.py names
    leaf-create-gate.sh three times and never executes it once.
    """
    text = _strip_prose(text, src_rel)
    parent = Path(src_rel).parent
    found = set()
    for pattern in (_EXEC_INTERP, _EXEC_DIRECT):
        for m in pattern.finditer(text):
            rel = _resolve(repo, m.group(1), parent)
            if rel and rel != src_rel and (repo / rel).suffix in _FOLLOWABLE:
                found.add(rel)
    if src_rel.endswith(".py"):
        for m in _PY_IMPORT.finditer(text):
            rel = _resolve(repo, (parent / (m.group(1) + ".py")).as_posix(), parent)
            if rel and rel != src_rel:
                found.add(rel)
    return found


def _references(repo: Path, text: str, src_rel: str) -> set:
    """Every repo path this source names: the data it reads plus the
    scripts it runs. Named, not followed - following is _executed()'s job."""
    text = _SHELL_VAR.sub(" ", _strip_prose(text, src_rel))
    raw = set()
    for pattern in (_FILE_REF, _PATH_REF):
        for m in pattern.finditer(text):
            raw.add(m.group(1))
    for m in _PATH_JOIN.finditer(text):
        raw.add("/".join(_QUOTED_SEG.findall(m.group(1))))
    parent = Path(src_rel).parent
    found = set()
    for ref in raw:
        rel = _resolve(repo, ref, parent)
        if rel:
            found.add(rel)
    return found


def gate_dependency_closure(repo: Path, gate: str) -> set:
    """Every repo path `make <gate>` statically reaches.

    Seeded from the target's own recipe, then followed through each script
    the recipe (and, transitively, each of those scripts) actually EXECUTES
    or imports. Paths that are merely named are required to exist but are
    never followed. Only static text is read: nothing here runs a gate.
    """
    recipe = gate_recipe(repo / "Makefile", gate)
    closure = _references(repo, recipe, "Makefile")
    queue = list(_executed(repo, recipe, "Makefile"))
    seen = set(queue)
    closure |= seen
    while queue:
        rel = queue.pop()
        path = repo / rel
        if not (path.is_file() and path.suffix in _FOLLOWABLE):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        closure |= _references(repo, text, rel)
        for nxt in _executed(repo, text, rel):
            if nxt not in seen:
                seen.add(nxt)
                closure.add(nxt)
                queue.append(nxt)
    return closure


def audit_gate_dependencies(repo: Path, fixture: Path, gates) -> dict:
    """Refuse a fixture that is missing anything a gate statically reaches.

    Returns {gate: number of dependencies checked}. Raises FixtureError
    naming the gate and the missing paths, because "the baseline went red
    for an unrelated reason" is precisely the failure this replaces.
    """
    checked, missing = {}, {}
    for gate in gates:
        closure = gate_dependency_closure(repo, gate)
        checked[gate] = len(closure)
        gone = sorted(
            rel for rel in closure
            if rel not in PRUNED_BY_DESIGN and not (fixture / rel).exists()
        )
        if gone:
            missing[gate] = gone
    if missing:
        raise FixtureError(
            "the fixture does not carry everything these gates need, so their "
            "baseline would be red for a reason no mutation planted: "
            + "; ".join(
                "%s needs %s" % (gate, ", ".join(paths))
                for gate, paths in sorted(missing.items())
            )
            + " (declare them in GATE_DEPENDENCIES, or record an exemption "
              "with its reason in PRUNED_BY_DESIGN)"
        )
    return checked


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


def _build_corpus(repo: Path, fixture: Path) -> int:
    """Assemble eval/hit1-corpus.yaml from the kept leaves' own fragments."""
    chunks = [
        "# Hit@1 corpus - negative-control fixture.",
        "# Assembled verbatim from the corpus fragments of the leaves this",
        "# fixture carries; tasks for leaves that were pruned would fail gate 5",
        "# for a reason that has nothing to do with the mutation under test.",
    ]
    body = []
    tasks = 0
    for leaf, fragment in KEPT_LEAVES:
        src = repo / "eval" / fragment
        if not src.exists():
            raise FixtureError("corpus fragment missing: eval/%s" % fragment)
        lines = src.read_text(encoding="utf-8").splitlines()
        try:
            start = next(i for i, ln in enumerate(lines) if ln.strip() == "tasks:")
        except StopIteration:
            raise FixtureError("fragment eval/%s has no 'tasks:' key" % fragment)
        block = [ln for ln in lines[start + 1:] if ln.strip()]
        if not block:
            raise FixtureError("fragment eval/%s carries no tasks" % fragment)
        tasks += sum(1 for ln in block if re.match(r"^\s*-\s*id:", ln))
        body.append("  # %s (from eval/%s)" % (leaf, fragment))
        body.extend(block)
        _copy_file(src, fixture / "eval" / fragment)
    text = "\n".join(chunks) + "\ntasks:\n" + "\n".join(body) + "\n"
    (fixture / "eval").mkdir(parents=True, exist_ok=True)
    (fixture / "eval/hit1-corpus.yaml").write_text(text, encoding="utf-8")
    return tasks


def _align_release_versions(fixture: Path) -> str:
    """Put the three version files on the band docs/metrics.json implies.

    Mirrors scripts/release-manager.py sync_versions() exactly, including its
    own regex for the gradle file, so the baseline is green for the same
    reason `--sync` would make the tree green.
    """
    leaves = json.loads((fixture / "docs/metrics.json").read_text(encoding="utf-8"))["leaves"]
    band = "1.%d.0" % ((leaves - 1) // 100)

    pkg = fixture / "packages/aero-agent-skills/package.json"
    data = json.loads(pkg.read_text(encoding="utf-8"))
    data["version"] = band
    pkg.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    gradle = fixture / "packages/jetbrains-plugin/build.gradle.kts"
    text = gradle.read_text(encoding="utf-8")
    m = re.search(r'version\s*=\s*"([^"]+)"', text)
    if not m:
        raise FixtureError("no version assignment in build.gradle.kts")
    gradle.write_text(text.replace(m.group(0), 'version = "%s"' % band, 1), encoding="utf-8")

    plugin = fixture / ".claude-plugin/plugin.json"
    data = json.loads(plugin.read_text(encoding="utf-8"))
    data["version"] = band
    plugin.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return band


# A cross-reference to a leaf: three lowercase slash-separated segments.
_LEAF_REF = re.compile(r"(?<![A-Za-z0-9_/-])([a-z0-9][a-z0-9.-]*(?:/[a-z0-9][a-z0-9.-]*){2})")


def _prune_pack_routers(repo: Path, fixture: Path, packs) -> int:
    """Drop router table rows that point at leaves this fixture pruned away.

    A pack router indexes every leaf in its pack. Since 2026-09-19 gate 1
    RESOLVES those references, so a router copied whole into a three-leaf
    fixture fails 342 times before any mutation is applied - the fixture's
    own pruning, read back as a gate finding. The rows are the fixture's
    doing, so the fixture removes them.

    Only table rows are dropped. A leaf reference in PROSE aborts the build
    instead: silently rewriting a sentence to keep a baseline green is how a
    fixture starts lying about the tree it stands in.
    """
    known_packs = {d.name for d in (repo / "skills").iterdir() if d.is_dir()}
    dropped = 0
    for pack in packs:
        path = fixture / "skills" / pack / "SKILL.md"
        lines = path.read_text(encoding="utf-8").splitlines()
        kept_lines = []
        for line in lines:
            missing = [
                ref for ref in _LEAF_REF.findall(line)
                if ref.split("/")[0] in known_packs
                and not (fixture / "skills" / ref).exists()
            ]
            if not missing:
                kept_lines.append(line)
                continue
            if not line.lstrip().startswith("|"):
                raise FixtureError(
                    "pack router skills/%s/SKILL.md refers to pruned leaf(s) %s "
                    "outside a table row; the fixture will not rewrite prose to "
                    "keep a baseline green" % (pack, ", ".join(missing))
                )
            dropped += 1
        if lines == kept_lines:
            continue
        path.write_text("\n".join(kept_lines) + "\n", encoding="utf-8")
    return dropped


def _write_claim_doc(fixture: Path) -> int:
    """A document holding one truthful, resolvable figure for brief-audit.

    Without a figure the gate walks its scan roots, finds nothing to resolve
    and prints PASS - a green that graded nothing. The mutant drifts this
    figure away from the register.
    """
    stars = register_stars(fixture)
    text = (
        "# Register claim (negative-control fixture)\n"
        "\n"
        "This page exists so the brief-audit gate has a figure to resolve\n"
        "against the canonical register at ops/automation/numbers.yaml. The\n"
        "value below is copied from that register at fixture build time, so a\n"
        "clean fixture is green and only the mutation makes it drift.\n"
        "\n"
        "| repo | stars |\n"
        "|---|---|\n"
        "| ajhcs/mbse-agents | %d |\n" % stars
    )
    path = fixture / CLAIM_DOC
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return stars


def build(repo: Path, dest: Path, gates=None) -> dict:
    """Build the fixture under `dest`. Returns a summary dict.

    `gates` is the gate set the fixture will be used against; each one's
    dependency closure is audited against the finished copy. Passing None
    skips the audit, which is only ever right in a unit test of the copy
    logic itself.
    """
    if dest.exists():
        raise FixtureError("fixture destination already exists: %s" % dest)
    dest.mkdir(parents=True)

    synthesized = []
    for rel in COPY_FILES:
        src = repo / rel
        if not src.exists() and rel in SYNTHESIZED_IF_ABSENT:
            # Legitimately absent (the public export drops it). Build the
            # shape the gate needs rather than failing the whole suite.
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(SYNTHESIZED_IF_ABSENT[rel](repo), encoding="utf-8")
            synthesized.append(rel)
            continue
        _copy_file(src, dest / rel)
    for rel in COPY_DIRS:
        _copy_dir(repo / rel, dest / rel)

    # Per-gate declared dependencies. Copied before the audit so the audit
    # grades the finished fixture, not an intention.
    declared = sorted({rel for deps in GATE_DEPENDENCIES.values() for rel in deps})
    for rel in declared:
        src = repo / rel
        if src.is_dir():
            _copy_dir(src, dest / rel)
        else:
            _copy_file(src, dest / rel)

    # ops/automation without its snapshot archive (stars-latest.json is copied
    # by COPY_FILES; the other 186 dated snapshots are never read).
    shutil.copytree(
        repo / OPS_AUTOMATION,
        dest / OPS_AUTOMATION,
        ignore=lambda d, names: _ignore(d, names) | ({"state"} if Path(d).name == "automation" else set()),
        symlinks=True,
        dirs_exist_ok=True,
    )

    packs = []
    for leaf, _fragment in KEPT_LEAVES:
        pack = leaf.split("/")[0]
        if pack not in packs:
            packs.append(pack)
            _copy_file(repo / "skills" / pack / "SKILL.md", dest / "skills" / pack / "SKILL.md")
        _copy_dir(repo / "skills" / leaf, dest / "skills" / leaf)

    tasks = _build_corpus(repo, dest)
    band = _align_release_versions(dest)
    stars = _write_claim_doc(dest)
    pruned_rows = _prune_pack_routers(repo, dest, packs)

    hashed = sorted(set(GATE_SOURCES) | {rel for rel in declared if (repo / rel).is_file()})
    absent = [rel for rel in hashed if not (dest / rel).exists()]
    if absent:
        raise FixtureError(
            "the tree ships these gate sources and the fixture does not carry "
            "them, so the gate that runs them would be red before any mutation: "
            "%s (add them to COPY_FILES, COPY_DIRS or GATE_DEPENDENCIES)"
            % ", ".join(absent)
        )
    mismatched = [rel for rel in hashed if sha256(repo / rel) != sha256(dest / rel)]
    if mismatched:
        raise FixtureError(
            "fixture gate sources differ from the tree (the control would grade "
            "a paraphrase, not the gate): %s" % ", ".join(mismatched)
        )

    audited = audit_gate_dependencies(repo, dest, gates) if gates else {}

    return {
        "leaves": [leaf for leaf, _ in KEPT_LEAVES],
        "packs": packs,
        "corpus_tasks": tasks,
        "band": band,
        "register_stars": stars,
        "router_rows_pruned": pruned_rows,
        "gate_sources_verified": len(hashed),
        "declared_dependencies": declared,
        "dependencies_audited": audited,
    }
