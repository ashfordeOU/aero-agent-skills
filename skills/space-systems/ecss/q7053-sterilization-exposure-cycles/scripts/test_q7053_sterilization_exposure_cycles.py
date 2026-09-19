"""Contract tests for the sterilization exposure cycle accounting logic."""

import unittest

from q7053_sterilization_exposure_cycles_logic import (
    DOSE_TOLERANCE_KGY,
    TIME_TOLERANCE_S,
    accumulated_dose_kgy,
    assess_exposure_campaign,
    dwell_time_at_or_above,
    grade_cycle,
    lethality_equivalent_s,
    peak_temperature,
    validate_log,
)

# A square dry-heat cycle: ramp up, 1800 s of dwell, ramp down.
SQUARE_LOG = [(0.0, 20.0), (600.0, 125.0), (2400.0, 125.0), (3000.0, 20.0)]
REFERENCE_C = 125.0
Z_VALUE_C = 20.0


def cycle(identifier, log=None, setpoint=125.0, required=1800.0, **extra):
    record = {
        "id": identifier,
        "log": log if log is not None else SQUARE_LOG,
        "setpoint_c": setpoint,
        "required_dwell_s": required,
    }
    record.update(extra)
    return record


class LogValidationTests(unittest.TestCase):
    def test_log_is_returned_as_float_pairs(self):
        log = validate_log([(0, 20), (10, 30)])
        self.assertEqual(log, [(0.0, 20.0), (10.0, 30.0)])

    def test_single_sample_log_rejected(self):
        with self.assertRaises(ValueError):
            validate_log([(0.0, 20.0)])

    def test_non_increasing_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_log([(0.0, 20.0), (0.0, 30.0)])

    def test_backwards_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_log([(10.0, 20.0), (5.0, 30.0)])

    def test_negative_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_log([(-1.0, 20.0), (5.0, 30.0)])

    def test_malformed_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_log([(0.0, 20.0), (5.0,)])

    def test_peak_temperature_is_the_maximum(self):
        self.assertAlmostEqual(peak_temperature(SQUARE_LOG), 125.0, places=9)


class DwellTests(unittest.TestCase):
    def test_square_cycle_dwell_excludes_the_ramps(self):
        self.assertAlmostEqual(
            dwell_time_at_or_above(SQUARE_LOG, 125.0), 1800.0, places=9
        )

    def test_rising_crossing_is_interpolated(self):
        self.assertAlmostEqual(
            dwell_time_at_or_above([(0.0, 100.0), (100.0, 140.0)], 120.0), 50.0, places=9
        )

    def test_falling_crossing_is_interpolated(self):
        self.assertAlmostEqual(
            dwell_time_at_or_above([(0.0, 140.0), (100.0, 100.0)], 120.0), 50.0, places=9
        )

    def test_a_dip_below_the_setpoint_is_not_credited(self):
        dipped = [(0.0, 130.0), (100.0, 110.0), (200.0, 130.0)]
        self.assertAlmostEqual(
            dwell_time_at_or_above(dipped, 130.0), 0.0, places=9
        )

    def test_a_cycle_never_reaching_the_setpoint_has_no_dwell(self):
        self.assertAlmostEqual(
            dwell_time_at_or_above([(0.0, 20.0), (100.0, 80.0)], 125.0), 0.0, places=9
        )

    def test_a_cycle_wholly_above_the_setpoint_credits_its_whole_span(self):
        self.assertAlmostEqual(
            dwell_time_at_or_above([(0.0, 130.0), (240.0, 135.0)], 125.0), 240.0, places=9
        )


class LethalityTests(unittest.TestCase):
    def test_isothermal_at_the_reference_is_its_own_duration(self):
        log = [(0.0, REFERENCE_C), (1800.0, REFERENCE_C)]
        self.assertAlmostEqual(
            lethality_equivalent_s(log, REFERENCE_C, Z_VALUE_C), 1800.0, places=9
        )

    def test_one_resistance_step_hotter_is_worth_ten_times(self):
        log = [(0.0, REFERENCE_C + Z_VALUE_C), (1800.0, REFERENCE_C + Z_VALUE_C)]
        self.assertAlmostEqual(
            lethality_equivalent_s(log, REFERENCE_C, Z_VALUE_C), 18000.0, places=6
        )

    def test_one_resistance_step_cooler_is_worth_a_tenth(self):
        log = [(0.0, REFERENCE_C - Z_VALUE_C), (1800.0, REFERENCE_C - Z_VALUE_C)]
        self.assertAlmostEqual(
            lethality_equivalent_s(log, REFERENCE_C, Z_VALUE_C), 180.0, places=9
        )

    def test_hotter_cycle_of_equal_dwell_carries_more_equivalence(self):
        cool = [(0.0, 120.0), (1800.0, 120.0)]
        hot = [(0.0, 130.0), (1800.0, 130.0)]
        self.assertGreater(
            lethality_equivalent_s(hot, REFERENCE_C, Z_VALUE_C),
            lethality_equivalent_s(cool, REFERENCE_C, Z_VALUE_C),
        )

    def test_zero_resistance_parameter_rejected(self):
        with self.assertRaises(ValueError):
            lethality_equivalent_s(SQUARE_LOG, REFERENCE_C, 0.0)


class DoseTests(unittest.TestCase):
    def test_dose_is_rate_times_time(self):
        self.assertAlmostEqual(accumulated_dose_kgy(10.0, 3600.0), 10.0, places=9)

    def test_half_an_hour_is_half_the_dose(self):
        self.assertAlmostEqual(accumulated_dose_kgy(10.0, 1800.0), 5.0, places=9)

    def test_zero_rate_delivers_nothing(self):
        self.assertAlmostEqual(accumulated_dose_kgy(0.0, 3600.0), 0.0, places=12)

    def test_negative_rate_rejected(self):
        with self.assertRaises(ValueError):
            accumulated_dose_kgy(-1.0, 3600.0)


class CycleGradingTests(unittest.TestCase):
    def test_conforming_cycle(self):
        record = grade_cycle(cycle("C1"), 150.0, REFERENCE_C, Z_VALUE_C)
        self.assertTrue(record["conforming"])
        self.assertAlmostEqual(record["dwell_s"], 1800.0, places=9)

    def test_dwell_exactly_at_the_requirement_is_met(self):
        record = grade_cycle(cycle("C2", required=1800.0), 150.0, REFERENCE_C, Z_VALUE_C)
        self.assertAlmostEqual(record["dwell_s"] - record["required_dwell_s"], 0.0, places=9)
        self.assertTrue(record["dwell_met"])

    def test_under_dwell_cycle_does_not_conform(self):
        record = grade_cycle(cycle("C3", required=3600.0), 150.0, REFERENCE_C, Z_VALUE_C)
        self.assertFalse(record["dwell_met"])
        self.assertFalse(record["conforming"])

    def test_excursion_above_the_material_limit_does_not_conform(self):
        hot = [(0.0, 20.0), (600.0, 180.0), (2400.0, 180.0), (3000.0, 20.0)]
        record = grade_cycle(cycle("C4", log=hot), 150.0, REFERENCE_C, Z_VALUE_C)
        self.assertFalse(record["within_material_limit"])
        self.assertFalse(record["conforming"])

    def test_peak_exactly_at_the_material_limit_is_within_it(self):
        record = grade_cycle(cycle("C5"), 125.0, REFERENCE_C, Z_VALUE_C)
        self.assertAlmostEqual(record["peak_temperature_c"], 125.0, places=9)
        self.assertTrue(record["within_material_limit"])

    def test_radiation_dose_is_carried_on_the_record(self):
        record = grade_cycle(
            cycle("C6", dose_rate_kgy_per_h=5.0, dose_duration_s=3600.0),
            150.0, REFERENCE_C, Z_VALUE_C,
        )
        self.assertAlmostEqual(record["dose_kgy"], 5.0, places=9)

    def test_cycle_without_dose_records_zero(self):
        record = grade_cycle(cycle("C7"), 150.0, REFERENCE_C, Z_VALUE_C)
        self.assertAlmostEqual(record["dose_kgy"], 0.0, places=12)

    def test_cycle_missing_a_key_rejected(self):
        bad = cycle("C8")
        del bad["setpoint_c"]
        with self.assertRaises(ValueError):
            grade_cycle(bad, 150.0, REFERENCE_C, Z_VALUE_C)

    def test_unnamed_cycle_rejected(self):
        with self.assertRaises(ValueError):
            grade_cycle(cycle(""), 150.0, REFERENCE_C, Z_VALUE_C)


class CampaignTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "cycles": [cycle("C1"), cycle("C2"), cycle("C3")],
            "material_limit_c": 150.0,
            "reference_c": REFERENCE_C,
            "z_value_c": Z_VALUE_C,
            "required_cycles": 3,
            "qualified_dose_kgy": 30.0,
        }
        spec.update(overrides)
        return spec

    def test_conforming_campaign_is_credited(self):
        result = assess_exposure_campaign(self._spec())
        self.assertTrue(result["credited"])
        self.assertEqual(result["findings"], [])

    def test_totals_add_across_cycles(self):
        result = assess_exposure_campaign(self._spec())
        self.assertAlmostEqual(result["total_dwell_s"], 5400.0, places=9)
        self.assertEqual(result["conforming_cycles"], 3)

    def test_lethality_equivalent_is_additive(self):
        result = assess_exposure_campaign(self._spec())
        single = lethality_equivalent_s(SQUARE_LOG, REFERENCE_C, Z_VALUE_C)
        self.assertAlmostEqual(
            result["total_lethality_equivalent_s"], 3.0 * single, places=6
        )

    def test_short_campaign_is_a_finding(self):
        result = assess_exposure_campaign(self._spec(cycles=[cycle("C1"), cycle("C2")]))
        self.assertFalse(result["credited"])
        self.assertTrue(any("conforming cycles" in f for f in result["findings"]))

    def test_under_dwell_cycle_is_named_in_the_findings(self):
        cycles = [cycle("C1"), cycle("SHORT", log=[(0.0, 20.0), (100.0, 126.0)]), cycle("C3")]
        result = assess_exposure_campaign(self._spec(cycles=cycles))
        self.assertTrue(any("SHORT" in f for f in result["findings"]))

    def test_cumulative_dose_above_the_qualified_value_is_a_finding(self):
        cycles = [
            cycle("R1", dose_rate_kgy_per_h=20.0, dose_duration_s=3600.0),
            cycle("R2", dose_rate_kgy_per_h=20.0, dose_duration_s=3600.0),
            cycle("R3", dose_rate_kgy_per_h=20.0, dose_duration_s=3600.0),
        ]
        result = assess_exposure_campaign(self._spec(cycles=cycles))
        self.assertAlmostEqual(result["total_dose_kgy"], 60.0, places=9)
        self.assertTrue(any("accumulated dose" in f for f in result["findings"]))

    def test_dose_exactly_at_the_qualified_value_is_credited(self):
        cycles = [
            cycle("R1", dose_rate_kgy_per_h=10.0, dose_duration_s=3600.0),
            cycle("R2", dose_rate_kgy_per_h=10.0, dose_duration_s=3600.0),
            cycle("R3", dose_rate_kgy_per_h=10.0, dose_duration_s=3600.0),
        ]
        result = assess_exposure_campaign(self._spec(cycles=cycles, qualified_dose_kgy=30.0))
        self.assertAlmostEqual(
            result["total_dose_kgy"] - result["qualified_dose_kgy"], 0.0, places=9
        )
        self.assertTrue(result["credited"])

    def test_duplicated_cycle_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_exposure_campaign(self._spec(cycles=[cycle("C1"), cycle("C1")]))

    def test_empty_cycle_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_exposure_campaign(self._spec(cycles=[]))

    def test_zero_required_cycles_rejected(self):
        with self.assertRaises(ValueError):
            assess_exposure_campaign(self._spec(required_cycles=0))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["z_value_c"]
        with self.assertRaises(ValueError):
            assess_exposure_campaign(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_exposure_campaign(["cycles"])

    def test_tolerances_are_representation_allowances_only(self):
        self.assertAlmostEqual(TIME_TOLERANCE_S, 1e-9, places=12)
        self.assertAlmostEqual(DOSE_TOLERANCE_KGY, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main()
