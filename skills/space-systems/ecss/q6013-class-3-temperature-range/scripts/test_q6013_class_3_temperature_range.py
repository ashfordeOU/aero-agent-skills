"""Contract tests for the clause 6.2.2.6 Class 3 temperature-range logic."""

import unittest

from q6013_class_3_temperature_range_logic import (
    CLASS_3_END_MARGIN_K,
    MAX_HOT_END_MOUNTING_CREDIT_K,
    MAX_UPRATING_EXTENSION_K,
    MIN_RETAINED_UNCERTAINTY_K,
    TEMPERATURE_GRADE_BANDS,
    assess_temperature_range,
    effective_uncertainty_k,
    end_disposition,
    end_margin,
    grade_band,
    mounting_repair_credit,
    normalize_mounting_repair,
    normalize_uprating,
    rated_limits,
    uprating_credit,
    widened_application_extremes,
)

INDUSTRIAL = {"temperature_grade": "industrial-grade"}


class GradeBandTests(unittest.TestCase):
    def test_industrial_band_is_returned(self):
        self.assertEqual(grade_band("industrial-grade"), (-40.0, 85.0))

    def test_every_tabulated_band_runs_cold_to_hot(self):
        for grade, (low, high) in TEMPERATURE_GRADE_BANDS.items():
            self.assertLess(low, high, grade)

    def test_unknown_grade_rejected(self):
        with self.assertRaises(ValueError):
            grade_band("space-grade-probably")

    def test_explicit_limits_resolve_without_a_grade(self):
        self.assertEqual(rated_limits({"rated_min_c": -20.0, "rated_max_c": 90.0}), (-20.0, 90.0))

    def test_grade_and_explicit_limits_together_rejected(self):
        with self.assertRaises(ValueError):
            rated_limits({"temperature_grade": "industrial-grade", "rated_max_c": 90.0})

    def test_neither_grade_nor_limits_rejected(self):
        with self.assertRaises(ValueError):
            rated_limits({})

    def test_inverted_explicit_limits_rejected(self):
        with self.assertRaises(ValueError):
            rated_limits({"rated_min_c": 90.0, "rated_max_c": -20.0})

    def test_non_mapping_declaration_rejected(self):
        with self.assertRaises(ValueError):
            rated_limits(["industrial-grade"])


class UncertaintyTests(unittest.TestCase):
    def test_uncorrelated_model_keeps_the_declared_uncertainty(self):
        self.assertAlmostEqual(effective_uncertainty_k(10.0, "model-uncorrelated"), 10.0, places=9)

    def test_correlated_model_earns_the_credit(self):
        self.assertAlmostEqual(
            effective_uncertainty_k(10.0, "model-correlated-by-thermal-balance-test"),
            5.0,
            places=9,
        )

    def test_credit_never_crosses_the_retained_floor(self):
        self.assertAlmostEqual(
            effective_uncertainty_k(3.0, "model-correlated-by-thermal-balance-test"),
            MIN_RETAINED_UNCERTAINTY_K,
            places=9,
        )

    def test_a_small_declared_uncertainty_is_never_widened_by_the_floor(self):
        self.assertAlmostEqual(
            effective_uncertainty_k(1.0, "model-correlated-by-thermal-balance-test"),
            1.0,
            places=9,
        )

    def test_unknown_model_state_rejected(self):
        with self.assertRaises(ValueError):
            effective_uncertainty_k(10.0, "model-looks-about-right")

    def test_negative_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            effective_uncertainty_k(-1.0)

    def test_widening_pushes_both_ends_outwards(self):
        self.assertEqual(widened_application_extremes(-20.0, 70.0, 5.0), (-25.0, 75.0))

    def test_zero_uncertainty_leaves_the_prediction(self):
        self.assertEqual(widened_application_extremes(-20.0, 70.0, 0.0), (-20.0, 70.0))

    def test_inverted_application_extremes_rejected(self):
        with self.assertRaises(ValueError):
            widened_application_extremes(70.0, -20.0, 5.0)


class EndMarginTests(unittest.TestCase):
    def test_cold_margin_is_the_gap_above_the_rated_minimum(self):
        self.assertAlmostEqual(end_margin("cold", -40.0, -25.0), 15.0, places=9)

    def test_hot_margin_is_the_gap_below_the_rated_maximum(self):
        self.assertAlmostEqual(end_margin("hot", 85.0, 75.0), 10.0, places=9)

    def test_an_end_outside_the_band_is_a_negative_margin(self):
        self.assertAlmostEqual(end_margin("hot", 85.0, 95.0), -10.0, places=9)

    def test_unknown_end_rejected(self):
        with self.assertRaises(ValueError):
            end_margin("warm", 85.0, 75.0)

    def test_margin_above_the_requirement_is_covered(self):
        self.assertEqual(end_disposition(20.0), "end-covered-with-margin")

    def test_margin_exactly_on_the_requirement_is_covered(self):
        self.assertEqual(end_disposition(CLASS_3_END_MARGIN_K), "end-covered-with-margin")

    def test_zero_margin_is_short_not_covered(self):
        self.assertEqual(end_disposition(0.0), "end-margin-short")

    def test_negative_margin_is_not_covered(self):
        self.assertEqual(end_disposition(-1.0), "end-not-covered")

    def test_negative_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            end_disposition(10.0, -5.0)


class UpratingTests(unittest.TestCase):
    def test_absent_claim_earns_nothing(self):
        credit, findings = uprating_credit(None)
        self.assertAlmostEqual(credit, 0.0, places=9)
        self.assertEqual(findings, [])

    def test_unevidenced_claim_earns_nothing_and_is_reported(self):
        credit, findings = uprating_credit(
            {"state": "uprating-claimed-without-evaluation", "extension_k": 10.0, "ends": ["hot"]}
        )
        self.assertAlmostEqual(credit, 0.0, places=9)
        self.assertIn("uprating-claimed-without-evaluation", findings)

    def test_evidenced_claim_earns_its_extension_and_still_reports(self):
        credit, findings = uprating_credit(
            {"state": "uprating-evaluated-and-approved", "extension_k": 10.0, "ends": ["hot"]}
        )
        self.assertAlmostEqual(credit, 10.0, places=9)
        self.assertIn("uprating-credit-taken", findings)

    def test_claim_past_the_bound_is_capped(self):
        credit, findings = uprating_credit(
            {
                "state": "uprating-evaluated-and-approved",
                "extension_k": MAX_UPRATING_EXTENSION_K * 2.0,
                "ends": ["hot"],
            }
        )
        self.assertAlmostEqual(credit, MAX_UPRATING_EXTENSION_K, places=9)
        self.assertIn("uprating-extension-beyond-bound", findings)

    def test_claim_naming_no_end_rejected(self):
        with self.assertRaises(ValueError):
            normalize_uprating({"state": "uprating-evaluated-and-approved", "extension_k": 5.0})

    def test_unknown_uprating_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_uprating({"state": "uprating-probably-fine", "ends": ["hot"]})

    def test_repeated_end_rejected(self):
        with self.assertRaises(ValueError):
            normalize_uprating(
                {
                    "state": "uprating-evaluated-and-approved",
                    "extension_k": 5.0,
                    "ends": ["hot", "hot"],
                }
            )


class MountingRepairTests(unittest.TestCase):
    def test_absent_repair_earns_nothing(self):
        credit, findings = mounting_repair_credit(None)
        self.assertAlmostEqual(credit, 0.0, places=9)
        self.assertEqual(findings, [])

    def test_unapproved_repair_earns_nothing_and_is_reported(self):
        credit, findings = mounting_repair_credit(
            {"state": "mounting-repair-claimed-without-approval", "credit_k": 6.0}
        )
        self.assertAlmostEqual(credit, 0.0, places=9)
        self.assertIn("mounting-repair-claimed-without-approval", findings)

    def test_approved_repair_earns_its_credit(self):
        credit, findings = mounting_repair_credit(
            {"state": "mounting-repair-approved", "credit_k": 6.0}
        )
        self.assertAlmostEqual(credit, 6.0, places=9)
        self.assertIn("hot-end-mounting-repair-credit-taken", findings)

    def test_repair_past_the_bound_is_capped(self):
        credit, findings = mounting_repair_credit(
            {
                "state": "mounting-repair-approved",
                "credit_k": MAX_HOT_END_MOUNTING_CREDIT_K * 3.0,
            }
        )
        self.assertAlmostEqual(credit, MAX_HOT_END_MOUNTING_CREDIT_K, places=9)
        self.assertIn("mounting-repair-credit-beyond-bound", findings)

    def test_a_cold_end_mounting_repair_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_mounting_repair({"state": "mounting-repair-approved", "end": "cold"})

    def test_unknown_mounting_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_mounting_repair({"state": "mounting-repair-maybe"})


class AssessmentTests(unittest.TestCase):
    def test_comfortable_part_covers_the_application_cleanly(self):
        result = assess_temperature_range("U1", INDUSTRIAL, -20.0, 60.0, 5.0)
        self.assertEqual(result["verdict"], "rated-range-covers-application")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["usable_at_class_3"])

    def test_uncertainty_can_turn_a_covered_part_short(self):
        result = assess_temperature_range("U2", INDUSTRIAL, -20.0, 78.0, 5.0)
        self.assertEqual(result["ends"]["hot"]["disposition"], "end-margin-short")
        self.assertEqual(result["verdict"], "rated-range-margin-short")

    def test_an_end_outside_the_band_is_not_covering(self):
        result = assess_temperature_range("U3", INDUSTRIAL, -20.0, 95.0, 0.0)
        self.assertEqual(result["verdict"], "rated-range-not-covering-application")
        self.assertEqual(result["ends"]["hot"]["disposition"], "end-not-covered")

    def test_correlated_model_buys_a_short_hot_end_back(self):
        short = assess_temperature_range("U4", INDUSTRIAL, -20.0, 74.0, 10.0)
        correlated = assess_temperature_range(
            "U4", INDUSTRIAL, -20.0, 74.0, 10.0, "model-correlated-by-thermal-balance-test"
        )
        self.assertEqual(short["verdict"], "rated-range-margin-short")
        self.assertEqual(correlated["verdict"], "rated-range-covers-application")

    def test_approved_mounting_repair_pulls_the_hot_extreme_in(self):
        result = assess_temperature_range(
            "U5",
            INDUSTRIAL,
            -20.0,
            78.0,
            5.0,
            "model-uncorrelated",
            None,
            {"state": "mounting-repair-approved", "credit_k": 6.0},
        )
        self.assertAlmostEqual(result["credited_mounting_k"], 6.0, places=9)
        self.assertAlmostEqual(result["application_hot_extreme_c"], 77.0, places=9)

    def test_mounting_repair_leaves_a_finding_even_when_it_covers(self):
        result = assess_temperature_range(
            "U6",
            INDUSTRIAL,
            -20.0,
            78.0,
            5.0,
            "model-uncorrelated",
            None,
            {"state": "mounting-repair-approved", "credit_k": 6.0},
        )
        self.assertEqual(result["verdict"], "rated-range-covers-application")
        self.assertFalse(result["usable_at_class_3"])

    def test_evidenced_uprating_extends_the_named_end_only(self):
        result = assess_temperature_range(
            "U7",
            INDUSTRIAL,
            -20.0,
            95.0,
            0.0,
            "model-uncorrelated",
            {"state": "uprating-evaluated-and-approved", "extension_k": 20.0, "ends": ["hot"]},
        )
        self.assertAlmostEqual(result["effective_rated_max_c"], 105.0, places=9)
        self.assertAlmostEqual(result["effective_rated_min_c"], -40.0, places=9)
        self.assertEqual(result["verdict"], "rated-range-covers-application")

    def test_unevidenced_uprating_does_not_move_the_band(self):
        result = assess_temperature_range(
            "U8",
            INDUSTRIAL,
            -20.0,
            95.0,
            0.0,
            "model-uncorrelated",
            {"state": "uprating-claimed-without-evaluation", "extension_k": 20.0, "ends": ["hot"]},
        )
        self.assertAlmostEqual(result["effective_rated_max_c"], 85.0, places=9)
        self.assertEqual(result["verdict"], "rated-range-not-covering-application")

    def test_cold_end_is_graded_separately_from_the_hot_one(self):
        result = assess_temperature_range("U9", INDUSTRIAL, -50.0, 60.0, 0.0)
        self.assertEqual(result["ends"]["cold"]["disposition"], "end-not-covered")
        self.assertEqual(result["ends"]["hot"]["disposition"], "end-covered-with-margin")

    def test_shortfalls_lead_with_the_worst_end(self):
        result = assess_temperature_range("U10", INDUSTRIAL, -50.0, 83.0, 0.0)
        self.assertEqual(result["shortfalls"][0]["end"], "cold")

    def test_zero_margin_end_is_reported_short(self):
        result = assess_temperature_range("U11", INDUSTRIAL, -20.0, 85.0, 0.0)
        self.assertAlmostEqual(result["ends"]["hot"]["margin_k"], 0.0, places=9)
        self.assertEqual(result["verdict"], "rated-range-margin-short")

    def test_empty_part_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_temperature_range("  ", INDUSTRIAL, -20.0, 60.0, 5.0)

    def test_unknown_grade_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_temperature_range(
                "U12", {"temperature_grade": "hopeful-grade"}, -20.0, 60.0, 5.0
            )

    def test_declared_and_effective_uncertainty_are_both_reported(self):
        result = assess_temperature_range(
            "U13", INDUSTRIAL, -20.0, 60.0, 10.0, "model-correlated-by-thermal-balance-test"
        )
        self.assertAlmostEqual(result["declared_uncertainty_k"], 10.0, places=9)
        self.assertAlmostEqual(result["effective_uncertainty_k"], 5.0, places=9)


if __name__ == "__main__":
    unittest.main()
