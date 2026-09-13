"""Contract test for the clause 6.2 pre-test vacuum bakeout logic (stdlib only)."""

import math
import unittest

import e2001_pre_test_vacuum_bakeout_logic as L


def _good_record():
    return {
        "setpoint_c": 120.0,
        "max_allowable_c": 150.0,
        "thermal_margin_k": 10.0,
        "minimum_effective_c": 80.0,
        "reference_c": 100.0,
        "bakeout_hours": 48.0,
        "required_reference_hours": 24.0,
        "chamber_pressure_mbar": 1.0e-6,
        "required_pressure_mbar": 1.0e-5,
        "hold_hours": 12.0,
        "allowed_hold_hours": 24.0,
        "backfill_gas": "dry-nitrogen",
        "initial_outgassing_rate": 1.0e-5,
        "target_outgassing_rate": 5.0e-7,
        "decay_exponent": 1.0,
    }


class TemperatureTests(unittest.TestCase):
    def test_freezing_point_converts_to_absolute(self):
        self.assertAlmostEqual(L.celsius_to_kelvin(0.0), 273.15, places=9)

    def test_absolute_zero_itself_is_rejected(self):
        with self.assertRaises(ValueError):
            L.celsius_to_kelvin(-273.15)

    def test_below_absolute_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            L.celsius_to_kelvin(-400.0)

    def test_non_numeric_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            L.celsius_to_kelvin("hot")


class SetpointTests(unittest.TestCase):
    def test_setpoint_inside_the_window_is_acceptable(self):
        result = L.evaluate_bakeout_setpoint(120.0, 150.0, 10.0, 80.0)
        self.assertTrue(result["acceptable"])
        self.assertAlmostEqual(result["headroom_k"], 20.0, places=9)

    def test_setpoint_exactly_on_the_derated_ceiling_is_acceptable(self):
        result = L.evaluate_bakeout_setpoint(140.0, 150.0, 10.0, 80.0)
        self.assertTrue(result["acceptable"])
        self.assertFalse(result["exceeds_allowance"])

    def test_ceiling_case_carrying_representation_error_is_acceptable(self):
        drifted = 0.0
        for _ in range(700):
            drifted += 0.2
        self.assertNotEqual(drifted, 140.0)
        self.assertGreater(drifted, 140.0)
        result = L.evaluate_bakeout_setpoint(drifted, 150.0, 10.0, 80.0)
        self.assertTrue(result["acceptable"])

    def test_setpoint_exactly_on_the_effective_floor_is_acceptable(self):
        result = L.evaluate_bakeout_setpoint(80.0, 150.0, 10.0, 80.0)
        self.assertTrue(result["acceptable"])
        self.assertFalse(result["below_effective_floor"])

    def test_setpoint_above_the_derated_ceiling_is_reported(self):
        result = L.evaluate_bakeout_setpoint(145.0, 150.0, 10.0, 80.0)
        self.assertTrue(result["exceeds_allowance"])
        self.assertFalse(result["acceptable"])

    def test_setpoint_below_the_effective_floor_is_reported(self):
        result = L.evaluate_bakeout_setpoint(60.0, 150.0, 10.0, 80.0)
        self.assertTrue(result["below_effective_floor"])
        self.assertFalse(result["acceptable"])

    def test_negative_thermal_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_bakeout_setpoint(120.0, 150.0, -5.0, 80.0)

    def test_collapsed_window_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_bakeout_setpoint(120.0, 100.0, 40.0, 80.0)

    def test_setpoint_below_absolute_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_bakeout_setpoint(-300.0, 150.0, 10.0, -290.0)


class AccelerationTests(unittest.TestCase):
    def test_equal_temperatures_give_unity(self):
        self.assertAlmostEqual(L.thermal_acceleration_factor(100.0, 100.0), 1.0, places=12)

    def test_hotter_bakeout_accelerates_desorption(self):
        self.assertGreater(L.thermal_acceleration_factor(120.0, 100.0), 1.0)

    def test_cooler_bakeout_decelerates_desorption(self):
        self.assertLess(L.thermal_acceleration_factor(80.0, 100.0), 1.0)

    def test_forward_and_reverse_factors_are_reciprocal(self):
        forward = L.thermal_acceleration_factor(120.0, 100.0)
        reverse = L.thermal_acceleration_factor(100.0, 120.0)
        self.assertAlmostEqual(forward * reverse, 1.0, places=12)

    def test_factor_matches_the_arrhenius_hand_computation(self):
        expected = math.exp(
            (0.6 / L.BOLTZMANN_EV_PER_K) * ((1.0 / 373.15) - (1.0 / 393.15))
        )
        self.assertAlmostEqual(L.thermal_acceleration_factor(120.0, 100.0, 0.6), expected, places=9)

    def test_zero_activation_energy_is_rejected(self):
        with self.assertRaises(ValueError):
            L.thermal_acceleration_factor(120.0, 100.0, 0.0)

    def test_negative_activation_energy_is_rejected(self):
        with self.assertRaises(ValueError):
            L.thermal_acceleration_factor(120.0, 100.0, -0.6)


class DwellTests(unittest.TestCase):
    def test_equivalent_hours_scale_with_the_acceleration_factor(self):
        factor = L.thermal_acceleration_factor(120.0, 100.0)
        self.assertAlmostEqual(
            L.equivalent_reference_hours(120.0, 100.0, 10.0), 10.0 * factor, places=9
        )

    def test_zero_dwell_yields_zero_equivalent_hours(self):
        self.assertAlmostEqual(L.equivalent_reference_hours(120.0, 100.0, 0.0), 0.0, places=12)

    def test_negative_dwell_is_rejected(self):
        with self.assertRaises(ValueError):
            L.equivalent_reference_hours(120.0, 100.0, -1.0)

    def test_long_dwell_covers_the_requirement(self):
        graded = L.evaluate_bakeout_dwell(120.0, 100.0, 48.0, 24.0)
        self.assertTrue(graded["sufficient"])
        self.assertGreater(graded["coverage"], 1.0)

    def test_dwell_exactly_on_the_requirement_is_sufficient(self):
        achieved = L.equivalent_reference_hours(110.0, 100.0, 7.0)
        graded = L.evaluate_bakeout_dwell(110.0, 100.0, 7.0, achieved)
        self.assertTrue(graded["sufficient"])
        self.assertTrue(graded["at_requirement"])

    def test_short_dwell_is_insufficient(self):
        graded = L.evaluate_bakeout_dwell(90.0, 100.0, 1.0, 24.0)
        self.assertFalse(graded["sufficient"])

    def test_zero_requirement_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_bakeout_dwell(120.0, 100.0, 10.0, 0.0)


class OutgassingTests(unittest.TestCase):
    def test_rate_is_held_at_the_decay_anchor(self):
        self.assertAlmostEqual(L.outgassing_rate(1.0e-5, 1.0), 1.0e-5, places=15)

    def test_rate_before_the_anchor_is_the_initial_rate(self):
        self.assertAlmostEqual(L.outgassing_rate(1.0e-5, 0.25), 1.0e-5, places=15)

    def test_unit_exponent_gives_inverse_time_decay(self):
        self.assertAlmostEqual(L.outgassing_rate(1.0e-5, 4.0, 1.0), 2.5e-6, places=15)

    def test_half_exponent_decays_more_slowly(self):
        self.assertAlmostEqual(L.outgassing_rate(1.0e-5, 4.0, 0.5), 5.0e-6, places=15)

    def test_negative_elapsed_time_is_rejected(self):
        with self.assertRaises(ValueError):
            L.outgassing_rate(1.0e-5, -1.0)

    def test_zero_initial_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            L.outgassing_rate(0.0, 4.0)

    def test_zero_decay_exponent_is_rejected(self):
        with self.assertRaises(ValueError):
            L.outgassing_rate(1.0e-5, 4.0, 0.0)

    def test_hours_to_target_for_unit_exponent(self):
        self.assertAlmostEqual(
            L.hours_to_reach_outgassing_target(1.0e-5, 1.0e-7, 1.0), 100.0, places=9
        )

    def test_hours_to_target_for_square_exponent(self):
        self.assertAlmostEqual(
            L.hours_to_reach_outgassing_target(1.0e-5, 1.0e-7, 2.0), 10.0, places=9
        )

    def test_target_already_met_needs_only_the_anchor(self):
        self.assertAlmostEqual(
            L.hours_to_reach_outgassing_target(1.0e-7, 1.0e-5, 1.0),
            L.DECAY_REFERENCE_HOURS,
            places=12,
        )

    def test_round_trip_from_target_back_to_rate(self):
        hours = L.hours_to_reach_outgassing_target(2.0e-5, 4.0e-7, 1.3)
        self.assertAlmostEqual(L.outgassing_rate(2.0e-5, hours, 1.3), 4.0e-7, places=15)

    def test_zero_target_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            L.hours_to_reach_outgassing_target(1.0e-5, 0.0)


class PressureTests(unittest.TestCase):
    def test_pressure_a_decade_below_the_requirement_is_compliant(self):
        graded = L.evaluate_chamber_pressure(1.0e-6, 1.0e-5)
        self.assertTrue(graded["compliant"])
        self.assertAlmostEqual(graded["decades_of_margin"], 1.0, places=9)

    def test_pressure_exactly_at_the_requirement_is_compliant(self):
        graded = L.evaluate_chamber_pressure(1.0e-5, 1.0e-5)
        self.assertTrue(graded["compliant"])
        self.assertTrue(graded["at_limit"])

    def test_pressure_above_the_requirement_is_not_compliant(self):
        graded = L.evaluate_chamber_pressure(1.0e-4, 1.0e-5)
        self.assertFalse(graded["compliant"])
        self.assertAlmostEqual(graded["decades_of_margin"], -1.0, places=9)

    def test_zero_measured_pressure_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_chamber_pressure(0.0, 1.0e-5)

    def test_negative_required_pressure_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_chamber_pressure(1.0e-6, -1.0e-5)


class BackfillTests(unittest.TestCase):
    def test_dry_nitrogen_is_inert(self):
        self.assertEqual(L.categorize_backfill_gas("dry-nitrogen"), "inert")

    def test_gas_name_spacing_and_case_are_tolerated(self):
        self.assertEqual(L.categorize_backfill_gas(" Dry Nitrogen "), "inert")

    def test_room_air_is_ambient(self):
        self.assertEqual(L.categorize_backfill_gas("room_air"), "ambient")

    def test_uncategorized_medium_is_rejected(self):
        with self.assertRaises(ValueError):
            L.categorize_backfill_gas("shop-compressed-air")

    def test_non_string_medium_is_rejected(self):
        with self.assertRaises(ValueError):
            L.categorize_backfill_gas(None)

    def test_empty_medium_is_rejected(self):
        with self.assertRaises(ValueError):
            L.categorize_backfill_gas("   ")


class HoldTests(unittest.TestCase):
    def test_short_inert_hold_keeps_the_bakeout_valid(self):
        hold = L.evaluate_post_bakeout_hold(12.0, 24.0, "dry-nitrogen")
        self.assertTrue(hold["bakeout_still_valid"])

    def test_hold_exactly_on_the_allowance_keeps_the_bakeout_valid(self):
        hold = L.evaluate_post_bakeout_hold(24.0, 24.0, "dry-argon")
        self.assertTrue(hold["bakeout_still_valid"])
        self.assertTrue(hold["at_limit"])

    def test_hold_beyond_the_allowance_voids_the_bakeout(self):
        hold = L.evaluate_post_bakeout_hold(72.0, 24.0, "dry-nitrogen")
        self.assertFalse(hold["bakeout_still_valid"])
        self.assertIn("allowance", hold["reason"])

    def test_ambient_break_voids_the_bakeout_even_with_no_wait(self):
        hold = L.evaluate_post_bakeout_hold(0.0, 24.0, "ambient-air")
        self.assertFalse(hold["bakeout_still_valid"])
        self.assertIn("ambient air", hold["reason"])

    def test_negative_hold_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_post_bakeout_hold(-1.0, 24.0, "dry-nitrogen")

    def test_zero_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_post_bakeout_hold(1.0, 0.0, "dry-nitrogen")


class ReadinessTests(unittest.TestCase):
    def test_clean_record_is_ready_for_test(self):
        result = L.assess_bakeout_readiness(_good_record())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["ready_for_test"])

    def test_hot_setpoint_is_a_finding(self):
        record = _good_record()
        record["setpoint_c"] = 149.0
        result = L.assess_bakeout_readiness(record)
        self.assertTrue(any("derated" in f for f in result["findings"]))
        self.assertFalse(result["ready_for_test"])

    def test_short_dwell_is_a_finding(self):
        record = _good_record()
        record["bakeout_hours"] = 0.5
        record["setpoint_c"] = 85.0
        result = L.assess_bakeout_readiness(record)
        self.assertTrue(any("dwell" in f for f in result["findings"]))

    def test_high_chamber_pressure_is_a_finding(self):
        record = _good_record()
        record["chamber_pressure_mbar"] = 1.0e-3
        result = L.assess_bakeout_readiness(record)
        self.assertTrue(any("chamber pressure" in f for f in result["findings"]))

    def test_ambient_break_is_a_finding(self):
        record = _good_record()
        record["backfill_gas"] = "ambient-air"
        result = L.assess_bakeout_readiness(record)
        self.assertTrue(any("voided the bakeout" in f for f in result["findings"]))

    def test_missing_outgassing_target_is_a_finding(self):
        record = _good_record()
        record.pop("target_outgassing_rate")
        result = L.assess_bakeout_readiness(record)
        self.assertIn("no outgassing-rate target on record for the bakeout", result["findings"])
        self.assertIsNone(result["outgassing"])

    def test_outgassing_still_above_target_is_a_finding(self):
        record = _good_record()
        record["target_outgassing_rate"] = 1.0e-9
        result = L.assess_bakeout_readiness(record)
        self.assertTrue(any("outgassing rate" in f for f in result["findings"]))

    def test_missing_required_key_is_rejected(self):
        record = _good_record()
        record.pop("required_pressure_mbar")
        with self.assertRaises(ValueError):
            L.assess_bakeout_readiness(record)

    def test_non_mapping_record_is_rejected(self):
        with self.assertRaises(ValueError):
            L.assess_bakeout_readiness([("setpoint_c", 120.0)])

    def test_findings_are_sorted_and_stable(self):
        record = _good_record()
        record["setpoint_c"] = 149.0
        record["chamber_pressure_mbar"] = 1.0e-3
        first = L.assess_bakeout_readiness(record)["findings"]
        second = L.assess_bakeout_readiness(record)["findings"]
        self.assertEqual(first, second)
        self.assertEqual(first, sorted(first))


if __name__ == "__main__":
    unittest.main()
