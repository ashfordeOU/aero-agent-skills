#!/usr/bin/env python3
"""Prove that every gate in `make validate` and `make attest` can return RED.

A gate nobody has ever seen fail is not a gate, it is a decoration that
reports PASS forever. For each gate this runner:

  1. builds a pruned COPY of the tree that the gate passes on (the baseline),
  2. copies that fixture again and applies ONE mutation the gate must reject,
  3. runs the gate on the mutant and requires a non-zero exit whose output
     matches the signature the mutation planted.

All three conditions must hold. A green baseline without a red mutant proves
nothing; a red mutant without the signature means the gate crashed near the
defect rather than detecting it; a red baseline means the red cannot be
attributed to the mutation at all.

Each control therefore lands in one of THREE states, never two:

  RED-CAPABLE  baseline green, mutant red, red names the planted defect.
  NOT PROVED   the control ran and the gate did not catch it. A finding
               about the GATE: it is blind to the defect it exists for.
  VOID         the control could not run at all - the baseline was already
               red, or the mutation could not be applied. A finding about
               the SUITE: it says nothing whatever about the gate.

Conflating the last two is how this suite once reported "11 of 12 gates
proved red-capable" while one of the twelve had never been exercised: its
fixture was missing a helper the gate needed, so baseline and mutant failed
identically and the run recorded a mere "DID NOT FAIL". Only RED-CAPABLE
counts towards the headline, and VOID is printed on its own line.

Everything runs on temporary copies. The working tree is never modified, and
nothing here touches the network (a stub `gh` is put first on PATH so a gate
that shells out to it fails closed instead of calling GitHub).

Usage:
    python3 tools/negative_controls/run_negative_controls.py [options]

      --only GATE     run one gate's control (repeatable)
      --list          list the gate set and each control's mutation, run nothing
      --verbose       print the captured output of every gate run
      --keep          keep the temporary fixtures and print where they are

Exit code: 0 when every gate proved red-capable, 1 otherwise.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# No .pyc next to these modules: a __pycache__ entry records the absolute
# source path, and absolute paths must not land in a committed tree.
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import controls as controls_mod  # noqa: E402
import fixture as fixture_mod  # noqa: E402

REPO = HERE.parent.parent

GATE_TIMEOUT_S = 1800
VOID_EXCERPT_LINES = 6

RED_CAPABLE = "RED-CAPABLE"
NOT_PROVED = "NOT PROVED"
VOID = "VOID"

# Gates whose red-capability cannot be shown by mutating the fixture, and the
# proof that is run in its place. NOT a waiver: each entry is executed on
# every run, its proof is named in the output, and a failure reports
# NOT PROVED exactly like a failed mutation.
#
# The bar for being listed here is that a fixture baseline can never be
# green, so every mutation would be VOID. Convenience is not a reason.
SELFTEST_PROOFS = {
    "role-bindings": {
        "why": (
            "it checks the WHOLE corpus against a contract naming hundreds "
            "of bound leaves. The fixture prunes the tree to four, so the "
            "baseline is red before any mutation and every mutation is "
            "VOID -- and a VOID control says nothing about the gate. Its "
            "own suite builds throwaway corpora and retires a bound leaf "
            "in one of them."
        ),
        "cmd": ["python3", "scripts/test_role_bindings_contract.py"],
        "source": "scripts/test_role_bindings_contract.py",
        "must_contain": [
            "def test_a_retired_bound_leaf_is_caught(",
            "def test_an_unbound_leaf_may_be_retired_freely(",
            "def test_a_missing_contract_is_a_failure_not_a_skip(",
        ],
    },
    "gated-set-check": {
        "why": (
            "it grades count claims in the real documents. The fixture "
            "prunes the tree and carries a four-leaf corpus, so every claim "
            "in it is already wrong before any mutation is applied."
        ),
        "cmd": ["python3", "ops/automation/test_gated_set_check.py"],
        "source": "ops/automation/test_gated_set_check.py",
        "must_contain": [
            "def test_a_wrong_gated_count_is_rejected(",
            "def test_a_wrong_map_total_is_rejected(",
            "def test_an_unrelated_number_is_left_alone(",
        ],
    },
    "stale-number-guard": {
        "why": (
            "same position: it reads the live documents, which the fixture "
            "does not reproduce. Its suite plants a retired count in a "
            "throwaway root and runs the real script over it."
        ),
        "cmd": ["python3", "ops/automation/test_stale_number_guard.py"],
        "source": "ops/automation/test_stale_number_guard.py",
        "must_contain": [
            "def test_a_retired_skill_count_is_caught(",
            "def test_a_current_count_is_not_a_finding(",
            "def test_the_exemption_does_not_leak_to_the_next_line(",
        ],
    },
    "hermeticity": {
        "why": (
            "it scans the REAL generated artefacts. The fixture prunes the "
            "tree to four leaves, so its regenerated artefacts describe a "
            "corpus that does not exist and any mutation is indistinguishable "
            "from the pruning itself."
        ),
        "cmd": ["python3", "tools/determinism/test_hermeticity.py"],
        "source": "tools/determinism/test_hermeticity.py",
        "must_contain": [
            "def test_every_rule_has_a_case_that_fires(",
            "def test_json_object_is_not_a_container_repr(",
            "def test_single_quoted_repr_is_still_caught(",
        ],
    },
    "evidence-contract": {
        "why": (
            "the contract is the record format itself, not the tree. A "
            "fixture mutation would have to corrupt a stored record, which "
            "is what the suite's own negative cases already do."
        ),
        "cmd": ["python3", "-m", "unittest", "-q",
                "tools.evidence.tests.test_record",
                "tools.evidence.tests.test_regrade",
                "tools.evidence.tests.test_frontmatter"],
        "source": "tools/evidence/tests/test_record.py",
        "must_contain": [
            "def test_a_float_is_refused(",
            "def test_non_finite_is_refused(",
            "def test_key_order_does_not_change_the_digest(",
        ],
    },
    "export-bundle": {
        "why": (
            "it grades the exported case set and its tokenizer, which the "
            "fixture does not build."
        ),
        "cmd": ["python3", "tools/export/test_export_bundle.py"],
        "source": "tools/export/test_export_bundle.py",
        "must_contain": [
            "def test_lowercases_and_keeps_internal_hyphens(",
            "def test_drops_stop_words(",
        ],
    },
    "figure-audit": {
        "why": (
            "whole-corpus figure consistency. The fixture prunes the tree to "
            "four leaves; every figure in docs/ describes the real corpus, so "
            "a freshly built fixture reports 62 violations before any "
            "mutation is applied and no mutation could be distinguished."
        ),
        "cmd": ["python3", "tools/figure_audit.py", "--selftest"],
        "source": "tools/figure_audit.py",
        # Named so that deleting or renaming the proof breaks this suite
        # instead of quietly removing the evidence.
        "must_contain": [
            "def test_stale_count_fails(",
            "def test_unregistered_growth_rate_fails(",
            "def test_registered_growth_rate_value_drift_fails(",
        ],
    },
    "release-machinery": {
        "why": (
            "it runs the ops/automation suites rather than reading the "
            "corpus. The fixture prunes the tree to four leaves, so those "
            "suites fail there for reasons that have nothing to do with the "
            "mutation and every mutation would be VOID. Its own suite proves "
            "the verdict directly instead, on synthesized sets of passing "
            "and failing suites."
        ),
        "cmd": ["python3", "ops/automation/test_release_machinery.py"],
        "source": "ops/automation/test_release_machinery.py",
        "must_contain": [
            "def test_a_failing_suite_turns_the_gate_red(",
            "def test_an_empty_directory_is_refused_not_passed(",
            "def test_a_shrunken_set_is_refused(",
        ],
    },
}


def run_selftest_proof(repo, gate, spec):
    """Run a gate's own detector tests. Returns (verdict, detail)."""
    src = repo / spec["source"]
    if not src.is_file():
        return NOT_PROVED, "%s is missing" % spec["source"]
    text = src.read_text(encoding="utf-8", errors="replace")
    absent = [m for m in spec["must_contain"] if m not in text]
    if absent:
        return NOT_PROVED, ("the named proof case(s) no longer exist in %s: %s"
                            % (spec["source"], ", ".join(absent)))
    try:
        r = subprocess.run(spec["cmd"], cwd=str(repo), capture_output=True,
                           text=True, timeout=GATE_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as exc:
        return NOT_PROVED, "could not run %s: %s" % (" ".join(spec["cmd"]), exc)
    if r.returncode != 0:
        tail = (r.stdout + r.stderr).strip().splitlines()[-4:]
        return NOT_PROVED, ("%s exited %d: %s"
                            % (" ".join(spec["cmd"]), r.returncode,
                               " | ".join(tail)))
    return RED_CAPABLE, ("%d detector case(s) asserted, including %s"
                         % (len(spec["must_contain"]),
                            spec["must_contain"][0].split("(")[0]
                            .replace("def ", "")))


# ---------------------------------------------------------------------------
# gate set, read from the files rather than assumed
# ---------------------------------------------------------------------------


def makefile_prerequisites(makefile: Path, target: str) -> list[str]:
    text = makefile.read_text(encoding="utf-8")
    text = re.sub(r"\\\n", " ", text)  # join line continuations
    m = re.search(r"^%s:[ \t]*(.*)$" % re.escape(target), text, re.M)
    if not m:
        raise SystemExit("cannot find target '%s:' in %s" % (target, makefile))
    return m.group(1).split()


def discover_gates(repo: Path) -> tuple[list[str], list[str]]:
    mk = repo / "Makefile"
    return (
        makefile_prerequisites(mk, "validate"),
        makefile_prerequisites(mk, "attest"),
    )


# ---------------------------------------------------------------------------
# running a gate
# ---------------------------------------------------------------------------


def offline_env(bindir: Path) -> dict:
    """Environment for a gate run: no network, no inherited publish token."""
    env = dict(os.environ)
    env.pop("GH_TOKEN", None)
    env.pop("GITHUB_TOKEN", None)
    env.pop("NUMBERS_YAML", None)
    env.pop("SNAPSHOT_STATE_DIR", None)
    env["PATH"] = "%s:%s" % (bindir, env.get("PATH", ""))
    return env


def make_offline_bin(root: Path) -> Path:
    """A stub `gh` so no control can reach GitHub.

    scripts/release-manager.py resolves `gh` at import and shells out to it
    for a REPORT-ONLY parity note. The stub keeps that path deterministic and
    offline; the blocking half of the gate never consults it.
    """
    bindir = root / "offline-bin"
    bindir.mkdir(parents=True, exist_ok=True)
    stub = bindir / "gh"
    stub.write_text(
        "#!/bin/sh\n"
        "echo 'negative-control: network disabled for this run' >&2\n"
        "exit 1\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return bindir


def _wrap_note(note: str, width: int = 84) -> list[str]:
    if not note:
        return []
    import textwrap

    return textwrap.wrap(note, width=width)


def run_gate(tree: Path, gate: str, env: dict) -> tuple[int, str, float]:
    """`make <gate>` in `tree`, capturing BOTH streams (unittest prints on stderr)."""
    t0 = time.time()
    proc = subprocess.run(
        ["make", gate],
        cwd=str(tree),
        env=env,
        capture_output=True,
        text=True,
        timeout=GATE_TIMEOUT_S,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out, time.time() - t0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def _run_control(root, base, gate, n, label, control, env, args,
                 rc_base, out_base, secs_base):
    """Run ONE control against a fresh mutant. Returns its verdict."""
    mutant = root / ("mutant-%s-%d" % (gate, n))
    shutil.copytree(base, mutant, symlinks=True)
    mutation_error = None
    rc_mut, out_mut, secs_mut = None, "", 0.0
    try:
        control.apply(mutant)
    except (controls_mod.MutationError, fixture_mod.FixtureError) as exc:
        mutation_error = str(exc)
    else:
        rc_mut, out_mut, secs_mut = run_gate(mutant, gate, env)

    signature_ok = bool(rc_mut and re.search(control.signature, out_mut))
    # Order matters. A control that never ran is VOID and says
    # nothing about the gate; only a control that DID run can
    # convict the gate of being blind.
    if rc_base != 0:
        verdict, reason = VOID, (
            "baseline is already red (exit %d)%s - the control never ran, "
            "and this is a finding about the fixture, not the gate"
            % (
                rc_base,
                "" if rc_mut is None else " and the mutant exited %d for the same reason" % rc_mut,
            )
        )
    elif mutation_error is not None:
        verdict, reason = VOID, (
            "mutation could not be applied: %s - the control never ran" % mutation_error
        )
    elif rc_mut == 0:
        verdict, reason = NOT_PROVED, "baseline green, mutant exited 0: the gate is blind to this defect"
    elif not signature_ok:
        verdict, reason = NOT_PROVED, (
            "mutant exited %d but never reported the planted defect (expected /%s/): "
            "the gate went red near the defect, not at it" % (rc_mut, control.signature)
        )
    else:
        verdict, reason = RED_CAPABLE, ""

    if verdict == RED_CAPABLE:
        print("GATE %s: %s (mutation: %s)" % (label, verdict, control.mutation))
    else:
        print("GATE %s: %s (mutation: %s; %s)" % (label, verdict, control.mutation, reason))
        if verdict == VOID and rc_base != 0:
            # A VOID is a repair job, so print enough of the
            # baseline to start it without re-running with --verbose.
            failing = [
                ln for ln in out_base.strip().splitlines()
                if re.search(r"(FAIL|Error|error|Traceback|No such file)", ln)
            ] or out_base.strip().splitlines()
            for line in failing[:VOID_EXCERPT_LINES]:
                print("    baseline | %s" % line.strip()[:200])
            if len(failing) > VOID_EXCERPT_LINES:
                print("    baseline | ... %d more line(s), see --verbose"
                      % (len(failing) - VOID_EXCERPT_LINES))
        # A second probe only means something once the baseline is
        # green; under a VOID control it would grade the same broken
        # fixture twice.
        if verdict == NOT_PROVED and control.diagnosis is not None:
            probe = root / ("diagnosis-%s-%d" % (gate, n))
            shutil.copytree(base, probe, symlinks=True)
            try:
                control.diagnosis.apply(probe)
            except (controls_mod.MutationError, fixture_mod.FixtureError) as exc:
                print("    diagnosis could not be applied: %s" % exc)
            else:
                rc_d, _out_d, _s = run_gate(probe, gate, env)
                print(
                    "    diagnosis: %s -> gate exit %d (%s)"
                    % (
                        control.diagnosis.description,
                        rc_d,
                        "RED" if rc_d else "still green",
                    )
                )
                print("    %s" % control.diagnosis.expectation)
        for line in _wrap_note(control.note):
            print("    %s" % line)

    if args.verbose:
        print("    baseline: exit %d in %.1fs" % (rc_base, secs_base))
        for line in out_base.strip().splitlines():
            print("      | %s" % line)
        if mutation_error is None:
            print("    mutant:   exit %d in %.1fs" % (rc_mut, secs_mut))
            for line in out_mut.strip().splitlines():
                print("      | %s" % line)
        print()
    return verdict


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", action="append", default=[], metavar="GATE")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args(argv)

    validate_gates, attest_gates = discover_gates(REPO)
    gates = validate_gates + attest_gates

    print("gate set read from the Makefile (not from any brief):")
    print("  make validate -> %d gates: %s" % (len(validate_gates), " ".join(validate_gates)))
    print("  make attest   -> %d gates: %s" % (len(attest_gates), " ".join(attest_gates)))

    missing = [g for g in gates
               if g not in controls_mod.BY_GATE and g not in SELFTEST_PROOFS]
    by_selftest = [g for g in gates
                   if g not in controls_mod.BY_GATE and g in SELFTEST_PROOFS]
    orphan = [c.gate for c in controls_mod.CONTROLS if c.gate not in gates]
    for g in missing:
        print("  ! no negative control defined for gate '%s'" % g)
    for g in by_selftest:
        print("  · gate '%s' is proven by its own detector tests, not by a "
              "fixture mutation: %s" % (g, SELFTEST_PROOFS[g]["why"]))
    for g in orphan:
        print("  ! control '%s' is not a gate of validate/attest any more" % g)

    if args.list:
        print()
        for gate in gates:
            cs = controls_mod.BY_GATE.get(gate) or []
            if not cs:
                print("%-24s %s" % (gate, "(no control)"))
            for c in cs:
                print("%-24s %s" % (gate, c.mutation))
        return 1 if (missing or orphan) else 0

    # A gate with no control is reported, never crashed on: this repo grows
    # gates faster than it grows proofs that they work.
    selected = [
        g for g in gates
        if g in controls_mod.BY_GATE and (not args.only or g in args.only)
    ]
    unknown = [g for g in args.only if g not in gates]
    if unknown:
        print("unknown gate(s): %s" % ", ".join(unknown), file=sys.stderr)
        return 1

    root = Path(tempfile.mkdtemp(prefix="aero-negative-controls-"))
    bindir = make_offline_bin(root)
    env = offline_env(bindir)
    results = []
    try:
        base = root / "base"
        t0 = time.time()
        # The gate set is handed to the builder so every gate's dependency
        # closure is audited against the finished copy. A gate whose helper
        # the fixture does not carry aborts the build here, loudly, instead
        # of producing a red baseline that looks like a gate finding.
        try:
            summary = fixture_mod.build(REPO, base, gates=selected)
        except fixture_mod.FixtureError as exc:
            print()
            print("FIXTURE UNUSABLE: %s" % exc, file=sys.stderr)
            print(
                "every control would be VOID against this fixture; nothing was run",
                file=sys.stderr,
            )
            return 1
        print()
        print(
            "fixture: %d leaves (%s), %d corpus tasks, release band %s, "
            "%d gate sources hash-matched against the tree, built in %.1fs"
            % (
                len(summary["leaves"]),
                ", ".join(summary["leaves"]),
                summary["corpus_tasks"],
                summary["band"],
                summary["gate_sources_verified"],
                time.time() - t0,
            )
        )
        audited = summary["dependencies_audited"]
        print(
            "         %d declared gate dependencies copied (%s); "
            "%d statically-reachable paths audited across %d gates, none missing"
            % (
                len(summary["declared_dependencies"]),
                ", ".join(summary["declared_dependencies"]) or "none",
                sum(audited.values()),
                len(audited),
            )
        )

        baseline_tree = root / "baseline"
        shutil.copytree(base, baseline_tree, symlinks=True)

        print()
        for gate in selected:
            # A gate may carry several controls, one per defect class it
            # claims to catch. Each runs on its own mutant and is reported
            # on its own line; the baseline is shared, because it is the
            # same tree. (Until 2026-09-22 this was a dict keyed by gate, so
            # a second control silently replaced the first and never ran.)
            gate_controls = controls_mod.BY_GATE[gate]
            rc_base, out_base, secs_base = run_gate(baseline_tree, gate, env)
            for n, control in enumerate(gate_controls, 1):
                label = gate if len(gate_controls) == 1 else "%s #%d" % (gate, n)
                results.append((label, gate, _run_control(
                    root, base, gate, n, label, control, env, args,
                    rc_base, out_base, secs_base)))
    finally:
        if args.keep:
            print("\nfixtures kept at %s" % root)
        else:
            shutil.rmtree(root, ignore_errors=True)

    for gate in by_selftest:
        verdict, detail = run_selftest_proof(REPO, gate, SELFTEST_PROOFS[gate])
        print("GATE %s: %s (self-test: %s)" % (gate, verdict, detail))
        results.append((gate, gate, verdict))

    proved = [lbl for lbl, _g, v in results if v == RED_CAPABLE]
    not_proved = [lbl for lbl, _g, v in results if v == NOT_PROVED]
    void = [lbl for lbl, _g, v in results if v == VOID]
    gates_run = sorted({g for _lbl, g, _v in results})
    gates_proved = sorted({g for _lbl, g, _v in results}
                          - {g for _lbl, g, v in results if v != RED_CAPABLE})
    print()
    print(
        "%d of %d gate(s) with a control proved RED-CAPABLE "
        "(%d of %d control(s))"
        % (len(gates_proved), len(gates_run), len(proved), len(results))
    )
    if not_proved:
        print(
            "NOT PROVED (control ran, gate did not catch it): %s"
            % ", ".join(not_proved)
        )
    if void:
        print(
            "VOID (control could not run; says nothing about the gate): %s"
            % ", ".join(void)
        )
    if missing:
        print("NO CONTROL (gate in the Makefile, no control defined): %s" % ", ".join(missing))
    if orphan:
        print("ORPHAN CONTROL (no such gate any more): %s" % ", ".join(orphan))
    return 0 if (not not_proved and not void and not missing and not orphan) else 1


if __name__ == "__main__":
    sys.exit(main())
