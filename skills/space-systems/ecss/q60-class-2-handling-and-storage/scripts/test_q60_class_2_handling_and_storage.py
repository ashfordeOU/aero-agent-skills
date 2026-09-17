"""Contract tests for the clause 5.4 Class 2 handling and storage logic."""

import unittest

from q60_class_2_handling_and_storage_logic import (
    DEFAULT_OPEN_AIR_BUDGET_MINUTES,
    DEFAULT_STORE_LIMITS,
    LOCATION_PROTECTION_LEVEL,
    OPEN_AIR_WARNING_FRACTION,
    PROTECTION_MEASURES,
    REINSPECTION_INTERVAL_MONTHS,
    assess_handling_chain,
    environment_margins,
    esd_band,
    grade_custody_chain,
    grade_leg,
    location_protection_level,
    open_air_budget_state,
    reinspection_due,
    required_protection_measures,
)


class EsdBandTests(unittest.TestCase):
    def test_a_fragile_part_lands_in_the_most_sensitive_band(self):
        self.assertEqual(esd_band(150.0)["band"], "esd-very-sensitive")

    def test_the_most_sensitive_band_owes_the_highest_level(self):
        self.assertEqual(esd_band(150.0)["required_level"], 3)

    def test_a_part_exactly_on_a_band_edge_stays_in_the_lower_band(self):
        self.assertEqual(esd_band(250.0)["band"], "esd-very-sensitive")

    def test_a_mid_range_part_owes_level_two(self):
        self.assertEqual(esd_band(500.0)["required_level"], 2)

    def test_a_part_on_the_upper_band_edge_still_owes_level_two(self):
        self.assertEqual(esd_band(1000.0)["required_level"], 2)

    def test_a_robust_part_owes_level_one(self):
        self.assertEqual(esd_band(4000.0)["required_level"], 1)

    def test_a_non_positive_withstand_refused(self):
        with self.assertRaises(ValueError):
            esd_band(0.0)

    def test_a_non_numeric_withstand_refused(self):
        with self.assertRaises(ValueError):
            esd_band("2 kV")


class ProtectionMeasureTests(unittest.TestCase):
    def test_every_level_owes_a_shielding_bag(self):
        for level in PROTECTION_MEASURES:
            self.assertIn("static-shielding-bag", required_protection_measures(level))

    def test_levels_are_cumulative(self):
        self.assertTrue(
            set(required_protection_measures(2)).issubset(
                set(required_protection_measures(3))
            )
        )

    def test_the_highest_level_owes_ionization(self):
        self.assertIn("air-ionizer", required_protection_measures(3))

    def test_the_lowest_level_owes_no_wrist_strap(self):
        self.assertNotIn("grounded-wrist-strap", required_protection_measures(1))

    def test_an_unregistered_level_refused(self):
        with self.assertRaises(ValueError):
            required_protection_measures(9)


class LocationTests(unittest.TestCase):
    def test_a_bonded_store_holds_the_highest_level(self):
        self.assertEqual(location_protection_level("bonded-store"), 3)

    def test_an_open_bench_holds_nothing(self):
        self.assertEqual(location_protection_level("open-bench"), 0)

    def test_a_location_token_is_normalized(self):
        self.assertEqual(location_protection_level(" Kitting-Cell "), 2)

    def test_an_ungraded_location_refused(self):
        with self.assertRaises(ValueError):
            location_protection_level("the-corridor")

    def test_the_register_carries_the_common_locations(self):
        self.assertIn("bonded-store", LOCATION_PROTECTION_LEVEL)
        self.assertIn("kitting-cell", LOCATION_PROTECTION_LEVEL)


class LegGradingTests(unittest.TestCase):
    def test_a_protected_leg_has_no_shortfall(self):
        leg = grade_leg({"location": "bonded-store", "open_air_minutes": 0.0}, 3)
        self.assertEqual(leg["shortfall"], 0)

    def test_a_one_level_shortfall_is_reported(self):
        leg = grade_leg({"location": "kitting-cell", "open_air_minutes": 10.0}, 3)
        self.assertEqual(leg["shortfall"], 1)

    def test_an_open_bench_is_a_deep_shortfall(self):
        leg = grade_leg({"location": "open-bench", "open_air_minutes": 10.0}, 3)
        self.assertEqual(leg["shortfall"], 3)

    def test_dry_storage_minutes_do_not_spend_the_budget(self):
        leg = grade_leg(
            {
                "location": "bonded-store",
                "open_air_minutes": 5000.0,
                "dry_storage": True,
            },
            2,
        )
        self.assertAlmostEqual(leg["open_air_minutes"], 0.0, places=9)

    def test_open_minutes_are_carried_through(self):
        leg = grade_leg({"location": "kitting-cell", "open_air_minutes": 42.0}, 2)
        self.assertAlmostEqual(leg["open_air_minutes"], 42.0, places=9)

    def test_a_leg_missing_a_key_refused(self):
        with self.assertRaises(ValueError):
            grade_leg({"location": "bonded-store"}, 2)

    def test_negative_open_minutes_refused(self):
        with self.assertRaises(ValueError):
            grade_leg({"location": "bonded-store", "open_air_minutes": -1.0}, 2)


class ChainGradingTests(unittest.TestCase):
    CHAIN = (
        {"location": "sealed-transport-container", "open_air_minutes": 0.0},
        {"location": "bonded-store", "open_air_minutes": 900.0, "dry_storage": True},
        {"location": "kitting-cell", "open_air_minutes": 60.0},
        {"location": "protected-assembly-area", "open_air_minutes": 45.0},
    )

    def test_a_protected_chain_has_no_shortfall(self):
        chain = grade_custody_chain(self.CHAIN, 2)
        self.assertEqual(chain["worst_shortfall"], 0)

    def test_one_open_bench_sets_the_worst_shortfall(self):
        chain = grade_custody_chain(
            list(self.CHAIN) + [{"location": "open-bench", "open_air_minutes": 5.0}], 2
        )
        self.assertEqual(chain["worst_shortfall"], 2)
        self.assertEqual(chain["weakest_leg"]["location"], "open-bench")

    def test_the_weakest_leg_is_named_not_averaged(self):
        chain = grade_custody_chain(
            list(self.CHAIN)
            + [{"location": "goods-inwards-counter", "open_air_minutes": 5.0}],
            2,
        )
        self.assertIn("goods-inwards-counter", chain["legs_below_requirement"])

    def test_open_minutes_accumulate_across_the_chain(self):
        chain = grade_custody_chain(self.CHAIN, 2)
        self.assertAlmostEqual(chain["open_air_minutes"], 105.0, places=9)

    def test_every_leg_is_sequenced(self):
        chain = grade_custody_chain(self.CHAIN, 2)
        self.assertEqual([leg["sequence"] for leg in chain["legs"]], [0, 1, 2, 3])

    def test_an_empty_chain_refused(self):
        with self.assertRaises(ValueError):
            grade_custody_chain([], 2)


class BudgetTests(unittest.TestCase):
    def test_a_half_spent_budget_is_reported_as_a_fraction(self):
        state = open_air_budget_state(240.0, 480.0)
        self.assertAlmostEqual(state["fraction_consumed"], 0.5, places=9)

    def test_a_half_spent_budget_is_not_near_exhaustion(self):
        self.assertFalse(open_air_budget_state(240.0, 480.0)["near_exhaustion"])

    def test_a_budget_exactly_spent_is_not_yet_exhausted(self):
        state = open_air_budget_state(480.0, 480.0)
        self.assertFalse(state["exhausted"])
        self.assertTrue(state["near_exhaustion"])

    def test_a_budget_overspent_is_exhausted(self):
        self.assertTrue(open_air_budget_state(600.0, 480.0)["exhausted"])

    def test_remaining_minutes_are_reported(self):
        state = open_air_budget_state(180.0, 480.0)
        self.assertAlmostEqual(state["remaining_minutes"], 300.0, places=9)

    def test_the_warning_fraction_is_below_the_budget(self):
        self.assertLess(OPEN_AIR_WARNING_FRACTION, 1.0)

    def test_the_default_budget_is_positive(self):
        self.assertGreater(DEFAULT_OPEN_AIR_BUDGET_MINUTES, 0.0)

    def test_a_warning_fraction_above_the_budget_refused(self):
        with self.assertRaises(ValueError):
            open_air_budget_state(10.0, 480.0, 1.5)

    def test_a_zero_budget_refused(self):
        with self.assertRaises(ValueError):
            open_air_budget_state(10.0, 0.0)


class EnvironmentTests(unittest.TestCase):
    def test_the_middle_of_the_band_is_a_full_margin(self):
        out = environment_margins(20.0, 30.0)
        self.assertAlmostEqual(out["temperature_margin"], 1.0, places=9)

    def test_a_reading_exactly_on_a_temperature_limit_has_no_margin(self):
        out = environment_margins(30.0, 30.0)
        self.assertAlmostEqual(out["temperature_margin"], 0.0, places=9)

    def test_a_reading_exactly_on_a_limit_is_still_within_limits(self):
        self.assertTrue(environment_margins(30.0, 30.0)["within_limits"])

    def test_a_reading_over_a_temperature_limit_is_outside(self):
        out = environment_margins(35.0, 30.0)
        self.assertFalse(out["within_limits"])

    def test_the_humidity_margin_is_a_share_of_its_limit(self):
        out = environment_margins(20.0, 30.0)
        self.assertAlmostEqual(out["humidity_margin"], 0.5, places=9)

    def test_humidity_exactly_on_its_limit_is_within_limits(self):
        self.assertTrue(environment_margins(20.0, 60.0)["within_limits"])

    def test_humidity_over_its_limit_is_outside(self):
        self.assertFalse(environment_margins(20.0, 75.0)["within_limits"])

    def test_inverted_temperature_limits_refused(self):
        with self.assertRaises(ValueError):
            environment_margins(
                20.0,
                30.0,
                {
                    "temperature_min_c": 30.0,
                    "temperature_max_c": 10.0,
                    "humidity_max_pct": 60.0,
                },
            )

    def test_limits_missing_a_key_refused(self):
        with self.assertRaises(ValueError):
            environment_margins(20.0, 30.0, {"temperature_min_c": 10.0})

    def test_the_default_limits_carry_all_three_bounds(self):
        self.assertEqual(len(DEFAULT_STORE_LIMITS), 3)


class ReinspectionTests(unittest.TestCase):
    def test_a_recently_inspected_lot_is_not_due(self):
        self.assertFalse(reinspection_due(6.0))

    def test_a_lot_exactly_on_its_interval_is_due(self):
        self.assertTrue(reinspection_due(REINSPECTION_INTERVAL_MONTHS))

    def test_an_overdue_lot_is_due(self):
        self.assertTrue(reinspection_due(30.0))

    def test_a_negative_interval_since_inspection_refused(self):
        with self.assertRaises(ValueError):
            reinspection_due(-1.0)

    def test_a_zero_interval_refused(self):
        with self.assertRaises(ValueError):
            reinspection_due(6.0, 0.0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "withstand_volts": 500.0,
            "custody_legs": [
                {"location": "sealed-transport-container", "open_air_minutes": 0.0},
                {
                    "location": "bonded-store",
                    "open_air_minutes": 900.0,
                    "dry_storage": True,
                },
                {"location": "kitting-cell", "open_air_minutes": 60.0},
                {"location": "protected-assembly-area", "open_air_minutes": 45.0},
            ],
            "store_temperature_c": 20.0,
            "store_humidity_pct": 40.0,
            "months_since_inspection": 6.0,
        }
        spec.update(overrides)
        return spec

    def test_a_clean_chain_is_fit_for_issue(self):
        out = assess_handling_chain(self._spec())
        self.assertEqual(out["disposition"], "fit-for-issue")

    def test_the_owed_measures_follow_the_band(self):
        out = assess_handling_chain(self._spec())
        self.assertIn("grounded-wrist-strap", out["owed_measures"])

    def test_a_deep_protection_shortfall_quarantines_the_lot(self):
        spec = self._spec()
        spec["custody_legs"].append(
            {"location": "open-bench", "open_air_minutes": 5.0}
        )
        out = assess_handling_chain(spec)
        self.assertEqual(out["disposition"], "quarantine-for-reconditioning")

    def test_a_one_level_shortfall_earns_actions(self):
        spec = self._spec()
        spec["custody_legs"].append(
            {"location": "goods-inwards-counter", "open_air_minutes": 5.0}
        )
        out = assess_handling_chain(spec)
        self.assertEqual(out["disposition"], "issue-with-actions")

    def test_a_robust_part_tolerates_a_lighter_location(self):
        spec = self._spec(withstand_volts=4000.0)
        spec["custody_legs"].append(
            {"location": "goods-inwards-counter", "open_air_minutes": 5.0}
        )
        out = assess_handling_chain(spec)
        self.assertEqual(out["disposition"], "fit-for-issue")

    def test_an_overspent_open_air_budget_quarantines_the_lot(self):
        out = assess_handling_chain(self._spec(open_air_budget_minutes=100.0))
        self.assertEqual(out["disposition"], "quarantine-for-reconditioning")

    def test_a_nearly_spent_open_air_budget_earns_actions(self):
        out = assess_handling_chain(self._spec(open_air_budget_minutes=120.0))
        self.assertEqual(out["disposition"], "issue-with-actions")

    def test_dry_storage_time_never_reaches_the_budget(self):
        out = assess_handling_chain(self._spec())
        self.assertAlmostEqual(
            out["open_air_budget"]["consumed_minutes"], 105.0, places=9
        )

    def test_an_out_of_limit_store_quarantines_the_lot(self):
        out = assess_handling_chain(self._spec(store_humidity_pct=80.0))
        self.assertEqual(out["disposition"], "quarantine-for-reconditioning")

    def test_a_store_exactly_on_its_humidity_limit_stays_fit(self):
        out = assess_handling_chain(self._spec(store_humidity_pct=60.0))
        self.assertEqual(out["disposition"], "fit-for-issue")

    def test_a_due_reinspection_earns_actions(self):
        out = assess_handling_chain(self._spec(months_since_inspection=30.0))
        self.assertEqual(out["disposition"], "issue-with-actions")

    def test_a_quarantine_finding_outranks_an_action_finding(self):
        out = assess_handling_chain(
            self._spec(store_humidity_pct=80.0, months_since_inspection=30.0)
        )
        self.assertEqual(out["disposition"], "quarantine-for-reconditioning")

    def test_the_margins_are_reported_alongside_the_verdict(self):
        out = assess_handling_chain(self._spec())
        self.assertAlmostEqual(
            out["store_environment"]["humidity_margin"], 1.0 / 3.0, places=9
        )

    def test_missing_required_key_refused(self):
        spec = self._spec()
        del spec["store_humidity_pct"]
        with self.assertRaises(ValueError):
            assess_handling_chain(spec)

    def test_non_mapping_spec_refused(self):
        with self.assertRaises(ValueError):
            assess_handling_chain(["withstand_volts"])

    def test_an_ungraded_location_refused_in_the_assessment(self):
        spec = self._spec()
        spec["custody_legs"].append(
            {"location": "the-corridor", "open_air_minutes": 5.0}
        )
        with self.assertRaises(ValueError):
            assess_handling_chain(spec)

    def test_every_disposition_carries_reasons(self):
        out = assess_handling_chain(self._spec())
        self.assertTrue(out["reasons"])


if __name__ == "__main__":
    unittest.main()
