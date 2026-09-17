"""Contract tests for the clause 6.4 handling, packaging and storage logic."""

import unittest

from q60_class_3_handling_and_storage_logic import (
    ENVIRONMENT_COST_TENTHS,
    HANDLING_EVENT_WEIGHTS,
    MSL_FLOOR_LIFE_HOURS,
    PACKAGING_LAYER_ORDER,
    REQUIRED_LOT_FIELDS,
    STORAGE_VERDICTS,
    assess_handling_and_storage,
    bake_qualifies,
    exposure_cost_tenths,
    floor_life_budget,
    floor_life_hours,
    handling_event_score,
    packaging_findings,
    storage_verdict,
)


def lot(**overrides):
    record = {
        "lot_id": "LOT-A",
        "part_number": "rh1020-ccg84b",
        "moisture_sensitivity_level": 3,
        "exposure_log": [
            {"hours": 40, "environment": "controlled-cleanroom"},
            {"hours": 500, "environment": "sealed-dry-nitrogen"},
        ],
        "packaging_chain": list(PACKAGING_LAYER_ORDER),
        "handling_events": [],
        "bake": None,
        "bake_facility_available": True,
    }
    record.update(overrides)
    return record


class FloorLifeTests(unittest.TestCase):
    def test_a_moisture_sensitive_level_carries_a_budget(self):
        self.assertEqual(floor_life_hours(3), 168)

    def test_the_least_sensitive_level_carries_no_budget(self):
        self.assertIsNone(floor_life_hours(1))

    def test_a_higher_level_carries_a_smaller_budget(self):
        self.assertLess(floor_life_hours(5), floor_life_hours(4))

    def test_an_unknown_level_is_rejected(self):
        with self.assertRaises(ValueError):
            floor_life_hours(9)

    def test_a_boolean_level_is_rejected(self):
        with self.assertRaises(ValueError):
            floor_life_hours(True)

    def test_every_tabulated_level_answers(self):
        for level in MSL_FLOOR_LIFE_HOURS:
            floor_life_hours(level)


class ExposureCostTests(unittest.TestCase):
    def test_sealed_nitrogen_costs_nothing(self):
        self.assertEqual(
            exposure_cost_tenths([{"hours": 500, "environment": "sealed-dry-nitrogen"}]), 0
        )

    def test_a_cleanroom_hour_costs_a_whole_budget_hour(self):
        self.assertEqual(
            exposure_cost_tenths([{"hours": 10, "environment": "controlled-cleanroom"}]), 100
        )

    def test_a_bench_hour_costs_more_than_a_cleanroom_hour(self):
        self.assertGreater(
            ENVIRONMENT_COST_TENTHS["open-bench"],
            ENVIRONMENT_COST_TENTHS["controlled-cleanroom"],
        )

    def test_a_dry_cabinet_hour_costs_a_tenth(self):
        self.assertEqual(
            exposure_cost_tenths([{"hours": 100, "environment": "dry-cabinet"}]), 100
        )

    def test_intervals_add_up(self):
        self.assertEqual(
            exposure_cost_tenths(
                [
                    {"hours": 10, "environment": "controlled-cleanroom"},
                    {"hours": 5, "environment": "open-bench"},
                ]
            ),
            200,
        )

    def test_an_unknown_environment_is_rejected(self):
        with self.assertRaises(ValueError):
            exposure_cost_tenths([{"hours": 1, "environment": "the-loading-bay"}])

    def test_a_negative_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            exposure_cost_tenths([{"hours": -1, "environment": "open-bench"}])

    def test_an_interval_missing_its_environment_is_rejected(self):
        with self.assertRaises(ValueError):
            exposure_cost_tenths([{"hours": 4}])

    def test_an_empty_log_costs_nothing(self):
        self.assertEqual(exposure_cost_tenths([]), 0)


class BakeTests(unittest.TestCase):
    def test_a_full_bake_qualifies(self):
        self.assertTrue(bake_qualifies({"hours": 24, "temperature_c": 125}, 3)["qualifies"])

    def test_a_short_bake_does_not(self):
        result = bake_qualifies({"hours": 8, "temperature_c": 125}, 3)
        self.assertFalse(result["qualifies"])
        self.assertTrue(any("hours" in r for r in result["reasons"]))

    def test_a_cool_bake_does_not(self):
        result = bake_qualifies({"hours": 24, "temperature_c": 60}, 3)
        self.assertFalse(result["qualifies"])
        self.assertTrue(any("floor" in r for r in result["reasons"]))

    def test_no_bake_recorded_is_reported_as_such(self):
        self.assertEqual(bake_qualifies(None, 3)["reasons"], ("no bake recorded",))

    def test_a_level_with_no_budget_has_nothing_to_reset(self):
        self.assertFalse(bake_qualifies({"hours": 96, "temperature_c": 125}, 1)["qualifies"])

    def test_a_bake_missing_its_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            bake_qualifies({"hours": 24}, 3)

    def test_a_non_integer_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            bake_qualifies({"hours": 24, "temperature_c": "125"}, 3)


class BudgetTests(unittest.TestCase):
    def test_a_lot_inside_its_budget_reports_the_margin_left(self):
        budget = floor_life_budget(3, lot()["exposure_log"])
        self.assertTrue(budget["within_budget"])
        self.assertEqual(budget["remaining_hours_tenths"], 1280)
        self.assertAlmostEqual(budget["margin"], 1280 / 1680, places=9)

    def test_a_lot_exactly_on_its_budget_is_still_inside_it(self):
        budget = floor_life_budget(
            3, [{"hours": 168, "environment": "controlled-cleanroom"}]
        )
        self.assertTrue(budget["within_budget"])
        self.assertEqual(budget["remaining_hours_tenths"], 0)
        self.assertAlmostEqual(budget["margin"], 0.0, places=9)

    def test_a_lot_one_tenth_past_its_budget_is_outside_it(self):
        budget = floor_life_budget(
            3,
            [
                {"hours": 168, "environment": "controlled-cleanroom"},
                {"hours": 1, "environment": "dry-cabinet"},
            ],
        )
        self.assertFalse(budget["within_budget"])

    def test_a_qualifying_bake_resets_the_spend_rather_than_discounting_it(self):
        budget = floor_life_budget(
            3,
            [{"hours": 400, "environment": "open-bench"}],
            {"hours": 24, "temperature_c": 125},
        )
        self.assertTrue(budget["within_budget"])
        self.assertEqual(budget["spent_hours_tenths"], 0)
        self.assertTrue(budget["bake_reset"])

    def test_a_bake_that_does_not_qualify_resets_nothing(self):
        budget = floor_life_budget(
            3,
            [{"hours": 400, "environment": "open-bench"}],
            {"hours": 2, "temperature_c": 125},
        )
        self.assertFalse(budget["within_budget"])
        self.assertFalse(budget["bake_reset"])

    def test_a_level_with_no_budget_is_always_inside_it(self):
        budget = floor_life_budget(1, [{"hours": 9000, "environment": "open-bench"}])
        self.assertTrue(budget["within_budget"])
        self.assertIsNone(budget["budget_hours"])


class PackagingTests(unittest.TestCase):
    def test_a_complete_chain_reports_nothing(self):
        self.assertEqual(packaging_findings(list(PACKAGING_LAYER_ORDER), 3), ())

    def test_a_missing_barrier_bag_is_reported_for_a_sensitive_part(self):
        findings = packaging_findings(
            ["conductive-inner-carrier", "cushioned-transit-outer"], 3
        )
        self.assertTrue(any("moisture-barrier-bag" in note for note in findings))

    def test_the_least_sensitive_level_owes_no_barrier_bag(self):
        self.assertEqual(
            packaging_findings(
                ["conductive-inner-carrier", "cushioned-transit-outer"], 1
            ),
            (),
        )

    def test_a_missing_inner_carrier_is_reported(self):
        findings = packaging_findings(
            ["moisture-barrier-bag", "cushioned-transit-outer"], 3
        )
        self.assertTrue(any("conductive-inner-carrier" in note for note in findings))

    def test_layers_recorded_out_of_order_are_reported(self):
        findings = packaging_findings(
            [
                "moisture-barrier-bag",
                "conductive-inner-carrier",
                "cushioned-transit-outer",
            ],
            3,
        )
        self.assertTrue(any("out of order" in note for note in findings))

    def test_an_unknown_layer_is_rejected(self):
        with self.assertRaises(ValueError):
            packaging_findings(["bubble-wrap"], 3)

    def test_a_repeated_layer_is_rejected(self):
        with self.assertRaises(ValueError):
            packaging_findings(
                ["conductive-inner-carrier", "conductive-inner-carrier"], 3
            )


class HandlingLedgerTests(unittest.TestCase):
    def test_an_empty_ledger_scores_zero(self):
        ledger = handling_event_score([])
        self.assertEqual(ledger["score"], 0)
        self.assertFalse(ledger["severe"])

    def test_events_accumulate(self):
        ledger = handling_event_score(["ungrounded-handling", "unprotected-transfer"])
        self.assertEqual(ledger["score"], 7)

    def test_a_drop_is_severe_whatever_the_score(self):
        ledger = handling_event_score(["container-drop"])
        self.assertTrue(ledger["severe"])

    def test_an_unknown_event_is_rejected(self):
        with self.assertRaises(ValueError):
            handling_event_score(["left-in-the-van"])

    def test_every_tabulated_event_is_scorable(self):
        for name in HANDLING_EVENT_WEIGHTS:
            self.assertGreater(handling_event_score([name])["score"], 0)


class VerdictTests(unittest.TestCase):
    def test_a_clean_lot_is_fit_for_issue(self):
        self.assertEqual(storage_verdict(True, True, True, False, 0), "fit-for-issue")

    def test_an_over_budget_lot_with_an_oven_is_baked_first(self):
        self.assertEqual(storage_verdict(False, True, True, False, 0), "bake-before-use")

    def test_an_over_budget_lot_with_no_oven_is_quarantined(self):
        self.assertEqual(storage_verdict(False, False, True, False, 0), "quarantine")

    def test_a_broken_chain_sends_the_lot_back_to_packing(self):
        self.assertEqual(
            storage_verdict(True, True, False, False, 0), "repack-and-requalify"
        )

    def test_a_severe_event_outranks_everything_else(self):
        self.assertEqual(storage_verdict(True, True, True, True, 0), "quarantine")

    def test_a_score_over_the_limit_sends_the_lot_back_to_packing(self):
        self.assertEqual(
            storage_verdict(True, True, True, False, 9, 6), "repack-and-requalify"
        )

    def test_a_score_exactly_on_the_limit_is_still_fit(self):
        self.assertEqual(storage_verdict(True, True, True, False, 6, 6), "fit-for-issue")

    def test_every_verdict_returned_is_a_known_verdict(self):
        for within in (True, False):
            for oven in (True, False):
                for packing in (True, False):
                    for severe in (True, False):
                        self.assertIn(
                            storage_verdict(within, oven, packing, severe, 0),
                            STORAGE_VERDICTS,
                        )

    def test_a_non_boolean_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            storage_verdict(1, True, True, False, 0)


class AssessLotTests(unittest.TestCase):
    def test_a_well_kept_lot_is_fit_for_issue(self):
        result = assess_handling_and_storage(lot())
        self.assertEqual(result["verdict"], "fit-for-issue")
        self.assertTrue(result["fit_as_stored"])
        self.assertEqual(result["findings"], [])

    def test_nitrogen_time_does_not_count_against_the_lot(self):
        result = assess_handling_and_storage(lot())
        self.assertEqual(result["budget"]["spent_hours_tenths"], 400)

    def test_an_over_exposed_lot_is_sent_to_bake(self):
        result = assess_handling_and_storage(
            lot(exposure_log=[{"hours": 300, "environment": "open-bench"}])
        )
        self.assertEqual(result["verdict"], "bake-before-use")
        self.assertTrue(any("budget" in note for note in result["findings"]))

    def test_an_over_exposed_lot_with_no_oven_is_quarantined(self):
        result = assess_handling_and_storage(
            lot(
                exposure_log=[{"hours": 300, "environment": "open-bench"}],
                bake_facility_available=False,
            )
        )
        self.assertEqual(result["verdict"], "quarantine")

    def test_a_qualifying_bake_returns_an_over_exposed_lot_to_issue(self):
        result = assess_handling_and_storage(
            lot(
                exposure_log=[{"hours": 300, "environment": "open-bench"}],
                bake={"hours": 24, "temperature_c": 125},
            )
        )
        self.assertEqual(result["verdict"], "fit-for-issue")

    def test_a_short_bake_is_reported_and_does_not_rescue_the_lot(self):
        result = assess_handling_and_storage(
            lot(
                exposure_log=[{"hours": 300, "environment": "open-bench"}],
                bake={"hours": 3, "temperature_c": 125},
            )
        )
        self.assertEqual(result["verdict"], "bake-before-use")
        self.assertTrue(
            any("does not reset the budget" in note for note in result["findings"])
        )

    def test_a_broken_packaging_chain_is_reported(self):
        result = assess_handling_and_storage(
            lot(packaging_chain=["conductive-inner-carrier", "cushioned-transit-outer"])
        )
        self.assertEqual(result["verdict"], "repack-and-requalify")

    def test_a_dropped_container_quarantines_an_otherwise_clean_lot(self):
        result = assess_handling_and_storage(lot(handling_events=["container-drop"]))
        self.assertEqual(result["verdict"], "quarantine")
        self.assertTrue(any("severe handling" in note for note in result["findings"]))

    def test_accumulated_minor_events_cross_the_limit(self):
        result = assess_handling_and_storage(
            lot(
                handling_events=[
                    "ungrounded-handling",
                    "unprotected-transfer",
                    "desiccant-absent-at-reseal",
                ]
            )
        )
        self.assertEqual(result["verdict"], "repack-and-requalify")

    def test_every_required_lot_field_is_enforced(self):
        for field in REQUIRED_LOT_FIELDS:
            record = lot()
            record[field] = ""
            with self.assertRaises(ValueError):
                assess_handling_and_storage(record)

    def test_a_non_mapping_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_handling_and_storage(["LOT-A"])


if __name__ == "__main__":
    unittest.main()
