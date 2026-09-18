#!/usr/bin/env python3
"""Contract test for corrective and preventive action selection (offline)."""

import copy
import unittest

from q1009_capa_logic import (
    ACTION_TYPES,
    CAUSE_CATEGORIES,
    CONTROL_STRENGTH,
    DETECTION_ONLY,
    SYSTEMIC_CATEGORIES,
    VERDICT_ADEQUATE,
    VERDICT_CONTAINMENT_ONLY,
    VERDICT_INSUFFICIENT,
    control_strength,
    coverage_by_cause,
    prevents_recurrence,
    preventive_gaps,
    select_capa,
    validate_actions,
    validate_root_causes,
)

CAUSE_WORKMANSHIP = {
    "id": "RC1",
    "category": "workmanship",
    "occurrences": 1,
    "evidence": "solder joint cross-section on the failed unit",
}

CAUSE_PROCEDURE = {
    "id": "RC2",
    "category": "procedure",
    "occurrences": 1,
    "evidence": "work order step omits the torque value",
}

CASE = {
    "root_causes": [dict(CAUSE_WORKMANSHIP)],
    "actions": [
        {
            "id": "A1",
            "type": "containment",
            "control": "detection-only",
            "rationale": "screen the built stock before further assembly",
        },
        {
            "id": "A2",
            "type": "corrective",
            "control": "engineering-control",
            "addresses": "RC1",
            "rationale": "fixture holds the part so the joint cannot be reached wrong",
        },
    ],
}


def _case(**overrides):
    case = copy.deepcopy(CASE)
    case.update(overrides)
    return case


class ControlTests(unittest.TestCase):
    def test_elimination_outranks_a_procedure_change(self):
        self.assertGreater(control_strength("elimination"), control_strength("procedure-change"))

    def test_procedure_change_outranks_detection(self):
        self.assertGreater(control_strength("procedure-change"), control_strength(DETECTION_ONLY))

    def test_every_declared_control_has_a_strength(self):
        for control in CONTROL_STRENGTH:
            self.assertGreaterEqual(control_strength(control), 1)

    def test_detection_does_not_prevent_recurrence(self):
        self.assertFalse(prevents_recurrence(DETECTION_ONLY))

    def test_engineering_control_prevents_recurrence(self):
        self.assertTrue(prevents_recurrence("engineering-control"))

    def test_unknown_control_rejected(self):
        with self.assertRaises(ValueError):
            control_strength("wishful-thinking")


class RootCauseTests(unittest.TestCase):
    def test_single_cause_validates(self):
        self.assertEqual(validate_root_causes([CAUSE_WORKMANSHIP])["ids"], ("RC1",))

    def test_systemic_category_owes_a_preventive_action(self):
        result = validate_root_causes([CAUSE_PROCEDURE])
        self.assertIn("RC2", result["preventive_due"])

    def test_every_systemic_category_is_flagged(self):
        for category in SYSTEMIC_CATEGORIES:
            cause = dict(CAUSE_WORKMANSHIP, category=category)
            self.assertIn("RC1", validate_root_causes([cause])["preventive_due"])

    def test_one_off_workmanship_owes_none(self):
        self.assertEqual(validate_root_causes([CAUSE_WORKMANSHIP])["preventive_due"], ())

    def test_repeat_occurrence_owes_a_preventive_action(self):
        cause = dict(CAUSE_WORKMANSHIP, occurrences=2)
        self.assertIn("RC1", validate_root_causes([cause])["preventive_due"])

    def test_threshold_is_configurable(self):
        cause = dict(CAUSE_WORKMANSHIP, occurrences=2)
        self.assertEqual(
            validate_root_causes([cause], recurrence_threshold=3)["preventive_due"], ()
        )

    def test_cause_without_evidence_is_a_finding(self):
        cause = dict(CAUSE_WORKMANSHIP, evidence="")
        self.assertTrue(validate_root_causes([cause])["findings"])

    def test_causes_are_grouped_by_category(self):
        result = validate_root_causes([CAUSE_WORKMANSHIP, CAUSE_PROCEDURE])
        self.assertEqual(result["grouped_by_category"]["procedure"], ("RC2",))

    def test_every_known_category_is_accepted(self):
        for category in CAUSE_CATEGORIES:
            validate_root_causes([dict(CAUSE_WORKMANSHIP, category=category)])

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_root_causes([dict(CAUSE_WORKMANSHIP, category="bad-luck")])

    def test_empty_cause_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_root_causes([])

    def test_duplicate_cause_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_root_causes([CAUSE_WORKMANSHIP, dict(CAUSE_WORKMANSHIP)])

    def test_zero_occurrences_rejected(self):
        with self.assertRaises(ValueError):
            validate_root_causes([dict(CAUSE_WORKMANSHIP, occurrences=0)])


class ActionValidationTests(unittest.TestCase):
    def test_actions_validate_against_the_cause_set(self):
        result = validate_actions(CASE["actions"], {"RC1"})
        self.assertEqual(len(result["actions"]), 2)

    def test_every_action_type_is_accepted(self):
        for atype in ACTION_TYPES:
            action = {
                "id": "A9",
                "type": atype,
                "control": "procedure-change",
                "addresses": "RC1",
                "rationale": "stated",
            }
            validate_actions([action], {"RC1"})

    def test_containment_needs_no_cause(self):
        action = {
            "id": "A1",
            "type": "containment",
            "control": DETECTION_ONLY,
            "rationale": "impound the stock",
        }
        self.assertIsNone(validate_actions([action], {"RC1"})["actions"][0]["addresses"])

    def test_corrective_action_against_an_unknown_cause_rejected(self):
        action = dict(CASE["actions"][1], addresses="RC9")
        with self.assertRaises(ValueError):
            validate_actions([action], {"RC1"})

    def test_action_without_a_rationale_is_a_finding(self):
        action = dict(CASE["actions"][1], rationale="")
        self.assertTrue(validate_actions([action], {"RC1"})["findings"])

    def test_duplicate_action_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_actions([CASE["actions"][1], dict(CASE["actions"][1])], {"RC1"})

    def test_empty_action_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_actions([], {"RC1"})

    def test_non_mapping_action_rejected(self):
        with self.assertRaises(ValueError):
            validate_actions(["fix it"], {"RC1"})


class CoverageTests(unittest.TestCase):
    def test_corrective_action_covers_its_cause(self):
        checked = validate_actions(CASE["actions"], {"RC1"})["actions"]
        coverage = coverage_by_cause(checked, ("RC1",))
        self.assertEqual(coverage["uncovered"], ())
        self.assertEqual(coverage["covered"]["RC1"]["action_ids"], ("A2",))

    def test_containment_does_not_cover_a_cause(self):
        checked = validate_actions([CASE["actions"][0]], {"RC1"})["actions"]
        self.assertEqual(coverage_by_cause(checked, ("RC1",))["uncovered"], ("RC1",))

    def test_detection_only_cover_is_reported(self):
        action = dict(CASE["actions"][1], control=DETECTION_ONLY)
        checked = validate_actions([action], {"RC1"})["actions"]
        coverage = coverage_by_cause(checked, ("RC1",))
        self.assertEqual(coverage["detection_only_causes"], ("RC1",))

    def test_strongest_control_is_kept_per_cause(self):
        weak = dict(CASE["actions"][1], id="A3", control=DETECTION_ONLY)
        checked = validate_actions([CASE["actions"][1], weak], {"RC1"})["actions"]
        coverage = coverage_by_cause(checked, ("RC1",))
        self.assertEqual(
            coverage["covered"]["RC1"]["best_strength"],
            control_strength("engineering-control"),
        )

    def test_preventive_gap_detected(self):
        checked = validate_actions(CASE["actions"], {"RC1"})["actions"]
        self.assertEqual(preventive_gaps(checked, ("RC1",)), ("RC1",))

    def test_preventive_action_closes_the_gap(self):
        preventive = {
            "id": "A4",
            "type": "preventive",
            "control": "procedure-change",
            "addresses": "RC1",
            "rationale": "same step corrected on every comparable work order",
        }
        checked = validate_actions(CASE["actions"] + [preventive], {"RC1"})["actions"]
        self.assertEqual(preventive_gaps(checked, ("RC1",)), ())


class SelectionTests(unittest.TestCase):
    def test_one_off_cause_with_an_engineering_control_is_adequate(self):
        result = select_capa(CASE)
        self.assertEqual(result["verdict"], VERDICT_ADEQUATE)
        self.assertTrue(result["adequate"])

    def test_containment_alone_is_never_adequate(self):
        result = select_capa(_case(actions=[CASE["actions"][0]]))
        self.assertEqual(result["verdict"], VERDICT_CONTAINMENT_ONLY)
        self.assertFalse(result["adequate"])

    def test_detection_only_correction_is_insufficient(self):
        actions = [CASE["actions"][0], dict(CASE["actions"][1], control=DETECTION_ONLY)]
        result = select_capa(_case(actions=actions))
        self.assertEqual(result["verdict"], VERDICT_INSUFFICIENT)
        self.assertIn("RC1", result["detection_only_causes"])

    def test_systemic_cause_without_prevention_is_insufficient(self):
        actions = [dict(CASE["actions"][1], addresses="RC2")]
        result = select_capa(_case(root_causes=[CAUSE_PROCEDURE], actions=actions))
        self.assertEqual(result["verdict"], VERDICT_INSUFFICIENT)
        self.assertIn("RC2", result["preventive_gaps"])

    def test_systemic_cause_with_prevention_is_adequate(self):
        actions = [
            dict(CASE["actions"][1], addresses="RC2"),
            {
                "id": "A5",
                "type": "preventive",
                "control": "procedure-change",
                "addresses": "RC2",
                "rationale": "torque values added to every work order of the family",
            },
        ]
        result = select_capa(_case(root_causes=[CAUSE_PROCEDURE], actions=actions))
        self.assertEqual(result["verdict"], VERDICT_ADEQUATE)

    def test_second_cause_left_uncovered_is_insufficient(self):
        result = select_capa(
            _case(root_causes=[CAUSE_WORKMANSHIP, dict(CAUSE_PROCEDURE, category="material")])
        )
        self.assertIn("RC2", result["uncovered_causes"])
        self.assertFalse(result["adequate"])

    def test_missing_rationale_blocks_adequacy(self):
        actions = [CASE["actions"][0], dict(CASE["actions"][1], rationale=" ")]
        result = select_capa(_case(actions=actions))
        self.assertFalse(result["adequate"])

    def test_weakest_corrective_strength_is_reported(self):
        weak = dict(CASE["actions"][1], id="A6", control="training")
        result = select_capa(_case(actions=CASE["actions"] + [weak]))
        self.assertEqual(result["weakest_corrective_strength"], control_strength("training"))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            select_capa("fix the solder")

    def test_missing_actions_rejected(self):
        case = _case()
        del case["actions"]
        with self.assertRaises(ValueError):
            select_capa(case)


if __name__ == "__main__":
    unittest.main()
