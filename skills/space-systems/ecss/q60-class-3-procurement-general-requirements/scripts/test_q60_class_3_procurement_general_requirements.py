"""Contract test for the ECSS-Q-ST-60C clause 6.3.1 Class 3 procurement leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q60_class_3_procurement_general_requirements.py
"""

import unittest

from q60_class_3_procurement_general_requirements_logic import (
    DATE_CODE_AGE_LIMIT_MONTHS,
    EVIDENCE_BEARING_ROUTES,
    MARGIN_TOLERANCE,
    PART_TYPE_STATUSES,
    QUALITY_LEVEL_LADDER,
    REQUIRED_AUTHENTICITY_EVIDENCE,
    SELF_TRACEABLE_ROUTES,
    SUPPLY_ROUTES,
    TARGET_CATEGORY,
    UPRATING_METHODS,
    assess_class_3_procurement,
    assess_purchased_type,
    authenticity_findings,
    date_code_findings,
    envelope_contains_mission,
    index_baseline,
    normalize_uprating_record,
    quality_findings,
    quality_level_is_adequate,
    quality_rank,
    temperature_margins,
    uprating_findings,
)


def baseline_entry(**overrides):
    entry = {
        "part_type": "ldo-regulator-3v3",
        "minimum_quality_level": "industrial-grade",
        "mission_low_c": -30.0,
        "mission_high_c": 70.0,
    }
    entry.update(overrides)
    return entry


def purchase(**overrides):
    entry = {
        "part_type": "ldo-regulator-3v3",
        "offered_quality_level": "automotive-qualified",
        "rated_low_c": -40.0,
        "rated_high_c": 85.0,
        "supply": {"route": "franchised-distributor", "evidence": []},
        "date_code_age_months": 18.0,
        "uprating_record": None,
    }
    entry.update(overrides)
    return entry


def order(**overrides):
    entry = {
        "order_id": "po-3311",
        "declared_category": TARGET_CATEGORY,
        "baseline": [baseline_entry()],
        "purchases": [purchase()],
    }
    entry.update(overrides)
    return entry


class QualityLadderTests(unittest.TestCase):
    def test_the_ladder_has_no_repeated_rung(self):
        self.assertEqual(len(QUALITY_LEVEL_LADDER), len(set(QUALITY_LEVEL_LADDER)))

    def test_the_ladder_is_indexed_in_ascending_order(self):
        ranks = [quality_rank(level) for level in QUALITY_LEVEL_LADDER]
        self.assertEqual(ranks, sorted(ranks))

    def test_the_class_3_ladder_reaches_down_to_a_commercial_rung(self):
        self.assertEqual(quality_rank("commercial-catalogue"), 0)

    def test_a_higher_rung_satisfies_a_lower_minimum(self):
        self.assertTrue(
            quality_level_is_adequate("military-grade", "industrial-grade")
        )

    def test_the_demanded_rung_itself_is_adequate(self):
        self.assertTrue(
            quality_level_is_adequate("industrial-grade", "industrial-grade")
        )

    def test_a_lower_rung_does_not_satisfy_a_higher_minimum(self):
        self.assertFalse(
            quality_level_is_adequate("commercial-catalogue", "automotive-qualified")
        )

    def test_an_unknown_quality_level_is_rejected(self):
        with self.assertRaises(ValueError):
            quality_rank("whatever-was-in-the-drawer")

    def test_an_inadequate_rung_raises_exactly_one_finding(self):
        findings = quality_findings("commercial-catalogue", baseline_entry())
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["finding"], "offered-quality-level-below-the-baseline-minimum"
        )

    def test_an_adequate_rung_raises_no_finding(self):
        self.assertEqual(quality_findings("space-qualified", baseline_entry()), ())


class BaselineIndexTests(unittest.TestCase):
    def test_a_baseline_indexes_by_part_type(self):
        index = index_baseline([baseline_entry()])
        self.assertIn("ldo-regulator-3v3", index)

    def test_a_duplicate_baseline_part_type_is_rejected(self):
        with self.assertRaises(ValueError):
            index_baseline([baseline_entry(), baseline_entry()])

    def test_an_empty_baseline_is_rejected(self):
        with self.assertRaises(ValueError):
            index_baseline([])

    def test_a_baseline_whose_mission_range_is_inverted_is_rejected(self):
        with self.assertRaises(ValueError):
            index_baseline([baseline_entry(mission_low_c=80.0, mission_high_c=20.0)])

    def test_a_baseline_minimum_outside_the_ladder_is_rejected(self):
        with self.assertRaises(ValueError):
            index_baseline([baseline_entry(minimum_quality_level="good-enough")])

    def test_a_bare_string_is_not_a_baseline(self):
        with self.assertRaises(ValueError):
            index_baseline("ldo-regulator-3v3")


class TemperatureTests(unittest.TestCase):
    def test_a_wider_rated_envelope_gives_margin_at_both_ends(self):
        margins = temperature_margins(-40.0, 85.0, baseline_entry())
        self.assertAlmostEqual(margins["cold_margin_c"], 10.0, places=9)
        self.assertAlmostEqual(margins["hot_margin_c"], 15.0, places=9)

    def test_a_rated_envelope_equal_to_the_mission_envelope_still_contains_it(self):
        entry = baseline_entry()
        self.assertTrue(
            envelope_contains_mission(
                entry["mission_low_c"], entry["mission_high_c"], entry
            )
        )

    def test_an_envelope_matching_exactly_has_zero_margin_at_both_ends(self):
        entry = baseline_entry()
        margins = temperature_margins(
            entry["mission_low_c"], entry["mission_high_c"], entry
        )
        self.assertAlmostEqual(margins["cold_margin_c"], 0.0, places=9)
        self.assertAlmostEqual(margins["hot_margin_c"], 0.0, places=9)

    def test_a_hot_end_short_of_the_mission_does_not_contain_it(self):
        self.assertFalse(envelope_contains_mission(-40.0, 60.0, baseline_entry()))

    def test_a_cold_end_short_of_the_mission_does_not_contain_it(self):
        self.assertFalse(envelope_contains_mission(-10.0, 85.0, baseline_entry()))

    def test_an_inverted_rated_envelope_is_rejected(self):
        with self.assertRaises(ValueError):
            temperature_margins(85.0, -40.0, baseline_entry())

    def test_a_non_numeric_rated_bound_is_rejected(self):
        with self.assertRaises(ValueError):
            temperature_margins("cold", 85.0, baseline_entry())


class UpratingTests(unittest.TestCase):
    def test_a_part_inside_the_envelope_needs_no_uprating_record(self):
        self.assertEqual(
            uprating_findings(-40.0, 85.0, baseline_entry(), None), ()
        )

    def test_a_part_outside_the_envelope_without_a_record_is_a_finding(self):
        findings = uprating_findings(-10.0, 60.0, baseline_entry(), None)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["finding"],
            "temperature-uprating-without-a-justification-record",
        )

    def test_the_finding_names_both_ends_that_fall_short(self):
        findings = uprating_findings(-10.0, 60.0, baseline_entry(), None)
        self.assertIn("cold end", findings[0]["detail"])
        self.assertIn("hot end", findings[0]["detail"])

    def test_a_recognised_uprating_record_admits_the_part(self):
        record = {
            "method": UPRATING_METHODS[0],
            "evidence_reference": "upr-001",
        }
        self.assertEqual(
            uprating_findings(-10.0, 60.0, baseline_entry(), record), ()
        )

    def test_an_unrecognised_uprating_method_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_uprating_record(
                {"method": "we-tested-one", "evidence_reference": "upr-002"}
            )

    def test_an_uprating_record_with_no_evidence_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_uprating_record(
                {"method": UPRATING_METHODS[0], "evidence_reference": "  "}
            )


class SupplyRouteTests(unittest.TestCase):
    def test_every_route_sits_in_exactly_one_group(self):
        self.assertEqual(
            set(SELF_TRACEABLE_ROUTES) & set(EVIDENCE_BEARING_ROUTES), set()
        )
        self.assertEqual(
            set(SUPPLY_ROUTES),
            set(SELF_TRACEABLE_ROUTES) | set(EVIDENCE_BEARING_ROUTES),
        )

    def test_a_self_traceable_route_needs_no_authenticity_evidence(self):
        self.assertEqual(
            authenticity_findings({"route": "manufacturer", "evidence": []}), ()
        )

    def test_a_broker_route_with_no_evidence_raises_one_finding_per_item(self):
        findings = authenticity_findings({"route": "broker", "evidence": []})
        self.assertEqual(len(findings), len(REQUIRED_AUTHENTICITY_EVIDENCE))

    def test_a_broker_route_with_the_full_evidence_set_is_admitted(self):
        findings = authenticity_findings(
            {
                "route": "broker",
                "evidence": list(REQUIRED_AUTHENTICITY_EVIDENCE),
            }
        )
        self.assertEqual(findings, ())

    def test_a_partial_evidence_set_names_only_what_is_still_absent(self):
        findings = authenticity_findings(
            {
                "route": "open-market-distributor",
                "evidence": [REQUIRED_AUTHENTICITY_EVIDENCE[0]],
            }
        )
        self.assertEqual(len(findings), len(REQUIRED_AUTHENTICITY_EVIDENCE) - 1)

    def test_an_unknown_supply_route_is_rejected(self):
        with self.assertRaises(ValueError):
            authenticity_findings({"route": "a-colleague-had-some", "evidence": []})

    def test_an_unknown_evidence_name_is_rejected(self):
        with self.assertRaises(ValueError):
            authenticity_findings(
                {"route": "broker", "evidence": ["it-looked-right"]}
            )


class DateCodeTests(unittest.TestCase):
    def test_a_fresh_lot_raises_no_finding(self):
        self.assertEqual(date_code_findings(6.0), ())

    def test_a_lot_exactly_on_the_age_limit_is_still_accepted(self):
        age = DATE_CODE_AGE_LIMIT_MONTHS
        self.assertAlmostEqual(age, DATE_CODE_AGE_LIMIT_MONTHS, places=9)
        self.assertEqual(date_code_findings(age), ())

    def test_a_lot_well_past_the_age_limit_is_refused(self):
        findings = date_code_findings(DATE_CODE_AGE_LIMIT_MONTHS + 24.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["finding"], "lot-date-code-older-than-the-agreed-limit"
        )

    def test_a_negative_lot_age_is_rejected(self):
        with self.assertRaises(ValueError):
            date_code_findings(-1.0)

    def test_a_non_positive_age_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            date_code_findings(6.0, 0.0)

    def test_the_margin_tolerance_is_small_enough_to_separate_a_bound(self):
        self.assertLess(MARGIN_TOLERANCE, 1e-6)


class PurchasedTypeTests(unittest.TestCase):
    def test_a_conforming_purchase_raises_nothing(self):
        record = assess_purchased_type(purchase(), index_baseline([baseline_entry()]))
        self.assertEqual(record["status"], "class-3-part-type-conforms-to-baseline")
        self.assertTrue(record["conforms"])
        self.assertEqual(record["findings"], [])

    def test_a_part_type_absent_from_the_baseline_is_named(self):
        record = assess_purchased_type(
            purchase(part_type="unlisted-opto"), index_baseline([baseline_entry()])
        )
        self.assertEqual(record["status"], "class-3-part-type-not-in-baseline")
        self.assertEqual(
            record["findings"][0]["finding"],
            "part-type-bought-against-no-baseline-entry",
        )

    def test_every_departure_is_reported_at_once(self):
        record = assess_purchased_type(
            purchase(
                offered_quality_level="commercial-catalogue",
                rated_low_c=-10.0,
                rated_high_c=60.0,
                supply={"route": "broker", "evidence": []},
                date_code_age_months=DATE_CODE_AGE_LIMIT_MONTHS + 12.0,
            ),
            index_baseline([baseline_entry()]),
        )
        names = [f["finding"] for f in record["findings"]]
        self.assertIn("offered-quality-level-below-the-baseline-minimum", names)
        self.assertIn("temperature-uprating-without-a-justification-record", names)
        self.assertIn("evidence-bearing-route-missing-authenticity-evidence", names)
        self.assertIn("lot-date-code-older-than-the-agreed-limit", names)

    def test_every_finding_carries_the_part_type_it_belongs_to(self):
        record = assess_purchased_type(
            purchase(offered_quality_level="commercial-catalogue"),
            index_baseline([baseline_entry()]),
        )
        for finding in record["findings"]:
            self.assertEqual(finding["part_type"], "ldo-regulator-3v3")

    def test_every_status_name_is_one_the_module_publishes(self):
        index = index_baseline([baseline_entry()])
        self.assertIn(assess_purchased_type(purchase(), index)["status"], PART_TYPE_STATUSES)
        self.assertIn(
            assess_purchased_type(purchase(part_type="unlisted-opto"), index)["status"],
            PART_TYPE_STATUSES,
        )

    def test_a_non_mapping_purchase_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_purchased_type("ldo-regulator-3v3", index_baseline([baseline_entry()]))


class OrderTests(unittest.TestCase):
    def test_a_conforming_order_conforms(self):
        report = assess_class_3_procurement(order())
        self.assertTrue(report["order_conforms"])
        self.assertEqual(report["findings"], [])
        self.assertAlmostEqual(report["conforming_fraction"], 1.0, places=9)

    def test_a_baseline_entry_nobody_bought_is_reported(self):
        report = assess_class_3_procurement(
            order(baseline=[baseline_entry(), baseline_entry(part_type="shunt-10m")])
        )
        self.assertEqual(report["baseline_entries_never_bought"], ["shunt-10m"])
        self.assertFalse(report["order_conforms"])

    def test_the_conforming_fraction_counts_only_conforming_types(self):
        report = assess_class_3_procurement(
            order(
                baseline=[baseline_entry(), baseline_entry(part_type="shunt-10m")],
                purchases=[
                    purchase(),
                    purchase(
                        part_type="shunt-10m",
                        offered_quality_level="commercial-catalogue",
                    ),
                ],
            )
        )
        self.assertAlmostEqual(report["conforming_fraction"], 0.5, places=9)
        self.assertEqual(report["departing_part_types"], ["shunt-10m"])

    def test_an_order_declared_in_another_category_is_not_checked_here(self):
        report = assess_class_3_procurement(order(declared_category="class-2"))
        self.assertIn(
            "declared-category-is-not-the-one-being-checked",
            [f["finding"] for f in report["findings"]],
        )
        self.assertFalse(report["order_conforms"])

    def test_a_repeated_purchased_part_type_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_procurement(order(purchases=[purchase(), purchase()]))

    def test_an_order_with_no_purchases_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_procurement(order(purchases=[]))

    def test_an_empty_order_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_procurement(order(order_id="  "))

    def test_a_non_sequence_purchase_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_procurement(order(purchases={"part_type": "x"}))

    def test_an_order_may_tighten_the_date_code_limit(self):
        report = assess_class_3_procurement(
            order(date_code_age_limit_months=12.0)
        )
        self.assertIn(
            "lot-date-code-older-than-the-agreed-limit",
            [f["finding"] for f in report["findings"]],
        )


if __name__ == "__main__":
    unittest.main()
