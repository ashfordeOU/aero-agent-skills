"""Contract tests for the clause 5.1.6 Class 2 engineering qualification model part logic."""

import unittest

from q60_class_2_eqm_component_usage_logic import (
    MANDATORY_PART_ATTRIBUTES,
    MAX_RELAXATION_STEPS,
    QUALITY_LEVELS,
    RATIO_TOLERANCE,
    RETENTION_THRESHOLD,
    REUSE_MARGIN_RESERVE,
    STRESS_KEYS,
    assess_eqm_part_handling,
    consumed_life,
    evaluate_eqm_part,
    flight_reuse_eligibility,
    post_campaign_disposition,
    quality_level_rank,
    relaxation_depth,
    remaining_margin,
    usage_permission,
    validate_part_id,
    validate_stress_limits,
)

LIMITS = {"thermal_cycles": 200, "rework_operations": 4, "powered_hours": 2000}


def part(**overrides):
    """Return one permitted, lightly used part fitted to the Class 2 model."""
    base = {
        "part_id": "M001",
        "part_number": "RH1499",
        "fitted_quality_level": "level-1",
        "flight_quality_level": "level-1",
        "interchangeable": True,
        "accumulated": {
            "thermal_cycles": 20,
            "rework_operations": 1,
            "powered_hours": 100,
        },
    }
    base.update(overrides)
    return base


def spent(hours, **overrides):
    """Return a part whose powered hours govern its consumed life."""
    return part(
        accumulated={
            "thermal_cycles": 20,
            "rework_operations": 1,
            "powered_hours": hours,
        },
        **overrides
    )


class ValidatePartIdTests(unittest.TestCase):
    def test_strips_surrounding_space(self):
        self.assertEqual(validate_part_id("  M001 "), "M001")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            validate_part_id("   ")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_part_id(11)


class QualityLadderTests(unittest.TestCase):
    def test_best_level_ranks_first(self):
        self.assertEqual(quality_level_rank("level-1"), 0)

    def test_ladder_is_strictly_ordered(self):
        ranks = [quality_level_rank(level) for level in QUALITY_LEVELS]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(len(set(ranks)), len(QUALITY_LEVELS))

    def test_rank_lookup_ignores_case(self):
        self.assertEqual(quality_level_rank("LEVEL-3"), quality_level_rank("level-3"))

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            quality_level_rank("whatever-was-on-the-shelf")

    def test_depth_is_positive_when_the_fitted_part_is_lower(self):
        self.assertEqual(relaxation_depth("level-3", "level-1"), 2)

    def test_depth_is_negative_when_the_fitted_part_is_better(self):
        self.assertEqual(relaxation_depth("level-1", "level-3"), -2)


class UsagePermissionTests(unittest.TestCase):
    def test_equal_level_is_permitted_outright(self):
        permission, depth = usage_permission(part())
        self.assertEqual(permission, "permitted-equivalent")
        self.assertEqual(depth, 0)

    def test_better_part_than_the_flight_part_is_still_permitted(self):
        permission, _ = usage_permission(
            part(fitted_quality_level="level-1", flight_quality_level="level-2")
        )
        self.assertEqual(permission, "permitted-equivalent")

    def test_class_2_allowance_reaches_three_rungs(self):
        self.assertEqual(MAX_RELAXATION_STEPS, 3)
        permission, depth = usage_permission(
            part(
                fitted_quality_level="commercial-upscreened",
                flight_quality_level="level-1",
                relaxation_justification="EQM-SUB-07 agreed at the build review",
            )
        )
        self.assertEqual(permission, "permitted-with-justification")
        self.assertEqual(depth, MAX_RELAXATION_STEPS)

    def test_same_relaxation_without_a_justification_is_a_finding(self):
        permission, _ = usage_permission(part(fitted_quality_level="level-2"))
        self.assertEqual(permission, "relaxation-not-justified")

    def test_blank_justification_does_not_count_as_recorded(self):
        permission, _ = usage_permission(
            part(fitted_quality_level="level-2", relaxation_justification="   ")
        )
        self.assertEqual(permission, "relaxation-not-justified")

    def test_relaxation_beyond_the_allowance_is_refused_even_with_a_justification(self):
        permission, depth = usage_permission(
            part(
                fitted_quality_level="commercial",
                flight_quality_level="level-1",
                relaxation_justification="EQM-SUB-08",
            )
        )
        self.assertEqual(permission, "relaxation-too-deep")
        self.assertGreater(depth, MAX_RELAXATION_STEPS)

    def test_a_deeper_ladder_step_inside_the_allowance_is_permitted(self):
        permission, depth = usage_permission(
            part(
                fitted_quality_level="commercial",
                flight_quality_level="level-2",
                relaxation_justification="EQM-SUB-09",
            )
        )
        self.assertEqual(permission, "permitted-with-justification")
        self.assertEqual(depth, 3)

    def test_interchangeability_is_decided_before_the_ladder(self):
        permission, _ = usage_permission(
            part(interchangeable=False, fitted_quality_level="level-2")
        )
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
    def test_declared_limits_validate(self):
        self.assertEqual(set(validate_stress_limits(LIMITS)), set(STRESS_KEYS))

    def test_missing_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_stress_limits({"thermal_cycles": 200, "rework_operations": 4})

    def test_zero_limit_is_an_input_error_not_an_unlimited_allowance(self):
        with self.assertRaises(ValueError):
            validate_stress_limits(dict(LIMITS, rework_operations=0))

    def test_negative_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_stress_limits(dict(LIMITS, powered_hours=-5))

    def test_non_mapping_limits_rejected(self):
        with self.assertRaises(ValueError):
            validate_stress_limits([200, 4, 2000])


class ConsumedLifeTests(unittest.TestCase):
    def test_governing_stress_is_the_largest_fraction_not_the_average(self):
        fraction, governing, per_stress = consumed_life(part(), LIMITS)
        self.assertEqual(governing, "rework_operations")
        self.assertAlmostEqual(fraction, 0.25, places=9)
        self.assertAlmostEqual(per_stress["thermal_cycles"], 0.1, places=9)

    def test_absent_stress_is_unspent_not_unknown(self):
        fraction, governing, _ = consumed_life(
            part(accumulated={"powered_hours": 400}), LIMITS
        )
        self.assertEqual(governing, "powered_hours")
        self.assertAlmostEqual(fraction, 0.2, places=9)

    def test_unknown_stress_key_rejected(self):
        with self.assertRaises(ValueError):
            consumed_life(part(accumulated={"vibration_hours": 3}), LIMITS)

    def test_negative_accumulated_value_rejected(self):
        with self.assertRaises(ValueError):
            consumed_life(part(accumulated={"thermal_cycles": -1}), LIMITS)

    def test_non_mapping_accumulated_rejected(self):
        with self.assertRaises(ValueError):
            consumed_life(part(accumulated=[20, 1, 100]), LIMITS)

    def test_margin_is_what_the_governing_stress_has_not_spent(self):
        fraction, _, _ = consumed_life(part(), LIMITS)
        self.assertAlmostEqual(remaining_margin(fraction), 0.75, places=9)

    def test_margin_never_goes_negative(self):
        self.assertAlmostEqual(remaining_margin(1.4), 0.0, places=9)


class DispositionTests(unittest.TestCase):
    def test_lightly_used_part_goes_back_to_model_stock(self):
        self.assertEqual(post_campaign_disposition(0.25), "return-to-model-stock")

    def test_threshold_reached_exactly_is_held_for_review(self):
        fraction, _, _ = consumed_life(spent(1500), LIMITS)
        self.assertAlmostEqual(fraction, RETENTION_THRESHOLD, places=9)
        self.assertEqual(post_campaign_disposition(fraction), "hold-for-review")

    def test_limit_reached_exactly_is_scrap(self):
        fraction, _, _ = consumed_life(spent(2000), LIMITS)
        self.assertAlmostEqual(fraction, 1.0, places=9)
        self.assertEqual(post_campaign_disposition(fraction), "scrap")

    def test_beyond_the_limit_is_scrap(self):
        self.assertEqual(post_campaign_disposition(1.6), "scrap")

    def test_negative_fraction_rejected(self):
        with self.assertRaises(ValueError):
            post_campaign_disposition(-0.1)


class FlightReuseTests(unittest.TestCase):
    def test_unpermitted_part_is_never_eligible(self):
        self.assertEqual(
            flight_reuse_eligibility("not-interchangeable", 0.1, True),
            "not-eligible-unpermitted",
        )

    def test_reserve_met_exactly_is_still_eligible(self):
        fraction, _, _ = consumed_life(spent(1200), LIMITS)
        self.assertAlmostEqual(
            remaining_margin(fraction), REUSE_MARGIN_RESERVE, places=9
        )
        self.assertEqual(
            flight_reuse_eligibility("permitted-equivalent", fraction, True), "eligible"
        )

    def test_margin_under_the_reserve_blocks_the_carry_over(self):
        fraction, _, _ = consumed_life(spent(1300), LIMITS)
        self.assertEqual(
            flight_reuse_eligibility("permitted-equivalent", fraction, True),
            "not-eligible-margin-exhausted",
        )

    def test_margin_alone_does_not_clear_a_part_without_rescreening(self):
        self.assertEqual(
            flight_reuse_eligibility("permitted-equivalent", 0.1, False),
            "eligible-after-rescreening",
        )

    def test_non_boolean_rescreening_flag_rejected(self):
        with self.assertRaises(ValueError):
            flight_reuse_eligibility("permitted-equivalent", 0.1, "recorded")


class EvaluatePartTests(unittest.TestCase):
    def test_incomplete_record_is_not_a_refusal(self):
        record = evaluate_eqm_part(part(part_number=None), LIMITS)
        self.assertEqual(record["permission"], "record-incomplete")
        self.assertEqual(record["findings"], ("record-incomplete",))
        self.assertFalse(record["permitted"])

    def test_completeness_counts_the_mandatory_attributes(self):
        record = evaluate_eqm_part(part(part_number="  "), LIMITS)
        expected = (len(MANDATORY_PART_ATTRIBUTES) - 1) / len(MANDATORY_PART_ATTRIBUTES)
        self.assertAlmostEqual(record["completeness"], expected, places=9)

    def test_clean_part_carries_no_finding(self):
        record = evaluate_eqm_part(part(), LIMITS)
        self.assertEqual(record["findings"], ())
        self.assertTrue(record["permitted"])
        self.assertEqual(record["disposition"], "return-to-model-stock")

    def test_a_part_nobody_nominates_gets_no_reuse_decision(self):
        record = evaluate_eqm_part(spent(1900), LIMITS)
        self.assertFalse(record["nominated_for_flight_reuse"])
        self.assertIsNone(record["reuse_eligibility"])

    def test_nominated_part_without_rescreening_raises_that_finding(self):
        record = evaluate_eqm_part(part(nominated_for_flight_reuse=True), LIMITS)
        self.assertEqual(record["reuse_eligibility"], "eligible-after-rescreening")
        self.assertIn("rescreening-outstanding", record["findings"])

    def test_nominated_part_with_rescreening_is_clear(self):
        record = evaluate_eqm_part(
            part(nominated_for_flight_reuse=True, rescreening_recorded=True), LIMITS
        )
        self.assertEqual(record["reuse_eligibility"], "eligible")
        self.assertEqual(record["findings"], ())

    def test_nominated_spent_part_raises_the_margin_finding(self):
        record = evaluate_eqm_part(
            spent(1500, nominated_for_flight_reuse=True, rescreening_recorded=True),
            LIMITS,
        )
        self.assertEqual(record["reuse_eligibility"], "not-eligible-margin-exhausted")
        self.assertIn("reuse-margin-exhausted", record["findings"])
        self.assertIn("held-for-review", record["findings"])

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_eqm_part(["M001"], LIMITS)

    def test_non_boolean_nomination_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_eqm_part(part(nominated_for_flight_reuse="yes"), LIMITS)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        base = {"parts": [part()], "stress_limits": dict(LIMITS)}
        base.update(overrides)
        return base

    def test_clean_model_is_accepted(self):
        result = assess_eqm_part_handling(self._spec())
        self.assertEqual(result["verdict"], "accept")
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_permitted_fraction_met_exactly_is_not_a_shortfall(self):
        spec = self._spec(
            parts=[part(), part(part_id="M002", interchangeable=False)],
            required_permitted_fraction=0.5,
        )
        result = assess_eqm_part_handling(spec)
        self.assertAlmostEqual(result["permitted_fraction"], 0.5, places=9)
        self.assertAlmostEqual(
            result["permitted_fraction"],
            result["required_permitted_fraction"],
            places=9,
        )
        self.assertTrue(result["meets_required_permitted_fraction"])
        self.assertEqual(result["verdict"], "hold")

    def test_findings_are_ranked_worst_first(self):
        spec = self._spec(
            parts=[
                part(part_id="M010", fitted_quality_level="level-2"),
                part(part_id="M011", part_number=None),
            ]
        )
        result = assess_eqm_part_handling(spec)
        self.assertEqual(result["findings"][0]["finding"], "record-incomplete")

    def test_scrap_list_names_the_spent_parts(self):
        spec = self._spec(parts=[part(), spent(2000, part_id="M020")])
        result = assess_eqm_part_handling(spec)
        self.assertEqual(result["parts_for_scrap"], ("M020",))

    def test_reuse_list_names_only_nominated_eligible_parts(self):
        spec = self._spec(
            parts=[
                part(part_id="M030", nominated_for_flight_reuse=True, rescreening_recorded=True),
                part(part_id="M031"),
                spent(1900, part_id="M032", nominated_for_flight_reuse=True, rescreening_recorded=True),
            ]
        )
        result = assess_eqm_part_handling(spec)
        self.assertEqual(result["parts_cleared_for_flight_reuse"], ("M030",))

    def test_governing_part_is_the_most_spent_one(self):
        spec = self._spec(parts=[part(), spent(1900, part_id="M040")])
        result = assess_eqm_part_handling(spec)
        self.assertEqual(result["governing_part"], "M040")

    def test_part_fitted_twice_rejected(self):
        with self.assertRaises(ValueError):
            assess_eqm_part_handling(self._spec(parts=[part(), part()]))

    def test_empty_parts_rejected(self):
        with self.assertRaises(ValueError):
            assess_eqm_part_handling(self._spec(parts=[]))

    def test_missing_stress_limits_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_eqm_part_handling({"parts": [part()]})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_eqm_part_handling(["parts"])

    def test_out_of_range_required_fraction_rejected(self):
        with self.assertRaises(ValueError):
            assess_eqm_part_handling(self._spec(required_permitted_fraction=2.0))

    def test_boolean_required_fraction_rejected(self):
        with self.assertRaises(ValueError):
            assess_eqm_part_handling(self._spec(required_permitted_fraction=True))

    def test_tolerance_is_declared_and_small(self):
        self.assertGreater(RATIO_TOLERANCE, 0.0)
        self.assertLess(RATIO_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
