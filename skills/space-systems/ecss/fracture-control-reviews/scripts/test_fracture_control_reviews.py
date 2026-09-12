"""
Offline deterministic tests for fracture_control_reviews_logic.
stdlib unittest only — no network, no external deps.
Run: python3 test_fracture_control_reviews.py
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from fracture_control_reviews_logic import (
    REVIEW_ORDER,
    FCI_MATURITY_LEVELS,
    REQUIRED_INPUTS,
    required_inputs,
    fci_maturity_required,
    check_fci_maturity,
    check_review_readiness,
    milestone_index,
    previous_milestone,
    next_milestone,
)


class TestRequiredInputs(unittest.TestCase):

    def test_srr_required_inputs_contains_plan_draft(self):
        inputs = required_inputs("SRR")
        self.assertIn("fracture_control_plan_draft", inputs)

    def test_srr_required_inputs_contains_fci_preliminary(self):
        inputs = required_inputs("SRR")
        self.assertIn("fci_list_preliminary", inputs)

    def test_cdr_required_inputs_contains_final_fci_list(self):
        inputs = required_inputs("CDR")
        self.assertIn("fci_list_final", inputs)

    def test_cdr_required_inputs_contains_previous_actions_closed(self):
        inputs = required_inputs("CDR")
        self.assertIn("previous_review_actions_closed", inputs)

    def test_ar_required_inputs_contains_summary_report(self):
        inputs = required_inputs("AR")
        self.assertIn("fracture_summary_report", inputs)

    def test_ar_required_inputs_contains_waivers_dispositioned(self):
        inputs = required_inputs("AR")
        self.assertIn("waivers_dispositioned", inputs)

    def test_unknown_milestone_raises_value_error(self):
        with self.assertRaises(ValueError):
            required_inputs("FRR")

    def test_empty_string_milestone_raises_value_error(self):
        with self.assertRaises(ValueError):
            required_inputs("")

    def test_required_inputs_returns_frozenset(self):
        result = required_inputs("PDR")
        self.assertIsInstance(result, frozenset)

    def test_pdr_required_inputs_contains_preliminary_analysis(self):
        inputs = required_inputs("PDR")
        self.assertIn("fracture_analysis_preliminary", inputs)


class TestFciMaturityRequired(unittest.TestCase):

    def test_srr_requires_preliminary(self):
        self.assertEqual(fci_maturity_required("SRR"), "preliminary")

    def test_pdr_requires_draft(self):
        self.assertEqual(fci_maturity_required("PDR"), "draft")

    def test_cdr_requires_final(self):
        self.assertEqual(fci_maturity_required("CDR"), "final")

    def test_qr_requires_verified(self):
        self.assertEqual(fci_maturity_required("QR"), "verified")

    def test_ar_requires_accepted(self):
        self.assertEqual(fci_maturity_required("AR"), "accepted")


class TestCheckFciMaturity(unittest.TestCase):

    def test_exact_match_meets_requirement(self):
        result = check_fci_maturity("CDR", "final")
        self.assertTrue(result["meets_requirement"])
        self.assertEqual(result["shortfall"], 0)

    def test_ahead_of_requirement_also_meets(self):
        result = check_fci_maturity("SRR", "draft")
        self.assertTrue(result["meets_requirement"])
        self.assertEqual(result["shortfall"], 0)

    def test_behind_requirement_does_not_meet(self):
        result = check_fci_maturity("CDR", "draft")
        self.assertFalse(result["meets_requirement"])
        self.assertGreater(result["shortfall"], 0)

    def test_shortfall_is_one_step_behind(self):
        result = check_fci_maturity("PDR", "preliminary")
        self.assertEqual(result["shortfall"], 1)

    def test_shortfall_is_two_steps_behind(self):
        result = check_fci_maturity("CDR", "preliminary")
        self.assertEqual(result["shortfall"], 2)

    def test_result_carries_required_and_current_maturity(self):
        result = check_fci_maturity("QR", "final")
        self.assertEqual(result["required_maturity"], "verified")
        self.assertEqual(result["current_maturity"], "final")

    def test_unknown_milestone_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_fci_maturity("PRR", "draft")

    def test_unknown_maturity_level_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_fci_maturity("CDR", "approved")


class TestCheckReviewReadiness(unittest.TestCase):

    def test_all_inputs_present_is_ready(self):
        all_inputs = set(REQUIRED_INPUTS["SRR"])
        result = check_review_readiness("SRR", all_inputs)
        self.assertTrue(result["ready"])
        self.assertEqual(result["missing"], frozenset())

    def test_empty_inputs_is_not_ready(self):
        result = check_review_readiness("SRR", set())
        self.assertFalse(result["ready"])
        self.assertEqual(result["missing"], REQUIRED_INPUTS["SRR"])

    def test_missing_one_item_is_not_ready(self):
        all_inputs = set(REQUIRED_INPUTS["PDR"])
        one_item = next(iter(all_inputs))
        all_inputs.remove(one_item)
        result = check_review_readiness("PDR", all_inputs)
        self.assertFalse(result["ready"])
        self.assertIn(one_item, result["missing"])

    def test_present_set_matches_available_and_required_intersection(self):
        partial = {"fracture_control_plan_approved", "fci_list_final"}
        result = check_review_readiness("CDR", partial)
        self.assertTrue(partial.issubset(result["present"]))

    def test_extra_inputs_not_in_required_do_not_affect_readiness(self):
        all_inputs = set(REQUIRED_INPUTS["AR"])
        all_inputs.add("supplementary_report_not_required")
        result = check_review_readiness("AR", all_inputs)
        self.assertTrue(result["ready"])

    def test_missing_action_closure_at_cdr_blocks_readiness(self):
        cdr_minus_actions = set(REQUIRED_INPUTS["CDR"]) - {"previous_review_actions_closed"}
        result = check_review_readiness("CDR", cdr_minus_actions)
        self.assertFalse(result["ready"])
        self.assertIn("previous_review_actions_closed", result["missing"])

    def test_unknown_milestone_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_review_readiness("MRR", set())

    def test_qr_all_inputs_present_is_ready(self):
        result = check_review_readiness("QR", set(REQUIRED_INPUTS["QR"]))
        self.assertTrue(result["ready"])


class TestMilestoneNavigation(unittest.TestCase):

    def test_milestone_order_is_sequential(self):
        for i, ms in enumerate(REVIEW_ORDER):
            self.assertEqual(milestone_index(ms), i)

    def test_srr_has_no_previous(self):
        self.assertIsNone(previous_milestone("SRR"))

    def test_cdr_previous_is_pdr(self):
        self.assertEqual(previous_milestone("CDR"), "PDR")

    def test_ar_previous_is_qr(self):
        self.assertEqual(previous_milestone("AR"), "QR")

    def test_ar_has_no_next(self):
        self.assertIsNone(next_milestone("AR"))

    def test_srr_next_is_pdr(self):
        self.assertEqual(next_milestone("SRR"), "PDR")

    def test_unknown_milestone_index_raises(self):
        with self.assertRaises(ValueError):
            milestone_index("TRR")

    def test_fci_maturity_levels_five_steps(self):
        self.assertEqual(len(FCI_MATURITY_LEVELS), 5)

    def test_review_order_has_five_milestones(self):
        self.assertEqual(len(REVIEW_ORDER), 5)


if __name__ == "__main__":
    unittest.main()
