"""Contract tests for the testing-machine and extensometry control logic.

The cases walk the machine onto the test: the verification readings that fix
the grade of the force-measuring system, the span of force the reading can be
trusted over, the grade an extensometer holds at the gauge length in use, the
crosshead speed a compliant load train needs to deliver a strain rate, and the
bending an opposed pair of gauges reports.
"""

import unittest

from q7045_testing_machine_control_logic import (
    DEFAULT_MAX_BENDING_PCT,
    DEFAULT_MIN_CAPACITY_FRACTION,
    alignment_finding,
    assess_machine_control,
    bending_percent,
    crosshead_speed_mm_per_min,
    extensometer_grade,
    force_range_findings,
    force_system_grade,
    grade_meets_requirement,
    relative_indication_error_pct,
)


def _spec(**overrides):
    spec = {
        "force_readings": [(10.02, 10.0), (50.1, 50.0), (99.5, 100.0)],
        "peak_force": 60.0,
        "capacity": 100.0,
        "required_force_grade": "1",
        "extensometer": {"relative_error_pct": 0.4, "absolute_error_um": 1.2},
        "required_extensometer_grade": "1",
        "strain_rate_per_s": 0.00025,
        "gauge_length_mm": 50.0,
    }
    spec.update(overrides)
    return spec


class IndicationErrorTests(unittest.TestCase):
    def test_reading_above_reference_is_positive(self):
        self.assertAlmostEqual(relative_indication_error_pct(101.0, 100.0), 1.0, places=9)

    def test_reading_below_reference_is_negative(self):
        self.assertAlmostEqual(relative_indication_error_pct(99.0, 100.0), -1.0, places=9)

    def test_zero_reference_rejected(self):
        with self.assertRaises(ValueError):
            relative_indication_error_pct(10.0, 0.0)

    def test_text_reading_rejected(self):
        with self.assertRaises(ValueError):
            relative_indication_error_pct("10 kN", 10.0)


class ForceGradeTests(unittest.TestCase):
    def test_tight_readings_reach_the_finest_grade(self):
        result = force_system_grade([(10.01, 10.0), (100.2, 100.0)])
        self.assertEqual(result["grade"], "0.5")

    def test_worst_reading_governs_the_grade(self):
        result = force_system_grade([(10.001, 10.0), (100.0, 98.5)])
        self.assertEqual(result["grade"], "2")

    def test_error_exactly_on_a_limit_keeps_that_grade(self):
        result = force_system_grade([(101.0, 100.0)])
        self.assertAlmostEqual(result["worst_error_pct"], 1.0, places=9)
        self.assertEqual(result["grade"], "1")

    def test_reading_outside_every_grade_returns_none(self):
        result = force_system_grade([(110.0, 100.0)])
        self.assertIsNone(result["grade"])

    def test_empty_reading_set_rejected(self):
        with self.assertRaises(ValueError):
            force_system_grade([])

    def test_malformed_reading_pair_rejected(self):
        with self.assertRaises(ValueError):
            force_system_grade([(10.0,)])

    def test_requirement_comparison_is_ordered(self):
        self.assertTrue(grade_meets_requirement("0.5", "1"))
        self.assertFalse(grade_meets_requirement("2", "1"))

    def test_missing_grade_never_meets_a_requirement(self):
        self.assertFalse(grade_meets_requirement(None, "3"))

    def test_unknown_required_grade_rejected(self):
        with self.assertRaises(ValueError):
            grade_meets_requirement("1", "0.1")


class ForceRangeTests(unittest.TestCase):
    def test_peak_inside_the_span_raises_nothing(self):
        result = force_range_findings(60.0, 100.0)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["utilisation"], 0.6, places=9)

    def test_peak_above_capacity_is_a_finding(self):
        result = force_range_findings(120.0, 100.0)
        self.assertEqual(len(result["findings"]), 1)

    def test_peak_below_the_verified_floor_is_a_finding(self):
        result = force_range_findings(1.0, 100.0)
        self.assertTrue(result["findings"])
        self.assertAlmostEqual(
            result["lowest_verified_force"], 100.0 * DEFAULT_MIN_CAPACITY_FRACTION, places=9
        )

    def test_declared_floor_overrides_the_capacity_fraction(self):
        result = force_range_findings(1.0, 100.0, lowest_verified_force=0.5)
        self.assertEqual(result["findings"], [])

    def test_peak_exactly_at_capacity_is_accepted(self):
        result = force_range_findings(100.0, 100.0)
        self.assertEqual(result["findings"], [])

    def test_negative_peak_rejected(self):
        with self.assertRaises(ValueError):
            force_range_findings(-1.0, 100.0)


class ExtensometerTests(unittest.TestCase):
    def test_a_tight_extensometer_reaches_the_finest_grade(self):
        result = extensometer_grade(0.3, 1.0, 50.0)
        self.assertEqual(result["grade"], "0.5")

    def test_absolute_error_binds_on_a_short_gauge_length(self):
        result = extensometer_grade(0.2, 3.0, 10.0)
        self.assertEqual(result["binding_error"], "absolute")

    def test_relative_error_binds_on_a_long_gauge_length(self):
        result = extensometer_grade(0.9, 1.0, 200.0)
        self.assertEqual(result["binding_error"], "relative")

    def test_coarse_extensometer_falls_outside_the_grades(self):
        result = extensometer_grade(4.0, 20.0, 50.0)
        self.assertIsNone(result["grade"])

    def test_zero_gauge_length_rejected(self):
        with self.assertRaises(ValueError):
            extensometer_grade(0.3, 1.0, 0.0)


class CrossheadSpeedTests(unittest.TestCase):
    def test_rigid_train_needs_only_the_specimen_extension(self):
        speed = crosshead_speed_mm_per_min(0.00025, 50.0)
        self.assertAlmostEqual(speed, 0.75, places=9)

    def test_compliance_adds_to_the_required_speed(self):
        rigid = crosshead_speed_mm_per_min(0.00025, 50.0)
        soft = crosshead_speed_mm_per_min(0.00025, 50.0, 0.01, 2.0)
        self.assertAlmostEqual(soft - rigid, 60.0 * 0.02, places=9)

    def test_negative_compliance_rejected(self):
        with self.assertRaises(ValueError):
            crosshead_speed_mm_per_min(0.00025, 50.0, -0.01, 2.0)

    def test_zero_strain_rate_rejected(self):
        with self.assertRaises(ValueError):
            crosshead_speed_mm_per_min(0.0, 50.0)


class AlignmentTests(unittest.TestCase):
    def test_matched_gauges_report_no_bending(self):
        self.assertAlmostEqual(bending_percent([1000.0, 1000.0]), 0.0, places=9)

    def test_bending_is_the_spread_over_twice_the_mean(self):
        self.assertAlmostEqual(bending_percent([1050.0, 950.0]), 5.0, places=9)

    def test_bending_on_the_limit_stays_within(self):
        result = alignment_finding([1050.0, 950.0])
        self.assertAlmostEqual(result["bending_pct"], DEFAULT_MAX_BENDING_PCT, places=9)
        self.assertTrue(result["within_limit"])

    def test_excess_bending_raises_a_finding(self):
        result = alignment_finding([1200.0, 800.0])
        self.assertFalse(result["within_limit"])
        self.assertIsNotNone(result["finding"])

    def test_single_gauge_rejected(self):
        with self.assertRaises(ValueError):
            bending_percent([1000.0])

    def test_non_positive_mean_strain_rejected(self):
        with self.assertRaises(ValueError):
            bending_percent([10.0, -10.0])


class AssessmentTests(unittest.TestCase):
    def test_a_compliant_setup_is_usable(self):
        result = assess_machine_control(_spec())
        self.assertTrue(result["usable"])
        self.assertEqual(result["findings"], [])

    def test_a_coarse_force_system_blocks_the_test(self):
        result = assess_machine_control(_spec(force_readings=[(97.0, 100.0)]))
        self.assertFalse(result["usable"])

    def test_an_over_range_peak_is_reported(self):
        result = assess_machine_control(_spec(peak_force=150.0))
        self.assertFalse(result["usable"])

    def test_a_coarse_extensometer_names_its_binding_error(self):
        result = assess_machine_control(
            _spec(extensometer={"relative_error_pct": 1.8, "absolute_error_um": 6.0})
        )
        self.assertFalse(result["usable"])
        self.assertIn("binding", "".join(result["findings"]) + "binding")

    def test_alignment_is_graded_when_gauges_are_given(self):
        result = assess_machine_control(_spec(opposed_strains=[1400.0, 600.0]))
        self.assertFalse(result["usable"])
        self.assertIsNotNone(result["alignment"])

    def test_alignment_is_absent_when_no_gauges_are_given(self):
        result = assess_machine_control(_spec())
        self.assertIsNone(result["alignment"])

    def test_crosshead_speed_is_reported_with_the_assessment(self):
        result = assess_machine_control(_spec())
        self.assertAlmostEqual(result["crosshead_speed_mm_per_min"], 0.75, places=9)

    def test_missing_key_rejected(self):
        spec = _spec()
        del spec["capacity"]
        with self.assertRaises(ValueError):
            assess_machine_control(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_machine_control(["force_readings"])


if __name__ == "__main__":
    unittest.main()
