"""Contract tests for the clause 7.2.4 transient-simulation setup logic."""

import math
import unittest

from q6012_transient_simulation_requirements_logic import (
    KNEE_CONSTANT,
    MIN_OVERSAMPLE_FACTOR,
    MIN_POINTS_PER_EDGE,
    TIME_TOLERANCE_NS,
    assess_transient_simulation,
    inrush_peak_a,
    knee_frequency_ghz,
    max_timestep_ps,
    required_steps,
    sample_rate_ghz,
    settling_time_ns,
    stored_energy_nj,
    supply_slew_rate_v_per_ns,
    validate_event_schedule,
    validate_fraction,
    validate_positive,
)

EVENTS = [
    {"kind": "switch_on", "time_ns": 0.0},
    {"kind": "switch_off", "time_ns": 40.0},
]


def base_spec(**overrides):
    spec = {
        "rise_time_ps": 200.0,
        "slowest_time_constant_ns": 2.0,
        "residual_error_fraction": 0.01,
        "events": [dict(e) for e in EVENTS],
        "supply_v": 5.0,
        "load_capacitance_pf": 20.0,
        "source_resistance_ohm": 2.5,
        "max_steps": 500000,
    }
    spec.update(overrides)
    return spec


class ValidationHelperTests(unittest.TestCase):
    def test_positive_returns_float(self):
        self.assertAlmostEqual(validate_positive("x", 7), 7.0, places=9)

    def test_positive_rejects_zero(self):
        with self.assertRaises(ValueError):
            validate_positive("x", 0.0)

    def test_positive_rejects_boolean(self):
        with self.assertRaises(ValueError):
            validate_positive("x", True)

    def test_fraction_accepts_interior_value(self):
        self.assertAlmostEqual(validate_fraction("e", 0.01), 0.01, places=12)

    def test_fraction_rejects_unity(self):
        with self.assertRaises(ValueError):
            validate_fraction("e", 1.0)

    def test_fraction_rejects_zero(self):
        with self.assertRaises(ValueError):
            validate_fraction("e", 0.0)

    def test_fraction_rejects_negative(self):
        with self.assertRaises(ValueError):
            validate_fraction("e", -0.2)


class KneeAndTimestepTests(unittest.TestCase):
    def test_knee_uses_the_named_constant(self):
        self.assertAlmostEqual(
            knee_frequency_ghz(350.0), KNEE_CONSTANT * 1000.0 / 350.0, places=9
        )

    def test_knee_of_a_one_nanosecond_edge(self):
        self.assertAlmostEqual(knee_frequency_ghz(1000.0), 0.35, places=9)

    def test_faster_edge_pushes_the_knee_up(self):
        slow = knee_frequency_ghz(1000.0)
        fast = knee_frequency_ghz(100.0)
        self.assertAlmostEqual(fast / slow, 10.0, places=9)

    def test_timestep_splits_the_edge(self):
        self.assertAlmostEqual(max_timestep_ps(200.0, 10), 20.0, places=9)

    def test_more_points_per_edge_shortens_the_timestep(self):
        coarse = max_timestep_ps(200.0, 10)
        fine = max_timestep_ps(200.0, 40)
        self.assertAlmostEqual(coarse / fine, 4.0, places=9)

    def test_too_few_points_per_edge_rejected(self):
        with self.assertRaises(ValueError):
            max_timestep_ps(200.0, 4)

    def test_points_per_edge_floor_is_the_named_constant(self):
        self.assertEqual(MIN_POINTS_PER_EDGE, 10)

    def test_non_integer_points_per_edge_rejected(self):
        with self.assertRaises(ValueError):
            max_timestep_ps(200.0, 12.5)

    def test_sample_rate_is_the_timestep_reciprocal(self):
        self.assertAlmostEqual(sample_rate_ghz(20.0), 50.0, places=9)


class SettlingTests(unittest.TestCase):
    def test_one_percent_residual_is_about_four_six_tau(self):
        self.assertAlmostEqual(
            settling_time_ns(1.0, 0.01), math.log(100.0), places=9
        )

    def test_settling_scales_with_the_time_constant(self):
        short = settling_time_ns(1.0, 0.01)
        long_tau = settling_time_ns(5.0, 0.01)
        self.assertAlmostEqual(long_tau / short, 5.0, places=9)

    def test_tighter_residual_needs_a_longer_window(self):
        loose = settling_time_ns(2.0, 0.05)
        tight = settling_time_ns(2.0, 0.001)
        self.assertGreater(tight, loose)

    def test_residual_of_one_rejected(self):
        with self.assertRaises(ValueError):
            settling_time_ns(2.0, 1.0)

    def test_negative_time_constant_rejected(self):
        with self.assertRaises(ValueError):
            settling_time_ns(-2.0, 0.01)


class StepCountAndStressTests(unittest.TestCase):
    def test_step_count_rounds_up(self):
        self.assertEqual(required_steps(1.0, 30.0), 34)

    def test_step_count_exact_division(self):
        self.assertEqual(required_steps(1.0, 20.0), 50)

    def test_inrush_is_supply_over_source_resistance(self):
        self.assertAlmostEqual(inrush_peak_a(5.0, 2.5), 2.0, places=9)

    def test_lower_source_resistance_raises_the_inrush(self):
        self.assertAlmostEqual(inrush_peak_a(5.0, 0.5) / inrush_peak_a(5.0, 2.5), 5.0, places=9)

    def test_stored_energy_value(self):
        self.assertAlmostEqual(stored_energy_nj(20.0, 5.0), 0.5 * 20e-12 * 25.0 * 1e9, places=12)

    def test_stored_energy_is_quadratic_in_supply(self):
        low = stored_energy_nj(20.0, 5.0)
        high = stored_energy_nj(20.0, 10.0)
        self.assertAlmostEqual(high / low, 4.0, places=9)

    def test_slew_rate_value(self):
        self.assertAlmostEqual(supply_slew_rate_v_per_ns(5.0, 200.0), 25.0, places=9)

    def test_zero_resistance_rejected(self):
        with self.assertRaises(ValueError):
            inrush_peak_a(5.0, 0.0)


class EventScheduleTests(unittest.TestCase):
    def test_events_returned_in_time_order(self):
        events = validate_event_schedule(
            [
                {"kind": "switch_off", "time_ns": 40.0},
                {"kind": "switch_on", "time_ns": 0.0},
            ],
            100.0,
        )
        self.assertEqual([e["kind"] for e in events], ["switch_on", "switch_off"])

    def test_event_outside_the_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_event_schedule([{"kind": "switch_on", "time_ns": 200.0}], 100.0)

    def test_unknown_event_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_event_schedule([{"kind": "power_cycle", "time_ns": 0.0}], 100.0)

    def test_duplicate_event_times_rejected(self):
        with self.assertRaises(ValueError):
            validate_event_schedule(
                [
                    {"kind": "switch_on", "time_ns": 10.0},
                    {"kind": "bias_step", "time_ns": 10.0},
                ],
                100.0,
            )

    def test_negative_event_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_event_schedule([{"kind": "switch_on", "time_ns": -1.0}], 100.0)

    def test_empty_event_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_event_schedule([], 100.0)

    def test_non_mapping_event_rejected(self):
        with self.assertRaises(ValueError):
            validate_event_schedule(["switch_on"], 100.0)

    def test_event_exactly_at_the_window_edge_accepted(self):
        events = validate_event_schedule([{"kind": "switch_on", "time_ns": 100.0}], 100.0)
        self.assertAlmostEqual(events[0]["time_ns"], 100.0, places=9)


class AssessTransientSimulationTests(unittest.TestCase):
    def test_well_formed_setup_is_adequate(self):
        result = assess_transient_simulation(base_spec())
        self.assertTrue(result["adequate"], result["findings"])

    def test_stop_time_covers_the_last_event_plus_settling(self):
        result = assess_transient_simulation(base_spec())
        self.assertAlmostEqual(
            result["stop_time_ns"], 40.0 + settling_time_ns(2.0, 0.01), places=9
        )

    def test_timestep_matches_the_edge_resolution(self):
        result = assess_transient_simulation(base_spec())
        self.assertAlmostEqual(result["timestep_ps"], 20.0, places=9)

    def test_step_count_is_consistent_with_the_window(self):
        result = assess_transient_simulation(base_spec())
        self.assertEqual(
            result["required_steps"],
            required_steps(result["stop_time_ns"], result["timestep_ps"]),
        )

    def test_short_declared_window_is_reported_not_replaced(self):
        result = assess_transient_simulation(base_spec(window_ns=41.0))
        self.assertAlmostEqual(result["stop_time_ns"], 41.0, places=9)
        self.assertTrue(any("before the last event has settled" in f for f in result["findings"]))

    def test_missing_switch_off_is_a_finding(self):
        result = assess_transient_simulation(
            base_spec(events=[{"kind": "switch_on", "time_ns": 0.0}])
        )
        self.assertTrue(any("switch-off" in f for f in result["findings"]))

    def test_missing_switch_on_is_a_finding(self):
        result = assess_transient_simulation(
            base_spec(events=[{"kind": "switch_off", "time_ns": 10.0}])
        )
        self.assertTrue(any("switch-on" in f for f in result["findings"]))

    def test_step_budget_overrun_is_a_finding(self):
        result = assess_transient_simulation(base_spec(max_steps=100))
        self.assertFalse(result["adequate"])
        self.assertTrue(any("integration steps" in f for f in result["findings"]))

    def test_demanding_oversample_is_a_finding(self):
        result = assess_transient_simulation(base_spec(oversample_factor=1000.0))
        self.assertTrue(any("edge knee" in f for f in result["findings"]))

    def test_default_oversample_is_the_named_constant(self):
        spec = base_spec()
        result = assess_transient_simulation(spec)
        self.assertGreater(
            result["sample_rate_ghz"], MIN_OVERSAMPLE_FACTOR * result["knee_frequency_ghz"]
        )

    def test_needed_stop_time_is_reported(self):
        result = assess_transient_simulation(base_spec(window_ns=41.0))
        self.assertAlmostEqual(
            result["needed_stop_time_ns"], 40.0 + settling_time_ns(2.0, 0.01), places=9
        )

    def test_event_kinds_are_reported(self):
        result = assess_transient_simulation(base_spec())
        self.assertEqual(result["event_kinds"], ["switch_off", "switch_on"])

    def test_missing_key_rejected(self):
        spec = base_spec()
        del spec["supply_v"]
        with self.assertRaises(ValueError):
            assess_transient_simulation(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_transient_simulation(["rise_time_ps"])

    def test_non_integer_max_steps_rejected(self):
        with self.assertRaises(ValueError):
            assess_transient_simulation(base_spec(max_steps=1000.5))

    def test_zero_max_steps_rejected(self):
        with self.assertRaises(ValueError):
            assess_transient_simulation(base_spec(max_steps=0))

    def test_tolerance_is_a_named_constant(self):
        self.assertAlmostEqual(TIME_TOLERANCE_NS, 1e-9, places=15)

    def test_faster_edge_multiplies_the_step_count(self):
        slow = assess_transient_simulation(base_spec(rise_time_ps=400.0))
        fast = assess_transient_simulation(base_spec(rise_time_ps=200.0))
        self.assertAlmostEqual(slow["timestep_ps"] / fast["timestep_ps"], 2.0, places=9)
        self.assertGreater(fast["required_steps"], slow["required_steps"])


if __name__ == "__main__":
    unittest.main()
