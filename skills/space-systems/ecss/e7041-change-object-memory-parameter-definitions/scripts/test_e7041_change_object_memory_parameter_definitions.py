"""Contract test for the e7041 object-memory parameter definition change leaf."""

import unittest

from e7041_change_object_memory_parameter_definitions_logic import (
    VERDICT_ACCEPTED,
    VERDICT_PARTIAL,
    VERDICT_REJECTED,
    apply_definition_change,
    assess_change_instruction,
    binding_findings,
    store_is_consistent,
    type_width_bits,
    validate_change_instruction,
    validate_change_request,
    validate_definition_store,
    validate_memory,
    validate_memory_map,
    validate_parameter_definition,
)


def memory(mid="OM-RAM", size_bits=4096, alignment_bits=8, access="read-write"):
    return {
        "id": mid,
        "size_bits": size_bits,
        "alignment_bits": alignment_bits,
        "access": access,
    }


def memories():
    return [memory(), memory("OM-ROM", 2048, 8, "read-only")]


def definition(pid="P-BATT-V", memory_id="OM-RAM", offset_bits=64, type_name="uint16", **kw):
    record = {
        "id": pid,
        "memory_id": memory_id,
        "offset_bits": offset_bits,
        "type": type_name,
        "redefinable": True,
        "settable": False,
    }
    record.update(kw)
    return record


def store():
    return [
        definition("P-BATT-V"),
        definition("P-TEMP-A", offset_bits=128, type_name="real32"),
        definition("P-MODE", offset_bits=256, type_name="uint8", redefinable=False),
        definition("P-BIAS", offset_bits=320, type_name="int16", settable=True),
    ]


def instruction(pid="P-BATT-V", memory_id="OM-RAM", offset_bits=512, type_name=None):
    record = {"parameter_id": pid, "memory_id": memory_id, "offset_bits": offset_bits}
    if type_name is not None:
        record["type"] = type_name
    return record


class TestTypeAndMemoryValidation(unittest.TestCase):
    def test_a_declared_type_reports_its_width(self):
        self.assertEqual(type_width_bits("real64"), 64)

    def test_an_undeclared_type_raises(self):
        with self.assertRaises(ValueError):
            type_width_bits("float128")

    def test_a_valid_memory_normalizes(self):
        record = validate_memory(memory())
        self.assertEqual(record["id"], "OM-RAM")
        self.assertEqual(record["alignment_bits"], 8)

    def test_a_memory_with_a_zero_extent_raises(self):
        with self.assertRaises(ValueError):
            validate_memory(memory(size_bits=0))

    def test_a_memory_extent_off_its_alignment_unit_raises(self):
        with self.assertRaises(ValueError):
            validate_memory(memory(size_bits=100, alignment_bits=8))

    def test_an_unknown_access_mode_raises(self):
        with self.assertRaises(ValueError):
            validate_memory(memory(access="write-only"))

    def test_a_duplicate_memory_id_raises(self):
        with self.assertRaises(ValueError):
            validate_memory_map([memory(), memory()])

    def test_a_non_list_memory_declaration_raises(self):
        with self.assertRaises(ValueError):
            validate_memory_map(memory())


class TestDefinitionValidation(unittest.TestCase):
    def test_a_valid_definition_normalizes_and_carries_its_width(self):
        record = validate_parameter_definition(definition())
        self.assertEqual(record["width_bits"], 16)
        self.assertTrue(record["redefinable"])

    def test_a_blank_parameter_id_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(definition(""))

    def test_a_negative_offset_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(definition(offset_bits=-8))

    def test_a_boolean_offset_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(definition(offset_bits=True))

    def test_a_non_boolean_redefinable_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter_definition(definition(redefinable="yes"))

    def test_a_duplicate_parameter_id_raises(self):
        with self.assertRaises(ValueError):
            validate_definition_store([definition(), definition()])

    def test_an_empty_store_is_valid(self):
        self.assertEqual(validate_definition_store([]), [])


class TestBindingChecks(unittest.TestCase):
    def test_an_in_extent_aligned_binding_reports_nothing(self):
        self.assertEqual(binding_findings(validate_memory(memory()), 64, 16, "p"), [])

    def test_a_binding_that_runs_past_the_extent_is_reported(self):
        findings = binding_findings(validate_memory(memory(size_bits=128)), 120, 16, "p")
        self.assertEqual(len(findings), 1)

    def test_a_binding_that_ends_exactly_on_the_extent_is_accepted(self):
        self.assertEqual(binding_findings(validate_memory(memory(size_bits=128)), 112, 16, "p"), [])

    def test_a_misaligned_offset_is_reported(self):
        findings = binding_findings(validate_memory(memory(alignment_bits=16)), 8, 16, "p")
        self.assertEqual(len(findings), 1)

    def test_a_misaligned_and_overrunning_binding_reports_both(self):
        findings = binding_findings(validate_memory(memory(size_bits=128, alignment_bits=16)), 124, 16, "p")
        self.assertEqual(len(findings), 2)


class TestRequestValidation(unittest.TestCase):
    def test_a_bare_instruction_list_is_accepted(self):
        self.assertEqual(len(validate_change_request([instruction()])), 1)

    def test_a_mapping_request_yields_its_instruction_list(self):
        self.assertEqual(
            len(validate_change_request({"instructions": [instruction()]})), 1
        )

    def test_an_empty_request_raises(self):
        with self.assertRaises(ValueError):
            validate_change_request([])

    def test_a_repeated_parameter_in_one_request_raises(self):
        with self.assertRaises(ValueError):
            validate_change_request([instruction(), instruction(offset_bits=640)])

    def test_instruction_order_is_preserved(self):
        parsed = validate_change_request([instruction("P-TEMP-A"), instruction("P-BATT-V")])
        self.assertEqual(
            [i["parameter_id"] for i in parsed], ["P-TEMP-A", "P-BATT-V"]
        )

    def test_an_instruction_naming_an_undeclared_type_raises(self):
        with self.assertRaises(ValueError):
            validate_change_instruction(instruction(type_name="decimal"))

    def test_a_non_mapping_instruction_raises(self):
        with self.assertRaises(ValueError):
            validate_change_instruction(["P-BATT-V"])


class TestInstructionAssessment(unittest.TestCase):
    def setUp(self):
        self.store_by_id = {r["id"]: r for r in validate_definition_store(store())}
        self.memory_map = validate_memory_map(memories())

    def test_a_clean_instruction_is_accepted(self):
        outcome = assess_change_instruction(
            validate_change_instruction(instruction()), self.store_by_id, self.memory_map
        )
        self.assertTrue(outcome["accepted"])
        self.assertEqual(outcome["definition"]["offset_bits"], 512)

    def test_an_unheld_parameter_is_refused_not_skipped(self):
        outcome = assess_change_instruction(
            validate_change_instruction(instruction("P-GHOST")),
            self.store_by_id,
            self.memory_map,
        )
        self.assertFalse(outcome["accepted"])
        self.assertEqual(len(outcome["findings"]), 1)

    def test_a_fixed_definition_cannot_be_re_pointed(self):
        outcome = assess_change_instruction(
            validate_change_instruction(instruction("P-MODE")),
            self.store_by_id,
            self.memory_map,
        )
        self.assertFalse(outcome["accepted"])

    def test_an_undeclared_target_memory_is_refused(self):
        outcome = assess_change_instruction(
            validate_change_instruction(instruction(memory_id="OM-GHOST")),
            self.store_by_id,
            self.memory_map,
        )
        self.assertFalse(outcome["accepted"])

    def test_a_settable_parameter_is_refused_in_read_only_memory(self):
        outcome = assess_change_instruction(
            validate_change_instruction(instruction("P-BIAS", "OM-ROM", 64)),
            self.store_by_id,
            self.memory_map,
        )
        self.assertFalse(outcome["accepted"])

    def test_a_read_only_memory_still_takes_a_non_settable_parameter(self):
        outcome = assess_change_instruction(
            validate_change_instruction(instruction("P-BATT-V", "OM-ROM", 64)),
            self.store_by_id,
            self.memory_map,
        )
        self.assertTrue(outcome["accepted"])

    def test_a_widening_type_change_is_checked_against_the_new_width(self):
        outcome = assess_change_instruction(
            validate_change_instruction(instruction("P-BATT-V", "OM-ROM", 2016, "real64")),
            self.store_by_id,
            self.memory_map,
        )
        self.assertFalse(outcome["accepted"])

    def test_a_type_change_that_fits_is_carried_into_the_definition(self):
        outcome = assess_change_instruction(
            validate_change_instruction(instruction("P-BATT-V", "OM-RAM", 512, "real64")),
            self.store_by_id,
            self.memory_map,
        )
        self.assertTrue(outcome["accepted"])
        self.assertEqual(outcome["definition"]["width_bits"], 64)


class TestStoreConsistency(unittest.TestCase):
    def test_a_clean_store_is_consistent(self):
        result = store_is_consistent(
            validate_definition_store(store()), validate_memory_map(memories())
        )
        self.assertTrue(result["consistent"])

    def test_a_definition_in_an_undeclared_memory_is_reported(self):
        records = validate_definition_store(store())
        records[0]["memory_id"] = "OM-GHOST"
        result = store_is_consistent(records, validate_memory_map(memories()))
        self.assertFalse(result["consistent"])

    def test_a_definition_past_the_extent_is_reported(self):
        records = validate_definition_store(store())
        records[0]["offset_bits"] = 4088
        result = store_is_consistent(records, validate_memory_map(memories()))
        self.assertFalse(result["consistent"])


class TestChangeApplication(unittest.TestCase):
    def test_a_fully_valid_request_is_accepted_and_changes_the_store(self):
        result = apply_definition_change(store(), memories(), [instruction()])
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)
        self.assertTrue(result["store_changed"])
        changed = {r["id"]: r for r in result["store"]}
        self.assertEqual(changed["P-BATT-V"]["offset_bits"], 512)

    def test_a_mixed_request_is_partially_accepted(self):
        result = apply_definition_change(
            store(), memories(), [instruction(), instruction("P-GHOST")]
        )
        self.assertEqual(result["verdict"], VERDICT_PARTIAL)
        self.assertEqual(result["applied"], ["P-BATT-V"])
        self.assertEqual(result["refused"], ["P-GHOST"])

    def test_a_wholly_invalid_request_is_rejected_and_leaves_the_store(self):
        result = apply_definition_change(
            store(), memories(), [instruction("P-GHOST"), instruction("P-MODE")]
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertFalse(result["store_changed"])
        self.assertEqual(len(result["findings"]), 2)

    def test_the_untouched_definitions_survive_a_partial_change(self):
        result = apply_definition_change(
            store(), memories(), [instruction(), instruction("P-GHOST")]
        )
        kept = {r["id"]: r for r in result["store"]}
        self.assertEqual(kept["P-TEMP-A"]["offset_bits"], 128)

    def test_an_already_inconsistent_store_raises_before_any_change(self):
        broken = store()
        broken[0]["offset_bits"] = 9000
        with self.assertRaises(ValueError):
            apply_definition_change(broken, memories(), [instruction("P-TEMP-A")])

    def test_a_repeated_instruction_raises(self):
        with self.assertRaises(ValueError):
            apply_definition_change(store(), memories(), [instruction(), instruction()])

    def test_an_empty_request_raises(self):
        with self.assertRaises(ValueError):
            apply_definition_change(store(), memories(), [])

    def test_every_instruction_gets_its_own_outcome(self):
        result = apply_definition_change(
            store(), memories(), [instruction(), instruction("P-TEMP-A", "OM-RAM", 640)]
        )
        self.assertEqual(len(result["outcomes"]), 2)
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)


if __name__ == "__main__":
    unittest.main()
