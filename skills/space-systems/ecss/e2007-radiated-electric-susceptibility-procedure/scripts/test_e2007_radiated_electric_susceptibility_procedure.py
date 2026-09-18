#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radiated-electric-susceptibility-procedure.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radiated_electric_susceptibility_procedure.py
"""

import math
import unittest

from e2007_radiated_electric_susceptibility_procedure_logic import (
    CATEGORY_ON_LADDER,
    CATEGORY_SHORT_DWELL,
    DEFAULT_EXPOSURE_LIMIT_W_PER_M2,
    MINIMUM_STEP_DWELL_S,
    REQUIRED_SAFETY_PROVISIONS,
    VERDICT_RUN_REJECTED,
    VERDICT_RUN_STANDS,
    assess_exposure_run,
    dwell_floor,
    hazard_clearance_distance,
    linear_gain,
    normalize_steps,
    power_density,
    step_coverage,
    step_ladder,
    validate_safety_provisions,
    validate_span,
)

START_HZ = 100.0
STOP_HZ = 200.0
MAX_STEP = 0.5


def good_provisions(**over):
    record = dict((name, True) for name in REQUIRED_SAFETY_PROVISIONS)
    record.update(over)
    return record


def ladder_steps(dwell=2.0):
    return [
        {"frequency_hz": f, "dwell_s": dwell}
        for f in step_ladder(START_HZ, STOP_HZ, MAX_STEP)
    ]


def run(**over):
    kwargs = {
        "provisions": good_provisions(),
        "steps": ladder_steps(),
        "start_hz": START_HZ,
        "stop_hz": STOP_HZ,
        "max_fractional_step": MAX_STEP,
        "unit_response_time_s": 1.5,
        "forward_power_w": 100.0,
        "gain_dbi": 0.0,
        "occupied_distance_m": 5.0,
    }
    kwargs.update(over)
    return assess_exposure_run(**kwargs)


class TestLinearGain(unittest.TestCase):
    def test_zero_decibels_is_unity(self):
        self.assertAlmostEqual(linear_gain(0.0), 1.0, places=9)

    def test_ten_decibels_is_a_factor_of_ten(self):
        self.assertAlmostEqual(linear_gain(10.0), 10.0, places=9)

    def test_negative_gain_is_a_loss(self):
        self.assertAlmostEqual(linear_gain(-10.0), 0.1, places=9)

    def test_non_finite_gain_rejected(self):
        with self.assertRaises(ValueError):
            linear_gain(float("inf"))


class TestPowerDensity(unittest.TestCase):
    def test_isotropic_density_is_the_sphere_spread(self):
        self.assertAlmostEqual(
            power_density(100.0, 0.0, 1.0), 100.0 / (4.0 * math.pi), places=9
        )

    def test_density_falls_with_the_square_of_distance(self):
        near = power_density(100.0, 0.0, 1.0)
        far = power_density(100.0, 0.0, 2.0)
        self.assertAlmostEqual(far * 4.0, near, places=9)

    def test_gain_multiplies_the_density(self):
        plain = power_density(100.0, 0.0, 2.0)
        gained = power_density(100.0, 10.0, 2.0)
        self.assertAlmostEqual(gained, plain * 10.0, places=9)

    def test_zero_forward_power_gives_no_density(self):
        self.assertAlmostEqual(power_density(0.0, 6.0, 2.0), 0.0, places=9)

    def test_negative_forward_power_rejected(self):
        with self.assertRaises(ValueError):
            power_density(-1.0, 0.0, 1.0)

    def test_zero_distance_rejected(self):
        with self.assertRaises(ValueError):
            power_density(100.0, 0.0, 0.0)


class TestHazardClearance(unittest.TestCase):
    def test_clearance_is_where_the_density_meets_the_limit(self):
        clearance = hazard_clearance_distance(100.0, 0.0, 10.0)
        self.assertAlmostEqual(power_density(100.0, 0.0, clearance), 10.0, places=9)

    def test_clearance_grows_with_the_square_root_of_power(self):
        low = hazard_clearance_distance(100.0, 0.0, 10.0)
        high = hazard_clearance_distance(400.0, 0.0, 10.0)
        self.assertAlmostEqual(high, 2.0 * low, places=9)

    def test_a_tighter_limit_pushes_the_clearance_out(self):
        loose = hazard_clearance_distance(100.0, 0.0, 10.0)
        tight = hazard_clearance_distance(100.0, 0.0, 2.5)
        self.assertAlmostEqual(tight, 2.0 * loose, places=9)

    def test_default_limit_is_used_when_none_is_given(self):
        self.assertAlmostEqual(
            hazard_clearance_distance(100.0, 0.0),
            hazard_clearance_distance(100.0, 0.0, DEFAULT_EXPOSURE_LIMIT_W_PER_M2),
            places=9,
        )

    def test_non_positive_limit_rejected(self):
        with self.assertRaises(ValueError):
            hazard_clearance_distance(100.0, 0.0, 0.0)

    def test_negative_power_rejected(self):
        with self.assertRaises(ValueError):
            hazard_clearance_distance(-100.0, 0.0, 10.0)


class TestSafetyProvisions(unittest.TestCase):
    def test_complete_provisions_normalize(self):
        self.assertEqual(
            validate_safety_provisions(good_provisions()), good_provisions()
        )

    def test_missing_provision_rejected(self):
        broken = good_provisions()
        del broken["chamber-door-interlock-armed"]
        with self.assertRaises(ValueError):
            validate_safety_provisions(broken)

    def test_non_boolean_provision_rejected(self):
        with self.assertRaises(ValueError):
            validate_safety_provisions(
                good_provisions(**{"hazard-warning-indicator-lit": "yes"})
            )

    def test_invented_provision_rejected(self):
        with self.assertRaises(ValueError):
            validate_safety_provisions(good_provisions(**{"door-propped-open": True}))

    def test_non_mapping_provisions_rejected(self):
        with self.assertRaises(ValueError):
            validate_safety_provisions(list(REQUIRED_SAFETY_PROVISIONS))


class TestSpan(unittest.TestCase):
    def test_valid_span_returns_its_edges(self):
        self.assertEqual(validate_span(100.0, 200.0), (100.0, 200.0))

    def test_non_positive_start_rejected(self):
        with self.assertRaises(ValueError):
            validate_span(0.0, 200.0)

    def test_stop_at_or_below_start_rejected(self):
        with self.assertRaises(ValueError):
            validate_span(200.0, 200.0)


class TestStepLadder(unittest.TestCase):
    def test_ladder_begins_at_the_declared_start(self):
        self.assertAlmostEqual(step_ladder(100.0, 200.0, 0.5)[0], 100.0, places=9)

    def test_ladder_ends_at_the_declared_stop(self):
        self.assertAlmostEqual(step_ladder(100.0, 200.0, 0.5)[-1], 200.0, places=9)

    def test_rungs_rise_by_the_declared_fraction(self):
        rungs = step_ladder(100.0, 400.0, 0.5)
        self.assertAlmostEqual(rungs[1] / rungs[0], 1.5, places=9)
        self.assertAlmostEqual(rungs[2] / rungs[1], 1.5, places=9)

    def test_no_rung_exceeds_the_allowed_ratio(self):
        rungs = step_ladder(1.0e6, 1.0e9, 0.02)
        for lower, upper in zip(rungs, rungs[1:]):
            # The slack is a millionth, far outside any libm rounding spread,
            # so the comparison never sits on its own bound.
            self.assertLessEqual(upper / lower, 1.02 * 1.000001)

    def test_a_span_landing_exactly_on_a_rung_is_not_duplicated(self):
        rungs = step_ladder(100.0, 225.0, 0.5)
        self.assertEqual(len(rungs), 3)
        self.assertAlmostEqual(rungs[-1], 225.0, places=9)

    def test_a_narrow_span_needs_only_its_two_edges(self):
        self.assertEqual(len(step_ladder(100.0, 110.0, 0.5)), 2)

    def test_a_finer_step_builds_a_longer_ladder(self):
        self.assertGreater(
            len(step_ladder(100.0, 1000.0, 0.02)), len(step_ladder(100.0, 1000.0, 0.5))
        )

    def test_step_fraction_at_or_above_one_rejected(self):
        with self.assertRaises(ValueError):
            step_ladder(100.0, 200.0, 1.0)

    def test_non_positive_step_fraction_rejected(self):
        with self.assertRaises(ValueError):
            step_ladder(100.0, 200.0, 0.0)


class TestStepRecords(unittest.TestCase):
    def test_records_come_back_sorted_by_frequency(self):
        normalized = normalize_steps(
            [
                {"frequency_hz": 200.0, "dwell_s": 2.0},
                {"frequency_hz": 100.0, "dwell_s": 2.0},
            ]
        )
        self.assertAlmostEqual(normalized[0]["frequency_hz"], 100.0, places=9)

    def test_empty_step_list_rejected(self):
        with self.assertRaises(ValueError):
            normalize_steps([])

    def test_duplicate_frequency_rejected(self):
        with self.assertRaises(ValueError):
            normalize_steps(
                [
                    {"frequency_hz": 100.0, "dwell_s": 2.0},
                    {"frequency_hz": 100.0, "dwell_s": 3.0},
                ]
            )

    def test_non_positive_dwell_rejected(self):
        with self.assertRaises(ValueError):
            normalize_steps([{"frequency_hz": 100.0, "dwell_s": 0.0}])

    def test_step_missing_a_field_rejected(self):
        with self.assertRaises(ValueError):
            normalize_steps([{"frequency_hz": 100.0}])

    def test_non_mapping_step_rejected(self):
        with self.assertRaises(ValueError):
            normalize_steps([100.0])


class TestDwellFloor(unittest.TestCase):
    def test_a_slow_unit_sets_the_floor(self):
        self.assertAlmostEqual(dwell_floor(4.0), 4.0, places=9)

    def test_a_fast_unit_falls_back_to_the_minimum(self):
        self.assertAlmostEqual(dwell_floor(0.2), MINIMUM_STEP_DWELL_S, places=9)

    def test_a_named_minimum_overrides_the_default(self):
        self.assertAlmostEqual(dwell_floor(0.2, 3.0), 3.0, places=9)

    def test_non_positive_response_time_rejected(self):
        with self.assertRaises(ValueError):
            dwell_floor(0.0)


class TestStepCoverage(unittest.TestCase):
    def test_the_ladder_itself_is_continuous(self):
        rungs = step_ladder(START_HZ, STOP_HZ, MAX_STEP)
        coverage = step_coverage(rungs, START_HZ, STOP_HZ, MAX_STEP)
        self.assertTrue(coverage["continuous"])
        self.assertEqual(coverage["oversized_jumps"], ())

    def test_an_oversized_jump_is_reported_with_its_ratio(self):
        coverage = step_coverage([100.0, 200.0], START_HZ, STOP_HZ, MAX_STEP)
        self.assertFalse(coverage["continuous"])
        self.assertEqual(len(coverage["oversized_jumps"]), 1)
        self.assertAlmostEqual(coverage["oversized_jumps"][0]["ratio"], 2.0, places=9)

    def test_a_jump_exactly_on_the_allowed_ratio_is_not_a_finding(self):
        coverage = step_coverage([100.0, 150.0], 100.0, 150.0, 0.5)
        self.assertEqual(coverage["oversized_jumps"], ())

    def test_a_walk_starting_above_the_span_is_reported(self):
        coverage = step_coverage([300.0, 400.0], 100.0, 400.0, 0.5)
        self.assertTrue(
            any("starts at" in finding for finding in coverage["edge_findings"])
        )

    def test_a_walk_stopping_below_the_span_is_reported(self):
        coverage = step_coverage([100.0, 150.0], 100.0, 400.0, 0.5)
        self.assertTrue(
            any("stops at" in finding for finding in coverage["edge_findings"])
        )

    def test_empty_frequency_list_rejected(self):
        with self.assertRaises(ValueError):
            step_coverage([], START_HZ, STOP_HZ, MAX_STEP)

    def test_step_fraction_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            step_coverage([100.0, 150.0], START_HZ, STOP_HZ, 1.5)


class TestExposureRun(unittest.TestCase):
    def test_a_clean_run_stands(self):
        result = run()
        self.assertEqual(result["verdict"], VERDICT_RUN_STANDS)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["short_dwell_steps"], 0)

    def test_every_step_is_graded_and_reported(self):
        result = run()
        self.assertEqual(result["recorded_steps"], len(result["steps"]))
        for entry in result["steps"]:
            self.assertEqual(entry["category"], CATEGORY_ON_LADDER)

    def test_an_absent_safety_provision_stops_the_run(self):
        result = run(
            provisions=good_provisions(**{"personnel-clear-of-the-field-volume": False})
        )
        self.assertEqual(result["verdict"], VERDICT_RUN_REJECTED)
        self.assertTrue(
            any("personnel-clear-of-the-field-volume" in f for f in result["findings"])
        )

    def test_an_occupied_position_inside_the_clearance_stops_the_run(self):
        result = run(occupied_distance_m=0.1)
        self.assertEqual(result["verdict"], VERDICT_RUN_REJECTED)
        self.assertTrue(any("hazard clearance" in f for f in result["findings"]))

    def test_a_position_exactly_on_the_clearance_is_not_a_finding(self):
        clearance = hazard_clearance_distance(100.0, 0.0)
        result = run(occupied_distance_m=clearance)
        self.assertAlmostEqual(result["hazard_clearance_m"], clearance, places=9)
        self.assertEqual(result["verdict"], VERDICT_RUN_STANDS)

    def test_a_short_dwell_is_a_finding_against_the_response_time(self):
        result = run(steps=ladder_steps(dwell=0.5), unit_response_time_s=2.0)
        self.assertEqual(result["verdict"], VERDICT_RUN_REJECTED)
        self.assertEqual(result["short_dwell_steps"], len(result["steps"]))
        self.assertEqual(result["steps"][0]["category"], CATEGORY_SHORT_DWELL)

    def test_a_dwell_exactly_on_the_floor_is_accepted(self):
        result = run(steps=ladder_steps(dwell=2.0), unit_response_time_s=2.0)
        self.assertAlmostEqual(result["dwell_floor_s"], 2.0, places=9)
        self.assertEqual(result["verdict"], VERDICT_RUN_STANDS)
        self.assertAlmostEqual(result["steps"][0]["dwell_headroom_s"], 0.0, places=9)

    def test_a_skipped_stretch_stops_the_run(self):
        result = run(
            steps=[
                {"frequency_hz": START_HZ, "dwell_s": 2.0},
                {"frequency_hz": STOP_HZ, "dwell_s": 2.0},
            ]
        )
        self.assertEqual(result["verdict"], VERDICT_RUN_REJECTED)
        self.assertTrue(any("stepped from" in f for f in result["findings"]))

    def test_a_walk_finer_than_the_ladder_is_a_limitation_not_a_finding(self):
        steps = [
            {"frequency_hz": f, "dwell_s": 2.0}
            for f in step_ladder(START_HZ, STOP_HZ, 0.1)
        ]
        result = run(steps=steps)
        self.assertEqual(result["verdict"], VERDICT_RUN_STANDS)
        self.assertEqual(len(result["limitations"]), 1)

    def test_total_dwell_is_the_chamber_time_the_walk_occupies(self):
        result = run(steps=ladder_steps(dwell=3.0))
        self.assertAlmostEqual(
            result["total_dwell_s"], 3.0 * result["recorded_steps"], places=9
        )

    def test_the_density_at_the_occupied_position_is_reported(self):
        result = run(occupied_distance_m=5.0)
        self.assertAlmostEqual(
            result["power_density_at_occupied_position_w_per_m2"],
            power_density(100.0, 0.0, 5.0),
            places=9,
        )

    def test_a_non_positive_occupied_distance_rejected(self):
        with self.assertRaises(ValueError):
            run(occupied_distance_m=0.0)

    def test_the_ladder_the_run_was_graded_against_is_returned(self):
        result = run()
        self.assertEqual(result["ladder_steps"], len(result["ladder"]))
        self.assertAlmostEqual(result["ladder"][0], START_HZ, places=9)


if __name__ == "__main__":
    unittest.main(verbosity=0)
