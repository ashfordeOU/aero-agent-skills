#!/usr/bin/env python3
"""Contract test for the coverglass qualification schedule, clause 8.6.2 (offline)."""

import copy
import unittest

from e2008_coverglass_qualification_schedule_logic import (
    DEFAULT_COVERGLASS_SCHEDULE_POLICY,
    REQUIRED_COVERGLASS_QUALIFICATION_STEPS,
    SCHEDULE_NOT_RUNNABLE,
    SCHEDULE_RUNNABLE,
    STEP_DWELL_SHORT,
    STEP_OVERRUNS_MILESTONE,
    STEP_PREREQUISITE_ABSENT,
    STEP_SCHEDULED,
    STEP_STARTS_BEFORE_PREREQUISITE_ENDS,
    assess_coverglass_qualification_schedule,
    assess_schedule_step,
    campaign_window,
    milestone_float_days,
    normalise_schedule,
    required_coverglass_qualification_steps,
    resolve_dated_precedence,
    step_duration_days,
    validate_schedule_policy,
    worst_step_verdict,
)

REQUIRED_BY = "2026-06-01"

CLEAN_STEPS = (
    ("coverglass-lot-manufacture", "2026-01-05", "2026-01-16"),
    ("coverglass-lot-identification", "2026-01-19", "2026-01-20"),
    ("coverglass-incoming-visual-inspection", "2026-01-21", "2026-01-23"),
    ("coverglass-dimensional-measurement", "2026-01-26", "2026-01-28"),
    ("coverglass-baseline-transmittance-measurement", "2026-01-26", "2026-01-30"),
    ("coverglass-surface-resistivity-measurement", "2026-02-02", "2026-02-03"),
    ("coverglass-thermal-cycling", "2026-02-09", "2026-03-10"),
    ("coverglass-ultraviolet-exposure", "2026-02-09", "2026-04-10"),
    ("coverglass-particle-irradiation", "2026-02-09", "2026-02-20"),
    ("coverglass-humidity-exposure", "2026-02-23", "2026-03-06"),
    (
        "coverglass-post-exposure-transmittance-measurement",
        "2026-04-13",
        "2026-04-17",
    ),
    ("coverglass-post-exposure-visual-inspection", "2026-04-13", "2026-04-15"),
    ("coverglass-qualification-report", "2026-04-20", "2026-04-30"),
)


def _steps(drop=(), **moves):
    """The clean dated sequence, with named steps dropped or re-dated."""
    built = []
    for name, starts_on, ends_on in CLEAN_STEPS:
        if name in drop:
            continue
        if name in moves:
            starts_on, ends_on = moves[name]
        built.append({"name": name, "starts_on": starts_on, "ends_on": ends_on})
    return built


def _plan(steps=None, **overrides):
    plan = {
        "campaign_id": "cg-qual-2026",
        "required_by": REQUIRED_BY,
        "steps": steps if steps is not None else _steps(),
    }
    plan.update(overrides)
    return plan


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_schedule_policy(DEFAULT_COVERGLASS_SCHEDULE_POLICY),
            DEFAULT_COVERGLASS_SCHEDULE_POLICY,
        )

    def test_default_policy_enforces_dated_precedence(self):
        self.assertTrue(DEFAULT_COVERGLASS_SCHEDULE_POLICY["enforce_dated_precedence"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule_policy("run it in order")

    def test_negative_float_requirement_rejected(self):
        broken = copy.deepcopy(DEFAULT_COVERGLASS_SCHEDULE_POLICY)
        broken["min_milestone_float_days"] = -5
        with self.assertRaises(ValueError):
            validate_schedule_policy(broken)

    def test_non_integer_float_requirement_rejected(self):
        broken = copy.deepcopy(DEFAULT_COVERGLASS_SCHEDULE_POLICY)
        broken["min_milestone_float_days"] = 10.5
        with self.assertRaises(ValueError):
            validate_schedule_policy(broken)

    def test_out_of_range_step_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_COVERGLASS_SCHEDULE_POLICY)
        broken["min_declared_step_fraction"] = 1.4
        with self.assertRaises(ValueError):
            validate_schedule_policy(broken)


class RequiredStepTests(unittest.TestCase):
    def test_the_step_map_is_returned_as_a_copy(self):
        steps = required_coverglass_qualification_steps()
        self.assertEqual(sorted(steps), sorted(REQUIRED_COVERGLASS_QUALIFICATION_STEPS))
        steps.pop("coverglass-qualification-report")
        self.assertIn(
            "coverglass-qualification-report", REQUIRED_COVERGLASS_QUALIFICATION_STEPS
        )

    def test_the_ultraviolet_exposure_carries_the_longest_dwell(self):
        steps = required_coverglass_qualification_steps()
        longest = max(
            steps, key=lambda name: steps[name]["min_duration_days"]
        )
        self.assertEqual(longest, "coverglass-ultraviolet-exposure")

    def test_the_report_closes_the_sequence(self):
        steps = required_coverglass_qualification_steps()
        depended_on = set()
        for spec in steps.values():
            depended_on |= set(spec["prerequisites"])
        self.assertNotIn("coverglass-qualification-report", depended_on)

    def test_the_post_exposure_measurement_waits_on_every_exposure(self):
        steps = required_coverglass_qualification_steps()
        prerequisites = set(
            steps["coverglass-post-exposure-transmittance-measurement"][
                "prerequisites"
            ]
        )
        self.assertIn("coverglass-ultraviolet-exposure", prerequisites)
        self.assertIn("coverglass-humidity-exposure", prerequisites)


class NormaliseTests(unittest.TestCase):
    def test_the_clean_sequence_reads_back_every_step(self):
        schedule = normalise_schedule(_steps())
        self.assertEqual(len(schedule), len(CLEAN_STEPS))

    def test_a_step_the_campaign_does_not_know_is_rejected(self):
        steps = _steps()
        steps.append(
            {
                "name": "coverglass-polishing-trial",
                "starts_on": "2026-02-01",
                "ends_on": "2026-02-02",
            }
        )
        with self.assertRaises(ValueError):
            normalise_schedule(steps)

    def test_a_repeated_step_is_rejected(self):
        steps = _steps()
        steps.append(dict(steps[0]))
        with self.assertRaises(ValueError):
            normalise_schedule(steps)

    def test_a_step_ending_before_it_starts_is_rejected(self):
        steps = _steps(
            **{"coverglass-thermal-cycling": ("2026-03-10", "2026-02-09")}
        )
        with self.assertRaises(ValueError):
            normalise_schedule(steps)

    def test_an_undated_step_is_rejected(self):
        steps = _steps()
        del steps[0]["ends_on"]
        with self.assertRaises(ValueError):
            normalise_schedule(steps)

    def test_a_date_that_is_not_a_calendar_date_is_rejected(self):
        steps = _steps(**{"coverglass-lot-manufacture": ("5 January 2026", "2026-01-16")})
        with self.assertRaises(ValueError):
            normalise_schedule(steps)

    def test_an_empty_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_schedule([])

    def test_a_non_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_schedule("thermal cycling then report")


class DurationTests(unittest.TestCase):
    def test_a_one_day_step_counts_as_one_day(self):
        self.assertEqual(
            step_duration_days({"starts_on": "2026-02-09", "ends_on": "2026-02-09"}), 1
        )

    def test_the_duration_counts_both_end_days(self):
        self.assertEqual(
            step_duration_days({"starts_on": "2026-02-09", "ends_on": "2026-02-20"}), 12
        )

    def test_a_reversed_step_is_rejected(self):
        with self.assertRaises(ValueError):
            step_duration_days({"starts_on": "2026-02-20", "ends_on": "2026-02-09"})

    def test_a_non_mapping_step_is_rejected(self):
        with self.assertRaises(ValueError):
            step_duration_days("twelve days")


class PrecedenceTests(unittest.TestCase):
    def test_the_clean_sequence_satisfies_every_prerequisite(self):
        resolution = resolve_dated_precedence(normalise_schedule(_steps()))
        self.assertTrue(all(entry["satisfied"] for entry in resolution.values()))

    def test_a_dropped_prerequisite_is_named_as_absent(self):
        schedule = normalise_schedule(
            _steps(drop=("coverglass-baseline-transmittance-measurement",))
        )
        resolution = resolve_dated_precedence(schedule)
        self.assertEqual(
            resolution["coverglass-thermal-cycling"]["absent_prerequisites"],
            ["coverglass-baseline-transmittance-measurement"],
        )

    def test_a_prerequisite_finishing_after_the_step_starts_is_late(self):
        schedule = normalise_schedule(
            _steps(**{"coverglass-thermal-cycling": ("2026-01-29", "2026-03-10")})
        )
        resolution = resolve_dated_precedence(schedule)
        self.assertEqual(
            resolution["coverglass-thermal-cycling"]["late_prerequisites"],
            ["coverglass-baseline-transmittance-measurement"],
        )

    def test_a_prerequisite_finishing_on_the_start_day_is_not_late(self):
        schedule = normalise_schedule(
            _steps(**{"coverglass-thermal-cycling": ("2026-01-30", "2026-03-10")})
        )
        resolution = resolve_dated_precedence(schedule)
        self.assertTrue(resolution["coverglass-thermal-cycling"]["satisfied"])

    def test_an_empty_schedule_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_dated_precedence({})


class WindowTests(unittest.TestCase):
    def test_the_campaign_window_spans_the_declared_dates(self):
        window = campaign_window(normalise_schedule(_steps()))
        self.assertEqual(window["campaign_start"], "2026-01-05")
        self.assertEqual(window["campaign_end"], "2026-04-30")

    def test_the_span_counts_both_end_days(self):
        window = campaign_window(normalise_schedule(_steps()))
        self.assertEqual(window["span_days"], 116)

    def test_the_float_to_the_need_date_is_reported(self):
        schedule = normalise_schedule(_steps())
        self.assertEqual(milestone_float_days(schedule, REQUIRED_BY), 32)

    def test_a_need_date_inside_the_campaign_gives_negative_float(self):
        schedule = normalise_schedule(_steps())
        self.assertLess(milestone_float_days(schedule, "2026-04-01"), 0)

    def test_a_malformed_need_date_is_rejected(self):
        schedule = normalise_schedule(_steps())
        with self.assertRaises(ValueError):
            milestone_float_days(schedule, "first of June")

    def test_an_empty_schedule_has_no_window(self):
        with self.assertRaises(ValueError):
            campaign_window({})


class StepVerdictTests(unittest.TestCase):
    def _assess(self, name, steps=None, required_by=REQUIRED_BY, policy=None):
        schedule = normalise_schedule(steps if steps is not None else _steps())
        resolution = resolve_dated_precedence(schedule)
        if policy is None:
            policy = DEFAULT_COVERGLASS_SCHEDULE_POLICY
        return assess_schedule_step(name, schedule, resolution, required_by, policy)

    def test_a_clean_step_is_scheduled(self):
        result = self._assess("coverglass-thermal-cycling")
        self.assertEqual(result["verdict"], STEP_SCHEDULED)
        self.assertTrue(result["scheduled"])

    def test_an_absent_prerequisite_outranks_a_dated_break(self):
        steps = _steps(
            drop=("coverglass-baseline-transmittance-measurement",),
            **{"coverglass-thermal-cycling": ("2026-01-27", "2026-03-10")}
        )
        result = self._assess("coverglass-thermal-cycling", steps)
        self.assertEqual(result["verdict"], STEP_PREREQUISITE_ABSENT)

    def test_a_dated_break_outranks_a_short_dwell(self):
        steps = _steps(**{"coverglass-thermal-cycling": ("2026-01-29", "2026-02-01")})
        result = self._assess("coverglass-thermal-cycling", steps)
        self.assertEqual(result["verdict"], STEP_STARTS_BEFORE_PREREQUISITE_ENDS)

    def test_a_short_dwell_is_caught(self):
        steps = _steps(
            **{"coverglass-ultraviolet-exposure": ("2026-02-09", "2026-02-20")}
        )
        result = self._assess("coverglass-ultraviolet-exposure", steps)
        self.assertEqual(result["verdict"], STEP_DWELL_SHORT)
        self.assertFalse(result["dwell_sufficient"])
        self.assertEqual(result["duration_days"], 12)

    def test_a_short_dwell_outranks_a_milestone_overrun(self):
        steps = _steps(
            **{"coverglass-ultraviolet-exposure": ("2026-02-09", "2026-02-20")}
        )
        result = self._assess(
            "coverglass-ultraviolet-exposure", steps, required_by="2026-02-10"
        )
        self.assertEqual(result["verdict"], STEP_DWELL_SHORT)

    def test_a_step_finishing_after_the_need_date_overruns_the_milestone(self):
        result = self._assess(
            "coverglass-qualification-report", required_by="2026-04-25"
        )
        self.assertEqual(result["verdict"], STEP_OVERRUNS_MILESTONE)
        self.assertFalse(result["within_milestone"])

    def test_a_step_finishing_on_the_need_date_is_within_the_milestone(self):
        result = self._assess(
            "coverglass-qualification-report", required_by="2026-04-30"
        )
        self.assertTrue(result["within_milestone"])
        self.assertEqual(result["verdict"], STEP_SCHEDULED)

    def test_a_dated_break_stands_when_the_policy_drops_precedence(self):
        policy = copy.deepcopy(DEFAULT_COVERGLASS_SCHEDULE_POLICY)
        policy["enforce_dated_precedence"] = False
        steps = _steps(**{"coverglass-thermal-cycling": ("2026-01-29", "2026-03-10")})
        result = self._assess("coverglass-thermal-cycling", steps, policy=policy)
        self.assertEqual(result["verdict"], STEP_SCHEDULED)

    def test_a_short_dwell_stands_when_the_policy_drops_the_minimum(self):
        policy = copy.deepcopy(DEFAULT_COVERGLASS_SCHEDULE_POLICY)
        policy["enforce_minimum_dwell"] = False
        steps = _steps(
            **{"coverglass-ultraviolet-exposure": ("2026-02-09", "2026-02-20")}
        )
        result = self._assess(
            "coverglass-ultraviolet-exposure", steps, policy=policy
        )
        self.assertEqual(result["verdict"], STEP_SCHEDULED)

    def test_a_step_outside_the_read_schedule_is_rejected(self):
        with self.assertRaises(ValueError):
            self._assess("coverglass-surface-resistivity-measurement", _steps(
                drop=("coverglass-surface-resistivity-measurement",)
            ))

    def test_findings_name_the_step(self):
        steps = _steps(**{"coverglass-thermal-cycling": ("2026-01-29", "2026-03-10")})
        result = self._assess("coverglass-thermal-cycling", steps)
        self.assertTrue(
            any("coverglass-thermal-cycling" in f for f in result["findings"])
        )


class WorstVerdictTests(unittest.TestCase):
    def test_the_most_serious_arm_wins(self):
        self.assertEqual(
            worst_step_verdict([STEP_DWELL_SHORT, STEP_PREREQUISITE_ABSENT]),
            STEP_PREREQUISITE_ABSENT,
        )

    def test_a_clean_set_reports_scheduled(self):
        self.assertEqual(
            worst_step_verdict([STEP_SCHEDULED, STEP_SCHEDULED]), STEP_SCHEDULED
        )

    def test_an_unknown_verdict_is_rejected(self):
        with self.assertRaises(ValueError):
            worst_step_verdict(["step-probably-fine"])

    def test_an_empty_verdict_set_is_rejected(self):
        with self.assertRaises(ValueError):
            worst_step_verdict([])


class ScheduleTests(unittest.TestCase):
    def test_a_clean_campaign_is_runnable(self):
        result = assess_coverglass_qualification_schedule(_plan())
        self.assertEqual(result["verdict"], SCHEDULE_RUNNABLE)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["every_step_declared"])

    def test_the_campaign_window_and_float_are_reported(self):
        result = assess_coverglass_qualification_schedule(_plan())
        self.assertEqual(result["campaign_window"]["campaign_end"], "2026-04-30")
        self.assertEqual(result["milestone_float_days"], 32)

    def test_an_undeclared_step_is_named_and_blocks_the_campaign(self):
        plan = _plan(_steps(drop=("coverglass-surface-resistivity-measurement",)))
        result = assess_coverglass_qualification_schedule(plan)
        self.assertEqual(result["verdict"], SCHEDULE_NOT_RUNNABLE)
        self.assertEqual(
            result["undeclared_steps"], ["coverglass-surface-resistivity-measurement"]
        )

    def test_the_declared_step_share_is_reported(self):
        plan = _plan(_steps(drop=("coverglass-surface-resistivity-measurement",)))
        result = assess_coverglass_qualification_schedule(plan)
        self.assertAlmostEqual(
            result["declared_step_fraction"], 12.0 / 13.0, places=9
        )

    def test_a_clean_campaign_declares_every_step(self):
        result = assess_coverglass_qualification_schedule(_plan())
        self.assertAlmostEqual(result["declared_step_fraction"], 1.0, places=9)

    def test_a_dated_precedence_break_blocks_the_campaign(self):
        plan = _plan(
            _steps(**{"coverglass-thermal-cycling": ("2026-01-29", "2026-03-10")})
        )
        result = assess_coverglass_qualification_schedule(plan)
        self.assertEqual(result["verdict"], SCHEDULE_NOT_RUNNABLE)
        self.assertEqual(
            result["grouped_by_verdict"][STEP_STARTS_BEFORE_PREREQUISITE_ENDS],
            ["coverglass-thermal-cycling"],
        )

    def test_a_shortened_exposure_blocks_the_campaign(self):
        plan = _plan(
            _steps(
                **{"coverglass-ultraviolet-exposure": ("2026-02-09", "2026-02-20")}
            )
        )
        result = assess_coverglass_qualification_schedule(plan)
        self.assertEqual(
            result["open_step_ids"], ["coverglass-ultraviolet-exposure"]
        )
        self.assertEqual(result["worst_verdict"], STEP_DWELL_SHORT)

    def test_a_need_date_inside_the_campaign_blocks_it(self):
        plan = _plan(required_by="2026-04-25")
        result = assess_coverglass_qualification_schedule(plan)
        self.assertEqual(result["verdict"], SCHEDULE_NOT_RUNNABLE)
        self.assertEqual(
            result["grouped_by_verdict"][STEP_OVERRUNS_MILESTONE],
            ["coverglass-qualification-report"],
        )

    def test_thin_float_blocks_a_campaign_whose_steps_all_fit(self):
        plan = _plan(required_by="2026-05-05")
        result = assess_coverglass_qualification_schedule(plan)
        self.assertEqual(result["verdict"], SCHEDULE_NOT_RUNNABLE)
        self.assertEqual(result["open_step_ids"], [])
        self.assertFalse(result["milestone_float_sufficient"])
        self.assertEqual(result["milestone_float_days"], 5)

    def test_float_exactly_on_the_required_reserve_is_sufficient(self):
        plan = _plan(required_by="2026-05-10")
        result = assess_coverglass_qualification_schedule(plan)
        self.assertEqual(result["milestone_float_days"], 10)
        self.assertTrue(result["milestone_float_sufficient"])
        self.assertEqual(result["verdict"], SCHEDULE_RUNNABLE)

    def test_the_milestone_arm_stands_down_when_the_policy_drops_it(self):
        policy = copy.deepcopy(DEFAULT_COVERGLASS_SCHEDULE_POLICY)
        policy["enforce_milestone"] = False
        result = assess_coverglass_qualification_schedule(
            _plan(required_by="2026-04-25"), policy
        )
        self.assertEqual(result["verdict"], SCHEDULE_RUNNABLE)

    def test_step_assessments_come_back_in_name_order(self):
        result = assess_coverglass_qualification_schedule(_plan())
        names = [entry["name"] for entry in result["step_assessments"]]
        self.assertEqual(names, sorted(names))

    def test_a_campaign_without_an_identifier_is_rejected(self):
        plan = _plan()
        del plan["campaign_id"]
        with self.assertRaises(ValueError):
            assess_coverglass_qualification_schedule(plan)

    def test_a_campaign_without_a_need_date_is_rejected(self):
        plan = _plan()
        del plan["required_by"]
        with self.assertRaises(ValueError):
            assess_coverglass_qualification_schedule(plan)

    def test_a_non_mapping_plan_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_qualification_schedule(_steps())

    def test_the_campaign_carries_every_step_finding(self):
        plan = _plan(
            _steps(
                **{"coverglass-ultraviolet-exposure": ("2026-02-09", "2026-02-20")}
            )
        )
        result = assess_coverglass_qualification_schedule(plan)
        self.assertTrue(
            any("minimum dwell" in f for f in result["findings"])
        )

    def test_dropping_a_prerequisite_reports_both_arms(self):
        plan = _plan(_steps(drop=("coverglass-humidity-exposure",)))
        result = assess_coverglass_qualification_schedule(plan)
        self.assertIn("coverglass-humidity-exposure", result["undeclared_steps"])
        self.assertEqual(
            result["grouped_by_verdict"][STEP_PREREQUISITE_ABSENT],
            [
                "coverglass-post-exposure-transmittance-measurement",
                "coverglass-post-exposure-visual-inspection",
            ],
        )


if __name__ == "__main__":
    unittest.main()
