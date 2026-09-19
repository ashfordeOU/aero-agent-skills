"""Contract test for the e7041 parameter value report leaf."""

import unittest

from e7041_report_parameter_values_logic import (
    VERDICT_DEFECTIVE,
    VERDICT_FAILED_START,
    VERDICT_REPORTED,
    assess_value_report,
    build_value_report,
    failure_notifications,
    report_is_complete,
    representable_domain,
    resolve_request,
    validate_parameter,
    validate_request,
    validate_store,
    value_fits,
    value_report_entry,
)


def parameter(parameter_id="PAR-BUS-VOLTAGE", apid="AP-PWR",
              representation="unsigned-integer", value=42, **kw):
    record = {
        "application_process_id": apid,
        "parameter_id": parameter_id,
        "representation": representation,
        "value": value,
    }
    if representation in ("unsigned-integer", "signed-integer"):
        record.setdefault("bits", 8)
    record.update(kw)
    return record


def store():
    return [
        parameter("PAR-BUS-VOLTAGE", "AP-PWR", value=42),
        parameter("PAR-BUS-CURRENT", "AP-PWR", value=17),
        parameter("PAR-BUS-VOLTAGE", "AP-THM", value=200),
    ]


class TestStoreValidation(unittest.TestCase):
    def test_a_valid_parameter_normalizes(self):
        record = validate_parameter(parameter())
        self.assertEqual(record["parameter_id"], "PAR-BUS-VOLTAGE")
        self.assertEqual(record["domain"], {"lower": 0, "upper": 255})

    def test_a_non_mapping_parameter_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter("PAR-BUS-VOLTAGE")

    def test_a_parameter_with_no_current_value_raises(self):
        record = parameter()
        del record["value"]
        with self.assertRaises(ValueError):
            validate_parameter(record)

    def test_an_unknown_representation_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter(parameter(representation="float128"))

    def test_an_integer_parameter_with_no_width_raises(self):
        record = parameter()
        del record["bits"]
        with self.assertRaises(ValueError):
            validate_parameter(record)

    def test_declared_limits_narrow_the_domain(self):
        record = validate_parameter(parameter(lower_limit=10, upper_limit=100))
        self.assertEqual(record["domain"], {"lower": 10, "upper": 100})

    def test_an_empty_domain_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter(parameter(lower_limit=200, upper_limit=100))

    def test_a_repeated_identifier_in_one_process_raises(self):
        with self.assertRaises(ValueError):
            validate_store([parameter("PAR-A"), parameter("PAR-A")])

    def test_the_same_name_under_another_process_is_another_parameter(self):
        self.assertEqual(len(validate_store(store())), 3)

    def test_a_non_list_store_raises(self):
        with self.assertRaises(ValueError):
            validate_store(parameter())

    def test_an_integer_domain_is_derived_with_exact_arithmetic(self):
        domain = representable_domain("unsigned-integer", 32)
        self.assertEqual(domain["upper"], (1 << 32) - 1)


class TestStoredValueCheck(unittest.TestCase):
    def test_a_value_inside_the_domain_fits(self):
        self.assertTrue(value_fits(parameter(value=42))["fits"])

    def test_a_value_on_the_upper_bound_fits(self):
        self.assertTrue(value_fits(parameter(value=255))["fits"])

    def test_a_value_past_the_representation_does_not_fit(self):
        result = value_fits(parameter(value=300))
        self.assertFalse(result["fits"])
        self.assertIn("upper", result["reason"])

    def test_a_value_outside_a_declared_limit_does_not_fit(self):
        self.assertFalse(value_fits(parameter(value=200, upper_limit=100))["fits"])

    def test_a_fractional_value_does_not_fit_an_integer_parameter(self):
        self.assertFalse(value_fits(parameter(value=4.5))["fits"])

    def test_a_boolean_parameter_takes_only_booleans(self):
        self.assertTrue(value_fits(parameter(representation="boolean", value=True))["fits"])
        self.assertFalse(value_fits(parameter(representation="boolean", value=1))["fits"])

    def test_a_real_value_on_its_declared_bound_fits(self):
        record = parameter(
            representation="real", value=1.0, lower_limit=0.0, upper_limit=1.0
        )
        self.assertTrue(value_fits(record)["fits"])
        self.assertAlmostEqual(validate_parameter(record)["domain"]["upper"], 1.0, places=9)

    def test_normalizing_a_normalized_parameter_keeps_its_limits(self):
        once = validate_parameter(parameter(value=42, upper_limit=100))
        self.assertEqual(validate_parameter(once)["domain"], {"lower": 0, "upper": 100})

    def test_a_report_withholds_a_value_past_a_declared_limit(self):
        records = store()
        records[0]["upper_limit"] = 100
        records[0]["value"] = 200
        outcome = build_value_report(records, "AP-PWR", ["PAR-BUS-VOLTAGE"])
        self.assertEqual(outcome["report"]["withheld_count"], 1)
        self.assertEqual(outcome["report"]["reported_count"], 0)

    def test_a_text_value_does_not_fit_a_numeric_parameter(self):
        self.assertFalse(value_fits(parameter(value="42"))["fits"])


class TestRequestNormalization(unittest.TestCase):
    def test_a_named_request_normalizes(self):
        request = validate_request(["PAR-A", "PAR-B"])
        self.assertEqual(request["identifiers"], ["PAR-A", "PAR-B"])

    def test_an_empty_request_is_refused_rather_than_read_as_a_sweep(self):
        with self.assertRaises(ValueError):
            validate_request([])

    def test_a_repeated_identifier_collapses_and_is_recorded(self):
        request = validate_request(["PAR-A", "PAR-B", "PAR-A"])
        self.assertEqual(request["identifiers"], ["PAR-A", "PAR-B"])
        self.assertEqual(request["repeated"], ["PAR-A"])

    def test_request_order_is_preserved(self):
        self.assertEqual(
            validate_request(["PAR-C", "PAR-A"])["identifiers"], ["PAR-C", "PAR-A"]
        )

    def test_a_non_list_request_raises(self):
        with self.assertRaises(ValueError):
            validate_request("PAR-A")

    def test_a_non_string_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_request(["PAR-A", 7])


class TestResolution(unittest.TestCase):
    def test_a_known_identifier_resolves(self):
        resolution = resolve_request(store(), "AP-PWR", ["PAR-BUS-CURRENT"])
        self.assertEqual(len(resolution["resolved"]), 1)

    def test_an_unknown_identifier_is_separated_not_dropped(self):
        resolution = resolve_request(store(), "AP-PWR", ["PAR-BUS-CURRENT", "PAR-GHOST"])
        self.assertEqual(resolution["unknown"], ["PAR-GHOST"])
        self.assertEqual(len(resolution["resolved"]), 1)

    def test_resolution_is_scoped_to_the_named_application_process(self):
        resolution = resolve_request(store(), "AP-THM", ["PAR-BUS-CURRENT"])
        self.assertEqual(resolution["unknown"], ["PAR-BUS-CURRENT"])

    def test_the_same_name_under_the_requested_process_resolves_to_that_one(self):
        resolution = resolve_request(store(), "AP-THM", ["PAR-BUS-VOLTAGE"])
        self.assertEqual(resolution["resolved"][0]["value"], 200)

    def test_resolution_keeps_request_order(self):
        resolution = resolve_request(
            store(), "AP-PWR", ["PAR-BUS-CURRENT", "PAR-BUS-VOLTAGE"]
        )
        self.assertEqual(
            [r["parameter_id"] for r in resolution["resolved"]],
            ["PAR-BUS-CURRENT", "PAR-BUS-VOLTAGE"],
        )

    def test_one_notification_is_raised_per_unknown_identifier(self):
        resolution = resolve_request(store(), "AP-PWR", ["PAR-G1", "PAR-G2"])
        notifications = failure_notifications(resolution)
        self.assertEqual(len(notifications), 2)
        self.assertEqual(notifications[0]["failure"], "no-such-on-board-parameter")

    def test_a_non_mapping_resolution_raises(self):
        with self.assertRaises(ValueError):
            failure_notifications(["PAR-A"])


class TestReportAssembly(unittest.TestCase):
    def test_an_entry_carries_the_value_and_representation(self):
        entry = value_report_entry(parameter(value=42))
        self.assertEqual(entry["value"], 42)
        self.assertEqual(entry["representation"], "unsigned-integer")

    def test_a_clean_request_is_reported_in_request_order(self):
        outcome = build_value_report(
            store(), "AP-PWR", ["PAR-BUS-CURRENT", "PAR-BUS-VOLTAGE"]
        )
        self.assertTrue(outcome["generated"])
        self.assertEqual(
            [e["parameter_id"] for e in outcome["report"]["entries"]],
            ["PAR-BUS-CURRENT", "PAR-BUS-VOLTAGE"],
        )

    def test_a_partly_unknown_request_still_reports_the_known_ones(self):
        outcome = build_value_report(store(), "AP-PWR", ["PAR-BUS-VOLTAGE", "PAR-GHOST"])
        self.assertEqual(outcome["report"]["reported_count"], 1)
        self.assertEqual(outcome["report"]["unknown_count"], 1)

    def test_a_request_where_nothing_resolves_generates_no_report(self):
        outcome = build_value_report(store(), "AP-PWR", ["PAR-G1", "PAR-G2"])
        self.assertFalse(outcome["generated"])
        self.assertIsNone(outcome["report"])
        self.assertEqual(len(outcome["notifications"]), 2)

    def test_a_repeated_identifier_produces_one_entry(self):
        outcome = build_value_report(
            store(), "AP-PWR", ["PAR-BUS-VOLTAGE", "PAR-BUS-VOLTAGE"]
        )
        self.assertEqual(outcome["report"]["reported_count"], 1)

    def test_a_stored_value_that_no_longer_fits_is_withheld(self):
        records = store()
        records[0]["value"] = 999
        outcome = build_value_report(records, "AP-PWR", ["PAR-BUS-VOLTAGE"])
        self.assertEqual(outcome["report"]["reported_count"], 0)
        self.assertEqual(outcome["report"]["withheld_count"], 1)

    def test_a_withheld_value_carries_a_reason(self):
        records = store()
        records[0]["value"] = 999
        outcome = build_value_report(records, "AP-PWR", ["PAR-BUS-VOLTAGE"])
        self.assertTrue(outcome["withheld"][0]["reason"])

    def test_the_value_is_read_at_assembly_time_not_cached(self):
        records = store()
        first = build_value_report(records, "AP-PWR", ["PAR-BUS-VOLTAGE"])
        records[0]["value"] = 77
        second = build_value_report(records, "AP-PWR", ["PAR-BUS-VOLTAGE"])
        self.assertEqual(first["report"]["entries"][0]["value"], 42)
        self.assertEqual(second["report"]["entries"][0]["value"], 77)


class TestReportCompleteness(unittest.TestCase):
    def test_a_freshly_built_report_is_complete(self):
        outcome = build_value_report(store(), "AP-PWR", ["PAR-BUS-VOLTAGE"])
        self.assertTrue(report_is_complete(outcome["report"])["complete"])

    def test_a_truncated_entry_list_is_detected(self):
        outcome = build_value_report(
            store(), "AP-PWR", ["PAR-BUS-VOLTAGE", "PAR-BUS-CURRENT"]
        )
        outcome["report"]["entries"] = outcome["report"]["entries"][:1]
        self.assertFalse(report_is_complete(outcome["report"])["complete"])

    def test_a_duplicated_entry_is_detected(self):
        outcome = build_value_report(store(), "AP-PWR", ["PAR-BUS-VOLTAGE"])
        report = outcome["report"]
        report["entries"].append(report["entries"][0])
        report["reported_count"] = 2
        self.assertFalse(report_is_complete(report)["complete"])

    def test_the_three_totals_must_account_for_every_identifier_requested(self):
        outcome = build_value_report(store(), "AP-PWR", ["PAR-BUS-VOLTAGE", "PAR-GHOST"])
        self.assertTrue(report_is_complete(outcome["report"])["complete"])
        outcome["report"]["unknown_count"] = 0
        self.assertFalse(report_is_complete(outcome["report"])["complete"])

    def test_a_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            report_is_complete(["entries"])

    def test_a_negative_declared_count_raises(self):
        outcome = build_value_report(store(), "AP-PWR", ["PAR-BUS-VOLTAGE"])
        outcome["report"]["reported_count"] = -1
        with self.assertRaises(ValueError):
            report_is_complete(outcome["report"])


class TestFullAssessment(unittest.TestCase):
    def test_a_clean_request_is_reported(self):
        result = assess_value_report(store(), "AP-PWR", ["PAR-BUS-VOLTAGE"])
        self.assertEqual(result["verdict"], VERDICT_REPORTED)
        self.assertEqual(result["findings"], [])

    def test_the_reported_identifiers_follow_request_order(self):
        result = assess_value_report(
            store(), "AP-PWR", ["PAR-BUS-CURRENT", "PAR-BUS-VOLTAGE"]
        )
        self.assertEqual(result["reported_ids"], ["PAR-BUS-CURRENT", "PAR-BUS-VOLTAGE"])

    def test_an_unknown_identifier_is_named_in_the_findings(self):
        result = assess_value_report(store(), "AP-PWR", ["PAR-BUS-VOLTAGE", "PAR-GHOST"])
        self.assertEqual(result["unknown_ids"], ["PAR-GHOST"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_request_where_nothing_resolves_fails_at_start(self):
        result = assess_value_report(store(), "AP-PWR", ["PAR-GHOST"])
        self.assertEqual(result["verdict"], VERDICT_FAILED_START)
        self.assertIsNone(result["report"])

    def test_a_repeated_identifier_is_raised_as_a_finding(self):
        result = assess_value_report(
            store(), "AP-PWR", ["PAR-BUS-VOLTAGE", "PAR-BUS-VOLTAGE"]
        )
        self.assertEqual(result["verdict"], VERDICT_REPORTED)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_withheld_value_makes_the_outcome_defective(self):
        records = store()
        records[1]["value"] = 999
        result = assess_value_report(records, "AP-PWR", ["PAR-BUS-CURRENT"])
        self.assertEqual(result["verdict"], VERDICT_DEFECTIVE)
        self.assertEqual(result["withheld_ids"], ["PAR-BUS-CURRENT"])

    def test_an_invalid_store_entry_raises_before_any_report(self):
        broken = store()
        del broken[0]["value"]
        with self.assertRaises(ValueError):
            assess_value_report(broken, "AP-PWR", ["PAR-BUS-VOLTAGE"])

    def test_an_empty_request_raises_before_any_report(self):
        with self.assertRaises(ValueError):
            assess_value_report(store(), "AP-PWR", [])


if __name__ == "__main__":
    unittest.main()
