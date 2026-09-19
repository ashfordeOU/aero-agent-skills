"""Contract test for the find-files leaf (stdlib unittest)."""

import unittest

from e7041_find_files_logic import (
    DEFAULT_REPORT_CAPACITY,
    FAILURE_REPOSITORY_UNKNOWN,
    MAX_NAME_OCTETS,
    OUTCOME_COMPLETE,
    OUTCOME_NO_MATCH,
    OUTCOME_TRUNCATED,
    assess_search_request,
    build_file_system,
    find_files,
    is_under,
    normalize_repository_path,
    pattern_is_unbounded,
    pattern_matches,
    repositories_in_scope,
    validate_name,
    validate_pattern,
    validate_repository,
)


def repositories():
    return [
        {"path": "mem1/logs", "files": ["EVT-001.DAT", "EVT-002.DAT", "HK.BIN"]},
        {"path": "mem1/logs/archive", "files": ["EVT-900.DAT", "NOTES.TXT"]},
        {"path": "mem1/images", "files": ["IMG-01.RAW"]},
    ]


def system():
    return build_file_system(repositories())


class TestValidation(unittest.TestCase):
    def test_a_stored_name_may_not_hold_a_wildcard(self):
        with self.assertRaises(ValueError):
            validate_name("EVT-*.DAT")

    def test_over_long_stored_name_raises(self):
        with self.assertRaises(ValueError):
            validate_name("A" * (MAX_NAME_OCTETS + 1))

    def test_a_pattern_crossing_a_separator_raises(self):
        with self.assertRaises(ValueError):
            validate_pattern("archive/EVT-*.DAT")

    def test_an_empty_pattern_raises(self):
        with self.assertRaises(ValueError):
            validate_pattern("   ")

    def test_path_is_normalized(self):
        self.assertEqual(normalize_repository_path("/mem1/logs/"), "mem1/logs")

    def test_path_with_an_empty_inner_segment_raises(self):
        with self.assertRaises(ValueError):
            normalize_repository_path("mem1//logs")

    def test_duplicate_file_name_in_a_repository_raises(self):
        with self.assertRaises(ValueError):
            validate_repository({"path": "mem1/logs", "files": ["A.DAT", "A.DAT"]})

    def test_duplicate_repository_path_raises(self):
        with self.assertRaises(ValueError):
            build_file_system(
                [{"path": "mem1/logs", "files": []}, {"path": "/mem1/logs", "files": []}]
            )


class TestWildcardMatching(unittest.TestCase):
    def test_a_literal_pattern_matches_only_itself(self):
        self.assertTrue(pattern_matches("HK.BIN", "HK.BIN"))
        self.assertFalse(pattern_matches("HK.BIN", "HK.BIN.OLD"))

    def test_the_any_run_wildcard_matches_a_run(self):
        self.assertTrue(pattern_matches("EVT-*.DAT", "EVT-001.DAT"))

    def test_the_any_run_wildcard_matches_nothing_at_all(self):
        self.assertTrue(pattern_matches("HK*.BIN", "HK.BIN"))

    def test_the_single_character_wildcard_matches_exactly_one(self):
        self.assertTrue(pattern_matches("HK?BIN", "HK.BIN"))
        self.assertFalse(pattern_matches("HK?BIN", "HKBIN"))

    def test_several_any_run_wildcards_backtrack_correctly(self):
        self.assertTrue(pattern_matches("*-*-*", "A-B-C"))
        self.assertFalse(pattern_matches("*-*-*-*", "A-B-C"))

    def test_a_trailing_any_run_wildcard_absorbs_the_tail(self):
        self.assertTrue(pattern_matches("EVT*", "EVT-001.DAT"))

    def test_matching_is_case_sensitive(self):
        self.assertFalse(pattern_matches("evt-*.dat", "EVT-001.DAT"))

    def test_a_wildcard_only_pattern_is_unbounded(self):
        self.assertTrue(pattern_is_unbounded("*"))
        self.assertTrue(pattern_is_unbounded("**"))
        self.assertFalse(pattern_is_unbounded("EVT*"))

    def test_matching_an_empty_name_raises(self):
        with self.assertRaises(ValueError):
            pattern_matches("*", "")


class TestScope(unittest.TestCase):
    def test_a_repository_is_under_itself(self):
        self.assertTrue(is_under("mem1/logs", "mem1/logs"))

    def test_a_sub_repository_is_under_its_parent(self):
        self.assertTrue(is_under("mem1/logs/archive", "mem1/logs"))

    def test_a_sibling_sharing_a_prefix_is_not_under_it(self):
        self.assertFalse(is_under("mem1/logsarchive", "mem1/logs"))

    def test_a_non_recursive_search_walks_one_repository(self):
        self.assertEqual(repositories_in_scope(system(), "mem1/logs", False), ["mem1/logs"])

    def test_a_recursive_search_walks_the_sub_repositories(self):
        self.assertEqual(
            repositories_in_scope(system(), "mem1/logs", True),
            ["mem1/logs", "mem1/logs/archive"],
        )

    def test_scope_of_an_unknown_repository_raises(self):
        with self.assertRaises(ValueError):
            repositories_in_scope(system(), "mem9/logs", True)

    def test_a_non_boolean_recursion_flag_raises(self):
        with self.assertRaises(ValueError):
            repositories_in_scope(system(), "mem1/logs", "yes")


class TestSearch(unittest.TestCase):
    def test_a_non_recursive_search_does_not_reach_a_sub_repository(self):
        result = find_files(system(), "mem1/logs", "EVT-*.DAT")
        self.assertEqual(result["outcome"], OUTCOME_COMPLETE)
        self.assertEqual(result["match_count"], 2)
        self.assertEqual(result["repositories_searched"], 1)

    def test_a_recursive_search_reaches_the_sub_repository(self):
        result = find_files(system(), "mem1/logs", "EVT-*.DAT", recursive=True)
        self.assertEqual(result["match_count"], 3)
        self.assertEqual(result["repositories_searched"], 2)

    def test_every_entry_carries_its_repository_path(self):
        result = find_files(system(), "mem1/logs", "EVT-*.DAT", recursive=True)
        self.assertEqual(
            result["entries"][-1],
            {"repository_path": "mem1/logs/archive", "file_name": "EVT-900.DAT"},
        )

    def test_entries_are_sorted_by_path_then_name(self):
        entries = find_files(system(), "mem1", "*", recursive=True)["entries"]
        keys = [(e["repository_path"], e["file_name"]) for e in entries]
        self.assertEqual(keys, sorted(keys))

    def test_a_search_matching_nothing_has_its_own_outcome(self):
        result = find_files(system(), "mem1/logs", "TM-*.PKT")
        self.assertEqual(result["outcome"], OUTCOME_NO_MATCH)
        self.assertEqual(result["entries"], [])

    def test_an_unknown_root_repository_is_a_failure_not_an_empty_result(self):
        result = find_files(system(), "mem9/logs", "*")
        self.assertEqual(result["outcome"], FAILURE_REPOSITORY_UNKNOWN)
        self.assertEqual(result["match_count"], 0)

    def test_a_search_over_the_capacity_reports_truncated(self):
        result = find_files(system(), "mem1/logs", "*", report_capacity=2)
        self.assertEqual(result["outcome"], OUTCOME_TRUNCATED)
        self.assertEqual(result["reported_count"], 2)
        self.assertEqual(result["match_count"], 3)
        self.assertEqual(result["omitted_count"], 1)

    def test_a_search_exactly_at_the_capacity_is_complete(self):
        result = find_files(system(), "mem1/logs", "*", report_capacity=3)
        self.assertEqual(result["outcome"], OUTCOME_COMPLETE)
        self.assertEqual(result["omitted_count"], 0)

    def test_a_zero_report_capacity_raises(self):
        with self.assertRaises(ValueError):
            find_files(system(), "mem1/logs", "*", report_capacity=0)

    def test_the_default_report_capacity_is_a_positive_bound(self):
        self.assertGreaterEqual(DEFAULT_REPORT_CAPACITY, 1)


class TestAdvice(unittest.TestCase):
    def test_a_truncated_search_is_not_authoritative(self):
        result = assess_search_request(
            repositories(),
            {"root_path": "mem1/logs", "pattern": "*", "report_capacity": 1},
        )
        self.assertFalse(result["report_is_authoritative"])
        self.assertTrue(any("narrow the pattern" in a for a in result["advice"]))

    def test_a_truncated_unbounded_search_is_called_out_as_never_narrowed(self):
        result = assess_search_request(
            repositories(),
            {"root_path": "mem1/logs", "pattern": "*", "report_capacity": 1},
        )
        self.assertTrue(any("matches every name" in a for a in result["advice"]))

    def test_a_truncated_narrow_search_is_not_called_unbounded(self):
        result = assess_search_request(
            repositories(),
            {"root_path": "mem1/logs", "pattern": "EVT-*", "report_capacity": 1},
        )
        self.assertEqual(result["outcome"], OUTCOME_TRUNCATED)
        self.assertFalse(any("matches every name" in a for a in result["advice"]))

    def test_a_complete_search_is_authoritative_and_silent(self):
        result = assess_search_request(
            repositories(), {"root_path": "mem1/images", "pattern": "IMG-*.RAW"}
        )
        self.assertTrue(result["report_is_authoritative"])
        self.assertEqual(result["advice"], [])

    def test_an_unknown_root_is_advised_as_an_addressing_problem(self):
        result = assess_search_request(
            repositories(), {"root_path": "mem9/logs", "pattern": "*"}
        )
        self.assertTrue(any("does not exist" in a for a in result["advice"]))

    def test_a_request_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_search_request(repositories(), ["mem1/logs", "*"])


if __name__ == "__main__":
    unittest.main()
