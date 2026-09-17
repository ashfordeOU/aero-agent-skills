"""Contract tests for the clause 5.2.1 Class 2 selection general requirements logic."""

import unittest

from q60_class_2_selection_general_requirements_logic import (
    BLOCKING_PREREQUISITES,
    DECLARATION_STATES,
    INDEX_TOLERANCE,
    PREREQUISITE_WEIGHTS,
    READINESS_THRESHOLD,
    TAILORING_CREDIT,
    assess_class_2_selection_readiness,
    next_prerequisite_to_close,
    normalize_declarations,
    open_blocking_prerequisites,
    prerequisite_credit,
    readiness_index,
    validate_state,
    validate_weight_table,
)

TAILORING = {
    "state": "tailored",
    "rationale": "catalogue part already qualified on the previous build",
    "approval_reference": "PA-TLR-114",
}
INAPPLICABLE = {
    "state": "not-applicable",
    "justification": "part is already held in the bonded store",
}


def declarations(**overrides):
    """Return a fully satisfied Class 2 prerequisite register, with overrides."""
    base = {name: "satisfied" for name in PREREQUISITE_WEIGHTS}
    base.update(overrides)
    return base


class WeightTableTests(unittest.TestCase):
    def test_house_table_validates(self):
        table = validate_weight_table(PREREQUISITE_WEIGHTS)
        self.assertAlmostEqual(sum(table.values()), 20.0, places=9)

    def test_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_weight_table({})

    def test_zero_weight_rejected(self):
        with self.assertRaises(ValueError):
            validate_weight_table(dict(PREREQUISITE_WEIGHTS, **{"derating-rules-agreed": 0}))

    def test_negative_weight_rejected(self):
        with self.assertRaises(ValueError):
            validate_weight_table(
                dict(PREREQUISITE_WEIGHTS, **{"derating-rules-agreed": -2})
            )

    def test_boolean_weight_rejected(self):
        with self.assertRaises(ValueError):
            validate_weight_table(
                dict(PREREQUISITE_WEIGHTS, **{"derating-rules-agreed": True})
            )

    def test_table_omitting_a_blocking_prerequisite_rejected(self):
        trimmed = dict(PREREQUISITE_WEIGHTS)
        del trimmed["component-control-plan-approved"]
        with self.assertRaises(ValueError):
            validate_weight_table(trimmed)

    def test_non_mapping_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_weight_table(["mission-environment-defined"])


class StateTests(unittest.TestCase):
    def test_states_validate_and_ignore_case(self):
        for state in DECLARATION_STATES:
            self.assertEqual(validate_state(state.upper()), state)

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_state("probably-fine")

    def test_blank_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_state("   ")

    def test_satisfied_counts_in_full(self):
        self.assertAlmostEqual(prerequisite_credit("satisfied"), 1.0, places=9)

    def test_open_counts_for_nothing(self):
        self.assertAlmostEqual(prerequisite_credit("open"), 0.0, places=9)

    def test_tailored_counts_partially(self):
        self.assertAlmostEqual(prerequisite_credit("tailored"), TAILORING_CREDIT, places=9)
        self.assertGreater(TAILORING_CREDIT, 0.0)
        self.assertLess(TAILORING_CREDIT, 1.0)

    def test_inapplicable_leaves_the_count_entirely(self):
        self.assertIsNone(prerequisite_credit("not-applicable"))


class DeclarationTests(unittest.TestCase):
    def test_full_register_normalizes(self):
        normalized = normalize_declarations(declarations())
        self.assertEqual(set(normalized), set(PREREQUISITE_WEIGHTS))

    def test_undeclared_prerequisite_is_rejected_not_assumed(self):
        partial = declarations()
        del partial["procurement-source-identified"]
        with self.assertRaises(ValueError):
            normalize_declarations(partial)

    def test_unknown_prerequisite_rejected(self):
        with self.assertRaises(ValueError):
            normalize_declarations(declarations(**{"vendor-lunch-booked": "satisfied"}))

    def test_tailoring_without_a_rationale_rejected(self):
        broken = dict(TAILORING)
        del broken["rationale"]
        with self.assertRaises(ValueError):
            normalize_declarations(declarations(**{"derating-rules-agreed": broken}))

    def test_tailoring_without_an_approval_reference_rejected(self):
        broken = dict(TAILORING, approval_reference="  ")
        with self.assertRaises(ValueError):
            normalize_declarations(declarations(**{"derating-rules-agreed": broken}))

    def test_a_blocking_prerequisite_cannot_be_tailored(self):
        with self.assertRaises(ValueError):
            normalize_declarations(
                declarations(**{"component-control-plan-approved": dict(TAILORING)})
            )

    def test_a_blocking_prerequisite_cannot_be_declared_inapplicable(self):
        with self.assertRaises(ValueError):
            normalize_declarations(
                declarations(**{"mission-environment-defined": dict(INAPPLICABLE)})
            )

    def test_inapplicable_without_a_justification_rejected(self):
        with self.assertRaises(ValueError):
            normalize_declarations(
                declarations(**{"obsolescence-and-lead-time-assessed": {"state": "not-applicable"}})
            )

    def test_mapping_without_a_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_declarations(
                declarations(**{"derating-rules-agreed": {"rationale": "because"}})
            )

    def test_non_mapping_declaration_rejected(self):
        with self.assertRaises(ValueError):
            normalize_declarations(declarations(**{"derating-rules-agreed": 3}))

    def test_empty_register_rejected(self):
        with self.assertRaises(ValueError):
            normalize_declarations({})


class ReadinessIndexTests(unittest.TestCase):
    def test_fully_satisfied_register_reads_one(self):
        index, in_force, credited = readiness_index(normalize_declarations(declarations()))
        self.assertAlmostEqual(index, 1.0, places=9)
        self.assertAlmostEqual(in_force, 20.0, places=9)
        self.assertAlmostEqual(credited, 20.0, places=9)

    def test_open_items_are_weighted_not_counted(self):
        normalized = normalize_declarations(
            declarations(
                **{
                    "quality-level-target-agreed": "open",
                    "radiation-environment-assessed": "open",
                }
            )
        )
        index, _, _ = readiness_index(normalized)
        self.assertAlmostEqual(index, 0.8, places=9)

    def test_one_heavy_open_item_is_not_two_light_ones(self):
        heavy = readiness_index(
            normalize_declarations(declarations(**{"declared-components-list-entry": "open"}))
        )[0]
        light = readiness_index(
            normalize_declarations(
                declarations(
                    **{
                        "obsolescence-and-lead-time-assessed": "open",
                        "procurement-source-identified": "open",
                    }
                )
            )
        )[0]
        self.assertLess(heavy, light)

    def test_tailoring_lands_between_satisfied_and_open(self):
        tailored = readiness_index(
            normalize_declarations(declarations(**{"derating-rules-agreed": dict(TAILORING)}))
        )[0]
        opened = readiness_index(
            normalize_declarations(declarations(**{"derating-rules-agreed": "open"}))
        )[0]
        self.assertLess(tailored, 1.0)
        self.assertGreater(tailored, opened)
        self.assertAlmostEqual(tailored, 19.0 / 20.0, places=9)

    def test_an_inapplicable_item_is_neutral_rather_than_free_credit(self):
        normalized = normalize_declarations(
            declarations(**{"obsolescence-and-lead-time-assessed": dict(INAPPLICABLE)})
        )
        index, in_force, _ = readiness_index(normalized)
        self.assertAlmostEqual(in_force, 19.0, places=9)
        self.assertAlmostEqual(index, 1.0, places=9)

    def test_inapplicability_cannot_lift_an_index_that_has_an_open_item(self):
        with_na = readiness_index(
            normalize_declarations(
                declarations(
                    **{
                        "obsolescence-and-lead-time-assessed": dict(INAPPLICABLE),
                        "derating-rules-agreed": "open",
                    }
                )
            )
        )[0]
        without_na = readiness_index(
            normalize_declarations(declarations(**{"derating-rules-agreed": "open"}))
        )[0]
        self.assertLess(with_na, without_na)

    def test_non_mapping_normalized_rejected(self):
        with self.assertRaises(ValueError):
            readiness_index(["mission-environment-defined"])


class BlockingTests(unittest.TestCase):
    def test_blocking_set_is_narrower_than_the_register(self):
        self.assertTrue(BLOCKING_PREREQUISITES.issubset(set(PREREQUISITE_WEIGHTS)))
        self.assertLess(len(BLOCKING_PREREQUISITES), len(PREREQUISITE_WEIGHTS))

    def test_open_blocking_items_are_named(self):
        normalized = normalize_declarations(
            declarations(**{"component-requirements-specified": "open"})
        )
        self.assertEqual(
            open_blocking_prerequisites(normalized), ("component-requirements-specified",)
        )

    def test_clean_register_has_no_open_blocker(self):
        self.assertEqual(
            open_blocking_prerequisites(normalize_declarations(declarations())), ()
        )

    def test_next_to_close_takes_a_blocker_before_a_heavier_open_item(self):
        normalized = normalize_declarations(
            declarations(
                **{
                    "component-control-plan-approved": "open",
                    "declared-components-list-entry": "open",
                }
            )
        )
        self.assertEqual(
            next_prerequisite_to_close(normalized), "component-control-plan-approved"
        )

    def test_next_to_close_takes_the_heaviest_when_nothing_blocks(self):
        normalized = normalize_declarations(
            declarations(
                **{
                    "declared-components-list-entry": "open",
                    "procurement-source-identified": "open",
                }
            )
        )
        self.assertEqual(
            next_prerequisite_to_close(normalized), "declared-components-list-entry"
        )

    def test_nothing_open_means_nothing_to_close(self):
        self.assertIsNone(next_prerequisite_to_close(normalize_declarations(declarations())))


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        base = {"candidate_part": "RH1499", "declarations": declarations()}
        base.update(overrides)
        return base

    def test_clean_register_authorizes(self):
        result = assess_class_2_selection_readiness(self._spec())
        self.assertEqual(result["verdict"], "authorize")
        self.assertTrue(result["authorized"])
        self.assertEqual(result["candidate_part"], "RH1499")

    def test_tailoring_is_named_in_the_verdict(self):
        result = assess_class_2_selection_readiness(
            self._spec(declarations=declarations(**{"derating-rules-agreed": dict(TAILORING)}))
        )
        self.assertEqual(result["verdict"], "authorize-with-tailoring")
        self.assertEqual(result["tailored_prerequisites"], ("derating-rules-agreed",))

    def test_index_landing_exactly_on_the_threshold_authorizes(self):
        result = assess_class_2_selection_readiness(
            self._spec(
                declarations=declarations(
                    **{
                        "quality-level-target-agreed": "open",
                        "radiation-environment-assessed": "open",
                    }
                )
            )
        )
        self.assertAlmostEqual(result["readiness_index"], READINESS_THRESHOLD, places=9)
        self.assertTrue(result["meets_threshold"])
        self.assertEqual(result["verdict"], "authorize")

    def test_a_high_index_does_not_carry_an_open_blocker(self):
        result = assess_class_2_selection_readiness(
            self._spec(declarations=declarations(**{"mission-environment-defined": "open"}))
        )
        self.assertGreater(result["readiness_index"], 0.8)
        self.assertEqual(result["verdict"], "blocked")
        self.assertFalse(result["authorized"])

    def test_index_below_the_threshold_holds(self):
        result = assess_class_2_selection_readiness(
            self._spec(
                declarations=declarations(
                    **{
                        "declared-components-list-entry": "open",
                        "derating-rules-agreed": "open",
                    }
                )
            )
        )
        self.assertEqual(result["verdict"], "hold")

    def test_next_to_close_is_reported_with_the_verdict(self):
        result = assess_class_2_selection_readiness(
            self._spec(declarations=declarations(**{"component-control-plan-approved": "open"}))
        )
        self.assertEqual(result["next_to_close"], "component-control-plan-approved")

    def test_missing_declarations_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_selection_readiness({"candidate_part": "RH1499"})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_selection_readiness(["declarations"])

    def test_out_of_range_threshold_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_selection_readiness(self._spec(readiness_threshold=1.4))

    def test_boolean_threshold_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_selection_readiness(self._spec(readiness_threshold=True))

    def test_blank_candidate_part_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_selection_readiness(self._spec(candidate_part="   "))

    def test_tolerance_is_declared_and_small(self):
        self.assertGreater(INDEX_TOLERANCE, 0.0)
        self.assertLess(INDEX_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
