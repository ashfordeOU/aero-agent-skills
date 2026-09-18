#!/usr/bin/env python3
"""Contract test for anodizing line qualification (offline)."""

import copy
import unittest

from q7003_process_qualification_logic import (
    CONDITIONALLY_QUALIFIED,
    MIN_QUALIFICATION_RUNS,
    NOT_QUALIFIED,
    QUALIFIED,
    REQUALIFICATION_TRIGGERS,
    assess_coupon_results,
    assess_position_coverage,
    check_run_parameters,
    coupons_required,
    qualify_process,
    requalification_required,
    validate_parameter_windows,
)

WINDOWS = {
    "bath_temperature_c": (18.0, 22.0),
    "current_density_a_dm2": (1.2, 1.8),
    "dwell_minutes": (40.0, 60.0),
}

NOMINAL_RUN = {
    "bath_temperature_c": 20.0,
    "current_density_a_dm2": 1.5,
    "dwell_minutes": 50.0,
}

CHARACTERISTICS = ["coating-thickness", "coating-adhesion", "seal-quality"]

GOOD_CASE = {
    "parameter_windows": WINDOWS,
    "runs": [dict(NOMINAL_RUN), dict(NOMINAL_RUN), dict(NOMINAL_RUN)],
    "positions_sampled": [1, 2, 3, 4],
    "positions_available": 4,
    "required_characteristics": CHARACTERISTICS,
    "coupon_results": {name: "pass" for name in CHARACTERISTICS},
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class WindowTests(unittest.TestCase):
    def test_a_sound_window_set_validates(self):
        self.assertIs(validate_parameter_windows(WINDOWS), WINDOWS)

    def test_an_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter_windows({"dwell_minutes": (60.0, 40.0)})

    def test_an_empty_window_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter_windows({})

    def test_a_single_valued_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter_windows({"dwell_minutes": (50.0,)})

    def test_a_non_numeric_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter_windows({"dwell_minutes": ("40 min", 60.0)})

    def test_a_degenerate_window_is_allowed(self):
        self.assertTrue(validate_parameter_windows({"ph": (1.5, 1.5)}))


class RunParameterTests(unittest.TestCase):
    def test_a_nominal_run_is_in_control(self):
        result = check_run_parameters(NOMINAL_RUN, WINDOWS)
        self.assertTrue(result["in_control"])
        self.assertEqual(result["excursions"], [])

    def test_a_value_exactly_on_a_window_edge_is_in_control(self):
        # 0.1 + 0.2 lands one unit in the last place above 0.3, and a
        # logged parameter carries the same representation error.
        edge = dict(NOMINAL_RUN, bath_temperature_c=22.0 + (0.1 + 0.2 - 0.3))
        self.assertTrue(check_run_parameters(edge, WINDOWS)["in_control"])

    def test_a_value_on_the_lower_edge_is_in_control(self):
        edge = dict(NOMINAL_RUN, current_density_a_dm2=1.2)
        self.assertTrue(check_run_parameters(edge, WINDOWS)["in_control"])

    def test_an_excursion_is_named_with_its_window(self):
        hot = dict(NOMINAL_RUN, bath_temperature_c=27.0)
        result = check_run_parameters(hot, WINDOWS)
        self.assertFalse(result["in_control"])
        self.assertTrue(any("bath_temperature_c" in e for e in result["excursions"]))

    def test_an_unrecorded_parameter_is_an_excursion_not_a_pass(self):
        partial = {"bath_temperature_c": 20.0}
        result = check_run_parameters(partial, WINDOWS)
        self.assertFalse(result["in_control"])
        self.assertIn("dwell_minutes", result["unrecorded"])

    def test_a_non_mapping_run_rejected(self):
        with self.assertRaises(ValueError):
            check_run_parameters("all nominal", WINDOWS)


class CoverageTests(unittest.TestCase):
    def test_full_coverage_has_no_findings(self):
        result = assess_position_coverage([1, 2, 3, 4], 4)
        self.assertTrue(result["extremes_covered"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)

    def test_a_missing_extreme_is_reported(self):
        result = assess_position_coverage([2, 3], 4)
        self.assertFalse(result["extremes_covered"])
        self.assertTrue(any("ends of the rack" in f for f in result["findings"]))

    def test_extremes_only_on_a_long_rack_is_a_thin_interior(self):
        result = assess_position_coverage([1, 8], 8)
        self.assertTrue(result["extremes_covered"])
        self.assertTrue(any("interior spread" in f for f in result["findings"]))

    def test_coverage_exactly_on_the_recommended_fraction_is_clean(self):
        result = assess_position_coverage([1, 2, 7, 8], 8)
        self.assertAlmostEqual(result["coverage_fraction"], 0.5, places=9)
        self.assertEqual(result["findings"], [])

    def test_duplicate_positions_are_counted_once(self):
        result = assess_position_coverage([1, 1, 2, 2], 2)
        self.assertEqual(result["sampled_positions"], [1, 2])

    def test_a_position_beyond_the_rack_rejected(self):
        with self.assertRaises(ValueError):
            assess_position_coverage([1, 9], 4)

    def test_an_empty_sample_rejected(self):
        with self.assertRaises(ValueError):
            assess_position_coverage([], 4)

    def test_a_zero_position_rejected(self):
        with self.assertRaises(ValueError):
            assess_position_coverage([0, 1], 4)


class CouponTests(unittest.TestCase):
    def test_coupon_count_is_positions_times_runs(self):
        self.assertEqual(coupons_required(4, 3), 12)

    def test_zero_runs_rejected(self):
        with self.assertRaises(ValueError):
            coupons_required(4, 0)

    def test_a_clean_result_set_is_complete_and_passing(self):
        result = assess_coupon_results(
            {name: "pass" for name in CHARACTERISTICS}, CHARACTERISTICS
        )
        self.assertTrue(result["complete"])
        self.assertTrue(result["all_passed"])

    def test_an_unmeasured_characteristic_is_reported(self):
        result = assess_coupon_results({"coating-thickness": "pass"}, CHARACTERISTICS)
        self.assertFalse(result["complete"])
        self.assertIn("seal-quality", result["missing"])

    def test_a_failed_coupon_is_reported(self):
        results = {name: "pass" for name in CHARACTERISTICS}
        results["seal-quality"] = "fail"
        result = assess_coupon_results(results, CHARACTERISTICS)
        self.assertTrue(result["complete"])
        self.assertEqual(result["failed"], ["seal-quality"])

    def test_an_unknown_outcome_rejected(self):
        with self.assertRaises(ValueError):
            assess_coupon_results({"coating-thickness": "probably ok"}, ["coating-thickness"])

    def test_no_required_characteristics_rejected(self):
        with self.assertRaises(ValueError):
            assess_coupon_results({}, [])


class RequalificationTests(unittest.TestCase):
    def test_a_fresh_line_owes_nothing(self):
        result = requalification_required([], 30, 365)
        self.assertFalse(result["required"])
        self.assertEqual(result["reasons"], [])

    def test_elapsed_validity_triggers_a_campaign(self):
        result = requalification_required([], 365, 365)
        self.assertTrue(result["required"])

    def test_every_declared_trigger_forces_a_campaign(self):
        for change in REQUALIFICATION_TRIGGERS:
            self.assertTrue(requalification_required([change], 1, 365)["required"])

    def test_an_unknown_change_rejected(self):
        with self.assertRaises(ValueError):
            requalification_required(["new operator"], 1, 365)

    def test_a_non_sequence_change_list_rejected(self):
        with self.assertRaises(ValueError):
            requalification_required("bath-rebuild", 1, 365)

    def test_zero_validity_rejected(self):
        with self.assertRaises(ValueError):
            requalification_required([], 1, 0)


class QualifyProcessTests(unittest.TestCase):
    def test_a_sound_campaign_qualifies(self):
        result = qualify_process(GOOD_CASE)
        self.assertEqual(result["verdict"], QUALIFIED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["coupons_required"], 12)

    def test_too_few_runs_does_not_qualify(self):
        result = qualify_process(_case(runs=[dict(NOMINAL_RUN)]))
        self.assertEqual(result["verdict"], NOT_QUALIFIED)
        self.assertTrue(
            any(str(MIN_QUALIFICATION_RUNS) in f for f in result["findings"])
        )

    def test_a_parameter_excursion_does_not_qualify(self):
        runs = [dict(NOMINAL_RUN), dict(NOMINAL_RUN, dwell_minutes=90.0), dict(NOMINAL_RUN)]
        result = qualify_process(_case(runs=runs))
        self.assertEqual(result["verdict"], NOT_QUALIFIED)
        self.assertEqual(result["runs_with_excursions"], [2])

    def test_a_missing_rack_extreme_does_not_qualify(self):
        result = qualify_process(_case(positions_sampled=[2, 3]))
        self.assertEqual(result["verdict"], NOT_QUALIFIED)

    def test_a_failed_coupon_does_not_qualify(self):
        results = {name: "pass" for name in CHARACTERISTICS}
        results["coating-adhesion"] = "fail"
        result = qualify_process(_case(coupon_results=results))
        self.assertEqual(result["verdict"], NOT_QUALIFIED)

    def test_a_thin_interior_qualifies_conditionally(self):
        result = qualify_process(_case(positions_sampled=[1, 8], positions_available=8))
        self.assertEqual(result["verdict"], CONDITIONALLY_QUALIFIED)
        self.assertTrue(result["findings"])

    def test_extra_runs_are_counted(self):
        result = qualify_process(
            _case(runs=[dict(NOMINAL_RUN) for _ in range(5)])
        )
        self.assertEqual(result["runs_recorded"], 5)
        self.assertEqual(result["verdict"], QUALIFIED)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            qualify_process("the line is fine")

    def test_no_runs_rejected(self):
        with self.assertRaises(ValueError):
            qualify_process(_case(runs=[]))

    def test_a_missing_window_set_rejected(self):
        case = _case()
        del case["parameter_windows"]
        with self.assertRaises(ValueError):
            qualify_process(case)


if __name__ == "__main__":
    unittest.main()
