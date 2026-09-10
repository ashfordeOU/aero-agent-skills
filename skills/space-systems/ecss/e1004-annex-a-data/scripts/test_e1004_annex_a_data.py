#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C Annex A natural EM radiation
and solar/geomagnetic index reference dataset.

Exercises scripts/e1004_annex_a_data_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - every required
Annex A quantity must be present with a value and citation; phase-
dependent quantities must use minimum/mean/maximum labels and be
non-decreasing across supplied phases; phase-independent quantities
must use the phase_independent label and carry no solar-cycle phase.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_annex_a_data_logic as annex_a  # noqa: E402


def _entry(value=100.0, citation="ECSS-E-ST-10-04C Annex A"):
    return {"value": value, "citation": citation}


class IsPhaseDependentTests(unittest.TestCase):
    def test_f10_7_is_phase_dependent(self):
        self.assertTrue(annex_a.is_phase_dependent("f10_7"))

    def test_earth_albedo_is_phase_independent(self):
        self.assertFalse(annex_a.is_phase_dependent("earth_albedo"))

    def test_unknown_quantity_raises(self):
        with self.assertRaises(ValueError):
            annex_a.is_phase_dependent("lunar_albedo")


class AssessEntryTests(unittest.TestCase):
    def test_complete_entry_has_no_issues(self):
        self.assertEqual(annex_a.assess_entry(_entry()), [])

    def test_missing_value(self):
        entry = _entry(value=None)
        self.assertIn("missing value", annex_a.assess_entry(entry))

    def test_missing_citation(self):
        entry = _entry(citation="")
        self.assertIn("missing citation", annex_a.assess_entry(entry))

    def test_all_missing(self):
        self.assertEqual(len(annex_a.assess_entry({})), 2)


class AssessQuantityPhaseDependentTests(unittest.TestCase):
    def test_complete_three_phase_quantity(self):
        phase_entries = {
            "minimum": _entry(70.0),
            "mean": _entry(140.0),
            "maximum": _entry(230.0),
        }
        result = annex_a.assess_quantity("f10_7", phase_entries)
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing_phases"], [])
        self.assertTrue(result["ordering_ok"])

    def test_missing_phase_flagged(self):
        phase_entries = {"minimum": _entry(70.0), "maximum": _entry(230.0)}
        result = annex_a.assess_quantity("f10_7", phase_entries)
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing_phases"], ["mean"])

    def test_wrong_label_flagged(self):
        phase_entries = {
            "minimum": _entry(70.0),
            "mean": _entry(140.0),
            "maximum": _entry(230.0),
            "phase_independent": _entry(1.0),
        }
        result = annex_a.assess_quantity("f10_7", phase_entries)
        self.assertFalse(result["complete"])
        self.assertIn("phase_independent", result["issues_by_phase"])

    def test_incomplete_entry_flagged(self):
        phase_entries = {
            "minimum": _entry(70.0),
            "mean": {"value": 140.0, "citation": ""},
            "maximum": _entry(230.0),
        }
        result = annex_a.assess_quantity("f10_7", phase_entries)
        self.assertFalse(result["complete"])
        self.assertIn("missing citation", result["issues_by_phase"]["mean"])

    def test_ordering_violation_detected(self):
        phase_entries = {
            "minimum": _entry(230.0),
            "mean": _entry(140.0),
            "maximum": _entry(70.0),
        }
        result = annex_a.assess_quantity("f10_7", phase_entries)
        self.assertFalse(result["ordering_ok"])
        self.assertFalse(result["complete"])

    def test_equal_values_across_phases_ordering_ok(self):
        phase_entries = {
            "minimum": _entry(100.0),
            "mean": _entry(100.0),
            "maximum": _entry(100.0),
        }
        result = annex_a.assess_quantity("tsi", phase_entries)
        self.assertTrue(result["ordering_ok"])

    def test_single_phase_supplied_skips_ordering_but_flags_missing(self):
        phase_entries = {"mean": _entry(140.0)}
        result = annex_a.assess_quantity("f10_7", phase_entries)
        self.assertTrue(result["ordering_ok"])
        self.assertFalse(result["complete"])
        self.assertEqual(sorted(result["missing_phases"]), ["maximum", "minimum"])


class AssessQuantityPhaseIndependentTests(unittest.TestCase):
    def test_complete_phase_independent_quantity(self):
        phase_entries = {"phase_independent": _entry(0.3)}
        result = annex_a.assess_quantity("earth_albedo", phase_entries)
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing_phases"], [])

    def test_missing_phase_independent_entry_flagged(self):
        result = annex_a.assess_quantity("earth_albedo", {})
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing_phases"], ["phase_independent"])

    def test_solar_cycle_phase_label_on_phase_independent_quantity_flagged(self):
        phase_entries = {"phase_independent": _entry(0.3), "mean": _entry(0.31)}
        result = annex_a.assess_quantity("earth_albedo", phase_entries)
        self.assertFalse(result["complete"])
        self.assertIn("mean", result["issues_by_phase"])


class AssessQuantityErrorTests(unittest.TestCase):
    def test_unknown_quantity_raises(self):
        with self.assertRaises(ValueError):
            annex_a.assess_quantity("lunar_albedo", {})


class AssessDatasetTests(unittest.TestCase):
    def _complete_dataset(self):
        return {
            "quantities": {
                "tsi": {
                    "minimum": _entry(1360.5),
                    "mean": _entry(1361.0),
                    "maximum": _entry(1361.5),
                },
                "euv_xuv_irradiance": {
                    "minimum": _entry(1.0),
                    "mean": _entry(2.0),
                    "maximum": _entry(4.0),
                },
                "f10_7": {
                    "minimum": _entry(70.0),
                    "mean": _entry(140.0),
                    "maximum": _entry(230.0),
                },
                "f10_7a": {
                    "minimum": _entry(72.0),
                    "mean": _entry(140.0),
                    "maximum": _entry(200.0),
                },
                "geomagnetic_index": {
                    "minimum": _entry(5.0),
                    "mean": _entry(15.0),
                    "maximum": _entry(30.0),
                },
                "earth_albedo": {"phase_independent": _entry(0.3)},
                "earth_ir_emission": {"phase_independent": _entry(237.0)},
            }
        }

    def test_complete_dataset(self):
        result = annex_a.assess_dataset(self._complete_dataset())
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing_quantities"], [])

    def test_missing_quantity_blocks_completeness(self):
        dataset = self._complete_dataset()
        del dataset["quantities"]["geomagnetic_index"]
        result = annex_a.assess_dataset(dataset)
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing_quantities"], ["geomagnetic_index"])

    def test_incomplete_quantity_blocks_dataset_completeness(self):
        dataset = self._complete_dataset()
        del dataset["quantities"]["f10_7"]["maximum"]
        result = annex_a.assess_dataset(dataset)
        self.assertFalse(result["complete"])
        self.assertFalse(result["quantity_results"]["f10_7"]["complete"])

    def test_empty_dataset_reports_all_missing(self):
        result = annex_a.assess_dataset({})
        self.assertFalse(result["complete"])
        self.assertEqual(
            result["missing_quantities"], sorted(annex_a.REQUIRED_QUANTITIES)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
