import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from fci_classification_logic import (
    determine_fci_status,
    batch_determine_fci,
    summary_counts,
    FCIInputError,
    VALID_ITEM_TYPES,
    VALID_CONSEQUENCE_LEVELS,
)


class TestPressurizedSystemCriterion(unittest.TestCase):
    def test_pressure_vessel_catastrophic_is_fci(self):
        result = determine_fci_status({
            "name": "LOX_tank",
            "item_type": "pressure_vessel",
            "failure_consequence": "catastrophic",
        })
        self.assertEqual(result["fci_status"], "FCI")
        self.assertIn("PRESSURE_VESSEL_OR_LINE", result["fci_categories"])

    def test_pressurized_line_critical_is_fci(self):
        result = determine_fci_status({
            "name": "helium_pressurant_line",
            "item_type": "pressurized_line",
            "failure_consequence": "critical",
        })
        self.assertEqual(result["fci_status"], "FCI")
        self.assertIn("PRESSURE_VESSEL_OR_LINE", result["fci_categories"])

    def test_pressurized_fitting_catastrophic_is_fci(self):
        result = determine_fci_status({
            "name": "fuel_feed_fitting",
            "item_type": "pressurized_fitting",
            "failure_consequence": "catastrophic",
        })
        self.assertEqual(result["fci_status"], "FCI")
        self.assertIn("PRESSURE_VESSEL_OR_LINE", result["fci_categories"])

    def test_pressurized_line_non_critical_is_not_fci(self):
        result = determine_fci_status({
            "name": "low_pressure_purge_line",
            "item_type": "pressurized_line",
            "failure_consequence": "non_critical",
        })
        self.assertEqual(result["fci_status"], "NON_FCI")
        self.assertNotIn("PRESSURE_VESSEL_OR_LINE", result["fci_categories"])


class TestFLLICriterion(unittest.TestCase):
    def test_metallic_primary_flli_catastrophic_is_fci(self):
        result = determine_fci_status({
            "name": "main_spar_lug",
            "item_type": "metallic_primary",
            "failure_consequence": "catastrophic",
            "life_limited_by_fracture": True,
        })
        self.assertEqual(result["fci_status"], "FCI")
        self.assertIn("FLLI", result["fci_categories"])

    def test_metallic_primary_flli_critical_is_fci(self):
        result = determine_fci_status({
            "name": "attachment_bracket",
            "item_type": "metallic_primary",
            "failure_consequence": "critical",
            "life_limited_by_fracture": True,
        })
        self.assertEqual(result["fci_status"], "FCI")
        self.assertIn("FLLI", result["fci_categories"])

    def test_flli_non_critical_is_not_fci(self):
        result = determine_fci_status({
            "name": "secondary_bracket",
            "item_type": "metallic_secondary",
            "failure_consequence": "non_critical",
            "life_limited_by_fracture": True,
        })
        self.assertEqual(result["fci_status"], "NON_FCI")
        self.assertNotIn("FLLI", result["fci_categories"])

    def test_life_limited_by_fracture_defaults_false(self):
        result = determine_fci_status({
            "name": "panel_attach",
            "item_type": "metallic_primary",
            "failure_consequence": "catastrophic",
        })
        self.assertNotIn("FLLI", result["fci_categories"])


class TestNDTLimitedCriterion(unittest.TestCase):
    def test_ndt_inaccessible_catastrophic_is_fci(self):
        result = determine_fci_status({
            "name": "hidden_weld_joint",
            "item_type": "weld",
            "failure_consequence": "catastrophic",
            "ndt_accessible": False,
        })
        self.assertEqual(result["fci_status"], "FCI")
        self.assertIn("NDT_LIMITED", result["fci_categories"])

    def test_ndt_accessible_does_not_trigger_ndt_criterion(self):
        result = determine_fci_status({
            "name": "visible_weld_joint",
            "item_type": "weld",
            "failure_consequence": "catastrophic",
            "ndt_accessible": True,
        })
        self.assertNotIn("NDT_LIMITED", result["fci_categories"])

    def test_ndt_inaccessible_non_critical_is_not_fci(self):
        result = determine_fci_status({
            "name": "inner_bracket_weld",
            "item_type": "weld",
            "failure_consequence": "non_critical",
            "ndt_accessible": False,
        })
        self.assertEqual(result["fci_status"], "NON_FCI")

    def test_ndt_accessible_defaults_true(self):
        result = determine_fci_status({
            "name": "fastener_row",
            "item_type": "fastener",
            "failure_consequence": "catastrophic",
        })
        self.assertNotIn("NDT_LIMITED", result["fci_categories"])


class TestCompositePrimaryCriterion(unittest.TestCase):
    def test_composite_primary_catastrophic_is_fci(self):
        result = determine_fci_status({
            "name": "cfrp_strut",
            "item_type": "composite_primary",
            "failure_consequence": "catastrophic",
        })
        self.assertEqual(result["fci_status"], "FCI")
        self.assertIn("COMPOSITE_PRIMARY", result["fci_categories"])

    def test_composite_primary_critical_is_fci(self):
        result = determine_fci_status({
            "name": "cfrp_boom",
            "item_type": "composite_primary",
            "failure_consequence": "critical",
        })
        self.assertEqual(result["fci_status"], "FCI")
        self.assertIn("COMPOSITE_PRIMARY", result["fci_categories"])

    def test_composite_secondary_does_not_trigger_composite_criterion(self):
        result = determine_fci_status({
            "name": "cfrp_fairing_panel",
            "item_type": "composite_secondary",
            "failure_consequence": "catastrophic",
        })
        self.assertNotIn("COMPOSITE_PRIMARY", result["fci_categories"])

    def test_composite_primary_non_critical_is_not_fci(self):
        result = determine_fci_status({
            "name": "composite_cover",
            "item_type": "composite_primary",
            "failure_consequence": "non_critical",
        })
        self.assertEqual(result["fci_status"], "NON_FCI")
        self.assertNotIn("COMPOSITE_PRIMARY", result["fci_categories"])


class TestMultipleCriteria(unittest.TestCase):
    def test_flli_and_ndt_limited_both_assigned(self):
        result = determine_fci_status({
            "name": "inaccessible_life_limited_lug",
            "item_type": "metallic_primary",
            "failure_consequence": "catastrophic",
            "ndt_accessible": False,
            "life_limited_by_fracture": True,
        })
        self.assertEqual(result["fci_status"], "FCI")
        self.assertIn("FLLI", result["fci_categories"])
        self.assertIn("NDT_LIMITED", result["fci_categories"])
        self.assertEqual(len(result["fci_categories"]), 2)

    def test_non_fci_item_has_empty_categories(self):
        result = determine_fci_status({
            "name": "secondary_bracket",
            "item_type": "metallic_secondary",
            "failure_consequence": "non_critical",
        })
        self.assertEqual(result["fci_categories"], [])
        self.assertEqual(result["fci_status"], "NON_FCI")


class TestValidation(unittest.TestCase):
    def test_missing_name_raises(self):
        with self.assertRaises(FCIInputError):
            determine_fci_status({
                "item_type": "metallic_primary",
                "failure_consequence": "catastrophic",
            })

    def test_missing_item_type_raises(self):
        with self.assertRaises(FCIInputError):
            determine_fci_status({
                "name": "test_item",
                "failure_consequence": "catastrophic",
            })

    def test_missing_consequence_raises(self):
        with self.assertRaises(FCIInputError):
            determine_fci_status({
                "name": "test_item",
                "item_type": "metallic_primary",
            })

    def test_invalid_item_type_raises(self):
        with self.assertRaises(FCIInputError):
            determine_fci_status({
                "name": "test_item",
                "item_type": "unknown_widget",
                "failure_consequence": "catastrophic",
            })

    def test_invalid_consequence_raises(self):
        with self.assertRaises(FCIInputError):
            determine_fci_status({
                "name": "test_item",
                "item_type": "metallic_primary",
                "failure_consequence": "severe",
            })


class TestBatchAndSummary(unittest.TestCase):
    def test_batch_returns_correct_statuses(self):
        items = [
            {"name": "A", "item_type": "pressure_vessel", "failure_consequence": "catastrophic"},
            {"name": "B", "item_type": "metallic_secondary", "failure_consequence": "non_critical"},
        ]
        results = batch_determine_fci(items)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["fci_status"], "FCI")
        self.assertEqual(results[1]["fci_status"], "NON_FCI")

    def test_summary_counts_correct(self):
        items = [
            {"name": "A", "item_type": "pressure_vessel", "failure_consequence": "catastrophic"},
            {"name": "B", "item_type": "pressurized_line", "failure_consequence": "critical"},
            {"name": "C", "item_type": "metallic_secondary", "failure_consequence": "non_critical"},
        ]
        results = batch_determine_fci(items)
        counts = summary_counts(results)
        self.assertEqual(counts["FCI"], 2)
        self.assertEqual(counts["NON_FCI"], 1)
        self.assertEqual(counts["total"], 3)

    def test_batch_non_list_raises(self):
        with self.assertRaises(FCIInputError):
            batch_determine_fci("not_a_list")

    def test_result_contains_rationale_list(self):
        result = determine_fci_status({
            "name": "test_part",
            "item_type": "pressure_vessel",
            "failure_consequence": "catastrophic",
        })
        self.assertIsInstance(result["rationale"], list)
        self.assertGreater(len(result["rationale"]), 0)

    def test_name_echoed_in_result(self):
        result = determine_fci_status({
            "name": "my_specific_item",
            "item_type": "composite_primary",
            "failure_consequence": "critical",
        })
        self.assertEqual(result["name"], "my_specific_item")

    def test_batch_empty_list_returns_empty(self):
        self.assertEqual(batch_determine_fci([]), [])


if __name__ == "__main__":
    unittest.main()
