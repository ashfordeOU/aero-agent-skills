"""Contract tests for the clause 10.2 pre-dicing wafer screening flow."""

import unittest

from q6012_wafer_screening_and_acceptance_testing_logic import (
    DRIFT_TOLERANCE,
    MEASUREMENT_ACTIVITIES,
    POST_DICING_ONLY_ACTIVITIES,
    STRESS_ACTIVITIES,
    assess_wafer_screening,
    failing_fraction,
    grade_sites,
    normalise_activity,
    parameter_drift,
    site_verdict,
    stress_bracketing,
    validate_flow,
    within_drift_limit,
)

GOOD_FLOW = [
    "wafer_visual_inspection",
    "initial_parametric_measurement",
    "wafer_level_stress_burn_in",
    "final_parametric_measurement",
    "wafer_acceptance_review",
]

LIMITS = {"idss": 0.10, "gain_db": 0.05}


def site(site_id, idss_post=1.02, gain_post=1.01):
    return {
        "site_id": site_id,
        "pre": {"idss": 1.0, "gain_db": 1.0},
        "post": {"idss": idss_post, "gain_db": gain_post},
    }


def good_case(**overrides):
    case = {
        "activities": list(GOOD_FLOW),
        "sites": [site("s1"), site("s2"), site("s3"), site("s4")],
        "drift_limits": dict(LIMITS),
        "percent_defective_allowed": 0.25,
    }
    case.update(overrides)
    return case


class NormaliseActivityTests(unittest.TestCase):
    def test_spelling_is_folded(self):
        self.assertEqual(normalise_activity("Wafer-Visual Inspection"),
                         "wafer_visual_inspection")

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            normalise_activity("coffee_break")

    def test_blank_activity_rejected(self):
        with self.assertRaises(ValueError):
            normalise_activity("   ")

    def test_non_string_activity_rejected(self):
        with self.assertRaises(ValueError):
            normalise_activity(4)


class ValidateFlowTests(unittest.TestCase):
    def test_good_flow_has_nothing_misplaced(self):
        result = validate_flow(GOOD_FLOW)
        self.assertEqual(result["misplaced_activities"], ())
        self.assertEqual(len(result["flow"]), len(GOOD_FLOW))

    def test_die_level_activity_is_reported_misplaced(self):
        flow = GOOD_FLOW + ["die_shear_test"]
        self.assertEqual(validate_flow(flow)["misplaced_activities"], ("die_shear_test",))

    def test_repeated_activity_rejected(self):
        with self.assertRaises(ValueError):
            validate_flow(GOOD_FLOW + ["wafer_visual_inspection"])

    def test_empty_flow_rejected(self):
        with self.assertRaises(ValueError):
            validate_flow([])

    def test_die_level_set_is_disjoint_from_the_measurements(self):
        self.assertEqual(
            set(POST_DICING_ONLY_ACTIVITIES) & set(MEASUREMENT_ACTIVITIES), set()
        )


class BracketingTests(unittest.TestCase):
    def test_bracketed_stress_is_clean(self):
        self.assertEqual(stress_bracketing(validate_flow(GOOD_FLOW)["flow"]), ())

    def test_stress_with_no_measurement_after_is_reported(self):
        flow = ["initial_parametric_measurement", "wafer_level_stress_burn_in"]
        self.assertEqual(
            stress_bracketing(validate_flow(flow)["flow"]),
            ("wafer_level_stress_burn_in",),
        )

    def test_stress_with_no_measurement_before_is_reported(self):
        flow = ["high_temperature_storage", "final_parametric_measurement"]
        self.assertEqual(
            stress_bracketing(validate_flow(flow)["flow"]),
            ("high_temperature_storage",),
        )

    def test_a_flow_without_stress_reports_nothing_unbracketed(self):
        flow = ["initial_parametric_measurement", "final_parametric_measurement"]
        self.assertEqual(stress_bracketing(validate_flow(flow)["flow"]), ())

    def test_both_stress_activities_are_recognised(self):
        self.assertEqual(len(STRESS_ACTIVITIES), 2)


class DriftTests(unittest.TestCase):
    def test_rise_gives_a_positive_drift(self):
        self.assertAlmostEqual(parameter_drift(1.0, 1.25), 0.25, places=9)

    def test_fall_gives_a_negative_drift(self):
        self.assertAlmostEqual(parameter_drift(2.0, 1.5), -0.25, places=9)

    def test_no_change_gives_zero_drift(self):
        self.assertAlmostEqual(parameter_drift(4.0, 4.0), 0.0, places=9)

    def test_zero_pre_reading_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift(0.0, 1.0)

    def test_non_finite_reading_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift(1.0, float("nan"))

    def test_boolean_reading_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift(True, 1.0)

    def test_drift_exactly_on_the_limit_is_inside_it(self):
        self.assertTrue(within_drift_limit(0.05, 0.05))

    def test_drift_just_past_the_limit_is_outside_it(self):
        self.assertFalse(within_drift_limit(0.06, 0.05))

    def test_negative_drift_is_judged_on_magnitude(self):
        self.assertFalse(within_drift_limit(-0.06, 0.05))

    def test_negative_limit_rejected(self):
        with self.assertRaises(ValueError):
            within_drift_limit(0.01, -0.05)

    def test_tolerance_is_small_enough_to_be_a_boundary_allowance(self):
        self.assertAlmostEqual(DRIFT_TOLERANCE, 1e-9, places=12)


class SiteGradingTests(unittest.TestCase):
    def test_clean_site_passes(self):
        record = site_verdict(site("s1"), LIMITS)
        self.assertTrue(record["passing"])
        self.assertEqual(record["breached_parameters"], ())

    def test_site_breaching_one_parameter_fails(self):
        record = site_verdict(site("s1", gain_post=1.20), LIMITS)
        self.assertFalse(record["passing"])
        self.assertEqual(record["breached_parameters"], ("gain_db",))

    def test_site_missing_a_reading_pair_fails(self):
        bad = site("s1")
        del bad["post"]["idss"]
        record = site_verdict(bad, LIMITS)
        self.assertEqual(record["unmeasured_parameters"], ("idss",))
        self.assertFalse(record["passing"])

    def test_site_without_readings_rejected(self):
        with self.assertRaises(ValueError):
            site_verdict({"site_id": "s1", "pre": {"idss": 1.0}}, LIMITS)

    def test_empty_limit_set_rejected(self):
        with self.assertRaises(ValueError):
            site_verdict(site("s1"), {})

    def test_repeated_site_identifier_rejected(self):
        with self.assertRaises(ValueError):
            grade_sites([site("s1"), site("s1")], LIMITS)

    def test_grading_groups_the_sites(self):
        grading = grade_sites([site("s1"), site("s2", gain_post=1.4)], LIMITS)
        self.assertEqual(grading["passing_sites"], ("s1",))
        self.assertEqual(grading["failing_sites"], ("s2",))

    def test_empty_site_list_rejected(self):
        with self.assertRaises(ValueError):
            grade_sites([], LIMITS)


class FailingFractionTests(unittest.TestCase):
    def test_quarter_of_the_sites(self):
        self.assertAlmostEqual(failing_fraction(1, 4), 0.25, places=9)

    def test_no_failures_is_zero(self):
        self.assertAlmostEqual(failing_fraction(0, 8), 0.0, places=9)

    def test_more_failures_than_sites_rejected(self):
        with self.assertRaises(ValueError):
            failing_fraction(5, 4)

    def test_zero_sites_rejected(self):
        with self.assertRaises(ValueError):
            failing_fraction(0, 0)

    def test_non_integer_count_rejected(self):
        with self.assertRaises(ValueError):
            failing_fraction(1.0, 4)


class AssessmentTests(unittest.TestCase):
    def test_clean_case_is_accepted(self):
        result = assess_wafer_screening(good_case())
        self.assertEqual(result["verdict"], "accepted")
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["failing_fraction"], 0.0, places=9)

    def test_failing_fraction_exactly_on_the_allowance_is_accepted(self):
        case = good_case()
        case["sites"] = [site("s1"), site("s2"), site("s3"), site("s4", gain_post=1.4)]
        result = assess_wafer_screening(case)
        self.assertAlmostEqual(result["failing_fraction"], 0.25, places=9)
        self.assertTrue(result["within_percent_defective_allowed"])
        self.assertEqual(result["verdict"], "accepted")

    def test_failing_fraction_past_the_allowance_is_rejected(self):
        case = good_case()
        case["sites"] = [site("s1"), site("s2"), site("s3", gain_post=1.4),
                         site("s4", gain_post=1.4)]
        result = assess_wafer_screening(case)
        self.assertAlmostEqual(result["failing_fraction"], 0.5, places=9)
        self.assertEqual(result["verdict"], "rejected")

    def test_die_level_activity_invalidates_the_flow(self):
        case = good_case()
        case["activities"] = GOOD_FLOW + ["wire_bond_pull_test"]
        self.assertEqual(assess_wafer_screening(case)["verdict"], "flow-invalid")

    def test_unbracketed_stress_invalidates_the_flow(self):
        case = good_case()
        case["activities"] = ["initial_parametric_measurement",
                              "wafer_level_stress_burn_in"]
        result = assess_wafer_screening(case)
        self.assertEqual(result["verdict"], "flow-invalid")
        self.assertEqual(result["unbracketed_stress"], ("wafer_level_stress_burn_in",))

    def test_a_flow_with_no_stress_is_reported(self):
        case = good_case()
        case["activities"] = ["initial_parametric_measurement",
                              "final_parametric_measurement"]
        result = assess_wafer_screening(case)
        self.assertTrue(any("no wafer level stress" in f for f in result["findings"]))

    def test_allowance_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_wafer_screening(good_case(percent_defective_allowed=1.5))

    def test_missing_drift_limits_rejected(self):
        case = good_case()
        del case["drift_limits"]
        with self.assertRaises(ValueError):
            assess_wafer_screening(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_wafer_screening(["activities"])


if __name__ == "__main__":
    unittest.main()
