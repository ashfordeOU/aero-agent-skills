"""Contract test for the IR ultracleaning-verification leaf (unittest)."""

import unittest

from q7005_use_in_ultracleaning_logic import (
    ACCEPTED,
    FURTHER_CYCLE_REQUIRED,
    NOT_DEMONSTRATED,
    PROCESS_CHANGE_REQUIRED,
    blank_bounded_level,
    cumulative_removal,
    cycle_efficiencies,
    plateau_detected,
    projected_cycles_to_target,
    removal_efficiency,
    resolved_policy,
    validate_campaign,
    verify_campaign_set,
    verify_ultracleaning,
)


def campaign(item="optical-bench-face", levels=(4.0, 1.5), **kw):
    record = {
        "item": item,
        "process_reference": "UCP-0031",
        "initial_level_mg_m2": 10.0,
        "target_level_mg_m2": 2.0,
        "cycles": [{"post_level_mg_m2": level} for level in levels],
        "verification_blank_level_mg_m2": 0.05,
    }
    record.update(kw)
    return record


class TestRemovalEfficiency(unittest.TestCase):
    def test_a_half_removal_reads_as_a_half(self):
        self.assertAlmostEqual(removal_efficiency(10.0, 5.0), 0.5, places=9)

    def test_a_complete_removal_reads_as_one(self):
        self.assertAlmostEqual(removal_efficiency(10.0, 0.0), 1.0, places=12)

    def test_a_rise_reads_as_a_negative_efficiency(self):
        self.assertAlmostEqual(removal_efficiency(2.0, 3.0), -0.5, places=9)

    def test_a_zero_starting_level_raises(self):
        with self.assertRaises(ValueError):
            removal_efficiency(0.0, 0.0)

    def test_a_non_numeric_level_raises(self):
        with self.assertRaises(ValueError):
            removal_efficiency("10", 5.0)

    def test_cumulative_removal_spans_the_whole_campaign(self):
        self.assertAlmostEqual(cumulative_removal(10.0, 1.0), 0.9, places=9)


class TestBlankBound(unittest.TestCase):
    def test_a_residual_well_above_the_blank_is_a_value(self):
        value, bounded = blank_bounded_level(1.5, 0.05, 3.0)
        self.assertAlmostEqual(value, 1.5, places=9)
        self.assertFalse(bounded)

    def test_a_residual_near_the_blank_becomes_a_bound(self):
        value, bounded = blank_bounded_level(0.10, 0.05, 3.0)
        self.assertTrue(bounded)
        self.assertAlmostEqual(value, 0.15, places=9)

    def test_a_residual_exactly_on_the_margin_is_still_a_value(self):
        value, bounded = blank_bounded_level(0.15, 0.05, 3.0)
        self.assertFalse(bounded)
        self.assertAlmostEqual(value, 0.15, places=9)

    def test_a_margin_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            blank_bounded_level(1.0, 0.05, 0.5)


class TestProjectedCycles(unittest.TestCase):
    def test_a_level_already_at_target_needs_no_cycle(self):
        self.assertEqual(projected_cycles_to_target(2.0, 2.0, 0.5), 0)

    def test_one_cycle_can_be_enough(self):
        self.assertEqual(projected_cycles_to_target(3.0, 2.0, 0.5), 1)

    def test_several_cycles_are_counted(self):
        self.assertEqual(projected_cycles_to_target(8.0, 2.0, 0.5), 2)

    def test_a_dead_process_never_reaches_the_target(self):
        self.assertIsNone(projected_cycles_to_target(8.0, 2.0, 0.0))

    def test_a_slow_process_exhausts_the_permitted_cycles(self):
        self.assertIsNone(
            projected_cycles_to_target(8.0, 2.0, 0.01, maximum_cycles=5)
        )

    def test_a_zero_target_raises(self):
        with self.assertRaises(ValueError):
            projected_cycles_to_target(8.0, 0.0, 0.5)


class TestPlateauDetection(unittest.TestCase):
    def test_two_dead_cycles_are_a_plateau(self):
        self.assertTrue(plateau_detected([0.6, 0.02, 0.01], 0.10, 2))

    def test_a_healthy_last_cycle_is_not_a_plateau(self):
        self.assertFalse(plateau_detected([0.02, 0.01, 0.4], 0.10, 2))

    def test_an_efficiency_exactly_on_the_floor_breaks_the_plateau(self):
        self.assertFalse(plateau_detected([0.02, 0.10], 0.10, 2))

    def test_too_few_cycles_cannot_show_a_plateau(self):
        self.assertFalse(plateau_detected([0.01], 0.10, 2))

    def test_a_non_list_raises(self):
        with self.assertRaises(ValueError):
            plateau_detected("0.01", 0.10, 2)


class TestPolicy(unittest.TestCase):
    def test_defaults_are_returned_when_nothing_is_passed(self):
        self.assertEqual(resolved_policy()["plateau_cycle_count"], 2)

    def test_an_unknown_policy_key_raises(self):
        with self.assertRaises(ValueError):
            resolved_policy({"plateau_cycles": 3})

    def test_a_margin_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            resolved_policy({"minimum_blank_margin_factor": 0.5})


class TestValidateCampaign(unittest.TestCase):
    def test_a_valid_campaign_normalizes_and_numbers_its_cycles(self):
        norm = validate_campaign(campaign())
        self.assertEqual(norm["cycles"][0]["cycle"], 1)
        self.assertEqual(norm["cycles"][1]["cycle"], 2)

    def test_a_missing_process_reference_raises(self):
        with self.assertRaises(ValueError):
            validate_campaign(campaign(process_reference="  "))

    def test_a_zero_initial_level_raises(self):
        with self.assertRaises(ValueError):
            validate_campaign(campaign(initial_level_mg_m2=0.0))

    def test_a_zero_target_raises(self):
        with self.assertRaises(ValueError):
            validate_campaign(campaign(target_level_mg_m2=0.0))

    def test_an_empty_cycle_list_raises(self):
        with self.assertRaises(ValueError):
            validate_campaign(campaign(cycles=[]))

    def test_a_negative_post_level_raises(self):
        with self.assertRaises(ValueError):
            validate_campaign(campaign(levels=(-1.0,)))


class TestCycleEfficiencies(unittest.TestCase):
    def test_each_cycle_is_measured_against_the_previous_level(self):
        rows = cycle_efficiencies(campaign(levels=(5.0, 2.5)))
        self.assertAlmostEqual(rows[0]["efficiency"], 0.5, places=9)
        self.assertAlmostEqual(rows[1]["efficiency"], 0.5, places=9)

    def test_the_first_cycle_is_measured_against_the_initial_level(self):
        rows = cycle_efficiencies(campaign(levels=(8.0,)))
        self.assertAlmostEqual(rows[0]["before_level_mg_m2"], 10.0, places=9)


class TestVerifyUltracleaning(unittest.TestCase):
    def test_a_campaign_reaching_the_target_is_accepted(self):
        row = verify_ultracleaning(campaign())
        self.assertEqual(row["outcome"], ACCEPTED)
        self.assertAlmostEqual(row["reported_level_mg_m2"], 1.5, places=9)

    def test_a_residual_exactly_on_the_target_is_accepted(self):
        row = verify_ultracleaning(campaign(levels=(4.0, 2.0)))
        self.assertEqual(row["outcome"], ACCEPTED)

    def test_a_working_process_short_of_target_asks_for_another_cycle(self):
        row = verify_ultracleaning(campaign(levels=(6.0, 3.0)))
        self.assertEqual(row["outcome"], FURTHER_CYCLE_REQUIRED)
        self.assertEqual(row["projected_further_cycles"], 1)

    def test_a_plateaued_process_asks_for_a_different_process(self):
        row = verify_ultracleaning(campaign(levels=(6.0, 5.95, 5.93)))
        self.assertEqual(row["outcome"], PROCESS_CHANGE_REQUIRED)
        self.assertTrue(row["plateau"])
        self.assertIn("successive-cycles-below-the-efficiency-floor",
                      row["findings"])

    def test_a_rise_across_a_cycle_is_reported_as_recontamination(self):
        row = verify_ultracleaning(campaign(levels=(1.0, 3.0, 1.2)))
        self.assertIn(
            "level-rose-across-cycle-2-recontamination-suspected",
            row["findings"],
        )

    def test_a_residual_lost_in_the_blank_is_not_a_clean_result(self):
        row = verify_ultracleaning(
            campaign(
                levels=(6.0, 1.0),
                target_level_mg_m2=0.5,
                verification_blank_level_mg_m2=0.9,
            )
        )
        self.assertEqual(row["outcome"], NOT_DEMONSTRATED)
        self.assertTrue(row["blank_limited"])
        self.assertIn(
            "residual-indistinguishable-from-the-verification-blank",
            row["findings"],
        )

    def test_a_blank_limited_bound_under_the_target_still_passes(self):
        row = verify_ultracleaning(
            campaign(
                levels=(6.0, 0.10),
                target_level_mg_m2=2.0,
                verification_blank_level_mg_m2=0.05,
            )
        )
        self.assertEqual(row["outcome"], ACCEPTED)
        self.assertTrue(row["blank_limited"])

    def test_the_campaign_removal_spans_first_to_last(self):
        row = verify_ultracleaning(campaign(levels=(4.0, 1.0)))
        self.assertAlmostEqual(row["campaign_removal"], 0.9, places=9)

    def test_a_tightened_efficiency_floor_can_declare_a_plateau(self):
        record = campaign(levels=(6.0, 4.8, 3.84))
        self.assertEqual(
            verify_ultracleaning(record)["outcome"], FURTHER_CYCLE_REQUIRED
        )
        self.assertEqual(
            verify_ultracleaning(record, {"minimum_cycle_efficiency": 0.5})[
                "outcome"
            ],
            PROCESS_CHANGE_REQUIRED,
        )

    def test_the_process_reference_is_carried_into_the_result(self):
        self.assertEqual(
            verify_ultracleaning(campaign())["process_reference"], "UCP-0031"
        )


class TestVerifyCampaignSet(unittest.TestCase):
    def test_a_clean_set_is_all_accepted(self):
        report = verify_campaign_set([campaign("a"), campaign("b")])
        self.assertTrue(report["all_accepted"])

    def test_outcomes_are_grouped_apart(self):
        report = verify_campaign_set(
            [campaign("a"), campaign("b", levels=(6.0, 5.95, 5.93))]
        )
        self.assertEqual(report["accepted"], ["a"])
        self.assertEqual(report["process_change"], ["b"])
        self.assertFalse(report["all_accepted"])

    def test_duplicate_item_raises(self):
        with self.assertRaises(ValueError):
            verify_campaign_set([campaign("a"), campaign("a")])

    def test_an_empty_set_raises(self):
        with self.assertRaises(ValueError):
            verify_campaign_set([])


if __name__ == "__main__":
    unittest.main()
