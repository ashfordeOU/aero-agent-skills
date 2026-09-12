#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.3.8.1 electrical
bonding of structure and equipment.

Exercises scripts/e20_electrical_bonding_conformance_logic.py (stdlib
unittest, offline). Contract: a bond kind maps to exactly one bonding
function and an unrecognized kind raises; each function carries a
resistance window, with a floor as well as a ceiling for the
charge-bleed path; a strap's direct-current resistance is the bulk term
plus the contact resistance of every joint, and a resistance landing on
the ceiling only through representation error stays compliant; a
radio-frequency reference bond is judged on its length-to-width ratio
and on the quadrature of resistance and strap reactance at the
frequency of interest; the galvanic screen takes the anodic-index
difference against an environment-dependent limit; a current-carrying
bond's temperature rise is the clearing-time energy over its thermal
mass; a missing strap geometry or fault case is reported rather than
assumed; and the aggregated review conforms only when every list is
empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_electrical_bonding_conformance_logic as bc  # noqa: E402


def _clean_power_bond():
    """A fault-current return bond that satisfies every clause 6.3.8.1
    check."""
    return {
        "bond_id": "BND-PWR-01",
        "bond_kind": "fault_current_return",
        "material_a": "aluminium_alloy",
        "material_b": "cadmium_plate",
        "environment": "normal",
        "strap": {
            "resistivity_ohm_m": 2.82e-8,
            "length_m": 0.10,
            "width_m": 0.020,
            "cross_section_m2": 2.0e-5,
            "contact_resistance_ohm": 5.0e-4,
            "joints": 2,
        },
        "fault_case": {
            "current_a": 20.0,
            "clearing_time_s": 0.05,
            "thermal_mass_j_per_k": 4.86,
        },
    }


def _clean_rf_bond():
    """A shield-termination bond that satisfies every clause 6.3.8.1
    check."""
    return {
        "bond_id": "BND-RF-01",
        "bond_kind": "shield_termination",
        "material_a": "copper",
        "material_b": "stainless_steel_passivated",
        "environment": "normal",
        "strap": {
            "resistivity_ohm_m": 1.68e-8,
            "length_m": 0.05,
            "width_m": 0.025,
            "cross_section_m2": 1.25e-5,
            "contact_resistance_ohm": 2.0e-4,
            "joints": 2,
        },
        "analysis_frequency_hz": 1.0e6,
    }


def _clean_bleed_bond():
    """A blanket charge-bleed path that satisfies every clause 6.3.8.1
    check."""
    return {
        "bond_id": "BND-ESD-01",
        "bond_kind": "thermal_blanket_bleed",
        "material_a": "aluminium_alloy",
        "material_b": "chromate_conversion_coating",
        "environment": "controlled",
        "measured_resistance_ohm": 1.0e7,
    }


class CategorizeBondTest(unittest.TestCase):
    def test_fault_current_return_is_a_power_fault_return(self):
        self.assertEqual(
            bc.categorize_bond("fault_current_return"), "power_fault_return"
        )

    def test_shield_termination_is_a_radio_frequency_reference(self):
        self.assertEqual(
            bc.categorize_bond("shield_termination"),
            "radio_frequency_reference",
        )

    def test_lightning_down_conductor_is_a_surge_path(self):
        self.assertEqual(
            bc.categorize_bond("lightning_down_conductor"), "surge_path"
        )

    def test_equipment_mounting_face_is_a_mechanical_interface(self):
        self.assertEqual(
            bc.categorize_bond("equipment_mounting_face"),
            "mechanical_interface",
        )

    def test_thermal_blanket_bleed_is_an_electrostatic_bleed(self):
        self.assertEqual(
            bc.categorize_bond("thermal_blanket_bleed"), "electrostatic_bleed"
        )

    def test_every_bond_kind_lands_in_a_known_category(self):
        for kind in bc.BOND_CATEGORY_BY_KIND:
            self.assertIn(bc.categorize_bond(kind), bc.BOND_CATEGORIES)

    def test_unknown_bond_kind_raises(self):
        with self.assertRaises(ValueError):
            bc.categorize_bond("velcro_patch")

    def test_none_bond_kind_raises(self):
        with self.assertRaises(ValueError):
            bc.categorize_bond(None)


class BondResistanceWindowTest(unittest.TestCase):
    def test_power_fault_return_window_has_no_floor(self):
        floor_ohm, ceiling_ohm = bc.bond_resistance_window_ohm(
            "power_fault_return"
        )
        self.assertAlmostEqual(floor_ohm, 0.0, places=15)
        self.assertAlmostEqual(ceiling_ohm, 2.5e-3, places=15)

    def test_charge_bleed_window_has_a_floor_and_a_ceiling(self):
        floor_ohm, ceiling_ohm = bc.bond_resistance_window_ohm(
            "electrostatic_bleed"
        )
        self.assertGreater(floor_ohm, 0.0)
        self.assertGreater(ceiling_ohm, floor_ohm)

    def test_surge_path_is_allowed_more_than_a_fault_return(self):
        self.assertGreater(
            bc.bond_resistance_window_ohm("surge_path")[1],
            bc.bond_resistance_window_ohm("power_fault_return")[1],
        )

    def test_every_category_carries_a_window(self):
        for category in bc.BOND_CATEGORIES:
            floor_ohm, ceiling_ohm = bc.bond_resistance_window_ohm(category)
            self.assertGreaterEqual(floor_ohm, 0.0)
            self.assertGreater(ceiling_ohm, floor_ohm)

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            bc.bond_resistance_window_ohm("thermal_strap")


class StrapDcResistanceTest(unittest.TestCase):
    def test_bulk_term_is_resistivity_times_length_over_area(self):
        self.assertAlmostEqual(
            bc.strap_dc_resistance_ohm(2.0e-8, 0.1, 1.0e-5, 0.0, 0),
            2.0e-4,
            places=15,
        )

    def test_each_joint_adds_its_contact_resistance(self):
        self.assertAlmostEqual(
            bc.strap_dc_resistance_ohm(2.0e-8, 0.1, 1.0e-5, 5.0e-4, 2),
            2.0e-4 + 1.0e-3,
            places=15,
        )

    def test_joints_default_to_two(self):
        self.assertAlmostEqual(
            bc.strap_dc_resistance_ohm(2.0e-8, 0.1, 1.0e-5, 5.0e-4),
            bc.strap_dc_resistance_ohm(2.0e-8, 0.1, 1.0e-5, 5.0e-4, 2),
            places=15,
        )

    def test_short_strap_is_dominated_by_its_joints(self):
        bulk_only = bc.strap_dc_resistance_ohm(2.82e-8, 0.05, 2.0e-5, 0.0, 0)
        with_joints = bc.strap_dc_resistance_ohm(
            2.82e-8, 0.05, 2.0e-5, 5.0e-4, 2
        )
        self.assertGreater(with_joints - bulk_only, bulk_only)

    def test_zero_length_leaves_only_the_joints(self):
        self.assertAlmostEqual(
            bc.strap_dc_resistance_ohm(2.0e-8, 0.0, 1.0e-5, 3.0e-4, 2),
            6.0e-4,
            places=15,
        )

    def test_negative_resistivity_raises(self):
        with self.assertRaises(ValueError):
            bc.strap_dc_resistance_ohm(-1.0e-8, 0.1, 1.0e-5)

    def test_negative_length_raises(self):
        with self.assertRaises(ValueError):
            bc.strap_dc_resistance_ohm(2.0e-8, -0.1, 1.0e-5)

    def test_zero_cross_section_raises(self):
        with self.assertRaises(ValueError):
            bc.strap_dc_resistance_ohm(2.0e-8, 0.1, 0.0)

    def test_negative_contact_resistance_raises(self):
        with self.assertRaises(ValueError):
            bc.strap_dc_resistance_ohm(2.0e-8, 0.1, 1.0e-5, -1.0e-4)

    def test_negative_joint_count_raises(self):
        with self.assertRaises(ValueError):
            bc.strap_dc_resistance_ohm(2.0e-8, 0.1, 1.0e-5, 1.0e-4, -1)

    def test_non_integer_joint_count_raises(self):
        with self.assertRaises(ValueError):
            bc.strap_dc_resistance_ohm(2.0e-8, 0.1, 1.0e-5, 1.0e-4, 2.5)


class StrapGeometryTest(unittest.TestCase):
    def test_ratio_is_length_over_width(self):
        self.assertAlmostEqual(
            bc.strap_length_to_width_ratio(0.10, 0.025), 4.0, places=12
        )

    def test_square_strap_has_unit_ratio(self):
        self.assertAlmostEqual(
            bc.strap_length_to_width_ratio(0.02, 0.02), 1.0, places=12
        )

    def test_zero_width_raises(self):
        with self.assertRaises(ValueError):
            bc.strap_length_to_width_ratio(0.1, 0.0)

    def test_zero_length_raises(self):
        with self.assertRaises(ValueError):
            bc.strap_length_to_width_ratio(0.0, 0.02)

    def test_inductance_matches_the_thin_strap_expression(self):
        expected = 2.0e-7 * 0.05 * (math.log(4.0) + 0.5)
        self.assertAlmostEqual(
            bc.strap_inductance_h(0.05, 0.025), expected, places=18
        )

    def test_inductance_grows_with_length(self):
        self.assertGreater(
            bc.strap_inductance_h(0.20, 0.025),
            bc.strap_inductance_h(0.05, 0.025),
        )

    def test_widening_a_strap_helps_only_logarithmically(self):
        narrow = bc.strap_inductance_h(0.10, 0.010)
        wide = bc.strap_inductance_h(0.10, 0.040)
        self.assertGreater(narrow, wide)
        self.assertLess(narrow / wide, 2.0)

    def test_strap_shorter_than_it_is_wide_raises(self):
        with self.assertRaises(ValueError):
            bc.strap_inductance_h(0.01, 0.02)


class StrapImpedanceTest(unittest.TestCase):
    def test_at_zero_frequency_impedance_is_the_resistance(self):
        self.assertAlmostEqual(
            bc.strap_impedance_ohm(2.0e-3, 2.0e-8, 0.0), 2.0e-3, places=15
        )

    def test_reactance_dominates_at_high_frequency(self):
        impedance = bc.strap_impedance_ohm(1.0e-3, 2.0e-8, 1.0e8)
        self.assertGreater(impedance, 10.0 * 1.0e-3)

    def test_quadrature_combination_is_used(self):
        expected = math.sqrt(3.0 ** 2 + 4.0 ** 2)
        inductance_h = 4.0 / (2.0 * math.pi * 1.0e6)
        self.assertAlmostEqual(
            bc.strap_impedance_ohm(3.0, inductance_h, 1.0e6),
            expected,
            places=9,
        )

    def test_impedance_rises_monotonically_with_frequency(self):
        values = [
            bc.strap_impedance_ohm(1.0e-3, 2.0e-8, f)
            for f in (1.0e4, 1.0e6, 1.0e8)
        ]
        for lower, higher in zip(values, values[1:]):
            self.assertLess(lower, higher)

    def test_negative_resistance_raises(self):
        with self.assertRaises(ValueError):
            bc.strap_impedance_ohm(-1.0, 2.0e-8, 1.0e6)

    def test_negative_inductance_raises(self):
        with self.assertRaises(ValueError):
            bc.strap_impedance_ohm(1.0, -2.0e-8, 1.0e6)

    def test_negative_frequency_raises(self):
        with self.assertRaises(ValueError):
            bc.strap_impedance_ohm(1.0, 2.0e-8, -1.0)


class GalvanicIndexTest(unittest.TestCase):
    def test_identical_materials_have_no_difference(self):
        self.assertAlmostEqual(
            bc.galvanic_index_difference_v("copper", "copper"), 0.0, places=12
        )

    def test_difference_is_symmetric(self):
        self.assertAlmostEqual(
            bc.galvanic_index_difference_v("copper", "aluminium_alloy"),
            bc.galvanic_index_difference_v("aluminium_alloy", "copper"),
            places=12,
        )

    def test_magnesium_against_gold_is_the_widest_couple(self):
        widest = bc.galvanic_index_difference_v("magnesium_alloy", "gold")
        for metal in bc.GALVANIC_ANODIC_INDEX_V:
            self.assertLessEqual(
                bc.galvanic_index_difference_v(metal, "gold"), widest
            )

    def test_aluminium_to_cadmium_is_a_deliberately_close_couple(self):
        self.assertAlmostEqual(
            bc.galvanic_index_difference_v("aluminium_alloy", "cadmium_plate"),
            0.15,
            places=9,
        )

    def test_unknown_first_material_raises(self):
        with self.assertRaises(ValueError):
            bc.galvanic_index_difference_v("unobtainium", "copper")

    def test_unknown_second_material_raises(self):
        with self.assertRaises(ValueError):
            bc.galvanic_index_difference_v("copper", "unobtainium")

    def test_environment_limits_tighten_from_controlled_to_harsh(self):
        self.assertGreater(
            bc.MAX_GALVANIC_DIFFERENCE_V["controlled"],
            bc.MAX_GALVANIC_DIFFERENCE_V["normal"],
        )
        self.assertGreater(
            bc.MAX_GALVANIC_DIFFERENCE_V["normal"],
            bc.MAX_GALVANIC_DIFFERENCE_V["harsh"],
        )


class FaultTemperatureRiseTest(unittest.TestCase):
    def test_rise_is_energy_over_thermal_mass(self):
        self.assertAlmostEqual(
            bc.fault_temperature_rise_k(10.0, 2.0e-3, 0.1, 2.0),
            10.0 * 10.0 * 2.0e-3 * 0.1 / 2.0,
            places=15,
        )

    def test_rise_scales_with_the_square_of_the_current(self):
        single = bc.fault_temperature_rise_k(10.0, 2.0e-3, 0.1, 2.0)
        doubled = bc.fault_temperature_rise_k(20.0, 2.0e-3, 0.1, 2.0)
        self.assertAlmostEqual(doubled, 4.0 * single, places=12)

    def test_zero_current_deposits_no_energy(self):
        self.assertAlmostEqual(
            bc.fault_temperature_rise_k(0.0, 2.0e-3, 0.1, 2.0), 0.0, places=15
        )

    def test_zero_clearing_time_deposits_no_energy(self):
        self.assertAlmostEqual(
            bc.fault_temperature_rise_k(10.0, 2.0e-3, 0.0, 2.0), 0.0, places=15
        )

    def test_negative_current_raises(self):
        with self.assertRaises(ValueError):
            bc.fault_temperature_rise_k(-1.0, 2.0e-3, 0.1, 2.0)

    def test_negative_clearing_time_raises(self):
        with self.assertRaises(ValueError):
            bc.fault_temperature_rise_k(10.0, 2.0e-3, -0.1, 2.0)

    def test_zero_thermal_mass_raises(self):
        with self.assertRaises(ValueError):
            bc.fault_temperature_rise_k(10.0, 2.0e-3, 0.1, 0.0)


class ResolveBondResistanceTest(unittest.TestCase):
    def test_measured_value_is_preferred(self):
        bond = _clean_power_bond()
        bond["measured_resistance_ohm"] = 1.9e-3
        self.assertAlmostEqual(
            bc.resolve_bond_resistance_ohm(bond), 1.9e-3, places=15
        )

    def test_geometry_is_used_when_no_measurement_is_on_record(self):
        bond = _clean_power_bond()
        self.assertAlmostEqual(
            bc.resolve_bond_resistance_ohm(bond),
            2.82e-8 * 0.10 / 2.0e-5 + 2 * 5.0e-4,
            places=15,
        )

    def test_a_measurement_of_zero_ohm_is_still_a_measurement(self):
        bond = _clean_bleed_bond()
        bond["measured_resistance_ohm"] = 0.0
        self.assertAlmostEqual(
            bc.resolve_bond_resistance_ohm(bond), 0.0, places=15
        )

    def test_negative_measurement_raises(self):
        bond = _clean_power_bond()
        bond["measured_resistance_ohm"] = -1.0e-3
        with self.assertRaises(ValueError):
            bc.resolve_bond_resistance_ohm(bond)

    def test_neither_measurement_nor_geometry_raises(self):
        with self.assertRaises(ValueError):
            bc.resolve_bond_resistance_ohm(
                {"bond_id": "X", "bond_kind": "fault_current_return"}
            )


class ResistanceFindingsTest(unittest.TestCase):
    def test_resistance_inside_the_window_is_clean(self):
        self.assertEqual(
            bc.resistance_findings("B1", "power_fault_return", 1.0e-3), []
        )

    def test_resistance_exactly_on_the_ceiling_is_compliant(self):
        self.assertEqual(
            bc.resistance_findings("B1", "power_fault_return", 2.5e-3), []
        )

    def test_representation_error_on_the_ceiling_is_absorbed(self):
        # Bulk plus joints lands two units in the last place above the
        # 2.5 milliohm ceiling; the bond is physically on the limit.
        resistance_ohm = bc.strap_dc_resistance_ohm(
            2.82e-8, 0.07, 5.0e-6, 0.0010526, 2
        )
        self.assertGreater(resistance_ohm, 2.5e-3)
        self.assertEqual(
            bc.resistance_findings("B1", "power_fault_return", resistance_ohm),
            [],
        )

    def test_resistance_above_the_ceiling_is_a_finding(self):
        findings = bc.resistance_findings("B1", "power_fault_return", 5.0e-3)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "bond_resistance_above_ceiling"
        )

    def test_charge_bleed_path_below_its_floor_is_a_finding(self):
        findings = bc.resistance_findings("B2", "electrostatic_bleed", 1.0e3)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "bond_resistance_below_floor")

    def test_charge_bleed_path_above_its_ceiling_is_a_finding(self):
        findings = bc.resistance_findings("B2", "electrostatic_bleed", 1.0e11)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "bond_resistance_above_ceiling")

    def test_charge_bleed_path_inside_its_window_is_clean(self):
        self.assertEqual(
            bc.resistance_findings("B2", "electrostatic_bleed", 1.0e7), []
        )

    def test_negative_resistance_raises(self):
        with self.assertRaises(ValueError):
            bc.resistance_findings("B1", "power_fault_return", -1.0e-3)


class ImpedanceFindingsTest(unittest.TestCase):
    def test_short_wide_strap_is_clean(self):
        bond = _clean_rf_bond()
        self.assertEqual(bc.impedance_findings("B1", bond, 4.672e-4), [])

    def test_long_thin_strap_breaches_ratio_and_impedance(self):
        bond = _clean_rf_bond()
        bond["strap"]["length_m"] = 0.30
        bond["strap"]["width_m"] = 0.020
        issues = [
            f["issue"] for f in bc.impedance_findings("B1", bond, 4.672e-4)
        ]
        self.assertIn("strap_length_to_width_ratio_above_limit", issues)
        self.assertIn("rf_bond_impedance_above_limit", issues)

    def test_ratio_exactly_on_the_geometry_limit_is_compliant(self):
        bond = _clean_rf_bond()
        bond["strap"]["length_m"] = 0.125
        bond["strap"]["width_m"] = 0.025
        issues = [
            f["issue"] for f in bc.impedance_findings("B1", bond, 4.672e-4)
        ]
        self.assertNotIn("strap_length_to_width_ratio_above_limit", issues)

    def test_raising_the_frequency_breaches_the_impedance_limit_alone(self):
        bond = _clean_rf_bond()
        bond["analysis_frequency_hz"] = 1.0e8
        issues = [
            f["issue"] for f in bc.impedance_findings("B1", bond, 4.672e-4)
        ]
        self.assertEqual(issues, ["rf_bond_impedance_above_limit"])

    def test_a_relaxed_impedance_limit_clears_the_finding(self):
        bond = _clean_rf_bond()
        bond["analysis_frequency_hz"] = 1.0e8
        bond["maximum_impedance_ohm"] = 500.0
        self.assertEqual(bc.impedance_findings("B1", bond, 4.672e-4), [])

    def test_missing_strap_width_is_reported_not_assumed(self):
        bond = _clean_rf_bond()
        del bond["strap"]["width_m"]
        findings = bc.impedance_findings("B1", bond, 4.672e-4)
        self.assertEqual(
            findings[0]["issue"], "rf_bond_strap_geometry_not_on_record"
        )

    def test_non_positive_impedance_limit_raises(self):
        bond = _clean_rf_bond()
        bond["maximum_impedance_ohm"] = 0.0
        with self.assertRaises(ValueError):
            bc.impedance_findings("B1", bond, 4.672e-4)


class GalvanicFindingsTest(unittest.TestCase):
    def test_close_couple_is_clean(self):
        self.assertEqual(
            bc.galvanic_findings("B1", _clean_power_bond()), []
        )

    def test_wide_couple_is_a_finding(self):
        bond = _clean_power_bond()
        bond["material_b"] = "gold"
        findings = bc.galvanic_findings("B1", bond)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "galvanic_couple_above_limit")

    def test_environment_defaults_to_normal(self):
        bond = _clean_power_bond()
        del bond["environment"]
        bond["material_b"] = "copper"
        findings = bc.galvanic_findings("B1", bond)
        self.assertEqual(findings[0]["environment"], "normal")

    def test_a_couple_can_pass_controlled_and_fail_harsh(self):
        bond = _clean_power_bond()
        bond["material_b"] = "chromate_conversion_coating"
        bond["environment"] = "controlled"
        self.assertEqual(bc.galvanic_findings("B1", bond), [])
        bond["environment"] = "normal"
        self.assertEqual(len(bc.galvanic_findings("B1", bond)), 1)
        bond["environment"] = "harsh"
        self.assertEqual(len(bc.galvanic_findings("B1", bond)), 1)

    def test_unknown_environment_raises(self):
        bond = _clean_power_bond()
        bond["environment"] = "tropical"
        with self.assertRaises(ValueError):
            bc.galvanic_findings("B1", bond)

    def test_unknown_material_raises(self):
        bond = _clean_power_bond()
        bond["material_a"] = "papier_mache"
        with self.assertRaises(ValueError):
            bc.galvanic_findings("B1", bond)


class ThermalFindingsTest(unittest.TestCase):
    def test_non_current_carrying_category_yields_nothing(self):
        self.assertEqual(
            bc.thermal_findings(
                "B1", "radio_frequency_reference", _clean_rf_bond(), 1.0e-3
            ),
            [],
        )

    def test_modest_fault_energy_is_clean(self):
        self.assertEqual(
            bc.thermal_findings(
                "B1", "power_fault_return", _clean_power_bond(), 1.141e-3
            ),
            [],
        )

    def test_large_fault_energy_is_a_finding(self):
        bond = _clean_power_bond()
        bond["fault_case"]["current_a"] = 2000.0
        bond["fault_case"]["clearing_time_s"] = 2.0
        findings = bc.thermal_findings(
            "B1", "power_fault_return", bond, 1.141e-3
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "bond_temperature_rise_above_limit"
        )

    def test_representation_error_on_the_rise_limit_is_absorbed(self):
        # 0.1 + 0.2 ohm deposits a rise a few units in the last place
        # above the 0.3 K limit it is physically equal to.
        bond = {
            "fault_case": {
                "current_a": 1.0,
                "clearing_time_s": 1.0,
                "thermal_mass_j_per_k": 1.0,
                "maximum_temperature_rise_k": 0.3,
            }
        }
        self.assertGreater(0.1 + 0.2, 0.3)
        self.assertEqual(
            bc.thermal_findings("B1", "power_fault_return", bond, 0.1 + 0.2),
            [],
        )

    def test_missing_fault_case_is_reported_not_assumed(self):
        bond = _clean_power_bond()
        del bond["fault_case"]
        findings = bc.thermal_findings(
            "B1", "power_fault_return", bond, 1.141e-3
        )
        self.assertEqual(
            findings[0]["issue"], "bond_fault_case_not_on_record"
        )

    def test_non_positive_rise_limit_raises(self):
        bond = _clean_power_bond()
        bond["fault_case"]["maximum_temperature_rise_k"] = 0.0
        with self.assertRaises(ValueError):
            bc.thermal_findings("B1", "power_fault_return", bond, 1.141e-3)


class BondReviewTest(unittest.TestCase):
    def test_clean_power_bond_has_no_findings_anywhere(self):
        review = bc.bond_review(_clean_power_bond())
        for findings in review.values():
            self.assertEqual(findings, [])
        self.assertTrue(bc.is_bond_compliant(review))

    def test_clean_rf_bond_has_no_findings_anywhere(self):
        review = bc.bond_review(_clean_rf_bond())
        self.assertTrue(bc.is_bond_compliant(review))

    def test_clean_bleed_bond_has_no_findings_anywhere(self):
        review = bc.bond_review(_clean_bleed_bond())
        self.assertTrue(bc.is_bond_compliant(review))

    def test_review_returns_the_four_expected_finding_lists(self):
        review = bc.bond_review(_clean_power_bond())
        self.assertEqual(
            sorted(review.keys()),
            ["galvanic", "impedance", "resistance", "thermal"],
        )

    def test_impedance_is_only_assessed_for_a_radio_frequency_bond(self):
        self.assertEqual(bc.bond_review(_clean_power_bond())["impedance"], [])
        self.assertEqual(bc.bond_review(_clean_bleed_bond())["impedance"], [])

    def test_thermal_is_only_assessed_for_a_current_carrying_bond(self):
        self.assertEqual(bc.bond_review(_clean_rf_bond())["thermal"], [])
        self.assertEqual(bc.bond_review(_clean_bleed_bond())["thermal"], [])

    def test_poor_contact_preparation_breaks_the_resistance_check(self):
        bond = _clean_power_bond()
        bond["strap"]["contact_resistance_ohm"] = 5.0e-2
        review = bc.bond_review(bond)
        self.assertEqual(len(review["resistance"]), 1)
        self.assertFalse(bc.is_bond_compliant(review))

    def test_a_bleed_path_that_is_too_conductive_is_caught(self):
        bond = _clean_bleed_bond()
        bond["measured_resistance_ohm"] = 1.0
        review = bc.bond_review(bond)
        self.assertEqual(
            review["resistance"][0]["issue"], "bond_resistance_below_floor"
        )
        self.assertFalse(bc.is_bond_compliant(review))

    def test_a_compliant_resistance_can_still_fail_the_rf_impedance(self):
        bond = _clean_rf_bond()
        bond["strap"]["length_m"] = 0.30
        bond["strap"]["width_m"] = 0.020
        review = bc.bond_review(bond)
        self.assertEqual(review["resistance"], [])
        self.assertTrue(review["impedance"])
        self.assertFalse(bc.is_bond_compliant(review))

    def test_review_does_not_mutate_the_input_bond(self):
        bond = _clean_power_bond()
        snapshot = repr(bond)
        bc.bond_review(bond)
        self.assertEqual(repr(bond), snapshot)

    def test_unrecognized_bond_kind_raises_through_the_review(self):
        bond = _clean_power_bond()
        bond["bond_kind"] = "duct_tape"
        with self.assertRaises(ValueError):
            bc.bond_review(bond)

    def test_unrecognized_material_raises_through_the_review(self):
        bond = _clean_rf_bond()
        bond["material_b"] = "kryptonite"
        with self.assertRaises(ValueError):
            bc.bond_review(bond)

    def test_compliance_helper_rejects_any_non_empty_list(self):
        self.assertFalse(
            bc.is_bond_compliant(
                {
                    "resistance": [],
                    "impedance": [],
                    "galvanic": [{"issue": "x"}],
                    "thermal": [],
                }
            )
        )

    def test_boundary_tolerance_is_small_and_positive(self):
        self.assertGreater(bc.BOUNDARY_REL_TOL, 0.0)
        self.assertLess(bc.BOUNDARY_REL_TOL, 1e-6)
        self.assertTrue(math.isfinite(bc.BOUNDARY_REL_TOL))


if __name__ == "__main__":
    unittest.main()
