"""Behavior contract tests for the layup-cure skill.

Offline, deterministic, stdlib unittest only. Runs in well under 30 s.

Contract assertions:
  - symmetric sequence [0,45,-45,90,90,-45,45,0] passes
    symmetric_check(), an asymmetric sequence fails
  - a standard 350F epoxy cure cycle (2 F/min ramp, 350 F hold
    120 min) reaches degree of cure >= 0.95
  - invalid ply orientation (e.g. 99 deg) raises ValueError
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from layup_cure_logic import (  # noqa: E402
    balanced_check,
    c_scan_verdict,
    cure_cycle_timeline,
    degree_of_cure,
    glass_transition_tg,
    ply_book,
    symmetric_check,
)

SYMMETRIC = [0, 45, -45, 90, 90, -45, 45, 0]
# Six plies: index 0 is 0 deg while index 5 is 45 deg, so the sequence
# does not mirror around the midplane.
ASYMMETRIC = [0, 45, -45, 90, -45, 45]

# Representative 350F-cure epoxy kinetics (per minute): A = 5e5 1/min,
# Ea = 60 kJ/mol, n = 1. Calibrated so the standard 350F/120-min cycle
# exceeds 95% degree of cure while a ramp-only cycle stays below it.
A_350F_EPOXY = 5.0e5
EA_350F_EPOXY = 60000.0
N_350F_EPOXY = 1.0


class TestSymmetricCheck(unittest.TestCase):
    def test_symmetric_sequence_passes(self):
        result = symmetric_check(SYMMETRIC)
        self.assertTrue(result["symmetric"])

    def test_asymmetric_sequence_fails(self):
        result = symmetric_check(ASYMMETRIC)
        self.assertFalse(result["symmetric"])

    def test_odd_ply_count_can_be_symmetric(self):
        self.assertTrue(symmetric_check([0, 45, -45, 90, -45, 45, 0])["symmetric"])

    def test_invalid_orientation_raises(self):
        with self.assertRaises(ValueError):
            symmetric_check([0, 99])
        with self.assertRaises(ValueError):
            symmetric_check([0, "45"])


class TestBalancedCheck(unittest.TestCase):
    def test_balanced_sequence_passes(self):
        self.assertTrue(balanced_check(SYMMETRIC)["balanced"])

    def test_unbalanced_sequence_fails(self):
        self.assertFalse(balanced_check([0, 45, 90])["balanced"])
        self.assertFalse(balanced_check([0, 45, 45, 90, -45])["balanced"])

    def test_self_balancing_plies(self):
        self.assertTrue(balanced_check([0, 0, 90, 90, -90])["balanced"])


class TestPlyBook(unittest.TestCase):
    def test_ply_book_structure(self):
        book = ply_book(SYMMETRIC, thicknesses_mm=[0.19] * 8)
        self.assertEqual(book["ply_count"], 8)
        self.assertEqual(book["plies"][0]["orientation"], 0)
        self.assertEqual(book["plies"][3]["orientation"], 90)
        self.assertEqual(book["plies"][1]["material"], "carbon-epoxy-prepreg")
        self.assertAlmostEqual(book["total_thickness_mm"], 8 * 0.19)

    def test_material_and_thickness_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            ply_book([0, 45], materials=["a"])
        with self.assertRaises(ValueError):
            ply_book([0, 45], thicknesses_mm=[0.19])
        with self.assertRaises(ValueError):
            ply_book([0, 45], thicknesses_mm=[0.19, -0.1])


class TestCureCycleTimeline(unittest.TestCase):
    def test_350f_cycle_phases_and_durations(self):
        cycle = cure_cycle_timeline()
        names = [p["phase"] for p in cycle["phases"]]
        self.assertEqual(names, ["vacuum-stabilize", "ramp", "dwell", "cool"])
        ramp = cycle["phases"][1]
        self.assertAlmostEqual(ramp["start_temp_f"], 70.0)
        self.assertAlmostEqual(ramp["end_temp_f"], 350.0)
        self.assertAlmostEqual(ramp["end_min"] - ramp["start_min"], (350.0 - 70.0) / 2.0)
        dwell = cycle["phases"][2]
        self.assertAlmostEqual(dwell["end_min"] - dwell["start_min"], 120.0)
        self.assertAlmostEqual(cycle["profile"][0], (0.0, 70.0))
        self.assertAlmostEqual(cycle["profile"][-1][1], 140.0)
        self.assertEqual(cycle["pressure"]["type"], "autoclave")
        self.assertEqual(cycle["pressure"]["pressure_psi"], 85.0)

    def test_pressure_type_variants(self):
        ooa = cure_cycle_timeline(pressure_type="out-of-autoclave")
        self.assertEqual(ooa["pressure"]["pressure_psi"], 0.0)
        self.assertIn("vacuum bag only", ooa["pressure"]["note"])
        press = cure_cycle_timeline(pressure_type="press", vacuum=False)
        self.assertEqual(press["pressure"]["pressure_psi"], 85.0)
        self.assertEqual(press["phases"][0]["vacuum_inhg"], 0.0)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            cure_cycle_timeline(ramp_rate_fpm=0.0)
        with self.assertRaises(ValueError):
            cure_cycle_timeline(cool_rate_fpm=-1.0)
        with self.assertRaises(ValueError):
            cure_cycle_timeline(cure_temp_f=50.0)  # at or below start temp
        with self.assertRaises(ValueError):
            cure_cycle_timeline(pressure_type="vacuum-bag-only")


class TestDegreeOfCure(unittest.TestCase):
    def test_350f_standard_cycle_reaches_95_percent(self):
        cycle = cure_cycle_timeline()  # 2 F/min ramp, 350 F hold 120 min
        alpha = degree_of_cure(
            cycle["profile"], A=A_350F_EPOXY, Ea=EA_350F_EPOXY, n=N_350F_EPOXY, dt=0.5
        )
        self.assertGreaterEqual(alpha, 0.95)
        self.assertLessEqual(alpha, 1.0)

    def test_dict_profile_input(self):
        cycle = cure_cycle_timeline()
        alpha = degree_of_cure(cycle, A=A_350F_EPOXY, Ea=EA_350F_EPOXY, n=1.0)
        self.assertGreaterEqual(alpha, 0.95)

    def test_ramp_only_cycle_does_not_cure(self):
        ramp_only = [(0.0, 70.0), (140.0, 350.0)]
        alpha = degree_of_cure(
            ramp_only, A=A_350F_EPOXY, Ea=EA_350F_EPOXY, n=N_350F_EPOXY, dt=0.5
        )
        self.assertLess(alpha, 0.95)

    def test_no_reaction_at_low_temperature(self):
        alpha = degree_of_cure(
            [(0.0, 70.0), (300.0, 70.0)], A=A_350F_EPOXY, Ea=EA_350F_EPOXY, n=1.0, dt=0.5
        )
        self.assertLess(alpha, 0.01)

    def test_zero_order_and_high_alpha_sanity(self):
        # n = 0: constant linear rate k ~ A at high temperature with
        # negligible Ea, alpha saturates and clamps at 1.0.
        alpha = degree_of_cure(
            [(0.0, 350.0), (120.0, 350.0)], A=1.0, Ea=1.0, n=0.0, dt=1.0
        )
        self.assertAlmostEqual(alpha, 1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            degree_of_cure([(0.0, 70.0)], A=5.0e5, Ea=60000.0, n=1.0, dt=0.5)
        with self.assertRaises(ValueError):
            degree_of_cure([(0.0, 70.0), (10.0, 350.0)], A=-1.0, Ea=60000.0, n=1.0, dt=0.5)
        with self.assertRaises(ValueError):
            degree_of_cure([(0.0, 70.0), (10.0, 350.0)], A=5.0e5, Ea=60000.0, n=1.0, dt=0.0)


class TestGlassTransition(unittest.TestCase):
    def test_endpoints(self):
        self.assertAlmostEqual(glass_transition_tg(0.0), -10.0)
        self.assertAlmostEqual(glass_transition_tg(1.0), 200.0)

    def test_monotonic_increase_with_cure(self):
        alphas = (0.0, 0.25, 0.5, 0.75, 0.95, 1.0)
        tgs = [glass_transition_tg(a) for a in alphas]
        self.assertEqual(tgs, sorted(tgs))
        self.assertGreater(glass_transition_tg(0.95), 150.0)

    def test_alpha_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            glass_transition_tg(1.5)
        with self.assertRaises(ValueError):
            glass_transition_tg(-0.1)


class TestCScanVerdict(unittest.TestCase):
    def test_pass_and_fail(self):
        self.assertEqual(c_scan_verdict(0.5)["verdict"], "PASS")
        self.assertEqual(c_scan_verdict(2.5)["verdict"], "FAIL")
        self.assertEqual(c_scan_verdict(1.0)["verdict"], "PASS")  # at limit

    def test_custom_limit(self):
        self.assertEqual(c_scan_verdict(1.5, acceptance_limit_pct=2.0)["verdict"], "PASS")

    def test_porosity_causes_present(self):
        result = c_scan_verdict(2.5)
        self.assertGreaterEqual(len(result["porosity_causes"]), 5)
        self.assertIn("vacuum", " ".join(result["porosity_causes"]).lower())

    def test_negative_porosity_raises(self):
        with self.assertRaises(ValueError):
            c_scan_verdict(-0.1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
