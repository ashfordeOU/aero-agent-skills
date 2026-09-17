"""Contract tests for the clause 6.2.3.4 Class 3 evaluation-testing logic."""

import unittest

from q60_class_3_evaluation_testing_logic import (
    CONDITION_SENSES,
    DEFAULT_ACCEPTANCE_NUMBER,
    DEFAULT_OVER_TEST_FACTOR,
    GUARANTEED_LIMIT_SOURCES,
    LIMIT_SOURCES,
    LIMIT_TOLERANCE,
    MANDATORY_TEST_METHODS,
    SEVERITY_TOLERANCE,
    TESTING_FAILED,
    TESTING_INCOMPLETE,
    TESTING_PASSED,
    acceptance_decision,
    assess_condition,
    assess_evaluation_test_programme,
    assess_test_method,
    demanded_severity,
    missing_methods,
    normalize_method_name,
    reading_within_limits,
    severity_met,
    validate_acceptance_limits,
    validate_condition_sense,
    validate_over_test_factor,
)

GOOD_LIMITS = {"lower": 18.0, "upper": 22.0, "source": "project-specification"}


def _methods():
    return [
        {
            "name": "electrical-characterization",
            "conditions": {"temperature_c": 25.0},
            "mission_requirements": {
                "temperature_c": {"mission_value": 25.0, "over_test_factor": 1.0}
            },
            "readings": [
                {"parameter": "supply-current-ma", "value": 20.0,
                 "limits": dict(GOOD_LIMITS)},
                {"parameter": "input-leakage-na", "value": 5.0,
                 "limits": {"lower": 0.0, "upper": 10.0,
                            "source": "manufacturer-datasheet-limit"}},
            ],
            "sample_size": 10,
            "failures": 0,
        },
        {
            "name": "temperature-cycling",
            "conditions": {"cycles": 220.0, "low_temperature_c": -60.5,
                           "high_temperature_c": 137.5},
            "mission_requirements": {
                "cycles": {"mission_value": 200.0},
                "low_temperature_c": {"mission_value": -55.0, "sense": "at-most"},
                "high_temperature_c": {"mission_value": 125.0},
            },
            "sample_size": 12,
            "failures": 0,
        },
        {
            "name": "operating-life",
            "conditions": {"duration_h": 2200.0, "temperature_c": 137.5},
            "mission_requirements": {
                "duration_h": {"mission_value": 2000.0},
                "temperature_c": {"mission_value": 125.0},
            },
            "sample_size": 10,
            "failures": 0,
        },
        {
            "name": "mechanical-robustness",
            "conditions": {"shock_g": 1650.0},
            "mission_requirements": {"shock_g": {"mission_value": 1500.0}},
            "sample_size": 10,
            "failures": 0,
        },
    ]


def _spec(**overrides):
    spec = {
        "manufacturer": "Example Semiconductor",
        "part_number": "EX-9930-C3",
        "defaults": {
            "over_test_factor": DEFAULT_OVER_TEST_FACTOR,
            "required_sample_size": 10,
            "acceptance_number": DEFAULT_ACCEPTANCE_NUMBER,
        },
        "methods": _methods(),
    }
    spec.update(overrides)
    return spec


class MethodNameTests(unittest.TestCase):
    def test_underscores_and_case_fold_onto_hyphens(self):
        self.assertEqual(normalize_method_name("Operating_Life"), "operating-life")

    def test_spaces_fold_onto_hyphens(self):
        self.assertEqual(
            normalize_method_name("  Temperature  Cycling "), "temperature-cycling"
        )

    def test_blank_method_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_method_name("   ")

    def test_every_mandatory_method_is_already_normalized(self):
        for name in MANDATORY_TEST_METHODS:
            self.assertEqual(normalize_method_name(name), name)


class OverTestFactorTests(unittest.TestCase):
    def test_unity_factor_is_allowed(self):
        self.assertAlmostEqual(validate_over_test_factor(1.0), 1.0, places=9)

    def test_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_over_test_factor(0.9)

    def test_non_numeric_factor_rejected(self):
        with self.assertRaises(ValueError):
            validate_over_test_factor("1.1")

    def test_default_factor_opens_the_condition_out(self):
        self.assertGreater(DEFAULT_OVER_TEST_FACTOR, 1.0)


class DemandedSeverityTests(unittest.TestCase):
    def test_an_upward_condition_is_raised(self):
        self.assertAlmostEqual(
            demanded_severity(200.0, "at-least", 1.10), 220.0, places=9
        )

    def test_a_downward_condition_is_pushed_colder(self):
        self.assertAlmostEqual(
            demanded_severity(-55.0, "at-most", 1.10), -60.5, places=9
        )

    def test_a_unity_factor_demands_the_mission_value_itself(self):
        self.assertAlmostEqual(
            demanded_severity(1500.0, "at-least", 1.0), 1500.0, places=9
        )

    def test_a_negative_upward_condition_still_opens_out(self):
        self.assertAlmostEqual(
            demanded_severity(-10.0, "at-least", 1.20), -8.0, places=9
        )

    def test_unknown_sense_rejected(self):
        with self.assertRaises(ValueError):
            demanded_severity(200.0, "roughly", 1.10)

    def test_both_senses_are_published(self):
        self.assertEqual(set(CONDITION_SENSES), {"at-least", "at-most"})

    def test_severity_tolerance_is_representation_sized_only(self):
        self.assertLess(SEVERITY_TOLERANCE, 1e-6)
        self.assertLess(LIMIT_TOLERANCE, 1e-6)


class SeverityMetTests(unittest.TestCase):
    def test_exactly_the_demanded_upward_severity_is_met(self):
        self.assertTrue(severity_met(220.0, 220.0, "at-least"))

    def test_exactly_the_demanded_downward_severity_is_met(self):
        self.assertTrue(severity_met(-60.5, -60.5, "at-most"))

    def test_a_shortfall_upward_is_not_met(self):
        self.assertFalse(severity_met(150.0, 220.0, "at-least"))

    def test_a_warmer_soak_than_demanded_is_not_met(self):
        self.assertFalse(severity_met(-40.0, -60.5, "at-most"))

    def test_a_built_condition_lands_on_its_demand(self):
        demanded = demanded_severity(200.0, "at-least", 1.10)
        self.assertTrue(severity_met(220.0, demanded, "at-least"))

    def test_condition_sense_validator_rejects_a_blank(self):
        with self.assertRaises(ValueError):
            validate_condition_sense(" ")


class ConditionTests(unittest.TestCase):
    def test_a_covered_condition_is_met(self):
        record = assess_condition(
            "cycles", 220.0, {"mission_value": 200.0, "over_test_factor": 1.10}
        )
        self.assertTrue(record["met"])

    def test_a_condition_carries_its_demanded_value(self):
        record = assess_condition(
            "cycles", 260.0, {"mission_value": 200.0, "over_test_factor": 1.10}
        )
        self.assertAlmostEqual(record["demanded"], 220.0, places=9)

    def test_sense_defaults_to_at_least(self):
        record = assess_condition("cycles", 300.0, {"mission_value": 200.0})
        self.assertEqual(record["sense"], "at-least")

    def test_requirement_without_a_mission_value_rejected(self):
        with self.assertRaises(ValueError):
            assess_condition("cycles", 300.0, {"sense": "at-least"})

    def test_non_mapping_requirement_rejected(self):
        with self.assertRaises(ValueError):
            assess_condition("cycles", 300.0, 200.0)


class AcceptanceLimitTests(unittest.TestCase):
    def test_a_project_limit_is_guaranteed(self):
        band = validate_acceptance_limits(GOOD_LIMITS)
        self.assertTrue(band["guaranteed"])

    def test_a_typical_column_is_not_guaranteed(self):
        band = validate_acceptance_limits(
            {"lower": 18.0, "upper": 22.0,
             "source": "manufacturer-datasheet-typical"}
        )
        self.assertFalse(band["guaranteed"])

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_limits(
                {"lower": 22.0, "upper": 18.0, "source": "project-specification"}
            )

    def test_collapsed_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_limits(
                {"lower": 20.0, "upper": 20.0, "source": "project-specification"}
            )

    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_limits(
                {"lower": 18.0, "upper": 22.0, "source": "an-applications-engineer"}
            )

    def test_missing_source_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_limits({"lower": 18.0, "upper": 22.0})

    def test_every_guaranteed_source_is_a_published_source(self):
        for source in GUARANTEED_LIMIT_SOURCES:
            self.assertIn(source, LIMIT_SOURCES)

    def test_a_reading_on_the_upper_edge_is_inside(self):
        self.assertTrue(reading_within_limits(22.0, GOOD_LIMITS))

    def test_a_reading_on_the_lower_edge_is_inside(self):
        self.assertTrue(reading_within_limits(18.0, GOOD_LIMITS))

    def test_a_reading_above_the_band_is_outside(self):
        self.assertFalse(reading_within_limits(23.0, GOOD_LIMITS))


class AcceptanceDecisionTests(unittest.TestCase):
    def test_a_full_sample_with_no_failure_is_accepted(self):
        decision = acceptance_decision(10, 0, 10, 0)
        self.assertTrue(decision["accepted"])

    def test_one_failure_against_accept_on_zero_is_rejected(self):
        decision = acceptance_decision(10, 1, 10, 0)
        self.assertFalse(decision["within_acceptance_number"])
        self.assertFalse(decision["accepted"])

    def test_a_short_sample_is_not_accepted_even_with_no_failure(self):
        decision = acceptance_decision(4, 0, 10, 0)
        self.assertFalse(decision["sample_size_met"])
        self.assertFalse(decision["accepted"])

    def test_a_failure_inside_a_raised_acceptance_number_is_accepted(self):
        decision = acceptance_decision(20, 1, 20, 2)
        self.assertTrue(decision["accepted"])

    def test_more_failures_than_parts_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_decision(10, 11, 10, 0)

    def test_an_acceptance_number_that_accepts_everything_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_decision(10, 0, 10, 10)

    def test_zero_sample_size_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_decision(0, 0, 10, 0)

    def test_fractional_sample_size_rejected(self):
        with self.assertRaises(ValueError):
            acceptance_decision(10.5, 0, 10, 0)


class TestMethodTests(unittest.TestCase):
    def test_a_clean_method_passes(self):
        record = assess_test_method(_methods()[1], {"required_sample_size": 10})
        self.assertTrue(record["passed"])
        self.assertEqual(record["findings"], [])

    def test_an_unapplied_required_condition_is_a_hole_of_its_own(self):
        method = _methods()[1]
        del method["conditions"]["high_temperature_c"]
        record = assess_test_method(method, {"required_sample_size": 10})
        self.assertFalse(record["conditions_met"])
        self.assertFalse(record["rejected"])

    def test_an_under_severe_condition_does_not_reject_the_part(self):
        method = _methods()[3]
        method["conditions"]["shock_g"] = 1500.0
        record = assess_test_method(method, {"required_sample_size": 10})
        self.assertFalse(record["passed"])
        self.assertFalse(record["rejected"])

    def test_a_reading_outside_its_band_rejects_the_method(self):
        method = _methods()[0]
        method["readings"][0]["value"] = 30.0
        record = assess_test_method(method, {"required_sample_size": 10})
        self.assertTrue(record["rejected"])

    def test_a_typical_column_limit_blocks_the_pass_without_rejecting(self):
        method = _methods()[0]
        method["readings"][0]["limits"]["source"] = "manufacturer-datasheet-typical"
        record = assess_test_method(method, {"required_sample_size": 10})
        self.assertFalse(record["limits_guaranteed"])
        self.assertFalse(record["passed"])
        self.assertFalse(record["rejected"])

    def test_the_same_parameter_measured_twice_rejected(self):
        method = _methods()[0]
        method["readings"].append(dict(method["readings"][0]))
        with self.assertRaises(ValueError):
            assess_test_method(method, {"required_sample_size": 10})

    def test_readings_must_be_a_sequence(self):
        method = _methods()[0]
        method["readings"] = {"parameter": "supply-current-ma"}
        with self.assertRaises(ValueError):
            assess_test_method(method, {"required_sample_size": 10})

    def test_a_malformed_mission_requirement_rejected(self):
        method = _methods()[3]
        method["mission_requirements"]["shock_g"] = 1500.0
        with self.assertRaises(ValueError):
            assess_test_method(method, {"required_sample_size": 10})

    def test_condition_and_acceptance_findings_both_surface(self):
        method = _methods()[3]
        method["conditions"]["shock_g"] = 1000.0
        method["failures"] = 1
        record = assess_test_method(method, {"required_sample_size": 10})
        self.assertEqual(len(record["findings"]), 2)


class ProgrammeTests(unittest.TestCase):
    def test_a_complete_campaign_passes(self):
        result = assess_evaluation_test_programme(_spec())
        self.assertEqual(result["verdict"], TESTING_PASSED)
        self.assertTrue(result["evaluated"])
        self.assertEqual(result["findings"], [])

    def test_a_mandatory_method_never_run_leaves_it_incomplete(self):
        methods = [m for m in _methods() if m["name"] != "operating-life"]
        result = assess_evaluation_test_programme(_spec(methods=methods))
        self.assertEqual(result["missing_methods"], ["operating-life"])
        self.assertEqual(result["verdict"], TESTING_INCOMPLETE)

    def test_missing_methods_keep_the_published_order(self):
        records = [{"name": "temperature-cycling"}]
        self.assertEqual(
            missing_methods(records),
            [n for n in MANDATORY_TEST_METHODS if n != "temperature-cycling"],
        )

    def test_missing_methods_rejects_a_malformed_record(self):
        with self.assertRaises(ValueError):
            missing_methods([{"conditions": {}}])

    def test_a_failure_count_over_the_acceptance_number_fails_the_campaign(self):
        methods = _methods()
        methods[2]["failures"] = 1
        result = assess_evaluation_test_programme(_spec(methods=methods))
        self.assertEqual(result["verdict"], TESTING_FAILED)
        self.assertEqual(result["rejected_methods"], ["operating-life"])

    def test_a_failure_outranks_a_missing_method(self):
        methods = [m for m in _methods() if m["name"] != "operating-life"]
        methods[0]["failures"] = 1
        result = assess_evaluation_test_programme(_spec(methods=methods))
        self.assertEqual(result["verdict"], TESTING_FAILED)

    def test_a_thin_sample_leaves_the_campaign_incomplete(self):
        methods = _methods()
        methods[3]["sample_size"] = 3
        result = assess_evaluation_test_programme(_spec(methods=methods))
        self.assertEqual(result["verdict"], TESTING_INCOMPLETE)

    def test_a_duplicate_method_declaration_rejected(self):
        methods = _methods() + [_methods()[0]]
        with self.assertRaises(ValueError):
            assess_evaluation_test_programme(_spec(methods=methods))

    def test_an_empty_method_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_evaluation_test_programme(_spec(methods=[]))

    def test_a_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_evaluation_test_programme(["EX-9930-C3"])

    def test_a_blank_part_number_rejected(self):
        with self.assertRaises(ValueError):
            assess_evaluation_test_programme(_spec(part_number=" "))

    def test_every_shortfall_is_named_not_only_the_first(self):
        methods = [m for m in _methods() if m["name"] != "mechanical-robustness"]
        methods[1]["conditions"]["cycles"] = 100.0
        methods[2]["sample_size"] = 2
        result = assess_evaluation_test_programme(_spec(methods=methods))
        self.assertGreaterEqual(len(result["findings"]), 3)


if __name__ == "__main__":
    unittest.main()
