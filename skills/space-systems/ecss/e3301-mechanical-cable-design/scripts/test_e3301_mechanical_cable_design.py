"""Contract tests for the clause 4.7.3.4.3 cable-drive design logic."""

import math
import unittest

from e3301_mechanical_cable_design_logic import (
    DEFAULT_TENSION_EXPONENT,
    allowable_flexure_cycles,
    assess_cable_drive,
    bend_ratio,
    bending_stress_pa,
    flexure_cycles,
    interpolate_log_log,
    margin_of_safety,
    run_tensions_n,
    termination_strength_n,
)

LIFE_CURVE = [
    (20.0, 1.0e4),
    (40.0, 1.0e5),
    (60.0, 4.0e5),
    (100.0, 2.0e6),
]


def base_spec(**overrides):
    """Return a representative pointing-mechanism cable drive."""
    spec = {
        "preload_n": 120.0,
        "drive_force_n": 160.0,
        "cable_diameter_mm": 0.8,
        "strand_diameter_mm": 0.06,
        "pulley_diameter_mm": 40.0,
        "min_bend_ratio": 40.0,
        "youngs_modulus_pa": 1.9e11,
        "mission_cycles": 20000,
        "pulleys": 4,
        "passes_per_pulley_per_cycle": 2,
        "breaking_load_n": 2500.0,
        "termination_efficiency": 0.85,
        "safety_factor": 2.0,
        "life_factor": 2.0,
        "flexure_life_curve": LIFE_CURVE,
    }
    spec.update(overrides)
    return spec


class RunTensionTests(unittest.TestCase):
    def test_drive_force_splits_between_the_runs(self):
        tensions = run_tensions_n(120.0, 160.0)
        self.assertAlmostEqual(tensions["tight_run_n"], 200.0, places=9)
        self.assertAlmostEqual(tensions["slack_run_n"], 40.0, places=9)

    def test_no_drive_force_leaves_both_runs_at_the_preload(self):
        tensions = run_tensions_n(120.0, 0.0)
        self.assertAlmostEqual(tensions["tight_run_n"], 120.0, places=9)
        self.assertAlmostEqual(tensions["slack_run_n"], 120.0, places=9)

    def test_slack_run_is_reported_negative_not_clamped(self):
        tensions = run_tensions_n(120.0, 300.0)
        self.assertAlmostEqual(tensions["slack_run_n"], -30.0, places=9)

    def test_zero_preload_rejected(self):
        with self.assertRaises(ValueError):
            run_tensions_n(0.0, 160.0)

    def test_negative_drive_force_rejected(self):
        with self.assertRaises(ValueError):
            run_tensions_n(120.0, -10.0)


class GeometryTests(unittest.TestCase):
    def test_bend_ratio_is_the_diameter_quotient(self):
        self.assertAlmostEqual(bend_ratio(40.0, 0.8), 50.0, places=9)

    def test_cable_fatter_than_the_pulley_rejected(self):
        with self.assertRaises(ValueError):
            bend_ratio(0.8, 40.0)

    def test_bending_stress_uses_the_strand_not_the_cable(self):
        self.assertAlmostEqual(
            bending_stress_pa(1.9e11, 0.06, 40.0), 1.9e11 * 0.06 / 40.0, places=3
        )

    def test_larger_pulley_lowers_the_bending_stress(self):
        small = bending_stress_pa(1.9e11, 0.06, 20.0)
        large = bending_stress_pa(1.9e11, 0.06, 40.0)
        self.assertAlmostEqual(small, large * 2.0, places=3)

    def test_zero_strand_diameter_rejected(self):
        with self.assertRaises(ValueError):
            bending_stress_pa(1.9e11, 0.0, 40.0)


class FlexureCountTests(unittest.TestCase):
    def test_every_pulley_contributes_its_passes(self):
        self.assertAlmostEqual(flexure_cycles(20000, 4, 2), 160000.0, places=6)

    def test_single_pulley_single_pass(self):
        self.assertAlmostEqual(flexure_cycles(100, 1, 1), 100.0, places=9)

    def test_zero_pulleys_rejected(self):
        with self.assertRaises(ValueError):
            flexure_cycles(20000, 0, 2)

    def test_non_integer_mission_cycles_rejected(self):
        with self.assertRaises(ValueError):
            flexure_cycles(20000.5, 4, 2)


class LifeCurveTests(unittest.TestCase):
    def test_tabulated_point_returns_its_own_value(self):
        self.assertAlmostEqual(interpolate_log_log(LIFE_CURVE, 40.0), 1.0e5, places=3)

    def test_interpolation_is_geometric_between_points(self):
        value = interpolate_log_log(LIFE_CURVE, math.sqrt(40.0 * 60.0))
        self.assertAlmostEqual(value, math.sqrt(1.0e5 * 4.0e5), places=3)

    def test_extrapolation_refused(self):
        with self.assertRaises(ValueError):
            interpolate_log_log(LIFE_CURVE, 150.0)

    def test_unsorted_curve_rejected(self):
        with self.assertRaises(ValueError):
            interpolate_log_log([(40.0, 1.0e5), (20.0, 1.0e4)], 30.0)

    def test_tension_derating_follows_the_exponent(self):
        at_reference = allowable_flexure_cycles(LIFE_CURVE, 40.0, 0.10, 0.10, 3.0)
        at_double = allowable_flexure_cycles(LIFE_CURVE, 40.0, 0.20, 0.10, 3.0)
        self.assertAlmostEqual(at_reference, 1.0e5, places=3)
        self.assertAlmostEqual(at_double * 8.0, at_reference, places=3)

    def test_default_exponent_is_cubic(self):
        self.assertAlmostEqual(DEFAULT_TENSION_EXPONENT, 3.0, places=12)

    def test_tension_at_the_breaking_load_rejected(self):
        with self.assertRaises(ValueError):
            allowable_flexure_cycles(LIFE_CURVE, 40.0, 1.0)


class TerminationTests(unittest.TestCase):
    def test_efficiency_derates_the_breaking_load(self):
        self.assertAlmostEqual(termination_strength_n(2500.0, 0.85), 2125.0, places=9)

    def test_efficiency_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            termination_strength_n(2500.0, 1.2)

    def test_margin_of_safety_definition(self):
        self.assertAlmostEqual(margin_of_safety(2500.0, 200.0, 2.0), 5.25, places=12)

    def test_zero_margin_at_the_exact_allowable(self):
        self.assertAlmostEqual(margin_of_safety(400.0, 200.0, 2.0), 0.0, places=12)

    def test_safety_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            margin_of_safety(2500.0, 200.0, 0.8)


class AssessCableDriveTests(unittest.TestCase):
    def test_representative_drive_is_compliant(self):
        result = assess_cable_drive(base_spec())
        self.assertTrue(result["compliant"], result["findings"])
        self.assertAlmostEqual(result["bend_ratio"], 50.0, places=9)
        self.assertAlmostEqual(result["tension_ratio"], 0.08, places=12)

    def test_slack_run_is_reported_as_a_finding(self):
        result = assess_cable_drive(base_spec(drive_force_n=260.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("goes slack" in f for f in result["findings"]))

    def test_small_pulley_trips_the_bend_ratio_floor(self):
        result = assess_cable_drive(base_spec(pulley_diameter_mm=24.0))
        self.assertTrue(any("diameter ratio" in f for f in result["findings"]))

    def test_long_mission_exhausts_the_flexure_life(self):
        result = assess_cable_drive(base_spec(mission_cycles=500000))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("flexure life" in f for f in result["findings"]))

    def test_life_factor_scales_the_demanded_bends(self):
        single = assess_cable_drive(base_spec(life_factor=1.0))
        doubled = assess_cable_drive(base_spec(life_factor=2.0))
        self.assertAlmostEqual(
            doubled["demanded_flexure_bends"], single["demanded_flexure_bends"] * 2.0,
            places=6,
        )

    def test_weak_termination_governs_and_is_reported(self):
        result = assess_cable_drive(base_spec(termination_efficiency=0.05))
        self.assertEqual(result["governing_strength_item"], "end-fitting")
        self.assertLess(result["end_fitting_margin_of_safety"], 0.0)
        self.assertFalse(result["compliant"])

    def test_strong_termination_leaves_the_cable_governing(self):
        result = assess_cable_drive(base_spec(termination_efficiency=1.0))
        self.assertEqual(result["governing_strength_item"], "cable-strength")

    def test_missing_key_rejected(self):
        spec = base_spec()
        del spec["breaking_load_n"]
        with self.assertRaises(ValueError):
            assess_cable_drive(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_cable_drive(["preload_n", 120.0])

    def test_bend_ratio_outside_the_curve_is_refused_not_extrapolated(self):
        with self.assertRaises(ValueError):
            assess_cable_drive(base_spec(pulley_diameter_mm=200.0))


if __name__ == "__main__":
    unittest.main()
