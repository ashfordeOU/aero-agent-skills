"""Contract tests for the clause 5.5.5.2c diode heat pipe logic."""

import unittest

from e3102_diode_heat_pipe_verification_logic import (
    assess_diode_heat_pipe,
    conductance_w_per_k,
    diodicity_ratio,
    forward_transport_check,
    interpolate_curve,
    mode_switch_time_s,
    reverse_heat_leak_w,
    switch_energy_j,
    validate_curve,
    validate_transient,
)

CURVE = [
    (-20.0, 40.0),
    (0.0, 80.0),
    (20.0, 120.0),
    (40.0, 140.0),
]

# Reverse power collapsing from the forward level to a settled residue.
TRANSIENT = [
    (0.0, 40.0),
    (10.0, 20.0),
    (20.0, 8.0),
    (30.0, 2.0),
    (40.0, 1.0),
    (50.0, 1.0),
]


class CurveTests(unittest.TestCase):
    def test_validate_returns_float_points(self):
        self.assertEqual(validate_curve([(-10, 40), (10, 80)]), [(-10.0, 40.0), (10.0, 80.0)])

    def test_single_point_curve_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve([(0.0, 80.0)])

    def test_non_monotone_curve_rejected(self):
        with self.assertRaises(ValueError):
            validate_curve([(20.0, 120.0), (0.0, 80.0)])

    def test_interpolation_is_linear(self):
        self.assertAlmostEqual(interpolate_curve(CURVE, 10.0), 100.0, places=9)

    def test_outside_the_curve_refused(self):
        with self.assertRaises(ValueError):
            interpolate_curve(CURVE, 60.0)


class ForwardTests(unittest.TestCase):
    def test_capability_above_the_requirement_passes(self):
        out = forward_transport_check(CURVE, 20.0, 100.0)
        self.assertAlmostEqual(out["capability_w"], 120.0, places=9)
        self.assertTrue(out["compliant"])

    def test_capability_exactly_at_the_requirement_passes(self):
        out = forward_transport_check(CURVE, 20.0, 120.0)
        self.assertAlmostEqual(out["ratio"], 1.0, places=9)
        self.assertTrue(out["compliant"])

    def test_cold_end_shortfall_fails(self):
        self.assertFalse(forward_transport_check(CURVE, -20.0, 100.0)["compliant"])

    def test_zero_requirement_rejected(self):
        with self.assertRaises(ValueError):
            forward_transport_check(CURVE, 20.0, 0.0)


class ConductanceTests(unittest.TestCase):
    def test_conductance_is_heat_over_rise(self):
        self.assertAlmostEqual(conductance_w_per_k(100.0, 4.0), 25.0, places=12)

    def test_zero_rise_rejected(self):
        with self.assertRaises(ValueError):
            conductance_w_per_k(100.0, 0.0)

    def test_negative_heat_rejected(self):
        with self.assertRaises(ValueError):
            conductance_w_per_k(-1.0, 4.0)

    def test_diodicity_is_the_conductance_ratio(self):
        out = diodicity_ratio(25.0, 0.25, 50.0)
        self.assertAlmostEqual(out["ratio"], 100.0, places=9)
        self.assertTrue(out["compliant"])

    def test_diodicity_exactly_at_the_requirement_passes(self):
        out = diodicity_ratio(25.0, 0.25, 100.0)
        self.assertAlmostEqual(out["ratio"], out["required_ratio"], places=9)
        self.assertTrue(out["compliant"])

    def test_leaky_reverse_path_fails_the_diodicity(self):
        self.assertFalse(diodicity_ratio(25.0, 5.0, 50.0)["compliant"])

    def test_required_ratio_below_one_rejected(self):
        with self.assertRaises(ValueError):
            diodicity_ratio(25.0, 0.25, 0.5)

    def test_zero_reverse_conductance_rejected(self):
        with self.assertRaises(ValueError):
            diodicity_ratio(25.0, 0.0, 50.0)


class ReverseLeakTests(unittest.TestCase):
    def test_leak_is_conductance_times_difference(self):
        out = reverse_heat_leak_w(0.25, 30.0, 10.0)
        self.assertAlmostEqual(out["leak_w"], 7.5, places=12)
        self.assertTrue(out["compliant"])

    def test_leak_exactly_at_the_allowance_passes(self):
        out = reverse_heat_leak_w(0.25, 30.0, 7.5)
        self.assertAlmostEqual(out["leak_w"], out["allowed_w"], places=9)
        self.assertTrue(out["compliant"])

    def test_excess_leak_fails(self):
        self.assertFalse(reverse_heat_leak_w(2.0, 30.0, 10.0)["compliant"])

    def test_negative_reverse_difference_rejected(self):
        with self.assertRaises(ValueError):
            reverse_heat_leak_w(0.25, -30.0, 10.0)


class TransientTests(unittest.TestCase):
    def test_validate_returns_float_pairs(self):
        self.assertEqual(validate_transient([(0, 10), (1, 2)]), [(0.0, 10.0), (1.0, 2.0)])

    def test_single_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_transient([(0.0, 10.0)])

    def test_non_monotone_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_transient([(10.0, 5.0), (2.0, 1.0)])

    def test_negative_power_rejected(self):
        with self.assertRaises(ValueError):
            validate_transient([(0.0, 10.0), (1.0, -2.0)])

    def test_malformed_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_transient([(0.0, 10.0), (1.0,)])


class SwitchTimeTests(unittest.TestCase):
    def test_settling_time_is_interpolated_between_samples(self):
        # Between (20 s, 8 W) and (30 s, 2 W) the 5 W crossing sits halfway.
        self.assertAlmostEqual(mode_switch_time_s(TRANSIENT, 5.0), 25.0, places=9)

    def test_crossing_exactly_on_a_sample(self):
        self.assertAlmostEqual(mode_switch_time_s(TRANSIENT, 8.0), 20.0, places=9)

    def test_a_dip_that_recovers_is_not_a_completed_switch(self):
        # The early dip at 10 s is followed by a rise back to 30 W, so the
        # switch only completes on the last descent through 5 W.
        samples = [(0.0, 40.0), (10.0, 1.0), (20.0, 30.0), (30.0, 2.0), (40.0, 2.0)]
        self.assertAlmostEqual(
            mode_switch_time_s(samples, 5.0), 20.0 + 10.0 * (25.0 / 28.0), places=9
        )

    def test_already_settled_at_the_first_sample(self):
        samples = [(0.0, 1.0), (10.0, 1.0)]
        self.assertAlmostEqual(mode_switch_time_s(samples, 5.0), 0.0, places=12)

    def test_never_settling_transient_refused(self):
        with self.assertRaises(ValueError):
            mode_switch_time_s(TRANSIENT, 0.5)

    def test_negative_threshold_rejected(self):
        with self.assertRaises(ValueError):
            mode_switch_time_s(TRANSIENT, -1.0)


class SwitchEnergyTests(unittest.TestCase):
    def test_trapezoid_over_a_flat_transient(self):
        self.assertAlmostEqual(switch_energy_j([(0.0, 4.0), (10.0, 4.0)]), 40.0, places=9)

    def test_trapezoid_over_a_ramp(self):
        self.assertAlmostEqual(switch_energy_j([(0.0, 10.0), (10.0, 0.0)]), 50.0, places=9)

    def test_partial_integration_stops_at_the_limit(self):
        self.assertAlmostEqual(
            switch_energy_j([(0.0, 10.0), (10.0, 0.0)], until_time_s=5.0), 37.5, places=9
        )

    def test_integration_to_the_last_sample_matches_the_default(self):
        full = switch_energy_j(TRANSIENT)
        self.assertAlmostEqual(switch_energy_j(TRANSIENT, until_time_s=50.0), full, places=9)

    def test_limit_past_the_last_sample_rejected(self):
        with self.assertRaises(ValueError):
            switch_energy_j(TRANSIENT, until_time_s=90.0)

    def test_limit_before_the_first_sample_rejected(self):
        with self.assertRaises(ValueError):
            switch_energy_j([(5.0, 4.0), (10.0, 4.0)], until_time_s=1.0)

    def test_energy_over_the_documented_transient(self):
        # Trapezoids: 300 + 140 + 50 + 15 + 10 over the five intervals.
        self.assertAlmostEqual(switch_energy_j(TRANSIENT), 515.0, places=9)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "forward_curve": CURVE,
            "operating_temperature_c": 20.0,
            "required_forward_w": 100.0,
            "forward_heat_w": 100.0,
            "forward_delta_t_k": 4.0,
            "reverse_heat_w": 0.5,
            "reverse_delta_t_k": 2.0,
            "required_diodicity": 50.0,
            "reverse_service_delta_t_k": 30.0,
            "allowed_reverse_leak_w": 10.0,
            "transient_samples": TRANSIENT,
            "settled_threshold_w": 5.0,
            "allowed_switch_time_s": 30.0,
            "allowed_switch_energy_j": 600.0,
        }
        spec.update(overrides)
        return spec

    def test_clean_case_is_compliant(self):
        out = assess_diode_heat_pipe(self._spec())
        self.assertTrue(out["compliant"])
        self.assertEqual(out["findings"], [])

    def test_conductances_are_reported(self):
        out = assess_diode_heat_pipe(self._spec())
        self.assertAlmostEqual(out["forward_conductance"], 25.0, places=12)
        self.assertAlmostEqual(out["reverse_conductance"], 0.25, places=12)

    def test_switch_time_is_the_interpolated_crossing(self):
        out = assess_diode_heat_pipe(self._spec())
        self.assertAlmostEqual(out["switch_time_s"], 25.0, places=9)

    def test_switch_energy_integrates_only_to_the_crossing(self):
        # Trapezoids to the 25 s crossing: 300 + 140 + 32.5, against 515 J for
        # the whole sampled transient.
        out = assess_diode_heat_pipe(self._spec())
        self.assertAlmostEqual(out["switch_energy_j"], 472.5, places=9)
        self.assertLess(out["switch_energy_j"], switch_energy_j(TRANSIENT))

    def test_forward_shortfall_surfaces(self):
        out = assess_diode_heat_pipe(self._spec(required_forward_w=400.0))
        self.assertTrue(any("forward transport" in f for f in out["findings"]))

    def test_diodicity_shortfall_surfaces(self):
        out = assess_diode_heat_pipe(self._spec(required_diodicity=500.0))
        self.assertTrue(any("diodicity" in f for f in out["findings"]))

    def test_reverse_leak_shortfall_surfaces(self):
        out = assess_diode_heat_pipe(self._spec(allowed_reverse_leak_w=1.0))
        self.assertTrue(any("reverse-mode heat leak" in f for f in out["findings"]))

    def test_slow_switch_surfaces(self):
        out = assess_diode_heat_pipe(self._spec(allowed_switch_time_s=5.0))
        self.assertTrue(any("mode switch takes" in f for f in out["findings"]))

    def test_switch_energy_overrun_surfaces(self):
        out = assess_diode_heat_pipe(self._spec(allowed_switch_energy_j=100.0))
        self.assertTrue(any("mode switch leaks" in f for f in out["findings"]))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["required_diodicity"]
        with self.assertRaises(ValueError):
            assess_diode_heat_pipe(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_heat_pipe(["forward_curve"])

    def test_never_settling_transient_refuses_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_diode_heat_pipe(self._spec(settled_threshold_w=0.5))


if __name__ == "__main__":
    unittest.main()
