#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C Annex B.4 FLUMIC worst-case
trapped electron model.

Exercises scripts/e1004_b4_flumic_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - region parameters are
looked up per belt region ("inner_belt", "outer_belt"); confidence and
duration scale factors are looked up per percentile and duration
class; the differential spectrum is an exponential reference spectrum
scaled by those factors; the integral flux above a threshold energy is
the analytic integral of that spectrum; the combined integral flux
sums every region an orbit crosses; a case is compliant only when its
duration class matches what its analysis purpose requires (worst_day
for peak_risk, mission for cumulative_fluence); the assessment record
covers every case with no duplicates and is reported all-compliant
only when every case is compliant.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_b4_flumic_logic as fl  # noqa: E402


class RegionParamsTest(unittest.TestCase):
    def test_inner_belt_params(self):
        self.assertEqual(fl.region_params("inner_belt"), fl.REGION_PARAMS["inner_belt"])

    def test_outer_belt_params(self):
        self.assertEqual(fl.region_params("outer_belt"), fl.REGION_PARAMS["outer_belt"])

    def test_returns_copy_not_reference(self):
        params = fl.region_params("outer_belt")
        params["flux0"] = -1.0
        self.assertEqual(fl.REGION_PARAMS["outer_belt"]["flux0"], 2.0e10)

    def test_unknown_region_raises(self):
        with self.assertRaises(ValueError):
            fl.region_params("radiation_belt_c")


class ConfidenceScaleFactorTest(unittest.TestCase):
    def test_known_percentiles(self):
        self.assertEqual(fl.confidence_scale_factor(90), 1.0)
        self.assertEqual(fl.confidence_scale_factor(95), 1.3)
        self.assertEqual(fl.confidence_scale_factor(99), 1.8)

    def test_unsupported_percentile_raises(self):
        with self.assertRaises(ValueError):
            fl.confidence_scale_factor(50)


class DurationScaleFactorTest(unittest.TestCase):
    def test_known_duration_classes(self):
        self.assertEqual(fl.duration_scale_factor("worst_day"), 1.0)
        self.assertEqual(fl.duration_scale_factor("worst_week"), 0.6)
        self.assertEqual(fl.duration_scale_factor("mission"), 0.25)

    def test_unknown_duration_class_raises(self):
        with self.assertRaises(ValueError):
            fl.duration_scale_factor("worst_year")


class RequiredDurationClassTest(unittest.TestCase):
    def test_peak_risk_requires_worst_day(self):
        self.assertEqual(fl.required_duration_class("peak_risk"), "worst_day")

    def test_cumulative_fluence_requires_mission(self):
        self.assertEqual(fl.required_duration_class("cumulative_fluence"), "mission")

    def test_unknown_purpose_raises(self):
        with self.assertRaises(ValueError):
            fl.required_duration_class("dose")


class DifferentialFluxTest(unittest.TestCase):
    def test_flux_at_zero_energy_equals_scaled_flux0(self):
        value = fl.differential_flux("outer_belt", 0.0, 90, "worst_day")
        self.assertAlmostEqual(value, fl.REGION_PARAMS["outer_belt"]["flux0"])

    def test_flux_decreases_with_energy(self):
        low = fl.differential_flux("outer_belt", 0.5, 90, "worst_day")
        high = fl.differential_flux("outer_belt", 2.0, 90, "worst_day")
        self.assertGreater(low, high)

    def test_higher_confidence_increases_flux(self):
        base = fl.differential_flux("outer_belt", 1.0, 90, "worst_day")
        higher = fl.differential_flux("outer_belt", 1.0, 99, "worst_day")
        self.assertGreater(higher, base)

    def test_longer_duration_decreases_flux(self):
        worst_day = fl.differential_flux("outer_belt", 1.0, 90, "worst_day")
        mission = fl.differential_flux("outer_belt", 1.0, 90, "mission")
        self.assertGreater(worst_day, mission)

    def test_negative_energy_raises(self):
        with self.assertRaises(ValueError):
            fl.differential_flux("outer_belt", -1.0, 90, "worst_day")


class IntegralFluxAboveTest(unittest.TestCase):
    def test_zero_threshold_equals_flux0_times_e0(self):
        params = fl.REGION_PARAMS["outer_belt"]
        expected = params["flux0"] * params["e0_mev"]
        self.assertAlmostEqual(
            fl.integral_flux_above("outer_belt", 0.0, 90, "worst_day"), expected
        )

    def test_higher_threshold_decreases_integral(self):
        low_threshold = fl.integral_flux_above("outer_belt", 1.0, 90, "worst_day")
        high_threshold = fl.integral_flux_above("outer_belt", 3.0, 90, "worst_day")
        self.assertGreater(low_threshold, high_threshold)

    def test_negative_threshold_raises(self):
        with self.assertRaises(ValueError):
            fl.integral_flux_above("outer_belt", -1.0, 90, "worst_day")


class CombinedIntegralFluxAboveTest(unittest.TestCase):
    def test_combines_both_regions(self):
        inner = fl.integral_flux_above("inner_belt", 1.0, 90, "worst_day")
        outer = fl.integral_flux_above("outer_belt", 1.0, 90, "worst_day")
        combined = fl.combined_integral_flux_above(
            ["inner_belt", "outer_belt"], 1.0, 90, "worst_day"
        )
        self.assertAlmostEqual(combined, inner + outer)

    def test_single_region_matches_integral_flux_above(self):
        combined = fl.combined_integral_flux_above(["outer_belt"], 1.0, 90, "worst_day")
        self.assertAlmostEqual(
            combined, fl.integral_flux_above("outer_belt", 1.0, 90, "worst_day")
        )

    def test_empty_regions_raises(self):
        with self.assertRaises(ValueError):
            fl.combined_integral_flux_above([], 1.0, 90, "worst_day")


class AssessCaseTest(unittest.TestCase):
    def test_compliant_peak_risk_case(self):
        case = {
            "id": "FLU-001",
            "regions": ["outer_belt"],
            "analysis_purpose": "peak_risk",
            "duration_class": "worst_day",
            "percentile": 95,
            "threshold_energy_mev": 1.5,
        }
        result = fl.assess_case(case)
        self.assertEqual(result["required_duration_class"], "worst_day")
        self.assertTrue(result["duration_class_ok"])
        self.assertTrue(result["compliant"])
        self.assertGreater(result["flux_above_threshold"], 0.0)

    def test_noncompliant_peak_risk_case_with_mission_duration(self):
        case = {
            "id": "FLU-002",
            "regions": ["outer_belt"],
            "analysis_purpose": "peak_risk",
            "duration_class": "mission",
            "percentile": 95,
            "threshold_energy_mev": 1.5,
        }
        result = fl.assess_case(case)
        self.assertFalse(result["duration_class_ok"])
        self.assertFalse(result["compliant"])

    def test_compliant_cumulative_fluence_case(self):
        case = {
            "id": "FLU-003",
            "regions": ["inner_belt", "outer_belt"],
            "analysis_purpose": "cumulative_fluence",
            "duration_class": "mission",
            "percentile": 90,
            "threshold_energy_mev": 1.0,
        }
        result = fl.assess_case(case)
        self.assertTrue(result["duration_class_ok"])
        self.assertTrue(result["compliant"])

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            fl.assess_case({
                "regions": ["outer_belt"],
                "analysis_purpose": "peak_risk",
                "duration_class": "worst_day",
                "percentile": 90,
                "threshold_energy_mev": 1.0,
            })

    def test_unknown_analysis_purpose_raises(self):
        with self.assertRaises(ValueError):
            fl.assess_case({
                "id": "FLU-004",
                "regions": ["outer_belt"],
                "analysis_purpose": "dose",
                "duration_class": "worst_day",
                "percentile": 90,
                "threshold_energy_mev": 1.0,
            })

    def test_does_not_mutate_input_regions_list(self):
        regions = ["outer_belt"]
        case = {
            "id": "FLU-005",
            "regions": regions,
            "analysis_purpose": "peak_risk",
            "duration_class": "worst_day",
            "percentile": 90,
            "threshold_energy_mev": 1.0,
        }
        result = fl.assess_case(case)
        result["regions"].append("inner_belt")
        self.assertEqual(regions, ["outer_belt"])


class BuildAssessmentTest(unittest.TestCase):
    CASES = [
        {
            "id": "FLU-001",
            "regions": ["outer_belt"],
            "analysis_purpose": "peak_risk",
            "duration_class": "worst_day",
            "percentile": 95,
            "threshold_energy_mev": 1.5,
        },
        {
            "id": "FLU-002",
            "regions": ["outer_belt"],
            "analysis_purpose": "peak_risk",
            "duration_class": "mission",
            "percentile": 95,
            "threshold_energy_mev": 1.5,
        },
    ]

    def test_record_order_and_status(self):
        record = fl.build_assessment(self.CASES)
        self.assertEqual(record[0]["id"], "FLU-001")
        self.assertTrue(record[0]["compliant"])
        self.assertEqual(record[1]["id"], "FLU-002")
        self.assertFalse(record[1]["compliant"])

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            fl.build_assessment(self.CASES + [self.CASES[0]])

    def test_does_not_mutate_input(self):
        before = [dict(c) for c in self.CASES]
        fl.build_assessment(self.CASES)
        self.assertEqual(self.CASES, before)


class RecordSummaryTest(unittest.TestCase):
    def test_noncompliant_items(self):
        record = fl.build_assessment(BuildAssessmentTest.CASES)
        self.assertEqual(fl.noncompliant_items(record), ["FLU-002"])

    def test_all_compliant_true_when_all_pass(self):
        record = fl.build_assessment([BuildAssessmentTest.CASES[0]])
        self.assertTrue(fl.all_compliant(record))

    def test_all_compliant_false_when_any_fail(self):
        record = fl.build_assessment(BuildAssessmentTest.CASES)
        self.assertFalse(fl.all_compliant(record))


if __name__ == "__main__":
    unittest.main(verbosity=2)
