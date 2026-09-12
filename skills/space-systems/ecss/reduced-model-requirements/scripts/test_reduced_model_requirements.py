#!/usr/bin/env python3
"""Gate 3 contract tests for reduced_model_requirements_logic.py.

Stdlib unittest only — offline, deterministic.
Run: python3 test_reduced_model_requirements.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from reduced_model_requirements_logic import (
    MASS_ACCURACY_LIMIT,
    FREQUENCY_ACCURACY_LIMIT,
    INTERNAL_MODE_FREQ_MARGIN,
    ReducedModelError,
    check_reduction_method,
    check_interface_nodes,
    check_craig_bampton,
    check_guyan,
    check_residual_flexibility,
    categorize_method_from_properties,
    assess_reduced_model,
)


# ── check_reduction_method ────────────────────────────────────────────────────

class TestCheckReductionMethod(unittest.TestCase):

    def test_craig_bampton_accepted(self):
        self.assertEqual(check_reduction_method("craig_bampton"), "craig_bampton")

    def test_guyan_accepted(self):
        self.assertEqual(check_reduction_method("guyan"), "guyan")

    def test_superelement_accepted(self):
        self.assertEqual(check_reduction_method("superelement"), "superelement")

    def test_case_insensitive_normalisation(self):
        self.assertEqual(check_reduction_method("Craig_Bampton"), "craig_bampton")
        self.assertEqual(check_reduction_method("  GUYAN  "), "guyan")

    def test_unknown_method_raises(self):
        with self.assertRaises(ReducedModelError):
            check_reduction_method("mac_neal_rubin")

    def test_empty_string_raises(self):
        with self.assertRaises(ReducedModelError):
            check_reduction_method("")


# ── check_interface_nodes ─────────────────────────────────────────────────────

class TestCheckInterfaceNodes(unittest.TestCase):

    def test_empty_list_flagged(self):
        findings = check_interface_nodes([])
        self.assertTrue(len(findings) > 0)
        self.assertTrue(any("empty" in f for f in findings))

    def test_valid_single_node(self):
        nodes = [{"node_id": 101, "dof_codes": [1, 2, 3, 4, 5, 6]}]
        self.assertEqual(check_interface_nodes(nodes), [])

    def test_valid_multiple_nodes(self):
        nodes = [
            {"node_id": 1, "dof_codes": [1, 2, 3]},
            {"node_id": 2, "dof_codes": [4, 5, 6]},
        ]
        self.assertEqual(check_interface_nodes(nodes), [])

    def test_duplicate_node_id_flagged(self):
        nodes = [
            {"node_id": 5, "dof_codes": [1, 2, 3]},
            {"node_id": 5, "dof_codes": [4, 5, 6]},
        ]
        findings = check_interface_nodes(nodes)
        self.assertTrue(any("duplicate" in f for f in findings))

    def test_invalid_dof_code_flagged(self):
        nodes = [{"node_id": 10, "dof_codes": [1, 7]}]
        findings = check_interface_nodes(nodes)
        self.assertTrue(any("invalid" in f for f in findings))

    def test_missing_node_id_flagged(self):
        nodes = [{"dof_codes": [1, 2, 3]}]
        findings = check_interface_nodes(nodes)
        self.assertTrue(any("node_id" in f for f in findings))

    def test_missing_dof_codes_flagged(self):
        nodes = [{"node_id": 20}]
        findings = check_interface_nodes(nodes)
        self.assertTrue(any("dof_codes" in f for f in findings))

    def test_non_dict_entry_flagged(self):
        findings = check_interface_nodes(["not_a_dict"])
        self.assertTrue(any("dict" in f for f in findings))

    def test_zero_node_id_flagged(self):
        nodes = [{"node_id": 0, "dof_codes": [1, 2]}]
        findings = check_interface_nodes(nodes)
        self.assertTrue(any("node_id" in f for f in findings))


# ── check_craig_bampton ───────────────────────────────────────────────────────

class TestCheckCraigBampton(unittest.TestCase):

    def _valid_kwargs(self, **overrides):
        base = dict(
            boundary_dof_count=6,
            internal_mode_count=20,
            target_frequency_hz=100.0,
            max_retained_mode_frequency_hz=160.0,  # 100 × 1.5 = 150, so 160 passes
            mass_fractional_error=0.005,
            frequency_fractional_error=0.01,
        )
        base.update(overrides)
        return base

    def test_compliant_parameters_produce_no_findings(self):
        self.assertEqual(check_craig_bampton(**self._valid_kwargs()), [])

    def test_mode_cutoff_too_low_flagged(self):
        findings = check_craig_bampton(
            **self._valid_kwargs(max_retained_mode_frequency_hz=140.0)
        )
        self.assertTrue(any("retained internal mode" in f for f in findings))

    def test_mass_error_exceeded_flagged(self):
        findings = check_craig_bampton(
            **self._valid_kwargs(mass_fractional_error=MASS_ACCURACY_LIMIT + 0.001)
        )
        self.assertTrue(any("mass fractional error" in f for f in findings))

    def test_frequency_error_exceeded_flagged(self):
        findings = check_craig_bampton(
            **self._valid_kwargs(
                frequency_fractional_error=FREQUENCY_ACCURACY_LIMIT + 0.001
            )
        )
        self.assertTrue(any("frequency fractional error" in f for f in findings))

    def test_zero_boundary_dofs_flagged(self):
        findings = check_craig_bampton(**self._valid_kwargs(boundary_dof_count=0))
        self.assertTrue(any("boundary_dof_count" in f for f in findings))

    def test_negative_input_raises(self):
        with self.assertRaises(ReducedModelError):
            check_craig_bampton(**self._valid_kwargs(boundary_dof_count=-1))

    def test_zero_target_frequency_skips_cutoff_check(self):
        # target_frequency_hz=0 → no cutoff check → no mode-coverage finding
        findings = check_craig_bampton(
            **self._valid_kwargs(
                target_frequency_hz=0.0,
                max_retained_mode_frequency_hz=0.0,
            )
        )
        self.assertFalse(any("retained internal mode" in f for f in findings))


# ── check_guyan ───────────────────────────────────────────────────────────────

class TestCheckGuyan(unittest.TestCase):

    def _valid_kwargs(self, **overrides):
        base = dict(
            total_dof_count=1000,
            master_dof_count=50,
            target_frequency_hz=30.0,
            lowest_slave_mode_frequency_hz=200.0,
            mass_fractional_error=0.005,
        )
        base.update(overrides)
        return base

    def test_compliant_parameters_produce_no_findings(self):
        self.assertEqual(check_guyan(**self._valid_kwargs()), [])

    def test_target_freq_at_slave_mode_freq_flagged(self):
        findings = check_guyan(
            **self._valid_kwargs(
                target_frequency_hz=200.0,
                lowest_slave_mode_frequency_hz=200.0,
            )
        )
        self.assertTrue(any("slave-mode frequency" in f for f in findings))

    def test_target_freq_above_slave_mode_freq_flagged(self):
        findings = check_guyan(
            **self._valid_kwargs(
                target_frequency_hz=250.0,
                lowest_slave_mode_frequency_hz=200.0,
            )
        )
        self.assertTrue(any("slave-mode frequency" in f for f in findings))

    def test_master_equals_total_flagged(self):
        findings = check_guyan(
            **self._valid_kwargs(total_dof_count=100, master_dof_count=100)
        )
        self.assertTrue(any("master_dof_count" in f for f in findings))

    def test_zero_master_dofs_flagged(self):
        findings = check_guyan(**self._valid_kwargs(master_dof_count=0))
        self.assertTrue(any("master_dof_count" in f for f in findings))

    def test_mass_error_exceeded_flagged(self):
        findings = check_guyan(
            **self._valid_kwargs(mass_fractional_error=MASS_ACCURACY_LIMIT + 0.001)
        )
        self.assertTrue(any("mass fractional error" in f for f in findings))

    def test_negative_input_raises(self):
        with self.assertRaises(ReducedModelError):
            check_guyan(**self._valid_kwargs(total_dof_count=-1))


# ── check_residual_flexibility ────────────────────────────────────────────────

class TestCheckResidualFlexibility(unittest.TestCase):

    def test_correction_required_and_missing_flagged(self):
        # max_retained=100 Hz, target=100 Hz → required cutoff=150 Hz → not met
        findings = check_residual_flexibility(
            target_frequency_hz=100.0,
            max_retained_mode_frequency_hz=100.0,
            residual_flexibility_applied=False,
        )
        self.assertTrue(len(findings) > 0)
        self.assertTrue(any("residual flexibility" in f for f in findings))

    def test_correction_required_and_applied_passes(self):
        findings = check_residual_flexibility(
            target_frequency_hz=100.0,
            max_retained_mode_frequency_hz=100.0,
            residual_flexibility_applied=True,
        )
        self.assertEqual(findings, [])

    def test_mode_set_covers_cutoff_no_correction_needed(self):
        findings = check_residual_flexibility(
            target_frequency_hz=100.0,
            max_retained_mode_frequency_hz=160.0,  # 100 × 1.5 = 150, 160 passes
            residual_flexibility_applied=False,
        )
        self.assertEqual(findings, [])

    def test_zero_target_frequency_skips_check(self):
        findings = check_residual_flexibility(
            target_frequency_hz=0.0,
            max_retained_mode_frequency_hz=0.0,
            residual_flexibility_applied=False,
        )
        self.assertEqual(findings, [])


# ── categorize_method_from_properties ────────────────────────────────────────

class TestCategorizeMethodFromProperties(unittest.TestCase):

    def test_fixed_boundary_with_modes_gives_craig_bampton(self):
        result = categorize_method_from_properties(
            boundary_fixed=True, dynamic_modes_retained=True
        )
        self.assertEqual(result, "craig_bampton")

    def test_fixed_boundary_without_modes_gives_guyan(self):
        result = categorize_method_from_properties(
            boundary_fixed=True, dynamic_modes_retained=False
        )
        self.assertEqual(result, "guyan")

    def test_free_boundary_gives_free_interface(self):
        result = categorize_method_from_properties(
            boundary_fixed=False, dynamic_modes_retained=True
        )
        self.assertEqual(result, "free_interface")

    def test_free_boundary_without_modes_gives_free_interface(self):
        result = categorize_method_from_properties(
            boundary_fixed=False, dynamic_modes_retained=False
        )
        self.assertEqual(result, "free_interface")


# ── assess_reduced_model ──────────────────────────────────────────────────────

class TestAssessReducedModel(unittest.TestCase):

    def _cb_spec(self, **overrides):
        base = dict(
            method="craig_bampton",
            interface_nodes=[{"node_id": 1, "dof_codes": [1, 2, 3, 4, 5, 6]}],
            boundary_dof_count=6,
            internal_mode_count=20,
            target_frequency_hz=100.0,
            max_retained_mode_frequency_hz=160.0,
            mass_fractional_error=0.005,
            frequency_fractional_error=0.01,
            residual_flexibility_applied=False,
        )
        base.update(overrides)
        return base

    def test_craig_bampton_compliant_spec(self):
        result = assess_reduced_model(self._cb_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_craig_bampton_mode_cutoff_violation(self):
        result = assess_reduced_model(
            self._cb_spec(max_retained_mode_frequency_hz=120.0)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(len(result["findings"]) > 0)

    def test_guyan_compliant_spec(self):
        spec = dict(
            method="guyan",
            interface_nodes=[{"node_id": 10, "dof_codes": [1, 2, 3]}],
            total_dof_count=500,
            master_dof_count=30,
            target_frequency_hz=25.0,
            lowest_slave_mode_frequency_hz=300.0,
            mass_fractional_error=0.004,
        )
        result = assess_reduced_model(spec)
        self.assertTrue(result["compliant"])

    def test_superelement_mass_violation(self):
        spec = dict(
            method="superelement",
            interface_nodes=[{"node_id": 1, "dof_codes": [1, 2, 3, 4, 5, 6]}],
            mass_fractional_error=0.05,
        )
        result = assess_reduced_model(spec)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("mass fractional error" in f for f in result["findings"]))

    def test_unknown_method_returns_noncompliant(self):
        spec = dict(
            method="polynomial_expansion",
            interface_nodes=[{"node_id": 1, "dof_codes": [1]}],
        )
        result = assess_reduced_model(spec)
        self.assertFalse(result["compliant"])
        self.assertTrue(len(result["findings"]) > 0)

    def test_empty_interface_nodes_flagged(self):
        result = assess_reduced_model(self._cb_spec(interface_nodes=[]))
        self.assertFalse(result["compliant"])


if __name__ == "__main__":
    unittest.main()
