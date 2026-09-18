"""Contract test for the stock-rotation leaf (stdlib unittest)."""

import unittest

from q7022_stock_rotation_logic import (
    assess_stock_rotation,
    evaluate_pick,
    issue_sequence,
    next_issue,
    policy_conflicts,
    separation_findings,
    sort_key,
    validate_lot,
    validate_stock,
)


def lot(lid="L-1", material="sealant-a", lot_number="LN-1", received="2026-01-10",
        expiry="2027-01-10", bin_name="BIN-1", **kw):
    record = {
        "id": lid,
        "material": material,
        "lot_number": lot_number,
        "received": received,
        "expiry": expiry,
        "bin": bin_name,
    }
    record.update(kw)
    return record


def three_lots():
    return [
        lot("L-3", received="2026-03-01", expiry="2027-03-01", lot_number="LN-3",
            bin_name="BIN-3"),
        lot("L-1", received="2026-01-10", expiry="2027-01-10", lot_number="LN-1",
            bin_name="BIN-1"),
        lot("L-2", received="2026-02-05", expiry="2027-02-05", lot_number="LN-2",
            bin_name="BIN-2"),
    ]


class TestValidateLot(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_lot(lot())
        self.assertEqual(norm["availability"], "available")
        self.assertEqual(norm["quantity"], 1)
        self.assertFalse(norm["divided"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_lot(["L-1"])

    def test_missing_material_raises(self):
        broken = lot()
        del broken["material"]
        with self.assertRaises(ValueError):
            validate_lot(broken)

    def test_malformed_date_raises(self):
        with self.assertRaises(ValueError):
            validate_lot(lot(received="10/01/2026"))

    def test_expiry_before_receipt_raises(self):
        with self.assertRaises(ValueError):
            validate_lot(lot(received="2026-05-01", expiry="2026-04-01"))

    def test_unknown_availability_raises(self):
        with self.assertRaises(ValueError):
            validate_lot(lot(availability="maybe"))

    def test_boolean_quantity_raises(self):
        with self.assertRaises(ValueError):
            validate_lot(lot(quantity=True))

    def test_negative_quantity_raises(self):
        with self.assertRaises(ValueError):
            validate_lot(lot(quantity=-2))

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            validate_stock([lot("L-1"), lot("L-1", lot_number="LN-9")])

    def test_empty_stock_raises(self):
        with self.assertRaises(ValueError):
            validate_stock([])


class TestOrdering(unittest.TestCase):
    def test_fifo_orders_by_receipt(self):
        self.assertEqual(issue_sequence(three_lots()), ["L-1", "L-2", "L-3"])

    def test_fefo_orders_by_expiry(self):
        stock = three_lots()
        stock[0]["expiry"] = "2026-06-01"
        self.assertEqual(issue_sequence(stock, policy="fefo")[0], "L-3")

    def test_unknown_policy_raises(self):
        with self.assertRaises(ValueError):
            sort_key(lot(), policy="lifo")

    def test_same_receipt_date_breaks_on_expiry_then_lot_number(self):
        stock = [
            lot("L-B", received="2026-01-10", expiry="2027-02-10", lot_number="LN-B"),
            lot("L-A", received="2026-01-10", expiry="2027-01-10", lot_number="LN-A"),
        ]
        self.assertEqual(issue_sequence(stock), ["L-A", "L-B"])

    def test_quarantined_stock_is_not_issuable(self):
        stock = three_lots()
        stock[1]["availability"] = "quarantined"
        self.assertEqual(issue_sequence(stock), ["L-2", "L-3"])

    def test_zero_quantity_stock_is_not_issuable(self):
        stock = three_lots()
        stock[1]["quantity"] = 0
        self.assertNotIn("L-1", issue_sequence(stock))

    def test_material_filter_narrows_the_queue(self):
        stock = three_lots() + [lot("L-9", material="adhesive-b", bin_name="BIN-9")]
        self.assertEqual(next_issue(stock, "adhesive-b"), "L-9")

    def test_next_issue_is_none_when_nothing_is_issuable(self):
        stock = three_lots()
        for item in stock:
            item["availability"] = "issued"
        self.assertIsNone(next_issue(stock, "sealant-a"))


class TestPolicyConflicts(unittest.TestCase):
    def test_aligned_orders_report_no_conflict(self):
        self.assertEqual(policy_conflicts(three_lots()), [])

    def test_late_receipt_with_early_expiry_is_a_conflict(self):
        stock = three_lots()
        stock[0]["expiry"] = "2026-06-01"
        conflicts = policy_conflicts(stock)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["fifo_head"], "L-1")
        self.assertEqual(conflicts[0]["fefo_head"], "L-3")


class TestSeparation(unittest.TestCase):
    def test_one_lot_per_bin_is_clean(self):
        self.assertEqual(separation_findings(three_lots()), [])

    def test_two_materials_in_one_bin_is_a_finding(self):
        stock = [lot("L-1", bin_name="BIN-X"),
                 lot("L-2", material="adhesive-b", lot_number="LN-2", bin_name="BIN-X")]
        kinds = [f["kind"] for f in separation_findings(stock)]
        self.assertIn("mixed-material-bin", kinds)

    def test_two_lot_numbers_of_one_material_need_a_divider(self):
        stock = [lot("L-1", lot_number="LN-1", bin_name="BIN-X"),
                 lot("L-2", lot_number="LN-2", bin_name="BIN-X")]
        kinds = [f["kind"] for f in separation_findings(stock)]
        self.assertEqual(kinds, ["commingled-lots"])

    def test_a_declared_divider_clears_the_commingling_finding(self):
        stock = [lot("L-1", lot_number="LN-1", bin_name="BIN-X", divided=True),
                 lot("L-2", lot_number="LN-2", bin_name="BIN-X", divided=True)]
        self.assertEqual(separation_findings(stock), [])

    def test_quarantined_stock_beside_issuable_stock_is_a_finding(self):
        stock = [lot("L-1", lot_number="LN-1", bin_name="BIN-X"),
                 lot("L-2", lot_number="LN-1", bin_name="BIN-X", availability="quarantined")]
        kinds = [f["kind"] for f in separation_findings(stock)]
        self.assertIn("quarantine-not-segregated", kinds)


class TestEvaluatePick(unittest.TestCase):
    def test_the_head_of_the_queue_is_in_rotation(self):
        report = evaluate_pick(three_lots(), "L-1")
        self.assertTrue(report["compliant"])
        self.assertEqual(report["passed_over"], [])

    def test_a_later_lot_names_every_lot_passed_over(self):
        report = evaluate_pick(three_lots(), "L-3")
        self.assertFalse(report["compliant"])
        self.assertEqual(report["passed_over"], ["L-1", "L-2"])

    def test_picking_quarantined_stock_is_not_compliant(self):
        stock = three_lots()
        stock[1]["availability"] = "quarantined"
        report = evaluate_pick(stock, "L-1")
        self.assertFalse(report["compliant"])

    def test_unknown_pick_raises(self):
        with self.assertRaises(ValueError):
            evaluate_pick(three_lots(), "L-99")

    def test_empty_pick_id_raises(self):
        with self.assertRaises(ValueError):
            evaluate_pick(three_lots(), "")


class TestAssessStockRotation(unittest.TestCase):
    def test_clean_holding_with_a_correct_pick_is_compliant(self):
        report = assess_stock_rotation(three_lots(), ["L-1"])
        self.assertEqual(report["disposition"], "stock-control-compliant")
        self.assertTrue(report["compliant"])
        self.assertAlmostEqual(report["rotation_compliance_rate"], 1.0, places=9)

    def test_an_out_of_rotation_pick_fails_the_holding(self):
        report = assess_stock_rotation(three_lots(), ["L-1", "L-3"])
        self.assertEqual(report["out_of_rotation_ids"], ["L-3"])
        self.assertAlmostEqual(report["rotation_compliance_rate"], 0.5, places=9)
        self.assertFalse(report["compliant"])

    def test_a_separation_finding_alone_fails_the_holding(self):
        stock = [lot("L-1", lot_number="LN-1", bin_name="BIN-X"),
                 lot("L-2", lot_number="LN-2", bin_name="BIN-X")]
        report = assess_stock_rotation(stock)
        self.assertEqual(report["disposition"], "stock-control-non-compliant")

    def test_a_rotation_conflict_is_reported_without_failing_the_holding(self):
        stock = three_lots()
        stock[0]["expiry"] = "2026-06-01"
        report = assess_stock_rotation(stock)
        self.assertEqual(report["disposition"], "compliant-with-rotation-conflict")
        self.assertEqual(len(report["policy_conflicts"]), 1)

    def test_no_picks_gives_a_full_rate(self):
        report = assess_stock_rotation(three_lots())
        self.assertAlmostEqual(report["rotation_compliance_rate"], 1.0, places=9)

    def test_non_sequence_picks_raises(self):
        with self.assertRaises(ValueError):
            assess_stock_rotation(three_lots(), "L-1")

    def test_unknown_policy_raises(self):
        with self.assertRaises(ValueError):
            assess_stock_rotation(three_lots(), [], policy="random")


if __name__ == "__main__":
    unittest.main()
