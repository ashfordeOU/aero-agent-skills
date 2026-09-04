"""Contract test for order_requirements_review_logic (stdlib unittest).

Offline and deterministic. Covers the three worked cases from the wave-33
spec, per-element and per-class detection, independent blocker firing,
verdict precedence, empty and invalid inputs, summary keys, determinism.

Run: python3 test_order_requirements_review.py
"""

import unittest

import order_requirements_review_logic as m

E = m.REQUIRED_ORDER_ELEMENTS
S = m.SPECIAL_REQUIREMENT_CLASSES

ALL_ELEMENTS = set(E)
CLEAN_GATES = (True, True, True, 25, 25)  # all qualified, delivery at frozen


class OrderRequirementsReviewContractTest(unittest.TestCase):

    # --- Worked cases from the spec ------------------------------------

    def test_order_a_verdict_reject_review(self):
        # Missing acceptance-criteria, unrecognized exotic-clause,
        # unqualified special process, delivery 30 days > frozen 25 days.
        elements = ALL_ELEMENTS - {"acceptance-criteria"}
        specials = {"fai", "key-characteristic-control", "serialization",
                    "exotic-clause"}
        summary = m.order_review_summary(elements, specials, False, True,
                                         True, 30, 25, True)
        self.assertEqual(summary["verdict"], "reject-review")
        self.assertFalse(summary["complete"])
        self.assertEqual(summary["missing"], ["acceptance-criteria"])
        self.assertEqual(summary["recognized_specials"],
                         ["fai", "key-characteristic-control", "serialization"])
        self.assertEqual(summary["unrecognized_specials"], ["exotic-clause"])
        self.assertEqual(summary["blockers"],
                         ["unqualified-special-process",
                          "delivery-exceeds-frozen-lead-time"])

    def test_order_a_blockers_fire_from_gates(self):
        blockers = m.feasibility_blockers(False, True, True, 30, 25)
        self.assertEqual(blockers,
                         ["unqualified-special-process",
                          "delivery-exceeds-frozen-lead-time"])

    def test_order_b_verdict_accept_with_fai_condition(self):
        # Complete 8/8, 6/6 recognized specials, all gates OK, FAI pending.
        specials = {"fai", "delta-fai-notification",
                    "key-characteristic-control", "special-process-approval",
                    "source-verification", "serialization"}
        summary = m.order_review_summary(ALL_ELEMENTS, specials, True, True,
                                         True, 40, 45, True)
        self.assertEqual(summary["verdict"], "accept-with-fai-condition")
        self.assertTrue(summary["complete"])
        self.assertEqual(summary["missing"], [])
        self.assertEqual(len(summary["recognized_specials"]), 6)
        self.assertEqual(summary["unrecognized_specials"], [])
        self.assertEqual(summary["blockers"], [])
        self.assertTrue(summary["fai_pending"])

    def test_order_c_verdict_accept(self):
        # Clean, complete, recognized specials only, no FAI pending.
        specials = {"certificate-of-conformance", "serialization"}
        summary = m.order_review_summary(ALL_ELEMENTS, specials, True, True,
                                         True, 20, 25, False)
        self.assertEqual(summary["verdict"], "accept")
        self.assertTrue(summary["complete"])
        self.assertEqual(summary["blockers"], [])
        self.assertFalse(summary["fai_pending"])

    # --- Each of the 8 canonical elements detected when missing ---------

    def test_missing_element_product_identification_detected(self):
        complete, missing = m.requirements_completeness(
            ALL_ELEMENTS - {"product-identification"})
        self.assertFalse(complete)
        self.assertEqual(missing, ["product-identification"])

    def test_missing_element_spec_drawing_revision_detected(self):
        complete, missing = m.requirements_completeness(
            ALL_ELEMENTS - {"spec-drawing-revision"})
        self.assertFalse(complete)
        self.assertEqual(missing, ["spec-drawing-revision"])

    def test_missing_element_quantity_schedule_detected(self):
        complete, missing = m.requirements_completeness(
            ALL_ELEMENTS - {"quantity-schedule"})
        self.assertFalse(complete)
        self.assertEqual(missing, ["quantity-schedule"])

    def test_missing_element_delivery_date_detected(self):
        complete, missing = m.requirements_completeness(
            ALL_ELEMENTS - {"delivery-date"})
        self.assertFalse(complete)
        self.assertEqual(missing, ["delivery-date"])

    def test_missing_element_acceptance_criteria_detected(self):
        complete, missing = m.requirements_completeness(
            ALL_ELEMENTS - {"acceptance-criteria"})
        self.assertFalse(complete)
        self.assertEqual(missing, ["acceptance-criteria"])

    def test_missing_element_special_requirements_detected(self):
        complete, missing = m.requirements_completeness(
            ALL_ELEMENTS - {"special-requirements"})
        self.assertFalse(complete)
        self.assertEqual(missing, ["special-requirements"])

    def test_missing_element_preservation_packaging_detected(self):
        complete, missing = m.requirements_completeness(
            ALL_ELEMENTS - {"preservation-packaging"})
        self.assertFalse(complete)
        self.assertEqual(missing, ["preservation-packaging"])

    def test_missing_element_records_detected(self):
        complete, missing = m.requirements_completeness(
            ALL_ELEMENTS - {"records"})
        self.assertFalse(complete)
        self.assertEqual(missing, ["records"])

    # --- Each of the 8 aerospace special classes recognized -------------

    def test_recognizes_fai(self):
        recognized, unrecognized = m.classify_special_requirements({"fai"})
        self.assertEqual(recognized, ["fai"])
        self.assertEqual(unrecognized, [])

    def test_recognizes_delta_fai_notification(self):
        recognized, _ = m.classify_special_requirements(
            {"delta-fai-notification"})
        self.assertEqual(recognized, ["delta-fai-notification"])

    def test_recognizes_key_characteristic_control(self):
        recognized, _ = m.classify_special_requirements(
            {"key-characteristic-control"})
        self.assertEqual(recognized, ["key-characteristic-control"])

    def test_recognizes_counterfeit_free_evidence(self):
        recognized, _ = m.classify_special_requirements(
            {"counterfeit-free-evidence"})
        self.assertEqual(recognized, ["counterfeit-free-evidence"])

    def test_recognizes_special_process_approval(self):
        recognized, _ = m.classify_special_requirements(
            {"special-process-approval"})
        self.assertEqual(recognized, ["special-process-approval"])

    def test_recognizes_source_verification(self):
        recognized, _ = m.classify_special_requirements(
            {"source-verification"})
        self.assertEqual(recognized, ["source-verification"])

    def test_recognizes_certificate_of_conformance(self):
        recognized, _ = m.classify_special_requirements(
            {"certificate-of-conformance"})
        self.assertEqual(recognized, ["certificate-of-conformance"])

    def test_recognizes_serialization(self):
        recognized, _ = m.classify_special_requirements({"serialization"})
        self.assertEqual(recognized, ["serialization"])

    # --- Feasibility blockers fire independently ------------------------

    def test_blocker_unqualified_special_process_fires(self):
        blockers = m.feasibility_blockers(False, True, True, 25, 25)
        self.assertEqual(blockers, ["unqualified-special-process"])

    def test_blocker_unapproved_material_fires(self):
        blockers = m.feasibility_blockers(True, False, True, 25, 25)
        self.assertEqual(blockers, ["unapproved-material"])

    def test_blocker_no_ndt_capability_fires(self):
        blockers = m.feasibility_blockers(True, True, False, 25, 25)
        self.assertEqual(blockers, ["no-ndt-capability"])

    def test_blocker_delivery_exceeds_frozen_lead_time_fires(self):
        blockers = m.feasibility_blockers(True, True, True, 26, 25)
        self.assertEqual(blockers, ["delivery-exceeds-frozen-lead-time"])

    def test_no_blockers_when_all_gates_pass(self):
        # All qualified with delivery at and below the frozen lead time.
        self.assertEqual(m.feasibility_blockers(*CLEAN_GATES), [])
        self.assertEqual(m.feasibility_blockers(True, True, True, 24, 25), [])

    # --- Verdict precedence ----------------------------------------------

    def test_verdict_rejects_on_any_missing_unrecognized_or_blocker(self):
        # Each defect alone, with everything else passing, still rejects.
        self.assertEqual(
            m.order_acceptance_verdict(["records"], [], [], False),
            "reject-review")
        self.assertEqual(
            m.order_acceptance_verdict([], ["exotic-clause"], [], False),
            "reject-review")
        self.assertEqual(
            m.order_acceptance_verdict([], [], ["no-ndt-capability"], False),
            "reject-review")

    def test_verdict_accept_branching_on_fai_pending_only_when_clean(self):
        # Clean and no FAI pending accepts; clean with FAI pending carries
        # the FAI condition; FAI pending never overrides a defect.
        self.assertEqual(m.order_acceptance_verdict([], [], [], False),
                         "accept")
        self.assertEqual(m.order_acceptance_verdict([], [], [], True),
                         "accept-with-fai-condition")
        self.assertEqual(
            m.order_acceptance_verdict(["delivery-date"], [], [], True),
            "reject-review")
        self.assertEqual(
            m.order_acceptance_verdict([], [], ["unapproved-material"], True),
            "reject-review")

    # --- Empty and invalid inputs ----------------------------------------

    def test_empty_declarations_report_all_missing_and_no_specials(self):
        complete, missing = m.requirements_completeness([])
        self.assertFalse(complete)
        self.assertEqual(len(missing), 8)
        self.assertEqual(set(missing), set(ALL_ELEMENTS))
        recognized, unrecognized = m.classify_special_requirements([])
        self.assertEqual(recognized, [])
        self.assertEqual(unrecognized, [])

    def test_unknown_class_lands_in_unrecognized(self):
        recognized, unrecognized = m.classify_special_requirements(
            {"fai", "exotic-clause", "delta-fai-notification", "mystery"})
        self.assertEqual(recognized,
                         ["delta-fai-notification", "fai"])
        self.assertEqual(unrecognized, ["exotic-clause", "mystery"])

    def test_tokens_are_normalized_before_comparison(self):
        complete, missing = m.requirements_completeness(
            {"product-identification", "SPEC-DRAWING-REVISION",
             "Quantity-Schedule", "delivery-date", "acceptance-criteria",
             "special-requirements", "preservation-packaging", "records"})
        self.assertTrue(complete)
        self.assertEqual(missing, [])
        recognized, _ = m.classify_special_requirements({"FAI", " FAI "})
        self.assertEqual(recognized, ["fai"])

    def test_feasibility_non_physical_inputs_raise_value_error(self):
        # Negative days and wrong-typed gates and days are non-physical.
        with self.assertRaises(ValueError):
            m.feasibility_blockers(True, True, True, -1, 25)
        with self.assertRaises(ValueError):
            m.feasibility_blockers(True, True, True, 25, -5)
        with self.assertRaises(ValueError):
            m.feasibility_blockers("yes", True, True, 25, 25)
        with self.assertRaises(ValueError):
            m.feasibility_blockers(True, True, True, "30", 25)
        with self.assertRaises(ValueError):
            m.feasibility_blockers(True, True, True, True, 25)

    def test_empty_and_non_string_tokens_raise_value_error(self):
        with self.assertRaises(ValueError):
            m.requirements_completeness({""})
        with self.assertRaises(ValueError):
            m.requirements_completeness({"   "})
        with self.assertRaises(ValueError):
            m.classify_special_requirements({None})
        with self.assertRaises(ValueError):
            m.order_acceptance_verdict(None, [], [], False)
        with self.assertRaises(ValueError):
            m.order_acceptance_verdict([], [], [], "pending")

    # --- Summary dict and determinism -------------------------------------

    def test_summary_dict_has_exactly_documented_keys(self):
        summary = m.order_review_summary(ALL_ELEMENTS, {"fai"}, True, True,
                                         True, 20, 25, True)
        self.assertEqual(sorted(summary.keys()),
                         ["blockers", "complete", "fai_pending", "missing",
                          "recognized_specials", "unrecognized_specials",
                          "verdict"])
        self.assertEqual(len(summary), 7)

    def test_outputs_deterministic_run_to_run(self):
        elements = ALL_ELEMENTS - {"delivery-date"}
        specials = {"fai", "exotic-clause", "serialization"}
        first = m.order_review_summary(elements, specials, False, True, False,
                                       30, 25, True)
        second = m.order_review_summary(elements, specials, False, True,
                                        False, 30, 25, True)
        self.assertEqual(first, second)
        # Order of the declared input sets must not change the outputs.
        shuffled = m.order_review_summary(
            list(reversed(sorted(elements))),
            list(reversed(sorted(specials))),
            False, True, False, 30, 25, True)
        self.assertEqual(shuffled, first)


if __name__ == "__main__":
    unittest.main()
