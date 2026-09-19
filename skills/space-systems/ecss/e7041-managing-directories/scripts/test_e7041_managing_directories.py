"""Contract test for the managing-directories leaf (stdlib unittest)."""

import unittest

from e7041_managing_directories_logic import (
    CREATED,
    DELETED,
    FAILURE_ALREADY_EXISTS,
    FAILURE_DEPTH_EXCEEDED,
    FAILURE_IS_ROOT,
    FAILURE_MOVE_INTO_OWN_SUBTREE,
    FAILURE_NOT_EMPTY,
    FAILURE_PARENT_UNKNOWN,
    FAILURE_UNKNOWN,
    MAX_NAME_OCTETS,
    MOVED,
    RENAMED,
    apply_directory_plan,
    children_of,
    create_directory,
    delete_directory,
    depth_of,
    is_empty,
    is_within,
    join_path,
    move_directory,
    name_of,
    normalize_path,
    parent_of,
    rename_directory,
    split_path,
    validate_segment,
    validate_tree,
)


def tree():
    return {
        "mem1": [],
        "mem1/logs": ["EVT-001.DAT"],
        "mem1/logs/archive": [],
        "mem1/images": ["IMG-01.RAW"],
        "mem1/spare": [],
    }


class TestPathMechanics(unittest.TestCase):
    def test_empty_segment_name_raises(self):
        with self.assertRaises(ValueError):
            validate_segment("")

    def test_segment_with_a_separator_raises(self):
        with self.assertRaises(ValueError):
            validate_segment("logs/archive")

    def test_relative_marker_segment_raises(self):
        with self.assertRaises(ValueError):
            validate_segment("..")

    def test_over_long_segment_raises(self):
        with self.assertRaises(ValueError):
            validate_segment("A" * (MAX_NAME_OCTETS + 1))

    def test_path_is_normalized(self):
        self.assertEqual(normalize_path("/mem1/logs/"), "mem1/logs")

    def test_path_with_an_empty_inner_segment_raises(self):
        with self.assertRaises(ValueError):
            split_path("mem1//logs")

    def test_join_rejects_an_empty_segment_list(self):
        with self.assertRaises(ValueError):
            join_path([])

    def test_depth_counts_the_root_as_one(self):
        self.assertEqual(depth_of("mem1"), 1)
        self.assertEqual(depth_of("mem1/logs/archive"), 3)

    def test_a_root_repository_has_no_parent(self):
        self.assertIsNone(parent_of("mem1"))

    def test_parent_and_name_split_the_path(self):
        self.assertEqual(parent_of("mem1/logs/archive"), "mem1/logs")
        self.assertEqual(name_of("mem1/logs/archive"), "archive")

    def test_within_is_tested_on_whole_segments(self):
        self.assertTrue(is_within("mem1/logs/archive", "mem1/logs"))
        self.assertTrue(is_within("mem1/logs", "mem1/logs"))
        self.assertFalse(is_within("mem1/logsarchive", "mem1/logs"))


class TestTreeValidation(unittest.TestCase):
    def test_an_orphan_repository_raises(self):
        with self.assertRaises(ValueError):
            validate_tree({"mem1": [], "mem1/logs/archive": []})

    def test_a_duplicate_file_name_raises(self):
        with self.assertRaises(ValueError):
            validate_tree({"mem1": ["A.DAT", "A.DAT"]})

    def test_a_tree_past_the_declared_depth_raises(self):
        with self.assertRaises(ValueError):
            validate_tree(tree(), max_depth=2)

    def test_an_empty_tree_raises(self):
        with self.assertRaises(ValueError):
            validate_tree({})

    def test_children_are_returned_in_name_order(self):
        self.assertEqual(children_of(tree(), "mem1"), ["images", "logs", "spare"])

    def test_children_of_an_unknown_repository_raises(self):
        with self.assertRaises(ValueError):
            children_of(tree(), "mem9")

    def test_empty_means_no_files_and_no_sub_repositories(self):
        self.assertTrue(is_empty(tree(), "mem1/spare"))
        self.assertFalse(is_empty(tree(), "mem1/images"))
        self.assertFalse(is_empty(tree(), "mem1/logs"))


class TestCreate(unittest.TestCase):
    def test_a_create_under_a_known_parent_succeeds(self):
        result, outcome = create_directory(tree(), "mem1", "telemetry")
        self.assertEqual(outcome["outcome"], CREATED)
        self.assertIn("mem1/telemetry", result)

    def test_a_create_under_an_unknown_parent_is_refused(self):
        _, outcome = create_directory(tree(), "mem9", "telemetry")
        self.assertEqual(outcome["outcome"], FAILURE_PARENT_UNKNOWN)

    def test_a_create_over_an_existing_sub_repository_is_refused(self):
        _, outcome = create_directory(tree(), "mem1", "logs")
        self.assertEqual(outcome["outcome"], FAILURE_ALREADY_EXISTS)

    def test_a_create_clashing_with_a_file_name_is_refused(self):
        _, outcome = create_directory(tree(), "mem1/images", "IMG-01.RAW")
        self.assertEqual(outcome["outcome"], FAILURE_ALREADY_EXISTS)

    def test_a_create_past_the_declared_depth_is_refused_at_the_request(self):
        _, outcome = create_directory(tree(), "mem1/logs/archive", "old", max_depth=3)
        self.assertEqual(outcome["outcome"], FAILURE_DEPTH_EXCEEDED)

    def test_a_create_does_not_mutate_the_tree_it_was_given(self):
        original = tree()
        create_directory(original, "mem1", "telemetry")
        self.assertNotIn("mem1/telemetry", original)

    def test_a_created_repository_is_empty(self):
        result, _ = create_directory(tree(), "mem1", "telemetry")
        self.assertTrue(is_empty(result, "mem1/telemetry"))


class TestDelete(unittest.TestCase):
    def test_an_empty_sub_repository_is_deleted(self):
        result, outcome = delete_directory(tree(), "mem1/spare")
        self.assertEqual(outcome["outcome"], DELETED)
        self.assertNotIn("mem1/spare", result)

    def test_a_repository_holding_a_file_is_refused(self):
        _, outcome = delete_directory(tree(), "mem1/images")
        self.assertEqual(outcome["outcome"], FAILURE_NOT_EMPTY)
        self.assertEqual(outcome["detail"]["file_count"], 1)

    def test_a_repository_holding_a_sub_repository_is_refused(self):
        _, outcome = delete_directory(tree(), "mem1/logs")
        self.assertEqual(outcome["outcome"], FAILURE_NOT_EMPTY)
        self.assertEqual(outcome["detail"]["sub_repository_count"], 1)

    def test_a_refused_delete_leaves_the_content_in_place(self):
        result, _ = delete_directory(tree(), "mem1/logs")
        self.assertIn("mem1/logs/archive", result)

    def test_deleting_the_root_is_refused(self):
        _, outcome = delete_directory(tree(), "mem1")
        self.assertEqual(outcome["outcome"], FAILURE_IS_ROOT)

    def test_deleting_an_unknown_repository_is_refused(self):
        _, outcome = delete_directory(tree(), "mem1/nowhere")
        self.assertEqual(outcome["outcome"], FAILURE_UNKNOWN)

    def test_emptying_then_deleting_succeeds(self):
        working, _ = delete_directory(tree(), "mem1/logs/archive")
        working["mem1/logs"] = []
        result, outcome = delete_directory(working, "mem1/logs")
        self.assertEqual(outcome["outcome"], DELETED)
        self.assertNotIn("mem1/logs", result)


class TestRenameAndMove(unittest.TestCase):
    def test_a_rename_keeps_the_parent_and_repaths_the_subtree(self):
        result, outcome = rename_directory(tree(), "mem1/logs", "journal")
        self.assertEqual(outcome["outcome"], RENAMED)
        self.assertIn("mem1/journal/archive", result)
        self.assertNotIn("mem1/logs", result)

    def test_a_rename_carries_the_files_with_it(self):
        result, _ = rename_directory(tree(), "mem1/logs", "journal")
        self.assertEqual(result["mem1/journal"], ["EVT-001.DAT"])

    def test_a_rename_onto_an_existing_sibling_is_refused(self):
        _, outcome = rename_directory(tree(), "mem1/logs", "images")
        self.assertEqual(outcome["outcome"], FAILURE_ALREADY_EXISTS)

    def test_a_rename_to_the_same_name_is_accepted_and_changes_nothing(self):
        result, outcome = rename_directory(tree(), "mem1/logs", "logs")
        self.assertEqual(outcome["outcome"], RENAMED)
        self.assertIn("mem1/logs/archive", result)

    def test_renaming_the_root_is_refused(self):
        _, outcome = rename_directory(tree(), "mem1", "mem2")
        self.assertEqual(outcome["outcome"], FAILURE_IS_ROOT)

    def test_a_move_changes_the_parent_and_keeps_the_name(self):
        result, outcome = move_directory(tree(), "mem1/logs/archive", "mem1/spare")
        self.assertEqual(outcome["outcome"], MOVED)
        self.assertIn("mem1/spare/archive", result)
        self.assertNotIn("mem1/logs/archive", result)

    def test_a_move_into_the_targets_own_subtree_is_refused(self):
        _, outcome = move_directory(tree(), "mem1/logs", "mem1/logs/archive")
        self.assertEqual(outcome["outcome"], FAILURE_MOVE_INTO_OWN_SUBTREE)

    def test_a_move_onto_itself_is_refused_as_a_subtree_move(self):
        _, outcome = move_directory(tree(), "mem1/logs", "mem1/logs")
        self.assertEqual(outcome["outcome"], FAILURE_MOVE_INTO_OWN_SUBTREE)

    def test_a_move_under_an_unknown_parent_is_refused(self):
        _, outcome = move_directory(tree(), "mem1/logs", "mem9")
        self.assertEqual(outcome["outcome"], FAILURE_PARENT_UNKNOWN)

    def test_a_move_whose_subtree_would_pass_the_depth_cap_is_refused(self):
        _, outcome = move_directory(tree(), "mem1/logs", "mem1/spare", max_depth=3)
        self.assertEqual(outcome["outcome"], FAILURE_DEPTH_EXCEEDED)

    def test_a_move_colliding_with_a_name_at_the_destination_is_refused(self):
        working, _ = create_directory(tree(), "mem1/spare", "archive")
        _, outcome = move_directory(working, "mem1/logs/archive", "mem1/spare")
        self.assertEqual(outcome["outcome"], FAILURE_ALREADY_EXISTS)


class TestPlan(unittest.TestCase):
    def test_a_plan_reports_each_outcome_in_order(self):
        result = apply_directory_plan(
            tree(),
            [
                {"action": "create", "parent_path": "mem1", "name": "telemetry"},
                {"action": "delete", "path": "mem1/images"},
                {"action": "rename", "path": "mem1/spare", "new_name": "reserve"},
                {"action": "move", "path": "mem1/logs/archive", "new_parent_path": "mem1/reserve"},
            ],
        )
        self.assertEqual(
            [o["outcome"] for o in result["outcomes"]],
            [CREATED, FAILURE_NOT_EMPTY, RENAMED, MOVED],
        )
        self.assertEqual(result["applied_count"], 3)
        self.assertEqual(result["refused_count"], 1)
        self.assertFalse(result["plan_applied_in_full"])

    def test_a_clean_plan_applies_in_full(self):
        result = apply_directory_plan(
            tree(), [{"action": "create", "parent_path": "mem1", "name": "telemetry"}]
        )
        self.assertTrue(result["plan_applied_in_full"])
        self.assertEqual(result["repository_count"], 6)

    def test_a_plan_reports_the_deepest_path_reached(self):
        result = apply_directory_plan(
            tree(),
            [{"action": "create", "parent_path": "mem1/logs/archive", "name": "old"}],
        )
        self.assertEqual(result["deepest_path_depth"], 4)

    def test_an_unknown_action_raises(self):
        with self.assertRaises(ValueError):
            apply_directory_plan(tree(), [{"action": "purge", "path": "mem1/logs"}])

    def test_a_plan_must_be_a_list(self):
        with self.assertRaises(ValueError):
            apply_directory_plan(tree(), {"action": "delete", "path": "mem1/spare"})


if __name__ == "__main__":
    unittest.main()
