#!/usr/bin/env python3
"""Gate 3 contract test for e2007-tested-unit-bonding.

Stdlib unittest only, offline, deterministic.
"""

import unittest

from e2007_tested_unit_bonding_logic import (
    BOND_EPS,
    MAX_STRAP_ASPECT_RATIO,
    audit_bonding_configuration,
    categorize_bond_path,
    check_bond_resistance,
    check_strap_geometry,
    compare_declared_and_measured,
    contact_resistance_ohm,
    effective_bond_resistance_ohm,
    parallel_resistance_ohm,
    path_resistance_ohm,
    strap_aspect_ratio,
    strap_resistance_ohm,
)


def mounting_foot(name):
    return {
        "name": name,
        "provenance": "qualified-mounting-interface",
        "material": "aluminium",
        "length_mm": 20.0,
        "width_mm": 30.0,
        "thickness_mm": 3.0,
        "contact_resistances_ohm": [0.0002, 0.0002],
    }


def design_strap():
    return {
        "name": "design-bonding-strap",
        "provenance": "interface-control-document",
        "material": "tinned-copper-braid",
        "length_mm": 20.0,
        "width_mm": 10.0,
        "thickness_mm": 0.5,
        "contact_resistances_ohm": [0.0001, 0.0001],
    }


def auxiliary_jumper():
    return {
        "name": "laboratory-jumper",
        "provenance": "test-setup-jumper",
        "material": "copper",
        "length_mm": 300.0,
        "width_mm": 6.0,
        "thickness_mm": 0.5,
        "contact_resistances_ohm": [0.0003, 0.0003],
    }


def nominal_paths():
    return [mounting_foot("mounting-foot-a"), mounting_foot("mounting-foot-b"), design_strap()]


def nominal_config():
    return {
        "paths": nominal_paths(),
        "bond_resistance_limit_ohm": 2.5e-3,
        "measured_effective_resistance_ohm": 1.25e-4,
        "reconciliation_tolerance_fraction": 0.25,
    }


class TestBondProvenance(unittest.TestCase):
    def test_unit_design_is_design_provided(self):
        path = mounting_foot("foot")
        path["provenance"] = "unit-design"
        self.assertEqual(categorize_bond_path(path), "design-provided")

    def test_interface_document_is_design_provided(self):
        self.assertEqual(categorize_bond_path(design_strap()), "design-provided")

    def test_qualified_mounting_interface_is_design_provided(self):
        self.assertEqual(categorize_bond_path(mounting_foot("foot")), "design-provided")

    def test_setup_jumper_is_test_added(self):
        self.assertEqual(categorize_bond_path(auxiliary_jumper()), "test-added")

    def test_laboratory_auxiliary_strap_is_test_added(self):
        path = auxiliary_jumper()
        path["provenance"] = "laboratory-auxiliary-strap"
        self.assertEqual(categorize_bond_path(path), "test-added")

    def test_unrecognized_provenance_is_rejected(self):
        path = mounting_foot("foot")
        path["provenance"] = "someone-had-a-spare-braid"
        with self.assertRaises(ValueError):
            categorize_bond_path(path)

    def test_path_without_a_name_is_rejected(self):
        path = mounting_foot("foot")
        del path["name"]
        with self.assertRaises(ValueError):
            categorize_bond_path(path)

    def test_path_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_bond_path(["foot", "unit-design"])


class TestStrapResistance(unittest.TestCase):
    def test_copper_reference_value(self):
        self.assertAlmostEqual(
            strap_resistance_ohm("copper", 100.0, 20.0, 1.0), 8.6e-5, delta=1e-12
        )

    def test_aluminium_is_more_resistive_than_copper(self):
        self.assertGreater(
            strap_resistance_ohm("aluminium", 100.0, 20.0, 1.0),
            strap_resistance_ohm("copper", 100.0, 20.0, 1.0),
        )

    def test_resistance_is_proportional_to_length(self):
        short = strap_resistance_ohm("copper", 50.0, 20.0, 1.0)
        long_run = strap_resistance_ohm("copper", 100.0, 20.0, 1.0)
        self.assertAlmostEqual(long_run, 2.0 * short, delta=1e-15)

    def test_resistance_halves_with_double_width(self):
        narrow = strap_resistance_ohm("copper", 100.0, 10.0, 1.0)
        wide = strap_resistance_ohm("copper", 100.0, 20.0, 1.0)
        self.assertAlmostEqual(wide, narrow / 2.0, delta=1e-15)

    def test_unrecognized_material_is_rejected(self):
        with self.assertRaises(ValueError):
            strap_resistance_ohm("unobtanium", 100.0, 20.0, 1.0)

    def test_non_positive_length_is_rejected(self):
        with self.assertRaises(ValueError):
            strap_resistance_ohm("copper", 0.0, 20.0, 1.0)

    def test_non_positive_width_is_rejected(self):
        with self.assertRaises(ValueError):
            strap_resistance_ohm("copper", 100.0, -20.0, 1.0)

    def test_non_positive_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            strap_resistance_ohm("copper", 100.0, 20.0, 0.0)

    def test_non_numeric_length_is_rejected(self):
        with self.assertRaises(ValueError):
            strap_resistance_ohm("copper", "100", 20.0, 1.0)


class TestContactResistance(unittest.TestCase):
    def test_absent_contact_list_is_zero(self):
        self.assertAlmostEqual(contact_resistance_ohm(None), 0.0, delta=1e-15)

    def test_empty_contact_list_is_zero(self):
        self.assertAlmostEqual(contact_resistance_ohm([]), 0.0, delta=1e-15)

    def test_joints_add_in_series(self):
        self.assertAlmostEqual(
            contact_resistance_ohm([0.0002, 0.0003, 0.0001]), 0.0006, delta=1e-15
        )

    def test_negative_joint_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            contact_resistance_ohm([0.0002, -0.0001])

    def test_non_sequence_contact_list_is_rejected(self):
        with self.assertRaises(ValueError):
            contact_resistance_ohm(0.0002)


class TestPathResistance(unittest.TestCase):
    def test_path_is_strap_plus_joints(self):
        path = design_strap()
        strap_only = strap_resistance_ohm("tinned-copper-braid", 20.0, 10.0, 0.5)
        self.assertAlmostEqual(
            path_resistance_ohm(path), strap_only + 0.0002, delta=1e-15
        )

    def test_path_without_joints_equals_the_strap(self):
        path = design_strap()
        del path["contact_resistances_ohm"]
        self.assertAlmostEqual(
            path_resistance_ohm(path),
            strap_resistance_ohm("tinned-copper-braid", 20.0, 10.0, 0.5),
            delta=1e-15,
        )

    def test_provenance_is_checked_before_any_arithmetic(self):
        path = design_strap()
        path["provenance"] = "improvised"
        with self.assertRaises(ValueError):
            path_resistance_ohm(path)

    def test_missing_material_is_rejected(self):
        path = design_strap()
        del path["material"]
        with self.assertRaises(ValueError):
            path_resistance_ohm(path)


class TestParallelCombination(unittest.TestCase):
    def test_two_equal_paths_halve_the_resistance(self):
        self.assertAlmostEqual(parallel_resistance_ohm([0.005, 0.005]), 0.0025, delta=1e-15)

    def test_three_paths_combine(self):
        self.assertAlmostEqual(
            parallel_resistance_ohm([0.003, 0.006, 0.006]), 0.0015, delta=1e-15
        )

    def test_single_path_returns_itself(self):
        self.assertAlmostEqual(parallel_resistance_ohm([0.004]), 0.004, delta=1e-15)

    def test_empty_set_is_rejected(self):
        with self.assertRaises(ValueError):
            parallel_resistance_ohm([])

    def test_non_positive_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            parallel_resistance_ohm([0.005, 0.0])

    def test_non_numeric_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            parallel_resistance_ohm([0.005, "0.005"])


class TestEffectiveBondResistance(unittest.TestCase):
    def test_design_paths_combine_in_parallel(self):
        expected = parallel_resistance_ohm(
            [path_resistance_ohm(p) for p in nominal_paths()]
        )
        self.assertAlmostEqual(
            effective_bond_resistance_ohm(nominal_paths()), expected, delta=1e-15
        )

    def test_test_added_path_is_excluded_from_the_number(self):
        with_jumper = nominal_paths() + [auxiliary_jumper()]
        self.assertAlmostEqual(
            effective_bond_resistance_ohm(with_jumper),
            effective_bond_resistance_ohm(nominal_paths()),
            delta=1e-15,
        )

    def test_excluding_the_jumper_never_flatters_the_result(self):
        with_jumper = nominal_paths() + [auxiliary_jumper()]
        all_paths = parallel_resistance_ohm(
            [path_resistance_ohm(p) for p in with_jumper]
        )
        self.assertGreater(effective_bond_resistance_ohm(with_jumper), all_paths)

    def test_bench_with_only_test_added_paths_is_rejected(self):
        with self.assertRaises(ValueError):
            effective_bond_resistance_ohm([auxiliary_jumper()])

    def test_empty_path_set_is_rejected(self):
        with self.assertRaises(ValueError):
            effective_bond_resistance_ohm([])


class TestStrapGeometry(unittest.TestCase):
    def test_aspect_ratio_value(self):
        self.assertAlmostEqual(strap_aspect_ratio(100.0, 25.0), 4.0, delta=1e-15)

    def test_non_positive_length_is_rejected(self):
        with self.assertRaises(ValueError):
            strap_aspect_ratio(0.0, 25.0)

    def test_non_positive_width_is_rejected(self):
        with self.assertRaises(ValueError):
            strap_aspect_ratio(100.0, 0.0)

    def test_short_wide_strap_is_compliant(self):
        self.assertTrue(check_strap_geometry(100.0, 40.0)["compliant"])

    def test_long_thin_strap_is_not_compliant(self):
        result = check_strap_geometry(300.0, 6.0)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["aspect_ratio"], 50.0, delta=1e-12)

    def test_strap_exactly_at_the_maximum_ratio_is_compliant(self):
        self.assertTrue(check_strap_geometry(100.0, 20.0)["compliant"])

    def test_representation_error_at_the_ratio_limit_is_absorbed(self):
        length = 25.0 + 0.1 + 0.2
        self.assertGreater(length / 5.06, MAX_STRAP_ASPECT_RATIO)
        self.assertTrue(check_strap_geometry(length, 5.06)["compliant"])

    def test_non_positive_maximum_ratio_is_rejected(self):
        with self.assertRaises(ValueError):
            check_strap_geometry(100.0, 20.0, 0.0)


class TestBondResistanceCheck(unittest.TestCase):
    def test_resistance_below_the_limit_is_compliant(self):
        result = check_bond_resistance(1.0e-4, 2.5e-3)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_ohm"], 2.4e-3, delta=1e-15)

    def test_resistance_above_the_limit_is_not_compliant(self):
        self.assertFalse(check_bond_resistance(5.0e-3, 2.5e-3)["compliant"])

    def test_resistance_exactly_at_the_limit_is_compliant(self):
        self.assertTrue(check_bond_resistance(2.5e-3, 2.5e-3)["compliant"])

    def test_series_sum_representation_error_at_the_limit_is_absorbed(self):
        measured = 0.0001 + 0.0002
        self.assertGreater(measured, 0.0003)
        self.assertTrue(check_bond_resistance(measured, 0.0003)["compliant"])

    def test_negative_measured_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            check_bond_resistance(-1.0e-4, 2.5e-3)

    def test_non_positive_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            check_bond_resistance(1.0e-4, 0.0)


class TestReconciliation(unittest.TestCase):
    def test_close_measurement_agrees(self):
        result = compare_declared_and_measured(1.0e-4, 1.1e-4, 0.25)
        self.assertTrue(result["agrees"])
        self.assertAlmostEqual(result["relative_deviation"], 0.1, delta=1e-12)

    def test_distant_measurement_disagrees(self):
        self.assertFalse(compare_declared_and_measured(1.0e-4, 5.0e-4, 0.25)["agrees"])

    def test_measurement_exactly_at_the_tolerance_agrees(self):
        self.assertTrue(compare_declared_and_measured(1.0e-4, 1.25e-4, 0.25)["agrees"])

    def test_non_positive_computed_value_is_rejected(self):
        with self.assertRaises(ValueError):
            compare_declared_and_measured(0.0, 1.0e-4, 0.25)

    def test_negative_measured_value_is_rejected(self):
        with self.assertRaises(ValueError):
            compare_declared_and_measured(1.0e-4, -1.0e-4, 0.25)

    def test_negative_tolerance_fraction_is_rejected(self):
        with self.assertRaises(ValueError):
            compare_declared_and_measured(1.0e-4, 1.0e-4, -0.1)


class TestBondingAudit(unittest.TestCase):
    def test_as_designed_bonding_is_compliant(self):
        report = audit_bonding_configuration(nominal_config())
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["compliant"])
        self.assertEqual(report["status"], "bonding-as-designed")
        self.assertEqual(report["design_path_count"], 3)
        self.assertEqual(report["test_added_path_count"], 0)

    def test_auxiliary_jumper_is_a_non_conformance(self):
        config = nominal_config()
        config["paths"] = nominal_paths() + [auxiliary_jumper()]
        report = audit_bonding_configuration(config)
        self.assertFalse(report["compliant"])
        self.assertEqual(report["test_added_path_count"], 1)
        self.assertTrue(
            any("added for the test" in f for f in report["findings"])
        )

    def test_auxiliary_jumper_does_not_change_the_effective_resistance(self):
        clean = audit_bonding_configuration(nominal_config())
        config = nominal_config()
        config["paths"] = nominal_paths() + [auxiliary_jumper()]
        dirty = audit_bonding_configuration(config)
        self.assertAlmostEqual(
            dirty["effective_resistance_ohm"],
            clean["effective_resistance_ohm"],
            delta=1e-15,
        )

    def test_long_thin_design_strap_is_a_geometry_finding(self):
        config = nominal_config()
        paths = nominal_paths()
        paths[2]["length_mm"] = 300.0
        paths[2]["width_mm"] = 6.0
        config["paths"] = paths
        report = audit_bonding_configuration(config)
        self.assertTrue(
            any("length-to-width ratio" in f for f in report["findings"])
        )

    def test_resistance_above_the_requirement_is_a_finding(self):
        config = nominal_config()
        config["bond_resistance_limit_ohm"] = 1.0e-5
        report = audit_bonding_configuration(config)
        self.assertIn(
            "effective bonding resistance above the declared requirement", report["findings"]
        )

    def test_missing_bench_measurement_is_a_finding(self):
        config = nominal_config()
        del config["measured_effective_resistance_ohm"]
        report = audit_bonding_configuration(config)
        self.assertIn("no bench bonding-resistance measurement on record", report["findings"])

    def test_disagreeing_bench_measurement_is_a_finding(self):
        config = nominal_config()
        config["measured_effective_resistance_ohm"] = 2.0e-3
        report = audit_bonding_configuration(config)
        self.assertIn(
            "bench bonding measurement disagrees with the computed value", report["findings"]
        )

    def test_bench_with_no_design_path_is_reported_not_computed(self):
        config = nominal_config()
        config["paths"] = [auxiliary_jumper()]
        report = audit_bonding_configuration(config)
        self.assertIsNone(report["effective_resistance_ohm"])
        self.assertIn("no design-provided bonding path on record", report["findings"])
        self.assertEqual(report["status"], "bonding-non-conformance")

    def test_duplicate_path_names_are_rejected(self):
        config = nominal_config()
        paths = nominal_paths()
        paths[1]["name"] = paths[0]["name"]
        config["paths"] = paths
        with self.assertRaises(ValueError):
            audit_bonding_configuration(config)

    def test_empty_path_set_is_rejected(self):
        config = nominal_config()
        config["paths"] = []
        with self.assertRaises(ValueError):
            audit_bonding_configuration(config)

    def test_config_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            audit_bonding_configuration([("paths", [])])

    def test_non_numeric_limit_is_rejected(self):
        config = nominal_config()
        config["bond_resistance_limit_ohm"] = "2.5e-3"
        with self.assertRaises(ValueError):
            audit_bonding_configuration(config)

    def test_effective_resistance_is_below_every_single_path(self):
        report = audit_bonding_configuration(nominal_config())
        for record in report["paths"]:
            self.assertLess(report["effective_resistance_ohm"], record["resistance_ohm"])

    def test_named_tolerance_is_far_below_any_bonding_limit(self):
        self.assertLess(BOND_EPS, 1e-9)


if __name__ == "__main__":
    unittest.main()
