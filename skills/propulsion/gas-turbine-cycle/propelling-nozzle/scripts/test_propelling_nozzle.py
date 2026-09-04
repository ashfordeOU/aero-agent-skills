"""Contract test for the propelling-nozzle logic module.

Deterministic, offline, stdlib only. Run with:
    python3 scripts/test_propelling_nozzle.py
"""

import math
import unittest

import propelling_nozzle_logic as pn

# Worked example reference design point (spec): P0 = 300 kPa, T0 = 900 K,
# mdot = 70 kg/s, Pa = 101.325 kPa. Module real outputs used as targets.
P0_DESIGN = 300000.0
T0 = 900.0
MDOT = 70.0
P_AMB = 101325.0


class TestRegime(unittest.TestCase):
    def test_design_point_choked(self):
        regime = pn.nozzle_regime(P0_DESIGN, P_AMB)
        self.assertTrue(regime["choked"])
        self.assertAlmostEqual(regime["npr"], 2.9608, places=4)

    def test_off_design_unchoked(self):
        regime = pn.nozzle_regime(140000.0, P_AMB)
        self.assertFalse(regime["choked"])
        self.assertAlmostEqual(regime["npr"], 1.3817, places=4)

    def test_critical_ratio_value(self):
        # Critical ratio ((gamma+1)/2)^(gamma/(gamma-1)) = 1.851 at 1.33.
        self.assertAlmostEqual(pn.CRITICAL_RATIO, 1.851, delta=1e-3)
        self.assertGreater(pn.CRITICAL_RATIO, 1.0)

    def test_regime_dict_keys(self):
        self.assertEqual(
            set(pn.nozzle_regime(P0_DESIGN, P_AMB)),
            {"npr", "critical_ratio", "choked"},
        )

    def test_nonpositive_total_or_ambient_raises(self):
        for p0 in (0.0, -5.0):
            with self.assertRaises(ValueError):
                pn.nozzle_regime(p0, P_AMB)
        for p_amb in (0.0, -1.0):
            with self.assertRaises(ValueError):
                pn.nozzle_regime(P0_DESIGN, p_amb)

    def test_npr_at_or_below_one_raises(self):
        # npr = 1 (no expansion) and npr < 1 (back pressure) both raise.
        with self.assertRaises(ValueError):
            pn.nozzle_regime(P_AMB, P_AMB)
        with self.assertRaises(ValueError):
            pn.nozzle_regime(80000.0, P_AMB)


class TestThroatArea(unittest.TestCase):
    def test_throat_area_worked_example(self):
        # 70*sqrt(900)/(300000*sqrt(1.33/287)*0.5833) = 0.176305 m2.
        area = pn.throat_area(MDOT, P0_DESIGN, T0)
        self.assertAlmostEqual(area, 0.176305, delta=1e-5)

    def test_throat_area_scales_with_mass_flow(self):
        a1 = pn.throat_area(MDOT, P0_DESIGN, T0)
        a2 = pn.throat_area(2 * MDOT, P0_DESIGN, T0)
        self.assertAlmostEqual(a2 / a1, 2.0, places=12)

    def test_throat_area_inverse_sizing_roundtrip(self):
        # Sizing then re-evaluating the choked flow recovers the design
        # mass flow (closed-form identity).
        area = pn.throat_area(MDOT, P0_DESIGN, T0)
        choked_flow = (
            P0_DESIGN
            * area
            / math.sqrt(T0)
            * math.sqrt(pn.GAMMA / pn.R_GAS)
            * (2.0 / (pn.GAMMA + 1.0))
            ** ((pn.GAMMA + 1.0) / (2.0 * (pn.GAMMA - 1.0)))
        )
        self.assertAlmostEqual(choked_flow, MDOT, delta=1e-9)

    def test_throat_area_nonpositive_inputs_raise(self):
        for args in ((0.0, P0_DESIGN, T0), (-1.0, P0_DESIGN, T0),
                     (MDOT, 0.0, T0), (MDOT, P0_DESIGN, 0.0),
                     (MDOT, P0_DESIGN, -10.0)):
            with self.assertRaises(ValueError):
                pn.throat_area(*args)


class TestChokedExit(unittest.TestCase):
    def test_choked_exit_worked_example(self):
        state = pn.choked_exit_state(P0_DESIGN, T0)
        self.assertAlmostEqual(state["t_exit_k"], 772.5, delta=1e-1)
        self.assertAlmostEqual(state["v_exit_m_s"], 543.0, delta=1e-1)
        self.assertEqual(state["mach"], 1.0)
        self.assertAlmostEqual(state["t_exit_k"], 772.5322, delta=1e-3)

    def test_choked_exit_pe_magnitude(self):
        # Pe = 300000*(2/2.33)^(1.33/0.33) = 162109.2 Pa, magnitude 162.1 kPa.
        state = pn.choked_exit_state(P0_DESIGN, T0)
        self.assertAlmostEqual(state["p_exit_pa"], 162109.2053, delta=0.3)

    def test_choked_exit_identities(self):
        state = pn.choked_exit_state(250000.0, 1100.0)
        self.assertAlmostEqual(
            state["t_exit_k"], 1100.0 * 2.0 / (pn.GAMMA + 1.0), places=9
        )
        self.assertAlmostEqual(
            state["v_exit_m_s"],
            math.sqrt(pn.GAMMA * pn.R_GAS * state["t_exit_k"]),
            places=9,
        )
        self.assertAlmostEqual(
            state["p_exit_pa"],
            250000.0 * (2.0 / (pn.GAMMA + 1.0))
            ** (pn.GAMMA / (pn.GAMMA - 1.0)),
            places=6,
        )

    def test_choked_exit_keys_and_nonpositive_raises(self):
        self.assertEqual(
            set(pn.choked_exit_state(P0_DESIGN, T0)),
            {"t_exit_k", "v_exit_m_s", "p_exit_pa", "mach"},
        )
        for args in ((0.0, T0), (-2.0, T0), (P0_DESIGN, 0.0)):
            with self.assertRaises(ValueError):
                pn.choked_exit_state(*args)


class TestGrossThrust(unittest.TestCase):
    def test_gross_thrust_worked_example(self):
        # Fg = 70*543.02 + (162109.2-101325)*0.176305 = 48728.7 N.
        exit_state = pn.choked_exit_state(P0_DESIGN, T0)
        area = pn.throat_area(MDOT, P0_DESIGN, T0)
        thrust = pn.gross_thrust(
            MDOT, exit_state["v_exit_m_s"], exit_state["p_exit_pa"],
            P_AMB, area,
        )
        self.assertAlmostEqual(thrust, 48728.7, delta=1e-1)

    def test_fully_expanded_identity(self):
        # With Pe == Pa the pressure term vanishes: Fg = mdot*Ve.
        thrust = pn.gross_thrust(MDOT, 543.0315, P_AMB, P_AMB, 0.176305)
        self.assertAlmostEqual(thrust, MDOT * 543.0315, places=6)

    def test_gross_thrust_scales_with_mass_flow(self):
        t1 = pn.gross_thrust(MDOT, 543.0, 162109.0, P_AMB, 0.176305)
        t2 = pn.gross_thrust(2 * MDOT, 543.0, 162109.0, P_AMB, 0.176305)
        self.assertAlmostEqual(t2 - t1, MDOT * 543.0, places=3)

    def test_gross_thrust_invalid_inputs_raise(self):
        bad = (
            (0.0, 543.0, 162109.0, P_AMB, 0.176305),   # mdot <= 0
            (-2.0, 543.0, 162109.0, P_AMB, 0.176305),  # mdot <= 0
            (MDOT, -1.0, 162109.0, P_AMB, 0.176305),   # v_exit < 0
            (MDOT, 543.0, 0.0, P_AMB, 0.176305),       # p_exit <= 0
            (MDOT, 543.0, 162109.0, 0.0, 0.176305),    # p_amb <= 0
            (MDOT, 543.0, 162109.0, P_AMB, 0.0),       # area <= 0
        )
        for args in bad:
            with self.assertRaises(ValueError):
                pn.gross_thrust(*args)


class TestUnchokedExit(unittest.TestCase):
    def test_unchoked_exit_worked_example(self):
        # Off-design P0 = 140 kPa: NPR = 1.382 < 1.851, Me = 0.7115,
        # Ve = 400.6 m/s.
        state = pn.unchoked_exit_state(140000.0, P_AMB, T0)
        self.assertAlmostEqual(state["mach"], 0.7115, delta=1e-3)
        self.assertAlmostEqual(state["v_exit_m_s"], 400.6, delta=1e-1)
        self.assertEqual(
            set(state), {"mach", "t_exit_k", "v_exit_m_s"}
        )

    def test_unchoked_mach_satisfies_relation(self):
        # NPR = (1+(gamma-1)/2 Me^2)^(gamma/(gamma-1)) must hold exactly.
        state = pn.unchoked_exit_state(140000.0, P_AMB, T0)
        npr = 140000.0 / P_AMB
        lhs = 1.0 + (pn.GAMMA - 1.0) / 2.0 * state["mach"] ** 2
        self.assertAlmostEqual(
            lhs, npr ** ((pn.GAMMA - 1.0) / pn.GAMMA), places=9
        )

    def test_unchoked_exit_at_choked_npr_raises(self):
        # Calling the unchoked exit state at a choked NPR must raise.
        with self.assertRaises(ValueError):
            pn.unchoked_exit_state(P0_DESIGN, P_AMB, T0)
        with self.assertRaises(ValueError):
            pn.unchoked_exit_state(140000.0, P_AMB, 0.0)


class TestUnchokedMassFlow(unittest.TestCase):
    def test_unchoked_flow_worked_example(self):
        # The sized throat passes 30.02 kg/s at the 140 kPa off-design
        # point (spec magnitude 30.0 kg/s).
        area = pn.throat_area(MDOT, P0_DESIGN, T0)
        flow = pn.unchoked_mass_flow(area, 140000.0, T0, P_AMB)
        self.assertAlmostEqual(flow, 30.0214, delta=1e-2)

    def test_unchoked_flow_scales_with_area(self):
        area = pn.throat_area(MDOT, P0_DESIGN, T0)
        f1 = pn.unchoked_mass_flow(area, 140000.0, T0, P_AMB)
        f2 = pn.unchoked_mass_flow(2 * area, 140000.0, T0, P_AMB)
        self.assertAlmostEqual(f2 / f1, 2.0, places=12)

    def test_unchoked_flow_at_choked_npr_raises(self):
        area = pn.throat_area(MDOT, P0_DESIGN, T0)
        with self.assertRaises(ValueError):
            pn.unchoked_mass_flow(area, P0_DESIGN, T0, P_AMB)
        with self.assertRaises(ValueError):
            pn.unchoked_mass_flow(0.0, 140000.0, T0, P_AMB)

    def test_unchoked_flow_continuity_at_critical(self):
        # The unchoked and choked relations meet at the critical ratio:
        # continuous within 1e-3 relative.
        area = pn.throat_area(MDOT, P0_DESIGN, T0)
        p0 = P_AMB * pn.CRITICAL_RATIO * 0.9999
        unchoked = pn.unchoked_mass_flow(area, p0, T0, P_AMB)
        choked_ref = MDOT * p0 / P0_DESIGN
        self.assertAlmostEqual(unchoked / choked_ref, 1.0, delta=1e-3)


class TestNozzleSizing(unittest.TestCase):
    def test_sizing_worked_example(self):
        result = pn.nozzle_sizing(MDOT, P0_DESIGN, T0, P_AMB)
        self.assertEqual(
            set(result),
            {"regime", "throat_area_m2", "exit_state", "gross_thrust_n",
             "expansion_verdict"},
        )
        self.assertTrue(result["regime"]["choked"])
        self.assertAlmostEqual(result["throat_area_m2"], 0.176305, delta=1e-5)
        self.assertAlmostEqual(
            result["exit_state"]["t_exit_k"], 772.5, delta=1e-1
        )
        self.assertAlmostEqual(
            result["exit_state"]["v_exit_m_s"], 543.0, delta=1e-1
        )
        self.assertAlmostEqual(
            result["exit_state"]["p_exit_pa"], 162109.2053, delta=0.3
        )
        self.assertAlmostEqual(result["gross_thrust_n"], 48728.7, delta=1e-1)
        self.assertEqual(result["expansion_verdict"], "PRESSURE_TERM_ACTIVE")

    def test_sizing_fully_expanded_verdict(self):
        # At the critical ratio the exit equals ambient: verdict flips to
        # FULLY_EXPANDED and gross thrust reduces to mdot*Ve. The p_amb
        # nudge (1e-12 relative) keeps the float npr clearly choked.
        p_exit = pn.choked_exit_state(P0_DESIGN, T0)["p_exit_pa"]
        result = pn.nozzle_sizing(
            MDOT, P0_DESIGN, T0, p_exit * (1.0 - 1e-12)
        )
        self.assertEqual(result["expansion_verdict"], "FULLY_EXPANDED")
        self.assertAlmostEqual(
            result["gross_thrust_n"], MDOT * 543.0315, delta=1e-1
        )

    def test_sizing_unchoked_design_raises(self):
        with self.assertRaises(ValueError):
            pn.nozzle_sizing(MDOT, 140000.0, T0, P_AMB)

    def test_sizing_invalid_inputs_raise(self):
        for args in ((0.0, P0_DESIGN, T0, P_AMB),
                     (-1.0, P0_DESIGN, T0, P_AMB),
                     (MDOT, 0.0, T0, P_AMB),
                     (MDOT, P0_DESIGN, 0.0, P_AMB)):
            with self.assertRaises(ValueError):
                pn.nozzle_sizing(*args)


class TestOffDesign(unittest.TestCase):
    def test_off_design_worked_example(self):
        area = pn.throat_area(MDOT, P0_DESIGN, T0)
        result = pn.off_design_nozzle(area, 140000.0, T0, P_AMB)
        self.assertEqual(
            set(result),
            {"regime", "mach", "v_exit_m_s", "actual_mass_flow_kg_s"},
        )
        self.assertFalse(result["regime"]["choked"])
        self.assertAlmostEqual(result["mach"], 0.7115, delta=1e-3)
        self.assertAlmostEqual(result["v_exit_m_s"], 400.6, delta=1e-1)
        self.assertAlmostEqual(
            result["actual_mass_flow_kg_s"], 30.0214, delta=1e-2
        )

    def test_off_design_choked_or_bad_area_raises(self):
        area = pn.throat_area(MDOT, P0_DESIGN, T0)
        with self.assertRaises(ValueError):
            pn.off_design_nozzle(area, P0_DESIGN, T0, P_AMB)
        with self.assertRaises(ValueError):
            pn.off_design_nozzle(0.0, 140000.0, T0, P_AMB)

    def test_off_design_consistency(self):
        # Reported mach, velocity and flow must agree with the standalone
        # unchoked functions.
        area = pn.throat_area(MDOT, P0_DESIGN, T0)
        result = pn.off_design_nozzle(area, 140000.0, T0, P_AMB)
        state = pn.unchoked_exit_state(140000.0, P_AMB, T0)
        flow = pn.unchoked_mass_flow(area, 140000.0, T0, P_AMB)
        self.assertEqual(result["mach"], state["mach"])
        self.assertEqual(result["v_exit_m_s"], state["v_exit_m_s"])
        self.assertEqual(
            result["actual_mass_flow_kg_s"], flow
        )


class TestRobustness(unittest.TestCase):
    def test_determinism(self):
        self.assertEqual(
            pn.nozzle_sizing(MDOT, P0_DESIGN, T0, P_AMB),
            pn.nozzle_sizing(MDOT, P0_DESIGN, T0, P_AMB),
        )
        area = pn.throat_area(MDOT, P0_DESIGN, T0)
        self.assertEqual(
            pn.off_design_nozzle(area, 140000.0, T0, P_AMB),
            pn.off_design_nozzle(area, 140000.0, T0, P_AMB),
        )

    def test_module_constants(self):
        self.assertEqual(pn.GAMMA, 1.33)
        self.assertEqual(pn.R_GAS, 287.0)
        self.assertEqual(pn.P_AMB_DEFAULT, 101325.0)


if __name__ == "__main__":
    unittest.main()
