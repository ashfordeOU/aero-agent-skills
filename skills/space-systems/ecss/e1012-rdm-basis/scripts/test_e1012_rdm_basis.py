import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_rdm_basis_logic import (
    MINIMUM_RDM_FACTOR,
    RdmError,
    build_rdm_basis,
    check_component_compliance,
    compute_required_levels,
    validate_environment_spec,
    validate_rdm_factor,
)

_ENV = {
    "total_ionising_dose": 10.0,
    "proton_fluence": 1e11,
    "electron_fluence": 1e12,
}


class TestValidateEnvironmentSpec(unittest.TestCase):
    def test_valid_spec_returns_all_three_parameters(self):
        result = validate_environment_spec(_ENV)
        self.assertIn("total_ionising_dose", result)
        self.assertIn("proton_fluence", result)
        self.assertIn("electron_fluence", result)

    def test_values_are_cast_to_float(self):
        spec = dict(_ENV)
        spec["total_ionising_dose"] = "10"
        result = validate_environment_spec(spec)
        self.assertIsInstance(result["total_ionising_dose"], float)

    def test_missing_tid_raises(self):
        incomplete = {"proton_fluence": 1e11, "electron_fluence": 1e12}
        with self.assertRaises(RdmError):
            validate_environment_spec(incomplete)

    def test_missing_proton_fluence_raises(self):
        incomplete = {"total_ionising_dose": 10.0, "electron_fluence": 1e12}
        with self.assertRaises(RdmError):
            validate_environment_spec(incomplete)

    def test_zero_tid_raises(self):
        bad = dict(_ENV, total_ionising_dose=0.0)
        with self.assertRaises(RdmError):
            validate_environment_spec(bad)

    def test_negative_electron_fluence_raises(self):
        bad = dict(_ENV, electron_fluence=-5e11)
        with self.assertRaises(RdmError):
            validate_environment_spec(bad)

    def test_non_numeric_value_raises(self):
        bad = dict(_ENV, proton_fluence="many")
        with self.assertRaises(RdmError):
            validate_environment_spec(bad)

    def test_non_dict_input_raises(self):
        with self.assertRaises(RdmError):
            validate_environment_spec([10.0, 1e11, 1e12])


class TestValidateRdmFactor(unittest.TestCase):
    def test_minimum_factor_is_accepted(self):
        self.assertEqual(validate_rdm_factor(2.0), 2.0)

    def test_factor_above_minimum_is_accepted(self):
        self.assertAlmostEqual(validate_rdm_factor(3.0), 3.0)

    def test_factor_below_minimum_raises(self):
        with self.assertRaises(RdmError):
            validate_rdm_factor(1.99)

    def test_zero_factor_raises(self):
        with self.assertRaises(RdmError):
            validate_rdm_factor(0.0)

    def test_non_numeric_factor_raises(self):
        with self.assertRaises(RdmError):
            validate_rdm_factor("two")

    def test_minimum_rdm_constant_value(self):
        self.assertEqual(MINIMUM_RDM_FACTOR, 2.0)

    def test_string_numeric_factor_accepted(self):
        self.assertAlmostEqual(validate_rdm_factor("2.5"), 2.5)


class TestComputeRequiredLevels(unittest.TestCase):
    def test_required_levels_are_factor_times_environment(self):
        levels = compute_required_levels(_ENV, 2.0)
        self.assertAlmostEqual(levels["total_ionising_dose"], 20.0)
        self.assertAlmostEqual(levels["proton_fluence"], 2e11)
        self.assertAlmostEqual(levels["electron_fluence"], 2e12)

    def test_larger_factor_scales_all_parameters(self):
        levels = compute_required_levels(_ENV, 3.0)
        self.assertAlmostEqual(levels["total_ionising_dose"], 30.0)
        self.assertAlmostEqual(levels["proton_fluence"], 3e11)

    def test_invalid_factor_propagates_error(self):
        with self.assertRaises(RdmError):
            compute_required_levels(_ENV, 1.0)

    def test_invalid_env_propagates_error(self):
        with self.assertRaises(RdmError):
            compute_required_levels({}, 2.0)


class TestCheckComponentCompliance(unittest.TestCase):
    def _required(self):
        return compute_required_levels(_ENV, 2.0)

    def test_all_parameters_pass_when_withstand_exceeds_required(self):
        withstand = {
            "total_ionising_dose": 25.0,
            "proton_fluence": 3e11,
            "electron_fluence": 3e12,
        }
        findings = check_component_compliance(withstand, self._required())
        self.assertTrue(all(f["compliant"] for f in findings))

    def test_tid_below_required_is_flagged(self):
        withstand = {
            "total_ionising_dose": 15.0,  # required = 20.0
            "proton_fluence": 3e11,
            "electron_fluence": 3e12,
        }
        findings = check_component_compliance(withstand, self._required())
        tid = next(f for f in findings if f["parameter"] == "total_ionising_dose")
        self.assertFalse(tid["compliant"])
        self.assertIn("below required", tid["note"])

    def test_missing_withstand_entry_is_open_finding(self):
        withstand = {
            "total_ionising_dose": 25.0,
            "proton_fluence": 3e11,
            # electron_fluence absent
        }
        findings = check_component_compliance(withstand, self._required())
        ef = next(f for f in findings if f["parameter"] == "electron_fluence")
        self.assertFalse(ef["compliant"])
        self.assertIsNone(ef["withstand"])
        self.assertIsNone(ef["margin_ratio"])

    def test_withstand_exactly_at_required_passes(self):
        required = self._required()
        withstand = {k: v for k, v in required.items()}
        findings = check_component_compliance(withstand, required)
        self.assertTrue(all(f["compliant"] for f in findings))

    def test_margin_ratio_above_one_when_withstand_exceeds_required(self):
        withstand = {
            "total_ionising_dose": 40.0,  # required = 20.0
            "proton_fluence": 3e11,
            "electron_fluence": 3e12,
        }
        findings = check_component_compliance(withstand, self._required())
        tid = next(f for f in findings if f["parameter"] == "total_ionising_dose")
        self.assertGreater(tid["margin_ratio"], 1.0)

    def test_non_numeric_withstand_raises(self):
        withstand = {
            "total_ionising_dose": "unknown",
            "proton_fluence": 3e11,
            "electron_fluence": 3e12,
        }
        with self.assertRaises(RdmError):
            check_component_compliance(withstand, self._required())

    def test_three_findings_returned_for_three_parameters(self):
        withstand = {
            "total_ionising_dose": 25.0,
            "proton_fluence": 3e11,
            "electron_fluence": 3e12,
        }
        findings = check_component_compliance(withstand, self._required())
        self.assertEqual(len(findings), 3)


class TestBuildRdmBasis(unittest.TestCase):
    def test_without_withstand_returns_no_findings_and_none_compliant(self):
        result = build_rdm_basis(_ENV, 2.0)
        self.assertEqual(result["findings"], [])
        self.assertIsNone(result["overall_compliant"])

    def test_without_withstand_required_levels_are_present(self):
        result = build_rdm_basis(_ENV, 2.0)
        self.assertIn("total_ionising_dose", result["required_levels"])
        self.assertIn("proton_fluence", result["required_levels"])
        self.assertIn("electron_fluence", result["required_levels"])

    def test_compliant_component_overall_compliant_true(self):
        withstand = {
            "total_ionising_dose": 25.0,
            "proton_fluence": 3e11,
            "electron_fluence": 3e12,
        }
        result = build_rdm_basis(_ENV, 2.0, withstand)
        self.assertTrue(result["overall_compliant"])
        self.assertEqual(len(result["findings"]), 3)

    def test_non_compliant_tid_overall_compliant_false(self):
        withstand = {
            "total_ionising_dose": 5.0,  # required = 20.0
            "proton_fluence": 3e11,
            "electron_fluence": 3e12,
        }
        result = build_rdm_basis(_ENV, 2.0, withstand)
        self.assertFalse(result["overall_compliant"])

    def test_rdm_factor_below_minimum_raises(self):
        with self.assertRaises(RdmError):
            build_rdm_basis(_ENV, 1.9)

    def test_required_levels_double_environment_at_factor_two(self):
        result = build_rdm_basis(_ENV, 2.0)
        self.assertAlmostEqual(
            result["required_levels"]["total_ionising_dose"], 20.0
        )

    def test_partial_withstand_yields_open_finding(self):
        withstand = {
            "total_ionising_dose": 25.0,
            # proton_fluence and electron_fluence absent
        }
        result = build_rdm_basis(_ENV, 2.0, withstand)
        self.assertFalse(result["overall_compliant"])
        open_findings = [f for f in result["findings"] if f["withstand"] is None]
        self.assertEqual(len(open_findings), 2)


if __name__ == "__main__":
    unittest.main()
