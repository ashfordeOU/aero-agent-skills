#!/usr/bin/env python3
"""Contract test for contamination-control facility audits (offline)."""

import copy
import datetime
import unittest

from q7001_cleanliness_audits_logic import (
    APPROVAL_INDEX,
    BASE_REAUDIT_MONTHS,
    CONDITIONAL_INDEX,
    CRITICALITY_CRITICAL,
    CRITICALITY_LEVELS,
    CRITICALITY_SENSITIVE,
    CRITICALITY_STANDARD,
    FINDING_SEVERITIES,
    MAJOR_TOLERANCE,
    MIN_REAUDIT_MONTHS,
    PRACTICE_AREAS,
    SCORE_MAX,
    SEVERITY_MAJOR,
    SEVERITY_MINOR,
    SEVERITY_OBSERVATION,
    STATUS_APPROVED,
    STATUS_CONDITIONAL,
    STATUS_SUSPENDED,
    add_months,
    audit_contamination_control,
    conformity_index,
    group_findings,
    normalise_finding,
    normalise_scores,
    parse_date,
    reaudit_interval_months,
)

PERFECT = {area: SCORE_MAX for area in PRACTICE_AREAS}

CASE = {
    "facility": "supplier-cleanroom-hall-2",
    "audit_date": "2026-03-31",
    "criticality": CRITICALITY_SENSITIVE,
    "scores": PERFECT,
    "findings": [],
}


def _case(**overrides):
    case = copy.deepcopy(CASE)
    case.update(overrides)
    return case


def _scores(**overrides):
    scores = dict(PERFECT)
    scores.update(overrides)
    return scores


class ScaleTests(unittest.TestCase):
    def test_every_practice_area_carries_a_weight(self):
        for area, weight in PRACTICE_AREAS.items():
            self.assertGreater(weight, 0, area)

    def test_method_and_air_quality_outweigh_documentation(self):
        self.assertGreater(
            PRACTICE_AREAS["cleaning-and-verification-method"],
            PRACTICE_AREAS["documentation-and-traceability"],
        )
        self.assertGreater(
            PRACTICE_AREAS["cleanroom-air-quality-monitoring"],
            PRACTICE_AREAS["material-and-consumable-control"],
        )

    def test_score_above_the_scale_rejected(self):
        with self.assertRaises(ValueError):
            normalise_scores(_scores(**{"documentation-and-traceability": 5}))

    def test_negative_score_rejected(self):
        with self.assertRaises(ValueError):
            normalise_scores(_scores(**{"documentation-and-traceability": -1}))

    def test_boolean_score_rejected(self):
        with self.assertRaises(ValueError):
            normalise_scores(_scores(**{"documentation-and-traceability": True}))

    def test_unknown_practice_area_rejected(self):
        scores = _scores()
        scores["coffee-machine-hygiene"] = 4
        with self.assertRaises(ValueError):
            normalise_scores(scores)

    def test_empty_score_set_rejected(self):
        with self.assertRaises(ValueError):
            normalise_scores({})

    def test_iso_audit_date_parses(self):
        self.assertEqual(parse_date("audit_date", "2026-03-31"), datetime.date(2026, 3, 31))

    def test_malformed_audit_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("audit_date", "31/03/2026")

    def test_month_arithmetic_clamps_to_the_month_end(self):
        self.assertEqual(add_months(datetime.date(2026, 1, 31), 1), datetime.date(2026, 2, 28))

    def test_month_arithmetic_crosses_the_year(self):
        self.assertEqual(add_months(datetime.date(2026, 11, 15), 4), datetime.date(2027, 3, 15))

    def test_negative_month_offset_rejected(self):
        with self.assertRaises(ValueError):
            add_months(datetime.date(2026, 1, 31), -1)


class IndexTests(unittest.TestCase):
    def test_a_perfect_audit_indexes_at_one(self):
        self.assertAlmostEqual(conformity_index(PERFECT)["index"], 1.0, places=9)

    def test_the_index_is_weighted_not_averaged(self):
        heavy = conformity_index(_scores(**{"cleaning-and-verification-method": 2}))
        light = conformity_index(_scores(**{"documentation-and-traceability": 2}))
        self.assertLess(heavy["index"], light["index"])

    def test_a_partial_scope_still_indexes_on_a_zero_to_one_scale(self):
        subset = {
            "cleaning-and-verification-method": 4,
            "cleanroom-air-quality-monitoring": 4,
        }
        self.assertAlmostEqual(conformity_index(subset)["index"], 1.0, places=9)

    def test_areas_not_examined_are_reported_not_scored_zero(self):
        subset = {"cleaning-and-verification-method": 4}
        result = conformity_index(subset)
        self.assertIn("documentation-and-traceability", result["areas_not_examined"])
        self.assertAlmostEqual(result["index"], 1.0, places=9)

    def test_a_collapsed_area_is_named(self):
        result = conformity_index(_scores(**{"garmenting-and-personnel-flow": 0}))
        self.assertEqual(result["collapsed_areas"], ("garmenting-and-personnel-flow",))

    def test_the_weakest_area_is_identified(self):
        result = conformity_index(
            _scores(
                **{
                    "garmenting-and-personnel-flow": 1,
                    "documentation-and-traceability": 2,
                }
            )
        )
        self.assertEqual(result["weakest_area"], "garmenting-and-personnel-flow")


class FindingTests(unittest.TestCase):
    def test_findings_are_counted_by_severity(self):
        result = group_findings(
            [
                {"id": "F1", "area": "garmenting-and-personnel-flow", "severity": SEVERITY_MAJOR},
                {"id": "F2", "area": "documentation-and-traceability", "severity": SEVERITY_MINOR},
                {"id": "F3", "area": "documentation-and-traceability", "severity": SEVERITY_MINOR},
            ]
        )
        self.assertEqual(result["counts"][SEVERITY_MAJOR], 1)
        self.assertEqual(result["counts"][SEVERITY_MINOR], 2)
        self.assertEqual(result["total"], 3)

    def test_finding_identifiers_are_kept_to_act_on(self):
        result = group_findings(
            [{"id": "F9", "area": "handling-packaging-and-purge", "severity": SEVERITY_MAJOR}]
        )
        self.assertEqual(result["ids"][SEVERITY_MAJOR], ("F9",))

    def test_every_severity_is_represented_in_the_counts(self):
        result = group_findings([])
        for severity in FINDING_SEVERITIES:
            self.assertIn(severity, result["counts"])

    def test_finding_without_a_severity_rejected(self):
        with self.assertRaises(ValueError):
            normalise_finding({"id": "F4", "area": "documentation-and-traceability"})

    def test_finding_against_an_unknown_area_rejected(self):
        with self.assertRaises(ValueError):
            normalise_finding({"id": "F5", "area": "canteen", "severity": SEVERITY_MINOR})

    def test_duplicate_finding_identifier_rejected(self):
        rows = [
            {"id": "F6", "area": "documentation-and-traceability", "severity": SEVERITY_MINOR},
            {"id": "F6", "area": "documentation-and-traceability", "severity": SEVERITY_MINOR},
        ]
        with self.assertRaises(ValueError):
            group_findings(rows)

    def test_findings_must_be_a_list(self):
        with self.assertRaises(ValueError):
            group_findings({"id": "F7"})


class IntervalTests(unittest.TestCase):
    def test_a_strong_audit_gets_the_full_interval(self):
        for level in CRITICALITY_LEVELS:
            self.assertEqual(
                reaudit_interval_months(1.0, level), BASE_REAUDIT_MONTHS[level]
            )

    def test_criticality_shortens_the_interval_at_the_same_index(self):
        self.assertLess(
            reaudit_interval_months(1.0, CRITICALITY_CRITICAL),
            reaudit_interval_months(1.0, CRITICALITY_STANDARD),
        )

    def test_an_index_exactly_on_the_approval_threshold_keeps_the_full_interval(self):
        self.assertEqual(
            reaudit_interval_months(APPROVAL_INDEX, CRITICALITY_STANDARD),
            BASE_REAUDIT_MONTHS[CRITICALITY_STANDARD],
        )

    def test_an_index_exactly_on_the_conditional_threshold_halves_it(self):
        self.assertEqual(
            reaudit_interval_months(CONDITIONAL_INDEX, CRITICALITY_STANDARD),
            BASE_REAUDIT_MONTHS[CRITICALITY_STANDARD] // 2,
        )

    def test_a_weak_index_shortens_the_interval(self):
        self.assertLess(
            reaudit_interval_months(0.4, CRITICALITY_STANDARD),
            reaudit_interval_months(0.8, CRITICALITY_STANDARD),
        )

    def test_a_blocked_facility_is_re_audited_at_the_floor(self):
        self.assertEqual(
            reaudit_interval_months(1.0, CRITICALITY_STANDARD, blocked=True),
            MIN_REAUDIT_MONTHS,
        )

    def test_the_interval_never_drops_below_the_floor(self):
        for level in CRITICALITY_LEVELS:
            self.assertGreaterEqual(
                reaudit_interval_months(0.0, level), MIN_REAUDIT_MONTHS
            )

    def test_an_index_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            reaudit_interval_months(1.4, CRITICALITY_STANDARD)

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            reaudit_interval_months(1.0, "mission-critical")


class AuditOutcomeTests(unittest.TestCase):
    def test_a_clean_audit_approves_the_facility(self):
        result = audit_contamination_control(CASE)
        self.assertEqual(result["status"], STATUS_APPROVED)
        self.assertTrue(result["hardware_may_enter"])
        self.assertEqual(result["blocking_reasons"], ())

    def test_the_due_date_follows_from_the_interval(self):
        result = audit_contamination_control(CASE)
        self.assertEqual(result["reaudit_months"], 18)
        self.assertEqual(result["reaudit_due"], "2027-09-30")

    def test_a_minor_finding_makes_it_conditional(self):
        result = audit_contamination_control(
            _case(
                findings=[
                    {"id": "F1", "area": "documentation-and-traceability",
                     "severity": SEVERITY_MINOR}
                ]
            )
        )
        self.assertEqual(result["status"], STATUS_CONDITIONAL)
        self.assertTrue(result["hardware_may_enter"])

    def test_one_collapsed_area_suspends_a_strong_facility(self):
        result = audit_contamination_control(
            _case(scores=_scores(**{"garmenting-and-personnel-flow": 0}))
        )
        self.assertEqual(result["status"], STATUS_SUSPENDED)
        self.assertFalse(result["hardware_may_enter"])
        self.assertTrue(any("scoring zero" in r for r in result["blocking_reasons"]))

    def test_majors_past_the_tolerance_suspend_the_facility(self):
        findings = [
            {"id": "F%d" % i, "area": "handling-packaging-and-purge",
             "severity": SEVERITY_MAJOR}
            for i in range(MAJOR_TOLERANCE + 1)
        ]
        result = audit_contamination_control(_case(findings=findings))
        self.assertEqual(result["status"], STATUS_SUSPENDED)

    def test_a_major_within_tolerance_is_a_condition_not_a_suspension(self):
        result = audit_contamination_control(
            _case(
                findings=[
                    {"id": "F1", "area": "handling-packaging-and-purge",
                     "severity": SEVERITY_MAJOR}
                ]
            )
        )
        self.assertEqual(result["status"], STATUS_CONDITIONAL)
        self.assertTrue(any("F1" in c for c in result["conditions"]))

    def test_a_low_index_suspends_the_facility(self):
        result = audit_contamination_control(
            _case(scores={area: 1 for area in PRACTICE_AREAS})
        )
        self.assertEqual(result["status"], STATUS_SUSPENDED)
        self.assertEqual(result["reaudit_months"], MIN_REAUDIT_MONTHS)

    def test_an_observation_alone_does_not_block_entry(self):
        result = audit_contamination_control(
            _case(
                findings=[
                    {"id": "F1", "area": "documentation-and-traceability",
                     "severity": SEVERITY_OBSERVATION}
                ]
            )
        )
        self.assertTrue(result["hardware_may_enter"])

    def test_an_unexamined_area_becomes_a_condition(self):
        scores = dict(PERFECT)
        del scores["monitoring-instrument-calibration"]
        result = audit_contamination_control(_case(scores=scores))
        self.assertEqual(result["status"], STATUS_CONDITIONAL)
        self.assertTrue(any("not examined" in c for c in result["conditions"]))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            audit_contamination_control("supplier-cleanroom-hall-2")

    def test_missing_audit_date_rejected(self):
        case = _case()
        del case["audit_date"]
        with self.assertRaises(ValueError):
            audit_contamination_control(case)

    def test_missing_criticality_rejected(self):
        case = _case()
        del case["criticality"]
        with self.assertRaises(ValueError):
            audit_contamination_control(case)


if __name__ == "__main__":
    unittest.main()
