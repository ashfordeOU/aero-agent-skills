"""Contract test for the e7041 functional-monitoring-definition report leaf."""

import unittest

from e7041_report_functional_monitoring_definitions_logic import (
    ACCEPTANCE_ACCEPTED,
    ACCEPTANCE_PARTIAL,
    ACCEPTANCE_REJECTED,
    assess_report_request,
    build_definition_report,
    definition_report_entry,
    report_is_complete,
    resolve_requested_ids,
    validate_catalog,
    validate_definition,
    validate_request,
)


def constituent(pmid="PM-1", parameter="P-BATT-V", status="running"):
    return {
        "parameter_monitoring_id": pmid,
        "parameter_id": parameter,
        "checking_status": status,
    }


def definition(fid="FM-POWER", constituents=None, threshold=2, **kw):
    record = {
        "id": fid,
        "enabled": True,
        "constituents": constituents
        if constituents is not None
        else [constituent("PM-1"), constituent("PM-2", "P-BATT-I")],
        "failing_threshold": threshold,
        "event_definition_id": "EV-POWER-DEGRADED",
    }
    record.update(kw)
    return record


def catalog():
    return [
        definition("FM-POWER"),
        definition(
            "FM-THERMAL",
            constituents=[
                constituent("PM-3", "P-TEMP-A"),
                constituent("PM-4", "P-TEMP-B"),
                constituent("PM-5", "P-TEMP-C", "unchecked"),
            ],
            threshold=1,
            event_definition_id="EV-THERMAL-DEGRADED",
        ),
    ]


class TestDefinitionValidation(unittest.TestCase):
    def test_a_valid_definition_normalizes(self):
        record = validate_definition(definition())
        self.assertEqual(record["id"], "FM-POWER")
        self.assertEqual(len(record["constituents"]), 2)

    def test_a_non_mapping_definition_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(["FM-POWER"])

    def test_an_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(""))

    def test_a_definition_with_no_constituents_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(constituents=[], threshold=1))

    def test_a_repeated_constituent_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(
                definition(constituents=[constituent("PM-1"), constituent("PM-1")])
            )

    def test_a_threshold_above_the_constituent_count_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(threshold=5))

    def test_a_zero_threshold_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(threshold=0))

    def test_a_boolean_threshold_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(threshold=True))

    def test_an_unknown_checking_status_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(
                definition(constituents=[constituent(status="probably-fine")], threshold=1)
            )

    def test_a_missing_event_definition_raises(self):
        record = definition()
        del record["event_definition_id"]
        with self.assertRaises(ValueError):
            validate_definition(record)

    def test_a_non_boolean_enabled_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(enabled="yes"))

    def test_a_duplicate_definition_id_raises(self):
        with self.assertRaises(ValueError):
            validate_catalog([definition("FM-POWER"), definition("FM-POWER")])

    def test_an_empty_store_is_a_valid_catalog(self):
        self.assertEqual(validate_catalog([]), [])

    def test_a_non_list_store_raises(self):
        with self.assertRaises(ValueError):
            validate_catalog(definition())


class TestRequestValidation(unittest.TestCase):
    def test_a_missing_request_means_report_everything(self):
        self.assertEqual(validate_request(None), [])

    def test_a_mapping_request_yields_its_identifier_list(self):
        self.assertEqual(
            validate_request({"definition_ids": ["FM-POWER"]}), ["FM-POWER"]
        )

    def test_a_bare_list_request_is_accepted(self):
        self.assertEqual(validate_request(["FM-POWER"]), ["FM-POWER"])

    def test_a_repeated_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_request(["FM-POWER", "FM-POWER"])

    def test_a_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_request(["  "])

    def test_a_non_list_identifier_field_raises(self):
        with self.assertRaises(ValueError):
            validate_request({"definition_ids": "FM-POWER"})

    def test_identifier_order_is_preserved(self):
        self.assertEqual(
            validate_request(["FM-THERMAL", "FM-POWER"]), ["FM-THERMAL", "FM-POWER"]
        )


class TestResolution(unittest.TestCase):
    def test_an_empty_request_resolves_to_the_whole_store(self):
        resolution = resolve_requested_ids(None, catalog())
        self.assertTrue(resolution["reported_all"])
        self.assertEqual(resolution["known"], ["FM-POWER", "FM-THERMAL"])

    def test_a_known_identifier_resolves(self):
        resolution = resolve_requested_ids(["FM-THERMAL"], catalog())
        self.assertEqual(resolution["known"], ["FM-THERMAL"])
        self.assertEqual(resolution["unknown"], [])

    def test_an_unknown_identifier_is_carried_not_dropped(self):
        resolution = resolve_requested_ids(["FM-GHOST"], catalog())
        self.assertEqual(resolution["known"], [])
        self.assertEqual(resolution["unknown"], ["FM-GHOST"])

    def test_a_mixed_request_splits(self):
        resolution = resolve_requested_ids(["FM-POWER", "FM-GHOST"], catalog())
        self.assertEqual(resolution["known"], ["FM-POWER"])
        self.assertEqual(resolution["unknown"], ["FM-GHOST"])

    def test_an_empty_store_resolves_everything_as_unknown(self):
        resolution = resolve_requested_ids(["FM-POWER"], [])
        self.assertEqual(resolution["unknown"], ["FM-POWER"])


class TestReportAssembly(unittest.TestCase):
    def test_an_entry_carries_the_full_constituent_list(self):
        entry = definition_report_entry(definition())
        self.assertEqual(len(entry["constituents"]), 2)
        self.assertEqual(entry["constituent_count"], 2)

    def test_an_entry_carries_the_failing_threshold(self):
        entry = definition_report_entry(definition(threshold=1))
        self.assertEqual(entry["failing_threshold"], 1)

    def test_an_empty_request_reports_every_definition(self):
        report = build_definition_report(catalog())
        self.assertEqual(report["definition_count"], 2)
        self.assertTrue(report["reported_all"])

    def test_the_report_follows_the_requested_order(self):
        report = build_definition_report(catalog(), ["FM-THERMAL", "FM-POWER"])
        self.assertEqual(
            [entry["id"] for entry in report["entries"]], ["FM-THERMAL", "FM-POWER"]
        )

    def test_the_constituent_total_sums_across_entries(self):
        report = build_definition_report(catalog())
        self.assertEqual(report["constituent_count"], 5)

    def test_unknown_identifiers_produce_no_entry(self):
        report = build_definition_report(catalog(), ["FM-GHOST"])
        self.assertEqual(report["entries"], [])
        self.assertEqual(report["unknown_ids"], ["FM-GHOST"])

    def test_a_report_of_one_definition_carries_only_it(self):
        report = build_definition_report(catalog(), ["FM-POWER"])
        self.assertEqual([entry["id"] for entry in report["entries"]], ["FM-POWER"])
        self.assertEqual(report["constituent_count"], 2)


class TestReportCompleteness(unittest.TestCase):
    def test_a_freshly_built_report_is_complete(self):
        self.assertTrue(report_is_complete(build_definition_report(catalog()))["complete"])

    def test_a_truncated_entry_list_is_detected(self):
        report = build_definition_report(catalog())
        report["entries"] = report["entries"][:1]
        result = report_is_complete(report)
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["findings"]), 2)

    def test_a_wrong_constituent_total_is_detected(self):
        report = build_definition_report(catalog())
        report["constituent_count"] = 99
        self.assertFalse(report_is_complete(report)["complete"])

    def test_a_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            report_is_complete(["entries"])

    def test_a_negative_declared_count_raises(self):
        report = build_definition_report(catalog())
        report["definition_count"] = -1
        with self.assertRaises(ValueError):
            report_is_complete(report)

    def test_an_entry_without_a_constituent_list_raises(self):
        report = build_definition_report(catalog())
        del report["entries"][0]["constituents"]
        with self.assertRaises(ValueError):
            report_is_complete(report)


class TestRequestHandling(unittest.TestCase):
    def test_a_fully_resolvable_request_is_accepted(self):
        result = assess_report_request(catalog(), ["FM-POWER", "FM-THERMAL"])
        self.assertEqual(result["acceptance"], ACCEPTANCE_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_a_mixed_request_is_partially_accepted(self):
        result = assess_report_request(catalog(), ["FM-POWER", "FM-GHOST"])
        self.assertEqual(result["acceptance"], ACCEPTANCE_PARTIAL)
        self.assertEqual(result["reported_ids"], ["FM-POWER"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_wholly_unknown_request_is_rejected(self):
        result = assess_report_request(catalog(), ["FM-GHOST", "FM-PHANTOM"])
        self.assertEqual(result["acceptance"], ACCEPTANCE_REJECTED)
        self.assertEqual(result["reported_ids"], [])
        self.assertEqual(len(result["findings"]), 2)

    def test_an_empty_request_reports_the_whole_store(self):
        result = assess_report_request(catalog())
        self.assertEqual(result["acceptance"], ACCEPTANCE_ACCEPTED)
        self.assertTrue(result["reported_all"])
        self.assertEqual(result["held_count"], 2)

    def test_the_report_is_complete_by_construction(self):
        result = assess_report_request(catalog(), ["FM-THERMAL"])
        self.assertTrue(result["complete"])

    def test_an_empty_store_with_an_empty_request_reports_nothing(self):
        result = assess_report_request([])
        self.assertEqual(result["acceptance"], ACCEPTANCE_ACCEPTED)
        self.assertEqual(result["reported_ids"], [])

    def test_an_invalid_store_entry_raises_before_any_report(self):
        broken = catalog()
        broken[0]["failing_threshold"] = 9
        with self.assertRaises(ValueError):
            assess_report_request(broken)

    def test_a_repeated_requested_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_report_request(catalog(), ["FM-POWER", "FM-POWER"])


if __name__ == "__main__":
    unittest.main()
