"""Contract tests for the clauses 4.5.1 and 4.5.2.1 analysis logic."""

import math
import unittest

from e31_tcs_analysis_thermal_math_model_correlation_logic import (
    STABILITY_SAFETY_FACTOR,
    STEFAN_BOLTZMANN_W_M2_K4,
    TEMPERATURE_TOLERANCE_K,
    assess_tcs_analysis,
    correlation_statistics,
    integrate_transient,
    linearised_time_constant_s,
    max_stable_step_s,
    radiative_rejection_w,
    rank_parameter_attribution,
    required_radiator_area_m2,
    sensor_residuals_k,
    steady_state_temperature_k,
    validate_surface,
)

AREA = 0.8
EMITTANCE = 0.85
SINK = 4.0
DISSIPATION = 120.0
ABSORBED = 30.0


class SurfaceValidationTests(unittest.TestCase):
    def test_validated_surface_round_trips(self):
        self.assertEqual(validate_surface(0.8, 0.85, 4.0), (0.8, 0.85, 4.0))

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface(0.0, 0.85, 4.0)

    def test_emittance_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface(0.8, 1.2, 4.0)

    def test_negative_sink_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface(0.8, 0.85, -3.0)

    def test_boolean_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_surface(True, 0.85, 4.0)


class RadiativeBalanceTests(unittest.TestCase):
    def test_rejection_matches_the_closed_form(self):
        value = radiative_rejection_w(AREA, EMITTANCE, 300.0, SINK)
        expected = AREA * EMITTANCE * STEFAN_BOLTZMANN_W_M2_K4 * (
            300.0 ** 4 - SINK ** 4
        )
        self.assertAlmostEqual(value, expected, places=9)

    def test_surface_at_the_sink_rejects_nothing(self):
        self.assertAlmostEqual(
            radiative_rejection_w(AREA, EMITTANCE, SINK, SINK), 0.0, places=12
        )

    def test_surface_below_the_sink_absorbs(self):
        self.assertLess(radiative_rejection_w(AREA, EMITTANCE, 100.0, 200.0), 0.0)

    def test_rejection_is_not_linear_in_temperature(self):
        single = radiative_rejection_w(AREA, EMITTANCE, 300.0, 0.0)
        doubled = radiative_rejection_w(AREA, EMITTANCE, 600.0, 0.0)
        self.assertAlmostEqual(doubled / single, 16.0, places=9)

    def test_non_positive_surface_temperature_rejected(self):
        with self.assertRaises(ValueError):
            radiative_rejection_w(AREA, EMITTANCE, 0.0, SINK)


class SteadyStateTests(unittest.TestCase):
    def test_equilibrium_closes_the_balance(self):
        temperature = steady_state_temperature_k(
            DISSIPATION, ABSORBED, AREA, EMITTANCE, SINK
        )
        rejected = radiative_rejection_w(AREA, EMITTANCE, temperature, SINK)
        self.assertAlmostEqual(rejected, DISSIPATION + ABSORBED, places=6)

    def test_zero_load_settles_at_the_sink(self):
        temperature = steady_state_temperature_k(0.0, 0.0, AREA, EMITTANCE, 250.0)
        self.assertAlmostEqual(temperature, 250.0, places=9)

    def test_warmer_sink_raises_the_equilibrium(self):
        cold = steady_state_temperature_k(DISSIPATION, 0.0, AREA, EMITTANCE, 4.0)
        warm = steady_state_temperature_k(DISSIPATION, 0.0, AREA, EMITTANCE, 250.0)
        self.assertGreater(warm, cold)

    def test_doubling_the_load_does_not_double_the_temperature(self):
        single = steady_state_temperature_k(DISSIPATION, 0.0, AREA, EMITTANCE, 0.0)
        doubled = steady_state_temperature_k(2 * DISSIPATION, 0.0, AREA, EMITTANCE, 0.0)
        self.assertAlmostEqual(doubled / single, 2.0 ** 0.25, places=9)

    def test_absorbed_flux_adds_to_the_dissipation(self):
        split = steady_state_temperature_k(100.0, 50.0, AREA, EMITTANCE, SINK)
        whole = steady_state_temperature_k(150.0, 0.0, AREA, EMITTANCE, SINK)
        self.assertAlmostEqual(split, whole, places=9)

    def test_negative_dissipation_rejected(self):
        with self.assertRaises(ValueError):
            steady_state_temperature_k(-1.0, 0.0, AREA, EMITTANCE, SINK)


class RadiatorSizingTests(unittest.TestCase):
    def test_sizing_inverts_the_balance(self):
        area = required_radiator_area_m2(DISSIPATION, EMITTANCE, 320.0, SINK)
        rejected = radiative_rejection_w(area, EMITTANCE, 320.0, SINK)
        self.assertAlmostEqual(rejected, DISSIPATION, places=9)

    def test_area_is_linear_in_the_load(self):
        single = required_radiator_area_m2(100.0, EMITTANCE, 320.0, SINK)
        doubled = required_radiator_area_m2(200.0, EMITTANCE, 320.0, SINK)
        self.assertAlmostEqual(doubled, 2.0 * single, places=12)

    def test_warmer_sink_needs_more_area(self):
        cold = required_radiator_area_m2(100.0, EMITTANCE, 320.0, 4.0)
        warm = required_radiator_area_m2(100.0, EMITTANCE, 320.0, 290.0)
        self.assertGreater(warm, cold)

    def test_missing_sink_would_have_undersized_the_radiator(self):
        assumed_zero = required_radiator_area_m2(100.0, EMITTANCE, 320.0, 0.0)
        realistic = required_radiator_area_m2(100.0, EMITTANCE, 320.0, 290.0)
        self.assertGreater(realistic, assumed_zero)

    def test_limit_at_the_sink_is_refused(self):
        with self.assertRaises(ValueError):
            required_radiator_area_m2(100.0, EMITTANCE, 290.0, 290.0)

    def test_limit_below_the_sink_is_refused(self):
        with self.assertRaises(ValueError):
            required_radiator_area_m2(100.0, EMITTANCE, 280.0, 290.0)

    def test_zero_load_rejected(self):
        with self.assertRaises(ValueError):
            required_radiator_area_m2(0.0, EMITTANCE, 320.0, SINK)


class TransientTests(unittest.TestCase):
    CAPACITANCE = 4000.0

    def test_time_constant_matches_the_linearisation(self):
        tau = linearised_time_constant_s(self.CAPACITANCE, AREA, EMITTANCE, 300.0)
        expected = self.CAPACITANCE / (
            4.0 * AREA * EMITTANCE * STEFAN_BOLTZMANN_W_M2_K4 * 300.0 ** 3
        )
        self.assertAlmostEqual(tau, expected, places=6)

    def test_hotter_reference_shortens_the_time_constant(self):
        warm = linearised_time_constant_s(self.CAPACITANCE, AREA, EMITTANCE, 400.0)
        cold = linearised_time_constant_s(self.CAPACITANCE, AREA, EMITTANCE, 200.0)
        self.assertLess(warm, cold)

    def test_stable_step_is_a_fraction_of_the_time_constant(self):
        tau = linearised_time_constant_s(self.CAPACITANCE, AREA, EMITTANCE, 300.0)
        step = max_stable_step_s(self.CAPACITANCE, AREA, EMITTANCE, 300.0)
        self.assertAlmostEqual(step, STABILITY_SAFETY_FACTOR * tau, places=9)

    def test_starting_at_equilibrium_does_not_move(self):
        equilibrium = steady_state_temperature_k(
            DISSIPATION, ABSORBED, AREA, EMITTANCE, SINK
        )
        run = integrate_transient(
            equilibrium, DISSIPATION, ABSORBED, AREA, EMITTANCE, SINK,
            self.CAPACITANCE, 10.0, 20,
        )
        self.assertAlmostEqual(run["final_k"], equilibrium, places=6)

    def test_cold_start_relaxes_towards_equilibrium(self):
        equilibrium = steady_state_temperature_k(
            DISSIPATION, ABSORBED, AREA, EMITTANCE, SINK
        )
        run = integrate_transient(
            200.0, DISSIPATION, ABSORBED, AREA, EMITTANCE, SINK,
            self.CAPACITANCE, 50.0, 400,
        )
        self.assertLess(abs(run["final_k"] - equilibrium), 1.0)
        self.assertLess(run["trajectory"][0], run["final_k"])

    def test_trajectory_length_matches_the_step_count(self):
        run = integrate_transient(
            250.0, DISSIPATION, ABSORBED, AREA, EMITTANCE, SINK,
            self.CAPACITANCE, 10.0, 7,
        )
        self.assertEqual(len(run["trajectory"]), 8)

    def test_step_beyond_the_stability_limit_is_refused(self):
        limit = max_stable_step_s(self.CAPACITANCE, AREA, EMITTANCE, 300.0)
        with self.assertRaises(ValueError):
            integrate_transient(
                300.0, DISSIPATION, ABSORBED, AREA, EMITTANCE, SINK,
                self.CAPACITANCE, limit * 2.0, 5,
            )

    def test_step_exactly_on_the_stability_limit_is_accepted(self):
        limit = max_stable_step_s(self.CAPACITANCE, AREA, EMITTANCE, 300.0)
        run = integrate_transient(
            300.0, DISSIPATION, ABSORBED, AREA, EMITTANCE, SINK,
            self.CAPACITANCE, limit, 3,
        )
        self.assertAlmostEqual(run["step_s"], limit, places=9)

    def test_zero_steps_rejected(self):
        with self.assertRaises(ValueError):
            integrate_transient(
                300.0, DISSIPATION, ABSORBED, AREA, EMITTANCE, SINK,
                self.CAPACITANCE, 10.0, 0,
            )

    def test_zero_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            integrate_transient(
                300.0, DISSIPATION, ABSORBED, AREA, EMITTANCE, SINK,
                0.0, 10.0, 5,
            )


class ResidualTests(unittest.TestCase):
    def test_residual_is_predicted_minus_measured(self):
        result = sensor_residuals_k({"trp-a": 305.0}, {"trp-a": 300.0})
        self.assertAlmostEqual(result["residuals"]["trp-a"], 5.0, places=12)

    def test_unmodelled_sensor_is_reported(self):
        result = sensor_residuals_k({"trp-a": 305.0}, {"trp-a": 300.0, "trp-b": 290.0})
        self.assertEqual(result["unmodelled_sensors"], ["trp-b"])
        self.assertEqual(len(result["residuals"]), 1)

    def test_empty_measurement_set_rejected(self):
        with self.assertRaises(ValueError):
            sensor_residuals_k({"trp-a": 305.0}, {})

    def test_non_mapping_prediction_rejected(self):
        with self.assertRaises(ValueError):
            sensor_residuals_k([305.0], {"trp-a": 300.0})

    def test_non_absolute_measurement_rejected(self):
        with self.assertRaises(ValueError):
            sensor_residuals_k({"trp-a": 305.0}, {"trp-a": -3.0})

    def test_mean_and_spread_of_a_biased_model(self):
        stats = correlation_statistics({"a": 5.0, "b": 5.0, "c": 5.0})
        self.assertAlmostEqual(stats["mean_k"], 5.0, places=12)
        self.assertAlmostEqual(stats["spread_k"], 0.0, places=12)

    def test_zero_mean_can_hide_a_scattered_model(self):
        stats = correlation_statistics({"a": 15.0, "b": -15.0})
        self.assertAlmostEqual(stats["mean_k"], 0.0, places=12)
        self.assertAlmostEqual(stats["spread_k"], 15.0, places=12)
        self.assertAlmostEqual(stats["max_abs_k"], 15.0, places=12)

    def test_sequence_input_is_accepted(self):
        stats = correlation_statistics([2.0, 4.0])
        self.assertAlmostEqual(stats["mean_k"], 3.0, places=12)
        self.assertEqual(stats["count"], 2)

    def test_empty_residual_set_rejected(self):
        with self.assertRaises(ValueError):
            correlation_statistics({})

    def test_non_numeric_residual_rejected(self):
        with self.assertRaises(ValueError):
            correlation_statistics({"a": "warm"})


class AttributionTests(unittest.TestCase):
    PARAMETERS = [
        {"name": "interface-conductance", "sensitivity_k_per_unit": -4.0,
         "credible_range": 1.0},
        {"name": "blanket-effective-emittance", "sensitivity_k_per_unit": 40.0,
         "credible_range": 0.01},
    ]

    def test_required_change_cancels_the_residual(self):
        ranked = rank_parameter_attribution(4.0, self.PARAMETERS)
        by_name = {record["name"]: record for record in ranked}
        self.assertAlmostEqual(
            by_name["interface-conductance"]["required_change"], 1.0, places=12
        )

    def test_ranking_puts_the_smallest_change_first(self):
        ranked = rank_parameter_attribution(4.0, self.PARAMETERS)
        self.assertEqual(ranked[0]["name"], "blanket-effective-emittance")

    def test_change_inside_the_credible_range_is_defensible(self):
        ranked = rank_parameter_attribution(2.0, self.PARAMETERS)
        by_name = {record["name"]: record for record in ranked}
        self.assertTrue(by_name["interface-conductance"]["defensible"])

    def test_change_outside_the_credible_range_is_not_defensible(self):
        ranked = rank_parameter_attribution(40.0, self.PARAMETERS)
        by_name = {record["name"]: record for record in ranked}
        self.assertFalse(by_name["interface-conductance"]["defensible"])

    def test_change_exactly_on_the_credible_range_is_defensible(self):
        ranked = rank_parameter_attribution(4.0, self.PARAMETERS)
        by_name = {record["name"]: record for record in ranked}
        self.assertTrue(by_name["interface-conductance"]["defensible"])

    def test_zero_sensitivity_rejected(self):
        with self.assertRaises(ValueError):
            rank_parameter_attribution(4.0, [
                {"name": "inert", "sensitivity_k_per_unit": 0.0, "credible_range": 1.0}
            ])

    def test_empty_parameter_list_rejected(self):
        with self.assertRaises(ValueError):
            rank_parameter_attribution(4.0, [])

    def test_missing_credible_range_rejected(self):
        with self.assertRaises(ValueError):
            rank_parameter_attribution(4.0, [
                {"name": "p", "sensitivity_k_per_unit": 1.0}
            ])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "area_m2": 1.6,
            "emittance": EMITTANCE,
            "sink_k": SINK,
            "dissipation_w": DISSIPATION,
            "absorbed_external_w": ABSORBED,
            "limit_k": 330.0,
            "predicted": {"trp-a": 302.0, "trp-b": 298.0},
            "measured": {"trp-a": 300.0, "trp-b": 296.0},
            "parameters": [
                {"name": "interface-conductance", "sensitivity_k_per_unit": -4.0,
                 "credible_range": 1.0},
            ],
            "mean_tolerance_k": 3.0,
            "spread_tolerance_k": 3.0,
        }
        spec.update(overrides)
        return spec

    def test_well_sized_correlated_case_is_compliant(self):
        result = assess_tcs_analysis(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_equilibrium_and_required_area_are_reported(self):
        result = assess_tcs_analysis(self._spec())
        self.assertLess(result["equilibrium_k"], 330.0)
        self.assertLess(result["required_area_m2"], 1.6)

    def test_undersized_radiator_is_a_finding(self):
        result = assess_tcs_analysis(self._spec(area_m2=0.2))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("radiator" in f for f in result["findings"]))

    def test_hot_balance_over_the_limit_is_a_finding(self):
        result = assess_tcs_analysis(self._spec(area_m2=0.2, limit_k=300.0))
        self.assertTrue(any("steady-state" in f for f in result["findings"]))

    def test_biased_model_breaks_the_mean_allowance(self):
        result = assess_tcs_analysis(self._spec(
            predicted={"trp-a": 320.0, "trp-b": 316.0}
        ))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("mean residual" in f for f in result["findings"]))

    def test_scattered_model_breaks_the_spread_allowance(self):
        result = assess_tcs_analysis(self._spec(
            predicted={"trp-a": 315.0, "trp-b": 281.0}
        ))
        self.assertTrue(any("spread" in f for f in result["findings"]))

    def test_unmodelled_sensor_is_a_finding(self):
        result = assess_tcs_analysis(self._spec(
            measured={"trp-a": 300.0, "trp-b": 296.0, "trp-c": 290.0}
        ))
        self.assertEqual(result["unmodelled_sensors"], ["trp-c"])
        self.assertFalse(result["compliant"])

    def test_indefensible_attribution_is_a_finding(self):
        result = assess_tcs_analysis(self._spec(
            parameters=[{"name": "interface-conductance",
                         "sensitivity_k_per_unit": -4.0,
                         "credible_range": 0.0}],
        ))
        self.assertTrue(
            any("credible range" in f for f in result["findings"])
        )

    def test_transient_is_run_when_a_capacitance_is_declared(self):
        result = assess_tcs_analysis(self._spec(
            capacitance_j_per_k=4000.0, initial_k=250.0, step_s=20.0, steps=50
        ))
        self.assertIsNotNone(result["transient"])
        self.assertLess(result["transient"]["final_k"], 250.0)
        self.assertGreater(result["transient"]["final_k"], result["equilibrium_k"])

    def test_no_transient_without_a_capacitance(self):
        self.assertIsNone(assess_tcs_analysis(self._spec())["transient"])

    def test_statistics_are_reported(self):
        result = assess_tcs_analysis(self._spec())
        self.assertAlmostEqual(result["statistics"]["mean_k"], 2.0, places=12)
        self.assertEqual(result["statistics"]["count"], 2)

    def test_no_overlapping_sensor_rejected(self):
        with self.assertRaises(ValueError):
            assess_tcs_analysis(self._spec(
                predicted={"trp-z": 300.0}, measured={"trp-a": 300.0}
            ))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["limit_k"]
        with self.assertRaises(ValueError):
            assess_tcs_analysis(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_tcs_analysis("area_m2")

    def test_tolerance_is_tight(self):
        self.assertLess(TEMPERATURE_TOLERANCE_K, 1.0e-6)
        self.assertAlmostEqual(math.fabs(STABILITY_SAFETY_FACTOR), 0.5, places=12)


if __name__ == "__main__":
    unittest.main()
