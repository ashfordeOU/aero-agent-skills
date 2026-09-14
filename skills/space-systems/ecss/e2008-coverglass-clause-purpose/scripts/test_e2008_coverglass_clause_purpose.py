#!/usr/bin/env python3
"""Contract test for the generic coverglass rule scope (offline)."""

import copy
import unittest

from e2008_coverglass_clause_purpose_logic import (
    APPLICATIONS,
    COATINGS,
    DEFAULT_SCOPE_POLICY,
    HERITAGE_STATES,
    OUTSIDE_SCOPE,
    RULE_FAMILIES,
    RULES_COVERED,
    RULES_PARTIAL,
    RULES_UNCOVERED,
    applicable_rule_families,
    assess_clause_scope,
    family_coverage,
    normalise_coatings,
    required_activities,
    scope_coverage_index,
    validate_scope_policy,
)


def _all_activities(coatings=()):
    activities = []
    for family in RULE_FAMILIES:
        activities.extend(required_activities(family, coatings))
    return activities


FULL_CASE = {
    "application": "space-photovoltaic-assembly",
    "heritage_state": "new-design",
    "coatings": ["antireflective-coating", "conductive-coating"],
    "process_changed": False,
    "coating_changed": False,
    "declared_activities": _all_activities(
        ("antireflective-coating", "conductive-coating")
    ),
}

COUPON_CASE = {
    "application": "ground-test-coupon",
    "heritage_state": "new-design",
    "coatings": [],
    "declared_activities": [],
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_scope_policy(DEFAULT_SCOPE_POLICY), DEFAULT_SCOPE_POLICY)

    def test_policy_weights_every_family(self):
        for family in RULE_FAMILIES:
            self.assertIn(family, DEFAULT_SCOPE_POLICY["family_weights"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_scope_policy("default")

    def test_policy_missing_a_family_weight_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCOPE_POLICY)
        del broken["family_weights"]["test-programme"]
        with self.assertRaises(ValueError):
            validate_scope_policy(broken)

    def test_policy_with_zero_weight_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCOPE_POLICY)
        broken["family_weights"]["manufacture-control"] = 0.0
        with self.assertRaises(ValueError):
            validate_scope_policy(broken)

    def test_policy_floor_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_SCOPE_POLICY)
        broken["partial_index_floor"] = 1.4
        with self.assertRaises(ValueError):
            validate_scope_policy(broken)


class CoatingStackTests(unittest.TestCase):
    def test_stack_is_deduplicated_and_ordered(self):
        self.assertEqual(
            normalise_coatings(
                ["conductive-coating", "antireflective-coating", "conductive-coating"]
            ),
            ("antireflective-coating", "conductive-coating"),
        )

    def test_empty_stack_is_allowed(self):
        self.assertEqual(normalise_coatings([]), ())

    def test_unknown_coating_rejected(self):
        with self.assertRaises(ValueError):
            normalise_coatings(["gold-flash"])

    def test_bare_string_stack_rejected(self):
        with self.assertRaises(ValueError):
            normalise_coatings("antireflective-coating")


class ApplicabilityTests(unittest.TestCase):
    def test_space_photovoltaic_new_design_pulls_in_every_family(self):
        families = applicable_rule_families(
            "space-photovoltaic-assembly", "new-design"
        )
        for family in RULE_FAMILIES:
            self.assertTrue(families[family]["applicable"], family)

    def test_ground_coupon_is_outside_every_family(self):
        families = applicable_rule_families("ground-test-coupon", "new-design")
        for family in RULE_FAMILIES:
            self.assertFalse(families[family]["applicable"], family)

    def test_unchanged_qualified_heritage_drops_qualification_evidence(self):
        families = applicable_rule_families(
            "space-photovoltaic-assembly", "qualified-heritage"
        )
        self.assertFalse(families["qualification-evidence"]["applicable"])
        self.assertTrue(families["manufacture-control"]["applicable"])

    def test_process_change_restores_qualification_evidence(self):
        families = applicable_rule_families(
            "space-photovoltaic-assembly", "qualified-heritage", process_changed=True
        )
        self.assertTrue(families["qualification-evidence"]["applicable"])
        self.assertIn("process change", families["qualification-evidence"]["reason"])

    def test_coating_change_restores_qualification_evidence(self):
        families = applicable_rule_families(
            "space-photovoltaic-assembly", "qualified-heritage", coating_changed=True
        )
        self.assertTrue(families["qualification-evidence"]["applicable"])

    def test_unknown_application_rejected(self):
        with self.assertRaises(ValueError):
            applicable_rule_families("submarine-window", "new-design")

    def test_unknown_heritage_state_rejected(self):
        with self.assertRaises(ValueError):
            applicable_rule_families("space-photovoltaic-assembly", "probably-fine")

    def test_non_boolean_process_flag_rejected(self):
        with self.assertRaises(ValueError):
            applicable_rule_families(
                "space-photovoltaic-assembly", "new-design", process_changed="yes"
            )


class RequiredActivityTests(unittest.TestCase):
    def test_each_family_owes_at_least_one_activity(self):
        for family in RULE_FAMILIES:
            self.assertTrue(required_activities(family))

    def test_each_coating_adds_a_test_obligation(self):
        bare = required_activities("test-programme")
        coated = required_activities("test-programme", ["conductive-coating"])
        self.assertEqual(len(coated), len(bare) + 1)
        self.assertIn("conductive-coating-surface-conductivity-check", coated)

    def test_each_coating_adds_a_qualification_obligation(self):
        coated = required_activities(
            "qualification-evidence", ["uv-reflective-coating"]
        )
        self.assertIn("uv-reflective-coating-qualification-evidence", coated)

    def test_coatings_do_not_change_manufacture_control(self):
        self.assertEqual(
            required_activities("manufacture-control"),
            required_activities("manufacture-control", list(COATINGS)),
        )

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            required_activities("paperwork")


class FamilyCoverageTests(unittest.TestCase):
    def test_complete_declaration_scores_one(self):
        coverage = family_coverage(
            "test-programme", required_activities("test-programme")
        )
        self.assertAlmostEqual(coverage["fraction"], 1.0, places=9)
        self.assertEqual(coverage["missing"], ())

    def test_empty_declaration_scores_zero(self):
        coverage = family_coverage("test-programme", [])
        self.assertAlmostEqual(coverage["fraction"], 0.0, places=9)
        self.assertEqual(len(coverage["missing"]), 3)

    def test_two_of_three_scores_two_thirds(self):
        required = required_activities("manufacture-control")
        coverage = family_coverage("manufacture-control", required[:2])
        self.assertAlmostEqual(coverage["fraction"], 2.0 / 3.0, places=9)

    def test_unrelated_declarations_are_ignored(self):
        coverage = family_coverage("test-programme", ["a-lunch-order"])
        self.assertAlmostEqual(coverage["fraction"], 0.0, places=9)

    def test_non_sequence_declaration_rejected(self):
        with self.assertRaises(ValueError):
            family_coverage("test-programme", 3)


class CoverageIndexTests(unittest.TestCase):
    def test_all_families_complete_gives_one(self):
        coverage = {
            family: {"fraction": 1.0} for family in RULE_FAMILIES
        }
        self.assertAlmostEqual(scope_coverage_index(coverage), 1.0, places=9)

    def test_all_families_empty_gives_zero(self):
        coverage = {family: {"fraction": 0.0} for family in RULE_FAMILIES}
        self.assertAlmostEqual(scope_coverage_index(coverage), 0.0, places=9)

    def test_index_is_weighted_not_a_plain_mean(self):
        coverage = {
            "manufacture-control": {"fraction": 1.0},
            "test-programme": {"fraction": 1.0},
            "qualification-evidence": {"fraction": 0.0},
        }
        self.assertAlmostEqual(scope_coverage_index(coverage), 0.6, places=9)

    def test_index_over_two_families_renormalises(self):
        coverage = {
            "manufacture-control": {"fraction": 1.0},
            "test-programme": {"fraction": 0.0},
        }
        self.assertAlmostEqual(scope_coverage_index(coverage), 0.5, places=9)

    def test_out_of_range_fraction_rejected(self):
        with self.assertRaises(ValueError):
            scope_coverage_index({"test-programme": {"fraction": 1.5}})

    def test_unknown_family_in_coverage_rejected(self):
        with self.assertRaises(ValueError):
            scope_coverage_index({"vibe-check": {"fraction": 1.0}})


class AssessmentTests(unittest.TestCase):
    def test_fully_declared_case_is_covered(self):
        result = assess_clause_scope(FULL_CASE)
        self.assertEqual(result["verdict"], RULES_COVERED)
        self.assertAlmostEqual(result["coverage_index"], 1.0, places=9)
        self.assertEqual(result["missing_activities"], ())

    def test_ground_coupon_is_outside_the_clause(self):
        result = assess_clause_scope(COUPON_CASE)
        self.assertEqual(result["verdict"], OUTSIDE_SCOPE)
        self.assertIsNone(result["coverage_index"])
        self.assertEqual(result["coverage"], {})

    def test_missing_one_activity_is_partial(self):
        declared = list(FULL_CASE["declared_activities"])
        declared.remove("coverglass-dimensional-inspection")
        result = assess_clause_scope(_case(FULL_CASE, declared_activities=declared))
        self.assertEqual(result["verdict"], RULES_PARTIAL)
        self.assertIn("coverglass-dimensional-inspection", result["missing_activities"])

    def test_an_untouched_family_is_uncovered_however_good_the_rest(self):
        declared = [
            a
            for a in FULL_CASE["declared_activities"]
            if a not in required_activities("qualification-evidence", FULL_CASE["coatings"])
        ]
        result = assess_clause_scope(_case(FULL_CASE, declared_activities=declared))
        self.assertEqual(result["verdict"], RULES_UNCOVERED)
        self.assertTrue(
            any("qualification-evidence family" in f for f in result["findings"])
        )

    def test_nothing_declared_is_uncovered(self):
        result = assess_clause_scope(_case(FULL_CASE, declared_activities=[]))
        self.assertEqual(result["verdict"], RULES_UNCOVERED)
        self.assertAlmostEqual(result["coverage_index"], 0.0, places=9)

    def test_unchanged_heritage_drops_the_qualification_obligations(self):
        declared = _all_activities(())
        result = assess_clause_scope(
            {
                "application": "space-photovoltaic-assembly",
                "heritage_state": "qualified-heritage",
                "coatings": [],
                "declared_activities": declared,
            }
        )
        self.assertEqual(result["verdict"], RULES_COVERED)
        self.assertNotIn("qualification-evidence", result["coverage"])
        self.assertTrue(any("qualified heritage" in f for f in result["findings"]))

    def test_index_exactly_on_the_partial_floor_still_reads_partial(self):
        policy = copy.deepcopy(DEFAULT_SCOPE_POLICY)
        policy["family_weights"] = {f: 1.0 for f in RULE_FAMILIES}
        policy["partial_index_floor"] = 2.0 / 3.0
        declared = []
        for family in RULE_FAMILIES:
            needed = required_activities(family)
            declared.extend(needed if family != "test-programme" else needed[:2])
        case = {
            "application": "space-photovoltaic-assembly",
            "heritage_state": "new-design",
            "coatings": [],
            "declared_activities": declared,
        }
        result = assess_clause_scope(case, policy)
        self.assertEqual(result["verdict"], RULES_PARTIAL)

    def test_coating_stack_is_reported_normalised(self):
        result = assess_clause_scope(
            _case(
                FULL_CASE,
                coatings=["conductive-coating", "antireflective-coating"],
            )
        )
        self.assertEqual(
            result["coatings"], ("antireflective-coating", "conductive-coating")
        )

    def test_adding_a_coating_can_break_a_covered_case(self):
        case = _case(FULL_CASE, coatings=list(COATINGS))
        result = assess_clause_scope(case)
        self.assertNotEqual(result["verdict"], RULES_COVERED)
        self.assertIn(
            "uv-reflective-coating-cutoff-verification", result["missing_activities"]
        )

    def test_every_application_is_decidable(self):
        for application in APPLICATIONS:
            result = assess_clause_scope(_case(FULL_CASE, application=application))
            self.assertIn(
                result["verdict"],
                (OUTSIDE_SCOPE, RULES_COVERED, RULES_PARTIAL, RULES_UNCOVERED),
            )

    def test_every_heritage_state_is_decidable(self):
        for state in HERITAGE_STATES:
            result = assess_clause_scope(_case(FULL_CASE, heritage_state=state))
            self.assertIsNotNone(result["coverage_index"])

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_clause_scope("space-photovoltaic-assembly")

    def test_missing_application_rejected(self):
        case = _case(FULL_CASE)
        del case["application"]
        with self.assertRaises(ValueError):
            assess_clause_scope(case)

    def test_unknown_coating_in_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_clause_scope(_case(FULL_CASE, coatings=["sputtered-unobtainium"]))


if __name__ == "__main__":
    unittest.main()
