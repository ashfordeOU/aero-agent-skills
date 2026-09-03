"""Contract test for the pitch bandwidth and phase-delay criterion leaf.

Offline, deterministic, stdlib unittest.  Run with:

    python3 scripts/test_pitch_bandwidth_criteria.py

Covers the MIL-STD-1797A style pitch bandwidth evaluation on the short
period pitch attitude transfer function with control anticipation
numerator time constant and actuator lag: worked examples A and B from
the leaf spec, low damping and low frequency cases, the gain margin
branch, the numeric unwrap and bisection helpers, magnitude and phase
self consistency, verdict boundaries and ValueError rejection.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pitch_bandwidth_criteria_logic as pbw

# Worked example Case A: wn 4.0, zeta 0.7, T_th2 0.5, w_act 25.
A_WN, A_ZE, A_T2, A_WA = 4.0, 0.7, 0.5, 25.0
# Worked example Case B: wn 3.0, zeta 0.6, T_th2 0.7, w_act 20.
B_WN, B_ZE, B_T2, B_WA = 3.0, 0.6, 0.7, 20.0


class PitchBandwidthCaseATests(unittest.TestCase):
    """Worked example Case A against the spec reference numbers."""

    def test_case_a_w135_within_0p01(self):
        res = pbw.bandwidth(A_WN, A_ZE, A_T2, A_WA)
        self.assertIsNotNone(res["w_135"])
        self.assertTrue(abs(res["w_135"] - 4.58) <= 0.01,
                        "w_135 %r not within 0.01 of 4.58" % res["w_135"])

    def test_case_a_w180_within_0p02(self):
        res = pbw.bandwidth(A_WN, A_ZE, A_T2, A_WA)
        self.assertIsNotNone(res["w_180"])
        self.assertTrue(abs(res["w_180"] - 10.13) <= 0.02,
                        "w_180 %r not within 0.02 of 10.13" % res["w_180"])

    def test_case_a_tau_p_within_0p001(self):
        res = pbw.bandwidth(A_WN, A_ZE, A_T2, A_WA)
        self.assertIsNotNone(res["tau_p"])
        self.assertTrue(abs(res["tau_p"] - 0.0247) <= 0.001,
                        "tau_p %r not within 0.001 of 0.0247" % res["tau_p"])

    def test_case_a_w_gm6_is_none(self):
        # The 6 dB gain margin crossing is not reached in the stability
        # relevant band: gain is far below -6 dB once phase passes -180.
        res = pbw.bandwidth(A_WN, A_ZE, A_T2, A_WA)
        self.assertIsNone(res["w_gm6"])

    def test_case_a_verdict_level1_limiting_bandwidth(self):
        res = pbw.bandwidth(A_WN, A_ZE, A_T2, A_WA)
        ver = pbw.level_verdict(res["omega_BW"], res["tau_p"])
        self.assertEqual(ver["level"], "Level 1")
        self.assertEqual(ver["limiting"], "bandwidth")


class PitchBandwidthCaseBTests(unittest.TestCase):
    """Worked example Case B against the spec reference numbers."""

    def test_case_b_w135_within_0p01(self):
        res = pbw.bandwidth(B_WN, B_ZE, B_T2, B_WA)
        self.assertIsNotNone(res["w_135"])
        self.assertTrue(abs(res["w_135"] - 3.43) <= 0.01,
                        "w_135 %r not within 0.01 of 3.43" % res["w_135"])

    def test_case_b_w180_within_0p02(self):
        res = pbw.bandwidth(B_WN, B_ZE, B_T2, B_WA)
        self.assertIsNotNone(res["w_180"])
        self.assertTrue(abs(res["w_180"] - 7.23) <= 0.02,
                        "w_180 %r not within 0.02 of 7.23" % res["w_180"])

    def test_case_b_tau_p_within_0p001(self):
        res = pbw.bandwidth(B_WN, B_ZE, B_T2, B_WA)
        self.assertIsNotNone(res["tau_p"])
        self.assertTrue(abs(res["tau_p"] - 0.0325) <= 0.001,
                        "tau_p %r not within 0.001 of 0.0325" % res["tau_p"])

    def test_case_b_omega_bw_equals_w135(self):
        res = pbw.bandwidth(B_WN, B_ZE, B_T2, B_WA)
        self.assertEqual(res["omega_BW"], res["w_135"])

    def test_case_b_verdict_level2(self):
        # omega 3.43 is below the Level 1 floor of 3.5 but above 2.5.
        res = pbw.bandwidth(B_WN, B_ZE, B_T2, B_WA)
        ver = pbw.level_verdict(res["omega_BW"], res["tau_p"])
        self.assertEqual(ver["level"], "Level 2")
        self.assertEqual(ver["limiting"], "bandwidth")


class PitchBandwidthTrendTests(unittest.TestCase):
    """Parametric trends required by the leaf spec."""

    def test_low_zeta_phase_drops_faster(self):
        # Lightly damped (zeta 0.35) reaches -135 degrees at a lower
        # frequency than the zeta 0.7 case at the same wn.
        light = pbw.bandwidth(4.0, 0.35, 0.5, 25.0)
        base = pbw.bandwidth(4.0, 0.7, 0.5, 25.0)
        self.assertIsNotNone(light["w_135"])
        self.assertIsNotNone(base["w_135"])
        self.assertLess(light["w_135"], base["w_135"])

    def test_low_wn_level3_bandwidth(self):
        # wn 1.5 gives a bandwidth frequency below the Level 2 floor.
        res = pbw.bandwidth(1.5, 0.7, 0.5, 25.0)
        self.assertIsNotNone(res["omega_BW"])
        self.assertLess(res["omega_BW"], pbw.L2_OMEGA)
        ver = pbw.level_verdict(res["omega_BW"], res["tau_p"])
        self.assertEqual(ver["level"], "Level 3")
        self.assertEqual(ver["limiting"], "bandwidth")

    def test_gain_margin_branch_reached(self):
        # Very low wn with a small gain margin: the -6 dB gain crossing
        # sits beyond the -180 degree phase crossing and is returned.
        res = pbw.bandwidth(0.5, 0.9, 0.2, 25.0)
        self.assertIsNotNone(res["w_gm6"])
        self.assertAlmostEqual(res["w_gm6"], 1.2271, delta=0.05)
        self.assertEqual(res["omega_BW"], res["w_135"])

    def test_bandwidth_dict_has_all_keys(self):
        res = pbw.bandwidth(A_WN, A_ZE, A_T2, A_WA)
        for key in ("w_135", "w_gm6", "omega_BW", "w_180", "tau_p"):
            self.assertIn(key, res)
        self.assertEqual(res["omega_BW"], res["w_135"])


class PhaseAndUnwrapTests(unittest.TestCase):
    """Unwrapped phase helper and numeric unwrap behavior."""

    def test_phase_starts_near_minus_90(self):
        ph = pbw.phase_deg(A_WN, A_ZE, A_T2, A_WA, 0.01)
        self.assertGreater(ph, -95.0)
        self.assertLess(ph, -88.0)
        # Near the origin the complex argument tends to -90 degrees.
        g = pbw.transfer(A_WN, A_ZE, A_T2, A_WA, 1e-6)
        self.assertAlmostEqual(math.degrees(math.atan2(g.imag, g.real)),
                               -90.0, delta=1e-4)

    def test_phase_matches_transfer_principal_angle(self):
        # Unwrapped phase differs from the atan2 principal angle only by
        # an integer multiple of 360 degrees.
        for w in (0.05, 0.5, 4.58, 10.13, 50.0, 150.0):
            g = pbw.transfer(A_WN, A_ZE, A_T2, A_WA, w)
            principal = math.degrees(math.atan2(g.imag, g.real))
            diff = pbw.phase_deg(A_WN, A_ZE, A_T2, A_WA, w) - principal
            self.assertTrue(abs(diff % 360.0) < 1e-9 or
                            abs(diff % 360.0 - 360.0) < 1e-9, diff)

    def test_phase_decreases_over_criterion_band(self):
        # From 1 rad/s upward the unwrapped phase decreases monotonically
        # through the -135 and -180 degree crossings.
        prev = pbw.phase_deg(A_WN, A_ZE, A_T2, A_WA, 1.0)
        w = 2.0
        while w <= 200.0:
            cur = pbw.phase_deg(A_WN, A_ZE, A_T2, A_WA, w)
            self.assertLess(cur, prev)
            prev = cur
            w += 1.0

    def test_analytic_phase_matches_table_unwrap(self):
        # The branch-corrected analytic phase equals the numeric unwrap
        # of the principal phase over the dense sample grid.
        freqs, table = pbw._phase_table(A_WN, A_ZE, A_T2, A_WA)
        worst = 0.0
        for i in range(0, len(freqs), 25):
            worst = max(worst,
                        abs(table[i] - pbw.phase_deg(A_WN, A_ZE, A_T2,
                                                     A_WA, freqs[i])))
        self.assertLess(worst, 1e-6)

    def test_unwrap_helper_wraps_upward_jump_down(self):
        out = pbw.unwrap_phase_deg([-170.0, 179.0, 178.0, -179.0])
        self.assertEqual(out, [-170.0, -181.0, -182.0, -179.0])

    def test_unwrap_helper_keeps_continuous_series(self):
        series = [-90.0, -95.0, -140.0, -185.0, -240.0]
        self.assertEqual(pbw.unwrap_phase_deg(series), series)
        self.assertEqual(pbw.unwrap_phase_deg([]), [])


class RootAndMagnitudeTests(unittest.TestCase):
    """Bisection root finder and magnitude checks."""

    def test_find_root_phase_solves_its_target_in_order(self):
        roots = []
        for target in (-135.0, -180.0, -225.0):
            root = pbw.find_root_phase(A_WN, A_ZE, A_T2, A_WA, target)
            self.assertIsNotNone(root)
            self.assertAlmostEqual(
                pbw.phase_deg(A_WN, A_ZE, A_T2, A_WA, root), target, delta=1e-6)
            roots.append(root)
        self.assertLess(roots[0], roots[1])
        self.assertLess(roots[1], roots[2])

    def test_find_root_phase_unreachable_returns_none(self):
        # Phase floor is about -262 degrees at the top of the band.
        self.assertIsNone(
            pbw.find_root_phase(A_WN, A_ZE, A_T2, A_WA, -300.0))

    def test_mag_db_matches_transfer_magnitude(self):
        for w in (0.05, 1.0, 4.5832, 10.129, 60.0):
            g = pbw.transfer(A_WN, A_ZE, A_T2, A_WA, w)
            self.assertAlmostEqual(pbw.mag_db(A_WN, A_ZE, A_T2, A_WA, w),
                                   20.0 * math.log10(abs(g)), delta=1e-9)

    def test_mag_db_decreases_over_rolloff(self):
        prev = pbw.mag_db(A_WN, A_ZE, A_T2, A_WA, 2.0)
        for w in (4.0, 8.0, 16.0, 32.0, 64.0, 128.0):
            cur = pbw.mag_db(A_WN, A_ZE, A_T2, A_WA, w)
            self.assertLess(cur, prev)
            prev = cur


class VerdictBoundaryTests(unittest.TestCase):
    """Level verdict boundaries and missing metric reporting."""

    def test_verdict_level1_boundary_inclusive(self):
        ver = pbw.level_verdict(pbw.L1_OMEGA, pbw.L1_TAU)
        self.assertEqual(ver["level"], "Level 1")

    def test_verdict_level2_boundaries(self):
        self.assertEqual(pbw.level_verdict(3.49, 0.1)["level"], "Level 2")
        self.assertEqual(pbw.level_verdict(pbw.L2_OMEGA, 0.1)["level"],
                         "Level 2")

    def test_verdict_level3_by_bandwidth_only(self):
        ver = pbw.level_verdict(2.4, 0.1)
        self.assertEqual(ver["level"], "Level 3")
        self.assertEqual(ver["limiting"], "bandwidth")

    def test_verdict_level3_by_phase_delay_only(self):
        ver = pbw.level_verdict(3.6, 0.3)
        self.assertEqual(ver["level"], "Level 3")
        self.assertEqual(ver["limiting"], "phase delay")

    def test_verdict_level3_by_both(self):
        ver = pbw.level_verdict(2.0, 0.3)
        self.assertEqual(ver["level"], "Level 3")
        self.assertEqual(ver["limiting"], "both")

    def test_verdict_reports_missing_metrics(self):
        ver = pbw.level_verdict(None, 0.1)
        self.assertIn("omega_BW", ver["missing"])
        self.assertEqual(ver["level"], "Level 1")
        ver2 = pbw.level_verdict(4.0, None)
        self.assertIn("tau_p", ver2["missing"])
        ver3 = pbw.level_verdict(None, None)
        self.assertEqual(ver3["level"], "Level 3")
        self.assertIn("omega_BW", ver3["missing"])
        self.assertIn("tau_p", ver3["missing"])
        # With both metrics present the missing list stays empty.
        ver4 = pbw.level_verdict(4.58, 0.0247)
        self.assertEqual(ver4["missing"], [])


class ValueErrorTests(unittest.TestCase):
    """Rejection of non-physical model inputs."""

    def test_valueerror_wn_nonpositive(self):
        for wn in (0.0, -1.0):
            with self.assertRaises(ValueError):
                pbw.bandwidth(wn, 0.7, 0.5, 25.0)

    def test_valueerror_zeta_out_of_range(self):
        for zeta in (0.0, -0.2, 1.0, 1.5):
            with self.assertRaises(ValueError):
                pbw.bandwidth(4.0, zeta, 0.5, 25.0)

    def test_valueerror_T_th2_nonpositive(self):
        for t2 in (0.0, -0.5):
            with self.assertRaises(ValueError):
                pbw.bandwidth(4.0, 0.7, t2, 25.0)

    def test_valueerror_w_act_not_above_wn(self):
        for w_act in (4.0, 2.0):
            with self.assertRaises(ValueError):
                pbw.bandwidth(4.0, 0.7, 0.5, w_act)

    def test_valueerror_scalar_functions_reject_bad_frequency(self):
        for fn in (pbw.phase_deg, pbw.mag_db, pbw.transfer):
            for w in (-3.0, 0.0):
                with self.assertRaises(ValueError):
                    fn(4.0, 0.7, 0.5, 25.0, w)


if __name__ == "__main__":
    unittest.main()
