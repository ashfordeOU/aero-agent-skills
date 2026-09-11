"""
test_e1006_char_uniqueness.py

Stdlib unittest suite for e1006_char_uniqueness_logic.
Covers: exact duplicates, near-duplicates, normalization edge cases,
input validation, compliance flags, threshold boundary conditions.
Run: python3 test_e1006_char_uniqueness.py
"""

import sys
import os
import unittest

# Allow running from the scripts/ directory or from the repo root.
sys.path.insert(0, os.path.dirname(__file__))

from e1006_char_uniqueness_logic import (
    normalize_text,
    tokenize,
    jaccard_similarity,
    find_exact_duplicates,
    find_near_duplicates,
    check_uniqueness,
)


class TestNormalizeText(unittest.TestCase):

    def test_lowercase_conversion(self):
        self.assertEqual(normalize_text("The System SHALL"), "the system shall")

    def test_whitespace_collapse(self):
        self.assertEqual(normalize_text("  foo   bar  "), "foo bar")

    def test_unicode_nfc(self):
        # composed vs decomposed 'é'
        composed = "café"
        decomposed = "café"
        self.assertEqual(normalize_text(composed), normalize_text(decomposed))

    def test_empty_string(self):
        self.assertEqual(normalize_text(""), "")

    def test_type_error_for_non_string(self):
        with self.assertRaises(TypeError):
            normalize_text(42)


class TestTokenize(unittest.TestCase):

    def test_stopwords_removed(self):
        tokens = tokenize("The system shall provide power")
        self.assertNotIn("the", tokens)
        self.assertNotIn("shall", tokens)
        self.assertIn("system", tokens)
        self.assertIn("provide", tokens)
        self.assertIn("power", tokens)

    def test_empty_string_returns_empty_set(self):
        self.assertEqual(tokenize(""), set())

    def test_all_stopwords_returns_empty_set(self):
        self.assertEqual(tokenize("the and or but"), set())


class TestJaccardSimilarity(unittest.TestCase):

    def test_identical_sets(self):
        s = {"power", "supply", "voltage"}
        self.assertAlmostEqual(jaccard_similarity(s, s), 1.0)

    def test_disjoint_sets(self):
        self.assertAlmostEqual(
            jaccard_similarity({"alpha"}, {"beta"}), 0.0
        )

    def test_partial_overlap(self):
        a = {"x", "y", "z"}
        b = {"x", "y", "w"}
        # intersection=2, union=4 → 0.5
        self.assertAlmostEqual(jaccard_similarity(a, b), 0.5)

    def test_both_empty(self):
        self.assertAlmostEqual(jaccard_similarity(set(), set()), 0.0)


class TestFindExactDuplicates(unittest.TestCase):

    def test_no_duplicates(self):
        reqs = [
            {"id": "R-001", "text": "The system shall provide 28 V power."},
            {"id": "R-002", "text": "The system shall operate between -40 and 85 degC."},
        ]
        self.assertEqual(find_exact_duplicates(reqs), [])

    def test_exact_duplicate_pair(self):
        text = "The unit shall survive launch loads."
        reqs = [
            {"id": "R-001", "text": text},
            {"id": "R-002", "text": text},
        ]
        pairs = find_exact_duplicates(reqs)
        self.assertEqual(len(pairs), 1)
        self.assertIn(("R-001", "R-002"), pairs)

    def test_case_insensitive_duplicate(self):
        reqs = [
            {"id": "R-001", "text": "The System Shall Provide Power."},
            {"id": "R-002", "text": "the system shall provide power."},
        ]
        pairs = find_exact_duplicates(reqs)
        self.assertEqual(len(pairs), 1)

    def test_whitespace_normalised_duplicate(self):
        reqs = [
            {"id": "R-001", "text": "The  system  shall  provide  power."},
            {"id": "R-002", "text": "The system shall provide power."},
        ]
        pairs = find_exact_duplicates(reqs)
        self.assertEqual(len(pairs), 1)

    def test_three_way_duplicate_reports_two_pairs(self):
        text = "The subsystem shall maintain link budget margin."
        reqs = [
            {"id": "R-001", "text": text},
            {"id": "R-002", "text": text},
            {"id": "R-003", "text": text},
        ]
        pairs = find_exact_duplicates(reqs)
        # R-001 is the first occurrence; R-002 and R-003 are both flagged
        self.assertEqual(len(pairs), 2)
        ids = {p[1] for p in pairs}
        self.assertIn("R-002", ids)
        self.assertIn("R-003", ids)

    def test_single_requirement_no_duplicate(self):
        reqs = [{"id": "R-001", "text": "The bus shall supply regulated power."}]
        self.assertEqual(find_exact_duplicates(reqs), [])

    def test_empty_list(self):
        self.assertEqual(find_exact_duplicates([]), [])


class TestFindNearDuplicates(unittest.TestCase):

    def _make_req(self, req_id, text):
        return {"id": req_id, "text": text}

    def test_no_near_duplicates(self):
        reqs = [
            self._make_req("R-001", "The unit shall withstand 50g shock for 11 ms."),
            self._make_req("R-002", "The antenna shall radiate at 2.4 GHz center frequency."),
        ]
        triples = find_near_duplicates(reqs, threshold=0.85)
        self.assertEqual(triples, [])

    def test_near_duplicate_above_threshold(self):
        # These two are highly similar (differ only in one token)
        reqs = [
            self._make_req("R-001", "The power unit shall supply 28 V regulated output voltage."),
            self._make_req("R-002", "The power unit shall provide 28 V regulated output voltage."),
        ]
        triples = find_near_duplicates(reqs, threshold=0.75)
        self.assertTrue(len(triples) >= 1)
        ids = {(t[0], t[1]) for t in triples}
        self.assertIn(("R-001", "R-002"), ids)

    def test_near_duplicate_below_threshold_not_flagged(self):
        reqs = [
            self._make_req("R-001", "The power unit shall supply 28 V regulated output voltage."),
            self._make_req("R-002", "The power unit shall provide 28 V regulated output voltage."),
        ]
        # With threshold=1.0 only exact token-set matches qualify
        triples = find_near_duplicates(reqs, threshold=1.0)
        self.assertEqual(triples, [])

    def test_exact_pairs_excluded_from_near_dup(self):
        text = "The subsystem shall maintain link budget."
        reqs = [
            self._make_req("R-001", text),
            self._make_req("R-002", text),
        ]
        exclude = {("R-001", "R-002")}
        triples = find_near_duplicates(reqs, threshold=0.0, exclude_pairs=exclude)
        self.assertEqual(triples, [])

    def test_invalid_threshold_raises(self):
        reqs = [self._make_req("R-001", "Some requirement text here.")]
        with self.assertRaises(ValueError):
            find_near_duplicates(reqs, threshold=1.5)
        with self.assertRaises(ValueError):
            find_near_duplicates(reqs, threshold=-0.1)


class TestCheckUniqueness(unittest.TestCase):

    def test_empty_list_is_compliant(self):
        result = check_uniqueness([])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["findings"], [])

    def test_single_requirement_is_compliant(self):
        reqs = [{"id": "R-001", "text": "The system shall be fault-tolerant."}]
        result = check_uniqueness(reqs)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["total"], 1)

    def test_exact_duplicate_makes_non_compliant(self):
        text = "The thermal control system shall maintain temperature within range."
        reqs = [
            {"id": "R-001", "text": text},
            {"id": "R-002", "text": text},
        ]
        result = check_uniqueness(reqs)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["exact_duplicate_pairs"]), 1)
        self.assertTrue(len(result["findings"]) >= 1)
        self.assertIn("EXACT-DUPLICATE", result["findings"][0])

    def test_near_duplicate_makes_non_compliant(self):
        reqs = [
            {"id": "R-001", "text": "The power system shall supply regulated 28 V dc bus voltage."},
            {"id": "R-002", "text": "The power subsystem shall supply regulated 28 V dc bus voltage."},
        ]
        result = check_uniqueness(reqs, near_dup_threshold=0.7)
        self.assertFalse(result["compliant"])
        self.assertTrue(len(result["near_duplicate_pairs"]) >= 1)

    def test_unique_requirements_are_compliant(self):
        reqs = [
            {"id": "R-001", "text": "The attitude control system shall point the payload within 0.1 deg."},
            {"id": "R-002", "text": "The structure shall withstand 10g quasi-static launch load."},
            {"id": "R-003", "text": "The communication link shall achieve BER below 1e-6."},
        ]
        result = check_uniqueness(reqs, near_dup_threshold=0.85)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["total"], 3)

    def test_missing_id_raises_value_error(self):
        reqs = [{"text": "Some requirement text."}]
        with self.assertRaises(ValueError):
            check_uniqueness(reqs)

    def test_missing_text_raises_value_error(self):
        reqs = [{"id": "R-001"}]
        with self.assertRaises(ValueError):
            check_uniqueness(reqs)

    def test_empty_id_raises_value_error(self):
        reqs = [{"id": "   ", "text": "Some valid requirement text here."}]
        with self.assertRaises(ValueError):
            check_uniqueness(reqs)

    def test_empty_text_raises_value_error(self):
        reqs = [{"id": "R-001", "text": ""}]
        with self.assertRaises(ValueError):
            check_uniqueness(reqs)

    def test_duplicate_ids_raise_value_error(self):
        reqs = [
            {"id": "R-001", "text": "The system shall survive launch."},
            {"id": "R-001", "text": "The unit shall operate at 5 V."},
        ]
        with self.assertRaises(ValueError):
            check_uniqueness(reqs)

    def test_result_keys_present(self):
        reqs = [{"id": "R-001", "text": "The system shall be reliable."}]
        result = check_uniqueness(reqs)
        for key in ("total", "exact_duplicate_pairs", "near_duplicate_pairs",
                    "compliant", "findings"):
            self.assertIn(key, result)

    def test_exact_dup_not_also_near_dup(self):
        text = "The unit shall operate at nominal voltage supply rail."
        reqs = [
            {"id": "R-001", "text": text},
            {"id": "R-002", "text": text},
        ]
        result = check_uniqueness(reqs, near_dup_threshold=0.0)
        # The identical pair must appear only in exact_duplicate_pairs
        self.assertEqual(len(result["exact_duplicate_pairs"]), 1)
        near_ids = {(t[0], t[1]) for t in result["near_duplicate_pairs"]}
        self.assertNotIn(("R-001", "R-002"), near_ids)

    def test_finding_strings_contain_ids(self):
        text = "The propulsion system shall deliver 220 N thrust."
        reqs = [
            {"id": "REQ-A", "text": text},
            {"id": "REQ-B", "text": text},
        ]
        result = check_uniqueness(reqs)
        joined = " ".join(result["findings"])
        self.assertIn("REQ-A", joined)
        self.assertIn("REQ-B", joined)

    def test_near_dup_finding_contains_near_duplicate_label(self):
        reqs = [
            {"id": "R-001", "text": "The power unit shall supply 28 V regulated output."},
            {"id": "R-002", "text": "The power unit shall provide 28 V regulated output."},
        ]
        result = check_uniqueness(reqs, near_dup_threshold=0.7)
        if result["near_duplicate_pairs"]:
            self.assertTrue(
                any("NEAR-DUPLICATE" in f for f in result["findings"])
            )


if __name__ == "__main__":
    unittest.main()
