#!/usr/bin/env python3
"""Contract test for the new hybrid circuit design approval sequence (offline)."""

import copy
import unittest

from q6005_approval_of_new_circuit_designs_logic import (
    APPROVAL_GRANTED,
    APPROVAL_HELD_BY_FAILURE,
    APPROVAL_PENDING,
    APPROVAL_SEQUENCE_BROKEN,
    GRANT_STAGE,
    NEW_DESIGN_STAGES,
    STAGE_BY_ID,
    STAGE_IDS,
    STAGE_STATES,
    approval_decision,
    completion_fraction,
    failed_stages,
    next_executable_stages,
    plan_new_design_approval,
    remaining_critical_path_days,
    sequence_violations,
    stage_cost_days,
    unmet_prerequisites,
    validate_remaining_days,
    validate_stage_order,
    validate_stage_states,
)

NOTHING_STARTED = {stage_id: "not-started" for stage_id in STAGE_IDS}
ALL_COMPLETE = {stage_id: "complete" for stage_id in STAGE_IDS}
TOTAL_NOMINAL_DAYS = sum(stage["nominal_days"] for stage in NEW_DESIGN_STAGES)


def _states(base, **overrides):
    states = dict(base)
    states.update(overrides)
    return states


def _through(*done):
    return _states(NOTHING_STARTED, **{stage_id: "complete" for stage_id in done})


EARLY = _through("design-definition-review", "technology-and-parts-selection")

# Everything up to the qualification lot is done and the test programme then
# failed; the two stages behind it are untouched, so nothing is out of order.
QUAL_TEST_FAILED = _states(
    _through(
        "design-definition-review",
        "technology-and-parts-selection",
        "engineering-model-build",
        "design-verification-testing",
        "manufacturing-process-identification",
        "qualification-lot-manufacture",
    ),
    **{"qualification-test-programme": "failed"}
)


class StageGraphTests(unittest.TestCase):
    def test_the_stage_tuple_is_a_topological_order(self):
        self.assertTrue(validate_stage_order())

    def test_the_sequence_has_nine_stages(self):
        self.assertEqual(len(STAGE_IDS), 9)
        self.assertEqual(len(STAGE_BY_ID), 9)

    def test_the_first_stage_has_no_prerequisites(self):
        self.assertEqual(STAGE_BY_ID[STAGE_IDS[0]]["prerequisites"], ())

    def test_the_grant_is_the_last_stage(self):
        self.assertEqual(STAGE_IDS[-1], GRANT_STAGE)

    def test_every_stage_carries_a_positive_nominal_duration(self):
        for stage in NEW_DESIGN_STAGES:
            self.assertGreater(stage["nominal_days"], 0, stage["id"])

    def test_four_stage_states_are_offered(self):
        self.assertEqual(len(STAGE_STATES), 4)


class StateValidationTests(unittest.TestCase):
    def test_a_complete_declaration_validates(self):
        self.assertEqual(validate_stage_states(NOTHING_STARTED), NOTHING_STARTED)

    def test_a_missing_stage_is_rejected_not_defaulted(self):
        states = dict(NOTHING_STARTED)
        del states["qualification-test-programme"]
        with self.assertRaises(ValueError):
            validate_stage_states(states)

    def test_an_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage_states(_states(NOTHING_STARTED, **{"lunch": "complete"}))

    def test_an_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage_states(
                _states(NOTHING_STARTED, **{"design-definition-review": "nearly"})
            )

    def test_a_non_mapping_declaration_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage_states("not-started")

    def test_remaining_days_override_validates(self):
        self.assertEqual(
            validate_remaining_days({"qualification-test-programme": 12}),
            {"qualification-test-programme": 12},
        )

    def test_remaining_days_for_an_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_remaining_days({"lunch": 12})

    def test_a_negative_remaining_day_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_remaining_days({"qualification-test-programme": -1})

    def test_a_non_integer_remaining_day_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_remaining_days({"qualification-test-programme": 12.5})


class PrerequisiteTests(unittest.TestCase):
    def test_the_first_stage_is_always_executable(self):
        self.assertEqual(unmet_prerequisites("design-definition-review", NOTHING_STARTED), [])

    def test_a_later_stage_lists_its_unmet_prerequisites(self):
        self.assertEqual(
            unmet_prerequisites("qualification-test-programme", NOTHING_STARTED),
            ["qualification-lot-manufacture"],
        )

    def test_the_grant_waits_on_two_prerequisites(self):
        self.assertEqual(len(unmet_prerequisites(GRANT_STAGE, NOTHING_STARTED)), 2)

    def test_an_unknown_stage_id_rejected(self):
        with self.assertRaises(ValueError):
            unmet_prerequisites("lunch", NOTHING_STARTED)

    def test_only_the_first_stage_is_executable_at_the_start(self):
        self.assertEqual(next_executable_stages(NOTHING_STARTED), ["design-definition-review"])

    def test_two_stages_open_together_after_technology_selection(self):
        self.assertEqual(
            next_executable_stages(EARLY),
            ["engineering-model-build", "manufacturing-process-identification"],
        )

    def test_nothing_is_executable_once_everything_is_complete(self):
        self.assertEqual(next_executable_stages(ALL_COMPLETE), [])

    def test_an_in_progress_stage_is_still_reported_as_executable(self):
        states = _states(NOTHING_STARTED, **{"design-definition-review": "in-progress"})
        self.assertIn("design-definition-review", next_executable_stages(states))


class SequenceViolationTests(unittest.TestCase):
    def test_a_clean_start_has_no_violations(self):
        self.assertEqual(sequence_violations(NOTHING_STARTED), [])

    def test_a_clean_finish_has_no_violations(self):
        self.assertEqual(sequence_violations(ALL_COMPLETE), [])

    def test_a_stage_completed_out_of_order_is_reported(self):
        states = _states(NOTHING_STARTED, **{"qualification-test-programme": "complete"})
        violations = sequence_violations(states)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["stage"], "qualification-test-programme")
        self.assertEqual(
            violations[0]["unmet_prerequisites"], ["qualification-lot-manufacture"]
        )

    def test_a_stage_started_out_of_order_is_reported(self):
        states = _states(NOTHING_STARTED, **{"qualification-lot-manufacture": "in-progress"})
        self.assertEqual(len(sequence_violations(states)), 1)

    def test_a_not_started_stage_is_never_a_violation(self):
        self.assertEqual(sequence_violations(NOTHING_STARTED), [])

    def test_a_failed_stage_is_not_itself_a_sequence_violation(self):
        states = _states(NOTHING_STARTED, **{"design-definition-review": "failed"})
        self.assertEqual(sequence_violations(states), [])
        self.assertEqual(failed_stages(states), ["design-definition-review"])


class DurationTests(unittest.TestCase):
    def test_a_complete_stage_costs_nothing(self):
        self.assertEqual(stage_cost_days("design-definition-review", ALL_COMPLETE), 0)

    def test_an_open_stage_costs_its_nominal_duration(self):
        self.assertEqual(
            stage_cost_days("qualification-test-programme", NOTHING_STARTED),
            STAGE_BY_ID["qualification-test-programme"]["nominal_days"],
        )

    def test_an_override_replaces_the_nominal_duration(self):
        self.assertEqual(
            stage_cost_days(
                "qualification-test-programme",
                NOTHING_STARTED,
                {"qualification-test-programme": 12},
            ),
            12,
        )

    def test_an_override_on_a_complete_stage_is_ignored(self):
        self.assertEqual(
            stage_cost_days(
                "qualification-test-programme",
                ALL_COMPLETE,
                {"qualification-test-programme": 12},
            ),
            0,
        )

    def test_the_full_critical_path_from_a_standing_start(self):
        # design definition, technology selection, engineering model, design
        # verification, qualification lot, qualification test, evaluation,
        # grant: the process identification branch runs shorter and is hidden.
        self.assertEqual(remaining_critical_path_days(NOTHING_STARTED), 255)

    def test_the_critical_path_is_zero_once_everything_is_complete(self):
        self.assertEqual(remaining_critical_path_days(ALL_COMPLETE), 0)

    def test_completed_early_stages_shorten_the_critical_path(self):
        self.assertEqual(remaining_critical_path_days(EARLY), 210)

    def test_the_shorter_branch_does_not_drive_the_path(self):
        # Finishing only the process identification branch leaves the long
        # verification branch in charge, so the path does not move.
        states = _states(EARLY, **{"manufacturing-process-identification": "complete"})
        self.assertEqual(
            remaining_critical_path_days(states), remaining_critical_path_days(EARLY)
        )

    def test_an_override_shortens_the_path(self):
        base = remaining_critical_path_days(NOTHING_STARTED)
        shortened = remaining_critical_path_days(
            NOTHING_STARTED, {"qualification-test-programme": 20}
        )
        self.assertEqual(base - shortened, 40)


class CompletionTests(unittest.TestCase):
    def test_nothing_started_is_zero_complete(self):
        self.assertAlmostEqual(completion_fraction(NOTHING_STARTED), 0.0, places=9)

    def test_everything_complete_is_fully_complete(self):
        self.assertAlmostEqual(completion_fraction(ALL_COMPLETE), 1.0, places=9)

    def test_partial_completion_is_the_nominal_day_share(self):
        expected = (
            STAGE_BY_ID["design-definition-review"]["nominal_days"]
            + STAGE_BY_ID["technology-and-parts-selection"]["nominal_days"]
        ) / TOTAL_NOMINAL_DAYS
        self.assertAlmostEqual(completion_fraction(EARLY), expected, places=9)

    def test_an_in_progress_stage_does_not_count_as_complete(self):
        states = _states(EARLY, **{"engineering-model-build": "in-progress"})
        self.assertAlmostEqual(
            completion_fraction(states), completion_fraction(EARLY), places=9
        )


class DecisionTests(unittest.TestCase):
    def test_a_finished_sequence_grants_the_approval(self):
        self.assertEqual(approval_decision(ALL_COMPLETE), APPROVAL_GRANTED)

    def test_an_unfinished_sequence_is_pending(self):
        self.assertEqual(approval_decision(EARLY), APPROVAL_PENDING)

    def test_a_failed_stage_holds_the_grant(self):
        self.assertEqual(approval_decision(QUAL_TEST_FAILED), APPROVAL_HELD_BY_FAILURE)

    def test_a_failure_with_the_work_behind_it_recorded_done_is_a_broken_sequence(self):
        # A stage cannot be complete on the back of a prerequisite that failed;
        # that record is a sequence defect, not merely a held grant.
        states = _states(ALL_COMPLETE, **{"qualification-test-programme": "failed"})
        self.assertEqual(approval_decision(states), APPROVAL_SEQUENCE_BROKEN)

    def test_an_out_of_order_record_breaks_the_sequence(self):
        states = _states(NOTHING_STARTED, **{GRANT_STAGE: "complete"})
        self.assertEqual(approval_decision(states), APPROVAL_SEQUENCE_BROKEN)

    def test_a_broken_sequence_outranks_a_failure(self):
        states = _states(
            NOTHING_STARTED,
            **{GRANT_STAGE: "complete", "design-definition-review": "failed"}
        )
        self.assertEqual(approval_decision(states), APPROVAL_SEQUENCE_BROKEN)


class PlanTests(unittest.TestCase):
    def test_a_standing_start_plan(self):
        result = plan_new_design_approval({"states": NOTHING_STARTED})
        self.assertEqual(result["verdict"], APPROVAL_PENDING)
        self.assertEqual(result["next_executable_stages"], ["design-definition-review"])
        self.assertEqual(result["remaining_critical_path_days"], 255)
        self.assertAlmostEqual(result["completion_fraction"], 0.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_a_finished_plan_grants(self):
        result = plan_new_design_approval({"states": ALL_COMPLETE})
        self.assertEqual(result["verdict"], APPROVAL_GRANTED)
        self.assertEqual(result["remaining_critical_path_days"], 0)
        self.assertAlmostEqual(result["completion_fraction"], 1.0, places=9)

    def test_a_plan_reports_an_out_of_order_grant(self):
        result = plan_new_design_approval(
            {"states": _states(NOTHING_STARTED, **{GRANT_STAGE: "complete"})}
        )
        self.assertEqual(result["verdict"], APPROVAL_SEQUENCE_BROKEN)
        self.assertTrue(any("does not stand on that record" in f for f in result["findings"]))

    def test_a_plan_reports_a_failure(self):
        result = plan_new_design_approval({"states": QUAL_TEST_FAILED})
        self.assertEqual(result["verdict"], APPROVAL_HELD_BY_FAILURE)
        self.assertEqual(result["failed_stages"], ["qualification-test-programme"])
        self.assertTrue(any("the grant is held" in f for f in result["findings"]))
        self.assertEqual(result["next_executable_stages"], [])

    def test_a_plan_honours_a_remaining_days_override(self):
        result = plan_new_design_approval(
            {
                "states": NOTHING_STARTED,
                "remaining_days": {"qualification-test-programme": 20},
            }
        )
        self.assertEqual(result["remaining_critical_path_days"], 215)

    def test_plan_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            plan_new_design_approval("not-started")

    def test_plan_rejects_an_incomplete_state_declaration(self):
        states = dict(NOTHING_STARTED)
        del states["engineering-model-build"]
        with self.assertRaises(ValueError):
            plan_new_design_approval({"states": states})

    def test_plan_rejects_a_bad_override_table(self):
        with self.assertRaises(ValueError):
            plan_new_design_approval(
                {"states": NOTHING_STARTED, "remaining_days": {"lunch": 5}}
            )

    def test_progress_never_lengthens_the_critical_path(self):
        start = plan_new_design_approval({"states": NOTHING_STARTED})
        later = plan_new_design_approval({"states": EARLY})
        self.assertLess(
            later["remaining_critical_path_days"],
            start["remaining_critical_path_days"],
        )


if __name__ == "__main__":
    unittest.main()
