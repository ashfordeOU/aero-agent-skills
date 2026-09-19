#!/usr/bin/env python3
"""Regrade: flips, holds, the three non-answers, and corpus isolation."""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fixture  # noqa: E402
from evidence import canonical, checkers, record, regrade, schema  # noqa: E402

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def verdicts(rec):
    return {g["gate"]: g["outcome"]["verdict"] for g in rec["body"]["gates"]}


class RegradeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="aero-evidence-regrade-")
        cls.refs = fixture.build_repo(cls.root)
        cls.parent = record.build(cls.root, cls.refs[0], issuer="test-suite", at=1_700_000_000)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    def test_the_parent_passes_before_anything_changes(self):
        self.assertEqual(self.parent["body"]["verdict"]["overall"], "PASS")

    def test_an_unchanged_checker_set_holds_every_gate(self):
        same = checkers.build_set(label="unchanged")
        successor, entry = regrade.regrade(self.parent, same)
        self.assertEqual(entry["verdict_after"], "PASS")
        self.assertFalse(entry["verdict_changed"])
        self.assertEqual([g["change"] for g in entry["gates"]], ["held"] * len(entry["gates"]))
        self.assertEqual(entry["anomalies"], [])

    def test_a_raised_threshold_flips_one_gate_and_leaves_the_rest(self):
        words = self.parent["body"]["observations"]["desc-lint"]["word_count"]
        tightened = checkers.build_set(
            label="tightened",
            overrides={"checkers": {"desc-lint": {"params": {"min_words": words + 1}}}},
        )
        successor, entry = regrade.regrade(self.parent, tightened)
        after = verdicts(successor)
        self.assertEqual(after["desc-lint"], "FAIL")
        self.assertEqual(entry["verdict_before"], "PASS")
        self.assertEqual(entry["verdict_after"], "FAIL")
        flipped = [g["gate"] for g in entry["gates"] if g["change"] == "flipped"]
        self.assertEqual(flipped, ["desc-lint"])
        held = [g["gate"] for g in entry["gates"] if g["change"] == "held"]
        self.assertIn("contract-test", held)
        self.assertIn("portability", held)

    def test_a_relaxed_threshold_flips_a_failure_back(self):
        words = self.parent["body"]["observations"]["desc-lint"]["word_count"]
        strict = checkers.build_set(
            label="strict", overrides={"checkers": {"desc-lint": {"params": {"min_words": words + 1}}}}
        )
        failed, _ = regrade.regrade(self.parent, strict)
        self.assertEqual(failed["body"]["verdict"]["overall"], "FAIL")
        restored, entry = regrade.regrade(failed, checkers.build_set(label="restored"))
        self.assertEqual(restored["body"]["verdict"]["overall"], "PASS")
        self.assertEqual(entry["verdict_before"], "FAIL")

    def test_the_parent_is_not_mutated_by_a_regrade(self):
        before = canonical.digest(self.parent)
        regrade.regrade(
            self.parent,
            checkers.build_set(
                label="tightened", overrides={"checkers": {"desc-lint": {"params": {"min_words": 999}}}}
            ),
        )
        self.assertEqual(canonical.digest(self.parent), before)

    def test_the_successor_names_its_parent_by_digest(self):
        successor, _ = regrade.regrade(self.parent, checkers.build_set(label="same"))
        derivation = successor["body"]["derivation"]
        self.assertEqual(derivation["kind"], "regrade")
        self.assertEqual(derivation["parent"]["record_id"], self.parent["record_id"])
        self.assertEqual(
            derivation["parent"]["body_digest"], self.parent["seal"]["body_digest"]
        )
        self.assertFalse(derivation["corpus_re_executed"])
        self.assertEqual(schema.validate(successor), [])

    def test_a_retired_checker_is_withdrawn_not_silently_dropped(self):
        retired = checkers.build_set(
            label="retired", overrides={"checkers": {"stdlib-only": {"enabled": False}}}
        )
        successor, entry = regrade.regrade(self.parent, retired)
        self.assertEqual(verdicts(successor)["stdlib-only"], "WITHDRAWN")
        self.assertEqual(successor["body"]["verdict"]["overall"], "PASS")
        withdrawn = [g for g in entry["gates"] if g["change"] == "withdrawn"]
        self.assertEqual([g["gate"] for g in withdrawn], ["stdlib-only"])
        prior = [g for g in successor["body"]["gates"] if g["gate"] == "stdlib-only"][0]
        self.assertEqual(prior["prior"]["verdict"], "PASS")

    def test_a_rule_needing_evidence_nobody_collected_is_indeterminate(self):
        added = checkers.build_set(
            label="new-rule", overrides={"checkers": {"references-present": {"enabled": True}}}
        )
        successor, entry = regrade.regrade(self.parent, added)
        self.assertEqual(verdicts(successor)["references-present"], "INDETERMINATE")
        self.assertEqual(successor["body"]["verdict"]["overall"], "INDETERMINATE")
        self.assertIn("references-present", entry["reobservation_required"])
        gate = [g for g in successor["body"]["gates"] if g["gate"] == "references-present"][0]
        self.assertEqual(gate["outcome"]["needs"]["fields"], ["has_references_dir"])

    def test_a_marker_added_after_issue_is_indeterminate_not_a_pass(self):
        markers = list(checkers.MARKER_IDS) + ["export-control-banner"]
        added = checkers.build_set(
            label="new-marker",
            overrides={"checkers": {"no-verbatim": {"params": {"markers_enforced": markers}}}},
        )
        successor, entry = regrade.regrade(self.parent, added)
        self.assertEqual(verdicts(successor)["no-verbatim"], "INDETERMINATE")
        self.assertIn("no-verbatim", entry["reobservation_required"])

    def test_a_changed_measurement_vocabulary_is_indeterminate(self):
        changed = checkers.build_set(
            label="new-vocabulary",
            overrides={
                "checkers": {"desc-lint": {"params": {"action_verb_vocabulary_version": "2.0.0"}}}
            },
        )
        successor, _ = regrade.regrade(self.parent, changed)
        self.assertEqual(verdicts(successor)["desc-lint"], "INDETERMINATE")

    def test_a_tolerance_above_the_recorded_gap_floor_is_indeterminate(self):
        # Force the capped case: pretend only the tightest few of many
        # comparisons were kept, and ask about a tolerance above that floor.
        capped = copy.deepcopy(self.parent)
        boundary = capped["body"]["observations"]["near-boundary"]
        boundary["all_recorded"] = False
        boundary["comparisons_total"] = 5000
        boundary["gap_floor"] = canonical.num(1e-6)
        gates = capped["body"]["gates"]
        for gate in gates:
            if gate["observation"] == "near-boundary":
                gate["observation_digest"] = canonical.digest(boundary)
        capped["seal"]["body_digest"] = canonical.digest(capped["body"])
        capped["record_id"] = "er_" + capped["seal"]["body_digest"].split(":")[1][:16]
        self.assertEqual(schema.validate(capped), [])

        loose = checkers.build_set(
            label="loose",
            overrides={"checkers": {"portability": {"params": {"relative_tolerance": "1e-3"}}}},
        )
        successor, _ = regrade.regrade(capped, loose)
        self.assertEqual(verdicts(successor)["portability"], "INDETERMINATE")

        tighter = checkers.build_set(
            label="within-floor",
            overrides={"checkers": {"portability": {"params": {"relative_tolerance": "1e-9"}}}},
        )
        successor, _ = regrade.regrade(capped, tighter)
        self.assertIn(verdicts(successor)["portability"], ("PASS", "FAIL"))

    def test_a_tampered_parent_is_refused(self):
        tampered = copy.deepcopy(self.parent)
        tampered["body"]["verdict"]["overall"] = "PASS_FORGED"
        with self.assertRaises(ValueError):
            regrade.regrade(tampered, checkers.build_set())

    def test_batch_report_counts_what_changed(self):
        words = self.parent["body"]["observations"]["desc-lint"]["word_count"]
        second = record.build(self.root, self.refs[0], issuer="test-suite", at=1_700_000_500)
        tightened = checkers.build_set(
            label="tightened",
            overrides={"checkers": {"desc-lint": {"params": {"min_words": words + 1}}}},
        )
        successors, report = regrade.regrade_many([self.parent, second], tightened)
        self.assertEqual(len(successors), 2)
        self.assertEqual(report["summary"]["records"], 2)
        self.assertEqual(report["summary"]["verdict_changed"], 2)
        self.assertEqual(report["summary"]["gate_outcomes_flipped"], 2)
        self.assertFalse(report["corpus_re_executed"])


ISOLATION_PROBE = r'''
import json, os, sys

sys.path.insert(0, %(tools)r)

record_path = sys.argv[1]
corpus_root = os.path.abspath(sys.argv[2])

from evidence import checkers, record as record_module, regrade as regrade_module

parent = record_module.load(record_path)
checker_set = checkers.build_set(
    label="probe",
    overrides={"checkers": {"desc-lint": {"params": {"min_words": 999}}}},
)

TOUCHED = []


def hook(event, args):
    if event in ("open", "os.listdir", "os.scandir", "os.stat", "subprocess.Popen"):
        try:
            target = os.path.abspath(str(args[0]))
        except Exception:
            return
        if target.startswith(corpus_root):
            TOUCHED.append("%%s:%%s" %% (event, target))


sys.addaudithook(hook)
successor, entry = regrade_module.regrade(parent, checker_set)
sys.stdout.write(json.dumps({"touched": TOUCHED, "after": entry["verdict_after"]}))
'''


class CorpusIsolationTest(unittest.TestCase):
    """A regrade must not read the corpus.  Proven, not asserted."""

    def test_regrade_opens_nothing_under_the_corpus_root(self):
        root = tempfile.mkdtemp(prefix="aero-evidence-isolation-")
        self.addCleanup(shutil.rmtree, root, True)
        refs = fixture.build_repo(root)
        rec = record.build(root, refs[0], at=1_700_000_000)
        store = os.path.join(root, "records")
        path = record.save(rec, store)

        probe = os.path.join(root, "probe.py")
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write(ISOLATION_PROBE % {"tools": TOOLS_DIR})
        corpus_root = os.path.join(root, "skills")
        completed = subprocess.run(
            [sys.executable, probe, path, corpus_root],
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["touched"], [], "regrade touched the corpus")
        self.assertEqual(result["after"], "FAIL")

    def test_regrade_works_after_the_corpus_is_deleted(self):
        root = tempfile.mkdtemp(prefix="aero-evidence-gone-")
        self.addCleanup(shutil.rmtree, root, True)
        refs = fixture.build_repo(root)
        rec = record.build(root, refs[0], at=1_700_000_000)
        shutil.rmtree(os.path.join(root, "skills"))
        os.remove(os.path.join(root, "standards-map.yaml"))
        successor, entry = regrade.regrade(
            rec,
            checkers.build_set(
                label="after-deletion",
                overrides={"checkers": {"contract-test": {"params": {"min_tests": 99}}}},
            ),
        )
        self.assertEqual(entry["verdict_after"], "FAIL")
        self.assertEqual(schema.validate(successor), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
