"""Contract test for the e7041 on-board parameter definition leaf."""

import unittest

from e7041_parameter_definition_logic import (
    ACCESS_MODES,
    REPRESENTATIONS,
    VERDICT_SOUND,
    VERDICT_UNSOUND,
    assess_catalogue,
    effective_domain,
    representable_domain,
    validate_catalogue,
    validate_parameter_definition,
    value_belongs,
)


def definition(parameter_id="PAR-BUS-VOLTAGE", apid="AP-PWR",
               representation="unsigned-integer", **kw):
    record = {
        "application_process_id": apid,
        "parameter_id": parameter_id,
        "representation": representation,
    }
    if representation in ("unsigned-integer", "signed-integer"):
        record.setdefault("bits", 8)
    if representation == "enumerated":
        record.setdefault("codes", ["OFF", "STANDBY", "ON"])
    if representation == "octet-string":
        record.setdefault("length", 4)
    record.update(kw)
    return record


class TestRepresentableDomain(unittest.TestCase):
    def test_an_eight_bit_unsigned_domain_is_exact(self):
        domain = representable_domain("unsigned-integer", 8)
        self.assertEqual(domain["lower"], 0)
        self.assertEqual(domain["upper"], 255)

    def test_a_sixteen_bit_signed_domain_is_exact(self):
        domain = representable_domain("signed-integer", 16)
        self.assertEqual(domain["lower"], -32768)
        self.assertEqual(domain["upper"], 32767)

    def test_a_wide_unsigned_domain_is_derived_without_float_error(self):
        domain = representable_domain("unsigned-integer", 64)
        self.assertEqual(domain["upper"], (1 << 64) - 1)
        self.assertIsInstance(domain["upper"], int)

    def test_a_one_bit_signed_parameter_is_refused(self):
        with self.assertRaises(ValueError):
            representable_domain("signed-integer", 1)

    def test_a_zero_width_integer_is_refused(self):
        with self.assertRaises(ValueError):
            representable_domain("unsigned-integer", 0)

    def test_a_non_integer_width_is_refused(self):
        with self.assertRaises(ValueError):
            representable_domain("unsigned-integer", 8.0)

    def test_a_real_parameter_has_no_representable_bound(self):
        domain = representable_domain("real")
        self.assertIsNone(domain["lower"])
        self.assertIsNone(domain["upper"])

    def test_an_unknown_representation_is_refused(self):
        with self.assertRaises(ValueError):
            representable_domain("float128", 128)


class TestDefinitionValidation(unittest.TestCase):
    def test_a_valid_definition_normalizes(self):
        record = validate_parameter_definition(definition())
        self.assertEqual(record["parameter_id"], "PAR-BUS-VOLTAGE")
        self.assertEqual(record["representation"], "unsigned-integer")

    def test_a_non_mapping_definition_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition("PAR-BUS-VOLTAGE")

    def test_a_missing_identifier_raises(self):
        record = definition()
        del record["parameter_id"]
        with self.assertRaises(ValueError):
            validate_parameter_definition(record)

    def test_a_missing_representation_raises(self):
        record = definition()
        del record["representation"]
        with self.assertRaises(ValueError):
            validate_parameter_definition(record)

    def test_an_integer_definition_without_a_width_raises(self):
        record = definition()
        del record["bits"]
        with self.assertRaises(ValueError):
            validate_parameter_definition(record)

    def test_an_enumerated_definition_with_no_codes_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(definition(representation="enumerated", codes=[]))

    def test_an_enumerated_definition_repeating_a_code_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(
                definition(representation="enumerated", codes=["ON", "ON"])
            )

    def test_an_octet_string_definition_without_a_length_raises(self):
        record = definition(representation="octet-string")
        del record["length"]
        with self.assertRaises(ValueError):
            validate_parameter_definition(record)

    def test_access_defaults_to_read_write(self):
        self.assertEqual(validate_parameter_definition(definition())["access"], "read-write")

    def test_an_unknown_access_mode_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(definition(access="append-only"))

    def test_every_declared_representation_can_be_normalized(self):
        for representation in REPRESENTATIONS:
            record = validate_parameter_definition(
                definition(representation=representation)
            )
            self.assertIn(record["access"], ACCESS_MODES)


class TestEngineeringLimits(unittest.TestCase):
    def test_limits_inside_the_representation_are_kept(self):
        record = validate_parameter_definition(
            definition(bits=8, lower_limit=10, upper_limit=200)
        )
        self.assertEqual(record["limits"]["lower"], 10)
        self.assertEqual(record["limits"]["upper"], 200)

    def test_an_upper_limit_above_the_representation_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(definition(bits=8, upper_limit=300))

    def test_a_lower_limit_below_the_representation_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(definition(bits=8, lower_limit=-1))

    def test_an_inverted_limit_pair_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(
                definition(bits=8, lower_limit=200, upper_limit=10)
            )

    def test_limits_on_a_boolean_parameter_raise(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(
                definition(representation="boolean", lower_limit=0, upper_limit=1)
            )

    def test_a_non_numeric_limit_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(definition(bits=8, upper_limit="200"))

    def test_the_effective_domain_is_the_intersection(self):
        record = validate_parameter_definition(
            definition(bits=8, lower_limit=10, upper_limit=200)
        )
        self.assertEqual(record["effective"], {"lower": 10, "upper": 200})

    def test_an_unlimited_definition_keeps_the_representable_domain(self):
        record = validate_parameter_definition(definition(bits=8))
        self.assertEqual(record["effective"], {"lower": 0, "upper": 255})

    def test_a_real_parameters_effective_domain_comes_only_from_its_limits(self):
        record = validate_parameter_definition(
            definition(representation="real", lower_limit=-1.5, upper_limit=1.5)
        )
        self.assertAlmostEqual(record["effective"]["lower"], -1.5, places=9)
        self.assertAlmostEqual(record["effective"]["upper"], 1.5, places=9)

    def test_one_sided_limits_narrow_only_that_side(self):
        record = validate_parameter_definition(definition(bits=8, upper_limit=100))
        self.assertEqual(record["effective"], {"lower": 0, "upper": 100})

    def test_normalizing_a_normalized_definition_keeps_its_limits(self):
        once = validate_parameter_definition(definition(bits=8, upper_limit=100))
        twice = validate_parameter_definition(once)
        self.assertEqual(twice["effective"], {"lower": 0, "upper": 100})

    def test_a_normalized_definition_still_refuses_a_value_past_its_limit(self):
        once = validate_parameter_definition(definition(bits=8, upper_limit=100))
        self.assertFalse(value_belongs(once, 200)["belongs"])

    def test_the_intersection_helper_is_used_by_normalization(self):
        record = validate_parameter_definition(definition(bits=8, upper_limit=100))
        self.assertEqual(effective_domain(record), record["effective"])


class TestCatalogue(unittest.TestCase):
    def test_a_catalogue_normalizes(self):
        catalogue = validate_catalogue([definition("PAR-A"), definition("PAR-B")])
        self.assertEqual(len(catalogue), 2)

    def test_a_repeated_identifier_in_one_process_raises(self):
        with self.assertRaises(ValueError):
            validate_catalogue([definition("PAR-A"), definition("PAR-A")])

    def test_the_same_name_under_another_process_is_another_parameter(self):
        catalogue = validate_catalogue(
            [definition("PAR-A", apid="AP-PWR"), definition("PAR-A", apid="AP-THM")]
        )
        self.assertEqual(len(catalogue), 2)

    def test_an_empty_catalogue_is_valid(self):
        self.assertEqual(validate_catalogue([]), [])

    def test_a_non_list_catalogue_raises(self):
        with self.assertRaises(ValueError):
            validate_catalogue(definition())


class TestValueMembership(unittest.TestCase):
    def test_a_value_inside_the_effective_domain_belongs(self):
        self.assertTrue(value_belongs(definition(bits=8), 42)["belongs"])

    def test_a_value_on_the_upper_bound_belongs(self):
        self.assertTrue(value_belongs(definition(bits=8), 255)["belongs"])

    def test_a_value_one_past_the_representation_does_not_belong(self):
        result = value_belongs(definition(bits=8), 256)
        self.assertFalse(result["belongs"])
        self.assertIn("upper", result["reason"])

    def test_a_value_inside_the_representation_but_outside_the_limits_is_refused(self):
        result = value_belongs(definition(bits=8, upper_limit=100), 200)
        self.assertFalse(result["belongs"])

    def test_a_negative_value_does_not_belong_to_an_unsigned_parameter(self):
        self.assertFalse(value_belongs(definition(bits=8), -1)["belongs"])

    def test_a_signed_parameter_accepts_its_negative_bound(self):
        result = value_belongs(definition(representation="signed-integer", bits=8), -128)
        self.assertTrue(result["belongs"])

    def test_a_fractional_value_does_not_belong_to_an_integer_parameter(self):
        self.assertFalse(value_belongs(definition(bits=8), 4.5)["belongs"])

    def test_a_boolean_is_not_an_integer_parameter_value(self):
        self.assertFalse(value_belongs(definition(bits=8), True)["belongs"])

    def test_a_boolean_parameter_takes_only_booleans(self):
        self.assertTrue(value_belongs(definition(representation="boolean"), False)["belongs"])
        self.assertFalse(value_belongs(definition(representation="boolean"), 0)["belongs"])

    def test_an_enumerated_parameter_takes_only_its_codes(self):
        record = definition(representation="enumerated")
        self.assertTrue(value_belongs(record, "STANDBY")["belongs"])
        self.assertFalse(value_belongs(record, "SAFE")["belongs"])

    def test_an_octet_string_refuses_an_overlong_value(self):
        record = definition(representation="octet-string", length=4)
        self.assertTrue(value_belongs(record, b"\x01\x02")["belongs"])
        self.assertFalse(value_belongs(record, b"\x01\x02\x03\x04\x05")["belongs"])

    def test_an_octet_string_refuses_a_text_value(self):
        self.assertFalse(
            value_belongs(definition(representation="octet-string"), "abcd")["belongs"]
        )

    def test_a_real_value_on_its_declared_bound_belongs(self):
        record = definition(representation="real", lower_limit=0.0, upper_limit=1.0)
        result = value_belongs(record, 1.0)
        self.assertTrue(result["belongs"])

    def test_a_rejection_carries_a_reason_rather_than_a_bare_verdict(self):
        result = value_belongs(definition(bits=8), 999)
        self.assertFalse(result["belongs"])
        self.assertTrue(result["reason"])


class TestCatalogueAssessment(unittest.TestCase):
    def test_a_bounded_catalogue_is_sound(self):
        result = assess_catalogue([definition("PAR-A"), definition("PAR-B", apid="AP-THM")])
        self.assertEqual(result["verdict"], VERDICT_SOUND)
        self.assertEqual(result["findings"], [])

    def test_an_unbounded_real_parameter_is_a_finding(self):
        result = assess_catalogue([definition("PAR-R", representation="real")])
        self.assertEqual(result["verdict"], VERDICT_UNSOUND)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_bounded_real_parameter_is_sound(self):
        result = assess_catalogue(
            [definition("PAR-R", representation="real", lower_limit=-5.0, upper_limit=5.0)]
        )
        self.assertEqual(result["verdict"], VERDICT_SOUND)

    def test_parameters_are_grouped_by_application_process(self):
        result = assess_catalogue(
            [
                definition("PAR-A", apid="AP-PWR"),
                definition("PAR-B", apid="AP-PWR"),
                definition("PAR-A", apid="AP-THM"),
            ]
        )
        self.assertEqual(result["application_process_count"], 2)
        self.assertEqual(result["parameters_per_process"]["AP-PWR"], ["PAR-A", "PAR-B"])

    def test_limit_narrowed_parameters_are_named(self):
        result = assess_catalogue([definition("PAR-A", bits=8, upper_limit=100)])
        self.assertEqual(result["narrowed_by_limits"], ["AP-PWR/PAR-A"])

    def test_read_only_parameters_are_excluded_from_the_writable_count(self):
        result = assess_catalogue(
            [definition("PAR-A"), definition("PAR-B", access="read-only")]
        )
        self.assertEqual(result["parameter_count"], 2)
        self.assertEqual(result["writable_count"], 1)

    def test_an_empty_catalogue_is_sound_and_empty(self):
        result = assess_catalogue([])
        self.assertEqual(result["verdict"], VERDICT_SOUND)
        self.assertEqual(result["parameter_count"], 0)

    def test_an_invalid_definition_raises_before_any_assessment(self):
        with self.assertRaises(ValueError):
            assess_catalogue([definition("PAR-A", bits=8, upper_limit=999)])


if __name__ == "__main__":
    unittest.main()
