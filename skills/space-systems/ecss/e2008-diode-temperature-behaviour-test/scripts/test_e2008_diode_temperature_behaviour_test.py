"""Contract tests for the clause 9.6.14 diode temperature behaviour logic."""

import math
import unittest

from e2008_diode_temperature_behaviour_test_logic import (
    BEHAVIOUR_MAP_ACCEPTED,
    BEHAVIOUR_VERDICTS,
    DEFAULT_DIODE_SWEEP_POLICY,
    OPERATING_RANGE_NOT_COVERED,
    SWEEP_PLAN_DEFICIENT,
    TEMPERATURE_COEFFICIENT_OUT_OF_BAND,
    assess_diode_temperature_behaviour,
    endpoint_gaps_k,
    forward_coefficient_mv_per_k,
    largest_step_k,
    leakage_doubling_interval_k,
    normalise_sweep,
    sweep_span_k,
    validate_sweep_policy,
)

NOMINAL_TEMPS = [-100.0 + 25.0 * i for i in range(9)]


def _policy(**overrides):
    policy = dict(DEFAULT_DIODE_SWEEP_POLICY)
    policy.update(overrides)
    return policy


def _sweep(tempco_mv_per_k=-2.0, doubling_k=15.0, temps=None):
    temps = list(NOMINAL_TEMPS if temps is None else temps)
    return [
        {
            "temperature_c": t,
            "forward_voltage_v": 0.55 + (tempco_mv_per_k / 1000.0) * (t - 25.0),
            "reverse_leakage_a": 1.0e-12 * 2.0 ** ((t + 100.0) / doubling_k),
        }
        for t in temps
    ]


def _case(**overrides):
    case = {
        "operating_range": {"min_operating_c": -100.0, "max_operating_c": 100.0},
        "sweep": _sweep(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_sweep_policy(DEFAULT_DIODE_SWEEP_POLICY),
            DEFAULT_DIODE_SWEEP_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_policy("sweep")

    def test_a_two_point_sweep_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_policy(_policy(min_sweep_points=2))

    def test_an_inverted_coefficient_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_policy(_policy(min_forward_coefficient_mv_per_k=0.5))

    def test_an_inverted_doubling_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_policy(_policy(min_leakage_doubling_interval_k=40.0))

    def test_a_zero_step_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_policy(_policy(max_step_k=0.0))

    def test_every_verdict_is_declared(self):
        self.assertEqual(len(set(BEHAVIOUR_VERDICTS)), 4)


class SweepShapeTests(unittest.TestCase):
    def test_a_scrambled_sweep_is_ordered_by_temperature(self):
        rows = normalise_sweep(list(reversed(_sweep())))
        temperatures = [row["temperature_c"] for row in rows]
        self.assertEqual(temperatures, sorted(temperatures))

    def test_a_repeated_temperature_is_rejected(self):
        points = _sweep()
        points.append(dict(points[0]))
        with self.assertRaises(ValueError):
            normalise_sweep(points)

    def test_an_empty_sweep_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_sweep([])

    def test_a_non_mapping_sweep_point_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_sweep([[-40.0, 0.8, 1.0e-12]])

    def test_a_negative_forward_voltage_is_rejected(self):
        points = _sweep()
        points[0]["forward_voltage_v"] = -0.1
        with self.assertRaises(ValueError):
            normalise_sweep(points)

    def test_a_zero_leakage_reading_is_rejected(self):
        points = _sweep()
        points[0]["reverse_leakage_a"] = 0.0
        with self.assertRaises(ValueError):
            normalise_sweep(points)

    def test_the_span_is_the_distance_between_the_ends(self):
        self.assertAlmostEqual(sweep_span_k(_sweep()), 200.0, places=9)

    def test_the_largest_step_is_the_widest_neighbour_gap(self):
        self.assertAlmostEqual(largest_step_k(_sweep()), 25.0, places=9)

    def test_one_wide_gap_sets_the_largest_step(self):
        points = _sweep(temps=[-100.0, -75.0, -50.0, 40.0, 100.0])
        self.assertAlmostEqual(largest_step_k(points), 90.0, places=9)

    def test_a_single_point_sweep_has_no_step(self):
        with self.assertRaises(ValueError):
            largest_step_k(_sweep(temps=[25.0]))


class EndpointCoverageTests(unittest.TestCase):
    def test_a_sweep_reaching_both_ends_leaves_no_gap(self):
        gaps = endpoint_gaps_k(_sweep(), -100.0, 100.0)
        self.assertAlmostEqual(gaps["cold_gap_k"], 0.0, places=9)
        self.assertAlmostEqual(gaps["hot_gap_k"], 0.0, places=9)

    def test_a_sweep_stopping_short_of_the_cold_end_leaves_a_gap(self):
        gaps = endpoint_gaps_k(_sweep(), -140.0, 100.0)
        self.assertAlmostEqual(gaps["cold_gap_k"], 40.0, places=9)
        self.assertAlmostEqual(gaps["hot_gap_k"], 0.0, places=9)

    def test_a_sweep_stopping_short_of_the_hot_end_leaves_a_gap(self):
        gaps = endpoint_gaps_k(_sweep(), -100.0, 125.0)
        self.assertAlmostEqual(gaps["hot_gap_k"], 25.0, places=9)

    def test_a_sweep_overshooting_the_range_leaves_no_negative_gap(self):
        gaps = endpoint_gaps_k(_sweep(), -60.0, 60.0)
        self.assertAlmostEqual(gaps["cold_gap_k"], 0.0, places=9)
        self.assertAlmostEqual(gaps["hot_gap_k"], 0.0, places=9)

    def test_an_inverted_operating_range_is_rejected(self):
        with self.assertRaises(ValueError):
            endpoint_gaps_k(_sweep(), 100.0, -100.0)


class FitTests(unittest.TestCase):
    def test_the_coefficient_recovers_a_linear_sweep(self):
        self.assertAlmostEqual(
            forward_coefficient_mv_per_k(_sweep(tempco_mv_per_k=-2.0)),
            -2.0,
            places=9,
        )

    def test_the_coefficient_recovers_a_steeper_linear_sweep(self):
        self.assertAlmostEqual(
            forward_coefficient_mv_per_k(_sweep(tempco_mv_per_k=-3.5)),
            -3.5,
            places=9,
        )

    def test_a_flat_sweep_has_no_coefficient(self):
        self.assertAlmostEqual(
            forward_coefficient_mv_per_k(_sweep(tempco_mv_per_k=0.0)),
            0.0,
            places=9,
        )

    def test_the_fit_ignores_the_order_the_points_arrive_in(self):
        ordered = forward_coefficient_mv_per_k(_sweep())
        scrambled = forward_coefficient_mv_per_k(list(reversed(_sweep())))
        self.assertAlmostEqual(ordered, scrambled, places=12)

    def test_a_single_point_has_no_coefficient(self):
        with self.assertRaises(ValueError):
            forward_coefficient_mv_per_k(_sweep(temps=[25.0]))

    def test_the_doubling_interval_recovers_the_generated_one(self):
        self.assertAlmostEqual(
            leakage_doubling_interval_k(_sweep(doubling_k=15.0)), 15.0, places=9
        )

    def test_a_faster_doubling_gives_a_shorter_interval(self):
        points = [
            {
                "temperature_c": -20.0,
                "forward_voltage_v": 0.7,
                "reverse_leakage_a": 1.0e-12,
            },
            {
                "temperature_c": 20.0,
                "forward_voltage_v": 0.6,
                "reverse_leakage_a": 1.0e-12 * 2.0 ** 10.0,
            },
        ]
        self.assertAlmostEqual(leakage_doubling_interval_k(points), 4.0, places=9)

    def test_leakage_that_did_not_grow_has_no_doubling_interval(self):
        points = _sweep()
        for row in points:
            row["reverse_leakage_a"] = 1.0e-12
        with self.assertRaises(ValueError):
            leakage_doubling_interval_k(points)


class BehaviourAssessmentTests(unittest.TestCase):
    def test_a_nominal_map_is_accepted(self):
        result = assess_diode_temperature_behaviour(_case())
        self.assertEqual(result["verdict"], BEHAVIOUR_MAP_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_the_derived_numbers_are_reported(self):
        result = assess_diode_temperature_behaviour(_case())
        self.assertEqual(result["sweep_points"], 9)
        self.assertAlmostEqual(result["sweep_span_k"], 200.0, places=9)
        self.assertAlmostEqual(result["largest_step_k"], 25.0, places=9)
        self.assertAlmostEqual(
            result["forward_coefficient_mv_per_k"], -2.0, places=9
        )
        self.assertAlmostEqual(
            result["leakage_doubling_interval_k"], 15.0, places=9
        )

    def test_a_sweep_short_of_the_cold_end_does_not_cover_the_range(self):
        result = assess_diode_temperature_behaviour(
            _case(
                operating_range={
                    "min_operating_c": -150.0,
                    "max_operating_c": 100.0,
                }
            )
        )
        self.assertEqual(result["verdict"], OPERATING_RANGE_NOT_COVERED)
        self.assertAlmostEqual(result["cold_gap_k"], 50.0, places=9)

    def test_a_sweep_short_of_the_hot_end_does_not_cover_the_range(self):
        result = assess_diode_temperature_behaviour(
            _case(
                operating_range={
                    "min_operating_c": -100.0,
                    "max_operating_c": 160.0,
                }
            )
        )
        self.assertEqual(result["verdict"], OPERATING_RANGE_NOT_COVERED)
        self.assertAlmostEqual(result["hot_gap_k"], 60.0, places=9)

    def test_an_endpoint_gap_exactly_on_the_ceiling_is_accepted(self):
        policy = _policy()
        gap = policy["max_endpoint_gap_k"]
        result = assess_diode_temperature_behaviour(
            _case(
                operating_range={
                    "min_operating_c": -100.0 - gap,
                    "max_operating_c": 100.0,
                }
            ),
            policy,
        )
        self.assertAlmostEqual(result["cold_gap_k"], gap, places=9)
        self.assertEqual(result["verdict"], BEHAVIOUR_MAP_ACCEPTED)

    def test_a_narrow_declared_range_does_not_cover_the_map_requirement(self):
        result = assess_diode_temperature_behaviour(
            _case(
                operating_range={"min_operating_c": -20.0, "max_operating_c": 60.0},
                sweep=_sweep(temps=[-20.0, 0.0, 20.0, 40.0, 60.0]),
            )
        )
        self.assertEqual(result["verdict"], OPERATING_RANGE_NOT_COVERED)
        self.assertAlmostEqual(result["operating_span_k"], 80.0, places=9)

    def test_a_flat_forward_voltage_is_out_of_the_coefficient_band(self):
        result = assess_diode_temperature_behaviour(
            _case(sweep=_sweep(tempco_mv_per_k=-0.2))
        )
        self.assertEqual(result["verdict"], TEMPERATURE_COEFFICIENT_OUT_OF_BAND)

    def test_an_oversteep_forward_voltage_is_out_of_the_coefficient_band(self):
        result = assess_diode_temperature_behaviour(
            _case(sweep=_sweep(tempco_mv_per_k=-4.5))
        )
        self.assertEqual(result["verdict"], TEMPERATURE_COEFFICIENT_OUT_OF_BAND)

    def test_a_coefficient_exactly_on_the_band_edge_is_accepted(self):
        policy = _policy()
        edge = policy["min_forward_coefficient_mv_per_k"]
        result = assess_diode_temperature_behaviour(
            _case(sweep=_sweep(tempco_mv_per_k=edge)), policy
        )
        self.assertAlmostEqual(
            result["forward_coefficient_mv_per_k"], edge, places=9
        )
        self.assertEqual(result["verdict"], BEHAVIOUR_MAP_ACCEPTED)

    def test_a_sluggish_leakage_doubling_is_out_of_band(self):
        result = assess_diode_temperature_behaviour(
            _case(sweep=_sweep(doubling_k=30.0))
        )
        self.assertEqual(result["verdict"], TEMPERATURE_COEFFICIENT_OUT_OF_BAND)
        self.assertAlmostEqual(
            result["leakage_doubling_interval_k"], 30.0, places=9
        )

    def test_a_doubling_interval_exactly_on_the_band_edge_is_accepted(self):
        policy = _policy()
        edge = policy["max_leakage_doubling_interval_k"]
        result = assess_diode_temperature_behaviour(
            _case(sweep=_sweep(doubling_k=edge)), policy
        )
        self.assertAlmostEqual(
            result["leakage_doubling_interval_k"], edge, places=9
        )
        self.assertEqual(result["verdict"], BEHAVIOUR_MAP_ACCEPTED)

    def test_missing_range_coverage_outranks_a_bad_coefficient(self):
        result = assess_diode_temperature_behaviour(
            _case(
                operating_range={
                    "min_operating_c": -150.0,
                    "max_operating_c": 100.0,
                },
                sweep=_sweep(tempco_mv_per_k=-0.2),
            )
        )
        self.assertEqual(result["verdict"], OPERATING_RANGE_NOT_COVERED)

    def test_too_few_sweep_points_is_a_plan_deficiency(self):
        result = assess_diode_temperature_behaviour(
            _case(sweep=_sweep(temps=[-100.0, -40.0, 30.0, 100.0])),
            _policy(max_step_k=80.0),
        )
        self.assertEqual(result["verdict"], SWEEP_PLAN_DEFICIENT)
        self.assertEqual(result["sweep_points"], 4)

    def test_a_coarse_step_is_a_plan_deficiency(self):
        result = assess_diode_temperature_behaviour(
            _case(sweep=_sweep(temps=[-100.0, -50.0, 0.0, 50.0, 100.0]))
        )
        self.assertEqual(result["verdict"], SWEEP_PLAN_DEFICIENT)
        self.assertAlmostEqual(result["largest_step_k"], 50.0, places=9)

    def test_a_step_exactly_on_the_ceiling_is_accepted(self):
        policy = _policy(max_step_k=50.0)
        result = assess_diode_temperature_behaviour(
            _case(sweep=_sweep(temps=[-100.0, -50.0, 0.0, 50.0, 100.0])), policy
        )
        self.assertAlmostEqual(result["largest_step_k"], 50.0, places=9)
        self.assertEqual(result["verdict"], BEHAVIOUR_MAP_ACCEPTED)

    def test_a_bad_coefficient_outranks_a_coarse_step(self):
        result = assess_diode_temperature_behaviour(
            _case(
                sweep=_sweep(
                    tempco_mv_per_k=-0.2,
                    temps=[-100.0, -50.0, 0.0, 50.0, 100.0],
                )
            )
        )
        self.assertEqual(result["verdict"], TEMPERATURE_COEFFICIENT_OUT_OF_BAND)

    def test_every_sweep_finding_is_reported_not_only_the_first(self):
        result = assess_diode_temperature_behaviour(
            _case(sweep=_sweep(tempco_mv_per_k=-0.2, doubling_k=30.0,
                               temps=[-100.0, -50.0, 0.0, 50.0, 100.0]))
        )
        self.assertEqual(len(result["findings"]), 3)

    def test_a_missing_operating_range_is_rejected(self):
        case = _case()
        del case["operating_range"]
        with self.assertRaises(ValueError):
            assess_diode_temperature_behaviour(case)

    def test_a_missing_sweep_is_rejected(self):
        case = _case()
        del case["sweep"]
        with self.assertRaises(ValueError):
            assess_diode_temperature_behaviour(case)

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_temperature_behaviour(["sweep"])

    def test_an_operating_range_below_absolute_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_temperature_behaviour(
                _case(
                    operating_range={
                        "min_operating_c": -400.0,
                        "max_operating_c": 100.0,
                    }
                )
            )

    def test_the_fit_is_deterministic_across_runs(self):
        first = assess_diode_temperature_behaviour(_case())
        second = assess_diode_temperature_behaviour(_case())
        self.assertEqual(
            first["forward_coefficient_mv_per_k"],
            second["forward_coefficient_mv_per_k"],
        )
        self.assertTrue(math.isfinite(first["leakage_doubling_interval_k"]))


if __name__ == "__main__":
    unittest.main()
