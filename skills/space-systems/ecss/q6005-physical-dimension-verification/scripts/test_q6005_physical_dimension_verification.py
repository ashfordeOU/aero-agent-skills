"""Contract test for the physical-dimension-verification leaf (stdlib unittest)."""

import math
import unittest

from q6005_physical_dimension_verification_logic import (
    FAIL,
    INDETERMINATE,
    MIN_GAUGE_CAPABILITY_RATIO,
    OUTSIDE,
    PASS,
    WITHIN,
    accumulated_position_tolerance,
    assess_dimension,
    assess_package,
    assess_verification_lot,
    body_dimension,
    check_fit,
    check_terminal_accumulation,
    deviation,
    dimension_status,
    dimensions_not_shown,
    envelope_clearance,
    gauge_capability_ratio,
    limits,
    tolerance_band,
    tolerance_utilization,
    validate_dimension,
    validate_package,
    worst_case_extent,
)


def dim(name="body-length", **kw):
    spec = {
        "name": name,
        "nominal_mm": 12.70,
        "plus_tolerance": 0.20,
        "minus_tolerance": 0.20,
        "measured_mm": 12.72,
        "expanded_uncertainty": 0.01,
    }
    spec.update(kw)
    return spec


def package(unit_id="U-1", **kw):
    record = {
        "id": unit_id,
        "dimensions": [dim(), dim("body-width", nominal_mm=8.00, measured_mm=8.01)],
        "body_extent_name": "body-length",
        "site_extent_mm": 14.00,
        "keep_out_mm": 0.25,
        "terminal_count": 24,
        "pitch_tolerance_mm": 0.01,
        "host_position_allowance_mm": 0.30,
        "accumulation_method": "statistical",
    }
    record.update(kw)
    return record


class TestLimits(unittest.TestCase):
    def test_symmetric_limits_sit_either_side_of_nominal(self):
        lower, upper = limits(dim())
        self.assertAlmostEqual(lower, 12.50, places=9)
        self.assertAlmostEqual(upper, 12.90, places=9)

    def test_asymmetric_tolerances_are_not_folded_together(self):
        lower, upper = limits(dim(plus_tolerance=0.05, minus_tolerance=0.30))
        self.assertAlmostEqual(lower, 12.40, places=9)
        self.assertAlmostEqual(upper, 12.75, places=9)

    def test_band_is_the_sum_of_both_sides(self):
        self.assertAlmostEqual(
            tolerance_band(dim(plus_tolerance=0.05, minus_tolerance=0.30)),
            0.35,
            places=9,
        )

    def test_deviation_is_signed(self):
        self.assertAlmostEqual(deviation(dim(measured_mm=12.60)), -0.10, places=9)
        self.assertAlmostEqual(deviation(dim(measured_mm=12.80)), 0.10, places=9)

    def test_a_zero_width_band_raises(self):
        with self.assertRaises(ValueError):
            validate_dimension(dim(plus_tolerance=0.0, minus_tolerance=0.0))

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            validate_dimension(dim(plus_tolerance=-0.1))

    def test_non_mapping_dimension_raises(self):
        with self.assertRaises(ValueError):
            validate_dimension(["body-length"])

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            validate_dimension(dim(""))


class TestUtilization(unittest.TestCase):
    def test_utilization_uses_the_side_the_reading_went(self):
        spec = dim(plus_tolerance=0.05, minus_tolerance=0.30, measured_mm=12.55)
        self.assertAlmostEqual(tolerance_utilization(spec), 0.15 / 0.30, places=9)

    def test_a_reading_on_nominal_uses_none_of_the_band(self):
        self.assertAlmostEqual(
            tolerance_utilization(dim(measured_mm=12.70)), 0.0, places=12
        )

    def test_a_reading_on_the_limit_uses_all_of_its_side(self):
        self.assertAlmostEqual(
            tolerance_utilization(dim(measured_mm=12.90)), 1.0, places=9
        )

    def test_a_single_sided_band_reports_an_unbounded_utilization(self):
        spec = dim(plus_tolerance=0.0, minus_tolerance=0.20, measured_mm=12.75)
        self.assertEqual(tolerance_utilization(spec), math.inf)


class TestGaugeCapability(unittest.TestCase):
    def test_ratio_is_band_over_the_uncertainty_interval(self):
        self.assertAlmostEqual(
            gauge_capability_ratio(dim()), 0.40 / 0.02, places=9
        )

    def test_a_perfect_gauge_reports_an_unbounded_ratio(self):
        self.assertEqual(gauge_capability_ratio(dim(expanded_uncertainty=0.0)), math.inf)

    def test_a_coarse_gauge_is_a_finding(self):
        report = assess_dimension(dim(expanded_uncertainty=0.15))
        self.assertIn(
            "gauge-uncertainty-too-large-for-the-tolerance-band", report["findings"]
        )

    def test_a_ratio_exactly_on_the_minimum_is_accepted(self):
        uncertainty = 0.40 / (2.0 * MIN_GAUGE_CAPABILITY_RATIO)
        report = assess_dimension(
            dim(measured_mm=12.70, expanded_uncertainty=uncertainty)
        )
        self.assertAlmostEqual(
            report["gauge_capability_ratio"], MIN_GAUGE_CAPABILITY_RATIO, places=9
        )
        self.assertNotIn(
            "gauge-uncertainty-too-large-for-the-tolerance-band", report["findings"]
        )


class TestStatus(unittest.TestCase):
    def test_a_central_reading_is_within(self):
        self.assertEqual(dimension_status(dim(measured_mm=12.70)), WITHIN)

    def test_a_reading_past_the_limit_is_outside(self):
        self.assertEqual(dimension_status(dim(measured_mm=13.00)), OUTSIDE)

    def test_a_reading_inside_the_uncertainty_of_a_limit_is_not_shown(self):
        self.assertEqual(
            dimension_status(dim(measured_mm=12.895, expanded_uncertainty=0.01)),
            INDETERMINATE,
        )

    def test_a_perfect_gauge_leaves_no_indeterminate_zone(self):
        self.assertEqual(
            dimension_status(dim(measured_mm=12.90, expanded_uncertainty=0.0)),
            WITHIN,
        )

    def test_the_lower_guard_band_works_the_same_way(self):
        self.assertEqual(
            dimension_status(dim(measured_mm=12.505, expanded_uncertainty=0.01)),
            INDETERMINATE,
        )

    def test_an_outside_reading_is_a_finding(self):
        report = assess_dimension(dim(measured_mm=13.00))
        self.assertIn("dimension-outside-the-drawing-limits", report["findings"])

    def test_an_indeterminate_reading_is_its_own_finding(self):
        report = assess_dimension(dim(measured_mm=12.895))
        self.assertIn(
            "conformity-not-shown-inside-the-measurement-uncertainty",
            report["findings"],
        )

    def test_a_clean_dimension_carries_no_finding(self):
        self.assertEqual(assess_dimension(dim())["findings"], [])


class TestEnvelope(unittest.TestCase):
    def test_worst_case_extent_takes_the_plus_side(self):
        self.assertAlmostEqual(worst_case_extent(dim()), 12.90, places=9)

    def test_clearance_subtracts_the_keep_out_on_both_sides(self):
        self.assertAlmostEqual(
            envelope_clearance(12.90, 14.00, 0.25), 0.60, places=9
        )

    def test_a_tight_site_leaves_a_negative_clearance(self):
        self.assertLess(envelope_clearance(12.90, 13.00, 0.25), 0.0)

    def test_negative_keep_out_raises(self):
        with self.assertRaises(ValueError):
            envelope_clearance(12.90, 14.00, -0.1)

    def test_interference_is_a_finding(self):
        self.assertIn(
            "worst-case-envelope-exceeds-the-host-site",
            check_fit(package("U-1", site_extent_mm=13.00)),
        )

    def test_a_site_that_just_fits_carries_no_finding(self):
        exact = 12.90 + 2.0 * 0.25
        self.assertEqual(check_fit(package("U-1", site_extent_mm=exact)), [])

    def test_an_unmeasured_body_extent_raises(self):
        with self.assertRaises(ValueError):
            body_dimension(package("U-1", body_extent_name="body-height"))


class TestAccumulation(unittest.TestCase):
    def test_worst_case_accumulates_linearly_over_the_spans(self):
        self.assertAlmostEqual(
            accumulated_position_tolerance(0.01, 24, "worst-case"), 0.23, places=9
        )

    def test_statistical_accumulates_as_the_square_root(self):
        self.assertAlmostEqual(
            accumulated_position_tolerance(0.01, 24, "statistical"),
            0.01 * math.sqrt(23),
            places=12,
        )

    def test_a_longer_row_accumulates_more(self):
        self.assertGreater(
            accumulated_position_tolerance(0.01, 40, "worst-case"),
            accumulated_position_tolerance(0.01, 24, "worst-case"),
        )

    def test_a_single_terminal_row_raises(self):
        with self.assertRaises(ValueError):
            accumulated_position_tolerance(0.01, 1, "worst-case")

    def test_unknown_accumulation_method_raises(self):
        with self.assertRaises(ValueError):
            accumulated_position_tolerance(0.01, 24, "optimistic")

    def test_accumulation_beyond_the_host_allowance_is_a_finding(self):
        self.assertIn(
            "accumulated-terminal-position-exceeds-the-host-allowance",
            check_terminal_accumulation(
                package("U-1", accumulation_method="worst-case",
                        host_position_allowance_mm=0.10)
            ),
        )

    def test_accumulation_exactly_on_the_allowance_is_accepted(self):
        allowance = 0.01 * 23
        record = package(
            "U-1",
            accumulation_method="worst-case",
            host_position_allowance_mm=allowance,
        )
        self.assertEqual(check_terminal_accumulation(record), [])


class TestPackageValidation(unittest.TestCase):
    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            validate_package(["U-1"])

    def test_empty_dimension_list_raises(self):
        with self.assertRaises(ValueError):
            validate_package(package("U-1", dimensions=[]))

    def test_repeated_dimension_name_raises(self):
        with self.assertRaises(ValueError):
            validate_package(package("U-1", dimensions=[dim(), dim()]))

    def test_zero_terminal_count_raises(self):
        with self.assertRaises(ValueError):
            validate_package(package("U-1", terminal_count=0))

    def test_unknown_accumulation_method_on_a_package_raises(self):
        with self.assertRaises(ValueError):
            validate_package(package("U-1", accumulation_method="hopeful"))


class TestAssessPackage(unittest.TestCase):
    def test_a_conforming_package_is_accepted(self):
        result = assess_package(package())
        self.assertEqual(result["disposition"], PASS)
        self.assertEqual(result["findings"], [])

    def test_one_bad_dimension_rejects_the_package(self):
        result = assess_package(
            package("U-1", dimensions=[dim(measured_mm=13.10), dim("body-width")])
        )
        self.assertEqual(result["disposition"], FAIL)
        self.assertIn("dimension-outside-the-drawing-limits", result["findings"])

    def test_findings_are_not_repeated_across_dimensions(self):
        result = assess_package(
            package(
                "U-1",
                dimensions=[
                    dim(measured_mm=13.10),
                    dim("body-width", nominal_mm=8.0, measured_mm=9.0),
                ],
            )
        )
        self.assertEqual(
            result["findings"].count("dimension-outside-the-drawing-limits"), 1
        )

    def test_the_report_carries_the_clearance_and_the_accumulation(self):
        result = assess_package(package())
        self.assertAlmostEqual(result["envelope_clearance_mm"], 0.60, places=9)
        self.assertAlmostEqual(
            result["accumulated_position_mm"], 0.01 * math.sqrt(23), places=12
        )

    def test_indeterminate_dimensions_are_named(self):
        record = package(
            "U-1", dimensions=[dim(measured_mm=12.895), dim("body-width")]
        )
        self.assertEqual(dimensions_not_shown(record), ["body-length"])


class TestLot(unittest.TestCase):
    def test_a_clean_sample_is_accepted(self):
        report = assess_verification_lot([package("U-1"), package("U-2")])
        self.assertTrue(report["sample_accepted"])
        self.assertEqual(report["rejected_ids"], [])

    def test_one_bad_unit_fails_the_sample(self):
        report = assess_verification_lot(
            [package("U-1"), package("U-2", site_extent_mm=13.00)]
        )
        self.assertFalse(report["sample_accepted"])
        self.assertEqual(report["rejected_ids"], ["U-2"])
        self.assertEqual(report["accepted_ids"], ["U-1"])

    def test_the_tightest_clearance_is_reported(self):
        report = assess_verification_lot(
            [package("U-1"), package("U-2", site_extent_mm=13.60)]
        )
        self.assertAlmostEqual(report["tightest_clearance_mm"], 0.20, places=9)

    def test_duplicate_unit_id_raises(self):
        with self.assertRaises(ValueError):
            assess_verification_lot([package("U-1"), package("U-1")])

    def test_empty_sample_raises(self):
        with self.assertRaises(ValueError):
            assess_verification_lot([])

    def test_non_list_sample_raises(self):
        with self.assertRaises(ValueError):
            assess_verification_lot(package())


if __name__ == "__main__":
    unittest.main()
