#!/usr/bin/env python3
"""Behavior-contract tests for the parasite-drag buildup logic.

Gate 3 contract: stdlib unittest, offline, deterministic. Run with:
python3 test_parasite_drag.py
"""

import math
import unittest

import parasite_drag_logic as pd


class TestReynoldsNumber(unittest.TestCase):
    def test_concrete_value(self):
        # Sea-level air, V=70 m/s, chord 2.5 m: Re = rho*V*L/mu.
        self.assertAlmostEqual(
            pd.reynolds_number(1.225, 70.0, 2.5, 1.7894e-5),
            11980272.717, delta=1.0,
        )

    def test_scales_linearly_with_speed(self):
        base = pd.reynolds_number(1.225, 70.0, 2.5, 1.7894e-5)
        double = pd.reynolds_number(1.225, 140.0, 2.5, 1.7894e-5)
        self.assertAlmostEqual(double, 2.0 * base)

    def test_nonpositive_inputs_raise(self):
        for bad in [
            dict(rho=0.0, v=70.0, l=2.5, mu=1.7894e-5),
            dict(rho=1.225, v=-5.0, l=2.5, mu=1.7894e-5),
            dict(rho=1.225, v=70.0, l=0.0, mu=1.7894e-5),
            dict(rho=1.225, v=70.0, l=2.5, mu=-1.0),
        ]:
            with self.assertRaises(ValueError):
                pd.reynolds_number(**bad)


class TestFlatPlateSkinFriction(unittest.TestCase):
    def test_laminar_concrete(self):
        # Blasius: Cf = 1.328 / sqrt(Re) at Re = 1e5.
        self.assertAlmostEqual(
            pd.cf_flat_plate_laminar(1e5), 0.0041995047, delta=1e-9
        )

    def test_laminar_edge_zero_re_raises(self):
        with self.assertRaises(ValueError):
            pd.cf_flat_plate_laminar(0.0)
        with self.assertRaises(ValueError):
            pd.cf_flat_plate_laminar(-1e3)

    def test_turbulent_concrete(self):
        # Schlichting: Cf = 0.455 / (log10 Re)^2.58 at Re = 1e7.
        self.assertAlmostEqual(
            pd.cf_flat_plate_turbulent(1e7), 0.0030037131, delta=1e-9
        )

    def test_turbulent_decreases_with_re(self):
        self.assertGreater(
            pd.cf_flat_plate_turbulent(1e6), pd.cf_flat_plate_turbulent(1e8)
        )

    def test_turbulent_edge_re_le_10_raises(self):
        for re in (10.0, 1.0, 0.0, -5.0):
            with self.assertRaises(ValueError):
                pd.cf_flat_plate_turbulent(re)

    def test_mixed_concrete(self):
        # Re = 1e7, transition at Re_tr = 5e5:
        # Cf = Cf_turb(Re) - (Re_tr/Re)*(Cf_turb(Re_tr) - Cf_lam(Re_tr)).
        self.assertAlmostEqual(
            pd.cf_flat_plate_mixed(1e7, 5e5), 0.0028423311, delta=1e-9
        )

    def test_mixed_between_limits(self):
        cf_lam = pd.cf_flat_plate_laminar(1e7)
        cf_turb = pd.cf_flat_plate_turbulent(1e7)
        cf_mixed = pd.cf_flat_plate_mixed(1e7, 5e5)
        self.assertGreater(cf_mixed, cf_lam)
        self.assertLess(cf_mixed, cf_turb)

    def test_mixed_invalid_transition_raises(self):
        with self.assertRaises(ValueError):
            pd.cf_flat_plate_mixed(1e7, 1e7)  # transition at or beyond Re
        with self.assertRaises(ValueError):
            pd.cf_flat_plate_mixed(1e7, 5.0)  # transition below log10 domain


class TestFormFactor(unittest.TestCase):
    def test_wing_concrete(self):
        # FF = 1 + 2*(t/c) + 100*(t/c)^4 at t/c = 0.12.
        self.assertAlmostEqual(pd.form_factor("wing", t_over_c=0.12), 1.260736)

    def test_tail_thin_airfoil(self):
        self.assertAlmostEqual(pd.form_factor("tail", t_over_c=0.10), 1.21)

    def test_fuselage_concrete(self):
        # FF = 1 + 60/(l/d)^3 + 0.0025*(l/d) at l/d = 8.
        self.assertAlmostEqual(pd.form_factor("fuselage", l_over_d=8.0), 1.1371875)

    def test_nacelle_concrete(self):
        # FF = 1 + 0.35/(l/d) at l/d = 3.
        self.assertAlmostEqual(
            pd.form_factor("nacelle", l_over_d=3.0), 1.1166666667, delta=1e-9
        )

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            pd.form_factor("landing-gear", t_over_c=0.12)

    def test_out_of_range_geometry_raises(self):
        with self.assertRaises(ValueError):
            pd.form_factor("wing", t_over_c=0.5)   # thickness/chord boundary
        with self.assertRaises(ValueError):
            pd.form_factor("wing", t_over_c=-0.1)
        with self.assertRaises(ValueError):
            pd.form_factor("fuselage", l_over_d=1.0)  # fineness ratio boundary
        with self.assertRaises(ValueError):
            pd.form_factor("nacelle", l_over_d=0.5)


class TestComponentBuildup(unittest.TestCase):
    def test_component_drag_concrete(self):
        # CD = Cf * FF * Q * S_wet / S_ref.
        self.assertAlmostEqual(
            pd.component_parasite_drag(0.003, 1.26, 1.1, 50.0, 20.0),
            0.010395,
        )

    def test_component_drag_scales_with_wetted_area(self):
        small = pd.component_parasite_drag(0.003, 1.26, 1.1, 25.0, 20.0)
        large = pd.component_parasite_drag(0.003, 1.26, 1.1, 50.0, 20.0)
        self.assertAlmostEqual(large, 2.0 * small)

    def test_component_drag_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pd.component_parasite_drag(0.0, 1.26, 1.1, 50.0, 20.0)   # cf <= 0
        with self.assertRaises(ValueError):
            pd.component_parasite_drag(0.003, 0.9, 1.1, 50.0, 20.0)  # ff < 1
        with self.assertRaises(ValueError):
            pd.component_parasite_drag(0.003, 1.26, 0.8, 50.0, 20.0)  # q < 1
        with self.assertRaises(ValueError):
            pd.component_parasite_drag(0.003, 1.26, 1.1, -5.0, 20.0)  # s_wet
        with self.assertRaises(ValueError):
            pd.component_parasite_drag(0.003, 1.26, 1.1, 50.0, 0.0)  # s_ref

    def test_total_is_sum(self):
        self.assertAlmostEqual(
            pd.total_parasite_drag([0.010395, 0.005]), 0.015395
        )

    def test_total_empty_list_is_zero(self):
        self.assertEqual(pd.total_parasite_drag([]), 0.0)

    def test_equivalent_skin_friction_concrete(self):
        # Cf_e = CD * S_ref / S_wet_total.
        self.assertAlmostEqual(
            pd.equivalent_skin_friction(0.015395, 20.0, 100.0), 0.003079
        )

    def test_equivalent_skin_friction_edge_raises(self):
        with self.assertRaises(ValueError):
            pd.equivalent_skin_friction(-0.1, 20.0, 100.0)  # cd < 0
        with self.assertRaises(ValueError):
            pd.equivalent_skin_friction(0.015395, 0.0, 100.0)  # s_ref = 0
        with self.assertRaises(ValueError):
            pd.equivalent_skin_friction(0.015395, 20.0, 0.0)  # no wetted area

    def test_wing_wetted_area_concrete(self):
        # S_wet = 2 * S_exposed * (1 + 0.2*t/c).
        self.assertAlmostEqual(pd.wing_wetted_area(16.0, 0.12), 32.768)

    def test_wing_wetted_area_edge_raises(self):
        with self.assertRaises(ValueError):
            pd.wing_wetted_area(0.0, 0.12)
        with self.assertRaises(ValueError):
            pd.wing_wetted_area(16.0, 0.5)


class TestEndToEndBuildup(unittest.TestCase):
    def test_typical_configuration(self):
        # Generic light aircraft: wing + fuselage + nacelle + tail.
        re_w = pd.reynolds_number(1.225, 70.0, 1.8, 1.7894e-5)
        cf_w = pd.cf_flat_plate_mixed(re_w, 5e5)
        ff_w = pd.form_factor("wing", t_over_c=0.14)
        cd_w = pd.component_parasite_drag(cf_w, ff_w, 1.1, 32.0, 16.0)

        ff_f = pd.form_factor("fuselage", l_over_d=7.0)
        cd_f = pd.component_parasite_drag(cf_w, ff_f, 1.0, 42.0, 16.0)

        ff_n = pd.form_factor("nacelle", l_over_d=3.0)
        cd_n = pd.component_parasite_drag(cf_w, ff_n, 1.2, 4.0, 16.0)

        ff_t = pd.form_factor("tail", t_over_c=0.10)
        cd_t = pd.component_parasite_drag(cf_w, ff_t, 1.05, 9.0, 16.0)

        total = pd.total_parasite_drag([cd_w, cd_f, cd_n, cd_t])
        self.assertAlmostEqual(total, cd_w + cd_f + cd_n + cd_t)
        # Every component is a positive drag increment; the wing dominates
        # but the total exceeds any single component.
        self.assertGreater(total, cd_w)
        self.assertGreater(cd_w, 0.0)
        # Equivalent skin friction of the whole configuration sits in the
        # typical transport-aircraft band (0.0025-0.004).
        cfe = pd.equivalent_skin_friction(total, 16.0, 87.0)
        self.assertGreater(cfe, 0.0025)
        self.assertLess(cfe, 0.004)


if __name__ == "__main__":
    unittest.main(verbosity=2)
