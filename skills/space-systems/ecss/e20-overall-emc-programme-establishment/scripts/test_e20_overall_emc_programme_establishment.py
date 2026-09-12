#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.2.1 establishment of the
overall electromagnetic compatibility programme.

Exercises scripts/e20_overall_emc_programme_establishment_logic.py
(stdlib unittest, offline). Contract: every declared compatibility
activity maps onto exactly one programme area and an unrecognized
activity raises; the required area set is the baseline plus whatever the
mission profile pulls in, and an unknown or non-boolean profile flag
raises; absent areas and absent mandatory programme elements are
reported; each activity must name an owner and be established no later
than its area allows; the interference safety margin is the distance in
decibels between the susceptibility threshold and the predicted
interference level, judged against the margin the victim circuit
category demands, with an exactly-met policy not failed by decibel
subtraction; and the programme counts as established only when every
finding list is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_overall_emc_programme_establishment_logic as pe  # noqa: E402


def _baseline_activities():
    """One activity per baseline area, each owned and established in time."""
    return [
        {
            "activity_kind": "radiated_emission_control",
            "owner": "EMC lead engineer",
            "establishment_milestone": "PDR",
        },
        {
            "activity_kind": "radiated_susceptibility_control",
            "owner": "EMC lead engineer",
            "establishment_milestone": "PDR",
        },
        {
            "activity_kind": "grounding_concept_definition",
            "owner": "Electrical architect",
            "establishment_milestone": "PDR",
        },
        {
            "activity_kind": "harness_segregation_rules",
            "owner": "Harness engineer",
            "establishment_milestone": "CDR",
        },
        {
            "activity_kind": "electrostatic_discharge_control_measures",
            "owner": "Environment engineer",
            "establishment_milestone": "CDR",
        },
    ]


def _baseline_profile():
    return {
        "carries_radio_frequency_payload": False,
        "carries_ordnance": False,
        "carries_magnetic_sensor": False,
        "crewed_element": False,
        "uses_launch_site_services": False,
        "has_launcher_interface": False,
    }


def _declared_elements():
    return {
        "emc_control_plan": "EMC-PL-001 issue 1",
        "emc_analysis_approach": "EMC-AN-000 approach note",
        "emc_verification_programme": "EMC-VP-002",
        "interference_critical_point_list": "EMC-LI-003",
        "emc_requirement_flowdown": "EMC-RQ-004",
        "named_emc_authority": "EMC lead engineer",
    }


def _clean_programme():
    return {
        "profile": _baseline_profile(),
        "activities": _baseline_activities(),
        "declared_elements": _declared_elements(),
        "margin_cases": [
            {
                "point_id": "ICP-01",
                "circuit_category": "mission_critical",
                "susceptibility_threshold_db": 100.0,
                "interference_level_db": 88.0,
            }
        ],
    }


class TestActivityCategorization(unittest.TestCase):
    def test_radiated_emission_is_an_emission_activity(self):
        self.assertEqual(
            pe.categorize_programme_activity("radiated_emission_control"),
            "emission_control",
        )

    def test_bonding_activity_is_a_grounding_activity(self):
        self.assertEqual(
            pe.categorize_programme_activity("bonding_implementation_control"),
            "grounding_and_bonding",
        )

    def test_ordnance_hazard_is_a_radiation_hazard_activity(self):
        self.assertEqual(
            pe.categorize_programme_activity("ordnance_radiation_hazard_control"),
            "electromagnetic_radiation_hazard",
        )

    def test_every_activity_maps_into_a_known_area(self):
        for activity_kind in pe.ACTIVITY_AREAS:
            self.assertIn(
                pe.categorize_programme_activity(activity_kind), pe.PROGRAMME_AREAS
            )

    def test_uncategorized_activity_raises(self):
        with self.assertRaises(ValueError):
            pe.categorize_programme_activity("thermal_balance_control")

    def test_none_activity_raises(self):
        with self.assertRaises(ValueError):
            pe.categorize_programme_activity(None)


class TestMilestones(unittest.TestCase):
    def test_milestones_are_chronological(self):
        self.assertLess(pe.milestone_index("SRR"), pe.milestone_index("PDR"))
        self.assertLess(pe.milestone_index("PDR"), pe.milestone_index("CDR"))
        self.assertLess(pe.milestone_index("CDR"), pe.milestone_index("QR"))
        self.assertLess(pe.milestone_index("QR"), pe.milestone_index("AR"))

    def test_unknown_milestone_raises(self):
        with self.assertRaises(ValueError):
            pe.milestone_index("LRR")

    def test_every_area_has_a_latest_establishment_milestone(self):
        for area in pe.PROGRAMME_AREAS:
            self.assertIn(area, pe.AREA_LATEST_ESTABLISHMENT)
            pe.milestone_index(pe.AREA_LATEST_ESTABLISHMENT[area])


class TestRequiredAreas(unittest.TestCase):
    def test_baseline_profile_requires_the_baseline_areas(self):
        self.assertEqual(
            pe.required_programme_areas(_baseline_profile()), pe.BASELINE_AREAS
        )

    def test_empty_profile_still_requires_the_baseline(self):
        self.assertEqual(pe.required_programme_areas({}), pe.BASELINE_AREAS)

    def test_radio_frequency_payload_pulls_in_compatibility_area(self):
        profile = _baseline_profile()
        profile["carries_radio_frequency_payload"] = True
        self.assertIn(
            "radio_frequency_compatibility", pe.required_programme_areas(profile)
        )

    def test_ordnance_pulls_in_the_radiation_hazard_area(self):
        profile = _baseline_profile()
        profile["carries_ordnance"] = True
        self.assertIn(
            "electromagnetic_radiation_hazard", pe.required_programme_areas(profile)
        )

    def test_crewed_element_also_pulls_in_the_radiation_hazard_area(self):
        profile = _baseline_profile()
        profile["crewed_element"] = True
        self.assertIn(
            "electromagnetic_radiation_hazard", pe.required_programme_areas(profile)
        )

    def test_magnetic_sensor_pulls_in_magnetic_cleanliness(self):
        profile = _baseline_profile()
        profile["carries_magnetic_sensor"] = True
        self.assertIn("magnetic_cleanliness", pe.required_programme_areas(profile))

    def test_launcher_interface_pulls_in_intersystem_compatibility(self):
        profile = _baseline_profile()
        profile["has_launcher_interface"] = True
        self.assertIn(
            "intersystem_compatibility_with_launcher",
            pe.required_programme_areas(profile),
        )

    def test_unknown_profile_flag_raises(self):
        profile = _baseline_profile()
        profile["carries_cryocooler"] = True
        with self.assertRaises(ValueError):
            pe.required_programme_areas(profile)

    def test_non_boolean_profile_flag_raises(self):
        profile = _baseline_profile()
        profile["carries_ordnance"] = "yes"
        with self.assertRaises(ValueError):
            pe.required_programme_areas(profile)

    def test_non_mapping_profile_raises(self):
        with self.assertRaises(ValueError):
            pe.required_programme_areas(["carries_ordnance"])


class TestMissingAreasAndElements(unittest.TestCase):
    def test_baseline_programme_covers_every_required_area(self):
        self.assertEqual(
            pe.missing_programme_areas(_baseline_activities(), _baseline_profile()), []
        )

    def test_ordnance_without_hazard_activity_is_reported(self):
        profile = _baseline_profile()
        profile["carries_ordnance"] = True
        self.assertEqual(
            pe.missing_programme_areas(_baseline_activities(), profile),
            ["electromagnetic_radiation_hazard"],
        )

    def test_missing_areas_are_sorted(self):
        profile = _baseline_profile()
        profile["carries_ordnance"] = True
        profile["carries_magnetic_sensor"] = True
        missing = pe.missing_programme_areas(_baseline_activities(), profile)
        self.assertEqual(missing, sorted(missing))
        self.assertEqual(len(missing), 2)

    def test_full_element_set_reports_nothing_missing(self):
        self.assertEqual(pe.missing_programme_elements(_declared_elements()), [])

    def test_absent_element_is_reported(self):
        elements = _declared_elements()
        del elements["interference_critical_point_list"]
        self.assertEqual(
            pe.missing_programme_elements(elements), ["interference_critical_point_list"]
        )

    def test_blank_element_counts_as_absent(self):
        elements = _declared_elements()
        elements["named_emc_authority"] = "   "
        self.assertIn("named_emc_authority", pe.missing_programme_elements(elements))

    def test_false_element_counts_as_absent(self):
        elements = _declared_elements()
        elements["emc_analysis_approach"] = False
        self.assertIn("emc_analysis_approach", pe.missing_programme_elements(elements))

    def test_empty_declaration_reports_every_element(self):
        self.assertEqual(
            len(pe.missing_programme_elements({})),
            len(pe.MANDATORY_PROGRAMME_ELEMENTS),
        )

    def test_non_mapping_element_declaration_raises(self):
        with self.assertRaises(ValueError):
            pe.missing_programme_elements(["emc_control_plan"])


class TestMarginPolicy(unittest.TestCase):
    def test_ordnance_circuit_demands_twenty_decibels(self):
        self.assertAlmostEqual(
            pe.required_margin_db("electro_explosive_device"), 20.0, places=9
        )

    def test_standard_circuit_demands_six_decibels(self):
        self.assertAlmostEqual(pe.required_margin_db("standard"), 6.0, places=9)

    def test_unknown_circuit_category_raises(self):
        with self.assertRaises(ValueError):
            pe.required_margin_db("nice_to_have")

    def test_margin_is_threshold_less_interference(self):
        self.assertAlmostEqual(
            pe.interference_margin_db(100.0, 82.0), 18.0, places=9
        )

    def test_negative_margin_when_interference_exceeds_threshold(self):
        self.assertAlmostEqual(
            pe.interference_margin_db(80.0, 92.0), -12.0, places=9
        )

    def test_non_numeric_threshold_raises(self):
        with self.assertRaises(ValueError):
            pe.interference_margin_db("100", 82.0)

    def test_boolean_interference_level_raises(self):
        with self.assertRaises(ValueError):
            pe.interference_margin_db(100.0, True)

    def test_exactly_met_policy_survives_decibel_subtraction(self):
        """8.2 dB against 2.2 dB is exactly six decibels, but the
        subtraction lands one unit in the last place low."""
        margin = pe.interference_margin_db(8.2, 2.2)
        self.assertLess(margin, 6.0)
        self.assertTrue(pe.margin_meets_policy(margin, 6.0))

    def test_real_shortfall_still_fails(self):
        self.assertFalse(pe.margin_meets_policy(5.5, 6.0))

    def test_comfortable_margin_passes(self):
        self.assertTrue(pe.margin_meets_policy(24.0, 20.0))

    def test_negative_policy_margin_raises(self):
        with self.assertRaises(ValueError):
            pe.margin_meets_policy(6.0, -1.0)

    def test_non_numeric_policy_margin_raises(self):
        with self.assertRaises(ValueError):
            pe.margin_meets_policy(6.0, "6")

    def test_margin_findings_flag_a_thin_ordnance_point(self):
        cases = [
            {
                "point_id": "ICP-EED-01",
                "circuit_category": "electro_explosive_device",
                "susceptibility_threshold_db": 100.0,
                "interference_level_db": 85.0,
            }
        ]
        findings = pe.margin_findings(cases)
        self.assertEqual(len(findings), 1)
        self.assertIn("ICP-EED-01", findings[0])

    def test_margin_findings_accept_a_compliant_point(self):
        self.assertEqual(pe.margin_findings(_clean_programme()["margin_cases"]), [])

    def test_margin_findings_are_sorted(self):
        cases = [
            {
                "point_id": "ICP-B",
                "circuit_category": "safety_critical",
                "susceptibility_threshold_db": 100.0,
                "interference_level_db": 90.0,
            },
            {
                "point_id": "ICP-A",
                "circuit_category": "safety_critical",
                "susceptibility_threshold_db": 100.0,
                "interference_level_db": 95.0,
            },
        ]
        findings = pe.margin_findings(cases)
        self.assertEqual(findings, sorted(findings))
        self.assertEqual(len(findings), 2)


class TestActivityFindings(unittest.TestCase):
    def test_clean_activity_has_no_findings(self):
        self.assertEqual(pe.activity_findings(_baseline_activities()[0]), [])

    def test_unowned_activity_is_a_finding(self):
        activity = _baseline_activities()[0]
        activity["owner"] = ""
        findings = pe.activity_findings(activity)
        self.assertTrue(any("names no owner" in f for f in findings))

    def test_late_establishment_is_a_finding(self):
        activity = _baseline_activities()[2]
        activity["establishment_milestone"] = "QR"
        findings = pe.activity_findings(activity)
        self.assertTrue(any("later than" in f for f in findings))

    def test_early_establishment_is_accepted(self):
        activity = _baseline_activities()[3]
        activity["establishment_milestone"] = "SRR"
        self.assertEqual(pe.activity_findings(activity), [])

    def test_activity_findings_are_sorted(self):
        activity = _baseline_activities()[2]
        activity["owner"] = None
        activity["establishment_milestone"] = "AR"
        findings = pe.activity_findings(activity)
        self.assertEqual(findings, sorted(findings))
        self.assertEqual(len(findings), 2)

    def test_unknown_milestone_in_activity_raises(self):
        activity = _baseline_activities()[0]
        activity["establishment_milestone"] = "FRR"
        with self.assertRaises(ValueError):
            pe.activity_findings(activity)


class TestAggregate(unittest.TestCase):
    def test_clean_programme_is_established(self):
        result = pe.aggregate_emc_programme(_clean_programme())
        self.assertTrue(result["established"])
        self.assertEqual(result["uncovered_areas"], [])
        self.assertEqual(result["missing_elements"], [])
        self.assertEqual(result["activity_findings"], {})
        self.assertEqual(result["margin_findings"], [])
        self.assertAlmostEqual(result["area_coverage"], 1.0, places=9)

    def test_uncovered_area_blocks_establishment(self):
        programme = _clean_programme()
        programme["profile"]["carries_magnetic_sensor"] = True
        result = pe.aggregate_emc_programme(programme)
        self.assertFalse(result["established"])
        self.assertEqual(result["uncovered_areas"], ["magnetic_cleanliness"])
        self.assertLess(result["area_coverage"], 1.0)

    def test_missing_element_blocks_establishment(self):
        programme = _clean_programme()
        del programme["declared_elements"]["emc_control_plan"]
        result = pe.aggregate_emc_programme(programme)
        self.assertFalse(result["established"])
        self.assertEqual(result["missing_elements"], ["emc_control_plan"])

    def test_activity_finding_blocks_establishment(self):
        programme = _clean_programme()
        programme["activities"][0]["owner"] = None
        result = pe.aggregate_emc_programme(programme)
        self.assertFalse(result["established"])
        self.assertIn("radiated_emission_control", result["activity_findings"])

    def test_thin_margin_blocks_establishment(self):
        programme = _clean_programme()
        programme["margin_cases"][0]["interference_level_db"] = 96.0
        result = pe.aggregate_emc_programme(programme)
        self.assertFalse(result["established"])
        self.assertEqual(len(result["margin_findings"]), 1)

    def test_partial_coverage_is_a_fraction(self):
        programme = _clean_programme()
        programme["activities"] = _baseline_activities()[:4]
        result = pe.aggregate_emc_programme(programme)
        self.assertAlmostEqual(result["area_coverage"], 0.8, places=6)

    def test_coverage_is_not_compared_by_bare_equality(self):
        result = pe.aggregate_emc_programme(_clean_programme())
        self.assertTrue(math.isclose(result["area_coverage"], 1.0, rel_tol=1e-9))

    def test_programme_without_margin_cases_is_still_reviewable(self):
        programme = _clean_programme()
        del programme["margin_cases"]
        result = pe.aggregate_emc_programme(programme)
        self.assertTrue(result["established"])


if __name__ == "__main__":
    unittest.main()
