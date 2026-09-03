"""Contract tests for conjunction_assessment_logic (offline, stdlib).

Run: python3 scripts/test_conjunction_assessment.py
Covers the spec worked examples, boundary cases, ValueError rejection,
and the perpendicular miss identity (miss vector orthogonal to the
relative velocity at TCA).
"""

import math
import unittest

import conjunction_assessment_logic as ca

CLOSING = ([5000.0, -3000.0, 2000.0], [-7.0, 1.0, -0.5])


class TestTca(unittest.TestCase):
    def test_tca_worked_example(self):
        # dot(r,v) = -39000, dot(v,v) = 50.25 -> tca 776.1 s.
        self.assertAlmostEqual(ca.tca_s(*CLOSING), 776.1, delta=0.5)

    def test_tca_head_on_closing_positive(self):
        # 10 m ahead closing at 1 m/s: closest approach in 10 s.
        self.assertAlmostEqual(ca.tca_s([10, 0, 0], [-1, 0, 0]), 10.0, places=6)

    def test_tca_receding_negative(self):
        # Same direction as the velocity: closest approach was in the past.
        self.assertAlmostEqual(ca.tca_s([10, 0, 0], [1, 0, 0]), -10.0, places=6)

    def test_tca_perpendicular_geometry_zero(self):
        # Position orthogonal to the velocity: range rate already zero.
        self.assertEqual(ca.tca_s([0, 50, 0], [-1, 0, 0]), 0.0)

    def test_tca_zero_velocity_raises(self):
        with self.assertRaises(ValueError):
            ca.tca_s([1, 0, 0], [0, 0, 0])

class TestMissDistance(unittest.TestCase):
    def test_miss_worked_example(self):
        self.assertAlmostEqual(ca.miss_distance_m(*CLOSING,
                              ca.tca_s(*CLOSING)), 2780.5, delta=1.0)

    def test_miss_head_on_zero(self):
        self.assertAlmostEqual(ca.miss_distance_m([10, 0, 0], [-1, 0, 0], 10.0),
                               0.0, places=6)

    def test_miss_perpendicular_offset_50(self):
        # Position [0, 50, 0], closing along x: TCA 0, miss 50 m.
        self.assertAlmostEqual(ca.miss_distance_m([0, 50, 0], [-1, 0, 0], 0.0),
                               50.0, places=6)

    def test_miss_vector_orthogonal_to_velocity_identity(self):
        # At TCA the miss vector is perpendicular to the relative
        # velocity, so dot(r + v*tca, v) = 0 (round-trip identity).
        r, v = CLOSING
        tca = ca.tca_s(r, v)
        at_tca = [r[i] + v[i] * tca for i in range(3)]
        self.assertAlmostEqual(sum(a * b for a, b in zip(at_tca, v)),
                               0.0, places=3)


class TestEncounterSigma(unittest.TestCase):
    def test_encounter_sigma_circular_projection(self):
        # Circular approximation: encounter-plane sigma equals the
        # combined 1-sigma value.
        self.assertEqual(ca.encounter_sigma(100.0), 100.0)

    def test_encounter_sigma_nonpositive_raises(self):
        with self.assertRaises(ValueError):
            ca.encounter_sigma(0.0)
        with self.assertRaises(ValueError):
            ca.encounter_sigma(-25.0)


class TestProbabilityOfCollision(unittest.TestCase):
    def test_pc_large_miss_negligible(self):
        # Miss 2780.5 m, sigma 100, hard body 5: exponent huge
        # negative, Pc below 1e-12.
        pc = ca.probability_of_collision(2780.529, 100.0, 5.0)
        self.assertLess(pc, 1e-12)

    def test_pc_head_on_1p25e3(self):
        # Miss 0, sigma 100, hard body 5: Pc = 25/20000 = 1.25e-3.
        self.assertAlmostEqual(ca.probability_of_collision(0.0, 100.0, 5.0),
                               1.25e-3, delta=1e-6)

    def test_pc_offset_50m_1p103e3(self):
        # Miss 50 m: exp(-2500/20000) * 0.00125 = 1.103e-3.
        self.assertAlmostEqual(ca.probability_of_collision(50.0, 100.0, 5.0),
                               1.103e-3, delta=1e-6)

    def test_pc_zero_miss_equals_hard_body_term(self):
        # At zero miss the exponential is one: Pc = hb^2 / (2*sigma^2).
        self.assertEqual(ca.probability_of_collision(0.0, 100.0, 5.0),
                         25.0 / 20000.0)

    def test_pc_scales_with_hard_body_squared(self):
        # Doubling the hard body radius quadruples Pc at equal miss.
        base = ca.probability_of_collision(0.0, 100.0, 5.0)
        doubled = ca.probability_of_collision(0.0, 100.0, 10.0)
        self.assertAlmostEqual(doubled, 4.0 * base, places=12)

    def test_pc_larger_sigma_reduces(self):
        # At miss 0 the Pc scales as 1/sigma^2.
        sigma100 = ca.probability_of_collision(0.0, 100.0, 5.0)
        sigma200 = ca.probability_of_collision(0.0, 200.0, 5.0)
        self.assertAlmostEqual(sigma200, sigma100 / 4.0, places=12)

    def test_pc_negative_sigma_raises(self):
        with self.assertRaises(ValueError):
            ca.probability_of_collision(0.0, 0.0, 5.0)
        with self.assertRaises(ValueError):
            ca.probability_of_collision(0.0, -100.0, 5.0)

    def test_pc_negative_hard_body_raises(self):
        with self.assertRaises(ValueError):
            ca.probability_of_collision(0.0, 100.0, -1.0)

class TestScreenVerdict(unittest.TestCase):
    def test_verdict_actionable_high(self):
        d = ca.screen_verdict(1.25e-3)
        self.assertTrue(d["actionable"])
        self.assertEqual(d["severity"], "high")

    def test_verdict_actionable_at_threshold(self):
        d = ca.screen_verdict(1e-4)
        self.assertTrue(d["actionable"])
        self.assertEqual(d["severity"], "watch")

    def test_verdict_green_below_threshold(self):
        d = ca.screen_verdict(1e-5)
        self.assertFalse(d["actionable"])
        self.assertEqual(d["severity"], "green")

    def test_verdict_custom_threshold(self):
        # Pc 5e-4 against a 1e-3 threshold: not actionable, watch band.
        d = ca.screen_verdict(5e-4, threshold=1e-3)
        self.assertFalse(d["actionable"])
        self.assertEqual(d["severity"], "watch")

    def test_verdict_negative_pc_raises(self):
        with self.assertRaises(ValueError):
            ca.screen_verdict(-1e-5)

    def test_verdict_nonpositive_threshold_raises(self):
        with self.assertRaises(ValueError):
            ca.screen_verdict(1e-3, threshold=0.0)


class TestAnalyze(unittest.TestCase):
    def test_analyze_worked_example_green(self):
        d = ca.analyze([5000, -3000, 2000], [-7.0, 1.0, -0.5], 100.0)
        self.assertAlmostEqual(d["tca"], 776.1, delta=0.5)
        self.assertAlmostEqual(d["miss_m"], 2780.5, delta=1.0)
        self.assertEqual(d["sigma_m"], 100.0)
        self.assertLess(d["pc"], 1e-12)
        self.assertFalse(d["actionable"])
        self.assertEqual(d["severity"], "green")
        self.assertTrue(d["valid_approximation"])

    def test_analyze_near_miss_high(self):
        d = ca.analyze([10, 0, 0], [-1, 0, 0], 100.0)
        self.assertAlmostEqual(d["tca"], 10.0, places=6)
        self.assertAlmostEqual(d["miss_m"], 0.0, places=6)
        self.assertAlmostEqual(d["pc"], 1.25e-3, delta=1e-6)
        self.assertTrue(d["actionable"])
        self.assertEqual(d["severity"], "high")

    def test_analyze_offset_50m_high(self):
        # Perpendicular offset geometry realizing miss 50 m: the radial
        # relative position sits 50 m off the closing velocity axis.
        d = ca.analyze([0, 50, 0], [-1, 0, 0], 100.0)
        self.assertAlmostEqual(d["miss_m"], 50.0, places=6)
        self.assertAlmostEqual(d["pc"], 1.103e-3, delta=1e-6)
        self.assertTrue(d["actionable"])
        self.assertEqual(d["severity"], "high")

    def test_analyze_validity_flag_false(self):
        # Hard body 15 m with sigma 100: ratio 0.15 above the 0.1 small
        # hard-body validity limit, flag False while Pc still computes.
        d = ca.analyze([10, 0, 0], [-1, 0, 0], 100.0,
                       hard_body_radius_m=15.0)
        self.assertFalse(d["valid_approximation"])
        self.assertAlmostEqual(d["pc"], 225.0 / 20000.0, places=9)

    def test_analyze_validity_flag_boundary(self):
        # Hard body 10 m with sigma 100: ratio exactly 0.1, valid.
        d = ca.analyze([10, 0, 0], [-1, 0, 0], 100.0,
                       hard_body_radius_m=10.0)
        self.assertTrue(d["valid_approximation"])

    def test_analyze_zero_hard_body_green(self):
        # Two point objects: Pc zero, green screen.
        d = ca.analyze([10, 0, 0], [-1, 0, 0], 100.0,
                       hard_body_radius_m=0.0)
        self.assertEqual(d["pc"], 0.0)
        self.assertEqual(d["severity"], "green")

    def test_analyze_returns_expected_keys(self):
        d = ca.analyze([5000, -3000, 2000], [-7.0, 1.0, -0.5], 100.0)
        self.assertEqual(set(d.keys()),
                         {"tca", "miss_m", "sigma_m", "pc", "actionable",
                          "severity", "valid_approximation"})

    def test_analyze_zero_velocity_raises(self):
        with self.assertRaises(ValueError):
            ca.analyze([1, 0, 0], [0, 0, 0], 100.0)

    def test_analyze_nonpositive_sigma_raises(self):
        with self.assertRaises(ValueError):
            ca.analyze([10, 0, 0], [-1, 0, 0], 0.0)

    def test_analyze_negative_hard_body_raises(self):
        with self.assertRaises(ValueError):
            ca.analyze([10, 0, 0], [-1, 0, 0], 100.0,
                       hard_body_radius_m=-2.0)


if __name__ == "__main__":
    unittest.main()
