"""
test_drd_fci_lists.py

Offline stdlib unittest for drd_fci_lists_logic.py.
Run: python3 test_drd_fci_lists.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from drd_fci_lists_logic import (
    compute_margin_of_safety,
    validate_fcil_entry,
    validate_pfcil_entry,
    validate_fllil_entry,
    categorize_item,
    build_register,
    check_pfcil_subset_of_fcil,
    check_fllil_subset_of_fcil,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _good_fcil_entry():
    return {
        "item_id": "FCIL-001",
        "description": "Main lug attachment bolt",
        "material": "Ti-6Al-4V",
        "flaw_assumption_mm": 0.5,
        "fracture_toughness_mpa_sqrt_m": 55.0,
        "stress_mpa": 200.0,
        "required_life_cycles": 1000,
        "computed_life_cycles": 2500,
        "disposition": "safe_life",
    }


def _good_pfcil_entry():
    entry = _good_fcil_entry()
    entry["item_id"] = "PFCIL-001"
    entry["description"] = "Crew hatch hinge pin"
    entry["failure_consequence"] = "loss_of_life"
    return entry


def _good_fllil_entry():
    entry = _good_fcil_entry()
    entry["item_id"] = "FLLIL-001"
    entry["description"] = "Pressure vessel stiffening ring"
    entry["material"] = "Inconel 718"
    entry["life_limit_cycles"] = 1500
    entry["retest_interval_cycles"] = 400
    return entry


# ---------------------------------------------------------------------------
# FCIL entry validation
# ---------------------------------------------------------------------------

class TestFcilEntryValidation(unittest.TestCase):

    def test_valid_entry_produces_no_findings(self):
        self.assertEqual(validate_fcil_entry(_good_fcil_entry()), [])

    def test_missing_single_field_flagged(self):
        entry = _good_fcil_entry()
        del entry["material"]
        findings = validate_fcil_entry(entry)
        self.assertTrue(findings, "expected findings for missing field")
        self.assertTrue(any("missing" in f for f in findings))

    def test_missing_multiple_fields_flagged(self):
        entry = _good_fcil_entry()
        del entry["stress_mpa"]
        del entry["disposition"]
        findings = validate_fcil_entry(entry)
        self.assertTrue(findings)

    def test_zero_flaw_assumption_flagged(self):
        entry = _good_fcil_entry()
        entry["flaw_assumption_mm"] = 0.0
        self.assertTrue(validate_fcil_entry(entry))

    def test_negative_flaw_assumption_flagged(self):
        entry = _good_fcil_entry()
        entry["flaw_assumption_mm"] = -1.0
        self.assertTrue(validate_fcil_entry(entry))

    def test_negative_stress_flagged(self):
        entry = _good_fcil_entry()
        entry["stress_mpa"] = -50.0
        self.assertTrue(validate_fcil_entry(entry))

    def test_zero_required_life_flagged(self):
        entry = _good_fcil_entry()
        entry["required_life_cycles"] = 0
        self.assertTrue(validate_fcil_entry(entry))

    def test_invalid_disposition_flagged(self):
        entry = _good_fcil_entry()
        entry["disposition"] = "hope_and_prayer"
        self.assertTrue(validate_fcil_entry(entry))

    def test_valid_disposition_fracture_proof(self):
        entry = _good_fcil_entry()
        entry["disposition"] = "fracture_proof"
        self.assertEqual(validate_fcil_entry(entry), [])

    def test_valid_disposition_leak_before_burst(self):
        entry = _good_fcil_entry()
        entry["disposition"] = "leak_before_burst"
        self.assertEqual(validate_fcil_entry(entry), [])

    def test_valid_disposition_retirement(self):
        entry = _good_fcil_entry()
        entry["disposition"] = "retirement"
        self.assertEqual(validate_fcil_entry(entry), [])


# ---------------------------------------------------------------------------
# PFCIL entry validation
# ---------------------------------------------------------------------------

class TestPfcilEntryValidation(unittest.TestCase):

    def test_valid_pfcil_entry_produces_no_findings(self):
        self.assertEqual(validate_pfcil_entry(_good_pfcil_entry()), [])

    def test_missing_failure_consequence_flagged(self):
        entry = _good_pfcil_entry()
        del entry["failure_consequence"]
        findings = validate_pfcil_entry(entry)
        self.assertTrue(any("PFCIL" in f for f in findings))

    def test_invalid_failure_consequence_flagged(self):
        entry = _good_pfcil_entry()
        entry["failure_consequence"] = "loss_of_paint"
        self.assertTrue(validate_pfcil_entry(entry))

    def test_loss_of_life_accepted(self):
        entry = _good_pfcil_entry()
        entry["failure_consequence"] = "loss_of_life"
        self.assertEqual(validate_pfcil_entry(entry), [])

    def test_loss_of_vehicle_accepted(self):
        entry = _good_pfcil_entry()
        entry["failure_consequence"] = "loss_of_vehicle"
        self.assertEqual(validate_pfcil_entry(entry), [])

    def test_loss_of_mission_accepted(self):
        entry = _good_pfcil_entry()
        entry["failure_consequence"] = "loss_of_mission"
        self.assertEqual(validate_pfcil_entry(entry), [])

    def test_pfcil_inherits_fcil_checks(self):
        entry = _good_pfcil_entry()
        entry["stress_mpa"] = -1.0
        self.assertTrue(validate_pfcil_entry(entry))


# ---------------------------------------------------------------------------
# FLLIL entry validation
# ---------------------------------------------------------------------------

class TestFllilEntryValidation(unittest.TestCase):

    def test_valid_fllil_entry_produces_no_findings(self):
        self.assertEqual(validate_fllil_entry(_good_fllil_entry()), [])

    def test_missing_life_limit_flagged(self):
        entry = _good_fllil_entry()
        del entry["life_limit_cycles"]
        self.assertTrue(validate_fllil_entry(entry))

    def test_missing_retest_interval_flagged(self):
        entry = _good_fllil_entry()
        del entry["retest_interval_cycles"]
        self.assertTrue(validate_fllil_entry(entry))

    def test_life_limit_below_required_life_flagged(self):
        entry = _good_fllil_entry()
        entry["required_life_cycles"] = 1000
        entry["life_limit_cycles"] = 800  # below required
        self.assertTrue(validate_fllil_entry(entry))

    def test_life_limit_equal_to_required_life_accepted(self):
        entry = _good_fllil_entry()
        entry["required_life_cycles"] = 1000
        entry["life_limit_cycles"] = 1000
        entry["retest_interval_cycles"] = 400
        self.assertEqual(validate_fllil_entry(entry), [])

    def test_retest_interval_exceeds_life_limit_flagged(self):
        entry = _good_fllil_entry()
        entry["life_limit_cycles"] = 1500
        entry["retest_interval_cycles"] = 2000  # above life limit
        self.assertTrue(validate_fllil_entry(entry))

    def test_fllil_inherits_fcil_checks(self):
        entry = _good_fllil_entry()
        del entry["material"]
        self.assertTrue(validate_fllil_entry(entry))


# ---------------------------------------------------------------------------
# Margin of safety
# ---------------------------------------------------------------------------

class TestMarginOfSafety(unittest.TestCase):

    def test_positive_margin_when_computed_exceeds_required(self):
        mos = compute_margin_of_safety(2500.0, 1000.0)
        self.assertAlmostEqual(mos, 1.5)

    def test_zero_margin_when_computed_equals_required(self):
        mos = compute_margin_of_safety(1000.0, 1000.0)
        self.assertAlmostEqual(mos, 0.0)

    def test_negative_margin_when_computed_below_required(self):
        mos = compute_margin_of_safety(800.0, 1000.0)
        self.assertAlmostEqual(mos, -0.2)

    def test_small_computed_life_gives_large_negative_margin(self):
        mos = compute_margin_of_safety(100.0, 1000.0)
        self.assertAlmostEqual(mos, -0.9)

    def test_zero_required_life_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(1000.0, 0.0)

    def test_zero_computed_life_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(0.0, 1000.0)

    def test_negative_required_life_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(1000.0, -500.0)


# ---------------------------------------------------------------------------
# Item categorization
# ---------------------------------------------------------------------------

class TestCategorizeItem(unittest.TestCase):

    def test_non_fracture_critical_screened_out(self):
        result = categorize_item(None, False, False)
        self.assertEqual(result, [])

    def test_fracture_critical_without_consequence_or_limit_goes_to_fcil_only(self):
        result = categorize_item(None, False, True)
        self.assertIn("FCIL", result)
        self.assertNotIn("PFCIL", result)
        self.assertNotIn("FLLIL", result)

    def test_loss_of_life_consequence_assigns_pfcil_and_fcil(self):
        result = categorize_item("loss_of_life", False, True)
        self.assertIn("PFCIL", result)
        self.assertIn("FCIL", result)

    def test_loss_of_vehicle_consequence_assigns_pfcil_and_fcil(self):
        result = categorize_item("loss_of_vehicle", False, True)
        self.assertIn("PFCIL", result)
        self.assertIn("FCIL", result)

    def test_life_limited_item_assigns_fllil_and_fcil(self):
        result = categorize_item(None, True, True)
        self.assertIn("FLLIL", result)
        self.assertIn("FCIL", result)
        self.assertNotIn("PFCIL", result)

    def test_pfcil_and_life_limited_assigns_all_three_lists(self):
        result = categorize_item("loss_of_mission", True, True)
        self.assertIn("PFCIL", result)
        self.assertIn("FCIL", result)
        self.assertIn("FLLIL", result)

    def test_unknown_consequence_does_not_assign_pfcil(self):
        result = categorize_item("loss_of_paint", False, True)
        self.assertNotIn("PFCIL", result)
        self.assertIn("FCIL", result)


# ---------------------------------------------------------------------------
# Register builder
# ---------------------------------------------------------------------------

class TestBuildRegister(unittest.TestCase):

    def _items(self):
        return [
            {
                "item_id": "A1",
                "is_fracture_critical": True,
                "failure_consequence": "loss_of_mission",
                "has_life_limit": False,
            },
            {
                "item_id": "A2",
                "is_fracture_critical": True,
                "failure_consequence": None,
                "has_life_limit": True,
            },
            {
                "item_id": "A3",
                "is_fracture_critical": False,
                "failure_consequence": None,
                "has_life_limit": False,
            },
            {
                "item_id": "A4",
                "is_fracture_critical": True,
                "failure_consequence": "loss_of_life",
                "has_life_limit": True,
            },
        ]

    def test_screened_out_item_in_screened_out_list(self):
        reg = build_register(self._items())
        self.assertIn("A3", reg["screened_out"])

    def test_screened_out_item_absent_from_all_registers(self):
        reg = build_register(self._items())
        self.assertNotIn("A3", reg["FCIL"])
        self.assertNotIn("A3", reg["PFCIL"])
        self.assertNotIn("A3", reg["FLLIL"])

    def test_pfcil_item_present_on_fcil(self):
        reg = build_register(self._items())
        self.assertIn("A1", reg["PFCIL"])
        self.assertIn("A1", reg["FCIL"])

    def test_fllil_item_present_on_fcil(self):
        reg = build_register(self._items())
        self.assertIn("A2", reg["FLLIL"])
        self.assertIn("A2", reg["FCIL"])

    def test_item_on_all_three_lists(self):
        reg = build_register(self._items())
        self.assertIn("A4", reg["PFCIL"])
        self.assertIn("A4", reg["FCIL"])
        self.assertIn("A4", reg["FLLIL"])

    def test_missing_item_id_raises_value_error(self):
        with self.assertRaises(ValueError):
            build_register([{"is_fracture_critical": True}])

    def test_empty_item_list_returns_empty_registers(self):
        reg = build_register([])
        self.assertEqual(reg["FCIL"], [])
        self.assertEqual(reg["PFCIL"], [])
        self.assertEqual(reg["FLLIL"], [])
        self.assertEqual(reg["screened_out"], [])


# ---------------------------------------------------------------------------
# Cross-reference checks
# ---------------------------------------------------------------------------

class TestCrossReferenceChecks(unittest.TestCase):

    def test_pfcil_subset_of_fcil_no_gap(self):
        self.assertEqual(
            check_pfcil_subset_of_fcil(["A1", "A4"], ["A1", "A2", "A4"]),
            []
        )

    def test_pfcil_item_absent_from_fcil_returned_as_finding(self):
        result = check_pfcil_subset_of_fcil(["A1", "A9"], ["A1", "A2"])
        self.assertIn("A9", result)
        self.assertNotIn("A1", result)

    def test_fllil_subset_of_fcil_no_gap(self):
        self.assertEqual(
            check_fllil_subset_of_fcil(["A2"], ["A1", "A2", "A4"]),
            []
        )

    def test_fllil_item_absent_from_fcil_returned_as_finding(self):
        result = check_fllil_subset_of_fcil(["A7"], ["A1", "A2"])
        self.assertIn("A7", result)

    def test_empty_pfcil_against_populated_fcil_no_gap(self):
        self.assertEqual(check_pfcil_subset_of_fcil([], ["A1", "A2"]), [])

    def test_empty_fllil_against_populated_fcil_no_gap(self):
        self.assertEqual(check_fllil_subset_of_fcil([], ["A1", "A2"]), [])

    def test_multiple_missing_pfcil_items_all_returned(self):
        result = check_pfcil_subset_of_fcil(["X1", "X2", "X3"], ["X1"])
        self.assertIn("X2", result)
        self.assertIn("X3", result)
        self.assertNotIn("X1", result)


if __name__ == "__main__":
    unittest.main()
