"""Contract tests for the clause 5.2.19.1.1 load-inductance operating range.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a range with no specified
maximum, a stored energy or turn-off transient beyond what the clamp path
can take, and a demonstration record that leaves the endpoint or a stretch
of the range untouched.
"""

import math
import unittest

from e2020_load_inductance_operating_range_logic import (
    DEFAULT_INDUCTANCE_POLICY,
    INDUCTANCE_RANGE_NOT_DECLARED,
    OPERATION_ACROSS_RANGE_DEMONSTRATED,
    RANGE_COVERAGE_INCOMPLETE,
    TRANSIENT_BEYOND_CLAMP,
    assess_load_inductance_operating_range,
    clamp_energy_margin,
    clamp_voltage_margin,
    coverage_gaps,
    demonstrated_points,
    endpoint_demonstrated,
    inductance_advisories,
    points_outside_range,
    stored_energy_j,
    turn_off_transient_v,
    validate_declared_range,
    validate_demonstrated_point,
    validate_inductance_policy,
    validate_limiter_record,
    widest_coverage_gap,
)

L_MAX = 1.0e-3


def _policy(**overrides):
    policy = dict(DEFAULT_INDUCTANCE_POLICY)
    policy.update(overrides)
    return policy


def _limiter(**overrides):
    limiter = {
        "id": "lcl-11",
        "limitation_current_a": 4.0,
        "current_fall_s": 1.0e-3,
        "bus_voltage_v": 28.0,
        "clamp_voltage_v": 80.0,
        "clamp_energy_j": 0.5,
    }
    limiter.update(overrides)
    return limiter


def _range(**overrides):
    declared = {"min_load_inductance_h": 0.0, "max_load_inductance_h": L_MAX}
    declared.update(overrides)
    return declared


def _points(values=(0.0, 0.00025, 0.0005, 0.00075, L_MAX)):
    return [
        {"name": "point-%d" % index, "inductance_h": value}
        for index, value in enumerate(values)
    ]


def _case(**overrides):
    case = {
        "limiter": _limiter(),
        "declared_range": _range(),
        "demonstrated_points": _points(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_inductance_policy(DEFAULT_INDUCTANCE_POLICY),
            DEFAULT_INDUCTANCE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_inductance_policy("min_clamp_energy_margin")

    def test_energy_margin_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_inductance_policy(_policy(min_clamp_energy_margin=0.8))

    def test_voltage_margin_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_inductance_policy(_policy(min_clamp_voltage_margin=0.9))

    def test_zero_coverage_gap_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_inductance_policy(_policy(max_coverage_gap_fraction=0.0))

    def test_gap_allowance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_inductance_policy(_policy(max_coverage_gap_fraction=1.5))

    def test_non_boolean_endpoint_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_inductance_policy(_policy(require_endpoint_demonstration="yes"))

    def test_advisory_below_a_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            validate_inductance_policy(_policy(thin_margin_advisory=1.2))


class LimiterValidationTests(unittest.TestCase):
    def test_good_limiter_validates(self):
        record = validate_limiter_record(_limiter())
        self.assertEqual(record["id"], "lcl-11")
        self.assertAlmostEqual(record["limitation_current_a"], 4.0, places=9)

    def test_non_mapping_limiter_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(["lcl-11"])

    def test_blank_limiter_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(_limiter(id="  "))

    def test_zero_limitation_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(_limiter(limitation_current_a=0.0))

    def test_zero_current_fall_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(_limiter(current_fall_s=0.0))

    def test_clamp_voltage_at_the_bus_voltage_rejected(self):
        with self.assertRaises(ValueError):
            validate_limiter_record(_limiter(clamp_voltage_v=28.0))


class RangeValidationTests(unittest.TestCase):
    def test_good_range_validates(self):
        record = validate_declared_range(_range())
        self.assertAlmostEqual(record["max_load_inductance_h"], L_MAX, places=12)

    def test_an_absent_range_reads_as_none(self):
        self.assertIsNone(validate_declared_range(None))

    def test_non_mapping_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_declared_range([L_MAX])

    def test_a_maximum_at_the_minimum_rejected(self):
        with self.assertRaises(ValueError):
            validate_declared_range(_range(min_load_inductance_h=L_MAX))

    def test_negative_minimum_rejected(self):
        with self.assertRaises(ValueError):
            validate_declared_range(_range(min_load_inductance_h=-1.0e-6))

    def test_non_mapping_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_demonstrated_point(["point-0"])

    def test_blank_point_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_demonstrated_point({"name": " ", "inductance_h": L_MAX})

    def test_negative_point_inductance_rejected(self):
        with self.assertRaises(ValueError):
            validate_demonstrated_point({"name": "p", "inductance_h": -1.0e-6})

    def test_empty_point_record_rejected(self):
        with self.assertRaises(ValueError):
            demonstrated_points([])

    def test_duplicate_point_name_rejected(self):
        with self.assertRaises(ValueError):
            demonstrated_points(
                [
                    {"name": "p", "inductance_h": 0.0},
                    {"name": "p", "inductance_h": L_MAX},
                ]
            )

    def test_points_come_back_sorted_by_inductance(self):
        records = demonstrated_points(_points((L_MAX, 0.0, 0.0005)))
        self.assertAlmostEqual(records[0]["inductance_h"], 0.0, places=12)
        self.assertAlmostEqual(records[-1]["inductance_h"], L_MAX, places=12)


class StressTests(unittest.TestCase):
    def test_stored_energy_at_the_maximum(self):
        self.assertAlmostEqual(stored_energy_j(L_MAX, 4.0), 0.008, places=12)

    def test_stored_energy_is_zero_on_a_resistive_load(self):
        self.assertAlmostEqual(stored_energy_j(0.0, 4.0), 0.0, places=15)

    def test_stored_energy_rejects_a_zero_current(self):
        with self.assertRaises(ValueError):
            stored_energy_j(L_MAX, 0.0)

    def test_transient_is_the_bus_voltage_on_a_resistive_load(self):
        self.assertAlmostEqual(turn_off_transient_v(_limiter(), 0.0), 28.0, places=9)

    def test_transient_grows_with_the_inductance(self):
        self.assertAlmostEqual(
            turn_off_transient_v(_limiter(), L_MAX), 32.0, places=9
        )

    def test_energy_margin_at_the_maximum(self):
        self.assertAlmostEqual(
            clamp_energy_margin(_limiter(), L_MAX), 62.5, places=9
        )

    def test_energy_margin_is_unbounded_with_no_stored_energy(self):
        self.assertTrue(math.isinf(clamp_energy_margin(_limiter(), 0.0)))

    def test_voltage_margin_at_the_maximum(self):
        self.assertAlmostEqual(
            clamp_voltage_margin(_limiter(), L_MAX), 2.5, places=9
        )


class CoverageTests(unittest.TestCase):
    def test_an_even_spread_leaves_equal_gaps(self):
        gaps = coverage_gaps(_range(), _points())
        self.assertEqual(len(gaps), 4)
        for gap in gaps:
            self.assertAlmostEqual(gap, 0.25, places=9)

    def test_endpoints_only_leave_one_gap_of_the_whole_span(self):
        self.assertAlmostEqual(
            widest_coverage_gap(_range(), _points((0.0, L_MAX))), 1.0, places=9
        )

    def test_a_missing_top_stretch_is_the_widest_gap(self):
        self.assertAlmostEqual(
            widest_coverage_gap(_range(), _points((0.0, 0.0002, 0.0004))),
            0.6,
            places=9,
        )

    def test_the_endpoint_counts_as_demonstrated(self):
        self.assertTrue(endpoint_demonstrated(_range(), _points()))

    def test_approaching_the_endpoint_is_not_demonstrating_it(self):
        self.assertFalse(
            endpoint_demonstrated(_range(), _points((0.0, 0.0009)))
        )

    def test_a_point_beyond_the_endpoint_still_demonstrates_it(self):
        self.assertTrue(
            endpoint_demonstrated(_range(), _points((0.0, 0.0012)))
        )

    def test_a_point_above_the_range_is_named_separately(self):
        names = points_outside_range(_range(), _points((0.0, L_MAX, 0.0012)))
        self.assertEqual(len(names), 1)

    def test_a_point_on_the_endpoint_is_not_outside_the_range(self):
        self.assertEqual(points_outside_range(_range(), _points()), ())

    def test_a_point_below_the_declared_minimum_is_not_counted_inside(self):
        declared = _range(min_load_inductance_h=0.0002)
        gaps = coverage_gaps(declared, _points((0.0001, 0.0002, L_MAX)))
        self.assertAlmostEqual(max(gaps), 1.0, places=9)

    def test_coverage_refuses_an_undeclared_range(self):
        with self.assertRaises(ValueError):
            coverage_gaps(None, _points())


class AdvisoryTests(unittest.TestCase):
    def test_a_comfortable_design_raises_no_advisory(self):
        self.assertEqual(
            inductance_advisories(_limiter(), _range(), _points()), ()
        )

    def test_a_thin_voltage_margin_is_named(self):
        advisories = inductance_advisories(
            _limiter(clamp_voltage_v=60.0), _range(), _points()
        )
        self.assertEqual(len(advisories), 1)
        self.assertIn("clamp voltage margin", advisories[0])

    def test_a_thin_energy_margin_is_named(self):
        advisories = inductance_advisories(
            _limiter(clamp_energy_j=0.014), _range(), _points()
        )
        self.assertTrue(any("clamp energy margin" in item for item in advisories))

    def test_a_two_point_demonstration_is_named(self):
        advisories = inductance_advisories(
            _limiter(), _range(), _points((0.0, L_MAX))
        )
        self.assertTrue(any("assumed monotonic" in item for item in advisories))

    def test_demonstration_above_the_maximum_is_named(self):
        advisories = inductance_advisories(
            _limiter(), _range(), _points((0.0, 0.00025, 0.0005, 0.00075, L_MAX, 0.0012))
        )
        self.assertTrue(any("margin evidence" in item for item in advisories))

    def test_advisories_refuse_an_undeclared_range(self):
        with self.assertRaises(ValueError):
            inductance_advisories(_limiter(), None, _points())


class AssessmentTests(unittest.TestCase):
    def test_a_sound_design_passes(self):
        result = assess_load_inductance_operating_range(_case())
        self.assertEqual(result["verdict"], OPERATION_ACROSS_RANGE_DEMONSTRATED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["advisories"], [])

    def test_the_governing_numbers_are_reported(self):
        result = assess_load_inductance_operating_range(_case())
        self.assertAlmostEqual(result["stored_energy_j"], 0.008, places=12)
        self.assertAlmostEqual(result["turn_off_transient_v"], 32.0, places=9)
        self.assertAlmostEqual(result["clamp_energy_margin"], 62.5, places=9)
        self.assertAlmostEqual(result["clamp_voltage_margin"], 2.5, places=9)
        self.assertTrue(result["endpoint_demonstrated"])

    def test_an_undeclared_maximum_closes_the_assessment(self):
        result = assess_load_inductance_operating_range(_case(declared_range=None))
        self.assertEqual(result["verdict"], INDUCTANCE_RANGE_NOT_DECLARED)
        self.assertIn("no specified maximum", result["findings"][0])

    def test_a_clamp_energy_shortfall_fails(self):
        case = _case(limiter=_limiter(clamp_energy_j=0.005))
        result = assess_load_inductance_operating_range(case)
        self.assertEqual(result["verdict"], TRANSIENT_BEYOND_CLAMP)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_clamp_voltage_shortfall_fails(self):
        case = _case(limiter=_limiter(current_fall_s=1.0e-4))
        result = assess_load_inductance_operating_range(case)
        self.assertEqual(result["verdict"], TRANSIENT_BEYOND_CLAMP)
        self.assertAlmostEqual(result["turn_off_transient_v"], 68.0, places=9)

    def test_both_shortfalls_are_reported_not_only_the_first(self):
        case = _case(
            limiter=_limiter(clamp_energy_j=0.005, current_fall_s=1.0e-4)
        )
        result = assess_load_inductance_operating_range(case)
        self.assertEqual(len(result["findings"]), 2)

    def test_a_voltage_margin_exactly_on_the_bound_passes(self):
        case = _case(limiter=_limiter(clamp_voltage_v=41.6))
        result = assess_load_inductance_operating_range(case)
        self.assertAlmostEqual(result["clamp_voltage_margin"], 1.3, places=9)
        self.assertEqual(result["verdict"], OPERATION_ACROSS_RANGE_DEMONSTRATED)

    def test_an_undemonstrated_endpoint_fails_coverage(self):
        case = _case(demonstrated_points=_points((0.0, 0.00025, 0.0005, 0.00075)))
        result = assess_load_inductance_operating_range(case)
        self.assertEqual(result["verdict"], RANGE_COVERAGE_INCOMPLETE)
        self.assertFalse(result["endpoint_demonstrated"])

    def test_a_wide_untested_stretch_fails_coverage(self):
        case = _case(demonstrated_points=_points((0.0, L_MAX)))
        result = assess_load_inductance_operating_range(case)
        self.assertEqual(result["verdict"], RANGE_COVERAGE_INCOMPLETE)
        self.assertAlmostEqual(result["widest_coverage_gap"], 1.0, places=9)

    def test_the_endpoint_requirement_can_be_waived(self):
        case = _case(demonstrated_points=_points((0.0, 0.00025, 0.0005, 0.00075)))
        result = assess_load_inductance_operating_range(
            case, _policy(require_endpoint_demonstration=False)
        )
        self.assertEqual(result["verdict"], OPERATION_ACROSS_RANGE_DEMONSTRATED)

    def test_capability_is_judged_before_the_test_record(self):
        case = _case(
            limiter=_limiter(clamp_energy_j=0.005),
            demonstrated_points=_points((0.0, L_MAX)),
        )
        result = assess_load_inductance_operating_range(case)
        self.assertEqual(result["verdict"], TRANSIENT_BEYOND_CLAMP)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_load_inductance_operating_range(["limiter"])

    def test_missing_demonstrated_points_rejected(self):
        case = _case()
        del case["demonstrated_points"]
        with self.assertRaises(ValueError):
            assess_load_inductance_operating_range(case)

    def test_missing_limiter_rejected(self):
        case = _case()
        del case["limiter"]
        with self.assertRaises(ValueError):
            assess_load_inductance_operating_range(case)


if __name__ == "__main__":
    unittest.main()
