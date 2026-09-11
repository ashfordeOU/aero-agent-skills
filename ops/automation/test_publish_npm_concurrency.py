#!/usr/bin/env python3
"""Guard against the publish-npm double-trigger race (2026-09-11).

Two triggers on this workflow fire for ONE milestone: `push: tags: v*.*.0`
and `release: types: [published]`. Both runs pass the "Skip if this version
is already on npm" guard *before* either publishes (check-then-act), so the
loser dies with npm E403 "You cannot publish over the previously published
versions" and the public repo gains a red run — the exact violation of the
founder's "no failed CI in the public repo" directive.

Live evidence: run 34602128067 (push, red) vs its sibling 34602128683
(release, green) — BOTH logged "npm does not yet have 1.7.0 — will publish"
at 13:03:26-27Z; the sibling published 1.7.0 at 13:03:32.553Z and the push
run took E403 at 13:03:33.614Z.

The fix is a `concurrency` group that QUEUES the second run instead of
racing it, so the guard sees the version on the registry and skips as the
designed no-op success. This test asserts the properties that make that
true, so a later edit cannot silently drop the serialisation and reopen the
race. It also pins that both triggers and the guard are still present — the
serialisation only works while the guard is the only path to publish.

Run:  python3 ops/automation/test_publish_npm_concurrency.py [workflow.yml]
The pre-fix file (git show HEAD~:.github/workflows/publish-npm.yml) fails
4 of these cases; the landed file passes all of them (fail-first).
"""
from __future__ import annotations

import pathlib
import sys
import unittest

import yaml

DEFAULT_WF = (pathlib.Path(__file__).resolve().parents[2]
              / ".github/workflows/publish-npm.yml")


def load(path: str | None):
    """Parse the workflow. PyYAML (1.1) reads the `on:` key as boolean True."""
    data = yaml.safe_load(pathlib.Path(path or DEFAULT_WF).read_text())
    assert isinstance(data, dict), "workflow is not a mapping"
    return data


def triggers(data):
    on = data.get("on", data.get(True))
    assert on is not None, "no triggers block"
    return on


def step_by_name(data, name: str):
    for step in data["jobs"]["publish-npm"]["steps"]:
        if step.get("name") == name:
            return step
    raise AssertionError(f"step not found: {name}")


class TestPublishNpmConcurrency(unittest.TestCase):
    path: str | None = None

    def test_both_triggers_still_present(self):
        """The race exists because BOTH triggers fire; neither may be dropped."""
        on = triggers(load(self.path))
        self.assertIn("push", on, "tag-push trigger lost")
        self.assertIn("tags", on["push"], "tag filter lost")
        self.assertIn("release", on, "release trigger lost")

    def test_concurrency_group_serialises_publishes(self):
        """THE FIX: one group, no cancellation, so run 2 waits for run 1."""
        conc = load(self.path).get("concurrency")
        if not isinstance(conc, dict):
            self.fail("no concurrency block: the two triggers can race again")
        self.assertEqual(conc.get("group"), "publish-npm")
        self.assertFalse(
            conc.get("cancel-in-progress"),
            "cancel-in-progress must stay false: cancelling the second run "
            "hides it instead of letting the guard prove it a no-op")

    def test_skip_guard_step_present(self):
        """Serialisation is only safe while the guard can skip the loser."""
        step = step_by_name(load(self.path), "Skip if this version is already on npm")
        self.assertIn("npm view", step["run"])
        self.assertIn("already=true", step["run"])

    def test_publish_is_gated_on_the_guard(self):
        step = step_by_name(load(self.path), "Publish to npm")
        self.assertEqual(step.get("if"), "steps.npmcheck.outputs.already != 'true'")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        TestPublishNpmConcurrency.path = sys.argv[1]
    unittest.main(argv=[sys.argv[0], "-v"], exit=False)
