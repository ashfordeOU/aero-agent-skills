#!/usr/bin/env python3
"""Behaviour tests for ops/automation/public-ci-parity.py (VEDA-0035).

The guard exists because an automated sync landed public commits whose CI was
red: the public workflow ran a gate the export cannot satisfy. These tests
prove the guard now catches that shape - and that it does not block a
legitimate publish. Deterministic, offline, stdlib unittest only; a stub
`make` stands in for the real one so no gate is actually run.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(REPO_ROOT, "ops", "automation", "public-ci-parity.py")


def write(path: str, body: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(textwrap.dedent(body))


# A stub make: `attest` fails (the dev-only gate that cannot run on an
# export); every other target passes. Mirrors what the real Makefile does on
# a public tree, without paying for the real battery.
STUB_MAKE = """#!/usr/bin/env bash
if [ "${1:-}" = "attest" ]; then
  echo "ERROR number-snapshot --offline: no snapshot exists; run --live first"
  echo "make: *** [Makefile:118: number-snapshot-offline] Error 1"
  exit 2
fi
exit 0
"""


class ParityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="parity-test-")
        self.bin = os.path.join(self.tmp, "bin")
        os.makedirs(self.bin, exist_ok=True)
        write(os.path.join(self.bin, "make"), STUB_MAKE)
        os.chmod(os.path.join(self.bin, "make"), 0o755)
        self.repo = os.path.join(self.tmp, "export")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def workflow(self, name: str, body: str) -> None:
        write(os.path.join(self.repo, ".github", "workflows", name), body)

    def run_guard(self) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["PATH"] = self.bin + os.pathsep + env.get("PATH", "")
        return subprocess.run(
            [sys.executable, RUNNER, "--repo", self.repo],
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )

    # --- the incident this guard exists for ---------------------------------
    def test_pre_fix_workflow_is_caught(self) -> None:
        """Shape of attest.yml before the fix: `make attest` unconditionally.

        This is the exact step that went red on ec9d037b67 / b1f8c440e9 /
        0fd80ee0. The guard must refuse the publish.
        """
        self.workflow(
            "attest.yml",
            """
            name: attest
            on:
              push:
            jobs:
              attest:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@v4
                  - name: Attestation gates
                    run: make attest
            """,
        )
        proc = self.run_guard()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("number-snapshot", proc.stderr)

    def test_fixed_workflow_passes_on_an_export(self) -> None:
        """Shape of attest.yml at HEAD: the branch resolves to public gates.

        The export has no ops/automation/state, so the else-branch runs and
        the publish is allowed.
        """
        self.workflow(
            "attest.yml",
            """
            name: attest
            on:
              push:
            jobs:
              attest:
                runs-on: ubuntu-latest
                steps:
                  - name: Attestation gates
                    run: |
                      if [ -d ops/automation/state ]; then
                        make attest
                      else
                        make brief-audit
                        make content-policy-sweep
                      fi
            """,
        )
        proc = self.run_guard()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("PASS", proc.stdout)

    # --- skip discipline ----------------------------------------------------
    def test_external_step_is_skipped_not_run(self) -> None:
        self.workflow(
            "attest.yml",
            """
            name: attest
            on: push
            jobs:
              j:
                runs-on: ubuntu-latest
                steps:
                  - name: checkout-ish
                    run: python3 -m pip install --user pyyaml
                  - name: release
                    run: gh release create v9.9.9 --title t
                  - name: gate
                    run: make validate
            """,
        )
        proc = self.run_guard()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("SKIP", proc.stdout)
        self.assertIn("network install", proc.stdout)
        self.assertIn("GitHub API/CLI", proc.stdout)

    def test_gate_hidden_in_a_skipped_step_fails(self) -> None:
        self.workflow(
            "attest.yml",
            """
            name: attest
            on: push
            jobs:
              j:
                runs-on: ubuntu-latest
                steps:
                  - name: release and a secret gate
                    run: |
                      gh release create v9.9.9 --title t
                      make secret-gate
            """,
        )
        proc = self.run_guard()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("never executed", proc.stderr)

    def test_tag_only_workflow_is_not_a_gate(self) -> None:
        self.workflow(
            "attest.yml",
            """
            name: attest
            on: push
            jobs:
              j:
                runs-on: ubuntu-latest
                steps:
                  - name: gate
                    run: make validate
            """,
        )
        self.workflow(
            "publish-npm.yml",
            """
            name: publish-npm
            on:
              push:
                tags:
                  - 'v[0-9]+.[0-9]+.0'
            jobs:
              j:
                runs-on: ubuntu-latest
                steps:
                  - name: publish
                    run: npm publish
            """,
        )
        proc = self.run_guard()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("1 branch-push workflow", proc.stdout)

    # --- fail-closed config handling ---------------------------------------
    def test_missing_workflows_dir_is_a_config_error(self) -> None:
        os.makedirs(self.repo, exist_ok=True)
        proc = self.run_guard()
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)

    def test_no_branch_push_workflow_is_a_config_error(self) -> None:
        self.workflow(
            "publish-npm.yml",
            """
            name: publish-npm
            on:
              push:
                tags: ['v*']
            jobs:
              j:
                runs-on: ubuntu-latest
                steps:
                  - run: npm publish
            """,
        )
        proc = self.run_guard()
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)

    def test_failing_step_aborts(self) -> None:
        self.workflow(
            "attest.yml",
            """
            name: attest
            on: push
            jobs:
              j:
                runs-on: ubuntu-latest
                steps:
                  - name: boom
                    run: |
                      echo "about to fail"
                      exit 7
            """,
        )
        proc = self.run_guard()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("exit 7", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
