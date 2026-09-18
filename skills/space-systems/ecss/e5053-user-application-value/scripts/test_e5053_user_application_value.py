#!/usr/bin/env python3
"""Gate 3 contract test for e5053-user-application-value.

stdlib unittest, offline, deterministic. Run:
    python3 test_e5053_user_application_value.py
"""

import unittest

from e5053_user_application_value_logic import (
    ALTERED,
    REGISTERED,
    TRANSPARENT,
    UNREGISTERED,
    VALUE_MAX,
    assess_user_application_value,
    build_value_registry,
    carriage_report,
    categorize_carriage,
    categorize_meaning,
    is_registered,
    resolve_meaning,
    summarize_transfers,
    validate_user_application_value,
)

REGISTRY = {5: "housekeeping frame", 9: "science frame"}


class TestValueValidation(unittest.TestCase):
    def test_an_in_range_value_is_accepted(self):
        self.assertEqual(validate_user_application_value(5), 5)

    def test_the_top_of_the_field_is_accepted(self):
        self.assertEqual(validate_user_application_value(VALUE_MAX), 255)

    def test_a_value_over_the_field_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_user_application_value(256)

    def test_a_negative_value_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_user_application_value(-1)

    def test_a_boolean_is_not_an_octet(self):
        with self.assertRaises(ValueError):
            validate_user_application_value(True)

    def test_a_float_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_user_application_value(5.0)


class TestRegistry(unittest.TestCase):
    def test_an_absent_registry_is_empty_not_an_error(self):
        self.assertEqual(build_value_registry(None), {})

    def test_a_valid_assignment_is_kept(self):
        self.assertEqual(build_value_registry(REGISTRY)[9], "science frame")

    def test_a_non_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            build_value_registry([(5, "housekeeping frame")])

    def test_an_empty_meaning_is_rejected(self):
        with self.assertRaises(ValueError):
            build_value_registry({5: "   "})

    def test_a_repeated_meaning_is_rejected(self):
        with self.assertRaises(ValueError):
            build_value_registry({5: "same", 6: "same"})

    def test_an_out_of_range_key_is_rejected(self):
        with self.assertRaises(ValueError):
            build_value_registry({300: "too big"})


class TestMeaning(unittest.TestCase):
    def test_a_registered_value_resolves(self):
        self.assertEqual(resolve_meaning(5, REGISTRY), "housekeeping frame")
        self.assertTrue(is_registered(5, REGISTRY))

    def test_an_unregistered_value_resolves_to_nothing(self):
        self.assertIsNone(resolve_meaning(7, REGISTRY))
        self.assertFalse(is_registered(7, REGISTRY))

    def test_meaning_grouping_follows_registration(self):
        self.assertEqual(categorize_meaning(5, REGISTRY), REGISTERED)
        self.assertEqual(categorize_meaning(7, REGISTRY), UNREGISTERED)

    def test_with_no_registry_nothing_is_registered(self):
        self.assertEqual(categorize_meaning(5), UNREGISTERED)


class TestCarriage(unittest.TestCase):
    def test_an_unchanged_value_is_transparent(self):
        self.assertEqual(categorize_carriage(9, 9), TRANSPARENT)

    def test_a_changed_value_is_altered(self):
        self.assertEqual(categorize_carriage(9, 11), ALTERED)

    def test_the_report_counts_the_bits_that_moved(self):
        report = carriage_report(0x0F, 0x0E)
        self.assertEqual(report["changed_bits"], 1)
        self.assertFalse(report["transparent"])

    def test_a_transparent_report_moves_no_bits(self):
        self.assertEqual(carriage_report(9, 9)["changed_bits"], 0)

    def test_an_out_of_range_delivered_value_is_rejected(self):
        with self.assertRaises(ValueError):
            carriage_report(9, 999)


class TestSummary(unittest.TestCase):
    def test_a_clean_run_has_no_first_alteration(self):
        summary = summarize_transfers([(5, 5), (9, 9)])
        self.assertIsNone(summary["first_altered_index"])
        self.assertAlmostEqual(summary["altered_fraction"], 0.0, places=9)

    def test_the_first_alteration_index_is_kept(self):
        summary = summarize_transfers([(5, 5), (9, 8), (5, 4)])
        self.assertEqual(summary["first_altered_index"], 1)

    def test_the_altered_fraction_is_a_rate_not_a_count(self):
        summary = summarize_transfers([(5, 5), (9, 8), (5, 4), (9, 9)])
        self.assertAlmostEqual(summary["altered_fraction"], 0.5, places=9)
        self.assertEqual(summary["altered"], 2)

    def test_changed_bits_accumulate_across_the_run(self):
        summary = summarize_transfers([(0x0F, 0x0E), (0xFF, 0x00)])
        self.assertEqual(summary["changed_bits"], 9)

    def test_an_empty_run_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize_transfers([])

    def test_a_malformed_pair_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize_transfers([(5,)])


class TestAssessment(unittest.TestCase):
    def test_a_transparent_registered_value_is_delivered(self):
        report = assess_user_application_value(5, 5, REGISTRY)
        self.assertEqual(report["verdict"], "value-delivered")
        self.assertEqual(report["meaning"], "housekeeping frame")

    def test_an_altered_value_is_a_transport_finding(self):
        report = assess_user_application_value(5, 6, REGISTRY)
        self.assertEqual(report["verdict"], "value-suspect")
        self.assertTrue(any("carriage altered" in f for f in report["findings"]))

    def test_an_unregistered_value_is_only_a_limitation_by_default(self):
        report = assess_user_application_value(7, 7, REGISTRY)
        self.assertEqual(report["verdict"], "value-delivered")
        self.assertTrue(any("no meaning" in n for n in report["limitations"]))

    def test_an_unregistered_value_becomes_a_finding_when_required(self):
        report = assess_user_application_value(
            7, 7, REGISTRY, require_registered=True
        )
        self.assertEqual(report["verdict"], "value-suspect")

    def test_the_protocol_neutrality_note_is_always_recorded(self):
        report = assess_user_application_value(5, 5, REGISTRY)
        self.assertTrue(
            any("assigns this field no meaning" in n for n in report["limitations"])
        )

    def test_transport_and_application_faults_stay_separate(self):
        report = assess_user_application_value(
            5, 7, REGISTRY, require_registered=True
        )
        self.assertEqual(len(report["findings"]), 2)
        self.assertEqual(report["meaning_category"], UNREGISTERED)

    def test_assessment_propagates_a_field_error(self):
        with self.assertRaises(ValueError):
            assess_user_application_value(5, 400, REGISTRY)


if __name__ == "__main__":
    unittest.main()
