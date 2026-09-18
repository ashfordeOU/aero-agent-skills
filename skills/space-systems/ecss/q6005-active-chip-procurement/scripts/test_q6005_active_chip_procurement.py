"""Contract test for the active-chip-procurement leaf (stdlib unittest)."""

import unittest

from q6005_active_chip_procurement_logic import (
    BLOCKED,
    DESTRUCTIVE_SAMPLE_PER_WAFER_LOT,
    QUANTITY_EPSILON,
    READY,
    ROUTE_DEDICATED_QUALIFIED_LINE,
    ROUTE_QUALIFIED_PACKAGED_LINE,
    ROUTE_UNQUALIFIED_COMMERCIAL_LINE,
    UNIVERSAL_EVIDENCE,
    assess_die_order,
    assess_procurement_package,
    check_storage,
    check_traceability,
    deepest_covered_route,
    destructive_sample_size,
    die_bank_age_limit_months,
    missing_evidence,
    order_quantity,
    required_evidence_for_route,
    route_evidence_burden,
    surplus_evidence,
    traceability_depth,
    traceability_reaches_wafer_lot,
    validate_die_order,
)


def order(order_id="D-1", route=ROUTE_DEDICATED_QUALIFIED_LINE, **kw):
    record = {
        "id": order_id,
        "technology": "silicon-cmos",
        "route": route,
        "storage_condition": "dry-nitrogen-cabinet",
        "traceability_level": "wafer-lot",
        "evidence_on_file": list(required_evidence_for_route(route)),
        "die_bank_age_months": 6,
        "wafer_lots": 1,
        "required_good_dice": 100,
        "assembly_yield": 1.0,
    }
    record.update(kw)
    return record


class TestRouteEvidence(unittest.TestCase):
    def test_every_route_owes_the_universal_set(self):
        for route in (
            ROUTE_QUALIFIED_PACKAGED_LINE,
            ROUTE_DEDICATED_QUALIFIED_LINE,
            ROUTE_UNQUALIFIED_COMMERCIAL_LINE,
        ):
            owed = set(required_evidence_for_route(route))
            self.assertTrue(set(UNIVERSAL_EVIDENCE) <= owed)

    def test_unqualified_line_owes_the_most(self):
        self.assertGreater(
            route_evidence_burden(ROUTE_UNQUALIFIED_COMMERCIAL_LINE),
            route_evidence_burden(ROUTE_QUALIFIED_PACKAGED_LINE),
        )

    def test_qualified_packaged_line_cites_its_qualification(self):
        owed = required_evidence_for_route(ROUTE_QUALIFIED_PACKAGED_LINE)
        self.assertIn("packaged-part-qualification-reference", owed)

    def test_evidence_set_is_sorted_and_deduplicated(self):
        owed = required_evidence_for_route(ROUTE_UNQUALIFIED_COMMERCIAL_LINE)
        self.assertEqual(list(owed), sorted(set(owed)))

    def test_unknown_route_raises(self):
        with self.assertRaises(ValueError):
            required_evidence_for_route("die-from-a-drawer")


class TestStorageLimits(unittest.TestCase):
    def test_nitrogen_defends_the_longest_bank(self):
        self.assertGreater(
            die_bank_age_limit_months("dry-nitrogen-cabinet"),
            die_bank_age_limit_months("controlled-cleanroom-ambient"),
        )

    def test_unknown_storage_condition_raises(self):
        with self.assertRaises(ValueError):
            die_bank_age_limit_months("shoebox")

    def test_age_inside_the_limit_has_no_finding(self):
        self.assertEqual(check_storage(order()), [])

    def test_age_beyond_the_limit_is_a_finding(self):
        findings = check_storage(
            order(
                "D-1",
                storage_condition="controlled-cleanroom-ambient",
                die_bank_age_months=18,
            )
        )
        self.assertIn("die-bank-age-beyond-the-storage-atmosphere-limit", findings)

    def test_age_exactly_on_the_limit_is_accepted(self):
        limit = die_bank_age_limit_months("sealed-dry-pack-with-desiccant")
        findings = check_storage(
            order(
                "D-1",
                storage_condition="sealed-dry-pack-with-desiccant",
                die_bank_age_months=limit,
            )
        )
        self.assertEqual(findings, [])


class TestTraceability(unittest.TestCase):
    def test_deeper_levels_score_higher(self):
        self.assertGreater(
            traceability_depth("diffusion-lot"), traceability_depth("delivery-lot")
        )

    def test_wafer_lot_is_deep_enough(self):
        self.assertTrue(traceability_reaches_wafer_lot("wafer-lot"))
        self.assertTrue(traceability_reaches_wafer_lot("diffusion-lot"))

    def test_delivery_lot_is_not_deep_enough(self):
        self.assertFalse(traceability_reaches_wafer_lot("delivery-lot"))
        self.assertFalse(traceability_reaches_wafer_lot("assembly-die-lot"))

    def test_shallow_chain_is_a_finding(self):
        findings = check_traceability(order("D-1", traceability_level="delivery-lot"))
        self.assertIn("traceability-chain-stops-short-of-the-wafer-lot", findings)

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            traceability_depth("vibes")


class TestOrderQuantity(unittest.TestCase):
    def test_perfect_yield_buys_the_good_count_plus_the_sample(self):
        self.assertEqual(order_quantity(95, 1.0, 5), 100)

    def test_yield_loss_is_bought_up_front(self):
        self.assertEqual(order_quantity(100, 0.8, 5), 130)

    def test_a_partial_die_rounds_up(self):
        self.assertEqual(order_quantity(100, 0.75, 5), 139)

    def test_exact_division_does_not_buy_a_spare_die(self):
        self.assertEqual(order_quantity(50, 0.5, 0), 100)

    def test_epsilon_is_far_below_one_die(self):
        self.assertAlmostEqual(QUANTITY_EPSILON, 1.0e-9, places=15)

    def test_zero_yield_raises(self):
        with self.assertRaises(ValueError):
            order_quantity(100, 0.0, 5)

    def test_yield_above_one_raises(self):
        with self.assertRaises(ValueError):
            order_quantity(100, 1.2, 5)

    def test_non_numeric_yield_raises(self):
        with self.assertRaises(ValueError):
            order_quantity(100, "high", 5)

    def test_negative_sample_raises(self):
        with self.assertRaises(ValueError):
            order_quantity(100, 0.9, -1)

    def test_sample_scales_with_the_wafer_lots_used(self):
        self.assertEqual(
            destructive_sample_size(3), 3 * DESTRUCTIVE_SAMPLE_PER_WAFER_LOT
        )

    def test_zero_wafer_lots_raises(self):
        with self.assertRaises(ValueError):
            destructive_sample_size(0)


class TestValidateDieOrder(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_die_order(
            {
                "id": "D-9",
                "technology": "silicon-bipolar",
                "route": ROUTE_DEDICATED_QUALIFIED_LINE,
                "storage_condition": "dry-nitrogen-cabinet",
            }
        )
        self.assertEqual(norm["traceability_level"], "delivery-lot")
        self.assertEqual(norm["wafer_lots"], 1)
        self.assertEqual(norm["evidence_on_file"], [])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_die_order(["D-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_die_order(order(""))

    def test_unknown_technology_raises(self):
        with self.assertRaises(ValueError):
            validate_die_order(order("D-1", technology="vacuum-tube"))

    def test_non_sequence_evidence_raises(self):
        with self.assertRaises(ValueError):
            validate_die_order(order("D-1", evidence_on_file="everything"))

    def test_non_string_evidence_item_raises(self):
        with self.assertRaises(ValueError):
            validate_die_order(order("D-1", evidence_on_file=[7]))

    def test_negative_die_bank_age_raises(self):
        with self.assertRaises(ValueError):
            validate_die_order(order("D-1", die_bank_age_months=-2))

    def test_zero_required_good_dice_raises(self):
        with self.assertRaises(ValueError):
            validate_die_order(order("D-1", required_good_dice=0))


class TestEvidenceGaps(unittest.TestCase):
    def test_complete_file_has_no_gap(self):
        self.assertEqual(missing_evidence(order()), [])

    def test_a_dropped_item_is_reported(self):
        held = list(required_evidence_for_route(ROUTE_DEDICATED_QUALIFIED_LINE))
        held.remove("die-visual-inspection-record")
        gaps = missing_evidence(order("D-1", evidence_on_file=held))
        self.assertEqual(gaps, ["die-visual-inspection-record"])

    def test_unqualified_route_reports_every_extra_item(self):
        gaps = missing_evidence(
            order(
                "D-1",
                route=ROUTE_UNQUALIFIED_COMMERCIAL_LINE,
                evidence_on_file=list(UNIVERSAL_EVIDENCE),
            )
        )
        self.assertIn("die-construction-analysis-report", gaps)
        self.assertIn("supplier-process-audit-report", gaps)

    def test_extra_evidence_is_surplus_not_a_gap(self):
        held = list(required_evidence_for_route(ROUTE_DEDICATED_QUALIFIED_LINE))
        held.append("die-shear-strength-report")
        record = order("D-1", evidence_on_file=held)
        self.assertEqual(missing_evidence(record), [])
        self.assertEqual(surplus_evidence(record), ["die-shear-strength-report"])

    def test_deepest_covered_route_prefers_the_most_demanding(self):
        held = list(required_evidence_for_route(ROUTE_UNQUALIFIED_COMMERCIAL_LINE))
        self.assertEqual(
            deepest_covered_route(held), ROUTE_UNQUALIFIED_COMMERCIAL_LINE
        )

    def test_no_route_is_covered_by_an_empty_file(self):
        self.assertIsNone(deepest_covered_route([]))

    def test_non_sequence_evidence_file_raises(self):
        with self.assertRaises(ValueError):
            deepest_covered_route("everything")


class TestAssessDieOrder(unittest.TestCase):
    def test_complete_order_is_ready(self):
        result = assess_die_order(order())
        self.assertEqual(result["status"], READY)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["order_quantity"], 105)

    def test_missing_evidence_blocks_the_order(self):
        result = assess_die_order(order("D-1", evidence_on_file=[]))
        self.assertEqual(result["status"], BLOCKED)
        self.assertIn(
            "evidence-missing:die-visual-inspection-record", result["findings"]
        )

    def test_shallow_traceability_blocks_an_otherwise_complete_order(self):
        result = assess_die_order(order("D-1", traceability_level="delivery-lot"))
        self.assertEqual(result["status"], BLOCKED)
        self.assertEqual(result["missing_evidence"], [])

    def test_report_carries_the_age_limit_it_graded_against(self):
        result = assess_die_order(order())
        self.assertEqual(result["die_bank_age_limit_months"], 60)


class TestPackage(unittest.TestCase):
    def test_package_of_ready_orders_is_ready(self):
        report = assess_procurement_package([order("D-1"), order("D-2")])
        self.assertTrue(report["package_ready"])
        self.assertEqual(report["blocked_ids"], [])
        self.assertEqual(report["total_dice_to_place"], 210)

    def test_one_blocked_order_blocks_the_package(self):
        report = assess_procurement_package(
            [order("D-1"), order("D-2", evidence_on_file=[])]
        )
        self.assertFalse(report["package_ready"])
        self.assertEqual(report["blocked_ids"], ["D-2"])
        self.assertEqual(report["ready_ids"], ["D-1"])

    def test_duplicate_order_id_raises(self):
        with self.assertRaises(ValueError):
            assess_procurement_package([order("D-1"), order("D-1")])

    def test_empty_package_raises(self):
        with self.assertRaises(ValueError):
            assess_procurement_package([])

    def test_non_list_package_raises(self):
        with self.assertRaises(ValueError):
            assess_procurement_package(order())


if __name__ == "__main__":
    unittest.main()
