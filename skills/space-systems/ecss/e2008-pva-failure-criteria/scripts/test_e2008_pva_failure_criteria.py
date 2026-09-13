"""Contract tests for the clause 5.6.1 subgroup failure-criteria logic."""

import unittest

from e2008_pva_failure_criteria_logic import (
    COMPARISON_ABSOLUTE_TOLERANCE,
    FAILURE_CONDITIONS,
    OCCURRENCE_BASIS,
    assess_subgroup_failure,
    condition_basis,
    evaluate_observation,
    evaluate_observations,
    evaluate_sample_coverage,
    failing_sample_ids,
    normalize_condition,
    validate_observation,
)

# A four-coupon subgroup read through one occurrence condition and two
# limit-governed ones: degradation must stay at or under 5 %, retention must
# reach 0.95.
LIMITS = {
    "output-power-degradation": 0.05,
    "power-retention-ratio": 0.95,
    "cracked-area-fraction": 0.02,
    "in-situ-discontinuity": 0.0,
}

SAMPLES = ["c1", "c2", "c3", "c4"]
REQUIRED = ["continuity-loss", "output-power-degradation", "power-retention-ratio"]


def _occurrence(sample_id="c1", condition="continuity-loss", observed=False):
    return {"sample_id": sample_id, "condition": condition, "observed": observed}


def _measured(sample_id="c1", condition="output-power-degradation", value=0.01):
    return {"sample_id": sample_id, "condition": condition, "value": value}


def _clean_observations():
    records = []
    for sample_id in SAMPLES:
        records.append(_occurrence(sample_id))
        records.append(_measured(sample_id))
        records.append(_measured(sample_id, "power-retention-ratio", 0.99))
    return records


class ConditionCatalogueTests(unittest.TestCase):
    def test_recognized_condition_is_returned(self):
        self.assertEqual(normalize_condition("continuity-loss"), "continuity-loss")

    def test_case_and_space_are_absorbed(self):
        self.assertEqual(
            normalize_condition("  Component-Detachment "), "component-detachment"
        )

    def test_unrecognized_condition_rejected(self):
        with self.assertRaises(ValueError):
            normalize_condition("looks-a-bit-off")

    def test_non_string_condition_rejected(self):
        with self.assertRaises(ValueError):
            normalize_condition(7)

    def test_occurrence_and_limit_bases_both_exist(self):
        bases = {entry["basis"] for entry in FAILURE_CONDITIONS.values()}
        self.assertIn(OCCURRENCE_BASIS, bases)
        self.assertIn("at-or-under", bases)
        self.assertIn("at-or-over", bases)

    def test_continuity_loss_is_read_on_occurrence(self):
        self.assertEqual(condition_basis("continuity-loss"), OCCURRENCE_BASIS)

    def test_retention_ratio_is_read_against_a_floor(self):
        self.assertEqual(condition_basis("power-retention-ratio"), "at-or-over")


class ObservationValidationTests(unittest.TestCase):
    def test_occurrence_record_keeps_its_flag(self):
        record = validate_observation(_occurrence(observed=True))
        self.assertTrue(record["observed"])

    def test_measured_record_returns_a_float(self):
        record = validate_observation(_measured(value=1))
        self.assertAlmostEqual(record["value"], 1.0, places=12)

    def test_sample_id_is_trimmed(self):
        self.assertEqual(validate_observation(_occurrence(" c9 "))["sample_id"], "c9")

    def test_occurrence_record_without_a_flag_rejected(self):
        record = _occurrence()
        del record["observed"]
        with self.assertRaises(ValueError):
            validate_observation(record)

    def test_measured_record_without_a_value_rejected(self):
        record = _measured()
        del record["value"]
        with self.assertRaises(ValueError):
            validate_observation(record)

    def test_numeric_occurrence_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_observation(_occurrence(observed=1))

    def test_boolean_measured_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_observation(_measured(value=True))

    def test_negative_measured_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_observation(_measured(value=-0.01))

    def test_blank_sample_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_observation(_occurrence("   "))

    def test_non_mapping_observation_rejected(self):
        with self.assertRaises(ValueError):
            validate_observation(["c1"])


class OutcomeTests(unittest.TestCase):
    def test_occurrence_that_did_not_happen_does_not_fail(self):
        self.assertFalse(evaluate_observation(_occurrence())["failed"])

    def test_occurrence_that_happened_fails_on_occurrence_alone(self):
        outcome = evaluate_observation(_occurrence(observed=True))
        self.assertTrue(outcome["failed"])
        self.assertIn("occurrence alone", outcome["reason"])

    def test_value_under_its_ceiling_does_not_fail(self):
        outcome = evaluate_observation(_measured(value=0.01), LIMITS)
        self.assertFalse(outcome["failed"])
        self.assertAlmostEqual(outcome["margin"], 0.04, places=9)

    def test_value_over_its_ceiling_fails(self):
        outcome = evaluate_observation(_measured(value=0.30), LIMITS)
        self.assertTrue(outcome["failed"])
        self.assertLess(outcome["margin"], -0.2)

    def test_value_exactly_at_its_ceiling_does_not_fail(self):
        outcome = evaluate_observation(_measured(value=0.05), LIMITS)
        self.assertAlmostEqual(outcome["margin"], 0.0, places=12)
        self.assertFalse(outcome["failed"])

    def test_value_a_tolerance_over_its_ceiling_does_not_fail(self):
        value = 0.05 + COMPARISON_ABSOLUTE_TOLERANCE / 2.0
        self.assertFalse(evaluate_observation(_measured(value=value), LIMITS)["failed"])

    def test_value_exactly_at_its_floor_does_not_fail(self):
        outcome = evaluate_observation(
            _measured(condition="power-retention-ratio", value=0.95), LIMITS
        )
        self.assertAlmostEqual(outcome["margin"], 0.0, places=12)
        self.assertFalse(outcome["failed"])

    def test_value_under_its_floor_fails(self):
        outcome = evaluate_observation(
            _measured(condition="power-retention-ratio", value=0.40), LIMITS
        )
        self.assertTrue(outcome["failed"])
        self.assertIn("not at or over", outcome["reason"])

    def test_a_zero_ceiling_is_honoured(self):
        outcome = evaluate_observation(
            _measured(condition="in-situ-discontinuity", value=1.0), LIMITS
        )
        self.assertTrue(outcome["failed"])

    def test_missing_declared_limit_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_observation(_measured(condition="visual-defect-count", value=2.0),
                                 LIMITS)

    def test_negative_declared_limit_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_observation(_measured(), {"output-power-degradation": -0.1})

    def test_observations_are_evaluated_one_for_one(self):
        outcomes = evaluate_observations(
            [_occurrence("c1"), _measured("c1", value=0.9)], LIMITS
        )
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(failing_sample_ids(outcomes), ("c1",))

    def test_repeated_reading_of_one_condition_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_observations([_measured("c1"), _measured("c1")], LIMITS)

    def test_non_sequence_observation_set_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_observations({"sample_id": "c1"}, LIMITS)

    def test_failing_sample_ids_rejects_a_malformed_outcome(self):
        with self.assertRaises(ValueError):
            failing_sample_ids([{"sample_id": "c1"}])

    def test_a_sample_failing_twice_is_named_once(self):
        outcomes = evaluate_observations(
            [_occurrence("c1", observed=True), _measured("c1", value=0.9)], LIMITS
        )
        self.assertEqual(failing_sample_ids(outcomes), ("c1",))


class CoverageTests(unittest.TestCase):
    def test_full_record_is_complete(self):
        outcomes = evaluate_observations(_clean_observations(), LIMITS)
        records = evaluate_sample_coverage(outcomes, SAMPLES, REQUIRED)
        self.assertEqual(len(records), 4)
        self.assertTrue(all(record["complete"] for record in records))

    def test_sample_with_no_record_at_all_is_incomplete(self):
        outcomes = evaluate_observations(
            [o for o in _clean_observations() if o["sample_id"] != "c4"], LIMITS
        )
        records = evaluate_sample_coverage(outcomes, SAMPLES, REQUIRED)
        self.assertFalse(records[3]["complete"])
        self.assertEqual(len(records[3]["missing_conditions"]), 3)

    def test_sample_missing_one_condition_is_incomplete(self):
        kept = [
            o for o in _clean_observations()
            if not (o["sample_id"] == "c2" and o["condition"] == "power-retention-ratio")
        ]
        records = evaluate_sample_coverage(
            evaluate_observations(kept, LIMITS), SAMPLES, REQUIRED
        )
        self.assertEqual(records[1]["missing_conditions"], ("power-retention-ratio",))

    def test_duplicate_declared_sample_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sample_coverage([], ["c1", "c1"], REQUIRED)

    def test_empty_sample_list_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sample_coverage([], [], REQUIRED)

    def test_empty_required_condition_list_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sample_coverage([], SAMPLES, [])

    def test_repeated_required_condition_is_counted_once(self):
        records = evaluate_sample_coverage(
            [], SAMPLES, ["continuity-loss", "continuity-loss"]
        )
        self.assertEqual(records[0]["missing_conditions"], ("continuity-loss",))


class SubgroupVerdictTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "sample_ids": list(SAMPLES),
            "observations": _clean_observations(),
            "required_conditions": list(REQUIRED),
            "limits": dict(LIMITS),
        }
        spec.update(overrides)
        return spec

    def test_a_complete_clean_record_passes(self):
        result = assess_subgroup_failure(self._spec())
        self.assertTrue(result["passed"])
        self.assertFalse(result["subgroup_failed"])
        self.assertEqual(result["findings"], [])

    def test_one_occurrence_condition_fails_the_subgroup(self):
        observations = _clean_observations()
        observations[0] = _occurrence("c1", observed=True)
        result = assess_subgroup_failure(self._spec(observations=observations))
        self.assertTrue(result["subgroup_failed"])
        self.assertEqual(result["failing_sample_ids"], ("c1",))

    def test_one_exceeded_limit_fails_the_subgroup(self):
        observations = _clean_observations()
        observations[4] = _measured("c2", value=0.44)
        result = assess_subgroup_failure(self._spec(observations=observations))
        self.assertFalse(result["passed"])
        self.assertEqual(result["failing_observation_count"], 1)

    def test_an_incomplete_record_is_not_a_pass(self):
        observations = [o for o in _clean_observations() if o["sample_id"] != "c3"]
        result = assess_subgroup_failure(self._spec(observations=observations))
        self.assertFalse(result["passed"])
        self.assertFalse(result["record_complete"])
        self.assertFalse(result["subgroup_failed"])

    def test_observation_from_an_undeclared_sample_is_a_finding(self):
        observations = _clean_observations() + [_occurrence("c9")]
        result = assess_subgroup_failure(self._spec(observations=observations))
        self.assertFalse(result["passed"])
        self.assertTrue(
            any("never contained" in finding for finding in result["findings"])
        )

    def test_every_failing_sample_is_named(self):
        observations = _clean_observations()
        observations[0] = _occurrence("c1", observed=True)
        observations[3] = _occurrence("c2", observed=True)
        result = assess_subgroup_failure(self._spec(observations=observations))
        self.assertEqual(result["failing_sample_ids"], ("c1", "c2"))

    def test_coverage_records_travel_with_the_verdict(self):
        result = assess_subgroup_failure(self._spec())
        self.assertEqual(len(result["coverage"]), 4)
        self.assertTrue(result["record_complete"])

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["limits"]
        with self.assertRaises(ValueError):
            assess_subgroup_failure(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_subgroup_failure(["observations"])

    def test_undeclared_limit_in_the_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_subgroup_failure(self._spec(limits={"output-power-degradation": 0.05}))


if __name__ == "__main__":
    unittest.main()
