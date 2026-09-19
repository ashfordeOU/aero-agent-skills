"""Contract test for the OBCP execution status leaf (stdlib unittest)."""

import unittest

from e7041_execution_status_logic import (
    CATEGORY_ABSENT,
    CATEGORY_EXECUTING,
    CATEGORY_IDLE,
    CATEGORY_TERMINAL,
    STATUS_ACTIVE_RUNNING,
    STATUS_ACTIVE_SUSPENDED,
    STATUS_LOADED_INACTIVE,
    STATUS_NOT_LOADED,
    STATUS_TERMINATED_ABORTED,
    STATUS_TERMINATED_COMPLETED,
    TERMINATION_ABORTED,
    TERMINATION_COMPLETED,
    assess_engine_slot_demand,
    contradictions,
    derive_execution_status,
    facts_are_consistent,
    is_executing,
    is_terminal,
    owns_engine_slot,
    reconcile_reported_status,
    status_category,
    summarize_status_set,
    validate_facts,
    validate_status,
)


def facts(proc_id="OBCP-1", **kw):
    record = {
        "id": proc_id,
        "loaded": True,
        "started": False,
        "suspended": False,
        "terminated": False,
        "termination_reason": None,
    }
    record.update(kw)
    return record


def running(proc_id="OBCP-1"):
    return facts(proc_id, started=True)


def suspended(proc_id="OBCP-1"):
    return facts(proc_id, started=True, suspended=True)


def finished(proc_id="OBCP-1", reason=TERMINATION_COMPLETED):
    return facts(proc_id, started=True, terminated=True,
                 termination_reason=reason)


class TestFactValidation(unittest.TestCase):
    def test_facts_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_facts(["OBCP-1", True])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_facts(facts(""))

    def test_a_non_boolean_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_facts(facts(started=1))

    def test_unknown_termination_reason_raises(self):
        with self.assertRaises(ValueError):
            validate_facts(facts(terminated=True,
                                 termination_reason="gave-up"))

    def test_flags_default_to_false(self):
        normalized = validate_facts({"id": "OBCP-9"})
        self.assertFalse(normalized["loaded"])
        self.assertFalse(normalized["started"])


class TestStatusNames(unittest.TestCase):
    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            validate_status("paused")

    def test_absent_and_idle_are_different_categories(self):
        self.assertEqual(status_category(STATUS_NOT_LOADED), CATEGORY_ABSENT)
        self.assertEqual(status_category(STATUS_LOADED_INACTIVE),
                         CATEGORY_IDLE)

    def test_running_and_suspended_share_the_executing_category(self):
        self.assertEqual(status_category(STATUS_ACTIVE_RUNNING),
                         CATEGORY_EXECUTING)
        self.assertEqual(status_category(STATUS_ACTIVE_SUSPENDED),
                         CATEGORY_EXECUTING)

    def test_both_terminations_are_terminal(self):
        self.assertTrue(is_terminal(STATUS_TERMINATED_COMPLETED))
        self.assertTrue(is_terminal(STATUS_TERMINATED_ABORTED))
        self.assertEqual(status_category(STATUS_TERMINATED_ABORTED),
                         CATEGORY_TERMINAL)

    def test_an_idle_procedure_is_not_executing(self):
        self.assertFalse(is_executing(STATUS_LOADED_INACTIVE))

    def test_a_suspended_procedure_still_owns_its_engine_slot(self):
        self.assertTrue(owns_engine_slot(STATUS_ACTIVE_SUSPENDED))

    def test_a_finished_procedure_releases_its_engine_slot(self):
        self.assertFalse(owns_engine_slot(STATUS_TERMINATED_COMPLETED))


class TestDerivation(unittest.TestCase):
    def test_unloaded_and_untouched_is_not_loaded(self):
        self.assertEqual(
            derive_execution_status(facts(loaded=False)), STATUS_NOT_LOADED
        )

    def test_loaded_and_never_started_is_inactive(self):
        self.assertEqual(derive_execution_status(facts()),
                         STATUS_LOADED_INACTIVE)

    def test_started_and_not_held_is_running(self):
        self.assertEqual(derive_execution_status(running()),
                         STATUS_ACTIVE_RUNNING)

    def test_started_and_held_is_suspended(self):
        self.assertEqual(derive_execution_status(suspended()),
                         STATUS_ACTIVE_SUSPENDED)

    def test_completed_and_aborted_are_told_apart_by_the_reason(self):
        self.assertEqual(
            derive_execution_status(finished(reason=TERMINATION_COMPLETED)),
            STATUS_TERMINATED_COMPLETED,
        )
        self.assertEqual(
            derive_execution_status(finished(reason=TERMINATION_ABORTED)),
            STATUS_TERMINATED_ABORTED,
        )


class TestContradictions(unittest.TestCase):
    def test_running_while_not_loaded_is_a_contradiction(self):
        self.assertFalse(
            facts_are_consistent(facts(loaded=False, started=True))
        )

    def test_held_without_being_started_is_a_contradiction(self):
        self.assertFalse(facts_are_consistent(facts(suspended=True)))

    def test_held_and_finished_at_once_is_a_contradiction(self):
        self.assertFalse(
            facts_are_consistent(
                facts(started=True, suspended=True, terminated=True,
                      termination_reason=TERMINATION_COMPLETED)
            )
        )

    def test_finished_with_no_reason_is_a_contradiction(self):
        self.assertFalse(
            facts_are_consistent(facts(started=True, terminated=True))
        )

    def test_a_reason_while_still_running_is_a_contradiction(self):
        self.assertFalse(
            facts_are_consistent(
                facts(started=True,
                      termination_reason=TERMINATION_COMPLETED)
            )
        )

    def test_deriving_a_contradictory_status_raises(self):
        with self.assertRaises(ValueError):
            derive_execution_status(facts(suspended=True))

    def test_every_contradiction_is_named_not_just_the_first(self):
        found = contradictions(facts(loaded=False, suspended=True))
        self.assertGreaterEqual(len(found), 2)

    def test_a_clean_record_names_no_contradiction(self):
        self.assertEqual(contradictions(running()), [])


class TestReconciliation(unittest.TestCase):
    def test_an_agreeing_report_is_marked_agreed(self):
        result = reconcile_reported_status(STATUS_ACTIVE_RUNNING, running())
        self.assertTrue(result["agrees"])
        self.assertEqual(result["note"], "agreed")

    def test_a_stale_ground_model_is_caught(self):
        result = reconcile_reported_status(STATUS_ACTIVE_RUNNING, finished())
        self.assertFalse(result["agrees"])
        self.assertEqual(result["derived_status"],
                         STATUS_TERMINATED_COMPLETED)

    def test_a_disagreement_inside_one_category_is_reported_separately(self):
        result = reconcile_reported_status(STATUS_ACTIVE_RUNNING, suspended())
        self.assertFalse(result["agrees"])
        self.assertTrue(result["category_agrees"])

    def test_reconciling_against_an_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            reconcile_reported_status("halted", running())


class TestSummary(unittest.TestCase):
    def test_empty_record_list_raises(self):
        with self.assertRaises(ValueError):
            summarize_status_set([])

    def test_duplicate_procedure_id_raises(self):
        with self.assertRaises(ValueError):
            summarize_status_set([running("A"), facts("A")])

    def test_statuses_are_grouped(self):
        summary = summarize_status_set(
            [running("A"), suspended("B"), finished("C")]
        )
        self.assertEqual(summary["grouped_by_status"][STATUS_ACTIVE_RUNNING],
                         ["A"])
        self.assertEqual(summary["grouped_by_category"][CATEGORY_EXECUTING],
                         ["A", "B"])

    def test_counts_cover_every_status_including_the_empty_ones(self):
        summary = summarize_status_set([running("A")])
        self.assertEqual(summary["counts_by_status"][STATUS_NOT_LOADED], 0)
        self.assertEqual(summary["counts_by_status"][STATUS_ACTIVE_RUNNING], 1)

    def test_aborted_runs_are_counted_apart_from_completed_ones(self):
        summary = summarize_status_set(
            [finished("A", TERMINATION_ABORTED), finished("B")]
        )
        self.assertEqual(summary["aborted_count"], 1)
        self.assertEqual(summary["terminal_count"], 2)

    def test_slot_demand_counts_held_procedures(self):
        result = assess_engine_slot_demand(
            [running("A"), suspended("B"), finished("C")], 4
        )
        self.assertEqual(result["slot_owning_count"], 2)
        self.assertEqual(result["free_slots"], 2)
        self.assertFalse(result["over_limit"])

    def test_slot_demand_exactly_at_the_limit_is_not_over(self):
        result = assess_engine_slot_demand([running("A"), suspended("B")], 2)
        self.assertFalse(result["over_limit"])
        self.assertEqual(result["free_slots"], 0)

    def test_slot_demand_past_the_limit_is_flagged(self):
        result = assess_engine_slot_demand(
            [running("A"), running("B"), suspended("C")], 2
        )
        self.assertTrue(result["over_limit"])

    def test_zero_concurrency_limit_raises(self):
        with self.assertRaises(ValueError):
            assess_engine_slot_demand([running("A")], 0)


if __name__ == "__main__":
    unittest.main()
