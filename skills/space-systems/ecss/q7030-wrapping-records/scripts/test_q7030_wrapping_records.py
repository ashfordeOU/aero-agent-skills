"""Contract test for the q7030-wrapping-records leaf (stdlib unittest)."""

import copy
import datetime
import unittest

from q7030_wrapping_records_logic import (
    COMPLETE,
    INCOMPLETE,
    RECORD_RETENTION_YEARS,
    TOOL_SETUP_VALIDITY_DAYS,
    audit_wrapping_records,
    days_between,
    group_key,
    groups_without_pull_test,
    retention_findings,
    validate_package,
    validate_tool,
    validate_wrap_record,
    wrap_findings,
)

TODAY = datetime.date(2026, 9, 18)
WRAP_DAY = datetime.date(2026, 9, 15)


def tool(tool_id="TL-3", **kw):
    record = {
        "id": tool_id,
        "calibration_due_date": datetime.date(2027, 1, 1),
        "setup_verification_date": WRAP_DAY,
    }
    record.update(kw)
    return record


def wrap(wrap_id="W-1", **kw):
    record = {
        "id": wrap_id,
        "operator_id": "OP-11",
        "tool_id": "TL-3",
        "gauge": 26,
        "wrap_date": WRAP_DAY,
        "pull_test_reference": "PT-100",
        "inspection_reference": "INS-7",
    }
    record.update(kw)
    return record


def package(**kw):
    record = {
        "assembly_id": "ASSY-1",
        "certified_operators": ["OP-11", "OP-12"],
        "tools": [tool()],
        "wraps": [wrap("W-1"), wrap("W-2")],
    }
    record.update(kw)
    return copy.deepcopy(record)


class TestDates(unittest.TestCase):
    def test_days_between_counts_forward(self):
        self.assertEqual(days_between(WRAP_DAY, TODAY), 3)

    def test_days_between_counts_backward(self):
        self.assertEqual(days_between(TODAY, WRAP_DAY), -3)

    def test_an_iso_string_is_accepted(self):
        self.assertEqual(days_between("2026-09-15", TODAY), 3)

    def test_a_malformed_date_raises(self):
        with self.assertRaises(ValueError):
            days_between("15 Sept 2026", TODAY)


class TestValidation(unittest.TestCase):
    def test_a_tool_needs_an_id(self):
        with self.assertRaises(ValueError):
            validate_tool({"calibration_due_date": TODAY, "setup_verification_date": TODAY})

    def test_a_wrap_needs_a_known_gauge(self):
        with self.assertRaises(ValueError):
            validate_wrap_record(wrap(gauge=18))

    def test_a_wrap_may_have_no_operator(self):
        norm = validate_wrap_record(wrap(operator_id=None))
        self.assertIsNone(norm["operator_id"])

    def test_a_blank_operator_string_raises(self):
        with self.assertRaises(ValueError):
            validate_wrap_record(wrap(operator_id="   "))

    def test_a_package_needs_wraps(self):
        with self.assertRaises(ValueError):
            validate_package(package(wraps=[]))

    def test_duplicate_wrap_ids_raise(self):
        with self.assertRaises(ValueError):
            validate_package(package(wraps=[wrap("W-1"), wrap("W-1")]))

    def test_duplicate_tool_ids_raise(self):
        with self.assertRaises(ValueError):
            validate_package(package(tools=[tool("TL-3"), tool("TL-3")]))

    def test_group_key_is_operator_tool_and_gauge(self):
        self.assertEqual(group_key(wrap()), ("OP-11", "TL-3", 26))


class TestWrapFindings(unittest.TestCase):
    def setUp(self):
        self.tools = {"TL-3": validate_tool(tool())}
        self.certified = {"OP-11", "OP-12"}

    def test_a_complete_record_has_no_finding(self):
        self.assertEqual(wrap_findings(wrap(), self.tools, self.certified), [])

    def test_a_missing_operator_is_reported(self):
        findings = wrap_findings(wrap(operator_id=None), self.tools, self.certified)
        self.assertIn("no-operator-on-the-wrap-record", findings)

    def test_an_uncertified_operator_is_reported(self):
        findings = wrap_findings(wrap(operator_id="OP-99"), self.tools, self.certified)
        self.assertIn("operator-not-in-the-certified-list", findings)

    def test_a_missing_tool_is_reported(self):
        findings = wrap_findings(wrap(tool_id=None), self.tools, self.certified)
        self.assertIn("no-tool-on-the-wrap-record", findings)

    def test_a_tool_absent_from_the_package_is_reported(self):
        findings = wrap_findings(wrap(tool_id="TL-9"), self.tools, self.certified)
        self.assertIn("tool-not-described-in-the-package", findings)

    def test_a_missing_inspection_reference_is_reported(self):
        findings = wrap_findings(
            wrap(inspection_reference=None), self.tools, self.certified
        )
        self.assertIn("no-inspection-reference-on-the-wrap-record", findings)

    def test_calibration_expired_before_the_wrap_is_reported(self):
        tools = {"TL-3": validate_tool(tool(calibration_due_date=datetime.date(2026, 9, 1)))}
        findings = wrap_findings(wrap(), tools, self.certified)
        self.assertIn("tool-calibration-expired-before-the-wrap", findings)

    def test_calibration_due_on_the_wrap_day_is_still_in_date(self):
        tools = {"TL-3": validate_tool(tool(calibration_due_date=WRAP_DAY))}
        self.assertEqual(wrap_findings(wrap(), tools, self.certified), [])

    def test_a_setup_verified_after_the_wrap_is_reported(self):
        tools = {
            "TL-3": validate_tool(
                tool(setup_verification_date=WRAP_DAY + datetime.timedelta(days=1))
            )
        }
        findings = wrap_findings(wrap(), tools, self.certified)
        self.assertIn("tool-setup-verified-after-the-wrap", findings)

    def test_a_stale_setup_verification_is_reported(self):
        stale = WRAP_DAY - datetime.timedelta(days=TOOL_SETUP_VALIDITY_DAYS + 1)
        tools = {"TL-3": validate_tool(tool(setup_verification_date=stale))}
        findings = wrap_findings(wrap(), tools, self.certified)
        self.assertIn("tool-setup-verification-older-than-its-window", findings)

    def test_a_setup_exactly_on_the_window_edge_is_accepted(self):
        edge = WRAP_DAY - datetime.timedelta(days=TOOL_SETUP_VALIDITY_DAYS)
        tools = {"TL-3": validate_tool(tool(setup_verification_date=edge))}
        self.assertEqual(wrap_findings(wrap(), tools, self.certified), [])


class TestPullTestCoverage(unittest.TestCase):
    def test_a_covered_group_is_not_reported(self):
        self.assertEqual(groups_without_pull_test(package()), [])

    def test_a_second_operator_owes_its_own_pull_test(self):
        pkg = package(
            wraps=[wrap("W-1"), wrap("W-2", operator_id="OP-12", pull_test_reference=None)]
        )
        self.assertEqual(groups_without_pull_test(pkg), [("OP-12", "TL-3", 26)])

    def test_a_second_gauge_owes_its_own_pull_test(self):
        pkg = package(
            wraps=[wrap("W-1"), wrap("W-2", gauge=30, pull_test_reference=None)]
        )
        self.assertEqual(groups_without_pull_test(pkg), [("OP-11", "TL-3", 30)])

    def test_one_reference_covers_the_whole_group(self):
        pkg = package(wraps=[wrap("W-1"), wrap("W-2", pull_test_reference=None)])
        self.assertEqual(groups_without_pull_test(pkg), [])


class TestRetention(unittest.TestCase):
    def test_a_fresh_record_is_not_expiring(self):
        self.assertEqual(retention_findings(package(), TODAY), [])

    def test_a_record_past_retention_is_reported(self):
        old = WRAP_DAY - datetime.timedelta(days=RECORD_RETENTION_YEARS * 365 + 10)
        pkg = package(wraps=[wrap("W-1", wrap_date=old), wrap("W-2")])
        self.assertEqual(retention_findings(pkg, TODAY), ["W-1"])

    def test_a_record_exactly_on_the_retention_edge_is_kept(self):
        edge = TODAY - datetime.timedelta(days=RECORD_RETENTION_YEARS * 365)
        pkg = package(wraps=[wrap("W-1", wrap_date=edge)])
        self.assertEqual(retention_findings(pkg, TODAY), [])


class TestAudit(unittest.TestCase):
    def test_a_complete_package_is_complete(self):
        result = audit_wrapping_records(package(), TODAY)
        self.assertEqual(result["status"], COMPLETE)
        self.assertTrue(result["complete"])
        self.assertAlmostEqual(result["traceability_coverage"], 1.0, places=9)

    def test_one_untraceable_wrap_breaks_the_package(self):
        pkg = package(wraps=[wrap("W-1"), wrap("W-2", operator_id=None)])
        result = audit_wrapping_records(pkg, TODAY)
        self.assertEqual(result["status"], INCOMPLETE)
        self.assertEqual(result["untraceable_ids"], ["W-2"])
        self.assertAlmostEqual(result["traceability_coverage"], 0.5, places=9)

    def test_an_uncovered_group_breaks_the_package(self):
        pkg = package(
            wraps=[wrap("W-1"), wrap("W-2", gauge=30, pull_test_reference=None)]
        )
        result = audit_wrapping_records(pkg, TODAY)
        self.assertFalse(result["complete"])
        self.assertIn("group-without-a-referenced-pull-test", result["package_findings"])

    def test_an_out_of_retention_record_breaks_the_package(self):
        old = TODAY - datetime.timedelta(days=RECORD_RETENTION_YEARS * 365 + 5)
        pkg = package(wraps=[wrap("W-1", wrap_date=old)])
        result = audit_wrapping_records(pkg, TODAY)
        self.assertIn(
            "wrap-records-past-their-retention-period", result["package_findings"]
        )

    def test_coverage_is_exactly_one_on_a_three_wrap_package(self):
        pkg = package(wraps=[wrap("W-1"), wrap("W-2"), wrap("W-3")])
        result = audit_wrapping_records(pkg, TODAY)
        self.assertAlmostEqual(result["traceability_coverage"], 1.0, places=9)
        self.assertTrue(result["complete"])

    def test_a_non_mapping_package_raises(self):
        with self.assertRaises(ValueError):
            audit_wrapping_records(["ASSY-1"], TODAY)


if __name__ == "__main__":
    unittest.main()
