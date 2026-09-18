#!/usr/bin/env python3
"""Gate 3 contract test for e5053-status-code.

stdlib unittest, offline, deterministic. Run:
    python3 test_e5053_status_code.py
"""

import unittest

from e5053_status_code_logic import (
    ACCEPT,
    DEFINED_ERROR,
    REJECT,
    REPORT_ERROR,
    RESERVED,
    SUCCESS,
    SUCCESS_CODE,
    UNASSIGNED,
    USER_DEFINED,
    assess_status_code,
    build_registry,
    categorize_status_code,
    disposition,
    emittable,
    is_success,
    summarize_status_codes,
    validate_status_code,
)


class TestCodeValidation(unittest.TestCase):
    def test_success_encoding_is_valid(self):
        self.assertEqual(validate_status_code(SUCCESS_CODE), 0)

    def test_encoding_over_one_octet_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_status_code(256)

    def test_negative_encoding_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_status_code(-1)

    def test_boolean_encoding_is_not_an_integer(self):
        with self.assertRaises(ValueError):
            validate_status_code(True)

    def test_float_encoding_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_status_code(3.0)


class TestRegistry(unittest.TestCase):
    def test_default_registry_has_three_bands(self):
        registry = build_registry()
        self.assertEqual(len(registry), 3)

    def test_overlapping_bands_are_rejected(self):
        with self.assertRaises(ValueError):
            build_registry(defined_error_band=(1, 200))

    def test_inverted_band_is_rejected(self):
        with self.assertRaises(ValueError):
            build_registry(user_defined_band=(191, 128))

    def test_band_swallowing_the_success_encoding_is_rejected(self):
        with self.assertRaises(ValueError):
            build_registry(defined_error_band=(0, 15))

    def test_band_must_be_a_pair(self):
        with self.assertRaises(ValueError):
            build_registry(reserved_band=(192,))

    def test_custom_registry_moves_the_boundaries(self):
        registry = build_registry(
            defined_error_band=(1, 63),
            user_defined_band=(64, 127),
            reserved_band=(128, 255),
        )
        self.assertEqual(categorize_status_code(100, registry), USER_DEFINED)


class TestCategories(unittest.TestCase):
    def test_zero_is_success(self):
        self.assertEqual(categorize_status_code(0), SUCCESS)
        self.assertTrue(is_success(0))

    def test_low_band_is_a_defined_error(self):
        self.assertEqual(categorize_status_code(4), DEFINED_ERROR)
        self.assertFalse(is_success(4))

    def test_high_band_is_reserved(self):
        self.assertEqual(categorize_status_code(240), RESERVED)

    def test_user_band_is_user_defined(self):
        self.assertEqual(categorize_status_code(130), USER_DEFINED)

    def test_gap_between_bands_is_unassigned(self):
        self.assertEqual(categorize_status_code(64), UNASSIGNED)

    def test_registry_missing_a_band_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_status_code(4, {DEFINED_ERROR: (1, 15)})


class TestDisposition(unittest.TestCase):
    def test_success_is_accepted(self):
        self.assertEqual(disposition(0), ACCEPT)

    def test_defined_error_is_reported_not_silently_accepted(self):
        self.assertEqual(disposition(9), REPORT_ERROR)

    def test_reserved_encoding_is_rejected(self):
        self.assertEqual(disposition(250), REJECT)

    def test_unassigned_encoding_is_rejected(self):
        self.assertEqual(disposition(70), REJECT)

    def test_user_defined_follows_the_node_policy(self):
        self.assertEqual(disposition(140), ACCEPT)
        self.assertEqual(disposition(140, accept_user_defined=False), REJECT)

    def test_only_assigned_encodings_are_emittable(self):
        self.assertTrue(emittable(0))
        self.assertTrue(emittable(9))
        self.assertTrue(emittable(140))
        self.assertFalse(emittable(250))
        self.assertFalse(emittable(70))


class TestSummary(unittest.TestCase):
    def test_all_success_run_has_no_first_failure(self):
        summary = summarize_status_codes([0, 0, 0, 0])
        self.assertIsNone(summary["first_failure_index"])
        self.assertAlmostEqual(summary["success_fraction"], 1.0, places=9)

    def test_first_failure_index_is_the_first_non_success(self):
        summary = summarize_status_codes([0, 0, 7, 0, 250])
        self.assertEqual(summary["first_failure_index"], 2)

    def test_error_fraction_counts_every_non_success_category(self):
        summary = summarize_status_codes([0, 7, 250, 70])
        self.assertAlmostEqual(summary["error_fraction"], 0.75, places=9)

    def test_counts_are_kept_per_category(self):
        summary = summarize_status_codes([0, 7, 7, 130, 250])
        self.assertEqual(summary["counts"][DEFINED_ERROR], 2)
        self.assertEqual(summary["counts"][USER_DEFINED], 1)
        self.assertEqual(summary["counts"][RESERVED], 1)

    def test_empty_run_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize_status_codes([])

    def test_non_list_run_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize_status_codes(0)


class TestAssessment(unittest.TestCase):
    def test_success_assessment_is_clean(self):
        report = assess_status_code(0)
        self.assertEqual(report["verdict"], "accept")
        self.assertEqual(report["findings"], [])

    def test_defined_error_is_a_finding_and_holds(self):
        report = assess_status_code(5)
        self.assertEqual(report["verdict"], "hold")
        self.assertTrue(any("defined transfer error" in f for f in report["findings"]))

    def test_reserved_encoding_is_flagged_as_not_emittable(self):
        report = assess_status_code(200)
        self.assertFalse(report["emittable"])
        self.assertTrue(any("reserved" in f for f in report["findings"]))

    def test_unassigned_encoding_is_not_read_as_success(self):
        report = assess_status_code(100)
        self.assertEqual(report["category"], UNASSIGNED)
        self.assertEqual(report["verdict"], "hold")

    def test_accepted_user_defined_encoding_is_a_limitation(self):
        report = assess_status_code(150)
        self.assertEqual(report["verdict"], "accept")
        self.assertTrue(any("user-defined" in n for n in report["limitations"]))

    def test_refused_user_defined_encoding_becomes_a_finding(self):
        report = assess_status_code(150, accept_user_defined=False)
        self.assertEqual(report["verdict"], "hold")
        self.assertTrue(any("user-defined" in f for f in report["findings"]))

    def test_assessment_propagates_an_encoding_error(self):
        with self.assertRaises(ValueError):
            assess_status_code(300)


if __name__ == "__main__":
    unittest.main()
