"""Contract tests for the clause 10.2.2 screening flow variant logic."""

import unittest

from q6012_wafer_screening_flow_variants_logic import (
    ACCEPTANCE_MEASUREMENT,
    DRIFT_ASSESSMENT,
    EQUIVALENT,
    INCOMPLETE,
    INITIAL_INSPECTION,
    LOT_ACCEPTANCE_DECISION,
    POST_STRESS_MEASUREMENT,
    PRE_STRESS_MEASUREMENT,
    REORDER_REQUIRED,
    SUPPLIER_DATA_REVIEW,
    WAFER_LEVEL_STRESS,
    added_stages,
    applicable_constraints,
    assess_flow,
    drift_pairs_available,
    inverted_pairs,
    missing_stages,
    reference_sequence,
    select_situation,
    stage_coverage_fraction,
    validate_sequence,
    validate_situation,
)

FULL = "unscreened-wafer-procurement"
SUPPLIER_WAFER = "supplier-screened-wafer-procurement"
DIE = "screened-die-procurement"
RECURRENT = "recurrent-lot-approved-process"


class ValidationTests(unittest.TestCase):
    def test_known_situation_accepted(self):
        self.assertEqual(validate_situation("  %s " % FULL), FULL)

    def test_unknown_situation_rejected(self):
        with self.assertRaises(ValueError):
            validate_situation("bulk-tray-procurement")

    def test_non_string_situation_rejected(self):
        with self.assertRaises(ValueError):
            validate_situation(3)

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence([WAFER_LEVEL_STRESS, "burn-in-at-board-level"])

    def test_repeated_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence([WAFER_LEVEL_STRESS, WAFER_LEVEL_STRESS])

    def test_blank_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence([" "])

    def test_empty_flow_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence([])

    def test_bare_string_is_not_a_sequence(self):
        with self.assertRaises(ValueError):
            validate_sequence(WAFER_LEVEL_STRESS)


class SituationSelectionTests(unittest.TestCase):
    def test_unscreened_wafer_selects_the_full_flow(self):
        self.assertEqual(
            select_situation(
                {
                    "delivery_form": "wafer",
                    "supplier_screened": False,
                    "process_previously_approved": False,
                }
            ),
            FULL,
        )

    def test_supplier_screened_wafer_selects_the_review_flow(self):
        self.assertEqual(
            select_situation(
                {
                    "delivery_form": "wafer",
                    "supplier_screened": True,
                    "process_previously_approved": False,
                }
            ),
            SUPPLIER_WAFER,
        )

    def test_approved_process_selects_the_reduced_flow(self):
        self.assertEqual(
            select_situation(
                {
                    "delivery_form": "wafer",
                    "supplier_screened": False,
                    "process_previously_approved": True,
                }
            ),
            RECURRENT,
        )

    def test_screened_die_selects_the_die_flow(self):
        self.assertEqual(
            select_situation(
                {
                    "delivery_form": "die",
                    "supplier_screened": True,
                    "process_previously_approved": True,
                }
            ),
            DIE,
        )

    def test_unscreened_die_has_no_variant(self):
        with self.assertRaises(ValueError):
            select_situation(
                {
                    "delivery_form": "die",
                    "supplier_screened": False,
                    "process_previously_approved": True,
                }
            )

    def test_unknown_delivery_form_rejected(self):
        with self.assertRaises(ValueError):
            select_situation(
                {
                    "delivery_form": "module",
                    "supplier_screened": True,
                    "process_previously_approved": True,
                }
            )

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            select_situation(
                {
                    "delivery_form": "wafer",
                    "supplier_screened": "yes",
                    "process_previously_approved": True,
                }
            )


class ConstraintTests(unittest.TestCase):
    def test_constraints_narrow_to_the_stages_present(self):
        pairs = applicable_constraints([SUPPLIER_DATA_REVIEW, ACCEPTANCE_MEASUREMENT])
        self.assertEqual(pairs, ((SUPPLIER_DATA_REVIEW, ACCEPTANCE_MEASUREMENT),))

    def test_reference_flow_inverts_nothing(self):
        for situation in (FULL, SUPPLIER_WAFER, DIE, RECURRENT):
            self.assertEqual(inverted_pairs(reference_sequence(situation)), ())

    def test_measurement_after_the_stress_pair_is_inverted(self):
        flow = [
            INITIAL_INSPECTION,
            WAFER_LEVEL_STRESS,
            PRE_STRESS_MEASUREMENT,
            POST_STRESS_MEASUREMENT,
            DRIFT_ASSESSMENT,
            ACCEPTANCE_MEASUREMENT,
            LOT_ACCEPTANCE_DECISION,
        ]
        self.assertIn((PRE_STRESS_MEASUREMENT, WAFER_LEVEL_STRESS), inverted_pairs(flow))

    def test_decision_taken_first_inverts_every_closing_pair(self):
        flow = [LOT_ACCEPTANCE_DECISION, SUPPLIER_DATA_REVIEW, ACCEPTANCE_MEASUREMENT]
        self.assertIn((ACCEPTANCE_MEASUREMENT, LOT_ACCEPTANCE_DECISION), inverted_pairs(flow))

    def test_drift_pair_exists_when_the_stress_is_straddled(self):
        self.assertEqual(drift_pairs_available(reference_sequence(FULL)), 1)

    def test_no_drift_pair_without_a_pre_stress_measurement(self):
        self.assertEqual(drift_pairs_available(reference_sequence(RECURRENT)), 0)

    def test_no_drift_pair_when_both_measurements_follow_the_stress(self):
        flow = [WAFER_LEVEL_STRESS, PRE_STRESS_MEASUREMENT, POST_STRESS_MEASUREMENT]
        self.assertEqual(drift_pairs_available(flow), 0)


class StageSetTests(unittest.TestCase):
    def test_reference_flow_misses_nothing(self):
        self.assertEqual(missing_stages(FULL, reference_sequence(FULL)), ())

    def test_omitted_stage_reported_in_reference_order(self):
        flow = [s for s in reference_sequence(FULL) if s != DRIFT_ASSESSMENT]
        self.assertEqual(missing_stages(FULL, flow), (DRIFT_ASSESSMENT,))

    def test_stage_beyond_the_variant_is_an_addition(self):
        flow = list(reference_sequence(DIE)) + [INITIAL_INSPECTION]
        self.assertEqual(added_stages(DIE, flow), (INITIAL_INSPECTION,))

    def test_full_coverage_fraction(self):
        self.assertAlmostEqual(
            stage_coverage_fraction(DIE, reference_sequence(DIE)), 1.0, places=9
        )

    def test_partial_coverage_fraction(self):
        flow = [SUPPLIER_DATA_REVIEW, ACCEPTANCE_MEASUREMENT]
        self.assertAlmostEqual(stage_coverage_fraction(DIE, flow), 2.0 / 3.0, places=9)


class AssessTests(unittest.TestCase):
    def test_reference_flow_is_equivalent(self):
        result = assess_flow(FULL, reference_sequence(FULL))
        self.assertEqual(result["verdict"], EQUIVALENT)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], ())

    def test_free_stages_may_be_swapped(self):
        flow = [
            PRE_STRESS_MEASUREMENT,
            INITIAL_INSPECTION,
            WAFER_LEVEL_STRESS,
            POST_STRESS_MEASUREMENT,
            DRIFT_ASSESSMENT,
            ACCEPTANCE_MEASUREMENT,
            LOT_ACCEPTANCE_DECISION,
        ]
        self.assertEqual(assess_flow(FULL, flow)["verdict"], EQUIVALENT)

    def test_inverted_evidence_pair_demands_a_reorder(self):
        flow = [
            INITIAL_INSPECTION,
            WAFER_LEVEL_STRESS,
            PRE_STRESS_MEASUREMENT,
            POST_STRESS_MEASUREMENT,
            DRIFT_ASSESSMENT,
            ACCEPTANCE_MEASUREMENT,
            LOT_ACCEPTANCE_DECISION,
        ]
        result = assess_flow(FULL, flow)
        self.assertEqual(result["verdict"], REORDER_REQUIRED)
        self.assertFalse(result["acceptable"])

    def test_missing_stage_outranks_an_inversion(self):
        flow = [WAFER_LEVEL_STRESS, PRE_STRESS_MEASUREMENT, POST_STRESS_MEASUREMENT]
        self.assertEqual(assess_flow(FULL, flow)["verdict"], INCOMPLETE)

    def test_addition_does_not_disqualify_the_variant(self):
        flow = [SUPPLIER_DATA_REVIEW, INITIAL_INSPECTION, ACCEPTANCE_MEASUREMENT, LOT_ACCEPTANCE_DECISION]
        result = assess_flow(DIE, flow)
        self.assertEqual(result["verdict"], EQUIVALENT)
        self.assertEqual(result["added_stages"], (INITIAL_INSPECTION,))

    def test_addition_is_still_reported(self):
        flow = [SUPPLIER_DATA_REVIEW, INITIAL_INSPECTION, ACCEPTANCE_MEASUREMENT, LOT_ACCEPTANCE_DECISION]
        self.assertTrue(any("beyond the" in f for f in assess_flow(DIE, flow)["findings"]))

    def test_omission_is_named_in_the_findings(self):
        flow = [s for s in reference_sequence(FULL) if s != ACCEPTANCE_MEASUREMENT]
        self.assertTrue(
            any(ACCEPTANCE_MEASUREMENT in f for f in assess_flow(FULL, flow)["findings"])
        )

    def test_die_flow_carries_no_drift_pair(self):
        self.assertEqual(assess_flow(DIE, reference_sequence(DIE))["drift_pairs_available"], 0)

    def test_result_carries_both_sequences(self):
        result = assess_flow(RECURRENT, reference_sequence(RECURRENT))
        self.assertEqual(result["reference_sequence"], result["proposed_sequence"])

    def test_selected_situation_grades_its_own_reference_flow(self):
        situation = select_situation(
            {
                "delivery_form": "wafer",
                "supplier_screened": False,
                "process_previously_approved": False,
            }
        )
        self.assertTrue(assess_flow(situation, reference_sequence(situation))["acceptable"])

    def test_unknown_situation_rejected_by_assess(self):
        with self.assertRaises(ValueError):
            assess_flow("tray-procurement", reference_sequence(DIE))


if __name__ == "__main__":
    unittest.main()
