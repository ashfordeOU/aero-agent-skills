#!/usr/bin/env python3
"""Contract test for the blocking diode production schedule, clause 12.5.3 (offline)."""

import copy
import unittest
from datetime import date

from e2008_blocking_diode_production_schedule_logic import (
    ACTIVITY_ADDED_AFTER_LOT_START,
    ACTIVITY_OVERRUNS_MILESTONE,
    ACTIVITY_PHASES,
    ACTIVITY_PHASE_OUT_OF_ORDER,
    ACTIVITY_SCHEDULED,
    ACTIVITY_STARTS_BEFORE_LOT_START,
    DEFAULT_SCHEDULE_POLICY,
    SCHEDULE_NOT_RUNNABLE,
    SCHEDULE_RUNNABLE,
    activity_duration_days,
    assess_blocking_diode_production_schedule,
    assess_scheduled_activity,
    campaign_window,
    milestone_float_days,
    normalise_activities,
    phase_window,
    schedule_issue_chronology,
    validate_schedule_policy,
    worst_activity_verdict,
)

ACTIVITIES = [
    {
        "activity_id": "wafer-fabrication",
        "phase": "production",
        "planned_start": "2026-03-02",
        "planned_end": "2026-03-20",
        "recorded_on": "2026-02-10",
    },
    {
        "activity_id": "assembly-and-encapsulation",
        "phase": "production",
        "planned_start": "2026-03-23",
        "planned_end": "2026-04-03",
        "recorded_on": "2026-02-10",
    },
    {
        "activity_id": "electrical-characterisation",
        "phase": "testing",
        "planned_start": "2026-04-06",
        "planned_end": "2026-04-17",
        "recorded_on": "2026-02-10",
    },
    {
        "activity_id": "environmental-campaign",
        "phase": "testing",
        "planned_start": "2026-04-20",
        "planned_end": "2026-05-29",
        "recorded_on": "2026-02-10",
    },
]


def _activities(extra=None, drop=None, **overrides):
    rows = [
        copy.deepcopy(row) for row in ACTIVITIES if row["activity_id"] != drop
    ]
    if extra:
        rows.append(copy.deepcopy(extra))
    for row in rows:
        if row["activity_id"] in overrides:
            row.update(overrides[row["activity_id"]])
    return rows


def _schedule(activities=None, **overrides):
    schedule = {
        "schedule_id": "sch-bd-alpha-lot-1",
        "diode_type": "bd-type-alpha",
        "issued_on": "2026-02-10",
        "lot_start_date": "2026-03-02",
        "required_by": "2026-06-30",
        "activities": activities if activities is not None else _activities(),
    }
    schedule.update(overrides)
    return schedule


def _context(**overrides):
    context = {
        "lot_start_date": "2026-03-02",
        "required_by": "2026-06-30",
        "production_end": "2026-04-03",
    }
    context.update(overrides)
    return context


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_schedule_policy(DEFAULT_SCHEDULE_POLICY), DEFAULT_SCHEDULE_POLICY
        )

    def test_default_policy_requires_the_schedule_before_the_lot(self):
        self.assertTrue(DEFAULT_SCHEDULE_POLICY["require_schedule_before_lot_start"])

    def test_default_policy_refuses_an_activity_added_after_the_lot_started(self):
        self.assertFalse(
            DEFAULT_SCHEDULE_POLICY["admit_activity_added_after_lot_start"]
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule_policy("compile it first")

    def test_non_boolean_phase_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCHEDULE_POLICY)
        broken["enforce_phase_order"] = "yes"
        with self.assertRaises(ValueError):
            validate_schedule_policy(broken)

    def test_out_of_range_activity_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCHEDULE_POLICY)
        broken["min_scheduled_activity_fraction"] = 3.0
        with self.assertRaises(ValueError):
            validate_schedule_policy(broken)

    def test_production_and_testing_are_the_two_phases(self):
        self.assertEqual(sorted(ACTIVITY_PHASES), ["production", "testing"])


class ActivityShapeTests(unittest.TestCase):
    def test_the_activities_read_back_in_start_order(self):
        shuffled = list(reversed(_activities()))
        self.assertEqual(
            [row["activity_id"] for row in normalise_activities(shuffled)],
            [
                "wafer-fabrication",
                "assembly-and-encapsulation",
                "electrical-characterisation",
                "environmental-campaign",
            ],
        )

    def test_a_repeated_activity_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalise_activities(_activities(extra=copy.deepcopy(ACTIVITIES[0])))

    def test_an_undated_activity_rejected(self):
        rows = _activities()
        del rows[0]["planned_start"]
        with self.assertRaises(ValueError):
            normalise_activities(rows)

    def test_an_activity_ending_before_it_starts_rejected(self):
        with self.assertRaises(ValueError):
            normalise_activities(
                _activities(**{"wafer-fabrication": {"planned_end": "2026-03-01"}})
            )

    def test_an_unknown_phase_rejected(self):
        with self.assertRaises(ValueError):
            normalise_activities(
                _activities(**{"wafer-fabrication": {"phase": "packaging"}})
            )

    def test_a_non_iso_date_rejected(self):
        with self.assertRaises(ValueError):
            normalise_activities(
                _activities(**{"wafer-fabrication": {"planned_start": "2 March"}})
            )

    def test_an_empty_activity_list_rejected(self):
        with self.assertRaises(ValueError):
            normalise_activities([])

    def test_an_activity_may_carry_no_record_date(self):
        rows = _activities()
        del rows[0]["recorded_on"]
        self.assertIsNone(normalise_activities(rows)[0]["recorded_on"])

    def test_a_single_day_activity_lasts_one_day(self):
        self.assertEqual(
            activity_duration_days(
                {"planned_start": "2026-03-02", "planned_end": "2026-03-02"}
            ),
            1,
        )

    def test_a_nineteen_day_activity_counts_both_ends(self):
        self.assertEqual(activity_duration_days(ACTIVITIES[0]), 19)

    def test_a_backwards_duration_rejected(self):
        with self.assertRaises(ValueError):
            activity_duration_days(
                {"planned_start": "2026-03-20", "planned_end": "2026-03-02"}
            )


class ChronologyTests(unittest.TestCase):
    def test_a_schedule_issued_before_the_lot_is_compiled_in_time(self):
        read = schedule_issue_chronology(_schedule())
        self.assertTrue(read["compiled_before_lot_start"])
        self.assertEqual(read["days_before_lot_start"], 20)

    def test_a_schedule_issued_on_the_lot_start_day_is_compiled_in_time(self):
        read = schedule_issue_chronology(_schedule(issued_on="2026-03-02"))
        self.assertTrue(read["compiled_before_lot_start"])
        self.assertEqual(read["days_before_lot_start"], 0)

    def test_a_schedule_written_up_after_the_lot_started_is_caught(self):
        read = schedule_issue_chronology(_schedule(issued_on="2026-03-16"))
        self.assertFalse(read["compiled_before_lot_start"])
        self.assertEqual(read["days_before_lot_start"], -14)

    def test_a_relaxed_policy_accepts_a_late_schedule(self):
        relaxed = copy.deepcopy(DEFAULT_SCHEDULE_POLICY)
        relaxed["require_schedule_before_lot_start"] = False
        read = schedule_issue_chronology(_schedule(issued_on="2026-03-16"), relaxed)
        self.assertTrue(read["compiled_before_lot_start"])

    def test_a_schedule_without_a_lot_start_date_rejected(self):
        schedule = _schedule()
        del schedule["lot_start_date"]
        with self.assertRaises(ValueError):
            schedule_issue_chronology(schedule)


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.activities = normalise_activities(_activities())

    def test_the_production_window_spans_its_own_activities(self):
        read = phase_window(self.activities, "production")
        self.assertEqual(read["start"], date(2026, 3, 2))
        self.assertEqual(read["end"], date(2026, 4, 3))
        self.assertEqual(read["activity_count"], 2)

    def test_the_testing_window_spans_its_own_activities(self):
        read = phase_window(self.activities, "testing")
        self.assertEqual(read["end"], date(2026, 5, 29))

    def test_an_absent_phase_has_no_window(self):
        only_production = normalise_activities(
            [row for row in _activities() if row["phase"] == "production"]
        )
        self.assertIsNone(phase_window(only_production, "testing"))

    def test_an_unknown_phase_window_rejected(self):
        with self.assertRaises(ValueError):
            phase_window(self.activities, "shipping")

    def test_the_campaign_window_runs_end_to_end(self):
        read = campaign_window(self.activities)
        self.assertEqual(read["start"], "2026-03-02")
        self.assertEqual(read["end"], "2026-05-29")
        self.assertEqual(read["activity_count"], 4)

    def test_an_empty_campaign_window_rejected(self):
        with self.assertRaises(ValueError):
            campaign_window([])

    def test_the_float_is_the_gap_to_the_day_the_diodes_are_owed(self):
        self.assertEqual(
            milestone_float_days(self.activities, "2026-06-30"), 32
        )

    def test_a_campaign_running_past_the_milestone_has_negative_float(self):
        self.assertEqual(
            milestone_float_days(self.activities, "2026-05-01"), -28
        )

    def test_float_without_activities_rejected(self):
        with self.assertRaises(ValueError):
            milestone_float_days([], "2026-06-30")


class ActivityVerdictTests(unittest.TestCase):
    def test_a_clean_production_activity_is_scheduled(self):
        result = assess_scheduled_activity(ACTIVITIES[0], _context())
        self.assertEqual(result["verdict"], ACTIVITY_SCHEDULED)
        self.assertTrue(result["scheduled"])

    def test_a_clean_test_activity_is_scheduled(self):
        result = assess_scheduled_activity(ACTIVITIES[2], _context())
        self.assertEqual(result["verdict"], ACTIVITY_SCHEDULED)

    def test_an_activity_recorded_after_the_lot_started_is_caught(self):
        activity = copy.deepcopy(ACTIVITIES[3])
        activity["recorded_on"] = "2026-03-30"
        result = assess_scheduled_activity(activity, _context())
        self.assertEqual(result["verdict"], ACTIVITY_ADDED_AFTER_LOT_START)

    def test_an_activity_recorded_on_the_lot_start_day_is_scheduled(self):
        activity = copy.deepcopy(ACTIVITIES[0])
        activity["recorded_on"] = "2026-03-02"
        result = assess_scheduled_activity(activity, _context())
        self.assertEqual(result["verdict"], ACTIVITY_SCHEDULED)

    def test_an_activity_starting_before_the_lot_is_caught(self):
        activity = copy.deepcopy(ACTIVITIES[0])
        activity["planned_start"] = "2026-02-20"
        result = assess_scheduled_activity(activity, _context())
        self.assertEqual(result["verdict"], ACTIVITY_STARTS_BEFORE_LOT_START)

    def test_a_test_activity_overlapping_production_is_caught(self):
        activity = copy.deepcopy(ACTIVITIES[2])
        activity["planned_start"] = "2026-03-30"
        result = assess_scheduled_activity(activity, _context())
        self.assertEqual(result["verdict"], ACTIVITY_PHASE_OUT_OF_ORDER)

    def test_a_production_activity_inside_production_is_not_out_of_order(self):
        result = assess_scheduled_activity(ACTIVITIES[1], _context())
        self.assertEqual(result["verdict"], ACTIVITY_SCHEDULED)

    def test_a_relaxed_policy_lets_the_phases_overlap(self):
        relaxed = copy.deepcopy(DEFAULT_SCHEDULE_POLICY)
        relaxed["enforce_phase_order"] = False
        activity = copy.deepcopy(ACTIVITIES[2])
        activity["planned_start"] = "2026-03-30"
        result = assess_scheduled_activity(activity, _context(), relaxed)
        self.assertEqual(result["verdict"], ACTIVITY_SCHEDULED)

    def test_an_activity_running_past_the_milestone_is_caught(self):
        activity = copy.deepcopy(ACTIVITIES[3])
        activity["planned_end"] = "2026-07-20"
        result = assess_scheduled_activity(activity, _context())
        self.assertEqual(result["verdict"], ACTIVITY_OVERRUNS_MILESTONE)
        self.assertEqual(result["milestone_slip_days"], 20)

    def test_an_activity_ending_on_the_milestone_day_is_scheduled(self):
        activity = copy.deepcopy(ACTIVITIES[3])
        activity["planned_end"] = "2026-06-30"
        result = assess_scheduled_activity(activity, _context())
        self.assertEqual(result["verdict"], ACTIVITY_SCHEDULED)

    def test_a_late_record_outranks_a_milestone_overrun(self):
        activity = copy.deepcopy(ACTIVITIES[3])
        activity["recorded_on"] = "2026-04-01"
        activity["planned_end"] = "2026-07-20"
        result = assess_scheduled_activity(activity, _context())
        self.assertEqual(result["verdict"], ACTIVITY_ADDED_AFTER_LOT_START)

    def test_the_days_after_lot_start_are_reported(self):
        result = assess_scheduled_activity(ACTIVITIES[2], _context())
        self.assertEqual(result["days_after_lot_start"], 35)

    def test_an_activity_without_an_identifier_rejected(self):
        activity = copy.deepcopy(ACTIVITIES[0])
        del activity["activity_id"]
        with self.assertRaises(ValueError):
            assess_scheduled_activity(activity, _context())

    def test_a_non_mapping_context_rejected(self):
        with self.assertRaises(ValueError):
            assess_scheduled_activity(ACTIVITIES[0], "2026-03-02")


class RankTests(unittest.TestCase):
    def test_a_late_record_outranks_every_other_arm(self):
        self.assertEqual(
            worst_activity_verdict(
                [
                    ACTIVITY_SCHEDULED,
                    ACTIVITY_OVERRUNS_MILESTONE,
                    ACTIVITY_ADDED_AFTER_LOT_START,
                ]
            ),
            ACTIVITY_ADDED_AFTER_LOT_START,
        )

    def test_an_early_start_outranks_a_phase_inversion(self):
        self.assertEqual(
            worst_activity_verdict(
                [ACTIVITY_PHASE_OUT_OF_ORDER, ACTIVITY_STARTS_BEFORE_LOT_START]
            ),
            ACTIVITY_STARTS_BEFORE_LOT_START,
        )

    def test_a_clean_schedule_ranks_as_scheduled(self):
        self.assertEqual(
            worst_activity_verdict([ACTIVITY_SCHEDULED]), ACTIVITY_SCHEDULED
        )

    def test_an_unknown_verdict_rejected(self):
        with self.assertRaises(ValueError):
            worst_activity_verdict(["activity-looks-fine"])

    def test_an_empty_verdict_set_rejected(self):
        with self.assertRaises(ValueError):
            worst_activity_verdict([])


class ScheduleTests(unittest.TestCase):
    def test_a_clean_schedule_is_runnable(self):
        result = assess_blocking_diode_production_schedule(_schedule())
        self.assertEqual(result["verdict"], SCHEDULE_RUNNABLE)
        self.assertTrue(result["every_activity_scheduled"])
        self.assertEqual(result["findings"], [])

    def test_a_clean_schedule_places_every_activity(self):
        result = assess_blocking_diode_production_schedule(_schedule())
        self.assertAlmostEqual(
            result["scheduled_activity_fraction"], 1.0, places=9
        )

    def test_a_schedule_written_after_the_lot_started_is_not_runnable(self):
        result = assess_blocking_diode_production_schedule(
            _schedule(issued_on="2026-03-16")
        )
        self.assertEqual(result["verdict"], SCHEDULE_NOT_RUNNABLE)
        self.assertFalse(result["issue_chronology"]["compiled_before_lot_start"])

    def test_the_late_schedule_finding_names_both_dates(self):
        result = assess_blocking_diode_production_schedule(
            _schedule(issued_on="2026-03-16")
        )
        self.assertTrue(any("2026-03-16" in f for f in result["findings"]))

    def test_one_late_activity_in_four_scores_three_quarters(self):
        result = assess_blocking_diode_production_schedule(
            _schedule(
                _activities(**{"environmental-campaign": {"recorded_on": "2026-04-01"}})
            )
        )
        self.assertAlmostEqual(
            result["scheduled_activity_fraction"], 0.75, places=9
        )
        self.assertEqual(result["verdict"], SCHEDULE_NOT_RUNNABLE)

    def test_the_roll_up_names_the_open_activities(self):
        result = assess_blocking_diode_production_schedule(
            _schedule(
                _activities(**{"environmental-campaign": {"recorded_on": "2026-04-01"}})
            )
        )
        self.assertEqual(result["open_activity_ids"], ["environmental-campaign"])

    def test_the_roll_up_groups_the_activities_by_verdict(self):
        result = assess_blocking_diode_production_schedule(
            _schedule(
                _activities(
                    **{"electrical-characterisation": {"planned_start": "2026-03-30"}}
                )
            )
        )
        self.assertEqual(
            result["grouped_by_verdict"][ACTIVITY_PHASE_OUT_OF_ORDER],
            ["electrical-characterisation"],
        )

    def test_a_schedule_with_no_test_phase_is_not_runnable(self):
        production_only = [
            row for row in _activities() if row["phase"] == "production"
        ]
        result = assess_blocking_diode_production_schedule(
            _schedule(production_only)
        )
        self.assertEqual(result["absent_phases"], ["testing"])
        self.assertEqual(result["verdict"], SCHEDULE_NOT_RUNNABLE)

    def test_the_roll_up_reports_both_phase_windows(self):
        result = assess_blocking_diode_production_schedule(_schedule())
        self.assertEqual(result["production_window"]["end"], "2026-04-03")
        self.assertEqual(result["testing_window"]["start"], "2026-04-06")

    def test_the_roll_up_reports_the_campaign_span(self):
        result = assess_blocking_diode_production_schedule(_schedule())
        self.assertEqual(result["campaign_window"]["span_days"], 89)

    def test_the_roll_up_reports_the_float_to_the_milestone(self):
        result = assess_blocking_diode_production_schedule(_schedule())
        self.assertEqual(result["milestone_float_days"], 32)

    def test_a_schedule_without_a_milestone_reports_no_float(self):
        schedule = _schedule()
        del schedule["required_by"]
        result = assess_blocking_diode_production_schedule(schedule)
        self.assertIsNone(result["milestone_float_days"])

    def test_the_roll_up_reports_the_arm_to_close_first(self):
        result = assess_blocking_diode_production_schedule(
            _schedule(
                _activities(
                    **{
                        "environmental-campaign": {"recorded_on": "2026-04-01"},
                        "electrical-characterisation": {"planned_start": "2026-03-30"},
                    }
                )
            )
        )
        self.assertEqual(result["worst_verdict"], ACTIVITY_ADDED_AFTER_LOT_START)

    def test_a_relaxed_share_accepts_a_partly_placed_schedule(self):
        relaxed = copy.deepcopy(DEFAULT_SCHEDULE_POLICY)
        relaxed["min_scheduled_activity_fraction"] = 0.5
        result = assess_blocking_diode_production_schedule(
            _schedule(
                _activities(**{"environmental-campaign": {"recorded_on": "2026-04-01"}})
            ),
            relaxed,
        )
        self.assertEqual(result["required_activity_fraction"], 0.5)
        self.assertAlmostEqual(
            result["scheduled_activity_fraction"], 0.75, places=9
        )

    def test_a_schedule_without_an_identifier_rejected(self):
        schedule = _schedule()
        del schedule["schedule_id"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_production_schedule(schedule)

    def test_non_mapping_schedule_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_production_schedule(_activities())

    def test_the_roll_up_carries_every_activity_finding(self):
        result = assess_blocking_diode_production_schedule(
            _schedule(
                _activities(**{"wafer-fabrication": {"planned_start": "2026-02-20"}})
            )
        )
        self.assertTrue(any("wafer-fabrication" in f for f in result["findings"]))


if __name__ == "__main__":
    unittest.main()
