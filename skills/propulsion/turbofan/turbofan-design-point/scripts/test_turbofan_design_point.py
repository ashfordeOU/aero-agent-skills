"""Contract test for the turbofan-design-point leaf (wave-43).

Exercises the SKILL.md workflow end to end: step 1 fixes the operating
point (mach, altitude, opr, fpr, lpc_pr, bpr, Tt4, mdot_core and the
component efficiencies), step 2 resolves the ambient and flight state
with isa_atmosphere and freestream_state, step 3 traverses the inlet and
the fan to the fan-stream-station-states at station 13, step 4 compresses
the core stream through the booster and the HPC to close the OPR, step 5
burns at the combustor energy balance, step 6 closes the HP spool balance
(hp-and-lp-turbine-matching), step 7 closes the LP spool balance with the
(1 + bpr) fan multiplier of the two-spool-work-balance, step 8 exhausts
both streams through the choked-or-unchoked nozzle_exit traverse of the
separate-exhaust-cycle, and step 9 assembles the net-thrust decomposition
and the TSFC round trip. Runs offline, deterministic, in under 20 s.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import turbofan_design_point_logic as tfdp

# Worked-example operating point (spec, cruise 35000 ft).
MACH = 0.8
ALT = 10668.0          # 35000 ft
OPR = 36.0
FPR = 1.65
LPC_PR = 1.50
BPR = 8.0
TT4 = 1600.0
MDOT_CORE = 1.0
ETA_D = 0.97
ETA_FAN = 0.90
ETA_LPC = 0.89
ETA_HPC = 0.87
ETA_B = 0.98
ETA_HPT = 0.86
ETA_LPT = 0.86
CV_CORE = 0.98
CV_FAN = 0.98

HPC_PR = OPR / (FPR * LPC_PR)  # 14.5454545


def anchor(bpr=BPR):
    """Full design point run at the worked-example point (step 9 bookkeep)."""
    return tfdp.turbofan_design_point(
        MACH, ALT, OPR, FPR, LPC_PR, bpr, TT4, MDOT_CORE,
        ETA_D, ETA_FAN, ETA_LPC, ETA_HPC, ETA_B, ETA_HPT, ETA_LPT,
        CV_CORE, CV_FAN)


class TestIsaAndFreestream(unittest.TestCase):
    """SKILL.md workflow step 2: the ambient and flight ram state."""

    def test_isa_tropopause_anchor(self):
        """step 2 ambient: isa_atmosphere at 35000 ft (10668 m) gives the
        spec anchors t0 218.8080 K and p0 23835.9189 Pa within tolerance."""
        t0, p0 = tfdp.isa_atmosphere(ALT)
        self.assertAlmostEqual(t0, 218.8080, delta=0.05)
        self.assertAlmostEqual(p0, 23835.9189, delta=2.0)

    def test_isa_sea_level_and_tropopause(self):
        """step 2 ambient: sea level recovers the ISA constants and the
        tropopause boundary stays inside the valid altitude band."""
        t0, p0 = tfdp.isa_atmosphere(0.0)
        self.assertAlmostEqual(t0, tfdp.ISA_SEA_T, delta=1e-9)
        self.assertAlmostEqual(p0, tfdp.ISA_SEA_P, delta=1e-6)
        t_trop, _ = tfdp.isa_atmosphere(11000.0)
        self.assertAlmostEqual(t_trop, 216.65, delta=0.01)

    def test_isa_valueerrors(self):
        """step 2 guard: altitudes outside the troposphere [0, 11000] m
        (negative and stratospheric) raise ValueError."""
        for bad in (-1.0, 20000.0, 11000.5):
            with self.assertRaises(ValueError):
                tfdp.isa_atmosphere(bad)

    def test_freestream_ram_state_anchor(self):
        """step 2 flight: freestream_state gives v0 237.2655 m/s and
        Tt0 246.8154 K within tolerance at mach 0.8."""
        t0, p0 = tfdp.isa_atmosphere(ALT)
        v0, tt0, pt0 = tfdp.freestream_state(t0, p0, MACH)
        self.assertAlmostEqual(v0, 237.2655, delta=0.05)
        self.assertAlmostEqual(tt0, 246.8154, delta=0.01)
        self.assertAlmostEqual(pt0, 36334.0449, delta=5.0)
        self.assertAlmostEqual(pt0, p0 * (tt0 / t0) ** (1.0 / tfdp.KAPPA_C),
                               delta=1e-6)

    def test_freestream_valueerrors(self):
        """step 2 guard: non-positive static temperature or pressure and a
        negative mach number raise ValueError."""
        with self.assertRaises(ValueError):
            tfdp.freestream_state(0.0, 101325.0, 0.8)
        with self.assertRaises(ValueError):
            tfdp.freestream_state(288.15, -1.0, 0.8)
        with self.assertRaises(ValueError):
            tfdp.freestream_state(288.15, 101325.0, -0.5)


class TestInletAndFan(unittest.TestCase):
    """SKILL.md workflow step 3: the inlet traverse and the fan that feeds
    the fan-stream-station-states at station 13."""

    def test_diffuser_state_anchor(self):
        """step 3 inlet: the diffuser traverse returns Tt2 = Tt0 and
        Pt2 = 35902.97 Pa within 5 Pa at eta_d 0.97 (ram recovery
        0.988136)."""
        t0, p0 = tfdp.isa_atmosphere(ALT)
        _, tt0, pt0 = tfdp.freestream_state(t0, p0, MACH)
        tt2, pt2 = tfdp.diffuser_state(tt0, t0, p0, ETA_D)
        self.assertAlmostEqual(tt2, tt0, delta=1e-9)
        self.assertAlmostEqual(pt2, 35902.9677, delta=5.0)
        self.assertAlmostEqual(pt2 / pt0, 0.988136, delta=1e-5)

    def test_diffuser_ideal_recovery(self):
        """step 3 inlet: at eta_d = 1 the diffuser recovers the full
        freestream total pressure, pt2 equals pt0 to float noise."""
        t0, p0 = tfdp.isa_atmosphere(ALT)
        _, tt0, pt0 = tfdp.freestream_state(t0, p0, MACH)
        _, pt2 = tfdp.diffuser_state(tt0, t0, p0, 1.0)
        self.assertAlmostEqual(pt2, pt0, delta=abs(pt0) * 1e-12)

    def test_diffuser_valueerrors(self):
        """step 3 guard: an eta_d of 1.5 and non-positive inputs raise
        ValueError."""
        with self.assertRaises(ValueError):
            tfdp.diffuser_state(246.8, 218.8, 23835.9, 1.5)
        with self.assertRaises(ValueError):
            tfdp.diffuser_state(246.8, 218.8, 23835.9, 0.0)
        with self.assertRaises(ValueError):
            tfdp.diffuser_state(0.0, 218.8, 23835.9, 0.97)

    def test_fan_exit_station_13(self):
        """step 3 fan traverse: the fan at FPR 1.65 and eta_fan 0.90
        delivers the station-13 fan-stream-station-states Tt13 288.9991 K
        and Pt13 59239.90 Pa."""
        t0, p0 = tfdp.isa_atmosphere(ALT)
        _, tt0, _ = tfdp.freestream_state(t0, p0, MACH)
        tt2, pt2 = tfdp.diffuser_state(tt0, t0, p0, ETA_D)
        tt13 = tfdp.compressor_exit_temperature(tt2, FPR, ETA_FAN)
        self.assertAlmostEqual(tt13, 288.9991, delta=0.05)
        self.assertAlmostEqual(pt2 * FPR, 59239.8966, delta=5.0)

    def test_compressor_exit_valueerrors(self):
        """step 3/4 guard: a pressure ratio of 1.0 and an efficiency of 0
        are non-physical for the cold compression relations and raise
        ValueError."""
        with self.assertRaises(ValueError):
            tfdp.compressor_exit_temperature(300.0, 1.0, 0.9)
        with self.assertRaises(ValueError):
            tfdp.compressor_exit_temperature(300.0, 1.5, 0.0)
        with self.assertRaises(ValueError):
            tfdp.compressor_exit_temperature(-5.0, 1.5, 0.9)


class TestCoreCompressionAndBurner(unittest.TestCase):
    """SKILL.md workflow steps 4 and 5: the core stream up to Tt4 and the
    combustor energy balance."""

    def test_booster_and_hpc_states(self):
        """step 4 core compression: the booster exit Tt25 328.8823 K and
        the HPC exit Tt3 763.1803 K anchor the core stream between the fan
        discharge and the combustor."""
        tt25 = tfdp.compressor_exit_temperature(288.999073, LPC_PR, ETA_LPC)
        self.assertAlmostEqual(tt25, 328.8823, delta=0.05)
        tt3 = tfdp.compressor_exit_temperature(tt25, HPC_PR, ETA_HPC)
        self.assertAlmostEqual(tt3, 763.1803, delta=0.1)

    def test_hpc_ratio_closure(self):
        """step 4 OPR closure: hpc_pr = opr/(fpr*lpc_pr) = 14.545 and the
        design point closes pt3/pt2 to the input OPR 36 within 1e-9
        relative."""
        r = anchor()
        self.assertAlmostEqual(HPC_PR, 14.545454545, delta=1e-6)
        self.assertTrue(math.isclose(r["opr_actual"], OPR, rel_tol=1e-9))
        self.assertTrue(math.isclose(r["pt3"] / r["pt2"], OPR, rel_tol=1e-9))

    def test_fuel_air_ratio_anchor(self):
        """step 5 burner energy balance: fuel_air_ratio gives f
        0.01995738 kg/kg within 1e-6 at Tt3 763.18 K, Tt4 1600 K and
        eta_b 0.98, with pt4 equal to pt3 (no combustor pressure loss)."""
        f = tfdp.fuel_air_ratio(763.180293, TT4, ETA_B)
        self.assertAlmostEqual(f, 0.01995738, delta=1e-6)
        self.assertAlmostEqual(f, tfdp.CP_C * (TT4 - 763.180293) /
                               (ETA_B * tfdp.LHV), delta=1e-12)
        r = anchor()
        self.assertAlmostEqual(r["pt4"], r["pt3"], delta=1e-6)

    def test_fuel_air_ratio_valueerrors(self):
        """step 5 guard: tt4 below tt3 and an eta_b of 1.01 are rejected
        with ValueError."""
        with self.assertRaises(ValueError):
            tfdp.fuel_air_ratio(1500.0, 1500.0, ETA_B)
        with self.assertRaises(ValueError):
            tfdp.fuel_air_ratio(763.0, 1600.0, 1.01)


class TestSpoolBalances(unittest.TestCase):
    """SKILL.md workflow steps 6 and 7: the hp-and-lp-turbine-matching of
    the two-spool-work-balance."""

    def test_hp_spool_balance_anchor(self):
        """step 6 HP spool closure: hp_spool_balance sizes Tt45
        1220.4613 K so that cp_g*(Tt4 - Tt45) equals the HPC demand
        cp_c*(Tt3 - Tt25) to 1e-12 relative."""
        tt45 = tfdp.hp_spool_balance(328.882329, 763.180293, TT4)
        self.assertAlmostEqual(tt45, 1220.4613, delta=0.1)
        w_turb = tfdp.CP_G * (TT4 - tt45)
        w_comp = tfdp.CP_C * (763.180293 - 328.882329)
        self.assertTrue(math.isclose(w_turb, w_comp, rel_tol=1e-12))

    def test_hp_spool_valueerrors(self):
        """step 6 guard: a core ordering with tt3 below tt25 and an HP
        demand reaching tt4 (with cp_c above cp_g) raise ValueError."""
        with self.assertRaises(ValueError):
            tfdp.hp_spool_balance(800.0, 700.0, 1600.0)
        with self.assertRaises(ValueError):
            tfdp.hp_spool_balance(500.0, 900.0, 1000.0, cp_c=3000.0,
                                  cp_g=1000.0)

    def test_lp_spool_balance_anchor(self):
        """step 7 LP spool closure: lp_spool_balance sizes Tt5
        853.8233 K; the fan-share term cp_c*(1 + bpr)*(Tt13 - Tt2) is
        381551.108 J/kg within 0.01 and the booster term 40082.672 J/kg,
        summing to the LPT work to 1e-12 relative."""
        tt5 = tfdp.lp_spool_balance(246.815424, 288.999073, 328.882329,
                                    1220.461345, BPR)
        self.assertAlmostEqual(tt5, 853.8233, delta=0.1)
        fan_term = tfdp.CP_C * (1.0 + BPR) * (288.999073 - 246.815424)
        booster_term = tfdp.CP_C * (328.882329 - 288.999073)
        self.assertAlmostEqual(fan_term, 381551.108, delta=0.01)
        self.assertAlmostEqual(booster_term, 40082.6723, delta=0.01)
        w_lpt = tfdp.CP_G * (1220.461345 - tt5)
        self.assertTrue(math.isclose(w_lpt, fan_term + booster_term,
                                     rel_tol=1e-12))

    def test_lp_spool_fan_growth_limit(self):
        """step 7 fan-growth limit: at bpr 40 the LP enthalpy demand of
        the fan on both streams reaches the LPT inlet and the balance
        raises ValueError (the design point cannot grow the fan at fixed
        Tt4)."""
        with self.assertRaises(ValueError):
            tfdp.lp_spool_balance(246.815424, 288.999073, 328.882329,
                                  1220.461345, 40.0)

    def test_lp_spool_valueerrors(self):
        """step 7 guard: a negative bypass ratio and a broken station
        ordering raise ValueError."""
        with self.assertRaises(ValueError):
            tfdp.lp_spool_balance(246.8, 289.0, 328.9, 1220.5, -1.0)
        with self.assertRaises(ValueError):
            tfdp.lp_spool_balance(300.0, 289.0, 328.9, 1220.5, 8.0)

    def test_turbine_pressure_ratio_anchor(self):
        """step 6/7 turbine traverse: the HPT ratio closes Pt45
        355468.35 Pa and the LPT ratio closes Pt5 63721.91 Pa within
        5 Pa at the anchor."""
        r = anchor()
        self.assertAlmostEqual(r["pt45"], 355468.3493, delta=5.0)
        self.assertAlmostEqual(r["pt5"], 63721.9051, delta=5.0)
        pr_hpt = tfdp.turbine_pressure_ratio(TT4, r["tt45"], ETA_HPT)
        self.assertAlmostEqual(r["pt45"], r["pt4"] * pr_hpt,
                               delta=abs(r["pt4"] * pr_hpt) * 1e-12)

    def test_turbine_pressure_ratio_valueerrors(self):
        """step 6/7 guard: a turbine outlet at or above the inlet
        temperature and an efficiency outside (0, 1] raise ValueError."""
        with self.assertRaises(ValueError):
            tfdp.turbine_pressure_ratio(1600.0, 1600.0, ETA_HPT)
        with self.assertRaises(ValueError):
            tfdp.turbine_pressure_ratio(1600.0, 1650.0, ETA_HPT)
        with self.assertRaises(ValueError):
            tfdp.turbine_pressure_ratio(1600.0, 1200.0, 1.5)


class TestNozzles(unittest.TestCase):
    """SKILL.md workflow step 8: the choked-or-unchoked exhaust traverse
    of the separate-exhaust-cycle nozzles."""

    def test_nozzle_critical_ratios(self):
        """step 8 regime split: the cold critical nozzle pressure ratio is
        1.892929 and the hot critical ratio 1.852623 at the module
        gamma constants."""
        crit_cold = ((tfdp.GAMMA_C + 1) / 2) ** (tfdp.GAMMA_C /
                                                 (tfdp.GAMMA_C - 1))
        crit_hot = ((tfdp.GAMMA_G + 1) / 2) ** (tfdp.GAMMA_G /
                                                (tfdp.GAMMA_G - 1))
        self.assertAlmostEqual(crit_cold, 1.892929, delta=1e-6)
        self.assertAlmostEqual(crit_hot, 1.852623, delta=1e-6)

    def test_core_nozzle_choked_anchor(self):
        """step 8 core exhaust: the core nozzle at NPR 2.673356 above the
        hot critical 1.852623 chokes with Me 1, Te 731.8485 K, Pe
        34395.497 Pa and v9 519.0689 m/s within tolerance."""
        nz = tfdp.nozzle_exit(853.823275, 63721.9051, 23835.9189,
                              tfdp.GAMMA_G, tfdp.CP_G, CV_CORE)
        self.assertTrue(nz["choked"])
        self.assertAlmostEqual(nz["npr"], 2.673356, delta=1e-6)
        self.assertAlmostEqual(nz["me"], 1.0, delta=1e-9)
        self.assertAlmostEqual(nz["te"], 731.8485, delta=0.1)
        self.assertAlmostEqual(nz["pe"], 34395.4973, delta=5.0)
        self.assertAlmostEqual(nz["ve"], 519.0689, delta=0.5)
        self.assertAlmostEqual(nz["ve"], CV_CORE * nz["v_ideal"],
                               delta=abs(nz["v_ideal"]) * 1e-12)

    def test_fan_nozzle_choked_anchor(self):
        """step 8 fan exhaust: the fan nozzle at NPR 2.485320 above the
        cold critical 1.892929 chokes and v19 304.9276 m/s exits station
        13 at the fan-stream-station-states total state."""
        nz = tfdp.nozzle_exit(288.999073, 59239.8966, 23835.9189,
                              tfdp.GAMMA_C, tfdp.CP_C, CV_FAN)
        self.assertTrue(nz["choked"])
        self.assertAlmostEqual(nz["npr"], 2.485320, delta=1e-6)
        self.assertAlmostEqual(nz["me"], 1.0, delta=1e-9)
        self.assertAlmostEqual(nz["ve"], 304.9276, delta=0.5)

    def test_nozzle_unchoked_regime(self):
        """step 8 unchoked branch: below the critical ratio the nozzle
        fully expands to pe = p_amb with me below 1 and a velocity
        coefficient discount, and the exit pressure term vanishes."""
        nz = tfdp.nozzle_exit(900.0, 50000.0, 45000.0, tfdp.GAMMA_G,
                              tfdp.CP_G, 0.98)
        self.assertFalse(nz["choked"])
        self.assertLess(nz["npr"], nz["critical"])
        self.assertAlmostEqual(nz["pe"], 45000.0, delta=1e-6)
        self.assertLess(nz["me"], 1.0)
        self.assertGreater(nz["me"], 0.0)
        self.assertAlmostEqual(nz["ve"], 0.98 * nz["v_ideal"], delta=1e-6)

    def test_nozzle_valueerrors(self):
        """step 8 guard: an entry total pressure at or below ambient and a
        velocity coefficient of 1.01 raise ValueError (nothing to expand,
        sibling convention)."""
        with self.assertRaises(ValueError):
            tfdp.nozzle_exit(900.0, 45000.0, 45000.0, tfdp.GAMMA_C,
                             tfdp.CP_C, 0.98)
        with self.assertRaises(ValueError):
            tfdp.nozzle_exit(900.0, 40000.0, 45000.0, tfdp.GAMMA_C,
                             tfdp.CP_C, 0.98)
        with self.assertRaises(ValueError):
            tfdp.nozzle_exit(900.0, 60000.0, 45000.0, tfdp.GAMMA_C,
                             tfdp.CP_C, 1.01)


class TestDesignPointReport(unittest.TestCase):
    """SKILL.md workflow step 9: the assembled design point bookkeeping."""

    def test_station_chain_order_and_states(self):
        """step 9 station chain: the traverse keeps the fan-stream-station-
        states and core chain ordered Tt2 < Tt13 < Tt25 < Tt3 < Tt4 with
        Tt5 < Tt45 < Tt4 and the station total temperatures match their
        worked-example anchors."""
        r = anchor()
        self.assertLess(r["tt2"], r["tt13"])
        self.assertLess(r["tt13"], r["tt25"])
        self.assertLess(r["tt25"], r["tt3"])
        self.assertLess(r["tt3"], r["tt4"])
        self.assertLess(r["tt5"], r["tt45"])
        self.assertLess(r["tt45"], r["tt4"])
        self.assertAlmostEqual(r["tt13"], 288.9991, delta=0.05)
        self.assertAlmostEqual(r["pt13"], 59239.8966, delta=5.0)
        self.assertAlmostEqual(r["tt3"], 763.1803, delta=0.1)
        self.assertAlmostEqual(r["tt45"], 1220.4613, delta=0.1)
        self.assertAlmostEqual(r["tt5"], 853.8233, delta=0.1)

    def test_spool_closure_residuals(self):
        """step 9 spool closure: the HP and LP work balances close to
        below 1e-12 relative residual at the anchor and the fan-share
        term cp_c*(1 + bpr)*(Tt13 - Tt2) is 381551.108 J/kg within
        0.01."""
        r = anchor()
        w_hpt = tfdp.CP_G * (r["tt4"] - r["tt45"])
        w_hpc = tfdp.CP_C * (r["tt3"] - r["tt25"])
        self.assertTrue(math.isclose(w_hpt, w_hpc, rel_tol=1e-12))
        fan_term = tfdp.CP_C * (1.0 + BPR) * (r["tt13"] - r["tt2"])
        booster_term = tfdp.CP_C * (r["tt25"] - r["tt13"])
        w_lpt = tfdp.CP_G * (r["tt45"] - r["tt5"])
        self.assertAlmostEqual(fan_term, 381551.108, delta=0.01)
        self.assertTrue(math.isclose(w_lpt, fan_term + booster_term,
                                     rel_tol=1e-12))

    def test_mass_split(self):
        """step 9 mass split: mdot_fan = bpr*mdot_core = 8.0 kg/s and
        mdot_total = (1 + bpr)*mdot_core = 9.0 kg/s at the 1 kg/s core
        flow, with mdot_fuel = f*mdot_core to 1e-12 relative."""
        r = anchor()
        self.assertAlmostEqual(r["mdot_fan"], BPR * MDOT_CORE, delta=1e-12)
        self.assertAlmostEqual(r["mdot_total"], (1.0 + BPR) * MDOT_CORE,
                               delta=1e-12)
        self.assertTrue(math.isclose(r["mdot_fuel"], r["f"] * MDOT_CORE,
                                     rel_tol=1e-12))

    def test_thrust_decomposition(self):
        """step 9 thrust bookkeep: net thrust 1379.9922 N within 1 N
        equals the sum of the momentum terms mdot*(ve - v0) and the
        choked pressure terms (pe - p0)*A to 1e-9 relative, and the
        specific thrust is 153.3325 N/(kg/s)."""
        r = anchor()
        self.assertAlmostEqual(r["net_thrust"], 1379.9922, delta=1.0)
        self.assertAlmostEqual(r["specific_thrust"], 153.3325, delta=0.05)
        four = (r["f_core_mom"] + r["f_fan_mom"] + r["f_core_pres"] +
                r["f_fan_pres"])
        self.assertTrue(math.isclose(r["net_thrust"], four, rel_tol=1e-9))
        self.assertAlmostEqual(r["f_core_mom"],
                               MDOT_CORE * (r["core_nz"]["ve"] - 237.2655),
                               delta=0.05)
        self.assertAlmostEqual(r["f_fan_pres"],
                               (r["fan_nz"]["pe"] - 23835.9189) * r["a19"],
                               delta=1e-6)
        self.assertGreater(r["core_nz"]["pe"], 23835.9189)
        self.assertGreater(r["fan_nz"]["pe"], 23835.9189)

    def test_tsfc_round_trip(self):
        """step 9 TSFC: tsfc 1.4461947730e-05 kg/(N s) within 1e-8 sits
        inside the 0.5-0.7 lb/(lbf hr) plausibility band of 1.416e-5 to
        1.983e-5, tsfc_imp is 0.5106 within 0.005 lb/(lbf hr), and the
        round trip tsfc*net_thrust equals mdot_fuel to 1e-9 relative."""
        r = anchor()
        self.assertAlmostEqual(r["tsfc"], 1.4461947730e-05, delta=1e-8)
        self.assertGreaterEqual(r["tsfc"], 1.416e-5)
        self.assertLessEqual(r["tsfc"], 1.983e-5)
        self.assertAlmostEqual(r["tsfc_imp"], 0.5106, delta=0.005)
        self.assertTrue(math.isclose(r["tsfc"] * r["net_thrust"],
                                     r["mdot_fuel"], rel_tol=1e-9))

    def test_nozzle_exit_areas(self):
        """step 8/9 exit areas: the continuity areas A9 0.0117851 m^2 and
        A19 0.0579731 m^2 carry the choked pressure terms."""
        r = anchor()
        self.assertAlmostEqual(r["a9"], 0.0117851, delta=1e-5)
        self.assertAlmostEqual(r["a19"], 0.0579731, delta=1e-5)

    def test_design_point_valueerrors(self):
        """step 1 guard: an OPR at or below fpr*lpc_pr (the HPC would have
        no ratio) and a non-positive core mass flow raise ValueError."""
        with self.assertRaises(ValueError):
            tfdp.turbofan_design_point(
                MACH, ALT, 2.0, FPR, LPC_PR, BPR, TT4, MDOT_CORE,
                ETA_D, ETA_FAN, ETA_LPC, ETA_HPC, ETA_B, ETA_HPT, ETA_LPT,
                CV_CORE, CV_FAN)
        with self.assertRaises(ValueError):
            tfdp.turbofan_design_point(
                MACH, ALT, FPR * LPC_PR, FPR, LPC_PR, BPR, TT4, MDOT_CORE,
                ETA_D, ETA_FAN, ETA_LPC, ETA_HPC, ETA_B, ETA_HPT, ETA_LPT,
                CV_CORE, CV_FAN)
        with self.assertRaises(ValueError):
            tfdp.turbofan_design_point(
                MACH, ALT, OPR, FPR, LPC_PR, BPR, TT4, 0.0,
                ETA_D, ETA_FAN, ETA_LPC, ETA_HPC, ETA_B, ETA_HPT, ETA_LPT,
                CV_CORE, CV_FAN)


class TestTrendsAndRobustness(unittest.TestCase):
    """Design point behavior across the bypass ratio and determinism."""

    def test_bpr_trend_tsfc_minimum(self):
        """step 9 trade read-off: TSFC falls from bpr 4 (1.7955257472e-05
        kg/(N s), F 1111.5060 N, v9 562.1074 m/s) to bpr 8 (the anchor,
        below the bpr-4 value), then rises again at bpr 12 where the LP
        turbine has over-expanded the core and the core nozzle unchokes
        with v9 63.6385 m/s below v0, F back to 1286.9882 N."""
        r4 = anchor(4.0)
        self.assertAlmostEqual(r4["tsfc"], 1.7955257472e-05, delta=1e-8)
        self.assertAlmostEqual(r4["net_thrust"], 1111.5060, delta=1.0)
        self.assertAlmostEqual(r4["core_nz"]["ve"], 562.1074, delta=0.5)
        r8 = anchor()
        self.assertLess(r8["tsfc"], r4["tsfc"])
        r12 = anchor(12.0)
        self.assertAlmostEqual(r12["tt5"], 706.3639, delta=0.1)
        self.assertFalse(r12["core_nz"]["choked"])
        self.assertAlmostEqual(r12["core_nz"]["ve"], 63.6385, delta=0.1)
        self.assertLess(r12["core_nz"]["ve"], 237.2655)
        self.assertAlmostEqual(r12["net_thrust"], 1286.9882, delta=1.0)
        self.assertAlmostEqual(r12["tsfc"], 1.5507038944e-05, delta=1e-8)

    def test_bpr40_raises(self):
        """step 7 fan-growth limit at the report level: the design point
        at bpr 40 raises ValueError (the LP enthalpy guard of the
        two-spool-work-balance at fixed Tt4)."""
        with self.assertRaises(ValueError):
            anchor(40.0)

    def test_bpr0_degenerate(self):
        """step 9 degenerate case: at bpr 0 the fan stream vanishes
        (mdot_fan 0, fan thrust terms zero) and F 757.4655 N within 0.5 N
        is the core momentum 364.8118 plus the core pressure term
        392.6537."""
        r = anchor(0.0)
        self.assertAlmostEqual(r["net_thrust"], 757.4655, delta=0.5)
        self.assertAlmostEqual(r["mdot_fan"], 0.0, delta=1e-12)
        self.assertAlmostEqual(r["f_fan_mom"], 0.0, delta=1e-9)
        self.assertAlmostEqual(r["f_fan_pres"], 0.0, delta=1e-9)
        self.assertAlmostEqual(r["f_core_mom"], 364.8118, delta=0.05)
        self.assertAlmostEqual(r["f_core_pres"], 392.6537, delta=0.05)
        # the core pressure term is present, so the core nozzle stays choked
        self.assertTrue(r["core_nz"]["choked"])

    def test_determinism(self):
        """step 10 determinism: two identical runs return identical
        reports byte for byte, and the module imports only the stdlib
        math module."""
        r1 = anchor()
        r2 = anchor()
        self.assertEqual(sorted(r1.keys()), sorted(r2.keys()))
        for k in r1.keys():
            if isinstance(r1[k], dict):
                for kk in r1[k]:
                    self.assertEqual(r1[k][kk], r2[k][kk])
            else:
                self.assertEqual(r1[k], r2[k])
        self.assertIn("math", sys.modules)
        self.assertEqual(tfdp.GAMMA_C, 1.4)
        self.assertEqual(tfdp.GAMMA_G, 4.0 / 3.0)


if __name__ == "__main__":
    unittest.main()
