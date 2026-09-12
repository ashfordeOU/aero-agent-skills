import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from critical_location_and_crack_orientation_logic import (
    CrackCandidate,
    rank_candidates,
    select_critical_candidate,
)


class TestStressIntensityFactor(unittest.TestCase):
    def test_sif_basic(self):
        """K = F * sigma * sqrt(pi * a) for a standard surface-crack geometry."""
        c = CrackCandidate("hole-A", "axial", 100.0, 50.0, 0.001)
        expected = 1.12 * 100.0 * math.sqrt(math.pi * 0.001)
        self.assertAlmostEqual(c.stress_intensity_factor(), expected, places=6)

    def test_sif_unit_geometry_factor(self):
        """With F=1.0 the SIF reduces to sigma * sqrt(pi * a)."""
        c = CrackCandidate("hole-B", "circumferential", 200.0, 80.0, 0.002, geometry_factor=1.0)
        expected = 200.0 * math.sqrt(math.pi * 0.002)
        self.assertAlmostEqual(c.stress_intensity_factor(), expected, places=6)

    def test_sif_doubles_when_stress_doubles(self):
        """Doubling the net-section stress doubles the SIF."""
        c1 = CrackCandidate("weld-1", "axial", 50.0, 60.0, 0.001)
        c2 = CrackCandidate("weld-1", "axial", 100.0, 60.0, 0.001)
        self.assertAlmostEqual(c2.stress_intensity_factor(), 2.0 * c1.stress_intensity_factor(), places=6)

    def test_sif_doubles_when_crack_area_quadruples(self):
        """Quadrupling the crack length (4a) doubles K because K ∝ sqrt(a)."""
        c1 = CrackCandidate("corner-1", "radial", 100.0, 60.0, 0.001)
        c2 = CrackCandidate("corner-1", "radial", 100.0, 60.0, 0.004)
        self.assertAlmostEqual(c2.stress_intensity_factor(), 2.0 * c1.stress_intensity_factor(), places=6)

    def test_sif_positive_for_valid_inputs(self):
        """SIF must be strictly positive for any valid set of inputs."""
        c = CrackCandidate("bolt-hole", "transverse", 150.0, 40.0, 0.0005, geometry_factor=1.25)
        self.assertGreater(c.stress_intensity_factor(), 0.0)


class TestFractureMargin(unittest.TestCase):
    def test_margin_positive_when_toughness_exceeds_k(self):
        """MoS > 0 when Kc > K — fracture not predicted."""
        c = CrackCandidate("flange-A", "axial", 50.0, 200.0, 0.001)
        self.assertGreater(c.fracture_margin(), 0.0)

    def test_margin_negative_when_k_exceeds_toughness(self):
        """MoS < 0 when K > Kc — fracture predicted."""
        c = CrackCandidate("flange-B", "axial", 500.0, 5.0, 0.01)
        self.assertLess(c.fracture_margin(), 0.0)

    def test_margin_zero_when_kc_equals_k(self):
        """MoS is exactly 0 when Kc is set equal to the computed K."""
        sigma, a, F = 100.0, 0.001, 1.12
        kc = F * sigma * math.sqrt(math.pi * a)
        c = CrackCandidate("neutral-pt", "transverse", sigma, kc, a, geometry_factor=F)
        self.assertAlmostEqual(c.fracture_margin(), 0.0, places=10)

    def test_margin_formula_mos_equals_kc_over_k_minus_one(self):
        """MoS = Kc/K - 1 is verified against the explicit formula."""
        c = CrackCandidate("web-hole", "oblique", 120.0, 55.0, 0.002, geometry_factor=1.05)
        k = c.stress_intensity_factor()
        expected = 55.0 / k - 1.0
        self.assertAlmostEqual(c.fracture_margin(), expected, places=10)


class TestSelectCritical(unittest.TestCase):
    def test_single_candidate_returned(self):
        """With one candidate that candidate is always the critical one."""
        c = CrackCandidate("only", "axial", 100.0, 50.0, 0.001)
        self.assertIs(select_critical_candidate([c]), c)

    def test_picks_candidate_with_lowest_margin(self):
        """The candidate with the lowest MoS is selected over higher-margin ones."""
        c_high = CrackCandidate("site-safe", "axial", 50.0, 200.0, 0.001)
        c_low  = CrackCandidate("site-crit", "axial", 400.0, 10.0, 0.005)
        self.assertIs(select_critical_candidate([c_high, c_low]), c_low)

    def test_critical_candidate_is_not_always_first(self):
        """Critical candidate can appear at any position, including the last."""
        c1 = CrackCandidate("loc-1", "circumferential", 50.0, 200.0, 0.001)
        c2 = CrackCandidate("loc-2", "axial",           50.0, 200.0, 0.001)
        c3 = CrackCandidate("loc-3", "radial",          300.0, 10.0, 0.005)
        self.assertIs(select_critical_candidate([c1, c2, c3]), c3)

    def test_empty_candidates_raises(self):
        with self.assertRaises(ValueError):
            select_critical_candidate([])


class TestRankCandidates(unittest.TestCase):
    def test_ranked_list_is_sorted_ascending_by_margin(self):
        """rank_candidates returns list with MoS values in non-decreasing order."""
        c1 = CrackCandidate("loc-A", "axial",           50.0, 200.0, 0.001)
        c2 = CrackCandidate("loc-B", "circumferential", 100.0, 200.0, 0.001)
        c3 = CrackCandidate("loc-C", "radial",          200.0, 200.0, 0.001)
        ranked = rank_candidates([c1, c2, c3])
        margins = [r.fracture_margin() for r in ranked]
        self.assertEqual(margins, sorted(margins))

    def test_ranked_list_preserves_all_candidates(self):
        """All input candidates appear in the ranked output — none dropped."""
        candidates = [
            CrackCandidate(f"loc-{i}", "axial", float(50 + i * 10), 200.0, 0.001)
            for i in range(5)
        ]
        ranked = rank_candidates(candidates)
        self.assertEqual(len(ranked), len(candidates))
        for c in candidates:
            self.assertIn(c, ranked)

    def test_rank_empty_raises(self):
        with self.assertRaises(ValueError):
            rank_candidates([])

    def test_first_ranked_matches_select_critical(self):
        """The first element of rank_candidates is the same as select_critical_candidate."""
        c1 = CrackCandidate("s1", "axial",  80.0, 100.0, 0.002)
        c2 = CrackCandidate("s2", "radial", 20.0, 100.0, 0.001)
        c3 = CrackCandidate("s3", "axial", 300.0,  15.0, 0.003)
        self.assertIs(rank_candidates([c1, c2, c3])[0], select_critical_candidate([c1, c2, c3]))


class TestValidation(unittest.TestCase):
    def test_zero_crack_length_raises(self):
        with self.assertRaises(ValueError):
            CrackCandidate("loc", "axial", 100.0, 50.0, 0.0)

    def test_negative_crack_length_raises(self):
        with self.assertRaises(ValueError):
            CrackCandidate("loc", "axial", 100.0, 50.0, -0.001)

    def test_zero_stress_raises(self):
        with self.assertRaises(ValueError):
            CrackCandidate("loc", "axial", 0.0, 50.0, 0.001)

    def test_negative_stress_raises(self):
        with self.assertRaises(ValueError):
            CrackCandidate("loc", "axial", -100.0, 50.0, 0.001)

    def test_zero_toughness_raises(self):
        with self.assertRaises(ValueError):
            CrackCandidate("loc", "axial", 100.0, 0.0, 0.001)

    def test_negative_toughness_raises(self):
        with self.assertRaises(ValueError):
            CrackCandidate("loc", "axial", 100.0, -10.0, 0.001)

    def test_zero_geometry_factor_raises(self):
        with self.assertRaises(ValueError):
            CrackCandidate("loc", "axial", 100.0, 50.0, 0.001, geometry_factor=0.0)

    def test_negative_geometry_factor_raises(self):
        with self.assertRaises(ValueError):
            CrackCandidate("loc", "axial", 100.0, 50.0, 0.001, geometry_factor=-1.12)

    def test_empty_location_id_raises(self):
        with self.assertRaises(ValueError):
            CrackCandidate("", "axial", 100.0, 50.0, 0.001)

    def test_whitespace_location_id_raises(self):
        with self.assertRaises(ValueError):
            CrackCandidate("   ", "axial", 100.0, 50.0, 0.001)

    def test_empty_orientation_raises(self):
        with self.assertRaises(ValueError):
            CrackCandidate("loc", "", 100.0, 50.0, 0.001)


class TestAttributes(unittest.TestCase):
    def test_all_constructor_attributes_accessible(self):
        """All constructor parameters are stored as public attributes."""
        c = CrackCandidate("hole-X", "oblique", 150.0, 75.0, 0.003, geometry_factor=1.25)
        self.assertEqual(c.location_id, "hole-X")
        self.assertEqual(c.orientation, "oblique")
        self.assertAlmostEqual(c.net_stress_mpa, 150.0)
        self.assertAlmostEqual(c.fracture_toughness_mpa_sqrtm, 75.0)
        self.assertAlmostEqual(c.crack_half_length_m, 0.003)
        self.assertAlmostEqual(c.geometry_factor, 1.25)

    def test_repr_contains_location_and_orientation(self):
        """__repr__ includes the location identifier and orientation label."""
        c = CrackCandidate("weld-toe-1", "axial", 100.0, 50.0, 0.001)
        r = repr(c)
        self.assertIn("weld-toe-1", r)
        self.assertIn("axial", r)


if __name__ == "__main__":
    unittest.main()
