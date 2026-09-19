#!/usr/bin/env python3
"""Tests for the family-aware no-verbatim gate (stdlib unittest, offline).

Run: python3 tools/test_verbatim_gate.py

The sample "source" text below is invented prose written for this test. No
standards text is reproduced anywhere in this file.
"""

import sys

# no __pycache__ in the tree after a test run
sys.dont_write_bytecode = True

import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import verbatim_gate as vg  # noqa: E402
import verbatim_shingle as vs  # noqa: E402

# 60 invented words. Long enough that any 32-word run inside it is a
# guaranteed winnowing match.
SOURCE = (
    "the carriage assembly shall present a nominal seating plane to the "
    "lower bracket while the upper retainer keeps the guide pin inside its "
    "travel envelope during every qualification cycle and the acceptance "
    "record shall list the measured clearance at both ends of the travel "
    "together with the ambient temperature observed at the moment of the "
    "measurement and the identity of the measuring instrument used"
)


class Shingles(unittest.TestCase):
    def test_tokenize_ignores_markup_and_case(self):
        self.assertEqual(vs.tokenize("**Alpha**, beta-gamma\n  DELTA!"),
                         ["alpha", "beta", "gamma", "delta"])

    def test_hash_is_stable_across_processes(self):
        # not Python's salted hash(): the same text must fingerprint the
        # same way in the builder process and in the gate process
        out = subprocess.run(
            [sys.executable, "-B", "-c",
             "import sys;sys.path.insert(0,%r);import verbatim_shingle as v;"
             "print(v.fingerprints(%r)[0][1])" % (str(HERE), SOURCE)],
            stdout=subprocess.PIPE, check=True)
        self.assertEqual(int(out.stdout.strip()), vs.fingerprints(SOURCE)[0][1])

    def test_short_text_still_yields_a_fingerprint(self):
        words = " ".join("w%d" % i for i in range(vs.SHINGLE_N + 1))
        self.assertTrue(vs.fingerprints(words))

    def test_text_shorter_than_a_shingle_yields_none(self):
        self.assertEqual(vs.fingerprints("only four words here"), [])

    def test_guaranteed_run_length_is_detected(self):
        # a run of exactly GUARANTEE tokens, embedded in unrelated text
        run = SOURCE.split()[:vs.GUARANTEE]
        noise = ["zulu%d" % i for i in range(40)]
        doc = " ".join(noise + run + noise)
        src = {fp for _, fp in vs.fingerprints(SOURCE)}
        hit = {fp for _, fp in vs.fingerprints(doc)} & src
        self.assertTrue(hit, "a %d-word verbatim run must share a fingerprint"
                             % vs.GUARANTEE)

    def test_bare_numbers_are_not_fingerprinted(self):
        # a table of values is reference data, not authorship: two unrelated
        # files sharing only a number sequence must not match
        a = "alpha 0 0 1 0 2 0 3 0 4 0 5 0 6 0 7 0 8 0 9 1 0 1 1 1 2 omega"
        b = "kestrel 0 0 1 0 2 0 3 0 4 0 5 0 6 0 7 0 8 0 9 1 0 1 1 1 2 heron"
        self.assertFalse({fp for _, fp in vs.fingerprints(a)}
                         & {fp for _, fp in vs.fingerprints(b)})

    def test_a_repeated_word_is_not_fingerprinted(self):
        self.assertEqual(vs.fingerprints(" ".join(["a"] * 200)), [])

    def test_paraphrase_shares_no_fingerprint(self):
        para = ("each carriage is checked against its bracket, and the "
                "inspector writes down how much room is left at both stops, "
                "what the room temperature was, and which gauge was used")
        src = {fp for _, fp in vs.fingerprints(SOURCE)}
        self.assertFalse({fp for _, fp in vs.fingerprints(para)} & src)


class Index(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.src = self.tmp / "src"
        self.src.mkdir()
        (self.src / "sample-standard.txt").write_text(SOURCE, encoding="utf-8")
        self.out = self.tmp / "idx"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _build(self):
        rc = subprocess.run(
            [sys.executable, str(HERE / "build_verbatim_index.py"),
             "--family", "sample", "--sources", str(self.src),
             "--out", str(self.out)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertEqual(rc.returncode, 0, rc.stdout.decode())
        return self.out / "sample.idx"

    def test_round_trip_lookup(self):
        si = vg.SourceIndex(self._build())
        self.assertEqual(si.header["source_documents"], 1)
        for _, fp in vs.fingerprints(SOURCE):
            self.assertEqual(si.lookup(fp), "sample-standard.txt")

    def test_absent_fingerprint_is_not_reported(self):
        si = vg.SourceIndex(self._build())
        miss = {fp for _, fp in vs.fingerprints(
            "unrelated sentence about kites flying over a quiet harbour in "
            "the late afternoon while the tide runs out beneath them")}
        for fp in miss:
            self.assertIsNone(si.lookup(fp))

    def test_index_carries_no_readable_source_text(self):
        raw = self._build().read_bytes()
        for word in ("carriage", "retainer", "qualification", "clearance"):
            self.assertNotIn(word.encode(), raw)

    def test_build_is_deterministic(self):
        first = self._build().read_bytes()
        self.assertEqual(self._build().read_bytes(), first)

    def test_phrase_shared_across_documents_is_dropped(self):
        shared = ("the project review sequence runs through the system "
                  "requirements review the preliminary design review the "
                  "critical design review the qualification review and the "
                  "acceptance review in that order")
        for i in range(5):
            (self.src / ("shared-%d.txt" % i)).write_text(
                "%s document %s" % (shared, "abcdefghij"[i] * 30),
                encoding="utf-8")
        si = vg.SourceIndex(self._build())
        self.assertEqual(si.header["max_df"], 3)
        self.assertGreater(si.header["dropped_above_max_df"], 0)
        for _, fp in vs.fingerprints(shared):
            self.assertIsNone(si.lookup(fp),
                              "a phrase in 5 of 6 documents must not be indexed")

    def test_phrase_in_one_document_is_kept(self):
        (self.src / "other.txt").write_text(
            "an unrelated document about harbour cranes and the tide", encoding="utf-8")
        si = vg.SourceIndex(self._build())
        self.assertTrue(any(si.lookup(fp) == "sample-standard.txt"
                            for _, fp in vs.fingerprints(SOURCE)))

    def test_check_mode_detects_a_changed_source(self):
        self._build()
        (self.src / "sample-standard.txt").write_text(
            SOURCE + " and a further sentence the committed index never saw "
                     "because it was added after the index was written",
            encoding="utf-8")
        rc = subprocess.run(
            [sys.executable, str(HERE / "build_verbatim_index.py"),
             "--family", "sample", "--sources", str(self.src),
             "--out", str(self.out), "--check"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertEqual(rc.returncode, 1)
        self.assertIn(b"differs", rc.stdout)

    def test_scheme_mismatch_is_refused(self):
        p = self._build()
        raw = bytearray(p.read_bytes())
        i = raw.find(vs.SCHEME.encode())
        raw[i:i + len(vs.SCHEME)] = b"x" * len(vs.SCHEME)
        p.write_bytes(bytes(raw))
        with self.assertRaises(ValueError):
            vg.SourceIndex(p)


class Register(unittest.TestCase):
    def setUp(self):
        self.reg = vg.read_register(HERE.parent / "standards-map.yaml")

    def test_register_parses(self):
        self.assertGreater(len(self.reg), 20)
        self.assertIn("do-178c", self.reg)
        self.assertIn("ecss", self.reg)

    def test_every_registered_publisher_maps_to_a_family(self):
        orphan = sorted(sid for sid, e in self.reg.items()
                        if vg.family_of(e.get("publisher", "")) is None)
        self.assertEqual(orphan, [], "standards-map.yaml publishers with no "
                                     "family in verbatim_gate.FAMILIES")

    def test_joint_publishers_resolve_to_the_owning_body(self):
        self.assertEqual(vg.family_of("IAQG (develops) / SAE (publishes Americas)"),
                         "iaqg")
        self.assertEqual(vg.family_of("ARINC (AEEC; published via SAE ITC)"), "arinc")
        self.assertEqual(vg.family_of("RTCA (joint EUROCAE twin ED-12C)"), "rtca")

    def test_family_keys_are_unique(self):
        keys = [f["key"] for f in vg.FAMILIES]
        self.assertEqual(len(keys), len(set(keys)))

    def test_a_family_declares_markers_or_says_why_not(self):
        for f in vg.FAMILIES:
            self.assertTrue(f.get("markers") or f.get("no_markers"),
                            "%s has neither markers nor a stated reason"
                            % f["key"])


class GateRun(unittest.TestCase):
    """End-to-end over a throwaway repo shaped like the real one."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "tools").mkdir()
        for f in ("verbatim_gate.py", "verbatim_shingle.py",
                  "build_verbatim_index.py"):
            shutil.copy(HERE / f, self.tmp / "tools" / f)
        shutil.copy(HERE.parent / "standards-map.yaml", self.tmp)
        self.leaf = self.tmp / "skills" / "space-systems" / "ecss" / "sample-leaf"
        self.leaf.mkdir(parents=True)
        (self.tmp / "docs").mkdir()
        self.write_leaf("Paraphrased body: the assembly is checked and the "
                        "result is written down.")
        src = self.tmp / "src"
        src.mkdir()
        (src / "sample-standard.txt").write_text(SOURCE, encoding="utf-8")
        subprocess.run(
            [sys.executable, str(self.tmp / "tools" / "build_verbatim_index.py"),
             "--family", "ecss", "--sources", str(src)],
            stdout=subprocess.DEVNULL, check=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_leaf(self, body):
        (self.leaf / "SKILL.md").write_text(
            "---\nname: sample-leaf\nstandards:\n  - id: ecss\n"
            "    reference-only: true\n---\n\n# Sample\n\n%s\n" % body,
            encoding="utf-8")

    def run_gate(self, *args):
        return subprocess.run(
            [sys.executable, str(self.tmp / "tools" / "verbatim_gate.py")] + list(args),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_clean_tree_passes_and_prints_coverage(self):
        r = self.run_gate()
        out = r.stdout.decode()
        self.assertEqual(r.returncode, 0, out + r.stderr.decode())
        self.assertIn("COVERAGE gate4-no-verbatim:", out)
        self.assertIn("PASS gate4-no-verbatim", out)

    def test_source_text_run_fails_the_gate(self):
        self.write_leaf(SOURCE)          # the whole 60-word source
        r = self.run_gate()
        self.assertEqual(r.returncode, 1, r.stderr.decode())
        self.assertIn("reproduces ecss source text", r.stderr.decode())

    def test_a_single_shared_fingerprint_warns_but_passes(self):
        self.write_leaf(" ".join(SOURCE.split()[:vs.GUARANTEE + 2]))
        r = self.run_gate()
        err = r.stderr.decode()
        self.assertEqual(r.returncode, 0, err)
        self.assertIn("WARN gate4-no-verbatim", err)
        self.assertIn("short run", err)

    def test_min_fingerprints_one_turns_that_warn_into_a_failure(self):
        self.write_leaf(" ".join(SOURCE.split()[:vs.GUARANTEE + 2]))
        r = self.run_gate("--min-fingerprints", "1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("reproduces ecss source text", r.stderr.decode())

    def test_marker_line_fails_the_gate(self):
        self.write_leaf("Paraphrase.\n\nESA-ESTEC\nRequirements & Standards Division\n")
        r = self.run_gate()
        self.assertEqual(r.returncode, 1)
        self.assertIn("ecss marker", r.stderr.decode())

    def test_legitimate_citation_does_not_trip_the_gate(self):
        self.write_leaf("Apply the wire-category rule of ECSS-E-ST-20-07C "
                        "clause 4.2 when routing a bundle.")
        self.assertEqual(self.run_gate().returncode, 0)

    def test_pre_existing_rtca_markers_still_fire(self):
        (self.tmp / "docs" / "note.md").write_text(
            "Copyright RTCA, Inc. All Rights Reserved\n", encoding="utf-8")
        r = self.run_gate()
        self.assertEqual(r.returncode, 1)
        self.assertIn("rtca marker", r.stderr.decode())

    def test_generic_licence_marker_still_fires(self):
        (self.tmp / "docs" / "note.md").write_text(
            "This document is licensed to a single reader\n", encoding="utf-8")
        r = self.run_gate()
        self.assertEqual(r.returncode, 1)
        self.assertIn("generic marker", r.stderr.decode())

    def test_coverage_json_reports_unchecked_families(self):
        (self.leaf / "SKILL.md").write_text(
            "---\nname: sample-leaf\nstandards:\n  - id: far-25\n---\n\n"
            "# Sample\n\nParaphrased body.\n", encoding="utf-8")
        r = self.run_gate("--json")
        data = json.loads(r.stdout.decode())
        fams = {f["family"]: f for f in data["families"]}
        self.assertEqual(fams["faa"]["status"], "UNCHECKED")
        self.assertEqual(data["leaves_unchecked_family"], 1)
        self.assertTrue(fams["faa"]["reason"])

    def test_strict_fails_on_an_unchecked_family(self):
        (self.leaf / "SKILL.md").write_text(
            "---\nname: sample-leaf\nstandards:\n  - id: far-25\n---\n\n"
            "# Sample\n\nParaphrased body.\n", encoding="utf-8")
        self.assertEqual(self.run_gate().returncode, 0)
        r = self.run_gate("--strict")
        self.assertEqual(r.returncode, 1)
        self.assertIn("UNCHECKED", r.stderr.decode())

    def test_unmapped_standard_id_is_named_not_swallowed(self):
        (self.leaf / "SKILL.md").write_text(
            "---\nname: sample-leaf\nstandards:\n  - id: NOT-IN-THE-REGISTER\n"
            "---\n\n# Sample\n\nParaphrased body.\n", encoding="utf-8")
        r = self.run_gate("--json")
        data = json.loads(r.stdout.decode())
        self.assertEqual(data["unmapped_standard_ids"], {"NOT-IN-THE-REGISTER": 1})
        self.assertEqual(data["leaves_unchecked_family"], 1)

    def test_missing_register_refuses_rather_than_passing(self):
        os.remove(self.tmp / "standards-map.yaml")
        r = self.run_gate()
        self.assertEqual(r.returncode, 1)
        self.assertIn("standards-map.yaml is missing", r.stderr.decode())

    def test_missing_index_downgrades_the_family_to_markers_only(self):
        os.remove(self.tmp / "tools" / "verbatim-index" / "ecss.idx")
        r = self.run_gate("--json")
        data = json.loads(r.stdout.decode())
        fams = {f["family"]: f for f in data["families"]}
        self.assertEqual(fams["ecss"]["status"], "MARKERS-ONLY")
        self.assertEqual(data["leaves_source_checked"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
