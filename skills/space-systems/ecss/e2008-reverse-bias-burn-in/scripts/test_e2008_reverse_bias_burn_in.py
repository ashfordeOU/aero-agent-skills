"""Contract tests for the clause 12.6.7.3.1 reverse bias burn-in logic."""

import unittest

from e2008_reverse_bias_burn_in_logic import (
    BIAS_FORWARD,
    BIAS_REVERSE,
    BIAS_UNBIASED,
    DEFAULT_REVERSE_BIAS_POLICY,
    REVERSE_BIAS_DURATION_OUT_OF_WINDOW,
    REVERSE_BIAS_LOT_REJECTED,
    REVERSE_BIAS_NOT_APPLIED,
    REVERSE_BIAS_OVERSTRESSED,
    REVERSE_BIAS_POLARITY_WRONG,
    REVERSE_BIAS_SOAK_COMPLETE,
    REVERSE_BIAS_TEMPERATURE_LOW,
    applied_reverse_voltage_v,
    assess_reverse_bias_burn_in,
    bias_polarity,
    drifted_devices,
    junction_temperature_c,
    kelvin,
    leakage_drift_ratio,
    leakage_power_w,
    lot_drift_fraction,
    reverse_voltage_ratio,
    soak_within_window,
    validate_reverse_bias_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_REVERSE_BIAS_POLICY)
    policy.update(overrides)
    return policy


def _readings(drifted_count=0, lot_size=20):
    readings = []
    for index in range(lot_size):
        final = 3.0e-7 if index < drifted_count else 1.5e-7
        readings.append(
            {
                "device_id": "d%02d" % (index,),
                "initial_leakage_a": 1.0e-7,
                "final_leakage_a": final,
            }
        )
    return readings


def _soak(**overrides):
    soak = {
        "anode_voltage_v": 0.0,
        "cathode_voltage_v": 100.0,
        "rated_reverse_voltage_v": 200.0,
        "leakage_current_a": 1.0e-5,
        "case_temperature_c": 150.0,
        "thermal_resistance_c_per_w": 20.0,
        "duration_h": 48.0,
    }
    soak.update(overrides)
    return soak


def _case(**overrides):
    case = {"soak": _soak(), "readings": _readings()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_reverse_bias_policy(DEFAULT_REVERSE_BIAS_POLICY),
            DEFAULT_REVERSE_BIAS_POLICY,
        )

    def test_the_default_ceiling_is_the_forty_eight_hour_maximum(self):
        self.assertAlmostEqual(
            DEFAULT_REVERSE_BIAS_POLICY["max_soak_hours"], 48.0, places=9
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_reverse_bias_policy("forty-eight hours")

    def test_a_ceiling_below_the_floor_leaves_no_window(self):
        with self.assertRaises(ValueError):
            validate_reverse_bias_policy(_policy(max_soak_hours=12.0))

    def test_a_voltage_ratio_limit_at_the_rating_rejected(self):
        with self.assertRaises(ValueError):
            validate_reverse_bias_policy(_policy(max_reverse_voltage_ratio=1.0))

    def test_a_drift_limit_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_reverse_bias_policy(_policy(max_leakage_drift_ratio=0.5))

    def test_a_reject_limit_accepting_a_wholly_drifted_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_reverse_bias_policy(_policy(max_lot_drift_fraction=1.0))

    def test_a_junction_ceiling_below_the_case_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_reverse_bias_policy(_policy(max_junction_temperature_c=100.0))

    def test_a_case_floor_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_reverse_bias_policy(_policy(min_case_temperature_c=-300.0))


class PolarityTests(unittest.TestCase):
    def test_a_positive_cathode_holds_the_junction_in_reverse(self):
        self.assertEqual(bias_polarity(0.0, 100.0), BIAS_REVERSE)

    def test_a_positive_anode_holds_the_junction_forward(self):
        self.assertEqual(bias_polarity(100.0, 0.0), BIAS_FORWARD)

    def test_equal_terminals_leave_the_junction_unbiased(self):
        self.assertEqual(bias_polarity(50.0, 50.0), BIAS_UNBIASED)

    def test_polarity_follows_the_difference_not_the_sign_of_either_rail(self):
        self.assertEqual(bias_polarity(-150.0, -50.0), BIAS_REVERSE)

    def test_a_non_numeric_terminal_voltage_rejected(self):
        with self.assertRaises(ValueError):
            bias_polarity("0 V", 100.0)

    def test_the_reverse_voltage_is_the_terminal_difference(self):
        self.assertAlmostEqual(applied_reverse_voltage_v(0.0, 100.0), 100.0, places=9)

    def test_a_forward_junction_has_no_reverse_voltage(self):
        with self.assertRaises(ValueError):
            applied_reverse_voltage_v(100.0, 0.0)

    def test_an_unbiased_junction_has_no_reverse_voltage(self):
        with self.assertRaises(ValueError):
            applied_reverse_voltage_v(0.0, 0.0)


class StressTests(unittest.TestCase):
    def test_the_voltage_ratio_is_the_applied_share_of_the_rating(self):
        self.assertAlmostEqual(reverse_voltage_ratio(100.0, 200.0), 0.5, places=9)

    def test_a_zero_rating_rejected(self):
        with self.assertRaises(ValueError):
            reverse_voltage_ratio(100.0, 0.0)

    def test_a_zero_applied_voltage_rejected(self):
        with self.assertRaises(ValueError):
            reverse_voltage_ratio(0.0, 200.0)

    def test_a_blocking_junction_still_dissipates_its_leakage(self):
        self.assertAlmostEqual(leakage_power_w(100.0, 1.0e-5), 1.0e-3, places=12)

    def test_a_perfectly_blocking_junction_dissipates_nothing(self):
        self.assertAlmostEqual(leakage_power_w(100.0, 0.0), 0.0, places=12)

    def test_a_negative_leakage_current_rejected(self):
        with self.assertRaises(ValueError):
            leakage_power_w(100.0, -1.0e-6)

    def test_the_junction_sits_above_the_case_by_the_thermal_drop(self):
        self.assertAlmostEqual(
            junction_temperature_c(150.0, 1.0e-3, 20.0), 150.02, places=9
        )

    def test_a_perfect_thermal_path_leaves_the_junction_at_the_case(self):
        self.assertAlmostEqual(
            junction_temperature_c(150.0, 1.0e-3, 0.0), 150.0, places=9
        )

    def test_a_case_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(-300.0, 1.0e-3, 20.0)

    def test_kelvin_conversion_offsets_by_absolute_zero(self):
        self.assertAlmostEqual(kelvin(0.0), 273.15, places=9)


class WindowTests(unittest.TestCase):
    def test_a_soak_inside_the_window_is_accepted(self):
        self.assertTrue(soak_within_window(36.0, 24.0, 48.0))

    def test_a_soak_exactly_on_the_forty_eight_hour_ceiling_is_accepted(self):
        self.assertTrue(soak_within_window(48.0, 24.0, 48.0))

    def test_a_soak_exactly_on_the_floor_is_accepted(self):
        self.assertTrue(soak_within_window(24.0, 24.0, 48.0))

    def test_a_soak_past_the_ceiling_is_refused(self):
        self.assertFalse(soak_within_window(72.0, 24.0, 48.0))

    def test_a_soak_short_of_the_floor_is_refused(self):
        self.assertFalse(soak_within_window(8.0, 24.0, 48.0))

    def test_a_zero_length_soak_rejected(self):
        with self.assertRaises(ValueError):
            soak_within_window(0.0, 24.0, 48.0)


class DriftTests(unittest.TestCase):
    def test_the_drift_ratio_is_the_final_over_the_initial_leakage(self):
        self.assertAlmostEqual(leakage_drift_ratio(1.0e-7, 3.0e-7), 3.0, places=9)

    def test_a_junction_that_did_not_move_has_unity_drift(self):
        self.assertAlmostEqual(leakage_drift_ratio(1.0e-7, 1.0e-7), 1.0, places=12)

    def test_a_zero_initial_leakage_rejected(self):
        with self.assertRaises(ValueError):
            leakage_drift_ratio(0.0, 3.0e-7)

    def test_a_negative_final_leakage_rejected(self):
        with self.assertRaises(ValueError):
            leakage_drift_ratio(1.0e-7, -1.0e-7)

    def test_only_devices_past_the_limit_are_named(self):
        self.assertEqual(drifted_devices(_readings(2), 2.0), ("d00", "d01"))

    def test_a_device_exactly_on_the_drift_limit_is_kept(self):
        readings = [
            {
                "device_id": "d00",
                "initial_leakage_a": 1.0e-7,
                "final_leakage_a": 2.0e-7,
            }
        ]
        self.assertEqual(drifted_devices(readings, 2.0), ())

    def test_an_empty_reading_set_rejected(self):
        with self.assertRaises(ValueError):
            drifted_devices([], 2.0)

    def test_a_repeated_device_id_rejected(self):
        readings = _readings(0, 2)
        readings[1]["device_id"] = readings[0]["device_id"]
        with self.assertRaises(ValueError):
            drifted_devices(readings, 2.0)

    def test_a_reading_with_no_device_id_rejected(self):
        readings = _readings(0, 2)
        del readings[0]["device_id"]
        with self.assertRaises(ValueError):
            drifted_devices(readings, 2.0)

    def test_a_reading_that_is_not_a_mapping_rejected(self):
        with self.assertRaises(ValueError):
            drifted_devices([1.5e-7], 2.0)

    def test_the_lot_drift_fraction_counts_the_removed_share(self):
        self.assertAlmostEqual(lot_drift_fraction(_readings(3, 20), 2.0), 0.15, places=12)

    def test_a_lot_that_did_not_drift_has_a_zero_share(self):
        self.assertAlmostEqual(lot_drift_fraction(_readings(0, 20), 2.0), 0.0, places=12)


class AssessmentTests(unittest.TestCase):
    def test_a_compliant_soak_is_complete(self):
        result = assess_reverse_bias_burn_in(_case())
        self.assertEqual(result["verdict"], REVERSE_BIAS_SOAK_COMPLETE)
        self.assertEqual(result["findings"], [])

    def test_a_soak_exactly_on_the_ceiling_is_still_inside_the_window(self):
        result = assess_reverse_bias_burn_in(_case())
        self.assertTrue(result["duration_within_window"])
        self.assertAlmostEqual(result["duration_h"], 48.0, places=9)

    def test_the_polarity_is_reported_for_the_run(self):
        result = assess_reverse_bias_burn_in(_case())
        self.assertEqual(result["polarity"], BIAS_REVERSE)

    def test_the_junction_is_derived_from_the_blocking_leakage(self):
        result = assess_reverse_bias_burn_in(_case())
        self.assertAlmostEqual(result["junction_temperature_c"], 150.02, places=9)

    def test_an_unplanned_soak_is_its_own_verdict(self):
        case = _case()
        del case["soak"]
        result = assess_reverse_bias_burn_in(case)
        self.assertEqual(result["verdict"], REVERSE_BIAS_NOT_APPLIED)
        self.assertIsNone(result["junction_temperature_c"])

    def test_a_forward_connection_stops_the_assessment_at_the_polarity(self):
        result = assess_reverse_bias_burn_in(
            _case(soak=_soak(anode_voltage_v=100.0, cathode_voltage_v=0.0))
        )
        self.assertEqual(result["verdict"], REVERSE_BIAS_POLARITY_WRONG)
        self.assertEqual(result["polarity"], BIAS_FORWARD)
        self.assertIsNone(result["reverse_voltage_ratio"])

    def test_a_blocking_voltage_past_the_share_limit_overstresses_the_lot(self):
        result = assess_reverse_bias_burn_in(
            _case(soak=_soak(cathode_voltage_v=190.0))
        )
        self.assertEqual(result["verdict"], REVERSE_BIAS_OVERSTRESSED)
        self.assertFalse(result["voltage_within_limit"])

    def test_leakage_self_heating_can_carry_the_junction_past_its_ceiling(self):
        result = assess_reverse_bias_burn_in(
            _case(soak=_soak(leakage_current_a=1.0e-2, thermal_resistance_c_per_w=5000.0))
        )
        self.assertEqual(result["verdict"], REVERSE_BIAS_OVERSTRESSED)
        self.assertFalse(result["junction_within_limit"])

    def test_a_cool_soak_is_not_the_high_temperature_screen(self):
        result = assess_reverse_bias_burn_in(
            _case(soak=_soak(case_temperature_c=60.0))
        )
        self.assertEqual(result["verdict"], REVERSE_BIAS_TEMPERATURE_LOW)
        self.assertFalse(result["temperature_adequate"])

    def test_a_soak_run_past_the_ceiling_leaves_the_window(self):
        result = assess_reverse_bias_burn_in(_case(soak=_soak(duration_h=96.0)))
        self.assertEqual(result["verdict"], REVERSE_BIAS_DURATION_OUT_OF_WINDOW)
        self.assertFalse(result["duration_within_window"])

    def test_a_soak_stopped_short_also_leaves_the_window(self):
        result = assess_reverse_bias_burn_in(_case(soak=_soak(duration_h=6.0)))
        self.assertEqual(result["verdict"], REVERSE_BIAS_DURATION_OUT_OF_WINDOW)

    def test_a_drift_share_exactly_on_the_reject_limit_is_accepted(self):
        result = assess_reverse_bias_burn_in(_case(readings=_readings(1, 20)))
        self.assertEqual(result["verdict"], REVERSE_BIAS_SOAK_COMPLETE)
        self.assertTrue(result["lot_accepted"])
        self.assertEqual(result["drifted_devices"], ("d00",))

    def test_a_lot_shedding_too_many_devices_is_rejected(self):
        result = assess_reverse_bias_burn_in(_case(readings=_readings(4, 20)))
        self.assertEqual(result["verdict"], REVERSE_BIAS_LOT_REJECTED)
        self.assertFalse(result["lot_accepted"])

    def test_every_inadequacy_is_reported_not_only_the_first(self):
        result = assess_reverse_bias_burn_in(
            _case(
                soak=_soak(
                    cathode_voltage_v=190.0, case_temperature_c=60.0, duration_h=96.0
                ),
                readings=_readings(8, 20),
            )
        )
        self.assertEqual(result["verdict"], REVERSE_BIAS_OVERSTRESSED)
        self.assertGreaterEqual(len(result["findings"]), 4)

    def test_absent_readings_rejected(self):
        case = _case()
        del case["readings"]
        with self.assertRaises(ValueError):
            assess_reverse_bias_burn_in(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_reverse_bias_burn_in(["soak"])

    def test_a_non_mapping_soak_rejected(self):
        with self.assertRaises(ValueError):
            assess_reverse_bias_burn_in(_case(soak=[48.0]))

    def test_a_missing_rated_blocking_voltage_rejected(self):
        soak = _soak()
        del soak["rated_reverse_voltage_v"]
        with self.assertRaises(ValueError):
            assess_reverse_bias_burn_in(_case(soak=soak))


if __name__ == "__main__":
    unittest.main()
