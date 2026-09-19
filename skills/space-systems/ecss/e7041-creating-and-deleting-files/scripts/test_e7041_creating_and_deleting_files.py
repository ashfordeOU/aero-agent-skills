"""Contract tests for the clause 6.23.4.1 file create and delete logic."""

import unittest

from e7041_creating_and_deleting_files_logic import (
    MAX_NAME_CHARS,
    OPERATIONS,
    apply_operations,
    assess_file_operations,
    build_repository,
    create_file,
    delete_file,
    free_octets,
    reserved_octets,
    validate_file_name,
)


def repository(**over):
    spec = {
        "path": "/repo1",
        "capacity_octets": 10000,
        "max_file_octets": 4000,
        "max_files": 4,
        "files": {
            "hk001": {"allocated_octets": 2000, "locked": False, "open": False},
            "hk002": {"allocated_octets": 1000, "locked": True, "open": False},
            "ev001": {"allocated_octets": 1000, "locked": False, "open": True},
        },
    }
    spec.update(over)
    return spec


class NameTests(unittest.TestCase):
    def test_a_plain_name_is_accepted(self):
        self.assertEqual(validate_file_name("hk003"), "hk003")

    def test_an_empty_name_is_refused(self):
        with self.assertRaises(ValueError):
            validate_file_name("")

    def test_a_name_with_a_separator_is_refused(self):
        with self.assertRaises(ValueError):
            validate_file_name("sub/hk003")

    def test_a_name_past_the_length_limit_is_refused(self):
        with self.assertRaises(ValueError):
            validate_file_name("x" * (MAX_NAME_CHARS + 1))

    def test_a_padded_name_is_refused(self):
        with self.assertRaises(ValueError):
            validate_file_name("hk003 ")


class RepositoryTests(unittest.TestCase):
    def test_reserved_octets_sum_the_allocations(self):
        self.assertEqual(reserved_octets(build_repository(repository())), 4000)

    def test_free_octets_are_the_capacity_less_the_reservations(self):
        self.assertEqual(free_octets(build_repository(repository())), 6000)

    def test_an_unrooted_repository_path_is_refused(self):
        with self.assertRaises(ValueError):
            build_repository(repository(path="repo1"))

    def test_a_per_file_ceiling_above_the_capacity_is_refused(self):
        with self.assertRaises(ValueError):
            build_repository(repository(capacity_octets=1000, max_file_octets=4000))

    def test_declared_files_reserving_past_the_capacity_are_refused(self):
        with self.assertRaises(ValueError):
            build_repository(repository(capacity_octets=3000))

    def test_a_declared_file_above_the_per_file_ceiling_is_refused(self):
        with self.assertRaises(ValueError):
            build_repository(repository(max_file_octets=1500))

    def test_a_non_boolean_lock_on_a_declared_file_is_refused(self):
        spec = repository()
        spec["files"]["hk001"]["locked"] = "yes"
        with self.assertRaises(ValueError):
            build_repository(spec)

    def test_a_missing_repository_key_is_refused(self):
        spec = repository()
        del spec["max_files"]
        with self.assertRaises(ValueError):
            build_repository(spec)


class CreateTests(unittest.TestCase):
    def setUp(self):
        self.repo = build_repository(repository())

    def test_a_create_inside_the_free_space_is_accepted(self):
        state, verdict = create_file(self.repo, "hk003", 2000)
        self.assertTrue(verdict["accepted"])
        self.assertIn("hk003", state["files"])
        self.assertEqual(free_octets(state), 4000)

    def test_a_new_file_starts_unlocked_and_closed(self):
        state, _ = create_file(self.repo, "hk003", 100)
        self.assertFalse(state["files"]["hk003"]["locked"])
        self.assertFalse(state["files"]["hk003"]["open"])

    def test_a_duplicate_name_is_refused(self):
        state, verdict = create_file(self.repo, "hk001", 100)
        self.assertFalse(verdict["accepted"])
        self.assertEqual(reserved_octets(state), 4000)

    def test_an_allocation_past_the_per_file_ceiling_is_refused(self):
        _, verdict = create_file(self.repo, "hk003", 4001)
        self.assertFalse(verdict["accepted"])
        self.assertIn("per-file ceiling", verdict["reason"])

    def test_an_allocation_past_the_free_space_is_refused(self):
        repo = build_repository(repository(capacity_octets=4500))
        _, verdict = create_file(repo, "hk003", 1000)
        self.assertFalse(verdict["accepted"])
        self.assertIn("free", verdict["reason"])

    def test_an_allocation_exactly_filling_the_free_space_is_accepted(self):
        repo = build_repository(repository(capacity_octets=5000))
        state, verdict = create_file(repo, "hk003", 1000)
        self.assertTrue(verdict["accepted"])
        self.assertEqual(free_octets(state), 0)

    def test_a_repository_at_its_file_limit_refuses_a_create(self):
        repo = build_repository(repository(max_files=3))
        _, verdict = create_file(repo, "hk003", 100)
        self.assertFalse(verdict["accepted"])
        self.assertIn("maximum", verdict["reason"])

    def test_a_zero_allocation_is_refused(self):
        with self.assertRaises(ValueError):
            create_file(self.repo, "hk003", 0)

    def test_a_rejected_create_leaves_the_source_repository_alone(self):
        create_file(self.repo, "hk001", 100)
        self.assertEqual(len(self.repo["files"]), 3)


class DeleteTests(unittest.TestCase):
    def setUp(self):
        self.repo = build_repository(repository())

    def test_an_unlocked_closed_file_is_deleted(self):
        state, verdict = delete_file(self.repo, "hk001")
        self.assertTrue(verdict["accepted"])
        self.assertNotIn("hk001", state["files"])
        self.assertEqual(free_octets(state), 8000)

    def test_an_absent_file_is_refused(self):
        _, verdict = delete_file(self.repo, "hk009")
        self.assertFalse(verdict["accepted"])

    def test_a_locked_file_is_refused(self):
        _, verdict = delete_file(self.repo, "hk002")
        self.assertFalse(verdict["accepted"])
        self.assertIn("locked", verdict["reason"])

    def test_a_file_held_open_by_a_transfer_is_refused(self):
        _, verdict = delete_file(self.repo, "ev001")
        self.assertFalse(verdict["accepted"])
        self.assertIn("open", verdict["reason"])

    def test_a_rejected_delete_gives_back_no_space(self):
        state, _ = delete_file(self.repo, "hk002")
        self.assertEqual(free_octets(state), 6000)

    def test_a_malformed_name_is_refused(self):
        with self.assertRaises(ValueError):
            delete_file(self.repo, "")


class RunTests(unittest.TestCase):
    def test_the_two_operations_are_the_only_ones_offered(self):
        self.assertEqual(OPERATIONS, ("create", "delete"))

    def test_free_space_is_accounted_after_every_request(self):
        repo = build_repository(repository())
        _, verdicts = apply_operations(
            repo,
            [
                {"operation": "create", "name": "hk003", "allocation_octets": 2000},
                {"operation": "delete", "name": "hk001"},
            ],
        )
        self.assertEqual(verdicts[0]["free_octets_after"], 4000)
        self.assertEqual(verdicts[1]["free_octets_after"], 6000)

    def test_a_delete_frees_room_a_later_create_can_use(self):
        repo = build_repository(repository(capacity_octets=4000))
        state, verdicts = apply_operations(
            repo,
            [
                {"operation": "create", "name": "hk003", "allocation_octets": 1500},
                {"operation": "delete", "name": "hk001"},
                {"operation": "create", "name": "hk003", "allocation_octets": 1500},
            ],
        )
        self.assertFalse(verdicts[0]["accepted"])
        self.assertTrue(verdicts[1]["accepted"])
        self.assertTrue(verdicts[2]["accepted"])
        self.assertIn("hk003", state["files"])

    def test_an_unknown_operation_is_refused(self):
        with self.assertRaises(ValueError):
            apply_operations(
                build_repository(repository()), [{"operation": "rename", "name": "x"}]
            )

    def test_a_create_without_an_allocation_is_refused(self):
        with self.assertRaises(ValueError):
            apply_operations(
                build_repository(repository()),
                [{"operation": "create", "name": "hk003"}],
            )


class AssessmentTests(unittest.TestCase):
    def _spec(self, **over):
        spec = {
            "repository": repository(),
            "operations": [
                {"operation": "create", "name": "hk003", "allocation_octets": 2000},
                {"operation": "delete", "name": "hk002"},
            ],
        }
        spec.update(over)
        return spec

    def test_the_run_reports_opening_and_closing_free_space(self):
        result = assess_file_operations(self._spec())
        self.assertEqual(result["opening_free_octets"], 6000)
        self.assertEqual(result["closing_free_octets"], 4000)

    def test_a_refused_delete_is_reported_as_a_finding(self):
        result = assess_file_operations(self._spec())
        self.assertEqual(result["rejected_count"], 1)
        self.assertTrue(any("locked" in f for f in result["findings"]))

    def test_an_accepted_create_appears_in_the_final_names(self):
        result = assess_file_operations(self._spec())
        self.assertIn("hk003", result["file_names"])
        self.assertEqual(result["file_count"], 4)

    def test_a_full_repository_is_reported(self):
        result = assess_file_operations(self._spec())
        self.assertTrue(any("maximum" in f for f in result["findings"]))

    def test_a_clean_run_carries_no_finding(self):
        result = assess_file_operations(
            self._spec(
                operations=[{"operation": "delete", "name": "hk001"}]
            )
        )
        self.assertTrue(result["clean"])
        self.assertEqual(result["accepted_count"], 1)

    def test_reserved_octets_track_the_surviving_files(self):
        result = assess_file_operations(self._spec())
        self.assertEqual(result["reserved_octets"], 6000)

    def test_missing_spec_key_is_refused(self):
        with self.assertRaises(ValueError):
            assess_file_operations({"repository": repository()})

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_file_operations(["repository"])


if __name__ == "__main__":
    unittest.main()
