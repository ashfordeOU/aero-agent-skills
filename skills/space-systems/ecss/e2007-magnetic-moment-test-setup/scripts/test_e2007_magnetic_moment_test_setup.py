#!/usr/bin/env python3
"""Gate 3 contract test for e2007-magnetic-moment-test-setup.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_magnetic_moment_test_setup.py
"""

import unittest

from e2007_magnetic_moment_test_setup_logic import (
    DEFAULT_DIPOLE_DISTANCE_RATIO,
    DEFAULT_MIN_SNR,
    SETUP_DEFICIENT,
    SETUP_READY,
    STATE_COMPENSATED,
    STATE_PARTIAL,
    STATE_UNCOMPENSATED,
    assess_magnetic_moment_test_setup,
    axial_dipole_field_nt,
    compensation_grouping,
    fixture_findings,
    minimum_separation_m,
    residual_field_magnitude_nt,
    separation_findings,
    signal_to_noise_ratio,
    validate_setup,
)

UNIT_SIZE_M = 0.5
SENSOR_DISTANCE_M = 1.5
EXPECTED_MOMENT = 0.1


def good_setup(**over):
    record = {
        "residual_bx_nt": 3.0,
        "residual_by_nt": 4.0,
        "residual_bz_nt": 0.0,
        "compensation_tolerance_nt": 10.0,
        "largest_dimension_m": UNIT_SIZE_M,
        "measurement_distance_m": SENSOR_DISTANCE_M,
        "expected_moment_am2": EXPECTED_MOMENT,
        "sensor_noise_floor_nt": 0.05,
        "compensation_active": True,
        "non_magnetic_fixture": True,
        "ferromagnetic_items_present": False,
    }
    record.update(over)
    return record


class TestSetupValidation(unittest.TestCase):
    def test_good_setup_normalizes(self):
        setup = validate_setup(good_setup())
        self.assertAlmostEqual(setup["largest_dimension_m"], UNIT_SIZE_M, places=9)
        self.assertTrue(setup["compensation_active"])

    def test_integer_inputs_are_promoted_to_float(self):
        setup = validate_setup(good_setup(compensation_tolerance_nt=10))
        self.assertIsInstance(setup["compensation_tolerance_nt"], float)

    def test_negative_residual_component_is_accepted(self):
        setup = validate_setup(good_setup(residual_bz_nt=-2.0))
        self.assertAlmostEqual(setup["residual_bz_nt"], -2.0, places=9)

    def test_zero_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_setup(good_setup(compensation_tolerance_nt=0.0))

    def test_zero_separation_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_setup(good_setup(measurement_distance_m=0.0))

    def test_non_boolean_compensation_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_setup(good_setup(compensation_active="on"))

    def test_missing_field_is_rejected(self):
        record = good_setup()
        del record["sensor_noise_floor_nt"]
        with self.assertRaises(ValueError):
            validate_setup(record)

    def test_non_mapping_record_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_setup(["not", "a", "mapping"])


class TestResidualField(unittest.TestCase):
    def test_magnitude_is_the_vector_sum_of_the_components(self):
        self.assertAlmostEqual(residual_field_magnitude_nt(3.0, 4.0, 0.0), 5.0, places=9)

    def test_sign_does_not_change_the_magnitude(self):
        self.assertAlmostEqual(
            residual_field_magnitude_nt(-3.0, 0.0, -4.0), 5.0, places=9
        )

    def test_residual_at_the_tolerance_counts_as_compensated(self):
        self.assertEqual(compensation_grouping(5.0, 5.0), STATE_COMPENSATED)

    def test_residual_a_few_times_the_tolerance_is_partial(self):
        self.assertEqual(compensation_grouping(20.0, 5.0), STATE_PARTIAL)

    def test_residual_far_past_the_tolerance_is_uncompensated(self):
        self.assertEqual(compensation_grouping(40.0, 5.0), STATE_UNCOMPENSATED)

    def test_grouping_rejects_a_zero_tolerance(self):
        with self.assertRaises(ValueError):
            compensation_grouping(5.0, 0.0)

    def test_grouping_rejects_a_negative_residual(self):
        with self.assertRaises(ValueError):
            compensation_grouping(-1.0, 5.0)


class TestSeparation(unittest.TestCase):
    def test_minimum_separation_is_the_dimension_times_the_ratio(self):
        self.assertAlmostEqual(minimum_separation_m(0.5, 3.0), 1.5, places=9)

    def test_default_ratio_is_applied_when_none_is_given(self):
        self.assertAlmostEqual(
            minimum_separation_m(UNIT_SIZE_M),
            UNIT_SIZE_M * DEFAULT_DIPOLE_DISTANCE_RATIO,
            places=9,
        )

    def test_separation_exactly_at_the_minimum_raises_no_finding(self):
        setup = validate_setup(good_setup())
        self.assertEqual(separation_findings(setup), [])

    def test_separation_inside_the_minimum_is_reported(self):
        setup = validate_setup(good_setup(measurement_distance_m=0.8))
        findings = separation_findings(setup)
        self.assertEqual(len(findings), 1)
        self.assertIn("closest", findings[0])

    def test_a_ratio_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            minimum_separation_m(0.5, 0.5)

    def test_a_zero_dimension_is_rejected(self):
        with self.assertRaises(ValueError):
            minimum_separation_m(0.0)


class TestDipoleFieldAndNoise(unittest.TestCase):
    def test_unit_moment_at_one_metre_gives_the_axial_coefficient(self):
        self.assertAlmostEqual(axial_dipole_field_nt(1.0, 1.0), 200.0, places=9)

    def test_field_falls_with_the_cube_of_the_distance(self):
        self.assertAlmostEqual(axial_dipole_field_nt(2.0, 2.0), 50.0, places=9)

    def test_zero_distance_is_rejected(self):
        with self.assertRaises(ValueError):
            axial_dipole_field_nt(1.0, 0.0)

    def test_zero_moment_is_rejected(self):
        with self.assertRaises(ValueError):
            axial_dipole_field_nt(0.0, 1.0)

    def test_ratio_is_the_field_over_the_noise_floor(self):
        self.assertAlmostEqual(signal_to_noise_ratio(100.0, 10.0), 10.0, places=9)

    def test_a_zero_noise_floor_is_rejected(self):
        with self.assertRaises(ValueError):
            signal_to_noise_ratio(100.0, 0.0)


class TestFixture(unittest.TestCase):
    def test_a_clean_area_raises_no_fixture_finding(self):
        self.assertEqual(fixture_findings(validate_setup(good_setup())), [])

    def test_ferromagnetic_hardware_is_reported(self):
        setup = validate_setup(good_setup(ferromagnetic_items_present=True))
        findings = fixture_findings(setup)
        self.assertEqual(len(findings), 1)
        self.assertIn("ferromagnetic", findings[0])

    def test_fixture_findings_reject_an_incomplete_record(self):
        with self.assertRaises(ValueError):
            fixture_findings({"non_magnetic_fixture": True})


class TestFullAssessment(unittest.TestCase):
    def test_a_compensated_area_is_ready(self):
        report = assess_magnetic_moment_test_setup(good_setup())
        self.assertEqual(report["compensation_grouping"], STATE_COMPENSATED)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], SETUP_READY)

    def test_compensation_switched_off_is_a_finding(self):
        report = assess_magnetic_moment_test_setup(
            good_setup(compensation_active=False)
        )
        self.assertTrue(any("not running" in f for f in report["findings"]))
        self.assertEqual(report["verdict"], SETUP_DEFICIENT)

    def test_a_residual_over_the_tolerance_is_a_finding(self):
        report = assess_magnetic_moment_test_setup(
            good_setup(residual_bx_nt=60.0, residual_by_nt=0.0, residual_bz_nt=0.0)
        )
        self.assertEqual(report["compensation_grouping"], STATE_UNCOMPENSATED)
        self.assertEqual(report["verdict"], SETUP_DEFICIENT)

    def test_sensors_too_close_are_a_finding(self):
        report = assess_magnetic_moment_test_setup(
            good_setup(measurement_distance_m=0.8)
        )
        self.assertTrue(any("one dipole" in f for f in report["findings"]))

    def test_a_field_lost_in_the_noise_is_a_finding(self):
        report = assess_magnetic_moment_test_setup(
            good_setup(sensor_noise_floor_nt=2.0)
        )
        self.assertLess(report["signal_to_noise_ratio"], DEFAULT_MIN_SNR)
        self.assertEqual(report["verdict"], SETUP_DEFICIENT)

    def test_a_magnetic_fixture_is_a_limitation_not_a_finding(self):
        report = assess_magnetic_moment_test_setup(
            good_setup(non_magnetic_fixture=False)
        )
        self.assertEqual(report["findings"], [])
        self.assertTrue(any("fixture" in m for m in report["limitations"]))
        self.assertEqual(report["verdict"], SETUP_READY)

    def test_a_thin_noise_margin_is_a_limitation(self):
        report = assess_magnetic_moment_test_setup(
            good_setup(sensor_noise_floor_nt=0.4)
        )
        self.assertEqual(report["findings"], [])
        self.assertTrue(any("thin" in m for m in report["limitations"]))

    def test_report_carries_the_derived_separation_and_field(self):
        report = assess_magnetic_moment_test_setup(good_setup())
        self.assertAlmostEqual(report["minimum_separation_m"], 1.5, places=9)
        self.assertAlmostEqual(
            report["expected_field_nt"],
            axial_dipole_field_nt(EXPECTED_MOMENT, SENSOR_DISTANCE_M),
            places=9,
        )

    def test_assessment_propagates_a_setup_error(self):
        with self.assertRaises(ValueError):
            assess_magnetic_moment_test_setup(good_setup(expected_moment_am2=0.0))

    def test_a_non_positive_minimum_ratio_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_magnetic_moment_test_setup(good_setup(), min_snr=0.0)


if __name__ == "__main__":
    unittest.main()
