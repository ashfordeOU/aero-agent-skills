"""Contract tests for the clause 4.3.1 procurement conformity logic."""

import unittest

from q60_class_1_procurement_general_requirements_logic import (
    ASSURANCE_LADDER,
    BASELINE_TOLERANCE,
    MANDATORY_TRACEABILITY,
    assess_purchase,
    assurance_rank,
    is_declared_substitution,
    meets_assurance,
    missing_flowdown,
    missing_traceability,
    normalize_token,
    temperature_range_covered,
    validate_baseline,
    validate_delivered_lot,
    validate_purchase_order,
)

FLOWDOWN = ["par-4-3-1", "par-4-3-4", "par-4-4-2"]


def _baseline(**overrides):
    baseline = {
        "part_number": "EM-7712-CL1",
        "manufacturer": "Example Microelectronics",
        "assurance_level": "class-1",
        "temperature_range_c": [-55.0, 125.0],
        "required_tid_krad": 100.0,
        "required_flowdown": list(FLOWDOWN),
        "approved_alternates": ["em-7712-cl1-b"],
    }
    baseline.update(overrides)
    return baseline


def _order(**overrides):
    order = {
        "part_number": "EM-7712-CL1",
        "manufacturer": "Example Microelectronics",
        "assurance_level": "class-1",
        "quantity": 40,
        "flowed_clauses": list(FLOWDOWN),
    }
    order.update(overrides)
    return order


def _lot(**overrides):
    lot = {
        "lot_code": "LOT-2631-A",
        "quantity": 40,
        "temperature_range_c": [-55.0, 125.0],
        "tid_krad": 100.0,
        "records": list(MANDATORY_TRACEABILITY),
    }
    lot.update(overrides)
    return lot


def _spec(**overrides):
    spec = {
        "baseline": _baseline(),
        "purchase_order": _order(),
        "delivered_lot": _lot(),
    }
    spec.update(overrides)
    return spec


class BaselineValidationTests(unittest.TestCase):
    def test_baseline_returned_normalized(self):
        agreed = validate_baseline(_baseline())
        self.assertEqual(agreed["manufacturer"], "example-microelectronics")
        self.assertEqual(agreed["assurance_level"], "class-1")

    def test_missing_baseline_key_rejected(self):
        bad = _baseline()
        del bad["required_tid_krad"]
        with self.assertRaises(ValueError):
            validate_baseline(bad)

    def test_inverted_temperature_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_baseline(_baseline(temperature_range_c=[125.0, -55.0]))

    def test_degenerate_temperature_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_baseline(_baseline(temperature_range_c=[25.0, 25.0]))

    def test_negative_dose_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_baseline(_baseline(required_tid_krad=-10.0))

    def test_repeated_flowdown_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_baseline(_baseline(required_flowdown=["par-4-3-1", "PAR 4 3 1"]))

    def test_non_mapping_baseline_rejected(self):
        with self.assertRaises(ValueError):
            validate_baseline(["EM-7712-CL1"])

    def test_token_normalization_is_hyphenated_lower_case(self):
        self.assertEqual(normalize_token("Class_1"), "class-1")


class AssuranceLadderTests(unittest.TestCase):
    def test_ladder_runs_weakest_to_strongest(self):
        self.assertLess(assurance_rank("commercial"), assurance_rank("class-1"))

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            assurance_rank("aerospace-grade")

    def test_equal_level_meets_the_baseline(self):
        self.assertTrue(meets_assurance("class-1", "class-1"))

    def test_higher_level_meets_a_lower_baseline(self):
        self.assertTrue(meets_assurance("class-1", "class-2"))

    def test_lower_level_does_not_meet_the_baseline(self):
        self.assertFalse(meets_assurance("class-3", "class-1"))

    def test_every_ladder_entry_is_normalized(self):
        for level in ASSURANCE_LADDER:
            self.assertEqual(normalize_token(level), level)


class OrderAndLotValidationTests(unittest.TestCase):
    def test_order_returned_normalized(self):
        placed = validate_purchase_order(_order(assurance_level="Class 1"))
        self.assertEqual(placed["assurance_level"], "class-1")

    def test_zero_order_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_purchase_order(_order(quantity=0))

    def test_boolean_order_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_purchase_order(_order(quantity=True))

    def test_missing_order_key_rejected(self):
        bad = _order()
        del bad["flowed_clauses"]
        with self.assertRaises(ValueError):
            validate_purchase_order(bad)

    def test_blank_lot_code_rejected(self):
        with self.assertRaises(ValueError):
            validate_delivered_lot(_lot(lot_code="  "))

    def test_lot_records_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            validate_delivered_lot(_lot(records="screening-records"))

    def test_non_mapping_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_delivered_lot(["LOT-2631-A"])


class SubstitutionAndFlowdownTests(unittest.TestCase):
    def test_baseline_part_is_not_a_substitution(self):
        self.assertTrue(is_declared_substitution(_order(), _baseline()))

    def test_declared_alternate_is_accepted(self):
        self.assertTrue(is_declared_substitution(_order(part_number="EM-7712-CL1-B"),
                                                 _baseline()))

    def test_undeclared_part_number_is_not_accepted(self):
        self.assertFalse(is_declared_substitution(_order(part_number="EM-7712-CL2"),
                                                  _baseline()))

    def test_baseline_part_from_another_manufacturer_is_not_accepted(self):
        self.assertFalse(is_declared_substitution(
            _order(manufacturer="Other Semiconductor"), _baseline()))

    def test_full_flowdown_leaves_nothing_unflowed(self):
        self.assertEqual(missing_flowdown(_order(), _baseline()), [])

    def test_unflowed_requirement_reported(self):
        flowed = [ref for ref in FLOWDOWN if ref != "par-4-4-2"]
        self.assertEqual(missing_flowdown(_order(flowed_clauses=flowed), _baseline()),
                         ["par-4-4-2"])

    def test_missing_flowdown_preserves_baseline_order(self):
        self.assertEqual(missing_flowdown(_order(flowed_clauses=[]), _baseline()),
                         list(FLOWDOWN))


class RangeDoseAndRecordTests(unittest.TestCase):
    def test_identical_range_is_covered(self):
        self.assertTrue(temperature_range_covered([-55.0, 125.0], [-55.0, 125.0]))

    def test_wider_range_is_covered(self):
        self.assertTrue(temperature_range_covered([-65.0, 150.0], [-55.0, 125.0]))

    def test_narrow_upper_limit_is_not_covered(self):
        self.assertFalse(temperature_range_covered([-55.0, 85.0], [-55.0, 125.0]))

    def test_narrow_lower_limit_is_not_covered(self):
        self.assertFalse(temperature_range_covered([-40.0, 125.0], [-55.0, 125.0]))

    def test_complete_record_set_leaves_nothing_absent(self):
        self.assertEqual(missing_traceability(_lot()), [])

    def test_absent_record_reported(self):
        records = [r for r in MANDATORY_TRACEABILITY if r != "screening-records"]
        self.assertEqual(missing_traceability(_lot(records=records)),
                         ["screening-records"])

    def test_tolerance_is_representation_sized_only(self):
        self.assertLess(BASELINE_TOLERANCE, 1e-6)


class PurchaseAssessmentTests(unittest.TestCase):
    def test_conformant_purchase_passes(self):
        result = assess_purchase(_spec())
        self.assertTrue(result["conformant"])
        self.assertEqual(result["findings"], [])

    def test_dose_exactly_at_the_baseline_is_met(self):
        result = assess_purchase(_spec())
        self.assertAlmostEqual(result["delivered_lot"]["tid_krad"],
                               result["baseline"]["required_tid_krad"], places=9)
        self.assertTrue(result["dose_capability_met"])

    def test_dose_below_the_baseline_blocks_conformity(self):
        result = assess_purchase(_spec(delivered_lot=_lot(tid_krad=50.0)))
        self.assertFalse(result["dose_capability_met"])
        self.assertFalse(result["conformant"])

    def test_temperature_range_exactly_at_the_baseline_is_met(self):
        result = assess_purchase(_spec())
        self.assertTrue(result["temperature_range_met"])

    def test_narrower_delivered_range_blocks_conformity(self):
        result = assess_purchase(
            _spec(delivered_lot=_lot(temperature_range_c=[-40.0, 85.0])))
        self.assertFalse(result["temperature_range_met"])

    def test_order_below_the_baseline_level_blocks_conformity(self):
        result = assess_purchase(_spec(purchase_order=_order(assurance_level="class-2")))
        self.assertFalse(result["assurance_level_met"])
        self.assertFalse(result["conformant"])

    def test_undeclared_substitution_blocks_conformity(self):
        result = assess_purchase(_spec(purchase_order=_order(part_number="EM-7712-CL2")))
        self.assertFalse(result["substitution_declared"])
        self.assertFalse(result["conformant"])

    def test_unflowed_requirement_blocks_conformity(self):
        flowed = [ref for ref in FLOWDOWN if ref != "par-4-3-4"]
        result = assess_purchase(_spec(purchase_order=_order(flowed_clauses=flowed)))
        self.assertEqual(result["unflowed_requirements"], ["par-4-3-4"])
        self.assertFalse(result["conformant"])

    def test_short_delivery_blocks_conformity(self):
        result = assess_purchase(_spec(delivered_lot=_lot(quantity=30)))
        self.assertFalse(result["quantity_met"])

    def test_over_delivery_is_not_a_finding(self):
        result = assess_purchase(_spec(delivered_lot=_lot(quantity=45)))
        self.assertTrue(result["quantity_met"])
        self.assertTrue(result["conformant"])

    def test_absent_traceability_record_blocks_conformity(self):
        records = [r for r in MANDATORY_TRACEABILITY if r != "certificate-of-conformity"]
        result = assess_purchase(_spec(delivered_lot=_lot(records=records)))
        self.assertEqual(result["missing_records"], ["certificate-of-conformity"])
        self.assertFalse(result["conformant"])

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["delivered_lot"]
        with self.assertRaises(ValueError):
            assess_purchase(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_purchase(["baseline"])

    def test_every_shortfall_is_named_not_only_the_first(self):
        result = assess_purchase(_spec(
            purchase_order=_order(assurance_level="class-3", flowed_clauses=[]),
            delivered_lot=_lot(quantity=10, tid_krad=10.0, records=[])))
        self.assertGreaterEqual(len(result["findings"]), 8)


if __name__ == "__main__":
    unittest.main()
