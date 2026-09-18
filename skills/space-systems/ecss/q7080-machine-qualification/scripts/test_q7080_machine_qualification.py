#!/usr/bin/env python3
"""Contract test for powder bed fusion machine qualification (offline)."""

import copy
import statistics
import unittest

from q7080_machine_qualification_logic import (
    CALIBRATION_DUE,
    CALIBRATION_OVERDUE,
    CALIBRATION_VALID,
    DEFAULT_CAPABILITY_POLICY,
    DEFAULT_ENVIRONMENT_LIMITS,
    DELTA_QUALIFICATION,
    MACHINE_LIMITED,
    MACHINE_NOT_QUALIFIED,
    MACHINE_QUALIFIED,
    REQUALIFICATION_REQUIRED,
    WITHIN_ENVELOPE,
    calibration_status,
    capability_index,
    capability_statistics,
    envelope_change_impact,
    grade_calibration,
    grade_environment,
    qualification_envelope,
    qualify_machine,
    validate_calibration_item,
)

LASER_METER = {
    "item": "laser-power-meter",
    "days_since_calibration": 120,
    "interval_days": 365,
    "warning_days": 30,
}

PLATE_THERMOCOUPLE = {
    "item": "build-plate-thermocouple",
    "days_since_calibration": 300,
    "interval_days": 365,
    "warning_days": 30,
}

READINGS = {
    "residual_oxygen_ppm": 400.0,
    "dew_point_c": -35.0,
    "chamber_leak_rate_mbar_l_s": 2.0e-3,
}

SPECIMENS = [99.70, 99.80, 99.75, 99.72, 99.81, 99.78]

CASE = {
    "machine": "pbf-07",
    "material": "ti-6al-4v-grade-23",
    "layer_thickness_um": 30.0,
    "parameter_set": "ps-a",
    "calibration_items": [LASER_METER, PLATE_THERMOCOUPLE],
    "environment_readings": READINGS,
    "specimen_values": SPECIMENS,
    "lower_specification": 99.50,
}


def _item(base, **overrides):
    item = copy.deepcopy(base)
    item.update(overrides)
    return item


def _case(**overrides):
    case = copy.deepcopy(CASE)
    case.update(overrides)
    return case


class CalibrationTests(unittest.TestCase):
    def test_an_item_inside_its_interval_is_valid(self):
        self.assertEqual(calibration_status(LASER_METER)["status"], CALIBRATION_VALID)

    def test_an_item_inside_the_warning_window_is_due(self):
        item = _item(LASER_METER, days_since_calibration=350)
        self.assertEqual(calibration_status(item)["status"], CALIBRATION_DUE)

    def test_an_item_past_its_interval_is_overdue_and_counts_the_days(self):
        item = _item(LASER_METER, days_since_calibration=400)
        status = calibration_status(item)
        self.assertEqual(status["status"], CALIBRATION_OVERDUE)
        self.assertEqual(status["days_overdue"], 35)

    def test_an_item_exactly_on_its_interval_is_not_yet_overdue(self):
        item = _item(LASER_METER, days_since_calibration=365, warning_days=0)
        self.assertEqual(calibration_status(item)["status"], CALIBRATION_DUE)

    def test_a_non_mapping_item_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_calibration_item("laser-power-meter")

    def test_a_warning_window_longer_than_the_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_calibration_item(_item(LASER_METER, warning_days=400))

    def test_a_zero_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_calibration_item(_item(LASER_METER, interval_days=0))

    def test_the_schedule_separates_the_overdue_from_the_due(self):
        graded = grade_calibration(
            [_item(LASER_METER, days_since_calibration=400),
             _item(PLATE_THERMOCOUPLE, days_since_calibration=350)]
        )
        self.assertEqual(graded["overdue"], ("laser-power-meter",))
        self.assertEqual(graded["due"], ("build-plate-thermocouple",))

    def test_a_repeated_calibrated_item_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_calibration([LASER_METER, dict(LASER_METER)])

    def test_an_empty_calibration_schedule_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_calibration([])


class EnvironmentTests(unittest.TestCase):
    def test_a_controlled_chamber_is_within_every_limit(self):
        for entry in grade_environment(READINGS):
            self.assertEqual(entry["verdict"], "within-limit")

    def test_residual_oxygen_above_the_limit_is_outside(self):
        graded = grade_environment(dict(READINGS, residual_oxygen_ppm=1500.0))
        breaches = [e["parameter"] for e in graded if e["verdict"] == "outside-limit"]
        self.assertEqual(breaches, ["residual-oxygen-ppm"])

    def test_a_reading_exactly_on_the_limit_is_within_it(self):
        graded = grade_environment(dict(READINGS, residual_oxygen_ppm=1000.0))
        self.assertEqual(graded[0]["verdict"], "within-limit")

    def test_a_warm_dew_point_is_outside_the_limit(self):
        graded = grade_environment(dict(READINGS, dew_point_c=-5.0))
        breaches = [e["parameter"] for e in graded if e["verdict"] == "outside-limit"]
        self.assertIn("chamber-dew-point-c", breaches)

    def test_a_missing_reading_is_rejected(self):
        readings = dict(READINGS)
        del readings["dew_point_c"]
        with self.assertRaises(ValueError):
            grade_environment(readings)

    def test_an_incomplete_limit_set_is_rejected(self):
        limits = dict(DEFAULT_ENVIRONMENT_LIMITS)
        del limits["max_dew_point_c"]
        with self.assertRaises(ValueError):
            grade_environment(READINGS, limits)


class CapabilityTests(unittest.TestCase):
    def test_the_statistics_match_the_library_values(self):
        stats = capability_statistics(SPECIMENS)
        self.assertEqual(stats["count"], 6)
        self.assertAlmostEqual(stats["mean"], statistics.fmean(SPECIMENS), places=12)
        self.assertAlmostEqual(
            stats["sample_standard_deviation"], statistics.stdev(SPECIMENS), places=12
        )

    def test_too_few_specimens_are_rejected(self):
        with self.assertRaises(ValueError):
            capability_statistics(SPECIMENS[:3])

    def test_a_non_numeric_specimen_is_rejected(self):
        with self.assertRaises(ValueError):
            capability_statistics(SPECIMENS[:5] + ["99.8"])

    def test_the_one_sided_index_uses_the_lower_specification(self):
        expected = (statistics.fmean(SPECIMENS) - 99.50) / (
            3.0 * statistics.stdev(SPECIMENS)
        )
        self.assertAlmostEqual(
            capability_index(SPECIMENS, lower_specification=99.50), expected, places=12
        )

    def test_the_two_sided_index_takes_the_nearer_bound(self):
        index = capability_index(
            SPECIMENS, lower_specification=99.50, upper_specification=99.80
        )
        self.assertLess(index, capability_index(SPECIMENS, lower_specification=99.50))

    def test_a_specification_set_with_no_bound_is_rejected(self):
        with self.assertRaises(ValueError):
            capability_index(SPECIMENS)

    def test_an_inverted_specification_band_is_rejected(self):
        with self.assertRaises(ValueError):
            capability_index(
                SPECIMENS, lower_specification=99.80, upper_specification=99.50
            )

    def test_a_specimen_set_with_no_spread_has_no_index(self):
        with self.assertRaises(ValueError):
            capability_index([99.7] * 6, lower_specification=99.5)


class EnvelopeTests(unittest.TestCase):
    def test_an_envelope_normalizes_its_four_parts(self):
        envelope = qualification_envelope("pbf-07", "ti-6al-4v-grade-23", 30.0, "ps-a")
        self.assertEqual(envelope["machine"], "pbf-07")
        self.assertAlmostEqual(envelope["layer_thickness_um"], 30.0, places=12)

    def test_an_unnamed_parameter_set_is_rejected(self):
        with self.assertRaises(ValueError):
            qualification_envelope("pbf-07", "ti-6al-4v-grade-23", 30.0, " ")

    def test_an_identical_envelope_needs_nothing(self):
        envelope = qualification_envelope("pbf-07", "ti-6al-4v-grade-23", 30.0, "ps-a")
        self.assertEqual(
            envelope_change_impact(envelope, dict(envelope)), WITHIN_ENVELOPE
        )

    def test_a_parameter_set_change_costs_a_delta_qualification(self):
        envelope = qualification_envelope("pbf-07", "ti-6al-4v-grade-23", 30.0, "ps-a")
        self.assertEqual(
            envelope_change_impact(envelope, dict(envelope, parameter_set="ps-b")),
            DELTA_QUALIFICATION,
        )

    def test_a_layer_thickness_change_costs_a_requalification(self):
        envelope = qualification_envelope("pbf-07", "ti-6al-4v-grade-23", 30.0, "ps-a")
        self.assertEqual(
            envelope_change_impact(envelope, dict(envelope, layer_thickness_um=60.0)),
            REQUALIFICATION_REQUIRED,
        )

    def test_a_material_change_costs_a_requalification(self):
        envelope = qualification_envelope("pbf-07", "ti-6al-4v-grade-23", 30.0, "ps-a")
        self.assertEqual(
            envelope_change_impact(envelope, dict(envelope, material="in718")),
            REQUALIFICATION_REQUIRED,
        )

    def test_a_thickness_move_inside_the_tolerance_stays_in_the_envelope(self):
        envelope = qualification_envelope("pbf-07", "ti-6al-4v-grade-23", 30.0, "ps-a")
        self.assertEqual(
            envelope_change_impact(
                envelope, dict(envelope, layer_thickness_um=30.5),
                layer_thickness_tolerance_um=0.5,
            ),
            WITHIN_ENVELOPE,
        )

    def test_an_envelope_missing_a_part_is_rejected(self):
        with self.assertRaises(ValueError):
            envelope_change_impact({"machine": "pbf-07"}, {"machine": "pbf-07"})


class QualificationTests(unittest.TestCase):
    def test_a_clean_machine_is_qualified(self):
        self.assertEqual(qualify_machine(CASE)["verdict"], MACHINE_QUALIFIED)

    def test_an_overdue_calibration_blocks_qualification(self):
        case = _case(
            calibration_items=[
                _item(LASER_METER, days_since_calibration=400), PLATE_THERMOCOUPLE
            ]
        )
        result = qualify_machine(case)
        self.assertEqual(result["verdict"], MACHINE_NOT_QUALIFIED)
        self.assertTrue(any("overdue" in f for f in result["findings"]))

    def test_a_chamber_outside_its_limits_blocks_qualification(self):
        case = _case(
            environment_readings=dict(READINGS, residual_oxygen_ppm=1800.0)
        )
        result = qualify_machine(case)
        self.assertEqual(result["verdict"], MACHINE_NOT_QUALIFIED)
        self.assertEqual(result["environment_breaches"], ("residual-oxygen-ppm",))

    def test_a_scattered_witness_build_blocks_qualification(self):
        case = _case(specimen_values=[99.9, 98.4, 99.6, 98.8, 99.9, 98.2])
        self.assertEqual(qualify_machine(case)["verdict"], MACHINE_NOT_QUALIFIED)

    def test_a_calibration_falling_due_limits_rather_than_blocks(self):
        case = _case(
            calibration_items=[
                _item(LASER_METER, days_since_calibration=350), PLATE_THERMOCOUPLE
            ]
        )
        self.assertEqual(qualify_machine(case)["verdict"], MACHINE_LIMITED)

    def test_an_index_between_the_two_thresholds_limits_the_verdict(self):
        policy = dict(DEFAULT_CAPABILITY_POLICY,
                      minimum_capability_index=1.33,
                      preferred_capability_index=3.0)
        self.assertEqual(
            qualify_machine(CASE, policy=policy)["verdict"], MACHINE_LIMITED
        )

    def test_the_verdict_carries_the_envelope_it_is_tied_to(self):
        envelope = qualify_machine(CASE)["envelope"]
        self.assertEqual(envelope["parameter_set"], "ps-a")
        self.assertEqual(envelope["material"], "ti-6al-4v-grade-23")

    def test_a_policy_whose_preferred_index_is_below_the_minimum_is_rejected(self):
        policy = dict(DEFAULT_CAPABILITY_POLICY, preferred_capability_index=1.0)
        with self.assertRaises(ValueError):
            qualify_machine(CASE, policy=policy)

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            qualify_machine("pbf-07")


if __name__ == "__main__":
    unittest.main()
