"""Contract tests for the clause 5.5.3.4.1 bracketed power-measurement logic."""

import unittest

from e2008_power_measurement_purpose_logic import (
    BASELINE_NOT_MEASURED,
    COMMON_OBJECTIVE,
    DEFAULT_POWER_MEASUREMENT_POLICY,
    DEGRADATION_EXCEEDS_ALLOWANCE,
    DEGRADATION_NOT_RESOLVABLE,
    DEGRADATION_WITHIN_ALLOWANCE,
    assess_power_measurement_purpose,
    bracketed_test_inventory,
    combined_uncertainty_pct,
    degradation_is_resolvable,
    degradation_objectives,
    relative_degradation_pct,
    resolvable_degradation_pct,
    validate_power_measurement_policy,
)

TESTS = ["solar-array-thermal-cycling", "solar-array-humidity-exposure"]


def _policy(**overrides):
    policy = dict(DEFAULT_POWER_MEASUREMENT_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "bracketed_tests": list(TESTS),
        "pre_test_measurement": {"power_w": 200.0, "uncertainty_pct": 0.3},
        "post_test_measurement": {"power_w": 198.0, "uncertainty_pct": 0.4},
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_power_measurement_policy(DEFAULT_POWER_MEASUREMENT_POLICY),
            DEFAULT_POWER_MEASUREMENT_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_measurement_policy(["allowable_degradation_pct"])

    def test_resolution_margin_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_measurement_policy(_policy(resolution_margin=0.5))

    def test_zero_coverage_factor_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_measurement_policy(_policy(coverage_factor=0.0))

    def test_allowance_above_one_hundred_percent_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_measurement_policy(
                _policy(allowable_degradation_pct=140.0)
            )


class DegradationTests(unittest.TestCase):
    def test_degradation_is_the_relative_power_loss(self):
        self.assertAlmostEqual(
            relative_degradation_pct(200.0, 198.0), 1.0, places=9
        )

    def test_no_loss_gives_zero_degradation(self):
        self.assertAlmostEqual(
            relative_degradation_pct(150.0, 150.0), 0.0, places=9
        )

    def test_a_measured_gain_is_reported_as_a_negative_loss(self):
        self.assertAlmostEqual(
            relative_degradation_pct(100.0, 101.0), -1.0, places=9
        )

    def test_degradation_scales_with_the_baseline_not_the_absolute_loss(self):
        small = relative_degradation_pct(100.0, 99.0)
        large = relative_degradation_pct(400.0, 396.0)
        self.assertAlmostEqual(small, large, places=9)

    def test_zero_baseline_power_rejected(self):
        with self.assertRaises(ValueError):
            relative_degradation_pct(0.0, 0.0)

    def test_negative_post_test_power_rejected(self):
        with self.assertRaises(ValueError):
            relative_degradation_pct(100.0, -1.0)

    def test_boolean_power_rejected(self):
        with self.assertRaises(ValueError):
            relative_degradation_pct(True, 0.5)


class ResolutionTests(unittest.TestCase):
    def test_combined_uncertainty_is_the_root_sum_square(self):
        self.assertAlmostEqual(combined_uncertainty_pct(3.0, 4.0), 5.0, places=9)

    def test_combined_uncertainty_is_order_independent(self):
        self.assertAlmostEqual(
            combined_uncertainty_pct(0.3, 0.4),
            combined_uncertainty_pct(0.4, 0.3),
            places=12,
        )

    def test_combined_uncertainty_exceeds_either_contribution(self):
        combined = combined_uncertainty_pct(0.3, 0.4)
        self.assertGreater(combined, 0.4)

    def test_resolution_is_the_covered_combined_uncertainty(self):
        resolution = resolvable_degradation_pct(3.0, 4.0, _policy())
        self.assertAlmostEqual(resolution, 10.0, places=9)

    def test_resolution_exactly_at_the_allowance_is_resolvable(self):
        policy = _policy(allowable_degradation_pct=10.0)
        self.assertAlmostEqual(
            resolvable_degradation_pct(3.0, 4.0, policy),
            policy["allowable_degradation_pct"],
            places=9,
        )
        self.assertTrue(degradation_is_resolvable(3.0, 4.0, policy))

    def test_coarse_measurements_cannot_resolve_the_allowance(self):
        self.assertFalse(degradation_is_resolvable(2.0, 2.0, _policy()))

    def test_fine_measurements_resolve_the_allowance(self):
        self.assertTrue(degradation_is_resolvable(0.2, 0.2, _policy()))

    def test_negative_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            combined_uncertainty_pct(-0.1, 0.2)


class ObjectiveTests(unittest.TestCase):
    def test_each_bracketed_test_contributes_an_objective(self):
        objectives = degradation_objectives(TESTS)
        self.assertIn("interconnect-fatigue-power-loss", objectives)
        self.assertIn("bondline-adhesion-power-loss", objectives)

    def test_the_shared_objective_is_appended_once(self):
        objectives = degradation_objectives(TESTS)
        self.assertEqual(objectives.count(COMMON_OBJECTIVE), 1)

    def test_no_bracketed_test_yields_no_objective(self):
        self.assertEqual(degradation_objectives([]), ())

    def test_repeated_test_is_grouped_once(self):
        grouped = bracketed_test_inventory(
            ["solar-array-thermal-cycling", "solar-array-thermal-cycling"]
        )
        self.assertEqual(grouped, ("solar-array-thermal-cycling",))

    def test_unknown_bracketed_test_rejected(self):
        with self.assertRaises(ValueError):
            bracketed_test_inventory(["solar-array-bake-out"])

    def test_non_collection_test_list_rejected(self):
        with self.assertRaises(ValueError):
            bracketed_test_inventory("solar-array-thermal-cycling")


class PurposeAssessmentTests(unittest.TestCase):
    def test_a_resolvable_small_loss_is_within_allowance(self):
        result = assess_power_measurement_purpose(_case())
        self.assertEqual(result["verdict"], DEGRADATION_WITHIN_ALLOWANCE)
        self.assertTrue(result["resolvable"])
        self.assertEqual(result["findings"], [])

    def test_a_large_loss_exceeds_the_allowance(self):
        result = assess_power_measurement_purpose(
            _case(post_test_measurement={"power_w": 180.0, "uncertainty_pct": 0.4})
        )
        self.assertEqual(result["verdict"], DEGRADATION_EXCEEDS_ALLOWANCE)
        self.assertTrue(result["findings"])

    def test_a_loss_exactly_at_the_allowance_is_within_it(self):
        result = assess_power_measurement_purpose(
            _case(post_test_measurement={"power_w": 196.0, "uncertainty_pct": 0.4})
        )
        self.assertAlmostEqual(
            result["degradation_pct"], result["allowable_degradation_pct"], places=9
        )
        self.assertEqual(result["verdict"], DEGRADATION_WITHIN_ALLOWANCE)

    def test_coarse_pair_cannot_detect_and_says_so(self):
        result = assess_power_measurement_purpose(
            _case(
                pre_test_measurement={"power_w": 200.0, "uncertainty_pct": 2.0},
                post_test_measurement={"power_w": 198.0, "uncertainty_pct": 2.0},
            )
        )
        self.assertEqual(result["verdict"], DEGRADATION_NOT_RESOLVABLE)
        self.assertFalse(result["resolvable"])

    def test_an_unresolvable_pair_is_not_reported_as_a_clean_result(self):
        result = assess_power_measurement_purpose(
            _case(
                pre_test_measurement={"power_w": 200.0, "uncertainty_pct": 2.0},
                post_test_measurement={"power_w": 200.0, "uncertainty_pct": 2.0},
            )
        )
        self.assertNotEqual(result["verdict"], DEGRADATION_WITHIN_ALLOWANCE)

    def test_missing_baseline_blocks_detection(self):
        case = _case()
        del case["pre_test_measurement"]
        result = assess_power_measurement_purpose(case)
        self.assertEqual(result["verdict"], BASELINE_NOT_MEASURED)
        self.assertIsNone(result["degradation_pct"])

    def test_missing_post_test_measurement_blocks_detection(self):
        case = _case()
        del case["post_test_measurement"]
        result = assess_power_measurement_purpose(case)
        self.assertEqual(result["verdict"], BASELINE_NOT_MEASURED)

    def test_objectives_survive_a_missing_baseline(self):
        case = _case()
        del case["pre_test_measurement"]
        result = assess_power_measurement_purpose(case)
        self.assertIn(COMMON_OBJECTIVE, result["objectives"])

    def test_absent_bracketed_tests_key_rejected(self):
        case = _case()
        del case["bracketed_tests"]
        with self.assertRaises(ValueError):
            assess_power_measurement_purpose(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_power_measurement_purpose(["bracketed_tests"])

    def test_non_mapping_measurement_rejected(self):
        with self.assertRaises(ValueError):
            assess_power_measurement_purpose(_case(pre_test_measurement=[200.0]))

    def test_missing_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            assess_power_measurement_purpose(
                _case(post_test_measurement={"power_w": 198.0})
            )

    def test_tighter_allowance_can_flip_a_clean_pair_to_undetectable(self):
        loose = assess_power_measurement_purpose(_case(), _policy())
        tight = assess_power_measurement_purpose(
            _case(), _policy(allowable_degradation_pct=0.1)
        )
        self.assertEqual(loose["verdict"], DEGRADATION_WITHIN_ALLOWANCE)
        self.assertEqual(tight["verdict"], DEGRADATION_NOT_RESOLVABLE)


if __name__ == "__main__":
    unittest.main()
