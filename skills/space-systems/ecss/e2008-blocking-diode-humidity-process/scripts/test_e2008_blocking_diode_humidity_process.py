"""Contract tests for the clause 12.6.4.1.2 chamber sealing logic."""

import unittest

from e2008_blocking_diode_humidity_process_logic import (
    CHAMBER_ENCLOSURE_DEFICIENT,
    CHAMBER_SEALING_ACCEPTED,
    DEFAULT_BLOCKING_DIODE_SEALING_POLICY,
    HOURS_PER_DAY,
    SEALED_POPULATION_INCOMPLETE,
    SEALING_VERDICTS,
    SEAL_LEAK_EXCESSIVE,
    assess_blocking_diode_sealing,
    chamber_air_exchanges_per_day,
    chamber_free_volume_fraction,
    pressure_in_ambient_band,
    seal_leak_rate_kpa_per_h,
    sealed_population_fraction,
    validate_blocking_diode_sealing_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_BLOCKING_DIODE_SEALING_POLICY)
    policy.update(overrides)
    return policy


def _closure(**overrides):
    closure = {
        "decay_start_kpa": 102.0,
        "decay_end_kpa": 101.8,
        "seal_proof_dwell_h": 2.0,
        "working_pressure_kpa": 101.3,
        "chamber_volume_l": 200.0,
        "fixture_volume_l": 20.0,
        "device_volume_l": 0.5,
        "exposure_duration_h": 1000.0,
    }
    closure.update(overrides)
    return closure


def _case(**overrides):
    case = {
        "lot": {"lot_devices": 20, "sealed_devices": 20},
        "closure": _closure(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_the_default_policy_validates(self):
        self.assertIs(
            validate_blocking_diode_sealing_policy(
                DEFAULT_BLOCKING_DIODE_SEALING_POLICY
            ),
            DEFAULT_BLOCKING_DIODE_SEALING_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_sealing_policy("ambient")

    def test_an_inverted_pressure_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_sealing_policy(
                _policy(min_chamber_pressure_kpa=140.0)
            )

    def test_a_zero_leak_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_sealing_policy(
                _policy(max_seal_leak_rate_kpa_per_h=0.0)
            )

    def test_a_population_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_sealing_policy(
                _policy(min_sealed_population_fraction=1.5)
            )

    def test_a_negative_exposure_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_sealing_policy(
                _policy(min_exposure_duration_h=-5.0)
            )

    def test_every_sealing_verdict_is_declared_once(self):
        self.assertEqual(len(set(SEALING_VERDICTS)), 4)


class SealLeakTests(unittest.TestCase):
    def test_the_leak_rate_is_the_drop_over_the_hold(self):
        self.assertAlmostEqual(
            seal_leak_rate_kpa_per_h(102.0, 101.0, 2.0), 0.5, places=9
        )

    def test_a_chamber_that_held_pressure_reports_no_leak(self):
        self.assertAlmostEqual(
            seal_leak_rate_kpa_per_h(101.3, 101.3, 4.0), 0.0, places=9
        )

    def test_a_longer_hold_reports_a_smaller_rate(self):
        short = seal_leak_rate_kpa_per_h(102.0, 101.0, 1.0)
        long_hold = seal_leak_rate_kpa_per_h(102.0, 101.0, 4.0)
        self.assertLess(long_hold, short)

    def test_a_rising_chamber_is_not_a_leak_measurement(self):
        with self.assertRaises(ValueError):
            seal_leak_rate_kpa_per_h(101.0, 105.0, 2.0)

    def test_a_zero_length_hold_rejected(self):
        with self.assertRaises(ValueError):
            seal_leak_rate_kpa_per_h(102.0, 101.0, 0.0)

    def test_a_non_numeric_pressure_rejected(self):
        with self.assertRaises(ValueError):
            seal_leak_rate_kpa_per_h("102", 101.0, 2.0)

    def test_air_exchanges_scale_a_daily_leak_by_the_working_pressure(self):
        expected = 0.5 * HOURS_PER_DAY / 100.0
        self.assertAlmostEqual(
            chamber_air_exchanges_per_day(0.5, 100.0), expected, places=12
        )

    def test_a_sealed_chamber_exchanges_nothing(self):
        self.assertAlmostEqual(
            chamber_air_exchanges_per_day(0.0, 101.3), 0.0, places=12
        )

    def test_a_zero_working_pressure_rejected(self):
        with self.assertRaises(ValueError):
            chamber_air_exchanges_per_day(0.5, 0.0)


class PopulationTests(unittest.TestCase):
    def test_a_whole_lot_sealed_in_is_a_full_share(self):
        self.assertAlmostEqual(sealed_population_fraction(20, 20), 1.0, places=9)

    def test_a_partial_load_reports_its_share(self):
        self.assertAlmostEqual(sealed_population_fraction(15, 20), 0.75, places=9)

    def test_more_devices_than_the_lot_declares_rejected(self):
        with self.assertRaises(ValueError):
            sealed_population_fraction(21, 20)

    def test_a_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            sealed_population_fraction(0, 20)

    def test_a_fractional_device_count_rejected(self):
        with self.assertRaises(ValueError):
            sealed_population_fraction(4.5, 20)


class FreeVolumeTests(unittest.TestCase):
    def test_free_volume_is_what_fixture_and_devices_leave(self):
        fraction = chamber_free_volume_fraction(
            {
                "chamber_volume_l": 200.0,
                "fixture_volume_l": 20.0,
                "device_volume_l": 0.5,
                "device_count": 20,
            }
        )
        self.assertAlmostEqual(fraction, 0.85, places=9)

    def test_a_chamber_filled_to_its_walls_leaves_nothing_free(self):
        fraction = chamber_free_volume_fraction(
            {
                "chamber_volume_l": 100.0,
                "fixture_volume_l": 20.0,
                "device_volume_l": 4.0,
                "device_count": 20,
            }
        )
        self.assertAlmostEqual(fraction, 0.0, places=9)

    def test_a_denser_load_leaves_less_free_volume(self):
        loose = chamber_free_volume_fraction(
            {
                "chamber_volume_l": 200.0,
                "fixture_volume_l": 20.0,
                "device_volume_l": 0.5,
                "device_count": 10,
            }
        )
        dense = chamber_free_volume_fraction(
            {
                "chamber_volume_l": 200.0,
                "fixture_volume_l": 20.0,
                "device_volume_l": 0.5,
                "device_count": 40,
            }
        )
        self.assertLess(dense, loose)

    def test_a_load_larger_than_its_chamber_rejected(self):
        with self.assertRaises(ValueError):
            chamber_free_volume_fraction(
                {
                    "chamber_volume_l": 50.0,
                    "fixture_volume_l": 20.0,
                    "device_volume_l": 4.0,
                    "device_count": 20,
                }
            )

    def test_a_non_mapping_chamber_rejected(self):
        with self.assertRaises(ValueError):
            chamber_free_volume_fraction([200.0, 20.0, 0.5, 20])

    def test_a_negative_fixture_volume_rejected(self):
        with self.assertRaises(ValueError):
            chamber_free_volume_fraction(
                {
                    "chamber_volume_l": 200.0,
                    "fixture_volume_l": -1.0,
                    "device_volume_l": 0.5,
                    "device_count": 20,
                }
            )


class PressureBandTests(unittest.TestCase):
    def test_the_ambient_setpoint_sits_in_the_band(self):
        self.assertTrue(pressure_in_ambient_band(101.3, _policy()))

    def test_the_lower_edge_is_in_band(self):
        policy = _policy()
        edge = float(policy["min_chamber_pressure_kpa"])
        self.assertAlmostEqual(edge, policy["min_chamber_pressure_kpa"], places=9)
        self.assertTrue(pressure_in_ambient_band(edge, policy))

    def test_the_upper_edge_is_in_band(self):
        policy = _policy()
        edge = float(policy["max_chamber_pressure_kpa"])
        self.assertTrue(pressure_in_ambient_band(edge, policy))

    def test_a_pressurised_chamber_is_out_of_band(self):
        self.assertFalse(pressure_in_ambient_band(260.0, _policy()))

    def test_a_pumped_down_chamber_is_out_of_band(self):
        self.assertFalse(pressure_in_ambient_band(15.0, _policy()))

    def test_a_zero_pressure_rejected(self):
        with self.assertRaises(ValueError):
            pressure_in_ambient_band(0.0, _policy())


class SealingAssessmentTests(unittest.TestCase):
    def test_a_nominal_closure_is_accepted(self):
        result = assess_blocking_diode_sealing(_case())
        self.assertEqual(result["verdict"], CHAMBER_SEALING_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_the_leak_rate_and_exchanges_are_reported(self):
        result = assess_blocking_diode_sealing(_case())
        self.assertAlmostEqual(
            result["seal_leak_rate_kpa_per_h"], 0.1, places=9
        )
        self.assertAlmostEqual(
            result["air_exchanges_per_day"],
            result["seal_leak_rate_kpa_per_h"] * HOURS_PER_DAY / 101.3,
            places=12,
        )

    def test_a_leaking_closure_outranks_every_other_finding(self):
        result = assess_blocking_diode_sealing(
            _case(
                lot={"lot_devices": 20, "sealed_devices": 10},
                closure=_closure(decay_end_kpa=95.0),
            )
        )
        self.assertEqual(result["verdict"], SEAL_LEAK_EXCESSIVE)

    def test_a_leak_rate_exactly_at_the_allowance_is_accepted(self):
        policy = _policy()
        allowance = float(policy["max_seal_leak_rate_kpa_per_h"])
        result = assess_blocking_diode_sealing(
            _case(
                closure=_closure(
                    decay_start_kpa=102.0,
                    decay_end_kpa=102.0 - allowance * 2.0,
                    seal_proof_dwell_h=2.0,
                )
            ),
            policy,
        )
        self.assertAlmostEqual(
            result["seal_leak_rate_kpa_per_h"], allowance, places=9
        )
        self.assertEqual(result["verdict"], CHAMBER_SEALING_ACCEPTED)

    def test_a_slow_leak_over_a_low_pressure_still_trips_the_exchange_cap(self):
        result = assess_blocking_diode_sealing(
            _case(
                closure=_closure(
                    decay_start_kpa=102.0,
                    decay_end_kpa=101.7,
                    seal_proof_dwell_h=1.0,
                )
            )
        )
        self.assertEqual(result["verdict"], SEAL_LEAK_EXCESSIVE)

    def test_a_part_left_on_the_bench_is_a_population_finding(self):
        result = assess_blocking_diode_sealing(
            _case(lot={"lot_devices": 20, "sealed_devices": 19})
        )
        self.assertEqual(result["verdict"], SEALED_POPULATION_INCOMPLETE)
        self.assertAlmostEqual(
            result["sealed_population_fraction"], 0.95, places=9
        )

    def test_a_population_exactly_at_the_floor_is_accepted(self):
        policy = _policy()
        result = assess_blocking_diode_sealing(_case(), policy)
        self.assertAlmostEqual(
            result["sealed_population_fraction"],
            policy["min_sealed_population_fraction"],
            places=9,
        )
        self.assertEqual(result["verdict"], CHAMBER_SEALING_ACCEPTED)

    def test_a_pressurised_closure_is_an_enclosure_finding(self):
        result = assess_blocking_diode_sealing(
            _case(closure=_closure(working_pressure_kpa=300.0))
        )
        self.assertEqual(result["verdict"], CHAMBER_ENCLOSURE_DEFICIENT)
        self.assertFalse(result["pressure_in_band"])

    def test_a_packed_chamber_is_an_enclosure_finding(self):
        result = assess_blocking_diode_sealing(
            _case(closure=_closure(device_volume_l=4.0, chamber_volume_l=110.0))
        )
        self.assertEqual(result["verdict"], CHAMBER_ENCLOSURE_DEFICIENT)
        self.assertLess(result["chamber_free_volume_fraction"], 0.5)

    def test_a_free_volume_exactly_at_the_floor_is_accepted(self):
        policy = _policy()
        result = assess_blocking_diode_sealing(
            _case(
                closure=_closure(
                    chamber_volume_l=200.0,
                    fixture_volume_l=20.0,
                    device_volume_l=4.0,
                )
            ),
            policy,
        )
        self.assertAlmostEqual(
            result["chamber_free_volume_fraction"],
            policy["min_chamber_free_volume_fraction"],
            places=9,
        )
        self.assertEqual(result["verdict"], CHAMBER_SEALING_ACCEPTED)

    def test_a_short_seal_proof_hold_is_an_enclosure_finding(self):
        result = assess_blocking_diode_sealing(
            _case(
                closure=_closure(
                    decay_start_kpa=102.0,
                    decay_end_kpa=101.99,
                    seal_proof_dwell_h=0.25,
                )
            )
        )
        self.assertEqual(result["verdict"], CHAMBER_ENCLOSURE_DEFICIENT)

    def test_a_truncated_exposure_is_an_enclosure_finding(self):
        result = assess_blocking_diode_sealing(
            _case(closure=_closure(exposure_duration_h=240.0))
        )
        self.assertEqual(result["verdict"], CHAMBER_ENCLOSURE_DEFICIENT)

    def test_every_enclosure_finding_is_reported_not_only_the_first(self):
        result = assess_blocking_diode_sealing(
            _case(
                closure=_closure(
                    working_pressure_kpa=300.0, exposure_duration_h=240.0
                )
            )
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_a_missing_lot_block_rejected(self):
        case = _case()
        del case["lot"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_sealing(case)

    def test_a_missing_closure_block_rejected(self):
        case = _case()
        del case["closure"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_sealing(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_sealing(["lot"])

    def test_a_negative_exposure_duration_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_sealing(
                _case(closure=_closure(exposure_duration_h=-10.0))
            )

    def test_the_verdict_is_always_one_of_the_declared_verdicts(self):
        result = assess_blocking_diode_sealing(_case())
        self.assertIn(result["verdict"], SEALING_VERDICTS)


if __name__ == "__main__":
    unittest.main()
