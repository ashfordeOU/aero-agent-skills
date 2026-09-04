"""Contract test for thrust_chamber_cooling_logic (wave-34).

Offline deterministic stdlib unittest. Run from the leaf directory:

    python3 scripts/test_thrust_chamber_cooling.py
"""

import math
import unittest

from thrust_chamber_cooling_logic import (
    adiabatic_wall_temperature,
    bartz_hot_gas_coefficient,
    chamber_cooling_summary,
    chamber_mass_flow,
    coolant_mass_flux_for_wall_limit,
    coolant_side_coefficient,
    film_cooling_handoff,
    throat_area,
    wall_heat_flux,
)

# Worked example: LOX/RP-1 subscale chamber, Pc 7.0 MPa, c-star 1750 m/s,
# Tc 3500 K, gamma 1.2, Dt 0.15 m, Pr_g 0.72, mu_g 8.0e-5, cp_g 2000;
# RP-1 coolant 300 K in channels D_h 2 mm, G_c 12000 kg/m2 s, mu_c 0.0022,
# cp_c 2000, k_c 0.13; copper wall 1.5 mm, k_w 390, limit 800 K.
PC = 7.0e6
CSTAR = 1750.0
TC = 3500.0
GAMMA = 1.2
DT = 0.15
PR_G = 0.72
MU_G = 8.0e-5
CP_G = 2000.0
GC = 12000.0
DH = 0.002
MU_C = 0.0022
CP_C = 2000.0
K_C = 0.13
TW = 0.0015
KW = 390.0
TCOOL = 300.0
TLIMIT = 800.0

COOLANT_PROPS = {
    "hydraulic_diameter_m": DH,
    "mu_c": MU_C,
    "cp_c": CP_C,
    "k_c": K_C,
}


def _rel(actual, expected, tol):
    return abs(actual - expected) <= tol * abs(expected)


class ThroatAreaTests(unittest.TestCase):
    def test_throat_area_worked_case(self):
        at = throat_area(DT)
        self.assertTrue(_rel(at, math.pi * DT ** 2 / 4.0, 1e-12))
        self.assertTrue(_rel(at, 0.017671, 1e-3),
                        "throat area must sit in the 0.017671 m2 band")

    def test_throat_area_raises_non_positive(self):
        for bad in (0.0, -0.5, -2.0):
            with self.subTest(diameter=bad):
                with self.assertRaises(ValueError):
                    throat_area(bad)


class MassFlowTests(unittest.TestCase):
    def test_mass_flow_worked_case(self):
        at = throat_area(DT)
        mdot = chamber_mass_flow(PC, at, CSTAR)
        self.assertTrue(_rel(mdot, 70.6858, 1e-3),
                        "worked mass flow must match 70.6858 kg/s to 1e-3")
        self.assertTrue(_rel(mdot, PC * at / CSTAR, 1e-12))

    def test_mass_flow_pressure_scaling(self):
        at = throat_area(DT)
        base = chamber_mass_flow(PC, at, CSTAR)
        doubled = chamber_mass_flow(2.0 * PC, at, CSTAR)
        self.assertTrue(_rel(doubled, 2.0 * base, 1e-12))

    def test_mass_flow_raises_non_positive(self):
        at = throat_area(DT)
        cases = [(0.0, at, CSTAR), (-PC, at, CSTAR),
                 (PC, 0.0, CSTAR), (PC, -at, CSTAR),
                 (PC, at, 0.0), (PC, at, -CSTAR)]
        for args in cases:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    chamber_mass_flow(*args)


class AdiabaticWallTemperatureTests(unittest.TestCase):
    def test_throat_static_and_recovery(self):
        aw = adiabatic_wall_temperature(TC, GAMMA, PR_G)
        self.assertTrue(_rel(aw["throat_static_temp_k"], TC / 1.1, 1e-9),
                        "T_t must equal Tc/1.1 at gamma 1.2")
        self.assertTrue(_rel(aw["recovery_temp_k"], 3467.0, 5e-4),
                        "T_aw must sit in the 3467.00 K band")
        self.assertTrue(aw["throat_static_temp_k"] < aw["recovery_temp_k"])
        self.assertTrue(aw["recovery_temp_k"] < TC)
        self.assertTrue(_rel(aw["throat_static_temp_k"], 3181.82, 1e-4))
        self.assertEqual(adiabatic_wall_temperature(TC, GAMMA),
                         adiabatic_wall_temperature(TC, GAMMA, 0.72))

    def test_raises_non_physical(self):
        cases = [(0.0, GAMMA, PR_G), (-TC, GAMMA, PR_G),
                 (TC, 1.0, PR_G), (TC, 0.9, PR_G),
                 (TC, GAMMA, 0.0), (TC, GAMMA, -1.0)]
        for args in cases:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    adiabatic_wall_temperature(*args)


class BartzCoefficientTests(unittest.TestCase):
    def test_worked_value(self):
        hg = bartz_hot_gas_coefficient(PC, CSTAR, DT, MU_G, CP_G, PR_G)
        self.assertTrue(_rel(hg, 10682.0, 1e-2),
                        "worked h_g must sit in the 10682 W/m2K band")
        self.assertTrue(_rel(hg, 10681.975669269419, 1e-9))

    def test_pressure_scaling(self):
        base = bartz_hot_gas_coefficient(PC, CSTAR, DT, MU_G, CP_G, PR_G)
        raised = bartz_hot_gas_coefficient(
            2.0 * PC, CSTAR, DT, MU_G, CP_G, PR_G)
        self.assertTrue(_rel(raised, base * 2.0 ** 0.8, 1e-9),
                        "h_g must scale as Pc^0.8")

    def test_diameter_scaling(self):
        base = bartz_hot_gas_coefficient(PC, CSTAR, DT, MU_G, CP_G, PR_G)
        bigger = bartz_hot_gas_coefficient(
            PC, CSTAR, 2.0 * DT, MU_G, CP_G, PR_G)
        self.assertTrue(_rel(bigger, base * 2.0 ** -0.2, 1e-9),
                        "h_g must scale as Dt^-0.2")

    def test_sigma_scaling_linear(self):
        base = bartz_hot_gas_coefficient(PC, CSTAR, DT, MU_G, CP_G, PR_G)
        scaled = bartz_hot_gas_coefficient(
            PC, CSTAR, DT, MU_G, CP_G, PR_G, sigma=2.0)
        self.assertTrue(_rel(scaled, 2.0 * base, 1e-9))
        half = bartz_hot_gas_coefficient(
            PC, CSTAR, DT, MU_G, CP_G, PR_G, sigma=0.5)
        self.assertTrue(_rel(half, 0.5 * base, 1e-9))

    def test_raises_non_positive(self):
        cases = [(0.0, CSTAR, DT, MU_G, CP_G, PR_G),
                 (PC, 0.0, DT, MU_G, CP_G, PR_G),
                 (PC, CSTAR, 0.0, MU_G, CP_G, PR_G),
                 (PC, CSTAR, DT, 0.0, CP_G, PR_G),
                 (PC, CSTAR, DT, MU_G, 0.0, PR_G),
                 (PC, CSTAR, DT, MU_G, CP_G, 0.0)]
        for args in cases:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    bartz_hot_gas_coefficient(*args)

    def test_raises_sigma_non_positive(self):
        for sigma in (0.0, -1.0):
            with self.subTest(sigma=sigma):
                with self.assertRaises(ValueError):
                    bartz_hot_gas_coefficient(
                        PC, CSTAR, DT, MU_G, CP_G, PR_G, sigma=sigma)


class CoolantSideTests(unittest.TestCase):
    def test_worked_values(self):
        cs = coolant_side_coefficient(GC, DH, MU_C, CP_C, K_C)
        self.assertTrue(_rel(cs["reynolds"], 10909.1, 1e-4),
                        "Re must sit in the 10909.1 band")
        self.assertTrue(_rel(cs["prandtl"], 33.85, 1e-3),
                        "Pr must sit in the 33.85 band")
        self.assertTrue(_rel(cs["nusselt"], 159.87, 1e-3),
                        "Nu must sit in the 159.87 band")
        self.assertTrue(_rel(cs["h_c"], 10391.4, 1e-3),
                        "h_c must sit in the 10391.4 W/m2K band")
        self.assertTrue(_rel(cs["reynolds"], GC * DH / MU_C, 1e-12))
        self.assertTrue(_rel(cs["prandtl"], CP_C * MU_C / K_C, 1e-12))
        self.assertEqual(set(cs.keys()),
                         {"h_c", "reynolds", "nusselt", "prandtl"})

    def test_nusselt_closed_form(self):
        cs = coolant_side_coefficient(GC, DH, MU_C, CP_C, K_C)
        expected = 0.023 * cs["reynolds"] ** 0.8 * cs["prandtl"] ** 0.4
        self.assertTrue(_rel(cs["nusselt"], expected, 1e-12))

    def test_h_from_nusselt(self):
        cs = coolant_side_coefficient(GC, DH, MU_C, CP_C, K_C)
        expected = cs["nusselt"] * K_C / DH
        self.assertTrue(_rel(cs["h_c"], expected, 1e-12))

    def test_mass_flux_scaling(self):
        base = coolant_side_coefficient(GC, DH, MU_C, CP_C, K_C)
        doubled = coolant_side_coefficient(2.0 * GC, DH, MU_C, CP_C, K_C)
        self.assertTrue(_rel(doubled["h_c"], base["h_c"] * 2.0 ** 0.8, 1e-9),
                        "h_c must scale as G^0.8 through Re^0.8")

    def test_raises_non_positive(self):
        cases = [(0.0, DH, MU_C, CP_C, K_C),
                 (GC, 0.0, MU_C, CP_C, K_C),
                 (GC, DH, 0.0, CP_C, K_C),
                 (GC, DH, MU_C, 0.0, K_C),
                 (GC, DH, MU_C, CP_C, 0.0)]
        for args in cases:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    coolant_side_coefficient(*args)

class WallHeatFluxTests(unittest.TestCase):
    def _worked(self):
        hg = bartz_hot_gas_coefficient(PC, CSTAR, DT, MU_G, CP_G, PR_G)
        cs = coolant_side_coefficient(GC, DH, MU_C, CP_C, K_C)
        aw = adiabatic_wall_temperature(TC, GAMMA, PR_G)
        return wall_heat_flux(
            hg, cs["h_c"], TW, KW, aw["recovery_temp_k"], TCOOL)

    def test_worked_values(self):
        wf = self._worked()
        self.assertTrue(_rel(wf["heat_flux_wm2"], 16.35e6, 1e-3),
                        "q must sit in the 16.350 MW/m2 band")
        self.assertTrue(_rel(wf["heat_flux_wm2"], 16350453.537071193, 1e-9))
        self.assertTrue(abs(wf["hot_wall_temp_k"] - 1936.3) < 0.1,
                        "T_wg must sit in the 1936.3 K band")
        self.assertTrue(abs(wf["cold_wall_temp_k"] - 1873.5) < 0.1,
                        "T_wc must sit in the 1873.5 K band")
        self.assertTrue(abs(wf["wall_delta_temp_k"] - 62.9) < 0.1,
                        "wall dT must sit in the 62.9 K band")
        self.assertEqual(
            set(wf.keys()),
            {"heat_flux_wm2", "hot_wall_temp_k", "cold_wall_temp_k",
             "wall_delta_temp_k"})

    def test_series_network_identity(self):
        wf = self._worked()
        hg = bartz_hot_gas_coefficient(PC, CSTAR, DT, MU_G, CP_G, PR_G)
        cs = coolant_side_coefficient(GC, DH, MU_C, CP_C, K_C)
        aw = adiabatic_wall_temperature(TC, GAMMA, PR_G)
        r_total = 1.0 / hg + TW / KW + 1.0 / cs["h_c"]
        expected_q = (aw["recovery_temp_k"] - TCOOL) / r_total
        self.assertTrue(_rel(wf["heat_flux_wm2"], expected_q, 1e-12))

    def test_wall_delta_identity(self):
        wf = self._worked()
        lhs = wf["hot_wall_temp_k"] - wf["cold_wall_temp_k"]
        rhs = wf["heat_flux_wm2"] * TW / KW
        self.assertTrue(_rel(lhs, rhs, 1e-9),
                        "T_wg - T_wc must equal q t_w/k_w")

    def test_ordering(self):
        wf = self._worked()
        self.assertTrue(wf["cold_wall_temp_k"] > TCOOL)
        self.assertTrue(wf["hot_wall_temp_k"] < 3466.998483871819)
        self.assertTrue(wf["hot_wall_temp_k"] > wf["cold_wall_temp_k"])

    def test_raises_non_positive(self):
        cases = [(0.0, 5000.0, TW, KW, 2000.0, TCOOL),
                 (5000.0, 0.0, TW, KW, 2000.0, TCOOL),
                 (5000.0, 5000.0, 0.0, KW, 2000.0, TCOOL),
                 (5000.0, 5000.0, TW, 0.0, 2000.0, TCOOL),
                 (5000.0, 5000.0, TW, KW, 0.0, TCOOL),
                 (5000.0, 5000.0, TW, KW, 2000.0, 0.0)]
        for args in cases:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    wall_heat_flux(*args)

class FilmCoolingHandoffTests(unittest.TestCase):
    def _hot_wall(self, coolant_flux):
        hg = bartz_hot_gas_coefficient(PC, CSTAR, DT, MU_G, CP_G, PR_G)
        cs = coolant_side_coefficient(
            coolant_flux, DH, MU_C, CP_C, K_C)
        aw = adiabatic_wall_temperature(TC, GAMMA, PR_G)
        return wall_heat_flux(
            hg, cs["h_c"], TW, KW, aw["recovery_temp_k"], TCOOL)

    def test_worked_case_true(self):
        hot = self._hot_wall(GC)["hot_wall_temp_k"]
        self.assertTrue(hot > TLIMIT)
        self.assertTrue(film_cooling_handoff(hot, TLIMIT),
                        "plain regenerative flow cannot hold the 800 K limit")

    def test_high_mass_flux_false(self):
        hot = self._hot_wall(200000.0)["hot_wall_temp_k"]
        self.assertTrue(hot < TLIMIT)
        self.assertFalse(film_cooling_handoff(hot, TLIMIT))

    def test_raises_non_positive(self):
        for args in [(0.0, TLIMIT), (1936.0, 0.0), (-5.0, TLIMIT),
                     (1936.0, -1.0)]:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    film_cooling_handoff(*args)


class WallLimitMassFluxTests(unittest.TestCase):
    def _required(self):
        hg = bartz_hot_gas_coefficient(PC, CSTAR, DT, MU_G, CP_G, PR_G)
        aw = adiabatic_wall_temperature(TC, GAMMA, PR_G)
        return coolant_mass_flux_for_wall_limit(
            hg, TW, KW, aw["recovery_temp_k"], TCOOL, TLIMIT,
            COOLANT_PROPS)

    def test_worked_values(self):
        req = self._required()
        self.assertTrue(_rel(req["required_h_c"], 72968.0, 1e-3),
                        "required h_c must sit in the 72968 W/m2K band")
        self.assertTrue(_rel(req["required_reynolds"], 124698.0, 1e-3),
                        "required Re must sit in the 124698 band")
        self.assertTrue(_rel(req["required_mass_flux"], 137168.0, 1e-3),
                        "required G must sit in the 137168 kg/m2s band")
        self.assertTrue(_rel(req["required_h_c"], 72968.22715310067, 1e-9))
        self.assertEqual(set(req.keys()),
                         {"required_h_c", "required_reynolds",
                          "required_mass_flux"})

    def test_round_trip_through_coolant_correlation(self):
        req = self._required()
        cs = coolant_side_coefficient(
            req["required_mass_flux"], DH, MU_C, CP_C, K_C)
        self.assertTrue(_rel(cs["h_c"], req["required_h_c"], 1e-6),
                        "feeding the required mass flux back through "
                        "Dittus-Boelter must recover the required h_c")
        self.assertTrue(_rel(cs["reynolds"], req["required_reynolds"], 1e-9))

    def test_raises_wall_limit_at_or_above_recovery(self):
        hg = bartz_hot_gas_coefficient(PC, CSTAR, DT, MU_G, CP_G, PR_G)
        aw = adiabatic_wall_temperature(TC, GAMMA, PR_G)
        t_aw = aw["recovery_temp_k"]
        for bad_limit in (t_aw, t_aw + 500.0, 1.0e6):
            with self.subTest(limit=bad_limit):
                with self.assertRaises(ValueError):
                    coolant_mass_flux_for_wall_limit(
                        hg, TW, KW, t_aw, TCOOL, bad_limit, COOLANT_PROPS)

    def test_raises_unreachable_low_limit(self):
        hg = bartz_hot_gas_coefficient(PC, CSTAR, DT, MU_G, CP_G, PR_G)
        aw = adiabatic_wall_temperature(TC, GAMMA, PR_G)
        t_aw = aw["recovery_temp_k"]
        for bad_limit in (TCOOL, 100.0, 350.0):
            with self.subTest(limit=bad_limit):
                with self.assertRaises(ValueError):
                    coolant_mass_flux_for_wall_limit(
                        hg, TW, KW, t_aw, TCOOL, bad_limit, COOLANT_PROPS)

    def test_raises_non_positive_props(self):
        hg = bartz_hot_gas_coefficient(PC, CSTAR, DT, MU_G, CP_G, PR_G)
        aw = adiabatic_wall_temperature(TC, GAMMA, PR_G)
        t_aw = aw["recovery_temp_k"]
        bad = dict(COOLANT_PROPS)
        bad["k_c"] = 0.0
        with self.assertRaises(ValueError):
            coolant_mass_flux_for_wall_limit(
                hg, TW, KW, t_aw, TCOOL, TLIMIT, bad)

class SummaryAndDeterminismTests(unittest.TestCase):
    def _summary(self):
        return chamber_cooling_summary(
            PC, CSTAR, TC, GAMMA, DT, PR_G, MU_G, CP_G, GC, DH, MU_C,
            CP_C, K_C, TW, KW, TCOOL, TLIMIT)

    def test_summary_matches_individual_calls(self):
        s = self._summary()
        hg = bartz_hot_gas_coefficient(PC, CSTAR, DT, MU_G, CP_G, PR_G)
        cs = coolant_side_coefficient(GC, DH, MU_C, CP_C, K_C)
        aw = adiabatic_wall_temperature(TC, GAMMA, PR_G)
        wf = wall_heat_flux(
            hg, cs["h_c"], TW, KW, aw["recovery_temp_k"], TCOOL)
        self.assertTrue(_rel(s["throat_area_m2"], throat_area(DT), 1e-12))
        self.assertTrue(_rel(
            s["chamber_mass_flow_kg_s"],
            chamber_mass_flow(PC, throat_area(DT), CSTAR), 1e-12))
        self.assertTrue(_rel(s["h_g"], hg, 1e-12))
        self.assertTrue(_rel(s["h_c"], cs["h_c"], 1e-12))
        self.assertTrue(_rel(s["heat_flux_wm2"], wf["heat_flux_wm2"], 1e-12))
        self.assertTrue(_rel(
            s["hot_wall_temp_k"], wf["hot_wall_temp_k"], 1e-12))
        self.assertTrue(_rel(
            s["cold_wall_temp_k"], wf["cold_wall_temp_k"], 1e-12))

    def test_summary_keys_and_worked_handoff(self):
        s = self._summary()
        self.assertEqual(
            set(s.keys()),
            {"throat_area_m2", "chamber_mass_flow_kg_s",
             "throat_static_temp_k", "recovery_temp_k", "h_g", "h_c",
             "reynolds", "nusselt", "prandtl", "heat_flux_wm2",
             "hot_wall_temp_k", "cold_wall_temp_k", "wall_delta_temp_k",
             "film_cooling_handoff", "required_h_c", "required_reynolds",
             "required_mass_flux"})
        self.assertTrue(s["film_cooling_handoff"])
        self.assertTrue(_rel(s["required_mass_flux"], 137168.0, 1e-3))
        self.assertTrue(_rel(s["recovery_temp_k"], 3467.0, 5e-4))

    def test_determinism(self):
        first = self._summary()
        second = self._summary()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
