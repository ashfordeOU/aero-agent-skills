#!/usr/bin/env python3
"""Contract tests for the clause 7.5.11 contact surface finish logic (offline)."""

import copy
import unittest

from e2008_cell_surface_finish_test_logic import (
    ANOMALY_KINDS,
    ANOMALY_SEVERITY_WEIGHTS,
    DEFAULT_FINISH_POLICY,
    EXAMINATION_INADEQUATE,
    FINISH_ACCEPTED,
    FINISH_GRADES,
    FINISH_REJECTED,
    GRADE_COMPLIANT,
    GRADE_MARGINAL,
    GRADE_NON_COMPLIANT,
    anomaly_area_fraction,
    anomaly_severity_weight,
    assess_contact_surface_finish,
    demerit_score,
    finish_grade,
    largest_single_anomaly_mm2,
    normalise_anomalies,
    roughness_consistency,
    total_anomaly_area_mm2,
    trace_adequacy,
    validate_finish_policy,
)

CLEAN_ANOMALIES = [{"kind": "discoloration", "count": 2, "single_area_mm2": 0.004}]

ONE_LARGE_VOID = [{"kind": "void", "count": 1, "single_area_mm2": 0.090}]

MANY_SEVERE = [{"kind": "flaking", "count": 3, "single_area_mm2": 0.001}]

NOTHING_FOUND = [
    {"kind": "pit", "count": 0, "single_area_mm2": 0.0},
    {"kind": "scratch", "count": 0},
]


def _case(**overrides):
    case = {
        "contact_identifier": "coupon-14-front-bus-bar",
        "inspected_area_mm2": 120.0,
        "trace_length_mm": 8.0,
        "roughness_ra_um": 0.35,
        "roughness_rz_um": 2.10,
        "anomalies": copy.deepcopy(CLEAN_ANOMALIES),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_normalises(self):
        limits = validate_finish_policy()
        self.assertAlmostEqual(limits["maximum_roughness_ra_um"], 1.2, places=9)
        self.assertAlmostEqual(limits["marginal_band_fraction"], 0.80, places=9)

    def test_an_unknown_policy_key_is_refused(self):
        with self.assertRaises(ValueError):
            validate_finish_policy({"maximum_thickness_um": 9.0})

    def test_a_peak_limit_below_the_mean_limit_is_refused(self):
        with self.assertRaises(ValueError):
            validate_finish_policy(
                {"maximum_roughness_ra_um": 4.0, "maximum_roughness_rz_um": 2.0}
            )

    def test_a_ratio_floor_below_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_finish_policy({"minimum_rz_to_ra_ratio": 0.5})

    def test_an_area_fraction_limit_above_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_finish_policy({"maximum_anomaly_area_fraction": 1.4})

    def test_a_non_mapping_policy_is_refused(self):
        with self.assertRaises(ValueError):
            validate_finish_policy("default")


class AnomalyValidationTests(unittest.TestCase):
    def test_every_known_kind_carries_a_weight(self):
        for kind in ANOMALY_KINDS:
            self.assertIn(kind, ANOMALY_SEVERITY_WEIGHTS)
            self.assertGreaterEqual(anomaly_severity_weight(kind), 1)

    def test_a_flake_outweighs_a_stain(self):
        self.assertGreater(
            anomaly_severity_weight("flaking"), anomaly_severity_weight("staining")
        )

    def test_an_unknown_anomaly_kind_is_refused(self):
        with self.assertRaises(ValueError):
            anomaly_severity_weight("delamination")

    def test_a_repeated_anomaly_kind_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_anomalies(
                [
                    {"kind": "pit", "count": 1, "single_area_mm2": 0.01},
                    {"kind": "pit", "count": 2, "single_area_mm2": 0.02},
                ]
            )

    def test_a_counted_anomaly_needs_an_area(self):
        with self.assertRaises(ValueError):
            normalise_anomalies([{"kind": "pit", "count": 2}])

    def test_a_negative_count_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_anomalies(
                [{"kind": "pit", "count": -1, "single_area_mm2": 0.01}]
            )

    def test_a_fractional_count_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_anomalies(
                [{"kind": "pit", "count": 1.5, "single_area_mm2": 0.01}]
            )

    def test_an_observation_that_found_nothing_is_kept(self):
        anomalies = normalise_anomalies(NOTHING_FOUND)
        self.assertEqual(len(anomalies), 2)
        self.assertAlmostEqual(total_anomaly_area_mm2(anomalies), 0.0, places=9)

    def test_no_anomaly_record_at_all_is_accepted(self):
        self.assertEqual(normalise_anomalies(None), ())
        self.assertAlmostEqual(demerit_score(None), 0.0, places=9)


class AnomalyReductionTests(unittest.TestCase):
    def test_total_area_multiplies_count_by_size(self):
        self.assertAlmostEqual(
            total_anomaly_area_mm2(CLEAN_ANOMALIES), 0.008, places=9
        )

    def test_the_largest_single_anomaly_is_reported(self):
        anomalies = [
            {"kind": "pit", "count": 4, "single_area_mm2": 0.010},
            {"kind": "void", "count": 1, "single_area_mm2": 0.030},
        ]
        self.assertAlmostEqual(
            largest_single_anomaly_mm2(anomalies), 0.030, places=9
        )

    def test_an_uncounted_kind_does_not_become_the_largest(self):
        anomalies = [
            {"kind": "pit", "count": 2, "single_area_mm2": 0.010},
            {"kind": "void", "count": 0, "single_area_mm2": 0.090},
        ]
        self.assertAlmostEqual(
            largest_single_anomaly_mm2(anomalies), 0.010, places=9
        )

    def test_a_clean_surface_has_no_largest_anomaly(self):
        self.assertAlmostEqual(largest_single_anomaly_mm2(None), 0.0, places=9)

    def test_the_demerit_score_weights_by_severity(self):
        self.assertAlmostEqual(demerit_score(MANY_SEVERE), 15.0, places=9)
        self.assertAlmostEqual(demerit_score(CLEAN_ANOMALIES), 2.0, places=9)

    def test_the_area_fraction_is_taken_over_the_inspected_area(self):
        self.assertAlmostEqual(
            anomaly_area_fraction(CLEAN_ANOMALIES, 80.0), 0.0001, places=9
        )

    def test_anomaly_area_beyond_the_inspected_area_is_refused(self):
        with self.assertRaises(ValueError):
            anomaly_area_fraction(
                [{"kind": "pit", "count": 10, "single_area_mm2": 1.0}], 4.0
            )

    def test_a_zero_inspected_area_is_refused(self):
        with self.assertRaises(ValueError):
            anomaly_area_fraction(CLEAN_ANOMALIES, 0.0)


class TraceTests(unittest.TestCase):
    def test_a_consistent_trace_returns_its_ratio(self):
        profile = roughness_consistency(0.35, 2.10)
        self.assertAlmostEqual(profile["rz_to_ra_ratio"], 6.0, places=9)

    def test_a_peak_height_below_the_mean_deviation_is_refused(self):
        with self.assertRaises(ValueError):
            roughness_consistency(2.0, 1.0)

    def test_a_zero_roughness_is_refused(self):
        with self.assertRaises(ValueError):
            roughness_consistency(0.0, 2.0)

    def test_a_long_consistent_trace_is_adequate(self):
        trace = trace_adequacy(8.0, 0.35, 2.10)
        self.assertTrue(trace["adequate"])
        self.assertEqual(trace["findings"], [])

    def test_a_short_trace_is_inadequate(self):
        trace = trace_adequacy(2.0, 0.35, 2.10)
        self.assertFalse(trace["adequate"])
        self.assertTrue(
            any("profile trace is" in finding for finding in trace["findings"])
        )

    def test_a_trace_on_the_length_floor_is_adequate(self):
        trace = trace_adequacy(4.0, 0.35, 2.10)
        self.assertAlmostEqual(
            trace["trace_length_mm"],
            DEFAULT_FINISH_POLICY["minimum_trace_length_mm"],
            places=9,
        )
        self.assertTrue(trace["adequate"])

    def test_a_flat_looking_trace_is_not_believed(self):
        trace = trace_adequacy(8.0, 0.50, 1.20)
        self.assertFalse(trace["adequate"])
        self.assertTrue(
            any("real contact surface" in finding for finding in trace["findings"])
        )


class GradeTests(unittest.TestCase):
    def test_low_utilisation_grades_compliant(self):
        self.assertEqual(finish_grade({"roughness_ra": 0.3}), GRADE_COMPLIANT)

    def test_utilisation_in_the_marginal_band_grades_marginal(self):
        self.assertEqual(finish_grade({"roughness_ra": 0.9}), GRADE_MARGINAL)

    def test_utilisation_on_the_marginal_edge_grades_marginal(self):
        self.assertEqual(finish_grade({"roughness_ra": 0.80}), GRADE_MARGINAL)

    def test_utilisation_on_the_limit_is_still_inside_it(self):
        self.assertEqual(finish_grade({"roughness_ra": 1.0}), GRADE_MARGINAL)

    def test_utilisation_beyond_the_limit_grades_non_compliant(self):
        self.assertEqual(finish_grade({"roughness_ra": 1.05}), GRADE_NON_COMPLIANT)

    def test_one_bad_measure_carries_the_grade(self):
        grade = finish_grade({"roughness_ra": 0.1, "demerit_score": 2.0})
        self.assertEqual(grade, GRADE_NON_COMPLIANT)

    def test_an_empty_utilisation_set_is_refused(self):
        with self.assertRaises(ValueError):
            finish_grade({})

    def test_every_grade_is_a_declared_grade(self):
        for value in (0.1, 0.85, 1.0, 2.0):
            self.assertIn(finish_grade({"roughness_ra": value}), FINISH_GRADES)


class FinishAssessmentTests(unittest.TestCase):
    def test_a_clean_contact_is_accepted(self):
        result = assess_contact_surface_finish(_case())
        self.assertEqual(result["verdict"], FINISH_ACCEPTED)
        self.assertEqual(result["finish_grade"], GRADE_COMPLIANT)
        self.assertEqual(result["findings"], [])

    def test_a_rough_contact_is_rejected(self):
        result = assess_contact_surface_finish(
            _case(roughness_ra_um=1.50, roughness_rz_um=6.00)
        )
        self.assertEqual(result["verdict"], FINISH_REJECTED)
        self.assertTrue(
            any("mean deviation" in finding for finding in result["findings"])
        )

    def test_one_large_void_is_rejected_on_its_own(self):
        result = assess_contact_surface_finish(_case(anomalies=ONE_LARGE_VOID))
        self.assertEqual(result["verdict"], FINISH_REJECTED)
        self.assertTrue(
            any("largest anomaly" in finding for finding in result["findings"])
        )

    def test_a_small_severe_population_is_caught_by_the_demerit_score(self):
        result = assess_contact_surface_finish(_case(anomalies=MANY_SEVERE))
        self.assertEqual(result["verdict"], FINISH_REJECTED)
        self.assertAlmostEqual(result["demerit_score"], 15.0, places=9)
        self.assertTrue(
            any("demerit score" in finding for finding in result["findings"])
        )
        self.assertLess(result["limit_utilisation"]["anomaly_area_fraction"], 0.1)

    def test_many_small_faults_are_caught_by_the_area_fraction(self):
        result = assess_contact_surface_finish(
            _case(
                inspected_area_mm2=20.0,
                anomalies=[
                    {"kind": "discoloration", "count": 5, "single_area_mm2": 0.045}
                ],
            )
        )
        self.assertEqual(result["verdict"], FINISH_REJECTED)
        self.assertTrue(
            any("of the contact" in finding for finding in result["findings"])
        )

    def test_a_marginal_finish_is_accepted_and_named(self):
        result = assess_contact_surface_finish(
            _case(roughness_ra_um=1.00, roughness_rz_um=5.00)
        )
        self.assertEqual(result["verdict"], FINISH_ACCEPTED)
        self.assertEqual(result["finish_grade"], GRADE_MARGINAL)
        self.assertTrue(
            any("marginal" in finding for finding in result["findings"])
        )

    def test_an_inadequate_trace_is_neither_an_acceptance_nor_a_rejection(self):
        result = assess_contact_surface_finish(_case(trace_length_mm=1.5))
        self.assertEqual(result["verdict"], EXAMINATION_INADEQUATE)
        self.assertFalse(result["accepted"])

    def test_an_inadequate_trace_outranks_a_bad_anomaly_population(self):
        result = assess_contact_surface_finish(
            _case(trace_length_mm=1.5, anomalies=ONE_LARGE_VOID)
        )
        self.assertEqual(result["verdict"], EXAMINATION_INADEQUATE)

    def test_the_kinds_actually_found_are_listed(self):
        result = assess_contact_surface_finish(_case(anomalies=NOTHING_FOUND))
        self.assertEqual(result["anomaly_kinds_found"], ())
        self.assertAlmostEqual(result["demerit_score"], 0.0, places=9)

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_contact_surface_finish("coupon-14")

    def test_a_case_without_an_inspected_area_is_refused(self):
        case = _case()
        del case["inspected_area_mm2"]
        with self.assertRaises(ValueError):
            assess_contact_surface_finish(case)

    def test_a_tighter_policy_travels_with_the_case(self):
        result = assess_contact_surface_finish(
            _case(policy={"maximum_roughness_ra_um": 0.30})
        )
        self.assertEqual(result["verdict"], FINISH_REJECTED)

    def test_the_default_policy_is_not_mutated_by_a_case_policy(self):
        assess_contact_surface_finish(_case(policy={"maximum_demerit_score": 1.0}))
        self.assertAlmostEqual(
            DEFAULT_FINISH_POLICY["maximum_demerit_score"], 10.0, places=9
        )

    def test_every_limit_is_reported_as_a_utilisation(self):
        result = assess_contact_surface_finish(_case())
        for name in (
            "roughness_ra",
            "roughness_rz",
            "largest_anomaly",
            "anomaly_area_fraction",
            "demerit_score",
        ):
            self.assertIn(name, result["limit_utilisation"])



class WorkflowOrderTests(unittest.TestCase):
    """The examination runs as ordered steps and the trace gate is first.

    A trace that cannot carry a roughness figure must stop the workflow
    before the surface is graded, and the grade itself is taken from the
    worst share of any single limit rather than from an average of them.
    """

    def test_the_trace_gate_stops_a_surface_that_would_also_be_rejected(self):
        result = assess_contact_surface_finish(
            _case(trace_length_mm=1.5, anomalies=MANY_SEVERE)
        )
        self.assertEqual(result["verdict"], EXAMINATION_INADEQUATE)
        self.assertAlmostEqual(result["demerit_score"], 15.0, places=9)

    def test_the_grading_step_takes_the_worst_share_not_the_average(self):
        grade = finish_grade(
            {"roughness_ra": 0.05, "roughness_rz": 0.05, "demerit_score": 1.4}
        )
        self.assertEqual(grade, GRADE_NON_COMPLIANT)

    def test_every_step_of_the_workflow_reports_its_own_section(self):
        result = assess_contact_surface_finish(_case())
        for section in (
            "trace",
            "anomalies",
            "anomaly_area_fraction",
            "demerit_score",
            "limit_utilisation",
            "finish_grade",
            "verdict",
        ):
            self.assertIn(section, result)


if __name__ == "__main__":
    unittest.main()
