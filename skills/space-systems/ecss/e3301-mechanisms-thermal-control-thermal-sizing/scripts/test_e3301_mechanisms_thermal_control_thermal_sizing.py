"""Contract tests for the clause 4.7.4.1-4.7.4.2 mechanism thermal sizing logic."""

import unittest

from e3301_mechanisms_thermal_control_thermal_sizing_logic import (
    STEFAN_BOLTZMANN,
    assess_thermal_sizing,
    conductive_conductance_w_per_k,
    heat_balance_residual_w,
    interface_gradient_k,
    radiative_coupling_m2,
    required_conductance_w_per_k,
    series_conductance_w_per_k,
    steady_state_temperature_k,
    thermoelastic_distortion_m,
)


def base_spec(**overrides):
    """Return a representative bracket-mounted mechanism thermal model."""
    spec = {
        "conductance_w_per_k": 0.35,
        "coupling_m2": 0.02,
        "cases": [
            {
                "name": "hot-operational",
                "dissipation_w": 2.0,
                "absorbed_flux_w": 1.5,
                "sink_temperature_k": 293.0,
            },
            {
                "name": "cold-operational",
                "dissipation_w": 0.5,
                "absorbed_flux_w": 0.0,
                "sink_temperature_k": 253.0,
            },
        ],
        "min_operational_k": 233.0,
        "max_operational_k": 333.0,
        "distortion_length_m": 0.08,
        "cte_per_k": 23.0e-6,
        "allowable_distortion_m": 3.0e-5,
    }
    spec.update(overrides)
    return spec


class ConductancePathTests(unittest.TestCase):
    def test_conductance_follows_section_over_length(self):
        self.assertAlmostEqual(
            conductive_conductance_w_per_k(150.0, 2.0e-4, 0.05), 150.0 * 2.0e-4 / 0.05,
            places=12,
        )

    def test_longer_path_conducts_less(self):
        short = conductive_conductance_w_per_k(150.0, 2.0e-4, 0.025)
        long_path = conductive_conductance_w_per_k(150.0, 2.0e-4, 0.05)
        self.assertAlmostEqual(short, long_path * 2.0, places=12)

    def test_zero_length_rejected(self):
        with self.assertRaises(ValueError):
            conductive_conductance_w_per_k(150.0, 2.0e-4, 0.0)

    def test_series_paths_are_softer_than_either_member(self):
        self.assertAlmostEqual(series_conductance_w_per_k([1.0, 1.0]), 0.5, places=12)

    def test_series_is_dominated_by_the_poor_joint(self):
        combined = series_conductance_w_per_k([10.0, 0.1])
        self.assertAlmostEqual(combined, 1.0 / (1.0 / 10.0 + 1.0 / 0.1), places=12)

    def test_empty_series_rejected(self):
        with self.assertRaises(ValueError):
            series_conductance_w_per_k([])


class RadiativeCouplingTests(unittest.TestCase):
    def test_coupling_is_the_product_of_emittance_area_and_view(self):
        self.assertAlmostEqual(radiative_coupling_m2(0.85, 0.04, 0.5), 0.017, places=12)

    def test_default_view_factor_is_full(self):
        self.assertAlmostEqual(radiative_coupling_m2(0.85, 0.04), 0.034, places=12)

    def test_emittance_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            radiative_coupling_m2(1.4, 0.04)

    def test_view_factor_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            radiative_coupling_m2(0.85, 0.04, 1.2)


class SteadyStateTests(unittest.TestCase):
    def test_residual_vanishes_at_the_solution(self):
        t = steady_state_temperature_k(3.5, 0.35, 0.02, 293.0)
        self.assertAlmostEqual(
            heat_balance_residual_w(t, 3.5, 0.35, 0.02, 293.0), 0.0, places=9
        )

    def test_no_heat_settles_at_the_sink(self):
        self.assertAlmostEqual(
            steady_state_temperature_k(0.0, 0.35, 0.02, 293.0), 293.0, places=6
        )

    def test_more_dissipation_runs_hotter(self):
        low = steady_state_temperature_k(1.0, 0.35, 0.02, 293.0)
        high = steady_state_temperature_k(6.0, 0.35, 0.02, 293.0)
        self.assertGreater(high, low + 1.0)

    def test_better_conductance_runs_cooler(self):
        poor = steady_state_temperature_k(3.5, 0.05, 0.02, 293.0)
        good = steady_state_temperature_k(3.5, 2.0, 0.02, 293.0)
        self.assertGreater(poor, good + 1.0)

    def test_radiation_only_node_still_solves(self):
        t = steady_state_temperature_k(3.5, 0.0, 0.02, 293.0)
        self.assertAlmostEqual(
            heat_balance_residual_w(t, 3.5, 0.0, 0.02, 293.0), 0.0, places=9
        )

    def test_node_with_no_path_to_the_sink_rejected(self):
        with self.assertRaises(ValueError):
            steady_state_temperature_k(3.5, 0.0, 0.0, 293.0)

    def test_non_positive_sink_temperature_rejected(self):
        with self.assertRaises(ValueError):
            steady_state_temperature_k(3.5, 0.35, 0.02, 0.0)

    def test_stefan_boltzmann_constant_is_the_si_value(self):
        self.assertAlmostEqual(STEFAN_BOLTZMANN, 5.670374419e-8, places=17)


class SizingTests(unittest.TestCase):
    def test_required_conductance_without_radiation(self):
        self.assertAlmostEqual(
            required_conductance_w_per_k(3.5, 300.0, 293.0), 0.5, places=12
        )

    def test_radiation_reduces_the_conductance_needed(self):
        with_rad = required_conductance_w_per_k(3.5, 300.0, 293.0, 0.02)
        self.assertLess(with_rad, 0.5)

    def test_radiation_alone_can_hold_the_limit(self):
        self.assertAlmostEqual(
            required_conductance_w_per_k(0.5, 350.0, 293.0, 0.02), 0.0, places=12
        )

    def test_limit_at_or_below_the_sink_rejected(self):
        with self.assertRaises(ValueError):
            required_conductance_w_per_k(3.5, 293.0, 293.0, 0.02)

    def test_gradient_is_heat_over_conductance(self):
        self.assertAlmostEqual(interface_gradient_k(3.5, 0.35), 10.0, places=12)

    def test_zero_conductance_gradient_rejected(self):
        with self.assertRaises(ValueError):
            interface_gradient_k(3.5, 0.0)

    def test_distortion_scales_with_gradient_and_length(self):
        self.assertAlmostEqual(
            thermoelastic_distortion_m(23.0e-6, 0.08, 10.0), 23.0e-6 * 0.8, places=15
        )

    def test_zero_gradient_gives_no_distortion(self):
        self.assertAlmostEqual(thermoelastic_distortion_m(23.0e-6, 0.08, 0.0), 0.0, places=18)


class AssessThermalSizingTests(unittest.TestCase):
    def test_representative_mechanism_is_compliant(self):
        result = assess_thermal_sizing(base_spec())
        self.assertTrue(result["compliant"], result["findings"])
        self.assertEqual(result["hottest_case"]["name"], "hot-operational")
        self.assertEqual(result["coldest_case"]["name"], "cold-operational")

    def test_hot_margin_is_measured_from_the_ceiling(self):
        result = assess_thermal_sizing(base_spec())
        self.assertAlmostEqual(
            result["hot_margin_k"], 333.0 - result["hottest_case"]["temperature_k"],
            places=9,
        )

    def test_high_dissipation_breaches_the_ceiling_and_returns_a_design_action(self):
        spec = base_spec()
        spec["cases"][0]["dissipation_w"] = 60.0
        result = assess_thermal_sizing(spec)
        self.assertFalse(result["compliant"])
        self.assertIn("required_conductance_w_per_k", result["cases"][0])
        self.assertGreater(result["cases"][0]["required_conductance_w_per_k"], 0.35)

    def test_cold_sink_breaches_the_floor(self):
        spec = base_spec()
        spec["cases"][1]["sink_temperature_k"] = 150.0
        spec["cases"][1]["dissipation_w"] = 0.1
        result = assess_thermal_sizing(spec)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("floor" in f for f in result["findings"]))

    def test_tight_distortion_allowance_is_a_finding(self):
        result = assess_thermal_sizing(base_spec(allowable_distortion_m=1.0e-6))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("distorts" in f for f in result["findings"]))

    def test_distortion_is_reported_per_case(self):
        result = assess_thermal_sizing(base_spec())
        for record in result["cases"]:
            self.assertIn("distortion_m", record)

    def test_partial_distortion_inputs_rejected(self):
        spec = base_spec()
        del spec["cte_per_k"]
        with self.assertRaises(ValueError):
            assess_thermal_sizing(spec)

    def test_inverted_operational_band_rejected(self):
        with self.assertRaises(ValueError):
            assess_thermal_sizing(base_spec(min_operational_k=350.0))

    def test_empty_case_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_thermal_sizing(base_spec(cases=[]))

    def test_malformed_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_thermal_sizing(base_spec(cases=[{"name": "hot"}]))

    def test_missing_key_rejected(self):
        spec = base_spec()
        del spec["coupling_m2"]
        with self.assertRaises(ValueError):
            assess_thermal_sizing(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_thermal_sizing(("conductance_w_per_k", 0.35))


if __name__ == "__main__":
    unittest.main()
