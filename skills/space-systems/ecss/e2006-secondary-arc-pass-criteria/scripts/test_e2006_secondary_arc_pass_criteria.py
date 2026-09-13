#!/usr/bin/env python3
"""Contract test for the secondary-arc pass conditions leaf (offline, stdlib)."""

import unittest

from e2006_secondary_arc_pass_criteria_logic import (
    MIN_RESISTANCE_RETENTION,
    NON_SUSTAINED_LIMIT_S,
    SUSTAINING_CURRENT_A,
    arc_condition_findings,
    assess_secondary_arc_pass,
    categorize_arc_event,
    check_campaign_coverage,
    evaluate_string_insulation,
    insulation_retention_ratio,
    summarize_arc_events,
)


def good_coverage(**overrides):
    coverage = {
        "applied_string_voltage_v": 120.0,
        "worst_case_string_voltage_v": 100.0,
        "applied_string_current_a": 2.0,
        "worst_case_string_current_a": 1.5,
        "primary_arc_count": 60.0,
        "required_primary_arc_count": 50.0,
        "dwell_duration_s": 400.0,
        "required_dwell_duration_s": 300.0,
    }
    coverage.update(overrides)
    return coverage


def good_insulation(**overrides):
    sample = {
        "pre_test_resistance_ohm": 2.0e9,
        "post_test_resistance_ohm": 1.8e9,
        "required_resistance_ohm": 1.0e9,
        "observed_conditions": ["none"],
    }
    sample.update(overrides)
    return sample


def good_record(**overrides):
    record = {
        "coverage": good_coverage(),
        "arc_events": [
            {"duration_s": 2.0e-4, "peak_current_a": 1.2, "termination": "self-extinguished"},
            {"duration_s": 5.0e-5, "peak_current_a": 0.9, "termination": "self-extinguished"},
        ],
        "insulation": good_insulation(),
    }
    record.update(overrides)
    return record


class CategorizeArcEventTests(unittest.TestCase):
    def test_short_self_extinguished_event_is_non_sustained(self):
        event = {"duration_s": 1.0e-4, "peak_current_a": 1.0, "termination": "self-extinguished"}
        self.assertEqual(categorize_arc_event(event), "non-sustained")

    def test_long_self_extinguished_event_is_temporary_sustained(self):
        event = {"duration_s": 5.0e-3, "peak_current_a": 1.0, "termination": "self-extinguished"}
        self.assertEqual(categorize_arc_event(event), "temporary-sustained")

    def test_external_cutoff_is_permanent_sustained(self):
        event = {"duration_s": 2.0, "peak_current_a": 1.4, "termination": "external-cutoff"}
        self.assertEqual(categorize_arc_event(event), "permanent-sustained")

    def test_low_current_long_event_cannot_be_fed_by_the_string(self):
        event = {"duration_s": 0.5, "peak_current_a": 0.01, "termination": "self-extinguished"}
        self.assertEqual(categorize_arc_event(event), "non-sustained")

    def test_duration_exactly_at_the_transient_limit_stays_non_sustained(self):
        # The recorded duration is a difference of two timestamps, so an
        # exactly-compliant event can land a few ULPs above the limit.
        start = 0.1
        stop = start + NON_SUSTAINED_LIMIT_S
        duration = stop - start
        self.assertGreaterEqual(duration, NON_SUSTAINED_LIMIT_S)
        event = {"duration_s": duration, "peak_current_a": 2.0, "termination": "self-extinguished"}
        self.assertEqual(categorize_arc_event(event), "non-sustained")

    def test_current_exactly_at_the_sustaining_threshold_counts_as_sustainable(self):
        event = {
            "duration_s": 0.2,
            "peak_current_a": SUSTAINING_CURRENT_A,
            "termination": "self-extinguished",
        }
        self.assertEqual(categorize_arc_event(event), "temporary-sustained")

    def test_unknown_termination_mode_is_rejected(self):
        event = {"duration_s": 1.0e-4, "peak_current_a": 1.0, "termination": "quenched"}
        with self.assertRaises(ValueError):
            categorize_arc_event(event)

    def test_missing_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_arc_event({"peak_current_a": 1.0, "termination": "self-extinguished"})

    def test_negative_peak_current_is_rejected(self):
        event = {"duration_s": 1.0e-4, "peak_current_a": -0.2, "termination": "self-extinguished"}
        with self.assertRaises(ValueError):
            categorize_arc_event(event)

    def test_non_numeric_duration_is_rejected(self):
        event = {"duration_s": "1e-4", "peak_current_a": 1.0, "termination": "self-extinguished"}
        with self.assertRaises(ValueError):
            categorize_arc_event(event)

    def test_non_mapping_event_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_arc_event(["duration_s", 1.0])

    def test_non_positive_transient_limit_is_rejected(self):
        event = {"duration_s": 1.0e-4, "peak_current_a": 1.0, "termination": "self-extinguished"}
        with self.assertRaises(ValueError):
            categorize_arc_event(event, non_sustained_limit_s=0.0)


class SummaryTests(unittest.TestCase):
    def test_counts_every_category(self):
        events = [
            {"duration_s": 1.0e-4, "peak_current_a": 1.0, "termination": "self-extinguished"},
            {"duration_s": 4.0e-3, "peak_current_a": 1.0, "termination": "self-extinguished"},
            {"duration_s": 3.0, "peak_current_a": 1.1, "termination": "external-cutoff"},
        ]
        summary = summarize_arc_events(events)
        self.assertEqual(summary["counts"]["non-sustained"], 1)
        self.assertEqual(summary["counts"]["temporary-sustained"], 1)
        self.assertEqual(summary["counts"]["permanent-sustained"], 1)
        self.assertEqual(summary["sustained_count"], 2)
        self.assertEqual(summary["event_count"], 3)

    def test_empty_campaign_has_no_sustained_events(self):
        summary = summarize_arc_events([])
        self.assertEqual(summary["sustained_count"], 0)

    def test_events_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            summarize_arc_events({"duration_s": 1.0})

    def test_permanent_sustained_event_produces_a_finding(self):
        events = [{"duration_s": 3.0, "peak_current_a": 1.1, "termination": "external-cutoff"}]
        result = arc_condition_findings(events)
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("permanent-sustained", result["findings"][0])

    def test_temporary_sustained_event_produces_a_finding_by_default(self):
        events = [{"duration_s": 4.0e-3, "peak_current_a": 1.0, "termination": "self-extinguished"}]
        self.assertEqual(len(arc_condition_findings(events)["findings"]), 1)

    def test_temporary_sustained_event_can_be_admitted_explicitly(self):
        events = [{"duration_s": 4.0e-3, "peak_current_a": 1.0, "termination": "self-extinguished"}]
        result = arc_condition_findings(events, allow_temporary_sustained=True)
        self.assertEqual(result["findings"], [])


class InsulationTests(unittest.TestCase):
    def test_retention_ratio_is_the_post_over_pre_quotient(self):
        self.assertAlmostEqual(insulation_retention_ratio(2.0e9, 1.0e9), 0.5, places=9)

    def test_zero_pre_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            insulation_retention_ratio(0.0, 1.0e9)

    def test_healthy_insulation_has_no_findings(self):
        result = evaluate_string_insulation(good_insulation())
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["retention_ratio"], 0.9, places=9)

    def test_resistance_below_the_required_floor_is_a_finding(self):
        result = evaluate_string_insulation(
            good_insulation(post_test_resistance_ohm=5.0e8, pre_test_resistance_ohm=6.0e8)
        )
        self.assertTrue(any("below the required" in f for f in result["findings"]))

    def test_resistance_exactly_at_the_required_floor_passes(self):
        # The measured value is reconstructed as a sum, which can land a few
        # ULPs below the floor; the compliant sample must still pass.
        required = 1.0e9
        measured = 0.7e9 + 0.3e9
        result = evaluate_string_insulation(
            good_insulation(post_test_resistance_ohm=measured, required_resistance_ohm=required)
        )
        self.assertEqual(result["findings"], [])

    def test_retention_exactly_at_the_floor_passes(self):
        pre = 2.0e9
        post = pre * MIN_RESISTANCE_RETENTION
        result = evaluate_string_insulation(
            good_insulation(
                pre_test_resistance_ohm=pre,
                post_test_resistance_ohm=post,
                required_resistance_ohm=1.0e8,
            )
        )
        self.assertEqual(result["findings"], [])

    def test_retention_collapse_is_a_finding_even_above_the_floor_value(self):
        result = evaluate_string_insulation(
            good_insulation(
                pre_test_resistance_ohm=1.0e11,
                post_test_resistance_ohm=2.0e9,
                required_resistance_ohm=1.0e9,
            )
        )
        self.assertTrue(any("retention" in f for f in result["findings"]))

    def test_carbonized_track_is_disqualifying(self):
        result = evaluate_string_insulation(
            good_insulation(observed_conditions=["carbonized-track"])
        )
        self.assertEqual(result["damage_conditions"], ["carbonized-track"])
        self.assertTrue(any("carbonized-track" in f for f in result["findings"]))

    def test_discoloration_alone_is_cosmetic(self):
        result = evaluate_string_insulation(good_insulation(observed_conditions=["discoloration"]))
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["cosmetic_conditions"], ["discoloration"])

    def test_uncategorized_surface_condition_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_string_insulation(good_insulation(observed_conditions=["sparkly"]))

    def test_conditions_must_be_a_list(self):
        with self.assertRaises(ValueError):
            evaluate_string_insulation(good_insulation(observed_conditions="none"))

    def test_missing_required_resistance_is_rejected(self):
        sample = good_insulation()
        del sample["required_resistance_ohm"]
        with self.assertRaises(ValueError):
            evaluate_string_insulation(sample)

    def test_retention_floor_outside_the_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_string_insulation(good_insulation(), min_retention=1.5)


class CoverageTests(unittest.TestCase):
    def test_bounding_campaign_has_no_findings(self):
        result = check_campaign_coverage(good_coverage())
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["voltage_margin_v"], 20.0, places=9)
        self.assertAlmostEqual(result["current_margin_a"], 0.5, places=9)

    def test_applied_voltage_exactly_at_the_worst_case_passes(self):
        # Applied voltage built from a sum of segment voltages: the exact
        # equality case must not be read as a shortfall.
        worst = 100.0
        applied = 33.4 + 33.3 + 33.3
        result = check_campaign_coverage(
            good_coverage(applied_string_voltage_v=applied, worst_case_string_voltage_v=worst)
        )
        self.assertEqual(result["findings"], [])

    def test_voltage_shortfall_is_a_finding(self):
        result = check_campaign_coverage(good_coverage(applied_string_voltage_v=80.0))
        self.assertTrue(any("string-voltage" in f for f in result["findings"]))

    def test_current_shortfall_is_a_finding(self):
        result = check_campaign_coverage(good_coverage(applied_string_current_a=1.0))
        self.assertTrue(any("string-current" in f for f in result["findings"]))

    def test_primary_arc_population_shortfall_is_a_finding(self):
        result = check_campaign_coverage(good_coverage(primary_arc_count=10.0))
        self.assertTrue(any("primary-arc population" in f for f in result["findings"]))

    def test_short_dwell_is_a_finding(self):
        result = check_campaign_coverage(good_coverage(dwell_duration_s=10.0))
        self.assertTrue(any("bias dwell" in f for f in result["findings"]))

    def test_zero_applied_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            check_campaign_coverage(good_coverage(applied_string_voltage_v=0.0))

    def test_negative_primary_arc_count_is_rejected(self):
        with self.assertRaises(ValueError):
            check_campaign_coverage(good_coverage(primary_arc_count=-1.0))

    def test_coverage_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            check_campaign_coverage([120.0, 100.0])


class VerdictTests(unittest.TestCase):
    def test_clean_campaign_passes(self):
        result = assess_secondary_arc_pass(good_record())
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["finding_count"], 0)

    def test_sustained_discharge_fails_the_campaign(self):
        record = good_record()
        record["arc_events"].append(
            {"duration_s": 2.5, "peak_current_a": 1.3, "termination": "external-cutoff"}
        )
        result = assess_secondary_arc_pass(record)
        self.assertEqual(result["verdict"], "fail")
        self.assertGreaterEqual(result["finding_count"], 1)

    def test_damaged_insulation_fails_the_campaign(self):
        record = good_record(insulation=good_insulation(observed_conditions=["melted-insulation"]))
        self.assertEqual(assess_secondary_arc_pass(record)["verdict"], "fail")

    def test_short_coverage_fails_even_with_a_clean_arc_record(self):
        record = good_record(coverage=good_coverage(applied_string_voltage_v=50.0))
        result = assess_secondary_arc_pass(record)
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(result["arc_events"]["findings"], [])

    def test_all_three_sections_can_fail_together(self):
        record = good_record(
            coverage=good_coverage(applied_string_current_a=0.1),
            insulation=good_insulation(observed_conditions=["string-to-string-short"]),
        )
        record["arc_events"] = [
            {"duration_s": 9.0, "peak_current_a": 1.0, "termination": "external-cutoff"}
        ]
        result = assess_secondary_arc_pass(record)
        self.assertEqual(result["finding_count"], 3)

    def test_missing_section_is_rejected(self):
        record = good_record()
        del record["insulation"]
        with self.assertRaises(ValueError):
            assess_secondary_arc_pass(record)

    def test_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_secondary_arc_pass("campaign")


if __name__ == "__main__":
    unittest.main()
