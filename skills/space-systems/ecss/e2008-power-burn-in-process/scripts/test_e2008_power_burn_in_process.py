"""Contract tests for the clause 12.6.7.2.2 power burn-in process logic."""

import unittest

from e2008_power_burn_in_process_logic import (
    DEFAULT_POWER_BURN_IN_POLICY,
    POWER_BURN_IN_COMPLETE,
    POWER_BURN_IN_CURRENT_OUT_OF_BAND,
    POWER_BURN_IN_DURATION_SHORT,
    POWER_BURN_IN_JUNCTION_OVER_LIMIT,
    POWER_BURN_IN_MONITORING_BLIND,
    POWER_BURN_IN_NOT_PERFORMED,
    SEGMENT_INTERRUPTION,
    SEGMENT_OVERDRIVE,
    SEGMENT_SOAK,
    assess_power_burn_in_process,
    categorize_segment,
    current_band,
    defect_inventory,
    dissipated_power_w,
    grouped_segments,
    interruption_hours,
    junction_temperature_c,
    kelvin,
    overdrive_hours,
    qualifying_soak_hours,
    total_soak_hours,
    unwatched_defects,
    validate_power_burn_in_policy,
    watched_parameters,
)

DEFECTS = [
    "die-attach-void",
    "passivation-flaw",
    "wire-bond-weakness",
]

PARAMETERS = [
    "power-burn-in-thermal-resistance",
    "power-burn-in-reverse-leakage",
    "power-burn-in-forward-voltage",
]

SPECIFIED_A = 2.0
TOLERANCE = 0.05


def _policy(**overrides):
    policy = dict(DEFAULT_POWER_BURN_IN_POLICY)
    policy.update(overrides)
    return policy


def _soak(**overrides):
    soak = {
        "specified_forward_current_a": SPECIFIED_A,
        "forward_voltage_v": 0.9,
        "case_temperature_c": 125.0,
        "thermal_resistance_c_per_w": 12.0,
        "segments": [{"duration_h": 100.0, "forward_current_a": 2.0}],
    }
    soak.update(overrides)
    return soak


def _case(**overrides):
    case = {
        "declared_defects": list(DEFECTS),
        "monitored_parameters": list(PARAMETERS),
        "soak": _soak(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_power_burn_in_policy(DEFAULT_POWER_BURN_IN_POLICY),
            DEFAULT_POWER_BURN_IN_POLICY,
        )

    def test_the_default_floor_is_the_ninety_six_hour_minimum(self):
        self.assertAlmostEqual(
            DEFAULT_POWER_BURN_IN_POLICY["min_soak_hours"], 96.0, places=9
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_burn_in_policy("ninety-six hours")

    def test_a_zero_soak_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_burn_in_policy(_policy(min_soak_hours=0.0))

    def test_a_tolerance_band_wider_than_the_setpoint_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_burn_in_policy(_policy(current_tolerance_fraction=1.0))

    def test_a_negative_interruption_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_burn_in_policy(_policy(max_interruption_hours=-1.0))

    def test_a_junction_ceiling_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_burn_in_policy(_policy(max_junction_temperature_c=-300.0))


class BandTests(unittest.TestCase):
    def test_the_band_straddles_the_specified_current(self):
        lower, upper = current_band(2.0, 0.05)
        self.assertAlmostEqual(lower, 1.9, places=9)
        self.assertAlmostEqual(upper, 2.1, places=9)

    def test_a_zero_specified_current_rejected(self):
        with self.assertRaises(ValueError):
            current_band(0.0, 0.05)

    def test_current_on_the_setpoint_is_soak_time(self):
        self.assertEqual(categorize_segment(2.0, SPECIFIED_A, TOLERANCE), SEGMENT_SOAK)

    def test_current_exactly_on_the_lower_band_edge_is_soak_time(self):
        lower, _upper = current_band(SPECIFIED_A, TOLERANCE)
        self.assertEqual(
            categorize_segment(lower, SPECIFIED_A, TOLERANCE), SEGMENT_SOAK
        )

    def test_current_exactly_on_the_upper_band_edge_is_soak_time(self):
        _lower, upper = current_band(SPECIFIED_A, TOLERANCE)
        self.assertEqual(
            categorize_segment(upper, SPECIFIED_A, TOLERANCE), SEGMENT_SOAK
        )

    def test_current_below_the_band_is_an_interruption(self):
        self.assertEqual(
            categorize_segment(0.0, SPECIFIED_A, TOLERANCE), SEGMENT_INTERRUPTION
        )

    def test_current_above_the_band_is_overdrive(self):
        self.assertEqual(
            categorize_segment(2.6, SPECIFIED_A, TOLERANCE), SEGMENT_OVERDRIVE
        )

    def test_a_negative_applied_current_rejected(self):
        with self.assertRaises(ValueError):
            categorize_segment(-0.1, SPECIFIED_A, TOLERANCE)


class SegmentTests(unittest.TestCase):
    def test_every_segment_is_grouped_in_log_order(self):
        segments = [
            {"duration_h": 10.0, "forward_current_a": 2.0},
            {"duration_h": 2.0, "forward_current_a": 0.0},
            {"duration_h": 3.0, "forward_current_a": 2.6},
        ]
        self.assertEqual(
            grouped_segments(segments, SPECIFIED_A, TOLERANCE),
            (SEGMENT_SOAK, SEGMENT_INTERRUPTION, SEGMENT_OVERDRIVE),
        )

    def test_only_in_band_time_counts_towards_the_total(self):
        segments = [
            {"duration_h": 40.0, "forward_current_a": 2.0},
            {"duration_h": 5.0, "forward_current_a": 0.0},
            {"duration_h": 40.0, "forward_current_a": 1.95},
        ]
        self.assertAlmostEqual(
            total_soak_hours(segments, SPECIFIED_A, TOLERANCE), 80.0, places=9
        )

    def test_overdrive_hours_are_counted_separately(self):
        segments = [
            {"duration_h": 40.0, "forward_current_a": 2.0},
            {"duration_h": 6.0, "forward_current_a": 3.0},
        ]
        self.assertAlmostEqual(
            overdrive_hours(segments, SPECIFIED_A, TOLERANCE), 6.0, places=9
        )

    def test_interruption_hours_are_counted_separately(self):
        segments = [
            {"duration_h": 40.0, "forward_current_a": 2.0},
            {"duration_h": 4.0, "forward_current_a": 0.2},
        ]
        self.assertAlmostEqual(
            interruption_hours(segments, SPECIFIED_A, TOLERANCE), 4.0, places=9
        )

    def test_an_empty_log_rejected(self):
        with self.assertRaises(ValueError):
            total_soak_hours([], SPECIFIED_A, TOLERANCE)

    def test_a_non_sequence_log_rejected(self):
        with self.assertRaises(ValueError):
            total_soak_hours("100 h", SPECIFIED_A, TOLERANCE)

    def test_a_zero_length_segment_rejected(self):
        with self.assertRaises(ValueError):
            total_soak_hours(
                [{"duration_h": 0.0, "forward_current_a": 2.0}],
                SPECIFIED_A,
                TOLERANCE,
            )

    def test_a_segment_that_is_not_a_mapping_rejected(self):
        with self.assertRaises(ValueError):
            total_soak_hours([96.0], SPECIFIED_A, TOLERANCE)


class QualifyingHoursTests(unittest.TestCase):
    def test_one_unbroken_soak_qualifies_whole(self):
        segments = [{"duration_h": 100.0, "forward_current_a": 2.0}]
        self.assertAlmostEqual(
            qualifying_soak_hours(segments, SPECIFIED_A, TOLERANCE, 1.0),
            100.0,
            places=9,
        )

    def test_a_short_interruption_does_not_break_the_run(self):
        segments = [
            {"duration_h": 60.0, "forward_current_a": 2.0},
            {"duration_h": 0.5, "forward_current_a": 0.0},
            {"duration_h": 60.0, "forward_current_a": 2.0},
        ]
        self.assertAlmostEqual(
            qualifying_soak_hours(segments, SPECIFIED_A, TOLERANCE, 1.0),
            120.0,
            places=9,
        )

    def test_an_interruption_exactly_on_the_allowance_does_not_break_the_run(self):
        segments = [
            {"duration_h": 60.0, "forward_current_a": 2.0},
            {"duration_h": 1.0, "forward_current_a": 0.0},
            {"duration_h": 60.0, "forward_current_a": 2.0},
        ]
        self.assertAlmostEqual(
            qualifying_soak_hours(segments, SPECIFIED_A, TOLERANCE, 1.0),
            120.0,
            places=9,
        )

    def test_a_long_interruption_restarts_the_clock(self):
        segments = [
            {"duration_h": 60.0, "forward_current_a": 2.0},
            {"duration_h": 2.0, "forward_current_a": 0.0},
            {"duration_h": 60.0, "forward_current_a": 2.0},
        ]
        self.assertAlmostEqual(
            qualifying_soak_hours(segments, SPECIFIED_A, TOLERANCE, 1.0),
            60.0,
            places=9,
        )

    def test_the_longest_run_is_the_one_reported(self):
        segments = [
            {"duration_h": 30.0, "forward_current_a": 2.0},
            {"duration_h": 5.0, "forward_current_a": 0.0},
            {"duration_h": 97.0, "forward_current_a": 2.0},
        ]
        self.assertAlmostEqual(
            qualifying_soak_hours(segments, SPECIFIED_A, TOLERANCE, 1.0),
            97.0,
            places=9,
        )

    def test_a_negative_allowance_rejected(self):
        segments = [{"duration_h": 100.0, "forward_current_a": 2.0}]
        with self.assertRaises(ValueError):
            qualifying_soak_hours(segments, SPECIFIED_A, TOLERANCE, -1.0)


class ThermalTests(unittest.TestCase):
    def test_power_is_the_forward_current_times_the_forward_drop(self):
        self.assertAlmostEqual(dissipated_power_w(2.0, 0.9), 1.8, places=9)

    def test_a_zero_forward_current_rejected(self):
        with self.assertRaises(ValueError):
            dissipated_power_w(0.0, 0.9)

    def test_a_boolean_forward_voltage_rejected(self):
        with self.assertRaises(ValueError):
            dissipated_power_w(2.0, True)

    def test_the_junction_sits_above_the_case_by_the_thermal_drop(self):
        self.assertAlmostEqual(
            junction_temperature_c(125.0, 1.8, 12.0), 146.6, places=9
        )

    def test_a_perfect_thermal_path_leaves_the_junction_at_the_case(self):
        self.assertAlmostEqual(
            junction_temperature_c(125.0, 1.8, 0.0), 125.0, places=9
        )

    def test_a_case_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(-300.0, 1.8, 12.0)

    def test_kelvin_conversion_offsets_by_absolute_zero(self):
        self.assertAlmostEqual(kelvin(0.0), 273.15, places=9)


class InventoryTests(unittest.TestCase):
    def test_a_repeated_defect_is_grouped_once(self):
        self.assertEqual(
            defect_inventory(["die-attach-void", "die-attach-void"]),
            ("die-attach-void",),
        )

    def test_an_unknown_defect_rejected(self):
        with self.assertRaises(ValueError):
            defect_inventory(["coverglass-darkening"])

    def test_a_non_collection_defect_list_rejected(self):
        with self.assertRaises(ValueError):
            defect_inventory("die-attach-void")

    def test_two_defects_sharing_a_parameter_list_it_once(self):
        self.assertEqual(
            watched_parameters(["wire-bond-weakness", "metallisation-thinning"]),
            ("power-burn-in-forward-voltage",),
        )

    def test_every_declared_defect_reaches_a_parameter(self):
        self.assertEqual(len(watched_parameters(DEFECTS)), 3)

    def test_a_defect_with_no_parameter_watching_it_is_named(self):
        blind = unwatched_defects(DEFECTS, ["power-burn-in-thermal-resistance"])
        self.assertEqual(sorted(blind), ["passivation-flaw", "wire-bond-weakness"])

    def test_full_monitoring_leaves_no_defect_unwatched(self):
        self.assertEqual(unwatched_defects(DEFECTS, PARAMETERS), ())


class AssessmentTests(unittest.TestCase):
    def test_a_compliant_soak_is_complete(self):
        result = assess_power_burn_in_process(_case())
        self.assertEqual(result["verdict"], POWER_BURN_IN_COMPLETE)
        self.assertEqual(result["findings"], [])

    def test_a_soak_exactly_on_the_ninety_six_hour_floor_is_complete(self):
        result = assess_power_burn_in_process(
            _case(soak=_soak(segments=[{"duration_h": 96.0, "forward_current_a": 2.0}]))
        )
        self.assertEqual(result["verdict"], POWER_BURN_IN_COMPLETE)
        self.assertTrue(result["duration_met"])

    def test_the_junction_temperature_is_derived_not_taken_from_the_case(self):
        result = assess_power_burn_in_process(_case())
        self.assertAlmostEqual(result["junction_temperature_c"], 146.6, places=9)

    def test_an_unlogged_burn_in_is_its_own_verdict(self):
        case = _case()
        del case["soak"]
        result = assess_power_burn_in_process(case)
        self.assertEqual(result["verdict"], POWER_BURN_IN_NOT_PERFORMED)
        self.assertIsNone(result["junction_temperature_c"])

    def test_a_soak_short_of_the_floor_is_reported_short(self):
        result = assess_power_burn_in_process(
            _case(soak=_soak(segments=[{"duration_h": 72.0, "forward_current_a": 2.0}]))
        )
        self.assertEqual(result["verdict"], POWER_BURN_IN_DURATION_SHORT)
        self.assertFalse(result["duration_met"])

    def test_a_long_interruption_can_leave_a_long_log_short(self):
        result = assess_power_burn_in_process(
            _case(
                soak=_soak(
                    segments=[
                        {"duration_h": 60.0, "forward_current_a": 2.0},
                        {"duration_h": 4.0, "forward_current_a": 0.0},
                        {"duration_h": 60.0, "forward_current_a": 2.0},
                    ]
                )
            )
        )
        self.assertEqual(result["verdict"], POWER_BURN_IN_DURATION_SHORT)
        self.assertAlmostEqual(result["total_soak_hours"], 120.0, places=9)
        self.assertAlmostEqual(result["qualifying_soak_hours"], 60.0, places=9)

    def test_overdrive_time_puts_the_current_out_of_band(self):
        result = assess_power_burn_in_process(
            _case(
                soak=_soak(
                    segments=[
                        {"duration_h": 100.0, "forward_current_a": 2.0},
                        {"duration_h": 3.0, "forward_current_a": 3.0},
                    ]
                )
            )
        )
        self.assertEqual(result["verdict"], POWER_BURN_IN_CURRENT_OUT_OF_BAND)
        self.assertFalse(result["current_within_band"])

    def test_a_junction_beyond_the_ceiling_outranks_a_short_soak(self):
        result = assess_power_burn_in_process(
            _case(soak=_soak(case_temperature_c=170.0))
        )
        self.assertEqual(result["verdict"], POWER_BURN_IN_JUNCTION_OVER_LIMIT)
        self.assertFalse(result["junction_within_limit"])

    def test_an_unwatched_defect_makes_the_soak_blind(self):
        result = assess_power_burn_in_process(
            _case(monitored_parameters=["power-burn-in-thermal-resistance"])
        )
        self.assertEqual(result["verdict"], POWER_BURN_IN_MONITORING_BLIND)
        self.assertEqual(len(result["unwatched_defects"]), 2)

    def test_every_inadequacy_is_reported_not_only_the_first(self):
        result = assess_power_burn_in_process(
            _case(
                soak=_soak(
                    case_temperature_c=170.0,
                    segments=[
                        {"duration_h": 10.0, "forward_current_a": 2.0},
                        {"duration_h": 3.0, "forward_current_a": 3.0},
                    ],
                ),
                monitored_parameters=[],
            )
        )
        self.assertEqual(result["verdict"], POWER_BURN_IN_JUNCTION_OVER_LIMIT)
        self.assertGreaterEqual(len(result["findings"]), 4)

    def test_an_absent_defect_inventory_rejected(self):
        case = _case()
        del case["declared_defects"]
        with self.assertRaises(ValueError):
            assess_power_burn_in_process(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_power_burn_in_process(["soak"])

    def test_a_non_mapping_soak_rejected(self):
        with self.assertRaises(ValueError):
            assess_power_burn_in_process(_case(soak=[96.0]))

    def test_a_missing_specified_current_rejected(self):
        soak = _soak()
        del soak["specified_forward_current_a"]
        with self.assertRaises(ValueError):
            assess_power_burn_in_process(_case(soak=soak))


if __name__ == "__main__":
    unittest.main()
