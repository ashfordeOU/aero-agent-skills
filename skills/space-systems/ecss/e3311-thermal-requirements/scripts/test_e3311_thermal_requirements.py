"""Contract test for the e3311 thermal-requirements leaf (stdlib unittest)."""

import unittest

from e3311_thermal_requirements_logic import (
    DEFAULT_THERMAL_POLICY,
    VERDICT_MET,
    VERDICT_NOT_MET,
    arrhenius_acceleration_factor,
    assess_decomposition_onset,
    assess_temperature_envelope,
    assess_thermal_requirements,
    assess_thermal_stability,
    equivalent_time_at_reference_h,
    hottest_segment,
    kelvin_from_celsius,
    temperature_margin_k,
    validate_thermal_policy,
    validate_thermal_profile,
)

REFERENCE_K = 350.0
ACTIVATION = 1.6e5


def profile(*segments):
    if segments:
        return list(segments)
    return [
        {"label": "cruise", "temperature_k": 300.0, "duration_h": 8000.0},
        {"label": "hot-case-dwell", "temperature_k": 330.0, "duration_h": 200.0},
    ]


def envelope_case(**kw):
    case = {
        "qualification_hot_limit_k": 358.15,
        "qualification_cold_limit_k": 233.15,
        "predicted_hot_k": 338.15,
        "predicted_cold_k": 253.15,
        "prediction_uncertainty_k": 5.0,
    }
    case.update(kw)
    return case


def onset_case(**kw):
    case = {
        "decomposition_onset_k": 450.0,
        "predicted_hot_k": 338.15,
        "prediction_uncertainty_k": 5.0,
    }
    case.update(kw)
    return case


def stability_case(**kw):
    case = {
        "qualification_dwell_temperature_k": REFERENCE_K,
        "qualification_dwell_hours": 1000.0,
        "activation_energy_j_per_mol": ACTIVATION,
        "profile": profile(),
    }
    case.update(kw)
    return case


def full_case(**kw):
    case = {
        "prediction_uncertainty_k": 5.0,
        "envelope": envelope_case(),
        "onset": onset_case(),
        "stability": stability_case(),
    }
    case.update(kw)
    return case


class TestPolicyAndUnits(unittest.TestCase):
    def test_default_policy_is_valid(self):
        self.assertIs(
            validate_thermal_policy(DEFAULT_THERMAL_POLICY), DEFAULT_THERMAL_POLICY
        )

    def test_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_thermal_policy("margin 10 K")

    def test_zero_activation_energy_in_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_thermal_policy(
                dict(DEFAULT_THERMAL_POLICY, activation_energy_j_per_mol=0.0)
            )

    def test_negative_qualification_margin_raises(self):
        with self.assertRaises(ValueError):
            validate_thermal_policy(
                dict(DEFAULT_THERMAL_POLICY, qualification_margin_k=-1.0)
            )

    def test_celsius_converts_to_kelvin(self):
        self.assertAlmostEqual(kelvin_from_celsius(0.0), 273.15, places=9)

    def test_celsius_below_absolute_zero_raises(self):
        with self.assertRaises(ValueError):
            kelvin_from_celsius(-300.0)

    def test_celsius_rejects_a_boolean(self):
        with self.assertRaises(ValueError):
            kelvin_from_celsius(True)


class TestArrhenius(unittest.TestCase):
    def test_factor_is_unity_at_the_reference(self):
        self.assertAlmostEqual(
            arrhenius_acceleration_factor(REFERENCE_K, REFERENCE_K, ACTIVATION),
            1.0,
            places=9,
        )

    def test_hotter_than_the_reference_accelerates(self):
        self.assertGreater(
            arrhenius_acceleration_factor(380.0, REFERENCE_K, ACTIVATION), 10.0
        )

    def test_colder_than_the_reference_decelerates(self):
        self.assertLess(
            arrhenius_acceleration_factor(300.0, REFERENCE_K, ACTIVATION), 0.01
        )

    def test_factors_are_reciprocal_across_the_reference(self):
        up = arrhenius_acceleration_factor(380.0, REFERENCE_K, ACTIVATION)
        down = arrhenius_acceleration_factor(REFERENCE_K, 380.0, ACTIVATION)
        self.assertAlmostEqual(up * down, 1.0, places=9)

    def test_zero_kelvin_raises(self):
        with self.assertRaises(ValueError):
            arrhenius_acceleration_factor(0.0, REFERENCE_K, ACTIVATION)

    def test_negative_activation_energy_raises(self):
        with self.assertRaises(ValueError):
            arrhenius_acceleration_factor(REFERENCE_K, REFERENCE_K, -1.0)


class TestProfile(unittest.TestCase):
    def test_a_valid_profile_normalizes(self):
        segments = validate_thermal_profile(profile())
        self.assertEqual([s["label"] for s in segments], ["cruise", "hot-case-dwell"])

    def test_a_missing_label_is_filled_in(self):
        segments = validate_thermal_profile(
            [{"temperature_k": 300.0, "duration_h": 1.0}]
        )
        self.assertEqual(segments[0]["label"], "segment-0")

    def test_an_empty_profile_raises(self):
        with self.assertRaises(ValueError):
            validate_thermal_profile([])

    def test_a_non_list_profile_raises(self):
        with self.assertRaises(ValueError):
            validate_thermal_profile({"temperature_k": 300.0})

    def test_a_zero_total_duration_raises(self):
        with self.assertRaises(ValueError):
            validate_thermal_profile([{"temperature_k": 300.0, "duration_h": 0.0}])

    def test_a_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            validate_thermal_profile([{"temperature_k": 300.0, "duration_h": -1.0}])

    def test_a_blank_label_raises(self):
        with self.assertRaises(ValueError):
            validate_thermal_profile(
                [{"label": "   ", "temperature_k": 300.0, "duration_h": 1.0}]
            )

    def test_the_hottest_segment_drives(self):
        self.assertEqual(hottest_segment(profile())["label"], "hot-case-dwell")


class TestEquivalentTime(unittest.TestCase):
    def test_time_at_the_reference_maps_one_to_one(self):
        equivalent = equivalent_time_at_reference_h(
            [{"label": "soak", "temperature_k": REFERENCE_K, "duration_h": 120.0}],
            REFERENCE_K,
            ACTIVATION,
        )
        self.assertAlmostEqual(equivalent, 120.0, places=6)

    def test_cooler_segments_cost_less_than_their_clock_time(self):
        equivalent = equivalent_time_at_reference_h(profile(), REFERENCE_K, ACTIVATION)
        self.assertLess(equivalent, 8200.0)

    def test_a_hot_excursion_can_dominate_a_long_cruise(self):
        equivalent = equivalent_time_at_reference_h(
            profile(
                {"label": "cruise", "temperature_k": 290.0, "duration_h": 20000.0},
                {"label": "excursion", "temperature_k": 380.0, "duration_h": 10.0},
            ),
            REFERENCE_K,
            ACTIVATION,
        )
        self.assertGreater(equivalent, 100.0)

    def test_segments_are_additive(self):
        one = equivalent_time_at_reference_h(
            [{"temperature_k": 330.0, "duration_h": 100.0}], REFERENCE_K, ACTIVATION
        )
        two = equivalent_time_at_reference_h(
            [
                {"temperature_k": 330.0, "duration_h": 60.0},
                {"temperature_k": 330.0, "duration_h": 40.0},
            ],
            REFERENCE_K,
            ACTIVATION,
        )
        self.assertAlmostEqual(one, two, places=9)


class TestTemperatureEnvelope(unittest.TestCase):
    def test_a_comfortable_envelope_passes(self):
        result = assess_temperature_envelope(envelope_case())
        self.assertTrue(result["compliant"])

    def test_the_uncertainty_widens_both_predictions(self):
        result = assess_temperature_envelope(envelope_case())
        self.assertAlmostEqual(
            result["bounds"]["hot"]["predicted_with_uncertainty_k"], 343.15, places=9
        )
        self.assertAlmostEqual(
            result["bounds"]["cold"]["predicted_with_uncertainty_k"], 248.15, places=9
        )

    def test_a_hot_margin_exactly_on_the_requirement_passes(self):
        result = assess_temperature_envelope(
            envelope_case(predicted_hot_k=343.15, prediction_uncertainty_k=5.0)
        )
        self.assertAlmostEqual(result["bounds"]["hot"]["margin_k"], 10.0, places=9)
        self.assertTrue(result["compliant"])

    def test_a_thin_hot_margin_fails_and_names_the_bound(self):
        result = assess_temperature_envelope(envelope_case(predicted_hot_k=350.0))
        self.assertFalse(result["compliant"])
        self.assertFalse(result["bounds"]["hot"]["compliant"])
        self.assertTrue(result["bounds"]["cold"]["compliant"])

    def test_a_thin_cold_margin_fails(self):
        result = assess_temperature_envelope(envelope_case(predicted_cold_k=235.0))
        self.assertFalse(result["compliant"])
        self.assertFalse(result["bounds"]["cold"]["compliant"])

    def test_an_inverted_qualification_range_raises(self):
        with self.assertRaises(ValueError):
            assess_temperature_envelope(
                envelope_case(qualification_cold_limit_k=400.0)
            )

    def test_a_negative_uncertainty_raises(self):
        with self.assertRaises(ValueError):
            assess_temperature_envelope(envelope_case(prediction_uncertainty_k=-1.0))

    def test_a_non_mapping_case_raises(self):
        with self.assertRaises(ValueError):
            assess_temperature_envelope(["hot", 358.15])


class TestDecompositionOnset(unittest.TestCase):
    def test_a_wide_onset_margin_passes(self):
        result = assess_decomposition_onset(onset_case())
        self.assertTrue(result["compliant"])

    def test_a_margin_exactly_on_the_requirement_passes(self):
        result = assess_decomposition_onset(
            onset_case(decomposition_onset_k=373.15, predicted_hot_k=338.15)
        )
        self.assertAlmostEqual(result["margin_k"], 30.0, places=9)
        self.assertTrue(result["compliant"])

    def test_a_thin_onset_margin_fails(self):
        result = assess_decomposition_onset(
            onset_case(decomposition_onset_k=350.0)
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_the_uncertainty_is_added_to_the_hot_prediction(self):
        result = assess_decomposition_onset(onset_case())
        self.assertAlmostEqual(result["hottest_predicted_k"], 343.15, places=9)

    def test_a_missing_onset_raises(self):
        case = onset_case()
        del case["decomposition_onset_k"]
        with self.assertRaises(ValueError):
            assess_decomposition_onset(case)


class TestThermalStability(unittest.TestCase):
    def test_a_cool_mission_leaves_dwell_unused(self):
        result = assess_thermal_stability(stability_case())
        self.assertTrue(result["compliant"])
        self.assertLess(result["utilization"], 1.0)

    def test_the_driving_segment_is_named(self):
        result = assess_thermal_stability(stability_case())
        self.assertEqual(result["driving_segment"], "hot-case-dwell")

    def test_utilization_exactly_at_the_limit_passes(self):
        result = assess_thermal_stability(
            stability_case(
                qualification_dwell_hours=500.0,
                profile=profile(
                    {
                        "label": "soak",
                        "temperature_k": REFERENCE_K,
                        "duration_h": 500.0,
                    }
                ),
            )
        )
        self.assertAlmostEqual(result["utilization"], 1.0, places=6)
        self.assertTrue(result["compliant"])

    def test_a_hot_mission_overruns_the_dwell(self):
        result = assess_thermal_stability(
            stability_case(
                profile=profile(
                    {"label": "hot-soak", "temperature_k": 390.0, "duration_h": 400.0}
                )
            )
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(result["findings"])

    def test_the_policy_activation_energy_is_used_when_the_case_omits_it(self):
        case = stability_case()
        del case["activation_energy_j_per_mol"]
        result = assess_thermal_stability(case)
        self.assertGreater(result["equivalent_time_h"], 0.0)

    def test_a_zero_dwell_raises(self):
        with self.assertRaises(ValueError):
            assess_thermal_stability(stability_case(qualification_dwell_hours=0.0))

    def test_a_missing_profile_raises(self):
        case = stability_case()
        del case["profile"]
        with self.assertRaises(ValueError):
            assess_thermal_stability(case)


class TestFullAssessment(unittest.TestCase):
    def test_a_sound_thermal_design_is_met(self):
        report = assess_thermal_requirements(full_case())
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["failed_checks"], [])

    def test_a_thin_envelope_is_the_only_failure(self):
        case = full_case()
        case["envelope"] = envelope_case(predicted_hot_k=350.0)
        report = assess_thermal_requirements(case)
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)
        self.assertEqual(report["failed_checks"], ["temperature-envelope"])

    def test_the_shared_uncertainty_reaches_a_subcase_that_omits_it(self):
        case = full_case(prediction_uncertainty_k=20.0)
        case["onset"] = {"decomposition_onset_k": 450.0, "predicted_hot_k": 338.15}
        report = assess_thermal_requirements(case)
        self.assertAlmostEqual(
            report["checks"]["decomposition-onset"]["hottest_predicted_k"],
            358.15,
            places=9,
        )

    def test_a_subcase_uncertainty_overrides_the_shared_one(self):
        case = full_case(prediction_uncertainty_k=20.0)
        report = assess_thermal_requirements(case)
        self.assertAlmostEqual(
            report["checks"]["decomposition-onset"]["hottest_predicted_k"],
            343.15,
            places=9,
        )

    def test_the_envelope_hot_prediction_is_reused_by_the_onset_check(self):
        case = full_case()
        case["onset"] = {"decomposition_onset_k": 450.0}
        report = assess_thermal_requirements(case)
        self.assertAlmostEqual(
            report["checks"]["decomposition-onset"]["hottest_predicted_k"],
            343.15,
            places=9,
        )

    def test_every_check_appears_in_the_report(self):
        report = assess_thermal_requirements(full_case())
        for name in (
            "temperature-envelope",
            "decomposition-onset",
            "thermal-stability",
        ):
            self.assertIn(name, report["checks"])

    def test_several_failures_are_all_named(self):
        case = full_case()
        case["envelope"] = envelope_case(predicted_hot_k=350.0)
        case["stability"] = stability_case(
            profile=profile(
                {"label": "hot-soak", "temperature_k": 390.0, "duration_h": 400.0}
            )
        )
        report = assess_thermal_requirements(case)
        self.assertEqual(
            report["failed_checks"], ["temperature-envelope", "thermal-stability"]
        )

    def test_a_non_mapping_case_raises(self):
        with self.assertRaises(ValueError):
            assess_thermal_requirements(None)


if __name__ == "__main__":
    unittest.main()
