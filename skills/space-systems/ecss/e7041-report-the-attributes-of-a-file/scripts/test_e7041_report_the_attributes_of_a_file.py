"""Contract test for the report-the-attributes-of-a-file leaf (stdlib unittest)."""

import unittest

from e7041_report_the_attributes_of_a_file_logic import (
    FAILURE_FILE_UNKNOWN,
    FAILURE_NAME_IS_A_REPOSITORY,
    FAILURE_REPOSITORY_UNKNOWN,
    MAX_NAME_OCTETS,
    OUTCOME_REPORTED,
    TRANSFER_DOWNLINK,
    TRANSFER_IDLE,
    TRANSFER_UPLINK,
    assess_attribute_requests,
    build_file_system,
    derive_permissions,
    downlink_octets,
    find_repository,
    normalize_repository_path,
    path_depth,
    report_file_attributes,
    report_file_attributes_batch,
    validate_file_record,
    validate_object_name,
    validate_repository,
)


def record(name="EVT-001.DAT", size=2048, locked=False, state=TRANSFER_IDLE, created=10):
    return {
        "name": name,
        "size_octets": size,
        "locked": locked,
        "transfer_state": state,
        "creation_time": created,
    }


def repository(path="mem1/logs", files=None, subs=None):
    return {
        "path": path,
        "files": list(files) if files is not None else [record()],
        "sub_repositories": list(subs) if subs is not None else [],
    }


def sample_system():
    return build_file_system(
        [
            repository(
                "mem1/logs",
                [
                    record("EVT-001.DAT", 2048),
                    record("EVT-002.DAT", 512, locked=True),
                    record("DUMP.BIN", 40960, state=TRANSFER_DOWNLINK),
                ],
                ["archive"],
            ),
            repository("mem1/logs/archive", [record("OLD.DAT", 128)]),
        ]
    )


class TestNameAndPathValidation(unittest.TestCase):
    def test_empty_file_name_raises(self):
        with self.assertRaises(ValueError):
            validate_object_name("")

    def test_name_with_separator_raises(self):
        with self.assertRaises(ValueError):
            validate_object_name("logs/EVT.DAT")

    def test_relative_marker_name_raises(self):
        with self.assertRaises(ValueError):
            validate_object_name("..")

    def test_over_long_name_raises(self):
        with self.assertRaises(ValueError):
            validate_object_name("A" * (MAX_NAME_OCTETS + 1))

    def test_path_is_normalized_to_canonical_form(self):
        self.assertEqual(normalize_repository_path("/mem1/logs/"), "mem1/logs")

    def test_path_with_an_empty_inner_segment_raises(self):
        with self.assertRaises(ValueError):
            normalize_repository_path("mem1//logs")

    def test_path_depth_counts_segments(self):
        self.assertEqual(path_depth("/mem1/logs/archive"), 3)


class TestRecordValidation(unittest.TestCase):
    def test_negative_size_raises(self):
        with self.assertRaises(ValueError):
            validate_file_record(record(size=-1))

    def test_boolean_size_raises(self):
        with self.assertRaises(ValueError):
            validate_file_record(record(size=True))

    def test_unknown_transfer_state_raises(self):
        with self.assertRaises(ValueError):
            validate_file_record(record(state="pending"))

    def test_non_boolean_lock_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_file_record(record(locked="yes"))

    def test_lock_defaults_to_unlocked(self):
        parsed = validate_file_record({"name": "A.DAT", "size_octets": 4})
        self.assertFalse(parsed["locked"])
        self.assertEqual(parsed["transfer_state"], TRANSFER_IDLE)

    def test_zero_octet_file_is_valid(self):
        self.assertEqual(validate_file_record(record(size=0))["size_octets"], 0)

    def test_duplicate_file_names_in_a_repository_raise(self):
        with self.assertRaises(ValueError):
            validate_repository(repository(files=[record("A.DAT"), record("A.DAT")]))

    def test_a_name_used_as_both_file_and_sub_repository_raises(self):
        with self.assertRaises(ValueError):
            validate_repository(repository(files=[record("archive")], subs=["archive"]))

    def test_duplicate_repository_path_raises(self):
        with self.assertRaises(ValueError):
            build_file_system([repository("mem1/logs"), repository("/mem1/logs")])

    def test_empty_file_system_raises(self):
        with self.assertRaises(ValueError):
            build_file_system([])


class TestLookup(unittest.TestCase):
    def test_known_repository_is_found(self):
        self.assertIsNotNone(find_repository(sample_system(), "mem1/logs"))

    def test_lookup_ignores_a_trailing_separator(self):
        self.assertIsNotNone(find_repository(sample_system(), "/mem1/logs/"))

    def test_unknown_repository_is_none(self):
        self.assertIsNone(find_repository(sample_system(), "mem2/logs"))


class TestAttributeReport(unittest.TestCase):
    def test_a_known_file_reports_its_size(self):
        answer = report_file_attributes(sample_system(), "mem1/logs", "EVT-001.DAT")
        self.assertEqual(answer["outcome"], OUTCOME_REPORTED)
        self.assertEqual(answer["attributes"]["size_octets"], 2048)

    def test_report_carries_the_canonical_repository_path(self):
        answer = report_file_attributes(sample_system(), "/mem1/logs", "EVT-001.DAT")
        self.assertEqual(answer["attributes"]["repository_path"], "mem1/logs")

    def test_unknown_repository_is_its_own_failure_code(self):
        answer = report_file_attributes(sample_system(), "mem9/logs", "EVT-001.DAT")
        self.assertEqual(answer["outcome"], FAILURE_REPOSITORY_UNKNOWN)
        self.assertIsNone(answer["attributes"])

    def test_unknown_file_is_a_different_failure_code(self):
        answer = report_file_attributes(sample_system(), "mem1/logs", "GONE.DAT")
        self.assertEqual(answer["outcome"], FAILURE_FILE_UNKNOWN)

    def test_a_sub_repository_name_is_a_third_failure_code(self):
        answer = report_file_attributes(sample_system(), "mem1/logs", "archive")
        self.assertEqual(answer["outcome"], FAILURE_NAME_IS_A_REPOSITORY)

    def test_the_three_failure_codes_are_distinct(self):
        codes = {
            FAILURE_REPOSITORY_UNKNOWN,
            FAILURE_FILE_UNKNOWN,
            FAILURE_NAME_IS_A_REPOSITORY,
        }
        self.assertEqual(len(codes), 3)


class TestDerivedPermissions(unittest.TestCase):
    def test_an_idle_unlocked_file_may_be_deleted(self):
        self.assertTrue(derive_permissions(validate_file_record(record()))["deletable"])

    def test_a_locked_file_may_not_be_deleted(self):
        rights = derive_permissions(validate_file_record(record(locked=True)))
        self.assertFalse(rights["deletable"])
        self.assertFalse(rights["overwritable"])

    def test_a_locked_file_is_still_readable(self):
        self.assertTrue(
            derive_permissions(validate_file_record(record(locked=True)))["readable"]
        )

    def test_an_uplink_in_progress_blocks_a_delete(self):
        rights = derive_permissions(
            validate_file_record(record(state=TRANSFER_UPLINK))
        )
        self.assertFalse(rights["deletable"])
        self.assertTrue(rights["held_by_transfer"])

    def test_a_downlink_in_progress_blocks_a_rename(self):
        rights = derive_permissions(
            validate_file_record(record(state=TRANSFER_DOWNLINK))
        )
        self.assertFalse(rights["renameable"])


class TestBatchAndSummary(unittest.TestCase):
    def test_batch_preserves_request_order(self):
        answers = report_file_attributes_batch(
            sample_system(),
            [
                {"repository_path": "mem1/logs", "file_name": "DUMP.BIN"},
                {"repository_path": "mem1/logs", "file_name": "EVT-001.DAT"},
            ],
        )
        self.assertEqual(
            [a["file_name"] for a in answers], ["DUMP.BIN", "EVT-001.DAT"]
        )

    def test_batch_requires_a_list(self):
        with self.assertRaises(ValueError):
            report_file_attributes_batch(sample_system(), "mem1/logs")

    def test_downlink_octets_ignores_failed_answers(self):
        answers = report_file_attributes_batch(
            sample_system(),
            [
                {"repository_path": "mem1/logs", "file_name": "EVT-001.DAT"},
                {"repository_path": "mem9/logs", "file_name": "EVT-001.DAT"},
            ],
        )
        self.assertEqual(downlink_octets(answers), 2048)

    def test_summary_groups_failures_by_code(self):
        result = assess_attribute_requests(
            [
                repository(
                    "mem1/logs",
                    [record("EVT-001.DAT", 2048), record("EVT-002.DAT", 512, True)],
                    ["archive"],
                )
            ],
            [
                {"repository_path": "mem1/logs", "file_name": "EVT-001.DAT"},
                {"repository_path": "mem1/logs", "file_name": "EVT-002.DAT"},
                {"repository_path": "mem1/logs", "file_name": "archive"},
                {"repository_path": "mem4/logs", "file_name": "EVT-001.DAT"},
                {"repository_path": "mem1/logs", "file_name": "GONE.DAT"},
            ],
        )
        self.assertEqual(result["reported_count"], 2)
        self.assertEqual(result["failed_count"], 3)
        self.assertEqual(
            sorted(result["failures_by_code"]),
            sorted(
                [
                    FAILURE_FILE_UNKNOWN,
                    FAILURE_NAME_IS_A_REPOSITORY,
                    FAILURE_REPOSITORY_UNKNOWN,
                ]
            ),
        )
        self.assertEqual(result["downlink_octets"], 2560)
        self.assertEqual(result["locked_count"], 1)
        self.assertFalse(result["all_reported"])

    def test_a_clean_request_set_reports_all_reported(self):
        result = assess_attribute_requests(
            [repository("mem1/logs", [record("A.DAT", 16)])],
            [{"repository_path": "mem1/logs", "file_name": "A.DAT"}],
        )
        self.assertTrue(result["all_reported"])
        self.assertEqual(result["held_count"], 0)


if __name__ == "__main__":
    unittest.main()
