"""Contract test for deep_stall_analysis_logic (flight-mechanics/stability-control/deep-stall-analysis).

Offline deterministic stdlib unittest. Run with:
    python3 scripts/test_deep_stall_analysis.py

Recorded module values for the TYPICAL_TTAIL_TRANSPORT worked example
(T-tail transport-like airplane: clmax 1.5, a_w 5.7, cm0_wb 0.02,
cm_alpha_wb -0.6, v_h 0.9, a_t 4.2, eta_t0 0.9, eta_blank 0.25,
alpha_wake_deg 20.0, d_eps_dalpha 0.35, sep_contrib 3.0,
cm_delta -1.1, delta_e_max_deg -25.0):

- stall_angle_deg        = 17.077836842105263  deg
- blanking_factor(25.0)  = 0.6388888888888888
- blanking_factor(35.0)  = 0.2777777777777778
- separation_pitch_up at 45 deg = 1.4620016707310528
- cm_total at 45 deg     = +0.5283315421060526
- cm_at_stall            = -0.8179490374079309
- find_deep_stall_trim   = 58.77010600344884   deg (root in [55.0, 60.0])
- lock_depth_deg         = 41.692269161343575  deg
- recovery_margin        = -0.24899844415757483 (alpha lock; max_down 0.4799658
                           vs pitch-up hump peak 0.7289641941575749)
- eta_blank 0.9 sanity:  lock None, recovery_margin inf, deep_stall False
- cm_delta -1.6 / delta_e_max_deg -30 recovery: margin +0.10879420584242527
"""

import unittest

import deep_stall_analysis_logic as dsa

TOL = 1e-6


def _inputs(**overrides):
    data = dict(dsa.TYPICAL_TTAIL_TRANSPORT)
    data.update(overrides)
    return data


class TestStallAngle(unittest.TestCase):
    def test_stall_angle_worked_example(self):
        self.assertAlmostEqual(
            dsa.stall_angle_deg(1.5, 5.7), 17.077836842105263, places=6
        )
        self.assertLess(abs(dsa.stall_angle_deg(1.5, 5.7) - 17.08), 0.01)

    def test_stall_angle_scales_with_clmax(self):
        # Doubling clmax at fixed slope doubles the linear part only.
        expected = (3.0 / 5.7) * dsa.R2D + dsa.VISC_STALL_SHIFT_DEG
        self.assertAlmostEqual(dsa.stall_angle_deg(3.0, 5.7), expected, places=9)


class TestBlankingFactor(unittest.TestCase):
    def setUp(self):
        self.inp = _inputs()
        self.ratio = self.inp["eta_blank"] / self.inp["eta_t0"]  # 0.2777...

    def test_blanking_below_wake_is_one(self):
        self.assertEqual(
            dsa.blanking_factor(10.0, self.inp["alpha_wake_deg"], self.ratio), 1.0
        )

    def test_blanking_at_wake_is_one(self):
        self.assertEqual(
            dsa.blanking_factor(20.0, self.inp["alpha_wake_deg"], self.ratio), 1.0
        )

    def test_blanking_mid_ramp(self):
        self.assertAlmostEqual(
            dsa.blanking_factor(25.0, self.inp["alpha_wake_deg"], self.ratio),
            0.6388888888888888,
            places=9,
        )

    def test_blanking_at_ramp_end(self):
        self.assertAlmostEqual(
            dsa.blanking_factor(30.0, self.inp["alpha_wake_deg"], self.ratio),
            0.2777777777777778,
            places=9,
        )

    def test_blanking_fully_blanked_above_ramp(self):
        self.assertAlmostEqual(
            dsa.blanking_factor(35.0, self.inp["alpha_wake_deg"], self.ratio),
            0.2777777777777778,
            places=9,
        )

    def test_blanking_never_blanked_ratio_one(self):
        # eta_blank == eta_t0 (0.9) keeps the factor at exactly 1.0.
        self.assertEqual(dsa.blanking_factor(60.0, 20.0, 1.0), 1.0)


class TestSeparationPitchUp(unittest.TestCase):
    def setUp(self):
        self.inp = _inputs()
        self.stall_r = dsa.stall_angle_deg(
            self.inp["clmax"], self.inp["a_w"]
        ) * dsa.D2R

    def test_separation_zero_below_stall(self):
        self.assertEqual(
            dsa.separation_pitch_up(self.stall_r - 0.1, self.stall_r, 3.0), 0.0
        )

    def test_separation_rise_linear_at_45_deg(self):
        # Worked example: x = 0.48733 rad < 0.6, sep = 3.0 * x.
        sep = dsa.separation_pitch_up(45.0 * dsa.D2R, self.stall_r, 3.0)
        self.assertAlmostEqual(sep, 1.4620016707310528, places=6)
        self.assertLess(abs(sep - 1.4618), 1e-3)

    def test_separation_peak_at_rise_end(self):
        sep = dsa.separation_pitch_up(self.stall_r + 0.6, self.stall_r, 3.0)
        self.assertAlmostEqual(sep, 1.8, places=9)

    def test_separation_fade_midpoint(self):
        # x = 0.8: 1.8 * (1 - 0.2/0.4) = 0.9.
        sep = dsa.separation_pitch_up(self.stall_r + 0.8, self.stall_r, 3.0)
        self.assertAlmostEqual(sep, 0.9, places=9)

    def test_separation_zero_at_fade_end(self):
        self.assertAlmostEqual(
            dsa.separation_pitch_up(self.stall_r + 1.0, self.stall_r, 3.0), 0.0,
            places=9,
        )

    def test_separation_zero_after_fade(self):
        self.assertEqual(
            dsa.separation_pitch_up(self.stall_r + 1.2, self.stall_r, 3.0), 0.0
        )


class TestCmTotal(unittest.TestCase):
    def setUp(self):
        self.inp = _inputs()

    def test_cm_total_positive_in_deep_stall_band(self):
        # 45 deg: wake-blanked tail + separated-flow pitch-up give Cm > 0.
        cm = dsa.cm_total(45.0, self.inp)
        self.assertGreater(cm, 0.0)
        self.assertAlmostEqual(cm, 0.5283315421060526, places=6)
        self.assertLess(abs(cm - 0.528), 1e-3)

    def test_cm_at_stall_negative(self):
        self.assertLess(dsa.cm_at_stall(self.inp), 0.0)
        self.assertAlmostEqual(
            dsa.cm_at_stall(self.inp), -0.8179490374079309, places=6
        )


class TestFindDeepStallTrim(unittest.TestCase):
    def setUp(self):
        self.inp = _inputs()

    def test_root_value_and_range(self):
        root = dsa.find_deep_stall_trim(self.inp)
        self.assertIsNotNone(root)
        self.assertAlmostEqual(root, 58.77010600344884, places=6)
        self.assertTrue(55.0 <= root <= 60.0)

    def test_root_deterministic(self):
        root1 = dsa.find_deep_stall_trim(self.inp)
        root2 = dsa.find_deep_stall_trim(self.inp)
        self.assertLess(abs(root1 - root2), 1e-9)

    def test_root_is_cm_crossing(self):
        root = dsa.find_deep_stall_trim(self.inp)
        self.assertIsNotNone(root)
        # Stable high-alpha trim: Cm crosses from positive back to negative.
        self.assertGreater(dsa.cm_total(root - 0.5, self.inp), 0.0)
        self.assertLess(dsa.cm_total(root + 0.5, self.inp), 0.0)
        self.assertLess(abs(dsa.cm_total(root, self.inp)), 1e-6)

    def test_no_root_when_tail_never_blanked(self):
        sane = _inputs(eta_blank=0.9)  # blank ratio 1.0, tail keeps authority
        self.assertIsNone(dsa.find_deep_stall_trim(sane))


class TestLockDepth(unittest.TestCase):
    def test_lock_depth_worked_example(self):
        depth = dsa.lock_depth_deg(58.77010600344884, 17.077836842105263)
        self.assertAlmostEqual(depth, 41.692269161343575, places=6)
        self.assertTrue(35.0 <= depth <= 45.0)

    def test_lock_depth_zero_when_below_stall(self):
        self.assertEqual(dsa.lock_depth_deg(10.0, 17.0), 0.0)


class TestRecoveryMargin(unittest.TestCase):
    def setUp(self):
        self.inp = _inputs()

    def test_margin_negative_typical(self):
        margin = dsa.recovery_margin(self.inp, 58.77010600344884)
        self.assertLess(margin, 0.0)
        self.assertAlmostEqual(margin, -0.24899844415757483, places=6)

    def test_margin_infinite_without_lock(self):
        self.assertEqual(dsa.recovery_margin(self.inp, None), float("inf"))

    def test_margin_positive_with_strong_elevator(self):
        strong = _inputs(cm_delta=-1.6, delta_e_max_deg=-30.0)
        margin = dsa.recovery_margin(strong, 58.77010600344884)
        self.assertGreater(margin, 0.0)
        self.assertAlmostEqual(margin, 0.10879420584242527, places=6)


class TestAnalyze(unittest.TestCase):
    def setUp(self):
        self.inp = _inputs()

    def test_analyze_alpha_lock_verdict(self):
        res = dsa.analyze(self.inp)
        self.assertTrue(res["deep_stall"])
        self.assertTrue(res["alpha_lock"])
        self.assertEqual(res["verdict"], "deep-stall alpha lock, elevator insufficient")
        self.assertAlmostEqual(res["blanking_at_lock"], 0.2777777777777778, places=9)

    def test_analyze_sanity_no_deep_stall(self):
        res = dsa.analyze(_inputs(eta_blank=0.9))
        self.assertIsNone(res["alpha_lock_deg"])
        self.assertFalse(res["deep_stall"])
        self.assertFalse(res["alpha_lock"])
        self.assertEqual(res["recovery_margin"], float("inf"))
        self.assertEqual(res["lock_depth_deg"], 0.0)
        self.assertEqual(res["verdict"], "no deep-stall trim")

    def test_analyze_elevator_recovers(self):
        res = dsa.analyze(_inputs(cm_delta=-1.6, delta_e_max_deg=-30.0))
        self.assertTrue(res["deep_stall"])
        self.assertFalse(res["alpha_lock"])
        self.assertEqual(res["verdict"], "deep-stall trim, elevator recovers")
        self.assertGreater(res["recovery_margin"], 0.0)

    def test_analyze_returns_full_dict(self):
        res = dsa.analyze(self.inp)
        for key in (
            "alpha_stall_deg", "alpha_lock_deg", "lock_depth_deg",
            "blanking_at_lock", "cm_at_stall", "recovery_margin",
            "deep_stall", "alpha_lock", "verdict",
        ):
            self.assertIn(key, res)


class TestValueErrors(unittest.TestCase):
    def test_nonpositive_slopes_and_volume(self):
        for overrides in (
            {"clmax": 0.0}, {"clmax": -1.0}, {"a_w": 0.0}, {"v_h": 0.0},
        ):
            with self.assertRaises(ValueError):
                dsa.cm_total(30.0, _inputs(**overrides))

    def test_eta_blank_out_of_range(self):
        for eta_blank in (-0.1, 0.95):  # 0.95 >= eta_t0 0.9
            with self.assertRaises(ValueError):
                dsa.analyze(_inputs(eta_blank=eta_blank))
        for eta_t0 in (0.0, 1.2):
            with self.assertRaises(ValueError):
                dsa.analyze(_inputs(eta_t0=eta_t0))

    def test_control_authority_signs(self):
        for overrides in (
            {"cm_delta": 0.5}, {"cm_delta": 0.0}, {"delta_e_max_deg": 10.0},
            {"cm_alpha_wb": 0.5},
        ):
            with self.assertRaises(ValueError):
                dsa.analyze(_inputs(**overrides))

    def test_flow_term_ranges(self):
        for overrides in (
            {"sep_contrib": 0.0}, {"d_eps_dalpha": 1.2},
            {"d_eps_dalpha": -0.1}, {"alpha_wake_deg": 0.0},
        ):
            with self.assertRaises(ValueError):
                dsa.cm_total(30.0, _inputs(**overrides))

    def test_bad_bracket(self):
        with self.assertRaises(ValueError):
            dsa.find_deep_stall_trim(_inputs(), lo_deg=50.0, hi_deg=40.0)

    def test_missing_input_key(self):
        data = _inputs()
        del data["clmax"]
        with self.assertRaises(ValueError):
            dsa.analyze(data)


if __name__ == "__main__":
    unittest.main()
