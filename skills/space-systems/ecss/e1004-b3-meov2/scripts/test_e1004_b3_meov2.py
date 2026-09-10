#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C Annex B.3 ONERA MEOv2
trapped-electron flux model.

Exercises scripts/e1004_b3_meov2_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - an L-shell within
[MEO_L_SHELL_MIN, MEO_L_SHELL_MAX] is valid and one outside it raises
on interpolation; the reference grid interpolates linearly between
bracketing nodes and returns the node values exactly at a grid point;
the spectral form is a positive, monotonically decreasing function of
energy at fixed L-shell; the orbit-average flux is a dwell-weighted
combination of the per-sample fluxes and defaults to equal weighting;
the worst-case L-shell is the sample with the highest flux at the
given energy; a case is valid only when every one of its L-shell
samples is in range, and an invalid case reports no computed flux; the
assessment record covers every case with no duplicates and is reported
all-valid only when every case is valid.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_b3_meov2_logic as ml  # noqa: E402


class ValidateLShellTest(unittest.TestCase):
    def test_in_range_does_not_raise(self):
        ml.validate_l_shell(ml.MEO_L_SHELL_MIN)
        ml.validate_l_shell(ml.MEO_L_SHELL_MAX)
        ml.validate_l_shell(4.5)

    def test_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            ml.validate_l_shell(ml.MEO_L_SHELL_MIN - 0.1)
        with self.assertRaises(ValueError):
            ml.validate_l_shell(ml.MEO_L_SHELL_MAX + 0.1)


class LShellInRangeTest(unittest.TestCase):
    def test_true_within_range(self):
        self.assertTrue(ml.l_shell_in_range(3.5))

    def test_false_outside_range(self):
        self.assertFalse(ml.l_shell_in_range(1.0))
        self.assertFalse(ml.l_shell_in_range(8.0))


class InterpolateSpectralParamsTest(unittest.TestCase):
    def test_exact_grid_node_returns_node_values(self):
        reference_flux, e_folding_energy = ml.interpolate_spectral_params(4.0)
        self.assertEqual(reference_flux, 2.0e4)
        self.assertEqual(e_folding_energy, 0.70)

    def test_last_grid_node_returns_node_values(self):
        reference_flux, e_folding_energy = ml.interpolate_spectral_params(7.0)
        self.assertEqual(reference_flux, 1.0e3)
        self.assertEqual(e_folding_energy, 1.30)

    def test_midpoint_interpolates_linearly(self):
        reference_flux, e_folding_energy = ml.interpolate_spectral_params(2.5)
        self.assertAlmostEqual(reference_flux, 7.5e4)
        self.assertAlmostEqual(e_folding_energy, 0.40)

    def test_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            ml.interpolate_spectral_params(1.0)
        with self.assertRaises(ValueError):
            ml.interpolate_spectral_params(9.0)


class DifferentialFluxTest(unittest.TestCase):
    def test_zero_energy_returns_reference_flux(self):
        self.assertAlmostEqual(ml.differential_flux(0.0, 4.0), 2.0e4)

    def test_flux_decreases_with_energy(self):
        low = ml.differential_flux(0.1, 4.0)
        high = ml.differential_flux(1.0, 4.0)
        self.assertGreater(low, high)
        self.assertGreater(high, 0.0)

    def test_negative_energy_raises(self):
        with self.assertRaises(ValueError):
            ml.differential_flux(-1.0, 4.0)

    def test_out_of_range_l_shell_raises(self):
        with self.assertRaises(ValueError):
            ml.differential_flux(0.5, 9.0)


class IntegralFluxAboveTest(unittest.TestCase):
    def test_zero_threshold_equals_reference_flux_times_e_folding(self):
        expected = 2.0e4 * 0.70
        self.assertAlmostEqual(ml.integral_flux_above(0.0, 4.0), expected)

    def test_integral_flux_decreases_with_threshold(self):
        low = ml.integral_flux_above(0.2, 4.0)
        high = ml.integral_flux_above(1.0, 4.0)
        self.assertGreater(low, high)

    def test_negative_threshold_raises(self):
        with self.assertRaises(ValueError):
            ml.integral_flux_above(-0.1, 4.0)


class OrbitAverageFluxTest(unittest.TestCase):
    def test_equal_weighting_default(self):
        samples = [3.0, 5.0]
        expected = (
            ml.differential_flux(0.5, 3.0) + ml.differential_flux(0.5, 5.0)
        ) / 2.0
        self.assertAlmostEqual(ml.orbit_average_flux(0.5, samples), expected)

    def test_dwell_weighted_average(self):
        samples = [3.0, 5.0]
        weights = [0.75, 0.25]
        expected = (
            0.75 * ml.differential_flux(0.5, 3.0)
            + 0.25 * ml.differential_flux(0.5, 5.0)
        )
        self.assertAlmostEqual(ml.orbit_average_flux(0.5, samples, weights), expected)

    def test_empty_samples_raises(self):
        with self.assertRaises(ValueError):
            ml.orbit_average_flux(0.5, [])

    def test_mismatched_dwell_fractions_length_raises(self):
        with self.assertRaises(ValueError):
            ml.orbit_average_flux(0.5, [3.0, 5.0], [1.0])

    def test_dwell_fractions_not_summing_to_one_raises(self):
        with self.assertRaises(ValueError):
            ml.orbit_average_flux(0.5, [3.0, 5.0], [0.5, 0.6])


class WorstCaseLShellTest(unittest.TestCase):
    def test_lower_l_shell_gives_higher_flux_in_this_grid(self):
        samples = [3.0, 5.0, 7.0]
        self.assertEqual(ml.worst_case_l_shell(0.5, samples), 3.0)

    def test_empty_samples_raises(self):
        with self.assertRaises(ValueError):
            ml.worst_case_l_shell(0.5, [])


class AssessMeov2CaseTest(unittest.TestCase):
    def test_valid_case_reports_flux_results(self):
        case = {
            "id": "MEOV2-001",
            "l_shell_samples": [3.0, 4.0, 5.0],
            "energy_mev": 0.5,
        }
        result = ml.assess_meov2_case(case)
        self.assertTrue(result["valid"])
        self.assertEqual(result["l_shell_in_range"], [True, True, True])
        self.assertIsNotNone(result["orbit_average_flux"])
        self.assertEqual(result["worst_case_l_shell"], 3.0)
        self.assertIsNotNone(result["worst_case_flux"])

    def test_invalid_case_reports_no_flux_results(self):
        case = {
            "id": "MEOV2-002",
            "l_shell_samples": [3.0, 8.0],
            "energy_mev": 0.5,
        }
        result = ml.assess_meov2_case(case)
        self.assertFalse(result["valid"])
        self.assertEqual(result["l_shell_in_range"], [True, False])
        self.assertIsNone(result["orbit_average_flux"])
        self.assertIsNone(result["worst_case_l_shell"])
        self.assertIsNone(result["worst_case_flux"])

    def test_dwell_fractions_honored(self):
        case = {
            "id": "MEOV2-003",
            "l_shell_samples": [3.0, 5.0],
            "energy_mev": 0.5,
            "dwell_fractions": [0.9, 0.1],
        }
        result = ml.assess_meov2_case(case)
        expected = ml.orbit_average_flux(0.5, [3.0, 5.0], [0.9, 0.1])
        self.assertAlmostEqual(result["orbit_average_flux"], expected)

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            ml.assess_meov2_case({"l_shell_samples": [3.0], "energy_mev": 0.5})

    def test_empty_l_shell_samples_raises(self):
        with self.assertRaises(ValueError):
            ml.assess_meov2_case(
                {"id": "MEOV2-004", "l_shell_samples": [], "energy_mev": 0.5}
            )

    def test_does_not_mutate_input(self):
        case = {
            "id": "MEOV2-005",
            "l_shell_samples": [3.0, 4.0],
            "energy_mev": 0.5,
        }
        before = dict(case)
        before["l_shell_samples"] = list(case["l_shell_samples"])
        ml.assess_meov2_case(case)
        self.assertEqual(case["l_shell_samples"], before["l_shell_samples"])
        self.assertEqual(case["id"], before["id"])
        self.assertEqual(case["energy_mev"], before["energy_mev"])


class BuildMeov2AssessmentTest(unittest.TestCase):
    CASES = [
        {
            "id": "MEOV2-001",
            "l_shell_samples": [3.0, 4.0],
            "energy_mev": 0.5,
        },
        {
            "id": "MEOV2-002",
            "l_shell_samples": [3.0, 8.0],
            "energy_mev": 0.5,
        },
    ]

    def test_record_order_and_status(self):
        record = ml.build_meov2_assessment(self.CASES)
        self.assertEqual(record[0]["id"], "MEOV2-001")
        self.assertTrue(record[0]["valid"])
        self.assertEqual(record[1]["id"], "MEOV2-002")
        self.assertFalse(record[1]["valid"])

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            ml.build_meov2_assessment(self.CASES + [self.CASES[0]])


class RecordSummaryTest(unittest.TestCase):
    def test_invalid_items(self):
        record = ml.build_meov2_assessment(BuildMeov2AssessmentTest.CASES)
        self.assertEqual(ml.invalid_items(record), ["MEOV2-002"])

    def test_all_valid_true_when_all_pass(self):
        record = ml.build_meov2_assessment([BuildMeov2AssessmentTest.CASES[0]])
        self.assertTrue(ml.all_valid(record))

    def test_all_valid_false_when_any_fail(self):
        record = ml.build_meov2_assessment(BuildMeov2AssessmentTest.CASES)
        self.assertFalse(ml.all_valid(record))


if __name__ == "__main__":
    unittest.main(verbosity=2)
