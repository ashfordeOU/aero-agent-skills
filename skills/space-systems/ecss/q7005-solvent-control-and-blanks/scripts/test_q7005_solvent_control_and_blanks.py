#!/usr/bin/env python3
"""Contract test for the solvent blank control logic (offline)."""

import copy
import math
import unittest

from q7005_solvent_control_and_blanks_logic import (
    DEFAULT_BLANK_POLICY,
    DETECTED_NOT_QUANTIFIABLE,
    GRADES,
    HANDLING_BLANK,
    NOT_DETECTED,
    QUANTIFIABLE,
    SOLVENT_BLANK,
    assess_blank_control,
    blank_fraction,
    combined_uncertainty_ug,
    detection_limit_ug,
    expected_blank_mass_ug,
    grade_net_result,
    net_residue_ug,
    quantitation_limit_ug,
    solvent_purity_check,
    validate_blank_policy,
)

BASE_CASE = {
    "blank_replicates": 3,
    "blank_kinds": (SOLVENT_BLANK, HANDLING_BLANK),
    "solvent_volume_ml": 20.0,
    "solvent_nvr_mg_per_l": 0.5,
    "measured_blank_ug": 11.0,
    "gross_residue_ug": 140.0,
    "blank_sd_ug": 2.0,
    "gross_sd_ug": 4.0,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_blank_policy(DEFAULT_BLANK_POLICY), DEFAULT_BLANK_POLICY
        )

    def test_a_single_replicate_requirement_rejected(self):
        broken = copy.deepcopy(DEFAULT_BLANK_POLICY)
        broken["min_blank_replicates"] = 1
        with self.assertRaises(ValueError):
            validate_blank_policy(broken)

    def test_a_blank_fraction_ceiling_of_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_BLANK_POLICY)
        broken["max_blank_fraction"] = 1.0
        with self.assertRaises(ValueError):
            validate_blank_policy(broken)

    def test_a_quantitation_sigma_below_detection_rejected(self):
        broken = copy.deepcopy(DEFAULT_BLANK_POLICY)
        broken["quantitation_sigma"] = 2.0
        with self.assertRaises(ValueError):
            validate_blank_policy(broken)

    def test_a_non_boolean_handling_blank_flag_rejected(self):
        broken = copy.deepcopy(DEFAULT_BLANK_POLICY)
        broken["require_handling_blank"] = "yes"
        with self.assertRaises(ValueError):
            validate_blank_policy(broken)

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_blank_policy(3)


class ExpectedBlankTests(unittest.TestCase):
    def test_milligrams_per_litre_times_millilitres_gives_micrograms(self):
        self.assertAlmostEqual(expected_blank_mass_ug(20.0, 0.5), 10.0, places=9)

    def test_doubling_the_volume_doubles_the_expected_blank(self):
        self.assertAlmostEqual(
            expected_blank_mass_ug(40.0, 0.5) / expected_blank_mass_ug(20.0, 0.5),
            2.0,
            places=9,
        )

    def test_a_perfectly_pure_solvent_contributes_nothing(self):
        self.assertAlmostEqual(expected_blank_mass_ug(20.0, 0.0), 0.0, places=9)

    def test_a_zero_volume_rejected(self):
        with self.assertRaises(ValueError):
            expected_blank_mass_ug(0.0, 0.5)

    def test_a_negative_residue_specification_rejected(self):
        with self.assertRaises(ValueError):
            expected_blank_mass_ug(20.0, -0.1)


class PurityTests(unittest.TestCase):
    def test_a_clean_grade_is_acceptable(self):
        check = solvent_purity_check(0.5)
        self.assertTrue(check["acceptable"])
        self.assertIsNone(check["reason"])

    def test_a_grade_exactly_on_the_ceiling_is_acceptable(self):
        ceiling = DEFAULT_BLANK_POLICY["max_solvent_nvr_mg_per_l"]
        self.assertTrue(solvent_purity_check(ceiling)["acceptable"])

    def test_a_dirty_grade_is_rejected_with_a_reason(self):
        check = solvent_purity_check(5.0)
        self.assertFalse(check["acceptable"])
        self.assertIn("exceeds the grade ceiling", check["reason"])

    def test_a_non_numeric_grade_rejected(self):
        with self.assertRaises(ValueError):
            solvent_purity_check("reagent")


class CorrectionTests(unittest.TestCase):
    def test_the_blank_fraction_is_the_blank_over_the_gross(self):
        self.assertAlmostEqual(blank_fraction(10.0, 100.0), 0.1, places=9)

    def test_a_zero_gross_residue_rejected(self):
        with self.assertRaises(ValueError):
            blank_fraction(10.0, 0.0)

    def test_the_net_is_the_gross_less_the_blank(self):
        net = net_residue_ug(140.0, 11.0)
        self.assertAlmostEqual(net["net_mass_ug"], 129.0, places=9)
        self.assertFalse(net["blank_exceeded_sample"])

    def test_a_blank_above_the_gross_clamps_the_net_but_is_flagged(self):
        net = net_residue_ug(10.0, 25.0)
        self.assertAlmostEqual(net["net_mass_ug"], 0.0, places=9)
        self.assertAlmostEqual(net["raw_net_ug"], -15.0, places=9)
        self.assertTrue(net["blank_exceeded_sample"])

    def test_a_blank_equal_to_the_gross_leaves_nothing_and_is_not_negative(self):
        net = net_residue_ug(20.0, 20.0)
        self.assertAlmostEqual(net["net_mass_ug"], 0.0, places=9)
        self.assertFalse(net["blank_exceeded_sample"])

    def test_a_negative_blank_rejected(self):
        with self.assertRaises(ValueError):
            net_residue_ug(140.0, -1.0)


class LimitTests(unittest.TestCase):
    def test_the_detection_limit_is_the_detection_sigma_times_the_scatter(self):
        self.assertAlmostEqual(
            detection_limit_ug(2.0),
            DEFAULT_BLANK_POLICY["detection_sigma"] * 2.0,
            places=9,
        )

    def test_the_quantitation_limit_sits_above_the_detection_limit(self):
        self.assertGreater(quantitation_limit_ug(2.0), detection_limit_ug(2.0))

    def test_both_limits_scale_with_the_blank_scatter(self):
        self.assertAlmostEqual(
            detection_limit_ug(4.0) / detection_limit_ug(2.0), 2.0, places=9
        )

    def test_a_zero_blank_scatter_rejected(self):
        with self.assertRaises(ValueError):
            detection_limit_ug(0.0)

    def test_the_combined_uncertainty_adds_in_quadrature(self):
        self.assertAlmostEqual(
            combined_uncertainty_ug(3.0, 4.0), 5.0, places=9
        )

    def test_a_noiseless_gross_leaves_the_blank_scatter_alone(self):
        self.assertAlmostEqual(combined_uncertainty_ug(0.0, 2.0), 2.0, places=9)

    def test_a_negative_scatter_rejected(self):
        with self.assertRaises(ValueError):
            combined_uncertainty_ug(-1.0, 2.0)


class GradingTests(unittest.TestCase):
    def test_a_large_net_is_quantifiable(self):
        self.assertEqual(grade_net_result(129.0, 2.0)["grade"], QUANTIFIABLE)

    def test_a_net_between_the_limits_is_detected_only(self):
        self.assertEqual(
            grade_net_result(12.0, 2.0)["grade"], DETECTED_NOT_QUANTIFIABLE
        )

    def test_a_net_below_the_detection_limit_is_not_detected(self):
        self.assertEqual(grade_net_result(2.0, 2.0)["grade"], NOT_DETECTED)

    def test_a_net_exactly_on_the_quantitation_limit_is_quantifiable(self):
        loq = quantitation_limit_ug(2.0)
        self.assertEqual(grade_net_result(loq, 2.0)["grade"], QUANTIFIABLE)

    def test_a_net_exactly_on_the_detection_limit_is_detected(self):
        lod = detection_limit_ug(2.0)
        self.assertEqual(
            grade_net_result(lod, 2.0)["grade"], DETECTED_NOT_QUANTIFIABLE
        )

    def test_every_grade_comes_from_the_declared_set(self):
        for net in (0.0, 7.0, 25.0, 300.0):
            self.assertIn(grade_net_result(net, 2.0)["grade"], GRADES)

    def test_a_negative_net_rejected(self):
        with self.assertRaises(ValueError):
            grade_net_result(-1.0, 2.0)


class AssessmentTests(unittest.TestCase):
    def test_the_base_case_blank_control_is_sound(self):
        result = assess_blank_control(BASE_CASE)
        self.assertTrue(result["blank_control_sound"])
        self.assertEqual(result["findings"], [])

    def test_the_base_case_result_is_quantifiable(self):
        result = assess_blank_control(BASE_CASE)
        self.assertEqual(result["grading"]["grade"], QUANTIFIABLE)

    def test_a_run_with_no_blank_is_refused_outright(self):
        with self.assertRaises(ValueError):
            assess_blank_control(_case(BASE_CASE, blank_replicates=0))

    def test_a_run_with_no_solvent_blank_is_refused(self):
        with self.assertRaises(ValueError):
            assess_blank_control(_case(BASE_CASE, blank_kinds=(HANDLING_BLANK,)))

    def test_an_unknown_blank_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_blank_control(
                _case(BASE_CASE, blank_kinds=(SOLVENT_BLANK, "field-blank"))
            )

    def test_too_few_replicates_is_a_finding(self):
        result = assess_blank_control(_case(BASE_CASE, blank_replicates=2))
        self.assertTrue(any("blank replicates" in f for f in result["findings"]))

    def test_a_missing_handling_blank_is_a_finding(self):
        result = assess_blank_control(
            _case(BASE_CASE, blank_kinds=(SOLVENT_BLANK,))
        )
        self.assertTrue(any("handling blank" in f for f in result["findings"]))

    def test_a_dirty_solvent_grade_is_a_finding(self):
        result = assess_blank_control(
            _case(
                BASE_CASE,
                solvent_nvr_mg_per_l=4.0,
                measured_blank_ug=80.0,
                gross_residue_ug=400.0,
            )
        )
        self.assertTrue(any("solvent grade" in f for f in result["findings"]))

    def test_a_blank_dominated_result_is_a_finding(self):
        result = assess_blank_control(
            _case(BASE_CASE, measured_blank_ug=11.0, gross_residue_ug=20.0)
        )
        self.assertTrue(any("blank-limited" in f for f in result["findings"]))

    def test_a_blank_fraction_exactly_on_the_ceiling_is_accepted(self):
        ceiling = DEFAULT_BLANK_POLICY["max_blank_fraction"]
        gross = 11.0 / ceiling
        result = assess_blank_control(_case(BASE_CASE, gross_residue_ug=gross))
        self.assertFalse(any("blank-limited" in f for f in result["findings"]))

    def test_a_blank_above_the_sample_is_a_finding(self):
        result = assess_blank_control(
            _case(
                BASE_CASE,
                measured_blank_ug=11.0,
                gross_residue_ug=8.0,
                solvent_nvr_mg_per_l=0.5,
            )
        )
        self.assertTrue(any("blank exceeded" in f for f in result["findings"]))

    def test_a_measured_blank_far_from_the_prediction_is_a_finding(self):
        result = assess_blank_control(_case(BASE_CASE, measured_blank_ug=30.0))
        self.assertTrue(any("departs from" in f for f in result["findings"]))

    def test_a_net_between_the_limits_is_a_finding(self):
        result = assess_blank_control(
            _case(BASE_CASE, gross_residue_ug=23.0, measured_blank_ug=11.0)
        )
        self.assertTrue(
            any("detection limit" in f for f in result["findings"])
            or any("blank-limited" in f for f in result["findings"])
        )

    def test_every_assessment_carries_the_net_correction_duty(self):
        result = assess_blank_control(BASE_CASE)
        self.assertTrue(any("blank-corrected net" in d for d in result["duties"]))

    def test_every_assessment_carries_the_solvent_lot_duty(self):
        result = assess_blank_control(BASE_CASE)
        self.assertTrue(any("solvent lot" in d for d in result["duties"]))

    def test_the_combined_uncertainty_is_reported(self):
        result = assess_blank_control(BASE_CASE)
        self.assertAlmostEqual(
            result["combined_uncertainty_ug"], math.sqrt(16.0 + 4.0), places=9
        )

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_blank_control("we used fresh solvent")


if __name__ == "__main__":
    unittest.main()
