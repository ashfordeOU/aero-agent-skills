#!/usr/bin/env python3
"""Gate 3 contract test for e2007-shielded-enclosure-sizing.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_shielded_enclosure_sizing.py
"""

import math
import unittest

from e2007_shielded_enclosure_sizing_logic import (
    ANTENNA_TIP_CLEARANCE_M,
    CALIBRATED_STANDOFFS_M,
    DIM_TOL_M,
    antenna_geometry,
    assess_shielded_enclosure_sizing,
    axis_result,
    bench_footprint,
    fits,
    required_lateral_axis,
    required_measurement_axis,
    required_vertical_axis,
    usable_envelope,
    validate_enclosure,
    validate_layout,
    validate_standoff,
)


def big_enclosure(**over):
    record = {
        "internal_length_m": 12.0,
        "internal_width_m": 8.0,
        "internal_height_m": 6.0,
        "wall_absorber_depth_m": 0.6,
        "ceiling_absorber_depth_m": 0.6,
        "floor_absorber_depth_m": 0.0,
        "quiet_zone_diameter_m": 2.5,
    }
    record.update(over)
    return record


def small_layout(**over):
    record = {
        "unit_depth_m": 0.6,
        "unit_width_m": 0.8,
        "unit_height_m": 0.4,
        "bench_height_m": 0.8,
        "edge_clearance_m": 0.1,
        "ceiling_headroom_m": 0.5,
        "antenna_scan_top_m": 2.0,
    }
    record.update(over)
    return record


class TestEnclosureValidation(unittest.TestCase):
    def test_valid_enclosure_normalizes(self):
        record = validate_enclosure(big_enclosure())
        self.assertAlmostEqual(record["internal_length_m"], 12.0)
        self.assertAlmostEqual(record["wall_absorber_depth_m"], 0.6)

    def test_ceiling_absorber_defaults_to_wall_depth(self):
        record = big_enclosure()
        del record["ceiling_absorber_depth_m"]
        self.assertAlmostEqual(validate_enclosure(record)["ceiling_absorber_depth_m"], 0.6)

    def test_floor_absorber_defaults_to_zero(self):
        record = big_enclosure()
        del record["floor_absorber_depth_m"]
        self.assertAlmostEqual(validate_enclosure(record)["floor_absorber_depth_m"], 0.0)

    def test_non_mapping_enclosure_rejected(self):
        with self.assertRaises(ValueError):
            validate_enclosure([12.0, 8.0, 6.0])

    def test_missing_internal_dimension_rejected(self):
        record = big_enclosure()
        del record["internal_height_m"]
        with self.assertRaises(ValueError):
            validate_enclosure(record)

    def test_zero_internal_dimension_rejected(self):
        with self.assertRaises(ValueError):
            validate_enclosure(big_enclosure(internal_width_m=0.0))

    def test_negative_absorber_depth_rejected(self):
        with self.assertRaises(ValueError):
            validate_enclosure(big_enclosure(wall_absorber_depth_m=-0.1))

    def test_non_numeric_dimension_rejected(self):
        with self.assertRaises(ValueError):
            validate_enclosure(big_enclosure(internal_length_m="twelve"))

    def test_boolean_dimension_rejected(self):
        with self.assertRaises(ValueError):
            validate_enclosure(big_enclosure(internal_length_m=True))

    def test_non_finite_dimension_rejected(self):
        with self.assertRaises(ValueError):
            validate_enclosure(big_enclosure(internal_length_m=float("inf")))

    def test_absorber_consuming_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_enclosure(big_enclosure(internal_width_m=1.0))

    def test_absorber_consuming_height_rejected(self):
        with self.assertRaises(ValueError):
            validate_enclosure(
                big_enclosure(
                    internal_height_m=1.0,
                    ceiling_absorber_depth_m=0.6,
                    floor_absorber_depth_m=0.6,
                )
            )


class TestUsableEnvelope(unittest.TestCase):
    def test_wall_absorber_removed_from_both_ends(self):
        usable = usable_envelope(big_enclosure())
        self.assertAlmostEqual(usable["measurement_m"], 12.0 - 1.2)
        self.assertAlmostEqual(usable["lateral_m"], 8.0 - 1.2)

    def test_vertical_removes_ceiling_and_floor_only(self):
        usable = usable_envelope(big_enclosure(floor_absorber_depth_m=0.3))
        self.assertAlmostEqual(usable["vertical_m"], 6.0 - 0.6 - 0.3)

    def test_quiet_zone_carried_through(self):
        self.assertAlmostEqual(
            usable_envelope(big_enclosure())["quiet_zone_diameter_m"], 2.5
        )


class TestAntennaAndStandoff(unittest.TestCase):
    def test_known_antenna_geometry(self):
        geometry = antenna_geometry("biconical")
        self.assertAlmostEqual(geometry["depth"], 0.55)
        self.assertAlmostEqual(geometry["half_aperture"], 0.70)

    def test_antenna_type_is_case_insensitive(self):
        self.assertAlmostEqual(antenna_geometry("Log-Periodic")["depth"], 0.75)

    def test_unknown_antenna_type_rejected(self):
        with self.assertRaises(ValueError):
            antenna_geometry("parabolic-dish")

    def test_non_string_antenna_type_rejected(self):
        with self.assertRaises(ValueError):
            antenna_geometry(3)

    def test_returned_geometry_is_a_copy(self):
        geometry = antenna_geometry("loop")
        geometry["depth"] = 99.0
        self.assertAlmostEqual(antenna_geometry("loop")["depth"], 0.20)

    def test_calibrated_standoffs_accepted(self):
        for standoff in CALIBRATED_STANDOFFS_M:
            self.assertAlmostEqual(validate_standoff(standoff), standoff)

    def test_uncalibrated_standoff_rejected(self):
        with self.assertRaises(ValueError):
            validate_standoff(2.0)

    def test_zero_standoff_rejected(self):
        with self.assertRaises(ValueError):
            validate_standoff(0.0)


class TestLayoutValidation(unittest.TestCase):
    def test_layout_defaults_applied(self):
        record = small_layout()
        del record["ceiling_headroom_m"]
        del record["antenna_scan_top_m"]
        normalized = validate_layout(record)
        self.assertAlmostEqual(normalized["ceiling_headroom_m"], 0.5)
        self.assertAlmostEqual(normalized["antenna_scan_top_m"], 0.0)
        self.assertAlmostEqual(normalized["support_rack_width_m"], 0.0)

    def test_non_mapping_layout_rejected(self):
        with self.assertRaises(ValueError):
            validate_layout("bench")

    def test_zero_unit_height_rejected(self):
        with self.assertRaises(ValueError):
            validate_layout(small_layout(unit_height_m=0.0))

    def test_negative_edge_clearance_rejected(self):
        with self.assertRaises(ValueError):
            validate_layout(small_layout(edge_clearance_m=-0.05))

    def test_rack_separation_without_rack_rejected(self):
        with self.assertRaises(ValueError):
            validate_layout(small_layout(support_rack_separation_m=0.5))

    def test_bench_footprint_and_diagonal(self):
        footprint = bench_footprint(small_layout())
        self.assertAlmostEqual(footprint["depth_m"], 0.8)
        self.assertAlmostEqual(footprint["width_m"], 1.0)
        self.assertAlmostEqual(footprint["diagonal_m"], math.hypot(0.8, 1.0))


class TestAxisRequirements(unittest.TestCase):
    def test_measurement_axis_sums_all_four_terms(self):
        required = required_measurement_axis(small_layout(), "biconical", 3.0)
        expected = 0.8 + 3.0 + 0.55 + ANTENNA_TIP_CLEARANCE_M
        self.assertAlmostEqual(required, expected)

    def test_measurement_axis_grows_with_standoff(self):
        near = required_measurement_axis(small_layout(), "loop", 1.0)
        far = required_measurement_axis(small_layout(), "loop", 10.0)
        self.assertAlmostEqual(far - near, 9.0)

    def test_lateral_axis_without_support_rack(self):
        self.assertAlmostEqual(required_lateral_axis(small_layout()), 1.0)

    def test_lateral_axis_adds_support_rack_and_separation(self):
        required = required_lateral_axis(
            small_layout(support_rack_width_m=0.6, support_rack_separation_m=0.4)
        )
        self.assertAlmostEqual(required, 1.0 + 0.4 + 0.6)

    def test_vertical_axis_governed_by_bench_stack(self):
        required = required_vertical_axis(
            small_layout(unit_height_m=3.0, antenna_scan_top_m=0.0), "biconical"
        )
        self.assertAlmostEqual(required, 0.8 + 3.0 + 0.5)

    def test_vertical_axis_governed_by_antenna_scan_ceiling(self):
        required = required_vertical_axis(
            small_layout(unit_height_m=0.4, antenna_scan_top_m=4.0), "biconical"
        )
        self.assertAlmostEqual(required, 4.0 + 0.70 + 0.5)

    def test_measurement_axis_rejects_uncalibrated_standoff(self):
        with self.assertRaises(ValueError):
            required_measurement_axis(small_layout(), "biconical", 5.0)

    def test_measurement_axis_rejects_unknown_antenna(self):
        with self.assertRaises(ValueError):
            required_measurement_axis(small_layout(), "helical", 3.0)


class TestFitsAndAxisResult(unittest.TestCase):
    def test_clear_fit(self):
        self.assertTrue(fits(5.0, 4.0))

    def test_clear_shortfall(self):
        self.assertFalse(fits(4.0, 5.0))

    def test_exact_fit_with_float_error_absorbed(self):
        required = 0.1 + 0.2 + 0.3 + 0.4  # 0.9999999999999999 style artefact
        available = 1.0
        self.assertTrue(fits(available, required))

    def test_shortfall_beyond_tolerance_not_absorbed(self):
        self.assertFalse(fits(1.0, 1.0 + 1000.0 * DIM_TOL_M))

    def test_axis_result_reports_signed_margin(self):
        result = axis_result("lateral", 4.0, 6.5)
        self.assertAlmostEqual(result["margin_m"], 2.5)
        self.assertTrue(result["adequate"])

    def test_axis_result_negative_margin_is_inadequate(self):
        result = axis_result("vertical", 6.0, 4.0)
        self.assertAlmostEqual(result["margin_m"], -2.0)
        self.assertFalse(result["adequate"])

    def test_unrecognized_axis_rejected(self):
        with self.assertRaises(ValueError):
            axis_result("diagonal", 1.0, 2.0)


class TestAssessment(unittest.TestCase):
    def test_roomy_enclosure_is_adequate(self):
        report = assess_shielded_enclosure_sizing(
            big_enclosure(), small_layout(), "biconical", 3.0
        )
        self.assertEqual(report["verdict"], "adequate")
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["quiet_zone_adequate"])

    def test_short_enclosure_fails_measurement_axis(self):
        report = assess_shielded_enclosure_sizing(
            big_enclosure(internal_length_m=5.0), small_layout(), "biconical", 3.0
        )
        self.assertEqual(report["verdict"], "inadequate")
        self.assertEqual(report["governing_axis"], "measurement")
        self.assertLess(report["governing_margin_m"], 0.0)

    def test_low_enclosure_fails_vertical_axis(self):
        report = assess_shielded_enclosure_sizing(
            big_enclosure(internal_height_m=2.0),
            small_layout(antenna_scan_top_m=0.0),
            "biconical",
            1.0,
        )
        self.assertEqual(report["verdict"], "inadequate")
        self.assertEqual(report["governing_axis"], "vertical")

    def test_narrow_enclosure_fails_lateral_axis(self):
        report = assess_shielded_enclosure_sizing(
            big_enclosure(internal_width_m=1.5),
            small_layout(support_rack_width_m=1.0, support_rack_separation_m=0.5),
            "loop",
            1.0,
        )
        self.assertEqual(report["governing_axis"], "lateral")
        self.assertTrue(
            any("lateral axis short" in f for f in report["findings"])
        )

    def test_undeclared_quiet_zone_is_a_finding(self):
        report = assess_shielded_enclosure_sizing(
            big_enclosure(quiet_zone_diameter_m=0.0), small_layout(), "loop", 1.0
        )
        self.assertFalse(report["quiet_zone_declared"])
        self.assertEqual(report["verdict"], "inadequate")
        self.assertTrue(any("quiet-zone" in f for f in report["findings"]))

    def test_footprint_larger_than_quiet_zone_is_a_finding(self):
        report = assess_shielded_enclosure_sizing(
            big_enclosure(quiet_zone_diameter_m=0.5), small_layout(), "loop", 1.0
        )
        self.assertFalse(report["quiet_zone_adequate"])
        self.assertTrue(
            any("quiet-zone diameter" in f for f in report["findings"])
        )

    def test_exactly_fitting_layout_is_adequate(self):
        layout = small_layout(antenna_scan_top_m=0.0)
        required = required_measurement_axis(layout, "biconical", 3.0)
        enclosure = big_enclosure(
            internal_length_m=required + 2.0 * 0.6, quiet_zone_diameter_m=4.0
        )
        report = assess_shielded_enclosure_sizing(enclosure, layout, "biconical", 3.0)
        measurement = [a for a in report["axes"] if a["axis"] == "measurement"][0]
        self.assertTrue(measurement["adequate"])
        self.assertEqual(report["verdict"], "adequate")

    def test_report_exposes_usable_envelope(self):
        report = assess_shielded_enclosure_sizing(
            big_enclosure(), small_layout(), "loop", 1.0
        )
        self.assertAlmostEqual(report["usable_envelope_m"]["lateral"], 6.8)

    def test_all_three_axes_reported(self):
        report = assess_shielded_enclosure_sizing(
            big_enclosure(), small_layout(), "loop", 1.0
        )
        self.assertEqual(
            [a["axis"] for a in report["axes"]],
            ["measurement", "lateral", "vertical"],
        )

    def test_assessment_propagates_enclosure_error(self):
        with self.assertRaises(ValueError):
            assess_shielded_enclosure_sizing(
                big_enclosure(internal_length_m=-1.0), small_layout(), "loop", 1.0
            )

    def test_assessment_propagates_layout_error(self):
        with self.assertRaises(ValueError):
            assess_shielded_enclosure_sizing(
                big_enclosure(), small_layout(bench_height_m=0.0), "loop", 1.0
            )


if __name__ == "__main__":
    unittest.main()
