#!/usr/bin/env python3
"""Gate 3 contract test for e2007-inrush-current-test-equipment.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_inrush_current_test_equipment.py
"""

import unittest

from e2007_inrush_current_test_equipment_logic import (
    DEFAULT_DROOP_FRACTION,
    DEFAULT_OVERSAMPLE_FACTOR,
    DEFAULT_PROBE_MARGIN,
    FITNESS_ADEQUATE,
    FITNESS_INADEQUATE,
    FITNESS_MARGINAL,
    ITEM_CURRENT_PROBE,
    ITEM_OSCILLOSCOPE,
    ITEM_RECORDING_MEDIUM,
    ITEM_SPIKE_GENERATOR,
    REQUIRED_ITEMS,
    RISE_TIME_BANDWIDTH_PRODUCT,
    VERDICT_FIT,
    VERDICT_UNFIT,
    assess_equipment,
    categorize_capability,
    categorize_ceiling,
    derive_requirements,
    generator_rise_time_ceiling_s,
    normalize_item,
    probe_low_corner_ceiling_hz,
    probe_rating_requirement_a,
    required_bandwidth_hz,
    required_record_points,
    required_sample_rate_hz,
)


def surge(**over):
    record = {
        "rise_time_s": 1.0e-6,
        "peak_current_a": 20.0,
        "pulse_duration_s": 1.0e-3,
        "capture_window_s": 1.0e-2,
    }
    record.update(over)
    return record


def inventory(**over):
    record = {
        ITEM_OSCILLOSCOPE: {"bandwidth_hz": 1.0e8, "sample_rate_hz": 1.0e9},
        ITEM_CURRENT_PROBE: {
            "peak_rating_a": 100.0,
            "bandwidth_hz": 5.0e7,
            "low_corner_hz": 1.0,
        },
        ITEM_SPIKE_GENERATOR: {"peak_output_a": 50.0, "rise_time_s": 1.0e-7},
        ITEM_RECORDING_MEDIUM: {"record_points": 1.0e6},
    }
    for key, value in over.items():
        record[key] = dict(record[key], **value)
    return record


class TestItemNormalization(unittest.TestCase):
    def test_every_required_item_normalizes(self):
        for item in REQUIRED_ITEMS:
            self.assertEqual(normalize_item(item.upper()), item)

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(normalize_item("  current-probe "), ITEM_CURRENT_PROBE)

    def test_unrecognized_item_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item("thermal-camera")

    def test_non_string_item_rejected(self):
        with self.assertRaises(ValueError):
            normalize_item(4)


class TestBandwidthRequirement(unittest.TestCase):
    def test_bandwidth_is_the_rise_time_product_over_the_rise_time(self):
        self.assertAlmostEqual(
            required_bandwidth_hz(1.0e-6) * 1.0e-6,
            RISE_TIME_BANDWIDTH_PRODUCT,
            places=9,
        )

    def test_halving_the_rise_time_doubles_the_bandwidth(self):
        slow = required_bandwidth_hz(2.0e-6)
        fast = required_bandwidth_hz(1.0e-6)
        self.assertAlmostEqual(fast, 2.0 * slow, places=9)

    def test_non_positive_rise_time_rejected(self):
        with self.assertRaises(ValueError):
            required_bandwidth_hz(0.0)

    def test_non_numeric_rise_time_rejected(self):
        with self.assertRaises(ValueError):
            required_bandwidth_hz("1 us")


class TestSampleRateAndDepth(unittest.TestCase):
    def test_sample_rate_oversamples_the_bandwidth(self):
        self.assertAlmostEqual(
            required_sample_rate_hz(1.0e6),
            1.0e6 * DEFAULT_OVERSAMPLE_FACTOR,
            places=9,
        )

    def test_oversample_below_two_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_rate_hz(1.0e6, 1.5)

    def test_record_depth_is_the_window_times_the_rate(self):
        self.assertEqual(required_record_points(1.0e-2, 1.75e6), 17500)

    def test_record_depth_rounds_a_partial_sample_up(self):
        self.assertEqual(required_record_points(1.5e-6, 1.0e6), 2)

    def test_non_positive_window_rejected(self):
        with self.assertRaises(ValueError):
            required_record_points(0.0, 1.0e6)


class TestProbeRequirements(unittest.TestCase):
    def test_rating_carries_the_declared_headroom(self):
        self.assertAlmostEqual(
            probe_rating_requirement_a(20.0, DEFAULT_PROBE_MARGIN), 30.0, places=9
        )

    def test_margin_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            probe_rating_requirement_a(20.0, 0.9)

    def test_low_corner_ceiling_falls_as_the_pulse_lengthens(self):
        short = probe_low_corner_ceiling_hz(1.0e-3)
        long_pulse = probe_low_corner_ceiling_hz(1.0e-2)
        self.assertAlmostEqual(long_pulse * 10.0, short, places=9)

    def test_tighter_droop_lowers_the_ceiling(self):
        loose = probe_low_corner_ceiling_hz(1.0e-3, 0.10)
        tight = probe_low_corner_ceiling_hz(1.0e-3, 0.05)
        self.assertAlmostEqual(loose, 2.0 * tight, places=9)

    def test_droop_fraction_outside_the_open_interval_rejected(self):
        with self.assertRaises(ValueError):
            probe_low_corner_ceiling_hz(1.0e-3, 1.0)

    def test_non_positive_pulse_duration_rejected(self):
        with self.assertRaises(ValueError):
            probe_low_corner_ceiling_hz(0.0)


class TestGeneratorRequirement(unittest.TestCase):
    def test_generator_edge_is_faster_than_the_chain(self):
        self.assertAlmostEqual(
            generator_rise_time_ceiling_s(1.0e-6), 5.0e-7, places=15
        )

    def test_factor_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            generator_rise_time_ceiling_s(1.0e-6, 0.0)


class TestCategorization(unittest.TestCase):
    def test_comfortable_capability_is_adequate(self):
        self.assertEqual(categorize_capability(100.0, 10.0), FITNESS_ADEQUATE)

    def test_capability_exactly_on_the_requirement_is_marginal(self):
        self.assertEqual(categorize_capability(10.0, 10.0), FITNESS_MARGINAL)

    def test_capability_below_the_requirement_is_inadequate(self):
        self.assertEqual(categorize_capability(9.0, 10.0), FITNESS_INADEQUATE)

    def test_ceiling_comfortably_under_is_adequate(self):
        self.assertEqual(categorize_ceiling(1.0, 10.0), FITNESS_ADEQUATE)

    def test_ceiling_exactly_on_the_limit_is_marginal(self):
        self.assertEqual(categorize_ceiling(10.0, 10.0), FITNESS_MARGINAL)

    def test_ceiling_above_the_limit_is_inadequate(self):
        self.assertEqual(categorize_ceiling(11.0, 10.0), FITNESS_INADEQUATE)

    def test_marginal_fraction_outside_range_rejected(self):
        with self.assertRaises(ValueError):
            categorize_capability(10.0, 10.0, 1.0)

    def test_non_positive_requirement_rejected(self):
        with self.assertRaises(ValueError):
            categorize_capability(10.0, 0.0)


class TestDeriveRequirements(unittest.TestCase):
    def test_requirements_follow_from_the_surge(self):
        needs = derive_requirements(surge())
        self.assertAlmostEqual(needs["bandwidth_hz"], 3.5e5, places=6)
        self.assertAlmostEqual(needs["sample_rate_hz"], 1.75e6, places=6)
        self.assertEqual(needs["record_points"], 17500)
        self.assertAlmostEqual(needs["probe_rating_a"], 30.0, places=9)

    def test_capture_window_defaults_to_ten_pulse_durations(self):
        record = surge()
        del record["capture_window_s"]
        needs = derive_requirements(record)
        self.assertAlmostEqual(needs["capture_window_s"], 1.0e-2, places=12)

    def test_pulse_shorter_than_the_rise_rejected(self):
        with self.assertRaises(ValueError):
            derive_requirements(surge(pulse_duration_s=1.0e-7))

    def test_window_shorter_than_the_pulse_rejected(self):
        with self.assertRaises(ValueError):
            derive_requirements(surge(capture_window_s=1.0e-5))

    def test_non_positive_peak_rejected(self):
        with self.assertRaises(ValueError):
            derive_requirements(surge(peak_current_a=0.0))

    def test_non_mapping_surge_rejected(self):
        with self.assertRaises(ValueError):
            derive_requirements(["1 us", "20 A"])

    def test_declared_droop_fraction_is_honoured(self):
        tight = derive_requirements(surge(droop_fraction=0.01))
        loose = derive_requirements(surge(droop_fraction=DEFAULT_DROOP_FRACTION))
        self.assertAlmostEqual(
            loose["probe_low_corner_ceiling_hz"],
            5.0 * tight["probe_low_corner_ceiling_hz"],
            places=9,
        )


class TestAssessEquipment(unittest.TestCase):
    def test_capable_bench_is_fit(self):
        report = assess_equipment(surge(), inventory())
        self.assertEqual(report["verdict"], VERDICT_FIT)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["missing_items"], [])

    def test_slow_oscilloscope_is_a_finding(self):
        report = assess_equipment(
            surge(), inventory(**{ITEM_OSCILLOSCOPE: {"bandwidth_hz": 1.0e4}})
        )
        self.assertEqual(report["verdict"], VERDICT_UNFIT)
        self.assertIsNotNone(report["governing_shortfall"])

    def test_undersampling_oscilloscope_is_a_finding(self):
        report = assess_equipment(
            surge(), inventory(**{ITEM_OSCILLOSCOPE: {"sample_rate_hz": 1.0e5}})
        )
        self.assertEqual(report["verdict"], VERDICT_UNFIT)

    def test_probe_rated_below_the_surge_is_a_finding(self):
        report = assess_equipment(
            surge(), inventory(**{ITEM_CURRENT_PROBE: {"peak_rating_a": 25.0}})
        )
        self.assertEqual(report["verdict"], VERDICT_UNFIT)

    def test_probe_low_corner_above_the_ceiling_is_a_finding(self):
        report = assess_equipment(
            surge(), inventory(**{ITEM_CURRENT_PROBE: {"low_corner_hz": 100.0}})
        )
        self.assertEqual(report["verdict"], VERDICT_UNFIT)

    def test_slow_spike_generator_is_a_finding(self):
        report = assess_equipment(
            surge(), inventory(**{ITEM_SPIKE_GENERATOR: {"rise_time_s": 1.0e-5}})
        )
        self.assertEqual(report["verdict"], VERDICT_UNFIT)

    def test_shallow_recording_medium_is_a_finding(self):
        report = assess_equipment(
            surge(), inventory(**{ITEM_RECORDING_MEDIUM: {"record_points": 100.0}})
        )
        self.assertEqual(report["verdict"], VERDICT_UNFIT)

    def test_absent_item_is_a_finding_and_is_named(self):
        bench = inventory()
        del bench[ITEM_SPIKE_GENERATOR]
        report = assess_equipment(surge(), bench)
        self.assertEqual(report["verdict"], VERDICT_UNFIT)
        self.assertEqual(report["missing_items"], [ITEM_SPIKE_GENERATOR])

    def test_barely_adequate_item_is_a_limitation_not_a_finding(self):
        needs = derive_requirements(surge())
        report = assess_equipment(
            surge(),
            inventory(**{ITEM_OSCILLOSCOPE: {"bandwidth_hz": needs["bandwidth_hz"]}}),
        )
        self.assertEqual(report["verdict"], VERDICT_FIT)
        self.assertTrue(report["limitations"])

    def test_governing_shortfall_names_the_worst_item(self):
        bench = inventory(
            **{
                ITEM_OSCILLOSCOPE: {"bandwidth_hz": 1.0e3},
                ITEM_CURRENT_PROBE: {"peak_rating_a": 29.0},
            }
        )
        report = assess_equipment(surge(), bench)
        self.assertEqual(report["governing_shortfall"]["item"], ITEM_OSCILLOSCOPE)

    def test_unknown_item_in_the_inventory_rejected(self):
        bench = inventory()
        bench["thermal-camera"] = {"bandwidth_hz": 1.0}
        with self.assertRaises(ValueError):
            assess_equipment(surge(), bench)

    def test_non_mapping_item_record_rejected(self):
        bench = inventory()
        bench[ITEM_RECORDING_MEDIUM] = "1 Mpts"
        with self.assertRaises(ValueError):
            assess_equipment(surge(), bench)

    def test_missing_quantity_on_a_declared_item_rejected(self):
        bench = inventory()
        bench[ITEM_CURRENT_PROBE] = {"peak_rating_a": 100.0, "bandwidth_hz": 5.0e7}
        with self.assertRaises(ValueError):
            assess_equipment(surge(), bench)

    def test_every_declared_item_produces_at_least_one_check(self):
        report = assess_equipment(surge(), inventory())
        covered = {check["item"] for check in report["checks"]}
        self.assertEqual(covered, set(REQUIRED_ITEMS))


if __name__ == "__main__":
    unittest.main()
