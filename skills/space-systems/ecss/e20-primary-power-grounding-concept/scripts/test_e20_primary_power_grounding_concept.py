#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 5.8.1 primary power
grounding concept.

Exercises scripts/e20_primary_power_grounding_concept_logic.py (stdlib
unittest, offline). Contract: a declared topology maps to the
single-point star reference or to a deviation and an unrecognized one
raises, with an unjustified deviation reported twice; the mandatory
star-point fields are reported when absent or empty; the bond list must
carry exactly one tie between the primary power return and structure,
with none, several, or a secondary return tied to structure all
reported and a malformed record raising; the adiabatic minimum section
is the fault current times the square root of the clearing time over
the material constant; the strap resistance is resistivity times length
over section and the structure offset is that resistance times the
fault current; a section or a resistance sitting exactly on its limit
is compliant; every user return is checked against a minimum isolation
resistance; and the concept is acceptable only when every finding list
is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_primary_power_grounding_concept_logic as gnd  # noqa: E402


def _star_point(**overrides):
    star_point = {
        "star_point_id": "SP-1",
        "material": "copper",
        "strap_length_m": 0.25,
        "strap_area_mm2": 6.0,
        "max_bond_resistance_ohm": 2.5e-3,
        "allowed_structure_offset_v": 0.5,
    }
    star_point.update(overrides)
    return star_point


def _fault_case(**overrides):
    fault_case = {"fault_current_a": 200.0, "clearing_time_s": 0.05}
    fault_case.update(overrides)
    return fault_case


def _units():
    return [
        {
            "unit_id": "PCDU-A",
            "return_to_structure_ohm": 1.0e7,
            "primary_return_bonded_to_structure": False,
        },
        {"unit_id": "PLD-A", "return_to_structure_ohm": 5.0e6},
    ]


def _clean_concept():
    return {
        "concept_id": "EPS-GND-01",
        "topology": "single_point_star",
        "star_point": _star_point(),
        "bonds": [
            {"bond_id": "B1", "from": "primary_power_return", "to": "structure"},
            {"bond_id": "B2", "from": "unit_chassis", "to": "structure"},
        ],
        "fault_case": _fault_case(),
        "units": _units(),
        "minimum_isolation_ohm": 1.0e6,
    }


class TopologyTests(unittest.TestCase):
    def test_single_point_star_is_the_required_concept(self):
        self.assertEqual(
            gnd.categorize_grounding_topology("single_point_star"),
            "single_point_star",
        )

    def test_multipoint_reference_is_a_deviation(self):
        self.assertEqual(
            gnd.categorize_grounding_topology("multipoint_structure_reference"),
            "deviation",
        )

    def test_floating_primary_return_is_a_deviation(self):
        self.assertEqual(
            gnd.categorize_grounding_topology("floating_primary_return"), "deviation"
        )

    def test_unrecognized_topology_raises(self):
        with self.assertRaises(ValueError):
            gnd.categorize_grounding_topology("mesh_bonding")

    def test_missing_topology_raises(self):
        with self.assertRaises(ValueError):
            gnd.categorize_grounding_topology(None)

    def test_star_topology_reports_nothing(self):
        self.assertEqual(gnd.evaluate_topology("single_point_star")["findings"], [])

    def test_justified_deviation_reports_once(self):
        result = gnd.evaluate_topology(
            "daisy_chained_return", "accepted at PDR, waiver EPS-W-004"
        )
        self.assertEqual(len(result["findings"]), 1)

    def test_unjustified_deviation_reports_twice(self):
        result = gnd.evaluate_topology("daisy_chained_return")
        self.assertEqual(len(result["findings"]), 2)

    def test_blank_justification_counts_as_none(self):
        result = gnd.evaluate_topology("daisy_chained_return", "   ")
        self.assertEqual(len(result["findings"]), 2)


class StarPointFieldTests(unittest.TestCase):
    def test_complete_sheet_reports_nothing(self):
        self.assertEqual(gnd.missing_star_point_fields(_star_point()), [])

    def test_absent_field_is_reported(self):
        star_point = _star_point()
        del star_point["strap_area_mm2"]
        self.assertEqual(
            gnd.missing_star_point_fields(star_point), ["strap_area_mm2"]
        )

    def test_empty_field_is_reported(self):
        star_point = _star_point(material=None)
        self.assertEqual(gnd.missing_star_point_fields(star_point), ["material"])

    def test_missing_fields_are_sorted(self):
        star_point = _star_point()
        del star_point["strap_length_m"]
        del star_point["material"]
        self.assertEqual(
            gnd.missing_star_point_fields(star_point),
            ["material", "strap_length_m"],
        )

    def test_sheet_that_is_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            gnd.missing_star_point_fields(["SP-1"])


class BondListTests(unittest.TestCase):
    def test_single_tie_reports_nothing(self):
        result = gnd.check_single_star_reference(
            [{"bond_id": "B1", "from": "primary_power_return", "to": "structure"}]
        )
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["primary_ties"], ["B1"])

    def test_tie_is_counted_in_either_direction(self):
        result = gnd.check_single_star_reference(
            [{"bond_id": "B1", "from": "structure", "to": "primary_power_return"}]
        )
        self.assertEqual(result["primary_ties"], ["B1"])

    def test_chassis_bond_is_not_a_primary_tie(self):
        result = gnd.check_single_star_reference(
            [
                {"bond_id": "B1", "from": "primary_power_return", "to": "structure"},
                {"bond_id": "B2", "from": "unit_chassis", "to": "structure"},
            ]
        )
        self.assertEqual(result["primary_ties"], ["B1"])
        self.assertEqual(result["findings"], [])

    def test_no_tie_leaves_the_primary_side_floating(self):
        result = gnd.check_single_star_reference(
            [{"bond_id": "B1", "from": "unit_chassis", "to": "structure"}]
        )
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("floating", result["findings"][0])

    def test_two_ties_are_reported_together(self):
        result = gnd.check_single_star_reference(
            [
                {"bond_id": "B1", "from": "primary_power_return", "to": "structure"},
                {"bond_id": "B2", "from": "primary_power_return", "to": "structure"},
            ]
        )
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("B1", result["findings"][0])
        self.assertIn("B2", result["findings"][0])

    def test_secondary_return_tied_to_structure_is_reported(self):
        result = gnd.check_single_star_reference(
            [
                {"bond_id": "B1", "from": "primary_power_return", "to": "structure"},
                {"bond_id": "B2", "from": "secondary_return", "to": "structure"},
            ]
        )
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("parallel", result["findings"][0])

    def test_unrecognized_node_raises(self):
        with self.assertRaises(ValueError):
            gnd.check_single_star_reference(
                [{"bond_id": "B1", "from": "antenna_boom", "to": "structure"}]
            )

    def test_duplicate_bond_identifier_raises(self):
        with self.assertRaises(ValueError):
            gnd.check_single_star_reference(
                [
                    {"bond_id": "B1", "from": "primary_power_return", "to": "structure"},
                    {"bond_id": "B1", "from": "unit_chassis", "to": "structure"},
                ]
            )

    def test_bond_without_an_identifier_raises(self):
        with self.assertRaises(ValueError):
            gnd.check_single_star_reference(
                [{"from": "primary_power_return", "to": "structure"}]
            )

    def test_bond_that_is_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            gnd.check_single_star_reference(["B1"])

    def test_empty_bond_list_raises(self):
        with self.assertRaises(ValueError):
            gnd.check_single_star_reference([])


class AdiabaticSizingTests(unittest.TestCase):
    def test_minimum_area_matches_closed_form(self):
        self.assertAlmostEqual(
            gnd.adiabatic_minimum_area_mm2(200.0, 0.05, "copper"),
            0.1978821219,
            places=9,
        )

    def test_area_scales_with_the_root_of_the_clearing_time(self):
        quick = gnd.adiabatic_minimum_area_mm2(200.0, 0.05, "copper")
        slow = gnd.adiabatic_minimum_area_mm2(200.0, 0.20, "copper")
        self.assertAlmostEqual(slow, 2.0 * quick, places=12)

    def test_area_scales_linearly_with_the_fault_current(self):
        single = gnd.adiabatic_minimum_area_mm2(100.0, 0.05, "copper")
        double = gnd.adiabatic_minimum_area_mm2(200.0, 0.05, "copper")
        self.assertAlmostEqual(double, 2.0 * single, places=12)

    def test_copper_needs_less_section_than_aluminium(self):
        copper = gnd.adiabatic_minimum_area_mm2(200.0, 0.05, "copper")
        aluminium = gnd.adiabatic_minimum_area_mm2(200.0, 0.05, "aluminium")
        self.assertLess(copper, aluminium)

    def test_stainless_steel_needs_the_most_section(self):
        steel = gnd.adiabatic_minimum_area_mm2(200.0, 0.05, "stainless_steel")
        aluminium = gnd.adiabatic_minimum_area_mm2(200.0, 0.05, "aluminium")
        self.assertGreater(steel, aluminium)

    def test_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            gnd.adiabatic_minimum_area_mm2(200.0, 0.05, "kapton")

    def test_zero_clearing_time_raises(self):
        with self.assertRaises(ValueError):
            gnd.adiabatic_minimum_area_mm2(200.0, 0.0, "copper")

    def test_negative_fault_current_raises(self):
        with self.assertRaises(ValueError):
            gnd.adiabatic_minimum_area_mm2(-200.0, 0.05, "copper")


class StrapElectricalTests(unittest.TestCase):
    def test_resistance_matches_closed_form(self):
        self.assertAlmostEqual(
            gnd.strap_dc_resistance_ohm(0.25, 6.0, "copper"), 7.1666667e-4, places=10
        )

    def test_doubling_the_length_doubles_the_resistance(self):
        short = gnd.strap_dc_resistance_ohm(0.25, 6.0, "copper")
        long = gnd.strap_dc_resistance_ohm(0.50, 6.0, "copper")
        self.assertAlmostEqual(long, 2.0 * short, places=12)

    def test_doubling_the_section_halves_the_resistance(self):
        thin = gnd.strap_dc_resistance_ohm(0.25, 6.0, "copper")
        thick = gnd.strap_dc_resistance_ohm(0.25, 12.0, "copper")
        self.assertAlmostEqual(thick, 0.5 * thin, places=12)

    def test_aluminium_is_more_resistive_than_copper(self):
        self.assertGreater(
            gnd.strap_dc_resistance_ohm(0.25, 6.0, "aluminium"),
            gnd.strap_dc_resistance_ohm(0.25, 6.0, "copper"),
        )

    def test_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            gnd.strap_dc_resistance_ohm(0.25, 6.0, "kapton")

    def test_zero_section_raises(self):
        with self.assertRaises(ValueError):
            gnd.strap_dc_resistance_ohm(0.25, 0.0, "copper")

    def test_offset_is_resistance_times_current(self):
        self.assertAlmostEqual(
            gnd.bond_voltage_offset_v(7.1666667e-4, 200.0), 0.14333333, places=8
        )

    def test_negative_resistance_raises(self):
        with self.assertRaises(ValueError):
            gnd.bond_voltage_offset_v(-1.0e-3, 200.0)

    def test_zero_current_raises(self):
        with self.assertRaises(ValueError):
            gnd.bond_voltage_offset_v(1.0e-3, 0.0)


class FaultCapabilityTests(unittest.TestCase):
    def test_clean_strap_reports_nothing(self):
        result = gnd.evaluate_star_point_fault_capability(
            _star_point(), _fault_case()
        )
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["minimum_area_mm2"], 0.1978821219, places=9)

    def test_undersized_strap_is_reported(self):
        star_point = _star_point(
            strap_area_mm2=0.1, allowed_structure_offset_v=100.0
        )
        result = gnd.evaluate_star_point_fault_capability(star_point, _fault_case())
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("below", result["findings"][0])

    def test_section_exactly_at_the_adiabatic_minimum_is_compliant(self):
        minimum = gnd.adiabatic_minimum_area_mm2(200.0, 0.05, "copper")
        star_point = _star_point(
            strap_area_mm2=minimum, allowed_structure_offset_v=100.0
        )
        result = gnd.evaluate_star_point_fault_capability(star_point, _fault_case())
        self.assertEqual(result["findings"], [])

    def test_section_one_representation_step_below_is_still_compliant(self):
        minimum = gnd.adiabatic_minimum_area_mm2(200.0, 0.05, "copper")
        star_point = _star_point(
            strap_area_mm2=minimum * (1.0 - 1.0e-15),
            allowed_structure_offset_v=100.0,
        )
        result = gnd.evaluate_star_point_fault_capability(star_point, _fault_case())
        self.assertEqual(result["findings"], [])

    def test_section_meaningfully_below_the_minimum_is_reported(self):
        minimum = gnd.adiabatic_minimum_area_mm2(200.0, 0.05, "copper")
        star_point = _star_point(
            strap_area_mm2=minimum * 0.99, allowed_structure_offset_v=100.0
        )
        result = gnd.evaluate_star_point_fault_capability(star_point, _fault_case())
        self.assertEqual(len(result["findings"]), 1)

    def test_structure_offset_above_the_allowance_is_reported(self):
        star_point = _star_point(allowed_structure_offset_v=0.1)
        result = gnd.evaluate_star_point_fault_capability(star_point, _fault_case())
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("structure potential offset", result["findings"][0])

    def test_a_slower_protection_can_undersize_a_compliant_strap(self):
        star_point = _star_point(
            strap_area_mm2=0.25, allowed_structure_offset_v=100.0
        )
        quick = gnd.evaluate_star_point_fault_capability(star_point, _fault_case())
        slow = gnd.evaluate_star_point_fault_capability(
            star_point, _fault_case(clearing_time_s=5.0)
        )
        self.assertEqual(quick["findings"], [])
        self.assertEqual(len(slow["findings"]), 1)

    def test_fault_case_that_is_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            gnd.evaluate_star_point_fault_capability(_star_point(), 200.0)

    def test_missing_fault_current_raises(self):
        with self.assertRaises(ValueError):
            gnd.evaluate_star_point_fault_capability(
                _star_point(), {"clearing_time_s": 0.05}
            )


class BondResistanceTests(unittest.TestCase):
    def test_clean_bond_reports_nothing(self):
        result = gnd.evaluate_bond_resistance(_star_point())
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(
            result["strap_resistance_ohm"], 7.1666667e-4, places=10
        )

    def test_resistance_exactly_on_the_class_limit_is_compliant(self):
        # A 0.75 m copper strap of 10 mm2 evaluates a few bits above
        # 1.29 mohm; the bond is physically on the class limit.
        star_point = _star_point(
            strap_length_m=0.75,
            strap_area_mm2=10.0,
            max_bond_resistance_ohm=0.00129,
        )
        result = gnd.evaluate_bond_resistance(star_point)
        self.assertGreater(result["strap_resistance_ohm"], 0.00129)
        self.assertEqual(result["findings"], [])

    def test_resistance_above_the_class_limit_is_reported(self):
        star_point = _star_point(max_bond_resistance_ohm=1.0e-4)
        result = gnd.evaluate_bond_resistance(star_point)
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("bonding", result["findings"][0])

    def test_missing_class_limit_raises(self):
        star_point = _star_point()
        del star_point["max_bond_resistance_ohm"]
        with self.assertRaises(ValueError):
            gnd.evaluate_bond_resistance(star_point)


class ReturnIsolationTests(unittest.TestCase):
    def test_isolated_units_report_nothing(self):
        self.assertEqual(
            gnd.evaluate_return_isolation(_units(), 1.0e6)["findings"], []
        )

    def test_unit_below_the_minimum_is_reported(self):
        units = _units()
        units[1]["return_to_structure_ohm"] = 1.0e3
        result = gnd.evaluate_return_isolation(units, 1.0e6)
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("PLD-A", result["findings"][0])

    def test_unit_exactly_on_the_minimum_is_compliant(self):
        units = _units()
        units[1]["return_to_structure_ohm"] = 1.0e6
        self.assertEqual(
            gnd.evaluate_return_isolation(units, 1.0e6)["findings"], []
        )

    def test_unit_bonding_its_primary_return_is_reported(self):
        units = _units()
        units[0]["primary_return_bonded_to_structure"] = True
        result = gnd.evaluate_return_isolation(units, 1.0e6)
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("parallel", result["findings"][0])

    def test_unit_with_no_isolation_figure_is_reported(self):
        units = _units()
        del units[1]["return_to_structure_ohm"]
        result = gnd.evaluate_return_isolation(units, 1.0e6)
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("no return-to-structure", result["findings"][0])

    def test_duplicate_unit_identifier_raises(self):
        units = _units()
        units[1]["unit_id"] = "PCDU-A"
        with self.assertRaises(ValueError):
            gnd.evaluate_return_isolation(units, 1.0e6)

    def test_unit_without_an_identifier_raises(self):
        with self.assertRaises(ValueError):
            gnd.evaluate_return_isolation([{"return_to_structure_ohm": 1.0e7}], 1.0e6)

    def test_empty_unit_list_raises(self):
        with self.assertRaises(ValueError):
            gnd.evaluate_return_isolation([], 1.0e6)

    def test_non_positive_minimum_isolation_raises(self):
        with self.assertRaises(ValueError):
            gnd.evaluate_return_isolation(_units(), 0.0)


class ConceptAssessmentTests(unittest.TestCase):
    def test_clean_concept_is_compliant(self):
        result = gnd.assess_primary_power_grounding_concept(_clean_concept())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["star_point_findings"], [])
        self.assertEqual(result["isolation_findings"], [])

    def test_reported_offset_matches_the_strap_and_the_fault(self):
        result = gnd.assess_primary_power_grounding_concept(_clean_concept())
        self.assertAlmostEqual(
            result["fault_capability"]["structure_offset_v"], 0.14333333, places=8
        )

    def test_deviating_topology_fails_the_concept(self):
        concept = _clean_concept()
        concept["topology"] = "hybrid_single_and_multipoint"
        result = gnd.assess_primary_power_grounding_concept(concept)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["topology"]["findings"]), 2)

    def test_second_star_bond_fails_the_concept(self):
        concept = _clean_concept()
        concept["bonds"].append(
            {"bond_id": "B3", "from": "primary_power_return", "to": "structure"}
        )
        result = gnd.assess_primary_power_grounding_concept(concept)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["star_point_findings"]), 1)

    def test_missing_star_point_field_stops_the_electrical_checks(self):
        concept = _clean_concept()
        del concept["star_point"]["strap_area_mm2"]
        result = gnd.assess_primary_power_grounding_concept(concept)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["fault_capability"]["findings"], [])
        self.assertTrue(
            any("strap_area_mm2" in finding for finding in result["star_point_findings"])
        )

    def test_undersized_strap_fails_the_concept(self):
        concept = _clean_concept()
        concept["star_point"]["strap_area_mm2"] = 0.1
        result = gnd.assess_primary_power_grounding_concept(concept)
        self.assertFalse(result["compliant"])
        self.assertTrue(result["fault_capability"]["findings"])

    def test_isolation_breach_fails_the_concept(self):
        concept = _clean_concept()
        concept["units"][0]["primary_return_bonded_to_structure"] = True
        result = gnd.assess_primary_power_grounding_concept(concept)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["isolation_findings"]), 1)

    def test_missing_concept_identifier_raises(self):
        concept = _clean_concept()
        concept["concept_id"] = "  "
        with self.assertRaises(ValueError):
            gnd.assess_primary_power_grounding_concept(concept)

    def test_unrecognized_topology_raises(self):
        concept = _clean_concept()
        concept["topology"] = "mesh_bonding"
        with self.assertRaises(ValueError):
            gnd.assess_primary_power_grounding_concept(concept)

    def test_concept_that_is_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            gnd.assess_primary_power_grounding_concept("EPS-GND-01")


if __name__ == "__main__":
    unittest.main()
