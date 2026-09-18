#!/usr/bin/env python3
"""Contract test for the load converter start-up current check (offline)."""

import copy
import unittest

from e2020_load_converter_startup_current_logic import (
    DEFAULT_CONVERTER_SET,
    DEFAULT_STARTUP_POLICY,
    FINDING_AGGREGATE,
    FINDING_HEADROOM,
    FINDING_SETTLED,
    FINDING_SINGLE,
    FINDING_UNSTAGGERABLE,
    VERDICT_EXCEEDS,
    VERDICT_WITHIN,
    assess_converter_startup,
    class_startup_allowance_a,
    converter_ramp_current_a,
    converter_windows,
    minimum_achievable_peak,
    peak_startup_current_a,
    settled_current_a,
    staggered_release_peak_a,
    startup_current_at_s,
    startup_current_profile,
    validate_converter,
    validate_converter_set,
    validate_startup_policy,
)

BUS_V = 28.0


def _converter(name="core-3v3"):
    for row in DEFAULT_CONVERTER_SET:
        if row["name"] == name:
            return copy.deepcopy(row)
    raise AssertionError("no such converter: %s" % name)


def _set(**overrides):
    rows = [copy.deepcopy(r) for r in DEFAULT_CONVERTER_SET]
    for row in rows:
        row.update(overrides)
    return rows


def _simultaneous():
    return _set(start_delay_s=0.0)


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_startup_policy(DEFAULT_STARTUP_POLICY), DEFAULT_STARTUP_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_startup_policy("default")

    def test_margin_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_startup_policy(
                dict(DEFAULT_STARTUP_POLICY, startup_current_margin=0.9)
            )

    def test_ramp_load_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_startup_policy(
                dict(DEFAULT_STARTUP_POLICY, ramp_load_fraction=1.4)
            )

    def test_headroom_floor_at_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_startup_policy(
                dict(DEFAULT_STARTUP_POLICY, headroom_advisory_floor=1.0)
            )


class ConverterValidationTests(unittest.TestCase):
    def test_default_set_validates(self):
        rows = validate_converter_set(DEFAULT_CONVERTER_SET)
        self.assertEqual(len(rows), len(DEFAULT_CONVERTER_SET))

    def test_missing_figure_rejected(self):
        row = _converter()
        del row["soft_start_ramp_s"]
        with self.assertRaises(ValueError):
            validate_converter(row)

    def test_zero_soft_start_ramp_rejected(self):
        row = _converter()
        row["soft_start_ramp_s"] = 0.0
        with self.assertRaises(ValueError):
            validate_converter(row)

    def test_negative_start_delay_rejected(self):
        row = _converter()
        row["start_delay_s"] = -1.0e-3
        with self.assertRaises(ValueError):
            validate_converter(row)

    def test_zero_start_delay_accepted(self):
        row = _converter()
        row["start_delay_s"] = 0.0
        self.assertAlmostEqual(validate_converter(row)["start_delay_s"], 0.0, places=12)

    def test_boolean_capacitance_rejected(self):
        row = _converter()
        row["input_capacitance_f"] = True
        with self.assertRaises(ValueError):
            validate_converter(row)

    def test_blank_converter_name_rejected(self):
        row = _converter()
        row["name"] = "  "
        with self.assertRaises(ValueError):
            validate_converter(row)

    def test_repeated_converter_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_converter_set([_converter(), _converter()])

    def test_empty_converter_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_converter_set([])

    def test_mapping_instead_of_a_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_converter_set(_converter())


class RampCurrentTests(unittest.TestCase):
    def test_ramp_current_is_charging_plus_loaded_draw(self):
        row = _converter()
        expected = (
            row["input_capacitance_f"] * BUS_V / row["soft_start_ramp_s"]
            + row["steady_input_current_a"]
        )
        self.assertAlmostEqual(
            converter_ramp_current_a(row, BUS_V), expected, places=12
        )

    def test_longer_ramp_draws_less(self):
        row = _converter()
        slow = copy.deepcopy(row)
        slow["soft_start_ramp_s"] = row["soft_start_ramp_s"] * 4.0
        self.assertGreater(
            converter_ramp_current_a(row, BUS_V),
            converter_ramp_current_a(slow, BUS_V),
        )

    def test_ramp_current_rises_with_bus_voltage(self):
        row = _converter()
        self.assertGreater(
            converter_ramp_current_a(row, 50.0), converter_ramp_current_a(row, 28.0)
        )

    def test_unloaded_ramp_fraction_drops_the_settled_share(self):
        row = _converter()
        unloaded = converter_ramp_current_a(
            row, BUS_V, dict(DEFAULT_STARTUP_POLICY, ramp_load_fraction=0.0)
        )
        expected = row["input_capacitance_f"] * BUS_V / row["soft_start_ramp_s"]
        self.assertAlmostEqual(unloaded, expected, places=12)

    def test_zero_bus_voltage_rejected(self):
        with self.assertRaises(ValueError):
            converter_ramp_current_a(_converter(), 0.0)


class ProfileTests(unittest.TestCase):
    def test_profile_has_a_point_per_release_and_settling(self):
        profile = startup_current_profile(DEFAULT_CONVERTER_SET, BUS_V)
        self.assertEqual(len(profile), 2 * len(DEFAULT_CONVERTER_SET))

    def test_profile_times_are_ascending(self):
        profile = startup_current_profile(DEFAULT_CONVERTER_SET, BUS_V)
        times = [p["time_s"] for p in profile]
        self.assertEqual(times, sorted(times))

    def test_last_profile_point_is_the_settled_draw(self):
        profile = startup_current_profile(DEFAULT_CONVERTER_SET, BUS_V)
        self.assertAlmostEqual(
            profile[-1]["current_a"], settled_current_a(DEFAULT_CONVERTER_SET), places=12
        )

    def test_current_before_the_first_release_is_zero(self):
        rows = _set()
        for row in rows:
            row["start_delay_s"] += 1.0e-3
        windows = converter_windows(rows, BUS_V)
        current, active = startup_current_at_s(windows, 0.0)
        self.assertAlmostEqual(current, 0.0, places=12)
        self.assertEqual(active, ())

    def test_instant_on_a_release_counts_the_converter_as_ramping(self):
        windows = converter_windows(DEFAULT_CONVERTER_SET, BUS_V)
        _, active = startup_current_at_s(windows, 0.0)
        self.assertEqual(active, (("core-3v3", "ramping"),))

    def test_instant_on_a_settling_counts_the_converter_as_settled(self):
        windows = converter_windows(DEFAULT_CONVERTER_SET, BUS_V)
        row = _converter()
        _, active = startup_current_at_s(windows, row["soft_start_ramp_s"])
        self.assertIn(("core-3v3", "settled"), active)

    def test_negative_instant_rejected(self):
        windows = converter_windows(DEFAULT_CONVERTER_SET, BUS_V)
        with self.assertRaises(ValueError):
            startup_current_at_s(windows, -1.0e-6)

    def test_simultaneous_release_peaks_higher_than_the_staggered_one(self):
        staggered, _ = peak_startup_current_a(DEFAULT_CONVERTER_SET, BUS_V)
        together, _ = peak_startup_current_a(_simultaneous(), BUS_V)
        self.assertGreater(together, staggered)

    def test_simultaneous_peak_is_the_sum_of_the_ramp_currents(self):
        rows = _simultaneous()
        expected = sum(converter_ramp_current_a(r, BUS_V) for r in rows)
        peak, when = peak_startup_current_a(rows, BUS_V)
        self.assertAlmostEqual(peak, expected, places=12)
        self.assertAlmostEqual(when, 0.0, places=12)


class StaggerTests(unittest.TestCase):
    def test_release_order_must_name_every_converter(self):
        with self.assertRaises(ValueError):
            staggered_release_peak_a(DEFAULT_CONVERTER_SET, BUS_V, ["core-3v3"])

    def test_release_order_rejects_an_unknown_name(self):
        with self.assertRaises(ValueError):
            staggered_release_peak_a(
                DEFAULT_CONVERTER_SET, BUS_V, ["core-3v3", "payload-5v", "ghost"]
            )

    def test_release_order_rejects_a_bare_string(self):
        with self.assertRaises(ValueError):
            staggered_release_peak_a(DEFAULT_CONVERTER_SET, BUS_V, "core-3v3")

    def test_best_order_is_no_worse_than_any_order(self):
        best = minimum_achievable_peak(DEFAULT_CONVERTER_SET, BUS_V)
        arbitrary = staggered_release_peak_a(
            DEFAULT_CONVERTER_SET, BUS_V, ["rf-12v", "payload-5v", "core-3v3"]
        )
        self.assertTrue(best["peak_a"] <= arbitrary)

    def test_best_order_is_searched_exactly_for_a_small_set(self):
        best = minimum_achievable_peak(DEFAULT_CONVERTER_SET, BUS_V)
        self.assertTrue(best["exact"])
        self.assertEqual(len(best["order"]), len(DEFAULT_CONVERTER_SET))

    def test_already_staggered_set_reaches_its_own_floor(self):
        best = minimum_achievable_peak(DEFAULT_CONVERTER_SET, BUS_V)
        peak, _ = peak_startup_current_a(DEFAULT_CONVERTER_SET, BUS_V)
        self.assertAlmostEqual(best["peak_a"], peak, places=9)


class AssessmentTests(unittest.TestCase):
    def test_generous_class_passes_with_no_findings(self):
        result = assess_converter_startup(DEFAULT_CONVERTER_SET, BUS_V, 4.0)
        self.assertEqual(result["verdict"], VERDICT_WITHIN)
        self.assertEqual(result["findings"], [])

    def test_allowance_takes_the_margin_out_of_the_class_current(self):
        self.assertAlmostEqual(class_startup_allowance_a(2.4), 2.0, places=9)

    def test_peak_exactly_on_the_allowance_is_accepted(self):
        peak, _ = peak_startup_current_a(DEFAULT_CONVERTER_SET, BUS_V)
        margin = float(DEFAULT_STARTUP_POLICY["startup_current_margin"])
        result = assess_converter_startup(DEFAULT_CONVERTER_SET, BUS_V, peak * margin)
        self.assertAlmostEqual(result["allowance_a"], peak, places=9)
        self.assertEqual(result["verdict"], VERDICT_WITHIN)

    def test_simultaneous_release_on_a_tight_class_is_a_finding(self):
        result = assess_converter_startup(_simultaneous(), BUS_V, 1.6)
        self.assertEqual(result["verdict"], VERDICT_EXCEEDS)
        self.assertTrue(any(FINDING_AGGREGATE in f for f in result["findings"]))

    def test_restagger_is_offered_when_an_order_would_fit(self):
        result = assess_converter_startup(_simultaneous(), BUS_V, 1.6)
        self.assertTrue(result["restagger_would_help"])
        self.assertFalse(
            any(FINDING_UNSTAGGERABLE in f for f in result["findings"])
        )

    def test_a_class_below_the_settled_draw_reports_the_settled_finding(self):
        result = assess_converter_startup(DEFAULT_CONVERTER_SET, BUS_V, 1.0)
        self.assertTrue(any(FINDING_SETTLED in f for f in result["findings"]))

    def test_a_class_no_order_can_meet_says_so(self):
        result = assess_converter_startup(DEFAULT_CONVERTER_SET, BUS_V, 1.0)
        self.assertTrue(any(FINDING_UNSTAGGERABLE in f for f in result["findings"]))
        self.assertFalse(result["restagger_would_help"])

    def test_one_oversized_converter_is_named_on_its_own(self):
        rows = _set()
        rows[0]["input_capacitance_f"] = 4.7e-3
        result = assess_converter_startup(rows, BUS_V, 4.0)
        self.assertTrue(any(FINDING_SINGLE in f for f in result["findings"]))
        self.assertEqual(result["worst_single_converter"], rows[0]["name"])

    def test_a_barely_passing_unit_raises_an_advisory_not_a_finding(self):
        result = assess_converter_startup(DEFAULT_CONVERTER_SET, BUS_V, 1.35)
        self.assertEqual(result["verdict"], VERDICT_WITHIN)
        self.assertEqual(result["findings"], [])
        self.assertTrue(any(FINDING_HEADROOM in a for a in result["advisories"]))

    def test_headroom_falls_as_the_class_current_falls(self):
        wide = assess_converter_startup(DEFAULT_CONVERTER_SET, BUS_V, 4.0)
        tight = assess_converter_startup(DEFAULT_CONVERTER_SET, BUS_V, 2.0)
        self.assertGreater(wide["headroom"], tight["headroom"])

    def test_assessment_rejects_a_broken_converter_set(self):
        rows = _set()
        rows[1]["steady_input_current_a"] = 0.0
        with self.assertRaises(ValueError):
            assess_converter_startup(rows, BUS_V, 4.0)

    def test_assessment_rejects_a_non_positive_class_current(self):
        with self.assertRaises(ValueError):
            assess_converter_startup(DEFAULT_CONVERTER_SET, BUS_V, 0.0)

    def test_assessment_carries_the_profile_it_read(self):
        result = assess_converter_startup(DEFAULT_CONVERTER_SET, BUS_V, 4.0)
        self.assertEqual(
            len(result["profile"]), 2 * len(DEFAULT_CONVERTER_SET)
        )


if __name__ == "__main__":
    unittest.main()
