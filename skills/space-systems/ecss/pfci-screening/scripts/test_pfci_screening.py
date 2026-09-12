"""
Contract tests for pfci_screening_logic.py.
Run: python3 test_pfci_screening.py
"""

import sys
import os
import unittest

# Allow import from the same directory regardless of invocation location.
sys.path.insert(0, os.path.dirname(__file__))

from pfci_screening_logic import (
    FailureEffect,
    MIN_CROSS_SECTION_CM2,
    ScreeningOutcome,
    StructuralItem,
    screen_batch,
    screen_item,
)


def _pfci_item(**overrides) -> StructuralItem:
    """Return a base item that passes all five gates (PFCI outcome)."""
    defaults = dict(
        item_id="ITEM-001",
        name="Primary bracket",
        is_structural=True,
        failure_effect=FailureEffect.CATASTROPHIC,
        carries_tensile_load=True,
        material_susceptible=True,
        min_cross_section_cm2=2.0,
        is_gse=False,
        gse_critical_operation=False,
        notes="",
    )
    defaults.update(overrides)
    return StructuralItem(**defaults)


class TestGatePassed(unittest.TestCase):

    def test_all_gates_pass_gives_pfci(self):
        result = screen_item(_pfci_item())
        self.assertEqual(result.outcome, ScreeningOutcome.PFCI)

    def test_pfci_result_has_no_disqualifying_gate(self):
        result = screen_item(_pfci_item())
        self.assertIsNone(result.disqualifying_gate)

    def test_pfci_result_reasons_non_empty(self):
        result = screen_item(_pfci_item())
        self.assertGreater(len(result.reasons), 0)

    def test_critical_failure_effect_gives_pfci(self):
        result = screen_item(_pfci_item(failure_effect=FailureEffect.CRITICAL))
        self.assertEqual(result.outcome, ScreeningOutcome.PFCI)

    def test_at_exact_dimension_threshold_gives_pfci(self):
        result = screen_item(_pfci_item(min_cross_section_cm2=MIN_CROSS_SECTION_CM2))
        self.assertEqual(result.outcome, ScreeningOutcome.PFCI)


class TestGsePreCheck(unittest.TestCase):

    def test_gse_not_in_critical_op_is_non_pfci(self):
        item = _pfci_item(is_gse=True, gse_critical_operation=False)
        result = screen_item(item)
        self.assertEqual(result.outcome, ScreeningOutcome.NON_PFCI)

    def test_gse_not_in_critical_op_records_correct_gate(self):
        item = _pfci_item(is_gse=True, gse_critical_operation=False)
        result = screen_item(item)
        self.assertEqual(result.disqualifying_gate, "GSE-CRITICAL-OPERATION")

    def test_gse_in_critical_op_all_gates_pass_gives_pfci(self):
        item = _pfci_item(is_gse=True, gse_critical_operation=True)
        result = screen_item(item)
        self.assertEqual(result.outcome, ScreeningOutcome.PFCI)

    def test_gse_pfci_reason_mentions_critical_operation(self):
        item = _pfci_item(is_gse=True, gse_critical_operation=True)
        result = screen_item(item)
        combined = " ".join(result.reasons).lower()
        self.assertIn("critical operation", combined)


class TestGate1Structural(unittest.TestCase):

    def test_non_structural_item_is_non_pfci(self):
        item = _pfci_item(is_structural=False)
        result = screen_item(item)
        self.assertEqual(result.outcome, ScreeningOutcome.NON_PFCI)

    def test_non_structural_item_records_gate_1(self):
        item = _pfci_item(is_structural=False)
        result = screen_item(item)
        self.assertEqual(result.disqualifying_gate, "GATE-1-STRUCTURAL")


class TestGate2FailureEffect(unittest.TestCase):

    def test_marginal_failure_effect_is_non_pfci(self):
        item = _pfci_item(failure_effect=FailureEffect.MARGINAL)
        result = screen_item(item)
        self.assertEqual(result.outcome, ScreeningOutcome.NON_PFCI)

    def test_negligible_failure_effect_is_non_pfci(self):
        item = _pfci_item(failure_effect=FailureEffect.NEGLIGIBLE)
        result = screen_item(item)
        self.assertEqual(result.outcome, ScreeningOutcome.NON_PFCI)

    def test_failure_effect_gate_records_gate_2(self):
        item = _pfci_item(failure_effect=FailureEffect.MARGINAL)
        result = screen_item(item)
        self.assertEqual(result.disqualifying_gate, "GATE-2-FAILURE-EFFECT")


class TestGate3TensileLoad(unittest.TestCase):

    def test_no_tensile_load_is_non_pfci(self):
        item = _pfci_item(carries_tensile_load=False)
        result = screen_item(item)
        self.assertEqual(result.outcome, ScreeningOutcome.NON_PFCI)

    def test_no_tensile_load_records_gate_3(self):
        item = _pfci_item(carries_tensile_load=False)
        result = screen_item(item)
        self.assertEqual(result.disqualifying_gate, "GATE-3-TENSILE-LOAD")


class TestGate4Material(unittest.TestCase):

    def test_non_susceptible_material_is_non_pfci(self):
        item = _pfci_item(material_susceptible=False)
        result = screen_item(item)
        self.assertEqual(result.outcome, ScreeningOutcome.NON_PFCI)

    def test_non_susceptible_material_records_gate_4(self):
        item = _pfci_item(material_susceptible=False)
        result = screen_item(item)
        self.assertEqual(result.disqualifying_gate, "GATE-4-MATERIAL")


class TestGate5Dimension(unittest.TestCase):

    def test_below_threshold_is_non_pfci(self):
        item = _pfci_item(min_cross_section_cm2=MIN_CROSS_SECTION_CM2 - 0.01)
        result = screen_item(item)
        self.assertEqual(result.outcome, ScreeningOutcome.NON_PFCI)

    def test_below_threshold_records_gate_5(self):
        item = _pfci_item(min_cross_section_cm2=MIN_CROSS_SECTION_CM2 - 0.01)
        result = screen_item(item)
        self.assertEqual(result.disqualifying_gate, "GATE-5-DIMENSION")

    def test_zero_cross_section_is_non_pfci(self):
        item = _pfci_item(min_cross_section_cm2=0.0)
        result = screen_item(item)
        self.assertEqual(result.outcome, ScreeningOutcome.NON_PFCI)

    def test_programme_override_tighter_threshold(self):
        # Item just above module default but below tighter programme override.
        item = _pfci_item(min_cross_section_cm2=1.5)
        result = screen_item(item, min_cross_section_override_cm2=2.0)
        self.assertEqual(result.outcome, ScreeningOutcome.NON_PFCI)
        self.assertEqual(result.disqualifying_gate, "GATE-5-DIMENSION")

    def test_programme_override_passes_item_above_threshold(self):
        item = _pfci_item(min_cross_section_cm2=1.5)
        result = screen_item(item, min_cross_section_override_cm2=1.0)
        self.assertEqual(result.outcome, ScreeningOutcome.PFCI)


class TestBatchScreening(unittest.TestCase):

    def test_batch_counts_pfci_and_non_pfci(self):
        items = [
            _pfci_item(item_id="A"),               # PFCI
            _pfci_item(item_id="B", is_structural=False),  # NON_PFCI Gate-1
            _pfci_item(item_id="C", carries_tensile_load=False),  # NON_PFCI Gate-3
        ]
        summary = screen_batch(items)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["pfci_count"], 1)
        self.assertEqual(summary["non_pfci_count"], 2)

    def test_batch_pfci_ids_list(self):
        items = [
            _pfci_item(item_id="X"),
            _pfci_item(item_id="Y", failure_effect=FailureEffect.NEGLIGIBLE),
        ]
        summary = screen_batch(items)
        self.assertEqual(summary["pfci_ids"], ["X"])

    def test_batch_empty_list(self):
        summary = screen_batch([])
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["pfci_count"], 0)
        self.assertEqual(summary["non_pfci_count"], 0)
        self.assertEqual(summary["pfci_ids"], [])

    def test_batch_results_length_matches_input(self):
        items = [_pfci_item(item_id=str(i)) for i in range(5)]
        summary = screen_batch(items)
        self.assertEqual(len(summary["results"]), 5)


class TestInputValidation(unittest.TestCase):

    def test_empty_item_id_raises(self):
        item = _pfci_item(item_id="")
        with self.assertRaises(ValueError):
            screen_item(item)

    def test_whitespace_item_id_raises(self):
        item = _pfci_item(item_id="   ")
        with self.assertRaises(ValueError):
            screen_item(item)

    def test_negative_cross_section_raises(self):
        item = _pfci_item(min_cross_section_cm2=-0.5)
        with self.assertRaises(ValueError):
            screen_item(item)

    def test_negative_override_threshold_raises(self):
        item = _pfci_item()
        with self.assertRaises(ValueError):
            screen_item(item, min_cross_section_override_cm2=-1.0)


if __name__ == "__main__":
    unittest.main()
