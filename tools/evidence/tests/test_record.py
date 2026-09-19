#!/usr/bin/env python3
"""Evidence record: canonical encoding, corpus binding, seal, amendments."""

import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fixture  # noqa: E402
from evidence import canonical, checkers, corpus, record, schema  # noqa: E402


class CanonicalTest(unittest.TestCase):
    def test_key_order_does_not_change_the_digest(self):
        a = {"b": 1, "a": {"y": [1, 2], "x": "t"}}
        b = {"a": {"x": "t", "y": [1, 2]}, "b": 1}
        self.assertEqual(canonical.digest(a), canonical.digest(b))

    def test_a_float_is_refused(self):
        with self.assertRaises(canonical.CanonicalError):
            canonical.canonical_bytes({"gap": 1.5})

    def test_measurements_travel_as_decimal_strings(self):
        text = canonical.num(1.0 / 3.0)
        self.assertIsInstance(text, str)
        self.assertEqual(canonical.parse_num(text), 1.0 / 3.0)

    def test_non_finite_is_refused(self):
        with self.assertRaises(canonical.CanonicalError):
            canonical.num(float("inf"))

    def test_digest_is_stable_across_encodings_of_the_same_object(self):
        obj = {"z": [1, {"k": "v"}], "a": True, "n": None}
        self.assertEqual(canonical.digest(obj), canonical.digest(json.loads(json.dumps(obj))))


class CorpusDigestTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="aero-evidence-corpus-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.refs = fixture.build_repo(self.root, leaves=("demo-leaf", "demo-leaf-two"))

    def test_one_changed_byte_moves_both_digests(self):
        before_corpus = corpus.corpus_binding(self.root)["subtree_digest"]
        before_leaf = corpus.leaf_binding(self.root, self.refs[0])["leaf_digest"]
        path = os.path.join(self.root, self.refs[0].replace("/", os.sep), "SKILL.md")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n")
        after_corpus = corpus.corpus_binding(self.root)["subtree_digest"]
        after_leaf = corpus.leaf_binding(self.root, self.refs[0])["leaf_digest"]
        self.assertNotEqual(before_corpus, after_corpus)
        self.assertNotEqual(before_leaf, after_leaf)

    def test_adding_a_leaf_leaves_the_other_leaf_digest_alone(self):
        # This is the property behind "adding capabilities is a data change,
        # not a re-qualification event".
        before_corpus = corpus.corpus_binding(self.root)["subtree_digest"]
        before_leaf = corpus.leaf_binding(self.root, self.refs[0])["leaf_digest"]
        fixture.write_leaf(self.root, "demo-leaf-three")
        self.assertNotEqual(before_corpus, corpus.corpus_binding(self.root)["subtree_digest"])
        self.assertEqual(before_leaf, corpus.leaf_binding(self.root, self.refs[0])["leaf_digest"])

    def test_build_noise_is_not_content(self):
        before = corpus.corpus_binding(self.root)["subtree_digest"]
        noise = os.path.join(self.root, "skills", "__pycache__")
        os.makedirs(noise, exist_ok=True)
        with open(os.path.join(noise, "x.pyc"), "wb") as fh:
            fh.write(b"\x00\x01")
        self.assertEqual(before, corpus.corpus_binding(self.root)["subtree_digest"])


class RecordTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="aero-evidence-record-")
        cls.refs = fixture.build_repo(cls.root)
        cls.record = record.build(cls.root, cls.refs[0], issuer="test-suite")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    def test_the_fixture_leaf_passes_every_default_gate(self):
        self.assertEqual(self.record["body"]["verdict"]["overall"], "PASS")
        self.assertEqual(
            sorted(g["gate"] for g in self.record["body"]["gates"]),
            sorted(checkers.DEFAULT_ENABLED),
        )

    def test_schema_validates(self):
        self.assertEqual(schema.validate(self.record), [])

    def test_harness_and_specification_versions_are_separate_fields(self):
        versions = self.record["body"]["versions"]
        self.assertIn("harness_runtime", versions)
        self.assertIn("specification", versions)
        self.assertNotEqual(
            versions["harness_runtime"]["version"], versions["specification"]["version"]
        )
        self.assertTrue(versions["specification"]["source_digest"].startswith("sha256:"))

    def test_standards_editions_are_present_and_explicitly_unbound(self):
        entry = self.record["body"]["standards"]["in_scope"][0]
        self.assertIn("issue", entry)
        self.assertIn("issue_date", entry)
        self.assertIsNone(entry["issue"])
        self.assertIsNone(entry["issue_date"])
        self.assertEqual(entry["edition_binding"], "unbound")
        self.assertTrue(entry["edition_source"])
        self.assertEqual(self.record["body"]["standards"]["edition_gaps"], ["demo-std"])

    def test_the_record_carries_no_absolute_path(self):
        self.assertEqual(schema.absolute_path_strings(self.record["body"]), [])

    def test_observations_are_threshold_free(self):
        desc = self.record["body"]["observations"]["desc-lint"]
        self.assertIn("word_count", desc)
        self.assertFalse(
            [k for k in desc if k.endswith("_ok") or k.startswith("passes")],
            "an observation must not record a verdict",
        )

    def test_the_near_boundary_observation_recorded_real_comparisons(self):
        boundary = self.record["body"]["observations"]["near-boundary"]
        self.assertGreater(boundary["comparisons_total"], 0)
        self.assertTrue(boundary["all_recorded"])
        self.assertTrue(
            all(isinstance(e["relative_gap"], str) for e in boundary["tightest"])
        )

    def test_telemetry_is_outside_the_seal(self):
        self.assertIn("telemetry", self.record)
        self.assertNotIn("telemetry", self.record["body"])
        self.assertTrue(self.record["telemetry"]["contract_test_runs"])

    def test_two_runs_with_a_pinned_clock_seal_to_the_same_digest(self):
        first = record.build(self.root, self.refs[0], at=1_700_000_000)
        second = record.build(self.root, self.refs[0], at=1_700_000_000)
        self.assertEqual(first["seal"]["body_digest"], second["seal"]["body_digest"])
        self.assertEqual(first["record_id"], second["record_id"])

    def test_tampering_with_the_body_breaks_the_seal(self):
        tampered = copy.deepcopy(self.record)
        tampered["body"]["verdict"]["overall"] = "PASS "
        errors = schema.validate(tampered)
        self.assertTrue(any("seal is broken" in e for e in errors), errors)

    def test_a_gate_may_not_cite_an_observation_it_did_not_read(self):
        tampered = copy.deepcopy(self.record)
        tampered["body"]["observations"]["desc-lint"]["word_count"] = 9999
        tampered["seal"]["body_digest"] = canonical.digest(tampered["body"])
        tampered["record_id"] = "er_" + tampered["seal"]["body_digest"].split(":")[1][:16]
        errors = schema.validate(tampered)
        self.assertTrue(any("observation digest" in e for e in errors), errors)

    def test_verify_rederives_the_stored_verdicts(self):
        report = record.verify(self.record)
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["rederivation"]["possible"])
        self.assertEqual(report["rederivation"]["mismatches"], [])

    def test_save_and_load_round_trip(self):
        directory = tempfile.mkdtemp(prefix="aero-evidence-store-")
        self.addCleanup(shutil.rmtree, directory, True)
        path = record.save(self.record, directory)
        self.assertEqual(record.load(path), self.record)


class AmendmentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="aero-evidence-amend-")
        cls.refs = fixture.build_repo(cls.root)
        cls.record = record.build(cls.root, cls.refs[0], issuer="test-suite", at=1_700_000_000)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, True)

    def amended(self):
        return record.amend(
            self.record,
            author="quality.lead@example",
            reason="the issuing run named the wrong issuer",
            pointer="/issued/by",
            new_value="ashforde-conformance",
            at=1_700_000_100,
        )

    def test_the_body_and_the_seal_are_untouched(self):
        after = self.amended()
        self.assertEqual(after["body"], self.record["body"])
        self.assertEqual(after["seal"], self.record["seal"])
        self.assertEqual(after["body"]["issued"]["by"], "test-suite")

    def test_the_prior_value_author_and_reason_are_recorded(self):
        entry = self.amended()["amendments"][0]
        self.assertEqual(entry["seq"], 1)
        self.assertEqual(entry["prior_value"], "test-suite")
        self.assertEqual(entry["new_value"], "ashforde-conformance")
        self.assertEqual(entry["author"], "quality.lead@example")
        self.assertTrue(entry["reason"])

    def test_the_amended_reading_is_computed_not_stored(self):
        after = self.amended()
        self.assertEqual(record.current_view(after)["issued"]["by"], "ashforde-conformance")
        self.assertEqual(after["body"]["issued"]["by"], "test-suite")

    def test_the_chain_verifies_and_the_record_stays_valid(self):
        after = self.amended()
        self.assertEqual(record.verify_history(after), [])
        self.assertEqual(schema.validate(after), [])

    def test_two_amendments_chain(self):
        first = self.amended()
        second = record.amend(
            first,
            author="quality.lead@example",
            reason="correcting the correction",
            pointer="/issued/by",
            new_value="ashforde-conformance-office",
            at=1_700_000_200,
        )
        self.assertEqual([a["seq"] for a in second["amendments"]], [1, 2])
        self.assertEqual(second["amendments"][1]["prior_value"], "ashforde-conformance")
        self.assertEqual(record.verify_history(second), [])

    def test_removing_an_entry_from_the_middle_is_detected(self):
        first = self.amended()
        second = record.amend(
            first,
            author="quality.lead@example",
            reason="correcting the correction",
            pointer="/issued/by",
            new_value="ashforde-conformance-office",
            at=1_700_000_200,
        )
        broken = copy.deepcopy(second)
        del broken["amendments"][0]
        broken["amendments"][0]["seq"] = 1
        problems = record.verify_history(broken)
        self.assertTrue(problems, "a removed amendment must not replay cleanly")

    def test_rewriting_a_prior_value_is_detected(self):
        broken = copy.deepcopy(self.amended())
        broken["amendments"][0]["prior_value"] = "somebody-else"
        problems = record.verify_history(broken)
        self.assertTrue(any("prior value" in p for p in problems), problems)

    def test_an_amendment_must_carry_an_author_and_a_reason(self):
        for author, reason in (("", "r"), ("a", "   ")):
            with self.assertRaises(ValueError):
                record.amend(self.record, author, reason, "/issued/by", "x")

    def test_the_seal_and_the_history_cannot_be_amended(self):
        for pointer in ("/seal/body_digest", "/amendments/0"):
            with self.assertRaises(ValueError):
                record.amend(self.record, "a", "r", pointer, "x")

    def test_a_no_op_amendment_is_refused(self):
        with self.assertRaises(ValueError):
            record.amend(self.record, "a", "r", "/issued/by", "test-suite")


class SchemaGuardTest(unittest.TestCase):
    def test_a_record_missing_body_keys_is_rejected(self):
        errors = schema.validate({"kind": schema.KIND})
        self.assertTrue(errors)

    def test_an_absolute_path_in_the_body_is_rejected(self):
        root = tempfile.mkdtemp(prefix="aero-evidence-abs-")
        self.addCleanup(shutil.rmtree, root, True)
        refs = fixture.build_repo(root)
        rec = record.build(root, refs[0])
        rec["body"]["subject"]["ref"] = "/opt/example/skills/demo"
        rec["seal"]["body_digest"] = canonical.digest(rec["body"])
        rec["record_id"] = "er_" + rec["seal"]["body_digest"].split(":")[1][:16]
        errors = schema.validate(rec)
        self.assertTrue(any("absolute path" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
