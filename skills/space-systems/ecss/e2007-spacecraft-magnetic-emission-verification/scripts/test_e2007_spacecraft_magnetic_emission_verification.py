"""Contract test for the spacecraft magnetic emission verification leaf."""

import unittest

from e2007_spacecraft_magnetic_emission_verification_logic import (
    FIELD_TOLERANCE_NT,
    MOMENT_COVERAGE_FACTOR,
    analysis_worst_case_am2,
    assess_magnetic_emission,
    check_budget_provenance,
    check_evidence_coverage,
    check_field_limit,
    combined_uncertainty_am2,
    far_field_flux_density_nt,
    measured_worst_case_am2,
    moment_magnitude,
    reconcile_analysis_and_test,
    validate_source,
    validate_sources,
    vector_sum_moment,
)


def source(sid="U-1", method="measured", moment=(0.05, 0.0, 0.0), **kw):
    record = {
        "id": sid,
        "method": method,
        "moment_am2": list(moment),
        "uncertainty_am2": 0.01,
    }
    record.update(kw)
    return record


def case(**kw):
    record = {
        "sources": [
            source("U-1", "measured", (0.05, 0.0, 0.0)),
            source("U-2", "analysis", (0.0, 0.05, 0.0)),
        ],
        "measured_moment_am2": 0.09,
        "measurement_uncertainty_am2": 0.004,
        "evaluation_distance_m": 1.0,
        "evaluation_angle_deg": 0.0,
        "limit_nt": 25.0,
        "analysis_complete": True,
        "test_complete": True,
    }
    record.update(kw)
    return record


class TestValidateSource(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_source({"id": "U-1", "method": "analysis",
                                "moment_am2": [0.0, 0.0, 0.0]})
        self.assertAlmostEqual(norm["uncertainty_am2"], 0.0, places=9)
        self.assertFalse(norm["compensated"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_source(["U-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_source(source(""))

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            validate_source(source("U-1", method="guessed"))

    def test_two_component_moment_raises(self):
        with self.assertRaises(ValueError):
            validate_source(source("U-1", moment=(0.1, 0.2)))

    def test_non_numeric_component_raises(self):
        with self.assertRaises(ValueError):
            validate_source(source("U-1", moment=("0.1", 0.0, 0.0)))

    def test_boolean_component_raises(self):
        with self.assertRaises(ValueError):
            validate_source(source("U-1", moment=(True, 0.0, 0.0)))

    def test_infinite_component_raises(self):
        with self.assertRaises(ValueError):
            validate_source(source("U-1", moment=(float("inf"), 0.0, 0.0)))

    def test_negative_uncertainty_raises(self):
        with self.assertRaises(ValueError):
            validate_source(source("U-1", uncertainty_am2=-0.01))

    def test_non_boolean_compensated_raises(self):
        with self.assertRaises(ValueError):
            validate_source(source("U-1", compensated="yes"))

    def test_empty_source_list_raises(self):
        with self.assertRaises(ValueError):
            validate_sources([])

    def test_non_list_sources_raises(self):
        with self.assertRaises(ValueError):
            validate_sources(source())

    def test_duplicate_source_id_raises(self):
        with self.assertRaises(ValueError):
            validate_sources([source("U-1"), source("U-1")])


class TestMomentArithmetic(unittest.TestCase):
    def test_opposing_moments_cancel_on_the_shared_axis(self):
        total = vector_sum_moment(
            [source("U-1", moment=(0.4, 0.0, 0.0)),
             source("U-2", moment=(-0.4, 0.0, 0.0))]
        )
        self.assertAlmostEqual(total[0], 0.0, places=9)

    def test_sum_keeps_each_axis_separate(self):
        total = vector_sum_moment(
            [source("U-1", moment=(0.1, 0.2, 0.3)),
             source("U-2", moment=(0.4, 0.0, -0.1))]
        )
        self.assertAlmostEqual(total[0], 0.5, places=9)
        self.assertAlmostEqual(total[1], 0.2, places=9)
        self.assertAlmostEqual(total[2], 0.2, places=9)

    def test_magnitude_of_a_right_triangle_moment(self):
        self.assertAlmostEqual(moment_magnitude((3.0, 4.0, 0.0)), 5.0, places=9)

    def test_magnitude_rejects_a_short_vector(self):
        with self.assertRaises(ValueError):
            moment_magnitude((1.0, 2.0))

    def test_uncertainties_combine_in_quadrature(self):
        rss = combined_uncertainty_am2(
            [source("U-1", uncertainty_am2=3.0), source("U-2", uncertainty_am2=4.0)]
        )
        self.assertAlmostEqual(rss, 5.0, places=9)

    def test_zero_uncertainties_give_zero(self):
        rss = combined_uncertainty_am2([source("U-1", uncertainty_am2=0.0)])
        self.assertAlmostEqual(rss, 0.0, places=9)

    def test_worst_case_expands_the_sum_by_the_coverage_factor(self):
        worst = analysis_worst_case_am2(
            [source("U-1", moment=(1.0, 0.0, 0.0), uncertainty_am2=0.5)]
        )
        self.assertAlmostEqual(
            worst, 1.0 + MOMENT_COVERAGE_FACTOR * 0.5, places=9
        )

    def test_negative_coverage_factor_raises(self):
        with self.assertRaises(ValueError):
            analysis_worst_case_am2([source("U-1")], coverage_factor=-1.0)


class TestFarFieldFluxDensity(unittest.TestCase):
    def test_on_axis_unit_moment_at_one_metre(self):
        self.assertAlmostEqual(
            far_field_flux_density_nt(1.0, 1.0, 0.0), 200.0, places=9
        )

    def test_equatorial_point_is_half_the_axial_value(self):
        self.assertAlmostEqual(
            far_field_flux_density_nt(1.0, 1.0, 90.0), 100.0, places=9
        )

    def test_doubling_the_radius_divides_the_field_by_eight(self):
        near = far_field_flux_density_nt(2.0, 1.0, 0.0)
        far = far_field_flux_density_nt(2.0, 2.0, 0.0)
        self.assertAlmostEqual(far, near / 8.0, places=9)

    def test_zero_distance_raises(self):
        with self.assertRaises(ValueError):
            far_field_flux_density_nt(1.0, 0.0, 0.0)

    def test_negative_distance_raises(self):
        with self.assertRaises(ValueError):
            far_field_flux_density_nt(1.0, -1.0, 0.0)

    def test_angle_beyond_half_turn_raises(self):
        with self.assertRaises(ValueError):
            far_field_flux_density_nt(1.0, 1.0, 181.0)

    def test_negative_moment_raises(self):
        with self.assertRaises(ValueError):
            far_field_flux_density_nt(-1.0, 1.0, 0.0)


class TestMeasuredWorstCase(unittest.TestCase):
    def test_measurement_uncertainty_is_covered(self):
        self.assertAlmostEqual(
            measured_worst_case_am2(0.1, 0.01),
            0.1 + MOMENT_COVERAGE_FACTOR * 0.01,
            places=9,
        )

    def test_zero_uncertainty_leaves_the_measurement_alone(self):
        self.assertAlmostEqual(measured_worst_case_am2(0.1, 0.0), 0.1, places=9)

    def test_negative_measurement_raises(self):
        with self.assertRaises(ValueError):
            measured_worst_case_am2(-0.1, 0.0)


class TestReconciliation(unittest.TestCase):
    def test_measurement_inside_the_analysis_worst_case_is_clean(self):
        self.assertEqual(reconcile_analysis_and_test(0.10, 0.09), [])

    def test_measurement_exactly_on_the_worst_case_is_clean(self):
        self.assertEqual(reconcile_analysis_and_test(0.10, 0.10), [])

    def test_measurement_above_the_worst_case_is_a_finding(self):
        self.assertIn(
            "measured-moment-above-the-analysis-worst-case",
            reconcile_analysis_and_test(0.10, 0.20),
        )

    def test_analysis_far_above_the_measurement_is_a_finding(self):
        self.assertIn(
            "analysis-worst-case-outside-the-reconciliation-band",
            reconcile_analysis_and_test(1.0, 0.1),
        )

    def test_analysis_at_the_reconciliation_ratio_is_clean(self):
        self.assertEqual(reconcile_analysis_and_test(0.3, 0.1), [])

    def test_a_null_measurement_against_a_positive_budget_is_a_finding(self):
        self.assertIn(
            "analysis-worst-case-outside-the-reconciliation-band",
            reconcile_analysis_and_test(0.5, 0.0),
        )


class TestEvidenceAndProvenance(unittest.TestCase):
    def test_both_legs_present_is_clean(self):
        self.assertEqual(
            check_evidence_coverage({"analysis_complete": True, "test_complete": True}),
            [],
        )

    def test_missing_analysis_leg_is_a_finding(self):
        self.assertIn(
            "steady-emission-not-covered-by-analysis",
            check_evidence_coverage({"analysis_complete": False, "test_complete": True}),
        )

    def test_missing_test_leg_is_a_finding(self):
        self.assertIn(
            "steady-emission-not-covered-by-test",
            check_evidence_coverage({"analysis_complete": True, "test_complete": False}),
        )

    def test_non_boolean_evidence_flag_raises(self):
        with self.assertRaises(ValueError):
            check_evidence_coverage({"analysis_complete": "yes", "test_complete": True})

    def test_a_measured_contributor_clears_provenance(self):
        self.assertEqual(check_budget_provenance([source("U-1", "measured")]), [])

    def test_an_all_analysis_budget_is_a_finding(self):
        self.assertIn(
            "no-contributor-moment-is-measured",
            check_budget_provenance([source("U-1", "analysis")]),
        )

    def test_a_similarity_only_budget_is_flagged_twice(self):
        findings = check_budget_provenance([source("U-1", "similarity")])
        self.assertIn("no-contributor-moment-is-measured", findings)
        self.assertIn("budget-rests-on-similarity-only", findings)


class TestFieldLimit(unittest.TestCase):
    def test_field_under_the_limit_is_clean(self):
        self.assertEqual(check_field_limit(10.0, 25.0), [])

    def test_field_exactly_on_the_limit_is_clean(self):
        self.assertEqual(check_field_limit(25.0, 25.0), [])

    def test_field_within_the_named_tolerance_is_clean(self):
        self.assertEqual(check_field_limit(25.0 + FIELD_TOLERANCE_NT / 2.0, 25.0), [])

    def test_field_above_the_limit_is_a_finding(self):
        self.assertEqual(
            check_field_limit(30.0, 25.0),
            ["steady-magnetic-emission-above-the-vehicle-limit"],
        )

    def test_non_positive_limit_raises(self):
        with self.assertRaises(ValueError):
            check_field_limit(10.0, 0.0)


class TestAssessMagneticEmission(unittest.TestCase):
    def test_a_reconciled_compliant_vehicle_has_no_findings(self):
        report = assess_magnetic_emission(case())
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["compliant"])

    def test_the_governing_moment_is_the_larger_of_the_two_legs(self):
        report = assess_magnetic_emission(case())
        self.assertAlmostEqual(
            report["governing_moment_am2"],
            max(report["analysis_worst_case_am2"], report["measured_worst_case_am2"]),
            places=9,
        )

    def test_a_tight_limit_turns_the_vehicle_non_compliant(self):
        report = assess_magnetic_emission(case(limit_nt=5.0))
        self.assertIn(
            "steady-magnetic-emission-above-the-vehicle-limit", report["findings"]
        )
        self.assertFalse(report["compliant"])

    def test_a_missing_system_measurement_is_a_finding(self):
        report = assess_magnetic_emission(case(measured_moment_am2=None))
        self.assertIn("no-measured-system-moment-on-record", report["findings"])
        self.assertIsNone(report["measured_worst_case_am2"])

    def test_a_measurement_above_the_budget_is_reported(self):
        report = assess_magnetic_emission(case(measured_moment_am2=0.5, limit_nt=400.0))
        self.assertIn(
            "measured-moment-above-the-analysis-worst-case", report["findings"]
        )

    def test_the_field_follows_the_evaluation_geometry(self):
        near = assess_magnetic_emission(case(limit_nt=400.0))
        far = assess_magnetic_emission(
            case(evaluation_distance_m=2.0, limit_nt=400.0)
        )
        self.assertAlmostEqual(far["field_nt"], near["field_nt"] / 8.0, places=9)

    def test_cancelling_units_shrink_the_summed_moment(self):
        report = assess_magnetic_emission(
            case(
                sources=[
                    source("U-1", "measured", (0.4, 0.0, 0.0)),
                    source("U-2", "measured", (-0.4, 0.0, 0.0)),
                ],
                measured_moment_am2=0.04,
                limit_nt=400.0,
            )
        )
        self.assertAlmostEqual(report["summed_magnitude_am2"], 0.0, places=9)

    def test_a_non_mapping_case_raises(self):
        with self.assertRaises(ValueError):
            assess_magnetic_emission([])

    def test_a_missing_distance_raises(self):
        with self.assertRaises(ValueError):
            assess_magnetic_emission(case(evaluation_distance_m=None))


if __name__ == "__main__":
    unittest.main()
