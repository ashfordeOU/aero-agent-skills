"""Contract test for the ECSS-Q-ST-60-13C clause 6.2.3.4 reduced-testing leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6013_class_3_evaluation_testing.py
"""

import unittest

from q6013_class_3_evaluation_testing_logic import (
    ADMISSIBLE_FAILURES,
    CLASS_3_MINIMUM_SAMPLES,
    CLASS_3_REDUCTION_FACTOR,
    DRIFT_BEARING_GROUPS,
    DRIFT_WARNING_SHARE,
    GROUP_FULL_SAMPLES,
    MANDATORY_GROUPS,
    VERDICTS,
    assess_group,
    assess_reduced_test_campaign,
    group_full_samples,
    missing_groups,
    required_samples,
    validate_group,
    zero_failure_confidence,
)


def group_entry(name, **overrides):
    """One executed group, drawn at full size and clean unless overridden."""
    entry = {
        "group": name,
        "samples": GROUP_FULL_SAMPLES[name],
        "failures": 0,
        "parameter_drift_pct": 0.5,
        "drift_limit_pct": 2.0 if name in DRIFT_BEARING_GROUPS else 0.0,
    }
    entry.update(overrides)
    return entry


def clean_campaign(**overrides):
    """Every group executed at full size and clean, with named exceptions."""
    groups = []
    for name in sorted(GROUP_FULL_SAMPLES):
        if name in overrides and overrides[name] is None:
            continue
        groups.append(group_entry(name, **overrides.get(name, {})))
    return {
        "manufacturer": "cots-foundry-b",
        "part_number": "xy-4041",
        "groups": groups,
    }


class GroupSizeTests(unittest.TestCase):
    def test_every_group_carries_a_positive_full_assurance_size(self):
        for name in GROUP_FULL_SAMPLES:
            self.assertGreater(group_full_samples(name), 0)

    def test_every_mandatory_group_is_part_of_the_group_set(self):
        for name in MANDATORY_GROUPS:
            self.assertIn(name, GROUP_FULL_SAMPLES)

    def test_unknown_group_rejected(self):
        with self.assertRaises(ValueError):
            group_full_samples("looked-at-it-under-a-lamp")

    def test_the_reduced_draw_is_the_scaled_full_draw(self):
        self.assertEqual(
            required_samples("endurance-burn-in", 0.5),
            GROUP_FULL_SAMPLES["endurance-burn-in"] // 2,
        )

    def test_a_fractional_device_rounds_up_to_a_whole_one(self):
        self.assertEqual(required_samples("mechanical-and-environmental", 0.3), 3)

    def test_no_group_is_drawn_below_the_absolute_floor(self):
        for name in GROUP_FULL_SAMPLES:
            self.assertGreaterEqual(
                required_samples(name, 0.01), CLASS_3_MINIMUM_SAMPLES
            )

    def test_the_reduced_draw_never_exceeds_the_full_draw(self):
        for name in GROUP_FULL_SAMPLES:
            self.assertLessEqual(
                required_samples(name, CLASS_3_REDUCTION_FACTOR),
                max(GROUP_FULL_SAMPLES[name], CLASS_3_MINIMUM_SAMPLES),
            )

    def test_a_zero_reduction_factor_rejected(self):
        with self.assertRaises(ValueError):
            required_samples("endurance-burn-in", 0.0)

    def test_a_reduction_factor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            required_samples("endurance-burn-in", 1.5)

    def test_a_non_numeric_reduction_factor_rejected(self):
        with self.assertRaises(ValueError):
            required_samples("endurance-burn-in", "half")


class DemonstratedConfidenceTests(unittest.TestCase):
    def test_a_clean_run_of_four_against_a_half_defect_fraction(self):
        self.assertAlmostEqual(zero_failure_confidence(4, 0.5), 0.9375, places=9)

    def test_a_single_clean_device_demonstrates_the_defect_fraction_itself(self):
        self.assertAlmostEqual(zero_failure_confidence(1, 0.5), 0.5, places=9)

    def test_more_devices_demonstrate_more_confidence(self):
        self.assertGreater(
            zero_failure_confidence(6, 0.5), zero_failure_confidence(5, 0.5)
        )

    def test_a_zero_sample_run_rejected(self):
        with self.assertRaises(ValueError):
            zero_failure_confidence(0, 0.5)

    def test_a_defect_fraction_of_one_rejected(self):
        with self.assertRaises(ValueError):
            zero_failure_confidence(5, 1.0)

    def test_a_negative_defect_fraction_rejected(self):
        with self.assertRaises(ValueError):
            zero_failure_confidence(5, -0.1)


class ValidateGroupTests(unittest.TestCase):
    def test_a_group_reporting_more_failures_than_samples_rejected(self):
        with self.assertRaises(ValueError):
            validate_group(group_entry("endurance-burn-in", samples=4, failures=5))

    def test_a_group_drawn_with_no_samples_rejected(self):
        with self.assertRaises(ValueError):
            validate_group(group_entry("endurance-burn-in", samples=0))

    def test_a_drift_bearing_group_without_a_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_group(
                group_entry("electrical-characterisation", drift_limit_pct=0.0)
            )

    def test_a_negative_drift_rejected(self):
        with self.assertRaises(ValueError):
            validate_group(
                group_entry("electrical-characterisation", parameter_drift_pct=-0.1)
            )

    def test_a_non_mapping_group_rejected(self):
        with self.assertRaises(ValueError):
            validate_group("endurance-burn-in")


class AssessGroupTests(unittest.TestCase):
    def test_a_clean_full_draw_is_accepted_without_a_finding(self):
        record = assess_group(group_entry("endurance-burn-in"))
        self.assertTrue(record["accepted"])
        self.assertEqual(record["findings"], [])

    def test_a_reduced_draw_is_accepted_and_reported(self):
        record = assess_group(
            group_entry(
                "endurance-burn-in",
                samples=required_samples("endurance-burn-in"),
            )
        )
        self.assertTrue(record["accepted"])
        self.assertIn("reduced-sample-draw-taken", record["findings"])

    def test_a_draw_under_the_class_requirement_blocks(self):
        record = assess_group(
            group_entry(
                "endurance-burn-in",
                samples=required_samples("endurance-burn-in") - 1,
            )
        )
        self.assertFalse(record["accepted"])
        self.assertIn("sample-draw-below-class-3-requirement", record["findings"])

    def test_one_failure_blocks_against_zero_failure_acceptance(self):
        record = assess_group(
            group_entry("endurance-burn-in", failures=ADMISSIBLE_FAILURES + 1)
        )
        self.assertFalse(record["accepted"])
        self.assertIn(
            "failure-recorded-against-zero-failure-acceptance", record["findings"]
        )

    def test_drift_beyond_the_limit_blocks(self):
        record = assess_group(
            group_entry(
                "electrical-characterisation",
                parameter_drift_pct=3.0,
                drift_limit_pct=2.0,
            )
        )
        self.assertFalse(record["accepted"])
        self.assertIn("parameter-drift-beyond-limit", record["findings"])

    def test_drift_landing_on_the_limit_is_not_beyond_it(self):
        record = assess_group(
            group_entry(
                "electrical-characterisation",
                parameter_drift_pct=2.0,
                drift_limit_pct=2.0,
            )
        )
        self.assertTrue(record["accepted"])
        self.assertNotIn("parameter-drift-beyond-limit", record["findings"])
        self.assertIn("parameter-drift-in-warning-band", record["findings"])

    def test_drift_on_the_warning_threshold_is_not_yet_a_trend(self):
        record = assess_group(
            group_entry(
                "electrical-characterisation",
                parameter_drift_pct=2.0 * DRIFT_WARNING_SHARE,
                drift_limit_pct=2.0,
            )
        )
        self.assertEqual(record["findings"], [])

    def test_a_record_carries_both_the_reduced_and_the_full_draw(self):
        record = assess_group(group_entry("temperature-extremes"))
        self.assertEqual(
            record["required_samples"], required_samples("temperature-extremes")
        )
        self.assertEqual(
            record["full_assurance_samples"], GROUP_FULL_SAMPLES["temperature-extremes"]
        )


class MissingGroupTests(unittest.TestCase):
    def test_a_complete_executed_set_is_missing_nothing(self):
        records = [{"group": name} for name in GROUP_FULL_SAMPLES]
        self.assertEqual(missing_groups(records), [])

    def test_an_absent_mandatory_group_is_named(self):
        records = [
            {"group": name} for name in MANDATORY_GROUPS if name != "endurance-burn-in"
        ]
        self.assertEqual(missing_groups(records), ["endurance-burn-in"])

    def test_missing_groups_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            missing_groups({"group": "endurance-burn-in"})

    def test_missing_groups_rejects_a_record_with_no_group(self):
        with self.assertRaises(ValueError):
            missing_groups([{"samples": 6}])


class CampaignVerdictTests(unittest.TestCase):
    def test_a_clean_full_campaign_is_suitable_with_no_finding(self):
        report = assess_reduced_test_campaign(clean_campaign())
        self.assertEqual(report["verdict"], "class-3-part-type-suitable")
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["usable_at_class_3"])

    def test_an_unrun_supporting_group_leaves_actions(self):
        report = assess_reduced_test_campaign(
            clean_campaign(**{"solderability-and-mounting": None})
        )
        self.assertEqual(report["verdict"], "class-3-part-type-suitable-with-actions")
        self.assertIn(
            {"group": "solderability-and-mounting", "finding": "supporting-group-not-run"},
            report["findings"],
        )

    def test_an_unrun_mandatory_group_is_not_a_clean_group(self):
        report = assess_reduced_test_campaign(
            clean_campaign(**{"endurance-burn-in": None})
        )
        self.assertEqual(report["verdict"], "class-3-part-type-not-suitable")
        self.assertEqual(report["missing_groups"], ["endurance-burn-in"])
        self.assertFalse(report["usable_at_class_3"])

    def test_one_failing_group_sinks_the_whole_campaign(self):
        report = assess_reduced_test_campaign(
            clean_campaign(**{"temperature-extremes": {"failures": 1}})
        )
        self.assertEqual(report["verdict"], "class-3-part-type-not-suitable")

    def test_a_thin_draw_reports_the_confidence_it_actually_bought(self):
        report = assess_reduced_test_campaign(
            clean_campaign(
                **{
                    name: {"samples": required_samples(name)}
                    for name in GROUP_FULL_SAMPLES
                }
            )
        )
        self.assertEqual(report["verdict"], "class-3-part-type-suitable-with-actions")
        self.assertIn(
            {"group": "campaign", "finding": "demonstrated-confidence-below-target"},
            report["findings"],
        )
        self.assertLess(report["demonstrated_confidence"], report["target_confidence"])

    def test_every_verdict_name_is_one_the_module_publishes(self):
        seen = set()
        seen.add(assess_reduced_test_campaign(clean_campaign())["verdict"])
        seen.add(
            assess_reduced_test_campaign(
                clean_campaign(**{"solderability-and-mounting": None})
            )["verdict"]
        )
        seen.add(
            assess_reduced_test_campaign(
                clean_campaign(**{"endurance-burn-in": None})
            )["verdict"]
        )
        self.assertEqual(seen, set(VERDICTS))

    def test_duplicate_group_declaration_rejected(self):
        spec = clean_campaign()
        spec["groups"].append(group_entry("endurance-burn-in"))
        with self.assertRaises(ValueError):
            assess_reduced_test_campaign(spec)

    def test_a_blank_part_number_rejected(self):
        spec = clean_campaign()
        spec["part_number"] = "   "
        with self.assertRaises(ValueError):
            assess_reduced_test_campaign(spec)

    def test_a_missing_manufacturer_rejected(self):
        spec = clean_campaign()
        del spec["manufacturer"]
        with self.assertRaises(ValueError):
            assess_reduced_test_campaign(spec)

    def test_a_non_sequence_group_list_rejected(self):
        spec = clean_campaign()
        spec["groups"] = {"group": "endurance-burn-in"}
        with self.assertRaises(ValueError):
            assess_reduced_test_campaign(spec)

    def test_a_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_reduced_test_campaign(["cots-foundry-b", "xy-4041"])


if __name__ == "__main__":
    unittest.main()
