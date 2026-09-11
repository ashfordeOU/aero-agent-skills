#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §6.5.7 crewed-mission element tests.

Exercises scripts/e1003_el_crewed_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — a test record type must be
one of the four crewed-mission test families (vibroacoustic_emission,
hfe_test, toxic_offgassing, audible_noise) and an unrecognized type
raises; vibroacoustic emission raises for bad inputs and returns a finding
when the measured level exceeds the limit; the HFE check raises for non-bool
input and flags a failed judgment; toxic offgassing raises for bad inputs
and flags any substance above its cabin limit; audible noise raises for bad
inputs and flags a measurement above the habitability limit; the full
crewed-element review aggregates all family findings and reports missing
test families; an element is compliant only when findings is empty and
no families are missing.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_el_crewed_logic as cr  # noqa: E402


class CategorizeTestTest(unittest.TestCase):
    def test_vibroacoustic_emission_recognized(self):
        self.assertEqual(cr.categorize_test("vibroacoustic_emission"), "vibroacoustic_emission")

    def test_hfe_test_recognized(self):
        self.assertEqual(cr.categorize_test("hfe_test"), "hfe_test")

    def test_toxic_offgassing_recognized(self):
        self.assertEqual(cr.categorize_test("toxic_offgassing"), "toxic_offgassing")

    def test_audible_noise_recognized(self):
        self.assertEqual(cr.categorize_test("audible_noise"), "audible_noise")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            cr.categorize_test("electromagnetic_compatibility")


class CheckVibroacousticEmissionTest(unittest.TestCase):
    def test_within_limit_no_finding(self):
        self.assertEqual(
            cr.check_vibroacoustic_emission("panel-a", 65.0, 70.0), []
        )

    def test_at_limit_no_finding(self):
        self.assertEqual(
            cr.check_vibroacoustic_emission("panel-a", 70.0, 70.0), []
        )

    def test_exceeds_limit_finding_returned(self):
        findings = cr.check_vibroacoustic_emission("panel-a", 75.0, 70.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "vibroacoustic_emission_exceeds_limit")
        self.assertEqual(findings[0]["equipment"], "panel-a")
        self.assertAlmostEqual(findings[0]["measured_db"], 75.0)
        self.assertAlmostEqual(findings[0]["limit_db"], 70.0)

    def test_negative_measured_raises(self):
        with self.assertRaises(ValueError):
            cr.check_vibroacoustic_emission("panel-a", -1.0, 70.0)

    def test_zero_limit_raises(self):
        with self.assertRaises(ValueError):
            cr.check_vibroacoustic_emission("panel-a", 65.0, 0.0)


class CheckHfeTestTest(unittest.TestCase):
    def test_hfe_pass_no_finding(self):
        self.assertEqual(cr.check_hfe_test("ctrl-unit-1", True), [])

    def test_hfe_fail_finding_returned(self):
        findings = cr.check_hfe_test("ctrl-unit-1", False)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "hfe_test_failed")
        self.assertEqual(findings[0]["equipment"], "ctrl-unit-1")

    def test_non_bool_raises(self):
        with self.assertRaises(ValueError):
            cr.check_hfe_test("ctrl-unit-1", "yes")

    def test_int_instead_of_bool_raises(self):
        with self.assertRaises(ValueError):
            cr.check_hfe_test("ctrl-unit-1", 1)


class CheckToxicOffgassingTest(unittest.TestCase):
    def test_within_limit_no_finding(self):
        self.assertEqual(
            cr.check_toxic_offgassing("item-x", "formaldehyde", 0.05, 0.1), []
        )

    def test_at_limit_no_finding(self):
        self.assertEqual(
            cr.check_toxic_offgassing("item-x", "formaldehyde", 0.1, 0.1), []
        )

    def test_exceeds_limit_finding_returned(self):
        findings = cr.check_toxic_offgassing("item-x", "benzene", 0.5, 0.1)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "toxic_offgassing_exceeds_limit")
        self.assertEqual(findings[0]["substance"], "benzene")
        self.assertAlmostEqual(findings[0]["measured_mg_m3"], 0.5)
        self.assertAlmostEqual(findings[0]["limit_mg_m3"], 0.1)

    def test_negative_measured_raises(self):
        with self.assertRaises(ValueError):
            cr.check_toxic_offgassing("item-x", "co", -0.01, 10.0)

    def test_zero_limit_raises(self):
        with self.assertRaises(ValueError):
            cr.check_toxic_offgassing("item-x", "co", 0.01, 0.0)


class CheckAudibleNoiseTest(unittest.TestCase):
    def test_within_limit_no_finding(self):
        self.assertEqual(cr.check_audible_noise("rack-1", 55.0, 65.0), [])

    def test_at_limit_no_finding(self):
        self.assertEqual(cr.check_audible_noise("rack-1", 65.0, 65.0), [])

    def test_exceeds_limit_finding_returned(self):
        findings = cr.check_audible_noise("rack-1", 70.0, 65.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "audible_noise_exceeds_limit")
        self.assertEqual(findings[0]["equipment"], "rack-1")
        self.assertAlmostEqual(findings[0]["measured_dba"], 70.0)
        self.assertAlmostEqual(findings[0]["limit_dba"], 65.0)

    def test_negative_measured_raises(self):
        with self.assertRaises(ValueError):
            cr.check_audible_noise("rack-1", -5.0, 65.0)

    def test_zero_limit_raises(self):
        with self.assertRaises(ValueError):
            cr.check_audible_noise("rack-1", 55.0, 0.0)


class CrewedElementReviewTest(unittest.TestCase):
    def _all_four_records(self):
        return [
            {
                "test_type": "vibroacoustic_emission",
                "measured_db": 62.0,
                "limit_db": 70.0,
            },
            {
                "test_type": "hfe_test",
                "passed": True,
            },
            {
                "test_type": "toxic_offgassing",
                "substances": [
                    {"substance": "co2", "measured_mg_m3": 0.3, "limit_mg_m3": 1.0}
                ],
            },
            {
                "test_type": "audible_noise",
                "measured_dba": 55.0,
                "limit_dba": 65.0,
            },
        ]

    def test_fully_compliant_all_four_families(self):
        review = cr.crewed_element_review("eq-001", self._all_four_records())
        self.assertEqual(review["findings"], [])
        self.assertEqual(review["missing_families"], [])
        self.assertTrue(cr.is_crewed_element_compliant(review))

    def test_missing_all_families_blocks_acceptance(self):
        review = cr.crewed_element_review("eq-002", [])
        self.assertEqual(review["findings"], [])
        self.assertEqual(len(review["missing_families"]), 4)
        self.assertFalse(cr.is_crewed_element_compliant(review))

    def test_missing_one_family_is_noncompliant(self):
        records = [r for r in self._all_four_records() if r["test_type"] != "hfe_test"]
        review = cr.crewed_element_review("eq-003", records)
        self.assertIn("hfe_test", review["missing_families"])
        self.assertFalse(cr.is_crewed_element_compliant(review))

    def test_vibroacoustic_exceedance_surfaced(self):
        records = list(self._all_four_records())
        records[0] = {
            "test_type": "vibroacoustic_emission",
            "measured_db": 80.0,
            "limit_db": 70.0,
        }
        review = cr.crewed_element_review("eq-004", records)
        issues = [f["issue"] for f in review["findings"]]
        self.assertIn("vibroacoustic_emission_exceeds_limit", issues)
        self.assertFalse(cr.is_crewed_element_compliant(review))

    def test_hfe_failure_surfaced(self):
        records = list(self._all_four_records())
        records[1] = {"test_type": "hfe_test", "passed": False}
        review = cr.crewed_element_review("eq-005", records)
        issues = [f["issue"] for f in review["findings"]]
        self.assertIn("hfe_test_failed", issues)
        self.assertFalse(cr.is_crewed_element_compliant(review))

    def test_offgassing_exceedance_surfaced(self):
        records = list(self._all_four_records())
        records[2] = {
            "test_type": "toxic_offgassing",
            "substances": [
                {"substance": "acetaldehyde", "measured_mg_m3": 2.0, "limit_mg_m3": 0.5}
            ],
        }
        review = cr.crewed_element_review("eq-006", records)
        issues = [f["issue"] for f in review["findings"]]
        self.assertIn("toxic_offgassing_exceeds_limit", issues)
        self.assertFalse(cr.is_crewed_element_compliant(review))

    def test_audible_noise_exceedance_surfaced(self):
        records = list(self._all_four_records())
        records[3] = {
            "test_type": "audible_noise",
            "measured_dba": 72.0,
            "limit_dba": 65.0,
        }
        review = cr.crewed_element_review("eq-007", records)
        issues = [f["issue"] for f in review["findings"]]
        self.assertIn("audible_noise_exceeds_limit", issues)
        self.assertFalse(cr.is_crewed_element_compliant(review))

    def test_unknown_test_type_raises(self):
        with self.assertRaises(ValueError):
            cr.crewed_element_review("eq-008", [{"test_type": "shock_test"}])

    def test_multiple_offgassing_substances_all_checked(self):
        records = list(self._all_four_records())
        records[2] = {
            "test_type": "toxic_offgassing",
            "substances": [
                {"substance": "co", "measured_mg_m3": 0.1, "limit_mg_m3": 1.0},
                {"substance": "toluene", "measured_mg_m3": 5.0, "limit_mg_m3": 1.0},
            ],
        }
        review = cr.crewed_element_review("eq-009", records)
        self.assertEqual(len(review["findings"]), 1)
        self.assertEqual(review["findings"][0]["substance"], "toluene")

    def test_missing_families_sorted(self):
        review = cr.crewed_element_review("eq-010", [])
        self.assertEqual(review["missing_families"], sorted(cr.CREWED_TEST_FAMILIES))


if __name__ == "__main__":
    unittest.main(verbosity=2)
