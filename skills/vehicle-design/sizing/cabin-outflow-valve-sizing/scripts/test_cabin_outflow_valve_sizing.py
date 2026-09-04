"""Contract test for cabin outflow and pressure-relief valve sizing.

Offline deterministic stdlib unittest; run with:
    python3 scripts/test_cabin_outflow_valve_sizing.py
"""

import math
import unittest

import cabin_outflow_valve_sizing_logic as covs


class TestChokedMassFlux(unittest.TestCase):
    """Choked-flow mass flux G = p sqrt(g/(R T)) (2/(g+1))**((g+1)/(2(g-1)))."""

    def test_flux_cruise_worked_example(self):
        # 39,000 ft cruise, p_cab 75262 Pa, t_cab 288 K: G ~= 179.2499.
        flux = covs.choked_mass_flux(75262.0)
        self.assertAlmostEqual(flux, 179.2499, places=3)
        self.assertLess(abs(flux - 179.2499), 1e-2)

    def test_flux_relief_worked_example(self):
        # Relief ceiling p_cab = 11597 + 61363 = 72960 Pa: G ~= 173.7672.
        flux = covs.choked_mass_flux(72960.0)
        self.assertAlmostEqual(flux, 173.7672, places=3)
        self.assertLess(abs(flux - 173.7672), 1e-2)

    def test_flux_identity_closed_form(self):
        # G / (p sqrt(g/(R T))) must equal (2/(g+1))**((g+1)/(2(g-1)))
        # = 0.578704 within 1e-6.
        p, t = 75262.0, 288.0
        flux = covs.choked_mass_flux(p, t)
        ratio = flux / (p * math.sqrt(covs.GAMMA_AIR / (covs.R_AIR * t)))
        self.assertAlmostEqual(ratio, 0.578704, places=6)
        self.assertAlmostEqual(covs.FLUX_FACTOR, 0.578704, places=6)

    def test_flux_scales_linearly_with_pressure(self):
        g1 = covs.choked_mass_flux(50000.0)
        g2 = covs.choked_mass_flux(100000.0)
        self.assertAlmostEqual(g2 / g1, 2.0, places=9)

    def test_flux_temperature_dependence_and_default(self):
        # Higher cabin temperature lowers the flux; the default is 288 K.
        g_cold = covs.choked_mass_flux(75262.0, 273.15)
        g_hot = covs.choked_mass_flux(75262.0, 303.15)
        self.assertGreater(g_cold, g_hot)
        self.assertEqual(
            covs.choked_mass_flux(75262.0),
            covs.choked_mass_flux(75262.0, covs.T_CABIN_DEFAULT),
        )

    def test_flux_nonpositive_pressure_raises(self):
        with self.assertRaises(ValueError):
            covs.choked_mass_flux(0.0)
        with self.assertRaises(ValueError):
            covs.choked_mass_flux(-100.0)

    def test_flux_nonpositive_temperature_raises(self):
        with self.assertRaises(ValueError):
            covs.choked_mass_flux(75262.0, 0.0)
        with self.assertRaises(ValueError):
            covs.choked_mass_flux(75262.0, -5.0)


class TestIsChoked(unittest.TestCase):
    """Pressure-ratio choked check, strict at the critical ratio."""

    def test_choked_at_cruise_ratio(self):
        # p_amb/p_cab = 19677/75262 = 0.2614 < 0.528 -> choked.
        self.assertTrue(covs.is_choked(75262.0, 19677.0))
        self.assertAlmostEqual(19677.0 / 75262.0, 0.2614, places=4)
        self.assertTrue(covs.is_choked(1.0, 0.2614))

    def test_not_choked_at_high_ratio(self):
        # p_amb/p_cab = 0.7 > 0.528 -> not choked.
        self.assertFalse(covs.is_choked(1.0, 0.7))
        self.assertFalse(covs.is_choked(100000.0, 70000.0))

    def test_threshold_strict_at_critical_ratio(self):
        # A ratio exactly at the critical ratio (0.52828) is NOT choked;
        # just below it is choked, just above is not.
        self.assertFalse(covs.is_choked(1.0, covs.CRITICAL_RATIO))
        self.assertTrue(covs.is_choked(1.0, covs.CRITICAL_RATIO - 1e-6))
        self.assertFalse(covs.is_choked(1.0, covs.CRITICAL_RATIO + 1e-6))

    def test_critical_ratio_constant_value(self):
        # (2/(g+1))**(g/(g-1)) for g = 1.4.
        self.assertAlmostEqual(covs.CRITICAL_RATIO, 0.528282, places=5)

    def test_is_choked_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            covs.is_choked(0.0, 101325.0)
        with self.assertRaises(ValueError):
            covs.is_choked(-1.0, 101325.0)
        with self.assertRaises(ValueError):
            covs.is_choked(75262.0, -10.0)


class TestValveArea(unittest.TestCase):
    """Effective area A = m_dot / G and equivalent diameter D = sqrt(4A/pi)."""

    def test_valve_area_and_diameter_cruise(self):
        area = covs.valve_area(3.156617, 75262.0)
        self.assertAlmostEqual(area["area_m2"], 0.017610, places=6)
        self.assertLess(abs(area["area_m2"] - 0.017610), 1e-5)
        self.assertAlmostEqual(area["diameter_m"], 0.1497, places=3)
        self.assertLess(abs(area["diameter_m"] - 0.1497), 1e-3)

    def test_area_round_trip_through_diameter(self):
        # pi * (D/2)^2 must recover the effective area.
        area = covs.valve_area(3.156617, 75262.0)
        recovered = math.pi * (area["diameter_m"] / 2.0) ** 2
        self.assertAlmostEqual(recovered, area["area_m2"], places=9)

    def test_area_scales_with_mass_flow(self):
        a1 = covs.valve_area(1.0, 75262.0)["area_m2"]
        a2 = covs.valve_area(2.0, 75262.0)["area_m2"]
        self.assertAlmostEqual(a2 / a1, 2.0, places=9)

    def test_valve_area_dict_keys(self):
        self.assertEqual(
            set(covs.valve_area(3.156617, 75262.0).keys()),
            {"area_m2", "diameter_m"},
        )

    def test_valve_area_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            covs.valve_area(0.0, 75262.0)
        with self.assertRaises(ValueError):
            covs.valve_area(-3.0, 75262.0)
        with self.assertRaises(ValueError):
            covs.valve_area(3.156617, 0.0)
        with self.assertRaises(ValueError):
            covs.valve_area(3.156617, 75262.0, 0.0)


class TestOutflowValveSizing(unittest.TestCase):
    """Outflow valve sized on the governing pack inflow at cruise."""

    def test_outflow_worked_example(self):
        out = covs.outflow_valve_sizing(3.156617, 75262.0, 19677.0, 0.16)
        self.assertTrue(out["choked"])
        self.assertAlmostEqual(out["mass_flux_kg_m2s"], 179.2499, places=3)
        self.assertAlmostEqual(out["area_m2"], 0.017610, places=6)
        self.assertLess(abs(out["area_m2"] - 0.017610), 1e-5)
        self.assertAlmostEqual(out["diameter_m"], 0.1497, places=3)
        self.assertLess(abs(out["diameter_m"] - 0.1497), 1e-3)
        self.assertEqual(out["fit_verdict"], "PASS")

    def test_outflow_fit_verdicts(self):
        # PASS against the 0.16 m nominal limit, FAIL against 0.14 m, and
        # PASS when the limit equals the sized diameter.
        self.assertEqual(
            covs.outflow_valve_sizing(3.156617, 75262.0, 19677.0, 0.16)[
                "fit_verdict"
            ],
            "PASS",
        )
        self.assertEqual(
            covs.outflow_valve_sizing(3.156617, 75262.0, 19677.0, 0.14)[
                "fit_verdict"
            ],
            "FAIL",
        )
        d = covs.valve_area(3.156617, 75262.0)["diameter_m"]
        self.assertEqual(
            covs.outflow_valve_sizing(3.156617, 75262.0, 19677.0, d)[
                "fit_verdict"
            ],
            "PASS",
        )

    def test_outflow_unchoked_raises(self):
        # p_amb/p_cab = 0.7 -> not choked -> ValueError.
        with self.assertRaises(ValueError):
            covs.outflow_valve_sizing(3.156617, 100000.0, 70000.0, 0.16)

    def test_outflow_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            covs.outflow_valve_sizing(0.0, 75262.0, 19677.0, 0.16)
        with self.assertRaises(ValueError):
            covs.outflow_valve_sizing(3.156617, 0.0, 19677.0, 0.16)
        with self.assertRaises(ValueError):
            covs.outflow_valve_sizing(3.156617, 75262.0, 19677.0, 0.0)
        with self.assertRaises(ValueError):
            covs.outflow_valve_sizing(3.156617, 75262.0, 19677.0, -0.1)

    def test_outflow_dict_keys(self):
        out = covs.outflow_valve_sizing(3.156617, 75262.0, 19677.0, 0.16)
        self.assertEqual(
            set(out.keys()),
            {
                "choked",
                "mass_flux_kg_m2s",
                "area_m2",
                "diameter_m",
                "fit_verdict",
            },
        )


class TestReliefValveSizing(unittest.TestCase):
    """Relief valve dumps the pack flow at the differential clamp ceiling."""

    def test_relief_worked_example(self):
        # p_cab = 11597 + 61363 = 72960 Pa at 50,000 ft.
        rel = covs.relief_valve_sizing(3.156617, 11597.0, 61363.0, 0.16)
        self.assertTrue(rel["choked"])
        self.assertAlmostEqual(rel["mass_flux_kg_m2s"], 173.7672, places=3)
        self.assertAlmostEqual(rel["area_m2"], 0.018166, places=6)
        self.assertLess(abs(rel["area_m2"] - 0.018166), 1e-5)
        self.assertAlmostEqual(rel["diameter_m"], 0.1521, places=3)
        self.assertLess(abs(rel["diameter_m"] - 0.1521), 1e-3)
        self.assertEqual(rel["fit_verdict"], "PASS")

    def test_relief_upstream_is_amb_plus_clamp(self):
        # The relief flux equals the choked flux at p_amb + dp_clamp, and
        # the pressure ratio 11597/72960 = 0.159 is choked.
        rel = covs.relief_valve_sizing(3.156617, 11597.0, 61363.0, 0.16)
        self.assertEqual(
            rel["mass_flux_kg_m2s"], covs.choked_mass_flux(72960.0)
        )
        self.assertAlmostEqual(11597.0 / 72960.0, 0.1590, places=4)
        self.assertTrue(covs.is_choked(72960.0, 11597.0))

    def test_relief_default_clamp_is_61363_pa(self):
        rel1 = covs.relief_valve_sizing(
            3.156617, 11597.0, max_valve_diameter_m=0.16
        )
        rel2 = covs.relief_valve_sizing(
            3.156617, 11597.0, covs.DP_CLAMP_DEFAULT, 0.16
        )
        self.assertEqual(rel1, rel2)
        self.assertEqual(covs.DP_CLAMP_DEFAULT, 61363.0)

    def test_relief_fit_verdicts(self):
        self.assertEqual(
            covs.relief_valve_sizing(3.156617, 11597.0, 61363.0, 0.16)[
                "fit_verdict"
            ],
            "PASS",
        )
        self.assertEqual(
            covs.relief_valve_sizing(3.156617, 11597.0, 61363.0, 0.14)[
                "fit_verdict"
            ],
            "FAIL",
        )

    def test_relief_unchoked_raises(self):
        # A tiny clamp gives p_amb/p_cab ~= 0.92 -> not choked.
        with self.assertRaises(ValueError):
            covs.relief_valve_sizing(3.156617, 11597.0, 1000.0, 0.16)

    def test_relief_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            covs.relief_valve_sizing(0.0, 11597.0, 61363.0, 0.16)
        with self.assertRaises(ValueError):
            covs.relief_valve_sizing(3.156617, -100.0, 61363.0, 0.16)
        with self.assertRaises(ValueError):
            covs.relief_valve_sizing(3.156617, 11597.0, 0.0, 0.16)
        with self.assertRaises(ValueError):
            covs.relief_valve_sizing(3.156617, 11597.0, -5000.0, 0.16)
        with self.assertRaises(ValueError):
            covs.relief_valve_sizing(3.156617, 11597.0, 61363.0)

    def test_relief_dict_keys(self):
        rel = covs.relief_valve_sizing(3.156617, 11597.0, 61363.0, 0.16)
        self.assertEqual(
            set(rel.keys()),
            {
                "choked",
                "mass_flux_kg_m2s",
                "area_m2",
                "diameter_m",
                "fit_verdict",
            },
        )

    def test_relief_area_exceeds_outflow_area(self):
        # The 50,000 ft relief ceiling has lower p_cab (72960 vs 75262),
        # so the same pack flow needs a larger relief effective area.
        rel = covs.relief_valve_sizing(3.156617, 11597.0, 61363.0, 0.16)
        out = covs.outflow_valve_sizing(3.156617, 75262.0, 19677.0, 0.16)
        self.assertGreater(rel["area_m2"], out["area_m2"])


class TestDeterminismAndAnchors(unittest.TestCase):
    """Offline determinism and module anchor constants."""

    def test_outflow_deterministic(self):
        r1 = covs.outflow_valve_sizing(3.156617, 75262.0, 19677.0, 0.16)
        r2 = covs.outflow_valve_sizing(3.156617, 75262.0, 19677.0, 0.16)
        self.assertEqual(r1, r2)

    def test_relief_deterministic(self):
        r1 = covs.relief_valve_sizing(3.156617, 11597.0, 61363.0, 0.16)
        r2 = covs.relief_valve_sizing(3.156617, 11597.0, 61363.0, 0.16)
        self.assertEqual(r1, r2)

    def test_module_anchor_constants(self):
        self.assertEqual(covs.GAMMA_AIR, 1.4)
        self.assertEqual(covs.R_AIR, 287.0)
        self.assertEqual(covs.T_CABIN_DEFAULT, 288.0)
        self.assertEqual(covs.P_AMB_39000FT, 19677.0)
        self.assertEqual(covs.P_AMB_50000FT, 11597.0)

    def test_flux_positive_at_isa_anchors(self):
        self.assertGreater(covs.choked_mass_flux(covs.P_AMB_39000FT), 0.0)
        self.assertGreater(covs.choked_mass_flux(covs.P_AMB_50000FT), 0.0)


if __name__ == "__main__":
    unittest.main()
