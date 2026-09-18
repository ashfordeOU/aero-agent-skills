"""Contract tests for the clause 7.2 microwave circuit design-task-set logic."""

import unittest

from q6012_mmic_design_task_set_logic import (
    EFFORT_CONCENTRATION_LIMIT,
    MANDATED_ACTIVITIES,
    TASK_STATES,
    activity_coverage,
    assess_design_task_set,
    build_task_set,
    completion_ratio_by_count,
    completion_ratio_by_effort,
    deliverable_gaps,
    effort_by_activity,
    effort_concentration,
    normalise_activity,
    ownership_gaps,
    validate_task,
)


def task(identifier, activity, state="planned", effort=100.0,
         owner="rf-design-lead", deliverable="design-note"):
    return {
        "id": identifier,
        "activity": activity,
        "state": state,
        "effort_hours": effort,
        "owner": owner,
        "deliverable": deliverable,
    }


def full_set(**overrides):
    """One task per mandated activity, each with equal declared effort."""
    tasks = []
    for i, activity in enumerate(MANDATED_ACTIVITIES, start=1):
        tasks.append(task("T%02d" % i, activity, **overrides))
    return tasks


class NormaliseActivityTests(unittest.TestCase):
    def test_lowercases_and_hyphenates(self):
        self.assertEqual(normalise_activity("Circuit Design"), "circuit-design")

    def test_underscores_become_hyphens(self):
        self.assertEqual(normalise_activity("layout_design"), "layout-design")

    def test_collapses_repeated_spaces(self):
        self.assertEqual(normalise_activity("  thermal   design "), "thermal-design")

    def test_empty_activity_rejected(self):
        with self.assertRaises(ValueError):
            normalise_activity("   ")

    def test_non_string_activity_rejected(self):
        with self.assertRaises(ValueError):
            normalise_activity(7)


class ValidateTaskTests(unittest.TestCase):
    def test_returns_canonical_record(self):
        record = validate_task(task("T1", "Circuit Design", state="Complete"))
        self.assertEqual(record["activity"], "circuit-design")
        self.assertEqual(record["state"], "complete")
        self.assertAlmostEqual(record["effort_hours"], 100.0, places=9)

    def test_missing_owner_is_recorded_as_none_not_an_error(self):
        record = validate_task(task("T1", "circuit-design", owner=None))
        self.assertIsNone(record["owner"])

    def test_blank_deliverable_becomes_none(self):
        record = validate_task(task("T1", "circuit-design", deliverable="   "))
        self.assertIsNone(record["deliverable"])

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_task(task("T1", "circuit-design", state="nearly-done"))

    def test_zero_effort_rejected(self):
        with self.assertRaises(ValueError):
            validate_task(task("T1", "circuit-design", effort=0.0))

    def test_negative_effort_rejected(self):
        with self.assertRaises(ValueError):
            validate_task(task("T1", "circuit-design", effort=-40.0))

    def test_boolean_effort_rejected(self):
        with self.assertRaises(ValueError):
            validate_task(task("T1", "circuit-design", effort=True))

    def test_non_finite_effort_rejected(self):
        with self.assertRaises(ValueError):
            validate_task(task("T1", "circuit-design", effort=float("inf")))

    def test_missing_key_rejected(self):
        bad = task("T1", "circuit-design")
        del bad["state"]
        with self.assertRaises(ValueError):
            validate_task(bad)

    def test_non_mapping_task_rejected(self):
        with self.assertRaises(ValueError):
            validate_task(["T1", "circuit-design"])

    def test_empty_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_task(task("  ", "circuit-design"))

    def test_state_vocabulary_is_closed(self):
        self.assertEqual(TASK_STATES, ("planned", "in-progress", "complete"))


class BuildTaskSetTests(unittest.TestCase):
    def test_builds_every_declared_task(self):
        records = build_task_set(full_set())
        self.assertEqual(len(records), len(MANDATED_ACTIVITIES))

    def test_duplicate_identifier_rejected(self):
        tasks = [task("T1", "circuit-design"), task("T1", "layout-design")]
        with self.assertRaises(ValueError):
            build_task_set(tasks)

    def test_empty_task_set_rejected(self):
        with self.assertRaises(ValueError):
            build_task_set([])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            build_task_set({"id": "T1"})


class ActivityCoverageTests(unittest.TestCase):
    def test_full_set_has_no_gap(self):
        coverage = activity_coverage(build_task_set(full_set()))
        self.assertEqual(coverage["missing"], [])
        self.assertEqual(len(coverage["covered"]), len(MANDATED_ACTIVITIES))

    def test_missing_activity_named_in_mandated_order(self):
        tasks = [t for t in full_set() if t["activity"] != "thermal-design"]
        coverage = activity_coverage(build_task_set(tasks))
        self.assertEqual(coverage["missing"], ["thermal-design"])

    def test_two_tasks_on_one_activity_still_cover_it_once(self):
        tasks = full_set() + [task("TX", "circuit-design")]
        coverage = activity_coverage(build_task_set(tasks))
        self.assertEqual(coverage["missing"], [])
        self.assertEqual(coverage["covered"].count("circuit-design"), 1)

    def test_project_extra_is_not_counted_as_a_gap(self):
        tasks = full_set() + [task("TX", "wafer-lot-planning")]
        coverage = activity_coverage(build_task_set(tasks))
        self.assertEqual(coverage["missing"], [])
        self.assertEqual(coverage["extra"], ["wafer-lot-planning"])


class EffortTests(unittest.TestCase):
    def test_effort_sums_per_activity(self):
        tasks = [
            task("T1", "circuit-design", effort=60.0),
            task("T2", "circuit-design", effort=40.0),
            task("T3", "layout-design", effort=25.0),
        ]
        totals = effort_by_activity(build_task_set(tasks))
        self.assertAlmostEqual(totals["circuit-design"], 100.0, places=9)
        self.assertAlmostEqual(totals["layout-design"], 25.0, places=9)

    def test_even_split_gives_the_reciprocal_concentration(self):
        records = build_task_set(full_set())
        self.assertAlmostEqual(
            effort_concentration(records), 1.0 / len(MANDATED_ACTIVITIES), places=9
        )

    def test_single_activity_concentrates_all_effort(self):
        records = build_task_set([task("T1", "circuit-design", effort=10.0)])
        self.assertAlmostEqual(effort_concentration(records), 1.0, places=9)

    def test_concentration_limit_is_a_half(self):
        self.assertAlmostEqual(EFFORT_CONCENTRATION_LIMIT, 0.5, places=9)


class CompletionRatioTests(unittest.TestCase):
    def test_effort_weighting_differs_from_task_count(self):
        tasks = [
            task("T1", "circuit-design", state="complete", effort=10.0),
            task("T2", "layout-design", state="complete", effort=10.0),
            task("T3", "thermal-design", state="planned", effort=180.0),
        ]
        records = build_task_set(tasks)
        self.assertAlmostEqual(completion_ratio_by_count(records), 2.0 / 3.0, places=9)
        self.assertAlmostEqual(completion_ratio_by_effort(records), 0.1, places=9)

    def test_nothing_complete_gives_zero(self):
        records = build_task_set(full_set())
        self.assertAlmostEqual(completion_ratio_by_effort(records), 0.0, places=9)

    def test_everything_complete_gives_one(self):
        records = build_task_set(full_set(state="complete"))
        self.assertAlmostEqual(completion_ratio_by_effort(records), 1.0, places=9)

    def test_in_progress_does_not_count_as_complete(self):
        records = build_task_set(full_set(state="in-progress"))
        self.assertAlmostEqual(completion_ratio_by_effort(records), 0.0, places=9)


class GapTests(unittest.TestCase):
    def test_ownership_gap_listed_by_identifier(self):
        tasks = full_set()
        tasks[2]["owner"] = None
        records = build_task_set(tasks)
        self.assertEqual(ownership_gaps(records), [tasks[2]["id"]])

    def test_deliverable_gap_listed_by_identifier(self):
        tasks = full_set()
        tasks[5]["deliverable"] = None
        records = build_task_set(tasks)
        self.assertEqual(deliverable_gaps(records), [tasks[5]["id"]])

    def test_complete_set_has_no_gaps(self):
        records = build_task_set(full_set())
        self.assertEqual(ownership_gaps(records), [])
        self.assertEqual(deliverable_gaps(records), [])


class AssessDesignTaskSetTests(unittest.TestCase):
    def _spec(self, **kwargs):
        spec = {"tasks": full_set()}
        spec.update(kwargs)
        return spec

    def test_full_plan_is_authorised(self):
        result = assess_design_task_set(self._spec())
        self.assertTrue(result["authorised"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["coverage_ratio"], 1.0, places=9)

    def test_missing_activity_blocks_authorisation(self):
        tasks = [t for t in full_set() if t["activity"] != "design-review"]
        result = assess_design_task_set(self._spec(tasks=tasks))
        self.assertFalse(result["authorised"])
        self.assertEqual(result["missing_activities"], ["design-review"])

    def test_ownership_gap_blocks_authorisation(self):
        tasks = full_set()
        tasks[0]["owner"] = None
        result = assess_design_task_set(self._spec(tasks=tasks))
        self.assertFalse(result["authorised"])
        self.assertIn(tasks[0]["id"], result["ownership_gaps"])

    def test_deliverable_gap_blocks_authorisation(self):
        tasks = full_set()
        tasks[1]["deliverable"] = None
        result = assess_design_task_set(self._spec(tasks=tasks))
        self.assertFalse(result["authorised"])
        self.assertIn(tasks[1]["id"], result["deliverable_gaps"])

    def test_effort_concentration_blocks_authorisation(self):
        tasks = full_set()
        tasks[0]["effort_hours"] = 5000.0
        result = assess_design_task_set(self._spec(tasks=tasks))
        self.assertFalse(result["authorised"])
        self.assertTrue(any("declared effort" in f for f in result["findings"]))

    def test_concentration_exactly_at_the_limit_is_absorbed(self):
        tasks = [
            task("T%02d" % i, activity, effort=(700.0 if i == 1 else 100.0))
            for i, activity in enumerate(MANDATED_ACTIVITIES, start=1)
        ]
        result = assess_design_task_set(self._spec(tasks=tasks))
        self.assertAlmostEqual(result["effort_concentration"], 0.5, places=9)
        self.assertTrue(result["authorised"])

    def test_total_effort_is_reported(self):
        result = assess_design_task_set(self._spec())
        self.assertAlmostEqual(
            result["total_effort_hours"], 100.0 * len(MANDATED_ACTIVITIES), places=9
        )

    def test_project_extra_does_not_block_authorisation(self):
        tasks = full_set() + [task("TX", "wafer-lot-planning")]
        result = assess_design_task_set(self._spec(tasks=tasks))
        self.assertTrue(result["authorised"])
        self.assertEqual(result["extra_activities"], ["wafer-lot-planning"])

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_task_set(["tasks"])

    def test_missing_tasks_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_task_set({"concentration_limit": 0.4})

    def test_out_of_range_concentration_limit_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_task_set(self._spec(concentration_limit=0.0))

    def test_non_numeric_concentration_limit_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_task_set(self._spec(concentration_limit="half"))

    def test_coverage_ratio_tracks_the_gaps(self):
        tasks = [t for t in full_set() if t["activity"] not in
                 ("thermal-design", "design-review")]
        result = assess_design_task_set(self._spec(tasks=tasks))
        self.assertAlmostEqual(
            result["coverage_ratio"],
            (len(MANDATED_ACTIVITIES) - 2) / float(len(MANDATED_ACTIVITIES)),
            places=9,
        )


if __name__ == "__main__":
    unittest.main()
