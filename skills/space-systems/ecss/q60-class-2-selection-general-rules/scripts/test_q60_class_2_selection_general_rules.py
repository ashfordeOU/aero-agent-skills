"""Contract tests for the clause 5.2.2.1 Class 2 selection rule flow-down logic."""

import unittest

from q60_class_2_selection_general_rules_logic import (
    COVERAGE_TOLERANCE,
    COVERING_STATES,
    IN_HOUSE_TIER,
    MAX_TIERS,
    RULE_STATES,
    assess_selection_rule_flow_down,
    chain_reach,
    normalize_rule_matrix,
    rule_survival_depth,
    rules_in_force,
    tier_coverage,
    validate_rule_names,
    validate_rule_state,
    validate_tiers,
)

TIERS = {0: "in-house", 1: "prime-subcontractor", 2: "component-broker"}
RULES = (
    "part-approval-before-order",
    "lot-traceability-maintained",
    "derating-rules-applied",
    "customer-deviation-requested",
)
ACCEPTED_EQUIVALENT = {"state": "equivalent", "acceptance_reference": "PA-EQ-22"}
APPROVED_WAIVER = {"state": "waived", "approval_reference": "PA-WVR-31"}


def matrix(**overrides):
    """Return a fully applied rule matrix, with per-rule row overrides."""
    base = {rule: {tier: "applied" for tier in TIERS} for rule in RULES}
    for rule, row in overrides.items():
        target = rule.replace("_", "-")
        base[target] = dict(base[target])
        base[target].update(row)
    return base


def spec(**overrides):
    """Return a clean flow-down spec, with overrides."""
    base = {"tiers": dict(TIERS), "rules": list(RULES), "matrix": matrix()}
    base.update(overrides)
    return base


class TierValidationTests(unittest.TestCase):
    def test_house_chain_validates(self):
        self.assertEqual(validate_tiers(TIERS)[IN_HOUSE_TIER], "in-house")

    def test_chain_with_a_gap_is_refused_rather_than_scored(self):
        with self.assertRaises(ValueError):
            validate_tiers({0: "in-house", 2: "component-broker"})

    def test_chain_without_the_in_house_tier_rejected(self):
        with self.assertRaises(ValueError):
            validate_tiers({1: "prime-subcontractor"})

    def test_blank_tier_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_tiers({0: "   "})

    def test_negative_tier_index_rejected(self):
        with self.assertRaises(ValueError):
            validate_tiers({0: "in-house", -1: "somewhere"})

    def test_empty_chain_rejected(self):
        with self.assertRaises(ValueError):
            validate_tiers({})

    def test_absurdly_deep_chain_rejected(self):
        with self.assertRaises(ValueError):
            validate_tiers({index: "tier-%d" % index for index in range(MAX_TIERS + 2)})

    def test_non_mapping_chain_rejected(self):
        with self.assertRaises(ValueError):
            validate_tiers(["in-house"])


class RuleStateTests(unittest.TestCase):
    def test_states_validate_and_ignore_case(self):
        for state in RULE_STATES:
            self.assertEqual(validate_rule_state(state.upper()), state)

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_rule_state("mostly-applied")

    def test_not_applied_is_the_only_state_outside_the_covering_set(self):
        self.assertEqual(
            tuple(s for s in RULE_STATES if s not in COVERING_STATES), ("not-applied",)
        )

    def test_rule_names_validate(self):
        self.assertEqual(len(validate_rule_names(list(RULES))), len(RULES))

    def test_duplicate_rule_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_rule_names(["derating-rules-applied", "derating-rules-applied"])

    def test_empty_rule_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_rule_names([])

    def test_string_rule_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_rule_names("derating-rules-applied")


class MatrixTests(unittest.TestCase):
    def test_clean_matrix_normalizes(self):
        normalized = normalize_rule_matrix(matrix(), RULES, TIERS)
        self.assertTrue(normalized["derating-rules-applied"][2]["covered"])

    def test_accepted_equivalent_supplier_rule_carries_the_rule(self):
        normalized = normalize_rule_matrix(
            matrix(derating_rules_applied={1: dict(ACCEPTED_EQUIVALENT)}), RULES, TIERS
        )
        entry = normalized["derating-rules-applied"][1]
        self.assertTrue(entry["covered"])
        self.assertIsNone(entry["downgraded_from"])

    def test_equivalence_with_no_acceptance_carries_nothing(self):
        normalized = normalize_rule_matrix(
            matrix(derating_rules_applied={1: {"state": "equivalent"}}), RULES, TIERS
        )
        entry = normalized["derating-rules-applied"][1]
        self.assertFalse(entry["covered"])
        self.assertEqual(entry["downgraded_from"], "equivalent")
        self.assertEqual(entry["state"], "not-applied")

    def test_approved_waiver_counts_as_coverage(self):
        normalized = normalize_rule_matrix(
            matrix(lot_traceability_maintained={2: dict(APPROVED_WAIVER)}), RULES, TIERS
        )
        self.assertTrue(normalized["lot-traceability-maintained"][2]["covered"])

    def test_unapproved_waiver_does_not_count_as_coverage(self):
        normalized = normalize_rule_matrix(
            matrix(lot_traceability_maintained={2: {"state": "waived"}}), RULES, TIERS
        )
        entry = normalized["lot-traceability-maintained"][2]
        self.assertFalse(entry["covered"])
        self.assertEqual(entry["downgraded_from"], "waived")

    def test_blank_approval_reference_does_not_count_as_recorded(self):
        normalized = normalize_rule_matrix(
            matrix(lot_traceability_maintained={2: {"state": "waived", "approval_reference": "  "}}),
            RULES,
            TIERS,
        )
        self.assertFalse(normalized["lot-traceability-maintained"][2]["covered"])

    def test_undeclared_tier_for_a_rule_rejected(self):
        broken = matrix()
        del broken["derating-rules-applied"][2]
        with self.assertRaises(ValueError):
            normalize_rule_matrix(broken, RULES, TIERS)

    def test_rule_declared_at_a_tier_the_chain_does_not_have_rejected(self):
        with self.assertRaises(ValueError):
            normalize_rule_matrix(matrix(derating_rules_applied={5: "applied"}), RULES, TIERS)

    def test_matrix_row_for_an_unlisted_rule_rejected(self):
        extra = matrix()
        extra["coffee-machine-serviced"] = {tier: "applied" for tier in TIERS}
        with self.assertRaises(ValueError):
            normalize_rule_matrix(extra, RULES, TIERS)

    def test_missing_row_rejected(self):
        broken = matrix()
        del broken["customer-deviation-requested"]
        with self.assertRaises(ValueError):
            normalize_rule_matrix(broken, RULES, TIERS)

    def test_mapping_without_a_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_rule_matrix(
                matrix(derating_rules_applied={1: {"acceptance_reference": "PA-EQ-22"}}),
                RULES,
                TIERS,
            )

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            normalize_rule_matrix(matrix(derating_rules_applied={1: 4}), RULES, TIERS)

    def test_non_mapping_matrix_rejected(self):
        with self.assertRaises(ValueError):
            normalize_rule_matrix(["derating-rules-applied"], RULES, TIERS)


class InForceTests(unittest.TestCase):
    def test_every_applied_rule_is_in_force(self):
        normalized = normalize_rule_matrix(matrix(), RULES, TIERS)
        self.assertEqual(len(rules_in_force(normalized)), len(RULES))

    def test_a_rule_not_applied_in_house_is_not_in_force(self):
        normalized = normalize_rule_matrix(
            matrix(customer_deviation_requested={0: "not-applied"}), RULES, TIERS
        )
        self.assertNotIn("customer-deviation-requested", rules_in_force(normalized))

    def test_a_rule_never_in_force_has_no_survival_depth(self):
        normalized = normalize_rule_matrix(
            matrix(customer_deviation_requested={0: "not-applied"}), RULES, TIERS
        )
        self.assertIsNone(
            rule_survival_depth(normalized["customer-deviation-requested"], TIERS)
        )

    def test_a_rule_carried_all_the_way_survives_to_the_last_tier(self):
        normalized = normalize_rule_matrix(matrix(), RULES, TIERS)
        self.assertEqual(
            rule_survival_depth(normalized["derating-rules-applied"], TIERS), 2
        )

    def test_a_rule_lost_at_the_first_supplier_survives_only_in_house(self):
        normalized = normalize_rule_matrix(
            matrix(derating_rules_applied={1: "not-applied"}), RULES, TIERS
        )
        self.assertEqual(
            rule_survival_depth(normalized["derating-rules-applied"], TIERS), IN_HOUSE_TIER
        )

    def test_a_rule_lost_at_the_second_supplier_survives_one_tier_out(self):
        normalized = normalize_rule_matrix(
            matrix(derating_rules_applied={2: "not-applied"}), RULES, TIERS
        )
        self.assertEqual(rule_survival_depth(normalized["derating-rules-applied"], TIERS), 1)

    def test_survival_is_contiguous_not_a_tally(self):
        normalized = normalize_rule_matrix(
            matrix(derating_rules_applied={1: "not-applied", 2: "applied"}), RULES, TIERS
        )
        self.assertEqual(
            rule_survival_depth(normalized["derating-rules-applied"], TIERS), IN_HOUSE_TIER
        )


class CoverageTests(unittest.TestCase):
    def test_clean_chain_covers_every_tier(self):
        normalized = normalize_rule_matrix(matrix(), RULES, TIERS)
        coverage = tier_coverage(normalized, TIERS)
        for tier in TIERS:
            self.assertAlmostEqual(coverage[tier], 1.0, places=9)

    def test_a_rule_out_of_force_leaves_the_denominator(self):
        normalized = normalize_rule_matrix(
            matrix(
                customer_deviation_requested={0: "not-applied", 1: "not-applied", 2: "not-applied"}
            ),
            RULES,
            TIERS,
        )
        coverage = tier_coverage(normalized, TIERS)
        self.assertAlmostEqual(coverage[2], 1.0, places=9)

    def test_one_lost_rule_in_four_reads_three_quarters(self):
        normalized = normalize_rule_matrix(
            matrix(derating_rules_applied={2: "not-applied"}), RULES, TIERS
        )
        coverage = tier_coverage(normalized, TIERS)
        self.assertAlmostEqual(coverage[2], 0.75, places=9)

    def test_chain_is_graded_on_its_weakest_tier_not_its_average(self):
        normalized = normalize_rule_matrix(
            matrix(derating_rules_applied={2: "not-applied"}), RULES, TIERS
        )
        weakest, reach = chain_reach(tier_coverage(normalized, TIERS))
        self.assertEqual(weakest, 2)
        self.assertAlmostEqual(reach, 0.75, places=9)

    def test_a_chain_with_nothing_in_force_is_refused(self):
        normalized = normalize_rule_matrix(
            {rule: {tier: "not-applied" for tier in TIERS} for rule in RULES},
            RULES,
            TIERS,
        )
        with self.assertRaises(ValueError):
            tier_coverage(normalized, TIERS)

    def test_empty_coverage_rejected(self):
        with self.assertRaises(ValueError):
            chain_reach({})


class AssessmentTests(unittest.TestCase):
    def test_clean_chain_is_accepted(self):
        result = assess_selection_rule_flow_down(spec())
        self.assertEqual(result["verdict"], "accept")
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["chain_reach"], 1.0, places=9)

    def test_reach_landing_exactly_on_the_requirement_is_not_a_shortfall(self):
        result = assess_selection_rule_flow_down(
            spec(matrix=matrix(derating_rules_applied={2: "not-applied"}), required_coverage=0.75)
        )
        self.assertAlmostEqual(result["chain_reach"], 0.75, places=9)
        self.assertAlmostEqual(
            result["chain_reach"], result["required_coverage"], places=9
        )
        self.assertTrue(result["meets_required_coverage"])
        self.assertEqual(result["verdict"], "hold")

    def test_a_rule_never_in_force_is_reported_as_that_and_not_as_a_break(self):
        result = assess_selection_rule_flow_down(
            spec(
                matrix=matrix(
                    customer_deviation_requested={
                        0: "not-applied",
                        1: "not-applied",
                        2: "not-applied",
                    }
                )
            )
        )
        kinds = set(entry["finding"] for entry in result["findings"])
        self.assertIn("rule-not-in-force", kinds)
        self.assertNotIn("flow-down-break", kinds)
        self.assertEqual(result["rules_not_in_force"], ("customer-deviation-requested",))

    def test_a_rule_lost_downstream_is_a_flow_down_break(self):
        result = assess_selection_rule_flow_down(
            spec(matrix=matrix(derating_rules_applied={1: "not-applied"}))
        )
        finding = result["findings"][0]
        self.assertEqual(finding["finding"], "flow-down-break")
        self.assertEqual(finding["rule"], "derating-rules-applied")
        self.assertEqual(finding["tier"], 1)

    def test_an_unapproved_waiver_raises_both_its_own_finding_and_the_break(self):
        result = assess_selection_rule_flow_down(
            spec(matrix=matrix(lot_traceability_maintained={2: {"state": "waived"}}))
        )
        kinds = set(entry["finding"] for entry in result["findings"])
        self.assertIn("waiver-not-approved", kinds)
        self.assertIn("flow-down-break", kinds)

    def test_an_accepted_equivalent_rule_raises_nothing(self):
        result = assess_selection_rule_flow_down(
            spec(matrix=matrix(derating_rules_applied={1: dict(ACCEPTED_EQUIVALENT)}))
        )
        self.assertEqual(result["verdict"], "accept")

    def test_findings_are_ranked_worst_first(self):
        result = assess_selection_rule_flow_down(
            spec(
                matrix=matrix(
                    customer_deviation_requested={0: "not-applied"},
                    derating_rules_applied={1: "not-applied"},
                )
            )
        )
        self.assertEqual(result["findings"][0]["finding"], "rule-not-in-force")

    def test_governing_rule_survives_fewest_tiers(self):
        result = assess_selection_rule_flow_down(
            spec(
                matrix=matrix(
                    derating_rules_applied={1: "not-applied", 2: "not-applied"},
                    lot_traceability_maintained={2: "not-applied"},
                )
            )
        )
        self.assertEqual(result["governing_rule"], "derating-rules-applied")

    def test_survival_depths_are_reported_per_rule(self):
        result = assess_selection_rule_flow_down(
            spec(matrix=matrix(derating_rules_applied={2: "not-applied"}))
        )
        self.assertEqual(result["rule_survival_depth"]["derating-rules-applied"], 1)
        self.assertEqual(result["rule_survival_depth"]["part-approval-before-order"], 2)

    def test_missing_matrix_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_selection_rule_flow_down({"tiers": dict(TIERS), "rules": list(RULES)})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_selection_rule_flow_down(["tiers"])

    def test_out_of_range_required_coverage_rejected(self):
        with self.assertRaises(ValueError):
            assess_selection_rule_flow_down(spec(required_coverage=1.2))

    def test_boolean_required_coverage_rejected(self):
        with self.assertRaises(ValueError):
            assess_selection_rule_flow_down(spec(required_coverage=True))

    def test_tolerance_is_declared_and_small(self):
        self.assertGreater(COVERAGE_TOLERANCE, 0.0)
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
