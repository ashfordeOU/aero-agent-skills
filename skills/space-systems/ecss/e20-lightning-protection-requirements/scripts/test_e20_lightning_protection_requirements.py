#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.3.2.4 lightning
protection requirements.

Exercises scripts/e20_lightning_protection_requirements_logic.py
(stdlib unittest, offline). Contract: a coupling mechanism maps to
exactly one effect family and an unrecognized mechanism raises; an
external region maps to a lightning attachment zone and an unzoned
region raises; each zone carries a fixed provision set; the adiabatic
conductor cross-section is the square root of the stroke action
integral over the material action constant; the induced bundle
transient is the inductive term plus the resistive term; the transient
margin is twenty times the base-ten logarithm of the design level over
the induced level and a margin exactly on the requirement passes; a
function whose deviation exceeds its allowance or whose recovery needs
intervention is reported; and the aggregated review is compliant only
when every list is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_lightning_protection_requirements_logic as lp  # noqa: E402


def _clean_region():
    return {
        "region_id": "STR-NOSE-01",
        "region": "nose_cap",
        "provisions": [
            "conductive_attachment_path",
            "arc_root_thickness_margin",
        ],
        "conductor_area_mm2": 20.0,
        "conductor_material": "copper",
        "stroke_action_integral_a2s": 2.0e6,
    }


def _clean_bundle():
    return {
        "bundle_id": "HARN-AV-01",
        "mutual_inductance_h": 2.0e-9,
        "current_rate_a_per_s": 1.4e11,
        "structure_resistance_ohm": 5.0e-5,
        "peak_current_a": 2.0e5,
        "equipment_design_level_v": 1500.0,
    }


def _clean_functions():
    return [
        {
            "function_id": "AOCS-RATE-SENSE",
            "parameter_deviation": 0.01,
            "allowed_deviation": 0.05,
            "self_recovering": True,
        }
    ]


def _clean_system():
    return {
        "system_id": "SC-LV-STACK",
        "regions": [_clean_region()],
        "bundles": [_clean_bundle()],
        "functions": _clean_functions(),
    }


class CategorizeLightningEffectTest(unittest.TestCase):
    def test_arc_root_attachment_is_direct(self):
        self.assertEqual(
            lp.categorize_lightning_effect("arc_root_attachment"), "direct"
        )

    def test_resistive_burn_through_is_direct(self):
        self.assertEqual(
            lp.categorize_lightning_effect("resistive_burn_through"), "direct"
        )

    def test_acoustic_shock_is_direct(self):
        self.assertEqual(
            lp.categorize_lightning_effect("acoustic_shock_overpressure"),
            "direct",
        )

    def test_aperture_field_coupling_is_indirect(self):
        self.assertEqual(
            lp.categorize_lightning_effect("aperture_field_coupling"),
            "indirect",
        )

    def test_bundle_inductive_coupling_is_indirect(self):
        self.assertEqual(
            lp.categorize_lightning_effect("cable_bundle_inductive_coupling"),
            "indirect",
        )

    def test_ground_potential_rise_is_indirect(self):
        self.assertEqual(
            lp.categorize_lightning_effect("ground_potential_rise"), "indirect"
        )

    def test_families_do_not_overlap(self):
        self.assertEqual(
            lp.DIRECT_EFFECT_MECHANISMS & lp.INDIRECT_EFFECT_MECHANISMS,
            frozenset(),
        )

    def test_unknown_mechanism_raises(self):
        with self.assertRaises(ValueError):
            lp.categorize_lightning_effect("micrometeoroid_impact")


class AttachmentZoneTest(unittest.TestCase):
    def test_nose_cap_is_zone_1a(self):
        self.assertEqual(lp.attachment_zone("nose_cap"), "zone_1a")

    def test_trailing_edge_is_zone_1b(self):
        self.assertEqual(
            lp.attachment_zone("trailing_edge_exit_point"), "zone_1b"
        )

    def test_intertank_skin_is_zone_2a(self):
        self.assertEqual(lp.attachment_zone("intertank_skin"), "zone_2a")

    def test_umbilical_panel_is_zone_2b(self):
        self.assertEqual(lp.attachment_zone("umbilical_panel"), "zone_2b")

    def test_interior_bay_is_zone_3(self):
        self.assertEqual(
            lp.attachment_zone("protected_interior_bay"), "zone_3"
        )

    def test_unzoned_region_raises(self):
        with self.assertRaises(ValueError):
            lp.attachment_zone("solar_array_hinge")


class ZoneProvisionsTest(unittest.TestCase):
    def test_zone_1b_adds_dwell_provision(self):
        self.assertIn(
            "hang_on_dwell_provision", lp.required_zone_provisions("zone_1b")
        )

    def test_zone_1a_has_no_dwell_provision(self):
        self.assertNotIn(
            "hang_on_dwell_provision", lp.required_zone_provisions("zone_1a")
        )

    def test_zone_2a_requires_diverter(self):
        self.assertIn(
            "diverter_or_conductive_coating",
            lp.required_zone_provisions("zone_2a"),
        )

    def test_zone_3_requires_conduction_path_only(self):
        self.assertEqual(
            lp.required_zone_provisions("zone_3"),
            frozenset({"current_conduction_path"}),
        )

    def test_unknown_zone_raises(self):
        with self.assertRaises(ValueError):
            lp.required_zone_provisions("zone_9")


class ConductorAreaTest(unittest.TestCase):
    def test_copper_area_for_severe_stroke(self):
        self.assertAlmostEqual(
            lp.required_conductor_area_mm2(2.0e6, "copper"),
            math.sqrt(2.0e6) / 143.0,
            places=9,
        )

    def test_aluminium_needs_more_area_than_copper(self):
        self.assertGreater(
            lp.required_conductor_area_mm2(2.0e6, "aluminium"),
            lp.required_conductor_area_mm2(2.0e6, "copper"),
        )

    def test_area_scales_with_root_of_action_integral(self):
        single = lp.required_conductor_area_mm2(1.0e6, "copper")
        quadruple = lp.required_conductor_area_mm2(4.0e6, "copper")
        self.assertAlmostEqual(quadruple / single, 2.0, places=9)

    def test_zero_action_integral_raises(self):
        with self.assertRaises(ValueError):
            lp.required_conductor_area_mm2(0.0, "copper")

    def test_negative_action_integral_raises(self):
        with self.assertRaises(ValueError):
            lp.required_conductor_area_mm2(-1.0, "copper")

    def test_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            lp.required_conductor_area_mm2(2.0e6, "kapton")


class DirectEffectFindingsTest(unittest.TestCase):
    def test_clean_region_has_no_findings(self):
        self.assertEqual(lp.direct_effect_findings(_clean_region()), [])

    def test_missing_provision_is_reported(self):
        case = _clean_region()
        case["provisions"] = ["conductive_attachment_path"]
        findings = lp.direct_effect_findings(case)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "missing_direct_effect_provision"
        )
        self.assertEqual(findings[0]["missing"], ["arc_root_thickness_margin"])

    def test_undersized_conductor_is_reported(self):
        case = _clean_region()
        case["conductor_area_mm2"] = 1.0
        issues = [f["issue"] for f in lp.direct_effect_findings(case)]
        self.assertIn("conductor_area_below_action_integral_demand", issues)

    def test_conductor_area_exactly_at_demand_passes(self):
        case = _clean_region()
        case["conductor_area_mm2"] = math.sqrt(2.0e6) / 143.0
        self.assertEqual(lp.direct_effect_findings(case), [])

    def test_both_direct_findings_can_coexist(self):
        case = _clean_region()
        case["provisions"] = []
        case["conductor_area_mm2"] = 0.5
        self.assertEqual(len(lp.direct_effect_findings(case)), 2)

    def test_zero_conductor_area_raises(self):
        case = _clean_region()
        case["conductor_area_mm2"] = 0.0
        with self.assertRaises(ValueError):
            lp.direct_effect_findings(case)

    def test_unzoned_region_raises_in_findings(self):
        case = _clean_region()
        case["region"] = "antenna_boom"
        with self.assertRaises(ValueError):
            lp.direct_effect_findings(case)


class TransientTermsTest(unittest.TestCase):
    def test_inductive_term(self):
        self.assertAlmostEqual(
            lp.inductive_transient_v(2.0e-9, 1.4e11), 280.0, places=9
        )

    def test_zero_mutual_inductance_gives_zero_volts(self):
        self.assertAlmostEqual(
            lp.inductive_transient_v(0.0, 1.4e11), 0.0, places=9
        )

    def test_resistive_term(self):
        self.assertAlmostEqual(
            lp.resistive_transient_v(5.0e-5, 2.0e5), 10.0, places=9
        )

    def test_total_is_the_sum_of_terms(self):
        self.assertAlmostEqual(
            lp.induced_transient_level_v(_clean_bundle()), 290.0, places=9
        )

    def test_negative_mutual_inductance_raises(self):
        with self.assertRaises(ValueError):
            lp.inductive_transient_v(-1.0e-9, 1.4e11)

    def test_zero_current_rate_raises(self):
        with self.assertRaises(ValueError):
            lp.inductive_transient_v(2.0e-9, 0.0)

    def test_negative_structure_resistance_raises(self):
        with self.assertRaises(ValueError):
            lp.resistive_transient_v(-1.0e-5, 2.0e5)

    def test_zero_peak_current_raises(self):
        with self.assertRaises(ValueError):
            lp.resistive_transient_v(5.0e-5, 0.0)


class TransientMarginTest(unittest.TestCase):
    def test_factor_of_two_is_about_six_decibels(self):
        self.assertAlmostEqual(
            lp.transient_margin_db(580.0, 290.0), 6.0206, places=4
        )

    def test_equal_levels_give_zero_margin(self):
        self.assertAlmostEqual(
            lp.transient_margin_db(290.0, 290.0), 0.0, places=9
        )

    def test_design_level_below_induced_is_negative(self):
        self.assertLess(lp.transient_margin_db(145.0, 290.0), 0.0)

    def test_zero_design_level_raises(self):
        with self.assertRaises(ValueError):
            lp.transient_margin_db(0.0, 290.0)

    def test_zero_induced_level_raises(self):
        with self.assertRaises(ValueError):
            lp.transient_margin_db(580.0, 0.0)


class IndirectEffectFindingsTest(unittest.TestCase):
    def test_clean_bundle_has_no_findings(self):
        self.assertEqual(lp.indirect_effect_findings(_clean_bundle()), [])

    def test_thin_margin_is_reported(self):
        case = _clean_bundle()
        case["equipment_design_level_v"] = 400.0
        findings = lp.indirect_effect_findings(case)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "transient_margin_below_requirement"
        )
        self.assertAlmostEqual(findings[0]["induced_level_v"], 290.0, places=9)

    def test_margin_exactly_on_requirement_passes(self):
        case = _clean_bundle()
        case["equipment_design_level_v"] = 290.0 * (10.0 ** (6.0 / 20.0))
        self.assertEqual(lp.indirect_effect_findings(case), [])

    def test_raised_requirement_can_fail_a_passing_bundle(self):
        case = _clean_bundle()
        case["equipment_design_level_v"] = 600.0
        self.assertEqual(lp.indirect_effect_findings(case, 6.0), [])
        self.assertEqual(len(lp.indirect_effect_findings(case, 12.0)), 1)

    def test_negative_required_margin_raises(self):
        with self.assertRaises(ValueError):
            lp.indirect_effect_findings(_clean_bundle(), -1.0)

    def test_zero_design_level_raises_in_findings(self):
        case = _clean_bundle()
        case["equipment_design_level_v"] = 0.0
        with self.assertRaises(ValueError):
            lp.indirect_effect_findings(case)


class PerformanceDegradationTest(unittest.TestCase):
    def test_clean_functions_have_no_findings(self):
        self.assertEqual(
            lp.performance_degradation_findings(_clean_functions()), []
        )

    def test_deviation_beyond_allowance_is_reported(self):
        functions = _clean_functions()
        functions[0]["parameter_deviation"] = 0.2
        findings = lp.performance_degradation_findings(functions)
        self.assertEqual(
            findings[0]["issue"], "performance_degraded_beyond_allowance"
        )

    def test_negative_deviation_uses_magnitude(self):
        functions = _clean_functions()
        functions[0]["parameter_deviation"] = -0.2
        self.assertEqual(len(lp.performance_degradation_findings(functions)), 1)

    def test_deviation_exactly_on_allowance_passes(self):
        functions = _clean_functions()
        functions[0]["parameter_deviation"] = 0.1 + 0.2
        functions[0]["allowed_deviation"] = 0.3
        self.assertEqual(lp.performance_degradation_findings(functions), [])

    def test_intervention_recovery_is_reported(self):
        functions = _clean_functions()
        functions[0]["self_recovering"] = False
        findings = lp.performance_degradation_findings(functions)
        self.assertEqual(findings[0]["issue"], "recovery_requires_intervention")

    def test_out_of_band_deviation_reports_once(self):
        functions = _clean_functions()
        functions[0]["parameter_deviation"] = 0.9
        functions[0]["self_recovering"] = False
        self.assertEqual(len(lp.performance_degradation_findings(functions)), 1)

    def test_empty_function_list_has_no_findings(self):
        self.assertEqual(lp.performance_degradation_findings([]), [])

    def test_negative_allowance_raises(self):
        functions = _clean_functions()
        functions[0]["allowed_deviation"] = -0.1
        with self.assertRaises(ValueError):
            lp.performance_degradation_findings(functions)


class AssessLightningProtectionTest(unittest.TestCase):
    def test_clean_system_is_compliant(self):
        result = lp.assess_lightning_protection(_clean_system())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["system_id"], "SC-LV-STACK")

    def test_direct_finding_breaks_compliance(self):
        system = _clean_system()
        system["regions"][0]["provisions"] = []
        result = lp.assess_lightning_protection(system)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["direct_effect_findings"]), 1)

    def test_indirect_finding_breaks_compliance(self):
        system = _clean_system()
        system["bundles"][0]["equipment_design_level_v"] = 300.0
        result = lp.assess_lightning_protection(system)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["indirect_effect_findings"]), 1)

    def test_performance_finding_breaks_compliance(self):
        system = _clean_system()
        system["functions"][0]["self_recovering"] = False
        result = lp.assess_lightning_protection(system)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["performance_findings"]), 1)

    def test_empty_system_is_vacuously_compliant(self):
        result = lp.assess_lightning_protection(
            {"system_id": "EMPTY", "regions": [], "bundles": [],
             "functions": []}
        )
        self.assertTrue(result["compliant"])

    def test_required_margin_flows_through_aggregate(self):
        system = _clean_system()
        self.assertTrue(
            lp.assess_lightning_protection(system, 6.0)["compliant"]
        )
        self.assertFalse(
            lp.assess_lightning_protection(system, 20.0)["compliant"]
        )


if __name__ == "__main__":
    unittest.main()
