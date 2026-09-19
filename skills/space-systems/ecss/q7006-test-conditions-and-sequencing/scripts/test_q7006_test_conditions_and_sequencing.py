"""Contract tests for the exposure conditions and sequencing logic."""

import unittest

from q7006_test_conditions_and_sequencing_logic import (
    DEFAULT_TEMPERATURE_TOLERANCE_C,
    MAX_ACCELERATION_FACTOR,
    MAX_AIR_EXPOSURE_MINUTES,
    MAX_CHAMBER_PRESSURE_PA,
    agent_order_findings,
    assess_test_conditions,
    build_sequence,
    flux_rate_findings,
    interruption_findings,
    normalise_step_fractions,
    pressure_findings,
    step_duration_hours,
    temperature_findings,
)


def base_spec(**overrides):
    spec = {
        "total_exposure": 1.0e14,
        "step_fractions": [0.1, 0.2, 0.3, 0.4],
        "flux": 1.0e8,
        "mission_flux": 1.0e6,
        "achieved_pressure_pa": 1.0e-4,
        "achieved_temperature_c": 22.0,
        "specified_temperature_c": 20.0,
        "agents": ["particles", "ultraviolet"],
        "order": ["combined"],
    }
    spec.update(overrides)
    return spec


class PressureTests(unittest.TestCase):
    def test_good_vacuum_has_no_findings(self):
        self.assertEqual(pressure_findings(1.0e-5), [])

    def test_pressure_exactly_at_the_limit_passes(self):
        self.assertEqual(pressure_findings(MAX_CHAMBER_PRESSURE_PA), [])

    def test_soft_vacuum_is_a_finding(self):
        self.assertEqual(len(pressure_findings(1.0)), 1)

    def test_tighter_limit_can_be_imposed(self):
        self.assertEqual(len(pressure_findings(1.0e-4, limit_pa=1.0e-5)), 1)

    def test_zero_pressure_rejected(self):
        with self.assertRaises(ValueError):
            pressure_findings(0.0)

    def test_non_numeric_pressure_rejected(self):
        with self.assertRaises(ValueError):
            pressure_findings("1e-4")


class TemperatureTests(unittest.TestCase):
    def test_on_target_has_no_findings(self):
        self.assertEqual(temperature_findings(20.0, 20.0), [])

    def test_inside_the_band_has_no_findings(self):
        self.assertEqual(temperature_findings(23.0, 20.0), [])

    def test_exactly_at_the_band_edge_passes(self):
        edge = 20.0 + DEFAULT_TEMPERATURE_TOLERANCE_C
        self.assertEqual(temperature_findings(edge, 20.0), [])

    def test_outside_the_band_is_a_finding(self):
        self.assertEqual(len(temperature_findings(40.0, 20.0)), 1)

    def test_cold_side_is_graded_too(self):
        self.assertEqual(len(temperature_findings(-40.0, 20.0)), 1)

    def test_negative_specified_temperature_is_allowed(self):
        self.assertEqual(temperature_findings(-100.0, -100.0), [])

    def test_tighter_band_can_be_imposed(self):
        self.assertEqual(len(temperature_findings(23.0, 20.0, tolerance_c=1.0)), 1)

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            temperature_findings(20.0, 20.0, tolerance_c=-1.0)


class StepFractionTests(unittest.TestCase):
    def test_fractions_summing_to_one_accepted(self):
        self.assertEqual(normalise_step_fractions([0.25, 0.25, 0.5]), [0.25, 0.25, 0.5])

    def test_many_small_steps_accepted(self):
        self.assertEqual(len(normalise_step_fractions([0.1] * 10)), 10)

    def test_short_sum_rejected(self):
        with self.assertRaises(ValueError):
            normalise_step_fractions([0.25, 0.25])

    def test_over_sum_rejected(self):
        with self.assertRaises(ValueError):
            normalise_step_fractions([0.5, 0.6])

    def test_zero_step_rejected(self):
        with self.assertRaises(ValueError):
            normalise_step_fractions([0.0, 1.0])

    def test_negative_step_rejected(self):
        with self.assertRaises(ValueError):
            normalise_step_fractions([-0.1, 1.1])

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            normalise_step_fractions([])


class SequenceTests(unittest.TestCase):
    def test_duration_is_exposure_over_flux(self):
        self.assertAlmostEqual(step_duration_hours(3.6e9, 1.0e6), 1.0, places=9)

    def test_zero_exposure_takes_no_time(self):
        self.assertAlmostEqual(step_duration_hours(0.0, 1.0e6), 0.0, places=9)

    def test_zero_flux_rejected(self):
        with self.assertRaises(ValueError):
            step_duration_hours(1.0e12, 0.0)

    def test_step_count_matches_the_fractions(self):
        steps = build_sequence(1.0e12, [0.5, 0.5], 1.0e8)
        self.assertEqual(len(steps), 2)

    def test_cumulative_exposure_reaches_the_total(self):
        steps = build_sequence(1.0e12, [0.1, 0.2, 0.3, 0.4], 1.0e8)
        self.assertAlmostEqual(steps[-1]["cumulative_exposure"], 1.0e12, places=0)

    def test_cumulative_hours_are_monotone(self):
        steps = build_sequence(1.0e12, [0.1, 0.2, 0.3, 0.4], 1.0e8)
        hours = [step["cumulative_hours"] for step in steps]
        self.assertEqual(hours, sorted(hours))

    def test_steps_are_numbered_from_one(self):
        steps = build_sequence(1.0e12, [0.5, 0.5], 1.0e8)
        self.assertEqual([step["index"] for step in steps], [1, 2])

    def test_higher_flux_shortens_the_sequence(self):
        slow = build_sequence(1.0e12, [1.0], 1.0e7)
        fast = build_sequence(1.0e12, [1.0], 1.0e8)
        self.assertAlmostEqual(fast[-1]["cumulative_hours"] * 10.0,
                               slow[-1]["cumulative_hours"], places=6)


class FluxRateTests(unittest.TestCase):
    def test_moderate_acceleration_has_no_findings(self):
        self.assertEqual(flux_rate_findings(1.0e8, 1.0e6), [])

    def test_acceleration_exactly_at_the_limit_passes(self):
        self.assertEqual(flux_rate_findings(1.0e6 * MAX_ACCELERATION_FACTOR, 1.0e6), [])

    def test_excessive_acceleration_is_a_finding(self):
        notes = flux_rate_findings(1.0e6 * MAX_ACCELERATION_FACTOR * 10.0, 1.0e6)
        self.assertTrue(any("above the limit" in note for note in notes))

    def test_running_slower_than_the_mission_is_a_finding(self):
        notes = flux_rate_findings(1.0e5, 1.0e6)
        self.assertTrue(any("slower than the mission" in note for note in notes))

    def test_running_at_the_mission_rate_is_clean(self):
        self.assertEqual(flux_rate_findings(1.0e6, 1.0e6), [])

    def test_zero_mission_flux_rejected(self):
        with self.assertRaises(ValueError):
            flux_rate_findings(1.0e8, 0.0)


class AgentOrderTests(unittest.TestCase):
    def test_combined_block_covers_both_agents(self):
        self.assertEqual(agent_order_findings(["combined"], ["particles", "ultraviolet"]), [])

    def test_sequential_order_covers_both_agents(self):
        self.assertEqual(
            agent_order_findings(["ultraviolet", "particles"], ["particles", "ultraviolet"]), []
        )

    def test_single_agent_campaign_needs_one_block(self):
        self.assertEqual(agent_order_findings(["particles"], ["particles"]), [])

    def test_missing_agent_is_a_finding(self):
        notes = agent_order_findings(["particles"], ["particles", "ultraviolet"])
        self.assertTrue(any("never exposes" in note for note in notes))

    def test_repeated_agent_is_a_finding(self):
        notes = agent_order_findings(
            ["particles", "particles"], ["particles", "ultraviolet"]
        )
        self.assertTrue(any("twice" in note for note in notes))

    def test_surplus_agent_is_a_finding(self):
        notes = agent_order_findings(["particles", "ultraviolet"], ["particles"])
        self.assertTrue(any("does not need" in note for note in notes))

    def test_unknown_block_rejected(self):
        with self.assertRaises(ValueError):
            agent_order_findings(["plasma"], ["particles"])

    def test_empty_order_rejected(self):
        with self.assertRaises(ValueError):
            agent_order_findings([], ["particles"])


class InterruptionTests(unittest.TestCase):
    def test_multi_step_stable_property_is_clean(self):
        self.assertEqual(interruption_findings(4, False, False, 0.0), [])

    def test_single_step_is_a_finding(self):
        notes = interruption_findings(1, False, False, 0.0)
        self.assertTrue(any("degradation trend" in note for note in notes))

    def test_air_sensitive_property_read_in_place_is_clean(self):
        self.assertEqual(interruption_findings(4, True, True, 600.0), [])

    def test_air_sensitive_property_inside_the_window_is_clean(self):
        self.assertEqual(
            interruption_findings(4, True, False, MAX_AIR_EXPOSURE_MINUTES), []
        )

    def test_air_sensitive_property_past_the_window_is_a_finding(self):
        notes = interruption_findings(4, True, False, MAX_AIR_EXPOSURE_MINUTES * 4.0)
        self.assertTrue(any("minute window" in note for note in notes))

    def test_zero_steps_rejected(self):
        with self.assertRaises(ValueError):
            interruption_findings(0, False, False, 0.0)

    def test_non_boolean_sensitivity_rejected(self):
        with self.assertRaises(ValueError):
            interruption_findings(4, "yes", False, 0.0)


class AssessTestConditionsTests(unittest.TestCase):
    def test_clean_procedure_is_ready(self):
        result = assess_test_conditions(base_spec())
        self.assertTrue(result["procedure_ready"])
        self.assertEqual(result["findings"], [])

    def test_measurement_points_match_the_steps(self):
        self.assertEqual(assess_test_conditions(base_spec())["measurement_points"], 4)

    def test_acceleration_factor_is_reported(self):
        self.assertAlmostEqual(
            assess_test_conditions(base_spec())["acceleration_factor"], 100.0, places=9
        )

    def test_total_beam_hours_match_the_last_step(self):
        result = assess_test_conditions(base_spec())
        self.assertAlmostEqual(
            result["total_beam_hours"], result["steps"][-1]["cumulative_hours"], places=9
        )

    def test_soft_vacuum_blocks_the_procedure(self):
        result = assess_test_conditions(base_spec(achieved_pressure_pa=1.0))
        self.assertFalse(result["procedure_ready"])

    def test_off_band_temperature_blocks_the_procedure(self):
        result = assess_test_conditions(base_spec(achieved_temperature_c=120.0))
        self.assertTrue(any("specimen held" in note for note in result["findings"]))

    def test_incomplete_order_blocks_the_procedure(self):
        result = assess_test_conditions(base_spec(order=["particles"]))
        self.assertTrue(any("never exposes" in note for note in result["findings"]))

    def test_single_step_sequence_blocks_the_procedure(self):
        result = assess_test_conditions(base_spec(step_fractions=[1.0]))
        self.assertTrue(any("degradation trend" in note for note in result["findings"]))

    def test_slow_air_read_of_a_recovering_property_blocks_the_procedure(self):
        result = assess_test_conditions(
            base_spec(air_sensitive=True, air_exposure_minutes=180.0)
        )
        self.assertTrue(any("minute window" in note for note in result["findings"]))

    def test_step_fractions_must_account_for_the_whole_exposure(self):
        with self.assertRaises(ValueError):
            assess_test_conditions(base_spec(step_fractions=[0.3, 0.3]))

    def test_missing_key_rejected(self):
        spec = base_spec()
        del spec["flux"]
        with self.assertRaises(ValueError):
            assess_test_conditions(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_conditions(["flux"])

    def test_order_is_echoed_as_a_tuple(self):
        self.assertEqual(assess_test_conditions(base_spec())["order"], ("combined",))


if __name__ == "__main__":
    unittest.main()
