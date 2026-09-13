"""Contract tests for the clause 6.4.3.16.1 assembly capacitance purpose logic."""

import math
import unittest

from e2008_sca_capacitance_test_purpose_logic import (
    ASSEMBLY_MEASUREMENT_NOT_PLANNED,
    COMMON_OBJECTIVE,
    DEFAULT_EXTRAPOLATION_POLICY,
    EXTRAPOLATION_INADEQUATE,
    PANEL_BEHAVIOUR_CHARACTERISED,
    PANEL_CHARACTERISATION_NOT_REQUIRED,
    assess_sca_capacitance_purpose,
    behaviour_inventory,
    extrapolation_objectives,
    panel_capacitance_f,
    panel_discharge_energy_j,
    panel_displacement_current_a,
    panel_stored_charge_c,
    precision_adequate,
    representativeness_ratio,
    sample_count_adequate,
    sample_is_representative,
    sample_statistics,
    specific_capacitance_f_per_m2,
    validate_extrapolation_policy,
)

BEHAVIOURS = [
    "panel-electrostatic-discharge-energy",
    "panel-regulator-switching-transient",
]

READINGS = [2.00e-7, 2.02e-7, 1.98e-7, 2.00e-7]
NOISY_READINGS = [1.00e-7, 3.00e-7, 2.00e-7, 2.00e-7]


def _policy(**overrides):
    policy = dict(DEFAULT_EXTRAPOLATION_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "panel_behaviours": list(BEHAVIOURS),
        "panel": {
            "assemblies_in_series": 20,
            "strings_in_parallel": 12,
            "working_point_v": 100.0,
            "step_rate_v_per_s": 1.0e5,
        },
        "assembly_measurement": {
            "capacitances_f": list(READINGS),
            "active_area_m2": 0.004,
            "reference_specific_f_per_m2": 5.0e-5,
        },
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_extrapolation_policy(DEFAULT_EXTRAPOLATION_POLICY),
            DEFAULT_EXTRAPOLATION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_extrapolation_policy("extrapolate")

    def test_a_single_assembly_basis_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_extrapolation_policy(_policy(min_sample_count=1))

    def test_a_fractional_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_extrapolation_policy(_policy(min_sample_count=3.5))

    def test_a_standard_error_limit_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_extrapolation_policy(_policy(max_relative_standard_error=1.0))

    def test_a_representativeness_band_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_extrapolation_policy(_policy(representativeness_band=1.0))

    def test_zero_significance_trigger_rejected(self):
        with self.assertRaises(ValueError):
            validate_extrapolation_policy(_policy(significance_trigger_f=0.0))


class SampleTests(unittest.TestCase):
    def test_the_mean_is_the_arithmetic_mean_of_the_readings(self):
        stats = sample_statistics(READINGS)
        self.assertAlmostEqual(_ratio(stats["mean_f"], 2.0e-7), 1.0, places=12)

    def test_the_count_is_reported(self):
        self.assertEqual(sample_statistics(READINGS)["count"], 4)

    def test_the_scatter_uses_the_sample_standard_deviation(self):
        expected = math.sqrt((2.0 * (2.0e-9 ** 2)) / 3.0)
        stats = sample_statistics(READINGS)
        self.assertAlmostEqual(
            _ratio(stats["sample_standard_deviation_f"], expected), 1.0, places=10
        )

    def test_the_relative_standard_error_shrinks_with_the_root_of_the_count(self):
        stats = sample_statistics(READINGS)
        expected = stats["sample_standard_deviation_f"] / (
            stats["mean_f"] * math.sqrt(stats["count"])
        )
        self.assertAlmostEqual(
            _ratio(stats["relative_standard_error"], expected), 1.0, places=12
        )

    def test_identical_readings_report_no_scatter(self):
        stats = sample_statistics([2.0e-7, 2.0e-7, 2.0e-7])
        self.assertAlmostEqual(stats["relative_standard_error"], 0.0, places=12)

    def test_one_reading_is_rejected_not_treated_as_a_sample(self):
        with self.assertRaises(ValueError):
            sample_statistics([2.0e-7])

    def test_a_non_positive_reading_rejected(self):
        with self.assertRaises(ValueError):
            sample_statistics([2.0e-7, 0.0])

    def test_a_bare_number_is_not_a_reading_sequence(self):
        with self.assertRaises(ValueError):
            sample_statistics(2.0e-7)


class ExtrapolationBasisTests(unittest.TestCase):
    def test_specific_capacitance_is_value_over_active_area(self):
        self.assertAlmostEqual(
            _ratio(specific_capacitance_f_per_m2(2.0e-7, 0.004), 5.0e-5),
            1.0,
            places=12,
        )

    def test_zero_active_area_rejected(self):
        with self.assertRaises(ValueError):
            specific_capacitance_f_per_m2(2.0e-7, 0.0)

    def test_a_sample_matching_the_reference_has_unit_ratio(self):
        self.assertAlmostEqual(
            representativeness_ratio(5.0e-5, 5.0e-5), 1.0, places=12
        )

    def test_a_sample_at_the_band_edge_is_still_representative(self):
        policy = _policy(representativeness_band=0.20)
        self.assertAlmostEqual(
            abs(1.20 - 1.0), policy["representativeness_band"], places=9
        )
        self.assertTrue(sample_is_representative(1.20, policy))

    def test_a_sample_at_half_the_reference_is_not_representative(self):
        self.assertFalse(sample_is_representative(0.5, _policy()))

    def test_a_negative_ratio_rejected(self):
        with self.assertRaises(ValueError):
            sample_is_representative(-1.0, _policy())

    def test_the_minimum_sample_count_is_adequate(self):
        self.assertTrue(sample_count_adequate(3, _policy(min_sample_count=3)))

    def test_one_assembly_short_of_the_minimum_is_not_adequate(self):
        self.assertFalse(sample_count_adequate(2, _policy(min_sample_count=3)))

    def test_a_standard_error_exactly_at_the_limit_is_adequate(self):
        policy = _policy(max_relative_standard_error=0.05)
        self.assertTrue(
            precision_adequate(policy["max_relative_standard_error"], policy)
        )

    def test_a_standard_error_far_above_the_limit_is_not_adequate(self):
        self.assertFalse(precision_adequate(0.5, _policy()))


class PanelScalingTests(unittest.TestCase):
    def test_series_assemblies_divide_and_parallel_strings_multiply(self):
        self.assertAlmostEqual(
            _ratio(panel_capacitance_f(2.0e-7, 20, 12), 1.2e-7), 1.0, places=12
        )

    def test_a_one_by_one_panel_is_the_assembly_value(self):
        self.assertAlmostEqual(
            _ratio(panel_capacitance_f(2.0e-7, 1, 1), 2.0e-7), 1.0, places=12
        )

    def test_doubling_the_series_count_halves_the_panel_value(self):
        long_string = panel_capacitance_f(2.0e-7, 40, 12)
        short_string = panel_capacitance_f(2.0e-7, 20, 12)
        self.assertAlmostEqual(
            _ratio(short_string, 2.0 * long_string), 1.0, places=12
        )

    def test_a_fractional_series_count_rejected(self):
        with self.assertRaises(ValueError):
            panel_capacitance_f(2.0e-7, 20.5, 12)

    def test_zero_parallel_strings_rejected(self):
        with self.assertRaises(ValueError):
            panel_capacitance_f(2.0e-7, 20, 0)

    def test_stored_charge_is_capacitance_times_voltage(self):
        self.assertAlmostEqual(
            _ratio(panel_stored_charge_c(1.2e-7, 100.0), 1.2e-5), 1.0, places=12
        )

    def test_discharge_energy_is_half_c_v_squared(self):
        self.assertAlmostEqual(
            _ratio(panel_discharge_energy_j(1.2e-7, 100.0), 6.0e-4), 1.0, places=12
        )

    def test_displacement_current_is_capacitance_times_rate(self):
        self.assertAlmostEqual(
            _ratio(panel_displacement_current_a(1.2e-7, 1.0e5), 1.2e-2),
            1.0,
            places=12,
        )

    def test_a_non_finite_step_rate_rejected(self):
        with self.assertRaises(ValueError):
            panel_displacement_current_a(1.2e-7, float("inf"))


class ObjectiveTests(unittest.TestCase):
    def test_each_behaviour_contributes_an_objective(self):
        objectives = extrapolation_objectives(BEHAVIOURS)
        self.assertIn("panel-stored-energy-feeding-an-arc", objectives)
        self.assertIn("panel-displacement-current-at-switching", objectives)

    def test_the_shared_objective_is_appended_once(self):
        objectives = extrapolation_objectives(BEHAVIOURS)
        self.assertEqual(objectives.count(COMMON_OBJECTIVE), 1)

    def test_no_behaviour_yields_no_objective(self):
        self.assertEqual(extrapolation_objectives([]), ())

    def test_a_repeated_behaviour_is_grouped_once(self):
        grouped = behaviour_inventory(
            [
                "panel-bus-stability-margin",
                "panel-bus-stability-margin",
            ]
        )
        self.assertEqual(grouped, ("panel-bus-stability-margin",))

    def test_unknown_behaviour_rejected(self):
        with self.assertRaises(ValueError):
            behaviour_inventory(["panel-deployment-shock"])

    def test_a_bare_string_is_not_a_behaviour_collection(self):
        with self.assertRaises(ValueError):
            behaviour_inventory("panel-bus-stability-margin")


class PurposeAssessmentTests(unittest.TestCase):
    def test_an_adequate_basis_characterises_the_panel(self):
        result = assess_sca_capacitance_purpose(_case())
        self.assertEqual(result["verdict"], PANEL_BEHAVIOUR_CHARACTERISED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["required"])

    def test_the_panel_value_is_extrapolated_from_the_sample_mean(self):
        result = assess_sca_capacitance_purpose(_case())
        self.assertAlmostEqual(
            _ratio(result["panel_capacitance_f"], 1.2e-7), 1.0, places=12
        )

    def test_the_panel_quantities_follow_the_extrapolated_value(self):
        result = assess_sca_capacitance_purpose(_case())
        self.assertAlmostEqual(
            _ratio(result["panel_stored_charge_c"], 1.2e-5), 1.0, places=12
        )
        self.assertAlmostEqual(
            _ratio(result["panel_discharge_energy_j"], 6.0e-4), 1.0, places=12
        )
        self.assertAlmostEqual(
            _ratio(result["panel_displacement_current_a"], 1.2e-2), 1.0, places=12
        )

    def test_no_declared_behaviour_means_no_panel_characterisation(self):
        result = assess_sca_capacitance_purpose(_case(panel_behaviours=[]))
        self.assertEqual(result["verdict"], PANEL_CHARACTERISATION_NOT_REQUIRED)
        self.assertFalse(result["required"])

    def test_a_declared_behaviour_without_a_measurement_is_its_own_verdict(self):
        case = _case()
        del case["assembly_measurement"]
        result = assess_sca_capacitance_purpose(case)
        self.assertEqual(result["verdict"], ASSEMBLY_MEASUREMENT_NOT_PLANNED)
        self.assertIsNone(result["panel_capacitance_f"])

    def test_a_panel_value_below_the_trigger_earns_nothing(self):
        result = assess_sca_capacitance_purpose(
            _case(), _policy(significance_trigger_f=1.0)
        )
        self.assertEqual(result["verdict"], PANEL_CHARACTERISATION_NOT_REQUIRED)
        self.assertFalse(result["required"])

    def test_a_panel_value_exactly_at_the_trigger_earns_the_campaign(self):
        trigger = panel_capacitance_f(2.0e-7, 20, 12)
        result = assess_sca_capacitance_purpose(
            _case(), _policy(significance_trigger_f=trigger)
        )
        self.assertAlmostEqual(
            _ratio(result["panel_capacitance_f"], trigger), 1.0, places=12
        )
        self.assertTrue(result["required"])

    def test_too_few_assemblies_makes_the_extrapolation_inadequate(self):
        result = assess_sca_capacitance_purpose(_case(), _policy(min_sample_count=8))
        self.assertEqual(result["verdict"], EXTRAPOLATION_INADEQUATE)
        self.assertFalse(result["sample_count_adequate"])

    def test_a_scattered_sample_makes_the_extrapolation_inadequate(self):
        case = _case()
        case["assembly_measurement"]["capacitances_f"] = list(NOISY_READINGS)
        result = assess_sca_capacitance_purpose(case)
        self.assertEqual(result["verdict"], EXTRAPOLATION_INADEQUATE)
        self.assertFalse(result["precision_adequate"])

    def test_an_unrepresentative_sample_makes_the_extrapolation_inadequate(self):
        case = _case()
        case["assembly_measurement"]["reference_specific_f_per_m2"] = 1.0e-4
        result = assess_sca_capacitance_purpose(case)
        self.assertEqual(result["verdict"], EXTRAPOLATION_INADEQUATE)
        self.assertFalse(result["sample_representative"])

    def test_every_inadequacy_is_reported_not_only_the_first(self):
        case = _case()
        case["assembly_measurement"]["capacitances_f"] = list(NOISY_READINGS)
        case["assembly_measurement"]["reference_specific_f_per_m2"] = 1.0e-4
        result = assess_sca_capacitance_purpose(case, _policy(min_sample_count=8))
        self.assertEqual(len(result["findings"]), 3)

    def test_objectives_survive_an_unplanned_measurement(self):
        case = _case()
        del case["assembly_measurement"]
        result = assess_sca_capacitance_purpose(case)
        self.assertIn(COMMON_OBJECTIVE, result["objectives"])

    def test_absent_behaviour_key_rejected(self):
        case = _case()
        del case["panel_behaviours"]
        with self.assertRaises(ValueError):
            assess_sca_capacitance_purpose(case)

    def test_missing_panel_block_rejected(self):
        case = _case()
        del case["panel"]
        with self.assertRaises(ValueError):
            assess_sca_capacitance_purpose(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_sca_capacitance_purpose(["panel_behaviours"])

    def test_non_mapping_measurement_rejected(self):
        with self.assertRaises(ValueError):
            assess_sca_capacitance_purpose(_case(assembly_measurement=[2.0e-7]))


if __name__ == "__main__":
    unittest.main()
