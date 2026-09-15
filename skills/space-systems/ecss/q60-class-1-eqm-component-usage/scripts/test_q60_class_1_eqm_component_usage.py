"""Contract tests for the clause 4.1.6 engineering qualification model part handling logic."""

import unittest

from q60_class_1_eqm_component_usage_logic import (
    MANDATORY_PART_ATTRIBUTES,
    MAX_RELAXATION_STEPS,
    QUALITY_LEVELS,
    RATIO_TOLERANCE,
    RETENTION_THRESHOLD,
    STRESS_KEYS,
    assess_eqm_part_handling,
    consumed_life,
    evaluate_eqm_part,
    post_use_disposition,
    quality_level_rank,
    relaxation_depth,
    usage_permission,
    validate_part_id,
    validate_stress_limits,
)

LIMITS = {"thermal_cycles": 200, "rework_operations": 4, "powered_hours": 2000}


def part(**overrides):
    """Return one permitted, lightly used fitted part with optional overrides."""
    base = {
        "part_id": "M001",
        "part_number": "RH1499",
        "fitted_quality_level": "level-1",
        "flight_quality_level": "level-1",
        "interchangeable": True,
        "accumulated": {"thermal_cycles": 20, "rework_operations": 1, "powered_hours": 100},
    }
    base.update(overrides)
    return base


class ValidatePartIdTests(unittest.TestCase):
    def test_strips_surrounding_space(self):
        self.assertEqual(validate_part_id("  M001 "), "M001")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            validate_part_id("  ")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_part_id(3)


class QualityLadderTests(unittest.TestCase):
    def test_best_level_ranks_first(self):
        self.assertEqual(quality_level_rank("level-1"), 0)

    def test_ladder_is_strictly_ordered(self):
        ranks = [quality_level_rank(level) for level in QUALITY_LEVELS]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(len(set(ranks)), len(QUALITY_LEVELS))

    def test_rank_lookup_is_case_insensitive(self):
        self.assertEqual(quality_level_rank("LEVEL-2"), quality_level_rank("level-2"))

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            quality_level_rank("whatever-was-in-the-drawer")

    def test_depth_is_positive_when_the_fitted_part_is_lower(self):
        self.assertEqual(relaxation_depth("level-3", "level-1"), 2)

    def test_depth_is_negative_when_the_fitted_part_is_better(self):
        self.assertEqual(relaxation_depth("level-1", "level-3"), -2)


class UsagePermissionTests(unittest.TestCase):
    def test_equal_level_is_permitted_outright(self):
        permission, depth = usage_permission(part())
        self.assertEqual(permission, "permitted-equivalent")
        self.assertEqual(depth, 0)

    def test_better_part_than_flight_is_still_permitted(self):
        permission, _ = usage_permission(
            part(fitted_quality_level="level-1", flight_quality_level="level-2")
        )
        self.assertEqual(permission, "permitted-equivalent")

    def test_relaxation_within_the_allowance_needs_a_recorded_note(self):
        relaxed = part(fitted_quality_level="level-2", substitution_note="SUB-11 approved")
        permission, depth = usage_permission(relaxed)
        self.assertEqual(permission, "permitted-with-substitution-note")
        self.assertEqual(depth, 1)

    def test_same_relaxation_without_a_note_is_a_finding(self):
        permission, _ = usage_permission(part(fitted_quality_level="level-2"))
        self.assertEqual(permission, "relaxation-not-recorded")

    def test_blank_note_does_not_count_as_recorded(self):
        permission, _ = usage_permission(
            part(fitted_quality_level="level-2", substitution_note="   ")
        )
        self.assertEqual(permission, "relaxation-not-recorded")

    def test_relaxation_beyond_the_allowance_is_refused_even_with_a_note(self):
        deep = part(
            fitted_quality_level="commercial",
            flight_quality_level="level-1",
            substitution_note="SUB-12",
        )
        permission, depth = usage_permission(deep)
        self.assertEqual(permission, "relaxation-too-deep")
        self.assertGreater(depth, MAX_RELAXATION_STEPS)

    def test_a_part_that_is_not_interchangeable_is_refused_first(self):
        permission, _ = usage_permission(part(interchangeable=False))
        self.assertEqual(permission, "not-interchangeable")

    def test_missing_level_key_rejected(self):
        broken = part()
        del broken["flight_quality_level"]
        with self.assertRaises(ValueError):
            usage_permission(broken)

    def test_non_boolean_interchangeable_rejected(self):
        with self.assertRaises(ValueError):
            usage_permission(part(interchangeable="yes"))


class StressLimitTests(unittest.TestCase):
    def test_valid_limits_are_returned_as_floats(self):
        validated = validate_stress_limits(LIMITS)
        for key in STRESS_KEYS:
            self.assertIsInstance(validated[key], float)

    def test_missing_limit_rejected(self):
        broken = dict(LIMITS)
        del broken["powered_hours"]
        with self.assertRaises(ValueError):
            validate_stress_limits(broken)

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_stress_limits(dict(LIMITS, rework_operations=0))

    def test_negative_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_stress_limits(dict(LIMITS, thermal_cycles=-5))

    def test_non_mapping_limits_rejected(self):
        with self.assertRaises(ValueError):
            validate_stress_limits(["thermal_cycles"])


class ConsumedLifeTests(unittest.TestCase):
    def test_fraction_is_the_governing_stress_not_an_average(self):
        heavy = part(
            accumulated={"thermal_cycles": 20, "rework_operations": 3, "powered_hours": 100}
        )
        fraction, governing, per_stress = consumed_life(heavy, LIMITS)
        self.assertEqual(governing, "rework_operations")
        self.assertAlmostEqual(fraction, 3 / 4, places=9)
        self.assertAlmostEqual(per_stress["thermal_cycles"], 20 / 200, places=9)

    def test_absent_stress_counts_as_unspent(self):
        fraction, _, per_stress = consumed_life(part(accumulated={}), LIMITS)
        self.assertAlmostEqual(fraction, 0.0, places=9)
        self.assertAlmostEqual(per_stress["powered_hours"], 0.0, places=9)

    def test_spending_past_a_limit_gives_a_fraction_above_one(self):
        fraction, governing, _ = consumed_life(
            part(accumulated={"thermal_cycles": 260}), LIMITS
        )
        self.assertEqual(governing, "thermal_cycles")
        self.assertAlmostEqual(fraction, 260 / 200, places=9)

    def test_negative_accumulated_stress_rejected(self):
        with self.assertRaises(ValueError):
            consumed_life(part(accumulated={"powered_hours": -1}), LIMITS)

    def test_non_mapping_accumulated_rejected(self):
        with self.assertRaises(ValueError):
            consumed_life(part(accumulated=[10, 1, 100]), LIMITS)


class PostUseDispositionTests(unittest.TestCase):
    def test_lightly_used_part_returns_to_model_stock(self):
        self.assertEqual(post_use_disposition(0.1), "return-to-model-stock")

    def test_part_past_the_retention_threshold_is_held(self):
        self.assertEqual(post_use_disposition(0.9), "hold-for-review")

    def test_exactly_at_the_retention_threshold_is_held(self):
        value = RETENTION_THRESHOLD
        self.assertAlmostEqual(value, RETENTION_THRESHOLD, places=9)
        self.assertEqual(post_use_disposition(value), "hold-for-review")

    def test_exactly_at_the_limit_goes_to_scrap(self):
        fraction, _, _ = consumed_life(
            part(accumulated={"rework_operations": 4}), LIMITS
        )
        self.assertAlmostEqual(fraction, 1.0, places=9)
        self.assertEqual(post_use_disposition(fraction), "scrap")

    def test_past_the_limit_goes_to_scrap(self):
        self.assertEqual(post_use_disposition(1.4), "scrap")

    def test_negative_fraction_rejected(self):
        with self.assertRaises(ValueError):
            post_use_disposition(-0.1)

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(RATIO_TOLERANCE, 1e-6)


class EvaluateEqmPartTests(unittest.TestCase):
    def test_clean_part_carries_no_finding(self):
        record = evaluate_eqm_part(part(), LIMITS)
        self.assertTrue(record["permitted"])
        self.assertIsNone(record["finding"])
        self.assertEqual(record["disposition"], "return-to-model-stock")

    def test_incomplete_record_is_not_a_permission_decision(self):
        incomplete = part()
        del incomplete["interchangeable"]
        record = evaluate_eqm_part(incomplete, LIMITS)
        self.assertEqual(record["permission"], "record-incomplete")
        self.assertFalse(record["permitted"])
        expected = (len(MANDATORY_PART_ATTRIBUTES) - 1) / len(MANDATORY_PART_ATTRIBUTES)
        self.assertAlmostEqual(record["completeness"], expected, places=9)

    def test_flight_build_position_is_stated_for_every_fitted_part(self):
        record = evaluate_eqm_part(part(), LIMITS)
        self.assertEqual(record["flight_build_position"], "barred-from-flight-build")
        self.assertTrue(record["flight_build_reason"])

    def test_unrecorded_relaxation_is_the_finding_not_the_stress(self):
        record = evaluate_eqm_part(part(fitted_quality_level="level-2"), LIMITS)
        self.assertEqual(record["finding"], "relaxation-not-recorded")

    def test_exhausted_permitted_part_is_a_scrap_finding(self):
        record = evaluate_eqm_part(
            part(accumulated={"powered_hours": 2400}), LIMITS
        )
        self.assertEqual(record["disposition"], "scrap")
        self.assertEqual(record["finding"], "stress-limit-exceeded")

    def test_part_between_the_threshold_and_the_limit_is_held(self):
        record = evaluate_eqm_part(part(accumulated={"thermal_cycles": 180}), LIMITS)
        self.assertEqual(record["disposition"], "hold-for-review")
        self.assertEqual(record["finding"], "held-for-review")


class AssessEqmPartHandlingTests(unittest.TestCase):
    def _spec(self, **overrides):
        base = {
            "parts": [part()],
            "stress_limits": LIMITS,
            "required_permitted_fraction": 1.0,
        }
        base.update(overrides)
        return base

    def test_clean_model_build_is_accepted(self):
        result = assess_eqm_part_handling(self._spec())
        self.assertEqual(result["verdict"], "accept")
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["permitted_fraction"], 1.0, places=9)

    def test_one_refused_part_holds_the_build(self):
        spec = self._spec(
            parts=[part(), part(part_id="M002", interchangeable=False)]
        )
        result = assess_eqm_part_handling(spec)
        self.assertEqual(result["verdict"], "hold")
        self.assertAlmostEqual(result["permitted_fraction"], 1 / 2, places=9)

    def test_findings_are_ranked_with_the_worst_first(self):
        incomplete = part(part_id="M000")
        del incomplete["part_number"]
        spec = self._spec(
            parts=[
                part(part_id="M003", fitted_quality_level="level-2"),
                incomplete,
            ]
        )
        result = assess_eqm_part_handling(spec)
        self.assertEqual(result["findings"][0]["disposition"], "record-incomplete")

    def test_scrap_list_names_the_exhausted_parts(self):
        spec = self._spec(
            parts=[part(), part(part_id="M004", accumulated={"rework_operations": 9})]
        )
        result = assess_eqm_part_handling(spec)
        self.assertEqual(result["parts_for_scrap"], ("M004",))

    def test_governing_part_is_the_most_spent_one(self):
        spec = self._spec(
            parts=[
                part(part_id="M001", accumulated={"thermal_cycles": 20}),
                part(part_id="M005", accumulated={"thermal_cycles": 150}),
            ]
        )
        result = assess_eqm_part_handling(spec)
        self.assertEqual(result["governing_part"], "M005")

    def test_flight_build_position_is_reported_at_build_level(self):
        result = assess_eqm_part_handling(self._spec())
        self.assertEqual(result["flight_build_position"], "barred-from-flight-build")

    def test_part_fitted_twice_rejected(self):
        with self.assertRaises(ValueError):
            assess_eqm_part_handling(self._spec(parts=[part(), part()]))

    def test_requirement_met_exactly_is_not_a_shortfall(self):
        result = assess_eqm_part_handling(self._spec())
        self.assertAlmostEqual(
            result["permitted_fraction"], result["required_permitted_fraction"], places=9
        )
        self.assertEqual(result["verdict"], "accept")

    def test_missing_stress_limits_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_eqm_part_handling({"parts": [part()]})

    def test_empty_parts_rejected(self):
        with self.assertRaises(ValueError):
            assess_eqm_part_handling(self._spec(parts=[]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_eqm_part_handling(["parts"])

    def test_out_of_range_required_fraction_rejected(self):
        with self.assertRaises(ValueError):
            assess_eqm_part_handling(self._spec(required_permitted_fraction=2.0))

    def test_boolean_required_fraction_rejected(self):
        with self.assertRaises(ValueError):
            assess_eqm_part_handling(self._spec(required_permitted_fraction=True))


if __name__ == "__main__":
    unittest.main()
