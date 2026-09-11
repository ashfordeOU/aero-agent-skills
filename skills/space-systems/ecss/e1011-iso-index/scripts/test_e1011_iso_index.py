#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11C Annex E HFE ISO/EN standards index.

Exercises scripts/e1011_iso_index_logic.py (stdlib unittest, offline).
Contract: a known standard ID resolves to a record with title and topics;
an unknown ID raises ValueError; a topic query returns the correct standard
IDs or an empty list for an unknown topic; topics_for_standard returns a
sorted list or raises for an unknown ID; check_topic_coverage reports
covered topics with their matching standards and gaps for unindexed topics;
coverage_gaps is a consistent convenience wrapper; the catalog is non-empty
and every record carries the required fields; the topics index is consistent
with the catalog.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_iso_index_logic as idx  # noqa: E402


class LookupStandardTest(unittest.TestCase):
    def test_known_standard_returns_dict(self):
        record = idx.lookup_standard("ISO 9241-11")
        self.assertIsInstance(record, dict)

    def test_known_standard_has_nonempty_title(self):
        record = idx.lookup_standard("ISO 9241-11")
        self.assertIn("title", record)
        self.assertTrue(record["title"])

    def test_known_standard_has_nonempty_topics_list(self):
        record = idx.lookup_standard("ISO 9241-11")
        self.assertIn("topics", record)
        self.assertIsInstance(record["topics"], list)
        self.assertGreater(len(record["topics"]), 0)

    def test_lookup_returns_new_object_each_call(self):
        r1 = idx.lookup_standard("ISO 9241-11")
        r2 = idx.lookup_standard("ISO 9241-11")
        self.assertIsNot(r1, r2)

    def test_unknown_standard_raises_value_error(self):
        with self.assertRaises(ValueError):
            idx.lookup_standard("ISO 99999-99")

    def test_en_standard_resolves(self):
        record = idx.lookup_standard("EN 614-1")
        self.assertIn("title", record)
        self.assertTrue(record["title"])

    def test_iso_10075_resolves(self):
        record = idx.lookup_standard("ISO 10075-1")
        self.assertIn("topics", record)


class StandardsForTopicTest(unittest.TestCase):
    def test_anthropometry_returns_nonempty_list(self):
        result = idx.standards_for_topic("anthropometry")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_mental_workload_returns_nonempty_list(self):
        result = idx.standards_for_topic("mental_workload")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_unknown_topic_returns_empty_list(self):
        result = idx.standards_for_topic("zero_gravity_dance_ergonomics")
        self.assertEqual(result, [])

    def test_result_is_sorted(self):
        result = idx.standards_for_topic("display_design")
        self.assertEqual(result, sorted(result))

    def test_display_design_includes_en_standard(self):
        result = idx.standards_for_topic("display_design")
        self.assertIn("EN 894-2", result)

    def test_mental_workload_includes_iso_10075_series(self):
        result = idx.standards_for_topic("mental_workload")
        self.assertIn("ISO 10075-1", result)
        self.assertIn("ISO 10075-2", result)


class TopicsForStandardTest(unittest.TestCase):
    def test_known_standard_returns_nonempty_list(self):
        topics = idx.topics_for_standard("ISO 9241-11")
        self.assertIsInstance(topics, list)
        self.assertGreater(len(topics), 0)

    def test_result_is_sorted(self):
        topics = idx.topics_for_standard("ISO 10075-1")
        self.assertEqual(topics, sorted(topics))

    def test_unknown_standard_raises_value_error(self):
        with self.assertRaises(ValueError):
            idx.topics_for_standard("ISO 99999-99")

    def test_iso_10075_covers_mental_workload(self):
        topics = idx.topics_for_standard("ISO 10075-1")
        self.assertIn("mental_workload", topics)

    def test_iso_11064_4_covers_anthropometry(self):
        topics = idx.topics_for_standard("ISO 11064-4")
        self.assertIn("anthropometry", topics)


class CheckTopicCoverageTest(unittest.TestCase):
    def test_all_indexed_topics_show_covered(self):
        all_topics = list(idx._TOPICS_INDEX.keys())
        result = idx.check_topic_coverage(all_topics)
        self.assertEqual(result["gaps"], [])
        self.assertEqual(len(result["covered"]), len(all_topics))

    def test_unknown_topic_flagged_as_gap(self):
        result = idx.check_topic_coverage(["zero_gravity_dance_ergonomics"])
        self.assertIn("zero_gravity_dance_ergonomics", result["gaps"])
        self.assertEqual(result["covered"], [])

    def test_empty_input_returns_empty_covered_and_gaps(self):
        result = idx.check_topic_coverage([])
        self.assertEqual(result["covered"], [])
        self.assertEqual(result["gaps"], [])

    def test_covered_entry_has_topic_and_standards(self):
        result = idx.check_topic_coverage(["anthropometry"])
        self.assertEqual(len(result["covered"]), 1)
        entry = result["covered"][0]
        self.assertEqual(entry["topic"], "anthropometry")
        self.assertIsInstance(entry["standards"], list)
        self.assertGreater(len(entry["standards"]), 0)

    def test_mixed_known_and_unknown_topics(self):
        result = idx.check_topic_coverage(["anthropometry", "nonexistent_topic"])
        covered_topics = [e["topic"] for e in result["covered"]]
        self.assertIn("anthropometry", covered_topics)
        self.assertIn("nonexistent_topic", result["gaps"])

    def test_input_list_not_mutated(self):
        original = ["anthropometry", "mental_workload"]
        snapshot = list(original)
        idx.check_topic_coverage(original)
        self.assertEqual(original, snapshot)

    def test_covered_standards_are_sorted(self):
        result = idx.check_topic_coverage(["display_design"])
        entry = result["covered"][0]
        self.assertEqual(entry["standards"], sorted(entry["standards"]))


class CoverageGapsTest(unittest.TestCase):
    def test_no_gap_for_known_topic(self):
        gaps = idx.coverage_gaps(["anthropometry"])
        self.assertEqual(gaps, [])

    def test_gap_returned_for_unknown_topic(self):
        gaps = idx.coverage_gaps(["nonexistent_hfe_area"])
        self.assertEqual(gaps, ["nonexistent_hfe_area"])

    def test_empty_input_returns_empty_gaps(self):
        self.assertEqual(idx.coverage_gaps([]), [])

    def test_consistent_with_check_topic_coverage(self):
        topics = ["anthropometry", "nonexistent_hfe_area", "mental_workload"]
        full = idx.check_topic_coverage(topics)
        gaps = idx.coverage_gaps(topics)
        self.assertEqual(gaps, full["gaps"])


class CatalogConsistencyTest(unittest.TestCase):
    def test_catalog_is_nonempty(self):
        self.assertGreater(len(idx.ISO_STANDARDS), 0)

    def test_all_standards_have_nonempty_title(self):
        for sid, rec in idx.ISO_STANDARDS.items():
            with self.subTest(standard=sid):
                self.assertIn("title", rec)
                self.assertTrue(rec["title"])

    def test_all_standards_have_nonempty_topics_list(self):
        for sid, rec in idx.ISO_STANDARDS.items():
            with self.subTest(standard=sid):
                self.assertIn("topics", rec)
                self.assertIsInstance(rec["topics"], list)
                self.assertGreater(len(rec["topics"]), 0)

    def test_topics_index_consistent_with_catalog(self):
        for topic, sids in idx._TOPICS_INDEX.items():
            for sid in sids:
                with self.subTest(topic=topic, standard=sid):
                    self.assertIn(sid, idx.ISO_STANDARDS)
                    self.assertIn(topic, idx.ISO_STANDARDS[sid]["topics"])

    def test_catalog_covers_iso_9241_series(self):
        iso_9241_ids = [
            sid for sid in idx.ISO_STANDARDS if sid.startswith("ISO 9241-")
        ]
        self.assertGreater(len(iso_9241_ids), 1)

    def test_catalog_covers_iso_10075_series(self):
        iso_10075_ids = [
            sid for sid in idx.ISO_STANDARDS if sid.startswith("ISO 10075-")
        ]
        self.assertGreater(len(iso_10075_ids), 0)


if __name__ == "__main__":
    unittest.main()
