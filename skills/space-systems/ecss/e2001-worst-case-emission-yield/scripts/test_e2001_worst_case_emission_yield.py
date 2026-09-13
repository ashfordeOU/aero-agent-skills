#!/usr/bin/env python3
"""Gate 3 contract test for e2001-worst-case-emission-yield."""

import unittest

from e2001_worst_case_emission_yield_logic import (
    NO_SUSTAINED_GROWTH,
    SUSTAINED_GROWTH,
    assess_susceptibility,
    check_assessment_coverage,
    common_energy_grid,
    common_energy_span,
    crossover_energies,
    curve_energy_span,
    envelope_peak,
    interpolate_yield,
    summarize_envelope,
    validate_curve,
    within_limit,
    worst_case_envelope,
    yield_at_energy,
)

CURVE_A = {"curve_id": "coupon-A",
           "points": [(10.0, 0.5), (50.0, 1.2), (200.0, 2.1), (800.0, 1.4),
                      (1600.0, 0.6)]}
CURVE_B = {"curve_id": "coupon-B",
           "points": [(20.0, 0.7), (50.0, 1.0), (300.0, 2.4), (900.0, 1.1),
                      (1500.0, 0.5)]}
CURVE_SET = [CURVE_A, CURVE_B]

QUIET_CURVE = {"curve_id": "coupon-Q",
               "points": [(20.0, 0.2), (100.0, 0.6), (400.0, 0.8),
                          (1500.0, 0.3)]}


def synthetic_envelope(pairs, curve_id="coupon-A"):
    return [{"energy_ev": e, "yield": y, "curve_id": curve_id} for e, y in pairs]


class TestCurveValidation(unittest.TestCase):
    def test_valid_curve_is_normalised(self):
        curve = validate_curve({"curve_id": "  coupon-A  ",
                                "points": [(10.0, 0.5), (20.0, 0.9), (30.0, 1.3)]})
        self.assertEqual(curve["curve_id"], "coupon-A")
        self.assertEqual(len(curve["points"]), 3)

    def test_non_mapping_curve_raises(self):
        with self.assertRaises(ValueError):
            validate_curve([(10.0, 0.5), (20.0, 0.9), (30.0, 1.3)])

    def test_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_curve({"curve_id": "  ", "points": CURVE_A["points"]})

    def test_two_point_curve_raises(self):
        with self.assertRaises(ValueError):
            validate_curve({"curve_id": "short", "points": [(10.0, 0.5), (20.0, 0.9)]})

    def test_malformed_point_raises(self):
        with self.assertRaises(ValueError):
            validate_curve({"curve_id": "bad",
                            "points": [(10.0, 0.5), (20.0,), (30.0, 1.3)]})

    def test_out_of_order_energies_raise(self):
        with self.assertRaises(ValueError):
            validate_curve({"curve_id": "unsorted",
                            "points": [(10.0, 0.5), (30.0, 1.3), (20.0, 0.9)]})

    def test_duplicated_energy_raises(self):
        with self.assertRaises(ValueError):
            validate_curve({"curve_id": "dup",
                            "points": [(10.0, 0.5), (10.0, 0.9), (30.0, 1.3)]})

    def test_non_positive_energy_raises(self):
        with self.assertRaises(ValueError):
            validate_curve({"curve_id": "zero",
                            "points": [(0.0, 0.5), (20.0, 0.9), (30.0, 1.3)]})

    def test_negative_yield_raises(self):
        with self.assertRaises(ValueError):
            validate_curve({"curve_id": "neg",
                            "points": [(10.0, -0.1), (20.0, 0.9), (30.0, 1.3)]})

    def test_non_finite_yield_raises(self):
        with self.assertRaises(ValueError):
            validate_curve({"curve_id": "inf",
                            "points": [(10.0, 0.5), (20.0, float("inf")), (30.0, 1.3)]})

    def test_boolean_yield_raises(self):
        with self.assertRaises(ValueError):
            validate_curve({"curve_id": "bool",
                            "points": [(10.0, True), (20.0, 0.9), (30.0, 1.3)]})

    def test_curve_energy_span(self):
        low, high = curve_energy_span(CURVE_A)
        self.assertAlmostEqual(low, 10.0)
        self.assertAlmostEqual(high, 1600.0)


class TestInterpolation(unittest.TestCase):
    def test_measured_point_returns_its_own_yield(self):
        self.assertAlmostEqual(interpolate_yield(CURVE_A, 200.0), 2.1)

    def test_midpoint_is_linear(self):
        self.assertAlmostEqual(interpolate_yield(CURVE_A, 30.0), 0.85)

    def test_span_endpoints_are_allowed(self):
        self.assertAlmostEqual(interpolate_yield(CURVE_B, 20.0), 0.7)
        self.assertAlmostEqual(interpolate_yield(CURVE_B, 1500.0), 0.5)

    def test_energy_below_span_raises(self):
        with self.assertRaises(ValueError):
            interpolate_yield(CURVE_B, 5.0)

    def test_energy_above_span_raises(self):
        with self.assertRaises(ValueError):
            interpolate_yield(CURVE_B, 2000.0)


class TestCommonGrid(unittest.TestCase):
    def test_common_span_is_the_overlap(self):
        low, high = common_energy_span(CURVE_SET)
        self.assertAlmostEqual(low, 20.0)
        self.assertAlmostEqual(high, 1500.0)

    def test_disjoint_curves_raise(self):
        far = {"curve_id": "coupon-F",
               "points": [(2000.0, 0.4), (2500.0, 0.9), (3000.0, 1.1)]}
        with self.assertRaises(ValueError):
            common_energy_span([CURVE_A, far])

    def test_empty_curve_set_raises(self):
        with self.assertRaises(ValueError):
            common_energy_span([])

    def test_grid_holds_the_union_inside_the_overlap(self):
        grid = common_energy_grid(CURVE_SET)
        self.assertEqual(grid, [20.0, 50.0, 200.0, 300.0, 800.0, 900.0, 1500.0])

    def test_grid_excludes_energies_outside_the_overlap(self):
        grid = common_energy_grid(CURVE_SET)
        self.assertNotIn(10.0, grid)
        self.assertNotIn(1600.0, grid)

    def test_grid_is_sorted_and_deduplicated(self):
        grid = common_energy_grid(CURVE_SET)
        self.assertEqual(grid, sorted(grid))
        self.assertEqual(len(grid), len(set(grid)))


class TestEnvelope(unittest.TestCase):
    def setUp(self):
        self.envelope = worst_case_envelope(CURVE_SET)

    def test_envelope_matches_the_grid(self):
        self.assertEqual(len(self.envelope), len(common_energy_grid(CURVE_SET)))

    def test_low_energy_point_is_driven_by_the_second_coupon(self):
        point = self.envelope[0]
        self.assertAlmostEqual(point["energy_ev"], 20.0)
        self.assertAlmostEqual(point["yield"], 0.7)
        self.assertEqual(point["curve_id"], "coupon-B")

    def test_different_coupons_drive_different_grid_points(self):
        drivers = {p["energy_ev"]: p["curve_id"] for p in self.envelope}
        self.assertEqual(drivers[200.0], "coupon-A")
        self.assertEqual(drivers[300.0], "coupon-B")

    def test_envelope_is_an_upper_bound_on_every_curve(self):
        for point in self.envelope:
            for curve in CURVE_SET:
                self.assertTrue(within_limit(interpolate_yield(curve,
                                                               point["energy_ev"]),
                                             point["yield"]))

    def test_single_curve_envelope_reproduces_that_curve(self):
        envelope = worst_case_envelope([CURVE_B])
        self.assertAlmostEqual(envelope[0]["yield"], 0.7)
        self.assertEqual({p["curve_id"] for p in envelope}, {"coupon-B"})

    def test_explicit_grid_is_honoured(self):
        envelope = worst_case_envelope(CURVE_SET, grid=[100.0, 500.0, 1000.0])
        self.assertEqual([p["energy_ev"] for p in envelope], [100.0, 500.0, 1000.0])

    def test_grid_energy_outside_the_overlap_raises(self):
        with self.assertRaises(ValueError):
            worst_case_envelope(CURVE_SET, grid=[10.0, 500.0])

    def test_single_point_grid_raises(self):
        with self.assertRaises(ValueError):
            worst_case_envelope(CURVE_SET, grid=[500.0])

    def test_peak_reports_value_energy_and_driver(self):
        peak = envelope_peak(self.envelope)
        self.assertAlmostEqual(peak["yield"], 2.4)
        self.assertAlmostEqual(peak["energy_ev"], 300.0)
        self.assertEqual(peak["curve_id"], "coupon-B")

    def test_empty_envelope_peak_raises(self):
        with self.assertRaises(ValueError):
            envelope_peak([])

    def test_yield_at_energy_interpolates_the_envelope(self):
        self.assertAlmostEqual(yield_at_energy(self.envelope, 200.0), 2.1)

    def test_yield_outside_the_envelope_raises(self):
        with self.assertRaises(ValueError):
            yield_at_energy(self.envelope, 1800.0)


class TestCrossovers(unittest.TestCase):
    def setUp(self):
        self.envelope = worst_case_envelope(CURVE_SET)

    def test_first_crossover_is_interpolated_not_snapped_to_a_grid_point(self):
        crossings = crossover_energies(self.envelope)
        self.assertAlmostEqual(crossings["first_crossover_ev"], 38.0)

    def test_second_crossover_is_interpolated(self):
        crossings = crossover_energies(self.envelope)
        self.assertAlmostEqual(crossings["second_crossover_ev"], 1200.0)

    def test_grid_point_sitting_at_unity_is_itself_the_crossing(self):
        envelope = synthetic_envelope([(10.0, 0.5), (20.0, 1.0), (30.0, 1.5),
                                       (40.0, 0.5)])
        crossings = crossover_energies(envelope)
        self.assertAlmostEqual(crossings["first_crossover_ev"], 20.0)
        self.assertAlmostEqual(crossings["second_crossover_ev"], 35.0)

    def test_yield_one_ulp_off_unity_still_counts_as_the_crossing(self):
        envelope = synthetic_envelope([(10.0, 0.5), (20.0, 0.7 + 0.3),
                                       (30.0, 1.5), (40.0, 0.5)])
        crossings = crossover_energies(envelope)
        self.assertAlmostEqual(crossings["first_crossover_ev"], 20.0)

    def test_curve_set_below_unity_has_no_crossing(self):
        envelope = worst_case_envelope([QUIET_CURVE])
        crossings = crossover_energies(envelope)
        self.assertIsNone(crossings["first_crossover_ev"])
        self.assertIsNone(crossings["second_crossover_ev"])

    def test_non_positive_threshold_raises(self):
        with self.assertRaises(ValueError):
            crossover_energies(self.envelope, threshold=0.0)

    def test_single_point_envelope_raises(self):
        with self.assertRaises(ValueError):
            crossover_energies(synthetic_envelope([(10.0, 0.5)]))


class TestSusceptibility(unittest.TestCase):
    def setUp(self):
        self.envelope = worst_case_envelope(CURVE_SET)

    def test_envelope_above_unity_supports_growth(self):
        result = assess_susceptibility(self.envelope)
        self.assertEqual(result["verdict"], SUSTAINED_GROWTH)

    def test_envelope_below_unity_does_not(self):
        result = assess_susceptibility(worst_case_envelope([QUIET_CURVE]))
        self.assertEqual(result["verdict"], NO_SUSTAINED_GROWTH)
        self.assertTrue(result["compliant"])

    def test_peak_above_the_allowable_is_a_finding(self):
        result = assess_susceptibility(self.envelope, allowable_peak_yield=2.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("exceeds the allowable" in f for f in result["findings"]))

    def test_peak_exactly_at_the_allowable_stays_compliant(self):
        allowable = 2.05 + 0.11 + 0.24  # summed budget, lands 1 ULP under 2.4
        self.assertLess(allowable, 2.4)  # a bare <= against the peak would fail
        result = assess_susceptibility(self.envelope, allowable_peak_yield=allowable)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_non_positive_allowable_raises(self):
        with self.assertRaises(ValueError):
            assess_susceptibility(self.envelope, allowable_peak_yield=-1.0)

    def test_envelope_never_returning_below_unity_is_flagged(self):
        envelope = synthetic_envelope([(10.0, 0.5), (20.0, 1.4), (30.0, 1.8)])
        result = assess_susceptibility(envelope)
        self.assertTrue(any("fallen back through unity" in f
                            for f in result["findings"]))


class TestCoverageAndReport(unittest.TestCase):
    def test_required_span_inside_the_overlap_is_covered(self):
        result = check_assessment_coverage(CURVE_SET, (50.0, 1000.0))
        self.assertTrue(result["covered"])

    def test_required_span_wider_than_the_overlap_is_not_covered(self):
        result = check_assessment_coverage(CURVE_SET, (5.0, 2000.0))
        self.assertFalse(result["covered"])

    def test_required_span_exactly_equal_to_the_overlap_is_covered(self):
        result = check_assessment_coverage(CURVE_SET, (20.0, 1500.0))
        self.assertTrue(result["covered"])

    def test_decreasing_required_span_raises(self):
        with self.assertRaises(ValueError):
            check_assessment_coverage(CURVE_SET, (900.0, 100.0))

    def test_summary_reports_peak_driver_and_crossovers(self):
        lines = summarize_envelope(worst_case_envelope(CURVE_SET))
        self.assertTrue(lines[0].startswith("ECSS-E-ST-20-01C clause 9.3"))
        self.assertTrue(any("coupon-B" in line for line in lines))
        self.assertTrue(any("first crossover" in line for line in lines))

    def test_summary_states_a_missing_crossover(self):
        lines = summarize_envelope(worst_case_envelope([QUIET_CURVE]))
        self.assertTrue(any("not inside the measured span" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
