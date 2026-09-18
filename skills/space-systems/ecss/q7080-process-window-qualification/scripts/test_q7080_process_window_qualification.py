"""Contract tests for the parameter-window qualification logic."""

import copy
import unittest

from q7080_process_window_qualification_logic import (
    MIN_QUALIFICATION_RUNS,
    coupon_completeness,
    evaluate_coupon,
    grade_run_parameters,
    interior_coverage,
    qualify_window,
    validate_window,
    window_bound_coverage,
    within_window,
)

WINDOW = {
    "beam_power_w": (190.0, 210.0),
    "scan_speed_mm_s": (950.0, 1050.0),
    "layer_thickness_mm": (0.03, 0.03),
}

ACCEPTANCE = {
    "density_pct": {"min": 99.5},
    "tensile_uts_mpa": {"min": 900.0},
    "roughness_ra_um": {"max": 20.0},
}

REQUIRED = ["density_pct", "tensile_uts_mpa", "roughness_ra_um"]


def run(identifier, power, speed, layer=0.03, density=99.7, uts=940.0, ra=14.0):
    return {
        "id": identifier,
        "parameters": {
            "beam_power_w": power,
            "scan_speed_mm_s": speed,
            "layer_thickness_mm": layer,
        },
        "coupons": [
            {
                "id": identifier + "-c1",
                "measured": {
                    "density_pct": density,
                    "tensile_uts_mpa": uts,
                    "roughness_ra_um": ra,
                },
            }
        ],
    }


def campaign():
    return [
        run("r1", 190.0, 950.0),
        run("r2", 210.0, 1050.0, density=99.6, uts=920.0, ra=17.0),
        run("r3", 200.0, 1000.0, density=99.8, uts=950.0, ra=12.0),
    ]


def spec(runs=None):
    return {
        "window": copy.deepcopy(WINDOW),
        "runs": campaign() if runs is None else runs,
        "acceptance": copy.deepcopy(ACCEPTANCE),
        "required_characteristics": list(REQUIRED),
    }


class WindowValidationTests(unittest.TestCase):
    def test_bounds_returned_as_floats(self):
        validated = validate_window({"beam_power_w": (190, 210)})
        self.assertEqual(validated["beam_power_w"], (190.0, 210.0))

    def test_fixed_setpoint_window_accepted(self):
        validated = validate_window({"layer_thickness_mm": (0.03, 0.03)})
        self.assertEqual(validated["layer_thickness_mm"], (0.03, 0.03))

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_window({"beam_power_w": (210.0, 190.0)})

    def test_empty_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_window({})

    def test_malformed_bounds_rejected(self):
        with self.assertRaises(ValueError):
            validate_window({"beam_power_w": (190.0,)})

    def test_non_finite_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_window({"beam_power_w": (190.0, float("nan"))})


class WithinWindowTests(unittest.TestCase):
    def test_interior_value_is_inside(self):
        self.assertTrue(within_window(200.0, (190.0, 210.0)))

    def test_exact_low_bound_is_inside(self):
        self.assertTrue(within_window(190.0, (190.0, 210.0)))

    def test_exact_high_bound_is_inside(self):
        self.assertTrue(within_window(210.0, (190.0, 210.0)))

    def test_value_below_window_is_outside(self):
        self.assertFalse(within_window(189.0, (190.0, 210.0)))

    def test_value_above_window_is_outside(self):
        self.assertFalse(within_window(211.0, (190.0, 210.0)))


class RunGradingTests(unittest.TestCase):
    def test_compliant_run_has_no_excursions(self):
        self.assertEqual(grade_run_parameters(run("r1", 200.0, 1000.0), WINDOW), [])

    def test_out_of_window_parameter_reported(self):
        excursions = grade_run_parameters(run("r9", 215.0, 1000.0), WINDOW)
        self.assertEqual(len(excursions), 1)
        self.assertEqual(excursions[0]["reason"], "out-of-window")

    def test_unrecorded_parameter_reported(self):
        bad = run("r9", 200.0, 1000.0)
        del bad["parameters"]["scan_speed_mm_s"]
        excursions = grade_run_parameters(bad, WINDOW)
        self.assertEqual(excursions[0]["reason"], "unrecorded")

    def test_null_parameter_counts_as_unrecorded(self):
        bad = run("r9", 200.0, 1000.0)
        bad["parameters"]["scan_speed_mm_s"] = None
        self.assertEqual(grade_run_parameters(bad, WINDOW)[0]["reason"], "unrecorded")

    def test_undeclared_parameter_rejected(self):
        bad = run("r9", 200.0, 1000.0)
        bad["parameters"]["gas_flow_m_s"] = 2.0
        with self.assertRaises(ValueError):
            grade_run_parameters(bad, WINDOW)

    def test_run_without_id_rejected(self):
        bad = run("r9", 200.0, 1000.0)
        del bad["id"]
        with self.assertRaises(ValueError):
            grade_run_parameters(bad, WINDOW)


class CoverageTests(unittest.TestCase):
    def test_full_campaign_covers_every_bound(self):
        self.assertEqual(window_bound_coverage(campaign(), WINDOW), [])

    def test_unsampled_high_bound_reported(self):
        runs = campaign()
        runs[1] = run("r2", 205.0, 1045.0)
        missing = window_bound_coverage(runs, WINDOW)
        self.assertEqual(missing, [{"parameter": "beam_power_w", "bound": "high", "value": 210.0}])

    def test_fixed_setpoint_bound_is_covered_by_any_run(self):
        missing = window_bound_coverage(campaign(), {"layer_thickness_mm": (0.03, 0.03)})
        self.assertEqual(missing, [])

    def test_interior_sampled_by_the_centre_run(self):
        self.assertEqual(interior_coverage(campaign(), WINDOW), [])

    def test_edges_only_campaign_flags_the_interior(self):
        runs = [run("r1", 190.0, 950.0), run("r2", 210.0, 1050.0), run("r3", 190.0, 1050.0)]
        self.assertEqual(
            interior_coverage(runs, WINDOW), ["beam_power_w", "scan_speed_mm_s"]
        )

    def test_fixed_setpoint_has_no_interior_to_sample(self):
        self.assertEqual(interior_coverage(campaign(), {"layer_thickness_mm": (0.03, 0.03)}), [])

    def test_empty_run_list_rejected(self):
        with self.assertRaises(ValueError):
            window_bound_coverage([], WINDOW)


class CouponTests(unittest.TestCase):
    def test_compliant_coupon_passes(self):
        record = evaluate_coupon(campaign()[0]["coupons"][0], ACCEPTANCE)
        self.assertTrue(record["passed"])

    def test_below_minimum_reported(self):
        coupon = {"id": "c", "measured": {"density_pct": 99.2}}
        record = evaluate_coupon(coupon, ACCEPTANCE)
        self.assertEqual(record["failures"][0]["reason"], "below-minimum")

    def test_above_maximum_reported(self):
        coupon = {"id": "c", "measured": {"roughness_ra_um": 22.0}}
        record = evaluate_coupon(coupon, ACCEPTANCE)
        self.assertEqual(record["failures"][0]["reason"], "above-maximum")

    def test_value_exactly_on_the_limit_passes(self):
        coupon = {"id": "c", "measured": {"density_pct": 99.5, "roughness_ra_um": 20.0}}
        self.assertTrue(evaluate_coupon(coupon, ACCEPTANCE)["passed"])

    def test_characteristic_without_limit_rejected(self):
        coupon = {"id": "c", "measured": {"hardness_hv": 340.0}}
        with self.assertRaises(ValueError):
            evaluate_coupon(coupon, ACCEPTANCE)

    def test_coupon_without_measured_map_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_coupon({"id": "c"}, ACCEPTANCE)

    def test_unmeasured_characteristic_is_a_gap(self):
        runs = campaign()
        del runs[2]["coupons"][0]["measured"]["tensile_uts_mpa"]
        gaps = coupon_completeness(runs, REQUIRED)
        self.assertEqual(gaps, [{"run": "r3", "characteristic": "tensile_uts_mpa"}])

    def test_complete_campaign_has_no_gaps(self):
        self.assertEqual(coupon_completeness(campaign(), REQUIRED), [])

    def test_empty_required_list_rejected(self):
        with self.assertRaises(ValueError):
            coupon_completeness(campaign(), [])


class VerdictTests(unittest.TestCase):
    def test_clean_campaign_qualifies(self):
        result = qualify_window(spec())
        self.assertEqual(result["verdict"], "qualified")
        self.assertEqual(result["blocking"], [])

    def test_edges_only_campaign_qualifies_with_findings(self):
        runs = [run("r1", 190.0, 950.0), run("r2", 210.0, 1050.0), run("r3", 190.0, 1050.0)]
        result = qualify_window(spec(runs=runs))
        self.assertEqual(result["verdict"], "qualified-with-findings")
        self.assertEqual(len(result["findings"]), 2)

    def test_single_run_campaign_does_not_qualify(self):
        result = qualify_window(spec(runs=[run("r1", 190.0, 950.0)]))
        self.assertEqual(result["verdict"], "not-qualified")
        self.assertTrue(any("at least %d" % MIN_QUALIFICATION_RUNS in b
                            for b in result["blocking"]))

    def test_parameter_excursion_blocks_qualification(self):
        runs = campaign()
        runs[2]["parameters"]["beam_power_w"] = 215.0
        result = qualify_window(spec(runs=runs))
        self.assertEqual(result["verdict"], "not-qualified")
        self.assertTrue(any("out-of-window" in b for b in result["blocking"]))

    def test_failed_coupon_blocks_qualification(self):
        runs = campaign()
        runs[1]["coupons"][0]["measured"]["density_pct"] = 99.1
        result = qualify_window(spec(runs=runs))
        self.assertEqual(result["verdict"], "not-qualified")
        self.assertEqual(len(result["coupon_failures"]), 1)

    def test_unmeasured_characteristic_blocks_qualification(self):
        runs = campaign()
        del runs[0]["coupons"][0]["measured"]["roughness_ra_um"]
        result = qualify_window(spec(runs=runs))
        self.assertEqual(result["verdict"], "not-qualified")
        self.assertTrue(any("never measured" in b for b in result["blocking"]))

    def test_missing_bound_blocks_qualification(self):
        runs = campaign()
        runs[1] = run("r2", 205.0, 1045.0)
        result = qualify_window(spec(runs=runs))
        self.assertEqual(result["verdict"], "not-qualified")
        self.assertTrue(any("bound of beam_power_w" in b for b in result["blocking"]))

    def test_duplicate_run_id_rejected(self):
        runs = campaign()
        runs[2]["id"] = "r1"
        with self.assertRaises(ValueError):
            qualify_window(spec(runs=runs))

    def test_missing_spec_key_rejected(self):
        broken = spec()
        del broken["acceptance"]
        with self.assertRaises(ValueError):
            qualify_window(broken)

    def test_non_integer_min_runs_rejected(self):
        with self.assertRaises(ValueError):
            qualify_window(dict(spec(), min_runs=2.5))

    def test_run_count_reported(self):
        self.assertEqual(qualify_window(spec())["run_count"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=1)
