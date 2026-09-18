#!/usr/bin/env python3
"""Contract tests for the clause 5.3.5.1.1 load-undervoltage interaction study."""

import unittest

from e2020_load_undervoltage_interaction_study_logic import (
    CATEGORIES,
    DELAYED_LATCH_OFF,
    LOAD_STAYS_OFF,
    NO_LIMITATION,
    NO_UNDERVOLTAGE,
    REPETITIVE_CYCLE,
    SINGLE_LATCH_OFF,
    accumulated_limitation_time,
    cycle_period_s,
    cycles_to_latch_off,
    limitation_duty,
    limitation_entered,
    limited_output_voltage,
    pass_element_cycle_energy_j,
    protection_releases,
    steady_state_accumulation,
    study_interaction,
    undervoltage_trips,
    validate_load,
    validate_supply,
)

# A 28 V branch behind a 2 A latching limiter with a 10 ms trip-off delay,
# whose timer starts from zero every time limitation ends.
SUPPLY = {
    "bus_voltage_v": 28.0,
    "current_limit_a": 2.0,
    "trip_off_delay_s": 0.010,
    "timer_retention": 0.0,
}

# A load that pulls its input capacitance up through an effective ohm, and
# whose own undervoltage protection drops out at 18 V and releases at 20 V.
LOAD = {
    "inrush_current_a": 8.0,
    "load_resistance_ohm": 1.0,
    "undervoltage_trip_v": 18.0,
    "undervoltage_recovery_v": 20.0,
    "detection_delay_s": 0.002,
    "recovery_delay_s": 0.050,
}


def supply(**overrides):
    spec = dict(SUPPLY)
    spec.update(overrides)
    return spec


def load(**overrides):
    spec = dict(LOAD)
    spec.update(overrides)
    return spec


class ValidateSupplyTests(unittest.TestCase):
    def test_returns_floats(self):
        out = validate_supply(SUPPLY)
        self.assertAlmostEqual(out["trip_off_delay_s"], 0.010, places=9)

    def test_full_reset_retention_allowed(self):
        self.assertAlmostEqual(validate_supply(supply(timer_retention=0.0))["timer_retention"], 0.0, places=12)

    def test_integrating_retention_allowed(self):
        self.assertAlmostEqual(validate_supply(supply(timer_retention=1.0))["timer_retention"], 1.0, places=12)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_supply(["bus_voltage_v"])

    def test_missing_key_rejected(self):
        spec = dict(SUPPLY)
        del spec["current_limit_a"]
        with self.assertRaises(ValueError):
            validate_supply(spec)

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_supply(supply(current_limit_a=0.0))

    def test_retention_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_supply(supply(timer_retention=1.4))

    def test_negative_retention_rejected(self):
        with self.assertRaises(ValueError):
            validate_supply(supply(timer_retention=-0.1))

    def test_boolean_masquerading_as_delay_rejected(self):
        with self.assertRaises(ValueError):
            validate_supply(supply(trip_off_delay_s=True))


class ValidateLoadTests(unittest.TestCase):
    def test_returns_floats(self):
        out = validate_load(LOAD)
        self.assertAlmostEqual(out["undervoltage_trip_v"], 18.0, places=9)

    def test_zero_recovery_delay_allowed(self):
        out = validate_load(load(recovery_delay_s=0.0))
        self.assertAlmostEqual(out["recovery_delay_s"], 0.0, places=12)

    def test_equal_thresholds_allowed_as_zero_hysteresis(self):
        out = validate_load(load(undervoltage_recovery_v=18.0))
        self.assertAlmostEqual(out["undervoltage_recovery_v"], 18.0, places=9)

    def test_inverted_hysteresis_rejected(self):
        with self.assertRaises(ValueError):
            validate_load(load(undervoltage_recovery_v=16.0))

    def test_zero_detection_delay_rejected(self):
        with self.assertRaises(ValueError):
            validate_load(load(detection_delay_s=0.0))

    def test_negative_resistance_rejected(self):
        with self.assertRaises(ValueError):
            validate_load(load(load_resistance_ohm=-1.0))

    def test_non_finite_inrush_rejected(self):
        with self.assertRaises(ValueError):
            validate_load(load(inrush_current_a=float("nan")))

    def test_missing_key_rejected(self):
        spec = dict(LOAD)
        del spec["undervoltage_trip_v"]
        with self.assertRaises(ValueError):
            validate_load(spec)


class LimitationEntryTests(unittest.TestCase):
    def test_demand_below_the_limit_does_not_limit(self):
        self.assertFalse(limitation_entered(2.0, 1.5))

    def test_demand_exactly_at_the_limit_limits(self):
        self.assertTrue(limitation_entered(2.0, 2.0))

    def test_demand_above_the_limit_limits(self):
        self.assertTrue(limitation_entered(2.0, 8.0))

    def test_negative_demand_rejected(self):
        with self.assertRaises(ValueError):
            limitation_entered(2.0, -1.0)


class HeldVoltageTests(unittest.TestCase):
    def test_held_voltage_is_the_limited_current_through_the_load(self):
        self.assertAlmostEqual(limited_output_voltage(28.0, 2.0, 1.0), 2.0, places=9)

    def test_held_voltage_cannot_exceed_the_bus(self):
        self.assertAlmostEqual(limited_output_voltage(28.0, 2.0, 100.0), 28.0, places=9)

    def test_stiffer_load_holds_the_output_higher(self):
        low = limited_output_voltage(28.0, 2.0, 1.0)
        high = limited_output_voltage(28.0, 2.0, 6.0)
        self.assertGreater(high, low)

    def test_zero_resistance_rejected(self):
        with self.assertRaises(ValueError):
            limited_output_voltage(28.0, 2.0, 0.0)


class ThresholdTests(unittest.TestCase):
    def test_collapsed_output_trips_the_load_protection(self):
        self.assertTrue(undervoltage_trips(2.0, 18.0))

    def test_voltage_exactly_on_the_trip_threshold_trips(self):
        self.assertTrue(undervoltage_trips(18.0, 18.0))

    def test_voltage_above_the_threshold_does_not_trip(self):
        self.assertFalse(undervoltage_trips(24.0, 18.0))

    def test_recovered_bus_releases_the_protection(self):
        self.assertTrue(protection_releases(28.0, 20.0))

    def test_bus_exactly_on_the_release_threshold_releases(self):
        self.assertTrue(protection_releases(20.0, 20.0))

    def test_bus_below_the_release_threshold_holds_the_load_off(self):
        self.assertFalse(protection_releases(19.0, 20.0))

    def test_negative_threshold_rejected(self):
        with self.assertRaises(ValueError):
            undervoltage_trips(2.0, -1.0)


class CycleTests(unittest.TestCase):
    def test_period_is_detection_plus_recovery(self):
        self.assertAlmostEqual(cycle_period_s(0.002, 0.050), 0.052, places=9)

    def test_duty_is_the_limitation_share_of_the_period(self):
        self.assertAlmostEqual(limitation_duty(0.002, 0.050), 0.002 / 0.052, places=12)

    def test_duty_is_unity_with_no_recovery_delay(self):
        self.assertAlmostEqual(limitation_duty(0.002, 0.0), 1.0, places=12)

    def test_negative_recovery_delay_rejected(self):
        with self.assertRaises(ValueError):
            cycle_period_s(0.002, -0.001)


class AccumulationTests(unittest.TestCase):
    def test_zero_cycles_reads_zero(self):
        self.assertAlmostEqual(accumulated_limitation_time(0, 0.002, 1.0), 0.0, places=12)

    def test_integrating_timer_sums_the_windows(self):
        self.assertAlmostEqual(accumulated_limitation_time(5, 0.002, 1.0), 0.010, places=9)

    def test_full_reset_timer_never_exceeds_one_window(self):
        self.assertAlmostEqual(accumulated_limitation_time(40, 0.002, 0.0), 0.002, places=9)

    def test_partial_retention_lies_between_the_two(self):
        partial = accumulated_limitation_time(5, 0.002, 0.5)
        self.assertGreater(partial, 0.002)
        self.assertLess(partial, 0.010)

    def test_negative_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            accumulated_limitation_time(-1, 0.002, 0.5)

    def test_non_integer_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            accumulated_limitation_time(2.5, 0.002, 0.5)

    def test_retention_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            accumulated_limitation_time(3, 0.002, 1.5)


class SteadyStateTests(unittest.TestCase):
    def test_full_reset_converges_on_one_window(self):
        self.assertAlmostEqual(steady_state_accumulation(0.002, 0.0), 0.002, places=12)

    def test_integrating_timer_never_converges(self):
        self.assertEqual(steady_state_accumulation(0.002, 1.0), float("inf"))

    def test_partial_retention_converges_on_the_geometric_sum(self):
        self.assertAlmostEqual(steady_state_accumulation(0.002, 0.8), 0.010, places=9)

    def test_zero_window_rejected(self):
        with self.assertRaises(ValueError):
            steady_state_accumulation(0.0, 0.5)


class CyclesToLatchTests(unittest.TestCase):
    def test_full_reset_never_latches(self):
        self.assertIsNone(cycles_to_latch_off(0.002, 0.010, 0.0))

    def test_integrating_timer_latches_on_the_fifth_cycle(self):
        self.assertEqual(cycles_to_latch_off(0.002, 0.010, 1.0), 5)

    def test_window_at_the_delay_latches_on_the_first_cycle(self):
        self.assertEqual(cycles_to_latch_off(0.010, 0.010, 0.0), 1)

    def test_partial_retention_latches_later_than_an_integrator(self):
        integrating = cycles_to_latch_off(0.002, 0.010, 1.0)
        partial = cycles_to_latch_off(0.002, 0.010, 0.9)
        self.assertIsNotNone(partial)
        self.assertGreater(partial, integrating)

    def test_ceiling_exactly_at_the_delay_still_reaches_it(self):
        reached = cycles_to_latch_off(0.002, 0.010, 0.8)
        self.assertIsInstance(reached, int)

    def test_horizon_shorter_than_the_latch_reports_no_latch(self):
        self.assertIsNone(cycles_to_latch_off(0.002, 0.010, 1.0, max_cycles=3))

    def test_zero_horizon_rejected(self):
        with self.assertRaises(ValueError):
            cycles_to_latch_off(0.002, 0.010, 1.0, max_cycles=0)


class CycleEnergyTests(unittest.TestCase):
    def test_energy_is_stood_off_volts_times_limited_amps_times_window(self):
        self.assertAlmostEqual(
            pass_element_cycle_energy_j(28.0, 2.0, 2.0, 0.002), 0.104, places=9
        )

    def test_a_higher_held_voltage_lowers_the_energy(self):
        hard = pass_element_cycle_energy_j(28.0, 2.0, 2.0, 0.002)
        soft = pass_element_cycle_energy_j(28.0, 24.0, 2.0, 0.002)
        self.assertLess(soft, hard)

    def test_held_voltage_above_the_bus_rejected(self):
        with self.assertRaises(ValueError):
            pass_element_cycle_energy_j(28.0, 30.0, 2.0, 0.002)


class StudyInteractionTests(unittest.TestCase):
    def _spec(self, supply_overrides=None, load_overrides=None, **extra):
        spec = {
            "supply": supply(**(supply_overrides or {})),
            "load": load(**(load_overrides or {})),
        }
        spec.update(extra)
        return spec

    def test_demand_within_the_limit_is_not_an_interaction(self):
        report = study_interaction(self._spec(load_overrides={"inrush_current_a": 1.0}))
        self.assertEqual(report["category"], NO_LIMITATION)
        self.assertIsNone(report["held_voltage_v"])

    def test_load_that_rides_the_droop_through_lets_the_limiter_run_its_delay(self):
        report = study_interaction(self._spec(load_overrides={"load_resistance_ohm": 12.0}))
        self.assertEqual(report["category"], NO_UNDERVOLTAGE)
        self.assertFalse(report["undervoltage_trips"])
        self.assertAlmostEqual(report["held_voltage_v"], 24.0, places=9)

    def test_slow_load_detection_lets_the_branch_latch_off_once(self):
        report = study_interaction(self._spec(load_overrides={"detection_delay_s": 0.020}))
        self.assertEqual(report["category"], SINGLE_LATCH_OFF)
        self.assertEqual(report["cycles_to_latch_off"], 1)

    def test_protection_that_never_releases_leaves_the_load_off(self):
        report = study_interaction(
            self._spec(load_overrides={"undervoltage_recovery_v": 30.0})
        )
        self.assertEqual(report["category"], LOAD_STAYS_OFF)
        self.assertFalse(report["protection_releases"])

    def test_resetting_timer_produces_an_endless_repetitive_cycle(self):
        report = study_interaction(self._spec())
        self.assertEqual(report["category"], REPETITIVE_CYCLE)
        self.assertIsNone(report["cycles_to_latch_off"])
        self.assertAlmostEqual(report["cycle_period_s"], 0.052, places=9)
        self.assertEqual(len(report["findings"]), 2)

    def test_repetitive_cycle_reports_the_pass_element_duty(self):
        report = study_interaction(self._spec())
        self.assertAlmostEqual(report["cycle_energy_j"], 0.104, places=9)
        self.assertAlmostEqual(report["limitation_duty"], 0.002 / 0.052, places=12)

    def test_integrating_timer_ends_the_cycle_by_latching_off(self):
        report = study_interaction(self._spec(supply_overrides={"timer_retention": 1.0}))
        self.assertEqual(report["category"], DELAYED_LATCH_OFF)
        self.assertEqual(report["cycles_to_latch_off"], 5)

    def test_every_reported_category_is_a_declared_one(self):
        for overrides in (
            {"inrush_current_a": 1.0},
            {"load_resistance_ohm": 12.0},
            {"detection_delay_s": 0.020},
            {"undervoltage_recovery_v": 30.0},
            {},
        ):
            report = study_interaction(self._spec(load_overrides=overrides))
            self.assertIn(report["category"], CATEGORIES)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            study_interaction(["supply"])

    def test_missing_load_rejected(self):
        with self.assertRaises(ValueError):
            study_interaction({"supply": supply()})

    def test_non_integer_horizon_rejected(self):
        with self.assertRaises(ValueError):
            study_interaction(self._spec(max_cycles=2.5))


if __name__ == "__main__":
    unittest.main()
