#!/usr/bin/env python3
"""The role-bindings gate goes red on each defect it claims to catch.

This gate cannot be proved by the negative-control fixture. The fixture
prunes the corpus to four leaves, and the contract names 524 -- so the
baseline is red before any mutation, every mutation is VOID, and a VOID
control says nothing about the gate. Same position as figure-audit and
gated-set-check, and handled the same way: the detector is driven directly,
over throwaway trees built here.

Each case plants ONE defect and asserts the gate names it. A gate that goes
red for an unrelated reason proves it runs, not that it works.

Offline, stdlib only.
"""

import glob
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import role_bindings_contract as G   # noqa: E402


class Harness(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="aero-rbc-")
        self.saved = (G.ROOT, G.CONTRACT)
        G.ROOT = os.path.join(self.work, "corpus")
        G.CONTRACT = os.path.join(G.ROOT, "ops", "contracts",
                                  "role-bindings.json")
        os.makedirs(os.path.join(G.ROOT, "ops", "contracts"))
        self.out = io.StringIO()

    def tearDown(self):
        G.ROOT, G.CONTRACT = self.saved
        shutil.rmtree(self.work, ignore_errors=True)

    def leaves(self, *slugs):
        for slug in slugs:
            d = os.path.join(G.ROOT, "skills", *slug.split("/"))
            os.makedirs(d, exist_ok=True)
            io.open(os.path.join(d, "SKILL.md"), "w",
                    encoding="utf-8").write("# %s\n" % slug)

    def roles_corpus(self, mapping):
        """A throwaway roles corpus with the given role -> slugs mapping."""
        base = os.path.join(self.work, "roles-corpus", "roles")
        for role, slugs in mapping.items():
            d = os.path.join(base, role)
            os.makedirs(d, exist_ok=True)
            body = "---\ntype: role\nname: %s\nskills_bound:\n" % role
            for s in slugs:
                body += "  - %s\n" % s
            body += "---\n\n# %s\n" % role
            io.open(os.path.join(d, "ROLE.md"), "w",
                    encoding="utf-8").write(body)
        return os.path.dirname(base)

    def capture(self, fn, *a):
        err, sys.stderr = sys.stderr, self.out
        out, sys.stdout = sys.stdout, self.out
        try:
            return fn(*a)
        finally:
            sys.stderr, sys.stdout = err, out

    def said(self):
        return self.out.getvalue()


class TheGateCatchesWhatItClaims(Harness):
    def build(self):
        self.leaves("fam/pack/one", "fam/pack/two", "fam/pack/three")
        roles = self.roles_corpus({"alpha": ["fam/pack/one", "fam/pack/two"],
                                   "beta": ["fam/pack/two"]})
        self.assertEqual(self.capture(G.refresh, roles), 0, self.said())

    def test_baseline_is_green(self):
        self.build()
        self.assertEqual(self.capture(G.gate), 0, self.said())
        self.assertIn("PASS role-bindings", self.said())
        self.assertIn("2 role(s), 3 binding(s)", self.said())

    def test_a_retired_bound_leaf_is_caught(self):
        """The live risk: this corpus grows hourly and leaves get renamed."""
        self.build()
        shutil.rmtree(os.path.join(G.ROOT, "skills", "fam", "pack", "two"))
        self.assertEqual(self.capture(G.gate), 1)
        self.assertIn("no longer exists in this corpus", self.said())
        self.assertIn("fam/pack/two", self.said())

    def test_the_finding_names_the_role_not_just_the_leaf(self):
        self.build()
        shutil.rmtree(os.path.join(G.ROOT, "skills", "fam", "pack", "one"))
        self.capture(G.gate)
        self.assertIn("role alpha binds fam/pack/one", self.said())

    def test_an_unbound_leaf_may_be_retired_freely(self):
        """Only BOUND leaves matter; the corpus must stay free to change."""
        self.build()
        shutil.rmtree(os.path.join(G.ROOT, "skills", "fam", "pack", "three"))
        self.assertEqual(self.capture(G.gate), 0, self.said())

    def test_adding_leaves_is_not_a_qualification_event(self):
        self.build()
        self.leaves("fam/pack/four", "other/pack/five")
        self.assertEqual(self.capture(G.gate), 0, self.said())

    def test_a_missing_contract_is_a_failure_not_a_skip(self):
        self.build()
        os.remove(G.CONTRACT)
        self.assertEqual(self.capture(G.gate), 1)
        self.assertIn("is missing", self.said())

    def test_a_hand_edited_contract_is_caught(self):
        self.build()
        doc = json.load(io.open(G.CONTRACT, encoding="utf-8"))
        doc["roles"]["alpha"] = ["fam/pack/one"]
        json.dump(doc, io.open(G.CONTRACT, "w", encoding="utf-8"))
        self.assertEqual(self.capture(G.gate), 1)
        self.assertIn("edited by hand", self.said())

    def test_an_empty_contract_is_refused(self):
        self.build()
        doc = json.load(io.open(G.CONTRACT, encoding="utf-8"))
        doc["roles"] = {}
        doc["bindings_digest"] = G.digest({})
        json.dump(doc, io.open(G.CONTRACT, "w", encoding="utf-8"))
        self.assertEqual(self.capture(G.gate), 1)
        self.assertIn("names no roles", self.said())

    def test_an_empty_tree_is_a_failure_not_a_pass(self):
        self.build()
        shutil.rmtree(os.path.join(G.ROOT, "skills"))
        os.makedirs(os.path.join(G.ROOT, "skills"))
        self.assertEqual(self.capture(G.gate), 1)
        self.assertIn("0 leaves found", self.said())

    def test_a_contract_with_the_wrong_context(self):
        self.build()
        doc = json.load(io.open(G.CONTRACT, encoding="utf-8"))
        doc["context"] = "some-other-document"
        json.dump(doc, io.open(G.CONTRACT, "w", encoding="utf-8"))
        self.assertEqual(self.capture(G.gate), 1)
        self.assertIn("context", self.said())

    def test_the_verdict_states_its_denominator(self):
        self.build()
        self.capture(G.gate)
        self.assertIn("against 3 leaf/leaves in this tree", self.said())


class RefusingABadContract(Harness):
    def test_a_roles_corpus_with_no_bindings(self):
        self.leaves("fam/pack/one")
        roles = self.roles_corpus({})
        os.makedirs(os.path.join(roles, "roles"), exist_ok=True)
        self.assertEqual(self.capture(G.refresh, roles), 1)
        self.assertIn("asserts nothing", self.said())

    def test_a_malformed_binding_is_reported_not_dropped(self):
        """A typo that vanishes makes a role claim fewer leaves than it does."""
        self.leaves("fam/pack/one")
        roles = self.roles_corpus({"alpha": ["fam/pack/one", "not-a-slug"]})
        self.assertEqual(self.capture(G.refresh, roles), 1)
        self.assertIn("not a family/pack/leaf slug", self.said())


def _leaf_count():
    return len(glob.glob(os.path.join(G.ROOT, "skills", "*", "*", "*",
                                      "SKILL.md")))


def _tree_is_the_corpus():
    """(ok, why_not) -- is this checkout the tree the contract describes?

    The two cases below are INTEGRATION assertions: the shipped contract
    against the shipped tree. Everything above them builds its own throwaway
    corpora and is true anywhere.

    They must not run in a pruned tree. `gate3-pytest-contract` collects
    every `scripts/test_*.py` in whatever tree it is pointed at, and the
    negative-control fixture prunes the corpus to four leaves -- so these two
    failed there, the fixture BASELINE went red, and a red baseline makes
    every mutation VOID. That turned the whole battery red, which failed
    public-ci-parity, which silently stopped the public publish for hours
    while every leaf-count check reported "current".

    The skip is narrow on purpose. It fires only when this tree demonstrably
    cannot satisfy the contract, and `make role-bindings` still fails hard on
    a missing contract in a tree that should have one -- so a skip here can
    never be the only thing standing between a deleted contract and a green
    build.
    """
    if not os.path.isfile(G.CONTRACT):
        return False, ("this tree ships no ops/contracts/role-bindings.json, "
                       "so there is nothing to assert against. `make "
                       "role-bindings` fails hard on that in a tree that "
                       "should have one.")
    doc = G.load()
    bound = {slug for slugs in doc["roles"].values() for slug in slugs}
    present = _leaf_count()
    if present < len(bound):
        return False, ("this tree holds %d leaf/leaves and the contract "
                       "names %d distinct bound one(s), so it is not the "
                       "corpus the contract was generated from -- a pruned "
                       "fixture, not a regression." % (present, len(bound)))
    return True, ""


class TheShippedContract(unittest.TestCase):
    """The real one, against the real tree, once."""

    def setUp(self):
        ok, why_not = _tree_is_the_corpus()
        if not ok:
            self.skipTest(why_not)

    def test_it_loads_and_is_self_consistent(self):
        doc = G.load()
        self.assertIsNotNone(doc, "the contract is missing")
        self.assertEqual(G.digest(doc["roles"]), doc["bindings_digest"])
        self.assertEqual(doc["binding_count"],
                         sum(len(v) for v in doc["roles"].values()))

    def test_every_binding_resolves_in_this_tree(self):
        self.assertEqual(G.gate(), 0)


class TheCorpusGuard(unittest.TestCase):
    """The skip condition itself, because a skip that fires everywhere is a
    deleted test wearing a hat."""

    def test_this_tree_is_the_corpus(self):
        # In the dev repo and in CI this must be TRUE: if the guard starts
        # firing here, the two integration cases above have stopped running
        # and nobody would otherwise notice.
        if not os.path.isfile(G.CONTRACT):
            self.skipTest("no shipped contract in this tree")
        ok, why_not = _tree_is_the_corpus()
        self.assertTrue(ok, "the guard fired in a tree that ships the "
                            "contract: %s" % why_not)

    def test_a_pruned_tree_is_recognised(self):
        self.assertFalse(_tree_is_the_corpus.__doc__ is None)
        doc = G.load()
        if doc is None:
            self.skipTest("no shipped contract in this tree")
        bound = {s for v in doc["roles"].values() for s in v}
        self.assertGreater(len(bound), 4,
                           "the contract binds so few leaves that the "
                           "four-leaf fixture would satisfy it, and this "
                           "guard would stop protecting anything")


if __name__ == "__main__":
    unittest.main(verbosity=2)
