"""Contract tests for the clause 12.6.9 blocking diode temperature map.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused map policy, a
sweep that stops short of a service extreme, a sweep too coarse to resolve
a knee, a sweep whose parameters move the wrong way with temperature, a
self-heated junction that leaves the mapped range, and a junction that
settles above its rating.
"""

import unittest

from e2008_blocking_diode_temperature_behaviour_logic import (
    DEFAULT_MAP_POLICY,
    JUNCTION_RATING_EXCEEDED,
    MAP_COVERAGE_INSUFFICIENT,
    MAP_RESOLUTION_INSUFFICIENT,
    MAP_TRENDS_INCONSISTENT,
    PARAMETERS_MAPPED,
    SELF_HEATING_BEYOND_MAP,
    endpoint_gaps_c,
    forward_dissipation_w,
    forward_loss_fraction,
    forward_voltage_at_c,
    forward_voltage_trend_sound,
    junction_temperature_c,
    map_blocking_diode_temperature_behaviour,
    map_span_c,
    maximum_possible_junction_c,
    read_temperature_map,
    reverse_leakage_at_c,
    reverse_leakage_trend_sound,
    self_heated_operating_point,
    validate_map_point,
    validate_map_policy,
    validate_operating_range,
    widest_step_c,
)

COLD_END = -100.0
HOT_END = 85.0


def _policy(**overrides):
    policy = dict(DEFAULT_MAP_POLICY)
    policy.update(overrides)
    return policy


def _points():
    return [
        {"temperature_c": -100.0, "forward_voltage_v": 0.90, "reverse_leakage_ua": 0.001},
        {"temperature_c": -60.0, "forward_voltage_v": 0.82, "reverse_leakage_ua": 0.004},
        {"temperature_c": -20.0, "forward_voltage_v": 0.74, "reverse_leakage_ua": 0.016},
        {"temperature_c": 20.0, "forward_voltage_v": 0.66, "reverse_leakage_ua": 0.064},
        {"temperature_c": 60.0, "forward_voltage_v": 0.58, "reverse_leakage_ua": 0.256},
        {"temperature_c": 85.0, "forward_voltage_v": 0.53, "reverse_leakage_ua": 0.600},
    ]


def _case(**overrides):
    case = {
        "operating_range_c": {"min_c": COLD_END, "max_c": HOT_END},
        "points": _points(),
        "string_current_a": 2.0,
        "string_voltage_v": 100.0,
        "thermal_resistance_c_per_w": 4.0,
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_map_policy(DEFAULT_MAP_POLICY), DEFAULT_MAP_POLICY)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_map_policy("max_step_c")

    def test_single_point_map_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_map_policy(_policy(min_map_points=1))

    def test_negative_endpoint_gap_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_map_policy(_policy(max_endpoint_gap_c=-1.0))

    def test_whole_string_loss_fraction_rejected(self):
        with self.assertRaises(ValueError):
            validate_map_policy(_policy(max_forward_loss_fraction=1.0))


class MapReadingTests(unittest.TestCase):
    def test_map_is_returned_in_temperature_order(self):
        shuffled = list(reversed(_points()))
        mapped = read_temperature_map(shuffled)
        self.assertEqual([entry[0] for entry in mapped], sorted(entry[0] for entry in mapped))

    def test_repeated_temperature_rejected(self):
        points = _points()
        points[1]["temperature_c"] = -100.0
        with self.assertRaises(ValueError):
            read_temperature_map(points)

    def test_map_of_one_point_rejected(self):
        with self.assertRaises(ValueError):
            read_temperature_map(_points()[:1])

    def test_non_positive_forward_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_map_point(
                {"temperature_c": 20.0, "forward_voltage_v": 0.0, "reverse_leakage_ua": 0.1}
            )

    def test_inverted_operating_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_operating_range({"min_c": 85.0, "max_c": -100.0})


class SweepGeometryTests(unittest.TestCase):
    def setUp(self):
        self.mapped = read_temperature_map(_points())

    def test_span_covers_both_service_ends(self):
        self.assertAlmostEqual(map_span_c(self.mapped), 185.0, places=9)

    def test_endpoint_gaps_close_when_the_sweep_reaches_the_ends(self):
        cold, hot = endpoint_gaps_c(
            self.mapped, {"min_c": COLD_END, "max_c": HOT_END}
        )
        self.assertAlmostEqual(cold, 0.0, places=9)
        self.assertAlmostEqual(hot, 0.0, places=9)

    def test_endpoint_gap_reported_when_the_sweep_stops_short(self):
        cold, hot = endpoint_gaps_c(self.mapped, {"min_c": -120.0, "max_c": 110.0})
        self.assertAlmostEqual(cold, 20.0, places=9)
        self.assertAlmostEqual(hot, 25.0, places=9)

    def test_widest_step_is_the_largest_neighbouring_interval(self):
        self.assertAlmostEqual(widest_step_c(self.mapped), 40.0, places=9)


class TrendTests(unittest.TestCase):
    def test_nominal_map_trends_are_sound(self):
        mapped = read_temperature_map(_points())
        self.assertTrue(forward_voltage_trend_sound(mapped))
        self.assertTrue(reverse_leakage_trend_sound(mapped))

    def test_rising_forward_drop_is_unsound(self):
        points = _points()
        points[3]["forward_voltage_v"] = 0.80
        self.assertFalse(forward_voltage_trend_sound(read_temperature_map(points)))

    def test_falling_leakage_is_unsound(self):
        points = _points()
        points[4]["reverse_leakage_ua"] = 0.002
        self.assertFalse(reverse_leakage_trend_sound(read_temperature_map(points)))


class MapReadoutTests(unittest.TestCase):
    def setUp(self):
        self.mapped = read_temperature_map(_points())

    def test_forward_voltage_interpolates_linearly(self):
        self.assertAlmostEqual(forward_voltage_at_c(self.mapped, 0.0), 0.70, places=9)

    def test_leakage_interpolates_geometrically(self):
        value = reverse_leakage_at_c(self.mapped, 0.0)
        self.assertAlmostEqual(value, 0.032, delta=0.032 * 1e-9)

    def test_reading_far_outside_the_map_refused(self):
        with self.assertRaises(ValueError):
            forward_voltage_at_c(self.mapped, 200.0, 10.0)

    def test_reading_inside_the_extension_allowance_admitted(self):
        value = forward_voltage_at_c(self.mapped, 90.0, 10.0)
        self.assertAlmostEqual(value, 0.52, places=9)


class SelfHeatingTests(unittest.TestCase):
    def setUp(self):
        self.mapped = read_temperature_map(_points())

    def test_dissipation_is_drop_times_string_current(self):
        self.assertAlmostEqual(forward_dissipation_w(0.53, 2.0), 1.06, places=9)

    def test_junction_temperature_adds_the_rise_to_the_mount(self):
        self.assertAlmostEqual(junction_temperature_c(85.0, 1.06, 4.0), 89.24, places=9)

    def test_zero_thermal_resistance_leaves_the_junction_at_the_mount(self):
        settled = self_heated_operating_point(self.mapped, 60.0, 2.0, 0.0)
        self.assertAlmostEqual(settled["junction_temperature_c"], 60.0, places=9)
        self.assertAlmostEqual(settled["junction_rise_c"], 0.0, places=9)

    def test_loop_settles_between_the_mount_and_the_reachable_bound(self):
        settled = self_heated_operating_point(self.mapped, HOT_END, 2.0, 4.0)
        bound = maximum_possible_junction_c(self.mapped, HOT_END, 2.0, 4.0)
        self.assertGreater(settled["junction_temperature_c"], HOT_END + 1.0)
        self.assertLess(settled["junction_temperature_c"], bound - 1.0)
        self.assertGreaterEqual(settled["iterations"], 1)

    def test_loss_fraction_is_the_drop_over_the_string_voltage(self):
        self.assertAlmostEqual(forward_loss_fraction(0.90, 100.0), 0.009, places=9)


class RunTests(unittest.TestCase):
    def test_nominal_map_is_accepted(self):
        result = map_blocking_diode_temperature_behaviour(_case())
        self.assertEqual(result["verdict"], PARAMETERS_MAPPED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["point_count"], 6)
        self.assertGreater(result["junction_temperature_c"], HOT_END + 1.0)
        self.assertGreater(result["hot_reverse_leakage_ua"], 0.6)

    def test_sweep_short_of_the_cold_end_reports_coverage(self):
        result = map_blocking_diode_temperature_behaviour(
            _case(operating_range_c={"min_c": -130.0, "max_c": HOT_END})
        )
        self.assertEqual(result["verdict"], MAP_COVERAGE_INSUFFICIENT)
        self.assertTrue(result["findings"])

    def test_sweep_below_the_point_floor_reports_coverage(self):
        thin = [_points()[0], _points()[3], _points()[5]]
        result = map_blocking_diode_temperature_behaviour(_case(points=thin))
        self.assertEqual(result["verdict"], MAP_COVERAGE_INSUFFICIENT)

    def test_coarse_sweep_reports_resolution(self):
        points = _points()
        del points[1]
        result = map_blocking_diode_temperature_behaviour(_case(points=points))
        self.assertEqual(result["verdict"], MAP_RESOLUTION_INSUFFICIENT)

    def test_rising_forward_drop_reports_trends(self):
        points = _points()
        points[3]["forward_voltage_v"] = 0.80
        result = map_blocking_diode_temperature_behaviour(_case(points=points))
        self.assertEqual(result["verdict"], MAP_TRENDS_INCONSISTENT)

    def test_large_thermal_resistance_leaves_the_mapped_range(self):
        result = map_blocking_diode_temperature_behaviour(
            _case(thermal_resistance_c_per_w=50.0)
        )
        self.assertEqual(result["verdict"], SELF_HEATING_BEYOND_MAP)

    def test_low_rating_reports_the_settled_junction(self):
        result = map_blocking_diode_temperature_behaviour(
            _case(), _policy(max_junction_temperature_c=86.0)
        )
        self.assertEqual(result["verdict"], JUNCTION_RATING_EXCEEDED)
        self.assertGreater(result["junction_rise_c"], 0.0)

    def test_heavy_forward_loss_is_reported_without_voiding_the_map(self):
        result = map_blocking_diode_temperature_behaviour(_case(string_voltage_v=10.0))
        self.assertEqual(result["verdict"], PARAMETERS_MAPPED)
        self.assertTrue(result["findings"])

    def test_case_without_an_operating_range_rejected(self):
        case = _case()
        del case["operating_range_c"]
        with self.assertRaises(ValueError):
            map_blocking_diode_temperature_behaviour(case)


if __name__ == "__main__":
    unittest.main()
