"""Contract tests for the clause 6.14.3.2 forward-control definition logic."""

import unittest

from e7041_forward_control_definitions_logic import (
    add_definition,
    assess_definitions,
    definition_count,
    delete_definition,
    is_forwarded,
    new_store,
    report_store,
    validate_level,
)

FORWARDABLE = (10, 11, 12)


class LevelValidationTests(unittest.TestCase):
    def test_application_process_only_level(self):
        self.assertEqual(validate_level(10), (10, None, None))

    def test_service_type_level(self):
        self.assertEqual(validate_level(10, 3), (10, 3, None))

    def test_subtype_level(self):
        self.assertEqual(validate_level(10, 3, 25), (10, 3, 25))

    def test_subtype_without_service_type_is_refused(self):
        with self.assertRaises(ValueError):
            validate_level(10, None, 25)

    def test_unknown_application_process_is_refused(self):
        with self.assertRaises(ValueError):
            validate_level(99, 3, 25, FORWARDABLE)

    def test_non_integer_application_process_is_refused(self):
        with self.assertRaises(ValueError):
            validate_level("10", 3, 25)

    def test_zero_service_type_is_refused(self):
        with self.assertRaises(ValueError):
            validate_level(10, 0)


class AddTests(unittest.TestCase):
    def test_subtype_definition_is_held(self):
        store = new_store()
        add_definition(store, 10, 3, 25, FORWARDABLE)
        self.assertTrue(is_forwarded(store, 10, 3, 25))
        self.assertFalse(is_forwarded(store, 10, 3, 26))

    def test_whole_service_type_covers_every_subtype(self):
        store = new_store()
        add_definition(store, 10, 3, None, FORWARDABLE)
        self.assertTrue(is_forwarded(store, 10, 3, 25))
        self.assertTrue(is_forwarded(store, 10, 3, 26))
        self.assertFalse(is_forwarded(store, 10, 5, 4))

    def test_whole_application_process_covers_every_service_type(self):
        store = new_store()
        add_definition(store, 10, None, None, FORWARDABLE)
        self.assertTrue(is_forwarded(store, 10, 5, 4))
        self.assertFalse(is_forwarded(store, 11, 5, 4))

    def test_wider_add_absorbs_the_narrower_entries(self):
        store = new_store()
        add_definition(store, 10, 3, 25, FORWARDABLE)
        add_definition(store, 10, 5, 4, FORWARDABLE)
        findings = add_definition(store, 10, None, None, FORWARDABLE)
        self.assertEqual(definition_count(store), 1)
        self.assertTrue(any("absorbs" in f for f in findings))

    def test_whole_service_type_absorbs_its_subtypes(self):
        store = new_store()
        add_definition(store, 10, 3, 25, FORWARDABLE)
        findings = add_definition(store, 10, 3, None, FORWARDABLE)
        self.assertEqual(definition_count(store), 1)
        self.assertTrue(any("absorbs" in f for f in findings))

    def test_narrower_add_under_a_whole_application_process_is_redundant(self):
        store = new_store()
        add_definition(store, 10, None, None, FORWARDABLE)
        findings = add_definition(store, 10, 3, 25, FORWARDABLE)
        self.assertEqual(definition_count(store), 1)
        self.assertTrue(any("adds nothing" in f for f in findings))

    def test_subtype_under_a_whole_service_type_is_redundant(self):
        store = new_store()
        add_definition(store, 10, 3, None, FORWARDABLE)
        findings = add_definition(store, 10, 3, 25, FORWARDABLE)
        self.assertTrue(any("adds nothing" in f for f in findings))

    def test_repeated_subtype_add_is_reported(self):
        store = new_store()
        add_definition(store, 10, 3, 25, FORWARDABLE)
        findings = add_definition(store, 10, 3, 25, FORWARDABLE)
        self.assertEqual(definition_count(store), 1)
        self.assertTrue(any("already held" in f for f in findings))

    def test_application_process_capacity_is_refused_not_evicted(self):
        store = new_store()
        limits = {"max_application_processes": 2}
        add_definition(store, 10, 3, 25, (10, 11, 12), limits)
        add_definition(store, 11, 3, 25, (10, 11, 12), limits)
        with self.assertRaises(ValueError):
            add_definition(store, 12, 3, 25, (10, 11, 12), limits)
        self.assertEqual(len(store), 2)

    def test_service_type_capacity_is_refused(self):
        store = new_store()
        limits = {"max_service_types_per_application_process": 1}
        add_definition(store, 10, 3, 25, FORWARDABLE, limits)
        with self.assertRaises(ValueError):
            add_definition(store, 10, 5, 4, FORWARDABLE, limits)

    def test_subtype_capacity_is_refused(self):
        store = new_store()
        limits = {"max_subtypes_per_service_type": 2}
        add_definition(store, 10, 3, 25, FORWARDABLE, limits)
        add_definition(store, 10, 3, 26, FORWARDABLE, limits)
        with self.assertRaises(ValueError):
            add_definition(store, 10, 3, 27, FORWARDABLE, limits)

    def test_unknown_limit_key_is_refused(self):
        store = new_store()
        with self.assertRaises(ValueError):
            add_definition(store, 10, 3, 25, FORWARDABLE, {"max_definitions": 4})

    def test_unknown_application_process_add_is_refused(self):
        store = new_store()
        with self.assertRaises(ValueError):
            add_definition(store, 99, 3, 25, FORWARDABLE)

    def test_non_mapping_store_is_refused(self):
        with self.assertRaises(ValueError):
            add_definition([], 10, 3, 25, FORWARDABLE)


class DeleteTests(unittest.TestCase):
    def test_subtype_delete_removes_only_that_subtype(self):
        store = new_store()
        add_definition(store, 10, 3, 25, FORWARDABLE)
        add_definition(store, 10, 3, 26, FORWARDABLE)
        delete_definition(store, 10, 3, 25)
        self.assertFalse(is_forwarded(store, 10, 3, 25))
        self.assertTrue(is_forwarded(store, 10, 3, 26))

    def test_deleting_the_last_subtype_prunes_the_parents(self):
        store = new_store()
        add_definition(store, 10, 3, 25, FORWARDABLE)
        delete_definition(store, 10, 3, 25)
        self.assertEqual(store, {})

    def test_whole_service_type_delete(self):
        store = new_store()
        add_definition(store, 10, 3, None, FORWARDABLE)
        delete_definition(store, 10, 3)
        self.assertEqual(definition_count(store), 0)

    def test_whole_application_process_delete(self):
        store = new_store()
        add_definition(store, 10, None, None, FORWARDABLE)
        delete_definition(store, 10)
        self.assertEqual(store, {})

    def test_deleting_an_absent_application_process_is_refused(self):
        store = new_store()
        with self.assertRaises(ValueError):
            delete_definition(store, 10)

    def test_deleting_an_absent_subtype_is_refused(self):
        store = new_store()
        add_definition(store, 10, 3, 25, FORWARDABLE)
        with self.assertRaises(ValueError):
            delete_definition(store, 10, 3, 99)

    def test_deleting_at_the_wrong_level_is_refused(self):
        store = new_store()
        add_definition(store, 10, 3, 25, FORWARDABLE)
        with self.assertRaises(ValueError):
            delete_definition(store, 10)

    def test_deleting_a_whole_service_type_that_is_not_whole_is_refused(self):
        store = new_store()
        add_definition(store, 10, 3, 25, FORWARDABLE)
        with self.assertRaises(ValueError):
            delete_definition(store, 10, 3)


class CoverageAndReportTests(unittest.TestCase):
    def test_empty_store_forwards_nothing(self):
        self.assertFalse(is_forwarded(new_store(), 10, 3, 25))

    def test_coverage_needs_a_full_level(self):
        store = new_store()
        add_definition(store, 10, 3, 25, FORWARDABLE)
        with self.assertRaises(ValueError):
            is_forwarded(store, 10, None, None)

    def test_report_is_sorted_and_deterministic(self):
        store = new_store()
        add_definition(store, 11, 5, 4, FORWARDABLE)
        add_definition(store, 10, 3, 26, FORWARDABLE)
        add_definition(store, 10, 3, 25, FORWARDABLE)
        report = report_store(store)
        self.assertEqual([e["application_process"] for e in report], [10, 11])
        self.assertEqual(report[0]["service_types"][0]["message_subtypes"], [25, 26])

    def test_definition_count_spans_the_levels(self):
        store = new_store()
        add_definition(store, 10, 3, 25, FORWARDABLE)
        add_definition(store, 10, 5, None, FORWARDABLE)
        add_definition(store, 11, None, None, FORWARDABLE)
        self.assertEqual(definition_count(store), 3)

    def test_non_mapping_report_is_refused(self):
        with self.assertRaises(ValueError):
            report_store([])


class AssessmentTests(unittest.TestCase):
    def _spec(self, operations, **overrides):
        spec = {"forwardable": FORWARDABLE, "operations": operations}
        spec.update(overrides)
        return spec

    def test_clean_operation_run_reports_no_findings(self):
        result = assess_definitions(
            self._spec(
                [
                    {"action": "add", "application_process": 10, "service_type": 3,
                     "message_subtype": 25},
                    {"action": "add", "application_process": 11, "service_type": 5},
                ]
            )
        )
        self.assertTrue(result["clean"])
        self.assertEqual(result["definition_count"], 2)

    def test_refused_operation_is_collected_not_raised(self):
        result = assess_definitions(
            self._spec([{"action": "delete", "application_process": 10}])
        )
        self.assertEqual(len(result["refused"]), 1)
        self.assertFalse(result["clean"])

    def test_redundant_add_is_collected_as_a_finding(self):
        result = assess_definitions(
            self._spec(
                [
                    {"action": "add", "application_process": 10},
                    {"action": "add", "application_process": 10, "service_type": 3,
                     "message_subtype": 25},
                ]
            )
        )
        self.assertEqual(result["definition_count"], 1)
        self.assertTrue(any("adds nothing" in f for f in result["findings"]))

    def test_unknown_action_is_refused(self):
        with self.assertRaises(ValueError):
            assess_definitions(self._spec([{"action": "amend", "application_process": 10}]))

    def test_missing_operations_key_is_refused(self):
        with self.assertRaises(ValueError):
            assess_definitions({"forwardable": FORWARDABLE})

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_definitions(["operations"])

    def test_operations_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            assess_definitions(self._spec({"action": "add"}))


if __name__ == "__main__":
    unittest.main()
