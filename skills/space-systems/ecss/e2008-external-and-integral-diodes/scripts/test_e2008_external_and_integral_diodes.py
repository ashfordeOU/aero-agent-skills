#!/usr/bin/env python3
"""Contract test for the external and integral diode generic specification.

Walks the clause workflow step by step: the specification validation,
the per-issue and two-sided agreement rule, the binding date as the
later of the two party dates, the comparison against the earliest
acceptance activity, the agreed share against the declared minimum, the
coverage gaps over both diode kinds, the superseded citation detector
and the roll-up into one baseline verdict. Offline, stdlib only. This is
the gate 3 review evidence for the leaf.
"""

import copy
import unittest

from e2008_external_and_integral_diodes_logic import (
    BASELINE_AGREED,
    BASELINE_NOT_AGREED,
    DEFAULT_BASELINE_POLICY,
    DIODE_KINDS,
    PARTIES,
    assess_diode_specification_baseline,
    grade_agreement,
    grade_citations,
    grade_coverage,
    grade_timing,
    parse_date,
    resolve_policy,
    validate_activity,
    validate_agreement,
    validate_specification,
)


def _spec(issue=3, covers=DIODE_KINDS, spec_id="GS-DIODE-01"):
    return {"spec_id": spec_id, "issue": issue, "covers": list(covers)}


def _agreements(customer=("2026-01-10", 3), supplier=("2026-01-14", 3)):
    records = []
    if customer is not None:
        records.append(
            {
                "party": "customer",
                "agreed_on": customer[0],
                "agreed_issue": customer[1],
            }
        )
    if supplier is not None:
        records.append(
            {
                "party": "supplier",
                "agreed_on": supplier[0],
                "agreed_issue": supplier[1],
            }
        )
    return records


def _activities():
    return [
        {
            "activity_id": "AT-EXT-01",
            "diode_kind": "external",
            "started_on": "2026-02-02",
            "cited_issue": 3,
        },
        {
            "activity_id": "AT-INT-01",
            "diode_kind": "integral",
            "started_on": "2026-03-09",
            "cited_issue": 3,
        },
    ]


def _case(**extra):
    case = {
        "baseline_id": "BASE-944",
        "specification": _spec(),
        "agreements": _agreements(),
        "activities": _activities(),
    }
    case.update(copy.deepcopy(extra))
    return case


class SpecificationTests(unittest.TestCase):
    def test_a_sound_specification_validates(self):
        spec = validate_specification(_spec())
        self.assertEqual(spec["issue"], 3)
        self.assertEqual(spec["covers"], list(DIODE_KINDS))

    def test_a_zero_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_specification(_spec(issue=0))

    def test_a_non_integer_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_specification(_spec(issue="three"))

    def test_an_unknown_diode_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_specification(_spec(covers=("external", "bypass")))

    def test_a_specification_covering_nothing_rejected(self):
        with self.assertRaises(ValueError):
            validate_specification(_spec(covers=()))

    def test_a_blank_specification_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_specification(_spec(spec_id="  "))


class DateTests(unittest.TestCase):
    def test_an_ordered_date_parses(self):
        self.assertEqual(parse_date("agreed_on", "2026-01-10").year, 2026)

    def test_a_free_text_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("agreed_on", "sometime in January")

    def test_dates_order_by_value_not_by_text(self):
        self.assertLess(
            parse_date("a", "2025-12-31"), parse_date("b", "2026-01-01")
        )


class AgreementTests(unittest.TestCase):
    def test_a_two_sided_current_agreement_is_complete(self):
        result = grade_agreement(_spec(), _agreements())
        self.assertEqual(result["agreed_parties"], sorted(PARTIES))
        self.assertAlmostEqual(result["agreed_share"], 1.0, places=9)
        self.assertTrue(result["meets_agreed_share"])
        self.assertEqual(result["findings"], [])

    def test_the_binding_date_is_the_later_of_the_two(self):
        result = grade_agreement(_spec(), _agreements())
        self.assertEqual(result["binding_date"].isoformat(), "2026-01-14")

    def test_a_one_sided_record_is_reported(self):
        result = grade_agreement(_spec(), _agreements(customer=None))
        self.assertEqual(result["outstanding_parties"], ["customer"])
        self.assertAlmostEqual(result["agreed_share"], 0.5, places=9)
        self.assertFalse(result["meets_agreed_share"])

    def test_a_signature_carried_across_a_re_issue_does_not_count(self):
        result = grade_agreement(_spec(issue=3), _agreements(customer=("2026-01-10", 2)))
        self.assertEqual(result["stale_agreements"], ["customer"])
        self.assertIn("customer", result["outstanding_parties"])

    def test_a_party_listed_twice_rejected(self):
        records = _agreements() + [
            {"party": "customer", "agreed_on": "2026-01-11", "agreed_issue": 3}
        ]
        with self.assertRaises(ValueError):
            grade_agreement(_spec(), records)

    def test_an_unknown_party_rejected(self):
        with self.assertRaises(ValueError):
            validate_agreement(
                {"party": "auditor", "agreed_on": "2026-01-10", "agreed_issue": 3}
            )


class TimingTests(unittest.TestCase):
    def test_an_agreement_before_the_earliest_activity_passes(self):
        agreement = grade_agreement(_spec(), _agreements())
        result = grade_timing(agreement["binding_date"], _activities())
        self.assertTrue(result["settled_beforehand"])
        self.assertEqual(result["earliest_activity"], "AT-EXT-01")
        self.assertEqual(result["lead_days"], 19)

    def test_the_comparison_uses_the_earliest_not_the_latest_activity(self):
        agreement = grade_agreement(
            _spec(), _agreements(customer=("2026-02-20", 3), supplier=("2026-02-21", 3))
        )
        result = grade_timing(agreement["binding_date"], _activities())
        self.assertFalse(result["settled_beforehand"])
        self.assertEqual(result["earliest_activity"], "AT-EXT-01")

    def test_a_late_agreement_reports_a_negative_lead(self):
        agreement = grade_agreement(
            _spec(), _agreements(customer=("2026-02-10", 3), supplier=("2026-02-12", 3))
        )
        result = grade_timing(agreement["binding_date"], _activities())
        self.assertEqual(result["lead_days"], -10)
        self.assertTrue(result["findings"])

    def test_an_agreement_on_the_start_day_is_not_beforehand(self):
        agreement = grade_agreement(
            _spec(), _agreements(customer=("2026-02-01", 3), supplier=("2026-02-02", 3))
        )
        result = grade_timing(agreement["binding_date"], _activities())
        self.assertEqual(result["lead_days"], 0)
        self.assertFalse(result["settled_beforehand"])

    def test_no_binding_date_cannot_be_shown_beforehand(self):
        result = grade_timing(None, _activities())
        self.assertFalse(result["settled_beforehand"])
        self.assertIsNone(result["lead_days"])

    def test_an_empty_activity_list_rejected(self):
        with self.assertRaises(ValueError):
            grade_timing(parse_date("d", "2026-01-01"), [])


class CoverageTests(unittest.TestCase):
    def test_both_kinds_covered_leaves_no_gap(self):
        result = grade_coverage(_spec(), _activities())
        self.assertEqual(result["uncovered_kinds"], [])
        self.assertEqual(result["findings"], [])

    def test_a_dropped_integral_kind_is_a_gap(self):
        result = grade_coverage(_spec(covers=("external",)), _activities())
        self.assertEqual(result["uncovered_kinds"], ["integral"])
        self.assertEqual(result["uncovered_activities"], ["AT-INT-01"])

    def test_the_both_kinds_rule_can_be_relaxed_by_policy(self):
        result = grade_coverage(
            _spec(covers=("external",)),
            [_activities()[0]],
            {"require_both_kinds_covered": False},
        )
        self.assertEqual(result["findings"], [])

    def test_an_unknown_activity_kind_rejected(self):
        activity = _activities()[0]
        activity["diode_kind"] = "blocking"
        with self.assertRaises(ValueError):
            validate_activity(activity)


class CitationTests(unittest.TestCase):
    def test_current_citations_leave_nothing_superseded(self):
        result = grade_citations(_spec(), _activities())
        self.assertEqual(result["superseded_activities"], [])
        self.assertEqual(len(result["current_activities"]), 2)

    def test_a_superseded_citation_is_its_own_case(self):
        activities = _activities()
        activities[1]["cited_issue"] = 2
        result = grade_citations(_spec(), activities)
        self.assertEqual(result["superseded_activities"], ["AT-INT-01"])
        self.assertTrue(
            any("re-run or a justification" in f for f in result["findings"])
        )


class PolicyTests(unittest.TestCase):
    def test_defaults_resolve(self):
        settings = resolve_policy()
        self.assertAlmostEqual(
            settings["min_agreed_share"],
            DEFAULT_BASELINE_POLICY["min_agreed_share"],
            places=9,
        )
        self.assertFalse(settings["carry_late_agreement"])

    def test_a_non_boolean_late_policy_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"carry_late_agreement": "only if asked"})

    def test_a_share_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"min_agreed_share": 0.0})


class RollUpTests(unittest.TestCase):
    def test_a_sound_baseline_is_agreed(self):
        result = assess_diode_specification_baseline(_case())
        self.assertEqual(result["verdict"], BASELINE_AGREED)
        self.assertEqual(result["findings"], [])

    def test_a_one_sided_baseline_is_not_agreed(self):
        result = assess_diode_specification_baseline(
            _case(agreements=_agreements(supplier=None))
        )
        self.assertEqual(result["verdict"], BASELINE_NOT_AGREED)
        self.assertTrue(result["findings"])

    def test_a_late_baseline_blocks_unless_policy_carries_it(self):
        late = _case(
            agreements=_agreements(
                customer=("2026-02-10", 3), supplier=("2026-02-12", 3)
            )
        )
        self.assertEqual(
            assess_diode_specification_baseline(late)["verdict"],
            BASELINE_NOT_AGREED,
        )
        carried = copy.deepcopy(late)
        carried["policy"] = {"carry_late_agreement": True}
        self.assertEqual(
            assess_diode_specification_baseline(carried)["verdict"],
            BASELINE_AGREED,
        )

    def test_a_dropped_integral_kind_blocks_the_baseline(self):
        result = assess_diode_specification_baseline(
            _case(specification=_spec(covers=("external",)))
        )
        self.assertEqual(result["verdict"], BASELINE_NOT_AGREED)
        self.assertIn("integral", result["coverage"]["uncovered_kinds"])

    def test_a_superseded_citation_blocks_the_baseline(self):
        activities = _activities()
        activities[0]["cited_issue"] = 2
        result = assess_diode_specification_baseline(_case(activities=activities))
        self.assertEqual(result["verdict"], BASELINE_NOT_AGREED)
        self.assertEqual(result["citations"]["superseded_activities"], ["AT-EXT-01"])

    def test_a_blank_baseline_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_specification_baseline(_case(baseline_id="   "))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_specification_baseline("the parties agreed beforehand")


if __name__ == "__main__":
    unittest.main()
