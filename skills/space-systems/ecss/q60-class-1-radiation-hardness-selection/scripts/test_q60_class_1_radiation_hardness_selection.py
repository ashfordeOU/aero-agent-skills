#!/usr/bin/env python3
"""Contract test for the Class 1 radiation hardness selection leaf (offline)."""

import copy
import unittest

from q60_class_1_radiation_hardness_selection_logic import (
    DEFAULT_RADIATION_POLICY,
    DESTRUCTIVE_MECHANISMS,
    EVIDENCE_ABSENT,
    MARGIN_ADEQUATE,
    MARGIN_ON_LIMIT,
    MARGIN_SHORT,
    RADIATION_ADEQUATE,
    RADIATION_EVIDENCE_INCOMPLETE,
    RADIATION_INADEQUATE,
    RADIATION_MITIGATION_REQUIRED,
    SINGLE_EVENT_MECHANISMS,
    TECHNOLOGIES,
    effective_dose_capability,
    evaluate_radiation_selection,
    grade_displacement_damage,
    grade_single_event,
    grade_total_dose,
    mission_accumulated_dose,
    mission_accumulated_fluence,
    mission_duration_years,
    required_capability,
    validate_radiation_policy,
)

PHASES = [
    {
        "name": "transfer",
        "duration_years": 1.0,
        "dose_rate_krad_per_year": 5.0,
        "fluence_rate_per_cm2_per_year": 1.0e11,
    },
    {
        "name": "operational",
        "duration_years": 9.0,
        "dose_rate_krad_per_year": 2.0,
        "fluence_rate_per_cm2_per_year": 5.0e11,
    },
]

BASE_CASE = {
    "part_reference": "lin-amp-0001",
    "technology": "bipolar-linear",
    "dose_rate_basis": "low-dose-rate",
    "rated_total_dose_krad": 100.0,
    "rated_displacement_fluence_per_cm2": 1.0e13,
    "environment_let_mev_cm2_per_mg": 60.0,
    "mission_phases": PHASES,
    "single_event_data": [
        {
            "mechanism": "single-event-latch-up",
            "threshold_let_mev_cm2_per_mg": 80.0,
            "mitigation_available": False,
        },
        {
            "mechanism": "single-event-upset",
            "threshold_let_mev_cm2_per_mg": 75.0,
            "mitigation_available": True,
        },
    ],
}


def _case(**overrides):
    case = copy.deepcopy(BASE_CASE)
    case.update(overrides)
    return case


def _with_events(*events):
    return _case(single_event_data=[dict(event) for event in events])


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_radiation_policy(DEFAULT_RADIATION_POLICY),
            DEFAULT_RADIATION_POLICY,
        )

    def test_policy_covers_every_technology(self):
        for technology in TECHNOLOGIES:
            self.assertIn(
                technology, DEFAULT_RADIATION_POLICY["low_dose_rate_capability_factor"]
            )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_radiation_policy("default")

    def test_margin_factor_below_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_RADIATION_POLICY)
        broken["total_dose_margin_factor"] = 0.8
        with self.assertRaises(ValueError):
            validate_radiation_policy(broken)

    def test_capability_factor_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_RADIATION_POLICY)
        broken["low_dose_rate_capability_factor"]["bipolar-linear"] = 1.2
        with self.assertRaises(ValueError):
            validate_radiation_policy(broken)

    def test_policy_missing_a_technology_rejected(self):
        broken = copy.deepcopy(DEFAULT_RADIATION_POLICY)
        del broken["low_dose_rate_capability_factor"]["optocoupler"]
        with self.assertRaises(ValueError):
            validate_radiation_policy(broken)

    def test_policy_missing_a_margin_key_rejected(self):
        broken = copy.deepcopy(DEFAULT_RADIATION_POLICY)
        del broken["displacement_damage_margin_factor"]
        with self.assertRaises(ValueError):
            validate_radiation_policy(broken)


class MissionAccumulationTests(unittest.TestCase):
    def test_dose_accumulates_rate_times_duration(self):
        self.assertAlmostEqual(mission_accumulated_dose(PHASES), 23.0, places=9)

    def test_fluence_accumulates_rate_times_duration(self):
        self.assertAlmostEqual(mission_accumulated_fluence(PHASES), 4.6e12, places=3)

    def test_duration_is_the_sum_of_the_phases(self):
        self.assertAlmostEqual(mission_duration_years(PHASES), 10.0, places=9)

    def test_a_longer_phase_raises_the_dose(self):
        longer = copy.deepcopy(PHASES)
        longer[1]["duration_years"] = 19.0
        self.assertGreater(
            mission_accumulated_dose(longer), mission_accumulated_dose(PHASES)
        )

    def test_empty_phase_list_rejected(self):
        with self.assertRaises(ValueError):
            mission_accumulated_dose([])

    def test_phase_without_a_name_rejected(self):
        broken = [{"duration_years": 2.0, "dose_rate_krad_per_year": 1.0}]
        with self.assertRaises(ValueError):
            mission_accumulated_dose(broken)

    def test_zero_duration_phase_rejected(self):
        broken = [
            {
                "name": "instant",
                "duration_years": 0.0,
                "dose_rate_krad_per_year": 1.0,
            }
        ]
        with self.assertRaises(ValueError):
            mission_accumulated_dose(broken)

    def test_negative_dose_rate_rejected(self):
        broken = [
            {
                "name": "shielded",
                "duration_years": 1.0,
                "dose_rate_krad_per_year": -3.0,
            }
        ]
        with self.assertRaises(ValueError):
            mission_accumulated_dose(broken)


class MarginTests(unittest.TestCase):
    def test_requirement_is_the_environment_times_the_margin(self):
        self.assertAlmostEqual(required_capability(23.0, 2.0), 46.0, places=9)

    def test_margin_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            required_capability(23.0, 0.5)

    def test_negative_environment_rejected(self):
        with self.assertRaises(ValueError):
            required_capability(-1.0, 2.0)


class DoseCapabilityTests(unittest.TestCase):
    def test_low_dose_rate_capability_is_carried_whole(self):
        self.assertAlmostEqual(
            effective_dose_capability(100.0, "bipolar-linear", "low-dose-rate"),
            100.0,
            places=9,
        )

    def test_rate_sensitive_technology_is_cut(self):
        self.assertAlmostEqual(
            effective_dose_capability(100.0, "bipolar-linear", "high-dose-rate"),
            50.0,
            places=9,
        )

    def test_rate_insensitive_technology_is_not_cut(self):
        self.assertAlmostEqual(
            effective_dose_capability(100.0, "cmos-digital", "high-dose-rate"),
            100.0,
            places=9,
        )

    def test_unknown_technology_rejected(self):
        with self.assertRaises(ValueError):
            effective_dose_capability(100.0, "vacuum-tube", "low-dose-rate")

    def test_unknown_dose_rate_basis_rejected(self):
        with self.assertRaises(ValueError):
            effective_dose_capability(100.0, "cmos-digital", "medium-dose-rate")


class TotalDoseGradeTests(unittest.TestCase):
    def test_comfortable_part_is_adequate(self):
        graded = grade_total_dose(BASE_CASE)
        self.assertEqual(graded["verdict"], MARGIN_ADEQUATE)
        self.assertAlmostEqual(graded["required_capability_krad"], 46.0, places=9)

    def test_capability_landing_on_the_requirement_is_on_limit(self):
        graded = grade_total_dose(_case(rated_total_dose_krad=46.0))
        self.assertEqual(graded["verdict"], MARGIN_ON_LIMIT)
        self.assertTrue(graded["adequate"])
        self.assertAlmostEqual(
            graded["effective_capability_krad"],
            graded["required_capability_krad"],
            places=9,
        )

    def test_a_longer_mission_can_break_a_part_that_passed(self):
        longer = copy.deepcopy(PHASES)
        longer[1]["duration_years"] = 39.0
        graded = grade_total_dose(_case(mission_phases=longer))
        self.assertEqual(graded["verdict"], MARGIN_SHORT)

    def test_zero_dose_environment_leaves_no_ratio(self):
        quiet = [
            {
                "name": "shielded",
                "duration_years": 3.0,
                "dose_rate_krad_per_year": 0.0,
                "fluence_rate_per_cm2_per_year": 0.0,
            }
        ]
        graded = grade_total_dose(_case(mission_phases=quiet))
        self.assertIsNone(graded["margin_ratio"])
        self.assertTrue(graded["adequate"])

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            grade_total_dose("lin-amp-0001")


class DisplacementDamageTests(unittest.TestCase):
    def test_comfortable_fluence_is_adequate(self):
        graded = grade_displacement_damage(BASE_CASE)
        self.assertEqual(graded["verdict"], MARGIN_ADEQUATE)

    def test_absent_capability_is_reported_as_missing_evidence(self):
        graded = grade_displacement_damage(
            _case(rated_displacement_fluence_per_cm2=None)
        )
        self.assertEqual(graded["verdict"], EVIDENCE_ABSENT)
        self.assertFalse(graded["adequate"])

    def test_thin_fluence_capability_is_short(self):
        graded = grade_displacement_damage(
            _case(rated_displacement_fluence_per_cm2=1.0e11)
        )
        self.assertEqual(graded["verdict"], MARGIN_SHORT)


class SingleEventTests(unittest.TestCase):
    def test_destructive_list_sits_inside_the_mechanism_list(self):
        for mechanism in DESTRUCTIVE_MECHANISMS:
            self.assertIn(mechanism, SINGLE_EVENT_MECHANISMS)

    def test_threshold_above_the_environment_is_adequate(self):
        graded = grade_single_event(
            {
                "mechanism": "single-event-upset",
                "threshold_let_mev_cm2_per_mg": 75.0,
                "mitigation_available": False,
            },
            60.0,
        )
        self.assertEqual(graded["verdict"], MARGIN_ADEQUATE)

    def test_threshold_landing_on_the_environment_is_on_limit(self):
        graded = grade_single_event(
            {
                "mechanism": "single-event-upset",
                "threshold_let_mev_cm2_per_mg": 60.0,
                "mitigation_available": False,
            },
            60.0,
        )
        self.assertEqual(graded["verdict"], MARGIN_ON_LIMIT)
        self.assertTrue(graded["adequate"])

    def test_mitigation_answers_a_recoverable_event(self):
        graded = grade_single_event(
            {
                "mechanism": "single-event-upset",
                "threshold_let_mev_cm2_per_mg": 20.0,
                "mitigation_available": True,
            },
            60.0,
        )
        self.assertTrue(graded["mitigation_credited"])
        self.assertTrue(graded["adequate"])

    def test_mitigation_never_answers_a_destructive_event(self):
        graded = grade_single_event(
            {
                "mechanism": "single-event-burnout",
                "threshold_let_mev_cm2_per_mg": 20.0,
                "mitigation_available": True,
            },
            60.0,
        )
        self.assertFalse(graded["mitigation_credited"])
        self.assertFalse(graded["adequate"])

    def test_silent_datasheet_is_not_an_immune_part(self):
        graded = grade_single_event(
            {"mechanism": "single-event-latch-up", "mitigation_available": False}, 60.0
        )
        self.assertEqual(graded["verdict"], EVIDENCE_ABSENT)
        self.assertFalse(graded["adequate"])

    def test_unknown_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            grade_single_event(
                {
                    "mechanism": "single-event-sunburn",
                    "threshold_let_mev_cm2_per_mg": 40.0,
                },
                60.0,
            )

    def test_non_boolean_mitigation_flag_rejected(self):
        with self.assertRaises(ValueError):
            grade_single_event(
                {
                    "mechanism": "single-event-upset",
                    "threshold_let_mev_cm2_per_mg": 40.0,
                    "mitigation_available": "yes",
                },
                60.0,
            )

    def test_missing_environment_threshold_rejected(self):
        with self.assertRaises(ValueError):
            grade_single_event(
                {
                    "mechanism": "single-event-upset",
                    "threshold_let_mev_cm2_per_mg": 40.0,
                },
                None,
            )


class SelectionTests(unittest.TestCase):
    def test_sound_part_is_adequate(self):
        result = evaluate_radiation_selection(BASE_CASE)
        self.assertEqual(result["verdict"], RADIATION_ADEQUATE)
        self.assertTrue(result["adequate"])
        self.assertAlmostEqual(result["mission_duration_years"], 10.0, places=9)

    def test_rate_sensitive_cut_is_reported_even_when_it_still_passes(self):
        result = evaluate_radiation_selection(_case(dose_rate_basis="high-dose-rate"))
        self.assertEqual(result["verdict"], RADIATION_ADEQUATE)
        self.assertTrue(
            any("high dose rate" in finding for finding in result["findings"])
        )

    def test_lifetime_extension_breaks_a_rate_sensitive_part(self):
        longer = copy.deepcopy(PHASES)
        longer[1]["duration_years"] = 19.0
        result = evaluate_radiation_selection(
            _case(dose_rate_basis="high-dose-rate", mission_phases=longer)
        )
        self.assertEqual(result["verdict"], RADIATION_INADEQUATE)

    def test_destructive_event_below_the_environment_is_inadequate(self):
        result = evaluate_radiation_selection(
            _with_events(
                {
                    "mechanism": "single-event-latch-up",
                    "threshold_let_mev_cm2_per_mg": 20.0,
                    "mitigation_available": True,
                }
            )
        )
        self.assertEqual(result["verdict"], RADIATION_INADEQUATE)

    def test_mitigated_recoverable_event_needs_mitigation(self):
        result = evaluate_radiation_selection(
            _with_events(
                {
                    "mechanism": "single-event-upset",
                    "threshold_let_mev_cm2_per_mg": 20.0,
                    "mitigation_available": True,
                }
            )
        )
        self.assertEqual(result["verdict"], RADIATION_MITIGATION_REQUIRED)

    def test_unmitigated_recoverable_event_is_inadequate(self):
        result = evaluate_radiation_selection(
            _with_events(
                {
                    "mechanism": "single-event-upset",
                    "threshold_let_mev_cm2_per_mg": 20.0,
                    "mitigation_available": False,
                }
            )
        )
        self.assertEqual(result["verdict"], RADIATION_INADEQUATE)

    def test_absent_evidence_is_not_a_pass_and_not_a_breach(self):
        result = evaluate_radiation_selection(
            _case(rated_displacement_fluence_per_cm2=None)
        )
        self.assertEqual(result["verdict"], RADIATION_EVIDENCE_INCOMPLETE)
        self.assertFalse(result["adequate"])

    def test_absent_mechanism_binds_before_a_thin_one(self):
        result = evaluate_radiation_selection(
            _case(rated_displacement_fluence_per_cm2=None)
        )
        self.assertEqual(result["binding_mechanism"], "displacement-damage")

    def test_binding_mechanism_is_the_thinnest_margin(self):
        result = evaluate_radiation_selection(
            _case(rated_displacement_fluence_per_cm2=9.3e12)
        )
        self.assertEqual(result["binding_mechanism"], "displacement-damage")

    def test_empty_part_reference_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_radiation_selection(_case(part_reference="   "))

    def test_non_sequence_single_event_data_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_radiation_selection(_case(single_event_data={"mechanism": "x"}))

    def test_part_with_no_single_event_data_still_grades_dose(self):
        result = evaluate_radiation_selection(_case(single_event_data=[]))
        self.assertEqual(result["verdict"], RADIATION_ADEQUATE)
        self.assertEqual(result["single_events"], [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
