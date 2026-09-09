"""Contract test for landing-gear-weight-estimation (vehicle-design/sizing).

Exercises the SKILL.md Workflow steps: step 1 (fix the design landing
weight and the ultimate landing load factor), step 2
(main_gear_group_weight regression), step 3 (nose_gear_group_weight
regression), step 4 (landing_gear_group_total sum and the gear group
fraction of the design landing weight and MTOW), step 5 (the design
landing weight, load factor and geometry power-law identities), and
step 6 (ValueError rejection of non-physical inputs).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import landing_gear_weight_estimation_logic as lgwe

DESIGN_LANDING_WEIGHT_KG = 66000.0
LIMIT_LOAD_FACTOR = 3.0
MAIN_STRUT_LENGTH_M = 2.30
MAIN_WHEELS = 4
MAIN_SHOCK_STRUTS = 2
STALL_SPEED_KTS = 115.0
NOSE_STRUT_LENGTH_M = 1.40
NOSE_WHEELS = 2
MTOW_KG = 79000.0

EXPECTED_MAIN_KG = 2893.904950
EXPECTED_NOSE_KG = 430.316692
EXPECTED_TOTAL_KG = 3324.221642


class WorkedExampleTests(unittest.TestCase):
    """Step 1-4 of the SKILL.md Workflow: fix the design point, evaluate
    the main-gear-group-weight and nose-gear-group-weight regressions,
    and sum the landing gear group total for the 180-seat narrowbody
    worked example."""

    def setUp(self):
        self.w_main = lgwe.main_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            MAIN_STRUT_LENGTH_M,
            MAIN_WHEELS,
            MAIN_SHOCK_STRUTS,
            STALL_SPEED_KTS,
        )
        self.w_nose = lgwe.nose_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            NOSE_STRUT_LENGTH_M,
            NOSE_WHEELS,
        )
        self.total = lgwe.landing_gear_group_total(self.w_main, self.w_nose)

    def test_main_gear_group_weight_worked_example(self):
        self.assertAlmostEqual(
            self.w_main, EXPECTED_MAIN_KG, delta=1e-6 * EXPECTED_MAIN_KG
        )

    def test_nose_gear_group_weight_worked_example(self):
        self.assertAlmostEqual(
            self.w_nose, EXPECTED_NOSE_KG, delta=1e-6 * EXPECTED_NOSE_KG
        )

    def test_landing_gear_group_total_worked_example(self):
        self.assertAlmostEqual(
            self.total, EXPECTED_TOTAL_KG, delta=1e-6 * EXPECTED_TOTAL_KG
        )

    def test_gear_group_fraction_of_landing_weight(self):
        frac = lgwe.gear_group_fraction(self.total, DESIGN_LANDING_WEIGHT_KG)
        self.assertAlmostEqual(frac, 0.050367, delta=1e-5)

    def test_gear_group_fraction_of_mtow(self):
        frac = lgwe.gear_group_fraction(self.total, MTOW_KG)
        self.assertAlmostEqual(frac, 0.042079, delta=1e-5)

    def test_nose_gear_share_of_total(self):
        share = self.w_nose / self.total
        self.assertAlmostEqual(share, 0.129449, delta=1e-5)


class PhysicalSanityBandTests(unittest.TestCase):
    """Step 4 of the Workflow, the class-II physical-sanity band checks
    on the gear group total and its fractions of the design landing
    weight and MTOW."""

    def setUp(self):
        w_main = lgwe.main_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            MAIN_STRUT_LENGTH_M,
            MAIN_WHEELS,
            MAIN_SHOCK_STRUTS,
            STALL_SPEED_KTS,
        )
        w_nose = lgwe.nose_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            NOSE_STRUT_LENGTH_M,
            NOSE_WHEELS,
        )
        self.w_main = w_main
        self.w_nose = w_nose
        self.total = lgwe.landing_gear_group_total(w_main, w_nose)

    def test_group_masses_positive(self):
        self.assertGreater(self.w_main, 0.0)
        self.assertGreater(self.w_nose, 0.0)

    def test_main_gear_group_above_nose_gear_group(self):
        self.assertGreater(self.w_main, self.w_nose)

    def test_total_below_design_landing_weight(self):
        self.assertLess(self.total, DESIGN_LANDING_WEIGHT_KG)

    def test_landing_weight_fraction_in_band(self):
        frac = lgwe.gear_group_fraction(self.total, DESIGN_LANDING_WEIGHT_KG)
        self.assertGreaterEqual(frac, 0.03)
        self.assertLessEqual(frac, 0.07)

    def test_mtow_fraction_in_band(self):
        frac = lgwe.gear_group_fraction(self.total, MTOW_KG)
        self.assertGreaterEqual(frac, 0.03)
        self.assertLessEqual(frac, 0.06)

    def test_nose_share_in_band(self):
        share = self.w_nose / self.total
        self.assertGreaterEqual(share, 0.05)
        self.assertLessEqual(share, 0.25)

    def test_mtow_fraction_far_below_empty_weight_band(self):
        frac = lgwe.gear_group_fraction(self.total, MTOW_KG)
        self.assertLess(frac, 0.42)


class PowerLawIdentityTests(unittest.TestCase):
    """Step 5 of the Workflow, the exact-power identities: recomputing
    each regression at a doubled regressor scales the group mass by
    exactly 2 raised to that regressor's published exponent."""

    def setUp(self):
        self.w_main = lgwe.main_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            MAIN_STRUT_LENGTH_M,
            MAIN_WHEELS,
            MAIN_SHOCK_STRUTS,
            STALL_SPEED_KTS,
        )
        self.w_nose = lgwe.nose_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            NOSE_STRUT_LENGTH_M,
            NOSE_WHEELS,
        )

    def test_design_landing_weight_power_law_main(self):
        w_main2 = lgwe.main_gear_group_weight(
            2 * DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            MAIN_STRUT_LENGTH_M,
            MAIN_WHEELS,
            MAIN_SHOCK_STRUTS,
            STALL_SPEED_KTS,
        )
        self.assertTrue(
            math.isclose(w_main2 / self.w_main, 2 ** 0.888, rel_tol=1e-9)
        )

    def test_design_landing_weight_power_law_nose(self):
        w_nose2 = lgwe.nose_gear_group_weight(
            2 * DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            NOSE_STRUT_LENGTH_M,
            NOSE_WHEELS,
        )
        self.assertTrue(
            math.isclose(w_nose2 / self.w_nose, 2 ** 0.646, rel_tol=1e-9)
        )

    def test_load_factor_power_law_main(self):
        w_main2 = lgwe.main_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            2 * LIMIT_LOAD_FACTOR,
            MAIN_STRUT_LENGTH_M,
            MAIN_WHEELS,
            MAIN_SHOCK_STRUTS,
            STALL_SPEED_KTS,
        )
        self.assertTrue(
            math.isclose(w_main2 / self.w_main, 2 ** 0.25, rel_tol=1e-9)
        )

    def test_load_factor_power_law_nose(self):
        w_nose2 = lgwe.nose_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            2 * LIMIT_LOAD_FACTOR,
            NOSE_STRUT_LENGTH_M,
            NOSE_WHEELS,
        )
        self.assertTrue(
            math.isclose(w_nose2 / self.w_nose, 2 ** 0.2, rel_tol=1e-9)
        )

    def test_main_strut_length_power_law(self):
        w_main2 = lgwe.main_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            2 * MAIN_STRUT_LENGTH_M,
            MAIN_WHEELS,
            MAIN_SHOCK_STRUTS,
            STALL_SPEED_KTS,
        )
        self.assertTrue(
            math.isclose(w_main2 / self.w_main, 2 ** 0.4, rel_tol=1e-9)
        )

    def test_nose_strut_length_power_law(self):
        w_nose2 = lgwe.nose_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            2 * NOSE_STRUT_LENGTH_M,
            NOSE_WHEELS,
        )
        self.assertTrue(
            math.isclose(w_nose2 / self.w_nose, 2 ** 0.5, rel_tol=1e-9)
        )

    def test_main_wheel_count_power_law(self):
        w_main2 = lgwe.main_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            MAIN_STRUT_LENGTH_M,
            2 * MAIN_WHEELS,
            MAIN_SHOCK_STRUTS,
            STALL_SPEED_KTS,
        )
        self.assertTrue(
            math.isclose(w_main2 / self.w_main, 2 ** 0.321, rel_tol=1e-9)
        )

    def test_nose_wheel_count_power_law(self):
        w_nose2 = lgwe.nose_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            NOSE_STRUT_LENGTH_M,
            2 * NOSE_WHEELS,
        )
        self.assertTrue(
            math.isclose(w_nose2 / self.w_nose, 2 ** 0.45, rel_tol=1e-9)
        )

    def test_main_shock_strut_count_power_law_is_negative(self):
        w_main2 = lgwe.main_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            MAIN_STRUT_LENGTH_M,
            MAIN_WHEELS,
            2 * MAIN_SHOCK_STRUTS,
            STALL_SPEED_KTS,
        )
        ratio = w_main2 / self.w_main
        self.assertTrue(math.isclose(ratio, 2 ** -0.5, rel_tol=1e-9))
        self.assertLess(ratio, 1.0)

    def test_stall_speed_power_law(self):
        w_main2 = lgwe.main_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            MAIN_STRUT_LENGTH_M,
            MAIN_WHEELS,
            MAIN_SHOCK_STRUTS,
            2 * STALL_SPEED_KTS,
        )
        self.assertTrue(
            math.isclose(w_main2 / self.w_main, 2 ** 0.1, rel_tol=1e-9)
        )


class SublinearScalingAndMonotonicityTests(unittest.TestCase):
    """Step 5 of the Workflow: the sublinear fraction fall as the design
    landing weight grows, and step 1-3 monotonicity of both group masses
    in the design landing weight."""

    def test_gear_group_fraction_falls_when_landing_weight_doubles(self):
        w_main1 = lgwe.main_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            MAIN_STRUT_LENGTH_M,
            MAIN_WHEELS,
            MAIN_SHOCK_STRUTS,
            STALL_SPEED_KTS,
        )
        w_nose1 = lgwe.nose_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            NOSE_STRUT_LENGTH_M,
            NOSE_WHEELS,
        )
        total1 = lgwe.landing_gear_group_total(w_main1, w_nose1)
        frac1 = lgwe.gear_group_fraction(total1, DESIGN_LANDING_WEIGHT_KG)

        w_main2 = lgwe.main_gear_group_weight(
            2 * DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            MAIN_STRUT_LENGTH_M,
            MAIN_WHEELS,
            MAIN_SHOCK_STRUTS,
            STALL_SPEED_KTS,
        )
        w_nose2 = lgwe.nose_gear_group_weight(
            2 * DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            NOSE_STRUT_LENGTH_M,
            NOSE_WHEELS,
        )
        total2 = lgwe.landing_gear_group_total(w_main2, w_nose2)
        frac2 = lgwe.gear_group_fraction(total2, 2 * DESIGN_LANDING_WEIGHT_KG)

        self.assertAlmostEqual(frac1, 0.050367, delta=1e-5)
        self.assertAlmostEqual(frac2, 0.045673, delta=1e-5)
        self.assertLess(frac2, frac1)
        self.assertLess(w_main2 / w_main1, 2.0)
        self.assertLess(w_nose2 / w_nose1, 2.0)

    def test_monotonicity_one_percent_higher_landing_weight(self):
        w_main1 = lgwe.main_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            MAIN_STRUT_LENGTH_M,
            MAIN_WHEELS,
            MAIN_SHOCK_STRUTS,
            STALL_SPEED_KTS,
        )
        w_nose1 = lgwe.nose_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            NOSE_STRUT_LENGTH_M,
            NOSE_WHEELS,
        )
        w_main2 = lgwe.main_gear_group_weight(
            1.01 * DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            MAIN_STRUT_LENGTH_M,
            MAIN_WHEELS,
            MAIN_SHOCK_STRUTS,
            STALL_SPEED_KTS,
        )
        w_nose2 = lgwe.nose_gear_group_weight(
            1.01 * DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            NOSE_STRUT_LENGTH_M,
            NOSE_WHEELS,
        )
        self.assertGreater(w_main2, w_main1)
        self.assertGreater(w_nose2, w_nose1)


class ConsumerScaleCrossCheckTests(unittest.TestCase):
    """Step 6 of the Workflow: cross-check the main gear group weight
    per shock strut leg against the given gear weight scale that the
    landing-gear-retraction-sizing sibling worked example fixes as its
    input (14000 N main-gear leg weight, CG arm 1.10 m ahead of the
    retract pivot)."""

    def test_per_leg_force_on_order_of_retraction_sibling_input(self):
        w_main = lgwe.main_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            MAIN_STRUT_LENGTH_M,
            MAIN_WHEELS,
            MAIN_SHOCK_STRUTS,
            STALL_SPEED_KTS,
        )
        per_leg_n = w_main * 9.80665 / MAIN_SHOCK_STRUTS
        self.assertAlmostEqual(per_leg_n / 1000.0, 14.190, delta=0.01)
        retraction_sibling_given_n = 14000.0
        self.assertLess(
            abs(per_leg_n - retraction_sibling_given_n) / retraction_sibling_given_n,
            0.05,
        )


class ValueErrorRejectionTests(unittest.TestCase):
    """Step 6 of the Workflow: ValueError rejection of every non-physical
    input across main_gear_group_weight, nose_gear_group_weight and
    landing_gear_group_total."""

    def test_nonpositive_design_landing_weight(self):
        with self.assertRaises(ValueError) as ctx:
            lgwe.main_gear_group_weight(0.0, 3.0, 2.30, 4, 2, 115.0)
        self.assertEqual(
            str(ctx.exception), "design landing weight must be positive, got 0.0"
        )

    def test_nonpositive_limit_load_factor(self):
        with self.assertRaises(ValueError) as ctx:
            lgwe.main_gear_group_weight(66000.0, -1.0, 2.30, 4, 2, 115.0)
        self.assertEqual(
            str(ctx.exception),
            "design limit landing load factor must be positive, got -1.0",
        )

    def test_nonpositive_main_strut_length(self):
        with self.assertRaises(ValueError) as ctx:
            lgwe.main_gear_group_weight(66000.0, 3.0, 0.0, 4, 2, 115.0)
        self.assertEqual(
            str(ctx.exception), "main strut length must be positive, got 0.0"
        )

    def test_main_wheels_below_minimum(self):
        with self.assertRaises(ValueError) as ctx:
            lgwe.main_gear_group_weight(66000.0, 3.0, 2.30, 0, 2, 115.0)
        self.assertEqual(
            str(ctx.exception),
            "number of main gear wheels must be at least 1, got 0",
        )

    def test_main_shock_struts_below_minimum(self):
        with self.assertRaises(ValueError) as ctx:
            lgwe.main_gear_group_weight(66000.0, 3.0, 2.30, 4, 0, 115.0)
        self.assertEqual(
            str(ctx.exception),
            "number of main gear shock struts must be at least 1, got 0",
        )

    def test_nonpositive_stall_speed(self):
        with self.assertRaises(ValueError) as ctx:
            lgwe.main_gear_group_weight(66000.0, 3.0, 2.30, 4, 2, 0.0)
        self.assertEqual(
            str(ctx.exception), "stall speed must be positive, got 0.0"
        )

    def test_nonpositive_nose_strut_length(self):
        with self.assertRaises(ValueError) as ctx:
            lgwe.nose_gear_group_weight(66000.0, 3.0, 0.0, 2)
        self.assertEqual(
            str(ctx.exception), "nose strut length must be positive, got 0.0"
        )

    def test_nose_wheels_below_minimum(self):
        with self.assertRaises(ValueError) as ctx:
            lgwe.nose_gear_group_weight(66000.0, 3.0, 1.40, 0)
        self.assertEqual(
            str(ctx.exception),
            "number of nose gear wheels must be at least 1, got 0",
        )

    def test_negative_group_mass_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            lgwe.landing_gear_group_total(-1.0, 1.0)
        self.assertEqual(
            str(ctx.exception), "group mass 1 must be non-negative, got -1.0"
        )

    def test_nonnumber_group_mass_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            lgwe.landing_gear_group_total("a", 1.0)
        self.assertEqual(
            str(ctx.exception), "group mass 1 must be a number, got 'a'"
        )


class DeterminismTests(unittest.TestCase):
    """Step 6 of the Workflow: identical outputs run to run, confirming
    no randomness anywhere in the closed-form power-law arithmetic."""

    def test_repeated_calls_are_identical(self):
        run1 = lgwe.main_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            MAIN_STRUT_LENGTH_M,
            MAIN_WHEELS,
            MAIN_SHOCK_STRUTS,
            STALL_SPEED_KTS,
        )
        run2 = lgwe.main_gear_group_weight(
            DESIGN_LANDING_WEIGHT_KG,
            LIMIT_LOAD_FACTOR,
            MAIN_STRUT_LENGTH_M,
            MAIN_WHEELS,
            MAIN_SHOCK_STRUTS,
            STALL_SPEED_KTS,
        )
        self.assertEqual(run1, run2)

    def test_ultimate_load_factor_identity(self):
        self.assertAlmostEqual(
            lgwe.ultimate_landing_load_factor(3.0), 4.5, delta=1e-12
        )


if __name__ == "__main__":
    unittest.main()
