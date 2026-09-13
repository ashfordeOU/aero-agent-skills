#!/usr/bin/env python3
"""Gate 3 contract test for e2006-internal-grounding-inspection.

Stdlib unittest, offline, deterministic. Run:
    python3 test_e2006_internal_grounding_inspection.py
"""

import math
import unittest

from e2006_internal_grounding_inspection_logic import (
    FAMILY_BOND_LIMIT_OHM,
    GROUNDED,
    INAPPLICABLE,
    INCONCLUSIVE,
    INSPECTION_METHODS,
    UNGROUNDED,
    applicable_methods,
    assess_inspection_campaign,
    build_inventory,
    categorize_inspection_item,
    evaluate_record,
    family_bond_limit,
    inspection_coverage,
    match_records,
    resistance_within_limit,
    summarize_campaign,
    validate_inspection_record,
    validate_inventory_item,
)


def inv(item_id, kind="internal-bracket", source="structure-build-record"):
    return {"id": item_id, "kind": kind, "source": source}


def rec(item_id, method="bond-resistance-measurement", ohm=0.005, inspector="qa-14"):
    record = {"item_id": item_id, "method": method, "inspector": inspector}
    if INSPECTION_METHODS[method]["measures"]:
        record["measured_ohm"] = ohm
    return record


class TestCategorizeInspectionItem(unittest.TestCase):
    def test_shield_family(self):
        self.assertEqual(categorize_inspection_item("harness-shield"), "shield")

    def test_enclosure_family(self):
        self.assertEqual(categorize_inspection_item("screened-module-housing"), "enclosure")

    def test_structure_family_normalizes_case(self):
        self.assertEqual(categorize_inspection_item(" Equipment-Baseplate "), "structure")

    def test_uncategorized_kind_raises(self):
        with self.assertRaises(ValueError):
            categorize_inspection_item("thermal-blanket")

    def test_non_string_kind_raises(self):
        with self.assertRaises(ValueError):
            categorize_inspection_item(None)


class TestApplicableMethods(unittest.TestCase):
    def test_shield_accepts_the_continuity_check(self):
        self.assertIn("shield-continuity-check", applicable_methods("shield"))

    def test_structure_rejects_the_continuity_check(self):
        self.assertNotIn("shield-continuity-check", applicable_methods("structure"))

    def test_enclosure_rejects_the_continuity_check(self):
        self.assertNotIn("shield-continuity-check", applicable_methods("enclosure"))

    def test_every_family_accepts_a_resistance_measurement(self):
        for family in FAMILY_BOND_LIMIT_OHM:
            self.assertIn("bond-resistance-measurement", applicable_methods(family))

    def test_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            applicable_methods("plumbing")

    def test_non_string_family_raises(self):
        with self.assertRaises(ValueError):
            applicable_methods(7)


class TestFamilyBondLimit(unittest.TestCase):
    def test_shield_limit_matches_the_table(self):
        self.assertAlmostEqual(family_bond_limit("shield"), FAMILY_BOND_LIMIT_OHM["shield"])

    def test_structure_limit_is_looser_than_shield(self):
        self.assertGreater(family_bond_limit("structure"), family_bond_limit("shield"))

    def test_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            family_bond_limit("avionics")

    def test_non_string_family_raises(self):
        with self.assertRaises(ValueError):
            family_bond_limit(None)


class TestValidateInventoryItem(unittest.TestCase):
    def test_normalizes_id_and_family(self):
        norm = validate_inventory_item(inv(" b1 ", kind="Internal-Bracket"))
        self.assertEqual(norm["id"], "b1")
        self.assertEqual(norm["family"], "structure")
        self.assertEqual(norm["kind"], "internal-bracket")

    def test_harness_source_accepted(self):
        norm = validate_inventory_item(
            inv("s1", kind="harness-shield", source="harness-build-record")
        )
        self.assertEqual(norm["source"], "harness-build-record")

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_inventory_item(["b1"])

    def test_blank_id_raises(self):
        with self.assertRaises(ValueError):
            validate_inventory_item(inv("   "))

    def test_uncategorized_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_inventory_item(inv("b1", kind="thermal-blanket"))

    def test_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            validate_inventory_item(inv("b1", source="inspection-sheet"))

    def test_missing_source_raises(self):
        item = inv("b1")
        del item["source"]
        with self.assertRaises(ValueError):
            validate_inventory_item(item)


class TestBuildInventory(unittest.TestCase):
    def test_builds_a_keyed_inventory(self):
        inventory = build_inventory([inv("b1"), inv("s1", kind="harness-shield", source="harness-build-record")])
        self.assertEqual(sorted(inventory), ["b1", "s1"])

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            build_inventory(inv("b1"))

    def test_empty_inventory_raises(self):
        with self.assertRaises(ValueError):
            build_inventory([])

    def test_duplicate_item_id_raises(self):
        with self.assertRaises(ValueError):
            build_inventory([inv("b1"), inv("b1")])


class TestValidateInspectionRecord(unittest.TestCase):
    def test_visual_record_needs_no_measurement(self):
        norm = validate_inspection_record(rec("b1", method="visual-bond-inspection"))
        self.assertIsNone(norm["measured_ohm"])

    def test_measuring_record_keeps_the_value(self):
        norm = validate_inspection_record(rec("b1", ohm=0.004))
        self.assertAlmostEqual(norm["measured_ohm"], 0.004)

    def test_method_and_id_are_normalized(self):
        norm = validate_inspection_record(
            {
                "item_id": " b1 ",
                "method": "Bond-Resistance-Measurement",
                "inspector": " qa-14 ",
                "measured_ohm": 0.004,
            }
        )
        self.assertEqual(norm["item_id"], "b1")
        self.assertEqual(norm["method"], "bond-resistance-measurement")
        self.assertEqual(norm["inspector"], "qa-14")

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_inspection_record("b1")

    def test_blank_item_id_raises(self):
        with self.assertRaises(ValueError):
            validate_inspection_record(rec("  "))

    def test_unrecognized_method_raises(self):
        with self.assertRaises(ValueError):
            validate_inspection_record(
                {"item_id": "b1", "method": "eyeball-it", "inspector": "qa-14"}
            )

    def test_missing_inspector_raises(self):
        record = rec("b1")
        del record["inspector"]
        with self.assertRaises(ValueError):
            validate_inspection_record(record)

    def test_measuring_method_without_a_value_raises(self):
        record = rec("b1")
        del record["measured_ohm"]
        with self.assertRaises(ValueError):
            validate_inspection_record(record)

    def test_boolean_measurement_raises(self):
        record = rec("b1")
        record["measured_ohm"] = True
        with self.assertRaises(ValueError):
            validate_inspection_record(record)

    def test_negative_measurement_raises(self):
        with self.assertRaises(ValueError):
            validate_inspection_record(rec("b1", ohm=-0.001))

    def test_non_finite_measurement_raises(self):
        with self.assertRaises(ValueError):
            validate_inspection_record(rec("b1", ohm=float("inf")))


class TestResistanceWithinLimit(unittest.TestCase):
    def test_comfortably_below_limit(self):
        self.assertTrue(resistance_within_limit(0.004, 0.010))

    def test_exactly_on_limit(self):
        self.assertTrue(resistance_within_limit(0.010, 0.010))

    def test_summed_reading_a_few_ulps_over_limit_is_still_compliant(self):
        total = 0.0008 + 0.0041 + 0.0051
        self.assertGreater(total, 0.010)
        self.assertTrue(resistance_within_limit(total, 0.010))

    def test_genuine_exceedance_is_rejected(self):
        self.assertFalse(resistance_within_limit(0.02, 0.010))


class TestEvaluateRecord(unittest.TestCase):
    def setUp(self):
        self.bracket = validate_inventory_item(inv("b1"))
        self.shield = validate_inventory_item(
            inv("s1", kind="harness-shield", source="harness-build-record")
        )
        self.housing = validate_inventory_item(inv("e1", kind="screened-module-housing"))

    def test_measurement_below_limit_is_grounded(self):
        result = evaluate_record(validate_inspection_record(rec("b1", ohm=0.004)), self.bracket)
        self.assertEqual(result["status"], GROUNDED)

    def test_measurement_above_limit_is_ungrounded(self):
        result = evaluate_record(validate_inspection_record(rec("b1", ohm=0.4)), self.bracket)
        self.assertEqual(result["status"], UNGROUNDED)
        self.assertIn("above", result["reason"])

    def test_boundary_measurement_is_grounded(self):
        total = 0.0008 + 0.0041 + 0.0051
        result = evaluate_record(
            validate_inspection_record(rec("s1", ohm=total)), self.shield
        )
        self.assertEqual(result["status"], GROUNDED)

    def test_visual_check_settles_a_structure_item(self):
        result = evaluate_record(
            validate_inspection_record(rec("b1", method="visual-bond-inspection")),
            self.bracket,
        )
        self.assertEqual(result["status"], GROUNDED)

    def test_visual_check_on_a_shield_is_inconclusive(self):
        result = evaluate_record(
            validate_inspection_record(rec("s1", method="visual-bond-inspection")),
            self.shield,
        )
        self.assertEqual(result["status"], INCONCLUSIVE)

    def test_visual_check_on_a_housing_is_inconclusive(self):
        result = evaluate_record(
            validate_inspection_record(rec("e1", method="visual-bond-inspection")),
            self.housing,
        )
        self.assertEqual(result["status"], INCONCLUSIVE)

    def test_continuity_check_settles_a_shield(self):
        result = evaluate_record(
            validate_inspection_record(rec("s1", method="shield-continuity-check", ohm=0.003)),
            self.shield,
        )
        self.assertEqual(result["status"], GROUNDED)

    def test_continuity_check_on_a_bracket_is_inapplicable(self):
        result = evaluate_record(
            validate_inspection_record(rec("b1", method="shield-continuity-check", ohm=0.003)),
            self.bracket,
        )
        self.assertEqual(result["status"], INAPPLICABLE)

    def test_limit_override_tightens_the_verdict(self):
        record = validate_inspection_record(rec("b1", ohm=0.020))
        self.assertEqual(evaluate_record(record, self.bracket)["status"], GROUNDED)
        tightened = evaluate_record(record, self.bracket, limits={"structure": 0.005})
        self.assertEqual(tightened["status"], UNGROUNDED)

    def test_non_positive_limit_override_raises(self):
        with self.assertRaises(ValueError):
            evaluate_record(
                validate_inspection_record(rec("b1")), self.bracket, limits={"structure": 0.0}
            )

    def test_non_mapping_limit_override_raises(self):
        with self.assertRaises(ValueError):
            evaluate_record(
                validate_inspection_record(rec("b1")), self.bracket, limits=[("structure", 0.01)]
            )

    def test_record_for_another_item_raises(self):
        with self.assertRaises(ValueError):
            evaluate_record(validate_inspection_record(rec("b9")), self.bracket)

    def test_unnormalized_record_raises(self):
        with self.assertRaises(ValueError):
            evaluate_record({"item_id": "b1"}, self.bracket)

    def test_unnormalized_item_raises(self):
        with self.assertRaises(ValueError):
            evaluate_record(validate_inspection_record(rec("b1")), {"id": "b1"})


class TestMatchRecords(unittest.TestCase):
    def setUp(self):
        self.inventory = build_inventory([inv("b1"), inv("b2")])

    def test_all_items_matched(self):
        matched, gaps, orphans = match_records(self.inventory, [rec("b1"), rec("b2")])
        self.assertEqual(len(matched), 2)
        self.assertEqual(gaps, [])
        self.assertEqual(orphans, [])

    def test_uninspected_item_is_a_gap(self):
        matched, gaps, orphans = match_records(self.inventory, [rec("b1")])
        self.assertEqual(gaps, ["b2"])
        self.assertEqual(orphans, [])

    def test_record_for_absent_hardware_is_an_orphan(self):
        matched, gaps, orphans = match_records(
            self.inventory, [rec("b1"), rec("b2"), rec("b9")]
        )
        self.assertEqual(orphans, ["b9"])
        self.assertEqual(gaps, [])

    def test_non_list_records_raises(self):
        with self.assertRaises(ValueError):
            match_records(self.inventory, rec("b1"))

    def test_non_mapping_inventory_raises(self):
        with self.assertRaises(ValueError):
            match_records([inv("b1")], [rec("b1")])


class TestInspectionCoverage(unittest.TestCase):
    def test_full_coverage(self):
        inventory = build_inventory([inv("b1"), inv("b2")])
        self.assertAlmostEqual(inspection_coverage(inventory, []), 1.0)

    def test_partial_coverage(self):
        inventory = build_inventory([inv("b1"), inv("b2")])
        self.assertAlmostEqual(inspection_coverage(inventory, ["b2"]), 0.5)

    def test_empty_inventory_raises(self):
        with self.assertRaises(ValueError):
            inspection_coverage({}, [])


class TestAssessInspectionCampaign(unittest.TestCase):
    def test_fully_inspected_campaign_closes(self):
        report = assess_inspection_campaign(
            [inv("b1"), inv("s1", kind="harness-shield", source="harness-build-record")],
            [rec("b1", ohm=0.010), rec("s1", method="shield-continuity-check", ohm=0.003)],
        )
        self.assertTrue(report["closed"])
        self.assertAlmostEqual(report["coverage_ratio"], 1.0)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["grounded_items"], ["b1", "s1"])

    def test_uninspected_item_opens_the_campaign(self):
        report = assess_inspection_campaign([inv("b1"), inv("b2")], [rec("b1")])
        self.assertFalse(report["closed"])
        self.assertEqual(report["coverage_gaps"], ["b2"])
        self.assertAlmostEqual(report["coverage_ratio"], 0.5)

    def test_over_limit_measurement_is_an_ungrounded_finding(self):
        report = assess_inspection_campaign([inv("b1")], [rec("b1", ohm=0.9)])
        self.assertFalse(report["closed"])
        self.assertEqual(report["ungrounded_items"], ["b1"])

    def test_visual_only_shield_is_inconclusive_despite_full_coverage(self):
        report = assess_inspection_campaign(
            [inv("s1", kind="harness-shield", source="harness-build-record")],
            [rec("s1", method="visual-bond-inspection")],
        )
        self.assertAlmostEqual(report["coverage_ratio"], 1.0)
        self.assertFalse(report["closed"])
        self.assertEqual(report["inconclusive_items"], ["s1"])

    def test_backup_measurement_settles_an_inconclusive_item(self):
        report = assess_inspection_campaign(
            [inv("s1", kind="harness-shield", source="harness-build-record")],
            [
                rec("s1", method="visual-bond-inspection"),
                rec("s1", method="shield-continuity-check", ohm=0.002),
            ],
        )
        self.assertTrue(report["closed"])
        self.assertEqual(report["inconclusive_items"], [])
        self.assertEqual(report["grounded_items"], ["s1"])

    def test_one_over_limit_reading_outweighs_a_good_one(self):
        report = assess_inspection_campaign(
            [inv("b1")],
            [rec("b1", ohm=0.004), rec("b1", method="visual-bond-inspection")],
        )
        self.assertTrue(report["closed"])
        worse = assess_inspection_campaign(
            [inv("b1")], [rec("b1", ohm=0.004), rec("b1", ohm=0.9)]
        )
        self.assertFalse(worse["closed"])
        self.assertEqual(worse["ungrounded_items"], ["b1"])
        self.assertEqual(worse["grounded_items"], [])

    def test_inapplicable_method_leaves_the_item_unsettled(self):
        report = assess_inspection_campaign(
            [inv("b1")], [rec("b1", method="shield-continuity-check", ohm=0.002)]
        )
        self.assertFalse(report["closed"])
        self.assertEqual(report["inapplicable_items"], ["b1"])
        self.assertAlmostEqual(report["coverage_ratio"], 1.0)

    def test_orphan_record_is_a_finding(self):
        report = assess_inspection_campaign([inv("b1")], [rec("b1"), rec("b9")])
        self.assertFalse(report["closed"])
        self.assertEqual(report["orphan_records"], ["b9"])
        self.assertEqual(report["record_count"], 2)

    def test_limits_override_flows_into_the_campaign(self):
        report = assess_inspection_campaign(
            [inv("b1")], [rec("b1", ohm=0.020)], limits={"structure": 0.005}
        )
        self.assertFalse(report["closed"])
        self.assertEqual(report["ungrounded_items"], ["b1"])

    def test_boundary_reading_closes_the_campaign(self):
        total = 0.0008 + 0.0041 + 0.0051
        report = assess_inspection_campaign(
            [inv("s1", kind="harness-shield", source="harness-build-record")],
            [rec("s1", ohm=total)],
        )
        self.assertTrue(report["closed"])

    def test_empty_inventory_raises(self):
        with self.assertRaises(ValueError):
            assess_inspection_campaign([], [rec("b1")])

    def test_bad_record_raises(self):
        with self.assertRaises(ValueError):
            assess_inspection_campaign(
                [inv("b1")], [{"item_id": "b1", "method": "guess", "inspector": "qa-14"}]
            )


class TestSummarizeCampaign(unittest.TestCase):
    def test_closed_summary_text(self):
        report = assess_inspection_campaign([inv("b1")], [rec("b1", ohm=0.004)])
        text = summarize_campaign(report)
        self.assertIn("CLOSED", text)
        self.assertIn("coverage 1.000", text)

    def test_open_summary_text(self):
        report = assess_inspection_campaign([inv("b1"), inv("b2")], [rec("b1")])
        self.assertIn("OPEN", summarize_campaign(report))

    def test_summary_of_non_report_raises(self):
        with self.assertRaises(ValueError):
            summarize_campaign({"closed": True})


class TestDeterminismAndTables(unittest.TestCase):
    def test_repeated_campaign_is_identical(self):
        items = [inv("b1"), inv("b2")]
        records = [rec("b1", ohm=0.004), rec("b2", method="visual-bond-inspection")]
        self.assertEqual(
            assess_inspection_campaign(items, records),
            assess_inspection_campaign(items, records),
        )

    def test_bond_limit_table_is_finite_and_positive(self):
        for family, limit in FAMILY_BOND_LIMIT_OHM.items():
            self.assertTrue(math.isfinite(limit), family)
            self.assertGreater(limit, 0.0, family)

    def test_every_method_is_applicable_to_at_least_one_family(self):
        covered = set()
        for family in FAMILY_BOND_LIMIT_OHM:
            covered |= set(applicable_methods(family))
        self.assertEqual(covered, set(INSPECTION_METHODS))


if __name__ == "__main__":
    unittest.main()
