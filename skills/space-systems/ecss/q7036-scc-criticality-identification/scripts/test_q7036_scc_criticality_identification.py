"""Contract tests for the SCC-critical application identification logic."""

import unittest

from q7036_scc_criticality_identification_logic import (
    RATIO_TOLERANCE,
    STRESS_RATIO_FLOOR,
    SUSTAINED_HOURS_MIN,
    alloy_condition_met,
    assess_criticality,
    coexisting_conditions,
    environment_condition_met,
    grade_application,
    normalize_category,
    normalize_consequence,
    normalize_severity,
    required_actions,
    stress_condition_met,
)


def application(app_id="a1", **overrides):
    record = {
        "id": app_id,
        "resistance_category": "low",
        "stress_ratio": 0.45,
        "sustained_hours": 8760.0,
        "environment_severity": "severe",
        "failure_consequence": "catastrophic",
        "redundant": False,
    }
    record.update(overrides)
    return record


class NormalizationTests(unittest.TestCase):
    def test_category_alias(self):
        self.assertEqual(normalize_category("Susceptible"), "low")

    def test_category_unknown_rejected(self):
        with self.assertRaises(ValueError):
            normalize_category("very-high")

    def test_category_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalize_category(3)

    def test_severity_alias(self):
        self.assertEqual(normalize_severity("Aggressive"), "severe")

    def test_severity_blank_rejected(self):
        with self.assertRaises(ValueError):
            normalize_severity("  ")

    def test_consequence_alias(self):
        self.assertEqual(normalize_consequence("loss of mission"), "catastrophic")

    def test_consequence_unknown_rejected(self):
        with self.assertRaises(ValueError):
            normalize_consequence("cosmetic")


class ConditionTests(unittest.TestCase):
    def test_low_rated_alloy_counts(self):
        self.assertTrue(alloy_condition_met("low"))

    def test_medium_rated_alloy_counts(self):
        self.assertTrue(alloy_condition_met("medium"))

    def test_high_rated_alloy_does_not_count(self):
        self.assertFalse(alloy_condition_met("high"))

    def test_sustained_stress_above_both_boundaries(self):
        self.assertTrue(stress_condition_met(0.4, 1000.0))

    def test_stress_exactly_on_the_ratio_floor_counts(self):
        self.assertAlmostEqual(STRESS_RATIO_FLOOR, 0.10, places=9)
        self.assertTrue(stress_condition_met(STRESS_RATIO_FLOOR, 1000.0))

    def test_duration_exactly_on_the_sustained_boundary_counts(self):
        self.assertAlmostEqual(SUSTAINED_HOURS_MIN, 24.0, places=9)
        self.assertTrue(stress_condition_met(0.4, SUSTAINED_HOURS_MIN))

    def test_stress_below_the_floor_does_not_count(self):
        self.assertFalse(stress_condition_met(0.05, 1000.0))

    def test_transient_load_does_not_count(self):
        self.assertFalse(stress_condition_met(0.4, 2.0))

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            stress_condition_met(0.4, -5.0)

    def test_ratio_given_in_megapascals_rejected(self):
        with self.assertRaises(ValueError):
            stress_condition_met(310.0, 1000.0)

    def test_boolean_ratio_rejected(self):
        with self.assertRaises(ValueError):
            stress_condition_met(True, 1000.0)

    def test_moderate_environment_counts(self):
        self.assertTrue(environment_condition_met("moderate"))

    def test_benign_environment_does_not_count(self):
        self.assertFalse(environment_condition_met("dry"))

    def test_tolerance_is_tight(self):
        self.assertLess(RATIO_TOLERANCE, 1e-6)


class CoexistenceTests(unittest.TestCase):
    def test_all_three_present(self):
        conditions = coexisting_conditions(application())
        self.assertEqual(
            conditions, {"alloy": True, "stress": True, "environment": True}
        )

    def test_missing_key_rejected(self):
        record = application()
        del record["environment_severity"]
        with self.assertRaises(ValueError):
            coexisting_conditions(record)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            coexisting_conditions(["a1"])


class GradingTests(unittest.TestCase):
    def test_all_conditions_and_catastrophic_is_critical(self):
        record = grade_application(application())
        self.assertEqual(record["grade"], "scc-critical")
        self.assertEqual(record["absent_conditions"], [])

    def test_redundant_load_path_is_monitored_not_critical(self):
        record = grade_application(application(redundant=True))
        self.assertEqual(record["grade"], "scc-monitored")

    def test_minor_consequence_is_monitored(self):
        record = grade_application(application(failure_consequence="minor"))
        self.assertEqual(record["grade"], "scc-monitored")

    def test_resistant_alloy_clears_the_application(self):
        record = grade_application(application(resistance_category="high"))
        self.assertEqual(record["grade"], "not-scc-critical")
        self.assertEqual(record["absent_conditions"], ["alloy"])

    def test_benign_environment_clears_the_application(self):
        record = grade_application(application(environment_severity="benign"))
        self.assertEqual(record["absent_conditions"], ["environment"])

    def test_transient_load_clears_the_application(self):
        record = grade_application(application(sustained_hours=1.0))
        self.assertEqual(record["absent_conditions"], ["stress"])

    def test_two_absent_conditions_are_both_named(self):
        record = grade_application(
            application(resistance_category="high", environment_severity="benign")
        )
        self.assertEqual(record["absent_conditions"], ["alloy", "environment"])

    def test_critical_grade_owes_four_actions(self):
        self.assertEqual(len(required_actions("scc-critical")), 4)

    def test_cleared_grade_owes_one_action(self):
        self.assertEqual(len(required_actions("not-scc-critical")), 1)

    def test_unknown_grade_rejected(self):
        with self.assertRaises(ValueError):
            required_actions("probably-fine")

    def test_blank_application_id_rejected(self):
        with self.assertRaises(ValueError):
            grade_application(application(""))


class AssessmentTests(unittest.TestCase):
    def test_mixed_population_is_counted(self):
        result = assess_criticality(
            [
                application("a"),
                application("b", redundant=True),
                application("c", resistance_category="high"),
            ]
        )
        self.assertEqual(result["critical_count"], 1)
        self.assertEqual(result["monitored_count"], 1)
        self.assertEqual(result["cleared_count"], 1)

    def test_findings_name_every_critical_application(self):
        result = assess_criticality([application("a"), application("b")])
        self.assertEqual(len(result["findings"]), 2)
        self.assertTrue(result["any_critical"])

    def test_clean_population_has_no_findings(self):
        result = assess_criticality([application("a", environment_severity="benign")])
        self.assertEqual(result["findings"], [])
        self.assertFalse(result["any_critical"])

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_criticality([application("a"), application("a")])

    def test_empty_population_rejected(self):
        with self.assertRaises(ValueError):
            assess_criticality([])


if __name__ == "__main__":
    unittest.main()
