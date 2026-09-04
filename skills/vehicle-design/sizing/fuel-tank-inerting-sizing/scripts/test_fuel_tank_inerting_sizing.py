"""Contract test for fuel tank inerting sizing logic (wave-36).

Offline, deterministic, stdlib unittest. Run with:
    python3 scripts/test_fuel_tank_inerting_sizing.py
"""

import math
import unittest

import fuel_tank_inerting_sizing_logic as m

C0_AIR = 0.21
C_NEA_DEFAULT = 0.05
SCFM_PER_M3S = 2118.88


class FuelTankInertingSizingTest(unittest.TestCase):

    def test_flow_required_worked_example_m3_s(self):
        # (3.2/300) * ln(0.16/0.04) = 0.014787 m3/s, bound 1e-6.
        r = m.nea_flow_required(3.2, 0.09, 300.0)
        self.assertAlmostEqual(r["flow_m3_s"], 0.014787, delta=1e-6)

    def test_flow_required_worked_example_scfm(self):
        # 0.014787 * 2118.88 = 31.33 SCFM, bound 1e-2.
        r = m.nea_flow_required(3.2, 0.09, 300.0)
        self.assertAlmostEqual(r["flow_scfm"], 31.33, delta=1e-2)

    def test_flow_required_matches_hand_calculation(self):
        expected = (3.2 / 300.0) * math.log(0.16 / 0.04)
        r = m.nea_flow_required(3.2, 0.09, 300.0)
        self.assertAlmostEqual(r["flow_m3_s"], expected, delta=1e-12)

    def test_scfm_conversion_constant(self):
        r = m.nea_flow_required(3.2, 0.09, 300.0)
        self.assertAlmostEqual(
            r["flow_scfm"], r["flow_m3_s"] * SCFM_PER_M3S, delta=1e-9
        )
        self.assertAlmostEqual(SCFM_PER_M3S, 2118.88, delta=1e-9)

    def test_flow_required_dict_keys(self):
        r = m.nea_flow_required(3.2, 0.09, 300.0)
        self.assertEqual(sorted(r.keys()), ["flow_m3_s", "flow_scfm"])

    def test_washout_identity_o2_at_required_flow_is_target(self):
        # C(Q_required, t) == target within 1e-9.
        r = m.nea_flow_required(3.2, 0.09, 300.0)
        c = m.ullage_o2_fraction(3.2, r["flow_m3_s"], 300.0)
        self.assertAlmostEqual(c, 0.09, delta=1e-9)

    def test_washout_time_equals_required_time(self):
        # washout_time at the required flow is 300 s within 1e-6.
        r = m.nea_flow_required(3.2, 0.09, 300.0)
        t = m.washout_time(3.2, r["flow_m3_s"], 0.09)
        self.assertAlmostEqual(t, 300.0, delta=1e-6)

    def test_worked_example_o2_at_time_is_0_09(self):
        # C(300) = 0.05 + 0.16 * exp(-ln 4) = 0.09 exactly.
        s = m.inerting_summary(3.2, 0.09, 300.0, 0.02)
        self.assertAlmostEqual(s["o2_at_time"], 0.09, delta=1e-9)

    def test_summary_dict_keys(self):
        s = m.inerting_summary(3.2, 0.09, 300.0, 0.02)
        self.assertEqual(
            sorted(s.keys()),
            ["capacity_verdict", "flow_m3_s", "flow_scfm", "o2_at_time"],
        )

    def test_summary_flow_matches_flow_required(self):
        r = m.nea_flow_required(3.2, 0.09, 300.0)
        s = m.inerting_summary(3.2, 0.09, 300.0, 0.02)
        self.assertEqual(s["flow_m3_s"], r["flow_m3_s"])
        self.assertEqual(s["flow_scfm"], r["flow_scfm"])

    def test_verdict_pass_at_capacity_0_02(self):
        s = m.inerting_summary(3.2, 0.09, 300.0, 0.02)
        self.assertEqual(s["capacity_verdict"], "PASS")

    def test_verdict_fail_at_capacity_0_01(self):
        s = m.inerting_summary(3.2, 0.09, 300.0, 0.01)
        self.assertEqual(s["capacity_verdict"], "FAIL")

    def test_verdict_pass_at_exact_capacity(self):
        r = m.nea_flow_required(3.2, 0.09, 300.0)
        s = m.inerting_summary(3.2, 0.09, 300.0, r["flow_m3_s"])
        self.assertEqual(s["capacity_verdict"], "PASS")

    def test_doubling_target_delta_halves_flow(self):
        # target delta 0.04 (0.09) to 0.08 (0.13) halves required flow.
        r1 = m.nea_flow_required(3.2, 0.09, 300.0)
        r2 = m.nea_flow_required(3.2, 0.13, 300.0)
        self.assertAlmostEqual(r2["flow_m3_s"], r1["flow_m3_s"] / 2.0, delta=1e-9)

    def test_doubling_time_halves_flow(self):
        r1 = m.nea_flow_required(3.2, 0.09, 300.0)
        r2 = m.nea_flow_required(3.2, 0.09, 600.0)
        self.assertAlmostEqual(r2["flow_m3_s"], r1["flow_m3_s"] / 2.0, delta=1e-9)

    def test_doubling_ullage_doubles_flow(self):
        r1 = m.nea_flow_required(3.2, 0.09, 300.0)
        r2 = m.nea_flow_required(6.4, 0.09, 300.0)
        self.assertAlmostEqual(r2["flow_m3_s"], r1["flow_m3_s"] * 2.0, delta=1e-9)

    def test_ullage_o2_fraction_at_zero_time_is_c0(self):
        c = m.ullage_o2_fraction(3.2, 0.01, 0.0)
        self.assertEqual(c, C0_AIR)

    def test_ullage_o2_fraction_zero_flow_is_c0(self):
        c = m.ullage_o2_fraction(3.2, 0.0, 300.0)
        self.assertEqual(c, C0_AIR)

    def test_o2_fraction_monotonic_decay(self):
        c1 = m.ullage_o2_fraction(3.2, 0.0147871398519455, 100.0)
        c2 = m.ullage_o2_fraction(3.2, 0.0147871398519455, 200.0)
        self.assertGreater(c1, c2)
        self.assertLess(c2, C0_AIR)
        self.assertGreater(c2, C_NEA_DEFAULT)

    def test_o2_fraction_asymptotic_to_c_nea(self):
        c = m.ullage_o2_fraction(3.2, 0.0147871398519455, 1e6)
        self.assertAlmostEqual(c, C_NEA_DEFAULT, delta=1e-6)

    def test_washout_time_scales_with_ullage(self):
        t1 = m.washout_time(3.2, 0.0147871398519455, 0.09)
        t2 = m.washout_time(6.4, 0.0147871398519455, 0.09)
        self.assertAlmostEqual(t2, t1 * 2.0, delta=1e-9)

    def test_washout_round_trip_flow_time(self):
        # flow required then washout_time recovers the required time.
        r = m.nea_flow_required(3.2, 0.09, 300.0)
        t = m.washout_time(3.2, r["flow_m3_s"], 0.09)
        self.assertAlmostEqual(t, 300.0, delta=1e-6)

    def test_valueerror_ullage_non_positive_flow_required(self):
        with self.assertRaises(ValueError):
            m.nea_flow_required(0.0, 0.09, 300.0)
        with self.assertRaises(ValueError):
            m.nea_flow_required(-3.2, 0.09, 300.0)

    def test_valueerror_time_non_positive_flow_required(self):
        with self.assertRaises(ValueError):
            m.nea_flow_required(3.2, 0.09, 0.0)
        with self.assertRaises(ValueError):
            m.nea_flow_required(3.2, 0.09, -300.0)

    def test_valueerror_target_out_of_range(self):
        # target <= c_nea is unreachable, target >= c0 is already air.
        with self.assertRaises(ValueError):
            m.nea_flow_required(3.2, 0.05, 300.0)
        with self.assertRaises(ValueError):
            m.nea_flow_required(3.2, 0.04, 300.0)
        with self.assertRaises(ValueError):
            m.nea_flow_required(3.2, 0.21, 300.0)
        with self.assertRaises(ValueError):
            m.nea_flow_required(3.2, 0.5, 300.0)

    def test_valueerror_non_physical_supply_fractions(self):
        with self.assertRaises(ValueError):
            m.nea_flow_required(3.2, 0.09, 300.0, c_nea=0.0)
        with self.assertRaises(ValueError):
            m.nea_flow_required(3.2, 0.09, 300.0, c_nea=0.22)
        with self.assertRaises(ValueError):
            m.nea_flow_required(3.2, 0.09, 300.0, c0=0.0)
        with self.assertRaises(ValueError):
            m.nea_flow_required(3.2, 0.09, 300.0, c0=1.0)
        with self.assertRaises(ValueError):
            m.nea_flow_required(3.2, 0.09, 300.0, c0=0.21, c_nea=0.21)

    def test_valueerror_negative_time_and_flow_o2_fraction(self):
        with self.assertRaises(ValueError):
            m.ullage_o2_fraction(3.2, 0.01, -1.0)
        with self.assertRaises(ValueError):
            m.ullage_o2_fraction(3.2, -0.01, 300.0)
        with self.assertRaises(ValueError):
            m.ullage_o2_fraction(0.0, 0.01, 300.0)

    def test_valueerror_flow_non_positive_washout_time(self):
        with self.assertRaises(ValueError):
            m.washout_time(3.2, 0.0, 0.09)
        with self.assertRaises(ValueError):
            m.washout_time(3.2, -0.01, 0.09)

    def test_valueerror_non_positive_capacity(self):
        with self.assertRaises(ValueError):
            m.inerting_summary(3.2, 0.09, 300.0, 0.0)
        with self.assertRaises(ValueError):
            m.inerting_summary(3.2, 0.09, 300.0, -0.02)

    def test_custom_nea_fraction_inputs(self):
        # Richer NEA (c_nea = 0.02) needs less flow than 0.05 supply.
        r05 = m.nea_flow_required(3.2, 0.09, 300.0, c_nea=0.05)
        r02 = m.nea_flow_required(3.2, 0.09, 300.0, c_nea=0.02)
        self.assertLess(r02["flow_m3_s"], r05["flow_m3_s"])

    def test_determinism(self):
        r1 = m.nea_flow_required(3.2, 0.09, 300.0)
        r2 = m.nea_flow_required(3.2, 0.09, 300.0)
        self.assertEqual(r1, r2)


if __name__ == "__main__":
    unittest.main()
