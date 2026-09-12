"""
Offline deterministic unit tests for copc_nonmetallic_liner_logic.py.
Run: python3 test_copc_nonmetallic_liner.py
"""

import sys
import os
import unittest

# Ensure the logic module is importable regardless of invocation directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import copc_nonmetallic_liner_logic as logic


class TestCategorizeLinnerMaterial(unittest.TestCase):

    def test_thermoplastic_accepted(self):
        self.assertEqual(logic.categorize_liner_material("thermoplastic"), "thermoplastic")

    def test_thermoset_accepted(self):
        self.assertEqual(logic.categorize_liner_material("thermoset"), "thermoset")

    def test_elastomer_accepted(self):
        self.assertEqual(logic.categorize_liner_material("elastomer"), "elastomer")

    def test_case_insensitive(self):
        self.assertEqual(logic.categorize_liner_material("Thermoplastic"), "thermoplastic")
        self.assertEqual(logic.categorize_liner_material("THERMOSET"), "thermoset")

    def test_invalid_material_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_liner_material("steel")

    def test_non_string_raises(self):
        with self.assertRaises(TypeError):
            logic.categorize_liner_material(42)


class TestPressureFactors(unittest.TestCase):

    def test_compute_proof_pressure(self):
        self.assertAlmostEqual(logic.compute_proof_pressure(10.0, 1.1), 11.0)

    def test_compute_burst_pressure(self):
        self.assertAlmostEqual(logic.compute_burst_pressure(10.0, 1.5), 15.0)

    def test_proof_factor_pass(self):
        result = logic.check_proof_factor(1.2)
        self.assertTrue(result["pass"])
        self.assertEqual(result["shortfall"], 0.0)

    def test_proof_factor_at_minimum_passes(self):
        result = logic.check_proof_factor(1.1)
        self.assertTrue(result["pass"])

    def test_proof_factor_fail(self):
        result = logic.check_proof_factor(1.05)
        self.assertFalse(result["pass"])
        self.assertAlmostEqual(result["shortfall"], 0.05, places=6)

    def test_burst_factor_pass(self):
        result = logic.check_burst_factor(1.7)
        self.assertTrue(result["pass"])
        self.assertEqual(result["shortfall"], 0.0)

    def test_burst_factor_at_minimum_passes(self):
        result = logic.check_burst_factor(1.5)
        self.assertTrue(result["pass"])

    def test_burst_factor_fail(self):
        result = logic.check_burst_factor(1.3)
        self.assertFalse(result["pass"])
        self.assertAlmostEqual(result["shortfall"], 0.2, places=6)

    def test_zero_meop_raises(self):
        with self.assertRaises(ValueError):
            logic.compute_proof_pressure(0.0, 1.1)


class TestPermeationRate(unittest.TestCase):

    def test_permeation_within_limit_passes(self):
        result = logic.check_permeation_rate(0.005, 0.01)
        self.assertTrue(result["pass"])
        self.assertEqual(result["exceedance"], 0.0)

    def test_permeation_at_limit_passes(self):
        result = logic.check_permeation_rate(0.01, 0.01)
        self.assertTrue(result["pass"])

    def test_permeation_exceeds_limit_fails(self):
        result = logic.check_permeation_rate(0.02, 0.01)
        self.assertFalse(result["pass"])
        self.assertAlmostEqual(result["exceedance"], 0.01, places=6)

    def test_negative_rate_raises(self):
        with self.assertRaises(ValueError):
            logic.check_permeation_rate(-0.001, 0.01)

    def test_zero_limit_raises(self):
        with self.assertRaises(ValueError):
            logic.check_permeation_rate(0.005, 0.0)


class TestLoadShareRatio(unittest.TestCase):

    def test_ratio_computation(self):
        ratio = logic.compute_load_share_ratio(10.0, 90.0)
        self.assertAlmostEqual(ratio, 0.1)

    def test_ratio_within_threshold_passes(self):
        ratio = logic.compute_load_share_ratio(10.0, 90.0)  # 10 %
        result = logic.check_load_share_ratio(ratio)
        self.assertTrue(result["pass"])
        self.assertEqual(result["excess"], 0.0)

    def test_ratio_exceeds_threshold_fails(self):
        ratio = logic.compute_load_share_ratio(30.0, 70.0)  # 30 %
        result = logic.check_load_share_ratio(ratio)
        self.assertFalse(result["pass"])
        self.assertAlmostEqual(result["excess"], 0.10, places=6)

    def test_zero_liner_stiffness_gives_zero_ratio(self):
        ratio = logic.compute_load_share_ratio(0.0, 100.0)
        self.assertEqual(ratio, 0.0)

    def test_negative_liner_stiffness_raises(self):
        with self.assertRaises(ValueError):
            logic.compute_load_share_ratio(-1.0, 100.0)


class TestLinnerCompatibility(unittest.TestCase):

    def test_thermoplastic_nitrogen_compatible(self):
        result = logic.check_liner_compatibility("thermoplastic", "nitrogen")
        self.assertTrue(result["compatible"])

    def test_elastomer_hydrazine_incompatible(self):
        result = logic.check_liner_compatibility("elastomer", "hydrazine")
        self.assertFalse(result["compatible"])

    def test_thermoset_hydrazine_compatible(self):
        result = logic.check_liner_compatibility("thermoset", "hydrazine")
        self.assertTrue(result["compatible"])

    def test_invalid_liner_raises(self):
        with self.assertRaises(ValueError):
            logic.check_liner_compatibility("aluminium", "nitrogen")

    def test_unknown_fluid_flagged_incompatible(self):
        result = logic.check_liner_compatibility("thermoplastic", "xenon_fluoride")
        self.assertFalse(result["compatible"])


class TestCyclicLife(unittest.TestCase):

    def test_sufficient_cycles_passes(self):
        result = logic.check_cyclic_life(100, 500, safety_factor=4.0)
        self.assertTrue(result["pass"])
        self.assertEqual(result["deficit"], 0.0)

    def test_exactly_required_cycles_passes(self):
        result = logic.check_cyclic_life(100, 400, safety_factor=4.0)
        self.assertTrue(result["pass"])

    def test_insufficient_cycles_fails(self):
        result = logic.check_cyclic_life(100, 200, safety_factor=4.0)
        self.assertFalse(result["pass"])
        self.assertAlmostEqual(result["deficit"], 200.0)

    def test_zero_cycles_required_raises(self):
        with self.assertRaises(ValueError):
            logic.check_cyclic_life(0, 400, safety_factor=4.0)

    def test_safety_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            logic.check_cyclic_life(100, 400, safety_factor=0.5)


class TestFullAssessment(unittest.TestCase):

    def _compliant_inputs(self):
        return dict(
            liner_type="thermoplastic",
            meop=10.0,
            proof_factor=1.2,
            burst_factor=1.6,
            permeation_rate=0.005,
            permeation_limit=0.01,
            liner_stiffness=10.0,
            overwrap_stiffness=90.0,
            fluid="nitrogen",
            cycles_required=100,
            cycles_demonstrated=500,
            fatigue_safety_factor=4.0,
        )

    def test_all_pass_yields_compliant(self):
        result = logic.assess_copc_nonmetallic(**self._compliant_inputs())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["liner_category"], "thermoplastic")

    def test_low_proof_factor_flags_finding(self):
        inputs = self._compliant_inputs()
        inputs["proof_factor"] = 1.05
        result = logic.assess_copc_nonmetallic(**inputs)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("Proof factor" in f for f in result["findings"]))

    def test_low_burst_factor_flags_finding(self):
        inputs = self._compliant_inputs()
        inputs["burst_factor"] = 1.3
        result = logic.assess_copc_nonmetallic(**inputs)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("Burst factor" in f for f in result["findings"]))

    def test_permeation_exceedance_flags_finding(self):
        inputs = self._compliant_inputs()
        inputs["permeation_rate"] = 0.02
        result = logic.assess_copc_nonmetallic(**inputs)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("Permeation" in f for f in result["findings"]))

    def test_high_load_share_flags_finding(self):
        inputs = self._compliant_inputs()
        inputs["liner_stiffness"] = 50.0
        inputs["overwrap_stiffness"] = 50.0
        result = logic.assess_copc_nonmetallic(**inputs)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("load-share" in f for f in result["findings"]))

    def test_incompatible_fluid_flags_finding(self):
        inputs = self._compliant_inputs()
        inputs["fluid"] = "hydrazine"  # not compatible with thermoplastic
        result = logic.assess_copc_nonmetallic(**inputs)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("compatible" in f for f in result["findings"]))

    def test_insufficient_fatigue_life_flags_finding(self):
        inputs = self._compliant_inputs()
        inputs["cycles_demonstrated"] = 50
        result = logic.assess_copc_nonmetallic(**inputs)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("cycles" in f for f in result["findings"]))

    def test_invalid_liner_type_returns_not_compliant(self):
        inputs = self._compliant_inputs()
        inputs["liner_type"] = "unobtainium"
        result = logic.assess_copc_nonmetallic(**inputs)
        self.assertFalse(result["compliant"])
        self.assertIsNone(result["liner_category"])

    def test_load_share_ratio_reported(self):
        result = logic.assess_copc_nonmetallic(**self._compliant_inputs())
        self.assertAlmostEqual(result["load_share_ratio"], 0.1)

    def test_multiple_failures_reported(self):
        inputs = self._compliant_inputs()
        inputs["proof_factor"] = 1.0   # too low
        inputs["burst_factor"] = 1.2   # too low
        result = logic.assess_copc_nonmetallic(**inputs)
        self.assertFalse(result["compliant"])
        self.assertGreaterEqual(len(result["findings"]), 2)


if __name__ == "__main__":
    unittest.main()
