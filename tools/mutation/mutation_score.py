#!/usr/bin/env python3
"""Sampled mutation scorer for the leaf corpus (stdlib only, offline).

Why this exists
---------------
"10 to 65 tests per leaf" is a count, not a measurement of suite strength.
A count says nothing about whether the suite would notice if the logic were
wrong.  This tool answers the question a count cannot: if we damage the logic
module in a small, well-defined way, does the leaf's own suite go red?

Method
------
  1. Enumerate the population of leaves under ``skills/``.  A leaf is a
     directory holding ``SKILL.md`` plus a ``scripts/`` directory with exactly
     one logic module and at least one unittest suite.  Modules are sorted
     into "suite" and "logic" by content (does the file define a TestCase or
     call ``unittest.main``), not by filename, because a handful of leaves
     ship a logic module whose name begins with ``test_``.
  2. Draw a sample of leaves with a caller-supplied seed.  The exact selection,
     the seed, the population size and a fingerprint of the population are all
     written into the report so the run can be repeated.
  3. For each sampled leaf, copy the whole leaf directory to a scratch
     location outside the repository.  Every run below happens in that copy;
     the working tree is never written to.
  4. Run the suite twice as a control: once against the untouched copy, once
     against a copy whose logic module has been round-tripped through the AST
     unparser with no change applied.  A leaf that fails either control is
     excluded from scoring and the reason is recorded -- a red or
     source-inspecting suite cannot yield an honest mutation score.
  5. Generate the mutant catalogue for the logic module, draw a seeded sample
     of mutants, apply each one to a fresh copy, and run the suite against it
     under a wall-clock limit, capturing BOTH stdout and stderr (unittest
     prints its OK line on stderr, so a stdout-only capture reads a pass as a
     failure).
  6. A mutant whose run exits non-zero is killed.  A mutant whose run exits
     zero SURVIVED -- that is a hole in the suite.  A mutant that exceeds the
     time limit is counted as killed and also counted separately, because an
     infinite loop is a detected change but not an assertion.

Mutation catalogue
------------------
  comparison-swap        <  <-> <=,  >  <-> >=,  == <-> !=,  is <-> is not,
                         in <-> not in
  boundary-offset        a compared bound n becomes n+1 or n-1
  arithmetic-swap        + <-> -,  * <-> /,  // -> *,  % -> *,  ** -> *
  boolean-negation       and <-> or, a `not` dropped, an if/while test
                         negated, True <-> False
  constant-perturbation  a numeric literal v becomes v+1, becomes 0 (or 1 if
                         it already is 0), and for floats v*1.01
  early-return           `return None` inserted at the top of a function body

Reading the number
------------------
The score is a LOWER bound on suite strength.  Some mutants are semantically
equivalent to the original (perturbing a tolerance constant by 1% often is),
and an equivalent mutant can never be killed, so it lands in the survivor
column and pushes the score down.  Equivalence is undecidable in general and
this tool makes no attempt to detect it.  A score reported here is therefore
"at least this strong", never "exactly this strong".

The sampling unit is the leaf, not the mutant, so mutants within one leaf are
correlated.  The report carries three intervals: a Wilson interval on the
pooled mutant-level proportion (which ignores that correlation and is
therefore too narrow), a cluster bootstrap over leaves on the pooled score
(the one to quote), and a cluster bootstrap on the mean of per-leaf scores.

Determinism
-----------
No unseeded random source is used.  Leaf selection is driven by the seed
argument; each leaf's mutant selection is driven by a sub-seed derived from
the seed and the leaf path, so changing the sample size does not change which
mutants an already-sampled leaf gets.  Child processes run with
PYTHONHASHSEED=0.

Usage
-----
  python3 tools/mutation/mutation_score.py --seed 20260919 --sample 40
  python3 tools/mutation/mutation_score.py --seed 20260919 --sample 200 \
      --mutants-per-leaf 30 --jobs 8 --timeout 10
  python3 tools/mutation/mutation_score.py --seed 20260919 --list-only
  python3 tools/mutation/mutation_score.py --leaves-file <selection.json>
"""

from __future__ import annotations

import argparse
import ast
import concurrent.futures
import datetime
import hashlib
import json
import math
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

TOOL_VERSION = "1.0.0"
TOOL_PATH = "tools/mutation/mutation_score.py"

# A module is a suite, not logic, when it defines a TestCase or drives the
# stdlib runner.  Filename is not reliable: a few leaves ship a logic module
# called test_<something>_logic.py.
SUITE_MARKER = re.compile(r"unittest\.main\s*\(|unittest\.TestCase")

CMP_SWAP = {
    "Lt": "LtE",
    "LtE": "Lt",
    "Gt": "GtE",
    "GtE": "Gt",
    "Eq": "NotEq",
    "NotEq": "Eq",
    "Is": "IsNot",
    "IsNot": "Is",
    "In": "NotIn",
    "NotIn": "In",
}

ARITH_SWAP = {
    "Add": "Sub",
    "Sub": "Add",
    "Mult": "Div",
    "Div": "Mult",
    "FloorDiv": "Mult",
    "Mod": "Mult",
    "Pow": "Mult",
}

OPERATOR_FAMILIES = (
    "comparison-swap",
    "boundary-offset",
    "arithmetic-swap",
    "boolean-negation",
    "constant-perturbation",
    "early-return",
)

Z95 = 1.959963984540054


# --------------------------------------------------------------------------
# corpus discovery
# --------------------------------------------------------------------------


def _read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def discover_leaves(repo_root, skills_dirname="skills"):
    """Return the sorted leaf population as a list of dicts.

    Each entry carries repo-relative paths only, so a report built from it
    holds no absolute path.
    """
    skills_root = os.path.join(repo_root, skills_dirname)
    leaves = []
    for dirpath, dirnames, filenames in os.walk(skills_root):
        dirnames.sort()
        if os.path.basename(dirpath) != "scripts":
            continue
        leaf_dir = os.path.dirname(dirpath)
        if not os.path.exists(os.path.join(leaf_dir, "SKILL.md")):
            continue
        logic, suites = [], []
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            src = _read_text(os.path.join(dirpath, name))
            (suites if SUITE_MARKER.search(src) else logic).append(name)
        if not logic or not suites:
            continue
        primary = _pick_logic(logic)
        leaves.append(
            {
                "leaf": os.path.relpath(leaf_dir, repo_root),
                "logic": primary,
                "suite": suites[0],
                "extra_logic": [m for m in logic if m != primary],
                "extra_suites": suites[1:],
            }
        )
    leaves.sort(key=lambda e: e["leaf"])
    return leaves


def _pick_logic(candidates):
    """Pick the primary logic module when a leaf ships more than one."""
    named = [c for c in candidates if c.endswith("_logic.py")]
    if len(named) == 1:
        return named[0]
    pool = named or candidates
    return sorted(pool)[0]


def corpus_fingerprint(leaves):
    digest = hashlib.sha256()
    for entry in leaves:
        digest.update(entry["leaf"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(entry["logic"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(entry["suite"].encode("utf-8"))
        digest.update(b"\n")
    return "sha256:" + digest.hexdigest()


def select_leaves(leaves, seed, sample):
    """Seeded sample of the population.  No unseeded source is touched."""
    rnd = random.Random("aero-mutation-leaf-selection:%s" % (seed,))
    if sample >= len(leaves):
        return list(leaves)
    return sorted(rnd.sample(leaves, sample), key=lambda e: e["leaf"])


# --------------------------------------------------------------------------
# mutation catalogue
# --------------------------------------------------------------------------


def _child_slots(node):
    for field, value in ast.iter_fields(node):
        if isinstance(value, list):
            for pos, item in enumerate(value):
                if isinstance(item, ast.AST):
                    yield field, pos, item
        elif isinstance(value, ast.AST):
            yield field, None, value


def _docstring_offset(body):
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return 1
    return 0


def enumerate_mutants(source):
    """Return the deterministic, ordered catalogue of mutants for a module.

    Every spec addresses its target by index into ``list(ast.walk(tree))``,
    which is a stable breadth-first order, so a spec can be re-applied to a
    freshly parsed copy of the same source.
    """
    tree = ast.parse(source)
    nodes = list(ast.walk(tree))
    specs = []

    for i, node in enumerate(nodes):
        line = getattr(node, "lineno", 0)

        if isinstance(node, ast.Compare):
            for j, op in enumerate(node.ops):
                name = type(op).__name__
                if name in CMP_SWAP:
                    specs.append(
                        {
                            "op": "comparison-swap",
                            "i": i,
                            "j": j,
                            "to": CMP_SWAP[name],
                            "line": line,
                            "detail": "%s -> %s" % (name, CMP_SWAP[name]),
                        }
                    )
            for j in range(len(node.comparators)):
                for delta in (1, -1):
                    specs.append(
                        {
                            "op": "boundary-offset",
                            "i": i,
                            "j": j,
                            "delta": delta,
                            "line": line,
                            "detail": "bound %+d" % delta,
                        }
                    )

        elif isinstance(node, ast.BinOp):
            name = type(node.op).__name__
            if name in ARITH_SWAP:
                specs.append(
                    {
                        "op": "arithmetic-swap",
                        "i": i,
                        "to": ARITH_SWAP[name],
                        "line": line,
                        "detail": "%s -> %s" % (name, ARITH_SWAP[name]),
                    }
                )

        elif isinstance(node, ast.BoolOp):
            flip = "Or" if isinstance(node.op, ast.And) else "And"
            specs.append(
                {
                    "op": "boolean-negation",
                    "kind": "boolop",
                    "i": i,
                    "to": flip,
                    "line": line,
                    "detail": "%s -> %s" % (type(node.op).__name__, flip),
                }
            )

        elif isinstance(node, (ast.If, ast.While)):
            specs.append(
                {
                    "op": "boolean-negation",
                    "kind": "negate-test",
                    "i": i,
                    "line": line,
                    "detail": "negate %s test" % type(node).__name__.lower(),
                }
            )

        elif isinstance(node, ast.Constant):
            value = node.value
            if isinstance(value, bool):
                specs.append(
                    {
                        "op": "boolean-negation",
                        "kind": "flip-bool",
                        "i": i,
                        "line": line,
                        "detail": "%r -> %r" % (value, not value),
                    }
                )
            elif isinstance(value, int) or (
                isinstance(value, float) and math.isfinite(value)
            ):
                specs.append(
                    {
                        "op": "constant-perturbation",
                        "kind": "plus-one",
                        "i": i,
                        "line": line,
                        "detail": "%r -> %r" % (value, value + 1),
                    }
                )
                zeroed = 1 if value == 0 else 0
                specs.append(
                    {
                        "op": "constant-perturbation",
                        "kind": "zero",
                        "i": i,
                        "line": line,
                        "detail": "%r -> %r" % (value, zeroed),
                    }
                )
                if isinstance(value, float) and value != 0.0:
                    specs.append(
                        {
                            "op": "constant-perturbation",
                            "kind": "one-percent",
                            "i": i,
                            "line": line,
                            "detail": "%r -> %r" % (value, value * 1.01),
                        }
                    )

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = _docstring_offset(node.body)
            remaining = node.body[start:]
            if len(remaining) >= 1 and not (
                len(remaining) == 1 and isinstance(remaining[0], ast.Return)
            ):
                specs.append(
                    {
                        "op": "early-return",
                        "i": i,
                        "pos": start,
                        "line": line,
                        "detail": "return None at top of %s" % node.name,
                    }
                )

        # `not X` needs its parent slot to be removed, so it is catalogued
        # from the parent side.
        for field, pos, child in _child_slots(node):
            if isinstance(child, ast.UnaryOp) and isinstance(child.op, ast.Not):
                specs.append(
                    {
                        "op": "boolean-negation",
                        "kind": "drop-not",
                        "i": i,
                        "field": field,
                        "pos": pos,
                        "line": getattr(child, "lineno", line),
                        "detail": "drop not",
                    }
                )

    for n, spec in enumerate(specs):
        spec["id"] = n
    return specs


def _new_op(name):
    return getattr(ast, name)()


def apply_mutant(source, spec):
    """Return the mutated source for one spec, or None if it is a no-op."""
    tree = ast.parse(source)
    nodes = list(ast.walk(tree))
    node = nodes[spec["i"]]
    family = spec["op"]

    if family == "comparison-swap":
        node.ops[spec["j"]] = _new_op(spec["to"])
    elif family == "boundary-offset":
        old = node.comparators[spec["j"]]
        op = ast.Add() if spec["delta"] > 0 else ast.Sub()
        node.comparators[spec["j"]] = ast.BinOp(left=old, op=op, right=ast.Constant(1))
    elif family == "arithmetic-swap":
        node.op = _new_op(spec["to"])
    elif family == "boolean-negation":
        kind = spec["kind"]
        if kind == "boolop":
            node.op = _new_op(spec["to"])
        elif kind == "negate-test":
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
        elif kind == "flip-bool":
            node.value = not node.value
        elif kind == "drop-not":
            if spec["pos"] is None:
                setattr(node, spec["field"], getattr(node, spec["field"]).operand)
            else:
                seq = getattr(node, spec["field"])
                seq[spec["pos"]] = seq[spec["pos"]].operand
        else:  # pragma: no cover - guarded by the catalogue
            raise ValueError("unknown boolean-negation kind %r" % (kind,))
    elif family == "constant-perturbation":
        kind = spec["kind"]
        if kind == "plus-one":
            node.value = node.value + 1
        elif kind == "zero":
            node.value = 1 if node.value == 0 else 0
        elif kind == "one-percent":
            node.value = node.value * 1.01
        else:  # pragma: no cover
            raise ValueError("unknown constant-perturbation kind %r" % (kind,))
    elif family == "early-return":
        node.body.insert(spec["pos"], ast.Return(value=ast.Constant(None)))
    else:  # pragma: no cover
        raise ValueError("unknown mutation family %r" % (family,))

    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def roundtrip(source):
    """The unmutated source put through the same parse/unparse path."""
    return ast.unparse(ast.parse(source))


def select_mutants(specs, seed, leaf_rel, cap):
    """Seeded sample of the catalogue for one leaf.

    The sub-seed folds in the leaf path, so growing --sample does not shuffle
    the mutants an already-sampled leaf receives.
    """
    if cap >= len(specs):
        return list(specs)
    rnd = random.Random("aero-mutation-mutant-selection:%s:%s" % (seed, leaf_rel))
    return sorted(rnd.sample(specs, cap), key=lambda s: s["id"])


# --------------------------------------------------------------------------
# sandboxed execution
# --------------------------------------------------------------------------

RUN_PASS = "pass"
RUN_FAIL = "fail"
RUN_TIMEOUT = "timeout"


class Sandbox:
    """A scratch copy of one leaf, guaranteed to live outside the repo."""

    def __init__(self, repo_root, leaf_dir_abs):
        self.repo_root = os.path.realpath(repo_root)
        self.tmp = tempfile.mkdtemp(prefix="aero-mutation-")
        real_tmp = os.path.realpath(self.tmp)
        if real_tmp == self.repo_root or real_tmp.startswith(self.repo_root + os.sep):
            shutil.rmtree(self.tmp, ignore_errors=True)
            raise RuntimeError("scratch directory landed inside the repository")
        self.leaf = os.path.join(self.tmp, "leaf")
        shutil.copytree(leaf_dir_abs, self.leaf)

    def write_logic(self, logic_name, source):
        target = os.path.join(self.leaf, "scripts", logic_name)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(source)

    def run_suite(self, suite_name, timeout):
        script = os.path.join(self.leaf, "scripts", suite_name)
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONHASHSEED"] = "0"
        env.pop("PYTHONSTARTUP", None)
        started = time.time()
        proc = subprocess.Popen(
            [sys.executable, script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.leaf,
            env=env,
            start_new_session=True,
        )
        try:
            out, err = proc.communicate(timeout=timeout)
            status = RUN_PASS if proc.returncode == 0 else RUN_FAIL
            code = proc.returncode
        except subprocess.TimeoutExpired:
            _kill_group(proc)
            try:
                out, err = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover
                out, err = b"", b""
            status = RUN_TIMEOUT
            code = None
        # unittest writes its OK / FAILED line to stderr; both streams are kept
        # so a pass is never misread as a failure.
        return {
            "status": status,
            "returncode": code,
            "seconds": round(time.time() - started, 3),
            "stdout": out.decode("utf-8", "replace"),
            "stderr": err.decode("utf-8", "replace"),
        }

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def _kill_group(proc):
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except OSError:  # pragma: no cover
            pass


ABS_PATH = re.compile(r"(?<![\w.])/(?:Users|home|var|private|tmp|opt|Library)/[^\s'\"<>)]*")


def scrub_paths(text):
    """Strip absolute paths so a written report carries none.

    Reports land in the repository; machine-local paths belong in a console
    log, never in a committed file.
    """
    return ABS_PATH.sub("<path>", text)


def _tail(text, limit=400):
    return scrub_paths(text.strip())[-limit:]


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------


def score_leaf(repo_root, entry, seed, mutants_per_leaf, timeout):
    """Score one leaf.  Returns a dict; never writes inside the repository."""
    leaf_rel = entry["leaf"]
    leaf_abs = os.path.join(repo_root, leaf_rel)
    logic_rel = os.path.join("scripts", entry["logic"])
    source = _read_text(os.path.join(leaf_abs, logic_rel))

    result = {
        "leaf": leaf_rel,
        "logic": entry["logic"],
        "suite": entry["suite"],
        "status": "scored",
        "sites": 0,
        "mutants_run": 0,
        "killed": 0,
        "survived": 0,
        "timeouts": 0,
        "no_op_skipped": 0,
        "score": None,
        "survivors": [],
        "by_operator": {},
        "by_kind": {},
        "seconds": 0.0,
    }
    started = time.time()

    box = None
    try:
        box = Sandbox(repo_root, leaf_abs)

        control = box.run_suite(entry["suite"], timeout)
        if control["status"] != RUN_PASS:
            result["status"] = "excluded:suite-red-before-mutation"
            result["note"] = _tail(control["stderr"] or control["stdout"])
            return result

        try:
            rt = roundtrip(source)
        except SyntaxError as exc:
            result["status"] = "excluded:unparseable-logic"
            result["note"] = str(exc)
            return result
        box.write_logic(entry["logic"], rt)
        control2 = box.run_suite(entry["suite"], timeout)
        if control2["status"] != RUN_PASS:
            result["status"] = "excluded:suite-sensitive-to-source-form"
            result["note"] = _tail(control2["stderr"] or control2["stdout"])
            return result

        specs = enumerate_mutants(source)
        result["sites"] = len(specs)
        if not specs:
            result["status"] = "excluded:no-mutation-sites"
            return result

        chosen = select_mutants(specs, seed, leaf_rel, mutants_per_leaf)

        per_op = {}
        per_kind = {}
        for spec in chosen:
            try:
                mutated = apply_mutant(source, spec)
            except (ValueError, TypeError, OverflowError, RecursionError):
                result["no_op_skipped"] += 1
                continue
            if mutated == rt:
                # Provably the same program text as the control; it could
                # never be killed, so it is not counted either way.
                result["no_op_skipped"] += 1
                continue

            box.write_logic(entry["logic"], mutated)
            run = box.run_suite(entry["suite"], timeout)
            bucket = per_op.setdefault(
                spec["op"], {"run": 0, "killed": 0, "survived": 0, "timeouts": 0}
            )
            kbucket = per_kind.setdefault(
                "%s/%s" % (spec["op"], spec.get("kind", "-")),
                {"run": 0, "killed": 0, "survived": 0, "timeouts": 0},
            )
            bucket["run"] += 1
            kbucket["run"] += 1
            result["mutants_run"] += 1
            if run["status"] == RUN_PASS:
                result["survived"] += 1
                bucket["survived"] += 1
                kbucket["survived"] += 1
                result["survivors"].append(
                    {
                        "op": spec["op"],
                        "kind": spec.get("kind", ""),
                        "line": spec["line"],
                        "detail": spec["detail"],
                    }
                )
            else:
                result["killed"] += 1
                bucket["killed"] += 1
                kbucket["killed"] += 1
                if run["status"] == RUN_TIMEOUT:
                    result["timeouts"] += 1
                    bucket["timeouts"] += 1
                    kbucket["timeouts"] += 1

        result["by_operator"] = per_op
        result["by_kind"] = per_kind
        if result["mutants_run"]:
            result["score"] = result["killed"] / result["mutants_run"]
        else:
            result["status"] = "excluded:no-effective-mutants"
    except Exception as exc:  # noqa: BLE001 - a broken leaf must not stop the sweep
        result["status"] = "excluded:harness-error"
        result["note"] = "%s: %s" % (type(exc).__name__, exc)
    finally:
        if box is not None:
            box.close()
        result["seconds"] = round(time.time() - started, 3)
    return result


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------


def wilson_interval(killed, total, z=Z95):
    if total <= 0:
        return None
    p = killed / total
    denom = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denom
    half = (
        z
        * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total))
        / denom
    )
    return [max(0.0, center - half), min(1.0, center + half)]


def cluster_bootstrap(per_leaf, seed, resamples, statistic):
    """Percentile bootstrap resampling LEAVES, not mutants.

    `statistic` takes a list of (killed, total) pairs and returns a float.
    """
    if not per_leaf:
        return None
    rnd = random.Random("aero-mutation-bootstrap:%s" % (seed,))
    n = len(per_leaf)
    draws = []
    for _ in range(resamples):
        sample = [per_leaf[rnd.randrange(n)] for _ in range(n)]
        value = statistic(sample)
        if value is not None:
            draws.append(value)
    if not draws:
        return None
    draws.sort()
    lo = draws[int(0.025 * (len(draws) - 1))]
    hi = draws[int(math.ceil(0.975 * (len(draws) - 1)))]
    return [lo, hi]


def _pooled(sample):
    killed = sum(k for k, _ in sample)
    total = sum(t for _, t in sample)
    return killed / total if total else None


def _mean_of_leaf_scores(sample):
    scores = [k / t for k, t in sample if t]
    return sum(scores) / len(scores) if scores else None


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------


def build_report(args, population, selection, results, elapsed):
    scored = [r for r in results if r["status"] == "scored"]
    excluded = [
        {"leaf": r["leaf"], "reason": r["status"], "note": r.get("note", "")}
        for r in results
        if r["status"] != "scored"
    ]
    pairs = [(r["killed"], r["mutants_run"]) for r in scored]
    killed = sum(r["killed"] for r in scored)
    survived = sum(r["survived"] for r in scored)
    timeouts = sum(r["timeouts"] for r in scored)
    total = killed + survived

    by_op, by_kind = {}, {}
    for r in scored:
        for source, sink in ((r["by_operator"], by_op), (r["by_kind"], by_kind)):
            for name, bucket in source.items():
                agg = sink.setdefault(
                    name, {"run": 0, "killed": 0, "survived": 0, "timeouts": 0}
                )
                for key in ("run", "killed", "survived", "timeouts"):
                    agg[key] += bucket[key]
    for sink in (by_op, by_kind):
        for name, agg in sink.items():
            agg["score"] = agg["killed"] / agg["run"] if agg["run"] else None

    aggregate = {
        "n_leaves_sampled": len(selection),
        "n_leaves_scored": len(scored),
        "n_leaves_excluded": len(excluded),
        "mutants_run": total,
        "killed": killed,
        "survived": survived,
        "killed_by_timeout": timeouts,
        "mutation_score_pooled": (killed / total) if total else None,
        "ci95_pooled_wilson_mutant_level": wilson_interval(killed, total),
        "ci95_pooled_cluster_bootstrap_leaf_level": cluster_bootstrap(
            pairs, args.seed, args.bootstrap, _pooled
        ),
        "mean_of_per_leaf_scores": _mean_of_leaf_scores(pairs),
        "ci95_mean_per_leaf_cluster_bootstrap": cluster_bootstrap(
            pairs, args.seed, args.bootstrap, _mean_of_leaf_scores
        ),
        "bootstrap_resamples": args.bootstrap,
    }

    return {
        "tool": TOOL_PATH,
        "tool_version": TOOL_VERSION,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "python": "%d.%d.%d" % sys.version_info[:3],
        "seed": args.seed,
        "requested_sample": args.sample,
        "mutants_per_leaf": args.mutants_per_leaf,
        "timeout_seconds": args.timeout,
        "jobs": args.jobs,
        "wall_seconds": round(elapsed, 1),
        "corpus": {
            "root": args.skills_dir,
            "population": len(population),
            "fingerprint": corpus_fingerprint(population),
        },
        "selection": [e["leaf"] for e in selection],
        "aggregate": aggregate,
        "by_operator": by_op,
        "by_operator_kind": dict(sorted(by_kind.items())),
        "excluded": excluded,
        "leaves": [
            {
                key: value
                for key, value in r.items()
                if key not in ("by_operator", "by_kind")
            }
            for r in sorted(results, key=lambda r: r["leaf"])
        ],
    }


def _fmt_interval(iv):
    if not iv:
        return "n/a"
    return "[%.4f, %.4f]" % (iv[0], iv[1])


def print_summary(report, stream=sys.stdout):
    agg = report["aggregate"]
    w = stream.write
    w("\n")
    w("Aero Agent Skills - sampled mutation score\n")
    w("=" * 58 + "\n")
    w("seed                        %s\n" % report["seed"])
    w("population (leaves)         %d\n" % report["corpus"]["population"])
    w("corpus fingerprint          %s\n" % report["corpus"]["fingerprint"])
    w("leaves sampled (n)          %d\n" % agg["n_leaves_sampled"])
    w("leaves scored               %d\n" % agg["n_leaves_scored"])
    w("leaves excluded             %d\n" % agg["n_leaves_excluded"])
    w("mutants per leaf (cap)      %d\n" % report["mutants_per_leaf"])
    w("mutants run                 %d\n" % agg["mutants_run"])
    w("killed                      %d\n" % agg["killed"])
    w("survived                    %d\n" % agg["survived"])
    w("killed via time limit       %d\n" % agg["killed_by_timeout"])
    w("wall seconds                %.1f\n" % report["wall_seconds"])
    w("-" * 58 + "\n")
    score = agg["mutation_score_pooled"]
    w("MUTATION SCORE (pooled)     %s\n" % ("%.4f" % score if score is not None else "n/a"))
    w(
        "  95%% CI, leaf bootstrap    %s   <- quote this one\n"
        % _fmt_interval(agg["ci95_pooled_cluster_bootstrap_leaf_level"])
    )
    w(
        "  95%% CI, Wilson (mutant)   %s   (ignores leaf clustering)\n"
        % _fmt_interval(agg["ci95_pooled_wilson_mutant_level"])
    )
    mean = agg["mean_of_per_leaf_scores"]
    w(
        "mean of per-leaf scores     %s\n"
        % ("%.4f" % mean if mean is not None else "n/a")
    )
    w(
        "  95%% CI, leaf bootstrap    %s\n"
        % _fmt_interval(agg["ci95_mean_per_leaf_cluster_bootstrap"])
    )
    w("-" * 58 + "\n")
    w("by mutation family:\n")
    for name in OPERATOR_FAMILIES:
        agg_op = report["by_operator"].get(name)
        if not agg_op:
            continue
        w(
            "  %-22s run %5d  killed %5d  survived %5d  score %.4f\n"
            % (
                name,
                agg_op["run"],
                agg_op["killed"],
                agg_op["survived"],
                agg_op["score"] if agg_op["score"] is not None else float("nan"),
            )
        )
    kinds = report.get("by_operator_kind") or {}
    if kinds:
        w("-" * 58 + "\n")
        w("by mutation kind (a low score here is where the holes are):\n")
        for name in sorted(kinds, key=lambda k: (kinds[k]["score"] or 0.0, k)):
            agg_k = kinds[name]
            w(
                "  %-34s run %5d  survived %5d  score %.4f\n"
                % (
                    name,
                    agg_k["run"],
                    agg_k["survived"],
                    agg_k["score"] if agg_k["score"] is not None else float("nan"),
                )
            )
    weakest = sorted(
        (r for r in report["leaves"] if r["status"] == "scored" and r["score"] is not None),
        key=lambda r: (r["score"], r["leaf"]),
    )[:10]
    if weakest:
        w("-" * 58 + "\n")
        w("weakest suites in the sample:\n")
        for r in weakest:
            w(
                "  %.3f  %3d/%-3d  %s\n"
                % (r["score"], r["killed"], r["mutants_run"], r["leaf"])
            )
    if report["excluded"]:
        w("-" * 58 + "\n")
        w("excluded leaves:\n")
        for e in report["excluded"][:20]:
            w("  %-46s %s\n" % (e["reason"], e["leaf"]))
    w("\n")
    w(
        "The score is a LOWER bound: equivalent mutants cannot be killed and\n"
        "are counted as survivors.  n and the interval above are part of the\n"
        "measurement; a score quoted without them is not one.\n"
    )


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Sampled mutation scorer for the leaf corpus (stdlib only)."
    )
    p.add_argument(
        "--repo-root",
        default=None,
        help="repository root (default: the parent of tools/)",
    )
    p.add_argument("--skills-dir", default="skills", help="corpus directory name")
    p.add_argument(
        "--seed",
        type=int,
        required=False,
        default=None,
        help="integer seed; required for any run that scores leaves",
    )
    p.add_argument("--sample", type=int, default=40, help="number of leaves to draw")
    p.add_argument(
        "--mutants-per-leaf",
        type=int,
        default=25,
        help="cap on mutants drawn per leaf",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="wall-clock limit in seconds for one suite run",
    )
    p.add_argument(
        "--jobs",
        type=int,
        default=min(8, os.cpu_count() or 1),
        help="parallel leaf workers",
    )
    p.add_argument(
        "--bootstrap",
        type=int,
        default=10000,
        help="cluster bootstrap resamples for the confidence interval",
    )
    p.add_argument("--out", default=None, help="write the JSON report here")
    p.add_argument(
        "--list-only",
        action="store_true",
        help="print the seeded selection and exit without running anything",
    )
    p.add_argument(
        "--leaves-file",
        default=None,
        help="re-run exactly the leaves named by a previous report or selection file",
    )
    return p.parse_args(argv)


def default_repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


def main(argv=None):
    if sys.version_info < (3, 9):
        sys.stderr.write("mutation_score.py needs Python 3.9 or newer (ast.unparse)\n")
        return 2
    args = parse_args(argv)
    repo_root = os.path.abspath(args.repo_root or default_repo_root())

    population = discover_leaves(repo_root, args.skills_dir)
    if not population:
        sys.stderr.write("no leaves found under %s/\n" % args.skills_dir)
        return 2

    if args.leaves_file:
        with open(args.leaves_file, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        wanted = payload.get("selection") or payload
        if not isinstance(wanted, list):
            sys.stderr.write("--leaves-file must hold a list under 'selection'\n")
            return 2
        index = {e["leaf"]: e for e in population}
        missing = [w for w in wanted if w not in index]
        if missing:
            sys.stderr.write(
                "leaves named by --leaves-file are not in the corpus: %s\n"
                % ", ".join(missing[:5])
            )
            return 2
        selection = [index[w] for w in wanted]
        if args.seed is None:
            args.seed = payload.get("seed")
        args.sample = len(selection)
    else:
        if args.seed is None:
            sys.stderr.write("--seed is required (the run must be reproducible)\n")
            return 2
        selection = select_leaves(population, args.seed, args.sample)

    if args.seed is None:
        sys.stderr.write("--seed is required (the run must be reproducible)\n")
        return 2

    if args.list_only:
        print(json.dumps(
            {
                "seed": args.seed,
                "requested_sample": args.sample,
                "corpus": {
                    "root": args.skills_dir,
                    "population": len(population),
                    "fingerprint": corpus_fingerprint(population),
                },
                "selection": [e["leaf"] for e in selection],
            },
            indent=2,
        ))
        return 0

    sys.stderr.write(
        "mutation sweep: %d leaves, <=%d mutants each, %d jobs, %.0fs limit, seed %s\n"
        % (len(selection), args.mutants_per_leaf, args.jobs, args.timeout, args.seed)
    )

    started = time.time()
    results = []
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {
            pool.submit(
                score_leaf,
                repo_root,
                entry,
                args.seed,
                args.mutants_per_leaf,
                args.timeout,
            ): entry["leaf"]
            for entry in selection
        }
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            done += 1
            if done % 10 == 0 or done == len(futures):
                sys.stderr.write("  %d/%d leaves\n" % (done, len(futures)))
                sys.stderr.flush()
    elapsed = time.time() - started

    report = build_report(args, population, selection, results, elapsed)

    out = args.out
    if out is None:
        out_dir = os.path.join(repo_root, "tools", "mutation", "results")
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(
            out_dir, "run-seed%s-n%d.json" % (args.seed, len(selection))
        )
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=False)
        fh.write("\n")

    print_summary(report)
    shown = os.path.relpath(out, repo_root)
    if shown.startswith(os.pardir):
        shown = out
    sys.stdout.write("report written to %s\n" % shown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
