#!/usr/bin/env python3
"""Contract tests for the test equipment control of clause 5.6.2.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused release
policy, equipment never identified, no calibration record, calibration
run out on the day of use, a due day contradicting the interval, an
unapproved configuration change, an accuracy ratio short of the bar, a
measurand outside the usable span, and a stale functional check.
"""

import unittest

from q20_test_equipment_logic import (
    CALIBRATION_NOT_VALID,
    CONFIGURATION_NOT_CONTROLLED,
    DEFAULT_TEST_EQUIPMENT_POLICY,
    EQUIPMENT_NOT_READY,
    KIND_ELECTRICAL_GSE,
    KIND_MEASUREMENT_INSTRUMENT,
    MEASUREMENT_CAPABILITY_INSUFFICIENT,
    RANGE_NOT_SUITABLE,
    RELEASED_FOR_TEST,
    TEST_EQUIPMENT_NOT_IDENTIFIED,
    accuracy_ratio,
    assess_test_equipment,
    calibration_due_day,
    calibration_is_valid,
    calibration_margin_days,
    capability_is_sufficient,
    configuration_is_controlled,
    guard_band,
    measurand_span,
    range_is_suitable,
    range_span,
    readiness_gaps,
    unreleased_equipment,
    validate_equipment,
    validate_test_equipment_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_TEST_EQUIPMENT_POLICY)
    policy.update(overrides)
    return policy


def _equipment(identifier="DMM-4401", **overrides):
    item = {
        "equipment_identifier": identifier,
        "kind": KIND_MEASUREMENT_INSTRUMENT,
        "calibrated_on_day": 100,
        "calibration_interval_days": 180,
        "calibration_due_day": None,
        "use_day": 200,
        "measurement_uncertainty": 0.1,
        "required_tolerance": 0.4,
        "configuration_baseline": "TE-BL-7",
        "unapproved_configuration_changes": 0,
        "self_test_passed": True,
        "last_functional_check_day": 195,
        "range_min": 0.0,
        "range_max": 100.0,
        "measurand_min": 20.0,
        "measurand_max": 80.0,
    }
    item.update(overrides)
    return item


def _egse(**overrides):
    item = _equipment("EGSE-2210", kind=KIND_ELECTRICAL_GSE)
    item.update(overrides)
    return item


def _case(**overrides):
    case = {"policy": _policy(), "equipment": _equipment()}
    case.update(overrides)
    return case


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_usable(self):
        self.assertIs(
            validate_test_equipment_policy(DEFAULT_TEST_EQUIPMENT_POLICY),
            DEFAULT_TEST_EQUIPMENT_POLICY,
        )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_test_equipment_policy(4.0)

    def test_an_accuracy_ratio_below_one_refused(self):
        with self.assertRaises(ValueError):
            validate_test_equipment_policy(_policy(min_accuracy_ratio=0.5))

    def test_a_guard_band_swallowing_the_span_refused(self):
        with self.assertRaises(ValueError):
            validate_test_equipment_policy(_policy(range_guard_band=0.5))

    def test_a_zero_functional_check_window_refused(self):
        with self.assertRaises(ValueError):
            validate_test_equipment_policy(_policy(functional_check_window_days=0))

    def test_non_boolean_self_test_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_test_equipment_policy(_policy(require_self_test="if-there-is-time"))


class EquipmentValidationTests(unittest.TestCase):
    def test_equipment_is_read_back(self):
        record = validate_equipment(_equipment())
        self.assertEqual(record["equipment_identifier"], "DMM-4401")
        self.assertEqual(record["kind"], KIND_MEASUREMENT_INSTRUMENT)

    def test_unrecognised_kind_refused(self):
        with self.assertRaises(ValueError):
            validate_equipment(_equipment(kind="that-box-in-the-corner"))

    def test_an_inverted_range_refused(self):
        with self.assertRaises(ValueError):
            validate_equipment(_equipment(range_min=100.0, range_max=0.0))

    def test_an_inverted_measurand_refused(self):
        with self.assertRaises(ValueError):
            validate_equipment(_equipment(measurand_min=80.0, measurand_max=20.0))

    def test_zero_uncertainty_refused(self):
        with self.assertRaises(ValueError):
            validate_equipment(_equipment(measurement_uncertainty=0.0))

    def test_zero_calibration_interval_refused(self):
        with self.assertRaises(ValueError):
            validate_equipment(_equipment(calibration_interval_days=0))


class CalibrationTests(unittest.TestCase):
    def test_the_due_day_is_derived_from_the_interval(self):
        self.assertEqual(calibration_due_day(_equipment()), 280)

    def test_a_declared_due_day_agreeing_with_the_interval_is_kept(self):
        self.assertEqual(
            calibration_due_day(_equipment(calibration_due_day=280)), 280
        )

    def test_a_declared_due_day_contradicting_the_interval_refused(self):
        with self.assertRaises(ValueError):
            calibration_due_day(_equipment(calibration_due_day=400))

    def test_no_calibration_record_has_no_due_day(self):
        self.assertIsNone(calibration_due_day(_equipment(calibrated_on_day=None)))

    def test_the_margin_is_taken_at_the_day_of_use(self):
        self.assertEqual(calibration_margin_days(_equipment()), 80)

    def test_calibration_is_judged_at_the_day_of_use(self):
        self.assertTrue(calibration_is_valid(_equipment(use_day=280)))
        self.assertFalse(calibration_is_valid(_equipment(use_day=281)))

    def test_a_margin_on_uncalibrated_equipment_refused(self):
        with self.assertRaises(ValueError):
            calibration_margin_days(_equipment(calibrated_on_day=None))


class CapabilityAndRangeTests(unittest.TestCase):
    def test_the_accuracy_ratio_is_tolerance_over_uncertainty(self):
        self.assertAlmostEqual(accuracy_ratio(_equipment()), 4.0, places=9)

    def test_a_ratio_landing_on_the_bar_is_sufficient(self):
        self.assertTrue(capability_is_sufficient(_equipment()))

    def test_a_ratio_below_the_bar_is_not(self):
        self.assertFalse(
            capability_is_sufficient(_equipment(measurement_uncertainty=0.2))
        )

    def test_a_looser_policy_accepts_the_same_instrument(self):
        self.assertTrue(
            capability_is_sufficient(
                _equipment(measurement_uncertainty=0.2), _policy(min_accuracy_ratio=2.0)
            )
        )

    def test_the_spans_are_read_off_the_record(self):
        self.assertAlmostEqual(range_span(_equipment()), 100.0, places=9)
        self.assertAlmostEqual(measurand_span(_equipment()), 60.0, places=9)

    def test_the_guard_band_is_a_share_of_the_span(self):
        self.assertAlmostEqual(guard_band(_equipment()), 10.0, places=9)

    def test_a_measurand_inside_the_guard_bands_is_suitable(self):
        self.assertTrue(range_is_suitable(_equipment()))

    def test_a_measurand_landing_on_the_guard_band_is_still_suitable(self):
        self.assertTrue(
            range_is_suitable(_equipment(measurand_min=10.0, measurand_max=90.0))
        )

    def test_a_measurand_past_the_guard_band_is_not_suitable(self):
        self.assertFalse(
            range_is_suitable(_equipment(measurand_min=5.0, measurand_max=95.0))
        )

    def test_a_smaller_guard_band_admits_the_same_measurand(self):
        self.assertTrue(
            range_is_suitable(
                _equipment(measurand_min=5.0, measurand_max=95.0),
                _policy(range_guard_band=0.02),
            )
        )


class ConfigurationAndReadinessTests(unittest.TestCase):
    def test_a_named_baseline_with_nothing_pending_is_controlled(self):
        self.assertTrue(configuration_is_controlled(_equipment()))

    def test_no_baseline_is_not_controlled(self):
        self.assertFalse(
            configuration_is_controlled(_equipment(configuration_baseline="  "))
        )

    def test_an_unapproved_change_is_not_controlled(self):
        self.assertFalse(
            configuration_is_controlled(
                _equipment(unapproved_configuration_changes=1)
            )
        )

    def test_a_ready_item_has_no_readiness_gaps(self):
        self.assertEqual(readiness_gaps(_equipment()), ())

    def test_a_failed_self_test_is_a_readiness_gap(self):
        self.assertEqual(len(readiness_gaps(_equipment(self_test_passed=False))), 1)

    def test_a_self_test_may_be_waived_by_policy(self):
        self.assertEqual(
            readiness_gaps(
                _equipment(self_test_passed=False), _policy(require_self_test=False)
            ),
            (),
        )

    def test_a_missing_functional_check_is_a_readiness_gap(self):
        self.assertEqual(
            len(readiness_gaps(_equipment(last_functional_check_day=None))), 1
        )

    def test_a_stale_functional_check_is_a_readiness_gap(self):
        self.assertEqual(
            len(readiness_gaps(_equipment(last_functional_check_day=180))), 1
        )

    def test_a_functional_check_after_the_day_of_use_refused(self):
        with self.assertRaises(ValueError):
            readiness_gaps(_equipment(last_functional_check_day=220))


class AssessmentTests(unittest.TestCase):
    def test_a_sound_instrument_is_released(self):
        result = assess_test_equipment(_case())
        self.assertEqual(result["verdict"], RELEASED_FOR_TEST)
        self.assertAlmostEqual(result["accuracy_ratio"], 4.0, places=9)

    def test_no_equipment_at_all_stops_the_assessment(self):
        result = assess_test_equipment(_case(equipment=None))
        self.assertEqual(result["verdict"], TEST_EQUIPMENT_NOT_IDENTIFIED)

    def test_equipment_with_no_identifier_is_not_identified(self):
        result = assess_test_equipment(
            _case(equipment=_equipment(equipment_identifier="  "))
        )
        self.assertEqual(result["verdict"], TEST_EQUIPMENT_NOT_IDENTIFIED)

    def test_no_calibration_record_outranks_the_later_checks(self):
        result = assess_test_equipment(
            _case(equipment=_equipment(calibrated_on_day=None))
        )
        self.assertEqual(result["verdict"], CALIBRATION_NOT_VALID)

    def test_calibration_run_out_on_the_day_of_use_is_refused(self):
        result = assess_test_equipment(_case(equipment=_equipment(use_day=300)))
        self.assertEqual(result["verdict"], CALIBRATION_NOT_VALID)
        self.assertEqual(result["calibration_margin_days"], -20)

    def test_a_calibration_falling_due_soon_is_an_advisory(self):
        result = assess_test_equipment(
            _case(
                equipment=_equipment(use_day=278, last_functional_check_day=270)
            )
        )
        self.assertEqual(result["verdict"], RELEASED_FOR_TEST)
        self.assertEqual(len(result["advisories"]), 1)

    def test_an_uncontrolled_egse_build_is_refused(self):
        result = assess_test_equipment(
            _case(equipment=_egse(unapproved_configuration_changes=2))
        )
        self.assertEqual(result["verdict"], CONFIGURATION_NOT_CONTROLLED)
        self.assertEqual(result["kind"], KIND_ELECTRICAL_GSE)

    def test_an_insufficient_accuracy_ratio_is_refused(self):
        result = assess_test_equipment(
            _case(equipment=_equipment(measurement_uncertainty=0.2))
        )
        self.assertEqual(result["verdict"], MEASUREMENT_CAPABILITY_INSUFFICIENT)

    def test_a_measurand_outside_the_usable_span_is_refused(self):
        result = assess_test_equipment(
            _case(equipment=_equipment(measurand_min=2.0, measurand_max=98.0))
        )
        self.assertEqual(result["verdict"], RANGE_NOT_SUITABLE)

    def test_a_stale_functional_check_holds_the_equipment(self):
        result = assess_test_equipment(
            _case(equipment=_equipment(last_functional_check_day=150))
        )
        self.assertEqual(result["verdict"], EQUIPMENT_NOT_READY)
        self.assertEqual(len(result["readiness_gaps"]), 1)

    def test_a_set_up_names_only_the_items_it_holds_back(self):
        held = unreleased_equipment(
            [_equipment(), _egse(self_test_passed=False)], _policy()
        )
        self.assertEqual(held, (("EGSE-2210", EQUIPMENT_NOT_READY),))

    def test_the_same_item_twice_in_a_set_up_refused(self):
        with self.assertRaises(ValueError):
            unreleased_equipment([_equipment(), _equipment()])

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_test_equipment(("equipment",))


if __name__ == "__main__":
    unittest.main()
