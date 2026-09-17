"""Contract tests for the clause 5.3.1 Class 2 procurement conformance logic.

The cases walk the duty one step at a time: indexing the agreed baseline,
the procurement-grade ladder, the temperature margin held at each end of the
mission range, the supply route and the evidence it owes, the validity of a
deviation on the order date, and the two-way reconciliation of ordered part
types against baseline entries. Every limit is exercised on both sides, and a
margin landing on its requirement is compared with a representation-sized
tolerance so the verdict does not change between machines.
"""

import datetime
import unittest

from q60_class_2_procurement_general_requirements_logic import (
    EVIDENCE_BEARING_ROUTES,
    MARGIN_TOLERANCE,
    PROCUREMENT_GRADE_LADDER,
    REQUIRED_BROKER_EVIDENCE,
    SELF_TRACEABLE_ROUTES,
    assess_part_type,
    assess_procurement_order,
    deviation_findings,
    grade_findings,
    grade_rank,
    index_baseline,
    normalize_token,
    parse_iso_date,
    supply_route_findings,
    temperature_findings,
    temperature_margins,
)

ORDER_DATE = "2026-04-13"


def _baseline(**overrides):
    entry = {
        "part_type": "ceramic-capacitor-cdr-series",
        "required_grade": "military",
        "mission_low_c": -30.0,
        "mission_high_c": 70.0,
        "required_margin_c": 5.0,
    }
    entry.update(overrides)
    return [entry]


def _purchase(**overrides):
    purchase = {
        "part_type": "ceramic-capacitor-cdr-series",
        "offered_grade": "military",
        "part_low_c": -55.0,
        "part_high_c": 125.0,
        "supply": {"route": "franchised-distributor"},
    }
    purchase.update(overrides)
    return purchase


def _order(**overrides):
    order = {
        "order_reference": "PO-2026-407",
        "order_date": ORDER_DATE,
        "baseline": _baseline(),
        "purchases": [_purchase()],
    }
    order.update(overrides)
    return order


def _entry(**overrides):
    return index_baseline(_baseline(**overrides))["ceramic-capacitor-cdr-series"]


class TokenAndDateTests(unittest.TestCase):
    def test_token_normalised(self):
        self.assertEqual(normalize_token("Franchised_Distributor", "route"), "franchised-distributor")

    def test_blank_token_refused(self):
        with self.assertRaises(ValueError):
            normalize_token("   ", "route")

    def test_non_string_token_refused(self):
        with self.assertRaises(ValueError):
            normalize_token(7, "route")

    def test_iso_date_parsed(self):
        self.assertEqual(parse_iso_date(ORDER_DATE, "date"), datetime.date(2026, 4, 13))

    def test_date_object_passes_through(self):
        day = datetime.date(2026, 4, 13)
        self.assertEqual(parse_iso_date(day, "date"), day)

    def test_non_calendar_date_refused(self):
        with self.assertRaises(ValueError):
            parse_iso_date("2026-04-31", "date")


class GradeLadderTests(unittest.TestCase):
    def test_ladder_rises(self):
        ranks = [grade_rank(g) for g in PROCUREMENT_GRADE_LADDER]
        self.assertEqual(ranks, sorted(ranks))

    def test_equal_grade_raises_nothing(self):
        self.assertEqual(grade_findings("military", _entry()), [])

    def test_higher_grade_satisfies_a_lower_demand(self):
        self.assertEqual(grade_findings("space", _entry()), [])

    def test_lower_grade_reported(self):
        findings = grade_findings("industrial", _entry())
        self.assertTrue(any("below the 'military'" in f for f in findings))

    def test_unknown_grade_refused(self):
        with self.assertRaises(ValueError):
            grade_rank("aerospace-ish")


class BaselineIndexTests(unittest.TestCase):
    def test_baseline_indexed_by_part_type(self):
        index = index_baseline(_baseline())
        self.assertIn("ceramic-capacitor-cdr-series", index)
        self.assertEqual(index["ceramic-capacitor-cdr-series"]["required_grade"], "military")

    def test_duplicate_part_type_refused(self):
        with self.assertRaises(ValueError):
            index_baseline(_baseline() + _baseline())

    def test_missing_baseline_key_refused(self):
        entry = _baseline()[0]
        del entry["required_margin_c"]
        with self.assertRaises(ValueError):
            index_baseline([entry])

    def test_mission_range_that_does_not_rise_refused(self):
        with self.assertRaises(ValueError):
            index_baseline(_baseline(mission_low_c=70.0, mission_high_c=-30.0))

    def test_negative_required_margin_refused(self):
        with self.assertRaises(ValueError):
            index_baseline(_baseline(required_margin_c=-1.0))

    def test_empty_baseline_refused(self):
        with self.assertRaises(ValueError):
            index_baseline([])


class TemperatureTests(unittest.TestCase):
    def test_margins_computed_at_both_ends(self):
        margins = temperature_margins(-55.0, 125.0, _entry())
        self.assertAlmostEqual(margins["cold_margin_c"], 25.0, places=9)
        self.assertAlmostEqual(margins["hot_margin_c"], 55.0, places=9)

    def test_margin_landing_on_the_requirement_is_accepted(self):
        margins = temperature_findings(-35.0, 75.0, _entry())
        self.assertEqual(margins["findings"], [])
        self.assertAlmostEqual(margins["cold_margin_c"], 5.0, places=9)

    def test_cold_shortfall_reported(self):
        margins = temperature_findings(-32.0, 125.0, _entry())
        self.assertTrue(any("cold margin" in f for f in margins["findings"]))

    def test_hot_shortfall_reported(self):
        margins = temperature_findings(-55.0, 72.0, _entry())
        self.assertTrue(any("hot margin" in f for f in margins["findings"]))

    def test_representation_sized_shortfall_is_not_a_finding(self):
        # 0.1 - (-10.2) lands a hair below 10.3 in binary; the tolerance keeps
        # the verdict the same on every machine.
        entry = _entry(mission_low_c=0.1, mission_high_c=70.0, required_margin_c=10.3)
        margins = temperature_findings(-10.2, 85.0, entry)
        self.assertEqual(margins["findings"], [])

    def test_part_range_that_does_not_rise_refused(self):
        with self.assertRaises(ValueError):
            temperature_margins(125.0, -55.0, _entry())

    def test_non_numeric_part_limit_refused(self):
        with self.assertRaises(ValueError):
            temperature_margins("-55", 125.0, _entry())

    def test_tolerance_is_representation_sized_only(self):
        self.assertLess(MARGIN_TOLERANCE, 1e-6)


class SupplyRouteTests(unittest.TestCase):
    def test_manufacturer_route_raises_nothing(self):
        self.assertEqual(supply_route_findings({"route": "manufacturer"}), [])

    def test_every_self_traceable_route_is_clean_without_evidence(self):
        for route in SELF_TRACEABLE_ROUTES:
            self.assertEqual(supply_route_findings({"route": route}), [])

    def test_broker_with_full_evidence_raises_nothing(self):
        supply = {"route": "broker", "evidence": list(REQUIRED_BROKER_EVIDENCE)}
        self.assertEqual(supply_route_findings(supply), [])

    def test_broker_missing_one_evidence_item_reported(self):
        supply = {"route": "broker", "evidence": ["traceability-chain"]}
        findings = supply_route_findings(supply)
        self.assertTrue(any("counterfeit-avoidance-test-report" in f for f in findings))

    def test_every_evidence_bearing_route_needs_the_full_set(self):
        for route in EVIDENCE_BEARING_ROUTES:
            findings = supply_route_findings({"route": route, "evidence": []})
            self.assertEqual(len(findings), len(REQUIRED_BROKER_EVIDENCE))

    def test_unknown_route_refused(self):
        with self.assertRaises(ValueError):
            supply_route_findings({"route": "a-friend-of-the-buyer"})

    def test_non_collection_evidence_refused(self):
        with self.assertRaises(ValueError):
            supply_route_findings({"route": "broker", "evidence": "traceability-chain"})

    def test_missing_route_key_refused(self):
        with self.assertRaises(ValueError):
            supply_route_findings({})


class DeviationTests(unittest.TestCase):
    def test_complete_deviation_raises_nothing(self):
        deviation = {
            "reference": "DEV-2026-019",
            "approval_authority": "parts-control-board",
            "valid_until": "2026-12-31",
        }
        self.assertEqual(deviation_findings(deviation, ORDER_DATE), [])

    def test_deviation_expiring_on_the_order_date_is_still_valid(self):
        deviation = {
            "reference": "DEV-2026-019",
            "approval_authority": "parts-control-board",
            "valid_until": ORDER_DATE,
        }
        self.assertEqual(deviation_findings(deviation, ORDER_DATE), [])

    def test_expired_deviation_reported(self):
        deviation = {
            "reference": "DEV-2026-019",
            "approval_authority": "parts-control-board",
            "valid_until": "2026-01-31",
        }
        findings = deviation_findings(deviation, ORDER_DATE)
        self.assertTrue(any("expired" in f for f in findings))

    def test_deviation_without_a_reference_reported(self):
        deviation = {"approval_authority": "parts-control-board"}
        findings = deviation_findings(deviation, ORDER_DATE)
        self.assertTrue(any("no reference" in f for f in findings))

    def test_deviation_without_an_authority_reported(self):
        deviation = {"reference": "DEV-2026-019"}
        findings = deviation_findings(deviation, ORDER_DATE)
        self.assertTrue(any("no approval authority" in f for f in findings))

    def test_absent_deviation_reported(self):
        findings = deviation_findings(None, ORDER_DATE)
        self.assertTrue(any("no deviation record" in f for f in findings))


class PartTypeTests(unittest.TestCase):
    def test_clean_part_type_is_compliant(self):
        index = index_baseline(_baseline())
        record = assess_part_type(_purchase(), index, ORDER_DATE)
        self.assertTrue(record["compliant"])
        self.assertTrue(record["in_baseline"])

    def test_part_type_outside_the_baseline_reported(self):
        index = index_baseline(_baseline())
        record = assess_part_type(_purchase(part_type="tantalum-capacitor"), index, ORDER_DATE)
        self.assertFalse(record["in_baseline"])
        self.assertTrue(any("no entry in the agreed baseline" in f for f in record["findings"]))

    def test_departure_without_a_deviation_reported(self):
        index = index_baseline(_baseline())
        record = assess_part_type(
            _purchase(offered_grade="industrial", departs_from_baseline=True), index, ORDER_DATE
        )
        self.assertGreaterEqual(len(record["findings"]), 2)

    def test_missing_purchase_key_refused(self):
        index = index_baseline(_baseline())
        purchase = _purchase()
        del purchase["supply"]
        with self.assertRaises(ValueError):
            assess_part_type(purchase, index, ORDER_DATE)

    def test_non_mapping_purchase_refused(self):
        index = index_baseline(_baseline())
        with self.assertRaises(ValueError):
            assess_part_type(["ceramic-capacitor-cdr-series"], index, ORDER_DATE)


class OrderTests(unittest.TestCase):
    def test_clean_order_meets_the_baseline(self):
        verdict = assess_procurement_order(_order())
        self.assertTrue(verdict["baseline_met"])
        self.assertEqual(verdict["findings"], [])
        self.assertAlmostEqual(verdict["compliant_fraction"], 1.0, places=9)

    def test_compliant_fraction_counts_only_clean_types(self):
        order = _order(
            baseline=_baseline() + [
                {
                    "part_type": "tantalum-capacitor-cwr-series",
                    "required_grade": "military",
                    "mission_low_c": -30.0,
                    "mission_high_c": 70.0,
                    "required_margin_c": 5.0,
                }
            ],
            purchases=[
                _purchase(),
                _purchase(part_type="tantalum-capacitor-cwr-series", offered_grade="commercial"),
            ],
        )
        verdict = assess_procurement_order(order)
        self.assertAlmostEqual(verdict["compliant_fraction"], 0.5, places=9)
        self.assertFalse(verdict["baseline_met"])

    def test_baseline_type_nobody_ordered_reported(self):
        order = _order(
            baseline=_baseline() + [
                {
                    "part_type": "tantalum-capacitor-cwr-series",
                    "required_grade": "military",
                    "mission_low_c": -30.0,
                    "mission_high_c": 70.0,
                    "required_margin_c": 5.0,
                }
            ]
        )
        verdict = assess_procurement_order(order)
        self.assertEqual(verdict["unordered_baseline_types"], ["tantalum-capacitor-cwr-series"])

    def test_part_type_purchased_twice_refused(self):
        with self.assertRaises(ValueError):
            assess_procurement_order(_order(purchases=[_purchase(), _purchase()]))

    def test_every_finding_is_carried_not_only_the_first(self):
        order = _order(
            purchases=[
                _purchase(
                    offered_grade="commercial",
                    part_low_c=-28.0,
                    supply={"route": "broker", "evidence": []},
                )
            ]
        )
        verdict = assess_procurement_order(order)
        self.assertGreaterEqual(len(verdict["findings"]), 4)

    def test_empty_purchase_list_refused(self):
        with self.assertRaises(ValueError):
            assess_procurement_order(_order(purchases=[]))

    def test_missing_order_key_refused(self):
        order = _order()
        del order["baseline"]
        with self.assertRaises(ValueError):
            assess_procurement_order(order)

    def test_non_mapping_order_refused(self):
        with self.assertRaises(ValueError):
            assess_procurement_order(["PO-2026-407"])

    def test_order_reference_and_date_echoed(self):
        verdict = assess_procurement_order(_order())
        self.assertEqual(verdict["order_reference"], "PO-2026-407")
        self.assertEqual(verdict["order_date"], ORDER_DATE)


if __name__ == "__main__":
    unittest.main()
