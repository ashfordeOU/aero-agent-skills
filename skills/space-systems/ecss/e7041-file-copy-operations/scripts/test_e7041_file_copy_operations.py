"""Contract tests for the clause 6.23.5.2 file copy operation logic."""

import copy
import unittest

from e7041_file_copy_operations_logic import (
    DEFAULT_LIST_CAPACITY,
    admit_copy_request,
    advance_copy,
    assess_copy_campaign,
    copy_key,
    copy_progress_fraction,
    new_copy_list,
    refusal_reason,
    repository_free_octets,
    repository_used_octets,
    status_report,
    validate_filesystem,
    validate_identifier,
    validate_repository,
)

FILESYSTEM = {
    "mass-memory": {
        "capacity_octets": 10000,
        "files": {"housekeeping.dat": 1200, "event-log.dat": 800},
    },
    "downlink-buffer": {"capacity_octets": 4000, "files": {}},
    "tiny-scratch": {"capacity_octets": 500, "files": {}},
}


def a_filesystem():
    return copy.deepcopy(FILESYSTEM)


def a_request(**overrides):
    request = {
        "source_repository": "mass-memory",
        "source_file": "housekeeping.dat",
        "target_repository": "downlink-buffer",
        "target_file": "housekeeping.dat",
    }
    request.update(overrides)
    return request


class IdentifierTests(unittest.TestCase):
    def test_plain_name_accepted(self):
        self.assertEqual(validate_identifier("mass-memory", "repository"), "mass-memory")

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("", "repository")

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("   ", "repository")

    def test_padded_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(" mass-memory", "repository")

    def test_non_string_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(7, "repository")


class RepositoryTests(unittest.TestCase):
    def test_used_octets_is_the_sum_of_file_sizes(self):
        self.assertEqual(repository_used_octets(FILESYSTEM["mass-memory"]), 2000)

    def test_free_octets_is_capacity_less_used(self):
        self.assertEqual(repository_free_octets(FILESYSTEM["mass-memory"]), 8000)

    def test_empty_repository_is_entirely_free(self):
        self.assertEqual(repository_free_octets(FILESYSTEM["downlink-buffer"]), 4000)

    def test_zero_capacity_repository_rejected(self):
        with self.assertRaises(ValueError):
            validate_repository({"capacity_octets": 0, "files": {}})

    def test_overfull_repository_rejected(self):
        with self.assertRaises(ValueError):
            validate_repository({"capacity_octets": 100, "files": {"big.dat": 200}})

    def test_negative_file_size_rejected(self):
        with self.assertRaises(ValueError):
            validate_repository({"capacity_octets": 100, "files": {"odd.dat": -1}})

    def test_missing_files_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_repository({"capacity_octets": 100})

    def test_empty_filesystem_rejected(self):
        with self.assertRaises(ValueError):
            validate_filesystem({})


class CopyKeyTests(unittest.TestCase):
    def test_key_is_the_four_part_pair_of_paths(self):
        self.assertEqual(
            copy_key("a", "b", "c", "d"),
            ("a", "b", "c", "d"),
        )

    def test_key_rejects_an_empty_part(self):
        with self.assertRaises(ValueError):
            copy_key("a", "", "c", "d")


class ListTests(unittest.TestCase):
    def test_new_list_is_empty(self):
        state = new_copy_list()
        self.assertEqual(state["operations"], [])
        self.assertEqual(state["capacity"], DEFAULT_LIST_CAPACITY)

    def test_zero_capacity_list_rejected(self):
        with self.assertRaises(ValueError):
            new_copy_list(0)

    def test_non_integer_capacity_rejected(self):
        with self.assertRaises(ValueError):
            new_copy_list(2.5)


class AdmissionTests(unittest.TestCase):
    def test_valid_request_is_admitted(self):
        state = new_copy_list()
        fs = a_filesystem()
        self.assertIsNone(refusal_reason(state, fs, a_request()))
        entry = admit_copy_request(state, fs, a_request())
        self.assertEqual(entry["octets_total"], 1200)
        self.assertEqual(entry["octets_copied"], 0)
        self.assertEqual(entry["state"], "running")

    def test_unknown_source_repository_refused(self):
        state = new_copy_list()
        reason = refusal_reason(state, a_filesystem(), a_request(source_repository="nowhere"))
        self.assertIn("source repository", reason)

    def test_missing_source_file_refused(self):
        state = new_copy_list()
        reason = refusal_reason(state, a_filesystem(), a_request(source_file="absent.dat"))
        self.assertIn("does not exist", reason)

    def test_unknown_target_repository_refused(self):
        state = new_copy_list()
        reason = refusal_reason(state, a_filesystem(), a_request(target_repository="nowhere"))
        self.assertIn("target repository", reason)

    def test_copy_onto_itself_refused(self):
        state = new_copy_list()
        reason = refusal_reason(
            state,
            a_filesystem(),
            a_request(target_repository="mass-memory", target_file="housekeeping.dat"),
        )
        self.assertIn("same file", reason)

    def test_existing_target_file_refused(self):
        state = new_copy_list()
        reason = refusal_reason(
            state,
            a_filesystem(),
            a_request(
                source_file="event-log.dat",
                target_repository="mass-memory",
                target_file="housekeeping.dat",
            ),
        )
        self.assertIn("already exists", reason)

    def test_duplicate_operation_refused(self):
        state = new_copy_list()
        fs = a_filesystem()
        admit_copy_request(state, fs, a_request())
        reason = refusal_reason(state, fs, a_request())
        self.assertIn("already in the copy operation list", reason)

    def test_second_writer_of_the_same_target_refused(self):
        state = new_copy_list()
        fs = a_filesystem()
        admit_copy_request(state, fs, a_request())
        reason = refusal_reason(state, fs, a_request(source_file="event-log.dat"))
        self.assertIn("already writing", reason)

    def test_target_without_room_refused(self):
        state = new_copy_list()
        reason = refusal_reason(
            state, a_filesystem(), a_request(target_repository="tiny-scratch")
        )
        self.assertIn("octets free", reason)

    def test_room_accounts_for_octets_already_landed(self):
        state = new_copy_list()
        fs = a_filesystem()
        fs["downlink-buffer"]["capacity_octets"] = 1500
        admit_copy_request(state, fs, a_request())
        advance_copy(state, fs, copy_key("mass-memory", "housekeeping.dat",
                                         "downlink-buffer", "housekeeping.dat"), 1000)
        reason = refusal_reason(
            state, fs, a_request(source_file="event-log.dat", target_file="event-log.dat")
        )
        self.assertIn("octets free", reason)

    def test_full_list_refuses_further_requests(self):
        state = new_copy_list(1)
        fs = a_filesystem()
        admit_copy_request(state, fs, a_request())
        reason = refusal_reason(
            state, fs, a_request(source_file="event-log.dat", target_file="event-log.dat")
        )
        self.assertIn("already holds its", reason)

    def test_admitting_a_refused_request_raises(self):
        state = new_copy_list()
        with self.assertRaises(ValueError):
            admit_copy_request(state, a_filesystem(), a_request(source_file="absent.dat"))

    def test_malformed_request_rejected(self):
        state = new_copy_list()
        with self.assertRaises(ValueError):
            refusal_reason(state, a_filesystem(), {"source_repository": "mass-memory"})


class ProgressTests(unittest.TestCase):
    def _started(self):
        state = new_copy_list()
        fs = a_filesystem()
        admit_copy_request(state, fs, a_request())
        return state, fs, copy_key(
            "mass-memory", "housekeeping.dat", "downlink-buffer", "housekeeping.dat"
        )

    def test_partial_advance_does_not_complete(self):
        state, fs, key = self._started()
        result = advance_copy(state, fs, key, 400)
        self.assertFalse(result["completed"])
        self.assertEqual(result["entry"]["octets_copied"], 400)

    def test_progress_fraction_tracks_the_octets(self):
        state, fs, key = self._started()
        advance_copy(state, fs, key, 300)
        self.assertAlmostEqual(copy_progress_fraction(state["operations"][0]), 0.25, places=9)

    def test_full_advance_completes_and_creates_the_target_file(self):
        state, fs, key = self._started()
        result = advance_copy(state, fs, key, 1200)
        self.assertTrue(result["completed"])
        self.assertEqual(fs["downlink-buffer"]["files"]["housekeeping.dat"], 1200)
        self.assertEqual(state["operations"], [])

    def test_source_file_is_left_in_place_by_a_copy(self):
        state, fs, key = self._started()
        advance_copy(state, fs, key, 1200)
        self.assertEqual(fs["mass-memory"]["files"]["housekeeping.dat"], 1200)

    def test_advance_past_the_file_size_rejected(self):
        state, fs, key = self._started()
        with self.assertRaises(ValueError):
            advance_copy(state, fs, key, 1201)

    def test_zero_octet_advance_rejected(self):
        state, fs, key = self._started()
        with self.assertRaises(ValueError):
            advance_copy(state, fs, key, 0)

    def test_advance_of_an_unknown_operation_rejected(self):
        state, fs, _ = self._started()
        with self.assertRaises(ValueError):
            advance_copy(state, fs, copy_key("mass-memory", "event-log.dat",
                                             "downlink-buffer", "event-log.dat"), 10)

    def test_progress_fraction_needs_a_positive_total(self):
        with self.assertRaises(ValueError):
            copy_progress_fraction({"octets_total": 0, "octets_copied": 0})


class ReportTests(unittest.TestCase):
    def test_report_counts_free_entries(self):
        state = new_copy_list(3)
        fs = a_filesystem()
        admit_copy_request(state, fs, a_request())
        report = status_report(state)
        self.assertEqual(report["in_progress"], 1)
        self.assertEqual(report["free_entries"], 2)

    def test_report_names_both_ends_of_each_operation(self):
        state = new_copy_list()
        fs = a_filesystem()
        admit_copy_request(state, fs, a_request())
        row = status_report(state)["operations"][0]
        self.assertEqual(row["source"], "mass-memory/housekeeping.dat")
        self.assertEqual(row["target"], "downlink-buffer/housekeeping.dat")

    def test_empty_report_has_no_rows(self):
        self.assertEqual(status_report(new_copy_list())["operations"], [])


class CampaignTests(unittest.TestCase):
    def test_campaign_admits_the_good_requests(self):
        result = assess_copy_campaign(
            {
                "filesystem": a_filesystem(),
                "requests": [
                    a_request(),
                    a_request(source_file="event-log.dat", target_file="event-log.dat"),
                ],
            }
        )
        self.assertEqual(len(result["accepted"]), 2)
        self.assertEqual(result["refused"], [])

    def test_campaign_records_each_refusal_reason(self):
        result = assess_copy_campaign(
            {
                "filesystem": a_filesystem(),
                "requests": [a_request(), a_request()],
            }
        )
        self.assertEqual(len(result["accepted"]), 1)
        self.assertEqual(len(result["refused"]), 1)
        self.assertIn("already in the copy operation list", result["refused"][0]["reason"])

    def test_duplicate_raises_a_finding(self):
        result = assess_copy_campaign(
            {"filesystem": a_filesystem(), "requests": [a_request(), a_request()]}
        )
        self.assertTrue(any("duplicate copy request" in f for f in result["findings"]))

    def test_full_list_raises_a_finding(self):
        result = assess_copy_campaign(
            {
                "filesystem": a_filesystem(),
                "requests": [a_request()],
                "list_capacity": 1,
            }
        )
        self.assertTrue(any("list is full" in f for f in result["findings"]))

    def test_campaign_with_no_admission_is_flagged(self):
        result = assess_copy_campaign(
            {"filesystem": a_filesystem(), "requests": [a_request(source_file="absent.dat")]}
        )
        self.assertIn("no copy request in the campaign was admitted", result["findings"])

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_copy_campaign({"filesystem": a_filesystem()})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_copy_campaign(["filesystem"])

    def test_non_sequence_requests_rejected(self):
        with self.assertRaises(ValueError):
            assess_copy_campaign({"filesystem": a_filesystem(), "requests": a_request()})


if __name__ == "__main__":
    unittest.main()
