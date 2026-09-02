#!/usr/bin/env python3
"""Contract test for flying_qualities_logic (MIL-STD-1797A summary).

Offline, deterministic, stdlib unittest. Asserts known-good engineering
values: the category A class IV short-period Level 1 case (zeta 0.7,
omega 3.0 rad/s), the Level 3 damping case (zeta 0.15), the spiral
Level 2 case (time to double 10 s, category A), the dutch roll
product gating, the phugoid and dutch roll level bands for every
flight phase category, the first-order roll response values, the
overall limiting level, the Cooper-Harper band tie-in, and ValueError
on invalid category, class, and physically invalid inputs.

Run: python3 test_flying_qualities.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import flying_qualities_logic as fql


class TestShortPeriod(unittest.TestCase):
    def test_level1_known_good(self):
        # zeta 0.7 in [0.35, 1.30]; omega 3.0 >= 2.5 min for A/IV.
        v = fql.assess_short_period(
            {"zeta_sp": 0.7, "omega_sp": 3.0}, "A", "IV")
        self.assertEqual(v["level"], 1)
        self.assertEqual(v["verdict"], "PASS")

    def test_low_damping_not_level1(self):
        # zeta 0.15 is below the Level 2 minimum 0.25: Level 3.
        v = fql.assess_short_period(
            {"zeta_sp": 0.15, "omega_sp": 3.0}, "A", "IV")
        self.assertNotEqual(v["level"], 1)
        self.assertEqual(v["level"], 3)
        self.assertEqual(v["verdict"], "FAIL")

    def test_frequency_table(self):
        self.assertAlmostEqual(
            fql.short_period_min_frequency("A", "IV", 1.0), 2.5, places=6)
        self.assertAlmostEqual(
            fql.short_period_min_frequency("A", "I", 1.0), 3.6, places=6)
        self.assertAlmostEqual(
            fql.short_period_min_frequency("A", "III", 1.0), 3.0, places=6)
        self.assertAlmostEqual(
            fql.short_period_min_frequency("B", "IV", 1.0), 1.0, places=6)
        self.assertAlmostEqual(
            fql.short_period_min_frequency("C", "IV", 1.0), 1.0, places=6)
        # Linear interpolation in n/alpha, clamped at 1.0 and 3.0.
        self.assertAlmostEqual(
            fql.short_period_min_frequency("A", "III", 2.0), 4.5, places=6)
        self.assertAlmostEqual(
            fql.short_period_min_frequency("A", "III", 3.0), 6.0, places=6)
        self.assertAlmostEqual(
            fql.short_period_min_frequency("A", "IV", 0.5), 2.5, places=6)

    def test_frequency_deficiency_downgrades(self):
        # 3.0 rad/s is fine for A/IV (min 2.5) but below the A/I min 3.6.
        v1 = fql.assess_short_period(
            {"zeta_sp": 0.7, "omega_sp": 3.0}, "A", "IV")
        v2 = fql.assess_short_period(
            {"zeta_sp": 0.7, "omega_sp": 3.0}, "A", "I")
        self.assertEqual(v1["level"], 1)
        self.assertEqual(v2["level"], 2)

    def test_damping_band_edges(self):
        self.assertEqual(fql.assess_short_period(
            {"zeta_sp": 0.35, "omega_sp": 5.0}, "A", "IV")["level"], 1)
        self.assertEqual(fql.assess_short_period(
            {"zeta_sp": 1.30, "omega_sp": 5.0}, "A", "IV")["level"], 1)
        self.assertEqual(fql.assess_short_period(
            {"zeta_sp": 1.31, "omega_sp": 5.0}, "A", "IV")["level"], 2)
        self.assertEqual(fql.assess_short_period(
            {"zeta_sp": 2.10, "omega_sp": 5.0}, "A", "IV")["level"], 3)


class TestPhugoid(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(fql.assess_phugoid(
            {"zeta_ph": 0.05}, "A", "IV")["level"], 1)
        self.assertEqual(fql.assess_phugoid(
            {"zeta_ph": 0.02}, "A", "IV")["level"], 2)
        self.assertEqual(fql.assess_phugoid(
            {"zeta_ph": 0.0}, "A", "IV")["level"], 2)
        # Divergent phugoid, slow enough: Level 3.
        v = fql.assess_phugoid(
            {"zeta_ph": -0.005, "t2_ph": 60.0}, "A", "IV")
        self.assertEqual(v["level"], 3)
        # T2 computed from zeta and omega_n when not measured:
        # ln(2) / (0.01 * 0.2) = 346.6 s.
        v2 = fql.assess_phugoid(
            {"zeta_ph": -0.01, "omega_ph": 0.2}, "A", "IV")
        self.assertEqual(v2["level"], 3)
        self.assertAlmostEqual(v2["metrics"]["t2_ph"], 346.57, places=1)

    def test_missing_t2_for_divergent_raises(self):
        with self.assertRaises(ValueError):
            fql.assess_phugoid({"zeta_ph": -0.005}, "A", "IV")


class TestDutchRoll(unittest.TestCase):
    def test_category_a_class_iv(self):
        # zeta 0.25 >= 0.19, omega 1.2 >= 1.0, product 0.30 < 0.35: Level 2.
        v = fql.assess_dutch_roll(
            {"zeta_dr": 0.25, "omega_dr": 1.2}, "A", "IV")
        self.assertEqual(v["level"], 2)
        # product 0.375 >= 0.35: Level 1.
        v1 = fql.assess_dutch_roll(
            {"zeta_dr": 0.25, "omega_dr": 1.5}, "A", "IV")
        self.assertEqual(v1["level"], 1)
        # zeta 0.19 / omega 1.0 exactly: product 0.19 < 0.35, Level 2.
        v2 = fql.assess_dutch_roll(
            {"zeta_dr": 0.19, "omega_dr": 1.0}, "A", "IV")
        self.assertEqual(v2["level"], 2)

    def test_category_a_other_classes(self):
        # Class I frequency minimum is 0.4; product still gates.
        v = fql.assess_dutch_roll(
            {"zeta_dr": 0.25, "omega_dr": 1.5}, "A", "I")
        self.assertEqual(v["level"], 1)
        v2 = fql.assess_dutch_roll(
            {"zeta_dr": 0.19, "omega_dr": 0.4}, "A", "I")
        self.assertEqual(v2["level"], 2)

    def test_category_b_and_c(self):
        self.assertEqual(fql.assess_dutch_roll(
            {"zeta_dr": 0.10, "omega_dr": 1.6}, "B", "IV")["level"], 1)
        # zeta 0.08 / omega 0.8: product 0.064 >= Level 2 min 0.05 but
        # below the Level 1 min 0.15: Level 2.
        self.assertEqual(fql.assess_dutch_roll(
            {"zeta_dr": 0.08, "omega_dr": 0.8}, "B", "IV")["level"], 2)
        self.assertEqual(fql.assess_dutch_roll(
            {"zeta_dr": 0.10, "omega_dr": 1.6}, "C", "III")["level"], 1)

    def test_unstable_and_very_low_damping(self):
        # Negative damping is a divergent mode: fails Level 3.
        self.assertEqual(fql.assess_dutch_roll(
            {"zeta_dr": -0.02, "omega_dr": 1.0}, "A", "IV")["level"], 3)
        self.assertEqual(fql.assess_dutch_roll(
            {"zeta_dr": 0.01, "omega_dr": 1.5}, "B", "IV")["level"], 3)


class TestSpiral(unittest.TestCase):
    def test_level1_times(self):
        self.assertEqual(fql.assess_spiral(
            {"t2_spiral": 20.0}, "A", "IV")["level"], 1)
        self.assertEqual(fql.assess_spiral(
            {"t2_spiral": 25.0}, "A", "IV")["level"], 1)
        self.assertEqual(fql.assess_spiral(
            {"t2_spiral": 12.0}, "B", "IV")["level"], 1)
        self.assertEqual(fql.assess_spiral(
            {"t2_spiral": 25.0}, "C", "IV")["level"], 1)
        # Stable spiral (no divergence): Level 1.
        self.assertEqual(fql.assess_spiral(
            {"t2_spiral": None}, "A", "IV")["level"], 1)

    def test_known_good_level2(self):
        # 10 s < 20 s Level 1 minimum, >= 8 s Level 2 minimum: Level 2.
        v = fql.assess_spiral({"t2_spiral": 10.0}, "A", "IV")
        self.assertEqual(v["level"], 2)
        self.assertEqual(v["verdict"], "FAIL")

    def test_level3(self):
        self.assertEqual(fql.assess_spiral(
            {"t2_spiral": 5.0}, "A", "IV")["level"], 3)


class TestRollMode(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(fql.assess_roll_mode(
            {"tau_roll": 1.0}, "A", "IV")["level"], 1)
        self.assertEqual(fql.assess_roll_mode(
            {"tau_roll": 0.8}, "A", "IV")["level"], 1)
        self.assertEqual(fql.assess_roll_mode(
            {"tau_roll": 1.2}, "A", "IV")["level"], 2)
        self.assertEqual(fql.assess_roll_mode(
            {"tau_roll": 2.0}, "A", "IV")["level"], 3)
        # Category B Level 1 maximum is 1.4 s.
        self.assertEqual(fql.assess_roll_mode(
            {"tau_roll": 1.4}, "B", "IV")["level"], 1)
        self.assertEqual(fql.assess_roll_mode(
            {"tau_roll": 2.0}, "B", "IV")["level"], 2)
        # Category C Level 2 maximum is 1.4 s.
        self.assertEqual(fql.assess_roll_mode(
            {"tau_roll": 1.5}, "C", "IV")["level"], 3)


class TestRollPerformance(unittest.TestCase):
    def test_first_order_response_metrics(self):
        # p_ss 100 deg/s, tau 0.5 s: phi(1 s) = 56.77 deg.
        v = fql.assess_roll_performance(
            {"roll_rate_ss": 100.0, "roll_mode_tau": 0.5}, "A", "I")
        self.assertAlmostEqual(v["metrics"]["phi_1s"], 56.77, places=2)
        self.assertAlmostEqual(v["metrics"]["t_60"], 1.04, places=2)
        self.assertAlmostEqual(v["metrics"]["t_90"], 1.37, places=2)
        self.assertEqual(v["level"], 1)

    def test_class_iii_relaxation(self):
        # About 1.47 s to 60 deg: Level 1 for class III (1.7 s max),
        # Level 2 for classes I/II/IV (1.3 s max). Model: p_ss 60 deg/s,
        # tau 0.5 s.
        v3 = fql.assess_roll_performance(
            {"roll_rate_ss": 60.0, "roll_mode_tau": 0.5}, "A", "III")
        v1 = fql.assess_roll_performance(
            {"roll_rate_ss": 60.0, "roll_mode_tau": 0.5}, "A", "I")
        self.assertEqual(v3["level"], 1)
        self.assertEqual(v1["level"], 2)
        self.assertAlmostEqual(v3["metrics"]["t_60"], 1.47, places=2)

    def test_measured_override_and_level2(self):
        # p_ss 50 deg/s, tau 0.5 s: t_60 about 1.68 s -> Level 2.
        v = fql.assess_roll_performance(
            {"roll_rate_ss": 50.0, "roll_mode_tau": 0.5}, "A", "I")
        self.assertEqual(v["level"], 2)
        self.assertAlmostEqual(v["metrics"]["phi_1s"], 28.38, places=2)
        # Measured value overrides the model.
        v2 = fql.assess_roll_performance(
            {"roll_rate_ss": 50.0, "roll_mode_tau": 0.5,
             "t_60_measured": 1.1}, "A", "I")
        self.assertEqual(v2["level"], 1)

    def test_category_b_not_applicable(self):
        v = fql.assess_roll_performance(
            {"roll_rate_ss": 100.0, "roll_mode_tau": 0.5}, "B", "I")
        self.assertIsNone(v["level"])
        self.assertEqual(v["verdict"], "N/A")
        self.assertAlmostEqual(v["metrics"]["phi_1s"], 56.77, places=2)


class TestOverall(unittest.TestCase):
    def _all_level1_state(self):
        return {
            "zeta_sp": 0.7, "omega_sp": 3.0, "n_over_alpha": 1.0,
            "zeta_ph": 0.05,
            "zeta_dr": 0.25, "omega_dr": 1.5,
            "t2_spiral": 25.0,
            "tau_roll": 0.8,
            "roll_rate_ss": 100.0, "roll_mode_tau": 0.5,
        }

    def test_overall_level1(self):
        o = fql.overall_flying_qualities_level(
            self._all_level1_state(), "A", "IV")
        self.assertEqual(o["level"], 1)
        self.assertEqual(o["cooper_harper_band"], (1, 3))
        self.assertEqual(len(o["assessments"]), 6)

    def test_overall_limiting_level2(self):
        state = self._all_level1_state()
        state["t2_spiral"] = 10.0  # Level 2 spiral
        o = fql.overall_flying_qualities_level(state, "A", "IV")
        self.assertEqual(o["level"], 2)
        self.assertEqual(o["limiting_modes"], ["spiral"])
        self.assertEqual(o["cooper_harper_band"], (4, 6))

    def test_overall_limiting_level3(self):
        state = self._all_level1_state()
        state["zeta_sp"] = 0.15  # Level 3 short period
        o = fql.overall_flying_qualities_level(state, "A", "IV")
        self.assertEqual(o["level"], 3)
        self.assertIn("short_period", o["limiting_modes"])
        self.assertEqual(o["cooper_harper_band"], (7, 9))

    def test_combine_levels_skips_not_applicable(self):
        assessments = {
            "roll_performance": {"level": None},
            "spiral": {"level": 1},
        }
        level, limiting = fql.combine_levels(assessments)
        self.assertEqual(level, 1)
        self.assertEqual(limiting, ["spiral"])


class TestValidation(unittest.TestCase):
    def test_invalid_category_raises(self):
        with self.assertRaises(ValueError):
            fql.assess_short_period({"zeta_sp": 0.7, "omega_sp": 3.0},
                                    "D", "IV")
        with self.assertRaises(ValueError):
            fql.assess_dutch_roll({"zeta_dr": 0.25, "omega_dr": 1.5},
                                  "D", "IV")
        with self.assertRaises(ValueError):
            fql.overall_flying_qualities_level(
                {"zeta_sp": 0.7, "omega_sp": 3.0}, "A", "IV")

    def test_invalid_class_raises(self):
        with self.assertRaises(ValueError):
            fql.assess_short_period({"zeta_sp": 0.7, "omega_sp": 3.0},
                                    "A", "V")
        with self.assertRaises(ValueError):
            fql.assess_roll_performance(
                {"roll_rate_ss": 100.0, "roll_mode_tau": 0.5}, "A", "X")

    def test_invalid_values_raise(self):
        # Non-numeric damping is invalid input.
        with self.assertRaises(ValueError):
            fql.assess_short_period({"zeta_sp": "low", "omega_sp": 3.0},
                                    "A", "IV")
        with self.assertRaises(ValueError):
            fql.assess_short_period({"zeta_sp": 0.7}, "A", "IV")
        with self.assertRaises(ValueError):
            fql.assess_short_period({"zeta_sp": 0.7, "omega_sp": 0.0},
                                    "A", "IV")
        with self.assertRaises(ValueError):
            fql.assess_dutch_roll({"zeta_dr": 0.25}, "A", "IV")
        with self.assertRaises(ValueError):
            fql.assess_roll_mode({"tau_roll": -1.0}, "A", "IV")
        with self.assertRaises(ValueError):
            fql.assess_roll_performance(
                {"roll_rate_ss": 0.0, "roll_mode_tau": 0.5}, "A", "I")
        with self.assertRaises(ValueError):
            fql.assess_phugoid({"zeta_ph": "low"}, "A", "IV")

    def test_divergent_modes_grade_level3(self):
        # Negative damping is a divergent mode: graded Level 3, not an
        # exception (the level framework caps at 3).
        self.assertEqual(fql.assess_short_period(
            {"zeta_sp": -0.1, "omega_sp": 3.0}, "A", "IV")["level"], 3)
        self.assertEqual(fql.assess_dutch_roll(
            {"zeta_dr": -0.05, "omega_dr": 1.0}, "A", "IV")["level"], 3)


class TestCooperHarperTieIn(unittest.TestCase):
    def test_bands(self):
        self.assertEqual(fql.COOPER_HARPER_BANDS[1], (1, 3))
        self.assertEqual(fql.COOPER_HARPER_BANDS[2], (4, 6))
        self.assertEqual(fql.COOPER_HARPER_BANDS[3], (7, 9))

    def test_descriptions(self):
        self.assertIn("precision", fql.CATEGORY_DESCRIPTIONS["A"])
        self.assertIn("gradual", fql.CATEGORY_DESCRIPTIONS["B"])
        self.assertIn("takeoff", fql.CATEGORY_DESCRIPTIONS["C"])
        self.assertIn("fighter", fql.CLASS_DESCRIPTIONS["IV"])
        self.assertIn("workload", fql.LEVEL_DESCRIPTIONS[2])


if __name__ == "__main__":
    unittest.main(verbosity=2)
