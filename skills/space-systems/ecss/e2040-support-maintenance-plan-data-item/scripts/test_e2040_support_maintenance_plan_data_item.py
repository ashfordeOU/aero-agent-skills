"""Contract tests for the Annex E support and maintenance plan data-item logic."""

import unittest

from e2040_support_maintenance_plan_data_item_logic import (
    MITIGATION_ALTERNATE_SOURCE,
    MITIGATION_LIFETIME_BUY,
    MITIGATION_MONITOR,
    REQUIRED_SECTIONS,
    RESPONSE_TOLERANCE_HOURS,
    assess_support_plan,
    ceil_with_tolerance,
    grade_commitment,
    grade_obsolescence_item,
    grade_upkeep_task,
    lifetime_buy_quantity,
    missing_sections,
    mitigation_category,
    unsupported_window_years,
    upkeep_occurrences,
    validate_commitment,
    validate_obsolescence_item,
    validate_service_life_months,
    validate_upkeep_task,
)

ALL_SECTIONS = list(REQUIRED_SECTIONS)


def item(identifier="P-1", ltb=2030.0, consumption=10.0, attrition=0.2, stock=0.0, storable=500):
    return {
        "id": identifier,
        "last_time_buy_year": ltb,
        "annual_consumption": consumption,
        "attrition_fraction": attrition,
        "stock_on_hand": stock,
        "storable_quantity": storable,
    }


class SectionTests(unittest.TestCase):
    def test_complete_section_list_has_no_gap(self):
        self.assertEqual(missing_sections(ALL_SECTIONS), [])

    def test_absent_obsolescence_section_is_named(self):
        partial = [s for s in ALL_SECTIONS if s != "obsolescence-management"]
        self.assertEqual(missing_sections(partial), ["obsolescence-management"])

    def test_section_match_ignores_case_and_padding(self):
        self.assertEqual(missing_sections([" " + s.upper() + " " for s in ALL_SECTIONS]), [])

    def test_non_sequence_section_list_rejected(self):
        with self.assertRaises(ValueError):
            missing_sections(None)


class ServiceLifeTests(unittest.TestCase):
    def test_positive_life_accepted(self):
        self.assertAlmostEqual(validate_service_life_months(120), 120.0)

    def test_zero_life_rejected(self):
        with self.assertRaises(ValueError):
            validate_service_life_months(0)

    def test_negative_life_rejected(self):
        with self.assertRaises(ValueError):
            validate_service_life_months(-12)

    def test_non_numeric_life_rejected(self):
        with self.assertRaises(ValueError):
            validate_service_life_months("120")


class CommitmentTests(unittest.TestCase):
    def test_faster_offer_meets_the_contract(self):
        record = grade_commitment(
            {"id": "SC-1", "offered_response_hours": 8.0, "contracted_response_hours": 24.0}
        )
        self.assertTrue(record["met"])
        self.assertAlmostEqual(record["shortfall_hours"], 0.0)

    def test_equal_offer_meets_the_contract_within_tolerance(self):
        record = grade_commitment(
            {"id": "SC-1", "offered_response_hours": 24.0, "contracted_response_hours": 24.0}
        )
        self.assertTrue(record["met"])
        self.assertLessEqual(
            abs(record["offered_response_hours"] - record["contracted_response_hours"]),
            RESPONSE_TOLERANCE_HOURS,
        )

    def test_slower_offer_reports_the_shortfall(self):
        record = grade_commitment(
            {"id": "SC-1", "offered_response_hours": 36.0, "contracted_response_hours": 24.0}
        )
        self.assertFalse(record["met"])
        self.assertAlmostEqual(record["shortfall_hours"], 12.0, places=9)

    def test_zero_offered_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_commitment(
                {"id": "SC-1", "offered_response_hours": 0.0, "contracted_response_hours": 24.0}
            )

    def test_missing_contracted_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_commitment({"id": "SC-1", "offered_response_hours": 24.0})


class UpkeepTests(unittest.TestCase):
    def test_interval_fits_a_whole_number_of_times(self):
        self.assertEqual(upkeep_occurrences(72.0, 24.0), 3)

    def test_partial_interval_does_not_count(self):
        self.assertEqual(upkeep_occurrences(72.0, 30.0), 2)

    def test_interval_longer_than_the_life_never_falls_due(self):
        self.assertEqual(upkeep_occurrences(24.0, 36.0), 0)

    def test_exact_division_is_not_lost_to_representation(self):
        self.assertEqual(upkeep_occurrences(0.3, 0.1), 3)

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            upkeep_occurrences(72.0, 0.0)

    def test_declared_count_matching_the_interval_is_consistent(self):
        record = grade_upkeep_task(
            {"id": "UK-1", "interval_months": 24.0, "declared_occurrences": 3}, 72.0
        )
        self.assertTrue(record["consistent"])
        self.assertEqual(record["computed_occurrences"], 3)

    def test_declared_count_disagreeing_with_the_interval_is_flagged(self):
        record = grade_upkeep_task(
            {"id": "UK-1", "interval_months": 30.0, "declared_occurrences": 3}, 72.0
        )
        self.assertFalse(record["consistent"])

    def test_non_integer_declared_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_upkeep_task(
                {"id": "UK-1", "interval_months": 24.0, "declared_occurrences": 2.4}
            )


class ObsolescenceTests(unittest.TestCase):
    def test_window_is_the_gap_to_the_end_of_life(self):
        self.assertAlmostEqual(unsupported_window_years(2030.0, 2035.0), 5.0, places=9)

    def test_part_supported_past_end_of_life_has_no_window(self):
        self.assertAlmostEqual(unsupported_window_years(2040.0, 2035.0), 0.0)

    def test_last_time_buy_on_the_end_date_has_no_window(self):
        self.assertAlmostEqual(unsupported_window_years(2035.0, 2035.0), 0.0)

    def test_tolerant_ceiling_keeps_a_near_integer(self):
        self.assertEqual(ceil_with_tolerance(60.0000000001), 60)

    def test_tolerant_ceiling_still_rounds_a_real_fraction_up(self):
        self.assertEqual(ceil_with_tolerance(60.4), 61)

    def test_lifetime_buy_grosses_up_for_attrition(self):
        self.assertEqual(lifetime_buy_quantity(10.0, 5.0, 0.2, 0.0), 60)

    def test_stock_on_hand_reduces_the_buy(self):
        self.assertEqual(lifetime_buy_quantity(10.0, 5.0, 0.2, 20.0), 40)

    def test_stock_covering_demand_gives_no_buy(self):
        self.assertEqual(lifetime_buy_quantity(10.0, 5.0, 0.2, 100.0), 0)

    def test_attrition_at_or_above_one_rejected(self):
        with self.assertRaises(ValueError):
            lifetime_buy_quantity(10.0, 5.0, 1.0, 0.0)

    def test_negative_stock_rejected(self):
        with self.assertRaises(ValueError):
            lifetime_buy_quantity(10.0, 5.0, 0.2, -1.0)

    def test_no_window_is_monitor_only(self):
        self.assertEqual(mitigation_category(0.0, 0, 100), MITIGATION_MONITOR)

    def test_buy_inside_the_storable_quantity_is_a_lifetime_buy(self):
        self.assertEqual(mitigation_category(5.0, 60, 100), MITIGATION_LIFETIME_BUY)

    def test_buy_above_the_storable_quantity_needs_another_source(self):
        self.assertEqual(mitigation_category(5.0, 600, 100), MITIGATION_ALTERNATE_SOURCE)

    def test_buy_exactly_at_the_storable_quantity_is_still_a_lifetime_buy(self):
        self.assertEqual(mitigation_category(5.0, 100, 100), MITIGATION_LIFETIME_BUY)

    def test_non_integer_storable_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_obsolescence_item(item(storable=100.5))

    def test_graded_item_carries_window_quantity_and_category(self):
        record = grade_obsolescence_item(item(), 2035.0)
        self.assertAlmostEqual(record["unsupported_window_years"], 5.0, places=9)
        self.assertEqual(record["lifetime_buy_quantity"], 60)
        self.assertEqual(record["mitigation"], MITIGATION_LIFETIME_BUY)


class AssessmentTests(unittest.TestCase):
    def _plan(self, **overrides):
        plan = {
            "sections": list(ALL_SECTIONS),
            "service_life_months": 72.0,
            "service_life_end_year": 2035.0,
            "commitments": [
                {"id": "SC-1", "offered_response_hours": 24.0, "contracted_response_hours": 24.0}
            ],
            "upkeep_tasks": [
                {"id": "UK-1", "interval_months": 24.0, "declared_occurrences": 3}
            ],
            "obsolescence_items": [item()],
        }
        plan.update(overrides)
        return plan

    def test_complete_plan_is_compliant(self):
        result = assess_support_plan(self._plan())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_total_lifetime_buy_is_summed(self):
        result = assess_support_plan(
            self._plan(obsolescence_items=[item("P-1"), item("P-2", consumption=5.0)])
        )
        self.assertEqual(result["total_lifetime_buy_units"], 90)

    def test_slow_commitment_is_a_finding(self):
        result = assess_support_plan(
            self._plan(
                commitments=[
                    {
                        "id": "SC-1",
                        "offered_response_hours": 48.0,
                        "contracted_response_hours": 24.0,
                    }
                ]
            )
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("later than contracted" in f for f in result["findings"]))

    def test_interval_mismatch_is_a_finding(self):
        result = assess_support_plan(
            self._plan(
                upkeep_tasks=[{"id": "UK-1", "interval_months": 30.0, "declared_occurrences": 3}]
            )
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("occurrences" in f for f in result["findings"]))

    def test_unbuyable_part_is_a_finding(self):
        result = assess_support_plan(
            self._plan(obsolescence_items=[item(consumption=400.0, storable=100)])
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(result["obsolescence_items"][0]["mitigation"], MITIGATION_ALTERNATE_SOURCE)

    def test_absent_section_is_a_finding(self):
        sections = [s for s in ALL_SECTIONS if s != "spares-and-logistics"]
        result = assess_support_plan(self._plan(sections=sections))
        self.assertEqual(result["missing_sections"], ["spares-and-logistics"])
        self.assertFalse(result["compliant"])

    def test_missing_plan_key_rejected(self):
        plan = self._plan()
        del plan["upkeep_tasks"]
        with self.assertRaises(ValueError):
            assess_support_plan(plan)

    def test_non_sequence_commitment_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_support_plan(self._plan(commitments="SC-1"))

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            assess_support_plan("plan")


if __name__ == "__main__":
    unittest.main()
