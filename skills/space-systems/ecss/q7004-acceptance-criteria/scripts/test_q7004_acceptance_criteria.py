#!/usr/bin/env python3
"""Contract test for the per-category acceptance criteria (offline)."""

import copy
import unittest

from q7004_acceptance_criteria_logic import (
    ACCEPTED,
    BONDED_ITEM,
    DEFAULT_ACCEPTANCE_POLICY,
    ELECTRONIC_ITEM,
    ITEM_CATEGORIES,
    MET,
    NOT_DEMONSTRATED,
    NOT_MET,
    OPTICAL_ITEM,
    REJECTED,
    STRUCTURAL_ITEM,
    UNDEMONSTRATED,
    applicable_criteria,
    apply_acceptance_criteria,
    criterion_limit,
    evaluate_criterion,
    validate_acceptance_policy,
)

STRUCTURAL_CASE = {
    "item_id": "BRACKET-01",
    "category": STRUCTURAL_ITEM,
    "observations": {
        "cracking_observed": False,
        "permanent_deformation_observed": False,
        "mass_loss_pct": 0.02,
    },
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    observations = overrides.pop("observations", None)
    case.update(overrides)
    if observations is not None:
        case["observations"] = observations
    return case


def _with_observation(base, key, value):
    case = copy.deepcopy(base)
    case["observations"][key] = value
    return case


def _without_observation(base, key):
    case = copy.deepcopy(base)
    del case["observations"][key]
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_acceptance_policy(DEFAULT_ACCEPTANCE_POLICY),
            DEFAULT_ACCEPTANCE_POLICY,
        )

    def test_every_category_carries_criteria(self):
        for category in ITEM_CATEGORIES:
            self.assertGreater(len(applicable_criteria(category)), 0)

    def test_policy_missing_a_category_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_POLICY)
        del broken["applicability"][OPTICAL_ITEM]
        with self.assertRaises(ValueError):
            validate_acceptance_policy(broken)

    def test_a_criterion_with_an_unknown_kind_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_POLICY)
        broken["criteria"]["no-cracking"]["kind"] = "eyeball"
        with self.assertRaises(ValueError):
            validate_acceptance_policy(broken)

    def test_applicability_naming_an_unknown_criterion_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_POLICY)
        broken["applicability"][STRUCTURAL_ITEM] = ("no-rust",)
        with self.assertRaises(ValueError):
            validate_acceptance_policy(broken)

    def test_a_bounded_criterion_without_a_limit_for_its_category_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_POLICY)
        del broken["criteria"]["mass-loss-within-limit"]["limits"][STRUCTURAL_ITEM]
        with self.assertRaises(ValueError):
            validate_acceptance_policy(broken)

    def test_a_repeated_criterion_in_one_category_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_POLICY)
        broken["applicability"][STRUCTURAL_ITEM] = ("no-cracking", "no-cracking")
        with self.assertRaises(ValueError):
            validate_acceptance_policy(broken)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_policy("house rules")


class CriterionTests(unittest.TestCase):
    def test_a_presence_criterion_is_met_when_nothing_was_seen(self):
        result = evaluate_criterion(
            "no-cracking", STRUCTURAL_ITEM, {"cracking_observed": False}
        )
        self.assertEqual(result["status"], MET)

    def test_a_presence_criterion_is_not_met_when_something_was_seen(self):
        result = evaluate_criterion(
            "no-cracking", STRUCTURAL_ITEM, {"cracking_observed": True}
        )
        self.assertEqual(result["status"], NOT_MET)

    def test_an_unrecorded_observation_is_undemonstrated_not_met(self):
        result = evaluate_criterion("no-cracking", STRUCTURAL_ITEM, {})
        self.assertEqual(result["status"], NOT_DEMONSTRATED)
        self.assertIn("undemonstrated", result["detail"])

    def test_a_non_boolean_presence_observation_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_criterion(
                "no-cracking", STRUCTURAL_ITEM, {"cracking_observed": "none seen"}
            )

    def test_a_bounded_criterion_is_met_below_its_limit(self):
        result = evaluate_criterion(
            "mass-loss-within-limit", STRUCTURAL_ITEM, {"mass_loss_pct": 0.01}
        )
        self.assertEqual(result["status"], MET)

    def test_a_value_landing_on_the_bound_is_met(self):
        limit = criterion_limit("mass-loss-within-limit", STRUCTURAL_ITEM)
        result = evaluate_criterion(
            "mass-loss-within-limit", STRUCTURAL_ITEM, {"mass_loss_pct": limit}
        )
        self.assertAlmostEqual(result["value"], limit, places=9)
        self.assertEqual(result["status"], MET)

    def test_a_value_above_the_bound_is_not_met(self):
        result = evaluate_criterion(
            "mass-loss-within-limit", STRUCTURAL_ITEM, {"mass_loss_pct": 0.5}
        )
        self.assertEqual(result["status"], NOT_MET)

    def test_a_negative_measurement_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_criterion(
                "mass-loss-within-limit", STRUCTURAL_ITEM, {"mass_loss_pct": -0.01}
            )

    def test_an_unknown_criterion_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_criterion("no-rust", STRUCTURAL_ITEM, {})

    def test_a_bound_asked_of_a_presence_criterion_rejected(self):
        with self.assertRaises(ValueError):
            criterion_limit("no-cracking", STRUCTURAL_ITEM)

    def test_a_bound_asked_for_the_wrong_category_rejected(self):
        with self.assertRaises(ValueError):
            criterion_limit("transmittance-loss-within-limit", STRUCTURAL_ITEM)

    def test_the_bonded_mass_allowance_is_looser_than_the_structural_one(self):
        bonded = criterion_limit("mass-loss-within-limit", BONDED_ITEM)
        structural = criterion_limit("mass-loss-within-limit", STRUCTURAL_ITEM)
        self.assertGreater(bonded, structural)


class ItemVerdictTests(unittest.TestCase):
    def test_a_clean_structural_item_is_accepted(self):
        verdict = apply_acceptance_criteria(STRUCTURAL_CASE)
        self.assertEqual(verdict["verdict"], ACCEPTED)
        self.assertEqual(verdict["met_count"], verdict["criteria_count"])

    def test_a_cracked_item_is_rejected(self):
        verdict = apply_acceptance_criteria(
            _with_observation(STRUCTURAL_CASE, "cracking_observed", True)
        )
        self.assertEqual(verdict["verdict"], REJECTED)
        self.assertEqual(verdict["not_met_count"], 1)

    def test_a_missing_observation_leaves_the_item_undemonstrated(self):
        verdict = apply_acceptance_criteria(
            _without_observation(STRUCTURAL_CASE, "mass_loss_pct")
        )
        self.assertEqual(verdict["verdict"], UNDEMONSTRATED)
        self.assertEqual(verdict["undemonstrated_count"], 1)

    def test_a_rejection_outranks_an_undemonstrated_criterion(self):
        case = _without_observation(STRUCTURAL_CASE, "mass_loss_pct")
        case["observations"]["cracking_observed"] = True
        verdict = apply_acceptance_criteria(case)
        self.assertEqual(verdict["verdict"], REJECTED)

    def test_an_observation_the_category_does_not_judge_is_surfaced(self):
        verdict = apply_acceptance_criteria(
            _with_observation(STRUCTURAL_CASE, "transmittance_loss_pct", 4.0)
        )
        self.assertIn("transmittance_loss_pct", verdict["unjudged_observations"])
        self.assertTrue(any("not judged" in f for f in verdict["findings"]))

    def test_an_electronic_item_is_judged_on_drift_not_transmittance(self):
        names = applicable_criteria(ELECTRONIC_ITEM)
        self.assertIn("performance-drift-within-limit", names)
        self.assertNotIn("transmittance-loss-within-limit", names)

    def test_a_bonded_item_is_judged_on_the_bond_line(self):
        verdict = apply_acceptance_criteria(
            {
                "item_id": "PANEL-07",
                "category": BONDED_ITEM,
                "observations": {
                    "delamination_observed": True,
                    "adhesion_loss_observed": False,
                    "mass_loss_pct": 0.1,
                },
            }
        )
        self.assertEqual(verdict["verdict"], REJECTED)
        self.assertTrue(any("no-delamination" in f for f in verdict["findings"]))

    def test_the_same_observations_can_pass_one_category_and_fail_another(self):
        loose = apply_acceptance_criteria(
            {
                "item_id": "PANEL-08",
                "category": BONDED_ITEM,
                "observations": {
                    "delamination_observed": False,
                    "adhesion_loss_observed": False,
                    "mass_loss_pct": 0.3,
                },
            }
        )
        tight = apply_acceptance_criteria(
            _with_observation(STRUCTURAL_CASE, "mass_loss_pct", 0.3)
        )
        self.assertEqual(loose["verdict"], ACCEPTED)
        self.assertEqual(tight["verdict"], REJECTED)

    def test_every_verdict_carries_the_undemonstrated_reporting_duty(self):
        verdict = apply_acceptance_criteria(STRUCTURAL_CASE)
        self.assertTrue(any("not a criterion" in d for d in verdict["duties"]))

    def test_an_undemonstrated_verdict_asks_for_the_missing_observation(self):
        verdict = apply_acceptance_criteria(
            _without_observation(STRUCTURAL_CASE, "mass_loss_pct")
        )
        self.assertTrue(any("missing observations" in d for d in verdict["duties"]))

    def test_a_blank_item_id_rejected(self):
        with self.assertRaises(ValueError):
            apply_acceptance_criteria(_case(STRUCTURAL_CASE, item_id="  "))

    def test_an_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            apply_acceptance_criteria(_case(STRUCTURAL_CASE, category="harness-item"))

    def test_non_mapping_observations_rejected(self):
        with self.assertRaises(ValueError):
            apply_acceptance_criteria(
                _case(STRUCTURAL_CASE, observations="no cracks seen")
            )

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            apply_acceptance_criteria("bracket looked fine")


if __name__ == "__main__":
    unittest.main()
