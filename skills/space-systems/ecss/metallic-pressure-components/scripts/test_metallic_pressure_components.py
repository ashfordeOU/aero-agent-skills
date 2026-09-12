import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from metallic_pressure_components_logic import (
    categorize_component,
    check_proof_pressure,
    check_burst_pressure,
    compute_hoop_stress,
    compute_margin_of_safety,
    compute_safe_life,
    check_fatigue_life,
    PROOF_FACTOR,
    SCATTER_FACTOR,
)


class TestCategorizeComponent(unittest.TestCase):
    def test_valve_is_valid(self):
        self.assertEqual(categorize_component("valve"), "valve")

    def test_pump_is_valid(self):
        self.assertEqual(categorize_component("pump"), "pump")

    def test_line_is_valid(self):
        self.assertEqual(categorize_component("line"), "line")

    def test_fitting_is_valid(self):
        self.assertEqual(categorize_component("fitting"), "fitting")

    def test_hose_is_valid(self):
        self.assertEqual(categorize_component("hose"), "hose")

    def test_uppercase_input_accepted(self):
        self.assertEqual(categorize_component("VALVE"), "valve")

    def test_mixed_case_input_accepted(self):
        self.assertEqual(categorize_component("Fitting"), "fitting")

    def test_unknown_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_component("manifold")

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_component("")


class TestProofPressure(unittest.TestCase):
    def test_passes_when_ratio_above_threshold(self):
        result = check_proof_pressure(meop_pa=100_000, proof_pa=115_000)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["ratio"], 1.15)

    def test_fails_when_ratio_below_threshold(self):
        result = check_proof_pressure(meop_pa=100_000, proof_pa=105_000)
        self.assertFalse(result["pass"])
        self.assertAlmostEqual(result["ratio"], 1.05)

    def test_passes_at_exact_threshold(self):
        result = check_proof_pressure(meop_pa=100_000, proof_pa=110_000)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["ratio"], PROOF_FACTOR)

    def test_required_ratio_is_proof_factor(self):
        result = check_proof_pressure(meop_pa=200_000, proof_pa=220_000)
        self.assertAlmostEqual(result["required_ratio"], PROOF_FACTOR)

    def test_zero_meop_raises(self):
        with self.assertRaises(ValueError):
            check_proof_pressure(meop_pa=0, proof_pa=110_000)

    def test_negative_meop_raises(self):
        with self.assertRaises(ValueError):
            check_proof_pressure(meop_pa=-1, proof_pa=110_000)


class TestBurstPressure(unittest.TestCase):
    def test_line_factor_1_5_passes(self):
        result = check_burst_pressure("line", meop_pa=100_000, burst_pa=150_000)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["required_ratio"], 1.5)

    def test_line_factor_1_5_fails_below(self):
        result = check_burst_pressure("line", meop_pa=100_000, burst_pa=140_000)
        self.assertFalse(result["pass"])

    def test_fitting_factor_1_5_passes(self):
        result = check_burst_pressure("fitting", meop_pa=80_000, burst_pa=121_000)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["required_ratio"], 1.5)

    def test_valve_factor_2_0_passes(self):
        result = check_burst_pressure("valve", meop_pa=100_000, burst_pa=200_000)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["required_ratio"], 2.0)

    def test_valve_factor_2_0_fails_below(self):
        result = check_burst_pressure("valve", meop_pa=100_000, burst_pa=190_000)
        self.assertFalse(result["pass"])

    def test_pump_uses_factor_2_0(self):
        result = check_burst_pressure("pump", meop_pa=50_000, burst_pa=100_000)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["required_ratio"], 2.0)

    def test_hose_uses_factor_2_0(self):
        result = check_burst_pressure("hose", meop_pa=80_000, burst_pa=160_000)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["required_ratio"], 2.0)

    def test_invalid_type_raises(self):
        with self.assertRaises(ValueError):
            check_burst_pressure("tank", meop_pa=100_000, burst_pa=200_000)

    def test_component_type_returned_canonical(self):
        result = check_burst_pressure("LINE", meop_pa=100_000, burst_pa=150_000)
        self.assertEqual(result["component_type"], "line")


class TestHoopStress(unittest.TestCase):
    def test_hoop_stress_correct_value(self):
        # p=1 MPa, r=0.05 m, t=0.002 m → r/t=25, sh=25 MPa
        result = compute_hoop_stress(1_000_000, 0.05, 0.002)
        self.assertAlmostEqual(result["sigma_hoop_pa"], 25_000_000)

    def test_axial_stress_is_half_hoop(self):
        result = compute_hoop_stress(1_000_000, 0.05, 0.002)
        self.assertAlmostEqual(result["sigma_axial_pa"], result["sigma_hoop_pa"] / 2.0)

    def test_r_over_t_returned(self):
        result = compute_hoop_stress(1_000_000, 0.05, 0.002)
        self.assertAlmostEqual(result["r_over_t"], 25.0)

    def test_von_mises_is_positive(self):
        result = compute_hoop_stress(1_000_000, 0.05, 0.002)
        self.assertGreater(result["sigma_vm_pa"], 0)

    def test_thin_wall_violation_raises(self):
        # r/t = 5 < 10 → should raise
        with self.assertRaises(ValueError):
            compute_hoop_stress(1_000_000, radius_m=0.05, wall_thickness_m=0.01)

    def test_zero_wall_thickness_raises(self):
        with self.assertRaises(ValueError):
            compute_hoop_stress(1_000_000, 0.05, 0.0)

    def test_negative_radius_raises(self):
        with self.assertRaises(ValueError):
            compute_hoop_stress(1_000_000, -0.05, 0.002)

    def test_zero_pressure_gives_zero_stresses(self):
        result = compute_hoop_stress(0.0, 0.05, 0.002)
        self.assertAlmostEqual(result["sigma_hoop_pa"], 0.0)
        self.assertAlmostEqual(result["sigma_vm_pa"], 0.0)


class TestMarginOfSafety(unittest.TestCase):
    def test_positive_margin_passes(self):
        # allowable = 400/1.25 = 320; applied = 200; MS = 320/200 - 1 = 0.6
        result = compute_margin_of_safety(sigma_vm_pa=200e6, ftu_pa=400e6, safety_factor=1.25)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["margin_of_safety"], 0.6)

    def test_negative_margin_fails(self):
        # allowable = 400/1.25 = 320; applied = 350; MS = 320/350 - 1 < 0
        result = compute_margin_of_safety(sigma_vm_pa=350e6, ftu_pa=400e6, safety_factor=1.25)
        self.assertFalse(result["pass"])
        self.assertLess(result["margin_of_safety"], 0)

    def test_allowable_equals_ftu_over_sf(self):
        result = compute_margin_of_safety(sigma_vm_pa=100e6, ftu_pa=250e6, safety_factor=1.25)
        self.assertAlmostEqual(result["allowable_pa"], 200e6)

    def test_zero_sigma_vm_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(sigma_vm_pa=0.0, ftu_pa=400e6)

    def test_zero_ftu_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(sigma_vm_pa=100e6, ftu_pa=0.0)


class TestFatigueSafeLife(unittest.TestCase):
    def test_safe_life_with_default_scatter_factor(self):
        result = compute_safe_life(test_cycles=4000)
        self.assertAlmostEqual(result["safe_life_cycles"], 1000.0)
        self.assertAlmostEqual(result["scatter_factor"], SCATTER_FACTOR)

    def test_safe_life_with_custom_scatter_factor(self):
        result = compute_safe_life(test_cycles=6000, scatter_factor=3.0)
        self.assertAlmostEqual(result["safe_life_cycles"], 2000.0)

    def test_fatigue_life_passes_when_safe_life_covers_required(self):
        result = check_fatigue_life(required_cycles=500, test_cycles=4000)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["margin_factor"], 2.0)

    def test_fatigue_life_fails_when_safe_life_short(self):
        result = check_fatigue_life(required_cycles=1500, test_cycles=4000)
        self.assertFalse(result["pass"])

    def test_margin_factor_correct(self):
        # safe = 8000/4 = 2000; required = 500; margin = 2000/500 = 4.0
        result = check_fatigue_life(required_cycles=500, test_cycles=8000)
        self.assertAlmostEqual(result["margin_factor"], 4.0)

    def test_zero_test_cycles_raises(self):
        with self.assertRaises(ValueError):
            compute_safe_life(test_cycles=0)

    def test_zero_required_cycles_raises(self):
        with self.assertRaises(ValueError):
            check_fatigue_life(required_cycles=0, test_cycles=4000)

    def test_scatter_factor_of_four_is_default(self):
        self.assertAlmostEqual(SCATTER_FACTOR, 4.0)


if __name__ == "__main__":
    unittest.main()
