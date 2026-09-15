#!/usr/bin/env python3
"""Contract test for the Class 1 selection general requirements (offline)."""

import copy
import unittest

from q60_class_1_selection_general_requirements_logic import (
    BLOCKING_PREREQUISITES,
    DEFAULT_PREREQUISITE_WEIGHTS,
    MIN_READINESS_INDEX,
    SELECTION_AUTHORIZED,
    SELECTION_BLOCKED,
    SELECTION_PREREQUISITES,
    SELECTION_WITH_ACTIONS,
    applicable_prerequisites,
    assess_selection_readiness,
    is_blocking,
    next_prerequisite_to_close,
    normalise_prerequisite_states,
    open_blockers,
    prerequisite_weight,
    readiness_index,
    validate_weight_table,
)

ALL_CLOSED = {name: {"state": "closed"} for name in SELECTION_PREREQUISITES}

GOOD_CASE = {
    "part_reference": "cap-ceramic-100n-50v",
    "prerequisites": copy.deepcopy(ALL_CLOSED),
}

# Sums to 10.0 so a single open 1.0-weight item lands the index on 0.90 exactly.
ON_THRESHOLD_WEIGHTS = {
    "mission-environment-defined": 1.5,
    "component-requirements-specified": 1.5,
    "component-control-plan-approved": 1.5,
    "declared-component-list-opened": 1.5,
    "quality-level-target-set": 1.5,
    "radiation-environment-quantified": 1.0,
    "lifetime-and-mission-duration-fixed": 0.5,
    "procurement-lead-time-assessed": 1.0,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    states = overrides.pop("open", ())
    for name in states:
        case["prerequisites"][name] = {"state": "open"}
    case.update(overrides)
    return case


class WeightTableTests(unittest.TestCase):
    def test_default_table_validates(self):
        self.assertIs(
            validate_weight_table(DEFAULT_PREREQUISITE_WEIGHTS),
            DEFAULT_PREREQUISITE_WEIGHTS,
        )

    def test_table_covers_every_prerequisite(self):
        for name in SELECTION_PREREQUISITES:
            self.assertIn(name, DEFAULT_PREREQUISITE_WEIGHTS)

    def test_every_weight_is_positive(self):
        for name in SELECTION_PREREQUISITES:
            self.assertGreater(prerequisite_weight(name), 0.0)

    def test_non_mapping_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_weight_table("default")

    def test_table_missing_a_prerequisite_rejected(self):
        broken = dict(DEFAULT_PREREQUISITE_WEIGHTS)
        del broken["quality-level-target-set"]
        with self.assertRaises(ValueError):
            validate_weight_table(broken)

    def test_table_with_an_unknown_prerequisite_rejected(self):
        broken = dict(DEFAULT_PREREQUISITE_WEIGHTS)
        broken["favourite-supplier-chosen"] = 1.0
        with self.assertRaises(ValueError):
            validate_weight_table(broken)

    def test_zero_weight_rejected(self):
        broken = dict(DEFAULT_PREREQUISITE_WEIGHTS)
        broken["procurement-lead-time-assessed"] = 0.0
        with self.assertRaises(ValueError):
            validate_weight_table(broken)

    def test_unknown_prerequisite_weight_rejected(self):
        with self.assertRaises(ValueError):
            prerequisite_weight("favourite-supplier-chosen")


class BlockingTests(unittest.TestCase):
    def test_control_plan_is_blocking(self):
        self.assertTrue(is_blocking("component-control-plan-approved"))

    def test_lead_time_is_not_blocking(self):
        self.assertFalse(is_blocking("procurement-lead-time-assessed"))

    def test_blocking_set_is_a_subset_of_the_prerequisites(self):
        self.assertTrue(BLOCKING_PREREQUISITES.issubset(set(SELECTION_PREREQUISITES)))

    def test_unknown_name_is_rejected_rather_than_assumed_open(self):
        with self.assertRaises(ValueError):
            is_blocking("favourite-supplier-chosen")


class StateDeclarationTests(unittest.TestCase):
    def test_bare_state_strings_are_accepted(self):
        states = {name: "closed" for name in SELECTION_PREREQUISITES}
        normalised = normalise_prerequisite_states(states)
        self.assertEqual(normalised["quality-level-target-set"]["state"], "closed")

    def test_undeclared_prerequisite_rejected(self):
        states = copy.deepcopy(ALL_CLOSED)
        del states["radiation-environment-quantified"]
        with self.assertRaises(ValueError):
            normalise_prerequisite_states(states)

    def test_unknown_prerequisite_rejected(self):
        states = copy.deepcopy(ALL_CLOSED)
        states["favourite-supplier-chosen"] = {"state": "closed"}
        with self.assertRaises(ValueError):
            normalise_prerequisite_states(states)

    def test_unknown_state_rejected(self):
        states = copy.deepcopy(ALL_CLOSED)
        states["procurement-lead-time-assessed"] = {"state": "probably-fine"}
        with self.assertRaises(ValueError):
            normalise_prerequisite_states(states)

    def test_waiver_without_justification_rejected(self):
        states = copy.deepcopy(ALL_CLOSED)
        states["radiation-environment-quantified"] = {"state": "not-applicable"}
        with self.assertRaises(ValueError):
            normalise_prerequisite_states(states)

    def test_blocking_prerequisite_cannot_be_waived(self):
        states = copy.deepcopy(ALL_CLOSED)
        states["component-control-plan-approved"] = {
            "state": "not-applicable",
            "justification": "heritage build",
        }
        with self.assertRaises(ValueError):
            normalise_prerequisite_states(states)

    def test_empty_declaration_rejected(self):
        with self.assertRaises(ValueError):
            normalise_prerequisite_states({})

    def test_waived_item_leaves_the_applicable_set(self):
        states = copy.deepcopy(ALL_CLOSED)
        states["procurement-lead-time-assessed"] = {
            "state": "not-applicable",
            "justification": "part already held in bonded store",
        }
        applicable = applicable_prerequisites(states)
        self.assertNotIn("procurement-lead-time-assessed", applicable)
        self.assertEqual(len(applicable), len(SELECTION_PREREQUISITES) - 1)


class ReadinessIndexTests(unittest.TestCase):
    def test_all_closed_is_a_full_index(self):
        self.assertAlmostEqual(readiness_index(ALL_CLOSED), 1.0, places=9)

    def test_index_drops_by_the_open_weight_share(self):
        states = copy.deepcopy(ALL_CLOSED)
        states["procurement-lead-time-assessed"] = {"state": "open"}
        self.assertAlmostEqual(readiness_index(states), 8.5 / 9.0, places=9)

    def test_waived_weight_leaves_the_denominator(self):
        states = copy.deepcopy(ALL_CLOSED)
        states["procurement-lead-time-assessed"] = {
            "state": "not-applicable",
            "justification": "part already held in bonded store",
        }
        self.assertAlmostEqual(readiness_index(states), 1.0, places=9)

    def test_index_on_the_threshold_is_recognised_exactly(self):
        states = copy.deepcopy(ALL_CLOSED)
        states["procurement-lead-time-assessed"] = {"state": "open"}
        self.assertAlmostEqual(
            readiness_index(states, ON_THRESHOLD_WEIGHTS),
            MIN_READINESS_INDEX,
            places=9,
        )


class NextActionTests(unittest.TestCase):
    def test_no_next_action_when_everything_is_closed(self):
        self.assertIsNone(next_prerequisite_to_close(ALL_CLOSED))

    def test_blocking_item_outranks_a_heavier_non_blocking_one(self):
        states = copy.deepcopy(ALL_CLOSED)
        states["declared-component-list-opened"] = {"state": "open"}
        states["radiation-environment-quantified"] = {"state": "open"}
        self.assertEqual(
            next_prerequisite_to_close(states), "declared-component-list-opened"
        )

    def test_heaviest_open_item_wins_inside_a_group(self):
        states = copy.deepcopy(ALL_CLOSED)
        states["radiation-environment-quantified"] = {"state": "open"}
        states["procurement-lead-time-assessed"] = {"state": "open"}
        self.assertEqual(
            next_prerequisite_to_close(states), "radiation-environment-quantified"
        )

    def test_ties_break_on_declaration_order(self):
        states = copy.deepcopy(ALL_CLOSED)
        states["radiation-environment-quantified"] = {"state": "open"}
        states["lifetime-and-mission-duration-fixed"] = {"state": "open"}
        self.assertEqual(
            next_prerequisite_to_close(states), "radiation-environment-quantified"
        )


class AssessSelectionReadinessTests(unittest.TestCase):
    def test_fully_prepared_selection_is_authorized(self):
        result = assess_selection_readiness(GOOD_CASE)
        self.assertEqual(result["verdict"], SELECTION_AUTHORIZED)
        self.assertTrue(result["authorized"])
        self.assertEqual(result["findings"], [])

    def test_open_blocker_blocks_the_selection(self):
        result = assess_selection_readiness(
            _case(open=("component-control-plan-approved",))
        )
        self.assertEqual(result["verdict"], SELECTION_BLOCKED)
        self.assertIn("component-control-plan-approved", result["open_blockers"])

    def test_a_blocker_is_not_bought_back_by_weight_elsewhere(self):
        result = assess_selection_readiness(
            _case(open=("declared-component-list-opened",))
        )
        self.assertEqual(result["verdict"], SELECTION_BLOCKED)
        self.assertGreater(result["readiness_index"], 0.8)

    def test_light_open_item_still_authorizes(self):
        result = assess_selection_readiness(
            _case(open=("procurement-lead-time-assessed",))
        )
        self.assertEqual(result["verdict"], SELECTION_AUTHORIZED)

    def test_heavier_open_item_needs_actions(self):
        result = assess_selection_readiness(
            _case(open=("radiation-environment-quantified",))
        )
        self.assertEqual(result["verdict"], SELECTION_WITH_ACTIONS)
        self.assertTrue(any("readiness index" in f for f in result["findings"]))

    def test_index_on_the_threshold_authorizes_rather_than_flags(self):
        result = assess_selection_readiness(
            _case(open=("procurement-lead-time-assessed",)),
            ON_THRESHOLD_WEIGHTS,
        )
        self.assertAlmostEqual(
            result["readiness_index"], MIN_READINESS_INDEX, places=9
        )
        self.assertEqual(result["verdict"], SELECTION_AUTHORIZED)

    def test_waived_item_is_reported_not_hidden(self):
        case = _case()
        case["prerequisites"]["procurement-lead-time-assessed"] = {
            "state": "not-applicable",
            "justification": "part already held in bonded store",
        }
        result = assess_selection_readiness(case)
        self.assertIn(
            "procurement-lead-time-assessed", result["waived_prerequisites"]
        )

    def test_missing_part_reference_rejected(self):
        case = _case()
        del case["part_reference"]
        with self.assertRaises(ValueError):
            assess_selection_readiness(case)

    def test_blank_part_reference_rejected(self):
        with self.assertRaises(ValueError):
            assess_selection_readiness(_case(part_reference="   "))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_selection_readiness(["cap-ceramic-100n-50v"])

    def test_next_prerequisite_is_named_when_work_remains(self):
        result = assess_selection_readiness(
            _case(open=("radiation-environment-quantified",))
        )
        self.assertEqual(
            result["next_prerequisite"], "radiation-environment-quantified"
        )

    def test_every_blocking_prerequisite_blocks_on_its_own(self):
        for name in sorted(BLOCKING_PREREQUISITES):
            result = assess_selection_readiness(_case(open=(name,)))
            self.assertEqual(result["verdict"], SELECTION_BLOCKED)
            self.assertEqual(result["open_blockers"], (name,))


if __name__ == "__main__":
    unittest.main(verbosity=1)
