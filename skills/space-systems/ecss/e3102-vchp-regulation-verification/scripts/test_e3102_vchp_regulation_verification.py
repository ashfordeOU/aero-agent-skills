"""Contract tests for the clause 5.5.5.2b variable conductance heat pipe logic."""

import unittest

from e3102_vchp_regulation_verification_logic import (
    REGULATION_MODES,
    active_reservoir_heater_w,
    assess_vchp_regulation,
    axial_conductance_w_per_k,
    condenser_blockage_fraction,
    interpolate_curve,
    maximum_transport_check,
    off_mode_heat_leak_w,
    regulation_swing,
    reservoir_resistance_k_per_w,
    validate_curve,
)

CURVE = [
    (-20.0, 60.0),
    (0.0, 110.0),
    (20.0, 150.0),
    (40.0, 170.0),
]

POINTS = [
    {"name": "min-power-cold-sink", "power_w": 20.0, "sink_c": -40.0, "evaporator_c": 18.0},
    {"name": "mid-power", "power_w": 60.0, "sink_c": -10.0, "evaporator_c": 20.0},
    {"name": "max-power-hot-sink", "power_w": 100.0, "sink_c": 10.0, "evaporator_c": 22.0},
]


class CurveTests(unittest.TestCase):
    def test_validate_returns_float_points(self):
        self.assertEqual(validate_curve([(-10, 40), (10, 80)]), [(-10.0, 40.0), (10.0, 80.0)])

    def test_non_monotone_curve_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve([(20.0, 150.0), (0.0, 110.0)])

    def test_negative_capability_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve([(0.0, -1.0), (20.0, 150.0)])

    def test_interpolation_is_linear(self):
        self.assertAlmostEqual(interpolate_curve(CURVE, 10.0), 130.0, places=9)

    def test_outside_the_curve_refused(self):
        with self.assertRaises(ValueError):
            interpolate_curve(CURVE, 60.0)


class TransportTests(unittest.TestCase):
    def test_capability_above_the_requirement_passes(self):
        out = maximum_transport_check(CURVE, 20.0, 100.0)
        self.assertAlmostEqual(out["capability_w"], 150.0, places=9)
        self.assertTrue(out["compliant"])

    def test_capability_exactly_at_the_requirement_passes(self):
        out = maximum_transport_check(CURVE, 20.0, 150.0)
        self.assertAlmostEqual(out["ratio"], 1.0, places=9)
        self.assertTrue(out["compliant"])

    def test_shortfall_fails(self):
        self.assertFalse(maximum_transport_check(CURVE, -20.0, 100.0)["compliant"])

    def test_zero_requirement_rejected(self):
        with self.assertRaises(ValueError):
            maximum_transport_check(CURVE, 20.0, 0.0)


class OffModeTests(unittest.TestCase):
    def test_axial_conductance_matches_the_closed_form(self):
        self.assertAlmostEqual(
            axial_conductance_w_per_k(160.0, 2.0e-5, 0.4), 160.0 * 2.0e-5 / 0.4, places=12
        )

    def test_zero_length_rejected(self):
        with self.assertRaises(ValueError):
            axial_conductance_w_per_k(160.0, 2.0e-5, 0.0)

    def test_leak_is_the_conductance_times_the_difference(self):
        out = off_mode_heat_leak_w(0.02, 50.0, 2.0)
        self.assertAlmostEqual(out["leak_w"], 1.0, places=12)
        self.assertTrue(out["compliant"])

    def test_leak_exactly_at_the_allowance_passes(self):
        out = off_mode_heat_leak_w(0.02, 50.0, 1.0)
        self.assertAlmostEqual(out["leak_w"], out["allowed_w"], places=9)
        self.assertTrue(out["compliant"])

    def test_excess_leak_fails(self):
        self.assertFalse(off_mode_heat_leak_w(0.2, 50.0, 2.0)["compliant"])

    def test_negative_conductance_rejected(self):
        with self.assertRaises(ValueError):
            off_mode_heat_leak_w(-0.02, 50.0, 2.0)

    def test_negative_delta_rejected(self):
        with self.assertRaises(ValueError):
            off_mode_heat_leak_w(0.02, -50.0, 2.0)


class ReservoirTests(unittest.TestCase):
    def test_resistance_is_the_rise_over_the_heat(self):
        out = reservoir_resistance_k_per_w(2.0, 0.5, 10.0)
        self.assertAlmostEqual(out["resistance_k_per_w"], 4.0, places=12)
        self.assertTrue(out["compliant"])

    def test_resistance_exactly_at_the_maximum_passes(self):
        out = reservoir_resistance_k_per_w(2.0, 0.5, 4.0)
        self.assertAlmostEqual(out["resistance_k_per_w"], out["maximum_k_per_w"], places=9)
        self.assertTrue(out["compliant"])

    def test_loose_reservoir_fails(self):
        self.assertFalse(reservoir_resistance_k_per_w(20.0, 0.5, 4.0)["compliant"])

    def test_zero_heat_rejected(self):
        with self.assertRaises(ValueError):
            reservoir_resistance_k_per_w(2.0, 0.0, 4.0)


class RegulationSwingTests(unittest.TestCase):
    def test_swing_is_the_evaporator_spread(self):
        out = regulation_swing(POINTS, 5.0)
        self.assertAlmostEqual(out["swing_k"], 4.0, places=12)
        self.assertTrue(out["compliant"])

    def test_swing_names_the_two_governing_points(self):
        out = regulation_swing(POINTS, 5.0)
        self.assertEqual(out["coldest_point"]["name"], "min-power-cold-sink")
        self.assertEqual(out["hottest_point"]["name"], "max-power-hot-sink")

    def test_swing_exactly_at_the_band_passes(self):
        out = regulation_swing(POINTS, 4.0)
        self.assertAlmostEqual(out["swing_k"], out["band_k"], places=9)
        self.assertTrue(out["compliant"])

    def test_swing_beyond_the_band_fails(self):
        self.assertFalse(regulation_swing(POINTS, 2.0)["compliant"])

    def test_single_point_rejected(self):
        with self.assertRaises(ValueError):
            regulation_swing(POINTS[:1], 5.0)

    def test_point_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            regulation_swing([{"power_w": 20.0, "sink_c": -40.0}, POINTS[1]], 5.0)

    def test_negative_band_rejected(self):
        with self.assertRaises(ValueError):
            regulation_swing(POINTS, -1.0)


class HeaterTests(unittest.TestCase):
    def test_demand_is_the_conductance_times_the_lift(self):
        out = active_reservoir_heater_w(0.05, 20.0, -40.0, 5.0)
        self.assertAlmostEqual(out["demand_w"], 3.0, places=12)
        self.assertTrue(out["compliant"])

    def test_demand_exactly_at_the_budget_passes(self):
        out = active_reservoir_heater_w(0.05, 20.0, -40.0, 3.0)
        self.assertAlmostEqual(out["demand_w"], out["available_w"], places=9)
        self.assertTrue(out["compliant"])

    def test_demand_beyond_the_budget_fails(self):
        self.assertFalse(active_reservoir_heater_w(0.2, 20.0, -40.0, 3.0)["compliant"])

    def test_sink_above_the_setpoint_needs_no_heater(self):
        out = active_reservoir_heater_w(0.05, 20.0, 30.0, 3.0)
        self.assertAlmostEqual(out["demand_w"], 0.0, places=12)
        self.assertTrue(out["compliant"])

    def test_negative_budget_rejected(self):
        with self.assertRaises(ValueError):
            active_reservoir_heater_w(0.05, 20.0, -40.0, -1.0)


class BlockageTests(unittest.TestCase):
    def test_blockage_is_the_power_turndown(self):
        out = condenser_blockage_fraction(20.0, 100.0, 0.9)
        self.assertAlmostEqual(out["blockage_fraction"], 0.8, places=12)
        self.assertTrue(out["compliant"])

    def test_blockage_exactly_at_the_limit_passes(self):
        out = condenser_blockage_fraction(20.0, 100.0, 0.8)
        self.assertAlmostEqual(out["blockage_fraction"], out["maximum_blockage"], places=9)
        self.assertTrue(out["compliant"])

    def test_undersized_reservoir_fails(self):
        self.assertFalse(condenser_blockage_fraction(5.0, 100.0, 0.8)["compliant"])

    def test_power_above_the_reference_rejected(self):
        with self.assertRaises(ValueError):
            condenser_blockage_fraction(120.0, 100.0, 0.9)

    def test_blockage_limit_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            condenser_blockage_fraction(20.0, 100.0, 1.5)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "transport_curve": CURVE,
            "design_temperature_c": 20.0,
            "required_transport_w": 100.0,
            "off_mode_conductance_w_per_k": 0.02,
            "off_mode_delta_t_k": 50.0,
            "allowed_off_mode_leak_w": 2.0,
            "reservoir_delta_t_k": 2.0,
            "reservoir_heat_w": 0.5,
            "maximum_reservoir_resistance_k_per_w": 10.0,
            "operating_points": POINTS,
            "control_band_k": 5.0,
            "regulation_mode": "passive",
        }
        spec.update(overrides)
        return spec

    def test_clean_passive_unit_is_compliant(self):
        out = assess_vchp_regulation(self._spec())
        self.assertTrue(out["compliant"])
        self.assertIsNone(out["heater"])

    def test_active_unit_sizes_its_heater(self):
        out = assess_vchp_regulation(
            self._spec(
                regulation_mode="active",
                reservoir_conductance_w_per_k=0.05,
                reservoir_setpoint_c=20.0,
                available_heater_w=5.0,
            )
        )
        self.assertTrue(out["compliant"])
        self.assertAlmostEqual(out["heater"]["demand_w"], 3.0, places=12)

    def test_active_unit_without_heater_data_rejected(self):
        with self.assertRaises(ValueError):
            assess_vchp_regulation(self._spec(regulation_mode="active"))

    def test_heater_shortfall_surfaces(self):
        out = assess_vchp_regulation(
            self._spec(
                regulation_mode="active",
                reservoir_conductance_w_per_k=0.2,
                reservoir_setpoint_c=20.0,
                available_heater_w=3.0,
            )
        )
        self.assertTrue(any("heater demand" in f for f in out["findings"]))

    def test_transport_shortfall_surfaces(self):
        out = assess_vchp_regulation(self._spec(required_transport_w=400.0))
        self.assertTrue(any("maximum transport" in f for f in out["findings"]))

    def test_off_mode_shortfall_surfaces(self):
        out = assess_vchp_regulation(self._spec(allowed_off_mode_leak_w=0.2))
        self.assertTrue(any("off-mode heat leak" in f for f in out["findings"]))

    def test_reservoir_shortfall_surfaces(self):
        out = assess_vchp_regulation(self._spec(maximum_reservoir_resistance_k_per_w=1.0))
        self.assertTrue(any("reservoir resistance" in f for f in out["findings"]))

    def test_regulation_band_shortfall_names_both_points(self):
        out = assess_vchp_regulation(self._spec(control_band_k=1.0))
        finding = [f for f in out["findings"] if "evaporator swing" in f][0]
        self.assertIn("min-power-cold-sink", finding)
        self.assertIn("max-power-hot-sink", finding)

    def test_blockage_check_runs_when_both_inputs_are_present(self):
        out = assess_vchp_regulation(self._spec(full_power_w=100.0, maximum_blockage=0.9))
        self.assertIsNotNone(out["blockage"])
        self.assertAlmostEqual(out["blockage"]["blockage_fraction"], 0.8, places=12)

    def test_undersized_reservoir_surfaces(self):
        out = assess_vchp_regulation(self._spec(full_power_w=100.0, maximum_blockage=0.5))
        self.assertTrue(any("condenser blockage" in f for f in out["findings"]))

    def test_unknown_regulation_mode_rejected(self):
        with self.assertRaises(ValueError):
            assess_vchp_regulation(self._spec(regulation_mode="semi-automatic"))

    def test_regulation_modes_are_the_two_known_ones(self):
        self.assertEqual(REGULATION_MODES, ("passive", "active"))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["control_band_k"]
        with self.assertRaises(ValueError):
            assess_vchp_regulation(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_vchp_regulation(["transport_curve"])


if __name__ == "__main__":
    unittest.main()
