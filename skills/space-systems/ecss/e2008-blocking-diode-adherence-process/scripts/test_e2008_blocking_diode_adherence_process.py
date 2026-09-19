"""Contract tests for the clause 12.6.4.2.2 chamber entry logic."""

import unittest

from e2008_blocking_diode_adherence_process_logic import (
    CHAMBER_ENTRY_ACCEPTED,
    CHAMBER_ENTRY_DEFICIENT,
    DEFAULT_BLOCKING_DIODE_ENTRY_POLICY,
    ENTRY_VERDICTS,
    FOREIGN_DEVICE_IN_CHAMBER,
    LOT_ENTRY_INCOMPLETE,
    assess_blocking_diode_chamber_entry,
    batch_residence_schedule,
    lot_entry_completeness,
    pressure_in_ambient_band,
    reconcile_entry_manifest,
    validate_blocking_diode_entry_policy,
)

ROSTER = ["BD-001", "BD-002", "BD-003", "BD-004", "BD-005", "BD-006"]


def _policy(**overrides):
    policy = dict(DEFAULT_BLOCKING_DIODE_ENTRY_POLICY)
    policy.update(overrides)
    return policy


def _entry(**overrides):
    entry = {
        "loaded_serials": list(ROSTER),
        "batches": [
            {"devices": 3, "dwell_h": 24.0},
            {"devices": 3, "dwell_h": 24.0},
        ],
        "changeover_h": 1.0,
        "chamber_pressure_kpa": 101.3,
    }
    entry.update(overrides)
    return entry


def _case(**overrides):
    case = {"lot": {"serials": list(ROSTER)}, "entry": _entry()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_the_default_policy_validates(self):
        self.assertIs(
            validate_blocking_diode_entry_policy(
                DEFAULT_BLOCKING_DIODE_ENTRY_POLICY
            ),
            DEFAULT_BLOCKING_DIODE_ENTRY_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_entry_policy("every device")

    def test_an_inverted_pressure_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_entry_policy(
                _policy(min_chamber_pressure_kpa=150.0)
            )

    def test_a_completeness_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_entry_policy(
                _policy(min_lot_entry_completeness=1.2)
            )

    def test_a_zero_residence_dwell_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_entry_policy(_policy(min_residence_dwell_h=0.0))

    def test_a_fractional_batch_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_entry_policy(_policy(max_entry_batches=2.5))

    def test_every_entry_verdict_is_declared_once(self):
        self.assertEqual(len(set(ENTRY_VERDICTS)), 4)


class ManifestTests(unittest.TestCase):
    def test_a_whole_lot_reconciles_clean(self):
        manifest = reconcile_entry_manifest(ROSTER, ROSTER)
        self.assertEqual(manifest["entered_count"], 6)
        self.assertEqual(manifest["missing"], [])
        self.assertEqual(manifest["foreign"], [])
        self.assertEqual(manifest["repeated"], [])

    def test_a_device_left_on_the_bench_is_named(self):
        manifest = reconcile_entry_manifest(ROSTER, ROSTER[:-1])
        self.assertEqual(manifest["missing"], ["BD-006"])
        self.assertEqual(manifest["entered_count"], 5)

    def test_a_device_from_another_lot_is_named(self):
        manifest = reconcile_entry_manifest(ROSTER, ROSTER + ["BD-900"])
        self.assertEqual(manifest["foreign"], ["BD-900"])
        self.assertEqual(manifest["entered_count"], 6)

    def test_a_serial_logged_onto_two_trays_is_named(self):
        manifest = reconcile_entry_manifest(ROSTER, ROSTER + ["BD-003"])
        self.assertEqual(manifest["repeated"], ["BD-003"])

    def test_a_swap_shows_as_a_missing_and_a_foreign_device(self):
        loaded = ROSTER[:-1] + ["BD-900"]
        manifest = reconcile_entry_manifest(ROSTER, loaded)
        self.assertEqual(manifest["missing"], ["BD-006"])
        self.assertEqual(manifest["foreign"], ["BD-900"])
        self.assertEqual(manifest["entered_count"], 5)

    def test_surrounding_whitespace_does_not_make_a_new_device(self):
        manifest = reconcile_entry_manifest(ROSTER, [" BD-001 "] + ROSTER[1:])
        self.assertEqual(manifest["foreign"], [])
        self.assertEqual(manifest["entered_count"], 6)

    def test_a_roster_that_repeats_a_serial_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_entry_manifest(ROSTER + ["BD-001"], ROSTER)

    def test_an_empty_roster_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_entry_manifest([], ROSTER)

    def test_a_bare_string_is_not_a_serial_list(self):
        with self.assertRaises(ValueError):
            reconcile_entry_manifest("BD-001", ROSTER)

    def test_a_blank_serial_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_entry_manifest(ROSTER, ROSTER[:-1] + ["   "])

    def test_a_numeric_serial_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_entry_manifest(ROSTER, ROSTER[:-1] + [6])


class CompletenessTests(unittest.TestCase):
    def test_a_whole_lot_is_fully_complete(self):
        self.assertAlmostEqual(lot_entry_completeness(6, 6), 1.0, places=9)

    def test_a_partial_entry_reports_its_share(self):
        self.assertAlmostEqual(lot_entry_completeness(3, 6), 0.5, places=9)

    def test_an_empty_chamber_is_no_share_at_all(self):
        self.assertAlmostEqual(lot_entry_completeness(0, 6), 0.0, places=9)

    def test_more_devices_than_the_lot_declares_rejected(self):
        with self.assertRaises(ValueError):
            lot_entry_completeness(7, 6)

    def test_a_negative_entered_count_rejected(self):
        with self.assertRaises(ValueError):
            lot_entry_completeness(-1, 6)

    def test_a_zero_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            lot_entry_completeness(0, 0)


class BatchScheduleTests(unittest.TestCase):
    def test_a_single_batch_needs_no_changeover(self):
        schedule = batch_residence_schedule([{"devices": 6, "dwell_h": 24.0}], 1.0)
        self.assertEqual(schedule["batch_count"], 1)
        self.assertAlmostEqual(schedule["total_chamber_time_h"], 24.0, places=9)

    def test_two_batches_carry_one_changeover(self):
        schedule = batch_residence_schedule(
            [{"devices": 3, "dwell_h": 24.0}, {"devices": 3, "dwell_h": 24.0}], 1.0
        )
        self.assertAlmostEqual(schedule["total_chamber_time_h"], 49.0, places=9)
        self.assertEqual(schedule["devices_total"], 6)

    def test_the_shortest_batch_is_the_one_reported(self):
        schedule = batch_residence_schedule(
            [{"devices": 3, "dwell_h": 30.0}, {"devices": 3, "dwell_h": 18.0}], 1.0
        )
        self.assertAlmostEqual(schedule["shortest_dwell_h"], 18.0, places=9)

    def test_a_zero_changeover_is_allowed(self):
        schedule = batch_residence_schedule(
            [{"devices": 3, "dwell_h": 24.0}, {"devices": 3, "dwell_h": 24.0}], 0.0
        )
        self.assertAlmostEqual(schedule["total_chamber_time_h"], 48.0, places=9)

    def test_no_batch_at_all_rejected(self):
        with self.assertRaises(ValueError):
            batch_residence_schedule([], 1.0)

    def test_a_mapping_is_not_a_list_of_batches(self):
        with self.assertRaises(ValueError):
            batch_residence_schedule({"devices": 6, "dwell_h": 24.0}, 1.0)

    def test_a_batch_with_no_dwell_rejected(self):
        with self.assertRaises(ValueError):
            batch_residence_schedule([{"devices": 6}], 1.0)

    def test_a_batch_with_a_fractional_device_count_rejected(self):
        with self.assertRaises(ValueError):
            batch_residence_schedule([{"devices": 6.5, "dwell_h": 24.0}], 1.0)

    def test_a_negative_changeover_rejected(self):
        with self.assertRaises(ValueError):
            batch_residence_schedule([{"devices": 6, "dwell_h": 24.0}], -1.0)


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
        self.assertTrue(
            pressure_in_ambient_band(
                float(policy["max_chamber_pressure_kpa"]), policy
            )
        )

    def test_a_pressurised_chamber_is_out_of_band(self):
        self.assertFalse(pressure_in_ambient_band(280.0, _policy()))

    def test_a_pumped_down_chamber_is_out_of_band(self):
        self.assertFalse(pressure_in_ambient_band(12.0, _policy()))

    def test_a_zero_pressure_rejected(self):
        with self.assertRaises(ValueError):
            pressure_in_ambient_band(0.0, _policy())


class EntryAssessmentTests(unittest.TestCase):
    def test_a_nominal_entry_is_accepted(self):
        result = assess_blocking_diode_chamber_entry(_case())
        self.assertEqual(result["verdict"], CHAMBER_ENTRY_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_a_missing_device_outranks_every_other_finding(self):
        result = assess_blocking_diode_chamber_entry(
            _case(
                entry=_entry(
                    loaded_serials=ROSTER[:-1] + ["BD-900"],
                    chamber_pressure_kpa=300.0,
                )
            )
        )
        self.assertEqual(result["verdict"], LOT_ENTRY_INCOMPLETE)
        self.assertEqual(result["missing"], ["BD-006"])

    def test_a_partial_load_is_not_a_lot_result(self):
        result = assess_blocking_diode_chamber_entry(
            _case(
                entry=_entry(
                    loaded_serials=ROSTER[:3],
                    batches=[{"devices": 3, "dwell_h": 24.0}],
                )
            )
        )
        self.assertEqual(result["verdict"], LOT_ENTRY_INCOMPLETE)
        self.assertAlmostEqual(result["lot_entry_completeness"], 0.5, places=9)

    def test_a_completeness_exactly_at_the_floor_is_accepted(self):
        policy = _policy()
        result = assess_blocking_diode_chamber_entry(_case(), policy)
        self.assertAlmostEqual(
            result["lot_entry_completeness"],
            policy["min_lot_entry_completeness"],
            places=9,
        )
        self.assertEqual(result["verdict"], CHAMBER_ENTRY_ACCEPTED)

    def test_a_foreign_device_contaminates_a_complete_entry(self):
        result = assess_blocking_diode_chamber_entry(
            _case(entry=_entry(loaded_serials=ROSTER + ["BD-900"]))
        )
        self.assertEqual(result["verdict"], FOREIGN_DEVICE_IN_CHAMBER)
        self.assertEqual(result["foreign"], ["BD-900"])

    def test_a_serial_on_two_trays_contaminates_a_complete_entry(self):
        result = assess_blocking_diode_chamber_entry(
            _case(entry=_entry(loaded_serials=ROSTER + ["BD-003"]))
        )
        self.assertEqual(result["verdict"], FOREIGN_DEVICE_IN_CHAMBER)
        self.assertEqual(result["repeated"], ["BD-003"])

    def test_a_batch_sheet_that_does_not_match_the_manifest_is_a_finding(self):
        result = assess_blocking_diode_chamber_entry(
            _case(
                entry=_entry(
                    batches=[
                        {"devices": 3, "dwell_h": 24.0},
                        {"devices": 2, "dwell_h": 24.0},
                    ]
                )
            )
        )
        self.assertEqual(result["verdict"], CHAMBER_ENTRY_DEFICIENT)
        self.assertEqual(result["devices_total"], 5)

    def test_a_short_batch_is_an_entry_deficiency(self):
        result = assess_blocking_diode_chamber_entry(
            _case(
                entry=_entry(
                    batches=[
                        {"devices": 3, "dwell_h": 24.0},
                        {"devices": 3, "dwell_h": 6.0},
                    ]
                )
            )
        )
        self.assertEqual(result["verdict"], CHAMBER_ENTRY_DEFICIENT)
        self.assertAlmostEqual(result["shortest_dwell_h"], 6.0, places=9)

    def test_a_dwell_exactly_at_the_floor_is_accepted(self):
        policy = _policy()
        floor = float(policy["min_residence_dwell_h"])
        result = assess_blocking_diode_chamber_entry(
            _case(
                entry=_entry(
                    batches=[
                        {"devices": 3, "dwell_h": floor},
                        {"devices": 3, "dwell_h": floor},
                    ]
                )
            ),
            policy,
        )
        self.assertAlmostEqual(result["shortest_dwell_h"], floor, places=9)
        self.assertEqual(result["verdict"], CHAMBER_ENTRY_ACCEPTED)

    def test_too_many_batches_is_an_entry_deficiency(self):
        result = assess_blocking_diode_chamber_entry(
            _case(
                entry=_entry(
                    batches=[{"devices": 1, "dwell_h": 24.0} for _ in range(6)]
                )
            )
        )
        self.assertEqual(result["verdict"], CHAMBER_ENTRY_DEFICIENT)
        self.assertEqual(result["batch_count"], 6)

    def test_a_long_changeover_is_an_entry_deficiency(self):
        result = assess_blocking_diode_chamber_entry(
            _case(entry=_entry(changeover_h=9.0))
        )
        self.assertEqual(result["verdict"], CHAMBER_ENTRY_DEFICIENT)

    def test_a_pressurised_chamber_is_an_entry_deficiency(self):
        result = assess_blocking_diode_chamber_entry(
            _case(entry=_entry(chamber_pressure_kpa=300.0))
        )
        self.assertEqual(result["verdict"], CHAMBER_ENTRY_DEFICIENT)
        self.assertFalse(result["pressure_in_band"])

    def test_every_entry_finding_is_reported_not_only_the_first(self):
        result = assess_blocking_diode_chamber_entry(
            _case(entry=_entry(changeover_h=9.0, chamber_pressure_kpa=300.0))
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_the_total_chamber_time_is_reported(self):
        result = assess_blocking_diode_chamber_entry(_case())
        self.assertAlmostEqual(result["total_chamber_time_h"], 49.0, places=9)

    def test_a_missing_lot_block_rejected(self):
        case = _case()
        del case["lot"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_chamber_entry(case)

    def test_a_missing_entry_block_rejected(self):
        case = _case()
        del case["entry"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_chamber_entry(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_chamber_entry(["lot"])

    def test_a_negative_chamber_pressure_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_chamber_entry(
                _case(entry=_entry(chamber_pressure_kpa=-101.3))
            )

    def test_the_verdict_is_always_one_of_the_declared_verdicts(self):
        result = assess_blocking_diode_chamber_entry(_case())
        self.assertIn(result["verdict"], ENTRY_VERDICTS)



class TestUnexercisedGuards(unittest.TestCase):
    """Two validation branches that no test had ever entered.

    Found with stdlib trace over this leaf's own suite: 139 statements, 10
    never executed, six of them docstrings. A guard that has never been
    seen to fire is the same problem as a gate that has never returned red
    -- it is assumed to work.
    """

    def test_non_integer_entered_count_is_refused(self):
        for bad in (2.0, "2", None, True):
            with self.assertRaises(ValueError):
                lot_entry_completeness(bad, 10)

    def test_batch_entry_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            batch_residence_schedule([("dwell_h", 4.0)], 1.0)


if __name__ == "__main__":
    unittest.main()
