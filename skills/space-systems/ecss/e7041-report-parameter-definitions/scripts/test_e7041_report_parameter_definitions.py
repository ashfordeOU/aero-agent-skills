"""Contract test for the e7041 parameter-definition report leaf."""

import unittest

from e7041_report_parameter_definitions_logic import (
    ACCEPTANCE_ACCEPTED,
    ACCEPTANCE_PARTIAL,
    ACCEPTANCE_REJECTED,
    assess_report_request,
    build_definition_report,
    definition_report_entry,
    report_is_complete,
    resolve_requested_ids,
    type_width_bits,
    validate_definition,
    validate_request,
    validate_store,
)


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
    ]


class TestTypes(unittest.TestCase):
    def test_a_declared_type_reports_its_width(self):
        self.assertEqual(type_width_bits("uint16"), 16)

    def test_an_undeclared_type_raises(self):
        with self.assertRaises(ValueError):
            type_width_bits("bcd12")


class TestDefinitionValidation(unittest.TestCase):
    def test_a_valid_definition_normalizes(self):
        record = validate_definition(definition())
        self.assertEqual(record["id"], "P-BATT-V")
        self.assertEqual(record["width_bits"], 16)

    def test_a_non_mapping_definition_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(["P-BATT-V"])

    def test_a_blank_id_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(""))

    def test_a_missing_memory_raises(self):
        record = definition()
        del record["memory_id"]
        with self.assertRaises(ValueError):
            validate_definition(record)

    def test_a_negative_offset_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(offset_bits=-1))

    def test_a_boolean_offset_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(offset_bits=False))

    def test_a_non_boolean_settable_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(settable="maybe"))

    def test_a_duplicate_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_store([definition(), definition()])

    def test_an_empty_store_is_valid(self):
        self.assertEqual(validate_store([]), [])

    def test_a_non_list_store_raises(self):
        with self.assertRaises(ValueError):
            validate_store(definition())


class TestRequestValidation(unittest.TestCase):
    def test_a_missing_request_means_report_everything(self):
        self.assertEqual(validate_request(None), [])

    def test_a_mapping_request_yields_its_identifier_list(self):
        self.assertEqual(validate_request({"parameter_ids": ["P-MODE"]}), ["P-MODE"])

    def test_a_bare_list_request_is_accepted(self):
        self.assertEqual(validate_request(["P-MODE"]), ["P-MODE"])

    def test_a_repeated_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_request(["P-MODE", "P-MODE"])

    def test_a_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_request([" "])

    def test_a_non_list_identifier_field_raises(self):
        with self.assertRaises(ValueError):
            validate_request({"parameter_ids": "P-MODE"})

    def test_requested_order_is_preserved(self):
        self.assertEqual(
            validate_request(["P-MODE", "P-BATT-V"]), ["P-MODE", "P-BATT-V"]
        )


class TestResolution(unittest.TestCase):
    def test_an_empty_request_resolves_to_the_whole_store(self):
        resolution = resolve_requested_ids(None, store())
        self.assertTrue(resolution["reported_all"])
        self.assertEqual(len(resolution["known"]), 3)

    def test_a_known_identifier_resolves(self):
        resolution = resolve_requested_ids(["P-TEMP-A"], store())
        self.assertEqual(resolution["known"], ["P-TEMP-A"])
        self.assertEqual(resolution["unknown"], [])

    def test_an_unknown_identifier_is_carried_not_dropped(self):
        resolution = resolve_requested_ids(["P-GHOST"], store())
        self.assertEqual(resolution["unknown"], ["P-GHOST"])

    def test_a_mixed_request_splits(self):
        resolution = resolve_requested_ids(["P-GHOST", "P-MODE"], store())
        self.assertEqual(resolution["known"], ["P-MODE"])
        self.assertEqual(resolution["unknown"], ["P-GHOST"])

    def test_an_empty_store_resolves_everything_as_unknown(self):
        self.assertEqual(resolve_requested_ids(["P-MODE"], [])["unknown"], ["P-MODE"])


class TestReportAssembly(unittest.TestCase):
    def test_an_entry_carries_the_whole_binding(self):
        entry = definition_report_entry(definition())
        for field in ("memory_id", "offset_bits", "type", "width_bits", "redefinable", "settable"):
            self.assertIn(field, entry)

    def test_an_empty_request_reports_every_definition(self):
        report = build_definition_report(store())
        self.assertEqual(report["definition_count"], 3)
        self.assertTrue(report["reported_all"])

    def test_the_report_follows_the_requested_order(self):
        report = build_definition_report(store(), ["P-MODE", "P-BATT-V"])
        self.assertEqual(
            [entry["id"] for entry in report["entries"]], ["P-MODE", "P-BATT-V"]
        )

    def test_an_empty_request_follows_store_order(self):
        report = build_definition_report(store())
        self.assertEqual(
            [entry["id"] for entry in report["entries"]],
            ["P-BATT-V", "P-TEMP-A", "P-MODE"],
        )

    def test_the_reported_width_sums_across_entries(self):
        self.assertEqual(build_definition_report(store())["reported_width_bits"], 56)

    def test_unknown_identifiers_produce_no_entry(self):
        report = build_definition_report(store(), ["P-GHOST"])
        self.assertEqual(report["entries"], [])
        self.assertEqual(report["unknown_ids"], ["P-GHOST"])

    def test_a_single_definition_report_carries_only_it(self):
        report = build_definition_report(store(), ["P-TEMP-A"])
        self.assertEqual([e["id"] for e in report["entries"]], ["P-TEMP-A"])
        self.assertEqual(report["reported_width_bits"], 32)


class TestReportCompleteness(unittest.TestCase):
    def test_a_freshly_built_report_is_complete(self):
        self.assertTrue(report_is_complete(build_definition_report(store()))["complete"])

    def test_a_truncated_entry_list_is_detected(self):
        report = build_definition_report(store())
        report["entries"] = report["entries"][:1]
        result = report_is_complete(report)
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["findings"]), 2)

    def test_a_wrong_width_total_is_detected(self):
        report = build_definition_report(store())
        report["reported_width_bits"] = 999
        self.assertFalse(report_is_complete(report)["complete"])

    def test_a_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            report_is_complete(["entries"])

    def test_a_negative_declared_count_raises(self):
        report = build_definition_report(store())
        report["definition_count"] = -1
        with self.assertRaises(ValueError):
            report_is_complete(report)

    def test_an_entry_reduced_to_an_identifier_raises(self):
        report = build_definition_report(store())
        del report["entries"][0]["memory_id"]
        with self.assertRaises(ValueError):
            report_is_complete(report)


class TestRequestHandling(unittest.TestCase):
    def test_a_fully_resolvable_request_is_accepted(self):
        result = assess_report_request(store(), ["P-BATT-V", "P-MODE"])
        self.assertEqual(result["acceptance"], ACCEPTANCE_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_a_mixed_request_is_partially_accepted(self):
        result = assess_report_request(store(), ["P-BATT-V", "P-GHOST"])
        self.assertEqual(result["acceptance"], ACCEPTANCE_PARTIAL)
        self.assertEqual(result["reported_ids"], ["P-BATT-V"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_wholly_unknown_request_is_rejected(self):
        result = assess_report_request(store(), ["P-GHOST", "P-PHANTOM"])
        self.assertEqual(result["acceptance"], ACCEPTANCE_REJECTED)
        self.assertEqual(result["reported_ids"], [])

    def test_an_empty_request_reports_the_whole_store(self):
        result = assess_report_request(store())
        self.assertTrue(result["reported_all"])
        self.assertEqual(result["held_count"], 3)

    def test_the_report_is_complete_by_construction(self):
        self.assertTrue(assess_report_request(store(), ["P-MODE"])["complete"])

    def test_an_empty_store_with_an_empty_request_reports_nothing(self):
        result = assess_report_request([])
        self.assertEqual(result["acceptance"], ACCEPTANCE_ACCEPTED)
        self.assertEqual(result["reported_ids"], [])

    def test_an_invalid_store_entry_raises_before_any_report(self):
        broken = store()
        broken[0]["type"] = "nibble"
        with self.assertRaises(ValueError):
            assess_report_request(broken)

    def test_a_repeated_requested_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_report_request(store(), ["P-MODE", "P-MODE"])


if __name__ == "__main__":
    unittest.main()
