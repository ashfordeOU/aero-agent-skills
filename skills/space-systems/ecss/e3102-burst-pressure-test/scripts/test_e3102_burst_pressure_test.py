"""Contract test for the burst-pressure-test leaf (stdlib unittest)."""

import math
import unittest

from e3102_burst_pressure_test_logic import (
    BURST_METHODS,
    BURST_TOLERANCE,
    DEFAULT_LBB_LENGTH_MARGIN,
    DEFAULT_LEAK_DETECTION_MARGIN,
    MIN_BURST_FACTOR,
    achieved_burst_factor,
    assess_burst_pressure,
    assess_burst_test,
    assess_leak_before_burst,
    assess_method,
    corrected_burst_pressure_pa,
    critical_crack_length_m,
    hoop_stress_pa,
    require_positive,
    require_real,
    required_burst_pressure_pa,
    temperature_correction_factor,
    validate_burst_factor,
    validate_burst_method,
)

MDP = 2.0e6
FACTOR = 2.0
TOUGHNESS = 30.0e6
RADIUS = 0.01
THICKNESS = 0.001


def good_spec(**overrides):
    spec = {
        "mdp_pa": MDP,
        "burst_factor": FACTOR,
        "actual_burst_pa": 4.2e6,
        "method": "hydraulic-ramp-after-life-cycling",
        "preceded_by_life_cycling": True,
        "fracture_toughness_pa_sqrt_m": TOUGHNESS,
        "radius_m": RADIUS,
        "thickness_m": THICKNESS,
        "through_wall_leak_rate": 1.0e-4,
        "detection_threshold": 1.0e-6,
    }
    spec.update(overrides)
    return spec


class TestValidators(unittest.TestCase):
    def test_require_real_rejects_boolean(self):
        with self.assertRaises(ValueError):
            require_real("x", True)

    def test_require_real_rejects_infinity(self):
        with self.assertRaises(ValueError):
            require_real("x", float("inf"))

    def test_require_positive_rejects_negative(self):
        with self.assertRaises(ValueError):
            require_positive("x", -1.0)


class TestBurstFactor(unittest.TestCase):
    def test_factor_above_unity_is_accepted(self):
        self.assertAlmostEqual(validate_burst_factor(2.0), 2.0, places=9)

    def test_factor_of_exactly_unity_is_refused(self):
        with self.assertRaises(ValueError):
            validate_burst_factor(MIN_BURST_FACTOR)

    def test_required_pressure_is_mdp_times_factor(self):
        self.assertAlmostEqual(required_burst_pressure_pa(MDP, FACTOR), 4.0e6, places=9)

    def test_achieved_factor_is_actual_over_mdp(self):
        self.assertAlmostEqual(achieved_burst_factor(4.2e6, MDP), 2.1, places=9)

    def test_zero_mdp_raises(self):
        with self.assertRaises(ValueError):
            achieved_burst_factor(4.2e6, 0.0)


class TestTemperatureCorrection(unittest.TestCase):
    def test_equal_allowables_give_unity(self):
        self.assertAlmostEqual(temperature_correction_factor(300.0e6, 300.0e6),
                               1.0, places=9)

    def test_correction_scales_the_requirement(self):
        value = corrected_burst_pressure_pa(MDP, FACTOR, 330.0e6, 300.0e6)
        self.assertAlmostEqual(value, 4.4e6, places=9)

    def test_uncorrected_when_no_allowables_given(self):
        self.assertAlmostEqual(corrected_burst_pressure_pa(MDP, FACTOR), 4.0e6, places=9)

    def test_half_declared_correction_raises(self):
        with self.assertRaises(ValueError):
            corrected_burst_pressure_pa(MDP, FACTOR, None, 300.0e6)


class TestBurstPressure(unittest.TestCase):
    def test_burst_above_the_requirement_passes(self):
        result = assess_burst_pressure(4.2e6, 4.0e6, MDP)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["achieved_factor"], 2.1, places=9)

    def test_burst_exactly_at_the_requirement_passes(self):
        result = assess_burst_pressure(4.0e6, 4.0e6, MDP)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_pa"], 0.0, places=9)

    def test_burst_below_the_requirement_fails(self):
        result = assess_burst_pressure(3.5e6, 4.0e6, MDP)
        self.assertFalse(result["compliant"])
        self.assertTrue(result["findings"])

    def test_zero_burst_pressure_raises(self):
        with self.assertRaises(ValueError):
            assess_burst_pressure(0.0, 4.0e6, MDP)


class TestMethod(unittest.TestCase):
    def test_every_recognised_method_validates(self):
        for name in BURST_METHODS:
            self.assertEqual(validate_burst_method(name.upper()), name)

    def test_unrecognised_method_raises(self):
        with self.assertRaises(ValueError):
            validate_burst_method("squeeze-until-it-pops")

    def test_empty_method_raises(self):
        with self.assertRaises(ValueError):
            validate_burst_method("  ")

    def test_cycled_article_with_a_hydraulic_ramp_is_compliant(self):
        result = assess_method("hydraulic-ramp-after-life-cycling", True)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_pristine_article_is_an_end_of_manufacture_result(self):
        result = assess_method("hydraulic-monotonic-ramp", False)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("end-of-life" in f for f in result["findings"]))

    def test_pneumatic_ramp_without_justification_fails(self):
        result = assess_method("pneumatic-monotonic-ramp", True)
        self.assertFalse(result["compliant"])
        self.assertFalse(result["hazard_justified"])

    def test_pneumatic_ramp_with_justification_passes(self):
        result = assess_method("pneumatic-monotonic-ramp", True,
                               hazard_justification=True)
        self.assertTrue(result["compliant"])

    def test_non_boolean_history_raises(self):
        with self.assertRaises(ValueError):
            assess_method("hydraulic-monotonic-ramp", "yes")


class TestFractureGeometry(unittest.TestCase):
    def test_hoop_stress_is_pressure_times_radius_over_thickness(self):
        self.assertAlmostEqual(hoop_stress_pa(MDP, RADIUS, THICKNESS), 2.0e7, places=6)

    def test_thick_wall_is_refused(self):
        with self.assertRaises(ValueError):
            hoop_stress_pa(MDP, 0.001, 0.002)

    def test_zero_thickness_raises(self):
        with self.assertRaises(ValueError):
            hoop_stress_pa(MDP, RADIUS, 0.0)

    def test_critical_length_follows_the_toughness_relation(self):
        stress = 2.0e7
        ratio = TOUGHNESS / stress
        expected = 2.0 * (ratio * ratio) / math.pi
        self.assertAlmostEqual(critical_crack_length_m(TOUGHNESS, stress),
                               expected, places=9)

    def test_critical_length_shrinks_as_stress_rises(self):
        low = critical_crack_length_m(TOUGHNESS, 4.0e7)
        high = critical_crack_length_m(TOUGHNESS, 2.0e7)
        self.assertLess(low, high)

    def test_zero_stress_raises(self):
        with self.assertRaises(ValueError):
            critical_crack_length_m(TOUGHNESS, 0.0)


class TestLeakBeforeBurst(unittest.TestCase):
    def test_tough_thin_wall_leaks_before_it_breaks(self):
        result = assess_leak_before_burst(TOUGHNESS, MDP, RADIUS, THICKNESS,
                                          1.0e-4, 1.0e-6)
        self.assertTrue(result["compliant"])
        self.assertGreater(result["length_ratio"], 1.0)

    def test_brittle_wall_runs_before_it_penetrates(self):
        result = assess_leak_before_burst(1.0e5, MDP, RADIUS, THICKNESS,
                                          1.0e-4, 1.0e-6)
        self.assertFalse(result["leaks_before_break"])
        self.assertFalse(result["compliant"])

    def test_length_exactly_at_the_required_value_is_accepted(self):
        stress = hoop_stress_pa(MDP, RADIUS, THICKNESS)
        critical = critical_crack_length_m(TOUGHNESS, stress)
        result = assess_leak_before_burst(
            TOUGHNESS, MDP, RADIUS, THICKNESS, 1.0e-4, 1.0e-6,
            length_margin=critical / THICKNESS,
        )
        self.assertTrue(result["leaks_before_break"])
        self.assertAlmostEqual(result["length_ratio"], 1.0, places=9)

    def test_leak_below_the_detection_margin_is_reported(self):
        result = assess_leak_before_burst(TOUGHNESS, MDP, RADIUS, THICKNESS,
                                          2.0e-6, 1.0e-6)
        self.assertTrue(result["leaks_before_break"])
        self.assertFalse(result["leak_detectable"])
        self.assertFalse(result["compliant"])

    def test_leak_exactly_at_the_detection_margin_is_accepted(self):
        threshold = 1.0e-6
        result = assess_leak_before_burst(
            TOUGHNESS, MDP, RADIUS, THICKNESS,
            DEFAULT_LEAK_DETECTION_MARGIN * threshold, threshold,
        )
        self.assertTrue(result["leak_detectable"])

    def test_default_length_margin_is_one_wall_thickness(self):
        # A declared policy constant, not a computed quantity: stated
        # exactly. One wall thickness is the floor, and the default sits on
        # it, so an inequality here would only assert the rounding
        # direction of a literal.
        self.assertEqual(DEFAULT_LBB_LENGTH_MARGIN, 1.0)

    def test_margin_below_the_wall_is_refused(self):
        # Below 1.0 the required length is shorter than the wall, which asks
        # the crack to be critical before it is through-wall -- the inverse
        # of the criterion being graded.
        with self.assertRaises(ValueError):
            assess_leak_before_burst(
                TOUGHNESS, MDP, RADIUS, THICKNESS, 1.0e-4, 1.0e-6,
                length_margin=0.9,
            )

    def test_margin_exactly_at_the_wall_is_accepted(self):
        result = assess_leak_before_burst(
            TOUGHNESS, MDP, RADIUS, THICKNESS, 1.0e-4, 1.0e-6,
            length_margin=1.0,
        )
        self.assertTrue(result["leaks_before_break"])

    def test_zero_detection_threshold_raises(self):
        with self.assertRaises(ValueError):
            assess_leak_before_burst(TOUGHNESS, MDP, RADIUS, THICKNESS, 1.0e-4, 0.0)


class TestWholeTest(unittest.TestCase):
    def test_good_burst_campaign_is_compliant(self):
        report = assess_burst_test(good_spec())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])
        self.assertAlmostEqual(report["required_burst_pa"], 4.0e6, places=9)

    def test_low_burst_names_the_failed_check(self):
        report = assess_burst_test(good_spec(actual_burst_pa=3.0e6))
        self.assertFalse(report["compliant"])
        self.assertIn("burst_pressure", report["failed_checks"])

    def test_pristine_article_names_the_failed_check(self):
        report = assess_burst_test(good_spec(preceded_by_life_cycling=False))
        self.assertIn("method", report["failed_checks"])

    def test_brittle_wall_names_the_failed_check(self):
        report = assess_burst_test(good_spec(fracture_toughness_pa_sqrt_m=1.0e5))
        self.assertIn("leak_before_burst", report["failed_checks"])

    def test_grading_pressure_defaults_to_the_design_pressure(self):
        report = assess_burst_test(good_spec())
        self.assertAlmostEqual(report["checks"]["leak_before_burst"]["hoop_stress_pa"],
                               2.0e7, places=6)

    def test_missing_key_raises(self):
        spec = good_spec()
        del spec["thickness_m"]
        with self.assertRaises(ValueError):
            assess_burst_test(spec)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_burst_test("burst")

    def test_tolerance_is_a_representation_allowance_only(self):
        self.assertLess(BURST_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
