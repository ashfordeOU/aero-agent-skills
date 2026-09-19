"""Contract test for the OBCP parameter leaf (stdlib unittest)."""

import unittest

from e7041_parameter_logic import (
    BITS_PER_OCTET,
    assess_obcp_parameters,
    bind_arguments,
    check_value,
    encoded_size_bits,
    encoded_size_octets,
    type_accepts,
    validate_declaration,
    validate_parameter_definition,
)


def unsigned(name="duration", bits=16, **kw):
    record = {"name": name, "type": "unsigned", "bits": bits,
              "minimum": 0, "maximum": 3600}
    record.update(kw)
    return record


def enumerated(name="mode", **kw):
    record = {"name": name, "type": "enumerated", "bits": 8,
              "values": ["safe", "nominal", "survival"]}
    record.update(kw)
    return record


DECLARATION = [
    unsigned("duration"),
    {"name": "threshold", "type": "real", "bits": 32,
     "minimum": -50.0, "maximum": 150.0},
    {"name": "latching", "type": "boolean", "bits": 1},
    enumerated("mode", required=False, default="nominal"),
]


class TestTypeAcceptance(unittest.TestCase):
    def test_boolean_is_not_a_narrow_unsigned(self):
        self.assertFalse(type_accepts("unsigned", True))

    def test_boolean_takes_a_boolean(self):
        self.assertTrue(type_accepts("boolean", False))

    def test_integer_is_an_acceptable_real(self):
        self.assertTrue(type_accepts("real", 7))

    def test_real_is_not_an_acceptable_unsigned(self):
        self.assertFalse(type_accepts("unsigned", 7.5))

    def test_negative_integer_is_not_unsigned(self):
        self.assertFalse(type_accepts("unsigned", -1))

    def test_negative_integer_is_signed(self):
        self.assertTrue(type_accepts("signed", -1))

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            type_accepts("octet-string", 1)


class TestDefinitionValidation(unittest.TestCase):
    def test_valid_definition_normalises(self):
        norm = validate_parameter_definition(unsigned())
        self.assertEqual(norm["bits"], 16)
        self.assertTrue(norm["required"])
        self.assertFalse(norm["has_default"])

    def test_zero_width_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(unsigned(bits=0))

    def test_boolean_wider_than_one_bit_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(
                {"name": "latching", "type": "boolean", "bits": 8}
            )

    def test_inverted_range_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(unsigned(minimum=100, maximum=10))

    def test_negative_minimum_on_unsigned_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(unsigned(minimum=-1))

    def test_empty_enumerated_set_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(enumerated(values=[]))

    def test_repeated_enumerated_value_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(enumerated(values=["safe", "safe"]))

    def test_default_failing_its_own_declaration_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(enumerated(default="hibernate"))

    def test_default_inside_the_declaration_is_kept(self):
        norm = validate_parameter_definition(enumerated(default="safe"))
        self.assertTrue(norm["has_default"])
        self.assertEqual(norm["default"], "safe")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition({"name": "x", "type": "blob", "bits": 8})


class TestDeclarationValidation(unittest.TestCase):
    def test_declaration_order_is_preserved(self):
        parameters = validate_declaration(DECLARATION)
        self.assertEqual([p["name"] for p in parameters],
                         ["duration", "threshold", "latching", "mode"])

    def test_duplicate_name_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration([unsigned("duration"), unsigned("duration")])

    def test_required_after_optional_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(
                [unsigned("a", required=False, default=1), unsigned("b")]
            )

    def test_revalidating_a_normalised_declaration_is_idempotent(self):
        once = validate_declaration(DECLARATION)
        self.assertEqual(validate_declaration(once), once)

    def test_non_sequence_declaration_raises(self):
        with self.assertRaises(ValueError):
            validate_declaration(unsigned())


class TestValueChecking(unittest.TestCase):
    def setUp(self):
        self.parameters = validate_declaration(DECLARATION)

    def test_in_range_value_is_usable(self):
        self.assertEqual(check_value(self.parameters[0], 600), (True, None))

    def test_value_on_the_declared_maximum_is_usable(self):
        usable, reason = check_value(self.parameters[0], 3600)
        self.assertTrue(usable)
        self.assertIsNone(reason)

    def test_value_above_the_maximum_is_refused(self):
        usable, reason = check_value(self.parameters[0], 3601)
        self.assertFalse(usable)
        self.assertIn("above the declared maximum", reason)

    def test_value_below_the_minimum_is_refused(self):
        usable, reason = check_value(self.parameters[1], -60.0)
        self.assertFalse(usable)
        self.assertIn("below the declared minimum", reason)

    def test_wrong_type_is_refused_before_any_range_talk(self):
        usable, reason = check_value(self.parameters[0], 12.5)
        self.assertFalse(usable)
        self.assertIn("not compatible with declared type", reason)

    def test_enumerated_member_is_usable(self):
        self.assertEqual(check_value(self.parameters[3], "survival"), (True, None))

    def test_value_outside_the_enumerated_set_is_refused(self):
        usable, reason = check_value(self.parameters[3], "hibernate")
        self.assertFalse(usable)
        self.assertIn("outside the enumerated set", reason)


class TestBinding(unittest.TestCase):
    def test_positional_binding_in_declared_order(self):
        result = bind_arguments(DECLARATION, [600, 20.0, True])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["bound"]["duration"], 600)
        self.assertEqual(result["bound"]["mode"], "nominal")

    def test_positional_binding_in_the_wrong_order_is_caught_by_type(self):
        result = bind_arguments(DECLARATION, [20.0, 600, True])
        self.assertTrue(result["findings"])

    def test_too_many_positional_arguments_is_its_own_finding(self):
        result = bind_arguments(DECLARATION, [600, 20.0, True, "safe", 1])
        self.assertTrue(
            any("5 arguments supplied" in f for f in result["findings"])
        )

    def test_missing_required_argument_is_a_finding(self):
        result = bind_arguments(DECLARATION, [600])
        self.assertTrue(
            any("required parameter threshold" in f for f in result["findings"])
        )

    def test_binding_by_name(self):
        result = bind_arguments(
            DECLARATION,
            {"duration": 10, "threshold": 1.0, "latching": False, "mode": "safe"},
        )
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["bound"]["mode"], "safe")

    def test_unknown_argument_name_is_a_finding(self):
        result = bind_arguments(
            DECLARATION,
            {"duration": 10, "threshold": 1.0, "latching": False, "speed": 3},
        )
        self.assertTrue(
            any("names no declared parameter" in f for f in result["findings"])
        )

    def test_omitted_optional_without_a_default_is_a_finding(self):
        declaration = [unsigned("duration"),
                       unsigned("margin", required=False)]
        result = bind_arguments(declaration, [600])
        self.assertTrue(
            any("declares no default" in f for f in result["findings"])
        )
        self.assertNotIn("margin", result["bound"])

    def test_default_is_applied_not_invented(self):
        result = bind_arguments(DECLARATION, [600, 20.0, True])
        self.assertEqual(result["bound"]["mode"], "nominal")

    def test_non_sequence_arguments_raise(self):
        with self.assertRaises(ValueError):
            bind_arguments(DECLARATION, 600)


class TestEncodedSize(unittest.TestCase):
    def test_size_follows_the_declaration_not_the_value(self):
        small = bind_arguments(DECLARATION, [1, 0.0, False])["bound"]
        large = bind_arguments(DECLARATION, [3600, 150.0, True])["bound"]
        self.assertEqual(
            encoded_size_bits(DECLARATION, small),
            encoded_size_bits(DECLARATION, large),
        )

    def test_bits_are_the_sum_of_the_declared_widths(self):
        bound = bind_arguments(DECLARATION, [600, 20.0, True])["bound"]
        self.assertEqual(encoded_size_bits(DECLARATION, bound), 16 + 32 + 1 + 8)

    def test_octets_round_up(self):
        bound = bind_arguments(DECLARATION, [600, 20.0, True])["bound"]
        bits = encoded_size_bits(DECLARATION, bound)
        self.assertEqual(
            encoded_size_octets(DECLARATION, bound),
            (bits + BITS_PER_OCTET - 1) // BITS_PER_OCTET,
        )

    def test_unbound_parameter_contributes_nothing(self):
        self.assertEqual(encoded_size_bits(DECLARATION, {"duration": 1}), 16)

    def test_non_mapping_bound_raises(self):
        with self.assertRaises(ValueError):
            encoded_size_bits(DECLARATION, ["duration"])


class TestAssessment(unittest.TestCase):
    def test_usable_argument_list(self):
        report = assess_obcp_parameters(
            {"declaration": DECLARATION, "arguments": [600, 20.0, True]}
        )
        self.assertTrue(report["usable"])
        self.assertEqual(report["bound_count"], 4)
        self.assertEqual(report["declared_count"], 4)
        # 16 + 32 + 1 + 8 = 57 bits, which occupies 8 whole octets.
        self.assertEqual(report["encoded_size_bits"], 57)
        self.assertEqual(report["encoded_size_octets"], 8)

    def test_range_violation_makes_the_list_unusable(self):
        report = assess_obcp_parameters(
            {"declaration": DECLARATION, "arguments": [4000, 20.0, True]}
        )
        self.assertFalse(report["usable"])
        self.assertEqual(report["bound_count"], 3)

    def test_octet_budget_is_enforced(self):
        report = assess_obcp_parameters(
            {"declaration": DECLARATION, "arguments": [600, 20.0, True],
             "max_octets": 4}
        )
        self.assertFalse(report["usable"])
        self.assertTrue(any("past the 4 octets" in f for f in report["findings"]))

    def test_generous_budget_is_clean(self):
        report = assess_obcp_parameters(
            {"declaration": DECLARATION, "arguments": [600, 20.0, True],
             "max_octets": 16}
        )
        self.assertTrue(report["usable"])

    def test_zero_budget_raises(self):
        with self.assertRaises(ValueError):
            assess_obcp_parameters(
                {"declaration": DECLARATION, "arguments": [600, 20.0, True],
                 "max_octets": 0}
            )

    def test_missing_spec_key_raises(self):
        with self.assertRaises(ValueError):
            assess_obcp_parameters({"declaration": DECLARATION})

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_obcp_parameters([DECLARATION])


if __name__ == "__main__":
    unittest.main()
