"""Contract test for the ECSS-Q-ST-60-05C clause 7.3.4 recurrent-approval leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_approval_of_recurrent_circuits.py
"""

import unittest

from q6005_approval_of_recurrent_circuits_logic import (
    BASE_EVIDENCE,
    CHANGE_RANKS,
    CONTINUITY_WINDOW_MONTHS,
    DEFAULT_ALLOWABLE_DEFECTIVE_PERCENT,
    PERCENT_TOLERANCE,
    PROCESS_AREA_TEST_GROUPS,
    ROUTE_FULL,
    ROUTE_PARTIAL,
    ROUTE_REDUCED,
    assess_order_book,
    assess_recurrent_order,
    change_rank,
    continuity_gap_months,
    defective_percent,
    identity_findings,
    lot_acceptance_holds,
    months_between,
    normalize_order,
    parse_date,
    process_area_groups,
    reopened_test_groups,
    worst_change_rank,
)


def order(**overrides):
    """A clean repeat build: same article, same line, recent, clean lot."""
    base = {
        "order_id": "po-2026-0041",
        "previous_approval": {
            "part_number": "hyb-4412",
            "drawing_issue": "c",
            "manufacturer": "hybrid-house-alpha",
            "production_line": "line-2",
            "approved_lot_date": "2025-04-10",
            "lot_size": 40,
            "lot_defectives": 2,
        },
        "current_build": {
            "part_number": "hyb-4412",
            "drawing_issue": "c",
            "manufacturer": "hybrid-house-alpha",
            "production_line": "line-2",
            "order_date": "2026-02-10",
        },
        "open_alert": False,
        "changes": [{"kind": "no-change", "area": None}],
    }
    base.update(overrides)
    return base


def with_approval(**fields):
    """The standard order with its previous approval block perturbed."""
    raw = order()
    approval = dict(raw["previous_approval"])
    approval.update(fields)
    raw["previous_approval"] = approval
    return raw


def with_build(**fields):
    """The standard order with its current build block perturbed."""
    raw = order()
    build = dict(raw["current_build"])
    build.update(fields)
    raw["current_build"] = build
    return raw


class ChangeRankTests(unittest.TestCase):
    def test_no_change_is_the_lowest_rank(self):
        self.assertEqual(change_rank("no-change"), 0)

    def test_a_design_change_is_the_highest_rank(self):
        self.assertEqual(change_rank("design-change"), max(CHANGE_RANKS.values()))

    def test_a_process_change_outranks_a_paperwork_change(self):
        self.assertGreater(change_rank("process-change"), change_rank("documentation-only"))

    def test_unknown_change_kind_rejected(self):
        with self.assertRaises(ValueError):
            change_rank("tweak")


class ProcessAreaTests(unittest.TestCase):
    def test_every_known_area_re_opens_at_least_one_group(self):
        for area in PROCESS_AREA_TEST_GROUPS:
            self.assertGreaterEqual(len(process_area_groups(area)), 1)

    def test_a_wire_bonding_change_re_opens_bond_pull(self):
        self.assertIn("bond-pull-strength", process_area_groups("wire-bonding"))

    def test_unknown_process_area_rejected(self):
        with self.assertRaises(ValueError):
            process_area_groups("packing")


class DateTests(unittest.TestCase):
    def test_a_whole_year_is_twelve_months(self):
        self.assertEqual(months_between("2025-01-15", "2026-01-15"), 12)

    def test_a_part_month_does_not_count(self):
        self.assertEqual(months_between("2025-01-15", "2025-02-14"), 0)

    def test_the_same_day_next_month_counts(self):
        self.assertEqual(months_between("2025-01-15", "2025-02-15"), 1)

    def test_a_reversed_pair_rejected(self):
        with self.assertRaises(ValueError):
            months_between("2026-01-15", "2025-01-15")

    def test_a_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("10/04/2025", "approved_lot_date")

    def test_a_non_string_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date(20250410, "approved_lot_date")


class DefectivePercentTests(unittest.TestCase):
    def test_a_clean_lot_is_nought_percent(self):
        self.assertAlmostEqual(defective_percent(0, 40), 0.0, places=9)

    def test_a_fifth_of_the_lot_is_twenty_percent(self):
        self.assertAlmostEqual(defective_percent(8, 40), 20.0, places=9)

    def test_an_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            defective_percent(0, 0)

    def test_more_defectives_than_parts_rejected(self):
        with self.assertRaises(ValueError):
            defective_percent(5, 4)

    def test_a_fractional_count_rejected(self):
        with self.assertRaises(ValueError):
            defective_percent(2.5, 40)

    def test_a_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            defective_percent(-1, 40)


class LotAcceptanceTests(unittest.TestCase):
    def test_a_lot_under_the_allowable_holds(self):
        self.assertTrue(lot_acceptance_holds(2, 40, 10.0))

    def test_a_lot_exactly_on_the_allowable_holds(self):
        percent = defective_percent(4, 40)
        self.assertAlmostEqual(percent, 10.0, places=9)
        self.assertTrue(lot_acceptance_holds(4, 40, 10.0))

    def test_representation_error_at_the_allowable_is_absorbed(self):
        self.assertTrue(lot_acceptance_holds(4, 40, 10.0 - PERCENT_TOLERANCE / 2.0))

    def test_a_real_overshoot_still_fails(self):
        self.assertFalse(lot_acceptance_holds(8, 40, 10.0))

    def test_an_allowable_outside_nought_to_a_hundred_rejected(self):
        with self.assertRaises(ValueError):
            lot_acceptance_holds(2, 40, 140.0)


class NormalizeOrderTests(unittest.TestCase):
    def test_a_complete_order_round_trips(self):
        record = normalize_order(order())
        self.assertEqual(record["order_id"], "po-2026-0041")
        self.assertAlmostEqual(
            record["allowable_defective_percent"],
            DEFAULT_ALLOWABLE_DEFECTIVE_PERCENT,
            places=9,
        )

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            normalize_order(["po-2026-0041"])

    def test_blank_order_id_rejected(self):
        with self.assertRaises(ValueError):
            normalize_order(order(order_id="  "))

    def test_a_missing_previous_approval_rejected(self):
        raw = order()
        del raw["previous_approval"]
        with self.assertRaises(ValueError):
            normalize_order(raw)

    def test_a_blank_production_line_rejected(self):
        with self.assertRaises(ValueError):
            normalize_order(with_build(production_line=""))

    def test_an_order_dated_before_its_approval_rejected(self):
        with self.assertRaises(ValueError):
            normalize_order(with_build(order_date="2024-01-01"))

    def test_a_non_boolean_alert_flag_rejected(self):
        with self.assertRaises(ValueError):
            normalize_order(order(open_alert="no"))

    def test_a_process_change_without_an_area_rejected(self):
        with self.assertRaises(ValueError):
            normalize_order(order(changes=[{"kind": "process-change", "area": None}]))

    def test_changes_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            normalize_order(order(changes={"kind": "no-change"}))


class IdentityTests(unittest.TestCase):
    def test_the_same_article_has_no_identity_finding(self):
        self.assertEqual(identity_findings(order()), [])

    def test_a_moved_part_number_is_flagged(self):
        self.assertIn("part-number-changed", identity_findings(with_build(part_number="hyb-4413")))

    def test_a_moved_production_line_is_flagged(self):
        self.assertIn(
            "production-line-changed", identity_findings(with_build(production_line="line-5"))
        )

    def test_a_moved_manufacturer_is_flagged(self):
        self.assertIn(
            "manufacturer-changed", identity_findings(with_build(manufacturer="hybrid-house-beta"))
        )


class ContinuityTests(unittest.TestCase):
    def test_the_gap_is_measured_in_whole_months(self):
        self.assertEqual(continuity_gap_months(order()), 10)

    def test_a_gap_on_the_window_is_still_inside_it(self):
        raw = with_build(order_date="2027-04-10")
        self.assertEqual(continuity_gap_months(raw), CONTINUITY_WINDOW_MONTHS)
        self.assertEqual(assess_recurrent_order(raw)["route"], ROUTE_REDUCED)

    def test_a_gap_past_the_window_pushes_the_order_back(self):
        raw = with_build(order_date="2027-06-10")
        result = assess_recurrent_order(raw)
        self.assertIn("continuity-window-exceeded", result["findings"])
        self.assertEqual(result["route"], ROUTE_FULL)


class ChangeAggregationTests(unittest.TestCase):
    def test_an_empty_change_list_ranks_at_no_change(self):
        self.assertEqual(worst_change_rank([]), 0)

    def test_the_most_disruptive_change_governs(self):
        changes = [
            {"kind": "documentation-only", "area": None},
            {"kind": "process-change", "area": "sealing"},
        ]
        self.assertEqual(worst_change_rank(changes), CHANGE_RANKS["process-change"])

    def test_only_process_changes_re_open_groups(self):
        changes = [{"kind": "documentation-only", "area": "sealing"}]
        self.assertEqual(reopened_test_groups(changes), ())

    def test_two_process_changes_take_the_union_of_their_groups(self):
        changes = [
            {"kind": "process-change", "area": "sealing"},
            {"kind": "process-change", "area": "wire-bonding"},
        ]
        groups = reopened_test_groups(changes)
        self.assertIn("hermeticity-and-seal", groups)
        self.assertIn("bond-pull-strength", groups)
        self.assertEqual(list(groups), sorted(set(groups)))

    def test_a_non_sequence_change_list_rejected(self):
        with self.assertRaises(ValueError):
            worst_change_rank("no-change")


class AssessRecurrentOrderTests(unittest.TestCase):
    def test_a_clean_repeat_order_takes_the_reduced_route(self):
        result = assess_recurrent_order(order())
        self.assertEqual(result["route"], ROUTE_REDUCED)
        self.assertEqual(result["evidence_set"], tuple(BASE_EVIDENCE))
        self.assertEqual(result["findings"], [])

    def test_a_documentation_only_change_keeps_the_reduced_route(self):
        result = assess_recurrent_order(
            order(changes=[{"kind": "documentation-only", "area": None}])
        )
        self.assertEqual(result["route"], ROUTE_REDUCED)

    def test_a_process_change_takes_the_partial_route(self):
        result = assess_recurrent_order(
            order(changes=[{"kind": "process-change", "area": "die-attach"}])
        )
        self.assertEqual(result["route"], ROUTE_PARTIAL)
        self.assertIn("die-shear-strength", result["reopened_test_groups"])
        self.assertIn("die-shear-strength", result["evidence_set"])

    def test_a_design_change_ends_the_recurrent_route(self):
        result = assess_recurrent_order(
            order(changes=[{"kind": "design-change", "area": None}])
        )
        self.assertEqual(result["route"], ROUTE_FULL)
        self.assertIn("design-change-declared", result["findings"])
        self.assertFalse(result["reduced_route_available"])

    def test_an_open_alert_ends_the_recurrent_route(self):
        result = assess_recurrent_order(order(open_alert=True))
        self.assertIn("open-alert-against-the-design", result["findings"])
        self.assertEqual(result["route"], ROUTE_FULL)

    def test_a_previous_lot_over_the_allowable_ends_the_route(self):
        result = assess_recurrent_order(with_approval(lot_defectives=9))
        self.assertIn("previous-lot-above-allowable-defectives", result["findings"])
        self.assertEqual(result["route"], ROUTE_FULL)

    def test_a_previous_lot_exactly_on_the_allowable_is_kept(self):
        result = assess_recurrent_order(with_approval(lot_defectives=4))
        self.assertAlmostEqual(result["defective_percent"], 10.0, places=9)
        self.assertEqual(result["route"], ROUTE_REDUCED)

    def test_an_advanced_drawing_issue_is_noted_without_ending_the_route(self):
        raw = with_build(drawing_issue="d")
        result = assess_recurrent_order(raw)
        self.assertIn(
            "drawing-issue-advanced-without-design-change", result["findings"]
        )
        self.assertEqual(result["route"], ROUTE_REDUCED)

    def test_a_moved_line_ends_the_recurrent_route(self):
        result = assess_recurrent_order(with_build(production_line="line-5"))
        self.assertEqual(result["route"], ROUTE_FULL)
        self.assertIn("production-line-changed", result["findings"])

    def test_a_blocked_order_is_not_given_re_opened_groups(self):
        raw = order(
            open_alert=True, changes=[{"kind": "process-change", "area": "sealing"}]
        )
        result = assess_recurrent_order(raw)
        self.assertEqual(result["reopened_test_groups"], ())


class OrderBookTests(unittest.TestCase):
    def book(self):
        return [
            order(order_id="po-2026-0041"),
            order(
                order_id="po-2026-0042",
                changes=[{"kind": "process-change", "area": "wire-bonding"}],
            ),
            order(order_id="po-2026-0043", open_alert=True),
        ]

    def test_every_order_produces_a_record(self):
        report = assess_order_book(self.book())
        self.assertEqual(len(report["records"]), 3)

    def test_the_routes_are_counted(self):
        report = assess_order_book(self.book())
        self.assertEqual(report["route_counts"][ROUTE_REDUCED], 1)
        self.assertEqual(report["route_counts"][ROUTE_PARTIAL], 1)
        self.assertEqual(report["route_counts"][ROUTE_FULL], 1)

    def test_a_pushed_back_order_carries_its_reasons(self):
        report = assess_order_book(self.book())
        self.assertEqual(report["pushed_to_full_approval"][0]["order_id"], "po-2026-0043")
        self.assertIn(
            "open-alert-against-the-design",
            report["pushed_to_full_approval"][0]["findings"],
        )

    def test_the_campaign_groups_are_the_union_of_the_partial_orders(self):
        report = assess_order_book(self.book())
        self.assertIn("bond-pull-strength", report["campaign_reopened_groups"])

    def test_a_mixed_book_is_not_all_on_the_reduced_route(self):
        self.assertFalse(assess_order_book(self.book())["all_on_reduced_route"])

    def test_a_clean_book_is_all_on_the_reduced_route(self):
        self.assertTrue(assess_order_book([order()])["all_on_reduced_route"])

    def test_duplicate_order_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_order_book([order(), order()])

    def test_an_empty_book_rejected(self):
        with self.assertRaises(ValueError):
            assess_order_book([])

    def test_a_non_sequence_book_rejected(self):
        with self.assertRaises(ValueError):
            assess_order_book(order())


if __name__ == "__main__":
    unittest.main()
