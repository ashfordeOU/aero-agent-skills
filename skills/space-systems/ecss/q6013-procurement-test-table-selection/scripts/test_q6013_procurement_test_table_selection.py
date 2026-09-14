"""Contract tests for the clause 8.2 procurement test table selection logic."""

import unittest

from q6013_procurement_test_table_selection_logic import (
    APPLICABILITY_TOLERANCE,
    ASSURANCE_CLASSES,
    COMPONENT_TYPES,
    FAMILY_BY_TYPE_AND_TECHNOLOGY,
    TECHNOLOGIES,
    TEST_TABLES,
    applicability_fraction,
    applicable_groups,
    deferred_groups,
    normalize_token,
    reconcile_waivers,
    resolve_family,
    select_procurement_test_table,
    table_for_family,
    table_groups,
    validate_assurance_class,
    validate_component_type,
    validate_technology,
)


def _part(**overrides):
    part = {
        "part_number": "MC-7742-CM",
        "component_type": "microcircuit",
        "technology": "monolithic",
        "assurance_class": 2,
    }
    part.update(overrides)
    return part


class TokenValidationTests(unittest.TestCase):
    def test_token_normalization_is_hyphenated_lower_case(self):
        self.assertEqual(normalize_token("Wound_Magnetics"), "wound-magnetics")

    def test_every_component_type_validates(self):
        for token in COMPONENT_TYPES:
            self.assertEqual(validate_component_type(token), token)

    def test_every_technology_validates(self):
        for token in TECHNOLOGIES:
            self.assertEqual(validate_technology(token), token)

    def test_unknown_component_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_component_type("flux-capacitor-assembly")

    def test_unknown_technology_rejected(self):
        with self.assertRaises(ValueError):
            validate_technology("hand-wound-guesswork")

    def test_blank_component_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_component_type("   ")

    def test_non_string_technology_rejected(self):
        with self.assertRaises(ValueError):
            validate_technology(7)

    def test_every_assurance_class_validates(self):
        for value in ASSURANCE_CLASSES:
            self.assertEqual(validate_assurance_class(value), value)

    def test_class_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_assurance_class(0)

    def test_boolean_class_rejected(self):
        with self.assertRaises(ValueError):
            validate_assurance_class(True)

    def test_string_class_rejected(self):
        with self.assertRaises(ValueError):
            validate_assurance_class("2")


class FamilyResolutionTests(unittest.TestCase):
    def test_monolithic_microcircuit_resolves(self):
        self.assertEqual(
            resolve_family("microcircuit", "monolithic"), "monolithic-microcircuit"
        )

    def test_same_type_different_technology_resolves_differently(self):
        self.assertNotEqual(
            resolve_family("microcircuit", "monolithic"),
            resolve_family("microcircuit", "hybrid"),
        )

    def test_same_technology_different_type_resolves_differently(self):
        self.assertEqual(resolve_family("capacitor", "film"), "film-capacitor")
        self.assertEqual(resolve_family("resistor", "film"), "film-resistor")

    def test_technology_alone_cannot_decide_the_family(self):
        film_families = {
            family
            for (_type, technology), family in FAMILY_BY_TYPE_AND_TECHNOLOGY.items()
            if technology == "film"
        }
        self.assertGreater(len(film_families), 1)

    def test_unpaired_type_and_technology_rejected(self):
        with self.assertRaises(ValueError):
            resolve_family("relay", "monolithic")

    def test_every_defined_pair_resolves_to_a_table(self):
        for pair, family in FAMILY_BY_TYPE_AND_TECHNOLOGY.items():
            self.assertEqual(resolve_family(pair[0], pair[1]), family)
            self.assertIn(family, TEST_TABLES)

    def test_every_family_has_a_distinct_table_identifier(self):
        tables = [entry["table"] for entry in TEST_TABLES.values()]
        self.assertEqual(len(tables), len(set(tables)))

    def test_unknown_family_has_no_table(self):
        with self.assertRaises(ValueError):
            table_for_family("interstellar-widget")


class TableGroupTests(unittest.TestCase):
    def test_table_groups_are_returned_in_table_order(self):
        groups = table_groups("tantalum-capacitor")
        self.assertEqual(groups[0], "external-visual-inspection")

    def test_class_three_gets_the_always_applicable_groups(self):
        groups = applicable_groups("monolithic-microcircuit", 3)
        self.assertIn("external-visual-inspection", groups)
        self.assertNotIn("burn-in", groups)

    def test_class_one_gets_the_whole_table(self):
        family = "monolithic-microcircuit"
        self.assertEqual(
            applicable_groups(family, 1), table_groups(family)
        )

    def test_class_one_applicability_is_unity(self):
        self.assertAlmostEqual(
            applicability_fraction("monolithic-microcircuit", 1), 1.0, places=9
        )

    def test_class_three_applicability_is_a_partial_fraction(self):
        fraction = applicability_fraction("monolithic-microcircuit", 3)
        self.assertAlmostEqual(fraction, 2.0 / 7.0, places=9)

    def test_applicability_never_rises_with_a_weaker_class(self):
        for family in TEST_TABLES:
            one = applicability_fraction(family, 1)
            two = applicability_fraction(family, 2)
            three = applicability_fraction(family, 3)
            self.assertGreaterEqual(one + APPLICABILITY_TOLERANCE, two)
            self.assertGreaterEqual(two + APPLICABILITY_TOLERANCE, three)

    def test_applicable_and_deferred_partition_the_table(self):
        for family in TEST_TABLES:
            for declared in ASSURANCE_CLASSES:
                applicable = applicable_groups(family, declared)
                deferred = deferred_groups(family, declared)
                self.assertEqual(
                    sorted(applicable + deferred), sorted(table_groups(family))
                )
                self.assertEqual(
                    set(applicable) & set(deferred), set()
                )

    def test_class_one_defers_nothing(self):
        for family in TEST_TABLES:
            self.assertEqual(deferred_groups(family, 1), [])

    def test_every_table_carries_external_visual_inspection_at_every_class(self):
        for family in TEST_TABLES:
            for declared in ASSURANCE_CLASSES:
                self.assertIn(
                    "external-visual-inspection",
                    applicable_groups(family, declared),
                )

    def test_applicability_tolerance_is_representation_sized(self):
        self.assertLess(APPLICABILITY_TOLERANCE, 1e-6)

    def test_unknown_family_groups_rejected(self):
        with self.assertRaises(ValueError):
            applicable_groups("interstellar-widget", 1)


class WaiverTests(unittest.TestCase):
    def test_waiver_against_an_applicable_group_is_effective(self):
        result = reconcile_waivers(["burn-in"], {"burn-in"}, {"burn-in"})
        self.assertEqual(result["effective_waivers"], ["burn-in"])

    def test_waiver_against_a_deferred_group_is_redundant(self):
        result = reconcile_waivers(["burn-in"], set(), {"burn-in"})
        self.assertEqual(result["already_deferred"], ["burn-in"])

    def test_waiver_against_an_absent_group_is_unknown(self):
        result = reconcile_waivers(["moon-dust-exposure"], set(), {"burn-in"})
        self.assertEqual(result["unknown_groups"], ["moon-dust-exposure"])

    def test_no_waivers_reconciles_empty(self):
        result = reconcile_waivers(None, {"burn-in"}, {"burn-in"})
        self.assertEqual(result["requested"], [])

    def test_repeated_waiver_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_waivers(["burn-in", "burn_in"], {"burn-in"}, {"burn-in"})

    def test_non_sequence_waivers_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_waivers("burn-in", {"burn-in"}, {"burn-in"})


class SelectionTests(unittest.TestCase):
    def test_clean_part_settles_on_one_table(self):
        result = select_procurement_test_table(_part())
        self.assertEqual(result["family"], "monolithic-microcircuit")
        self.assertEqual(result["table"], "procurement-table-a")
        self.assertTrue(result["single_table_governs"])
        self.assertTrue(result["selection_settled"])
        self.assertEqual(result["findings"], [])

    def test_class_one_part_reports_the_whole_table(self):
        result = select_procurement_test_table(_part(assurance_class=1))
        self.assertTrue(result["whole_table_applies"])
        self.assertAlmostEqual(result["applicability_fraction"], 1.0, places=9)
        self.assertEqual(result["deferred_groups"], [])

    def test_class_three_part_defers_the_higher_class_groups(self):
        result = select_procurement_test_table(_part(assurance_class=3))
        self.assertFalse(result["whole_table_applies"])
        self.assertIn("burn-in", result["deferred_groups"])

    def test_relay_and_microcircuit_select_different_tables(self):
        relay = select_procurement_test_table(
            _part(component_type="relay", technology="electromechanical")
        )
        micro = select_procurement_test_table(_part())
        self.assertNotEqual(relay["table"], micro["table"])

    def test_multifunction_part_reports_a_table_conflict(self):
        result = select_procurement_test_table(
            _part(
                additional_functions=[
                    {"component_type": "semiconductor", "technology": "optocoupler"}
                ]
            )
        )
        self.assertFalse(result["single_table_governs"])
        self.assertEqual(result["additional_families"], ["optocoupler"])
        self.assertFalse(result["selection_settled"])

    def test_additional_function_of_the_same_family_is_not_a_conflict(self):
        result = select_procurement_test_table(
            _part(
                additional_functions=[
                    {"component_type": "microcircuit", "technology": "monolithic"}
                ]
            )
        )
        self.assertTrue(result["single_table_governs"])
        self.assertTrue(result["selection_settled"])

    def test_repeated_additional_family_is_reported_once(self):
        result = select_procurement_test_table(
            _part(
                additional_functions=[
                    {"component_type": "relay", "technology": "electromechanical"},
                    {"component_type": "relay", "technology": "electromechanical"},
                ]
            )
        )
        self.assertEqual(result["additional_families"], ["electromechanical-relay"])

    def test_malformed_additional_function_rejected(self):
        with self.assertRaises(ValueError):
            select_procurement_test_table(
                _part(additional_functions=[{"component_type": "relay"}])
            )

    def test_effective_waiver_reaches_the_verdict(self):
        result = select_procurement_test_table(
            _part(proposed_waivers=["burn-in"])
        )
        self.assertEqual(result["waivers"]["effective_waivers"], ["burn-in"])
        self.assertFalse(result["selection_settled"])

    def test_redundant_waiver_is_named_as_redundant(self):
        result = select_procurement_test_table(
            _part(assurance_class=3, proposed_waivers=["burn-in"])
        )
        self.assertEqual(result["waivers"]["already_deferred"], ["burn-in"])
        self.assertTrue(any("redundant" in f for f in result["findings"]))

    def test_unknown_waiver_group_is_named(self):
        result = select_procurement_test_table(
            _part(proposed_waivers=["moon-dust-exposure"])
        )
        self.assertEqual(
            result["waivers"]["unknown_groups"], ["moon-dust-exposure"]
        )

    def test_missing_part_key_rejected(self):
        part = _part()
        del part["technology"]
        with self.assertRaises(ValueError):
            select_procurement_test_table(part)

    def test_blank_part_number_rejected(self):
        with self.assertRaises(ValueError):
            select_procurement_test_table(_part(part_number="  "))

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            select_procurement_test_table(["microcircuit"])

    def test_every_finding_is_named_not_only_the_first(self):
        result = select_procurement_test_table(
            _part(
                additional_functions=[
                    {"component_type": "relay", "technology": "electromechanical"}
                ],
                proposed_waivers=["burn-in", "moon-dust-exposure"],
            )
        )
        self.assertGreaterEqual(len(result["findings"]), 3)


if __name__ == "__main__":
    unittest.main()
