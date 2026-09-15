"""Contract tests for the clause 4.2.3.4 evaluation-programme logic."""

import unittest

from q60_class_1_evaluation_testing_logic import (
    CONDITION_SENSES,
    CONDITION_TOLERANCE,
    DRIFT_TOLERANCE,
    MANDATORY_STEPS,
    assess_conditions,
    assess_evaluation_programme,
    assess_measurement,
    assess_test_step,
    condition_met,
    missing_steps,
    normalize_step_name,
    parameter_drift_fraction,
    validate_applied_conditions,
    validate_candidate_part,
    validate_required_condition,
)

PART = {
    "manufacturer": "Example Microelectronics",
    "part_number": "EM-7712-CL1",
    "assurance_category": "class-1",
}


def _steps(**overrides):
    steps = [
        {"name": "visual-inspection", "conditions": {"magnification_x": 30.0},
         "required_conditions": {"magnification_x": {"value": 30.0, "sense": "at-least"}}},
        {"name": "electrical-measurement", "conditions": {"temperature_c": 25.0},
         "required_conditions": {"temperature_c": {"value": 25.0, "sense": "at-least"}},
         "measurements": [
             {"parameter": "input-leakage-na", "initial": 10.0, "final": 10.4,
              "drift_limit_fraction": 0.05},
             {"parameter": "supply-current-ma", "initial": 20.0, "final": 20.1,
              "lower_limit": 18.0, "upper_limit": 22.0},
         ]},
        {"name": "temperature-cycling",
         "conditions": {"cycles": 200.0, "low_temperature_c": -65.0,
                        "high_temperature_c": 150.0},
         "required_conditions": {
             "cycles": {"value": 200.0, "sense": "at-least"},
             "low_temperature_c": {"value": -55.0, "sense": "at-most"},
             "high_temperature_c": {"value": 125.0, "sense": "at-least"}}},
        {"name": "life-test",
         "conditions": {"duration_h": 2000.0, "temperature_c": 125.0},
         "required_conditions": {"duration_h": {"value": 2000.0, "sense": "at-least"},
                                 "temperature_c": {"value": 125.0, "sense": "at-least"}},
         "measurements": [
             {"parameter": "threshold-voltage-v", "initial": 1.0, "final": 1.02},
         ]},
        {"name": "mechanical-robustness", "conditions": {"shock_g": 1500.0},
         "required_conditions": {"shock_g": {"value": 1500.0, "sense": "at-least"}}},
    ]
    for key, patch in overrides.items():
        target = key.replace("_", "-")
        for step in steps:
            if step["name"] == target:
                step.update(patch)
    return steps


def _spec(**overrides):
    spec = {
        "part": dict(PART),
        "steps": _steps(),
        "default_drift_limit_fraction": 0.10,
    }
    spec.update(overrides)
    return spec


class CandidatePartTests(unittest.TestCase):
    def test_identity_returned(self):
        identity = validate_candidate_part(PART)
        self.assertEqual(identity["part_number"], "EM-7712-CL1")

    def test_category_normalized(self):
        identity = validate_candidate_part(dict(PART, assurance_category="Class 1"))
        self.assertEqual(identity["assurance_category"], "class-1")

    def test_blank_manufacturer_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate_part(dict(PART, manufacturer="  "))

    def test_missing_part_number_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate_part({"manufacturer": "Example",
                                     "assurance_category": "class-1"})

    def test_other_assurance_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate_part(dict(PART, assurance_category="class-2"))

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate_part(["Example", "EM-7712-CL1"])


class ConditionTests(unittest.TestCase):
    def test_step_name_normalized(self):
        self.assertEqual(normalize_step_name("Life_Test"), "life-test")

    def test_empty_condition_map_rejected(self):
        with self.assertRaises(ValueError):
            validate_applied_conditions({})

    def test_non_numeric_condition_rejected(self):
        with self.assertRaises(ValueError):
            validate_applied_conditions({"duration_h": "2000"})

    def test_boolean_condition_rejected(self):
        with self.assertRaises(ValueError):
            validate_applied_conditions({"duration_h": True})

    def test_unknown_sense_rejected(self):
        with self.assertRaises(ValueError):
            validate_required_condition({"value": 125.0, "sense": "near"})

    def test_sense_defaults_to_at_least(self):
        spec = validate_required_condition({"value": 125.0})
        self.assertEqual(spec["sense"], "at-least")

    def test_at_least_exact_equality_is_met(self):
        self.assertTrue(condition_met(125.0, 125.0, "at-least"))

    def test_at_most_exact_equality_is_met(self):
        self.assertTrue(condition_met(-55.0, -55.0, "at-most"))

    def test_at_most_colder_soak_is_met(self):
        self.assertTrue(condition_met(-65.0, -55.0, "at-most"))

    def test_at_most_warmer_soak_is_not_met(self):
        self.assertFalse(condition_met(-40.0, -55.0, "at-most"))

    def test_at_least_shortfall_is_not_met(self):
        self.assertFalse(condition_met(1500.0, 2000.0, "at-least"))

    def test_required_condition_never_applied_is_a_finding(self):
        result = assess_conditions({"duration_h": 2000.0},
                                   {"temperature_c": {"value": 125.0}})
        self.assertEqual(len(result["findings"]), 1)
        self.assertFalse(result["conditions"][0]["met"])

    def test_every_unmet_condition_is_named(self):
        result = assess_conditions(
            {"duration_h": 500.0, "temperature_c": 85.0},
            {"duration_h": {"value": 2000.0}, "temperature_c": {"value": 125.0}},
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_sense_list_holds_both_directions(self):
        self.assertEqual(set(CONDITION_SENSES), {"at-least", "at-most"})


class MeasurementTests(unittest.TestCase):
    def test_drift_fraction_is_relative_to_initial(self):
        self.assertAlmostEqual(parameter_drift_fraction(10.0, 10.5), 0.05, places=9)

    def test_drift_fraction_is_a_magnitude(self):
        self.assertAlmostEqual(parameter_drift_fraction(10.0, 9.5), 0.05, places=9)

    def test_zero_initial_reading_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift_fraction(0.0, 1.0)

    def test_drift_exactly_at_limit_passes(self):
        record = assess_measurement(
            {"parameter": "vth", "initial": 1.0, "final": 1.05,
             "drift_limit_fraction": 0.05}, 0.10)
        self.assertAlmostEqual(record["drift_fraction"],
                               record["drift_limit_fraction"], places=9)
        self.assertTrue(record["within_drift_limit"])
        self.assertTrue(record["passed"])

    def test_drift_above_limit_is_a_finding(self):
        record = assess_measurement(
            {"parameter": "vth", "initial": 1.0, "final": 1.5,
             "drift_limit_fraction": 0.05}, 0.10)
        self.assertFalse(record["passed"])

    def test_default_drift_limit_applies_when_none_declared(self):
        record = assess_measurement({"parameter": "vth", "initial": 1.0, "final": 1.2}, 0.10)
        self.assertAlmostEqual(record["drift_limit_fraction"], 0.10, places=9)
        self.assertFalse(record["within_drift_limit"])

    def test_declared_limit_overrides_the_default(self):
        record = assess_measurement(
            {"parameter": "vth", "initial": 1.0, "final": 1.2,
             "drift_limit_fraction": 0.25}, 0.10)
        self.assertTrue(record["within_drift_limit"])

    def test_final_reading_outside_band_is_a_finding(self):
        record = assess_measurement(
            {"parameter": "icc", "initial": 20.0, "final": 23.0,
             "drift_limit_fraction": 0.50, "lower_limit": 18.0, "upper_limit": 22.0}, 0.10)
        self.assertFalse(record["within_limit_band"])
        self.assertFalse(record["passed"])

    def test_final_reading_on_the_band_edge_passes(self):
        record = assess_measurement(
            {"parameter": "icc", "initial": 20.0, "final": 22.0,
             "drift_limit_fraction": 0.50, "lower_limit": 18.0, "upper_limit": 22.0}, 0.10)
        self.assertTrue(record["within_limit_band"])

    def test_drift_and_band_findings_are_both_kept(self):
        record = assess_measurement(
            {"parameter": "icc", "initial": 20.0, "final": 30.0,
             "drift_limit_fraction": 0.05, "lower_limit": 18.0, "upper_limit": 22.0}, 0.10)
        self.assertEqual(len(record["findings"]), 2)

    def test_inverted_limit_band_rejected(self):
        with self.assertRaises(ValueError):
            assess_measurement(
                {"parameter": "icc", "initial": 20.0, "final": 20.0,
                 "lower_limit": 22.0, "upper_limit": 18.0}, 0.10)

    def test_missing_final_reading_rejected(self):
        with self.assertRaises(ValueError):
            assess_measurement({"parameter": "icc", "initial": 20.0}, 0.10)

    def test_non_positive_drift_limit_rejected(self):
        with self.assertRaises(ValueError):
            assess_measurement({"parameter": "icc", "initial": 20.0, "final": 20.0,
                                "drift_limit_fraction": 0.0}, 0.10)


class StepTests(unittest.TestCase):
    def test_clean_step_passes(self):
        record = assess_test_step(_steps()[2], 0.10)
        self.assertTrue(record["passed"])

    def test_step_name_normalized_in_record(self):
        record = assess_test_step({"name": "Life Test", "conditions": {"duration_h": 10.0}},
                                  0.10)
        self.assertEqual(record["name"], "life-test")

    def test_repeated_parameter_in_one_step_rejected(self):
        step = {"name": "life-test", "conditions": {"duration_h": 10.0},
                "measurements": [{"parameter": "vth", "initial": 1.0, "final": 1.0},
                                 {"parameter": "vth", "initial": 1.0, "final": 1.0}]}
        with self.assertRaises(ValueError):
            assess_test_step(step, 0.10)

    def test_measurements_must_be_a_sequence(self):
        step = {"name": "life-test", "conditions": {"duration_h": 10.0},
                "measurements": {"parameter": "vth"}}
        with self.assertRaises(ValueError):
            assess_test_step(step, 0.10)

    def test_condition_and_measurement_findings_both_surface(self):
        step = {"name": "life-test", "conditions": {"duration_h": 500.0},
                "required_conditions": {"duration_h": {"value": 2000.0}},
                "measurements": [{"parameter": "vth", "initial": 1.0, "final": 2.0,
                                  "drift_limit_fraction": 0.05}]}
        record = assess_test_step(step, 0.10)
        self.assertEqual(len(record["findings"]), 2)


class ProgrammeTests(unittest.TestCase):
    def test_complete_programme_is_evaluated_clean(self):
        result = assess_evaluation_programme(_spec())
        self.assertTrue(result["evaluated"])
        self.assertEqual(result["findings"], [])

    def test_absent_mandatory_step_is_a_finding(self):
        steps = [s for s in _steps() if s["name"] != "life-test"]
        result = assess_evaluation_programme(_spec(steps=steps))
        self.assertEqual(result["missing_steps"], ["life-test"])
        self.assertFalse(result["evaluated"])

    def test_missing_steps_preserve_mandatory_order(self):
        records = [assess_test_step({"name": "life-test", "conditions": {"duration_h": 1.0}},
                                    0.10)]
        self.assertEqual(missing_steps(records),
                         [n for n in MANDATORY_STEPS if n != "life-test"])

    def test_missing_steps_rejects_malformed_record(self):
        with self.assertRaises(ValueError):
            missing_steps([{"conditions": {}}])

    def test_under_severity_step_blocks_the_verdict(self):
        steps = _steps(life_test={"conditions": {"duration_h": 500.0,
                                                 "temperature_c": 125.0}})
        result = assess_evaluation_programme(_spec(steps=steps))
        self.assertFalse(result["evaluated"])

    def test_duplicate_step_declaration_rejected(self):
        steps = _steps() + [{"name": "life-test", "conditions": {"duration_h": 10.0}}]
        with self.assertRaises(ValueError):
            assess_evaluation_programme(_spec(steps=steps))

    def test_empty_step_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_evaluation_programme(_spec(steps=[]))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["default_drift_limit_fraction"]
        with self.assertRaises(ValueError):
            assess_evaluation_programme(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_evaluation_programme(["part"])

    def test_every_shortfall_is_named_not_only_the_first(self):
        steps = _steps(life_test={"conditions": {"duration_h": 500.0,
                                                 "temperature_c": 85.0}})
        steps = [s for s in steps if s["name"] != "mechanical-robustness"]
        result = assess_evaluation_programme(_spec(steps=steps))
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_tolerances_are_representation_sized_only(self):
        self.assertLess(CONDITION_TOLERANCE, 1e-6)
        self.assertLess(DRIFT_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
