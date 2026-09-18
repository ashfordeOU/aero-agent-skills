"""Contract tests for the wire-wrapping applicability and purpose logic."""

import unittest

from q7030_applicability_and_purpose_logic import (
    APPLICABLE_GAUGE_RANGE,
    BASE_REQUIREMENT_AREAS,
    FLIGHT_REQUIREMENT_AREA,
    MIN_GAS_TIGHT_CONTACTS,
    MIN_SHARP_CORNERS,
    MODIFIED_WRAP_AREA,
    WRAPPABLE_SHAPES,
    assess_applicability,
    conductor_exclusions,
    gas_tight_contact_points,
    method_exclusions,
    requirement_areas,
    terminal_exclusions,
)


def _connection(**over):
    base = {
        "connection_method": "solderless-wrap",
        "terminal_shape": "rectangular",
        "sharp_corner_count": 4,
        "conductor_construction": "solid",
        "conductor_gauge_awg": 26,
        "turns": 6,
        "wrap_type": "conventional",
        "application": "flight-hardware",
    }
    base.update(over)
    return base


class MethodScopeTests(unittest.TestCase):
    def test_a_solderless_wrap_is_the_process_in_scope(self):
        self.assertEqual(method_exclusions("solderless-wrap"), [])

    def test_the_method_token_is_normalised(self):
        self.assertEqual(method_exclusions("  Solderless-Wrap "), [])

    def test_a_soldered_joint_is_outside_scope(self):
        exclusions = method_exclusions("soldered")
        self.assertEqual(exclusions[0]["control"], "joining-method")

    def test_a_crimped_joint_is_outside_scope(self):
        self.assertEqual(len(method_exclusions("crimped")), 1)

    def test_a_blank_method_is_rejected(self):
        with self.assertRaises(ValueError):
            method_exclusions("   ")

    def test_a_non_string_method_is_rejected(self):
        with self.assertRaises(ValueError):
            method_exclusions(7)


class TerminalScopeTests(unittest.TestCase):
    def test_every_wrappable_shape_with_enough_corners_is_in_scope(self):
        for shape in WRAPPABLE_SHAPES:
            self.assertEqual(terminal_exclusions(shape, 4), [])

    def test_a_round_post_has_no_corner_to_bite(self):
        exclusions = terminal_exclusions("round", 0)
        controls = [e["control"] for e in exclusions]
        self.assertIn("terminal-shape", controls)
        self.assertIn("terminal-corners", controls)

    def test_a_radiused_post_is_excluded_on_shape_alone(self):
        exclusions = terminal_exclusions("rectangular-with-radiused-corners", 4)
        self.assertEqual([e["control"] for e in exclusions], ["terminal-shape"])

    def test_a_post_on_the_minimum_corner_count_is_in_scope(self):
        self.assertEqual(terminal_exclusions("rectangular", MIN_SHARP_CORNERS), [])

    def test_a_post_one_corner_short_is_excluded(self):
        exclusions = terminal_exclusions("rectangular", MIN_SHARP_CORNERS - 1)
        self.assertEqual(exclusions[0]["control"], "terminal-corners")

    def test_a_negative_corner_count_is_rejected(self):
        with self.assertRaises(ValueError):
            terminal_exclusions("rectangular", -1)

    def test_a_boolean_corner_count_is_rejected(self):
        with self.assertRaises(ValueError):
            terminal_exclusions("rectangular", True)

    def test_a_fractional_corner_count_is_rejected(self):
        with self.assertRaises(ValueError):
            terminal_exclusions("rectangular", 4.0)


class ConductorScopeTests(unittest.TestCase):
    def test_a_solid_conductor_inside_the_span_is_in_scope(self):
        self.assertEqual(conductor_exclusions("solid", 24), [])

    def test_a_stranded_conductor_is_outside_the_process(self):
        exclusions = conductor_exclusions("stranded", 24)
        self.assertEqual(exclusions[0]["control"], "conductor-construction")

    def test_the_thickest_covered_gauge_is_in_scope(self):
        self.assertEqual(conductor_exclusions("solid", APPLICABLE_GAUGE_RANGE[0]), [])

    def test_the_thinnest_covered_gauge_is_in_scope(self):
        self.assertEqual(conductor_exclusions("solid", APPLICABLE_GAUGE_RANGE[1]), [])

    def test_a_wire_thicker_than_the_span_is_excluded(self):
        exclusions = conductor_exclusions("solid", APPLICABLE_GAUGE_RANGE[0] - 1)
        self.assertEqual(exclusions[0]["control"], "conductor-gauge")

    def test_a_wire_thinner_than_the_span_is_excluded(self):
        exclusions = conductor_exclusions("solid", APPLICABLE_GAUGE_RANGE[1] + 1)
        self.assertEqual(exclusions[0]["control"], "conductor-gauge")

    def test_a_stranded_wire_outside_the_span_raises_both_exclusions(self):
        self.assertEqual(len(conductor_exclusions("stranded", 40)), 2)

    def test_a_non_integer_gauge_is_rejected(self):
        with self.assertRaises(ValueError):
            conductor_exclusions("solid", 24.5)


class PurposeTests(unittest.TestCase):
    def test_contacts_are_turns_times_corners(self):
        self.assertEqual(gas_tight_contact_points(6, 4), 24)

    def test_a_post_with_more_corners_yields_more_contacts_at_equal_turns(self):
        self.assertGreater(gas_tight_contact_points(5, 6), gas_tight_contact_points(5, 4))

    def test_no_turns_makes_no_contact_area(self):
        self.assertEqual(gas_tight_contact_points(0, 4), 0)

    def test_a_negative_turn_count_is_rejected(self):
        with self.assertRaises(ValueError):
            gas_tight_contact_points(-1, 4)

    def test_a_boolean_turn_count_is_rejected(self):
        with self.assertRaises(ValueError):
            gas_tight_contact_points(True, 4)


class RequirementAreaTests(unittest.TestCase):
    def test_every_base_area_applies_to_any_wrap(self):
        areas = requirement_areas("conventional", "ground-support-equipment")
        self.assertEqual(areas, list(BASE_REQUIREMENT_AREAS))

    def test_a_modified_wrap_adds_the_insulation_turn_area(self):
        self.assertIn(MODIFIED_WRAP_AREA, requirement_areas("modified", "breadboard"))

    def test_a_conventional_wrap_does_not_carry_the_insulation_turn_area(self):
        self.assertNotIn(
            MODIFIED_WRAP_AREA, requirement_areas("conventional", "breadboard")
        )

    def test_flight_hardware_adds_operator_certification(self):
        self.assertIn(
            FLIGHT_REQUIREMENT_AREA, requirement_areas("conventional", "flight-hardware")
        )

    def test_a_breadboard_does_not_carry_operator_certification(self):
        self.assertNotIn(
            FLIGHT_REQUIREMENT_AREA, requirement_areas("conventional", "breadboard")
        )

    def test_an_unknown_wrap_type_is_rejected(self):
        with self.assertRaises(ValueError):
            requirement_areas("half-wrap", "flight-hardware")


class AssessmentTests(unittest.TestCase):
    def test_a_wrappable_flight_connection_is_within_scope(self):
        result = assess_applicability(_connection())
        self.assertTrue(result["in_scope"])
        self.assertEqual(result["disposition"], "within-scope")
        self.assertEqual(result["exclusions"], [])
        self.assertIn(FLIGHT_REQUIREMENT_AREA, result["requirement_areas"])

    def test_a_crimped_connection_carries_no_requirement_areas(self):
        result = assess_applicability(_connection(connection_method="crimped"))
        self.assertFalse(result["in_scope"])
        self.assertEqual(result["requirement_areas"], [])
        self.assertEqual(result["disposition"], "outside-scope")

    def test_a_round_post_puts_the_connection_outside_scope(self):
        result = assess_applicability(
            _connection(terminal_shape="round", sharp_corner_count=0)
        )
        self.assertEqual(result["disposition"], "outside-scope")
        self.assertEqual(result["gas_tight_contact_points"], 0)

    def test_a_stranded_wire_puts_the_connection_outside_scope(self):
        result = assess_applicability(_connection(conductor_construction="stranded"))
        self.assertFalse(result["in_scope"])

    def test_a_thin_wrap_stays_in_scope_but_owes_actions(self):
        result = assess_applicability(_connection(turns=2))
        self.assertTrue(result["in_scope"])
        self.assertEqual(result["disposition"], "within-scope-with-actions")
        self.assertLess(result["gas_tight_contact_points"], MIN_GAS_TIGHT_CONTACTS)

    def test_a_wrap_exactly_on_the_contact_minimum_needs_no_action(self):
        result = assess_applicability(_connection(turns=3, sharp_corner_count=4))
        self.assertEqual(result["gas_tight_contact_points"], MIN_GAS_TIGHT_CONTACTS)
        self.assertEqual(result["disposition"], "within-scope")

    def test_an_out_of_scope_connection_raises_no_contact_finding(self):
        result = assess_applicability(
            _connection(connection_method="soldered", turns=1)
        )
        self.assertEqual(result["findings"], [])

    def test_several_exclusions_are_all_reported(self):
        result = assess_applicability(
            _connection(
                connection_method="soldered",
                terminal_shape="round",
                sharp_corner_count=0,
                conductor_construction="stranded",
            )
        )
        controls = {e["control"] for e in result["exclusions"]}
        self.assertEqual(
            controls,
            {"joining-method", "terminal-shape", "terminal-corners",
             "conductor-construction"},
        )

    def test_a_modified_flight_wrap_carries_both_extra_areas(self):
        result = assess_applicability(_connection(wrap_type="modified"))
        self.assertIn(MODIFIED_WRAP_AREA, result["requirement_areas"])
        self.assertIn(FLIGHT_REQUIREMENT_AREA, result["requirement_areas"])

    def test_missing_connection_key_rejected(self):
        connection = _connection()
        del connection["turns"]
        with self.assertRaises(ValueError):
            assess_applicability(connection)

    def test_connection_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_applicability([_connection()])


if __name__ == "__main__":
    unittest.main(verbosity=1)
