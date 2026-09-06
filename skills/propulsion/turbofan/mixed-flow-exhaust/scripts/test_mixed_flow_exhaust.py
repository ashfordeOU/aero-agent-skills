"""test_mixed_flow_exhaust.py - contract test for the mixed-flow-exhaust leaf.

Exercises the step-1 operating point setup (mach, altitude, OPR = fpr *
lpc_pr * hpc_pr, BPR, Tt4, component efficiencies, cv, pi_duct and the
fan-stream mixer entry Mach), the step-2 atmosphere and freestream
traverse (isa_atmosphere, freestream_state), the step-3 station traverse
0-2-13-2.5-3-4-4.5-5 (design_point_traverse with its closure identities
opr == fpr*lpc_pr*hpc_pr, m_core == 1 + f, m_total == bpr + m_core), the
step-4 fan duct carry (tt16 = tt13, pt16 = pi_duct*pt13), the step-5
constant-area mixer closure (equal static pressure plane, derived core
entry Mach, entry areas from continuity, the energy balance to the mixed
total temperature and the momentum balance on the first subsonic root,
the mixing loss ratio), the step-6 common convergent nozzle expansion
(choked regime, exit velocity with the nozzle velocity coefficient), the
step-7 net thrust and TSFC bookkeeping per unit core air, and the step-8
separate-exhaust baseline with its mixed-vs-separate F and TSFC ratio
comparison.

All numeric asserts are tolerance-based (math.isclose / assertAlmostEqual
with delta); no exact float equality on computed aggregates. Deterministic
offline stdlib unittest: python3 scripts/test_mixed_flow_exhaust.py.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mixed_flow_exhaust_logic import (  # noqa: E402
    GAMMA_C, KAPPA_C, GAMMA_G, KAPPA_G, CP_C, CP_G, R_C, R_G, LHV,
    ISA_SEA_T, ISA_SEA_P, ISA_LAPSE, ISA_R, G0, ISA_EXP,
    LBF_PER_HR, BISECT_TOL,
    isa_atmosphere, freestream_state, diffuser_state, cold_compressor,
    burner_far, hp_spool, lp_spool, turbine_expansion,
    design_point_traverse, mixing_state, common_nozzle, net_thrust,
)

# Worked point: low-BPR military-style mixed-flow turbofan at Mach 0.85,
# 10668 m, OPR 24 = 4.0*1.6*3.75, BPR 0.6, Tt4 = 1750 K.
WORKED = dict(mach=0.85, altitude=10668.0, opr=24.0, fpr=4.0, bpr=0.6,
              lpc_pr=1.6, tt4=1750.0, eta_d=0.97, eta_fan=0.90,
              eta_bst=0.89, eta_hpc=0.88, eta_b=0.995, eta_hpt=0.90,
              eta_lpt=0.91)
CV = 0.985
PI_DUCT = 0.98
M_FAN_ENTRY = 0.3

T0_W = 218.808          # 288.15 - 0.0065*10668 (anchor 218.81)
P0_W = 23835.9189       # anchor p0 23835.9 Pa at 10668 m


def rel(a, b):
    """Relative error of a against b."""
    return abs(a - b) / abs(b)


def _worked_traverse():
    """Step-2/3 atmosphere, freestream and station traverse at the point."""
    return design_point_traverse(**WORKED)


class TestModuleConstants(unittest.TestCase):
    """Step-1 constants: the module gas constants pinned by the spec."""

    def test_gas_constants(self):
        self.assertEqual(GAMMA_C, 1.4)
        self.assertAlmostEqual(KAPPA_C, 2.0 / 7.0)
        self.assertAlmostEqual(GAMMA_G, 4.0 / 3.0)
        self.assertAlmostEqual(KAPPA_G, 1.0 / 4.0)
        self.assertEqual(CP_C, 1005.0)
        self.assertEqual(CP_G, 1150.0)

    def test_derived_gas_constants(self):
        self.assertTrue(math.isclose(R_C, 287.142857, rel_tol=1e-6))
        self.assertAlmostEqual(R_G, 287.5)
        self.assertEqual(LHV, 43.0e6)

    def test_isa_and_conversion_constants(self):
        self.assertEqual(ISA_SEA_T, 288.15)
        self.assertEqual(ISA_SEA_P, 101325.0)
        self.assertEqual(ISA_LAPSE, 0.0065)
        self.assertEqual(ISA_R, 287.0)
        self.assertEqual(G0, 9.80665)
        self.assertTrue(math.isclose(ISA_EXP, 5.25588, rel_tol=1e-2))
        self.assertTrue(math.isclose(LBF_PER_HR, 35303.9, rel_tol=1e-4))


class TestAtmosphereAndFreestream(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the atmosphere and freestream
    traverse, is exercised by these atmosphere and freestream tests."""

    def test_isa_sea_level_exact(self):
        t0, p0 = isa_atmosphere(0.0)
        self.assertEqual(t0, ISA_SEA_T)
        self.assertEqual(p0, ISA_SEA_P)

    def test_isa_worked_altitude(self):
        t0, p0 = isa_atmosphere(WORKED["altitude"])
        self.assertTrue(math.isclose(t0, T0_W, rel_tol=1e-9))
        self.assertTrue(math.isclose(p0, P0_W, rel_tol=1e-9))

    def test_isa_tropopause_upper_bound(self):
        t0, p0 = isa_atmosphere(11000.0)
        self.assertTrue(math.isclose(t0, 288.15 - 0.0065 * 11000.0,
                                     rel_tol=1e-12))
        self.assertTrue(math.isclose(p0, 22632.1, rel_tol=1e-3))

    def test_isa_rejects_out_of_range(self):
        for bad in (-1.0, 12000.0):
            with self.assertRaises(ValueError):
                isa_atmosphere(bad)

    def test_freestream_static_at_mach_zero(self):
        v0, tt0, pt0 = freestream_state(288.15, 101325.0, 0.0)
        self.assertEqual(v0, 0.0)
        self.assertEqual(tt0, 288.15)
        self.assertEqual(pt0, 101325.0)

    def test_freestream_worked_point(self):
        v0, tt0, pt0 = freestream_state(T0_W, P0_W, WORKED["mach"])
        self.assertTrue(math.isclose(v0, 252.0946, rel_tol=1e-6))
        self.assertTrue(math.isclose(tt0, 250.4258, rel_tol=1e-6))
        self.assertTrue(math.isclose(pt0, P0_W * (tt0 / T0_W) ** 3.5,
                                     rel_tol=1e-12))

    def test_freestream_ram_relation(self):
        v0, tt0, _ = freestream_state(T0_W, P0_W, WORKED["mach"])
        self.assertTrue(math.isclose(tt0 - T0_W, 0.2 * T0_W * 0.85 ** 2,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(v0, 0.85 * math.sqrt(1.4 * R_C * T0_W),
                                     rel_tol=1e-12))

    def test_freestream_rejects(self):
        with self.assertRaises(ValueError):
            freestream_state(T0_W, P0_W, -0.1)
        with self.assertRaises(ValueError):
            freestream_state(0.0, P0_W, 0.5)
        with self.assertRaises(ValueError):
            freestream_state(T0_W, -1.0, 0.5)


class TestDiffuserAndCompression(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the station traverse through the
    diffuser, fan, booster and HPC, is exercised by these compression
    tests and the traverse tests below."""

    def test_diffuser_state_worked(self):
        t0, p0 = isa_atmosphere(WORKED["altitude"])
        _, tt0, _ = freestream_state(t0, p0, WORKED["mach"])
        tt2, pt2 = diffuser_state(tt0, t0, p0, WORKED["eta_d"])
        self.assertTrue(math.isclose(tt2, tt0, rel_tol=1e-12))
        self.assertTrue(math.isclose(pt2, 37724.0983, rel_tol=1e-6))

    def test_diffuser_rejects_efficiency(self):
        t0, p0 = isa_atmosphere(WORKED["altitude"])
        _, tt0, _ = freestream_state(t0, p0, WORKED["mach"])
        with self.assertRaises(ValueError):
            diffuser_state(tt0, t0, p0, 0.0)
        with self.assertRaises(ValueError):
            diffuser_state(tt0, t0, p0, 1.5)

    def test_cold_compressor_fan_step(self):
        tr = _worked_traverse()
        tt13, pt13 = cold_compressor(tr["tt2"], tr["pt2"], WORKED["fpr"],
                                     WORKED["eta_fan"])
        self.assertTrue(math.isclose(tt13, 385.6541, rel_tol=1e-6))
        self.assertTrue(math.isclose(pt13, 150896.3931, rel_tol=1e-6))
        self.assertTrue(math.isclose(pt13, tr["pt2"] * 4.0, rel_tol=1e-12))

    def test_cold_compressor_rejects(self):
        with self.assertRaises(ValueError):
            cold_compressor(300.0, 50000.0, 0.9, 0.9)
        with self.assertRaises(ValueError):
            cold_compressor(300.0, 50000.0, 2.0, 0.0)
        with self.assertRaises(ValueError):
            cold_compressor(300.0, 50000.0, 2.0, 1.5)

    def test_booster_and_hpc_steps(self):
        tr = _worked_traverse()
        self.assertTrue(math.isclose(tr["tt25"], 447.9310, rel_tol=1e-6))
        self.assertTrue(math.isclose(tr["pt25"], 241434.2290, rel_tol=1e-6))
        self.assertTrue(math.isclose(tr["tt3"], 681.4885, rel_tol=1e-6))
        self.assertTrue(math.isclose(tr["pt3"], 905378.3586, rel_tol=1e-6))


class TestBurnerAndSpools(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the burner fuel-to-air ratio and
    the HP and LP spool work balances, is exercised by these tests."""

    def test_burner_far_worked(self):
        tr = _worked_traverse()
        f = burner_far(tr["tt3"], WORKED["tt4"], WORKED["eta_b"])
        self.assertTrue(math.isclose(f, 0.025099, rel_tol=1e-4))
        self.assertTrue(math.isclose(f, tr["f"], rel_tol=1e-12))

    def test_burner_energy_balance_closes_tt4(self):
        tr = _worked_traverse()
        tt4_back = tr["tt3"] + tr["f"] * WORKED["eta_b"] * LHV / CP_C
        self.assertTrue(math.isclose(tt4_back, WORKED["tt4"], rel_tol=1e-9))

    def test_burner_rejects_no_heat_release(self):
        with self.assertRaises(ValueError):
            burner_far(1750.0, 1750.0, 0.995)

    def test_hp_spool_work_balance(self):
        tr = _worked_traverse()
        tt45 = hp_spool(tr["tt3"], tr["tt25"], WORKED["tt4"],
                        WORKED["eta_hpt"])
        self.assertTrue(math.isclose(tt45, 1545.8911, rel_tol=1e-6))
        expect = WORKED["tt4"] - CP_C * (tr["tt3"] - tr["tt25"]) / CP_G
        self.assertTrue(math.isclose(tt45, expect, rel_tol=1e-12))

    def test_lp_spool_work_balance(self):
        tr = _worked_traverse()
        work = (1.0 + WORKED["bpr"]) * (tr["tt13"] - tr["tt2"]) \
            + (tr["tt25"] - tr["tt13"])
        expect = tr["tt45"] - CP_C * work / CP_G
        self.assertTrue(math.isclose(tr["tt5"], 1302.3820, rel_tol=1e-6))
        self.assertTrue(math.isclose(tr["tt5"], expect, rel_tol=1e-12))

    def test_lp_spool_rejects_negative_bpr(self):
        with self.assertRaises(ValueError):
            lp_spool(1500.0, 250.0, 380.0, 440.0, -0.5, 0.91)

    def test_turbine_expansion_pressures(self):
        tr = _worked_traverse()
        self.assertTrue(math.isclose(tr["pt45"], 519660.4508, rel_tol=1e-6))
        self.assertTrue(math.isclose(tr["pt5"], 242959.2421, rel_tol=1e-6))

    def test_turbine_expansion_rejects(self):
        with self.assertRaises(ValueError):
            turbine_expansion(1750.0, 1750.0, 905378.0, 0.9)
        with self.assertRaises(ValueError):
            turbine_expansion(1750.0, 1600.0, 905378.0, 1.5)


class TestDesignPointTraverse(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, the full design-point station
    traverse and its closure identities, is exercised by these tests."""

    def test_traverse_closure_opr_product(self):
        tr = _worked_traverse()
        self.assertTrue(math.isclose(tr["hpc_pr"], 3.75, rel_tol=1e-12))
        self.assertTrue(math.isclose(
            WORKED["fpr"] * WORKED["lpc_pr"] * tr["hpc_pr"],
            WORKED["opr"], rel_tol=1e-12))

    def test_traverse_mass_flow_identities(self):
        tr = _worked_traverse()
        self.assertTrue(math.isclose(tr["m_fan"], 0.6, rel_tol=1e-12))
        self.assertTrue(math.isclose(tr["m_core"], 1.0 + tr["f"],
                                     rel_tol=1e-12))
        self.assertTrue(math.isclose(tr["m_total"],
                                     WORKED["bpr"] + tr["m_core"],
                                     rel_tol=1e-12))
        self.assertTrue(math.isclose(tr["m_total"], 1.625099, rel_tol=1e-6))

    def test_traverse_station_states(self):
        tr = _worked_traverse()
        for key, anchor in (("tt2", 250.4258), ("pt2", 37724.0983),
                            ("tt13", 385.6541), ("pt13", 150896.3931),
                            ("tt25", 447.9310), ("pt25", 241434.2290),
                            ("tt3", 681.4885), ("pt3", 905378.3586),
                            ("tt45", 1545.8911), ("pt45", 519660.4508),
                            ("tt5", 1302.3820), ("pt5", 242959.2421)):
            self.assertTrue(math.isclose(tr[key], anchor, rel_tol=1e-6),
                            msg="%s off anchor" % key)

    def test_traverse_rejects_opr_below_fpr(self):
        with self.assertRaises(ValueError):
            design_point_traverse(mach=0.85, altitude=10668.0, opr=3.0,
                                  fpr=4.0, bpr=0.6, lpc_pr=1.6, tt4=1750.0,
                                  eta_d=0.97, eta_fan=0.90, eta_bst=0.89,
                                  eta_hpc=0.88, eta_b=0.995, eta_hpt=0.90,
                                  eta_lpt=0.91)

    def test_traverse_rejects_hpc_below_one(self):
        with self.assertRaises(ValueError):
            design_point_traverse(mach=0.85, altitude=10668.0, opr=12.0,
                                  fpr=4.0, bpr=0.6, lpc_pr=4.0, tt4=1750.0,
                                  eta_d=0.97, eta_fan=0.90, eta_bst=0.89,
                                  eta_hpc=0.88, eta_b=0.995, eta_hpt=0.90,
                                  eta_lpt=0.91)

    def test_traverse_rejects_bad_efficiency(self):
        with self.assertRaises(ValueError):
            design_point_traverse(mach=0.85, altitude=10668.0, opr=24.0,
                                  fpr=4.0, bpr=0.6, lpc_pr=1.6, tt4=1750.0,
                                  eta_d=0.97, eta_fan=0.90, eta_bst=0.89,
                                  eta_hpc=0.88, eta_b=0.995, eta_hpt=1.2,
                                  eta_lpt=0.91)


class TestMixer(unittest.TestCase):
    """Steps 4 and 5 of the SKILL.md workflow: the fan duct carry to
    station 16 and the constant-area mixer closure over the two streams'
    total states (equal static pressure plane, subsonic core entry Mach,
    entry areas, energy balance to the mixed total temperature, momentum
    balance on the first subsonic root, mixing loss ratio)."""

    @staticmethod
    def _worked_mixer():
        tr = _worked_traverse()
        return tr, mixing_state(
            tr["tt13"], tr["pt13"] * PI_DUCT,
            GAMMA_C, CP_C, R_C, tr["m_fan"],
            tr["tt5"], tr["pt5"],
            GAMMA_G, CP_G, R_G, tr["m_core"],
            m_fan_entry=M_FAN_ENTRY)

    def test_fan_duct_carry(self):
        tr, _ = self._worked_mixer()
        tt16 = tr["tt13"]
        pt16 = tr["pt13"] * PI_DUCT
        self.assertTrue(math.isclose(pt16, 147878.4652, rel_tol=1e-6))

    def test_mixer_equal_static_pressure_plane(self):
        tr, mx = self._worked_mixer()
        pt16 = tr["pt13"] * PI_DUCT
        expect = pt16 / (1.0 + 0.2 * M_FAN_ENTRY ** 2) ** 3.5
        self.assertTrue(math.isclose(mx["p_s"], 138927.3372, rel_tol=1e-6))
        self.assertTrue(math.isclose(mx["p_s"], expect, rel_tol=1e-12))
        self.assertTrue(math.isclose(mx["mach_f"], 0.3, rel_tol=1e-12))
        self.assertTrue(math.isclose(mx["mach_g"], 0.9486, rel_tol=1e-4))

    def test_mixer_entry_static_temperatures_and_velocities(self):
        tr, mx = self._worked_mixer()
        self.assertTrue(math.isclose(mx["T_s_f"], 378.8350, rel_tol=1e-6))
        self.assertTrue(math.isclose(mx["T_s_g"], 1132.5358, rel_tol=1e-6))
        self.assertTrue(math.isclose(mx["v_f"], 117.0737, rel_tol=1e-6))
        self.assertTrue(math.isclose(mx["v_g"], 625.0169, rel_tol=1e-6))

    def test_mixer_entry_areas_continuity(self):
        tr, mx = self._worked_mixer()
        self.assertTrue(math.isclose(mx["A_f"], 0.004013, rel_tol=1e-3))
        self.assertTrue(math.isclose(mx["A_g"], 0.003844, rel_tol=1e-3))
        self.assertTrue(math.isclose(mx["A"], mx["A_f"] + mx["A_g"],
                                     rel_tol=1e-12))
        # Continuity check per stream: m = rho*A*v with rho = p/(r*T_s).
        rho_f = mx["p_s"] / (R_C * mx["T_s_f"])
        self.assertTrue(math.isclose(rho_f * mx["A_f"] * mx["v_f"],
                                     tr["m_fan"], rel_tol=1e-9))

    def test_mixer_mixed_gas_properties(self):
        tr, mx = self._worked_mixer()
        m_tot = tr["m_fan"] + tr["m_core"]
        cp_exp = (tr["m_fan"] * CP_C + tr["m_core"] * CP_G) / m_tot
        r_exp = (tr["m_fan"] * R_C + tr["m_core"] * R_G) / m_tot
        self.assertTrue(math.isclose(mx["cp_mix"], 1096.4648, rel_tol=1e-6))
        self.assertTrue(math.isclose(mx["r_mix"], 287.368140, rel_tol=1e-6))
        self.assertTrue(math.isclose(mx["cp_mix"], cp_exp, rel_tol=1e-12))
        self.assertTrue(math.isclose(mx["r_mix"], r_exp, rel_tol=1e-12))
        self.assertTrue(math.isclose(mx["gamma_mix"], 1.355172,
                                     rel_tol=1e-5))

    def test_mixer_energy_balance(self):
        tr, mx = self._worked_mixer()
        num = (tr["m_fan"] * CP_C * tr["tt13"]
               + tr["m_core"] * CP_G * tr["tt5"])
        den = (tr["m_fan"] + tr["m_core"]) * mx["cp_mix"]
        self.assertTrue(math.isclose(mx["tt_mix"], 992.152327, rel_tol=1e-6))
        self.assertTrue(math.isclose(mx["tt_mix"], num / den, rel_tol=1e-12))

    def test_mixer_momentum_balance_subsonic_root(self):
        tr, mx = self._worked_mixer()
        self.assertTrue(math.isclose(mx["v_exit"], 356.787259, rel_tol=1e-6))
        self.assertTrue(math.isclose(mx["p_exit"], 155617.8612,
                                     rel_tol=1e-6))
        self.assertTrue(math.isclose(mx["M_exit"], 0.591555, rel_tol=1e-5))
        self.assertTrue(mx["M_exit"] < 1.0)
        self.assertTrue(math.isclose(mx["T_s_exit"], 934.103428,
                                     rel_tol=1e-6))
        # Residual closure: m_total*v + p*A equals the momentum sum.
        lhs = tr["m_total"] * mx["v_exit"] + mx["p_exit"] * mx["A"]
        rhs = (tr["m_fan"] * mx["v_f"] + tr["m_core"] * mx["v_g"]
               + mx["p_s"] * mx["A"])
        self.assertTrue(math.isclose(lhs, rhs, rel_tol=1e-9))

    def test_mixer_total_pressure_and_loss_ratio(self):
        tr, mx = self._worked_mixer()
        pt_tw = (tr["m_fan"] * tr["pt13"] * PI_DUCT
                 + tr["m_core"] * tr["pt5"]) / tr["m_total"]
        self.assertTrue(math.isclose(mx["pt_mix"], 195867.8819,
                                     rel_tol=1e-6))
        self.assertTrue(math.isclose(mx["pt_tw"], 207854.6290,
                                     rel_tol=1e-6))
        self.assertTrue(math.isclose(mx["pt_tw"], pt_tw, rel_tol=1e-12))
        self.assertTrue(math.isclose(mx["mixing_loss_ratio"], 0.942331,
                                     rel_tol=1e-5))
        self.assertTrue(mx["mixing_loss_ratio"] < 1.0)

    def test_mixer_rejects_negative_mass_flow(self):
        tr = _worked_traverse()
        with self.assertRaises(ValueError):
            mixing_state(tr["tt13"], tr["pt13"] * PI_DUCT,
                         GAMMA_C, CP_C, R_C, -0.5,
                         tr["tt5"], tr["pt5"], GAMMA_G, CP_G, R_G,
                         tr["m_core"], m_fan_entry=M_FAN_ENTRY)

    def test_mixer_rejects_entry_mach_range(self):
        tr = _worked_traverse()
        for bad in (0.0, 1.0, 1.5):
            with self.assertRaises(ValueError):
                mixing_state(tr["tt13"], tr["pt13"] * PI_DUCT,
                             GAMMA_C, CP_C, R_C, tr["m_fan"],
                             tr["tt5"], tr["pt5"], GAMMA_G, CP_G, R_G,
                             tr["m_core"], m_fan_entry=bad)

    def test_mixer_rejects_sonic_core_entry(self):
        tr = _worked_traverse()
        with self.assertRaises(ValueError):
            mixing_state(tr["tt13"], tr["pt13"] * PI_DUCT,
                         GAMMA_C, CP_C, R_C, tr["m_fan"],
                         tr["tt5"], tr["pt5"], GAMMA_G, CP_G, R_G,
                         tr["m_core"], m_fan_entry=0.5)


class TestCommonNozzle(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, the common convergent nozzle
    expansion of the mixed stream, is exercised by these nozzle tests."""

    @staticmethod
    def _worked_nozzle():
        tr = _worked_traverse()
        _, mx = TestMixer._worked_mixer()
        nz = common_nozzle(mx["tt_mix"], mx["pt_mix"], tr["p0"],
                           mx["gamma_mix"], mx["cp_mix"], mx["r_mix"], CV)
        return tr, mx, nz

    def test_nozzle_choked_regime(self):
        _, mx, nz = self._worked_nozzle()
        npr = mx["pt_mix"] / P0_W
        npr_crit = ((mx["gamma_mix"] + 1.0) / 2.0) \
            ** (mx["gamma_mix"] / (mx["gamma_mix"] - 1.0))
        self.assertTrue(npr > npr_crit)
        self.assertTrue(nz["choked"])
        self.assertEqual(nz["Me"], 1.0)

    def test_nozzle_exit_state(self):
        _, mx, nz = self._worked_nozzle()
        self.assertTrue(math.isclose(nz["Te"], 842.530824, rel_tol=1e-6))
        self.assertTrue(math.isclose(nz["pe"], 104975.5711, rel_tol=1e-6))
        self.assertTrue(math.isclose(
            nz["Te"], mx["tt_mix"] * 2.0 / (mx["gamma_mix"] + 1.0),
            rel_tol=1e-12))

    def test_nozzle_velocity_coefficient_round_trip(self):
        _, _, nz = self._worked_nozzle()
        self.assertTrue(math.isclose(nz["v_ideal"], 572.808364,
                                     rel_tol=1e-6))
        self.assertTrue(math.isclose(nz["v_exit"], 564.216238,
                                     rel_tol=1e-6))
        self.assertTrue(math.isclose(nz["v_exit"] / nz["v_ideal"], CV,
                                     rel_tol=1e-12))

    def test_nozzle_area_per_unit_mass_flow(self):
        _, mx, nz = self._worked_nozzle()
        self.assertTrue(math.isclose(nz["a_by_mdot"], 0.004088,
                                     rel_tol=1e-3))
        expect = mx["r_mix"] * nz["Te"] / (nz["pe"] * nz["v_exit"])
        self.assertTrue(math.isclose(nz["a_by_mdot"], expect, rel_tol=1e-12))

    def test_nozzle_unchoked_regime(self):
        nz = common_nozzle(600.0, 1.5 * 101325.0, 101325.0,
                           GAMMA_C, CP_C, R_C, 0.985)
        self.assertFalse(nz["choked"])
        self.assertTrue(nz["Me"] < 1.0)
        self.assertEqual(nz["pe"], 101325.0)
        # Exit total identity: tt = Te*(1 + 0.5*(gamma-1)*Me^2).
        back = nz["Te"] * (1.0 + 0.2 * nz["Me"] ** 2)
        self.assertTrue(math.isclose(back, 600.0, rel_tol=1e-12))

    def test_nozzle_rejects(self):
        with self.assertRaises(ValueError):
            common_nozzle(600.0, 200000.0, 101325.0, GAMMA_C, CP_C, R_C, 0.0)
        with self.assertRaises(ValueError):
            common_nozzle(600.0, 200000.0, 101325.0, GAMMA_C, CP_C, R_C, 1.5)
        with self.assertRaises(ValueError):
            common_nozzle(-5.0, 200000.0, 101325.0, GAMMA_C, CP_C, R_C, 0.985)


class TestNetThrustAndTsfc(unittest.TestCase):
    """Step 7 of the SKILL.md workflow, the net thrust and TSFC
    bookkeeping of the mixed-flow configuration per unit core air, is
    exercised by these tests."""

    def test_net_thrust_worked(self):
        tr, _, nz = TestCommonNozzle._worked_nozzle()
        F = net_thrust(tr["m_total"], nz["v_exit"], tr["v0"], nz["pe"],
                       tr["p0"], nz["a_by_mdot"])
        self.assertTrue(math.isclose(F, 1046.246808, rel_tol=1e-6))
        a9 = nz["a_by_mdot"] * tr["m_total"]
        expect = tr["m_total"] * (nz["v_exit"] - tr["v0"]) \
            + (nz["pe"] - tr["p0"]) * a9
        self.assertTrue(math.isclose(F, expect, rel_tol=1e-12))

    def test_tsfc_worked(self):
        tr, _, nz = TestCommonNozzle._worked_nozzle()
        F = net_thrust(tr["m_total"], nz["v_exit"], tr["v0"], nz["pe"],
                       tr["p0"], nz["a_by_mdot"])
        tsfc = tr["f"] / F
        self.assertTrue(math.isclose(tsfc, 2.4e-5, rel_tol=1e-2))
        self.assertTrue(math.isclose(tsfc * LBF_PER_HR, 0.8469,
                                     rel_tol=1e-3))

    def test_net_thrust_rejects(self):
        with self.assertRaises(ValueError):
            net_thrust(0.0, 500.0, 250.0, 100000.0, 23835.0, 0.004)


class TestSeparateExhaustBaseline(unittest.TestCase):
    """Step 8 of the SKILL.md workflow, the separate-exhaust baseline
    from the same traverse with per-stream convergent nozzles and the
    mixed-vs-separate F and TSFC ratio comparison, is exercised here."""

    @staticmethod
    def _baseline():
        tr = _worked_traverse()
        fan_nz = common_nozzle(tr["tt13"], tr["pt13"], tr["p0"],
                               GAMMA_C, CP_C, R_C, CV)
        core_nz = common_nozzle(tr["tt5"], tr["pt5"], tr["p0"],
                                GAMMA_G, CP_G, R_G, CV)
        F_fan = net_thrust(tr["m_fan"], fan_nz["v_exit"], tr["v0"],
                           fan_nz["pe"], tr["p0"], fan_nz["a_by_mdot"])
        F_core = net_thrust(tr["m_core"], core_nz["v_exit"], tr["v0"],
                            core_nz["pe"], tr["p0"], core_nz["a_by_mdot"])
        return tr, fan_nz, core_nz, F_fan, F_core

    def test_baseline_per_stream_nozzles(self):
        tr, fan_nz, core_nz, _, _ = self._baseline()
        self.assertTrue(fan_nz["choked"])
        self.assertTrue(core_nz["choked"])
        self.assertTrue(math.isclose(fan_nz["v_exit"], 354.044292,
                                     rel_tol=1e-6))
        self.assertTrue(math.isclose(core_nz["v_exit"], 644.347748,
                                     rel_tol=1e-6))
        # The two jets differ strongly in velocity at this point.
        self.assertTrue(core_nz["v_exit"] > 1.5 * fan_nz["v_exit"])

    def test_baseline_net_thrust(self):
        tr, _, _, F_fan, F_core = self._baseline()
        F_sep = F_fan + F_core
        self.assertTrue(math.isclose(F_sep, 990.685872, rel_tol=1e-6))
        tsfc_sep = tr["f"] / F_sep
        self.assertTrue(math.isclose(tsfc_sep * LBF_PER_HR, 0.8944,
                                     rel_tol=1e-3))

    def test_mixed_vs_separate_comparison(self):
        tr, _, _, F_fan, F_core = self._baseline()
        _, mx, nz = TestCommonNozzle._worked_nozzle()
        F_mix = net_thrust(tr["m_total"], nz["v_exit"], tr["v0"], nz["pe"],
                           tr["p0"], nz["a_by_mdot"])
        F_sep = F_fan + F_core
        f_ratio = F_mix / F_sep
        tsfc_mix = tr["f"] / F_mix
        tsfc_sep = tr["f"] / F_sep
        self.assertTrue(math.isclose(f_ratio, 1.056083, rel_tol=1e-5))
        self.assertTrue(math.isclose(tsfc_mix / tsfc_sep, 0.946895,
                                     rel_tol=1e-5))
        # Mixed-flow exhaust beats the separate-exhaust baseline on both.
        self.assertTrue(F_mix > F_sep)
        self.assertTrue(tsfc_mix < tsfc_sep)


class TestDeterminism(unittest.TestCase):
    """Step 9 of the SKILL.md workflow, the deterministic offline
    verification of the closed-form chain, is exercised here."""

    def test_no_rng_import(self):
        with open(os.path.abspath(__file__).replace("test_mixed_flow_exhaust",
                                                    "mixed_flow_exhaust_logic"),
                  "r") as handle:
            src = handle.read()
        self.assertNotIn("import random", src)
        self.assertNotIn("random.", src)

    def test_bisection_constants(self):
        self.assertEqual(BISECT_TOL, 1e-12)

    def test_repeat_run_identical(self):
        a = _worked_traverse()
        b = _worked_traverse()
        self.assertEqual(a["tt5"], b["tt5"])
        self.assertEqual(a["pt5"], b["pt5"])
        _, mx_a = TestMixer._worked_mixer()
        _, mx_b = TestMixer._worked_mixer()
        self.assertEqual(mx_a["pt_mix"], mx_b["pt_mix"])
        self.assertEqual(mx_a["v_exit"], mx_b["v_exit"])


if __name__ == "__main__":
    unittest.main()
