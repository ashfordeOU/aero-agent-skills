#!/usr/bin/env python3
"""Contract test for explosive-component mechanical design and marking."""

import copy
import unittest

from e3311_mechanical_requirements_colour_coding_logic import (
    DEFAULT_MARKING_POLICY,
    DEFAULT_MECHANICAL_POLICY,
    MARKING_FUNCTIONS,
    assess_explosive_component,
    burst_pressure_mpa,
    check_marking,
    hoop_stress_mpa,
    margin_of_safety,
    proof_pressure_mpa,
    thin_wall_valid,
    validate_colour_scheme,
    validate_marking_policy,
    validate_mechanical_policy,
    verify_mechanical_design,
)

SCHEME = {
    "live-explosive": "olive",
    "inert-replica": "blue",
    "training-unit": "light-blue",
    "expended-unit": "white",
    "handling-fixture": "yellow",
}

CASE = {
    "maximum_expected_pressure_mpa": 20.0,
    "inner_radius_mm": 12.0,
    "wall_thickness_mm": 1.2,
    "yield_strength_mpa": 900.0,
    "ultimate_strength_mpa": 1000.0,
    "colour_scheme": SCHEME,
    "marking": {
        "function": "live-explosive",
        "colour": "olive",
        "text_identifier": "EED-12",
        "serial_number": "SN-4",
    },
}


def _case(**overrides):
    case = copy.deepcopy(CASE)
    case.update(overrides)
    return case


def _scheme(**overrides):
    scheme = copy.deepcopy(SCHEME)
    scheme.update(overrides)
    return scheme


class PolicyTests(unittest.TestCase):
    def test_default_mechanical_policy_validates(self):
        self.assertIs(
            validate_mechanical_policy(DEFAULT_MECHANICAL_POLICY),
            DEFAULT_MECHANICAL_POLICY,
        )

    def test_default_marking_policy_validates(self):
        self.assertIs(
            validate_marking_policy(DEFAULT_MARKING_POLICY), DEFAULT_MARKING_POLICY
        )

    def test_burst_below_proof_rejected(self):
        broken = copy.deepcopy(DEFAULT_MECHANICAL_POLICY)
        broken["burst_factor"] = 1.2
        with self.assertRaises(ValueError):
            validate_mechanical_policy(broken)

    def test_proof_factor_below_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_MECHANICAL_POLICY)
        broken["proof_factor"] = 0.9
        broken["burst_factor"] = 2.5
        with self.assertRaises(ValueError):
            validate_mechanical_policy(broken)

    def test_malformed_confusable_pair_rejected(self):
        broken = copy.deepcopy(DEFAULT_MARKING_POLICY)
        broken["confusable_pairs"] = (("green",),)
        with self.assertRaises(ValueError):
            validate_marking_policy(broken)

    def test_unknown_required_function_rejected(self):
        broken = copy.deepcopy(DEFAULT_MARKING_POLICY)
        broken["required_functions"] = ("decorative-unit",)
        with self.assertRaises(ValueError):
            validate_marking_policy(broken)


class PressureTests(unittest.TestCase):
    def test_proof_and_burst_scale_from_the_operating_pressure(self):
        self.assertAlmostEqual(proof_pressure_mpa(20.0), 30.0, places=9)
        self.assertAlmostEqual(burst_pressure_mpa(20.0), 50.0, places=9)

    def test_zero_operating_pressure_rejected(self):
        with self.assertRaises(ValueError):
            proof_pressure_mpa(0.0)

    def test_hoop_stress_is_pressure_times_radius_over_wall(self):
        self.assertAlmostEqual(hoop_stress_mpa(30.0, 12.0, 1.2), 300.0, places=9)

    def test_thinner_wall_raises_the_stress(self):
        self.assertGreater(
            hoop_stress_mpa(30.0, 12.0, 0.8), hoop_stress_mpa(30.0, 12.0, 1.2)
        )

    def test_zero_wall_rejected(self):
        with self.assertRaises(ValueError):
            hoop_stress_mpa(30.0, 12.0, 0.0)

    def test_thin_wall_form_valid_on_a_slender_wall(self):
        self.assertTrue(thin_wall_valid(12.0, 1.2))

    def test_thin_wall_form_invalid_on_a_thick_wall(self):
        self.assertFalse(thin_wall_valid(12.0, 4.0))

    def test_ratio_exactly_on_the_bound_is_valid(self):
        ratio = 12.0 / 1.2
        self.assertAlmostEqual(
            ratio, DEFAULT_MECHANICAL_POLICY["thin_wall_ratio"], places=9
        )
        self.assertTrue(thin_wall_valid(12.0, 1.2))


class MarginTests(unittest.TestCase):
    def test_margin_is_allowable_over_factored_stress_less_one(self):
        self.assertAlmostEqual(margin_of_safety(1000.0, 500.0, 1.25), 0.6, places=9)

    def test_margin_is_zero_when_sized_exactly(self):
        self.assertAlmostEqual(margin_of_safety(625.0, 500.0, 1.25), 0.0, places=9)

    def test_negative_margin_on_an_undersized_body(self):
        self.assertLess(margin_of_safety(400.0, 500.0, 1.25), 0.0)

    def test_zero_design_factor_rejected(self):
        with self.assertRaises(ValueError):
            margin_of_safety(1000.0, 500.0, 0.0)


class MechanicalVerificationTests(unittest.TestCase):
    def test_sound_body_is_compliant(self):
        result = verify_mechanical_design(CASE)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["proof_hoop_stress_mpa"], 300.0, places=9)
        self.assertAlmostEqual(result["ultimate_margin_of_safety"], 0.6, places=9)

    def test_weak_material_fails_at_burst(self):
        result = verify_mechanical_design(
            _case(ultimate_strength_mpa=500.0, yield_strength_mpa=450.0)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("ultimate margin" in f for f in result["findings"]))

    def test_body_sized_exactly_to_its_allowable_still_passes(self):
        exact = _case(ultimate_strength_mpa=625.0, yield_strength_mpa=400.0)
        result = verify_mechanical_design(exact)
        self.assertAlmostEqual(result["ultimate_margin_of_safety"], 0.0, places=9)
        self.assertTrue(result["compliant"])

    def test_thick_wall_geometry_is_reported(self):
        result = verify_mechanical_design(_case(wall_thickness_mm=4.0))
        self.assertFalse(result["thin_wall_valid"])
        self.assertTrue(any("thin-wall" in f for f in result["findings"]))

    def test_ultimate_below_yield_rejected(self):
        with self.assertRaises(ValueError):
            verify_mechanical_design(
                _case(yield_strength_mpa=1000.0, ultimate_strength_mpa=800.0)
            )

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            verify_mechanical_design("20 MPa")


class ColourSchemeTests(unittest.TestCase):
    def test_a_complete_distinct_scheme_is_valid(self):
        self.assertTrue(validate_colour_scheme(SCHEME)["valid"])

    def test_one_colour_on_two_functions_is_ambiguous(self):
        result = validate_colour_scheme(_scheme(**{"inert-replica": "olive"}))
        self.assertFalse(result["valid"])
        self.assertTrue(any("cannot separate" in f for f in result["findings"]))

    def test_missing_function_is_reported(self):
        partial = copy.deepcopy(SCHEME)
        del partial["expended-unit"]
        result = validate_colour_scheme(partial)
        self.assertFalse(result["valid"])
        self.assertTrue(any("expended-unit" in f for f in result["findings"]))

    def test_reserved_colour_cannot_be_reused(self):
        result = validate_colour_scheme(
            _scheme(**{"handling-fixture": "hazard-reserved-red"})
        )
        self.assertFalse(result["valid"])
        self.assertTrue(any("reserved" in f for f in result["findings"]))

    def test_confusable_pair_around_a_live_unit_is_reported(self):
        result = validate_colour_scheme(
            _scheme(**{"live-explosive": "brown", "inert-replica": "red"})
        )
        self.assertFalse(result["valid"])
        self.assertTrue(any("readily confused" in f for f in result["findings"]))

    def test_confusable_pair_away_from_a_live_unit_is_tolerated(self):
        result = validate_colour_scheme(
            _scheme(**{"training-unit": "green"})
        )
        self.assertTrue(result["valid"])

    def test_unknown_function_in_a_scheme_rejected(self):
        with self.assertRaises(ValueError):
            validate_colour_scheme({"decorative-unit": "pink"})

    def test_empty_scheme_rejected(self):
        with self.assertRaises(ValueError):
            validate_colour_scheme({})


class MarkingTests(unittest.TestCase):
    def test_correct_marking_conforms(self):
        self.assertTrue(check_marking(CASE["marking"], SCHEME)["conforming"])

    def test_wrong_colour_is_reported(self):
        marking = dict(CASE["marking"])
        marking["colour"] = "blue"
        result = check_marking(marking, SCHEME)
        self.assertFalse(result["conforming"])
        self.assertEqual(result["expected_colour"], "olive")

    def test_colour_alone_is_not_a_discriminator(self):
        marking = dict(CASE["marking"])
        marking["text_identifier"] = "   "
        result = check_marking(marking, SCHEME)
        self.assertFalse(result["conforming"])
        self.assertFalse(result["text_identifier_present"])

    def test_live_unit_without_a_serial_is_reported(self):
        marking = dict(CASE["marking"])
        del marking["serial_number"]
        result = check_marking(marking, SCHEME)
        self.assertFalse(result["conforming"])
        self.assertFalse(result["serial_present"])

    def test_inert_unit_needs_no_serial(self):
        marking = {
            "function": "inert-replica",
            "colour": "blue",
            "text_identifier": "INERT-12",
        }
        self.assertTrue(check_marking(marking, SCHEME)["conforming"])

    def test_function_absent_from_the_scheme_rejected(self):
        partial = copy.deepcopy(SCHEME)
        del partial["live-explosive"]
        with self.assertRaises(ValueError):
            check_marking(CASE["marking"], partial)

    def test_unknown_function_rejected(self):
        with self.assertRaises(ValueError):
            check_marking({"function": "decorative-unit", "colour": "pink"}, SCHEME)

    def test_every_function_in_the_scheme_is_checkable(self):
        for function in MARKING_FUNCTIONS:
            marking = {
                "function": function,
                "colour": SCHEME[function],
                "text_identifier": "ID-1",
                "serial_number": "SN-1",
            }
            self.assertTrue(check_marking(marking, SCHEME)["conforming"])


class AssessmentTests(unittest.TestCase):
    def test_sound_component_satisfies_the_clause(self):
        result = assess_explosive_component(CASE)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], "clause-satisfied")

    def test_weak_body_alone_fails_on_the_mechanical_side(self):
        result = assess_explosive_component(
            _case(ultimate_strength_mpa=500.0, yield_strength_mpa=450.0)
        )
        self.assertEqual(result["verdict"], "mechanical-non-compliant")

    def test_ambiguous_scheme_alone_fails_on_the_scheme(self):
        result = assess_explosive_component(
            _case(colour_scheme=_scheme(**{"inert-replica": "olive"}))
        )
        self.assertEqual(result["verdict"], "colour-scheme-ambiguous")

    def test_wrong_unit_colour_alone_fails_on_the_marking(self):
        marking = dict(CASE["marking"])
        marking["colour"] = "white"
        result = assess_explosive_component(_case(marking=marking))
        self.assertEqual(result["verdict"], "marking-non-compliant")

    def test_both_halves_failing_is_reported_as_both(self):
        marking = dict(CASE["marking"])
        marking["colour"] = "white"
        result = assess_explosive_component(
            _case(
                marking=marking,
                ultimate_strength_mpa=500.0,
                yield_strength_mpa=450.0,
            )
        )
        self.assertEqual(result["verdict"], "mechanical-and-marking-non-compliant")
        self.assertGreater(len(result["findings"]), 1)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_explosive_component("a detonator")


if __name__ == "__main__":
    unittest.main()
