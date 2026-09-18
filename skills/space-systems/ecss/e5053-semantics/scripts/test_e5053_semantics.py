"""Contract tests for the clause 5.2.2.2 semantics-subclause validation."""

import unittest

from e5053_semantics_logic import (
    PRESENCE_KINDS,
    PRIMITIVE_KINDS,
    align_with_request,
    assess_primitive_semantics,
    assess_service_semantics,
    group_by_service,
    parameter_index,
    presence_counts,
    presence_is_stronger,
    split_primitive_name,
    validate_parameter,
    validate_parameter_list,
)

UNIT = {"name": "unit", "type": "octet string"}
PRIORITY = {"name": "priority", "type": "enumerated", "presence": "optional"}
SOURCE = {"name": "source", "type": "address", "provider_generated": True}


def request_spec(params=None):
    return {"primitive": "T-Data.request", "parameters": list(params or [UNIT, PRIORITY])}


def indication_spec(params=None):
    return {"primitive": "T-Data.indication", "parameters": list(params or [UNIT, SOURCE])}


class ParameterValidationTests(unittest.TestCase):
    def test_defaults_to_mandatory_presence(self):
        self.assertEqual(validate_parameter(UNIT)["presence"], "mandatory")

    def test_name_and_type_are_stripped(self):
        entry = validate_parameter({"name": "  unit ", "type": " octet string "})
        self.assertEqual(entry["name"], "unit")
        self.assertEqual(entry["type"], "octet string")

    def test_missing_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter({"name": "unit"})

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter({"name": "  ", "type": "octet string"})

    def test_unknown_presence_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter({"name": "unit", "type": "octet string", "presence": "maybe"})

    def test_conditional_without_condition_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter({"name": "unit", "type": "octet string", "presence": "conditional"})

    def test_conditional_with_condition_accepted(self):
        entry = validate_parameter(
            {
                "name": "unit",
                "type": "octet string",
                "presence": "conditional",
                "condition": "present when the segment is the last of the unit",
            }
        )
        self.assertEqual(entry["presence"], "conditional")
        self.assertTrue(entry["condition"])

    def test_condition_on_a_mandatory_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(
                {"name": "unit", "type": "octet string", "condition": "always"}
            )

    def test_non_mapping_parameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(["unit", "octet string"])

    def test_every_declared_presence_kind_is_accepted(self):
        for kind in PRESENCE_KINDS:
            param = {"name": "p", "type": "t", "presence": kind}
            if kind == "conditional":
                param["condition"] = "present when the peer asked for it"
            self.assertEqual(validate_parameter(param)["presence"], kind)


class ParameterListTests(unittest.TestCase):
    def test_none_list_is_empty(self):
        self.assertEqual(validate_parameter_list(None), [])

    def test_duplicate_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter_list([UNIT, {"name": "UNIT", "type": "octet string"}])

    def test_non_sequence_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter_list({"name": "unit"})

    def test_index_is_case_folded(self):
        index = parameter_index([{"name": "Unit", "type": "octet string"}])
        self.assertIn("unit", index)

    def test_presence_counts_add_up(self):
        counts = presence_counts([UNIT, PRIORITY])
        self.assertEqual(counts["mandatory"], 1)
        self.assertEqual(counts["optional"], 1)
        self.assertEqual(counts["conditional"], 0)


class PrimitiveNameTests(unittest.TestCase):
    def test_service_and_kind_are_split(self):
        self.assertEqual(split_primitive_name("T-Data.request"), ("T-Data", "request"))

    def test_kind_is_case_folded(self):
        self.assertEqual(split_primitive_name("T-Data.INDICATION")[1], "indication")

    def test_missing_suffix_rejected(self):
        with self.assertRaises(ValueError):
            split_primitive_name("T-Data")

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            split_primitive_name("T-Data.notify")

    def test_every_declared_kind_splits(self):
        for kind in PRIMITIVE_KINDS:
            self.assertEqual(split_primitive_name("T-Data.%s" % kind)[1], kind)


class GroupingTests(unittest.TestCase):
    def test_service_groups_its_primitives(self):
        grouped = group_by_service([request_spec(), indication_spec()])
        self.assertEqual(sorted(grouped["T-Data"]), ["indication", "request"])

    def test_repeated_kind_in_one_service_rejected(self):
        with self.assertRaises(ValueError):
            group_by_service([request_spec(), request_spec()])

    def test_empty_specification_rejected(self):
        with self.assertRaises(ValueError):
            group_by_service([])


class PresenceStrengthTests(unittest.TestCase):
    def test_mandatory_is_stronger_than_conditional(self):
        self.assertTrue(presence_is_stronger("mandatory", "conditional"))

    def test_conditional_is_not_stronger_than_mandatory(self):
        self.assertFalse(presence_is_stronger("conditional", "mandatory"))

    def test_equal_categories_are_not_stronger(self):
        self.assertFalse(presence_is_stronger("optional", "optional"))

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            presence_is_stronger("mandatory", "sometimes")


class AlignmentTests(unittest.TestCase):
    def test_clean_pair_raises_no_finding(self):
        self.assertEqual(align_with_request([UNIT, PRIORITY], [UNIT, SOURCE], "indication"), [])

    def test_dropped_mandatory_parameter_is_reported(self):
        findings = align_with_request([UNIT], [SOURCE], "indication")
        self.assertTrue(any("absent from the indication" in f for f in findings))

    def test_undeclared_partner_parameter_is_reported(self):
        stray = {"name": "stray", "type": "integer"}
        findings = align_with_request([UNIT], [UNIT, stray], "indication")
        self.assertTrue(any("provider generated" in f for f in findings))

    def test_provider_generated_partner_parameter_is_accepted(self):
        self.assertEqual(align_with_request([UNIT], [UNIT, SOURCE], "indication"), [])

    def test_tightened_presence_is_reported(self):
        findings = align_with_request([PRIORITY], [{"name": "priority", "type": "enumerated"}], "indication")
        self.assertTrue(any("never tighten" in f for f in findings))

    def test_relaxed_presence_is_accepted(self):
        relaxed = {
            "name": "unit",
            "type": "octet string",
            "presence": "conditional",
            "condition": "withheld when the provider truncates the unit",
        }
        self.assertEqual(align_with_request([UNIT], [relaxed], "indication"), [])


class PrimitiveAssessmentTests(unittest.TestCase):
    def test_populated_primitive_is_compliant(self):
        result = assess_primitive_semantics(request_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["service"], "T-Data")

    def test_empty_parameter_list_is_flagged(self):
        result = assess_primitive_semantics({"primitive": "T-Data.request", "parameters": []})
        self.assertFalse(result["compliant"])

    def test_non_mapping_specification_rejected(self):
        with self.assertRaises(ValueError):
            assess_primitive_semantics(["T-Data.request"])


class ServiceAssessmentTests(unittest.TestCase):
    def test_clean_service_is_compliant(self):
        result = assess_service_semantics([request_spec(), indication_spec()])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["compliant_primitives"], 2)

    def test_service_without_a_request_is_flagged(self):
        result = assess_service_semantics([indication_spec()])
        self.assertFalse(result["compliant"])
        self.assertTrue(any("no request primitive" in f for f in result["findings"]))

    def test_dropped_mandatory_parameter_surfaces_at_service_level(self):
        result = assess_service_semantics([request_spec([UNIT]), indication_spec([SOURCE])])
        self.assertFalse(result["compliant"])
        self.assertTrue(any("T-Data" in f for f in result["findings"]))

    def test_total_counts_every_primitive(self):
        result = assess_service_semantics([request_spec(), indication_spec()])
        self.assertEqual(result["total_primitives"], 2)

    def test_confirm_is_aligned_like_any_other_partner(self):
        confirm = {"primitive": "T-Data.confirm", "parameters": [{"name": "stray", "type": "integer"}]}
        result = assess_service_semantics([request_spec([UNIT]), confirm])
        self.assertTrue(any("confirm" in f for f in result["findings"]))

    def test_services_are_reported_individually(self):
        other = {"primitive": "T-Reset.request", "parameters": [UNIT]}
        result = assess_service_semantics([request_spec(), indication_spec(), other])
        self.assertEqual(sorted(result["services"]), ["T-Data", "T-Reset"])


if __name__ == "__main__":
    unittest.main()
