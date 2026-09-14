"""Contract test for the ECSS-Q-ST-60-13C clause 5.2.2.6 Class 2 range leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6013_class_2_temperature_range.py
"""

import unittest

from q6013_class_2_temperature_range_logic import (
    CLASS_2_END_MARGIN_K,
    ENDS,
    END_DISPOSITIONS,
    MARGIN_TOLERANCE,
    MAX_UPRATING_EXTENSION_K,
    TEMPERATURE_GRADE_BANDS,
    UPRATING_STATES,
    VERDICTS,
    assess_temperature_range,
    end_disposition,
    end_margin,
    grade_band,
    normalize_uprating,
    rated_limits,
    uprating_credit,
    widened_mission_extremes,
)


class GradeBandTests(unittest.TestCase):
    def test_every_grade_band_runs_cold_to_hot(self):
        for grade, (low, high) in TEMPERATURE_GRADE_BANDS.items():
            self.assertLess(low, high, grade)

    def test_industrial_grade_is_wider_than_commercial_grade(self):
        commercial = grade_band("commercial-grade")
        industrial = grade_band("industrial-grade")
        self.assertLess(industrial[0], commercial[0])
        self.assertGreater(industrial[1], commercial[1])

    def test_unknown_grade_rejected(self):
        with self.assertRaises(ValueError):
            grade_band("space-grade-probably")


class RatedLimitTests(unittest.TestCase):
    def test_a_grade_resolves_to_its_band(self):
        self.assertEqual(
            rated_limits({"temperature_grade": "industrial-grade"}),
            TEMPERATURE_GRADE_BANDS["industrial-grade"],
        )

    def test_explicit_limits_are_taken_as_declared(self):
        self.assertEqual(
            rated_limits({"rated_min_c": -20.0, "rated_max_c": 90.0}), (-20.0, 90.0)
        )

    def test_a_grade_and_explicit_limits_together_are_rejected(self):
        with self.assertRaises(ValueError):
            rated_limits(
                {
                    "temperature_grade": "industrial-grade",
                    "rated_min_c": -20.0,
                    "rated_max_c": 90.0,
                }
            )

    def test_a_part_with_no_band_at_all_is_rejected(self):
        with self.assertRaises(ValueError):
            rated_limits({"part_number": "cots-op-amp"})

    def test_inverted_explicit_limits_rejected(self):
        with self.assertRaises(ValueError):
            rated_limits({"rated_min_c": 90.0, "rated_max_c": -20.0})

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            rated_limits("industrial-grade")


class MissionExtremeTests(unittest.TestCase):
    def test_uncertainty_widens_both_ends(self):
        cold, hot = widened_mission_extremes(-20.0, 60.0, 5.0)
        self.assertAlmostEqual(cold, -25.0, places=9)
        self.assertAlmostEqual(hot, 65.0, places=9)

    def test_zero_uncertainty_leaves_the_prediction_alone(self):
        self.assertEqual(widened_mission_extremes(-20.0, 60.0, 0.0), (-20.0, 60.0))

    def test_negative_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            widened_mission_extremes(-20.0, 60.0, -1.0)

    def test_inverted_mission_case_rejected(self):
        with self.assertRaises(ValueError):
            widened_mission_extremes(60.0, -20.0, 5.0)

    def test_non_numeric_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            widened_mission_extremes(-20.0, 60.0, "five")

    def test_boolean_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            widened_mission_extremes(-20.0, 60.0, True)


class EndMarginTests(unittest.TestCase):
    def test_cold_end_margin_counts_down_from_the_case(self):
        self.assertAlmostEqual(end_margin("cold", -40.0, -25.0), 15.0, places=9)

    def test_hot_end_margin_counts_up_from_the_case(self):
        self.assertAlmostEqual(end_margin("hot", 85.0, 65.0), 20.0, places=9)

    def test_a_case_beyond_the_rated_limit_gives_a_negative_margin(self):
        self.assertAlmostEqual(end_margin("hot", 70.0, 80.0), -10.0, places=9)

    def test_unknown_end_rejected(self):
        with self.assertRaises(ValueError):
            end_margin("lukewarm", 70.0, 60.0)


class EndDispositionTests(unittest.TestCase):
    def test_a_margin_exactly_at_the_requirement_is_covered(self):
        self.assertEqual(
            end_disposition(CLASS_2_END_MARGIN_K), "end-covered-with-margin"
        )

    def test_a_margin_inside_the_band_but_short_is_a_finding(self):
        self.assertEqual(end_disposition(4.0), "end-margin-short")

    def test_a_zero_margin_is_short_not_covered(self):
        self.assertEqual(end_disposition(0.0), "end-margin-short")

    def test_a_negative_margin_is_not_covered(self):
        self.assertEqual(end_disposition(-0.5), "end-not-covered")

    def test_every_disposition_name_is_one_the_module_publishes(self):
        seen = {end_disposition(20.0), end_disposition(4.0), end_disposition(-4.0)}
        self.assertEqual(seen, set(END_DISPOSITIONS))

    def test_negative_requirement_rejected(self):
        with self.assertRaises(ValueError):
            end_disposition(5.0, -1.0)


class UpratingTests(unittest.TestCase):
    def test_an_absent_declaration_claims_nothing(self):
        declared = normalize_uprating(None)
        self.assertEqual(declared["state"], "uprating-not-claimed")
        self.assertEqual(declared["ends"], ())

    def test_every_published_state_is_accepted(self):
        for state in UPRATING_STATES:
            raw = {"state": state, "extension_k": 5.0, "ends": ["hot"]}
            self.assertEqual(normalize_uprating(raw)["state"], state)

    def test_a_claim_naming_no_end_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_uprating(
                {"state": "uprating-evaluated-and-approved", "extension_k": 5.0}
            )

    def test_a_repeated_end_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_uprating(
                {
                    "state": "uprating-evaluated-and-approved",
                    "extension_k": 5.0,
                    "ends": ["hot", "hot"],
                }
            )

    def test_an_unevidenced_claim_earns_no_extension(self):
        credited, findings = uprating_credit(
            {
                "state": "uprating-claimed-without-evaluation",
                "extension_k": 10.0,
                "ends": ["hot"],
            }
        )
        self.assertAlmostEqual(credited, 0.0, places=9)
        self.assertIn("uprating-claimed-without-evaluation", findings)

    def test_an_evidenced_claim_earns_its_extension_and_still_reports(self):
        credited, findings = uprating_credit(
            {
                "state": "uprating-evaluated-and-approved",
                "extension_k": 10.0,
                "ends": ["hot"],
            }
        )
        self.assertAlmostEqual(credited, 10.0, places=9)
        self.assertIn("uprating-credit-taken", findings)

    def test_an_extension_at_the_bound_is_credited_whole(self):
        credited, findings = uprating_credit(
            {
                "state": "uprating-evaluated-and-approved",
                "extension_k": MAX_UPRATING_EXTENSION_K,
                "ends": ["hot"],
            }
        )
        self.assertAlmostEqual(credited, MAX_UPRATING_EXTENSION_K, places=9)
        self.assertNotIn("uprating-extension-beyond-bound", findings)

    def test_an_extension_past_the_bound_is_capped_and_reported(self):
        credited, findings = uprating_credit(
            {
                "state": "uprating-evaluated-and-approved",
                "extension_k": MAX_UPRATING_EXTENSION_K + 10.0,
                "ends": ["hot"],
            }
        )
        self.assertAlmostEqual(credited, MAX_UPRATING_EXTENSION_K, places=9)
        self.assertIn("uprating-extension-beyond-bound", findings)

    def test_a_string_of_ends_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_uprating(
                {"state": "uprating-evaluated-and-approved", "extension_k": 5.0, "ends": "hot"}
            )


class AssessmentTests(unittest.TestCase):
    def test_a_band_with_margin_at_both_ends_is_usable(self):
        report = assess_temperature_range(
            "cots-op-amp-01",
            {"temperature_grade": "industrial-grade"},
            -20.0,
            60.0,
            5.0,
        )
        self.assertEqual(report["verdict"], "rated-range-covers-mission")
        self.assertTrue(report["usable_at_class_2"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["shortfalls"], [])

    def test_a_hot_end_exactly_on_the_required_margin_still_covers(self):
        report = assess_temperature_range(
            "cots-op-amp-01",
            {"rated_min_c": -55.0, "rated_max_c": 85.0},
            -20.0,
            70.0,
            5.0,
        )
        self.assertAlmostEqual(
            report["ends"]["hot"]["margin_k"], CLASS_2_END_MARGIN_K, places=9
        )
        self.assertEqual(report["ends"]["hot"]["disposition"], "end-covered-with-margin")
        self.assertEqual(report["verdict"], "rated-range-covers-mission")

    def test_a_short_hot_margin_names_the_hot_end_only(self):
        report = assess_temperature_range(
            "cots-op-amp-01",
            {"temperature_grade": "industrial-grade"},
            -20.0,
            75.0,
            5.0,
        )
        self.assertEqual(report["verdict"], "rated-range-margin-short")
        self.assertFalse(report["usable_at_class_2"])
        self.assertEqual([row["end"] for row in report["shortfalls"]], ["hot"])
        self.assertIn("hot-end-margin-short", report["findings"])

    def test_a_cold_case_outside_the_band_is_not_covered(self):
        report = assess_temperature_range(
            "cots-op-amp-01",
            {"temperature_grade": "commercial-grade"},
            -30.0,
            50.0,
            5.0,
        )
        self.assertEqual(report["verdict"], "rated-range-not-covering-mission")
        self.assertEqual(report["ends"]["cold"]["disposition"], "end-not-covered")
        self.assertIn("cold-end-not-covered", report["findings"])

    def test_shortfalls_come_back_worst_first(self):
        report = assess_temperature_range(
            "cots-op-amp-01",
            {"rated_min_c": 0.0, "rated_max_c": 70.0},
            -10.0,
            66.0,
            0.0,
        )
        self.assertEqual([row["end"] for row in report["shortfalls"]], ["cold", "hot"])
        self.assertGreater(
            report["shortfalls"][0]["shortfall_k"], report["shortfalls"][1]["shortfall_k"]
        )

    def test_an_evidenced_uprating_rescues_the_hot_end(self):
        report = assess_temperature_range(
            "cots-op-amp-01",
            {"temperature_grade": "industrial-grade"},
            -20.0,
            85.0,
            5.0,
            uprating={
                "state": "uprating-evaluated-and-approved",
                "extension_k": 15.0,
                "ends": ["hot"],
            },
        )
        self.assertAlmostEqual(report["effective_rated_max_c"], 100.0, places=9)
        self.assertEqual(report["verdict"], "rated-range-covers-mission")
        self.assertIn("uprating-credit-taken", report["findings"])
        self.assertFalse(report["usable_at_class_2"])

    def test_an_unevidenced_uprating_rescues_nothing(self):
        report = assess_temperature_range(
            "cots-op-amp-01",
            {"temperature_grade": "industrial-grade"},
            -20.0,
            85.0,
            5.0,
            uprating={
                "state": "uprating-claimed-without-evaluation",
                "extension_k": 15.0,
                "ends": ["hot"],
            },
        )
        self.assertAlmostEqual(report["effective_rated_max_c"], 85.0, places=9)
        self.assertEqual(report["verdict"], "rated-range-not-covering-mission")
        self.assertIn("uprating-claimed-without-evaluation", report["findings"])

    def test_every_verdict_name_is_one_the_module_publishes(self):
        part = {"temperature_grade": "industrial-grade"}
        seen = {
            assess_temperature_range("p", part, -20.0, 60.0, 5.0)["verdict"],
            assess_temperature_range("p", part, -20.0, 75.0, 5.0)["verdict"],
            assess_temperature_range("p", part, -20.0, 90.0, 5.0)["verdict"],
        }
        self.assertEqual(seen, set(VERDICTS))

    def test_both_ends_are_always_graded(self):
        report = assess_temperature_range(
            "p", {"temperature_grade": "military-grade"}, -20.0, 60.0, 5.0
        )
        self.assertEqual(tuple(sorted(report["ends"])), tuple(sorted(ENDS)))

    def test_the_tolerance_absorbs_a_margin_a_hair_under_the_bound(self):
        self.assertEqual(
            end_disposition(CLASS_2_END_MARGIN_K - MARGIN_TOLERANCE / 2.0),
            "end-covered-with-margin",
        )

    def test_empty_part_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_temperature_range(
                "  ", {"temperature_grade": "industrial-grade"}, -20.0, 60.0, 5.0
            )

    def test_unknown_uprating_state_rejected(self):
        with self.assertRaises(ValueError):
            assess_temperature_range(
                "p",
                {"temperature_grade": "industrial-grade"},
                -20.0,
                60.0,
                5.0,
                uprating={"state": "we-think-it-is-fine", "ends": ["hot"]},
            )


if __name__ == "__main__":
    unittest.main()
