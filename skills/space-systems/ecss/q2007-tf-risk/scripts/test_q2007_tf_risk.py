#!/usr/bin/env python3
"""Contract tests for facility hazard and risk assessment, clause 5.6.5.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused policy,
no hazards identified, an index outside its scale, a band table read at
its thresholds, a planned mitigation credited with nothing, a reduction
clamped at the floor of its scale, an unacceptable residual outranking
an unaccepted one, and category coverage short of what the facility
operates.
"""

import unittest

from q2007_tf_risk_logic import (
    ACCEPTANCE_AUTHORITY_MISSING,
    BAND_ACCEPTABLE,
    BAND_UNACCEPTABLE,
    BAND_UNDESIRABLE,
    CATEGORY_COVERAGE_SHORT,
    DEFAULT_RISK_POLICY,
    HAZARDS_NOT_IDENTIFIED,
    RESIDUAL_RISK_ACCEPTED,
    RESIDUAL_UNACCEPTABLE,
    RISK_REDUCTION_OUTSTANDING,
    SAFETY_CASE_STALE,
    assess_facility_risk,
    category_coverage,
    initial_index,
    planned_mitigations,
    residual_index,
    residual_indices,
    risk_band,
    safety_case_is_current,
    uncovered_categories,
    validate_hazard,
    validate_hazards,
    validate_mitigation,
    validate_risk_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_RISK_POLICY)
    policy.update(overrides)
    return policy


def _hazards():
    return [
        {
            "hazard_id": "pressure-vessel-burst",
            "category": "pressure",
            "severity": 5,
            "likelihood": 3,
            "mitigations": [
                {
                    "mitigation_id": "burst-disc-and-relief-path",
                    "target": "likelihood",
                    "steps": 2,
                    "implemented": True,
                }
            ],
        },
        {
            "hazard_id": "high-voltage-contact",
            "category": "energised-systems",
            "severity": 4,
            "likelihood": 2,
            "mitigations": [
                {
                    "mitigation_id": "cabinet-interlock",
                    "target": "likelihood",
                    "steps": 1,
                    "implemented": True,
                }
            ],
        },
        {
            "hazard_id": "crane-load-drop",
            "category": "lifting",
            "severity": 3,
            "likelihood": 2,
            "mitigations": [],
            "accepted_by": "test-centre-safety-authority",
        },
    ]


def _assessment(**overrides):
    assessment = {
        "hazards": _hazards(),
        "required_categories": ["pressure", "energised-systems", "lifting"],
        "assessed_day": 400,
        "last_modification_day": 350,
        "as_of_day": 500,
    }
    assessment.update(overrides)
    return assessment


def _case(**overrides):
    case = {"policy": _policy(), "assessment": _assessment()}
    case.update(overrides)
    return case


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_usable(self):
        self.assertIs(validate_risk_policy(DEFAULT_RISK_POLICY), DEFAULT_RISK_POLICY)

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_risk_policy("five by five")

    def test_a_collapsed_severity_scale_refused(self):
        with self.assertRaises(ValueError):
            validate_risk_policy(_policy(severity_max=1))

    def test_band_thresholds_that_do_not_ascend_refused(self):
        with self.assertRaises(ValueError):
            validate_risk_policy(_policy(unacceptable_threshold=4))

    def test_a_zero_acceptance_line_refused(self):
        with self.assertRaises(ValueError):
            validate_risk_policy(_policy(acceptance_line=0))

    def test_a_coverage_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_risk_policy(_policy(min_category_coverage=1.1))


class BandTests(unittest.TestCase):
    def test_an_index_below_the_first_threshold_is_acceptable(self):
        self.assertEqual(risk_band(5), BAND_ACCEPTABLE)

    def test_an_index_on_the_first_threshold_is_undesirable(self):
        self.assertEqual(risk_band(6), BAND_UNDESIRABLE)

    def test_an_index_just_below_the_second_threshold_is_undesirable(self):
        self.assertEqual(risk_band(14), BAND_UNDESIRABLE)

    def test_an_index_on_the_second_threshold_is_unacceptable(self):
        self.assertEqual(risk_band(15), BAND_UNACCEPTABLE)

    def test_the_top_of_the_matrix_is_unacceptable(self):
        self.assertEqual(risk_band(25), BAND_UNACCEPTABLE)


class HazardValidationTests(unittest.TestCase):
    def test_hazard_is_read_back(self):
        record = validate_hazard(_hazards()[0])
        self.assertEqual(record["category"], "pressure")
        self.assertEqual(len(record["mitigations"]), 1)

    def test_a_severity_above_the_scale_refused(self):
        hazard = _hazards()[0]
        hazard["severity"] = 9
        with self.assertRaises(ValueError):
            validate_hazard(hazard)

    def test_a_likelihood_below_the_scale_refused(self):
        hazard = _hazards()[0]
        hazard["likelihood"] = 0
        with self.assertRaises(ValueError):
            validate_hazard(hazard)

    def test_a_blank_category_refused(self):
        hazard = _hazards()[0]
        hazard["category"] = "  "
        with self.assertRaises(ValueError):
            validate_hazard(hazard)

    def test_mitigations_that_are_not_a_sequence_refused(self):
        hazard = _hazards()[0]
        hazard["mitigations"] = "interlock"
        with self.assertRaises(ValueError):
            validate_hazard(hazard)

    def test_the_same_hazard_twice_refused(self):
        with self.assertRaises(ValueError):
            validate_hazards(_hazards() + [_hazards()[0]])

    def test_an_empty_hazard_list_refused(self):
        with self.assertRaises(ValueError):
            validate_hazards([])


class MitigationTests(unittest.TestCase):
    def test_mitigation_is_read_back(self):
        record = validate_mitigation(_hazards()[0]["mitigations"][0])
        self.assertEqual(record["target"], "likelihood")
        self.assertEqual(record["steps"], 2)

    def test_a_mitigation_moving_neither_index_refused(self):
        mitigation = _hazards()[0]["mitigations"][0]
        mitigation["target"] = "cost"
        with self.assertRaises(ValueError):
            validate_mitigation(mitigation)

    def test_a_zero_step_mitigation_refused(self):
        mitigation = _hazards()[0]["mitigations"][0]
        mitigation["steps"] = 0
        with self.assertRaises(ValueError):
            validate_mitigation(mitigation)

    def test_a_non_boolean_implemented_flag_refused(self):
        mitigation = _hazards()[0]["mitigations"][0]
        mitigation["implemented"] = "soon"
        with self.assertRaises(ValueError):
            validate_mitigation(mitigation)


class ResidualTests(unittest.TestCase):
    def test_the_initial_index_ignores_every_mitigation(self):
        self.assertEqual(initial_index(_hazards()[0]), 15)

    def test_an_implemented_mitigation_is_credited(self):
        severity, likelihood = residual_indices(_hazards()[0])
        self.assertEqual(severity, 5)
        self.assertEqual(likelihood, 1)
        self.assertEqual(residual_index(_hazards()[0]), 5)

    def test_a_planned_mitigation_is_credited_with_nothing(self):
        hazard = _hazards()[0]
        hazard["mitigations"][0]["implemented"] = False
        self.assertEqual(residual_index(hazard), 15)

    def test_a_reduction_is_clamped_at_the_floor_of_its_scale(self):
        hazard = _hazards()[1]
        hazard["mitigations"][0]["steps"] = 4
        severity, likelihood = residual_indices(hazard)
        self.assertEqual(likelihood, 1)
        self.assertEqual(severity, 4)

    def test_a_severity_mitigation_moves_severity_not_likelihood(self):
        hazard = _hazards()[1]
        hazard["mitigations"][0]["target"] = "severity"
        severity, likelihood = residual_indices(hazard)
        self.assertEqual(severity, 3)
        self.assertEqual(likelihood, 2)

    def test_planned_mitigations_are_named(self):
        hazard = _hazards()[1]
        hazard["mitigations"][0]["implemented"] = False
        self.assertEqual(planned_mitigations(hazard), ("cabinet-interlock",))


class CoverageTests(unittest.TestCase):
    def test_every_operated_category_assessed_is_full_coverage(self):
        self.assertAlmostEqual(
            category_coverage(
                _hazards(), ["pressure", "energised-systems", "lifting"]
            ),
            1.0,
            places=9,
        )

    def test_an_unassessed_category_stays_in_the_denominator(self):
        required = ["pressure", "energised-systems", "lifting", "hazardous-fluids"]
        self.assertAlmostEqual(
            category_coverage(_hazards(), required), 0.75, places=9
        )
        self.assertEqual(
            uncovered_categories(_hazards(), required), ("hazardous-fluids",)
        )

    def test_a_facility_declaring_no_categories_refused(self):
        with self.assertRaises(ValueError):
            category_coverage(_hazards(), [])


class CurrencyTests(unittest.TestCase):
    def test_an_assessment_inside_its_interval_is_current(self):
        self.assertTrue(safety_case_is_current(400, 500, 350))

    def test_an_assessment_past_its_review_interval_is_not(self):
        self.assertFalse(safety_case_is_current(100, 500, 50))

    def test_an_assessment_predating_the_last_modification_is_not(self):
        self.assertFalse(safety_case_is_current(400, 500, 450))

    def test_no_assessment_date_at_all_is_not_current(self):
        self.assertFalse(safety_case_is_current(None, 500))

    def test_an_assessment_dated_after_today_refused(self):
        with self.assertRaises(ValueError):
            safety_case_is_current(600, 500)


class AssessmentTests(unittest.TestCase):
    def test_a_mitigated_and_accepted_facility_passes(self):
        result = assess_facility_risk(_case())
        self.assertEqual(result["verdict"], RESIDUAL_RISK_ACCEPTED)
        self.assertEqual(result["hazards_assessed"], 3)
        self.assertAlmostEqual(result["category_coverage"], 1.0, places=9)

    def test_no_assessment_at_all_stops_the_work(self):
        result = assess_facility_risk(_case(assessment=None))
        self.assertEqual(result["verdict"], HAZARDS_NOT_IDENTIFIED)

    def test_an_empty_hazard_sheet_is_not_a_hazard_free_facility(self):
        result = assess_facility_risk(_case(assessment=_assessment(hazards=[])))
        self.assertEqual(result["verdict"], HAZARDS_NOT_IDENTIFIED)

    def test_a_safety_case_older_than_the_facility_is_stale(self):
        result = assess_facility_risk(
            _case(assessment=_assessment(last_modification_day=460))
        )
        self.assertEqual(result["verdict"], SAFETY_CASE_STALE)

    def test_an_unacceptable_residual_outranks_an_unaccepted_one(self):
        hazards = _hazards()
        hazards[0]["mitigations"][0]["implemented"] = False
        del hazards[2]["accepted_by"]
        result = assess_facility_risk(
            _case(assessment=_assessment(hazards=hazards))
        )
        self.assertEqual(result["verdict"], RESIDUAL_UNACCEPTABLE)
        self.assertEqual(result["unacceptable"], ("pressure-vessel-burst",))

    def test_a_residual_on_the_acceptance_line_needs_a_named_authority(self):
        hazards = _hazards()
        del hazards[2]["accepted_by"]
        result = assess_facility_risk(
            _case(assessment=_assessment(hazards=hazards))
        )
        self.assertEqual(result["verdict"], ACCEPTANCE_AUTHORITY_MISSING)
        self.assertEqual(result["unaccepted"], ("crane-load-drop",))

    def test_a_residual_below_the_line_needs_no_authority(self):
        hazards = _hazards()
        hazards[2]["likelihood"] = 1
        del hazards[2]["accepted_by"]
        result = assess_facility_risk(
            _case(assessment=_assessment(hazards=hazards))
        )
        self.assertEqual(result["verdict"], RESIDUAL_RISK_ACCEPTED)

    def test_category_coverage_short_is_reported(self):
        assessment = _assessment(
            required_categories=[
                "pressure",
                "energised-systems",
                "lifting",
                "hazardous-fluids",
            ]
        )
        result = assess_facility_risk(_case(assessment=assessment))
        self.assertEqual(result["verdict"], CATEGORY_COVERAGE_SHORT)
        self.assertEqual(result["uncovered_categories"], ("hazardous-fluids",))

    def test_an_unimplemented_mitigation_is_reported_as_outstanding(self):
        hazards = _hazards()
        hazards[1]["mitigations"].append(
            {
                "mitigation_id": "arc-flash-barrier",
                "target": "severity",
                "steps": 1,
                "implemented": False,
            }
        )
        result = assess_facility_risk(
            _case(assessment=_assessment(hazards=hazards))
        )
        self.assertEqual(result["verdict"], RISK_REDUCTION_OUTSTANDING)
        self.assertEqual(result["planned_mitigations"], ("arc-flash-barrier",))
        self.assertEqual(len(result["advisories"]), 1)

    def test_the_band_table_is_carried_per_hazard(self):
        result = assess_facility_risk(_case())
        bands = {entry["hazard_id"]: entry for entry in result["hazard_bands"]}
        self.assertEqual(bands["pressure-vessel-burst"]["initial_index"], 15)
        self.assertEqual(bands["pressure-vessel-burst"]["residual_index"], 5)
        self.assertEqual(
            bands["pressure-vessel-burst"]["residual_band"], BAND_ACCEPTABLE
        )
        self.assertEqual(
            bands["crane-load-drop"]["residual_band"], BAND_UNDESIRABLE
        )

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_facility_risk(["assessment"])


if __name__ == "__main__":
    unittest.main()
