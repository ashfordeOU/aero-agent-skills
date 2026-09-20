#!/usr/bin/env python3
"""One negative control per gate: the smallest mutation the gate must reject.

Each control declares
  * the make target that runs the gate,
  * a mutation applied to a throwaway copy of the fixture,
  * a SIGNATURE the red output has to match.

The signature is the part that makes this a proof rather than a vibe. A gate
that exits non-zero because the mutation broke its parser has not detected the
defect - it crashed near it. A control only passes when the gate goes red AND
says the thing the mutation planted.

Rules honoured here:
  * mutations never touch the working tree (they run on a temp copy),
  * a mutation that finds nothing to change raises instead of silently doing
    nothing - a no-op mutation would fake a "gate cannot fail" finding,
  * marker strings the gates hunt for are assembled from fragments so this
    source file never itself carries one.

stdlib only, no network.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from fixture import (
    leaf_logic_module,
    FixtureError,
    PRIMARY_LEAF,
    CLAIM_DOC,
    KEPT_LEAVES,
    first_public_function,
    leaf_contract_test,
    leaf_logic_module,
    register_stars,
)


class MutationError(RuntimeError):
    """The mutation could not be applied, so the control cannot be trusted."""


@dataclass(frozen=True)
class Diagnosis:
    """A second, differently-shaped mutation, run ONLY when a control fails.

    It exists to separate "the gate is blind" from "the control is wrong". It
    never turns a failed control into a pass - a gate that needs a different
    mutation to go red is not red-capable for the defect the control planted.
    """

    description: str     # what this probe changes instead
    expectation: str     # what the outcome means either way
    apply: Callable[[Path], None]


@dataclass(frozen=True)
class Control:
    gate: str            # make target
    mutation: str        # what the mutation changes, in one clause
    signature: str       # regex the gate's red output must match
    apply: Callable[[Path], None]
    diagnosis: "Diagnosis | None" = None
    note: str = ""       # standing finding, printed when the control fails


# ---------------------------------------------------------------------------
# edit helpers
# ---------------------------------------------------------------------------


def _edit(path: Path, fn: Callable[[str], str]) -> None:
    """Rewrite a file through `fn`, refusing a no-op."""
    if not path.exists():
        raise MutationError("mutation target missing: %s" % path)
    before = path.read_text(encoding="utf-8")
    after = fn(before)
    if after == before:
        raise MutationError("mutation changed nothing in %s" % path)
    path.unlink()
    path.write_text(after, encoding="utf-8")


def _split_frontmatter(text: str):
    """(prefix, frontmatter, body) the way the gates themselves split it."""
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise MutationError("SKILL.md frontmatter is not closed")
    return parts[0], parts[1], parts[2]


def _edit_frontmatter(path: Path, fn: Callable[[str], str]) -> None:
    def whole(text: str) -> str:
        pre, fm, body = _split_frontmatter(text)
        return pre + "---" + fn(fm) + "---" + body

    _edit(path, whole)


def _skill_md(fixture: Path, leaf: str = PRIMARY_LEAF) -> Path:
    return fixture / "skills" / leaf / "SKILL.md"


# ---------------------------------------------------------------------------
# mutations - make validate
# ---------------------------------------------------------------------------


def mutate_lint_spec(fixture: Path) -> None:
    """Break the name <-> parent-directory identity the spec requires."""

    def fn(fm: str) -> str:
        new, n = re.subn(r"(?m)^name:\s*(\S+)\s*$", r"name: \1-notthisdir", fm, count=1)
        if not n:
            raise MutationError("no 'name:' key in the leaf frontmatter")
        return new

    _edit_frontmatter(_skill_md(fixture), fn)


def mutate_desc_lint(fixture: Path) -> None:
    """Remove the explicit when-to-use clause, keeping the word count intact."""

    def fn(fm: str) -> str:
        if "Use when" not in fm:
            raise MutationError("leaf description has no 'Use when' clause to remove")
        return fm.replace("Use when", "Apply when", 1)

    _edit_frontmatter(_skill_md(fixture), fn)


def mutate_pytest_contract(fixture: Path) -> None:
    """Stub the leaf logic module's first public entry point.

    A redefinition at the end of the module wins, so every caller of that
    function now gets None. This is a behaviour regression of exactly the kind
    the per-leaf contract test exists to catch.
    """
    module = leaf_logic_module(fixture)
    target = first_public_function(module)

    def fn(src: str) -> str:
        return src + (
            "\n\n# negative control: the shipped entry point is stubbed out.\n"
            "def %s(*_args, **_kwargs):\n"
            "    return None\n" % target
        )

    _edit(module, fn)


def mutate_no_verbatim(fixture: Path) -> None:
    """Plant one of the proprietary-source markers gate 4 hunts for."""
    marker = "PROPRIETARY" + " AND " + "CONFIDENTIAL"

    def fn(text: str) -> str:
        return text + "\n" + marker + "\n"

    _edit(_skill_md(fixture), fn)


# Our own prose, written for this control. Deliberately ordinary technical
# English, spaced like prose (no comma-separated runs), so the flattened-list
# discriminator in verbatim_gate.run_is_flattened has no reason to exclude it
# and the shingle arm is genuinely exercised. Long enough that winnowing picks
# well over the two fingerprints a FAIL needs.
CONTROL_SOURCE_PROSE = """
The supplier shall establish and maintain a register of every interface that
crosses a segment boundary and shall record for each one the responsible
party on either side together with the date on which the interface was last
agreed. Where an interface is changed after agreement the supplier shall
notify the affected parties before the change is applied and shall retain
evidence that the notification was issued. The register shall be available
for inspection at each milestone review and shall be complete in the sense
that every boundary identified in the architecture appears in it exactly
once. An interface that cannot be traced to an agreed requirement shall be
treated as an open item and shall be reported to the customer with a
proposed disposition and a date by which the disposition will be settled.
"""


def mutate_no_verbatim_source(fixture: Path) -> None:
    """Index an authored source, then plant it: the shingle arm must fail.

    Distinct from mutate_no_verbatim, which exercises the marker regex. This
    one proves the half of gate 4 that compares text against the indexed
    standards can still return red -- the property the flattened-list
    discriminator could otherwise have quietly removed.
    """
    import tempfile

    repo = Path(__file__).resolve().parents[2]
    builder = repo / "tools" / "build_verbatim_index.py"
    if not builder.is_file():
        raise MutationError("tools/build_verbatim_index.py is missing: the "
                            "source-text arm cannot be proven red-capable")
    out_dir = fixture / "tools" / "verbatim-index"
    if not out_dir.is_dir():
        raise MutationError("fixture carries no verbatim-index directory")

    src_dir = Path(tempfile.mkdtemp(prefix="aero-control-source-"))
    try:
        # Kept outside the fixture on purpose: inside it, the gate would scan
        # the source file itself and report it as its own reproduction.
        (src_dir / "CONTROL-AUTHORED-SOURCE.txt").write_text(
            CONTROL_SOURCE_PROSE, encoding="utf-8")
        r = subprocess.run(
            ["python3", str(builder), "--family", "ecss",
             "--sources", str(src_dir), "--out", str(out_dir)],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise MutationError("could not build the control index: %s"
                                % (r.stderr or r.stdout).strip()[:300])
    finally:
        shutil.rmtree(src_dir, ignore_errors=True)

    def fn(text: str) -> str:
        return text + "\n\n## Interface register\n" + CONTROL_SOURCE_PROSE

    _edit(_skill_md(fixture), fn)


def mutate_no_inference(fixture: Path) -> None:
    """Put a model call on the graded path.

    Claim 1 is that the graded corpus is a fixed, design-time rule base with
    no inference anywhere in it. Gate 10 is the only thing enforcing that, so
    it has to be shown rejecting the plainest possible violation: a leaf that
    reaches a model over the network at answer time.
    """
    module = leaf_logic_module(fixture)

    def fn(text: str) -> str:
        return (text + "\n\n"
                "import urllib.request\n\n\n"
                "def _ask_a_model(prompt):\n"
                "    req = urllib.request.Request(\n"
                '        "https://api.anthropic.com/v1/messages",\n'
                '        data=prompt.encode("utf-8"))\n'
                "    return urllib.request.urlopen(req).read()\n")

    _edit(module, fn)


def mutate_slug_uniqueness(fixture: Path) -> None:
    """Give one slug to two leaves.

    The published slug namespace is FLAT: an installed leaf is addressed by
    its slug alone, with no family or pack in the address. Two leaves sharing
    a slug therefore make one of them unreachable, and which one wins is a
    function of directory ordering. Copying a leaf into a second pack under
    the same directory name is the smallest way to produce that.
    """
    src = fixture / "skills" / PRIMARY_LEAF
    if not src.is_dir():
        raise MutationError("primary leaf %s is not in the fixture" % PRIMARY_LEAF)
    family, pack, slug = PRIMARY_LEAF.split("/")
    dst = fixture / "skills" / family / (pack + "-copy") / slug
    if dst.exists():
        raise MutationError("collision target already exists: %s" % dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)


def mutate_router_coverage_structure(fixture: Path) -> None:
    """Take one required key off a corpus case.

    Every router case owes four keys. Gate 12 grades the SHAPE of
    eval/hit1-corpus.yaml rather than its hit rate, because the Hit@1 gate
    reads only the tasks: key and would score a silently truncated file as a
    clean pass. Dropping one case's intent: is the smallest shape defect.
    """
    corpus = fixture / "eval/hit1-corpus.yaml"
    if not corpus.is_file():
        raise MutationError("fixture carries no eval/hit1-corpus.yaml")

    def fn(text: str) -> str:
        out, dropped = [], False
        for line in text.split("\n"):
            if not dropped and line.strip().startswith("intent:"):
                dropped = True
                continue
            out.append(line)
        if not dropped:
            raise MutationError("no corpus case carries an intent: key")
        return "\n".join(out)

    _edit(corpus, fn)


def mutate_router_coverage_complete(fixture: Path) -> None:
    """Plant a leaf skill that no router case names.

    Gate 5 grades the cases that exist; it is silent about a leaf with no case
    at all. That is how 2,251 of 3,189 leaves sat behind a green build with
    nothing ever asking the router about them. Gate 13 is the only gate that
    fails on that, so the mutation it must reject is a leaf arriving with no
    case anywhere.
    """
    primary = fixture / "skills" / PRIMARY_LEAF
    if not primary.is_dir():
        raise MutationError("fixture carries no %s" % PRIMARY_LEAF)
    planted = primary.parent / "leaf-with-no-router-case"
    if planted.exists():
        raise MutationError("the planted leaf is already in the fixture")
    planted.mkdir(parents=True)
    (planted / "SKILL.md").write_text(
        "---\n"
        "name: leaf-with-no-router-case\n"
        "description: \"Compute nothing; this leaf exists only so the "
        "coverage gate has an unasserted leaf to find. Use when running the "
        "negative control for gate 13. Trigger: negative-control, "
        "uncovered-leaf.\"\n"
        "license: Apache-2.0\n"
        "---\n"
        "\n"
        "## Domain quick reference\n"
        "\n"
        "- Planted by the negative-control suite. Not part of the catalogue.\n",
        encoding="utf-8")


def mutate_hit1(fixture: Path) -> None:
    """Point a corpus task at the wrong leaf, so top-1 no longer matches."""
    wrong = KEPT_LEAVES[1][0]
    right = KEPT_LEAVES[0][0]

    def fn(text: str) -> str:
        new, n = re.subn(
            r'expected_skill:\s*"%s"' % re.escape(right),
            'expected_skill: "%s"' % wrong,
            text,
            count=1,
        )
        if not n:
            raise MutationError("no corpus task expects %s" % right)
        return new

    _edit(fixture / "eval/hit1-corpus.yaml", fn)


def mutate_independence(fixture: Path) -> None:
    """Make one ledger row's verifier the same actor as its generator."""
    path = fixture / "ops/ecss-program/claims-ledger.md"

    def fn(text: str) -> str:
        lines = text.splitlines()
        cols = None
        for i, line in enumerate(lines):
            if not line.strip().startswith("|"):
                continue
            cells = [c.strip().lower() for c in line.strip().strip("|").split("|")]
            if cols is None:
                if "generator" in cells and "verifier" in cells:
                    cols = (cells.index("generator"), cells.index("verifier"))
                continue
            if set("".join(cells)) <= set("-: "):
                continue
            raw = [c for c in line.strip().strip("|").split("|")]
            gi, vi = cols
            if len(raw) <= max(gi, vi):
                continue
            raw[vi] = raw[gi]
            lines[i] = "|" + "|".join(raw) + "|"
            return "\n".join(lines) + "\n"
        raise MutationError("no claims-ledger row with generator/verifier columns")

    _edit(path, fn)


def mutate_release_law(fixture: Path) -> None:
    """Push the leaf count over the next 100-skill band boundary.

    The version files stay where they are, so they are now a minor behind the
    band the convention demands - the drift this gate was written for.
    """

    def fn(text: str) -> str:
        new, n = re.subn(
            r'("leaves"\s*:\s*)(\d+)',
            lambda m: m.group(1) + str(int(m.group(2)) + 100),
            text,
            count=1,
        )
        if not n:
            raise MutationError("no 'leaves' figure in docs/metrics.json")
        return new

    _edit(fixture / "docs/metrics.json", fn)


def mutate_portability(fixture: Path) -> None:
    """Add a strict inequality that sits ~1e-13 from its bound.

    The assertion PASSES, so the contract-test gate stays green: this is
    exactly the defect class (a test pinned to the last-place result of a
    libm call) that only the portability gate can see.
    """
    test = leaf_contract_test(fixture)
    block = (
        "class BoundaryNegativeControl(unittest.TestCase):\n"
        "    def test_strict_inequality_sits_on_its_bound(self):\n"
        "        self.assertLess(10.0 - 1e-13, 10.0)\n"
        "\n"
        "\n"
    )

    def fn(src: str) -> str:
        idx = src.rfind("if __name__")
        if idx < 0:
            raise MutationError("contract test has no __main__ guard to insert before")
        return src[:idx] + block + src[idx:]

    _edit(test, fn)


def probe_portability_module_scope(fixture: Path) -> None:
    """The same near-boundary assertion, executed at import instead of in a test.

    Diagnostic only. If this turns the gate red while the in-method mutation
    does not, the instrumentation works and the problem is that no test method
    ever runs underneath it.
    """
    test = leaf_contract_test(fixture)
    block = (
        "class _BoundaryProbe(unittest.TestCase):\n"
        "    def runTest(self):\n"
        "        pass\n"
        "\n"
        "\n"
        "_BoundaryProbe().assertLess(10.0 - 1e-13, 10.0)\n"
        "\n"
        "\n"
    )

    def fn(src: str) -> str:
        idx = src.rfind("if __name__")
        if idx < 0:
            raise MutationError("contract test has no __main__ guard to insert before")
        return src[:idx] + block + src[idx:]

    _edit(test, fn)


def mutate_corpus_naming(fixture: Path) -> None:
    """File a second corpus fragment for one leaf under a different spelling."""
    _leaf, fragment = KEPT_LEAVES[0]
    src = fixture / "eval" / fragment
    if not src.exists():
        raise MutationError("corpus fragment missing: eval/%s" % fragment)
    slug = KEPT_LEAVES[0][0].rsplit("/", 1)[-1]
    dup = fixture / "eval" / ("hit1-secondspelling-%s.yaml" % slug)
    if dup.exists():
        raise MutationError("duplicate fragment already present: %s" % dup.name)
    dup.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


# ---------------------------------------------------------------------------
# mutations - make attest
# ---------------------------------------------------------------------------


def mutate_number_snapshot(fixture: Path) -> None:
    """Drift the register away from the figure the snapshot recorded."""
    path = fixture / "ops/automation/numbers.yaml"
    current = register_stars(fixture)
    drifted = current * 1000 + 7

    def fn(text: str) -> str:
        lines = text.splitlines(keepends=True)
        seen = False
        for i, line in enumerate(lines):
            if re.match(r"^\s*-?\s*id:\s*ajhcs\s*$", line):
                seen = True
                continue
            if seen:
                m = re.match(r"^(\s*stars:\s*)(\d+)(\s*)$", line)
                if m:
                    lines[i] = "%s%d%s" % (m.group(1), drifted, m.group(3))
                    return "".join(lines)
                if re.match(r"^\s*-\s*id:\s*", line):
                    break
        raise MutationError("no stars figure for 'ajhcs' in the register")

    _edit(path, fn)


def mutate_brief_audit(fixture: Path) -> None:
    """Drift a published figure away from the register that governs it."""
    current = register_stars(fixture)
    drifted = current * 1000 + 7

    def fn(text: str) -> str:
        new, n = re.subn(r"\|\s*%d\s*\|" % current, "| %d |" % drifted, text, count=1)
        if not n:
            raise MutationError("claim document does not carry the register figure")
        return new

    _edit(fixture / CLAIM_DOC, fn)


def mutate_content_policy(fixture: Path) -> None:
    """Plant an export-compliance claim in buyer-facing content."""
    claim = "ITAR" + "-compliant"

    def fn(text: str) -> str:
        return text + "\nThis workflow is %s.\n" % claim

    _edit(_skill_md(fixture), fn)


# ---------------------------------------------------------------------------
# the control set
# ---------------------------------------------------------------------------


def mutate_shipped_instructions(fixture: Path) -> None:
    """Tell the reader to cd into a directory only the author has.

    The real defect: four shipped files opened their contract-test
    instructions by changing directory into a home path named AeroSkills --
    the repository's old layout, which
    exists on no customer's machine and not on the build host either. The
    first command a buyer copied out of those leaves failed before it ran
    anything, and one of them said "Run from anywhere:" directly above it.
    """
    _edit(_skill_md(fixture),
          # fragments, so controls.py does not trip the gate it exercises
          lambda s: s + "\n## Contract test\n\n    c" + "d ~/DevBoxOnly\n"
                        "    python3 scripts/test_it.py\n")


CONTROLS = [
    Control(
        gate="lint-spec",
        mutation="leaf SKILL.md frontmatter name no longer equals its parent directory",
        signature=r"FAIL gate1-spec-lint:.*!= parent dir name",
        apply=mutate_lint_spec,
    ),
    Control(
        gate="desc-lint",
        mutation="leaf description's 'Use when' clause reworded to 'Apply when'",
        signature=r"FAIL gate2-desc-lint:.*no when-to-use clause",
        apply=mutate_desc_lint,
    ),
    Control(
        gate="pytest-contract",
        mutation="leaf logic module's first public function stubbed to return None",
        signature=r"FAIL gate3-pytest-contract",
        apply=mutate_pytest_contract,
    ),
    Control(
        gate="no-verbatim",
        mutation="proprietary-source marker line planted in a leaf SKILL.md",
        signature=r"FAIL gate4-no-verbatim",
        apply=mutate_no_verbatim,
    ),
    Control(
        gate="no-verbatim",
        mutation="a leaf reproduces a paragraph that the family index holds "
                 "(index built from an authored control source, not ECSS)",
        signature=r"FAIL gate4-no-verbatim:.*reproduces ecss source text",
        apply=mutate_no_verbatim_source,
    ),
    Control(
        gate="no-inference",
        mutation="leaf logic module given a function that calls a model over "
                 "the network",
        signature=r"FAIL \S*no-inference:.*can reach model inference",
        apply=mutate_no_inference,
    ),
    Control(
        gate="slug-uniqueness",
        mutation="a leaf copied into a second pack under the same slug",
        signature=r"FAIL slug-uniqueness A:",
        apply=mutate_slug_uniqueness,
    ),
    Control(
        gate="router-coverage-structure",
        mutation="one corpus case stripped of its required intent: key",
        signature=r"FAIL router-coverage: eval/.*structurally malformed",
        apply=mutate_router_coverage_structure,
    ),
    Control(
        gate="router-coverage-complete",
        mutation="a leaf skill planted with no router case naming it",
        signature=r"FAIL router-coverage: \d+ uncovered leaves",
        apply=mutate_router_coverage_complete,
    ),
    Control(
        gate="hit1",
        mutation="one corpus task's expected_skill repointed to a different leaf",
        signature=r"FAIL gate5-hit1",
        apply=mutate_hit1,
    ),
    Control(
        gate="independence",
        mutation="claims-ledger row's verifier set to its own generator",
        signature=r"(verifier == generator|not independent)",
        apply=mutate_independence,
    ),
    Control(
        gate="release-law",
        mutation="docs/metrics.json leaf count pushed over the next 100-skill band",
        signature=r"version file behind band[\s\S]*VERDICT: FAIL",
        apply=mutate_release_law,
    ),
    Control(
        gate="portability",
        mutation="passing assertLess planted 1e-13 from its bound in a leaf contract test",
        signature=r"FAIL portability: \d+ strict assertion",
        apply=mutate_portability,
        diagnosis=Diagnosis(
            description="the same assertion moved to module scope, so it executes at import",
            expectation=(
                "red here + green above means the instrumentation works but no assertion "
                "inside a test method ever executes under it"
            ),
            apply=probe_portability_module_scope,
        ),
        note=(
            "PRIOR FINDING, repaired in scripts/ on 2026-09-19 and re-measured RED-CAPABLE "
            "the same day. Printed only if this control fails again, because the cause was "
            "invisible from the gate's own green line and is worth naming twice. "
            "scripts/portability_check.py ran each contract test with "
            "runpy under an instrumented unittest.TestCase while leaving sys.argv as "
            "[runner, target]. unittest.main() then read the target's own path as a "
            "test name, the loader turned it into a _FailedTest, and the file's test methods "
            "never ran - so no assertion was ever measured and the gate printed PASS over a "
            "set it did not execute. Remedy (one line, in RUNNER_SRC, immediately after the "
            "existing sys.path.insert): set sys.argv = [target] before runpy.run_path(...). "
            "Verified on a copy: with that line the in-method mutation above is caught."
        ),
    ),
    Control(
        gate="corpus-naming",
        mutation="one leaf's corpus fragment duplicated under a second spelling",
        signature=r"FAIL corpus-naming",
        apply=mutate_corpus_naming,
    ),
    Control(
        gate="number-snapshot-offline",
        mutation="register's tracked star figure drifted away from the recorded snapshot",
        signature=r"FAIL number-snapshot --offline",
        apply=mutate_number_snapshot,
    ),
    Control(
        gate="brief-audit",
        mutation="published figure in docs/ drifted away from the canonical register",
        signature=r"FAIL brief-audit: \d+ drift",
        apply=mutate_brief_audit,
    ),
    Control(
        gate="content-policy-sweep",
        mutation="export-compliance claim planted in a leaf SKILL.md",
        signature=r"FAIL content-policy-sweep",
        apply=mutate_content_policy,
    ),
    Control(
        gate="shipped-instructions",
        mutation="a shipped leaf told the reader to cd into a home directory "
                 "only the author has",
        signature=r"FAIL shipped-instructions:.*cd into ~/DevBoxOnly",
        apply=mutate_shipped_instructions,
    ),
]

BY_GATE = {c.gate: c for c in CONTROLS}
