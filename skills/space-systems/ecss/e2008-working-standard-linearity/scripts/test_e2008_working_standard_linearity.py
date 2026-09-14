#!/usr/bin/env python3
"""Contract test for the working standard linearity assessment (offline)."""

import copy
import unittest

from e2008_working_standard_linearity_logic import (
    DEFAULT_LINEARITY_CRITERIA,
    DEVICE_LINEAR,
    DEVICE_NON_LINEAR,
    DEVICE_REFERRED,
    OUT_OF_BAND,
    REFER,
    WITHIN_BAND,
    assess_working_standard_linearity,
    deviation_profile,
    least_squares_line,
    monotonicity_findings,
    range_coverage,
    reference_responsivity,
    responsivity_a_per_w_m2,
    validate_linearity_criteria,
    validate_linearity_points,
)

RESPONSIVITY = 0.0005
SWEEP_IRRADIANCES = (200.0, 400.0, 600.0, 800.0, 1000.0, 1100.0)


def _points(overrides=None, irradiances=SWEEP_IRRADIANCES, offset_a=0.0):
    overrides = overrides or {}
    built = []
    for irradiance in irradiances:
        current = overrides.get(
            irradiance, RESPONSIVITY * irradiance + offset_a
        )
        built.append(
            {
                "irradiance_w_m2": irradiance,
                "short_circuit_current_a": current,
            }
        )
    return built


def _device(points=None, **overrides):
    device = {
        "device_id": "WS-L-001",
        "method_reference": "referenced photovoltaic measurement standard, "
        "linearity method",
        "points": copy.deepcopy(points) if points else _points(),
    }
    device.update(overrides)
    return device


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_linearity_criteria(DEFAULT_LINEARITY_CRITERIA),
            DEFAULT_LINEARITY_CRITERIA,
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_linearity_criteria("default")

    def test_missing_limit_rejected(self):
        broken = dict(DEFAULT_LINEARITY_CRITERIA)
        del broken["max_offset_fraction"]
        with self.assertRaises(ValueError):
            validate_linearity_criteria(broken)

    def test_two_point_minimum_rejected(self):
        broken = dict(DEFAULT_LINEARITY_CRITERIA, min_points=2)
        with self.assertRaises(ValueError):
            validate_linearity_criteria(broken)

    def test_tolerance_of_a_whole_unit_rejected(self):
        broken = dict(
            DEFAULT_LINEARITY_CRITERIA, max_responsivity_deviation_fraction=1.0
        )
        with self.assertRaises(ValueError):
            validate_linearity_criteria(broken)

    def test_review_factor_below_one_rejected(self):
        broken = dict(DEFAULT_LINEARITY_CRITERIA, deviation_review_factor=0.5)
        with self.assertRaises(ValueError):
            validate_linearity_criteria(broken)

    def test_inverted_required_range_rejected(self):
        broken = dict(
            DEFAULT_LINEARITY_CRITERIA,
            required_low_irradiance_w_m2=1200.0,
            required_high_irradiance_w_m2=300.0,
        )
        with self.assertRaises(ValueError):
            validate_linearity_criteria(broken)


class ResponsivityTests(unittest.TestCase):
    def test_responsivity_is_current_over_irradiance(self):
        self.assertAlmostEqual(
            responsivity_a_per_w_m2(0.5, 1000.0), 0.0005, places=12
        )

    def test_non_positive_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            responsivity_a_per_w_m2(0.5, 0.0)

    def test_non_positive_current_rejected(self):
        with self.assertRaises(ValueError):
            responsivity_a_per_w_m2(0.0, 1000.0)


class PointTests(unittest.TestCase):
    def test_points_come_back_in_irradiance_order(self):
        shuffled = list(reversed(_points()))
        resolved = validate_linearity_points(shuffled)
        self.assertEqual(
            [entry["irradiance_w_m2"] for entry in resolved],
            sorted(SWEEP_IRRADIANCES),
        )

    def test_short_sweep_rejected(self):
        with self.assertRaises(ValueError):
            validate_linearity_points(_points()[:5])

    def test_repeat_irradiance_rejected(self):
        points = _points()
        points[1]["irradiance_w_m2"] = points[0]["irradiance_w_m2"]
        with self.assertRaises(ValueError):
            validate_linearity_points(points)

    def test_non_list_sweep_rejected(self):
        with self.assertRaises(ValueError):
            validate_linearity_points("six points")

    def test_non_mapping_point_rejected(self):
        points = _points()
        points[2] = (600.0, 0.3)
        with self.assertRaises(ValueError):
            validate_linearity_points(points)


class AnchorTests(unittest.TestCase):
    def test_anchor_comes_from_the_reference_level(self):
        self.assertAlmostEqual(
            reference_responsivity(_points()), RESPONSIVITY, places=12
        )

    def test_sweep_without_a_reference_point_rejected(self):
        with self.assertRaises(ValueError):
            reference_responsivity(
                _points(irradiances=(100.0, 200.0, 300.0, 400.0, 500.0, 600.0))
            )

    def test_anchor_ignores_points_outside_the_band(self):
        points = _points(overrides={200.0: 0.11})
        self.assertAlmostEqual(
            reference_responsivity(points), RESPONSIVITY, places=12
        )


class LineFitTests(unittest.TestCase):
    def test_slope_and_intercept_recovered(self):
        slope, intercept = least_squares_line([(0.0, 1.0), (1.0, 3.0), (2.0, 5.0)])
        self.assertAlmostEqual(slope, 2.0, places=9)
        self.assertAlmostEqual(intercept, 1.0, places=9)

    def test_line_through_one_point_rejected(self):
        with self.assertRaises(ValueError):
            least_squares_line([(1.0, 2.0)])

    def test_line_with_a_single_x_value_rejected(self):
        with self.assertRaises(ValueError):
            least_squares_line([(1.0, 2.0), (1.0, 3.0)])


class DeviationTests(unittest.TestCase):
    def test_linear_sweep_has_no_deviation(self):
        for entry in deviation_profile(_points()):
            self.assertAlmostEqual(entry["deviation_fraction"], 0.0, places=9)
            self.assertEqual(entry["disposition"], WITHIN_BAND)

    def test_point_exactly_on_the_allowance_stays_within_band(self):
        allowance = DEFAULT_LINEARITY_CRITERIA[
            "max_responsivity_deviation_fraction"
        ]
        points = _points(overrides={600.0: RESPONSIVITY * 600.0 * (1.0 + allowance)})
        entry = [e for e in deviation_profile(points) if e["irradiance_w_m2"] == 600.0][0]
        self.assertAlmostEqual(entry["deviation_fraction"], allowance, places=9)
        self.assertEqual(entry["disposition"], WITHIN_BAND)

    def test_point_past_the_allowance_is_referred(self):
        points = _points(overrides={600.0: RESPONSIVITY * 600.0 * 1.007})
        entry = [e for e in deviation_profile(points) if e["irradiance_w_m2"] == 600.0][0]
        self.assertEqual(entry["disposition"], REFER)

    def test_point_past_the_review_limit_is_out_of_band(self):
        points = _points(overrides={600.0: RESPONSIVITY * 600.0 * 1.02})
        entry = [e for e in deviation_profile(points) if e["irradiance_w_m2"] == 600.0][0]
        self.assertEqual(entry["disposition"], OUT_OF_BAND)

    def test_a_low_reading_deviates_as_much_as_a_high_one(self):
        points = _points(overrides={600.0: RESPONSIVITY * 600.0 * 0.98})
        entry = [e for e in deviation_profile(points) if e["irradiance_w_m2"] == 600.0][0]
        self.assertLess(entry["deviation_fraction"], 0.0)
        self.assertEqual(entry["disposition"], OUT_OF_BAND)


class CoverageTests(unittest.TestCase):
    def test_full_sweep_covers_the_required_range(self):
        coverage = range_coverage(_points())
        self.assertTrue(coverage["covers_required_range"])
        self.assertEqual(coverage["gaps"], [])
        self.assertAlmostEqual(coverage["range_ratio"], 5.5, places=9)

    def test_narrow_sweep_reports_every_gap(self):
        coverage = range_coverage(
            _points(irradiances=(800.0, 850.0, 900.0, 950.0, 1000.0, 1050.0))
        )
        self.assertFalse(coverage["covers_required_range"])
        self.assertEqual(len(coverage["gaps"]), 3)

    def test_monotonic_sweep_has_no_findings(self):
        self.assertEqual(monotonicity_findings(_points()), [])

    def test_falling_current_is_reported(self):
        points = _points(overrides={800.0: 0.28})
        findings = monotonicity_findings(points)
        self.assertEqual(len(findings), 1)
        self.assertIn("current fell", findings[0])


class DeviceTests(unittest.TestCase):
    def test_linear_device_passes(self):
        result = assess_working_standard_linearity(_device())
        self.assertEqual(result["verdict"], DEVICE_LINEAR)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["out_of_band_irradiances_w_m2"], [])
        self.assertAlmostEqual(
            result["fitted_slope_a_per_w_m2"], RESPONSIVITY, places=12
        )
        self.assertAlmostEqual(result["offset_fraction"], 0.0, places=9)

    def test_reference_current_follows_the_anchor(self):
        result = assess_working_standard_linearity(_device())
        self.assertAlmostEqual(result["reference_current_a"], 0.5, places=9)

    def test_curved_device_is_non_linear_and_names_the_irradiance(self):
        points = _points(overrides={400.0: RESPONSIVITY * 400.0 * 1.03})
        result = assess_working_standard_linearity(_device(points))
        self.assertEqual(result["verdict"], DEVICE_NON_LINEAR)
        self.assertAlmostEqual(
            result["worst_deviation_irradiance_w_m2"], 400.0, places=9
        )
        self.assertIn(400.0, result["out_of_band_irradiances_w_m2"])

    def test_offset_device_reports_a_current_at_zero_irradiance(self):
        result = assess_working_standard_linearity(_device(_points(offset_a=0.002)))
        self.assertAlmostEqual(result["fitted_intercept_a"], 0.002, places=9)
        self.assertGreater(result["offset_fraction"], 0.002)
        self.assertTrue(
            any("zero irradiance" in finding for finding in result["findings"])
        )

    def test_offset_bites_hardest_at_the_bottom_of_the_range(self):
        result = assess_working_standard_linearity(_device(_points(offset_a=0.002)))
        profile = {entry["irradiance_w_m2"]: entry for entry in result["profile"]}
        self.assertGreater(
            profile[200.0]["deviation_magnitude"],
            profile[800.0]["deviation_magnitude"],
        )

    def test_narrow_sweep_refers_an_otherwise_linear_device(self):
        result = assess_working_standard_linearity(
            _device(_points(irradiances=(800.0, 850.0, 900.0, 950.0, 1000.0, 1050.0)))
        )
        self.assertEqual(result["verdict"], DEVICE_REFERRED)
        self.assertFalse(result["coverage"]["covers_required_range"])

    def test_falling_reading_refers_the_device(self):
        result = assess_working_standard_linearity(
            _device(_points(overrides={1100.0: 0.49}))
        )
        self.assertTrue(
            any("current fell" in finding for finding in result["findings"])
        )
        self.assertNotEqual(result["verdict"], DEVICE_LINEAR)

    def test_device_without_a_named_method_rejected(self):
        device = _device()
        device["method_reference"] = "   "
        with self.assertRaises(ValueError):
            assess_working_standard_linearity(device)

    def test_device_without_an_id_rejected(self):
        device = _device()
        device["device_id"] = ""
        with self.assertRaises(ValueError):
            assess_working_standard_linearity(device)

    def test_non_mapping_device_rejected(self):
        with self.assertRaises(ValueError):
            assess_working_standard_linearity("WS-L-001")

    def test_device_without_points_rejected(self):
        device = _device()
        del device["points"]
        with self.assertRaises(ValueError):
            assess_working_standard_linearity(device)

    def test_point_count_is_reported(self):
        result = assess_working_standard_linearity(_device())
        self.assertEqual(result["point_count"], len(SWEEP_IRRADIANCES))

    def test_input_is_not_mutated_by_the_assessment(self):
        device = _device(_points(overrides={600.0: RESPONSIVITY * 600.0 * 1.02}))
        before = copy.deepcopy(device)
        assess_working_standard_linearity(device)
        self.assertEqual(device, before)


if __name__ == "__main__":
    unittest.main()
