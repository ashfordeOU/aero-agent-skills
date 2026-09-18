"""Contract tests for the clause 6.3 category-two validation-process logic."""

import datetime
import unittest

from q6005_category_two_validation_process_logic import (
    STEP_STATUSES,
    VALIDATION_STEPS,
    assess_category_two_validation,
    critical_chain,
    earliest_completion_date,
    earliest_completion_days,
    ordering_defects,
    outstanding_steps,
    parse_date,
    programme_margin_days,
    ready_steps,
    remaining_days,
    reuse_admissible,
    topological_order,
    validate_registry,
    validate_step_states,
    validation_verdict,
)

NOMINAL_SPAN_DAYS = 175


def states(**overrides):
    """Every step not started, unless overridden."""
    base = dict((step, "not-started") for step in VALIDATION_STEPS)
    base.update(overrides)
    return base


def through(*completed):
    """States with the named steps complete and the rest not started."""
    return states(**dict((step, "complete") for step in completed))


class RegistryTests(unittest.TestCase):
    def test_registry_is_a_usable_graph(self):
        self.assertIs(validate_registry(), VALIDATION_STEPS)

    def test_topological_order_covers_every_step(self):
        order = topological_order()
        self.assertEqual(set(order), set(VALIDATION_STEPS))
        self.assertEqual(len(order), len(VALIDATION_STEPS))

    def test_topological_order_never_precedes_a_prerequisite(self):
        order = topological_order()
        for step in order:
            for prereq in VALIDATION_STEPS[step]["requires"]:
                self.assertLess(order.index(prereq), order.index(step))

    def test_first_step_is_the_programme_applicability_review(self):
        self.assertEqual(topological_order()[0], "programme-applicability-review")

    def test_cycle_rejected(self):
        bad = {
            "a": {"requires": ("b",), "nominal_days": 5},
            "b": {"requires": ("a",), "nominal_days": 5},
        }
        with self.assertRaises(ValueError):
            topological_order(bad)

    def test_self_reference_rejected(self):
        bad = {"a": {"requires": ("a",), "nominal_days": 5}}
        with self.assertRaises(ValueError):
            validate_registry(bad)

    def test_unknown_prerequisite_rejected(self):
        bad = {"a": {"requires": ("ghost",), "nominal_days": 5}}
        with self.assertRaises(ValueError):
            validate_registry(bad)

    def test_non_positive_duration_rejected(self):
        bad = {"a": {"requires": (), "nominal_days": 0}}
        with self.assertRaises(ValueError):
            validate_registry(bad)

    def test_empty_registry_rejected(self):
        with self.assertRaises(ValueError):
            validate_registry({})


class StepStateTests(unittest.TestCase):
    def test_full_state_record_accepted(self):
        self.assertEqual(len(validate_step_states(states())), len(VALIDATION_STEPS))

    def test_status_case_normalised(self):
        validated = validate_step_states(states(**{"supplier-survey": "In-Progress"}))
        self.assertEqual(validated["supplier-survey"], "in-progress")

    def test_every_declared_status_is_recognised(self):
        for status in STEP_STATUSES:
            validated = validate_step_states(states(**{"supplier-survey": status}))
            self.assertEqual(validated["supplier-survey"], status)

    def test_unknown_step_rejected(self):
        bad = states()
        bad["marketing-review"] = "complete"
        with self.assertRaises(ValueError):
            validate_step_states(bad)

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            validate_step_states(states(**{"supplier-survey": "nearly"}))

    def test_omitted_step_rejected(self):
        partial = states()
        del partial["validation-lot-testing"]
        with self.assertRaises(ValueError):
            validate_step_states(partial)


class OrderingTests(unittest.TestCase):
    def test_clean_sequence_has_no_defects(self):
        self.assertEqual(ordering_defects(through("programme-applicability-review")), ())

    def test_step_started_before_its_prerequisite_is_a_defect(self):
        bad = states(**{"validation-lot-build": "in-progress"})
        defects = ordering_defects(bad)
        self.assertIn(("validation-lot-build", "process-identification-audit"), defects)
        self.assertIn(("validation-lot-build", "element-procurement-review"), defects)

    def test_both_unmet_prerequisites_are_named(self):
        bad = states(**{"validation-lot-build": "complete"})
        self.assertEqual(len(ordering_defects(bad)), 2)

    def test_ready_steps_are_the_openable_ones(self):
        self.assertEqual(ready_steps(states()), ("programme-applicability-review",))

    def test_two_steps_open_after_the_applicability_review(self):
        ready = ready_steps(through("programme-applicability-review"))
        self.assertEqual(set(ready), {"supplier-survey", "element-procurement-review"})

    def test_outstanding_steps_drop_the_finished_ones(self):
        out = outstanding_steps(through("programme-applicability-review"))
        self.assertNotIn("programme-applicability-review", out)
        self.assertEqual(len(out), len(VALIDATION_STEPS) - 1)


class ScheduleTests(unittest.TestCase):
    def test_nothing_started_takes_the_whole_nominal_chain(self):
        self.assertEqual(earliest_completion_days(states()), NOMINAL_SPAN_DAYS)

    def test_finished_steps_shorten_the_horizon(self):
        shorter = earliest_completion_days(through("programme-applicability-review"))
        self.assertEqual(shorter, NOMINAL_SPAN_DAYS - 10)

    def test_finishing_an_off_chain_step_does_not_shorten_the_horizon(self):
        same = earliest_completion_days(through("element-procurement-review"))
        self.assertEqual(same, NOMINAL_SPAN_DAYS)

    def test_completed_process_has_a_zero_horizon(self):
        self.assertEqual(earliest_completion_days(through(*VALIDATION_STEPS)), 0)

    def test_remaining_days_are_zero_for_finished_steps(self):
        left = remaining_days(through("programme-applicability-review", "supplier-survey"))
        self.assertEqual(left["programme-applicability-review"], 0)
        self.assertEqual(left["supplier-survey"], 0)
        self.assertEqual(
            left["validation-lot-testing"],
            VALIDATION_STEPS["validation-lot-testing"]["nominal_days"],
        )

    def test_override_replaces_the_nominal_duration(self):
        left = remaining_days(
            states(**{"validation-lot-testing": "in-progress"}),
            {"validation-lot-testing": 5},
        )
        self.assertEqual(left["validation-lot-testing"], 5)

    def test_override_shortens_the_horizon(self):
        horizon = earliest_completion_days(
            states(**{"validation-lot-testing": "in-progress"}),
            {"validation-lot-testing": 5},
        )
        self.assertEqual(horizon, NOMINAL_SPAN_DAYS - 35)

    def test_override_for_unknown_step_rejected(self):
        with self.assertRaises(ValueError):
            remaining_days(states(), {"ghost-step": 5})

    def test_negative_override_rejected(self):
        with self.assertRaises(ValueError):
            remaining_days(states(), {"supplier-survey": -1})

    def test_critical_chain_is_the_driving_sequence(self):
        chain = critical_chain(states())
        self.assertEqual(chain[0], "programme-applicability-review")
        self.assertEqual(chain[-1], "programme-authority-agreement")
        self.assertNotIn("element-procurement-review", chain)

    def test_critical_chain_is_empty_once_everything_is_done(self):
        self.assertEqual(critical_chain(through(*VALIDATION_STEPS)), ())

    def test_completion_date_is_the_horizon_from_the_start(self):
        done = earliest_completion_date("2026-01-05", states())
        self.assertEqual(done, datetime.date(2026, 1, 5) + datetime.timedelta(days=NOMINAL_SPAN_DAYS))

    def test_programme_margin_is_signed(self):
        self.assertEqual(programme_margin_days("2026-06-01", "2026-05-01"), -31)

    def test_parse_date_rejects_a_timestamp(self):
        with self.assertRaises(ValueError):
            parse_date(datetime.datetime(2026, 1, 5, 9, 0), "start_date")


class ReuseTests(unittest.TestCase):
    def test_same_programme_carries_over(self):
        self.assertTrue(reuse_admissible("Sentinel-Next", "sentinel-next"))

    def test_other_programme_does_not_carry_over(self):
        self.assertFalse(reuse_admissible("Sentinel-Next", "Lunar-Relay"))

    def test_no_previous_validation_is_not_reuse(self):
        self.assertFalse(reuse_admissible(None, "Lunar-Relay"))

    def test_blank_programme_rejected(self):
        with self.assertRaises(ValueError):
            reuse_admissible(None, "  ")

    def test_non_string_previous_programme_rejected(self):
        with self.assertRaises(ValueError):
            reuse_admissible(7, "Lunar-Relay")


class VerdictTests(unittest.TestCase):
    def test_nothing_started(self):
        self.assertEqual(validation_verdict(states()), "not-started")

    def test_partly_done(self):
        self.assertEqual(validation_verdict(through("programme-applicability-review")), "in-progress")

    def test_all_done(self):
        self.assertEqual(validation_verdict(through(*VALIDATION_STEPS)), "validated")

    def test_failure_dominates(self):
        bad = through("programme-applicability-review")
        bad["supplier-survey"] = "failed"
        self.assertEqual(validation_verdict(bad), "failed")

    def test_ordering_defect_reported_as_its_own_verdict(self):
        self.assertEqual(
            validation_verdict(states(**{"validation-lot-testing": "in-progress"})),
            "ordering-defect",
        )


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "programme": "Lunar-Relay",
            "steps": states(),
            "start_date": "2026-01-05",
            "programme_need_date": "2026-12-01",
        }
        spec.update(overrides)
        return spec

    def test_nominal_plan_fits_the_programme(self):
        out = assess_category_two_validation(self._spec())
        self.assertEqual(out["verdict"], "not-started")
        self.assertEqual(out["earliest_completion_days"], NOMINAL_SPAN_DAYS)
        self.assertGreater(out["programme_margin_days"], 0)

    def test_tight_programme_date_is_a_finding(self):
        out = assess_category_two_validation(self._spec(programme_need_date="2026-03-01"))
        self.assertLess(out["programme_margin_days"], 0)
        self.assertTrue(any("after the programme needs" in f for f in out["findings"]))

    def test_failed_step_named_in_findings(self):
        bad = through("programme-applicability-review")
        bad["supplier-survey"] = "failed"
        out = assess_category_two_validation(self._spec(steps=bad))
        self.assertEqual(out["verdict"], "failed")
        self.assertTrue(any("supplier-survey" in f for f in out["findings"]))

    def test_ordering_defect_named_with_its_prerequisite(self):
        out = assess_category_two_validation(
            self._spec(steps=states(**{"validation-lot-build": "in-progress"}))
        )
        self.assertEqual(out["verdict"], "ordering-defect")
        self.assertTrue(
            any("before its prerequisite" in f for f in out["findings"])
        )

    def test_validation_from_another_programme_does_not_carry_over(self):
        out = assess_category_two_validation(
            self._spec(previous_validation_programme="Sentinel-Next")
        )
        self.assertFalse(out["previous_validation_reusable"])
        self.assertTrue(any("does not carry over" in f for f in out["findings"]))

    def test_validation_from_this_programme_is_reusable(self):
        out = assess_category_two_validation(
            self._spec(previous_validation_programme="Lunar-Relay")
        )
        self.assertTrue(out["previous_validation_reusable"])
        self.assertFalse(any("does not carry over" in f for f in out["findings"]))

    def test_completed_process_reports_validated_with_no_remaining_chain(self):
        out = assess_category_two_validation(self._spec(steps=through(*VALIDATION_STEPS)))
        self.assertEqual(out["verdict"], "validated")
        self.assertEqual(out["critical_chain"], ())
        self.assertEqual(out["earliest_completion_days"], 0)

    def test_overrides_are_honoured_by_the_assessment(self):
        out = assess_category_two_validation(
            self._spec(
                steps=states(**{"validation-lot-testing": "in-progress"}),
                remaining_overrides={"validation-lot-testing": 5},
            )
        )
        self.assertEqual(out["earliest_completion_days"], NOMINAL_SPAN_DAYS - 35)

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["programme_need_date"]
        with self.assertRaises(ValueError):
            assess_category_two_validation(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_category_two_validation(["programme"])

    def test_blank_programme_rejected(self):
        with self.assertRaises(ValueError):
            assess_category_two_validation(self._spec(programme="   "))

    def test_need_date_before_start_rejected(self):
        with self.assertRaises(ValueError):
            assess_category_two_validation(self._spec(programme_need_date="2025-12-01"))


if __name__ == "__main__":
    unittest.main()
