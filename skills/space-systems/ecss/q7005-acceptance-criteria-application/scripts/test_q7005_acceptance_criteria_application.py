"""Contract test for the IR contamination acceptance leaf (stdlib unittest)."""

import unittest

from q7005_acceptance_criteria_application_logic import (
    COMPLIANT,
    COMPLIANT_ON_DEVIATION,
    INDETERMINATE,
    METHOD_INDIRECT,
    NON_COMPLIANT,
    ORGANIC_CLEANLINESS_LEVELS,
    RULE_BANDED_ACCEPTANCE,
    RULE_GUARDED_ACCEPTANCE,
    RULE_SIMPLE_ACCEPTANCE,
    assess_acceptance,
    decision_interval,
    evaluate_surface,
    level_limit,
    recovery_corrected_level,
    required_limit,
    surface_level,
    validate_result,
    within_level,
)


def result(surface="radiator-face", level=0.8, **kw):
    record = {"surface": surface, "measured_level_mg_m2": level}
    record.update(kw)
    return record


class TestCleanlinessLevels(unittest.TestCase):
    def test_every_level_carries_a_positive_limit(self):
        for name in ORGANIC_CLEANLINESS_LEVELS:
            self.assertGreater(level_limit(name), 0.0)

    def test_levels_are_ordered_from_tight_to_loose(self):
        self.assertLess(level_limit("level-a"), level_limit("level-d"))

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            level_limit("level-spotless")

    def test_a_numeric_requirement_is_used_directly(self):
        self.assertAlmostEqual(required_limit(3.5), 3.5, places=9)

    def test_a_negative_numeric_requirement_raises(self):
        with self.assertRaises(ValueError):
            required_limit(-1.0)


class TestRecoveryCorrection(unittest.TestCase):
    def test_a_partial_recovery_raises_the_surface_level(self):
        self.assertAlmostEqual(recovery_corrected_level(0.60, 0.75), 0.80, places=9)

    def test_a_full_recovery_leaves_the_level_alone(self):
        self.assertAlmostEqual(recovery_corrected_level(1.20, 1.0), 1.20, places=9)

    def test_a_zero_recovery_raises(self):
        with self.assertRaises(ValueError):
            recovery_corrected_level(0.60, 0.0)

    def test_a_recovery_above_unity_raises(self):
        with self.assertRaises(ValueError):
            recovery_corrected_level(0.60, 1.4)

    def test_non_numeric_recovery_raises(self):
        with self.assertRaises(ValueError):
            recovery_corrected_level(0.60, "0.75")


class TestWithinLevel(unittest.TestCase):
    def test_a_value_on_the_limit_is_within_it(self):
        self.assertTrue(within_level(2.0, 2.0))

    def test_a_value_under_the_limit_is_within_it(self):
        self.assertTrue(within_level(1.9, 2.0))

    def test_a_value_clearly_over_the_limit_is_not(self):
        self.assertFalse(within_level(2.5, 2.0))


class TestDecisionInterval(unittest.TestCase):
    def test_simple_acceptance_spends_no_uncertainty(self):
        low, high = decision_interval(1.0, 0.3, RULE_SIMPLE_ACCEPTANCE)
        self.assertAlmostEqual(low, 1.0, places=9)
        self.assertAlmostEqual(high, 1.0, places=9)

    def test_guarded_acceptance_spends_it_against_the_applicant(self):
        low, high = decision_interval(1.0, 0.3, RULE_GUARDED_ACCEPTANCE)
        self.assertAlmostEqual(low, 1.0, places=9)
        self.assertAlmostEqual(high, 1.3, places=9)

    def test_a_banded_rule_opens_the_interval_both_ways(self):
        low, high = decision_interval(1.0, 0.3, RULE_BANDED_ACCEPTANCE)
        self.assertAlmostEqual(low, 0.7, places=9)
        self.assertAlmostEqual(high, 1.3, places=9)

    def test_a_banded_interval_never_goes_below_zero(self):
        low, _ = decision_interval(0.1, 0.4, RULE_BANDED_ACCEPTANCE)
        self.assertAlmostEqual(low, 0.0, places=12)

    def test_a_guarded_rule_without_an_uncertainty_raises(self):
        with self.assertRaises(ValueError):
            decision_interval(1.0, None, RULE_GUARDED_ACCEPTANCE)

    def test_an_unknown_rule_raises(self):
        with self.assertRaises(ValueError):
            decision_interval(1.0, 0.1, "whatever-passes")


class TestValidateResult(unittest.TestCase):
    def test_a_valid_record_is_normalized(self):
        norm = validate_result(result())
        self.assertEqual(norm["surface"], "radiator-face")
        self.assertTrue(norm["detected"])

    def test_a_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_result(["radiator-face"])

    def test_an_empty_surface_raises(self):
        with self.assertRaises(ValueError):
            validate_result(result(""))

    def test_a_negative_level_raises(self):
        with self.assertRaises(ValueError):
            validate_result(result(level=-0.2))

    def test_a_detection_with_no_level_raises(self):
        with self.assertRaises(ValueError):
            validate_result({"surface": "s", "measured_level_mg_m2": None})

    def test_a_non_detect_with_no_bound_raises(self):
        with self.assertRaises(ValueError):
            validate_result(
                {"surface": "s", "detected": False, "measured_level_mg_m2": None}
            )

    def test_a_non_detect_carrying_a_level_raises(self):
        with self.assertRaises(ValueError):
            validate_result(
                result(detected=False, quantitation_limit_mg_m2=0.5)
            )

    def test_an_indirect_record_without_a_recovery_raises(self):
        with self.assertRaises(ValueError):
            validate_result(result(method_kind=METHOD_INDIRECT))

    def test_an_unknown_method_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_result(result(method_kind="by-eye"))

    def test_a_non_string_deviation_reference_raises(self):
        with self.assertRaises(ValueError):
            validate_result(result(deviation_reference=17))


class TestSurfaceLevel(unittest.TestCase):
    def test_a_direct_result_is_its_own_surface_level(self):
        self.assertAlmostEqual(surface_level(result(level=1.5)), 1.5, places=9)

    def test_an_indirect_result_is_lifted_by_its_recovery(self):
        value = surface_level(
            result(level=1.5, method_kind=METHOD_INDIRECT, recovery_fraction=0.75)
        )
        self.assertAlmostEqual(value, 2.0, places=9)

    def test_a_non_detect_has_no_surface_level(self):
        self.assertIsNone(
            surface_level(
                {
                    "surface": "s",
                    "detected": False,
                    "quantitation_limit_mg_m2": 0.4,
                }
            )
        )


class TestEvaluateSurface(unittest.TestCase):
    def test_a_clean_surface_is_compliant(self):
        row = evaluate_surface(result(level=0.5), "level-b",
                               RULE_SIMPLE_ACCEPTANCE)
        self.assertEqual(row["verdict"], COMPLIANT)
        self.assertEqual(row["findings"], [])

    def test_a_value_exactly_on_the_level_is_compliant(self):
        row = evaluate_surface(result(level=2.0), "level-b",
                               RULE_SIMPLE_ACCEPTANCE)
        self.assertEqual(row["verdict"], COMPLIANT)
        self.assertAlmostEqual(row["graded_level_mg_m2"], 2.0, places=9)

    def test_a_guarded_rule_can_fail_what_simple_acceptance_passes(self):
        record = result(level=1.9, expanded_uncertainty_mg_m2=0.3)
        self.assertEqual(
            evaluate_surface(record, "level-b", RULE_SIMPLE_ACCEPTANCE)["verdict"],
            COMPLIANT,
        )
        self.assertEqual(
            evaluate_surface(record, "level-b", RULE_GUARDED_ACCEPTANCE)["verdict"],
            NON_COMPLIANT,
        )

    def test_a_banded_rule_reports_a_straddling_result_as_undecided(self):
        row = evaluate_surface(
            result(level=1.9, expanded_uncertainty_mg_m2=0.3),
            "level-b",
            RULE_BANDED_ACCEPTANCE,
        )
        self.assertEqual(row["verdict"], INDETERMINATE)
        self.assertIn("uncertainty-band-straddles-the-required-level",
                      row["findings"])

    def test_recovery_correction_can_turn_a_pass_into_a_failure(self):
        record = result(
            level=1.8, method_kind=METHOD_INDIRECT, recovery_fraction=0.60
        )
        row = evaluate_surface(record, "level-b", RULE_SIMPLE_ACCEPTANCE)
        self.assertEqual(row["verdict"], NON_COMPLIANT)
        self.assertAlmostEqual(row["graded_level_mg_m2"], 3.0, places=9)

    def test_a_non_detect_under_the_level_demonstrates_compliance(self):
        row = evaluate_surface(
            {"surface": "s", "detected": False, "quantitation_limit_mg_m2": 0.4},
            "level-b",
        )
        self.assertEqual(row["verdict"], COMPLIANT)
        self.assertAlmostEqual(row["graded_level_mg_m2"], 0.4, places=9)

    def test_a_non_detect_coarser_than_the_level_demonstrates_nothing(self):
        row = evaluate_surface(
            {"surface": "s", "detected": False, "quantitation_limit_mg_m2": 4.0},
            "level-b",
        )
        self.assertEqual(row["verdict"], INDETERMINATE)
        self.assertIn("quantitation-limit-coarser-than-the-required-level",
                      row["findings"])

    def test_a_full_deviation_package_carries_a_failing_surface(self):
        row = evaluate_surface(
            result(
                level=4.0,
                deviation_reference="DEV-31",
                effects_assessment_reference="CEA-77",
            ),
            "level-b",
            RULE_SIMPLE_ACCEPTANCE,
        )
        self.assertEqual(row["verdict"], COMPLIANT_ON_DEVIATION)

    def test_a_deviation_without_an_effects_assessment_does_not(self):
        row = evaluate_surface(
            result(level=4.0, deviation_reference="DEV-31"),
            "level-b",
            RULE_SIMPLE_ACCEPTANCE,
        )
        self.assertEqual(row["verdict"], NON_COMPLIANT)
        self.assertIn("deviation-cited-without-an-effects-assessment",
                      row["findings"])

    def test_an_effects_assessment_without_a_deviation_does_not_either(self):
        row = evaluate_surface(
            result(level=4.0, effects_assessment_reference="CEA-77"),
            "level-b",
            RULE_SIMPLE_ACCEPTANCE,
        )
        self.assertEqual(row["verdict"], NON_COMPLIANT)
        self.assertIn("effects-assessment-cited-without-a-deviation",
                      row["findings"])

    def test_a_deviation_cannot_rescue_an_indeterminate_result(self):
        row = evaluate_surface(
            {
                "surface": "s",
                "detected": False,
                "quantitation_limit_mg_m2": 4.0,
                "deviation_reference": "DEV-31",
            },
            "level-b",
        )
        self.assertEqual(row["verdict"], INDETERMINATE)
        self.assertIn("deviation-offered-against-an-indeterminate-result",
                      row["findings"])

    def test_an_unknown_decision_rule_raises(self):
        with self.assertRaises(ValueError):
            evaluate_surface(result(), "level-b", "looks-fine")


class TestAssessAcceptance(unittest.TestCase):
    def test_a_clean_set_is_clear(self):
        report = assess_acceptance(
            [result("a", 0.4), result("b", 0.5)], "level-b",
            RULE_SIMPLE_ACCEPTANCE,
        )
        self.assertTrue(report["clear"])
        self.assertEqual(report["non_compliant"], [])

    def test_one_failure_clouds_the_set(self):
        report = assess_acceptance(
            [result("a", 0.4), result("b", 9.0)], "level-b",
            RULE_SIMPLE_ACCEPTANCE,
        )
        self.assertFalse(report["clear"])
        self.assertEqual(report["non_compliant"], ["b"])

    def test_indeterminate_surfaces_are_grouped_apart_from_failures(self):
        report = assess_acceptance(
            [
                result("a", 0.4),
                {
                    "surface": "b",
                    "detected": False,
                    "quantitation_limit_mg_m2": 9.0,
                },
            ],
            "level-b",
            RULE_SIMPLE_ACCEPTANCE,
        )
        self.assertEqual(report["indeterminate"], ["b"])
        self.assertEqual(report["non_compliant"], [])

    def test_duplicate_surface_raises(self):
        with self.assertRaises(ValueError):
            assess_acceptance([result("a"), result("a")], "level-b")

    def test_empty_set_raises(self):
        with self.assertRaises(ValueError):
            assess_acceptance([], "level-b")

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            assess_acceptance([result()], "level-immaculate")


if __name__ == "__main__":
    unittest.main()
