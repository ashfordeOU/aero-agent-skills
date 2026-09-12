#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.3.4.1 charging
protection programme applicability.

Exercises
scripts/e20_charging_protection_programme_applicability_logic.py
(stdlib unittest, offline). Contract: an orbit maps to exactly one
charging environment regime and an unmapped orbit raises; the
applicability drivers follow the regime, the bus voltage, the exposed
dielectric fraction, the mission duration and any ungrounded
conductive element, with a value sitting exactly on a threshold
counting as meeting it; the required section list grows with the
internal-charging regimes and with the high-voltage driver, and a
mission with no driver still owes a written justification; a section
that is absent, None or empty is reported; the milestone sequence
places the approval before the preliminary design review; a calendar
lead exactly on the minimum passes even when the subtraction lands a
few ULPs short; and the aggregated review is compliant only when both
finding lists are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_charging_protection_programme_applicability_logic as cp  # noqa: E402


def _geo_mission():
    return {
        "mission_id": "GEO-TELECOM-1",
        "orbit": "geo",
        "bus_voltage_v": 28.0,
        "exposed_dielectric_area_fraction": 0.35,
        "duration_years": 15.0,
        "has_ungrounded_conductive_element": False,
    }


def _benign_mission():
    return {
        "mission_id": "LEO-CUBESAT-7",
        "orbit": "equatorial_low_leo",
        "bus_voltage_v": 12.0,
        "exposed_dielectric_area_fraction": 0.02,
        "duration_years": 1.0,
        "has_ungrounded_conductive_element": False,
    }


def _full_sections(extra=()):
    sections = {
        name: "written" for name in cp.BASE_PROGRAMME_SECTIONS
    }
    for name in extra:
        sections[name] = "written"
    return sections


def _clean_approval():
    return {
        "approval_milestone": "srr",
        "approval_day": 100.0,
        "review_day": 200.0,
        "customer_approved": True,
    }


def _geo_case():
    return {
        "mission": _geo_mission(),
        "declared_sections": _full_sections(
            (cp.INTERNAL_CHARGING_SECTION,)
        ),
        "approval_record": _clean_approval(),
    }


class ChargingRegimeTest(unittest.TestCase):
    def test_geo_is_severe_on_both_paths(self):
        self.assertEqual(
            cp.charging_environment_regime("geo"),
            "severe_surface_and_internal",
        )

    def test_meo_is_severe_internal(self):
        self.assertEqual(
            cp.charging_environment_regime("meo"), "severe_internal"
        )

    def test_polar_leo_is_auroral(self):
        self.assertEqual(
            cp.charging_environment_regime("polar_leo"), "auroral_surface"
        )

    def test_interplanetary_is_moderate_surface(self):
        self.assertEqual(
            cp.charging_environment_regime("interplanetary"),
            "moderate_surface",
        )

    def test_equatorial_low_leo_is_benign(self):
        self.assertEqual(
            cp.charging_environment_regime("equatorial_low_leo"), "benign"
        )

    def test_internal_regimes_are_a_subset_of_all_regimes(self):
        self.assertTrue(
            cp.INTERNAL_CHARGING_REGIMES
            <= set(cp.ORBIT_CHARGING_REGIMES.values())
        )

    def test_unmapped_orbit_raises(self):
        with self.assertRaises(ValueError):
            cp.charging_environment_regime("halo_orbit")


class ApplicabilityTest(unittest.TestCase):
    def test_geo_mission_is_applicable(self):
        result = cp.programme_applicability(_geo_mission())
        self.assertTrue(result["applicable"])
        self.assertIn("charging_environment_regime", result["drivers"])

    def test_geo_mission_picks_up_dielectric_and_duration(self):
        drivers = cp.programme_applicability(_geo_mission())["drivers"]
        self.assertIn("exposed_external_dielectric", drivers)
        self.assertIn("long_duration_exposure", drivers)

    def test_benign_mission_has_no_drivers(self):
        result = cp.programme_applicability(_benign_mission())
        self.assertFalse(result["applicable"])
        self.assertEqual(result["drivers"], [])

    def test_dielectric_alone_does_not_apply_in_a_benign_regime(self):
        mission = _benign_mission()
        mission["exposed_dielectric_area_fraction"] = 0.5
        self.assertFalse(cp.programme_applicability(mission)["applicable"])

    def test_high_voltage_applies_even_in_a_benign_regime(self):
        mission = _benign_mission()
        mission["bus_voltage_v"] = 100.0
        result = cp.programme_applicability(mission)
        self.assertTrue(result["applicable"])
        self.assertEqual(
            result["drivers"], ["high_voltage_array_interaction"]
        )

    def test_voltage_exactly_on_threshold_applies(self):
        mission = _benign_mission()
        mission["bus_voltage_v"] = cp.HIGH_VOLTAGE_THRESHOLD_V
        self.assertTrue(cp.programme_applicability(mission)["applicable"])

    def test_voltage_just_below_threshold_does_not_apply(self):
        mission = _benign_mission()
        mission["bus_voltage_v"] = 54.0
        self.assertFalse(cp.programme_applicability(mission)["applicable"])

    def test_dielectric_fraction_exactly_on_threshold_counts(self):
        mission = _geo_mission()
        mission["exposed_dielectric_area_fraction"] = 0.3 - 0.2
        self.assertIn(
            "exposed_external_dielectric",
            cp.programme_applicability(mission)["drivers"],
        )

    def test_dielectric_fraction_below_threshold_is_not_a_driver(self):
        mission = _geo_mission()
        mission["exposed_dielectric_area_fraction"] = 0.02
        self.assertNotIn(
            "exposed_external_dielectric",
            cp.programme_applicability(mission)["drivers"],
        )

    def test_duration_exactly_on_threshold_counts(self):
        mission = _geo_mission()
        mission["duration_years"] = cp.LONG_DURATION_THRESHOLD_YEARS
        self.assertIn(
            "long_duration_exposure",
            cp.programme_applicability(mission)["drivers"],
        )

    def test_short_duration_is_not_a_driver(self):
        mission = _geo_mission()
        mission["duration_years"] = 2.0
        self.assertNotIn(
            "long_duration_exposure",
            cp.programme_applicability(mission)["drivers"],
        )

    def test_ungrounded_element_applies_on_its_own(self):
        mission = _benign_mission()
        mission["has_ungrounded_conductive_element"] = True
        result = cp.programme_applicability(mission)
        self.assertTrue(result["applicable"])
        self.assertEqual(result["drivers"], ["ungrounded_conductive_element"])

    def test_drivers_are_sorted(self):
        drivers = cp.programme_applicability(_geo_mission())["drivers"]
        self.assertEqual(drivers, sorted(drivers))

    def test_negative_bus_voltage_raises(self):
        mission = _geo_mission()
        mission["bus_voltage_v"] = -1.0
        with self.assertRaises(ValueError):
            cp.programme_applicability(mission)

    def test_dielectric_fraction_above_one_raises(self):
        mission = _geo_mission()
        mission["exposed_dielectric_area_fraction"] = 1.5
        with self.assertRaises(ValueError):
            cp.programme_applicability(mission)

    def test_negative_dielectric_fraction_raises(self):
        mission = _geo_mission()
        mission["exposed_dielectric_area_fraction"] = -0.1
        with self.assertRaises(ValueError):
            cp.programme_applicability(mission)

    def test_zero_duration_raises(self):
        mission = _geo_mission()
        mission["duration_years"] = 0.0
        with self.assertRaises(ValueError):
            cp.programme_applicability(mission)

    def test_unmapped_orbit_raises_in_applicability(self):
        mission = _geo_mission()
        mission["orbit"] = "halo_orbit"
        with self.assertRaises(ValueError):
            cp.programme_applicability(mission)


class RequiredSectionsTest(unittest.TestCase):
    def test_geo_requires_the_internal_charging_section(self):
        required = cp.required_programme_sections(
            cp.programme_applicability(_geo_mission())
        )
        self.assertIn(cp.INTERNAL_CHARGING_SECTION, required)

    def test_geo_does_not_require_the_array_interaction_section(self):
        required = cp.required_programme_sections(
            cp.programme_applicability(_geo_mission())
        )
        self.assertNotIn(cp.HIGH_VOLTAGE_SECTION, required)

    def test_auroral_regime_omits_the_internal_charging_section(self):
        mission = _geo_mission()
        mission["orbit"] = "polar_leo"
        required = cp.required_programme_sections(
            cp.programme_applicability(mission)
        )
        self.assertNotIn(cp.INTERNAL_CHARGING_SECTION, required)

    def test_high_voltage_adds_the_array_interaction_section(self):
        mission = _geo_mission()
        mission["bus_voltage_v"] = 100.0
        required = cp.required_programme_sections(
            cp.programme_applicability(mission)
        )
        self.assertIn(cp.HIGH_VOLTAGE_SECTION, required)

    def test_base_sections_are_always_required_when_applicable(self):
        required = cp.required_programme_sections(
            cp.programme_applicability(_geo_mission())
        )
        self.assertTrue(cp.BASE_PROGRAMME_SECTIONS <= required)

    def test_benign_mission_owes_only_a_justification(self):
        required = cp.required_programme_sections(
            cp.programme_applicability(_benign_mission())
        )
        self.assertEqual(
            required, frozenset({cp.NON_APPLICABILITY_SECTION})
        )

    def test_applicability_without_regime_raises(self):
        with self.assertRaises(ValueError):
            cp.required_programme_sections(
                {"applicable": True, "drivers": []}
            )


class MissingSectionsTest(unittest.TestCase):
    def test_complete_programme_has_no_gaps(self):
        required = cp.required_programme_sections(
            cp.programme_applicability(_geo_mission())
        )
        declared = _full_sections((cp.INTERNAL_CHARGING_SECTION,))
        self.assertEqual(
            cp.missing_programme_sections(declared, required), []
        )

    def test_absent_section_is_reported(self):
        required = cp.required_programme_sections(
            cp.programme_applicability(_geo_mission())
        )
        declared = _full_sections((cp.INTERNAL_CHARGING_SECTION,))
        del declared["esd_design_rules"]
        self.assertEqual(
            cp.missing_programme_sections(declared, required),
            ["esd_design_rules"],
        )

    def test_none_valued_section_counts_as_absent(self):
        required = cp.required_programme_sections(
            cp.programme_applicability(_geo_mission())
        )
        declared = _full_sections((cp.INTERNAL_CHARGING_SECTION,))
        declared[cp.INTERNAL_CHARGING_SECTION] = None
        self.assertEqual(
            cp.missing_programme_sections(declared, required),
            [cp.INTERNAL_CHARGING_SECTION],
        )

    def test_empty_section_counts_as_absent(self):
        required = cp.required_programme_sections(
            cp.programme_applicability(_geo_mission())
        )
        declared = _full_sections((cp.INTERNAL_CHARGING_SECTION,))
        declared["environment_definition"] = ""
        self.assertIn(
            "environment_definition",
            cp.missing_programme_sections(declared, required),
        )

    def test_result_is_sorted(self):
        required = cp.required_programme_sections(
            cp.programme_applicability(_geo_mission())
        )
        missing = cp.missing_programme_sections({}, required)
        self.assertEqual(missing, sorted(missing))
        self.assertEqual(len(missing), len(required))

    def test_non_mapping_declaration_raises(self):
        with self.assertRaises(ValueError):
            cp.missing_programme_sections(
                ["environment_definition"], frozenset({"esd_design_rules"})
            )


class MilestoneSequenceTest(unittest.TestCase):
    def test_mdr_is_first(self):
        self.assertEqual(cp.milestone_index("mdr"), 0)

    def test_srr_precedes_pdr(self):
        self.assertLess(cp.milestone_index("srr"), cp.milestone_index("pdr"))

    def test_cdr_follows_pdr(self):
        self.assertGreater(
            cp.milestone_index("cdr"), cp.milestone_index("pdr")
        )

    def test_orr_is_last(self):
        self.assertEqual(
            cp.milestone_index("orr"), len(cp.PROJECT_MILESTONE_SEQUENCE) - 1
        )

    def test_unknown_milestone_raises(self):
        with self.assertRaises(ValueError):
            cp.milestone_index("lrr")


class ApprovalLeadTest(unittest.TestCase):
    def test_lead_is_the_difference(self):
        self.assertAlmostEqual(
            cp.approval_lead_days(100.0, 200.0), 100.0, places=9
        )

    def test_approval_after_the_review_is_negative(self):
        self.assertLess(cp.approval_lead_days(250.0, 200.0), 0.0)


class ApprovalTimingTest(unittest.TestCase):
    def test_clean_approval_has_no_findings(self):
        self.assertEqual(cp.approval_timing_findings(_clean_approval()), [])

    def test_approval_at_pdr_is_reported(self):
        record = _clean_approval()
        record["approval_milestone"] = "pdr"
        issues = [f["issue"] for f in cp.approval_timing_findings(record)]
        self.assertIn("approval_milestone_not_before_pdr", issues)

    def test_approval_at_cdr_is_reported(self):
        record = _clean_approval()
        record["approval_milestone"] = "cdr"
        issues = [f["issue"] for f in cp.approval_timing_findings(record)]
        self.assertIn("approval_milestone_not_before_pdr", issues)

    def test_short_lead_is_reported(self):
        record = _clean_approval()
        record["approval_day"] = 190.0
        issues = [f["issue"] for f in cp.approval_timing_findings(record)]
        self.assertIn("approval_lead_below_minimum", issues)

    def test_lead_exactly_on_the_minimum_passes(self):
        record = _clean_approval()
        record["approval_day"] = 170.0
        self.assertEqual(cp.approval_timing_findings(record), [])

    def test_lead_short_by_representation_error_passes(self):
        record = _clean_approval()
        record["approval_day"] = 3.3
        record["review_day"] = 33.3
        self.assertLess(
            cp.approval_lead_days(
                record["approval_day"], record["review_day"]
            ),
            30.0,
        )
        self.assertEqual(cp.approval_timing_findings(record), [])

    def test_approval_after_the_review_is_reported(self):
        record = _clean_approval()
        record["approval_day"] = 250.0
        issues = [f["issue"] for f in cp.approval_timing_findings(record)]
        self.assertIn("approval_lead_below_minimum", issues)

    def test_unapproved_programme_is_reported(self):
        record = _clean_approval()
        record["customer_approved"] = False
        issues = [f["issue"] for f in cp.approval_timing_findings(record)]
        self.assertIn("customer_approval_not_granted", issues)

    def test_three_findings_can_coexist(self):
        record = {
            "approval_milestone": "cdr",
            "approval_day": 195.0,
            "review_day": 200.0,
            "customer_approved": False,
        }
        self.assertEqual(len(cp.approval_timing_findings(record)), 3)

    def test_raised_minimum_lead_can_fail_a_passing_record(self):
        record = _clean_approval()
        self.assertEqual(cp.approval_timing_findings(record, 30.0), [])
        self.assertEqual(len(cp.approval_timing_findings(record, 200.0)), 1)

    def test_negative_minimum_lead_raises(self):
        with self.assertRaises(ValueError):
            cp.approval_timing_findings(_clean_approval(), -1.0)

    def test_unknown_approval_milestone_raises(self):
        record = _clean_approval()
        record["approval_milestone"] = "lrr"
        with self.assertRaises(ValueError):
            cp.approval_timing_findings(record)


class AssessProgrammeTest(unittest.TestCase):
    def test_complete_geo_programme_is_compliant(self):
        result = cp.assess_charging_protection_programme(_geo_case())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["mission_id"], "GEO-TELECOM-1")
        self.assertTrue(result["applicable"])

    def test_missing_section_breaks_compliance(self):
        case = _geo_case()
        del case["declared_sections"]["verification_and_test_plan"]
        result = cp.assess_charging_protection_programme(case)
        self.assertFalse(result["compliant"])
        self.assertEqual(
            result["section_findings"][0]["missing"],
            ["verification_and_test_plan"],
        )

    def test_late_approval_breaks_compliance(self):
        case = _geo_case()
        case["approval_record"]["approval_milestone"] = "cdr"
        result = cp.assess_charging_protection_programme(case)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["timing_findings"]), 1)

    def test_benign_mission_with_justification_is_compliant(self):
        case = {
            "mission": _benign_mission(),
            "declared_sections": {
                cp.NON_APPLICABILITY_SECTION: "no driver present"
            },
            "approval_record": {
                "approval_milestone": "orr",
                "approval_day": 400.0,
                "review_day": 200.0,
                "customer_approved": False,
            },
        }
        result = cp.assess_charging_protection_programme(case)
        self.assertTrue(result["compliant"])
        self.assertFalse(result["applicable"])
        self.assertEqual(result["timing_findings"], [])

    def test_benign_mission_without_justification_is_not_compliant(self):
        case = {
            "mission": _benign_mission(),
            "declared_sections": {},
            "approval_record": _clean_approval(),
        }
        result = cp.assess_charging_protection_programme(case)
        self.assertFalse(result["compliant"])
        self.assertEqual(
            result["section_findings"][0]["missing"],
            [cp.NON_APPLICABILITY_SECTION],
        )

    def test_required_sections_are_reported_sorted(self):
        result = cp.assess_charging_protection_programme(_geo_case())
        self.assertEqual(
            result["required_sections"], sorted(result["required_sections"])
        )

    def test_minimum_lead_flows_through_aggregate(self):
        case = _geo_case()
        self.assertTrue(
            cp.assess_charging_protection_programme(case, 30.0)["compliant"]
        )
        self.assertFalse(
            cp.assess_charging_protection_programme(case, 300.0)["compliant"]
        )

    def test_high_voltage_geo_needs_both_extra_sections(self):
        case = _geo_case()
        case["mission"]["bus_voltage_v"] = 100.0
        result = cp.assess_charging_protection_programme(case)
        self.assertFalse(result["compliant"])
        self.assertEqual(
            result["section_findings"][0]["missing"],
            [cp.HIGH_VOLTAGE_SECTION],
        )


if __name__ == "__main__":
    unittest.main()
