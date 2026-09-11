"""
test_e1012_phase_margins.py

Offline deterministic unit tests for e1012_phase_margins_logic
(ECSS-E-ST-10-12C §5.6 phase margins).
Run: python3 test_e1012_phase_margins.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_phase_margins_logic import (
    MINIMUM_RDM,
    VALID_TEST_METHODS,
    PhaseGateResult,
    ProjectPhase,
    RadiationType,
    RdmResult,
    TestMethod,
    TestMethodResult,
    categorize_component_margin,
    check_rdm_compliance,
    compute_rdm,
    run_phase_gate,
    validate_test_method,
)


class TestEnums(unittest.TestCase):

    def test_project_phases(self):
        self.assertEqual(
            {p.value for p in ProjectPhase}, {"pre_pdr", "pdr_cdr", "post_cdr"}
        )

    def test_radiation_types(self):
        self.assertEqual(
            {r.value for r in RadiationType},
            {"tid", "dd", "see_heavy_ion", "see_proton"},
        )

    def test_test_method_values(self):
        self.assertEqual(TestMethod.COBALT_60.value, "cobalt_60")
        self.assertEqual(TestMethod.SIMILARITY.value, "similarity")
        self.assertEqual(TestMethod.ANALYSIS_ONLY.value, "analysis_only")


class TestConstants(unittest.TestCase):

    def test_minimum_rdm_is_two_for_tid_and_dd_at_every_phase(self):
        for rtype in (RadiationType.TID, RadiationType.DD):
            for phase in ProjectPhase:
                self.assertEqual(MINIMUM_RDM[rtype][phase], 2.0)

    def test_see_types_absent_from_numeric_rdm_table(self):
        self.assertNotIn(RadiationType.SEE_HEAVY_ION, MINIMUM_RDM)
        self.assertNotIn(RadiationType.SEE_PROTON, MINIMUM_RDM)

    def test_tid_methods(self):
        self.assertEqual(
            VALID_TEST_METHODS[RadiationType.TID],
            {TestMethod.COBALT_60, TestMethod.XRAY, TestMethod.ELDRS},
        )

    def test_dd_methods(self):
        self.assertEqual(
            VALID_TEST_METHODS[RadiationType.DD],
            {TestMethod.PROTON, TestMethod.NEUTRON},
        )

    def test_see_methods(self):
        self.assertEqual(
            VALID_TEST_METHODS[RadiationType.SEE_HEAVY_ION], {TestMethod.HEAVY_ION}
        )
        self.assertEqual(
            VALID_TEST_METHODS[RadiationType.SEE_PROTON], {TestMethod.PROTON}
        )


class TestComputeRdm(unittest.TestCase):

    def test_two_to_one_gives_two(self):
        self.assertAlmostEqual(compute_rdm(20.0, 10.0), 2.0)

    def test_margin_below_two(self):
        self.assertAlmostEqual(compute_rdm(15.0, 10.0), 1.5)

    def test_order_of_magnitude_case(self):
        self.assertAlmostEqual(compute_rdm(100.0, 25.0), 4.0)

    def test_zero_tolerance_raises(self):
        with self.assertRaises(ValueError):
            compute_rdm(0.0, 10.0)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            compute_rdm(-5.0, 10.0)

    def test_zero_environment_raises(self):
        with self.assertRaises(ValueError):
            compute_rdm(10.0, 0.0)

    def test_negative_environment_raises(self):
        with self.assertRaises(ValueError):
            compute_rdm(10.0, -1.0)

    def test_error_message_names_the_bad_argument(self):
        with self.assertRaises(ValueError) as ctx:
            compute_rdm(10.0, 0.0)
        self.assertIn("predicted_environment", str(ctx.exception))


class TestCheckRdmCompliance(unittest.TestCase):

    def test_tid_at_threshold_is_compliant(self):
        result = check_rdm_compliance(2.0, RadiationType.TID, ProjectPhase.PRE_PDR)
        self.assertTrue(result.compliant)
        self.assertEqual(result.threshold, 2.0)
        self.assertEqual(result.radiation_type, "tid")
        self.assertEqual(result.phase, "pre_pdr")

    def test_tid_below_threshold_is_non_compliant(self):
        result = check_rdm_compliance(1.9, RadiationType.TID, ProjectPhase.PDR_CDR)
        self.assertFalse(result.compliant)

    def test_dd_post_cdr_below_threshold_is_non_compliant(self):
        result = check_rdm_compliance(
            1.0, RadiationType.DD, ProjectPhase.POST_CDR
        )
        self.assertFalse(result.compliant)
        self.assertEqual(result.threshold, 2.0)

    def test_see_has_no_numeric_gate(self):
        result = check_rdm_compliance(
            1.0, RadiationType.SEE_HEAVY_ION, ProjectPhase.POST_CDR
        )
        self.assertTrue(result.compliant)
        self.assertEqual(result.threshold, 0.0)

    def test_see_proton_has_no_numeric_gate(self):
        result = check_rdm_compliance(
            0.5, RadiationType.SEE_PROTON, ProjectPhase.PRE_PDR
        )
        self.assertTrue(result.compliant)
        self.assertEqual(result.threshold, 0.0)

    def test_threshold_zero_labels_adequate(self):
        result = check_rdm_compliance(
            1.2, RadiationType.SEE_HEAVY_ION, ProjectPhase.PRE_PDR
        )
        self.assertEqual(result.status_label(), "adequate")

    def test_status_label_inadequate_below_threshold(self):
        result = check_rdm_compliance(1.5, RadiationType.TID, ProjectPhase.PRE_PDR)
        self.assertEqual(result.status_label(), "inadequate")

    def test_status_label_marginal_between_threshold_and_1_5x(self):
        result = check_rdm_compliance(2.5, RadiationType.TID, ProjectPhase.PRE_PDR)
        self.assertEqual(result.status_label(), "marginal")

    def test_status_label_adequate_at_or_above_1_5x_threshold(self):
        result = check_rdm_compliance(3.0, RadiationType.DD, ProjectPhase.POST_CDR)
        self.assertEqual(result.status_label(), "adequate")

    def test_rdm_result_dataclass_fields(self):
        result = RdmResult(
            rdm=4.0,
            threshold=2.0,
            compliant=True,
            radiation_type="tid",
            phase="pre_pdr",
        )
        self.assertEqual(result.rdm, 4.0)
        self.assertEqual(result.status_label(), "adequate")


class TestValidateTestMethod(unittest.TestCase):

    def test_analysis_only_valid_before_cdr(self):
        for phase in (ProjectPhase.PRE_PDR, ProjectPhase.PDR_CDR):
            result = validate_test_method(
                RadiationType.TID, TestMethod.ANALYSIS_ONLY, phase
            )
            self.assertTrue(result.valid, msg=f"phase={phase}")

    def test_analysis_only_invalid_post_cdr(self):
        result = validate_test_method(
            RadiationType.TID, TestMethod.ANALYSIS_ONLY, ProjectPhase.POST_CDR
        )
        self.assertFalse(result.valid)
        self.assertIn("Post-CDR", result.reason)

    def test_similarity_valid_at_every_phase(self):
        for phase in ProjectPhase:
            result = validate_test_method(
                RadiationType.DD, TestMethod.SIMILARITY, phase
            )
            self.assertTrue(result.valid, msg=f"phase={phase}")

    def test_cobalt_60_valid_for_tid(self):
        result = validate_test_method(
            RadiationType.TID, TestMethod.COBALT_60, ProjectPhase.POST_CDR
        )
        self.assertTrue(result.valid)

    def test_xray_and_eldrs_valid_for_tid(self):
        for method in (TestMethod.XRAY, TestMethod.ELDRS):
            result = validate_test_method(
                RadiationType.TID, method, ProjectPhase.POST_CDR
            )
            self.assertTrue(result.valid, msg=f"method={method}")

    def test_proton_and_neutron_valid_for_dd(self):
        for method in (TestMethod.PROTON, TestMethod.NEUTRON):
            result = validate_test_method(
                RadiationType.DD, method, ProjectPhase.POST_CDR
            )
            self.assertTrue(result.valid, msg=f"method={method}")

    def test_cobalt_60_invalid_for_dd(self):
        result = validate_test_method(
            RadiationType.DD, TestMethod.COBALT_60, ProjectPhase.POST_CDR
        )
        self.assertFalse(result.valid)
        self.assertIn("not applicable", result.reason)

    def test_proton_invalid_for_heavy_ion_see(self):
        result = validate_test_method(
            RadiationType.SEE_HEAVY_ION, TestMethod.PROTON, ProjectPhase.POST_CDR
        )
        self.assertFalse(result.valid)

    def test_heavy_ion_valid_for_heavy_ion_see(self):
        result = validate_test_method(
            RadiationType.SEE_HEAVY_ION, TestMethod.HEAVY_ION, ProjectPhase.POST_CDR
        )
        self.assertTrue(result.valid)

    def test_result_fields(self):
        result = validate_test_method(
            RadiationType.TID, TestMethod.COBALT_60, ProjectPhase.POST_CDR
        )
        self.assertIsInstance(result, TestMethodResult)
        self.assertEqual(result.radiation_type, "tid")
        self.assertEqual(result.test_method, "cobalt_60")
        self.assertEqual(result.phase, "post_cdr")


class TestRunPhaseGate(unittest.TestCase):

    def test_clean_gate_passes(self):
        rdm = [
            check_rdm_compliance(4.0, RadiationType.TID, ProjectPhase.PRE_PDR),
            check_rdm_compliance(3.0, RadiationType.DD, ProjectPhase.PRE_PDR),
        ]
        methods = [
            validate_test_method(
                RadiationType.TID, TestMethod.ANALYSIS_ONLY, ProjectPhase.PRE_PDR
            )
        ]
        result = run_phase_gate(ProjectPhase.PRE_PDR, rdm, methods)
        self.assertTrue(result.compliant)
        self.assertEqual(result.findings, [])
        self.assertEqual(result.phase, "pre_pdr")

    def test_rdm_shortfall_produces_finding(self):
        rdm = [check_rdm_compliance(1.2, RadiationType.TID, ProjectPhase.PDR_CDR)]
        result = run_phase_gate(ProjectPhase.PDR_CDR, rdm, [])
        self.assertFalse(result.compliant)
        self.assertEqual(len(result.findings), 1)
        self.assertIn("RDM", result.findings[0])

    def test_invalid_method_produces_finding(self):
        methods = [
            validate_test_method(
                RadiationType.TID,
                TestMethod.ANALYSIS_ONLY,
                ProjectPhase.POST_CDR,
            )
        ]
        result = run_phase_gate(ProjectPhase.POST_CDR, [], methods)
        self.assertFalse(result.compliant)
        self.assertEqual(len(result.findings), 1)
        self.assertIn("Invalid test method", result.findings[0])

    def test_multiple_findings_are_aggregated(self):
        rdm = [
            check_rdm_compliance(1.0, RadiationType.TID, ProjectPhase.POST_CDR),
            check_rdm_compliance(1.5, RadiationType.DD, ProjectPhase.POST_CDR),
        ]
        methods = [
            validate_test_method(
                RadiationType.DD,
                TestMethod.COBALT_60,
                ProjectPhase.POST_CDR,
            )
        ]
        result = run_phase_gate(ProjectPhase.POST_CDR, rdm, methods)
        self.assertFalse(result.compliant)
        self.assertEqual(len(result.findings), 3)

    def test_empty_inputs_pass(self):
        result = run_phase_gate(ProjectPhase.PRE_PDR, [], [])
        self.assertTrue(result.compliant)

    def test_see_with_no_numeric_gate_does_not_produce_finding(self):
        rdm = [
            check_rdm_compliance(
                0.5, RadiationType.SEE_HEAVY_ION, ProjectPhase.POST_CDR
            )
        ]
        result = run_phase_gate(ProjectPhase.POST_CDR, rdm, [])
        self.assertTrue(result.compliant)

    def test_phase_gate_result_defaults(self):
        result = PhaseGateResult(phase="pre_pdr")
        self.assertEqual(result.findings, [])
        self.assertTrue(result.compliant)


class TestCategorizeComponentMargin(unittest.TestCase):

    def test_adequate_at_1_5x_threshold(self):
        self.assertEqual(categorize_component_margin(3.0, 2.0), "adequate")

    def test_adequate_above_1_5x_threshold(self):
        self.assertEqual(categorize_component_margin(10.0, 2.0), "adequate")

    def test_marginal_at_threshold(self):
        self.assertEqual(categorize_component_margin(2.0, 2.0), "marginal")

    def test_marginal_just_below_1_5x_threshold(self):
        self.assertEqual(categorize_component_margin(2.99, 2.0), "marginal")

    def test_inadequate_below_threshold(self):
        self.assertEqual(categorize_component_margin(1.99, 2.0), "inadequate")

    def test_default_threshold_is_two(self):
        self.assertEqual(categorize_component_margin(3.0), "adequate")
        self.assertEqual(categorize_component_margin(1.0), "inadequate")

    def test_custom_threshold(self):
        self.assertEqual(categorize_component_margin(5.0, 5.0), "marginal")

    def test_zero_threshold_raises(self):
        with self.assertRaises(ValueError):
            categorize_component_margin(3.0, 0.0)

    def test_negative_threshold_raises(self):
        with self.assertRaises(ValueError):
            categorize_component_margin(3.0, -1.0)


if __name__ == "__main__":
    unittest.main()
