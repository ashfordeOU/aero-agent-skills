#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-12C §4 radiation evaluation
framework principles.

Exercises scripts/e1012_principles_logic.py (stdlib unittest, offline).
Contract: a radiation effect type maps to exactly one category and an
unrecognized type raises; the required evaluation activities for each
project stage are deterministic and an unknown stage raises; a
parameter-unit pair is accepted when listed in the §4 table, rejected
when not, and an unknown parameter raises; evaluation gaps are the
difference between required and performed activities; the full review
aggregates all three dimensions and is compliant only when all are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1012_principles_logic as el  # noqa: E402


class CategorizeEffectTest(unittest.TestCase):
    def test_tid_maps_to_total_ionising_dose(self):
        self.assertEqual(el.categorize_effect("tid"), "total_ionising_dose")

    def test_total_ionising_dose_keyword_maps_correctly(self):
        self.assertEqual(el.categorize_effect("total_ionising_dose"), "total_ionising_dose")

    def test_tid_silicon_maps_to_total_ionising_dose(self):
        self.assertEqual(el.categorize_effect("tid_silicon"), "total_ionising_dose")

    def test_dd_maps_to_displacement_damage(self):
        self.assertEqual(el.categorize_effect("dd"), "displacement_damage")

    def test_dd_proton_maps_to_displacement_damage(self):
        self.assertEqual(el.categorize_effect("dd_proton"), "displacement_damage")

    def test_dd_neutron_maps_to_displacement_damage(self):
        self.assertEqual(el.categorize_effect("dd_neutron"), "displacement_damage")

    def test_seu_maps_to_single_event_effect(self):
        self.assertEqual(el.categorize_effect("seu"), "single_event_effect")

    def test_sel_maps_to_single_event_effect(self):
        self.assertEqual(el.categorize_effect("sel"), "single_event_effect")

    def test_sefi_maps_to_single_event_effect(self):
        self.assertEqual(el.categorize_effect("sefi"), "single_event_effect")

    def test_set_maps_to_single_event_effect(self):
        self.assertEqual(el.categorize_effect("set"), "single_event_effect")

    def test_sehe_maps_to_single_event_effect(self):
        self.assertEqual(el.categorize_effect("sehe"), "single_event_effect")

    def test_eldrs_maps_to_enhanced_low_dose_rate(self):
        self.assertEqual(el.categorize_effect("eldrs"), "enhanced_low_dose_rate")

    def test_enhanced_low_dose_rate_keyword_maps_correctly(self):
        self.assertEqual(
            el.categorize_effect("enhanced_low_dose_rate_sensitivity"),
            "enhanced_low_dose_rate",
        )

    def test_unknown_effect_raises_value_error(self):
        with self.assertRaises(ValueError):
            el.categorize_effect("mystery_particle_beam")

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            el.categorize_effect("")


class StageRequiredActivitiesTest(unittest.TestCase):
    def test_phase_a_contains_environment_scoping(self):
        activities = el.stage_required_activities("phase_a")
        self.assertIn("environment_scoping", activities)

    def test_phase_a_contains_sensitivity_screening(self):
        activities = el.stage_required_activities("phase_a")
        self.assertIn("preliminary_sensitivity_screening", activities)

    def test_phase_b_contains_shielding_study(self):
        activities = el.stage_required_activities("phase_b")
        self.assertIn("preliminary_shielding_study", activities)

    def test_phase_cd_contains_radiation_test_programme(self):
        activities = el.stage_required_activities("phase_cd")
        self.assertIn("radiation_test_programme", activities)

    def test_phase_cd_contains_qualification_evidence(self):
        activities = el.stage_required_activities("phase_cd")
        self.assertIn("qualification_evidence", activities)

    def test_phase_cd_contains_margin_verification(self):
        activities = el.stage_required_activities("phase_cd")
        self.assertIn("radiation_design_margin_verification", activities)

    def test_phase_e_contains_in_flight_monitoring(self):
        activities = el.stage_required_activities("phase_e")
        self.assertIn("in_flight_monitoring", activities)

    def test_phase_e_contains_anomaly_assessment(self):
        activities = el.stage_required_activities("phase_e")
        self.assertIn("anomaly_radiation_assessment", activities)

    def test_phase_f_contains_end_of_life_dose_verification(self):
        activities = el.stage_required_activities("phase_f")
        self.assertIn("end_of_life_dose_verification", activities)

    def test_returns_frozenset(self):
        result = el.stage_required_activities("phase_b")
        self.assertIsInstance(result, frozenset)

    def test_unknown_stage_raises_value_error(self):
        with self.assertRaises(ValueError):
            el.stage_required_activities("phase_z")

    def test_result_is_immutable_copy(self):
        r1 = el.stage_required_activities("phase_a")
        r2 = el.stage_required_activities("phase_a")
        self.assertEqual(r1, r2)


class ValidateParameterUnitTest(unittest.TestCase):
    def test_rad_si_accepted_for_total_ionising_dose(self):
        self.assertTrue(el.validate_parameter_unit("total_ionising_dose", "rad_si"))

    def test_gy_si_accepted_for_total_ionising_dose(self):
        self.assertTrue(el.validate_parameter_unit("total_ionising_dose", "gy_si"))

    def test_krad_si_accepted_for_total_ionising_dose(self):
        self.assertTrue(el.validate_parameter_unit("total_ionising_dose", "krad_si"))

    def test_invalid_unit_returns_false_for_known_parameter(self):
        self.assertFalse(el.validate_parameter_unit("total_ionising_dose", "volts"))

    def test_mev_cm2_mg_accepted_for_let_threshold(self):
        self.assertTrue(el.validate_parameter_unit("let_threshold", "mev_cm2_mg"))

    def test_events_device_s_accepted_for_event_rate(self):
        self.assertTrue(el.validate_parameter_unit("event_rate", "events_device_s"))

    def test_upsets_day_accepted_for_event_rate(self):
        self.assertTrue(el.validate_parameter_unit("event_rate", "upsets_day"))

    def test_cm2_device_accepted_for_saturation_cross_section(self):
        self.assertTrue(el.validate_parameter_unit("saturation_cross_section", "cm2_device"))

    def test_mev_g_accepted_for_niel_dose(self):
        self.assertTrue(el.validate_parameter_unit("niel_dose", "mev_g"))

    def test_rad_si_accepted_for_eldrs_dose(self):
        self.assertTrue(el.validate_parameter_unit("eldrs_sensitivity_dose", "rad_si"))

    def test_unknown_parameter_raises_value_error(self):
        with self.assertRaises(ValueError):
            el.validate_parameter_unit("quantum_flux_density", "frobs")

    def test_parsecs_not_accepted_for_total_ionising_dose(self):
        self.assertFalse(el.validate_parameter_unit("total_ionising_dose", "parsecs"))


class EvaluationGapsTest(unittest.TestCase):
    def test_no_gaps_when_all_phase_a_activities_performed(self):
        all_a = list(el.stage_required_activities("phase_a"))
        self.assertEqual(el.evaluation_gaps("phase_a", all_a), [])

    def test_all_phase_a_activities_missing_when_none_performed(self):
        gaps = el.evaluation_gaps("phase_a", [])
        self.assertIn("environment_scoping", gaps)
        self.assertIn("preliminary_sensitivity_screening", gaps)

    def test_gaps_list_is_sorted(self):
        gaps = el.evaluation_gaps("phase_b", [])
        self.assertEqual(gaps, sorted(gaps))

    def test_partial_activities_shows_missing_only(self):
        gaps = el.evaluation_gaps("phase_a", ["environment_scoping"])
        self.assertNotIn("environment_scoping", gaps)
        self.assertIn("preliminary_sensitivity_screening", gaps)

    def test_extra_activities_beyond_required_not_flagged(self):
        required = list(el.stage_required_activities("phase_b"))
        extended = required + ["optional_review_not_in_table"]
        self.assertEqual(el.evaluation_gaps("phase_b", extended), [])

    def test_phase_cd_gaps_detected(self):
        gaps = el.evaluation_gaps("phase_cd", ["shielding_analysis"])
        self.assertIn("radiation_test_programme", gaps)
        self.assertNotIn("shielding_analysis", gaps)

    def test_unknown_stage_raises_value_error(self):
        with self.assertRaises(ValueError):
            el.evaluation_gaps("phase_x", [])


class FullEvaluationReviewTest(unittest.TestCase):
    def _compliant_phase_a_record(self):
        activities = list(el.stage_required_activities("phase_a"))
        return {
            "component_id": "comp-rail-001",
            "project_stage": "phase_a",
            "effect_types": ["tid", "seu"],
            "activities_performed": activities,
            "parameters": [
                {
                    "parameter": "total_ionising_dose",
                    "unit": "rad_si",
                    "value": 30000.0,
                }
            ],
        }

    def test_fully_compliant_record_has_no_issues(self):
        record = self._compliant_phase_a_record()
        review = el.full_evaluation_review(record)
        self.assertEqual(review["categorization_errors"], [])
        self.assertEqual(review["activity_gaps"], [])
        self.assertEqual(review["parameter_unit_issues"], [])
        self.assertTrue(el.is_evaluation_compliant(review))

    def test_unrecognized_effect_type_surfaces_as_categorization_error(self):
        record = self._compliant_phase_a_record()
        record = dict(record, effect_types=["tid", "alien_beam_42"])
        review = el.full_evaluation_review(record)
        self.assertEqual(len(review["categorization_errors"]), 1)
        self.assertEqual(review["categorization_errors"][0]["effect_type"], "alien_beam_42")
        self.assertFalse(el.is_evaluation_compliant(review))

    def test_missing_activities_surface_as_gaps(self):
        record = self._compliant_phase_a_record()
        record = dict(record, activities_performed=[])
        review = el.full_evaluation_review(record)
        self.assertGreater(len(review["activity_gaps"]), 0)
        self.assertFalse(el.is_evaluation_compliant(review))

    def test_invalid_unit_surfaces_as_parameter_unit_issue(self):
        record = self._compliant_phase_a_record()
        record = dict(
            record,
            parameters=[
                {"parameter": "total_ionising_dose", "unit": "parsecs", "value": 100.0}
            ],
        )
        review = el.full_evaluation_review(record)
        self.assertEqual(len(review["parameter_unit_issues"]), 1)
        self.assertEqual(
            review["parameter_unit_issues"][0]["issue"], "invalid_unit_for_parameter"
        )
        self.assertFalse(el.is_evaluation_compliant(review))

    def test_unknown_parameter_surfaces_as_parameter_unit_issue(self):
        record = self._compliant_phase_a_record()
        record = dict(
            record,
            parameters=[
                {"parameter": "warp_drive_output", "unit": "rad_si", "value": 1.0}
            ],
        )
        review = el.full_evaluation_review(record)
        self.assertEqual(len(review["parameter_unit_issues"]), 1)

    def test_multiple_issues_across_dimensions_all_captured(self):
        record = {
            "component_id": "comp-rail-002",
            "project_stage": "phase_a",
            "effect_types": ["tid", "plasma_zap"],
            "activities_performed": [],
            "parameters": [
                {"parameter": "total_ionising_dose", "unit": "furlongs", "value": 1.0}
            ],
        }
        review = el.full_evaluation_review(record)
        self.assertEqual(len(review["categorization_errors"]), 1)
        self.assertGreater(len(review["activity_gaps"]), 0)
        self.assertEqual(len(review["parameter_unit_issues"]), 1)
        self.assertFalse(el.is_evaluation_compliant(review))

    def test_unknown_stage_in_record_raises(self):
        record = self._compliant_phase_a_record()
        record = dict(record, project_stage="phase_omega")
        with self.assertRaises(ValueError):
            el.full_evaluation_review(record)

    def test_empty_effect_types_and_parameters_still_checks_activities(self):
        activities = list(el.stage_required_activities("phase_a"))
        record = {
            "component_id": "comp-rail-003",
            "project_stage": "phase_a",
            "effect_types": [],
            "activities_performed": activities,
            "parameters": [],
        }
        review = el.full_evaluation_review(record)
        self.assertEqual(review["categorization_errors"], [])
        self.assertEqual(review["activity_gaps"], [])
        self.assertEqual(review["parameter_unit_issues"], [])
        self.assertTrue(el.is_evaluation_compliant(review))

    def test_eldrs_parameter_unit_accepted(self):
        activities = list(el.stage_required_activities("phase_a"))
        record = {
            "component_id": "comp-bipolar-001",
            "project_stage": "phase_a",
            "effect_types": ["eldrs"],
            "activities_performed": activities,
            "parameters": [
                {"parameter": "eldrs_sensitivity_dose", "unit": "rad_si", "value": 500.0}
            ],
        }
        review = el.full_evaluation_review(record)
        self.assertEqual(review["parameter_unit_issues"], [])

    def test_see_cross_section_unit_accepted(self):
        activities = list(el.stage_required_activities("phase_a"))
        record = {
            "component_id": "comp-see-001",
            "project_stage": "phase_a",
            "effect_types": ["seu"],
            "activities_performed": activities,
            "parameters": [
                {
                    "parameter": "saturation_cross_section",
                    "unit": "cm2_device",
                    "value": 1e-4,
                }
            ],
        }
        review = el.full_evaluation_review(record)
        self.assertEqual(review["parameter_unit_issues"], [])
        self.assertTrue(el.is_evaluation_compliant(review))


if __name__ == "__main__":
    unittest.main(verbosity=2)
