"""Contract tests for the clause 8.2 passive chip procurement logic."""

import unittest

from q6005_passive_chip_procurement_logic import (
    BASELINE_DATA_ITEMS,
    DERATING_LIMITS,
    RATIO_TOLERANCE,
    assess_derating,
    assess_lot_structure,
    assess_order_line,
    assess_termination,
    derating_limit,
    missing_data_items,
    normalize_element_type,
    required_data_items,
    stress_ratio,
    summarize_order,
)

FULL_RESISTOR_ITEMS = [
    "manufacturer-part-identification",
    "procurement-specification",
    "lot-identification",
    "termination-metallization",
    "quality-level",
    "resistive-film-system",
    "resistance-tolerance",
    "trim-method",
]


def resistor_line(**overrides):
    line = {
        "element_type": "chip-resistor",
        "declared_items": list(FULL_RESISTOR_ITEMS),
        "termination": "gold",
        "attach_method": "gold-wire-bond",
        "applied": 0.05,
        "rated": 0.25,
        "lot_identifiers": ["LOT-2431-A"],
        "quantity": 400,
    }
    line.update(overrides)
    return line


class ElementTypeTests(unittest.TestCase):
    def test_canonical_type_passes_through(self):
        self.assertEqual(normalize_element_type("chip-capacitor"), "chip-capacitor")

    def test_bare_noun_is_resolved(self):
        self.assertEqual(normalize_element_type("resistor"), "chip-resistor")

    def test_underscores_and_case_are_normalized(self):
        self.assertEqual(normalize_element_type("Chip_Inductor"), "chip-inductor")

    def test_unknown_element_type_rejected(self):
        with self.assertRaises(ValueError):
            normalize_element_type("chip-transistor")

    def test_empty_element_type_rejected(self):
        with self.assertRaises(ValueError):
            normalize_element_type("   ")

    def test_non_string_element_type_rejected(self):
        with self.assertRaises(ValueError):
            normalize_element_type(7)


class DataItemTests(unittest.TestCase):
    def test_baseline_items_apply_to_every_type(self):
        for element_type in ("chip-resistor", "chip-capacitor", "chip-inductor"):
            required = set(required_data_items(element_type))
            self.assertTrue(set(BASELINE_DATA_ITEMS).issubset(required))

    def test_capacitor_owes_a_dielectric_category(self):
        self.assertIn("dielectric-category", required_data_items("chip-capacitor"))

    def test_resistor_does_not_owe_a_dielectric_category(self):
        self.assertNotIn("dielectric-category", required_data_items("chip-resistor"))

    def test_required_set_is_sorted_and_unique(self):
        required = required_data_items("chip-inductor")
        self.assertEqual(list(required), sorted(set(required)))

    def test_complete_line_has_nothing_missing(self):
        self.assertEqual(missing_data_items("chip-resistor", FULL_RESISTOR_ITEMS), ())

    def test_absent_item_is_named(self):
        declared = [item for item in FULL_RESISTOR_ITEMS if item != "trim-method"]
        self.assertEqual(missing_data_items("chip-resistor", declared), ("trim-method",))

    def test_declared_items_are_normalized_before_comparison(self):
        declared = [item.upper().replace("-", "_") for item in FULL_RESISTOR_ITEMS]
        self.assertEqual(missing_data_items("chip-resistor", declared), ())

    def test_extra_items_do_not_create_findings(self):
        declared = FULL_RESISTOR_ITEMS + ["radiation-report"]
        self.assertEqual(missing_data_items("chip-resistor", declared), ())

    def test_non_sequence_declaration_rejected(self):
        with self.assertRaises(ValueError):
            missing_data_items("chip-resistor", "trim-method")


class DeratingTests(unittest.TestCase):
    def test_limit_is_type_specific(self):
        self.assertAlmostEqual(derating_limit("chip-resistor"), DERATING_LIMITS["chip-resistor"])
        self.assertAlmostEqual(derating_limit("chip-capacitor"), DERATING_LIMITS["chip-capacitor"])

    def test_stress_ratio_is_the_quotient(self):
        self.assertAlmostEqual(stress_ratio(0.05, 0.25), 0.2)

    def test_zero_rated_value_rejected(self):
        with self.assertRaises(ValueError):
            stress_ratio(0.05, 0.0)

    def test_negative_applied_value_rejected(self):
        with self.assertRaises(ValueError):
            stress_ratio(-0.05, 0.25)

    def test_boolean_applied_value_rejected(self):
        with self.assertRaises(ValueError):
            stress_ratio(True, 0.25)

    def test_comfortable_derating_is_compliant(self):
        result = assess_derating("chip-resistor", 0.05, 0.25)
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["finding"])

    def test_ratio_exactly_on_the_limit_is_compliant(self):
        result = assess_derating("chip-resistor", 0.125, 0.25)
        self.assertAlmostEqual(result["ratio"], result["limit"], places=9)
        self.assertTrue(result["compliant"])

    def test_capacitor_voltage_on_its_limit_is_compliant(self):
        result = assess_derating("chip-capacitor", 30.0, 50.0)
        self.assertAlmostEqual(result["ratio"], 0.60, places=9)
        self.assertTrue(result["compliant"])

    def test_over_stressed_element_is_flagged(self):
        result = assess_derating("chip-capacitor", 45.0, 50.0)
        self.assertFalse(result["compliant"])
        self.assertIn("derating limit", result["finding"])

    def test_tolerance_is_narrow_enough_to_catch_a_real_overstress(self):
        result = assess_derating("chip-resistor", 0.25 * 0.5 + 1e-3, 0.25)
        self.assertFalse(result["compliant"])
        self.assertLess(RATIO_TOLERANCE, 1e-6)


class TerminationTests(unittest.TestCase):
    def test_gold_termination_takes_a_gold_wire_bond(self):
        result = assess_termination("gold", "gold-wire-bond")
        self.assertTrue(result["compatible"])

    def test_gold_termination_into_solder_is_a_conflict(self):
        result = assess_termination("gold", "solder")
        self.assertFalse(result["compatible"])
        self.assertIn("embrittle", result["finding"])

    def test_barriered_tin_termination_solders(self):
        self.assertTrue(assess_termination("nickel-barrier-tin", "solder")["compatible"])

    def test_silver_bearing_termination_is_not_a_bonding_surface(self):
        self.assertFalse(assess_termination("palladium-silver", "gold-wire-bond")["compatible"])

    def test_conductive_adhesive_accepts_a_silver_termination(self):
        self.assertTrue(assess_termination("silver", "conductive-adhesive")["compatible"])

    def test_unknown_termination_rejected(self):
        with self.assertRaises(ValueError):
            assess_termination("unobtainium", "solder")

    def test_unknown_attach_method_rejected(self):
        with self.assertRaises(ValueError):
            assess_termination("gold", "glue-gun")


class LotStructureTests(unittest.TestCase):
    def test_single_lot_delivery_is_clean(self):
        result = assess_lot_structure(["LOT-1"], 250)
        self.assertTrue(result["single_lot"])
        self.assertIsNone(result["finding"])

    def test_repeated_identifier_counts_once(self):
        result = assess_lot_structure(["LOT-1", "lot-1", " LOT-1 "], 250)
        self.assertEqual(result["lot_count"], 1)

    def test_split_delivery_is_flagged(self):
        result = assess_lot_structure(["LOT-1", "LOT-2"], 250)
        self.assertFalse(result["single_lot"])
        self.assertEqual(result["lot_count"], 2)

    def test_unidentified_delivery_is_flagged(self):
        result = assess_lot_structure([], 250)
        self.assertEqual(result["lot_count"], 0)
        self.assertIn("traceable", result["finding"])

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_structure(["LOT-1"], 0)

    def test_non_integer_quantity_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_structure(["LOT-1"], 12.5)


class OrderLineTests(unittest.TestCase):
    def test_complete_line_releases(self):
        result = assess_order_line(resistor_line())
        self.assertEqual(result["disposition"], "release")
        self.assertEqual(result["findings"], ())

    def test_missing_data_item_holds_the_line(self):
        declared = [item for item in FULL_RESISTOR_ITEMS if item != "quality-level"]
        result = assess_order_line(resistor_line(declared_items=declared))
        self.assertEqual(result["disposition"], "hold")
        self.assertIn("quality-level", result["governing_finding"])

    def test_split_lot_rejects_the_line(self):
        result = assess_order_line(resistor_line(lot_identifiers=["A", "B"]))
        self.assertEqual(result["disposition"], "reject")

    def test_termination_conflict_rejects_the_line(self):
        result = assess_order_line(resistor_line(attach_method="solder"))
        self.assertEqual(result["disposition"], "reject")

    def test_overstress_alone_holds_rather_than_rejects(self):
        result = assess_order_line(resistor_line(applied=0.20, rated=0.25))
        self.assertEqual(result["disposition"], "hold")

    def test_capacitor_line_owes_the_capacitor_items(self):
        line = resistor_line(
            element_type="chip-capacitor",
            declared_items=list(BASELINE_DATA_ITEMS),
            applied=20.0,
            rated=50.0,
        )
        result = assess_order_line(line)
        self.assertIn("dielectric-category", result["governing_finding"])

    def test_missing_key_rejected(self):
        line = resistor_line()
        del line["termination"]
        with self.assertRaises(ValueError):
            assess_order_line(line)

    def test_non_mapping_line_rejected(self):
        with self.assertRaises(ValueError):
            assess_order_line(["chip-resistor"])


class SummaryTests(unittest.TestCase):
    def test_all_clean_order_is_releasable(self):
        summary = summarize_order([resistor_line(), resistor_line(quantity=10)])
        self.assertTrue(summary["releasable"])
        self.assertEqual(summary["counts"]["release"], 2)

    def test_worst_line_governs_the_order(self):
        summary = summarize_order(
            [resistor_line(), resistor_line(lot_identifiers=["A", "B"])]
        )
        self.assertEqual(summary["disposition"], "reject")
        self.assertFalse(summary["releasable"])

    def test_governing_finding_comes_from_the_worst_line(self):
        summary = summarize_order(
            [resistor_line(applied=0.20, rated=0.25), resistor_line(attach_method="solder")]
        )
        self.assertIn("embrittle", summary["governing_finding"])

    def test_counts_cover_every_line(self):
        summary = summarize_order(
            [resistor_line(), resistor_line(applied=0.20, rated=0.25)]
        )
        self.assertEqual(sum(summary["counts"].values()), 2)

    def test_empty_order_rejected(self):
        with self.assertRaises(ValueError):
            summarize_order([])


if __name__ == "__main__":
    unittest.main()
