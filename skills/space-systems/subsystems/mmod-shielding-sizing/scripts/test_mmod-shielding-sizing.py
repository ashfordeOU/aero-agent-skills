"""Contract test for mmod-shielding-sizing (space-systems/subsystems).

Exercises the SKILL.md workflow steps end to end: step 1 (Cour-Palais
penetration depth), step 2 (single-wall required thickness and critical
diameter, including the round-trip inversion), step 3 (Whipple bumper
thickness), step 4 (Whipple rear-wall design thickness and the sphere
mass helper), step 5 (Whipple critical diameter across the low,
intermediate-blend, and hypervelocity regimes with the obliquity cap),
step 6 (the per-impact penetration verdict), and step 7 (the mission
penetration probability from the expected number of penetrating
impacts). Stdlib unittest, deterministic, offline, no network.
"""

import importlib.util
import math
import os
import unittest

_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
_SPEC = importlib.util.spec_from_file_location(
    "mmod_shielding_sizing_logic",
    os.path.join(_SCRIPTS, "mmod-shielding-sizing_logic.py"),
)
mmod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mmod)


class TestSingleWallCourPalais(unittest.TestCase):
    """Step 1 and step 2 of the SKILL.md workflow: the single-wall path."""

    def test_cour_palais_penetration_depth_worked_example(self):
        p_inf = mmod.cour_palais_penetration_depth(1.0, 2.7, 2.7, 95.0, 10.0, 0.0, 5.0)
        self.assertAlmostEqual(p_inf, 2.664324077003382, delta=1e-9)

    def test_single_wall_required_thickness_worked_example(self):
        t_req = mmod.single_wall_required_thickness(1.0, 2.7, 2.7, 95.0, 10.0, 0.0, 5.0)
        self.assertAlmostEqual(t_req, 4.795783338606088, delta=1e-9)

    def test_t_req_equals_k_times_p_inf(self):
        p_inf = mmod.cour_palais_penetration_depth(1.0, 2.7, 2.7, 95.0, 10.0, 0.0, 5.0)
        t_req = mmod.single_wall_required_thickness(1.0, 2.7, 2.7, 95.0, 10.0, 0.0, 5.0)
        self.assertAlmostEqual(t_req, mmod.K_PERFORATION * p_inf, delta=1e-12)

    def test_single_wall_critical_diameter_worked_example(self):
        dc = mmod.single_wall_critical_diameter(0.48, 2.7, 2.7, 95.0, 10.0, 0.0, 5.0)
        self.assertAlmostEqual(dc, 0.11297781552560618, delta=1e-9)

    def test_single_wall_round_trip_aluminum_branch(self):
        """Step 2 round trip on the r < 1.5 branch (aluminum on aluminum)."""
        d = 0.3
        t_req = mmod.single_wall_required_thickness(d, 2.7, 2.7, 95.0, 10.0, 0.0, 5.0)
        dc = mmod.single_wall_critical_diameter(t_req, 2.7, 2.7, 95.0, 10.0, 0.0, 5.0)
        self.assertAlmostEqual(dc / d, 1.0, delta=1e-9)

    def test_single_wall_round_trip_steel_branch(self):
        """Step 2 round trip on the r >= 1.5 branch (steel on aluminum)."""
        d = 0.3
        t_req = mmod.single_wall_required_thickness(d, 7.85, 2.7, 95.0, 10.0, 0.0, 5.0)
        dc = mmod.single_wall_critical_diameter(t_req, 7.85, 2.7, 95.0, 10.0, 0.0, 5.0)
        self.assertAlmostEqual(dc / d, 1.0, delta=1e-9)


class TestWhippleDesign(unittest.TestCase):
    """Step 3 and step 4 of the SKILL.md workflow: sizing the Whipple shield."""

    def test_whipple_bumper_thickness_near_branch(self):
        tb = mmod.whipple_bumper_thickness(1.0, 2.7, 2.7, 11.43)
        self.assertAlmostEqual(tb, 0.25, delta=1e-9)

    def test_whipple_bumper_thickness_far_branch(self):
        tb = mmod.whipple_bumper_thickness(1.0, 2.7, 2.7, 31.0)
        self.assertAlmostEqual(tb, mmod.CB_FAR * 1.0 * 2.7 / 2.7, delta=1e-9)

    def test_sphere_mass_g_worked_example(self):
        mp = mmod.sphere_mass_g(1.0, 2.7)
        self.assertAlmostEqual(mp, 1.413716694115407, delta=1e-9)

    def test_whipple_rear_wall_thickness_worked_example(self):
        tw = mmod.whipple_rear_wall_thickness(1.0, 2.7, 2.7, 11.43, 40.0, 7.0, 0.0)
        self.assertAlmostEqual(tw, 0.684892875727985, delta=1e-9)

    def test_whipple_rear_wall_thickness_rejects_low_velocity(self):
        with self.assertRaises(ValueError) as ctx:
            mmod.whipple_rear_wall_thickness(1.0, 2.7, 2.7, 11.43, 40.0, 6.0, 0.0)
        self.assertIn("at least 7 km/s", str(ctx.exception))


class TestWhippleBallisticLimit(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: the three-regime ballistic limit."""

    def setUp(self):
        self.tb = mmod.whipple_bumper_thickness(1.0, 2.7, 2.7, 11.43)
        self.tw = mmod.whipple_rear_wall_thickness(1.0, 2.7, 2.7, 11.43, 40.0, 7.0, 0.0)

    def test_design_case_critical_diameter(self):
        dc = mmod.whipple_critical_diameter(self.tb, self.tw, 40.0, 2.7, 2.7, 11.43, 7.0, 0.0)
        self.assertAlmostEqual(dc, 1.000075994715671, delta=1e-9)

    def test_design_self_consistency_closed_form(self):
        dc = mmod.whipple_critical_diameter(self.tb, self.tw, 40.0, 2.7, 2.7, 11.43, 7.0, 0.0)
        factor = mmod.C_HYPER * 0.16 ** (2.0 / 3.0) * (math.pi / 6.0) ** (2.0 / 9.0)
        self.assertAlmostEqual(dc, factor, delta=1e-9)
        self.assertTrue(abs(factor - 1.0) < 2e-4)

    def test_critical_diameter_at_10kms(self):
        dc10 = mmod.whipple_critical_diameter(self.tb, self.tw, 40.0, 2.7, 2.7, 11.43, 10.0, 0.0)
        self.assertAlmostEqual(dc10, 0.7884334285317389, delta=1e-9)

    def test_hypervelocity_scaling_identity(self):
        dc7 = mmod.whipple_critical_diameter(self.tb, self.tw, 40.0, 2.7, 2.7, 11.43, 7.0, 0.0)
        dc10 = mmod.whipple_critical_diameter(self.tb, self.tw, 40.0, 2.7, 2.7, 11.43, 10.0, 0.0)
        self.assertAlmostEqual(dc10 / dc7, (7.0 / 10.0) ** (2.0 / 3.0), delta=1e-12)

    def test_hypervelocity_depends_on_normal_velocity_only(self):
        dc7_normal = mmod.whipple_critical_diameter(
            self.tb, self.tw, 40.0, 2.7, 2.7, 11.43, 7.0, 0.0
        )
        v_oblique = 7.0 / math.cos(math.radians(45.0))
        dc7_oblique = mmod.whipple_critical_diameter(
            self.tb, self.tw, 40.0, 2.7, 2.7, 11.43, v_oblique, 45.0
        )
        self.assertAlmostEqual(dc7_normal, dc7_oblique, delta=1e-12)

    def test_obliquity_cap_at_65_degrees(self):
        dc70 = mmod.whipple_critical_diameter(self.tb, self.tw, 40.0, 2.7, 2.7, 11.43, 9.0, 70.0)
        dc65 = mmod.whipple_critical_diameter(self.tb, self.tw, 40.0, 2.7, 2.7, 11.43, 9.0, 65.0)
        self.assertAlmostEqual(dc70, dc65, delta=1e-12)
        self.assertAlmostEqual(dc65, 1.0594730484880124, delta=1e-9)

    def test_regime_continuity_at_vlow_boundary(self):
        dc_boundary = mmod.whipple_critical_diameter(
            self.tb, self.tw, 40.0, 2.7, 2.7, 11.43, mmod.V_LOW, 0.0
        )
        dc_l3 = mmod._dc_low(self.tb, self.tw, 2.7, 40.0, mmod.V_LOW, 0.0)
        self.assertAlmostEqual(dc_boundary, dc_l3, delta=1e-9)

    def test_regime_continuity_at_vhigh_boundary(self):
        dc_boundary = mmod.whipple_critical_diameter(
            self.tb, self.tw, 40.0, 2.7, 2.7, 11.43, mmod.V_HIGH, 0.0
        )
        dc_h7 = mmod._dc_hyper(self.tw, 2.7, 2.7, 11.43, 40.0, mmod.V_HIGH)
        self.assertAlmostEqual(dc_boundary, dc_h7, delta=1e-9)

    def test_regime_curve_low_and_intermediate_magnitudes(self):
        dc_low = mmod.whipple_critical_diameter(self.tb, self.tw, 40.0, 2.7, 2.7, 11.43, 2.0, 0.0)
        dc_mid = mmod.whipple_critical_diameter(self.tb, self.tw, 40.0, 2.7, 2.7, 11.43, 6.5, 0.0)
        self.assertAlmostEqual(dc_low, 0.6137885577448827, delta=1e-6)
        self.assertAlmostEqual(dc_mid, 0.9344564876830601, delta=1e-6)


class TestPenetrationVerdict(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: grading a single impact."""

    def setUp(self):
        self.tb = mmod.whipple_bumper_thickness(1.0, 2.7, 2.7, 11.43)
        self.tw = mmod.whipple_rear_wall_thickness(1.0, 2.7, 2.7, 11.43, 40.0, 7.0, 0.0)

    def test_no_penetration_at_design_case(self):
        verdict, margin = mmod.penetration_verdict(1.0, 1.000075994715671)
        self.assertEqual(verdict, "NO_PENETRATION")
        self.assertAlmostEqual(margin, 0.999924011059087, delta=1e-9)

    def test_penetration_at_10kms(self):
        verdict, margin = mmod.penetration_verdict(1.0, 0.7884334285317389)
        self.assertEqual(verdict, "PENETRATION")
        self.assertAlmostEqual(margin, 1.2683379012255367, delta=1e-9)

    def test_whipple_penetration_verdict_dict_shape(self):
        result = mmod.whipple_penetration_verdict(
            1.0, self.tb, self.tw, 40.0, 2.7, 2.7, 11.43, 7.0, 0.0
        )
        self.assertEqual(set(result.keys()), {"verdict", "dc", "margin"})
        self.assertEqual(result["verdict"], "NO_PENETRATION")
        self.assertAlmostEqual(result["margin"], result["dc"] and 1.0 / result["dc"], delta=1e-9)


class TestMissionRollup(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the Poisson mission penetration probability."""

    def test_zero_lambda_is_exactly_zero(self):
        self.assertEqual(mmod.penetration_probability(0.0), 0.0)

    def test_worked_example_value(self):
        p = mmod.penetration_probability(0.5)
        self.assertAlmostEqual(p, 0.3934693402873666, delta=1e-9)

    def test_monotonic_increase_with_lambda(self):
        values = [mmod.penetration_probability(lam) for lam in (0.0, 0.5, 2.0, 5.0)]
        for earlier, later in zip(values, values[1:]):
            self.assertLess(earlier, later)

    def test_negative_lambda_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            mmod.penetration_probability(-0.1)
        self.assertIn("non-negative", str(ctx.exception))


class TestInputValidation(unittest.TestCase):
    """Boundary and ValueError coverage for every public function."""

    def test_theta_at_90_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            mmod.cour_palais_penetration_depth(1.0, 2.7, 2.7, 95.0, 10.0, 90.0, 5.0)
        self.assertIn("[0, 90)", str(ctx.exception))

    def test_negative_diameter_rejected(self):
        with self.assertRaises(ValueError):
            mmod.cour_palais_penetration_depth(-1.0, 2.7, 2.7, 95.0, 10.0, 0.0, 5.0)

    def test_zero_hardness_rejected(self):
        with self.assertRaises(ValueError):
            mmod.cour_palais_penetration_depth(1.0, 2.7, 2.7, 0.0, 10.0, 0.0, 5.0)

    def test_boolean_argument_rejected(self):
        with self.assertRaises(ValueError):
            mmod.whipple_bumper_thickness(True, 2.7, 2.7, 11.43)

    def test_non_positive_k_rejected(self):
        with self.assertRaises(ValueError):
            mmod.single_wall_required_thickness(1.0, 2.7, 2.7, 95.0, 10.0, 0.0, 5.0, k=0.0)

    def test_non_positive_standoff_rejected(self):
        with self.assertRaises(ValueError):
            mmod.whipple_bumper_thickness(1.0, 2.7, 2.7, 0.0)


class TestDeterminism(unittest.TestCase):
    """Determinism and module constants, closing the SKILL.md contract."""

    def test_repeat_calls_identical(self):
        tb = mmod.whipple_bumper_thickness(1.0, 2.7, 2.7, 11.43)
        tw = mmod.whipple_rear_wall_thickness(1.0, 2.7, 2.7, 11.43, 40.0, 7.0, 0.0)
        first = mmod.whipple_penetration_verdict(1.0, tb, tw, 40.0, 2.7, 2.7, 11.43, 7.0, 0.0)
        second = mmod.whipple_penetration_verdict(1.0, tb, tw, 40.0, 2.7, 2.7, 11.43, 7.0, 0.0)
        self.assertEqual(first, second)

    def test_module_constants_pinned(self):
        self.assertEqual(mmod.C_CP, 5.24)
        self.assertEqual(mmod.K_PERFORATION, 1.8)
        self.assertEqual(mmod.K_DETACHED_SPALL, 2.2)
        self.assertEqual(mmod.K_INCIPIENT_SPALL, 3.0)
        self.assertEqual(mmod.C_HYPER, 3.918)
        self.assertEqual(mmod.C_WALL_DESIGN, 0.16)
        self.assertEqual(mmod.CB_NEAR, 0.25)
        self.assertEqual(mmod.CB_FAR, 0.20)
        self.assertEqual(mmod.V_LOW, 3.0)
        self.assertEqual(mmod.V_HIGH, 7.0)
        self.assertEqual(mmod.THETA_CAP_DEG, 65.0)


if __name__ == "__main__":
    unittest.main()
