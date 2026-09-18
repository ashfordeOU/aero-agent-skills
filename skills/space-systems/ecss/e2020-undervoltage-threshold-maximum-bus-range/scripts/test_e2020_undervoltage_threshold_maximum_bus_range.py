"""Contract tests for the clause 5.4.3.2.1 undervoltage threshold range logic."""

import unittest

from e2020_undervoltage_threshold_maximum_bus_range_logic import (
    ACCEPTED_REFERENCE,
    KNOWN_REFERENCES,
    VOLT_TOLERANCE_V,
    admissible_window,
    adjustment_step_volts,
    assess_threshold_range,
    reference_factor,
    setting_ladder,
    setting_verdicts,
    threshold_volts,
    validate_bus,
    validate_setting_range,
)

# A twenty-eight volt regulated bus: thirty-four volts at its worst-case top,
# twenty-six volts at the bottom of its steady band, and a load that stops
# behaving below twenty volts. Half a volt of comparator uncertainty closes
# the admissible window to 20.5 V .. 25.5 V.
BUS = {
    "bus_maximum_v": 34.0,
    "bus_steady_minimum_v": 26.0,
    "equipment_floor_v": 20.0,
    "sensing_uncertainty_v": 0.5,
}


def spec(bus=None, **range_overrides):
    settings = {
        "fraction_minimum": 0.62,
        "fraction_maximum": 0.74,
        "fraction_step": 0.01,
        "reference": "maximum-bus-voltage",
    }
    settings.update(range_overrides)
    return {"bus": dict(bus if bus is not None else BUS), "setting_range": settings}


class ValidationTests(unittest.TestCase):
    def test_valid_bus_returns_floats(self):
        bus = validate_bus(BUS)
        self.assertAlmostEqual(bus["bus_maximum_v"], 34.0, places=9)
        self.assertAlmostEqual(bus["sensing_uncertainty_v"], 0.5, places=9)

    def test_non_mapping_bus_rejected(self):
        with self.assertRaises(ValueError):
            validate_bus([34.0, 26.0])

    def test_missing_bus_key_rejected(self):
        partial = dict(BUS)
        del partial["equipment_floor_v"]
        with self.assertRaises(ValueError):
            validate_bus(partial)

    def test_negative_sensing_uncertainty_rejected(self):
        bad = dict(BUS, sensing_uncertainty_v=-0.1)
        with self.assertRaises(ValueError):
            validate_bus(bad)

    def test_boolean_voltage_rejected(self):
        bad = dict(BUS, bus_maximum_v=True)
        with self.assertRaises(ValueError):
            validate_bus(bad)

    def test_steady_minimum_above_maximum_rejected(self):
        bad = dict(BUS, bus_steady_minimum_v=40.0)
        with self.assertRaises(ValueError):
            validate_bus(bad)

    def test_equipment_floor_above_steady_minimum_rejected(self):
        bad = dict(BUS, equipment_floor_v=30.0)
        with self.assertRaises(ValueError):
            validate_bus(bad)

    def test_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_setting_range(
                {"fraction_minimum": 0.6, "fraction_maximum": 1.4, "fraction_step": 0.01}
            )

    def test_zero_fraction_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_setting_range(
                {"fraction_minimum": 0.6, "fraction_maximum": 0.7, "fraction_step": 0.0}
            )

    def test_fraction_step_wider_than_the_span_rejected(self):
        with self.assertRaises(ValueError):
            validate_setting_range(
                {"fraction_minimum": 0.6, "fraction_maximum": 0.62, "fraction_step": 0.1}
            )

    def test_maximum_fraction_below_minimum_rejected(self):
        with self.assertRaises(ValueError):
            validate_setting_range(
                {"fraction_minimum": 0.7, "fraction_maximum": 0.6, "fraction_step": 0.01}
            )

    def test_unknown_reference_rejected(self):
        with self.assertRaises(ValueError):
            reference_factor("bus-voltage-when-i-measured-it", validate_bus(BUS))

    def test_nominal_reference_without_a_nominal_voltage_rejected(self):
        with self.assertRaises(ValueError):
            reference_factor("nominal-bus-voltage", validate_bus(BUS))

    def test_missing_setting_range_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_threshold_range({"bus": dict(BUS)})


class ReferralTests(unittest.TestCase):
    def test_accepted_reference_is_the_maximum_bus_voltage(self):
        self.assertEqual(ACCEPTED_REFERENCE, "maximum-bus-voltage")
        self.assertIn("nominal-bus-voltage", KNOWN_REFERENCES)

    def test_maximum_reference_multiplies_by_the_maximum_bus_voltage(self):
        factor = reference_factor("maximum-bus-voltage", validate_bus(BUS))
        self.assertAlmostEqual(factor, 34.0, places=9)
        self.assertAlmostEqual(threshold_volts(0.7, factor), 23.8, places=9)

    def test_minimum_reference_gives_other_volts_for_the_same_fraction(self):
        bus = validate_bus(BUS)
        as_max = threshold_volts(0.7, reference_factor("maximum-bus-voltage", bus))
        as_min = threshold_volts(0.7, reference_factor("minimum-bus-voltage", bus))
        self.assertAlmostEqual(as_max, 23.8, places=9)
        self.assertAlmostEqual(as_min, 18.2, places=9)

    def test_ladder_walks_whole_steps_from_the_lowest_setting(self):
        ladder = setting_ladder(0.60, 0.70, 0.05)
        self.assertEqual(len(ladder), 3)
        self.assertAlmostEqual(ladder[0], 0.60, places=9)
        self.assertAlmostEqual(ladder[1], 0.65, places=9)
        self.assertAlmostEqual(ladder[2], 0.70, places=9)

    def test_single_point_range_returns_one_setting(self):
        self.assertEqual(len(setting_ladder(0.65, 0.65, 0.01)), 1)

    def test_adjustment_step_in_volts(self):
        self.assertAlmostEqual(adjustment_step_volts(0.01, 34.0), 0.34, places=9)

    def test_window_is_closed_in_from_both_ends_by_sensing_uncertainty(self):
        floor_v, ceiling_v = admissible_window(validate_bus(BUS))
        self.assertAlmostEqual(floor_v, 20.5, places=9)
        self.assertAlmostEqual(ceiling_v, 25.5, places=9)

    def test_a_setting_exactly_on_the_ceiling_is_admissible(self):
        bus = validate_bus(BUS)
        record = setting_verdicts([0.75], 34.0, bus)[0]
        _, ceiling_v = admissible_window(bus)
        self.assertAlmostEqual(record["volts"], ceiling_v, places=9)
        self.assertTrue(record["admissible"])


class AssessmentTests(unittest.TestCase):
    def test_nominal_design_is_compliant(self):
        result = assess_threshold_range(spec())
        self.assertEqual(result["verdict"], "compliant")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["reference_accepted"])
        self.assertTrue(result["ground_adjustable"])

    def test_every_settable_point_is_inside_the_window(self):
        result = assess_threshold_range(spec())
        self.assertEqual(result["usable_setting_count"], result["setting_count"])
        self.assertAlmostEqual(result["lowest_trip_v"], 21.08, places=9)
        self.assertAlmostEqual(result["highest_trip_v"], 25.16, places=9)

    def test_a_setting_below_the_equipment_floor_is_named(self):
        result = assess_threshold_range(
            spec(fraction_minimum=0.58, fraction_maximum=0.66, fraction_step=0.02)
        )
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertEqual(result["usable_setting_count"], 3)
        self.assertIn(
            "equipment operating floor", " | ".join(result["findings"])
        )

    def test_a_setting_inside_the_steady_band_is_named(self):
        result = assess_threshold_range(
            spec(fraction_minimum=0.72, fraction_maximum=0.78, fraction_step=0.02)
        )
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertEqual(result["usable_setting_count"], 2)
        self.assertIn("steady state bus band", " | ".join(result["findings"]))

    def test_nominal_reference_is_a_finding_even_when_the_volts_land_well(self):
        bus = dict(BUS, bus_nominal_v=28.0)
        result = assess_threshold_range(
            spec(
                bus=bus,
                fraction_minimum=0.75,
                fraction_maximum=0.89,
                reference="nominal-bus-voltage",
            )
        )
        self.assertFalse(result["reference_accepted"])
        self.assertEqual(result["usable_setting_count"], result["setting_count"])
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("maximum direct current bus voltage", result["findings"][0])

    def test_a_fixed_setting_is_not_ground_adjustable(self):
        result = assess_threshold_range(
            spec(fraction_minimum=0.68, fraction_maximum=0.68)
        )
        self.assertFalse(result["ground_adjustable"])
        self.assertEqual(result["setting_count"], 1)
        self.assertEqual(result["verdict"], "non-compliant")

    def test_a_coarse_ladder_fails_the_resolution_check(self):
        result = assess_threshold_range(spec(fraction_step=0.02))
        self.assertFalse(result["resolution_adequate"])
        self.assertAlmostEqual(result["adjustment_step_v"], 0.68, places=9)
        self.assertEqual(result["verdict"], "non-compliant")

    def test_uncertainty_that_closes_the_window_is_reported(self):
        bus = dict(BUS, sensing_uncertainty_v=4.0)
        result = assess_threshold_range(spec(bus=bus))
        self.assertFalse(result["window_open"])
        self.assertEqual(result["usable_setting_count"], 0)
        self.assertEqual(result["verdict"], "non-compliant")

    def test_reference_volts_are_reported_for_the_reader(self):
        result = assess_threshold_range(spec())
        self.assertAlmostEqual(result["reference_volts"], 34.0, places=9)
        self.assertEqual(result["reference"], "maximum-bus-voltage")

    def test_every_setting_record_carries_a_reason(self):
        result = assess_threshold_range(
            spec(fraction_minimum=0.58, fraction_maximum=0.66, fraction_step=0.02)
        )
        for record in result["settings"]:
            self.assertTrue(record["reason"])
            self.assertIn("volts", record)

    def test_volt_tolerance_is_tight_enough_to_be_a_representation_allowance(self):
        self.assertLessEqual(VOLT_TOLERANCE_V, 1e-6)


if __name__ == "__main__":
    unittest.main()
