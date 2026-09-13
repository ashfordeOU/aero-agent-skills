"""Contract tests for the clause 6.4.3.12.1 illumination stability purpose logic."""

import unittest

from e2008_illumination_stability_test_purpose_logic import (
    COMMON_OBJECTIVE,
    DEFAULT_STABILITY_POLICY,
    ILLUMINATION_STABILITY_CHARACTERISED,
    MEASUREMENT_INADEQUATE,
    MEASUREMENT_NOT_PLANNED,
    STABILITY_TEST_NOT_REQUIRED,
    assess_illumination_stability_purpose,
    drift_resolvable,
    drift_within_acceptance,
    measurement_point_count,
    mechanism_inventory,
    projected_drift_fraction,
    stability_objectives,
    temperature_representative,
    validate_stability_policy,
)

MECHANISMS = [
    "cell-light-induced-degradation",
    "coverglass-adhesive-photodarkening",
]


def _policy(**overrides):
    policy = dict(DEFAULT_STABILITY_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "stability_mechanisms": list(MECHANISMS),
        "mission": {
            "illuminated_hours": 20000.0,
            "drift_rate_per_hour": 1.0e-6,
            "reference_temperature_c": 25.0,
        },
        "measurement": {
            "soak_hours": 48.0,
            "sample_interval_hours": 12.0,
            "uncertainty_fraction": 1.0e-5,
            "soak_temperature_c": 25.0,
        },
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_stability_policy(DEFAULT_STABILITY_POLICY),
            DEFAULT_STABILITY_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_stability_policy("stability")

    def test_zero_significance_trigger_rejected(self):
        with self.assertRaises(ValueError):
            validate_stability_policy(_policy(significance_trigger_hours=0.0))

    def test_a_resolution_margin_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_stability_policy(_policy(resolution_margin=0.5))

    def test_fractional_minimum_point_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_stability_policy(_policy(min_measurement_points=2.5))

    def test_negative_temperature_offset_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_stability_policy(_policy(max_temperature_offset_c=-1.0))


class MechanismTests(unittest.TestCase):
    def test_each_mechanism_contributes_an_objective(self):
        objectives = stability_objectives(MECHANISMS)
        self.assertIn("illuminated-output-drift-bound", objectives)
        self.assertIn("optical-path-transmittance-loss-bound", objectives)

    def test_the_shared_objective_is_appended_once(self):
        objectives = stability_objectives(MECHANISMS)
        self.assertEqual(objectives.count(COMMON_OBJECTIVE), 1)

    def test_no_mechanism_yields_no_objective(self):
        self.assertEqual(stability_objectives([]), ())

    def test_a_repeated_mechanism_is_grouped_once(self):
        grouped = mechanism_inventory(
            ["metastable-defect-settling", "metastable-defect-settling"]
        )
        self.assertEqual(grouped, ("metastable-defect-settling",))

    def test_an_unknown_mechanism_is_rejected(self):
        with self.assertRaises(ValueError):
            mechanism_inventory(["cell-radiation-damage"])

    def test_a_bare_string_is_not_a_collection_of_mechanisms(self):
        with self.assertRaises(ValueError):
            mechanism_inventory("cell-light-induced-degradation")


class DriftTests(unittest.TestCase):
    def test_drift_is_the_rate_over_the_illuminated_interval(self):
        self.assertAlmostEqual(
            projected_drift_fraction(1.0e-6, 48.0), 4.8e-5, places=12
        )

    def test_no_illuminated_time_accumulates_no_drift(self):
        self.assertAlmostEqual(projected_drift_fraction(1.0e-6, 0.0), 0.0, places=12)

    def test_drift_is_capped_at_the_whole_output(self):
        self.assertAlmostEqual(
            projected_drift_fraction(1.0e-2, 1.0e6), 1.0, places=12
        )

    def test_a_negative_drift_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            projected_drift_fraction(-1.0e-6, 48.0)

    def test_a_drift_inside_the_acceptance_bound_is_accepted(self):
        self.assertTrue(drift_within_acceptance(0.005, _policy()))

    def test_a_drift_exactly_at_the_acceptance_bound_is_accepted(self):
        policy = _policy(max_allowable_drift_fraction=0.02)
        self.assertTrue(
            drift_within_acceptance(policy["max_allowable_drift_fraction"], policy)
        )

    def test_a_drift_beyond_the_acceptance_bound_is_refused(self):
        self.assertFalse(drift_within_acceptance(0.5, _policy()))


class ResolutionTests(unittest.TestCase):
    def test_a_drift_well_above_the_uncertainty_is_resolvable(self):
        self.assertTrue(drift_resolvable(4.8e-5, 1.0e-5, _policy()))

    def test_a_drift_exactly_at_the_resolution_margin_is_resolvable(self):
        policy = _policy(resolution_margin=3.0)
        drift = 3.0 * 1.6e-5
        self.assertAlmostEqual(drift, 4.8e-5, places=9)
        self.assertTrue(drift_resolvable(drift, 1.6e-5, policy))

    def test_a_drift_the_size_of_the_uncertainty_is_not_resolvable(self):
        self.assertFalse(drift_resolvable(1.0e-5, 1.0e-5, _policy()))

    def test_zero_measurement_uncertainty_is_rejected(self):
        with self.assertRaises(ValueError):
            drift_resolvable(4.8e-5, 0.0, _policy())

    def test_an_evenly_sampled_soak_counts_both_ends(self):
        self.assertEqual(measurement_point_count(48.0, 12.0), 5)

    def test_an_interval_equal_to_the_soak_gives_two_points(self):
        self.assertEqual(measurement_point_count(48.0, 48.0), 2)

    def test_an_interval_longer_than_the_soak_gives_one_point(self):
        self.assertEqual(measurement_point_count(48.0, 100.0), 1)

    def test_zero_sample_interval_rejected(self):
        with self.assertRaises(ValueError):
            measurement_point_count(48.0, 0.0)

    def test_a_soak_at_the_reference_temperature_is_representative(self):
        self.assertTrue(temperature_representative(25.0, 25.0, _policy()))

    def test_a_soak_exactly_at_the_offset_allowance_is_representative(self):
        policy = _policy(max_temperature_offset_c=2.0)
        self.assertAlmostEqual(
            abs(27.0 - 25.0), policy["max_temperature_offset_c"], places=9
        )
        self.assertTrue(temperature_representative(27.0, 25.0, policy))

    def test_a_soak_far_from_the_reference_temperature_is_not_representative(self):
        self.assertFalse(temperature_representative(60.0, 25.0, _policy()))


class PurposeAssessmentTests(unittest.TestCase):
    def test_an_adequate_plan_characterises_the_stability(self):
        result = assess_illumination_stability_purpose(_case())
        self.assertEqual(result["verdict"], ILLUMINATION_STABILITY_CHARACTERISED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["required"])

    def test_the_mission_drift_is_reported(self):
        result = assess_illumination_stability_purpose(_case())
        self.assertAlmostEqual(
            result["projected_mission_drift_fraction"], 0.02, places=9
        )

    def test_the_soak_drift_and_point_count_are_reported(self):
        result = assess_illumination_stability_purpose(_case())
        self.assertAlmostEqual(
            result["projected_soak_drift_fraction"], 4.8e-5, places=12
        )
        self.assertEqual(result["measurement_points"], 5)

    def test_no_declared_mechanism_means_no_test_required(self):
        result = assess_illumination_stability_purpose(
            _case(stability_mechanisms=[])
        )
        self.assertEqual(result["verdict"], STABILITY_TEST_NOT_REQUIRED)
        self.assertFalse(result["required"])

    def test_too_little_illuminated_time_does_not_earn_the_test(self):
        case = _case()
        case["mission"]["illuminated_hours"] = 10.0
        result = assess_illumination_stability_purpose(case)
        self.assertEqual(result["verdict"], STABILITY_TEST_NOT_REQUIRED)

    def test_illuminated_time_exactly_at_the_trigger_earns_the_test(self):
        policy = _policy(significance_trigger_hours=20000.0)
        result = assess_illumination_stability_purpose(_case(), policy)
        self.assertAlmostEqual(
            result["illuminated_hours"],
            policy["significance_trigger_hours"],
            places=9,
        )
        self.assertTrue(result["required"])

    def test_a_required_but_unplanned_soak_is_its_own_verdict(self):
        case = _case()
        del case["measurement"]
        result = assess_illumination_stability_purpose(case)
        self.assertEqual(result["verdict"], MEASUREMENT_NOT_PLANNED)
        self.assertIsNone(result["measurement_points"])

    def test_an_unresolvable_drift_is_inadequate(self):
        case = _case()
        case["measurement"]["uncertainty_fraction"] = 1.0e-3
        result = assess_illumination_stability_purpose(case)
        self.assertEqual(result["verdict"], MEASUREMENT_INADEQUATE)
        self.assertFalse(result["soak_drift_resolvable"])

    def test_too_few_measurement_points_are_inadequate(self):
        case = _case()
        case["measurement"]["sample_interval_hours"] = 48.0
        result = assess_illumination_stability_purpose(case)
        self.assertEqual(result["verdict"], MEASUREMENT_INADEQUATE)
        self.assertEqual(result["measurement_points"], 2)

    def test_a_soak_off_the_reference_temperature_is_inadequate(self):
        case = _case()
        case["measurement"]["soak_temperature_c"] = 60.0
        result = assess_illumination_stability_purpose(case)
        self.assertEqual(result["verdict"], MEASUREMENT_INADEQUATE)
        self.assertFalse(result["temperature_representative"])

    def test_every_inadequacy_is_reported_not_only_the_first(self):
        case = _case()
        case["measurement"]["uncertainty_fraction"] = 1.0e-3
        case["measurement"]["sample_interval_hours"] = 48.0
        case["measurement"]["soak_temperature_c"] = 60.0
        result = assess_illumination_stability_purpose(case)
        self.assertEqual(len(result["findings"]), 3)

    def test_objectives_survive_an_unplanned_soak(self):
        case = _case()
        del case["measurement"]
        result = assess_illumination_stability_purpose(case)
        self.assertIn(COMMON_OBJECTIVE, result["objectives"])

    def test_absent_mechanism_key_rejected(self):
        case = _case()
        del case["stability_mechanisms"]
        with self.assertRaises(ValueError):
            assess_illumination_stability_purpose(case)

    def test_missing_mission_block_rejected(self):
        case = _case()
        del case["mission"]
        with self.assertRaises(ValueError):
            assess_illumination_stability_purpose(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_illumination_stability_purpose(["stability_mechanisms"])

    def test_non_mapping_measurement_rejected(self):
        with self.assertRaises(ValueError):
            assess_illumination_stability_purpose(_case(measurement=[48.0]))


if __name__ == "__main__":
    unittest.main()
