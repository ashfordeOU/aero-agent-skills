"""Contract tests for the clause 5.5.3 class 2 alert handling assessment.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: no source declared at all, a
delegated subscription nobody recorded, a subscription forwarding too slowly, a
source nobody has swept, coverage short of either floor, an alert set aside
with no rationale, and a response clock that has run past its deadline.
"""

import unittest

from q6013_class_2_alert_handling_logic import (
    ALERT_HANDLING_MEETS_CLASS_TWO,
    APPLICABLE,
    COVERAGE_TOLERANCE,
    DEFAULT_MONITORING_POLICY,
    DELEGATED,
    DELEGATION_NOT_RECORDED,
    DIRECT,
    DISPOSITION_UNJUSTIFIED,
    MONITORING_NOT_ESTABLISHED,
    NOT_APPLICABLE,
    RECOGNISED_SOURCE_CATEGORIES,
    RESPONSE_OVERDUE,
    SOURCE_COVERAGE_SHORT,
    alert_response_timing,
    assess_alert_handling,
    category_coverage,
    effective_sources,
    source_is_live,
    validate_alert,
    validate_alerts,
    validate_monitoring_policy,
    validate_source,
    validate_sources,
    working_days_between,
)

AS_OF = 200


def _source(identifier, category, mode=DIRECT, sweep=195, record="", forwarding=1):
    source = {
        "id": identifier,
        "category": category,
        "mode": mode,
        "last_sweep_day": sweep,
    }
    if mode == DELEGATED:
        source["delegation_record"] = record
        source["forwarding_days"] = forwarding
    return source


def _full_sources():
    return [
        _source("src-%d" % index, category)
        for index, category in enumerate(RECOGNISED_SOURCE_CATEGORIES, start=1)
    ]


def _alert(identifier="alrt-1", received=196, acknowledged=197,
           disposition=APPLICABLE, disposition_day=199, rationale="", action="quarantine stock"):
    record = {
        "id": identifier,
        "received_day": received,
        "acknowledged_day": acknowledged,
        "rationale": rationale,
        "action": action,
    }
    if disposition is not None:
        record["disposition"] = disposition
        record["disposition_day"] = disposition_day
    return record


def _case(**overrides):
    case = {
        "sources": _full_sources(),
        "as_of_day": AS_OF,
        "alerts": [_alert()],
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        settings = validate_monitoring_policy(None)
        self.assertEqual(settings["monitoring_interval_days"], 30)
        self.assertEqual(len(settings["required_source_categories"]), 4)

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_monitoring_policy({"alert_interval": 30})

    def test_credited_floor_above_plain_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_monitoring_policy(
                {"min_source_coverage": 0.5, "min_credited_source_coverage": 0.9}
            )

    def test_unrecognised_required_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_monitoring_policy({"required_source_categories": ["rumour-mill"]})

    def test_empty_required_category_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_monitoring_policy({"required_source_categories": []})

    def test_negative_deadline_rejected(self):
        with self.assertRaises(ValueError):
            validate_monitoring_policy({"acknowledgement_working_days": -1})

    def test_credit_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_monitoring_policy({"delegated_source_credit": 1.5})

    def test_defaults_are_not_shared_between_calls(self):
        first = validate_monitoring_policy(None)
        first["required_source_categories"].append("manufacturer-notice")
        second = validate_monitoring_policy(None)
        self.assertEqual(len(second["required_source_categories"]),
                         len(DEFAULT_MONITORING_POLICY["required_source_categories"]))


class WorkingDayTests(unittest.TestCase):
    def test_same_day_is_zero_working_days(self):
        self.assertEqual(working_days_between(10, 10), 0)

    def test_a_whole_week_is_five_working_days(self):
        self.assertEqual(working_days_between(0, 7), 5)

    def test_a_weekend_is_skipped(self):
        # Day 4 is a Friday, day 7 the following Monday.
        self.assertEqual(working_days_between(4, 7), 1)

    def test_four_weeks_scale_exactly(self):
        self.assertEqual(working_days_between(0, 28), 20)

    def test_reversed_days_rejected(self):
        with self.assertRaises(ValueError):
            working_days_between(9, 8)

    def test_non_integer_day_rejected(self):
        with self.assertRaises(ValueError):
            working_days_between(0, 7.0)


class SourceValidationTests(unittest.TestCase):
    def test_source_without_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_source({"category": "manufacturer-notice", "last_sweep_day": 1})

    def test_unrecognised_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(_source("src-1", "back-channel"))

    def test_unknown_mode_rejected(self):
        bad = _source("src-1", "manufacturer-notice")
        bad["mode"] = "borrowed"
        with self.assertRaises(ValueError):
            validate_source(bad)

    def test_delegated_source_needs_forwarding_days(self):
        bad = _source("src-1", "manufacturer-notice", mode=DELEGATED, record="DEL-1")
        del bad["forwarding_days"]
        with self.assertRaises(ValueError):
            validate_source(bad)

    def test_direct_source_carrying_a_delegation_record_rejected(self):
        bad = _source("src-1", "manufacturer-notice")
        bad["delegation_record"] = "DEL-9"
        with self.assertRaises(ValueError):
            validate_source(bad)

    def test_duplicate_source_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_sources([_source("src-1", "manufacturer-notice"),
                              _source("src-1", "distributor-notice")])

    def test_sweep_after_the_assessment_day_rejected(self):
        record = validate_source(_source("src-1", "manufacturer-notice", sweep=250))
        with self.assertRaises(ValueError):
            source_is_live(record, AS_OF)


class MonitoringTests(unittest.TestCase):
    def test_a_recent_sweep_keeps_a_source_live(self):
        record = validate_source(_source("src-1", "manufacturer-notice", sweep=195))
        self.assertTrue(source_is_live(record, AS_OF))

    def test_a_sweep_exactly_on_the_interval_still_counts(self):
        record = validate_source(_source("src-1", "manufacturer-notice", sweep=AS_OF - 30))
        self.assertTrue(source_is_live(record, AS_OF))

    def test_a_sweep_past_the_interval_goes_stale(self):
        record = validate_source(_source("src-1", "manufacturer-notice", sweep=AS_OF - 31))
        self.assertFalse(source_is_live(record, AS_OF))

    def test_unrecorded_delegation_removes_the_source(self):
        sources = validate_sources(
            [_source("src-1", "manufacturer-notice", mode=DELEGATED, record="")]
        )
        split = effective_sources(sources, AS_OF)
        self.assertEqual(split["unrecorded_delegations"], ["src-1"])
        self.assertEqual(split["counted"], [])

    def test_slow_forwarding_removes_the_source(self):
        sources = validate_sources(
            [_source("src-1", "manufacturer-notice", mode=DELEGATED,
                     record="DEL-1", forwarding=9)]
        )
        split = effective_sources(sources, AS_OF)
        self.assertEqual(split["slow_forwarding"], ["src-1"])

    def test_forwarding_exactly_on_the_bound_is_kept(self):
        sources = validate_sources(
            [_source("src-1", "manufacturer-notice", mode=DELEGATED,
                     record="DEL-1", forwarding=5)]
        )
        split = effective_sources(sources, AS_OF)
        self.assertEqual([r["id"] for r in split["counted"]], ["src-1"])


class CoverageTests(unittest.TestCase):
    def test_all_categories_watched_directly_give_full_coverage(self):
        counted = effective_sources(validate_sources(_full_sources()), AS_OF)["counted"]
        coverage = category_coverage(counted)
        self.assertAlmostEqual(coverage["plain"], 1.0, places=9)
        self.assertAlmostEqual(coverage["credited"], 1.0, places=9)

    def test_a_delegated_category_is_credited_below_a_direct_one(self):
        sources = _full_sources()
        sources[0]["mode"] = DELEGATED
        sources[0]["delegation_record"] = "DEL-1"
        sources[0]["forwarding_days"] = 2
        counted = effective_sources(validate_sources(sources), AS_OF)["counted"]
        coverage = category_coverage(counted)
        self.assertAlmostEqual(coverage["plain"], 1.0, places=9)
        self.assertAlmostEqual(coverage["credited"], 0.875, places=9)

    def test_a_missing_category_is_named(self):
        counted = effective_sources(validate_sources(_full_sources()[:3]), AS_OF)["counted"]
        coverage = category_coverage(counted)
        self.assertEqual(coverage["uncovered_categories"], ["industry-alert-exchange"])
        self.assertAlmostEqual(coverage["plain"], 0.75, places=9)

    def test_coverage_exactly_on_its_floor_is_met(self):
        result = assess_alert_handling(_case(sources=_full_sources()[:3]))
        self.assertAlmostEqual(result["plain_source_coverage"], 0.75, places=9)
        self.assertNotEqual(result["verdict"], SOURCE_COVERAGE_SHORT)

    def test_the_best_source_for_a_category_wins(self):
        sources = _full_sources()
        extra = _source("src-dup", "manufacturer-notice", mode=DELEGATED,
                        record="DEL-2", forwarding=1)
        counted = effective_sources(validate_sources(sources + [extra]), AS_OF)["counted"]
        coverage = category_coverage(counted)
        self.assertAlmostEqual(coverage["credited"], 1.0, places=9)

    def test_coverage_tolerance_is_small_but_nonzero(self):
        self.assertGreater(COVERAGE_TOLERANCE, 0.0)
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


class AlertValidationTests(unittest.TestCase):
    def test_alert_without_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_alert({"received_day": 10})

    def test_acknowledgement_before_receipt_rejected(self):
        with self.assertRaises(ValueError):
            validate_alert(_alert(received=100, acknowledged=99))

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            validate_alert(_alert(disposition="deferred"))

    def test_disposition_without_a_day_rejected(self):
        bad = _alert()
        del bad["disposition_day"]
        with self.assertRaises(ValueError):
            validate_alert(bad)

    def test_duplicate_alert_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_alerts([_alert("alrt-1"), _alert("alrt-1")])

    def test_no_alerts_is_an_empty_desk_not_an_error(self):
        self.assertEqual(validate_alerts(None), [])


class ResponseTimingTests(unittest.TestCase):
    def test_an_answered_alert_reports_both_clocks(self):
        entry = alert_response_timing(validate_alert(_alert(received=196, acknowledged=197,
                                                            disposition_day=199)), AS_OF)
        self.assertTrue(entry["acknowledged"])
        self.assertTrue(entry["dispositioned"])
        self.assertEqual(entry["breaches"], [])

    def test_an_open_disposition_keeps_accruing_to_the_assessment_day(self):
        record = validate_alert(_alert(received=150, acknowledged=151, disposition=None))
        entry = alert_response_timing(record, AS_OF)
        self.assertGreater(entry["disposition_working_days"], 20)
        self.assertTrue(entry["breaches"])

    def test_a_late_acknowledgement_is_a_breach(self):
        record = validate_alert(_alert(received=150, acknowledged=170, disposition=None,
                                       disposition_day=None))
        entry = alert_response_timing(record, AS_OF)
        self.assertGreater(entry["acknowledgement_working_days"], 5)

    def test_a_record_after_the_assessment_day_rejected(self):
        record = validate_alert(_alert(received=196, acknowledged=250, disposition=None))
        with self.assertRaises(ValueError):
            alert_response_timing(record, AS_OF)


class AssessmentTests(unittest.TestCase):
    def test_a_complete_arrangement_meets_the_class(self):
        result = assess_alert_handling(_case())
        self.assertEqual(result["verdict"], ALERT_HANDLING_MEETS_CLASS_TWO)
        self.assertEqual(result["findings"], [])

    def test_no_sources_closes_on_monitoring_not_established(self):
        result = assess_alert_handling(_case(sources=[]))
        self.assertEqual(result["verdict"], MONITORING_NOT_ESTABLISHED)
        self.assertFalse(result["monitoring_established"])

    def test_every_source_stale_closes_on_monitoring_not_established(self):
        sources = [_source("src-%d" % i, c, sweep=10)
                   for i, c in enumerate(RECOGNISED_SOURCE_CATEGORIES, start=1)]
        result = assess_alert_handling(_case(sources=sources))
        self.assertEqual(result["verdict"], MONITORING_NOT_ESTABLISHED)

    def test_an_unrecorded_delegation_outranks_a_coverage_shortfall(self):
        sources = _full_sources()
        sources[0]["mode"] = DELEGATED
        sources[0]["delegation_record"] = ""
        sources[0]["forwarding_days"] = 1
        result = assess_alert_handling(_case(sources=sources))
        self.assertEqual(result["verdict"], DELEGATION_NOT_RECORDED)
        self.assertEqual(result["unrecorded_delegations"], ["src-1"])

    def test_two_missing_categories_are_coverage_short(self):
        result = assess_alert_handling(_case(sources=_full_sources()[:2]))
        self.assertEqual(result["verdict"], SOURCE_COVERAGE_SHORT)
        self.assertEqual(len(result["uncovered_categories"]), 2)

    def test_a_not_applicable_alert_without_rationale_is_unjustified(self):
        alert = _alert(disposition=NOT_APPLICABLE, rationale="", action="")
        result = assess_alert_handling(_case(alerts=[alert]))
        self.assertEqual(result["verdict"], DISPOSITION_UNJUSTIFIED)
        self.assertEqual(result["unjustified_alerts"], ["alrt-1"])

    def test_a_not_applicable_alert_with_rationale_passes(self):
        alert = _alert(disposition=NOT_APPLICABLE,
                       rationale="the named date codes were never procured", action="")
        result = assess_alert_handling(_case(alerts=[alert]))
        self.assertEqual(result["verdict"], ALERT_HANDLING_MEETS_CLASS_TWO)

    def test_an_applicable_alert_naming_no_action_is_undisposed(self):
        alert = _alert(action="")
        result = assess_alert_handling(_case(alerts=[alert]))
        self.assertEqual(result["verdict"], DISPOSITION_UNJUSTIFIED)
        self.assertEqual(result["undisposed_alerts"], ["alrt-1"])

    def test_a_late_answer_is_reported_as_overdue(self):
        alert = _alert(received=150, acknowledged=151, disposition_day=199)
        result = assess_alert_handling(_case(alerts=[alert]))
        self.assertEqual(result["verdict"], RESPONSE_OVERDUE)
        self.assertEqual(result["overdue_alerts"], ["alrt-1"])

    def test_stale_sources_are_named_rather_than_counted(self):
        sources = _full_sources()
        sources[3]["last_sweep_day"] = 10
        result = assess_alert_handling(_case(sources=sources))
        self.assertEqual(result["stale_sources"], ["src-4"])

    def test_case_without_sources_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_alert_handling({"as_of_day": AS_OF})

    def test_case_without_as_of_day_rejected(self):
        with self.assertRaises(ValueError):
            assess_alert_handling({"sources": _full_sources()})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_alert_handling(["sources"])

    def test_the_report_carries_both_coverage_figures(self):
        result = assess_alert_handling(_case())
        self.assertIn("plain_source_coverage", result)
        self.assertIn("credited_source_coverage", result)


if __name__ == "__main__":
    unittest.main(verbosity=0)
