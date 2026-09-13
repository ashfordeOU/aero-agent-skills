#!/usr/bin/env python3
"""Gate 3 contract test for e2006-secondary-arc-description."""

import math
import unittest

import e2006_secondary_arc_description_logic as logic


class ArcFamilyTests(unittest.TestCase):
    def test_non_sustained_note_mentions_self_extinction(self):
        self.assertIn("stops on its own", logic.arc_category_note("non-sustained"))

    def test_temporary_sustained_note_mentions_the_generator(self):
        self.assertIn("generator", logic.arc_category_note("temporary-sustained"))

    def test_permanent_sustained_note_mentions_disconnection(self):
        self.assertIn("disconnected", logic.arc_category_note("permanent-sustained"))

    def test_unknown_family_note_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.arc_category_note("intermittent")

    def test_every_family_carries_a_note(self):
        for family in logic.ARC_CATEGORIES:
            self.assertTrue(logic.arc_category_note(family))

    def test_self_extinction_is_a_self_termination(self):
        self.assertEqual(logic.termination_kind("self-extinction"), "self")

    def test_string_disconnection_is_an_external_termination(self):
        self.assertEqual(logic.termination_kind("string-disconnection"), "external")

    def test_unknown_termination_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.termination_kind("faded-away")

    def test_non_string_termination_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.termination_kind(0)

    def test_sustained_flag_is_false_for_a_flashover(self):
        self.assertFalse(logic.is_sustained("non-sustained"))

    def test_sustained_flag_is_true_for_a_temporary_arc(self):
        self.assertTrue(logic.is_sustained("temporary-sustained"))

    def test_sustained_flag_is_true_for_a_permanent_arc(self):
        self.assertTrue(logic.is_sustained("permanent-sustained"))

    def test_sustained_flag_rejects_an_unknown_family(self):
        with self.assertRaises(ValueError):
            logic.is_sustained("secondary")


class EventCategorisationTests(unittest.TestCase):
    def test_short_self_terminated_event_is_a_flashover(self):
        self.assertEqual(
            logic.categorize_arc_event(
                {"duration_s": 5.0e-4, "terminated_by": "self-extinction"}
            ),
            "non-sustained",
        )

    def test_event_exactly_at_the_flashover_bound_is_a_flashover(self):
        self.assertEqual(
            logic.categorize_arc_event(
                {"duration_s": 1.0e-3, "terminated_by": "self-extinction"}
            ),
            "non-sustained",
        )

    def test_event_a_few_ulps_over_the_bound_is_still_a_flashover(self):
        duration = 1.0e-3 * (1.0 + 1.0e-15)
        self.assertEqual(
            logic.categorize_arc_event(
                {"duration_s": duration, "terminated_by": "self-extinction"}
            ),
            "non-sustained",
        )

    def test_longer_self_terminated_event_is_temporary_sustained(self):
        self.assertEqual(
            logic.categorize_arc_event(
                {"duration_s": 0.4, "terminated_by": "self-extinction"}
            ),
            "temporary-sustained",
        )

    def test_event_ended_by_string_disconnection_is_permanent(self):
        self.assertEqual(
            logic.categorize_arc_event(
                {"duration_s": 12.0, "terminated_by": "string-disconnection"}
            ),
            "permanent-sustained",
        )

    def test_event_ended_by_bus_power_removal_is_permanent(self):
        self.assertEqual(
            logic.categorize_arc_event(
                {"duration_s": 3.0, "terminated_by": "bus-power-removal"}
            ),
            "permanent-sustained",
        )

    def test_event_still_arcing_at_record_end_is_permanent(self):
        self.assertEqual(
            logic.categorize_arc_event(
                {"duration_s": 30.0, "terminated_by": "still-arcing-at-record-end"}
            ),
            "permanent-sustained",
        )

    def test_short_externally_terminated_event_is_still_permanent(self):
        self.assertEqual(
            logic.categorize_arc_event(
                {"duration_s": 2.0e-4, "terminated_by": "string-disconnection"}
            ),
            "permanent-sustained",
        )

    def test_event_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.categorize_arc_event(["self-extinction", 1.0])

    def test_event_without_a_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_arc_event({"terminated_by": "self-extinction"})

    def test_event_without_a_termination_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_arc_event({"duration_s": 1.0e-4})

    def test_zero_duration_event_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_arc_event(
                {"duration_s": 0.0, "terminated_by": "self-extinction"}
            )

    def test_non_numeric_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_arc_event(
                {"duration_s": "1 ms", "terminated_by": "self-extinction"}
            )

    def test_unknown_termination_in_an_event_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_arc_event(
                {"duration_s": 1.0, "terminated_by": "operator-stopped-looking"}
            )


class SustainingThresholdTests(unittest.TestCase):
    def test_threshold_at_a_tabulated_current(self):
        self.assertAlmostEqual(logic.sustaining_threshold_voltage(0.5), 80.0, places=9)

    def test_threshold_at_the_one_ampere_point(self):
        self.assertAlmostEqual(logic.sustaining_threshold_voltage(1.0), 60.0, places=9)

    def test_log_interpolation_between_tabulated_points(self):
        midpoint = math.sqrt(0.1 * 0.25)
        self.assertAlmostEqual(
            logic.sustaining_threshold_voltage(midpoint), 114.0175425117, places=8
        )

    def test_threshold_falls_as_string_current_rises(self):
        currents = (0.12, 0.3, 0.7, 1.5, 3.0)
        voltages = [logic.sustaining_threshold_voltage(c) for c in currents]
        self.assertEqual(voltages, sorted(voltages, reverse=True))

    def test_current_below_the_table_cannot_sustain_an_arc(self):
        self.assertEqual(logic.sustaining_threshold_voltage(0.05), math.inf)

    def test_current_exactly_at_the_table_floor_is_tabulated(self):
        self.assertAlmostEqual(logic.sustaining_threshold_voltage(0.1), 130.0, places=9)

    def test_current_a_few_ulps_below_the_floor_is_absorbed(self):
        current = 0.1 * (1.0 - 1.0e-15)
        self.assertAlmostEqual(
            logic.sustaining_threshold_voltage(current), 130.0, places=6
        )

    def test_current_above_the_table_holds_the_floor_voltage(self):
        self.assertAlmostEqual(logic.sustaining_threshold_voltage(10.0), 35.0, places=9)

    def test_current_exactly_at_the_table_ceiling_holds_the_floor_voltage(self):
        self.assertAlmostEqual(logic.sustaining_threshold_voltage(4.0), 35.0, places=9)

    def test_non_positive_current_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.sustaining_threshold_voltage(0.0)

    def test_non_numeric_current_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.sustaining_threshold_voltage("1 A")

    def test_boolean_current_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.sustaining_threshold_voltage(True)


class SiteThresholdTests(unittest.TestCase):
    def test_reference_gap_leaves_the_threshold_unchanged(self):
        self.assertAlmostEqual(
            logic.site_threshold_voltage(1.0, 1.0, "pristine"), 60.0, places=9
        )

    def test_wider_gap_raises_the_threshold(self):
        self.assertAlmostEqual(
            logic.site_threshold_voltage(1.0, 4.0, "pristine"), 120.0, places=9
        )

    def test_gap_correction_is_capped(self):
        self.assertAlmostEqual(
            logic.site_threshold_voltage(1.0, 100.0, "pristine"), 180.0, places=9
        )

    def test_contamination_lowers_the_threshold(self):
        self.assertAlmostEqual(
            logic.site_threshold_voltage(1.0, 1.0, "contaminated"), 51.0, places=9
        )

    def test_a_carbonized_track_lowers_the_threshold_further(self):
        self.assertAlmostEqual(
            logic.site_threshold_voltage(1.0, 1.0, "carbonized-track"), 36.0, places=9
        )

    def test_unknown_site_condition_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.site_threshold_voltage(1.0, 1.0, "wet")

    def test_non_positive_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.site_threshold_voltage(1.0, 0.0, "pristine")

    def test_unsustainable_current_stays_unbounded_at_any_gap(self):
        self.assertEqual(logic.site_threshold_voltage(0.01, 5.0, "pristine"), math.inf)


class ApplicabilityTests(unittest.TestCase):
    def test_exposed_array_gap_is_covered(self):
        result = logic.provisions_apply("cell-to-cell-gap", True, 100.0, 1.0)
        self.assertTrue(result["applies"])
        self.assertEqual(result["reason"], "clause-7-provisions-apply")

    def test_encapsulated_harness_is_outside_the_provisions(self):
        result = logic.provisions_apply("encapsulated-harness", True, 100.0, 1.0)
        self.assertFalse(result["applies"])
        self.assertEqual(result["reason"], "site-is-not-an-array-surface")

    def test_equipment_interior_is_outside_the_provisions(self):
        result = logic.provisions_apply("internal-power-electronics", True, 100.0, 1.0)
        self.assertFalse(result["applies"])

    def test_site_without_plasma_access_is_outside_the_provisions(self):
        result = logic.provisions_apply("cell-interconnect", False, 100.0, 1.0)
        self.assertFalse(result["applies"])
        self.assertEqual(
            result["reason"], "no-plasma-access-to-trigger-a-primary-event"
        )

    def test_string_too_weak_to_feed_an_arc_is_outside_the_provisions(self):
        result = logic.provisions_apply("string-to-string-gap", True, 100.0, 0.01)
        self.assertFalse(result["applies"])
        self.assertEqual(result["reason"], "string-current-cannot-feed-an-arc")

    def test_potential_below_the_arc_floor_is_outside_the_provisions(self):
        result = logic.provisions_apply("string-to-string-gap", True, 20.0, 1.0)
        self.assertFalse(result["applies"])
        self.assertEqual(
            result["reason"], "differential-potential-below-the-arc-floor"
        )

    def test_potential_exactly_at_the_arc_floor_is_covered(self):
        result = logic.provisions_apply("string-to-string-gap", True, 35.0, 1.0)
        self.assertTrue(result["applies"])

    def test_unknown_array_location_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.provisions_apply("radiator-panel", True, 100.0, 1.0)

    def test_non_boolean_plasma_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.provisions_apply("cell-to-cell-gap", "yes", 100.0, 1.0)

    def test_non_positive_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.provisions_apply("cell-to-cell-gap", True, 0.0, 1.0)

    def test_non_positive_string_current_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.provisions_apply("cell-to-cell-gap", True, 100.0, -1.0)


class FlashoverEnergyTests(unittest.TestCase):
    def test_capacitive_energy_value(self):
        self.assertAlmostEqual(
            logic.flashover_energy_j(1.0e-7, 100.0), 5.0e-4, places=12
        )

    def test_energy_scales_with_the_square_of_the_potential(self):
        single = logic.flashover_energy_j(1.0e-7, 100.0)
        double = logic.flashover_energy_j(1.0e-7, 200.0)
        self.assertAlmostEqual(double / single, 4.0, places=9)

    def test_non_positive_capacitance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.flashover_energy_j(0.0, 100.0)

    def test_non_positive_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.flashover_energy_j(1.0e-7, -100.0)

    def test_energy_below_the_damage_limit_passes(self):
        self.assertTrue(logic.energy_within_limit(4.0e-4, 5.0e-4))

    def test_energy_exactly_at_the_damage_limit_passes(self):
        energy = logic.flashover_energy_j(1.0e-7, 100.0)
        self.assertTrue(logic.energy_within_limit(energy, 5.0e-4))

    def test_energy_a_few_ulps_over_the_limit_is_absorbed(self):
        limit = 5.0e-4
        self.assertTrue(logic.energy_within_limit(limit * (1.0 + 1.0e-15), limit))

    def test_energy_genuinely_over_the_limit_fails(self):
        self.assertFalse(logic.energy_within_limit(6.0e-4, 5.0e-4))

    def test_non_positive_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.energy_within_limit(5.0e-4, 0.0)

    def test_non_positive_energy_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.energy_within_limit(0.0, 5.0e-4)


class StringPairTests(unittest.TestCase):
    def credible_pair(self):
        return {
            "location": "string-to-string-gap",
            "plasma_exposed": True,
            "differential_voltage_v": 100.0,
            "string_current_a": 1.0,
            "gap_mm": 1.0,
        }

    def safe_pair(self):
        return {
            "location": "string-to-string-gap",
            "plasma_exposed": True,
            "differential_voltage_v": 50.0,
            "string_current_a": 1.0,
            "gap_mm": 4.0,
        }

    def test_pair_above_the_threshold_is_credible(self):
        result = logic.evaluate_string_pair(self.credible_pair())
        self.assertEqual(result["risk"], "sustained-arc-credible")
        self.assertIn("increase-the-conductor-gap", result["provisions"])

    def test_pair_below_the_threshold_is_flashover_only(self):
        result = logic.evaluate_string_pair(self.safe_pair())
        self.assertEqual(result["risk"], "non-sustained-only")
        self.assertAlmostEqual(result["threshold_v"], 120.0, places=9)

    def test_pair_exactly_on_the_threshold_is_credible(self):
        pair = self.safe_pair()
        threshold = logic.site_threshold_voltage(
            pair["string_current_a"], pair["gap_mm"], "pristine"
        )
        pair["differential_voltage_v"] = threshold * (1.0 - 1.0e-15)
        result = logic.evaluate_string_pair(pair)
        self.assertEqual(result["risk"], "sustained-arc-credible")

    def test_carbonized_track_turns_a_safe_pair_credible(self):
        pair = self.safe_pair()
        pair["differential_voltage_v"] = 80.0
        self.assertEqual(
            logic.evaluate_string_pair(pair)["risk"], "non-sustained-only"
        )
        pair["site_condition"] = "carbonized-track"
        self.assertEqual(
            logic.evaluate_string_pair(pair)["risk"], "sustained-arc-credible"
        )

    def test_pair_outside_the_provisions_carries_no_threshold(self):
        pair = self.credible_pair()
        pair["location"] = "battery-interface"
        result = logic.evaluate_string_pair(pair)
        self.assertEqual(result["risk"], "provisions-not-applicable")
        self.assertIsNone(result["threshold_v"])
        self.assertEqual(result["provisions"], ())

    def test_weak_string_is_reported_as_unable_to_feed_an_arc(self):
        pair = self.credible_pair()
        pair["string_current_a"] = 0.02
        result = logic.evaluate_string_pair(pair)
        self.assertEqual(result["risk"], "provisions-not-applicable")
        self.assertEqual(result["reason"], "string-current-cannot-feed-an-arc")

    def test_pair_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.evaluate_string_pair(["string-to-string-gap"])

    def test_pair_missing_a_required_key_is_rejected(self):
        pair = self.credible_pair()
        del pair["gap_mm"]
        with self.assertRaises(ValueError):
            logic.evaluate_string_pair(pair)

    def test_unknown_site_condition_in_a_pair_is_rejected(self):
        pair = self.credible_pair()
        pair["site_condition"] = "sandblasted"
        with self.assertRaises(ValueError):
            logic.evaluate_string_pair(pair)


class ProvisionListTests(unittest.TestCase):
    def test_credible_risk_imposes_four_provisions(self):
        self.assertEqual(len(logic.required_provisions("sustained-arc-credible")), 4)

    def test_flashover_only_risk_imposes_two_provisions(self):
        self.assertEqual(len(logic.required_provisions("non-sustained-only")), 2)

    def test_inapplicable_risk_imposes_nothing(self):
        self.assertEqual(logic.required_provisions("provisions-not-applicable"), ())

    def test_unknown_risk_category_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.required_provisions("maybe-sustained")


class SectionAssessmentTests(unittest.TestCase):
    def safe_pair(self):
        return {
            "location": "string-to-string-gap",
            "plasma_exposed": True,
            "differential_voltage_v": 50.0,
            "string_current_a": 1.0,
            "gap_mm": 4.0,
        }

    def credible_pair(self):
        return {
            "location": "cell-to-cell-gap",
            "plasma_exposed": True,
            "differential_voltage_v": 100.0,
            "string_current_a": 1.0,
            "gap_mm": 1.0,
        }

    def test_clean_section_is_clear(self):
        section = {
            "pairs": [self.safe_pair(), self.safe_pair()],
            "events": [{"duration_s": 5.0e-4, "terminated_by": "self-extinction"}],
        }
        result = logic.assess_array_section(section)
        self.assertTrue(result["clear"])
        self.assertEqual(result["findings"], [])
        self.assertFalse(result["sustained_arc_credible"])

    def test_credible_pair_blocks_the_section(self):
        section = {"pairs": [self.safe_pair(), self.credible_pair()]}
        result = logic.assess_array_section(section)
        self.assertFalse(result["clear"])
        self.assertTrue(result["sustained_arc_credible"])
        self.assertIn("cell-to-cell-gap", result["findings"][0])

    def test_recorded_sustained_event_blocks_the_section(self):
        section = {
            "pairs": [self.safe_pair()],
            "events": [{"duration_s": 0.2, "terminated_by": "self-extinction"}],
        }
        result = logic.assess_array_section(section)
        self.assertFalse(result["clear"])
        self.assertEqual(result["event_categories"], ["temporary-sustained"])

    def test_events_are_optional(self):
        result = logic.assess_array_section({"pairs": [self.safe_pair()]})
        self.assertEqual(result["event_categories"], [])
        self.assertTrue(result["clear"])

    def test_every_event_is_categorized(self):
        section = {
            "pairs": [self.safe_pair()],
            "events": [
                {"duration_s": 5.0e-4, "terminated_by": "self-extinction"},
                {"duration_s": 9.0, "terminated_by": "bus-power-removal"},
            ],
        }
        result = logic.assess_array_section(section)
        self.assertEqual(
            result["event_categories"], ["non-sustained", "permanent-sustained"]
        )

    def test_provisions_are_deduplicated_across_pairs(self):
        section = {"pairs": [self.credible_pair(), self.credible_pair()]}
        result = logic.assess_array_section(section)
        self.assertEqual(len(result["provisions"]), len(set(result["provisions"])))
        self.assertEqual(len(result["provisions"]), 4)

    def test_pair_results_are_returned_for_every_pair(self):
        section = {"pairs": [self.safe_pair(), self.credible_pair()]}
        self.assertEqual(len(logic.assess_array_section(section)["pair_results"]), 2)

    def test_section_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.assess_array_section([self.safe_pair()])

    def test_section_without_pairs_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_array_section({"events": []})

    def test_section_with_an_empty_pair_list_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_array_section({"pairs": []})

    def test_non_list_events_are_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_array_section(
                {"pairs": [self.safe_pair()], "events": {"duration_s": 1.0}}
            )


if __name__ == "__main__":
    unittest.main()
