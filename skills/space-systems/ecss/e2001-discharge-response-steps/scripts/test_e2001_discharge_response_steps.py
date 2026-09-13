#!/usr/bin/env python3
"""Gate 3 contract test for e2001-discharge-response-steps.

Offline, deterministic, stdlib unittest. Run:
python3 test_e2001_discharge_response_steps.py
"""

import unittest

import e2001_discharge_response_steps_logic as L


def base_event(**over):
    rec = {
        "event_id": "evt-01",
        "onset_level_w": 240.0,
        "chamber_pressure_pa": 2.0e-5,
        "channels_crossed": ["electron-probe", "harmonic-detection"],
        "outgassing_burst": False,
        "fixture_fault": False,
        "seeding_active": True,
    }
    rec.update(over)
    return rec


class RecordValidationTests(unittest.TestCase):
    def test_valid_record_normalises_and_sorts_channels(self):
        rec = L.validate_event_record(base_event())
        self.assertEqual(rec["channels_crossed"], ["electron-probe", "harmonic-detection"])
        self.assertAlmostEqual(rec["onset_level_w"], 240.0, places=9)

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            L.validate_event_record("evt-01")

    def test_blank_event_id_raises(self):
        with self.assertRaises(ValueError):
            L.validate_event_record(base_event(event_id="  "))

    def test_empty_channel_list_raises(self):
        with self.assertRaises(ValueError):
            L.validate_event_record(base_event(channels_crossed=[]))

    def test_non_string_channel_raises(self):
        with self.assertRaises(ValueError):
            L.validate_event_record(base_event(channels_crossed=[3]))

    def test_zero_onset_level_raises(self):
        with self.assertRaises(ValueError):
            L.validate_event_record(base_event(onset_level_w=0.0))

    def test_negative_pressure_raises(self):
        with self.assertRaises(ValueError):
            L.validate_event_record(base_event(chamber_pressure_pa=-1.0e-5))

    def test_non_finite_onset_raises(self):
        with self.assertRaises(ValueError):
            L.validate_event_record(base_event(onset_level_w=float("inf")))

    def test_non_boolean_indication_raises(self):
        with self.assertRaises(ValueError):
            L.validate_event_record(base_event(fixture_fault="maybe"))

    def test_missing_indication_raises(self):
        rec = base_event()
        del rec["outgassing_burst"]
        with self.assertRaises(ValueError):
            L.validate_event_record(rec)


class ImmediateActionTests(unittest.TestCase):
    def test_drive_removal_comes_first(self):
        steps = L.immediate_actions(base_event())
        self.assertIn("remove the drive", steps[0])

    def test_state_capture_comes_before_the_log_entry(self):
        steps = L.immediate_actions(base_event())
        self.assertIn("capture the onset state", steps[1])
        self.assertIn("run log", steps[2])

    def test_capture_names_the_onset_level_and_channels(self):
        steps = L.immediate_actions(base_event())
        self.assertIn("240.0000 W", steps[1])
        self.assertIn("electron-probe", steps[1])

    def test_immediate_actions_are_emitted_for_a_bench_event_too(self):
        steps = L.immediate_actions(base_event(fixture_fault=True))
        self.assertEqual(len(steps), 3)
        self.assertIn("remove the drive", steps[0])

    def test_invalid_record_propagates(self):
        with self.assertRaises(ValueError):
            L.immediate_actions(base_event(onset_level_w=-5.0))


class AttributionTests(unittest.TestCase):
    def test_clean_vacuum_with_seeding_points_at_the_unit(self):
        out = L.attribute_event(base_event())
        self.assertEqual(out["attribution"], L.ATTR_UNIT)

    def test_pressure_above_the_vacuum_limit_points_at_the_bench(self):
        out = L.attribute_event(base_event(chamber_pressure_pa=3.0e-3))
        self.assertEqual(out["attribution"], L.ATTR_FACILITY)
        self.assertTrue(any("vacuum limit" in r for r in out["reasons"]))

    def test_pressure_exactly_at_the_vacuum_limit_is_a_clean_bench(self):
        out = L.attribute_event(base_event(chamber_pressure_pa=L.VACUUM_LIMIT_PA))
        self.assertEqual(out["attribution"], L.ATTR_UNIT)

    def test_outgassing_burst_points_at_the_bench(self):
        out = L.attribute_event(base_event(outgassing_burst=True))
        self.assertEqual(out["attribution"], L.ATTR_FACILITY)

    def test_fixture_fault_points_at_the_bench(self):
        out = L.attribute_event(base_event(fixture_fault=True))
        self.assertEqual(out["attribution"], L.ATTR_FACILITY)

    def test_several_bench_indications_are_all_reported(self):
        out = L.attribute_event(
            base_event(
                chamber_pressure_pa=1.0e-2, outgassing_burst=True, fixture_fault=True
            )
        )
        self.assertEqual(len(out["reasons"]), 3)

    def test_inactive_seeding_leaves_the_attribution_open(self):
        out = L.attribute_event(base_event(seeding_active=False))
        self.assertEqual(out["attribution"], L.ATTR_UNDETERMINED)

    def test_bench_indication_wins_over_missing_seeding(self):
        out = L.attribute_event(base_event(seeding_active=False, fixture_fault=True))
        self.assertEqual(out["attribution"], L.ATTR_FACILITY)


class BackoffTests(unittest.TestCase):
    def test_three_decibel_backoff_roughly_halves_the_level(self):
        self.assertAlmostEqual(L.drive_backoff_level_w(200.0, 3.0), 100.2372, places=3)

    def test_ten_decibel_backoff_is_a_factor_of_ten(self):
        self.assertAlmostEqual(L.drive_backoff_level_w(500.0, 10.0), 50.0, places=9)

    def test_backoff_is_always_below_the_onset(self):
        self.assertLess(L.drive_backoff_level_w(240.0), 240.0)

    def test_zero_backoff_raises(self):
        with self.assertRaises(ValueError):
            L.drive_backoff_level_w(240.0, 0.0)

    def test_negative_backoff_raises(self):
        with self.assertRaises(ValueError):
            L.drive_backoff_level_w(240.0, -3.0)

    def test_non_numeric_backoff_raises(self):
        with self.assertRaises(ValueError):
            L.drive_backoff_level_w(240.0, "3 dB")

    def test_zero_onset_raises(self):
        with self.assertRaises(ValueError):
            L.drive_backoff_level_w(0.0, 3.0)


class ReproducibilityTests(unittest.TestCase):
    def test_identical_onsets_have_zero_spread(self):
        self.assertAlmostEqual(L.onset_spread_db([240.0, 240.0]), 0.0, places=12)

    def test_factor_of_ten_is_ten_decibels(self):
        self.assertAlmostEqual(L.onset_spread_db([100.0, 1000.0]), 10.0, places=9)

    def test_single_onset_cannot_be_judged(self):
        with self.assertRaises(ValueError):
            L.onset_spread_db([240.0])

    def test_non_list_onsets_raise(self):
        with self.assertRaises(ValueError):
            L.onset_spread_db(240.0)

    def test_non_positive_onset_raises(self):
        with self.assertRaises(ValueError):
            L.onset_spread_db([240.0, 0.0])

    def test_close_onsets_are_reproducible(self):
        out = L.reproducibility_verdict([240.0, 246.0])
        self.assertEqual(out["verdict"], L.VERDICT_REPRODUCIBLE)
        self.assertAlmostEqual(out["lowest_onset_level_w"], 240.0, places=9)

    def test_wide_onsets_are_not_reproducible(self):
        out = L.reproducibility_verdict([240.0, 400.0])
        self.assertEqual(out["verdict"], L.VERDICT_NOT_REPRODUCIBLE)
        self.assertGreater(out["spread_db"], 1.0)

    def test_spread_exactly_at_the_allowance_is_reproducible(self):
        # The second onset is the first taken up by exactly the allowed
        # spread, so the computed spread lands a few units in the last place
        # over 1.0 dB. That is representation error, not a wider allowance.
        high = 240.0 * (10.0 ** (L.DEFAULT_SPREAD_DB / 10.0))
        out = L.reproducibility_verdict([240.0, high])
        self.assertEqual(out["verdict"], L.VERDICT_REPRODUCIBLE)
        self.assertAlmostEqual(out["spread_db"], 1.0, places=9)

    def test_spread_one_percent_over_the_allowance_is_not_reproducible(self):
        high = 240.0 * (10.0 ** (1.01 * L.DEFAULT_SPREAD_DB / 10.0))
        out = L.reproducibility_verdict([240.0, high])
        self.assertEqual(out["verdict"], L.VERDICT_NOT_REPRODUCIBLE)

    def test_custom_allowance_is_honoured(self):
        out = L.reproducibility_verdict([240.0, 400.0], allowed_spread_db=3.0)
        self.assertEqual(out["verdict"], L.VERDICT_REPRODUCIBLE)

    def test_zero_allowance_raises(self):
        with self.assertRaises(ValueError):
            L.reproducibility_verdict([240.0, 246.0], allowed_spread_db=0.0)

    def test_non_numeric_allowance_raises(self):
        with self.assertRaises(ValueError):
            L.reproducibility_verdict([240.0, 246.0], allowed_spread_db=None)


class DeclarableCapTests(unittest.TestCase):
    def test_cap_sits_below_the_onset(self):
        self.assertLess(L.declarable_cap_w(240.0), 240.0)

    def test_cap_uses_the_defined_step_back(self):
        self.assertAlmostEqual(
            L.declarable_cap_w(240.0), 240.0 * L.ONSET_CAP_FRACTION, places=9
        )

    def test_zero_onset_cap_raises(self):
        with self.assertRaises(ValueError):
            L.declarable_cap_w(0.0)


class ResponsePlanTests(unittest.TestCase):
    def test_plan_opens_with_the_immediate_actions(self):
        plan = L.response_plan(base_event())
        self.assertIn("remove the drive", plan["steps"][0])
        self.assertIn("capture the onset state", plan["steps"][1])

    def test_bench_event_plan_corrects_the_condition(self):
        plan = L.response_plan(base_event(outgassing_burst=True))
        self.assertEqual(plan["attribution"], L.ATTR_FACILITY)
        self.assertTrue(any("correct the bench condition" in s for s in plan["steps"]))

    def test_unit_event_plan_holds_the_bench_condition(self):
        plan = L.response_plan(base_event())
        self.assertTrue(any("hold the bench condition" in s for s in plan["steps"]))

    def test_open_attribution_plan_restores_the_prerequisite(self):
        plan = L.response_plan(base_event(seeding_active=False))
        self.assertTrue(any("restore the missing prerequisite" in s for s in plan["steps"]))

    def test_plan_restarts_below_the_onset(self):
        plan = L.response_plan(base_event())
        self.assertLess(plan["backoff_level_w"], 240.0)
        self.assertTrue(any("restart the repeat run" in s for s in plan["steps"]))

    def test_plan_always_ends_with_the_report_obligation(self):
        plan = L.response_plan(base_event(fixture_fault=True))
        self.assertIn("carry the captured onset state into the report", plan["steps"][-1])

    def test_custom_backoff_is_used_in_the_plan(self):
        plan = L.response_plan(base_event(), backoff_db=6.0)
        self.assertAlmostEqual(
            plan["backoff_level_w"], 240.0 / (10.0 ** 0.6), places=6
        )


class DispositionTests(unittest.TestCase):
    def test_bench_event_is_corrected_and_repeated(self):
        out = L.disposition(base_event(chamber_pressure_pa=5.0e-3))
        self.assertEqual(out["disposition"], L.DISPOSITION_REPEAT)
        self.assertIsNone(out["declarable_cap_w"])

    def test_unit_event_without_repeats_stays_unexplained(self):
        out = L.disposition(base_event())
        self.assertEqual(out["disposition"], L.DISPOSITION_INVESTIGATION)

    def test_single_repeat_cannot_confirm_the_onset(self):
        out = L.disposition(base_event(), repeat_onsets_w=[238.0])
        self.assertEqual(out["disposition"], L.DISPOSITION_INVESTIGATION)

    def test_reproducible_unit_onset_raises_a_nonconformance(self):
        out = L.disposition(base_event(), repeat_onsets_w=[238.0, 241.0])
        self.assertEqual(out["disposition"], L.DISPOSITION_NONCONFORMANCE)
        self.assertEqual(out["reproducibility"]["verdict"], L.VERDICT_REPRODUCIBLE)

    def test_nonconformance_caps_below_the_lowest_onset(self):
        out = L.disposition(base_event(), repeat_onsets_w=[238.0, 241.0])
        self.assertLess(out["declarable_cap_w"], 238.0)
        self.assertAlmostEqual(
            out["declarable_cap_w"], 238.0 * L.ONSET_CAP_FRACTION, places=9
        )

    def test_scattered_repeats_stay_unexplained(self):
        out = L.disposition(base_event(), repeat_onsets_w=[150.0, 400.0])
        self.assertEqual(out["disposition"], L.DISPOSITION_INVESTIGATION)
        self.assertIsNone(out["declarable_cap_w"])

    def test_open_attribution_with_repeats_stays_unexplained(self):
        out = L.disposition(
            base_event(seeding_active=False), repeat_onsets_w=[238.0, 241.0]
        )
        self.assertEqual(out["disposition"], L.DISPOSITION_INVESTIGATION)

    def test_empty_repeat_list_raises(self):
        with self.assertRaises(ValueError):
            L.disposition(base_event(), repeat_onsets_w=[])

    def test_non_list_repeats_raise(self):
        with self.assertRaises(ValueError):
            L.disposition(base_event(), repeat_onsets_w=238.0)

    def test_disposition_carries_the_backoff_level(self):
        out = L.disposition(base_event())
        self.assertLess(out["backoff_level_w"], 240.0)

    def test_invalid_record_propagates_from_disposition(self):
        with self.assertRaises(ValueError):
            L.disposition(base_event(chamber_pressure_pa=0.0))


if __name__ == "__main__":
    unittest.main()
