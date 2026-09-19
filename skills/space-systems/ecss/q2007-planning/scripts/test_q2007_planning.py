#!/usr/bin/env python3
"""Contract tests for quality and safety planning, clause 5.3.2.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused policy,
a plan never established, an objective with no metric, target or
direction, an objective nobody owns, a resource planned below its
requirement, an objective no approved programme carries, a programme
pointing at an objective that does not exist, and attainment read in
both directions with the exact-equality case settled by tolerance.
"""

import unittest

from q2007_planning_logic import (
    DEFAULT_PLANNING_POLICY,
    HIGHER_IS_BETTER,
    LOWER_IS_BETTER,
    OBJECTIVES_UNCOVERED,
    OBJECTIVES_UNMEASURABLE,
    OBJECTIVES_UNOWNED,
    PLAN_ABSENT,
    PLAN_ESTABLISHED,
    PROGRAMME_APPROVED,
    PROGRAMME_DRAFT,
    RESOURCES_UNDER_PLANNED,
    assess_planning,
    at_least,
    at_most,
    dangling_programme_references,
    objective_attainment,
    objective_is_attained,
    objective_is_measurable,
    resource_coverage,
    resource_shortfalls,
    unattained_objectives,
    uncovered_objectives,
    unmeasurable_objectives,
    unowned_objectives,
    validate_objective,
    validate_plan,
    validate_planning_policy,
    validate_programme,
    validate_resource,
)


def _objective(objective_id="OBJ-ESCAPES", **overrides):
    record = {
        "objective_id": objective_id,
        "metric": "test-escapes-per-campaign",
        "target": 0.0,
        "direction": LOWER_IS_BETTER,
        "achieved": 0.0,
        "owner": "quality-and-safety",
        "due_day": 900,
    }
    record.update(overrides)
    return record


def _resource(resource_id="qualified-test-conductor-hours", **overrides):
    record = {
        "resource_id": resource_id,
        "required_units": 400.0,
        "planned_units": 400.0,
    }
    record.update(overrides)
    return record


def _programme(programme_id="PRG-QS-2026", covers=None, **overrides):
    record = {
        "programme_id": programme_id,
        "state": PROGRAMME_APPROVED,
        "covers_objectives": list(covers or ["OBJ-ESCAPES", "OBJ-UPTIME"]),
        "milestones": ["mid-year-review", "year-end-review"],
    }
    record.update(overrides)
    return record


def _plan(**overrides):
    record = {
        "established": True,
        "objectives": [
            _objective("OBJ-ESCAPES"),
            _objective(
                "OBJ-UPTIME",
                metric="facility-availability-fraction",
                target=0.95,
                direction=HIGHER_IS_BETTER,
                achieved=0.97,
                owner="test-operations",
            ),
        ],
        "resources": [
            _resource("qualified-test-conductor-hours"),
            _resource("safety-officer-hours", required_units=120.0, planned_units=120.0),
        ],
        "programmes": [_programme()],
    }
    record.update(overrides)
    return record


def _case(**overrides):
    case = {"plan": _plan(), "policy": dict(DEFAULT_PLANNING_POLICY)}
    case.update(overrides)
    return case


class PlanningPolicyValidation(unittest.TestCase):
    def test_default_policy_round_trips(self):
        rules = validate_planning_policy({})
        self.assertAlmostEqual(rules["min_resource_coverage"], 1.0, places=9)
        self.assertTrue(rules["require_objective_owner"])

    def test_unrecognised_policy_key_refused(self):
        with self.assertRaises(ValueError):
            validate_planning_policy({"coverage": 1.0})

    def test_coverage_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_planning_policy({"min_resource_coverage": 1.1})

    def test_non_boolean_owner_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_planning_policy({"require_objective_owner": "yes"})


class RecordValidation(unittest.TestCase):
    def test_objective_missing_field_refused(self):
        bad = _objective()
        del bad["direction"]
        with self.assertRaises(ValueError):
            validate_objective(bad)

    def test_unrecognised_direction_refused(self):
        with self.assertRaises(ValueError):
            validate_objective(_objective(direction="nearer-is-better"))

    def test_non_numeric_target_refused(self):
        with self.assertRaises(ValueError):
            validate_objective(_objective(target="zero"))

    def test_zero_required_resource_refused(self):
        with self.assertRaises(ValueError):
            validate_resource(_resource(required_units=0.0))

    def test_negative_planned_resource_refused(self):
        with self.assertRaises(ValueError):
            validate_resource(_resource(planned_units=-10.0))

    def test_unrecognised_programme_state_refused(self):
        with self.assertRaises(ValueError):
            validate_programme(_programme(state="running"))

    def test_duplicate_objective_id_refused(self):
        with self.assertRaises(ValueError):
            validate_plan(_plan(objectives=[_objective("OBJ-ESCAPES"), _objective("OBJ-ESCAPES")]))

    def test_duplicate_resource_id_refused(self):
        with self.assertRaises(ValueError):
            validate_plan(_plan(resources=[_resource(), _resource()]))

    def test_non_mapping_plan_refused(self):
        with self.assertRaises(ValueError):
            validate_plan(["established"])


class Measurability(unittest.TestCase):
    def test_a_complete_objective_is_measurable(self):
        self.assertTrue(objective_is_measurable(_objective()))

    def test_an_objective_without_a_target_is_not_measurable(self):
        self.assertFalse(objective_is_measurable(_objective(target=None)))

    def test_an_objective_without_a_metric_is_not_measurable(self):
        self.assertFalse(objective_is_measurable(_objective(metric=None)))

    def test_an_objective_without_a_direction_is_not_measurable(self):
        self.assertFalse(objective_is_measurable(_objective(direction=None)))

    def test_unmeasurable_objectives_are_named(self):
        plan = _plan(objectives=[_objective("OBJ-CULTURE", target=None)])
        self.assertEqual(unmeasurable_objectives(plan), ["OBJ-CULTURE"])

    def test_an_unmeasurable_objective_cannot_be_attained(self):
        with self.assertRaises(ValueError):
            objective_is_attained(_objective(target=None))

    def test_an_unowned_objective_is_named(self):
        plan = _plan(objectives=[_objective(owner=None)])
        self.assertEqual(unowned_objectives(plan), ["OBJ-ESCAPES"])


class Attainment(unittest.TestCase):
    def test_lower_is_better_reached_when_under_target(self):
        self.assertTrue(objective_is_attained(_objective(target=5.0, achieved=2.0)))

    def test_lower_is_better_missed_when_over_target(self):
        self.assertFalse(objective_is_attained(_objective(target=5.0, achieved=8.0)))

    def test_higher_is_better_reached_when_over_target(self):
        objective = _objective(direction=HIGHER_IS_BETTER, target=0.9, achieved=0.95)
        self.assertTrue(objective_is_attained(objective))

    def test_higher_is_better_missed_when_under_target(self):
        objective = _objective(direction=HIGHER_IS_BETTER, target=0.9, achieved=0.85)
        self.assertFalse(objective_is_attained(objective))

    def test_exact_equality_is_attained_in_both_directions(self):
        target = 1.0 / 3.0
        lower = _objective(target=target, achieved=target)
        higher = _objective(direction=HIGHER_IS_BETTER, target=target, achieved=target)
        self.assertTrue(objective_is_attained(lower))
        self.assertTrue(objective_is_attained(higher))

    def test_an_objective_with_nothing_achieved_is_not_attained(self):
        self.assertFalse(objective_is_attained(_objective(achieved=None)))

    def test_attainment_across_the_plan_is_a_fraction(self):
        plan = _plan(
            objectives=[
                _objective("OBJ-ESCAPES"),
                _objective("OBJ-LATE", target=5.0, achieved=9.0),
            ]
        )
        self.assertAlmostEqual(objective_attainment(plan), 0.5, places=9)
        self.assertEqual(unattained_objectives(plan), ["OBJ-LATE"])

    def test_attainment_of_a_plan_with_no_measurable_objective_is_zero(self):
        plan = _plan(objectives=[_objective(target=None)])
        self.assertAlmostEqual(objective_attainment(plan), 0.0, places=9)

    def test_at_least_and_at_most_agree_on_an_exact_equality(self):
        value = 0.1 + 0.2
        self.assertTrue(at_least(value, 0.3))
        self.assertTrue(at_most(value, 0.3))


class Resources(unittest.TestCase):
    def test_a_fully_planned_set_covers_exactly_one(self):
        self.assertAlmostEqual(resource_coverage(_plan()), 1.0, places=9)
        self.assertEqual(resource_shortfalls(_plan()), [])

    def test_an_under_planned_resource_is_named_with_its_shortfall(self):
        plan = _plan(resources=[_resource(required_units=400.0, planned_units=300.0)])
        shortfalls = resource_shortfalls(plan)
        self.assertEqual(shortfalls[0][0], "qualified-test-conductor-hours")
        self.assertAlmostEqual(shortfalls[0][1], 100.0, places=9)
        self.assertAlmostEqual(resource_coverage(plan), 0.75, places=9)

    def test_over_planning_one_resource_does_not_hide_a_shortfall_elsewhere(self):
        plan = _plan(
            resources=[
                _resource("conductor-hours", required_units=100.0, planned_units=400.0),
                _resource("safety-officer-hours", required_units=100.0, planned_units=0.0),
            ]
        )
        self.assertAlmostEqual(resource_coverage(plan), 0.5, places=9)
        self.assertEqual(len(resource_shortfalls(plan)), 1)

    def test_a_plan_with_no_resource_lines_has_zero_coverage(self):
        self.assertAlmostEqual(resource_coverage(_plan(resources=[])), 0.0, places=9)


class Programmes(unittest.TestCase):
    def test_an_approved_programme_carries_its_objectives(self):
        self.assertEqual(uncovered_objectives(_plan(), {}), [])

    def test_a_draft_programme_carries_nothing(self):
        plan = _plan(programmes=[_programme(state=PROGRAMME_DRAFT)])
        self.assertEqual(len(uncovered_objectives(plan, {})), 2)

    def test_a_programme_with_no_milestone_carries_nothing_by_default(self):
        plan = _plan(programmes=[_programme(milestones=[])])
        self.assertEqual(len(uncovered_objectives(plan, {})), 2)

    def test_a_programme_with_no_milestone_carries_when_policy_allows_it(self):
        plan = _plan(programmes=[_programme(milestones=[])])
        covered = uncovered_objectives(plan, {"require_programme_milestones": False})
        self.assertEqual(covered, [])

    def test_a_programme_pointing_at_no_objective_is_named(self):
        plan = _plan(programmes=[_programme(covers=["OBJ-ESCAPES", "OBJ-UPTIME", "OBJ-GHOST"])])
        self.assertEqual(dangling_programme_references(plan), [("PRG-QS-2026", "OBJ-GHOST")])


class Verdicts(unittest.TestCase):
    def test_a_complete_plan_is_established(self):
        result = assess_planning(_case())
        self.assertEqual(result["verdict"], PLAN_ESTABLISHED)
        self.assertEqual(result["findings"], [])

    def test_a_plan_never_established_short_circuits(self):
        result = assess_planning(_case(plan=_plan(established=False)))
        self.assertEqual(result["verdict"], PLAN_ABSENT)

    def test_a_plan_with_no_objectives_is_absent(self):
        result = assess_planning(_case(plan=_plan(objectives=[], programmes=[])))
        self.assertEqual(result["verdict"], PLAN_ABSENT)

    def test_an_unmeasurable_objective_outranks_an_unowned_one(self):
        plan = _plan(objectives=[_objective(target=None, owner=None)],
                     programmes=[_programme(covers=["OBJ-ESCAPES"])])
        result = assess_planning(_case(plan=plan))
        self.assertEqual(result["verdict"], OBJECTIVES_UNMEASURABLE)

    def test_an_unowned_objective_outranks_a_resource_shortfall(self):
        plan = _plan(
            objectives=[_objective(owner=None)],
            resources=[_resource(planned_units=0.0)],
            programmes=[_programme(covers=["OBJ-ESCAPES"])],
        )
        result = assess_planning(_case(plan=plan))
        self.assertEqual(result["verdict"], OBJECTIVES_UNOWNED)

    def test_an_unowned_objective_is_ignored_when_policy_drops_the_owner(self):
        plan = _plan(
            objectives=[_objective(owner=None)],
            programmes=[_programme(covers=["OBJ-ESCAPES"])],
        )
        result = assess_planning(
            _case(plan=plan, policy={"require_objective_owner": False})
        )
        self.assertEqual(result["verdict"], PLAN_ESTABLISHED)

    def test_a_resource_shortfall_outranks_an_uncovered_objective(self):
        plan = _plan(
            resources=[_resource(planned_units=100.0)],
            programmes=[],
        )
        result = assess_planning(_case(plan=plan))
        self.assertEqual(result["verdict"], RESOURCES_UNDER_PLANNED)

    def test_an_uncovered_objective_is_the_last_verdict_before_pass(self):
        result = assess_planning(_case(plan=_plan(programmes=[])))
        self.assertEqual(result["verdict"], OBJECTIVES_UNCOVERED)
        self.assertEqual(len(result["uncovered_objectives"]), 2)

    def test_a_dangling_reference_is_an_advisory_not_a_verdict(self):
        plan = _plan(
            programmes=[_programme(covers=["OBJ-ESCAPES", "OBJ-UPTIME", "OBJ-GHOST"])]
        )
        result = assess_planning(_case(plan=plan))
        self.assertEqual(result["verdict"], PLAN_ESTABLISHED)
        self.assertEqual(len(result["dangling_programme_references"]), 1)

    def test_low_attainment_is_an_advisory_not_a_verdict(self):
        plan = _plan(
            objectives=[
                _objective("OBJ-ESCAPES", target=0.0, achieved=4.0),
                _objective("OBJ-UPTIME", target=0.0, achieved=3.0),
            ],
            programmes=[_programme(covers=["OBJ-ESCAPES", "OBJ-UPTIME"])],
        )
        result = assess_planning(_case(plan=plan))
        self.assertEqual(result["verdict"], PLAN_ESTABLISHED)
        self.assertAlmostEqual(result["objective_attainment"], 0.0, places=9)
        self.assertEqual(len(result["advisories"]), 2)

    def test_a_case_without_a_plan_is_refused(self):
        with self.assertRaises(ValueError):
            assess_planning({"policy": {}})

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_planning(("plan",))


if __name__ == "__main__":
    unittest.main()
