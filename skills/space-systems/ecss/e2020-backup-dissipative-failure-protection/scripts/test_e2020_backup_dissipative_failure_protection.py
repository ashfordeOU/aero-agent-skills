"""Contract tests for the clause 5.2.14.3.1 backup dissipative protection logic."""

import unittest

from e2020_backup_dissipative_failure_protection_logic import (
    BACKUP_ADEQUATE,
    BACKUP_COVERAGE_GAP,
    BACKUP_DRIVE_WATCHDOG,
    BACKUP_MISSING,
    BACKUP_NOT_EVALUATED,
    BACKUP_NOT_INDEPENDENT,
    BACKUP_NOT_REQUIRED,
    BACKUP_REDUNDANT_SHUNT,
    BACKUP_SERIES_FUSE,
    BACKUP_THERMAL_CUTOUT,
    BACKUP_TOO_SLOW,
    BACKUP_UPSTREAM_LCL,
    DEFAULT_BACKUP_POLICY,
    DISSIPATIVE_FAILURE_MODES,
    FAIL_LOSS_OF_MODULATION,
    FAIL_OSCILLATING_DRIVE,
    FAIL_STUCK_CONDUCTING,
    FAIL_STUCK_OPEN,
    PROVISION_CONTINUOUS_RATING,
    PROVISION_INDEPENDENT_OFF_COMMAND,
    assess_backup_protection,
    backup_covers_mode,
    backup_shared_elements,
    categorize_backup_device,
    categorize_failure_mode,
    continuous_rating_provision_applies,
    derated_dissipation_capability_w,
    independent_off_command_paths,
    independent_off_command_provision_applies,
    time_to_thermal_limit_s,
    validate_backup_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_BACKUP_POLICY)
    policy.update(overrides)
    return policy


def _channel(**overrides):
    channel = {
        "failure_mode": FAIL_STUCK_CONDUCTING,
        "worst_case_dissipation_w": 40.0,
        "element_continuous_rating_w": 25.0,
        "thermal_capacity_j_per_k": 120.0,
        "initial_temperature_c": 55.0,
        "limit_temperature_c": 125.0,
        "switch_elements": ["drive-asic-u7", "gate-resistor-r12"],
        "off_command_paths": [
            {"id": "primary-off", "shared_elements": ["drive-asic-u7"]}
        ],
        "backup": {
            "device": BACKUP_THERMAL_CUTOUT,
            "action_time_s": 8.0,
            "shared_elements": ["thermostat-s3"],
        },
    }
    channel.update(overrides)
    return channel


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_backup_policy(DEFAULT_BACKUP_POLICY), DEFAULT_BACKUP_POLICY
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_backup_policy("derated")

    def test_a_derating_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_backup_policy(_policy(dissipation_derating=1.2))

    def test_a_derating_of_exactly_one_accepted(self):
        policy = _policy(dissipation_derating=1.0)
        self.assertIs(validate_backup_policy(policy), policy)

    def test_a_time_margin_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_backup_policy(_policy(min_thermal_time_margin=0.5))

    def test_a_zero_action_time_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_backup_policy(_policy(max_backup_action_time_s=0.0))


class VocabularyTests(unittest.TestCase):
    def test_every_known_failure_mode_round_trips(self):
        for mode in DISSIPATIVE_FAILURE_MODES:
            self.assertEqual(categorize_failure_mode(mode), mode)

    def test_an_unrecognised_failure_mode_rejected(self):
        with self.assertRaises(ValueError):
            categorize_failure_mode("stuck-warm")

    def test_an_empty_failure_mode_rejected(self):
        with self.assertRaises(ValueError):
            categorize_failure_mode("   ")

    def test_a_known_backup_device_round_trips(self):
        self.assertEqual(
            categorize_backup_device(" backup-series-fuse "), BACKUP_SERIES_FUSE
        )

    def test_an_unrecognised_backup_device_rejected(self):
        with self.assertRaises(ValueError):
            categorize_backup_device("spare-harness")


class CapabilityTests(unittest.TestCase):
    def test_capability_is_the_rating_after_derating(self):
        self.assertAlmostEqual(
            derated_dissipation_capability_w(50.0, 0.8), 40.0, places=9
        )

    def test_a_zero_rating_rejected(self):
        with self.assertRaises(ValueError):
            derated_dissipation_capability_w(0.0, 0.8)

    def test_a_derating_above_one_rejected_by_the_capability(self):
        with self.assertRaises(ValueError):
            derated_dissipation_capability_w(50.0, 1.4)


class ThermalTests(unittest.TestCase):
    def test_run_up_time_is_capacity_times_rise_over_power(self):
        self.assertAlmostEqual(
            time_to_thermal_limit_s(40.0, 120.0, 55.0, 125.0), 210.0, places=9
        )

    def test_a_limit_below_the_starting_temperature_rejected(self):
        with self.assertRaises(ValueError):
            time_to_thermal_limit_s(40.0, 120.0, 130.0, 125.0)

    def test_a_zero_dissipation_rejected(self):
        with self.assertRaises(ValueError):
            time_to_thermal_limit_s(0.0, 120.0, 55.0, 125.0)

    def test_a_negative_thermal_capacity_rejected(self):
        with self.assertRaises(ValueError):
            time_to_thermal_limit_s(40.0, -120.0, 55.0, 125.0)


class ProvisionTests(unittest.TestCase):
    def test_a_rating_that_absorbs_the_stuck_on_case_applies(self):
        channel = _channel(element_continuous_rating_w=80.0)
        self.assertTrue(continuous_rating_provision_applies(channel))

    def test_a_dissipation_exactly_on_the_derated_capability_applies(self):
        channel = _channel(
            worst_case_dissipation_w=40.0, element_continuous_rating_w=50.0
        )
        self.assertAlmostEqual(
            derated_dissipation_capability_w(50.0, 0.8),
            channel["worst_case_dissipation_w"],
            places=9,
        )
        self.assertTrue(continuous_rating_provision_applies(channel))

    def test_a_rating_short_of_the_stuck_on_case_does_not_apply(self):
        self.assertFalse(continuous_rating_provision_applies(_channel()))

    def test_an_off_command_path_clear_of_the_switch_applies(self):
        channel = _channel(
            off_command_paths=[
                {"id": "primary-off", "shared_elements": ["drive-asic-u7"]},
                {"id": "alternate-off", "shared_elements": ["relay-k4"]},
            ]
        )
        self.assertEqual(independent_off_command_paths(channel), ("alternate-off",))
        self.assertTrue(independent_off_command_provision_applies(channel))

    def test_an_off_command_path_through_the_failed_drive_does_not_apply(self):
        self.assertFalse(independent_off_command_provision_applies(_channel()))

    def test_a_duplicate_off_command_path_id_rejected(self):
        channel = _channel(
            off_command_paths=[
                {"id": "primary-off", "shared_elements": []},
                {"id": "primary-off", "shared_elements": []},
            ]
        )
        with self.assertRaises(ValueError):
            independent_off_command_paths(channel)

    def test_a_malformed_off_command_path_rejected(self):
        with self.assertRaises(ValueError):
            independent_off_command_paths(_channel(off_command_paths=[{"id": 5}]))

    def test_a_switch_element_named_twice_rejected(self):
        with self.assertRaises(ValueError):
            independent_off_command_paths(
                _channel(switch_elements=["drive-asic-u7", "drive-asic-u7"])
            )


class CoverageTests(unittest.TestCase):
    def test_a_series_fuse_answers_only_the_stuck_on_case(self):
        self.assertTrue(backup_covers_mode(BACKUP_SERIES_FUSE, FAIL_STUCK_CONDUCTING))
        self.assertFalse(
            backup_covers_mode(BACKUP_SERIES_FUSE, FAIL_LOSS_OF_MODULATION)
        )

    def test_a_redundant_shunt_answers_the_stuck_open_case(self):
        self.assertTrue(backup_covers_mode(BACKUP_REDUNDANT_SHUNT, FAIL_STUCK_OPEN))

    def test_a_drive_watchdog_does_nothing_about_a_stuck_on_switch(self):
        self.assertFalse(
            backup_covers_mode(BACKUP_DRIVE_WATCHDOG, FAIL_STUCK_CONDUCTING)
        )

    def test_an_upstream_lcl_answers_an_oscillating_drive(self):
        self.assertTrue(
            backup_covers_mode(BACKUP_UPSTREAM_LCL, FAIL_OSCILLATING_DRIVE)
        )

    def test_shared_parts_are_read_against_the_switch_not_the_schematic(self):
        channel = _channel(
            backup={
                "device": BACKUP_THERMAL_CUTOUT,
                "action_time_s": 8.0,
                "shared_elements": ["gate-resistor-r12", "thermostat-s3"],
            }
        )
        self.assertEqual(backup_shared_elements(channel), ("gate-resistor-r12",))


class ChannelAssessmentTests(unittest.TestCase):
    def test_an_untested_provision_outranks_everything_else(self):
        channel = _channel()
        del channel["off_command_paths"]
        result = assess_backup_protection(channel)
        self.assertEqual(result["verdict"], BACKUP_NOT_EVALUATED)
        self.assertEqual(
            result["untested_provisions"], [PROVISION_INDEPENDENT_OFF_COMMAND]
        )

    def test_an_untested_rating_is_reported_as_untested(self):
        channel = _channel()
        del channel["element_continuous_rating_w"]
        result = assess_backup_protection(channel)
        self.assertEqual(result["verdict"], BACKUP_NOT_EVALUATED)
        self.assertIn(PROVISION_CONTINUOUS_RATING, result["untested_provisions"])

    def test_an_applicable_earlier_provision_owes_no_backup(self):
        result = assess_backup_protection(_channel(element_continuous_rating_w=80.0))
        self.assertEqual(result["verdict"], BACKUP_NOT_REQUIRED)
        self.assertFalse(result["backup_required"])
        self.assertEqual(
            result["applicable_provisions"], [PROVISION_CONTINUOUS_RATING]
        )

    def test_a_required_backup_that_is_absent_is_reported(self):
        result = assess_backup_protection(_channel(backup=None))
        self.assertEqual(result["verdict"], BACKUP_MISSING)
        self.assertTrue(result["backup_required"])

    def test_a_backup_that_does_not_cover_the_mode_is_a_coverage_gap(self):
        result = assess_backup_protection(
            _channel(
                backup={
                    "device": BACKUP_DRIVE_WATCHDOG,
                    "action_time_s": 2.0,
                    "shared_elements": [],
                }
            )
        )
        self.assertEqual(result["verdict"], BACKUP_COVERAGE_GAP)
        self.assertFalse(result["covering"])

    def test_a_backup_sharing_a_part_with_the_switch_is_not_independent(self):
        result = assess_backup_protection(
            _channel(
                backup={
                    "device": BACKUP_THERMAL_CUTOUT,
                    "action_time_s": 8.0,
                    "shared_elements": ["drive-asic-u7"],
                }
            )
        )
        self.assertEqual(result["verdict"], BACKUP_NOT_INDEPENDENT)
        self.assertEqual(result["shared_elements"], ("drive-asic-u7",))

    def test_a_backup_slower_than_the_thermal_run_up_is_too_late(self):
        result = assess_backup_protection(
            _channel(
                backup={
                    "device": BACKUP_THERMAL_CUTOUT,
                    "action_time_s": 150.0,
                    "shared_elements": [],
                }
            ),
            _policy(max_backup_action_time_s=600.0),
        )
        self.assertEqual(result["verdict"], BACKUP_TOO_SLOW)
        self.assertAlmostEqual(result["time_to_limit_s"], 210.0, places=9)

    def test_a_backup_outside_the_policy_ceiling_is_too_late(self):
        result = assess_backup_protection(
            _channel(
                backup={
                    "device": BACKUP_THERMAL_CUTOUT,
                    "action_time_s": 90.0,
                    "shared_elements": [],
                }
            )
        )
        self.assertEqual(result["verdict"], BACKUP_TOO_SLOW)
        self.assertIsNone(result["time_to_limit_s"])

    def test_a_covering_independent_prompt_backup_is_adequate(self):
        result = assess_backup_protection(_channel())
        self.assertEqual(result["verdict"], BACKUP_ADEQUATE)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["time_to_limit_s"], 210.0, places=9)

    def test_a_backup_exactly_on_the_thermal_margin_is_adequate(self):
        result = assess_backup_protection(
            _channel(
                backup={
                    "device": BACKUP_THERMAL_CUTOUT,
                    "action_time_s": 105.0,
                    "shared_elements": [],
                }
            ),
            _policy(max_backup_action_time_s=600.0),
        )
        self.assertAlmostEqual(
            105.0 * float(DEFAULT_BACKUP_POLICY["min_thermal_time_margin"]),
            210.0,
            places=9,
        )
        self.assertEqual(result["verdict"], BACKUP_ADEQUATE)

    def test_a_stuck_open_mode_is_not_raced_against_a_thermal_run_up(self):
        result = assess_backup_protection(
            _channel(
                failure_mode=FAIL_STUCK_OPEN,
                backup={
                    "device": BACKUP_REDUNDANT_SHUNT,
                    "action_time_s": 30.0,
                    "shared_elements": [],
                },
            )
        )
        self.assertEqual(result["verdict"], BACKUP_ADEQUATE)
        self.assertIsNone(result["time_to_limit_s"])

    def test_an_unrecognised_declared_mode_rejected(self):
        with self.assertRaises(ValueError):
            assess_backup_protection(_channel(failure_mode="stuck-sideways"))

    def test_a_non_mapping_channel_rejected(self):
        with self.assertRaises(ValueError):
            assess_backup_protection(["dissipative-switch"])

    def test_every_finding_is_a_readable_sentence(self):
        result = assess_backup_protection(_channel(backup=None))
        self.assertTrue(result["findings"])
        for note in result["findings"]:
            self.assertIsInstance(note, str)
            self.assertGreater(len(note), 20)


if __name__ == "__main__":
    unittest.main()
