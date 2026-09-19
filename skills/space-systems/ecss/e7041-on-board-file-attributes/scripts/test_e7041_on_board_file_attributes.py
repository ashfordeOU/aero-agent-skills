"""Contract tests for the clause 6.23.3.4 on-board file attribute logic."""

import unittest

from e7041_on_board_file_attributes_logic import (
    DEFAULT_NEAR_FULL_RATIO,
    FILE_ATTRIBUTE_FIELDS,
    MAX_NAME_CHARS,
    OCCUPANCY_TOLERANCE,
    assess_file_attributes,
    may_delete,
    may_write,
    occupancy_ratio,
    remaining_octets,
    set_lock,
    validate_file_attributes,
    validate_file_name,
    validate_repository_path,
)


def record(name="hk001", repository="/repo1/housekeeping", size=400,
           allocated=1000, locked=False):
    return {
        "repository_path": repository,
        "file_name": name,
        "size_octets": size,
        "allocated_octets": allocated,
        "locked": locked,
    }


class NameTests(unittest.TestCase):
    def test_a_plain_name_is_accepted(self):
        self.assertEqual(validate_file_name("hk001"), "hk001")

    def test_an_empty_name_is_refused(self):
        with self.assertRaises(ValueError):
            validate_file_name("")

    def test_a_name_carrying_a_separator_is_refused(self):
        with self.assertRaises(ValueError):
            validate_file_name("dir/hk001")

    def test_a_padded_name_is_refused(self):
        with self.assertRaises(ValueError):
            validate_file_name(" hk001")

    def test_a_name_past_the_length_limit_is_refused(self):
        with self.assertRaises(ValueError):
            validate_file_name("x" * (MAX_NAME_CHARS + 1))

    def test_a_non_string_name_is_refused(self):
        with self.assertRaises(ValueError):
            validate_file_name(1001)


class RepositoryPathTests(unittest.TestCase):
    def test_a_rooted_repository_path_is_accepted(self):
        self.assertEqual(validate_repository_path("/repo1/hk"), "/repo1/hk")

    def test_an_unrooted_path_is_refused(self):
        with self.assertRaises(ValueError):
            validate_repository_path("repo1/hk")

    def test_a_trailing_separator_is_refused(self):
        with self.assertRaises(ValueError):
            validate_repository_path("/repo1/hk/")

    def test_an_empty_component_is_refused(self):
        with self.assertRaises(ValueError):
            validate_repository_path("/repo1//hk")


class RecordTests(unittest.TestCase):
    def test_the_record_carries_the_five_attributes(self):
        normalised = validate_file_attributes(record())
        self.assertEqual(
            tuple(sorted(normalised)), tuple(sorted(FILE_ATTRIBUTE_FIELDS))
        )

    def test_an_empty_file_is_a_valid_record(self):
        self.assertEqual(validate_file_attributes(record(size=0))["size_octets"], 0)

    def test_a_file_exactly_at_its_allocation_is_valid(self):
        self.assertEqual(
            validate_file_attributes(record(size=1000))["size_octets"], 1000
        )

    def test_a_size_past_the_allocation_is_refused(self):
        with self.assertRaises(ValueError):
            validate_file_attributes(record(size=1001))

    def test_a_zero_allocation_is_refused(self):
        with self.assertRaises(ValueError):
            validate_file_attributes(record(allocated=0))

    def test_a_non_boolean_lock_is_refused(self):
        with self.assertRaises(ValueError):
            validate_file_attributes(record(locked="yes"))

    def test_a_missing_attribute_is_refused(self):
        broken = record()
        del broken["allocated_octets"]
        with self.assertRaises(ValueError):
            validate_file_attributes(broken)


class DerivedTests(unittest.TestCase):
    def test_remaining_room_is_the_allocation_less_the_size(self):
        self.assertEqual(remaining_octets(record(size=400, allocated=1000)), 600)

    def test_a_full_file_has_no_room_left(self):
        self.assertEqual(remaining_octets(record(size=1000, allocated=1000)), 0)

    def test_occupancy_is_the_size_over_the_allocation(self):
        self.assertAlmostEqual(
            occupancy_ratio(record(size=400, allocated=1000)), 0.4, places=9
        )

    def test_an_empty_file_has_zero_occupancy(self):
        self.assertAlmostEqual(occupancy_ratio(record(size=0)), 0.0, places=9)

    def test_a_full_file_has_unit_occupancy(self):
        self.assertAlmostEqual(
            occupancy_ratio(record(size=1000, allocated=1000)), 1.0, places=9
        )


class WriteTests(unittest.TestCase):
    def test_a_write_inside_the_allocation_is_permitted(self):
        verdict = may_write(record(size=400, allocated=1000), 100)
        self.assertTrue(verdict["permitted"])
        self.assertEqual(verdict["resulting_size_octets"], 500)

    def test_a_write_exactly_filling_the_allocation_is_permitted(self):
        verdict = may_write(record(size=400, allocated=1000), 600)
        self.assertTrue(verdict["permitted"])
        self.assertEqual(verdict["resulting_size_octets"], 1000)

    def test_a_write_one_octet_past_the_allocation_is_refused(self):
        verdict = may_write(record(size=400, allocated=1000), 601)
        self.assertFalse(verdict["permitted"])

    def test_a_write_to_a_locked_file_is_refused(self):
        verdict = may_write(record(locked=True), 1)
        self.assertFalse(verdict["permitted"])
        self.assertIn("locked", verdict["reason"])

    def test_a_zero_length_write_is_refused(self):
        with self.assertRaises(ValueError):
            may_write(record(), 0)


class DeleteAndLockTests(unittest.TestCase):
    def test_an_unlocked_file_may_be_deleted(self):
        self.assertTrue(may_delete(record())["permitted"])

    def test_a_locked_file_may_not_be_deleted(self):
        self.assertFalse(may_delete(record(locked=True))["permitted"])

    def test_locking_changes_only_the_lock(self):
        locked = set_lock(record(size=400), True)
        self.assertTrue(locked["locked"])
        self.assertEqual(locked["size_octets"], 400)

    def test_unlocking_restores_the_write(self):
        unlocked = set_lock(record(locked=True), False)
        self.assertTrue(may_write(unlocked, 1)["permitted"])

    def test_a_non_boolean_lock_target_is_refused(self):
        with self.assertRaises(ValueError):
            set_lock(record(), "locked")


class AssessmentTests(unittest.TestCase):
    def _spec(self, **over):
        spec = {
            "files": [
                record(name="hk001", size=400, allocated=1000),
                record(name="hk002", size=950, allocated=1000),
                record(name="ev001", size=100, allocated=500, locked=True),
            ]
        }
        spec.update(over)
        return spec

    def test_totals_are_summed_across_the_repository(self):
        result = assess_file_attributes(self._spec())
        self.assertEqual(result["file_count"], 3)
        self.assertEqual(result["total_size_octets"], 1450)
        self.assertEqual(result["total_allocated_octets"], 2500)
        self.assertEqual(result["total_remaining_octets"], 1050)

    def test_overall_occupancy_is_reported(self):
        result = assess_file_attributes(self._spec())
        self.assertAlmostEqual(result["overall_occupancy"], 0.58, places=9)

    def test_near_full_files_are_named(self):
        result = assess_file_attributes(self._spec())
        self.assertEqual(len(result["near_full"]), 1)
        self.assertFalse(result["clean"])

    def test_a_file_exactly_on_the_threshold_counts_as_near_full(self):
        spec = self._spec(files=[record(size=900, allocated=1000)])
        result = assess_file_attributes(spec)
        self.assertEqual(len(result["near_full"]), 1)

    def test_locked_files_are_named(self):
        result = assess_file_attributes(self._spec())
        self.assertEqual(len(result["locked"]), 1)

    def test_a_pending_write_reports_the_files_it_cannot_land_on(self):
        result = assess_file_attributes(self._spec(pending_write_octets=100))
        self.assertEqual(len(result["write_blocked"]), 2)

    def test_the_default_threshold_is_a_fraction_below_one(self):
        self.assertLess(DEFAULT_NEAR_FULL_RATIO, 1.0)
        self.assertGreater(DEFAULT_NEAR_FULL_RATIO, OCCUPANCY_TOLERANCE)

    def test_a_threshold_above_unity_is_refused(self):
        with self.assertRaises(ValueError):
            assess_file_attributes(self._spec(near_full_ratio=1.5))

    def test_a_duplicate_file_is_refused(self):
        spec = self._spec(files=[record(name="hk001"), record(name="hk001")])
        with self.assertRaises(ValueError):
            assess_file_attributes(spec)

    def test_missing_files_key_is_refused(self):
        with self.assertRaises(ValueError):
            assess_file_attributes({})

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_file_attributes(["files"])


if __name__ == "__main__":
    unittest.main()
