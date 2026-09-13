"""Contract tests for the clause 6.4.3.10.1 interconnector pull-test purpose."""

import unittest

from e2008_interconnector_pull_test_purpose_logic import (
    DRIFT_TOLERANCE,
    FORCE_TOLERANCE_N,
    MIN_SAMPLE_SIZE,
    TOLERANCE_FACTORS,
    assess_pull_test_purpose,
    lower_tolerance_bound_n,
    required_bond_strength_n,
    resistance_drift_fraction,
    sample_statistics,
    stability_findings,
    strength_findings,
    tolerance_factor,
)

GOOD_FORCES = [4.2, 4.5, 4.1, 4.6, 4.3, 4.4, 4.25, 4.35]
WIDE_FORCES = [3.1, 6.0, 3.05, 6.2, 3.2, 6.1]


def pull_records(forces):
    return [
        {"tab": "tab-%d" % index, "pull_force_n": force}
        for index, force in enumerate(forces, start=1)
    ]


class RequiredStrengthTests(unittest.TestCase):
    def test_floor_is_the_load_times_the_factor(self):
        self.assertAlmostEqual(required_bond_strength_n(1.5, 2.0), 3.0, places=9)

    def test_unity_factor_is_accepted(self):
        self.assertAlmostEqual(required_bond_strength_n(2.5, 1.0), 2.5, places=9)

    def test_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            required_bond_strength_n(1.5, 0.9)

    def test_zero_design_load_rejected(self):
        with self.assertRaises(ValueError):
            required_bond_strength_n(0.0, 2.0)

    def test_boolean_load_rejected(self):
        with self.assertRaises(ValueError):
            required_bond_strength_n(True, 2.0)

    def test_non_finite_factor_rejected(self):
        with self.assertRaises(ValueError):
            required_bond_strength_n(1.5, float("nan"))


class SampleStatisticsTests(unittest.TestCase):
    def test_count_is_the_number_of_pulls(self):
        self.assertEqual(sample_statistics(GOOD_FORCES)["count"], 8)

    def test_mean_of_the_sample(self):
        self.assertAlmostEqual(
            sample_statistics(GOOD_FORCES)["mean_n"], 4.3375, places=9
        )

    def test_sample_spread_uses_the_n_minus_one_divisor(self):
        stats = sample_statistics([2.0, 4.0, 6.0])
        self.assertAlmostEqual(stats["stdev_n"], 2.0, places=9)

    def test_weakest_pull_is_reported(self):
        self.assertAlmostEqual(
            sample_statistics(GOOD_FORCES)["minimum_n"], 4.1, places=9
        )

    def test_identical_pulls_give_zero_spread(self):
        stats = sample_statistics([5.0, 5.0, 5.0, 5.0])
        self.assertAlmostEqual(stats["stdev_n"], 0.0, places=9)

    def test_too_few_pulls_rejected(self):
        with self.assertRaises(ValueError):
            sample_statistics([4.0, 4.2])

    def test_minimum_sample_size_constant(self):
        self.assertEqual(MIN_SAMPLE_SIZE, 3)

    def test_non_sequence_sample_rejected(self):
        with self.assertRaises(ValueError):
            sample_statistics({"tab-1": 4.0})

    def test_negative_pull_force_rejected(self):
        with self.assertRaises(ValueError):
            sample_statistics([4.0, -4.2, 4.4])


class ToleranceBoundTests(unittest.TestCase):
    def test_factor_for_a_tabulated_size(self):
        self.assertAlmostEqual(tolerance_factor(8), 3.188, places=9)

    def test_untabulated_size_takes_the_conservative_smaller_entry(self):
        self.assertAlmostEqual(tolerance_factor(11), TOLERANCE_FACTORS[10], places=9)

    def test_large_sample_saturates_at_the_last_entry(self):
        self.assertAlmostEqual(tolerance_factor(400), TOLERANCE_FACTORS[50], places=9)

    def test_factor_falls_as_the_sample_grows(self):
        self.assertLess(tolerance_factor(30), tolerance_factor(6))

    def test_factor_below_minimum_size_rejected(self):
        with self.assertRaises(ValueError):
            tolerance_factor(2)

    def test_non_integer_size_rejected(self):
        with self.assertRaises(ValueError):
            tolerance_factor(8.0)

    def test_bound_sits_below_the_mean(self):
        stats = sample_statistics(GOOD_FORCES)
        self.assertLess(lower_tolerance_bound_n(stats), stats["mean_n"])

    def test_zero_spread_bound_equals_the_mean(self):
        stats = sample_statistics([5.0, 5.0, 5.0, 5.0])
        self.assertAlmostEqual(lower_tolerance_bound_n(stats), 5.0, places=9)

    def test_bound_needs_the_statistics_mapping(self):
        with self.assertRaises(ValueError):
            lower_tolerance_bound_n([8, 4.3, 0.16])

    def test_bound_rejects_incomplete_statistics(self):
        with self.assertRaises(ValueError):
            lower_tolerance_bound_n({"count": 8, "mean_n": 4.3})


class StrengthFindingTests(unittest.TestCase):
    def test_strong_sample_produces_no_finding(self):
        self.assertEqual(strength_findings(pull_records(GOOD_FORCES), 3.0), [])

    def test_weak_tab_is_named(self):
        findings = strength_findings(
            pull_records([4.2, 2.4, 4.1, 4.6]), 3.0
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("tab-2", findings[0])

    def test_force_exactly_on_the_floor_is_compliant(self):
        self.assertEqual(
            strength_findings(
                [{"tab": "tab-1", "pull_force_n": 3.0},
                 {"tab": "tab-2", "pull_force_n": 3.4}],
                3.0,
            ),
            [],
        )

    def test_duplicate_tab_rejected(self):
        with self.assertRaises(ValueError):
            strength_findings(
                [{"tab": "tab-1", "pull_force_n": 4.0},
                 {"tab": "tab-1", "pull_force_n": 4.2}],
                3.0,
            )

    def test_empty_record_list_rejected(self):
        with self.assertRaises(ValueError):
            strength_findings([], 3.0)

    def test_record_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            strength_findings([{"tab": "tab-1"}], 3.0)

    def test_blank_tab_name_rejected(self):
        with self.assertRaises(ValueError):
            strength_findings([{"tab": "  ", "pull_force_n": 4.0}], 3.0)

    def test_force_tolerance_is_small(self):
        self.assertAlmostEqual(FORCE_TOLERANCE_N, 1e-9, places=12)


class StabilityTests(unittest.TestCase):
    def test_drift_is_the_fractional_change(self):
        self.assertAlmostEqual(
            resistance_drift_fraction(0.050, 0.055), 0.1, places=9
        )

    def test_drop_in_resistance_is_a_negative_drift(self):
        self.assertAlmostEqual(
            resistance_drift_fraction(0.050, 0.045), -0.1, places=9
        )

    def test_unchanged_circuit_has_zero_drift(self):
        self.assertAlmostEqual(
            resistance_drift_fraction(0.050, 0.050), 0.0, places=9
        )

    def test_zero_pre_resistance_rejected(self):
        with self.assertRaises(ValueError):
            resistance_drift_fraction(0.0, 0.050)

    def test_stable_circuit_produces_no_finding(self):
        records = [{"circuit": "string-1", "pre_ohm": 0.050, "post_ohm": 0.051}]
        self.assertEqual(stability_findings(records, 0.05), [])

    def test_drifted_circuit_is_named(self):
        records = [{"circuit": "string-2", "pre_ohm": 0.050, "post_ohm": 0.080}]
        findings = stability_findings(records, 0.05)
        self.assertEqual(len(findings), 1)
        self.assertIn("string-2", findings[0])

    def test_negative_drift_beyond_the_allowance_is_a_finding(self):
        records = [{"circuit": "string-3", "pre_ohm": 0.050, "post_ohm": 0.020}]
        self.assertEqual(len(stability_findings(records, 0.05)), 1)

    def test_missing_resistance_key_rejected(self):
        with self.assertRaises(ValueError):
            stability_findings([{"circuit": "string-1", "pre_ohm": 0.05}], 0.05)

    def test_drift_tolerance_is_small(self):
        self.assertAlmostEqual(DRIFT_TOLERANCE, 1e-12, places=15)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "design_load_n": 1.5,
            "safety_factor": 2.0,
            "pull_records": pull_records(GOOD_FORCES),
            "resistance_records": [
                {"circuit": "string-1", "pre_ohm": 0.050, "post_ohm": 0.051},
                {"circuit": "string-2", "pre_ohm": 0.048, "post_ohm": 0.0485},
            ],
            "drift_allowance": 0.05,
        }
        spec.update(overrides)
        return spec

    def test_compliant_campaign_meets_the_purpose(self):
        result = assess_pull_test_purpose(self._spec())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["purpose_met"])

    def test_derived_floor_is_reported(self):
        result = assess_pull_test_purpose(self._spec())
        self.assertAlmostEqual(result["required_strength_n"], 3.0, places=9)

    def test_weakest_tab_is_reported(self):
        result = assess_pull_test_purpose(self._spec())
        self.assertEqual(result["weakest_tab"], "tab-3")

    def test_strength_margin_is_the_weakest_pull_over_the_floor(self):
        result = assess_pull_test_purpose(self._spec())
        self.assertAlmostEqual(result["strength_margin_n"], 1.1, places=9)

    def test_wide_spread_fails_although_every_tab_clears_the_floor(self):
        result = assess_pull_test_purpose(
            self._spec(pull_records=pull_records(WIDE_FORCES))
        )
        self.assertFalse(result["purpose_met"])
        self.assertTrue(
            any("population lower bound" in item for item in result["findings"])
        )
        self.assertLess(result["lower_bound_n"], result["required_strength_n"])

    def test_undersized_sample_is_a_finding(self):
        result = assess_pull_test_purpose(
            self._spec(pull_records=pull_records([4.2, 4.4, 4.3]),
                       min_sample_size=8)
        )
        self.assertTrue(
            any("short of the 8" in item for item in result["findings"])
        )

    def test_unstable_circuit_fails_the_campaign(self):
        result = assess_pull_test_purpose(
            self._spec(resistance_records=[
                {"circuit": "string-1", "pre_ohm": 0.050, "post_ohm": 0.090}
            ])
        )
        self.assertFalse(result["purpose_met"])

    def test_tolerance_factor_is_reported_for_the_sample(self):
        result = assess_pull_test_purpose(self._spec())
        self.assertAlmostEqual(result["tolerance_factor"], 3.188, places=9)

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["drift_allowance"]
        with self.assertRaises(ValueError):
            assess_pull_test_purpose(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_pull_test_purpose(["design_load_n"])

    def test_min_sample_size_below_the_floor_rejected(self):
        with self.assertRaises(ValueError):
            assess_pull_test_purpose(self._spec(min_sample_size=2))

    def test_non_integer_min_sample_size_rejected(self):
        with self.assertRaises(ValueError):
            assess_pull_test_purpose(self._spec(min_sample_size=8.0))


if __name__ == "__main__":
    unittest.main()
