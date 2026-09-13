#!/usr/bin/env python3
"""Contract test for e20-antenna-design-baseline-definition (stdlib unittest)."""

import unittest

from e20_antenna_design_baseline_definition_logic import (
    BASELINE_FREEZE_MILESTONE,
    assess_design_baseline,
    categorize_antenna,
    check_baseline_freeze,
    check_performance_parameters,
    milestone_index,
    validate_element_set,
    validate_technology_selection,
)

REFLECTOR_ELEMENTS = [
    {"role": "reflector-surface", "technology": "carbon-fibre-shell", "readiness": 8},
    {"role": "feed-chain", "technology": "corrugated-horn", "readiness": 8},
    {"role": "support-structure", "technology": "carbon-fibre-strut", "readiness": 9},
]

GOOD_PARAMETERS = {
    "frequency-band-ghz": 19.7,
    "peak-gain-dbi": 34.5,
    "half-power-beamwidth-deg": 2.4,
    "axial-ratio-db": 1.2,
    "input-return-loss-db": 20.0,
    "polarization": "right-hand-circular",
}


def good_definition(**overrides):
    definition = {
        "id": "ka-band-user-link-antenna",
        "build": "parabolic-reflector",
        "milestone": "pdr",
        "elements": [dict(e) for e in REFLECTOR_ELEMENTS],
        "parameters": dict(GOOD_PARAMETERS),
        "open_items": [],
    }
    definition.update(overrides)
    return definition


class TestFamilyCategorization(unittest.TestCase):
    def test_parabolic_build_maps_to_the_reflector_family(self):
        self.assertEqual(categorize_antenna("parabolic-reflector"), "reflector")

    def test_phased_build_maps_to_the_array_family(self):
        self.assertEqual(categorize_antenna("phased-array"), "array")

    def test_helix_build_maps_to_the_wire_family(self):
        self.assertEqual(categorize_antenna("helix"), "wire")

    def test_build_name_is_case_and_whitespace_insensitive(self):
        self.assertEqual(categorize_antenna("  Dielectric-Lens "), "lens")

    def test_unknown_build_raises(self):
        with self.assertRaises(ValueError):
            categorize_antenna("metamaterial-aperture")

    def test_empty_build_raises(self):
        with self.assertRaises(ValueError):
            categorize_antenna("")


class TestMilestoneOrdering(unittest.TestCase):
    def test_reviews_are_ordered_along_the_design_cycle(self):
        self.assertLess(milestone_index("srr"), milestone_index("pdr"))
        self.assertLess(milestone_index("pdr"), milestone_index("cdr"))

    def test_freeze_milestone_resolves(self):
        self.assertEqual(
            milestone_index(BASELINE_FREEZE_MILESTONE), milestone_index("pdr")
        )

    def test_unknown_milestone_raises(self):
        with self.assertRaises(ValueError):
            milestone_index("flight-acceptance")


class TestElementSet(unittest.TestCase):
    def test_complete_reflector_set_is_clean(self):
        self.assertEqual(validate_element_set("reflector", REFLECTOR_ELEMENTS), [])

    def test_missing_feed_chain_is_a_finding(self):
        elements = [e for e in REFLECTOR_ELEMENTS if e["role"] != "feed-chain"]
        findings = validate_element_set("reflector", elements)
        self.assertEqual(len(findings), 1)
        self.assertIn("feed-chain", findings[0])

    def test_element_from_another_family_is_a_finding(self):
        elements = list(REFLECTOR_ELEMENTS) + [
            {"role": "beam-forming-network", "technology": "stripline-network",
             "readiness": 7}
        ]
        findings = validate_element_set("reflector", elements)
        self.assertTrue(any("does not belong" in f for f in findings))

    def test_array_family_requires_a_beam_forming_network(self):
        elements = [
            {"role": "radiating-element", "technology": "microstrip-patch",
             "readiness": 7},
            {"role": "support-structure", "technology": "aluminium-bracket",
             "readiness": 9},
        ]
        findings = validate_element_set("array", elements)
        self.assertTrue(any("beam-forming-network" in f for f in findings))

    def test_unknown_element_role_raises(self):
        with self.assertRaises(ValueError):
            validate_element_set(
                "reflector",
                [{"role": "radome", "technology": "quartz", "readiness": 6}],
            )

    def test_duplicate_element_role_raises(self):
        with self.assertRaises(ValueError):
            validate_element_set("reflector", REFLECTOR_ELEMENTS + [
                dict(REFLECTOR_ELEMENTS[0])
            ])

    def test_empty_element_list_raises(self):
        with self.assertRaises(ValueError):
            validate_element_set("reflector", [])

    def test_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            validate_element_set("reflectarray", REFLECTOR_ELEMENTS)


class TestTechnologySelection(unittest.TestCase):
    def test_admissible_mature_technology_is_clean(self):
        self.assertEqual(
            validate_technology_selection(
                "reflector-surface", "carbon-fibre-shell", 8, "pdr"
            ),
            [],
        )

    def test_technology_outside_the_role_is_a_finding(self):
        findings = validate_technology_selection(
            "reflector-surface", "coaxial-line", 9, "pdr"
        )
        self.assertTrue(any("not an admissible" in f for f in findings))

    def test_immature_technology_at_the_freeze_is_a_finding(self):
        findings = validate_technology_selection(
            "beam-forming-network", "digital-beam-former", 3, "pdr"
        )
        self.assertTrue(any("maturity" in f for f in findings))

    def test_immature_technology_before_the_freeze_is_tolerated(self):
        self.assertEqual(
            validate_technology_selection(
                "beam-forming-network", "digital-beam-former", 3, "srr"
            ),
            [],
        )

    def test_maturity_exactly_at_the_threshold_is_tolerated(self):
        self.assertEqual(
            validate_technology_selection(
                "beam-forming-network", "digital-beam-former", 5, "pdr"
            ),
            [],
        )

    def test_maturity_outside_one_to_nine_raises(self):
        with self.assertRaises(ValueError):
            validate_technology_selection(
                "feed-chain", "corrugated-horn", 12, "pdr"
            )

    def test_non_integer_maturity_raises(self):
        with self.assertRaises(ValueError):
            validate_technology_selection(
                "feed-chain", "corrugated-horn", 7.5, "pdr"
            )

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            validate_technology_selection("radome", "quartz", 6, "pdr")


class TestPerformanceParameters(unittest.TestCase):
    def test_complete_parameter_set_is_clean(self):
        self.assertEqual(check_performance_parameters(GOOD_PARAMETERS), [])

    def test_missing_parameter_is_a_finding(self):
        parameters = dict(GOOD_PARAMETERS)
        del parameters["axial-ratio-db"]
        findings = check_performance_parameters(parameters)
        self.assertEqual(len(findings), 1)
        self.assertIn("axial-ratio-db", findings[0])

    def test_out_of_bounds_parameter_is_a_finding(self):
        parameters = dict(GOOD_PARAMETERS)
        parameters["peak-gain-dbi"] = 95.0
        findings = check_performance_parameters(parameters)
        self.assertTrue(any("outside its declared bounds" in f for f in findings))

    def test_value_exactly_at_the_upper_bound_is_accepted(self):
        parameters = dict(GOOD_PARAMETERS)
        parameters["peak-gain-dbi"] = 70.0
        self.assertEqual(check_performance_parameters(parameters), [])

    def test_bound_reached_by_a_sum_of_contributions_is_accepted(self):
        # A gain built from stage contributions can land a few ULPs above the
        # declared ceiling; the physically compliant case must still pass.
        parameters = dict(GOOD_PARAMETERS)
        parameters["peak-gain-dbi"] = 69.9 + 0.1
        self.assertEqual(check_performance_parameters(parameters), [])

    def test_unrecognized_polarization_is_a_finding(self):
        parameters = dict(GOOD_PARAMETERS)
        parameters["polarization"] = "slant-45"
        findings = check_performance_parameters(parameters)
        self.assertTrue(any("not a recognized scheme" in f for f in findings))

    def test_extra_parameter_outside_the_fixed_set_is_a_finding(self):
        parameters = dict(GOOD_PARAMETERS)
        parameters["mass-kg"] = 4.2
        findings = check_performance_parameters(parameters)
        self.assertTrue(any("not part of the fixed" in f for f in findings))

    def test_non_numeric_parameter_raises(self):
        parameters = dict(GOOD_PARAMETERS)
        parameters["frequency-band-ghz"] = "ka"
        with self.assertRaises(ValueError):
            check_performance_parameters(parameters)

    def test_non_mapping_parameters_raise(self):
        with self.assertRaises(ValueError):
            check_performance_parameters(["frequency-band-ghz"])


class TestBaselineFreeze(unittest.TestCase):
    def test_open_item_before_the_freeze_is_tolerated(self):
        self.assertEqual(check_baseline_freeze(["feed-chain-technology"], "srr"), [])

    def test_open_item_at_the_freeze_is_a_finding(self):
        findings = check_baseline_freeze(["feed-chain-technology"], "pdr")
        self.assertEqual(len(findings), 1)

    def test_open_items_after_the_freeze_are_all_findings(self):
        findings = check_baseline_freeze(["polarization", "peak-gain"], "cdr")
        self.assertEqual(len(findings), 2)

    def test_non_sequence_open_items_raise(self):
        with self.assertRaises(ValueError):
            check_baseline_freeze("polarization", "cdr")


class TestBaselineRollUp(unittest.TestCase):
    def test_complete_baseline_is_compliant(self):
        result = assess_design_baseline(good_definition())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["family"], "reflector")
        self.assertEqual(result["element_count"], 3)
        self.assertTrue(result["frozen_expected"])

    def test_early_milestone_is_not_yet_expected_to_be_frozen(self):
        result = assess_design_baseline(good_definition(milestone="srr"))
        self.assertFalse(result["frozen_expected"])

    def test_findings_from_several_checks_accumulate(self):
        definition = good_definition(open_items=["polarization"])
        definition["elements"][1]["technology"] = "coaxial-line"
        del definition["parameters"]["axial-ratio-db"]
        result = assess_design_baseline(definition)
        self.assertFalse(result["compliant"])
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_array_baseline_rolls_up_clean(self):
        definition = good_definition(
            id="s-band-array",
            build="direct-radiating-array",
            elements=[
                {"role": "radiating-element", "technology": "microstrip-patch",
                 "readiness": 8},
                {"role": "beam-forming-network", "technology": "stripline-network",
                 "readiness": 7},
                {"role": "support-structure", "technology": "aluminium-bracket",
                 "readiness": 9},
            ],
        )
        result = assess_design_baseline(definition)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["family"], "array")

    def test_missing_identifier_raises(self):
        definition = good_definition()
        del definition["id"]
        with self.assertRaises(ValueError):
            assess_design_baseline(definition)

    def test_missing_elements_raise(self):
        definition = good_definition()
        del definition["elements"]
        with self.assertRaises(ValueError):
            assess_design_baseline(definition)

    def test_non_mapping_definition_raises(self):
        with self.assertRaises(ValueError):
            assess_design_baseline("ka-band-user-link-antenna")


if __name__ == "__main__":
    unittest.main()
