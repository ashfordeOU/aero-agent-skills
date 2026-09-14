"""Contract tests for the clause 6.3.6 class 3 buy-off inspection logic.

The cases follow the workflow one step at a time: the day parsing the closure
sequence rests on, the three release routes and what each one has to name, the
item-by-item document walk, the quantity reconciliation and its ceiling, the
moisture release against the packaging, the nonconformance grouping with a
closure requirement per route, and the release, partial-release or hold
disposition. Each limit is exercised on both sides, and the indicator boundary
is compared with a tolerance rather than a strict inequality.
"""

import unittest

from q6013_class_3_buy_off_inspection_logic import (
    MOISTURE_SENSITIVE_FROM_LEVEL,
    NONCONFORMANCE_STATES,
    OPTIONAL_DOCUMENTS,
    RELEASE_MODES,
    REQUIRED_DOCUMENTS,
    SEVERITIES,
    assess_buy_off,
    document_record,
    moisture_record,
    nonconformance_record,
    parse_day,
    quantity_record,
    release_mode_record,
)


def _spec(**overrides):
    spec = {
        "lot_reference": "LOT-8820",
        "delivery_date": "2026-05-04",
        "release": {
            "mode": "documentary-desk-review",
            "record_reference": "DESK-REL-118",
        },
        "documents_seen": list(REQUIRED_DOCUMENTS) + ["test-data-summary"],
        "ordered": 500,
        "delivered": 500,
        "rejected_on_receipt": 0,
        "overage_tolerance_percent": 2,
        "moisture_sensitivity_level": 3,
        "barrier_bag_intact": True,
        "humidity_indicator_percent": 5.0,
        "indicator_limit_percent": 10.0,
        "nonconformances": [],
        "minor_allowance": 1,
    }
    spec.update(overrides)
    return spec


class DayTests(unittest.TestCase):
    def test_parses_a_well_formed_day(self):
        self.assertEqual(parse_day("delivery_date", "2026-05-04"), (2026, 5, 4))

    def test_month_thirteen_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("delivery_date", "2026-13-04")

    def test_day_past_month_end_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("delivery_date", "2026-02-30")

    def test_short_form_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("delivery_date", "2026-5-4")


class ReleaseModeTests(unittest.TestCase):
    def test_desk_review_needs_only_its_record(self):
        record = release_mode_record(
            {"mode": "documentary-desk-review", "record_reference": "DESK-REL-118"}
        )
        self.assertTrue(record["admissible"])
        self.assertFalse(record["delegated"])

    def test_desk_review_without_a_record_refused(self):
        record = release_mode_record({"mode": "documentary-desk-review"})
        self.assertFalse(record["admissible"])
        self.assertIn("record_reference", record["missing"])

    def test_witnessed_route_needs_an_independent_inspector(self):
        record = release_mode_record(
            {
                "mode": "source-witness",
                "record_reference": "SRC-221",
                "inspector_organisation": "customer quality",
                "inspector_independent": True,
            }
        )
        self.assertTrue(record["admissible"])
        self.assertTrue(record["inspector_independent"])

    def test_witnessed_route_with_a_dependent_inspector_refused(self):
        record = release_mode_record(
            {
                "mode": "source-witness",
                "record_reference": "SRC-221",
                "inspector_organisation": "the production line",
                "inspector_independent": False,
            }
        )
        self.assertFalse(record["admissible"])

    def test_witnessed_route_without_the_independence_declaration_refused(self):
        record = release_mode_record(
            {
                "mode": "source-witness",
                "record_reference": "SRC-221",
                "inspector_organisation": "customer quality",
            }
        )
        self.assertFalse(record["admissible"])
        self.assertIn("inspector_independent", record["missing"])

    def test_delegated_route_with_reference_and_issue_admissible(self):
        record = release_mode_record(
            {
                "mode": "delegated-supplier-release",
                "record_reference": "DEL-REL-9",
                "delegation_reference": "PA-DEL-441",
                "delegation_issue": "B",
            }
        )
        self.assertTrue(record["admissible"])
        self.assertTrue(record["delegated"])

    def test_delegated_route_without_an_issue_refused(self):
        record = release_mode_record(
            {
                "mode": "delegated-supplier-release",
                "record_reference": "DEL-REL-9",
                "delegation_reference": "PA-DEL-441",
            }
        )
        self.assertFalse(record["admissible"])
        self.assertIn("delegation_issue", record["missing"])

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            release_mode_record({"mode": "a-quick-word-on-the-phone"})

    def test_missing_mode_rejected(self):
        with self.assertRaises(ValueError):
            release_mode_record({"record_reference": "DESK-REL-118"})

    def test_every_mode_is_reachable(self):
        self.assertEqual(len(set(RELEASE_MODES)), 3)


class DocumentTests(unittest.TestCase):
    def test_complete_pack_is_complete(self):
        record = document_record(list(REQUIRED_DOCUMENTS))
        self.assertTrue(record["complete"])
        self.assertEqual(record["missing"], [])

    def test_one_missing_item_is_named_not_averaged(self):
        record = document_record([name for name in REQUIRED_DOCUMENTS if name != "certificate-of-conformity"])
        self.assertFalse(record["complete"])
        self.assertEqual(record["missing"], ["certificate-of-conformity"])
        self.assertAlmostEqual(record["required_share_percent"], 75.0, places=9)

    def test_optional_items_do_not_change_completeness(self):
        record = document_record(list(REQUIRED_DOCUMENTS) + list(OPTIONAL_DOCUMENTS))
        self.assertTrue(record["complete"])
        self.assertEqual(record["optional_present"], list(OPTIONAL_DOCUMENTS))
        self.assertFalse(record["optional_thin"])

    def test_empty_pack_misses_everything(self):
        record = document_record(None)
        self.assertEqual(record["missing"], list(REQUIRED_DOCUMENTS))

    def test_unknown_document_rejected(self):
        with self.assertRaises(ValueError):
            document_record(["a-sticky-note"])

    def test_document_listed_twice_rejected(self):
        with self.assertRaises(ValueError):
            document_record(["certificate-of-conformity", "certificate-of-conformity"])


class QuantityTests(unittest.TestCase):
    def test_exact_delivery_reconciles(self):
        record = quantity_record(500, 500, 0)
        self.assertTrue(record["reconciled"])
        self.assertEqual(record["accepted_quantity"], 500)
        self.assertAlmostEqual(record["fill_percent"], 100.0, places=9)

    def test_receipt_rejections_leave_a_shortfall(self):
        record = quantity_record(500, 500, 20)
        self.assertEqual(record["accepted_quantity"], 480)
        self.assertEqual(record["shortfall"], 20)
        self.assertFalse(record["reconciled"])

    def test_overage_on_the_ceiling_is_allowed(self):
        record = quantity_record(500, 510, 0, 2)
        self.assertEqual(record["delivery_ceiling"], 510)
        self.assertEqual(record["overage"], 0)

    def test_overage_one_past_the_ceiling_is_a_finding(self):
        record = quantity_record(500, 511, 0, 2)
        self.assertEqual(record["overage"], 1)
        self.assertFalse(record["reconciled"])

    def test_rejections_beyond_the_delivery_rejected(self):
        with self.assertRaises(ValueError):
            quantity_record(500, 100, 101)

    def test_zero_order_rejected(self):
        with self.assertRaises(ValueError):
            quantity_record(0, 0, 0)

    def test_tolerance_beyond_one_hundred_percent_rejected(self):
        with self.assertRaises(ValueError):
            quantity_record(500, 500, 0, 140)


class MoistureTests(unittest.TestCase):
    def test_non_sensitive_part_needs_no_bake_even_when_breached(self):
        record = moisture_record(1, False, 40.0, 10.0)
        self.assertFalse(record["moisture_sensitive"])
        self.assertFalse(record["bake_required"])

    def test_sensitive_part_in_an_intact_bag_needs_no_bake(self):
        record = moisture_record(3, True, 5.0, 10.0)
        self.assertTrue(record["moisture_sensitive"])
        self.assertFalse(record["bake_required"])

    def test_breached_bag_sends_a_sensitive_part_to_a_bake(self):
        record = moisture_record(3, False, 5.0, 10.0)
        self.assertTrue(record["bake_required"])

    def test_indicator_exactly_on_the_limit_is_accepted(self):
        record = moisture_record(3, True, 10.0, 10.0)
        self.assertFalse(record["indicator_exceeded"])
        self.assertFalse(record["bake_required"])

    def test_indicator_past_the_limit_sends_the_lot_to_a_bake(self):
        record = moisture_record(3, True, 20.0, 10.0)
        self.assertTrue(record["indicator_exceeded"])
        self.assertTrue(record["bake_required"])

    def test_threshold_level_is_sensitive(self):
        record = moisture_record(MOISTURE_SENSITIVE_FROM_LEVEL, True, 0.0, 10.0)
        self.assertTrue(record["moisture_sensitive"])

    def test_level_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            moisture_record(7, True)

    def test_non_boolean_bag_flag_rejected(self):
        with self.assertRaises(ValueError):
            moisture_record(3, "intact")


class NonconformanceTests(unittest.TestCase):
    def test_no_nonconformances_does_not_block(self):
        record = nonconformance_record([], "2026-05-04")
        self.assertFalse(record["blocking"])

    def test_open_major_blocks(self):
        record = nonconformance_record(
            [{"identifier": "NCR-1", "severity": "major", "state": "open"}], "2026-05-04"
        )
        self.assertTrue(record["blocking"])

    def test_use_as_is_with_authority_and_day_closes_a_major(self):
        record = nonconformance_record(
            [
                {
                    "identifier": "NCR-1",
                    "severity": "major",
                    "state": "use-as-is",
                    "authority": "parts control board",
                    "decision_date": "2026-05-06",
                }
            ],
            "2026-05-04",
        )
        self.assertFalse(record["blocking"])
        self.assertEqual(len(record["closed"]), 1)

    def test_use_as_is_without_an_authority_stays_open(self):
        record = nonconformance_record(
            [
                {
                    "identifier": "NCR-1",
                    "severity": "major",
                    "state": "use-as-is",
                    "decision_date": "2026-05-06",
                }
            ],
            "2026-05-04",
        )
        self.assertTrue(record["blocking"])
        self.assertEqual(len(record["refused_closures"]), 1)

    def test_use_as_is_decided_before_delivery_stays_open(self):
        record = nonconformance_record(
            [
                {
                    "identifier": "NCR-1",
                    "severity": "major",
                    "state": "use-as-is",
                    "authority": "parts control board",
                    "decision_date": "2026-05-01",
                }
            ],
            "2026-05-04",
        )
        self.assertTrue(record["blocking"])

    def test_use_as_is_decided_on_the_delivery_day_closes(self):
        record = nonconformance_record(
            [
                {
                    "identifier": "NCR-1",
                    "severity": "major",
                    "state": "use-as-is",
                    "authority": "parts control board",
                    "decision_date": "2026-05-04",
                }
            ],
            "2026-05-04",
        )
        self.assertFalse(record["blocking"])

    def test_repair_without_a_verification_reference_stays_open(self):
        record = nonconformance_record(
            [{"identifier": "NCR-2", "severity": "major", "state": "repaired-and-verified"}],
            "2026-05-04",
        )
        self.assertTrue(record["blocking"])

    def test_repair_with_a_verification_reference_closes(self):
        record = nonconformance_record(
            [
                {
                    "identifier": "NCR-2",
                    "severity": "major",
                    "state": "repaired-and-verified",
                    "verification_reference": "VER-77",
                }
            ],
            "2026-05-04",
        )
        self.assertFalse(record["blocking"])

    def test_scrapping_needs_nothing_further(self):
        record = nonconformance_record(
            [{"identifier": "NCR-3", "severity": "major", "state": "scrapped"}], "2026-05-04"
        )
        self.assertFalse(record["blocking"])

    def test_minors_on_the_allowance_do_not_block(self):
        items = [
            {"identifier": "NCR-%d" % index, "severity": "minor", "state": "open"}
            for index in range(2)
        ]
        self.assertFalse(nonconformance_record(items, "2026-05-04", 2)["blocking"])

    def test_minors_one_past_the_allowance_block(self):
        items = [
            {"identifier": "NCR-%d" % index, "severity": "minor", "state": "open"}
            for index in range(3)
        ]
        self.assertTrue(nonconformance_record(items, "2026-05-04", 2)["blocking"])

    def test_duplicate_identifier_rejected(self):
        with self.assertRaises(ValueError):
            nonconformance_record(
                [
                    {"identifier": "NCR-1", "severity": "minor", "state": "open"},
                    {"identifier": "NCR-1", "severity": "minor", "state": "open"},
                ],
                "2026-05-04",
            )

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            nonconformance_record(
                [{"identifier": "NCR-1", "severity": "minor", "state": "probably-fine"}],
                "2026-05-04",
            )

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            nonconformance_record(
                [{"identifier": "NCR-1", "severity": "catastrophic", "state": "open"}],
                "2026-05-04",
            )

    def test_state_and_severity_vocabularies_are_disjoint(self):
        self.assertEqual(set(SEVERITIES) & set(NONCONFORMANCE_STATES), set())


class AssessmentTests(unittest.TestCase):
    def test_clean_delivery_releases_the_lot(self):
        result = assess_buy_off(_spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "release-lot")
        self.assertEqual(result["findings"], [])

    def test_shortfall_gives_a_partial_release(self):
        result = assess_buy_off(_spec(rejected_on_receipt=20))
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "partial-release")
        self.assertTrue(any("stays open against the supplier" in a for a in result["advisories"]))

    def test_missing_certificate_holds_the_lot(self):
        result = assess_buy_off(
            _spec(documents_seen=[name for name in REQUIRED_DOCUMENTS if name != "certificate-of-conformity"])
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["disposition"], "hold-on-receipt")

    def test_inadmissible_release_route_holds_the_lot(self):
        result = assess_buy_off(_spec(release={"mode": "delegated-supplier-release"}))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("release route is missing" in f for f in result["findings"]))

    def test_breached_bag_on_a_sensitive_part_holds_the_lot(self):
        result = assess_buy_off(_spec(barrier_bag_intact=False))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("need a bake before the line" in f for f in result["findings"]))

    def test_open_major_holds_the_lot(self):
        result = assess_buy_off(
            _spec(nonconformances=[{"identifier": "NCR-1", "severity": "major", "state": "open"}])
        )
        self.assertFalse(result["accepted"])

    def test_overage_beyond_the_ceiling_holds_the_lot(self):
        result = assess_buy_off(_spec(delivered=560))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("nobody ordered them" in f for f in result["findings"]))

    def test_thin_optional_evidence_is_an_advisory_not_a_hold(self):
        result = assess_buy_off(_spec(documents_seen=list(REQUIRED_DOCUMENTS)))
        self.assertTrue(result["accepted"])
        self.assertTrue(any("optional evidence" in a for a in result["advisories"]))

    def test_every_failing_check_reported_together(self):
        result = assess_buy_off(
            _spec(
                release={"mode": "delegated-supplier-release"},
                documents_seen=["certificate-of-conformity"],
                barrier_bag_intact=False,
                nonconformances=[{"identifier": "NCR-1", "severity": "major", "state": "open"}],
            )
        )
        self.assertGreaterEqual(len(result["findings"]), 6)

    def test_missing_required_key_rejected(self):
        spec = _spec()
        del spec["delivery_date"]
        with self.assertRaises(ValueError):
            assess_buy_off(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_buy_off(["not", "a", "mapping"])


if __name__ == "__main__":
    unittest.main()
