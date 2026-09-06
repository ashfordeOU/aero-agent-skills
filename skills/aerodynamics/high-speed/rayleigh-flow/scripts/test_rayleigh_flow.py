#!/usr/bin/env python3
"""Contract test for the rayleigh-flow leaf (aerodynamics/high-speed).

Exercises step 2 of the SKILL.md workflow, the conversion of the inlet
Mach number into the five Rayleigh-line station ratios, step 3, the
maximum heat addition that thermally chokes the constant-area
frictionless heat-addition duct on either inlet branch, step 4, the
recovery of the exit Mach number after a prescribed heat addition or
heat rejection per unit mass on the inlet's own branch, step 5, the
downstream static and stagnation state build with the second-law
entropy rise, and step 6, the Rayleigh T-s curve offset identity. All
numeric assertions are order-safe: exact float equality is never
asserted on computed aggregates, every check uses math.isclose or an
absolute delta so the suite passes identically under /usr/bin/python3
3.9 and the pyenv 3.13.12 pre-push interpreter.

Anchors: air at gamma 1.4, R 287.0, cp 1004.5 J/(kg K); duct inlet
T1 = 300 K, p1 = 101325 Pa at the dual inlet pair M1 = 0.5 and 2.0.
The thermal-choking heat addition q_max = 141257.8125 J/kg is shared
by both inlets (M to 1/M duality) and the worked example runs at
q = q_max/2 = 70628.90625 J/kg.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rayleigh_flow_logic as rf

GAMMA = 1.4
R = 287.0
CP = rf.CP
T1 = 300.0
P1 = 101325.0
QMAX = rf.heat_addition_maximum(T1, 0.5)
HALF = QMAX / 2.0


class TestStationRatios(unittest.TestCase):
    """Workflow step 2: convert the inlet Mach number into the five
    Rayleigh-line station ratios against the thermal-choking star."""

    def test_published_table_agreement(self):
        # M = 0.5 equals 64/81, 16/9, 9/4, 56/81 and 1.11405250318.
        r = rf.rayleigh_ratios(0.5)
        self.assertTrue(math.isclose(r["t_over_tstar"], 64.0 / 81.0, rel_tol=1e-12))
        self.assertTrue(math.isclose(r["p_over_pstar"], 16.0 / 9.0, rel_tol=1e-12))
        self.assertTrue(math.isclose(r["rho_over_rhostar"], 9.0 / 4.0, rel_tol=1e-12))
        self.assertTrue(math.isclose(r["t0_over_t0star"], 56.0 / 81.0, rel_tol=1e-12))
        self.assertTrue(
            math.isclose(r["p0_over_p0star"], 1.11405250318, rel_tol=1e-9)
        )
        # M = 2.0 equals 64/121, 4/11, 11/16, 96/121 and 1.50309597853.
        r = rf.rayleigh_ratios(2.0)
        self.assertTrue(math.isclose(r["t_over_tstar"], 64.0 / 121.0, rel_tol=1e-12))
        self.assertTrue(math.isclose(r["p_over_pstar"], 4.0 / 11.0, rel_tol=1e-12))
        self.assertTrue(math.isclose(r["rho_over_rhostar"], 11.0 / 16.0, rel_tol=1e-12))
        self.assertTrue(
            math.isclose(r["t0_over_t0star"], 96.0 / 121.0, rel_tol=1e-12)
        )
        self.assertTrue(
            math.isclose(r["p0_over_p0star"], 1.50309597853, rel_tol=1e-9)
        )

    def test_sonic_state_unity_and_dict_keys(self):
        r = rf.rayleigh_ratios(1.0)
        keys = list(r.keys())
        self.assertEqual(
            keys,
            ["t_over_tstar", "p_over_pstar", "rho_over_rhostar",
             "t0_over_t0star", "p0_over_p0star"],
        )
        for key in keys:
            self.assertTrue(math.isclose(r[key], 1.0, rel_tol=1e-12, abs_tol=1e-15))

    def test_density_roundtrip_identity(self):
        # rho/rho* == (p/p*)/(T/T*) exactly closes the three static
        # ratios at any Mach number of the frictionless duct.
        for m in (0.5, 2.0):
            r = rf.rayleigh_ratios(m)
            self.assertTrue(
                math.isclose(r["rho_over_rhostar"],
                             r["p_over_pstar"] / r["t_over_tstar"],
                             rel_tol=1e-12)
            )

    def test_static_temperature_peak(self):
        # T/T* peaks at 36/35 = 1.02857142857 at M = 1/sqrt(gamma).
        m_peak = 1.0 / math.sqrt(GAMMA)
        self.assertTrue(
            math.isclose(rf.rayleigh_ratios(m_peak)["t_over_tstar"],
                         36.0 / 35.0, rel_tol=1e-12)
        )
        for m in (0.5, 0.9, 2.0):
            self.assertLess(rf.rayleigh_ratios(m)["t_over_tstar"], 36.0 / 35.0)


class TestHeatAdditionMaximum(unittest.TestCase):
    """Workflow step 3: find the maximum heat addition q_max that
    thermally chokes the frictionless heat-addition duct."""

    def test_qmax_published_anchor_and_half_choke_heat(self):
        self.assertTrue(math.isclose(QMAX, 141257.8125, rel_tol=1e-9))
        self.assertTrue(math.isclose(HALF, 70628.90625, rel_tol=1e-12))

    def test_qmax_duality_m_to_one_over_m(self):
        # A Mach 0.5 inlet and a Mach 2.0 inlet at the same static
        # temperature choke on the same heat per kilogram.
        self.assertTrue(
            math.isclose(rf.heat_addition_maximum(T1, 0.5),
                         rf.heat_addition_maximum(T1, 2.0), rel_tol=1e-12)
        )

    def test_qmax_closed_form_ratio(self):
        # q_max/(cp*T1) = 0.46875 exactly in the closed form.
        self.assertTrue(math.isclose(QMAX / (CP * T1), 0.46875, rel_tol=1e-12))

    def test_qmax_equals_cp_t0star_minus_t01(self):
        # T0* = 455.625 K for the M = 0.5 case at T1 = 300 K, so
        # q_max = cp*(T0* - T0_1) = cp*140.625 J/kg exactly.
        t0_1 = T1 * (1.0 + 0.5 * (GAMMA - 1.0) * 0.5 ** 2)
        t0_star = 455.625
        self.assertTrue(math.isclose(QMAX, CP * (t0_star - t0_1),
                                     rel_tol=1e-12, abs_tol=1e-9))

    def test_qmax_zero_at_sonic_inlet(self):
        # No heat addition is left at M = 1, the duct is already
        # thermally choked.
        self.assertTrue(
            math.isclose(rf.heat_addition_maximum(T1, 1.0), 0.0, abs_tol=1e-15)
        )


class TestExitMach(unittest.TestCase):
    """Workflow step 4: recover the exit Mach number after a given
    heat addition per unit mass on the inlet's own branch."""

    def test_subsonic_half_choke_exit(self):
        self.assertTrue(math.isclose(rf.exit_mach(T1, 0.5, HALF),
                                     0.625879453912, rel_tol=1e-9))

    def test_supersonic_half_choke_exit(self):
        self.assertTrue(math.isclose(rf.exit_mach(T1, 2.0, HALF),
                                     1.54998945381, rel_tol=1e-9))

    def test_thermal_choke_exit_at_qmax(self):
        # q at the module q_max value chokes either branch at M = 1.
        self.assertTrue(math.isclose(rf.exit_mach(T1, 0.5, QMAX), 1.0,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(rf.exit_mach(T1, 2.0, QMAX), 1.0,
                                     rel_tol=1e-9))

    def test_no_heat_round_trip_inlet_mach(self):
        # q = 0 leaves the station unchanged on either branch.
        self.assertTrue(math.isclose(rf.exit_mach(T1, 0.5, 0.0), 0.5,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(rf.exit_mach(T1, 2.0, 0.0), 2.0,
                                     rel_tol=1e-9))

    def test_heat_addition_branch_drift(self):
        # Heating accelerates the subsonic branch toward 1 and
        # decelerates the supersonic branch toward 1.
        m_sub = rf.exit_mach(T1, 0.5, HALF)
        self.assertGreater(m_sub, 0.5)
        self.assertLessEqual(m_sub, 1.0)
        m_sup = rf.exit_mach(T1, 2.0, HALF)
        self.assertGreaterEqual(m_sup, 1.0)
        self.assertLess(m_sup, 2.0)

    def test_subsonic_rejection_decelerates(self):
        m2 = rf.exit_mach(T1, 0.5, -50000.0)
        self.assertTrue(math.isclose(m2, 0.430803500026, rel_tol=1e-9))
        self.assertLess(m2, 0.5)

    def test_supersonic_rejection_accelerates(self):
        m2 = rf.exit_mach(T1, 2.0, -200000.0)
        self.assertTrue(math.isclose(m2, 12.5126628564, rel_tol=1e-6))
        self.assertGreater(m2, 2.0)

    def test_sonic_inlet_no_heat_returns_one(self):
        self.assertEqual(rf.exit_mach(T1, 1.0, 0.0), 1.0)


class TestHeatAdditionState(unittest.TestCase):
    """Workflow step 5: build the downstream static and stagnation
    station and the second-law entropy rise of the heat addition."""

    def test_subsonic_half_choke_state(self):
        d = rf.heat_addition(T1, P1, 0.5, HALF)
        self.assertTrue(math.isclose(d["m2"], 0.625879453912, rel_tol=1e-9))
        self.assertTrue(math.isclose(d["t2"], 357.318384663, abs_tol=1e-6,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(d["p2"], 88341.1351391, abs_tol=1e-3,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(d["t2_over_t1"], 1.19106128221,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(d["p2_over_p1"], 0.871859216769,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(d["rho2_over_rho1"], 0.732001979908,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(d["t02_over_t01"], 1.22321428571,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(d["p02_over_p01"], 0.957052789099,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(d["ds"], 214.987084722, abs_tol=1e-6,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(d["ds_over_cp"], 0.214023976827,
                                     rel_tol=1e-9))
        self.assertFalse(d["choked"])
        # Heating raises the stagnation temperature and lowers the
        # stagnation pressure in the frictionless duct.
        self.assertGreater(d["t02_over_t01"], 1.0)
        self.assertLess(d["p02_over_p01"], 1.0)

    def test_supersonic_half_choke_state_and_station_ratios(self):
        d = rf.heat_addition(T1, P1, 2.0, HALF)
        self.assertTrue(math.isclose(d["m2"], 1.54998945381, rel_tol=1e-9))
        self.assertTrue(math.isclose(d["t2"], 412.23586319, abs_tol=1e-6,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(d["p2"], 153260.459443, abs_tol=1e-3,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(d["p2_over_p1"], 1.51256313292,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(d["t2_over_t1"], 1.37411954397,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(d["p02_over_p01"], 0.763277518128,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(d["ds"], 200.481131945, abs_tol=1e-6,
                                     rel_tol=1e-9))
        self.assertFalse(d["choked"])
        # Exit station ratios against the star at M2 = 1.55.
        r2 = rf.rayleigh_ratios(d["m2"])
        self.assertTrue(math.isclose(r2["p0_over_p0star"], 1.147279368,
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(r2["t_over_tstar"], 0.72680703152,
                                     rel_tol=1e-9))

    def test_thermal_choke_state(self):
        d = rf.heat_addition(T1, P1, 0.5, QMAX)
        self.assertEqual(d["m2"], 1.0)
        self.assertTrue(d["choked"])
        self.assertTrue(math.isclose(d["p02_over_p01"], 0.897623762925,
                                     rel_tol=1e-9))
        self.assertTrue(
            math.isclose(d["p02_over_p01"],
                         1.0 / rf.rayleigh_ratios(0.5)["p0_over_p0star"],
                         rel_tol=1e-12)
        )

    def test_rejection_state_entropy_falls(self):
        d = rf.heat_addition(T1, P1, 0.5, -50000.0)
        self.assertTrue(math.isclose(d["m2"], 0.430803500026, rel_tol=1e-9))
        self.assertLess(d["m2"], 0.5)
        self.assertLess(d["ds"], 0.0)
        self.assertTrue(math.isclose(d["ds_over_cp"], -0.17940496639,
                                     rel_tol=1e-9))
        self.assertFalse(d["choked"])

    def test_entropy_second_law_identity(self):
        d = rf.heat_addition(T1, P1, 0.5, HALF)
        # ds = cp*ln(T2/T1) - R*ln(p2/p1), both directly and from the
        # absolute exit state through entropy_rise.
        ds_direct = rf.entropy_rise(T1, P1, d["t2"], d["p2"])
        self.assertTrue(math.isclose(d["ds"], ds_direct, rel_tol=1e-12))
        self.assertTrue(
            math.isclose(d["ds"],
                         CP * math.log(d["t2_over_t1"])
                         - R * math.log(d["p2_over_p1"]),
                         rel_tol=1e-9)
        )

    def test_determinism_and_dict_keys(self):
        d1 = rf.heat_addition(T1, P1, 0.5, HALF)
        d2 = rf.heat_addition(T1, P1, 0.5, HALF)
        self.assertEqual(d1, d2)
        self.assertEqual(
            list(d1.keys()),
            ["m2", "t2", "p2", "rho2", "t02", "p02", "t2_over_t1",
             "p2_over_p1", "rho2_over_rho1", "t02_over_t01",
             "p02_over_p01", "ds", "ds_over_cp", "choked"],
        )


class TestRayleighCurveOffset(unittest.TestCase):
    """Workflow step 6: the entropy rise of the heated duct equals the
    climb of the Rayleigh T-s curve offset between the two stations."""

    def test_offset_difference_equals_ds_over_cp(self):
        m2 = rf.exit_mach(T1, 0.5, HALF)
        d = rf.heat_addition(T1, P1, 0.5, HALF)
        diff = rf.rayleigh_curve_offset(m2) - rf.rayleigh_curve_offset(0.5)
        self.assertTrue(math.isclose(diff, d["ds_over_cp"], rel_tol=1e-12))

    def test_offset_shape_and_sonic_maximum(self):
        # The offset is strictly negative off M = 1, zero at the sonic
        # entropy maximum, and matches the explicit second-law form.
        for m in (0.05, 0.2, 0.5, 0.8451542547285166, 1.5, 2.0, 5.0):
            self.assertLess(rf.rayleigh_curve_offset(m), 0.0)
        self.assertTrue(math.isclose(rf.rayleigh_curve_offset(1.0), 0.0,
                                     abs_tol=1e-12))
        r = rf.rayleigh_ratios(2.0)
        expected = (math.log(r["t_over_tstar"])
                    - ((GAMMA - 1.0) / GAMMA) * math.log(r["p_over_pstar"]))
        self.assertTrue(math.isclose(rf.rayleigh_curve_offset(2.0), expected,
                                     rel_tol=1e-12))


class TestValueErrorRejection(unittest.TestCase):
    """Non-physical inputs are rejected across the module functions."""

    def test_rayleigh_ratios_rejects_non_positive_mach(self):
        for m in (0.0, -0.5):
            with self.assertRaises(ValueError):
                rf.rayleigh_ratios(m)

    def test_heat_addition_maximum_rejects_bad_state(self):
        with self.assertRaises(ValueError):
            rf.heat_addition_maximum(0.0, 0.5)
        with self.assertRaises(ValueError):
            rf.heat_addition_maximum(-300.0, 0.5)
        with self.assertRaises(ValueError):
            rf.heat_addition_maximum(300.0, 0.0)

    def test_exit_mach_rejects_above_thermal_choking_limit(self):
        with self.assertRaises(ValueError) as ctx:
            rf.exit_mach(T1, 0.5, 1.01 * QMAX)
        self.assertIn("thermal choking limit", str(ctx.exception))

    def test_exit_mach_rejects_subsonic_cooling_limit(self):
        # q = -cp*315 = -cp*T0_1 for the M = 0.5, T1 = 300 K inlet.
        with self.assertRaises(ValueError):
            rf.exit_mach(T1, 0.5, -CP * 315.0)

    def test_exit_mach_rejects_supersonic_branch_limit(self):
        with self.assertRaises(ValueError) as ctx:
            rf.exit_mach(T1, 2.0, -250000.0)
        self.assertIn("branch limit", str(ctx.exception))

    def test_exit_mach_rejects_sonic_inlet_with_heat(self):
        with self.assertRaises(ValueError):
            rf.exit_mach(T1, 1.0, 1000.0)

    def test_misc_state_valueerrors(self):
        # entropy_rise with t1 = 0 and with p1 = -1, the curve offset
        # at 0, and heat_addition with p_static = 0.
        with self.assertRaises(ValueError):
            rf.entropy_rise(0.0, P1, 400.0, 90000.0)
        with self.assertRaises(ValueError):
            rf.entropy_rise(T1, -1.0, 400.0, 90000.0)
        with self.assertRaises(ValueError):
            rf.rayleigh_curve_offset(0.0)
        with self.assertRaises(ValueError):
            rf.heat_addition(T1, 0.0, 0.5, HALF)


if __name__ == "__main__":
    unittest.main()
