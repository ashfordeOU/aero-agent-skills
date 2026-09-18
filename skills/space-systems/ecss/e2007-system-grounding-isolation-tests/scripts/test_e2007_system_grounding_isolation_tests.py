"""Contract test for the system grounding isolation and continuity leaf."""

import unittest

from e2007_system_grounding_isolation_tests_logic import (
    CONTINUOUS_PAIR_THRESHOLD_OHM,
    INTENT_BONDED,
    INTENT_ISOLATED,
    ISOLATION_FLOOR_OHM,
    METHOD_FOUR_WIRE,
    METHOD_TWO_WIRE,
    MIN_ISOLATION_TEST_VOLTAGE_V,
    assess_grounding_isolation,
    bond_limit_ohm,
    check_continuity,
    check_isolation,
    check_measurement_coverage,
    check_pair,
    index_measurements,
    pair_key,
    structure_reference_findings,
    validate_declaration,
    validate_measurement,
)


def bonded(node_a="secondary-return", node_b="structure",
           category="structure-bond", **kw):
    record = {
        "node_a": node_a,
        "node_b": node_b,
        "intent": INTENT_BONDED,
        "bond_category": category,
    }
    record.update(kw)
    return record


def isolated(node_a="primary-return", node_b="structure", **kw):
    record = {"node_a": node_a, "node_b": node_b, "intent": INTENT_ISOLATED}
    record.update(kw)
    return record


def measured(node_a="secondary-return", node_b="structure", resistance=0.001, **kw):
    record = {"node_a": node_a, "node_b": node_b, "resistance_ohm": resistance}
    record.update(kw)
    return record


def architecture(**kw):
    record = {
        "declarations": [
            bonded(power_domain="payload-secondary"),
            bonded("unit-chassis", "structure", "unit-chassis-bond"),
            isolated(),
        ],
        "measurements": [
            measured(),
            measured("unit-chassis", "structure", 0.005),
            measured("primary-return", "structure", 5.0e6, test_voltage_v=100.0),
        ],
    }
    record.update(kw)
    return record


class TestBondCategories(unittest.TestCase):
    def test_a_known_category_has_a_limit(self):
        self.assertAlmostEqual(bond_limit_ohm("structure-bond"), 0.0025, places=9)

    def test_an_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            bond_limit_ohm("paint-bond")

    def test_a_lightning_path_is_the_tightest_category(self):
        self.assertLess(bond_limit_ohm("lightning-path-bond"),
                        bond_limit_ohm("structure-bond"))


class TestPairKey(unittest.TestCase):
    def test_the_key_is_order_independent(self):
        self.assertEqual(pair_key("structure", "chassis"),
                         pair_key("chassis", "structure"))

    def test_a_self_pair_raises(self):
        with self.assertRaises(ValueError):
            pair_key("structure", "structure")

    def test_an_empty_node_raises(self):
        with self.assertRaises(ValueError):
            pair_key("", "structure")

    def test_a_non_string_node_raises(self):
        with self.assertRaises(ValueError):
            pair_key(7, "structure")


class TestValidateDeclaration(unittest.TestCase):
    def test_a_bonded_pair_keeps_its_category(self):
        norm = validate_declaration(bonded())
        self.assertEqual(norm["intent"], INTENT_BONDED)
        self.assertEqual(norm["bond_category"], "structure-bond")

    def test_the_node_order_is_normalized(self):
        self.assertEqual(
            validate_declaration(bonded("structure", "secondary-return"))["key"],
            validate_declaration(bonded())["key"],
        )

    def test_a_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(["structure"])

    def test_an_unknown_intent_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(bonded(intent="floating"))

    def test_a_bonded_pair_without_a_category_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(bonded(category=None))

    def test_a_bonded_pair_with_an_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(bonded(category="tape-bond"))

    def test_an_isolated_pair_carrying_a_category_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(isolated(bond_category="structure-bond"))

    def test_an_empty_power_domain_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(bonded(power_domain=" "))


class TestValidateMeasurement(unittest.TestCase):
    def test_the_default_method_is_four_wire(self):
        self.assertEqual(validate_measurement(measured())["method"], METHOD_FOUR_WIRE)

    def test_a_missing_resistance_raises(self):
        with self.assertRaises(ValueError):
            validate_measurement({"node_a": "a", "node_b": "b"})

    def test_a_negative_resistance_raises(self):
        with self.assertRaises(ValueError):
            validate_measurement(measured(resistance=-0.001))

    def test_a_boolean_resistance_raises(self):
        with self.assertRaises(ValueError):
            validate_measurement(measured(resistance=True))

    def test_an_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            validate_measurement(measured(method="guessed"))

    def test_a_non_numeric_test_voltage_raises(self):
        with self.assertRaises(ValueError):
            validate_measurement(measured(test_voltage_v="100"))

    def test_a_duplicate_measured_pair_raises(self):
        with self.assertRaises(ValueError):
            index_measurements([measured(), measured("structure", "secondary-return")])

    def test_a_non_list_measurement_set_raises(self):
        with self.assertRaises(ValueError):
            index_measurements(measured())


class TestContinuity(unittest.TestCase):
    def test_a_bond_under_its_limit_is_clean(self):
        self.assertEqual(check_continuity(bonded(), measured(resistance=0.001)), [])

    def test_a_bond_exactly_on_its_limit_is_clean(self):
        self.assertEqual(
            check_continuity(bonded(), measured(resistance=bond_limit_ohm("structure-bond"))),
            [],
        )

    def test_a_bond_above_its_limit_is_a_finding(self):
        self.assertEqual(
            check_continuity(bonded(), measured(resistance=0.01)),
            ["bond-resistance-above-the-category-limit"],
        )

    def test_a_two_wire_reading_on_a_milliohm_bond_is_a_finding(self):
        self.assertIn(
            "bond-measured-below-the-two-wire-resolution-floor",
            check_continuity(bonded(), measured(resistance=0.001,
                                                method=METHOD_TWO_WIRE)),
        )

    def test_a_two_wire_reading_on_a_coarser_bond_is_accepted(self):
        self.assertEqual(
            check_continuity(
                bonded("unit-chassis", "structure", "signal-reference-bond"),
                measured("unit-chassis", "structure", 0.02, method=METHOD_TWO_WIRE),
            ),
            [],
        )

    def test_an_isolated_declaration_is_refused_here(self):
        with self.assertRaises(ValueError):
            check_continuity(isolated(), measured("primary-return", "structure", 1.0e7))


class TestIsolation(unittest.TestCase):
    def test_a_well_isolated_pair_is_clean(self):
        self.assertEqual(
            check_isolation(
                isolated(),
                measured("primary-return", "structure", 5.0e6, test_voltage_v=100.0),
            ),
            [],
        )

    def test_a_pair_exactly_on_the_floor_is_clean(self):
        self.assertEqual(
            check_isolation(
                isolated(),
                measured("primary-return", "structure", ISOLATION_FLOOR_OHM,
                         test_voltage_v=100.0),
            ),
            [],
        )

    def test_a_degraded_isolation_is_a_finding(self):
        self.assertEqual(
            check_isolation(
                isolated(),
                measured("primary-return", "structure", 1.0e4, test_voltage_v=100.0),
            ),
            ["isolation-resistance-below-the-floor"],
        )

    def test_a_shorted_pair_is_reported_as_continuous(self):
        self.assertEqual(
            check_isolation(
                isolated(),
                measured("primary-return", "structure", 0.05, test_voltage_v=100.0),
            ),
            ["isolated-pair-measured-as-continuous"],
        )

    def test_a_pair_on_the_continuity_threshold_is_a_leakage_finding(self):
        self.assertEqual(
            check_isolation(
                isolated(),
                measured("primary-return", "structure",
                         CONTINUOUS_PAIR_THRESHOLD_OHM, test_voltage_v=100.0),
            ),
            ["isolation-resistance-below-the-floor"],
        )

    def test_an_unrecorded_test_voltage_is_a_finding(self):
        self.assertIn(
            "isolation-test-voltage-not-recorded",
            check_isolation(
                isolated(), measured("primary-return", "structure", 5.0e6)
            ),
        )

    def test_a_low_test_voltage_is_a_finding(self):
        self.assertIn(
            "isolation-test-voltage-below-the-minimum",
            check_isolation(
                isolated(),
                measured("primary-return", "structure", 5.0e6,
                         test_voltage_v=MIN_ISOLATION_TEST_VOLTAGE_V / 2.0),
            ),
        )

    def test_a_bonded_declaration_is_refused_here(self):
        with self.assertRaises(ValueError):
            check_isolation(bonded(), measured())


class TestPairAndCoverage(unittest.TestCase):
    def test_an_unmeasured_bond_is_a_finding(self):
        self.assertEqual(check_pair(bonded(), None), ["declared-bond-not-measured"])

    def test_an_unmeasured_isolation_is_a_finding(self):
        self.assertEqual(
            check_pair(isolated(), None), ["declared-isolation-not-measured"]
        )

    def test_a_measured_pair_is_delegated_by_intent(self):
        self.assertEqual(check_pair(bonded(), measured(resistance=0.001)), [])

    def test_a_declared_pair_with_no_measurement_is_reported(self):
        findings = check_measurement_coverage([bonded()], [])
        self.assertEqual(
            findings, ["declared-pair-not-measured:secondary-return/structure"]
        )

    def test_a_measured_pair_outside_the_architecture_is_reported(self):
        findings = check_measurement_coverage(
            [bonded()], [measured(), measured("spare-bracket", "structure", 0.002)]
        )
        self.assertEqual(
            findings,
            ["measured-pair-absent-from-the-architecture:spare-bracket/structure"],
        )

    def test_a_duplicate_declaration_raises(self):
        with self.assertRaises(ValueError):
            check_measurement_coverage([bonded(), bonded()], [measured()])

    def test_an_empty_declaration_set_raises(self):
        with self.assertRaises(ValueError):
            check_measurement_coverage([], [])


class TestStructureReferences(unittest.TestCase):
    def test_one_reference_per_domain_is_clean(self):
        self.assertEqual(
            structure_reference_findings([bonded(power_domain="payload-secondary")]), []
        )

    def test_a_domain_with_two_references_is_a_finding(self):
        findings = structure_reference_findings(
            [
                bonded(power_domain="payload-secondary"),
                bonded("secondary-return-b", "structure",
                       power_domain="payload-secondary"),
            ]
        )
        self.assertEqual(
            findings,
            ["power-domain-with-multiple-structure-references:payload-secondary"],
        )

    def test_a_domain_with_no_bonded_reference_is_a_finding(self):
        findings = structure_reference_findings(
            [isolated(power_domain="platform-primary")]
        )
        self.assertEqual(
            findings, ["power-domain-without-a-structure-reference:platform-primary"]
        )

    def test_pairs_without_a_domain_are_left_alone(self):
        self.assertEqual(structure_reference_findings([bonded()]), [])


class TestAssessGroundingIsolation(unittest.TestCase):
    def test_a_measured_architecture_is_compliant(self):
        report = assess_grounding_isolation(architecture())
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["compliant"])
        self.assertEqual(len(report["pairs"]), 3)

    def test_a_shorted_isolation_fails_the_architecture(self):
        report = assess_grounding_isolation(
            architecture(
                measurements=[
                    measured(),
                    measured("unit-chassis", "structure", 0.005),
                    measured("primary-return", "structure", 0.02,
                             test_voltage_v=100.0),
                ]
            )
        )
        self.assertFalse(report["compliant"])
        self.assertIn("primary-return/structure", report["non_compliant_pairs"])

    def test_a_loose_bond_fails_the_architecture(self):
        report = assess_grounding_isolation(
            architecture(
                measurements=[
                    measured(resistance=0.05),
                    measured("unit-chassis", "structure", 0.005),
                    measured("primary-return", "structure", 5.0e6,
                             test_voltage_v=100.0),
                ]
            )
        )
        self.assertFalse(report["compliant"])
        self.assertIn(
            "bond-resistance-above-the-category-limit:secondary-return/structure",
            report["findings"],
        )

    def test_an_unmeasured_pair_is_reported_once_by_coverage(self):
        report = assess_grounding_isolation(
            architecture(
                measurements=[
                    measured(),
                    measured("unit-chassis", "structure", 0.005),
                ]
            )
        )
        self.assertIn(
            "declared-pair-not-measured:primary-return/structure", report["findings"]
        )
        self.assertIsNone(report["pairs"][2]["resistance_ohm"])

    def test_a_second_structure_reference_is_reported(self):
        report = assess_grounding_isolation(
            architecture(
                declarations=[
                    bonded(power_domain="payload-secondary"),
                    bonded("unit-chassis", "structure", "unit-chassis-bond",
                           power_domain="payload-secondary"),
                    isolated(),
                ]
            )
        )
        self.assertIn(
            "power-domain-with-multiple-structure-references:payload-secondary",
            report["findings"],
        )

    def test_a_non_mapping_architecture_raises(self):
        with self.assertRaises(ValueError):
            assess_grounding_isolation([bonded()])

    def test_a_missing_declaration_set_raises(self):
        with self.assertRaises(ValueError):
            assess_grounding_isolation({"measurements": []})


if __name__ == "__main__":
    unittest.main()
