"""Contract test for the OBCP definition leaf (stdlib unittest)."""

import unittest

from e7041_obcp_definition_logic import (
    ADMISSIBLE,
    ARG_TYPE_BOOLEAN,
    ARG_TYPE_INTEGER,
    ARG_TYPE_REAL,
    ARG_TYPE_STRING,
    OBSERVABILITY_NONE,
    OBSERVABILITY_PROCEDURE,
    OBSERVABILITY_STEP,
    REJECTED_OVER_ENGINE_LIMIT,
    REJECTED_STORE_FULL,
    REJECTED_UNKNOWN_ENGINE,
    argument_signature,
    assess_definition,
    assess_definition_set,
    bind_arguments,
    default_arguments,
    definition_digest,
    definitions_agree,
    mandatory_arguments,
    validate_argument,
    validate_definition,
    validate_engine,
    value_matches_type,
)


def engine(engine_id="ENG-A", limit=4096, **kw):
    record = {
        "id": engine_id,
        "language": "obcp-bytecode",
        "max_procedure_octets": limit,
    }
    record.update(kw)
    return record


def definition(proc_id="OBCP-1", **kw):
    record = {
        "id": proc_id,
        "version": 1,
        "engine_id": "ENG-A",
        "code_octets": 1024,
        "step_count": 12,
        "observability_level": OBSERVABILITY_PROCEDURE,
        "arguments": [
            {"name": "heater_setpoint", "type": ARG_TYPE_REAL, "default": 20.0},
            {"name": "retry_limit", "type": ARG_TYPE_INTEGER},
        ],
    }
    record.update(kw)
    return record


class TestDefinitionValidation(unittest.TestCase):
    def test_definition_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_definition(["OBCP-1", 1])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(""))

    def test_version_zero_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(version=0))

    def test_boolean_code_size_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(code_octets=True))

    def test_zero_step_count_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(step_count=0))

    def test_unknown_observability_level_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(observability_level="verbose"))

    def test_observability_defaults_to_procedure_level(self):
        record = definition()
        del record["observability_level"]
        self.assertEqual(
            validate_definition(record)["observability_level"],
            OBSERVABILITY_PROCEDURE,
        )

    def test_duplicate_argument_name_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(
                definition(
                    arguments=[
                        {"name": "mode", "type": ARG_TYPE_STRING},
                        {"name": "mode", "type": ARG_TYPE_INTEGER},
                    ]
                )
            )


class TestArguments(unittest.TestCase):
    def test_unknown_argument_type_raises(self):
        with self.assertRaises(ValueError):
            validate_argument({"name": "mode", "type": "enumeration"})

    def test_default_of_the_wrong_type_raises(self):
        with self.assertRaises(ValueError):
            validate_argument(
                {"name": "retry_limit", "type": ARG_TYPE_INTEGER,
                 "default": "three"}
            )

    def test_boolean_is_not_an_integer_argument(self):
        self.assertFalse(value_matches_type(ARG_TYPE_INTEGER, True))

    def test_boolean_argument_accepts_a_boolean(self):
        self.assertTrue(value_matches_type(ARG_TYPE_BOOLEAN, False))

    def test_integer_is_accepted_for_a_real_argument(self):
        self.assertTrue(value_matches_type(ARG_TYPE_REAL, 3))

    def test_signature_keeps_declaration_order(self):
        self.assertEqual(
            argument_signature(definition()),
            ["heater_setpoint", "retry_limit"],
        )

    def test_mandatory_arguments_are_the_ones_without_defaults(self):
        self.assertEqual(mandatory_arguments(definition()), ["retry_limit"])

    def test_defaults_map_only_covers_defaulted_arguments(self):
        self.assertEqual(default_arguments(definition()),
                         {"heater_setpoint": 20.0})


class TestBinding(unittest.TestCase):
    def test_missing_mandatory_argument_raises(self):
        with self.assertRaises(ValueError):
            bind_arguments(definition(), {"heater_setpoint": 18.0})

    def test_undeclared_argument_raises(self):
        with self.assertRaises(ValueError):
            bind_arguments(definition(), {"retry_limit": 3, "colour": "red"})

    def test_wrong_type_at_activation_raises(self):
        with self.assertRaises(ValueError):
            bind_arguments(definition(), {"retry_limit": "three"})

    def test_default_fills_an_unsupplied_argument(self):
        bound = bind_arguments(definition(), {"retry_limit": 3})
        self.assertAlmostEqual(bound["heater_setpoint"], 20.0, places=9)

    def test_supplied_value_overrides_the_default(self):
        bound = bind_arguments(definition(), {"retry_limit": 3,
                                              "heater_setpoint": 18.5})
        self.assertAlmostEqual(bound["heater_setpoint"], 18.5, places=9)

    def test_supplied_arguments_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            bind_arguments(definition(), [("retry_limit", 3)])


class TestDigest(unittest.TestCase):
    def test_identical_definitions_agree(self):
        self.assertTrue(definitions_agree(definition(), definition()))

    def test_a_version_bump_changes_the_digest(self):
        self.assertNotEqual(
            definition_digest(definition()),
            definition_digest(definition(version=2)),
        )

    def test_an_argument_losing_its_default_changes_the_digest(self):
        stripped = definition(
            arguments=[
                {"name": "heater_setpoint", "type": ARG_TYPE_REAL},
                {"name": "retry_limit", "type": ARG_TYPE_INTEGER},
            ]
        )
        self.assertFalse(definitions_agree(definition(), stripped))


class TestEngineAssessment(unittest.TestCase):
    def test_engine_must_declare_a_size_limit(self):
        with self.assertRaises(ValueError):
            validate_engine(engine(limit=0))

    def test_engine_with_no_observability_levels_raises(self):
        with self.assertRaises(ValueError):
            validate_engine(engine(observability_levels=[]))

    def test_unknown_engine_is_rejected(self):
        result = assess_definition(definition(engine_id="ENG-Z"), [engine()])
        self.assertEqual(result["disposition"], REJECTED_UNKNOWN_ENGINE)

    def test_oversized_procedure_is_rejected(self):
        result = assess_definition(definition(code_octets=8192), [engine()])
        self.assertEqual(result["disposition"], REJECTED_OVER_ENGINE_LIMIT)

    def test_procedure_exactly_at_the_engine_limit_is_admissible(self):
        result = assess_definition(definition(code_octets=4096), [engine()])
        self.assertEqual(result["disposition"], ADMISSIBLE)

    def test_unsupported_observability_level_is_a_finding_not_a_rejection(self):
        result = assess_definition(
            definition(observability_level=OBSERVABILITY_STEP),
            [engine(observability_levels=[OBSERVABILITY_NONE,
                                          OBSERVABILITY_PROCEDURE])],
        )
        self.assertEqual(result["disposition"], ADMISSIBLE)
        self.assertTrue(any("cannot observe" in f for f in result["findings"]))

    def test_mandatory_arguments_are_reported_as_a_finding(self):
        result = assess_definition(definition(), [engine()])
        self.assertTrue(any("mandatory" in f for f in result["findings"]))

    def test_duplicate_engine_id_raises(self):
        with self.assertRaises(ValueError):
            assess_definition(definition(), [engine(), engine()])


class TestDefinitionSet(unittest.TestCase):
    def test_empty_definition_list_raises(self):
        with self.assertRaises(ValueError):
            assess_definition_set([], [engine()], 8192)

    def test_duplicate_id_and_version_raises(self):
        with self.assertRaises(ValueError):
            assess_definition_set(
                [definition("OBCP-1"), definition("OBCP-1")], [engine()], 8192
            )

    def test_same_id_at_a_new_version_is_allowed(self):
        result = assess_definition_set(
            [definition("OBCP-1"), definition("OBCP-1", version=2)],
            [engine()], 8192,
        )
        self.assertEqual(result["admissible_count"], 2)

    def test_store_full_rejects_the_later_definition(self):
        result = assess_definition_set(
            [definition("OBCP-1"), definition("OBCP-2")], [engine()], 1500
        )
        self.assertEqual(result["results"][0]["disposition"], ADMISSIBLE)
        self.assertEqual(result["results"][1]["disposition"],
                         REJECTED_STORE_FULL)

    def test_rejected_definition_does_not_consume_store_space(self):
        result = assess_definition_set(
            [definition("OBCP-1", engine_id="ENG-Z"), definition("OBCP-2")],
            [engine()], 2048,
        )
        self.assertEqual(result["used_octets"], 1024)

    def test_fill_fraction_is_exact_at_a_full_store(self):
        result = assess_definition_set([definition()], [engine()], 1024)
        self.assertAlmostEqual(result["fill_fraction"], 1.0, places=9)

    def test_dispositions_are_grouped(self):
        result = assess_definition_set(
            [definition("OBCP-1"), definition("OBCP-2", engine_id="ENG-Z")],
            [engine()], 8192,
        )
        self.assertEqual(result["grouped_by_disposition"][ADMISSIBLE],
                         ["OBCP-1"])
        self.assertEqual(
            result["grouped_by_disposition"][REJECTED_UNKNOWN_ENGINE],
            ["OBCP-2"],
        )

    def test_all_admissible_flag_is_false_when_one_is_rejected(self):
        result = assess_definition_set(
            [definition("OBCP-1"), definition("OBCP-2", code_octets=9000)],
            [engine()], 65536,
        )
        self.assertFalse(result["all_admissible"])

    def test_zero_capacity_store_raises(self):
        with self.assertRaises(ValueError):
            assess_definition_set([definition()], [engine()], 0)


if __name__ == "__main__":
    unittest.main()
