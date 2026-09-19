"""Contract test for the summary-report-the-content-of-a-repository leaf."""

import unittest

from e7041_summary_report_the_content_of_a_repository_logic import (
    DEFAULT_ENTRY_CAPACITY,
    FAILURE_UNKNOWN,
    MAX_NAME_OCTETS,
    OUTCOME_COMPLETE,
    OUTCOME_EMPTY,
    OUTCOME_TRUNCATED,
    TYPE_FILE,
    TYPE_REPOSITORY,
    assess_summary_request,
    branch_file_count,
    branch_octets,
    depth_of,
    direct_octets,
    direct_sub_repositories,
    is_within,
    normalize_path,
    split_path,
    summarize_repository,
    summary_is_shallow,
    validate_segment,
    validate_tree,
)


def f(name, size):
    return {"name": name, "size_octets": size}


def tree():
    return {
        "mem1": [],
        "mem1/logs": [f("EVT-001.DAT", 2048), f("EVT-002.DAT", 512)],
        "mem1/logs/archive": [f("OLD-001.DAT", 4096)],
        "mem1/images": [f("IMG-01.RAW", 100000)],
        "mem1/spare": [],
    }


class TestValidation(unittest.TestCase):
    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            validate_segment("")

    def test_name_with_a_separator_raises(self):
        with self.assertRaises(ValueError):
            validate_segment("logs/EVT.DAT")

    def test_over_long_name_raises(self):
        with self.assertRaises(ValueError):
            validate_segment("A" * (MAX_NAME_OCTETS + 1))

    def test_path_is_normalized(self):
        self.assertEqual(normalize_path("/mem1/logs/"), "mem1/logs")

    def test_path_with_an_empty_inner_segment_raises(self):
        with self.assertRaises(ValueError):
            split_path("mem1//logs")

    def test_depth_counts_the_root_as_one(self):
        self.assertEqual(depth_of("mem1/logs"), 2)

    def test_containment_is_tested_on_whole_segments(self):
        self.assertTrue(is_within("mem1/logs/archive", "mem1/logs"))
        self.assertFalse(is_within("mem1/logsarchive", "mem1/logs"))

    def test_a_negative_file_size_raises(self):
        with self.assertRaises(ValueError):
            validate_tree({"mem1": [f("A.DAT", -1)]})

    def test_a_boolean_file_size_raises(self):
        with self.assertRaises(ValueError):
            validate_tree({"mem1": [f("A.DAT", True)]})

    def test_a_duplicate_file_name_raises(self):
        with self.assertRaises(ValueError):
            validate_tree({"mem1": [f("A.DAT", 1), f("A.DAT", 2)]})

    def test_an_orphan_repository_raises(self):
        with self.assertRaises(ValueError):
            validate_tree({"mem1": [], "mem1/logs/archive": []})

    def test_an_empty_tree_raises(self):
        with self.assertRaises(ValueError):
            validate_tree({})


class TestDirectAndBranchTotals(unittest.TestCase):
    def test_direct_sub_repositories_are_immediate_and_ordered(self):
        self.assertEqual(
            direct_sub_repositories(tree(), "mem1"), ["images", "logs", "spare"]
        )

    def test_a_grandchild_is_not_a_direct_sub_repository(self):
        self.assertNotIn("archive", direct_sub_repositories(tree(), "mem1"))

    def test_direct_octets_exclude_the_sub_repositories(self):
        self.assertEqual(direct_octets(tree(), "mem1/logs"), 2560)

    def test_branch_octets_include_the_sub_repositories(self):
        self.assertEqual(branch_octets(tree(), "mem1/logs"), 6656)

    def test_branch_file_count_walks_the_whole_branch(self):
        self.assertEqual(branch_file_count(tree(), "mem1/logs"), 3)

    def test_a_root_with_no_direct_files_still_has_a_branch_total(self):
        self.assertEqual(direct_octets(tree(), "mem1"), 0)
        self.assertEqual(branch_octets(tree(), "mem1"), 106656)

    def test_totals_for_an_unknown_repository_raise(self):
        with self.assertRaises(ValueError):
            direct_octets(tree(), "mem9")


class TestSummaryReport(unittest.TestCase):
    def test_a_summary_lists_files_and_sub_repositories_with_their_type(self):
        summary = summarize_repository(tree(), "mem1/logs")
        types = sorted({e["type"] for e in summary["entries"]})
        self.assertEqual(types, sorted([TYPE_FILE, TYPE_REPOSITORY]))

    def test_a_summary_counts_files_and_sub_repositories_separately(self):
        summary = summarize_repository(tree(), "mem1/logs")
        self.assertEqual(summary["file_count"], 2)
        self.assertEqual(summary["sub_repository_count"], 1)
        self.assertEqual(summary["object_count"], 3)

    def test_a_sub_repository_entry_carries_no_size(self):
        summary = summarize_repository(tree(), "mem1/logs")
        sub = [e for e in summary["entries"] if e["type"] == TYPE_REPOSITORY][0]
        self.assertIsNone(sub["size_octets"])

    def test_entries_are_deterministically_ordered(self):
        entries = summarize_repository(tree(), "mem1")["entries"]
        keys = [(e["type"], e["name"]) for e in entries]
        self.assertEqual(keys, sorted(keys))

    def test_a_summary_is_shallow_and_says_so(self):
        summary = summarize_repository(tree(), "mem1/logs")
        self.assertEqual(summary["direct_octets"], 2560)
        self.assertEqual(summary["branch_octets"], 6656)
        self.assertTrue(summary_is_shallow(summary))

    def test_a_leaf_repository_summary_is_not_shallow(self):
        self.assertFalse(summary_is_shallow(summarize_repository(tree(), "mem1/images")))

    def test_an_empty_repository_has_its_own_outcome(self):
        summary = summarize_repository(tree(), "mem1/spare")
        self.assertEqual(summary["outcome"], OUTCOME_EMPTY)
        self.assertEqual(summary["object_count"], 0)

    def test_an_unknown_repository_is_a_failure_not_an_empty_summary(self):
        summary = summarize_repository(tree(), "mem9")
        self.assertEqual(summary["outcome"], FAILURE_UNKNOWN)
        self.assertFalse(summary["report_is_authoritative"])

    def test_a_summary_over_the_entry_capacity_is_truncated(self):
        summary = summarize_repository(tree(), "mem1/logs", entry_capacity=2)
        self.assertEqual(summary["outcome"], OUTCOME_TRUNCATED)
        self.assertEqual(summary["listed_count"], 2)
        self.assertEqual(summary["omitted_count"], 1)

    def test_a_truncated_summary_still_counts_every_object(self):
        summary = summarize_repository(tree(), "mem1/logs", entry_capacity=1)
        self.assertEqual(summary["object_count"], 3)
        self.assertEqual(summary["file_count"], 2)
        self.assertEqual(summary["sub_repository_count"], 1)

    def test_a_truncated_summary_still_totals_every_octet(self):
        summary = summarize_repository(tree(), "mem1/logs", entry_capacity=1)
        self.assertEqual(summary["direct_octets"], 2560)

    def test_a_summary_exactly_at_the_capacity_is_complete(self):
        summary = summarize_repository(tree(), "mem1/logs", entry_capacity=3)
        self.assertEqual(summary["outcome"], OUTCOME_COMPLETE)
        self.assertTrue(summary["report_is_authoritative"])

    def test_a_zero_entry_capacity_raises(self):
        with self.assertRaises(ValueError):
            summarize_repository(tree(), "mem1", entry_capacity=0)

    def test_the_default_entry_capacity_is_a_positive_bound(self):
        self.assertGreaterEqual(DEFAULT_ENTRY_CAPACITY, 1)

    def test_a_malformed_summary_raises_when_checked_for_shallowness(self):
        with self.assertRaises(ValueError):
            summary_is_shallow({"file_count": 1})


class TestAdvice(unittest.TestCase):
    def test_a_truncated_summary_is_advised_with_the_omitted_count(self):
        result = assess_summary_request(tree(), "mem1/logs", entry_capacity=1)
        self.assertTrue(any("omitted" in a for a in result["advice"]))

    def test_a_shallow_summary_is_advised_as_one_level_deep(self):
        result = assess_summary_request(tree(), "mem1/logs")
        self.assertTrue(any("one level deep" in a for a in result["advice"]))

    def test_an_empty_repository_is_advised_as_deletable(self):
        result = assess_summary_request(tree(), "mem1/spare")
        self.assertTrue(result["deletable_as_is"])

    def test_a_repository_holding_objects_is_not_deletable_as_is(self):
        self.assertFalse(assess_summary_request(tree(), "mem1/logs")["deletable_as_is"])

    def test_an_unknown_repository_is_advised_as_an_addressing_problem(self):
        result = assess_summary_request(tree(), "mem9")
        self.assertTrue(any("does not exist" in a for a in result["advice"]))

    def test_a_complete_leaf_summary_carries_no_advice(self):
        self.assertEqual(assess_summary_request(tree(), "mem1/images")["advice"], [])


if __name__ == "__main__":
    unittest.main()
