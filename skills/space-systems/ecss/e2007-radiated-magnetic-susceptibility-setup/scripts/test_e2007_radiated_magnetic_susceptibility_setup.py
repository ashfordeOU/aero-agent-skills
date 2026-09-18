#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radiated-magnetic-susceptibility-setup.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radiated_magnetic_susceptibility_setup.py
"""

import math
import unittest

from e2007_radiated_magnetic_susceptibility_setup_logic import (
    DEFAULT_LOOP_DIAMETER_M,
    DEFAULT_MONITOR_FLOOR_V,
    DEFAULT_STANDOFF_WINDOW_M,
    GRADE_CONFORMING,
    GRADE_DEVIATION,
    GRADE_MARGINAL,
    RECOGNIZED_SURFACES,
    REQUIRED_ORIENTATIONS,
    VERDICT_CONFORMS,
    VERDICT_DEVIATES,
    assess_setup,
    flux_density_for_sense_voltage,
    grade_dimension,
    grid_spacing_ceiling_m,
    normalize_orientation,
    normalize_surface,
    scan_point_count,
    sense_loop_voltage_v,
    validate_position,
    validate_window,
)


def position(**over):
    record = {
        "surface": "forward-face",
        "width_m": 0.30,
        "height_m": 0.24,
        "standoff_m": 0.05,
        "grid_spacing_m": 0.10,
        "orientations": list(REQUIRED_ORIENTATIONS),
    }
    record.update(over)
    return record


def verification(**over):
    record = {
        "turns": 10.0,
        "area_m2": 0.01,
        "flux_density_t": 1.0e-6,
        "frequency_hz": 1.0e3,
    }
    record.update(over)
    return record


def bench(**over):
    records = {
        "forward": position(),
        "aft": position(surface="aft-face"),
    }
    records.update(over)
    return [records["forward"], records["aft"]]


class TestSurfaceNormalization(unittest.TestCase):
    def test_every_recognized_surface_normalizes(self):
        for surface in RECOGNIZED_SURFACES:
            self.assertEqual(normalize_surface(surface.upper()), surface)

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(normalize_surface("  harness-run "), "harness-run")

    def test_unrecognized_surface_rejected(self):
        with self.assertRaises(ValueError):
            normalize_surface("solar-wing-root")

    def test_non_string_surface_rejected(self):
        with self.assertRaises(ValueError):
            normalize_surface(4)

    def test_every_required_orientation_normalizes(self):
        for orientation in REQUIRED_ORIENTATIONS:
            self.assertEqual(normalize_orientation(orientation.upper()), orientation)

    def test_unrecognized_orientation_rejected(self):
        with self.assertRaises(ValueError):
            normalize_orientation("diagonal")


class TestWindowGrading(unittest.TestCase):
    def test_default_window_validates(self):
        low, high = validate_window(DEFAULT_STANDOFF_WINDOW_M)
        self.assertAlmostEqual(low, 0.04)
        self.assertAlmostEqual(high, 0.06)

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_window((0.06, 0.04))

    def test_negative_window_minimum_rejected(self):
        with self.assertRaises(ValueError):
            validate_window((-0.01, 0.06))

    def test_non_pair_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_window([0.04, 0.05, 0.06])

    def test_centre_of_the_window_conforms(self):
        report = grade_dimension(0.05, DEFAULT_STANDOFF_WINDOW_M)
        self.assertEqual(report["grade"], GRADE_CONFORMING)

    def test_value_just_inside_an_edge_is_marginal(self):
        report = grade_dimension(0.0405, DEFAULT_STANDOFF_WINDOW_M)
        self.assertEqual(report["grade"], GRADE_MARGINAL)

    def test_value_outside_the_window_is_a_deviation(self):
        report = grade_dimension(0.075, DEFAULT_STANDOFF_WINDOW_M)
        self.assertEqual(report["grade"], GRADE_DEVIATION)

    def test_value_exactly_on_an_edge_is_inside_the_window(self):
        report = grade_dimension(0.04, DEFAULT_STANDOFF_WINDOW_M)
        self.assertNotEqual(report["grade"], GRADE_DEVIATION)

    def test_value_exactly_on_the_margin_band_conforms(self):
        low, high = DEFAULT_STANDOFF_WINDOW_M
        band = (high - low) * 0.10
        report = grade_dimension(low + band, DEFAULT_STANDOFF_WINDOW_M)
        self.assertEqual(report["grade"], GRADE_CONFORMING)

    def test_edge_distance_is_reported(self):
        report = grade_dimension(0.045, DEFAULT_STANDOFF_WINDOW_M)
        self.assertAlmostEqual(report["edge_distance"], 0.005, places=9)

    def test_margin_fraction_at_or_above_a_half_rejected(self):
        with self.assertRaises(ValueError):
            grade_dimension(0.05, DEFAULT_STANDOFF_WINDOW_M, margin_fraction=0.5)

    def test_negative_margin_fraction_rejected(self):
        with self.assertRaises(ValueError):
            grade_dimension(0.05, DEFAULT_STANDOFF_WINDOW_M, margin_fraction=-0.1)


class TestScanGrid(unittest.TestCase):
    def test_spacing_ceiling_is_the_loop_diameter(self):
        self.assertAlmostEqual(
            grid_spacing_ceiling_m(), DEFAULT_LOOP_DIAMETER_M, places=12
        )

    def test_spacing_ceiling_rejects_a_zero_diameter(self):
        with self.assertRaises(ValueError):
            grid_spacing_ceiling_m(0.0)

    def test_an_exact_fit_is_not_rounded_up(self):
        grid = scan_point_count(0.30, 0.20, 0.10)
        self.assertEqual(grid["across"], 3)
        self.assertEqual(grid["down"], 2)
        self.assertEqual(grid["positions"], 6)

    def test_a_partial_step_adds_a_whole_position(self):
        grid = scan_point_count(0.31, 0.20, 0.10)
        self.assertEqual(grid["across"], 4)

    def test_a_surface_smaller_than_one_step_still_gets_one_position(self):
        grid = scan_point_count(0.02, 0.02, 0.10)
        self.assertEqual(grid["positions"], 1)

    def test_halving_the_spacing_quadruples_the_positions(self):
        coarse = scan_point_count(0.40, 0.40, 0.10)
        fine = scan_point_count(0.40, 0.40, 0.05)
        self.assertEqual(fine["positions"], coarse["positions"] * 4)

    def test_zero_spacing_rejected(self):
        with self.assertRaises(ValueError):
            scan_point_count(0.30, 0.20, 0.0)

    def test_negative_width_rejected(self):
        with self.assertRaises(ValueError):
            scan_point_count(-0.30, 0.20, 0.10)


class TestSenseLoop(unittest.TestCase):
    def test_read_back_matches_the_closed_form(self):
        expected = 2.0 * math.pi * 1.0e3 * 10.0 * 0.01 * 1.0e-6
        self.assertAlmostEqual(
            sense_loop_voltage_v(10.0, 0.01, 1.0e-6, 1.0e3), expected, places=15
        )

    def test_read_back_is_linear_in_frequency(self):
        low = sense_loop_voltage_v(10.0, 0.01, 1.0e-6, 1.0e3)
        high = sense_loop_voltage_v(10.0, 0.01, 1.0e-6, 2.0e3)
        self.assertAlmostEqual(high / low, 2.0, places=9)

    def test_read_back_is_linear_in_the_turns_area_product(self):
        one = sense_loop_voltage_v(10.0, 0.01, 1.0e-6, 1.0e3)
        two = sense_loop_voltage_v(20.0, 0.01, 1.0e-6, 1.0e3)
        self.assertAlmostEqual(two / one, 2.0, places=9)

    def test_flux_density_inverts_the_read_back_exactly(self):
        voltage = sense_loop_voltage_v(10.0, 0.01, 3.0e-6, 400.0)
        self.assertAlmostEqual(
            flux_density_for_sense_voltage(voltage, 10.0, 0.01, 400.0),
            3.0e-6,
            places=15,
        )

    def test_sub_unit_turn_count_rejected(self):
        with self.assertRaises(ValueError):
            sense_loop_voltage_v(0.0, 0.01, 1.0e-6, 1.0e3)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            sense_loop_voltage_v(10.0, 0.0, 1.0e-6, 1.0e3)

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            sense_loop_voltage_v(10.0, 0.01, 1.0e-6, 0.0)

    def test_zero_read_back_rejected_on_the_inverse(self):
        with self.assertRaises(ValueError):
            flux_density_for_sense_voltage(0.0, 10.0, 0.01, 1.0e3)


class TestPositionValidation(unittest.TestCase):
    def test_a_complete_position_normalizes(self):
        item = validate_position(position())
        self.assertEqual(item["surface"], "forward-face")
        self.assertEqual(item["missing_orientations"], [])

    def test_a_missing_orientation_is_listed(self):
        item = validate_position(position(orientations=["x-normal", "y-normal"]))
        self.assertEqual(item["missing_orientations"], ["z-normal"])

    def test_a_repeated_orientation_rejected(self):
        with self.assertRaises(ValueError):
            validate_position(position(orientations=["x-normal", "x-normal"]))

    def test_an_empty_orientation_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_position(position(orientations=[]))

    def test_negative_standoff_rejected(self):
        with self.assertRaises(ValueError):
            validate_position(position(standoff_m=-0.01))

    def test_zero_grid_spacing_rejected(self):
        with self.assertRaises(ValueError):
            validate_position(position(grid_spacing_m=0.0))

    def test_boolean_dimension_rejected_as_numeric(self):
        with self.assertRaises(ValueError):
            validate_position(position(width_m=True))

    def test_non_mapping_position_rejected(self):
        with self.assertRaises(ValueError):
            validate_position("the forward face")

    def test_standoff_grade_travels_with_the_position(self):
        item = validate_position(position(standoff_m=0.09))
        self.assertEqual(item["standoff_grade"]["grade"], GRADE_DEVIATION)


class TestAssessment(unittest.TestCase):
    def test_a_conforming_bench_has_no_findings(self):
        report = assess_setup(bench(), verification=verification())
        self.assertEqual(report["verdict"], VERDICT_CONFORMS)
        self.assertEqual(report["findings"], [])

    def test_a_standoff_outside_the_window_is_a_finding(self):
        report = assess_setup(
            bench(forward=position(standoff_m=0.12)), verification=verification()
        )
        self.assertEqual(report["verdict"], VERDICT_DEVIATES)
        self.assertTrue(any("outside the" in f for f in report["findings"]))

    def test_a_standoff_near_the_edge_is_a_limitation(self):
        report = assess_setup(
            bench(forward=position(standoff_m=0.0405)), verification=verification()
        )
        self.assertEqual(report["verdict"], VERDICT_CONFORMS)
        self.assertTrue(any("window edge" in n for n in report["limitations"]))

    def test_spacing_wider_than_the_loop_is_a_finding(self):
        report = assess_setup(
            bench(forward=position(grid_spacing_m=0.30)), verification=verification()
        )
        self.assertTrue(any("overlap ceiling" in f for f in report["findings"]))

    def test_spacing_exactly_at_the_loop_diameter_is_accepted(self):
        report = assess_setup(
            bench(forward=position(grid_spacing_m=DEFAULT_LOOP_DIAMETER_M)),
            verification=verification(),
        )
        self.assertFalse(any("overlap ceiling" in f for f in report["findings"]))

    def test_a_missing_loop_presentation_is_a_finding(self):
        report = assess_setup(
            bench(forward=position(orientations=["x-normal"])),
            verification=verification(),
        )
        self.assertTrue(any("never made" in f for f in report["findings"]))

    def test_a_repeated_surface_rejected(self):
        with self.assertRaises(ValueError):
            assess_setup([position(), position()], verification=verification())

    def test_an_absent_verification_arrangement_is_a_finding(self):
        report = assess_setup(bench())
        self.assertEqual(report["verdict"], VERDICT_DEVIATES)
        self.assertTrue(any("system verification" in f for f in report["findings"]))
        self.assertIsNone(report["verification"])

    def test_a_read_back_under_the_monitor_floor_is_a_finding(self):
        report = assess_setup(
            bench(), verification=verification(flux_density_t=1.0e-12)
        )
        self.assertTrue(any("monitor floor" in f for f in report["findings"]))

    def test_a_read_back_close_to_the_floor_is_a_limitation(self):
        report = assess_setup(
            bench(),
            verification=verification(turns=1.0, area_m2=1.0e-4, frequency_hz=200.0),
            monitor_floor_v=1.0e-7,
        )
        self.assertTrue(any("decade of the monitor floor" in n
                            for n in report["limitations"]))

    def test_total_exposures_multiply_grid_by_orientations(self):
        report = assess_setup(
            [position(width_m=0.30, height_m=0.20, grid_spacing_m=0.10)],
            verification=verification(),
        )
        self.assertEqual(report["total_exposures"], 6 * len(REQUIRED_ORIENTATIONS))

    def test_the_surfaces_covered_are_reported_in_order(self):
        report = assess_setup(bench(), verification=verification())
        self.assertEqual(report["surfaces"], ["forward-face", "aft-face"])

    def test_the_spacing_ceiling_is_reported(self):
        report = assess_setup(bench(), verification=verification())
        self.assertAlmostEqual(
            report["grid_spacing_ceiling_m"], DEFAULT_LOOP_DIAMETER_M, places=12
        )

    def test_an_empty_bench_rejected(self):
        with self.assertRaises(ValueError):
            assess_setup([])

    def test_a_non_mapping_verification_rejected(self):
        with self.assertRaises(ValueError):
            assess_setup(bench(), verification="a sense loop")

    def test_a_zero_monitor_floor_rejected(self):
        with self.assertRaises(ValueError):
            assess_setup(bench(), verification=verification(), monitor_floor_v=0.0)

    def test_the_default_monitor_floor_is_used_when_none_is_given(self):
        report = assess_setup(bench(), verification=verification())
        self.assertAlmostEqual(
            report["verification"]["monitor_floor_v"], DEFAULT_MONITOR_FLOOR_V,
            places=15,
        )


if __name__ == "__main__":
    unittest.main()
