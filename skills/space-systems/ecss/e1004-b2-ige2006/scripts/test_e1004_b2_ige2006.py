#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C Annex B.2 IGE-2006
geostationary trapped-electron flux model.

Exercises scripts/e1004_b2_ige2006_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the differential
flux at a tabulated energy or L-shell node returns that node's
reference value exactly; a query strictly inside the tabulated node
range is interpolated (log-linear for energy, linear for L-shell) and
flagged as not extrapolated; a query outside the tabulated node range
is flagged as extrapolated; the confidence-level scale factor is 1.0
for "mean" and strictly increasing with a higher worst-case
percentile; a request is compliant only when none of its energy or
L-shell lookups were extrapolated; the assessment record covers every
case with no duplicates and is reported all-compliant only when every
case is compliant.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_b2_ige2006_logic as ige  # noqa: E402


class InterpolateEnergyFluxTest(unittest.TestCase):
    def test_exact_node_returns_reference_value(self):
        flux, extrapolated = ige.interpolate_energy_flux(1.0)
        self.assertEqual(flux, ige.REFERENCE_DIFFERENTIAL_FLUX[1.0])
        self.assertFalse(extrapolated)

    def test_between_nodes_is_interpolated_not_extrapolated(self):
        flux, extrapolated = ige.interpolate_energy_flux(0.5)
        self.assertFalse(extrapolated)
        self.assertLess(flux, ige.REFERENCE_DIFFERENTIAL_FLUX[0.3])
        self.assertGreater(flux, ige.REFERENCE_DIFFERENTIAL_FLUX[0.7])

    def test_below_lowest_node_is_extrapolated(self):
        flux, extrapolated = ige.interpolate_energy_flux(0.01)
        self.assertTrue(extrapolated)
        self.assertEqual(flux, ige.REFERENCE_DIFFERENTIAL_FLUX[ige.ENERGY_NODES_MEV[0]])

    def test_above_highest_node_is_extrapolated(self):
        flux, extrapolated = ige.interpolate_energy_flux(7.0)
        self.assertTrue(extrapolated)
        self.assertEqual(flux, ige.REFERENCE_DIFFERENTIAL_FLUX[ige.ENERGY_NODES_MEV[-1]])

    def test_non_positive_energy_raises(self):
        with self.assertRaises(ValueError):
            ige.interpolate_energy_flux(0.0)
        with self.assertRaises(ValueError):
            ige.interpolate_energy_flux(-1.0)


class InterpolateLShellScaleTest(unittest.TestCase):
    def test_exact_node_returns_reference_value(self):
        scale, extrapolated = ige.interpolate_l_shell_scale(6.6)
        self.assertEqual(scale, ige.L_SHELL_SCALE_FACTOR[6.6])
        self.assertFalse(extrapolated)

    def test_between_nodes_is_interpolated_not_extrapolated(self):
        scale, extrapolated = ige.interpolate_l_shell_scale(6.3)
        self.assertFalse(extrapolated)
        self.assertGreater(scale, ige.L_SHELL_SCALE_FACTOR[6.0])
        self.assertLess(scale, ige.L_SHELL_SCALE_FACTOR[6.6])

    def test_below_lowest_node_is_extrapolated(self):
        scale, extrapolated = ige.interpolate_l_shell_scale(5.0)
        self.assertTrue(extrapolated)
        self.assertEqual(scale, ige.L_SHELL_SCALE_FACTOR[ige.L_SHELL_NODES[0]])

    def test_above_highest_node_is_extrapolated(self):
        scale, extrapolated = ige.interpolate_l_shell_scale(7.5)
        self.assertTrue(extrapolated)
        self.assertEqual(scale, ige.L_SHELL_SCALE_FACTOR[ige.L_SHELL_NODES[-1]])

    def test_non_positive_l_shell_raises(self):
        with self.assertRaises(ValueError):
            ige.interpolate_l_shell_scale(0.0)


class ConfidenceScaleFactorTest(unittest.TestCase):
    def test_mean_is_unit_scale(self):
        self.assertEqual(ige.confidence_scale_factor("mean"), 1.0)

    def test_higher_percentile_scales_up_more(self):
        p90 = ige.confidence_scale_factor("p90")
        p95 = ige.confidence_scale_factor("p95")
        p99 = ige.confidence_scale_factor("p99")
        self.assertGreater(p90, 1.0)
        self.assertGreater(p95, p90)
        self.assertGreater(p99, p95)

    def test_unknown_confidence_level_raises(self):
        with self.assertRaises(ValueError):
            ige.confidence_scale_factor("p50-worst-case")


class ComputeDifferentialFluxTest(unittest.TestCase):
    def test_within_range_point_is_compliant(self):
        result = ige.compute_differential_flux(1.0, 6.6, "mean")
        self.assertTrue(result["within_valid_range"])
        self.assertFalse(result["energy_extrapolated"])
        self.assertFalse(result["l_shell_extrapolated"])
        self.assertEqual(
            result["differential_flux"],
            ige.REFERENCE_DIFFERENTIAL_FLUX[1.0] * ige.L_SHELL_SCALE_FACTOR[6.6] * 1.0,
        )

    def test_out_of_range_energy_is_flagged(self):
        result = ige.compute_differential_flux(10.0, 6.6, "mean")
        self.assertTrue(result["energy_extrapolated"])
        self.assertFalse(result["within_valid_range"])

    def test_out_of_range_l_shell_is_flagged(self):
        result = ige.compute_differential_flux(1.0, 8.0, "mean")
        self.assertTrue(result["l_shell_extrapolated"])
        self.assertFalse(result["within_valid_range"])

    def test_worst_case_confidence_increases_flux(self):
        mean_result = ige.compute_differential_flux(1.0, 6.6, "mean")
        p99_result = ige.compute_differential_flux(1.0, 6.6, "p99")
        self.assertGreater(p99_result["differential_flux"], mean_result["differential_flux"])


class BuildEnergySpectrumTableTest(unittest.TestCase):
    def test_table_order_matches_input(self):
        table = ige.build_energy_spectrum_table([0.1, 1.0, 3.0], 6.6, "mean")
        self.assertEqual([entry["energy_mev"] for entry in table], [0.1, 1.0, 3.0])

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            ige.build_energy_spectrum_table([], 6.6, "mean")


class AssessFluxRequestTest(unittest.TestCase):
    def test_compliant_request_within_tabulated_range(self):
        case = {
            "id": "IGE-001",
            "energy_mev_list": [0.1, 1.0, 3.0],
            "l_shell": 6.6,
            "confidence_level": "p95",
        }
        result = ige.assess_flux_request(case)
        self.assertTrue(result["compliant"])
        self.assertEqual(len(result["spectrum_table"]), 3)

    def test_noncompliant_request_with_extrapolated_energy(self):
        case = {
            "id": "IGE-002",
            "energy_mev_list": [0.1, 8.0],
            "l_shell": 6.6,
            "confidence_level": "mean",
        }
        result = ige.assess_flux_request(case)
        self.assertFalse(result["compliant"])

    def test_noncompliant_request_with_extrapolated_l_shell(self):
        case = {
            "id": "IGE-003",
            "energy_mev_list": [1.0],
            "l_shell": 4.0,
            "confidence_level": "mean",
        }
        result = ige.assess_flux_request(case)
        self.assertFalse(result["compliant"])

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            ige.assess_flux_request({
                "energy_mev_list": [1.0],
                "l_shell": 6.6,
                "confidence_level": "mean",
            })


class BuildAssessmentTest(unittest.TestCase):
    CASES = [
        {
            "id": "IGE-001",
            "energy_mev_list": [0.1, 1.0],
            "l_shell": 6.6,
            "confidence_level": "p95",
        },
        {
            "id": "IGE-002",
            "energy_mev_list": [8.0],
            "l_shell": 6.6,
            "confidence_level": "mean",
        },
    ]

    def test_record_order_and_status(self):
        record = ige.build_assessment(self.CASES)
        self.assertEqual(record[0]["id"], "IGE-001")
        self.assertTrue(record[0]["compliant"])
        self.assertEqual(record[1]["id"], "IGE-002")
        self.assertFalse(record[1]["compliant"])

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            ige.build_assessment(self.CASES + [self.CASES[0]])

    def test_does_not_mutate_input(self):
        before = [dict(c) for c in self.CASES]
        ige.build_assessment(self.CASES)
        self.assertEqual(self.CASES, before)


class RecordSummaryTest(unittest.TestCase):
    def test_noncompliant_items(self):
        record = ige.build_assessment(BuildAssessmentTest.CASES)
        self.assertEqual(ige.noncompliant_items(record), ["IGE-002"])

    def test_all_compliant_true_when_all_pass(self):
        record = ige.build_assessment([BuildAssessmentTest.CASES[0]])
        self.assertTrue(ige.all_compliant(record))

    def test_all_compliant_false_when_any_fail(self):
        record = ige.build_assessment(BuildAssessmentTest.CASES)
        self.assertFalse(ige.all_compliant(record))


if __name__ == "__main__":
    unittest.main(verbosity=2)
