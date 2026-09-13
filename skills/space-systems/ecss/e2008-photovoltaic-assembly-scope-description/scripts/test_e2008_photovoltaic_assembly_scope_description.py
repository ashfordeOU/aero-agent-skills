#!/usr/bin/env python3
"""Contract test for the photovoltaic assembly scope description leaf."""

import unittest

from e2008_photovoltaic_assembly_scope_description_logic import (
    ADDRESSED_FAMILIES,
    COMMON_PROVISIONS,
    CONFIGURATION_FAMILIES,
    FLAT_PLATE_CONCENTRATION_RATIO,
    addressed_provisions,
    assess_array_scope,
    boundary_of_supply,
    configuration_family,
    element_placement,
    evaluate_assembly_declaration,
)


def elements(*extra):
    base = [
        "solar-cell",
        "coverglass",
        "coverglass-adhesive",
        "cell-interconnect",
        "substrate-facesheet",
        "substrate-core",
        "array-connector",
    ]
    base.extend(extra)
    return base


def rigid_attributes(**overrides):
    attributes = {
        "mounting": "panel",
        "substrate": "rigid",
        "deployable": True,
        "deployment_kinematics": "fold-out",
    }
    attributes.update(overrides)
    return attributes


def blanket_attributes(**overrides):
    attributes = {
        "mounting": "panel",
        "substrate": "flexible",
        "deployable": True,
        "deployment_kinematics": "roll-out",
    }
    attributes.update(overrides)
    return attributes


def declaration(**overrides):
    record = {
        "id": "WING-PY",
        "elements": elements(),
        "attributes": rigid_attributes(),
        "declared_provisions": list(COMMON_PROVISIONS)
        + ["deployment-induced-loading"],
    }
    record.update(overrides)
    return record


class TestElementPlacement(unittest.TestCase):
    def test_the_cell_is_inside_the_assembly(self):
        self.assertEqual(element_placement("solar-cell")["placement"], "inside")

    def test_the_array_connector_is_on_the_boundary(self):
        self.assertEqual(element_placement("array-connector")["placement"], "boundary")

    def test_the_drive_mechanism_is_outside(self):
        self.assertEqual(
            element_placement("solar-array-drive-mechanism")["placement"], "outside"
        )

    def test_the_deployment_hinge_is_outside(self):
        self.assertEqual(element_placement("deployment-hinge")["placement"], "outside")

    def test_every_placement_carries_a_rationale(self):
        self.assertTrue(element_placement("coverglass")["rationale"].strip())

    def test_surrounding_whitespace_is_tolerated(self):
        self.assertEqual(element_placement("  solar-cell  ")["element"], "solar-cell")

    def test_unknown_element_raises(self):
        with self.assertRaises(ValueError):
            element_placement("antenna-reflector")

    def test_blank_element_raises(self):
        with self.assertRaises(ValueError):
            element_placement("   ")


class TestBoundaryOfSupply(unittest.TestCase):
    def test_the_declared_elements_are_grouped(self):
        boundary = boundary_of_supply(elements())
        self.assertIn("solar-cell", boundary["inside"])
        self.assertIn("array-connector", boundary["boundary"])
        self.assertEqual(boundary["outside"], ())

    def test_a_declaration_with_a_boundary_element_is_bounded(self):
        self.assertTrue(boundary_of_supply(elements())["bounded"])

    def test_a_declaration_without_a_boundary_element_is_unbounded(self):
        without = [item for item in elements() if item != "array-connector"]
        self.assertFalse(boundary_of_supply(without)["bounded"])

    def test_the_converting_element_is_reported(self):
        self.assertTrue(boundary_of_supply(elements())["converting_element_present"])

    def test_an_outside_element_is_reported_separately(self):
        boundary = boundary_of_supply(elements("yoke"))
        self.assertEqual(boundary["outside"], ("yoke",))

    def test_a_repeated_element_raises(self):
        with self.assertRaises(ValueError):
            boundary_of_supply(elements("solar-cell"))

    def test_an_empty_element_list_raises(self):
        with self.assertRaises(ValueError):
            boundary_of_supply([])

    def test_a_string_element_list_raises(self):
        with self.assertRaises(ValueError):
            boundary_of_supply("solar-cell")


class TestConfigurationFamily(unittest.TestCase):
    def test_a_folding_rigid_wing_is_a_deployable_panel(self):
        result = configuration_family(rigid_attributes())
        self.assertEqual(result["family"], "rigid-deployable-panel")
        self.assertTrue(result["addressed"])

    def test_a_rolled_blanket_is_a_flexible_deployable(self):
        self.assertEqual(
            configuration_family(blanket_attributes())["family"],
            "flexible-deployable-blanket",
        )

    def test_a_fixed_body_array_is_body_mounted(self):
        result = configuration_family(
            {"mounting": "body-mounted", "substrate": "rigid", "deployable": False}
        )
        self.assertEqual(result["family"], "body-mounted")

    def test_a_wrapped_drum_is_a_spinner(self):
        result = configuration_family(
            {"mounting": "drum", "substrate": "rigid", "deployable": False}
        )
        self.assertEqual(result["family"], "spinner-drum")

    def test_a_concentrating_array_is_derived_but_not_addressed(self):
        result = configuration_family(rigid_attributes(concentration_ratio=6.0))
        self.assertEqual(result["family"], "concentrator")
        self.assertFalse(result["addressed"])
        self.assertNotIn(result["family"], ADDRESSED_FAMILIES)

    def test_a_flat_plate_ratio_of_one_is_not_concentrating(self):
        result = configuration_family(
            rigid_attributes(concentration_ratio=FLAT_PLATE_CONCENTRATION_RATIO)
        )
        self.assertFalse(result["concentrating"])
        self.assertAlmostEqual(
            result["concentration_ratio"], FLAT_PLATE_CONCENTRATION_RATIO, places=9
        )

    def test_a_ratio_a_hair_above_one_is_not_read_as_concentration(self):
        result = configuration_family(
            rigid_attributes(concentration_ratio=1.0 + 1.0e-13)
        )
        self.assertFalse(result["concentrating"])

    def test_an_absent_ratio_defaults_to_flat_plate(self):
        result = configuration_family(rigid_attributes())
        self.assertAlmostEqual(
            result["concentration_ratio"], FLAT_PLATE_CONCENTRATION_RATIO, places=9
        )

    def test_a_ratio_below_one_raises(self):
        with self.assertRaises(ValueError):
            configuration_family(rigid_attributes(concentration_ratio=0.8))

    def test_a_deployable_array_without_kinematics_raises(self):
        attributes = rigid_attributes()
        del attributes["deployment_kinematics"]
        with self.assertRaises(ValueError):
            configuration_family(attributes)

    def test_a_fixed_array_stating_kinematics_raises(self):
        with self.assertRaises(ValueError):
            configuration_family(
                {
                    "mounting": "body-mounted",
                    "substrate": "rigid",
                    "deployable": False,
                    "deployment_kinematics": "fold-out",
                }
            )

    def test_a_fixed_flexible_substrate_raises(self):
        with self.assertRaises(ValueError):
            configuration_family(
                {"mounting": "panel", "substrate": "flexible", "deployable": False}
            )

    def test_a_body_mounted_deployable_raises(self):
        with self.assertRaises(ValueError):
            configuration_family(
                rigid_attributes(mounting="body-mounted", deployable=True)
            )

    def test_a_non_boolean_deployable_raises(self):
        with self.assertRaises(ValueError):
            configuration_family(rigid_attributes(deployable="yes"))

    def test_unknown_mounting_raises(self):
        with self.assertRaises(ValueError):
            configuration_family(rigid_attributes(mounting="gimbal"))

    def test_unknown_attribute_key_raises(self):
        with self.assertRaises(ValueError):
            configuration_family(rigid_attributes(cell_technology="triple-junction"))

    def test_missing_attribute_key_raises(self):
        attributes = rigid_attributes()
        del attributes["substrate"]
        with self.assertRaises(ValueError):
            configuration_family(attributes)

    def test_attributes_that_are_not_a_mapping_raise(self):
        with self.assertRaises(ValueError):
            configuration_family(["panel", "rigid"])


class TestAddressedProvisions(unittest.TestCase):
    def test_every_family_carries_the_common_provisions(self):
        for family in CONFIGURATION_FAMILIES:
            provisions = addressed_provisions(family)
            for item in COMMON_PROVISIONS:
                self.assertIn(item, provisions)

    def test_a_deployable_panel_adds_deployment_loading(self):
        self.assertIn(
            "deployment-induced-loading",
            addressed_provisions("rigid-deployable-panel"),
        )

    def test_a_blanket_adds_tensioning_and_stowage(self):
        self.assertIn(
            "blanket-tensioning-and-stowage",
            addressed_provisions("flexible-deployable-blanket"),
        )

    def test_a_concentrator_adds_its_optics_provisions(self):
        provisions = addressed_provisions("concentrator")
        self.assertIn("concentrator-optics-alignment", provisions)
        self.assertIn("off-pointing-thermal-margin", provisions)

    def test_a_body_mounted_array_adds_structure_coupling(self):
        self.assertIn(
            "spacecraft-structure-thermal-coupling",
            addressed_provisions("body-mounted"),
        )

    def test_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            addressed_provisions("sail-mounted")


class TestEvaluateAssemblyDeclaration(unittest.TestCase):
    def test_a_sound_declaration_is_in_scope(self):
        record = evaluate_assembly_declaration(declaration())
        self.assertTrue(record["in_scope"])
        self.assertEqual(record["findings"], [])

    def test_an_unbounded_declaration_is_flagged(self):
        record = evaluate_assembly_declaration(
            declaration(
                elements=[item for item in elements() if item != "array-connector"]
            )
        )
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("assembly-boundary-undeclared", codes)

    def test_a_declaration_without_a_cell_is_flagged(self):
        record = evaluate_assembly_declaration(
            declaration(elements=[item for item in elements() if item != "solar-cell"])
        )
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("converting-element-absent", codes)

    def test_an_overreaching_declaration_is_flagged(self):
        record = evaluate_assembly_declaration(
            declaration(elements=elements("solar-array-drive-mechanism"))
        )
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("element-outside-the-assembly", codes)

    def test_a_concentrator_declaration_is_handed_over(self):
        record = evaluate_assembly_declaration(
            declaration(attributes=rigid_attributes(concentration_ratio=8.0))
        )
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("configuration-not-addressed", codes)
        self.assertFalse(record["in_scope"])

    def test_a_blanket_with_a_stiff_core_is_flagged(self):
        record = evaluate_assembly_declaration(
            declaration(attributes=blanket_attributes())
        )
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("element-inconsistent-with-configuration", codes)

    def test_an_uncovered_provision_is_named(self):
        record = evaluate_assembly_declaration(
            declaration(declared_provisions=list(COMMON_PROVISIONS))
        )
        self.assertIn("deployment-induced-loading", record["uncovered_provisions"])

    def test_omitting_the_provision_list_raises_no_coverage_finding(self):
        record = declaration()
        del record["declared_provisions"]
        evaluated = evaluate_assembly_declaration(record)
        self.assertEqual(evaluated["uncovered_provisions"], ())
        self.assertTrue(evaluated["in_scope"])

    def test_a_string_provision_list_raises(self):
        with self.assertRaises(ValueError):
            evaluate_assembly_declaration(
                declaration(declared_provisions="substrate-insulation")
            )

    def test_a_blank_provision_name_raises(self):
        with self.assertRaises(ValueError):
            evaluate_assembly_declaration(declaration(declared_provisions=["  "]))

    def test_unknown_declaration_key_raises(self):
        with self.assertRaises(ValueError):
            evaluate_assembly_declaration(declaration(owner="array supplier"))

    def test_missing_declaration_key_raises(self):
        record = declaration()
        del record["attributes"]
        with self.assertRaises(ValueError):
            evaluate_assembly_declaration(record)

    def test_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            evaluate_assembly_declaration(declaration(id="   "))

    def test_declaration_that_is_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            evaluate_assembly_declaration(["WING-PY"])

    def test_findings_carry_code_subject_and_detail(self):
        record = evaluate_assembly_declaration(
            declaration(elements=elements("yoke"))
        )
        for finding in record["findings"]:
            self.assertEqual(sorted(finding.keys()), ["code", "detail", "subject"])


class TestAssessArrayScope(unittest.TestCase):
    def test_a_sound_array_is_accepted(self):
        report = assess_array_scope([declaration()])
        self.assertTrue(report["accepted"])
        self.assertEqual(report["verdict"], "scope-consistent")

    def test_two_matched_wings_are_not_mixed(self):
        report = assess_array_scope(
            [declaration(id="WING-PY"), declaration(id="WING-MY")]
        )
        self.assertFalse(report["mixed_configuration"])
        self.assertEqual(report["families"], ("rigid-deployable-panel",))

    def test_two_unlike_wings_are_reported_as_mixed(self):
        second = declaration(
            id="WING-MY",
            elements=[item for item in elements() if item != "substrate-core"],
            attributes=blanket_attributes(),
            declared_provisions=list(COMMON_PROVISIONS)
            + ["deployment-induced-loading", "blanket-tensioning-and-stowage"],
        )
        report = assess_array_scope([declaration(), second])
        self.assertTrue(report["mixed_configuration"])
        self.assertEqual(len(report["families"]), 2)

    def test_one_bad_wing_rejects_the_array(self):
        report = assess_array_scope(
            [declaration(), declaration(id="WING-MY", elements=elements("yoke"))]
        )
        self.assertFalse(report["accepted"])
        self.assertEqual(report["verdict"], "scope-inconsistent")

    def test_in_scope_fraction_counts_wings_not_findings(self):
        report = assess_array_scope(
            [declaration(), declaration(id="WING-MY", elements=elements("yoke"))]
        )
        self.assertAlmostEqual(report["in_scope_fraction"], 0.5, places=9)

    def test_duplicate_wing_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_array_scope([declaration(), declaration()])

    def test_an_empty_array_raises(self):
        with self.assertRaises(ValueError):
            assess_array_scope([])

    def test_a_string_array_raises(self):
        with self.assertRaises(ValueError):
            assess_array_scope("WING-PY")


if __name__ == "__main__":
    unittest.main()
