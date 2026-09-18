#!/usr/bin/env python3
"""Contract test for the hybrid design approval general provisions (offline)."""

import copy
import datetime
import unittest

from q6005_design_approval_general_provisions_logic import (
    APPROVAL_NOT_VALID,
    GENERAL_PROVISIONS,
    PROVISIONS_MET,
    PROVISIONS_OPEN,
    PROVISION_STATES,
    VALIDITY_EXPIRED,
    VALIDITY_LINE_MOVED,
    VALIDITY_VALID,
    add_months,
    applicable_weight,
    approval_validity,
    assess_general_provisions,
    blocking_provisions,
    parse_date,
    readiness_fraction,
    validate_provision_states,
    validate_waiver,
)

AS_OF = "2026-09-18"

ALL_SATISFIED = {name: "satisfied" for name in GENERAL_PROVISIONS}

GOOD_WAIVER = {
    "authority": "customer product assurance manager",
    "reference": "waiver request 0042 rev B",
    "expires_on": "2027-03-31",
}

GOOD_CASE = {
    "states": dict(ALL_SATISFIED),
    "as_of": AS_OF,
    "granted_on": "2025-06-01",
    "validity_months": 24,
    "waivers": {},
}


def _states(**overrides):
    states = dict(ALL_SATISFIED)
    states.update(overrides)
    return states


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class RegistryTests(unittest.TestCase):
    def test_every_provision_carries_a_weight_and_a_waivability(self):
        for name, spec in GENERAL_PROVISIONS.items():
            self.assertIn("weight", spec, name)
            self.assertIn("waivable", spec, name)
            self.assertGreater(spec["weight"], 0, name)

    def test_the_hard_gates_are_not_waivable(self):
        for name in (
            "agreed-procurement-specification",
            "approved-design-baseline",
            "manufacturer-capability-approval",
            "named-manufacturing-line",
        ):
            self.assertFalse(GENERAL_PROVISIONS[name]["waivable"], name)

    def test_four_provision_states_are_offered(self):
        self.assertEqual(len(PROVISION_STATES), 4)


class StateValidationTests(unittest.TestCase):
    def test_a_complete_declaration_validates(self):
        self.assertEqual(validate_provision_states(ALL_SATISFIED), ALL_SATISFIED)

    def test_a_missing_provision_is_rejected_not_defaulted(self):
        states = dict(ALL_SATISFIED)
        del states["approved-design-baseline"]
        with self.assertRaises(ValueError):
            validate_provision_states(states)

    def test_an_unknown_provision_rejected(self):
        with self.assertRaises(ValueError):
            validate_provision_states(_states(**{"good-vibes": "satisfied"}))

    def test_an_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_provision_states(_states(**{"approved-design-baseline": "mostly"}))

    def test_a_non_mapping_declaration_rejected(self):
        with self.assertRaises(ValueError):
            validate_provision_states("satisfied")


class WeightTests(unittest.TestCase):
    def test_applicable_weight_counts_every_provision_by_default(self):
        self.assertEqual(
            applicable_weight(ALL_SATISFIED),
            sum(spec["weight"] for spec in GENERAL_PROVISIONS.values()),
        )

    def test_a_not_applicable_provision_leaves_the_denominator(self):
        states = _states(**{"change-control-notification-agreed": "not-applicable"})
        self.assertEqual(
            applicable_weight(states),
            applicable_weight(ALL_SATISFIED)
            - GENERAL_PROVISIONS["change-control-notification-agreed"]["weight"],
        )

    def test_all_satisfied_is_fully_ready(self):
        self.assertAlmostEqual(readiness_fraction(ALL_SATISFIED), 1.0, places=9)

    def test_an_open_provision_lowers_readiness_by_its_share(self):
        states = _states(**{"design-data-package-complete": "open"})
        total = applicable_weight(ALL_SATISFIED)
        expected = (
            total - GENERAL_PROVISIONS["design-data-package-complete"]["weight"]
        ) / total
        self.assertAlmostEqual(readiness_fraction(states), expected, places=9)

    def test_a_waived_provision_counts_as_closed_for_readiness(self):
        waived = _states(**{"design-data-package-complete": "waived"})
        self.assertAlmostEqual(readiness_fraction(waived), 1.0, places=9)

    def test_a_not_applicable_provision_does_not_lower_readiness(self):
        states = _states(**{"process-identification-document": "not-applicable"})
        self.assertAlmostEqual(readiness_fraction(states), 1.0, places=9)

    def test_everything_not_applicable_is_rejected(self):
        states = {name: "not-applicable" for name in GENERAL_PROVISIONS}
        with self.assertRaises(ValueError):
            readiness_fraction(states)


class DateTests(unittest.TestCase):
    def test_an_iso_string_parses(self):
        self.assertEqual(parse_date("as_of", "2026-09-18"), datetime.date(2026, 9, 18))

    def test_a_date_object_passes_through(self):
        day = datetime.date(2026, 9, 18)
        self.assertEqual(parse_date("as_of", day), day)

    def test_a_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("as_of", "18/09/2026")

    def test_a_non_string_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("as_of", 20260918)

    def test_months_roll_the_year_over(self):
        self.assertEqual(
            add_months(datetime.date(2025, 11, 15), 4), datetime.date(2026, 3, 15)
        )

    def test_a_long_day_clamps_into_a_short_month(self):
        self.assertEqual(
            add_months(datetime.date(2026, 1, 31), 1), datetime.date(2026, 2, 28)
        )

    def test_a_negative_month_count_rejected(self):
        with self.assertRaises(ValueError):
            add_months(datetime.date(2026, 1, 31), -1)


class WaiverTests(unittest.TestCase):
    def test_a_complete_waiver_validates(self):
        record = validate_waiver(GOOD_WAIVER, AS_OF)
        self.assertFalse(record["expired"])
        self.assertGreater(record["days_remaining"], 0)

    def test_a_waiver_without_an_authority_rejected(self):
        broken = dict(GOOD_WAIVER)
        del broken["authority"]
        with self.assertRaises(ValueError):
            validate_waiver(broken, AS_OF)

    def test_a_waiver_without_a_reference_rejected(self):
        broken = dict(GOOD_WAIVER, reference="   ")
        with self.assertRaises(ValueError):
            validate_waiver(broken, AS_OF)

    def test_a_waiver_without_an_expiry_rejected(self):
        broken = dict(GOOD_WAIVER)
        del broken["expires_on"]
        with self.assertRaises(ValueError):
            validate_waiver(broken, AS_OF)

    def test_an_expired_waiver_is_reported_as_expired(self):
        stale = dict(GOOD_WAIVER, expires_on="2026-01-31")
        self.assertTrue(validate_waiver(stale, AS_OF)["expired"])


class BlockerTests(unittest.TestCase):
    def test_all_satisfied_has_no_blockers(self):
        self.assertEqual(blocking_provisions(ALL_SATISFIED, {}, AS_OF), [])

    def test_an_open_provision_blocks(self):
        states = _states(**{"design-data-package-complete": "open"})
        blockers = blocking_provisions(states, {}, AS_OF)
        self.assertEqual([name for name, _ in blockers], ["design-data-package-complete"])

    def test_a_waiver_on_a_non_waivable_provision_does_not_close_it(self):
        states = _states(**{"manufacturer-capability-approval": "waived"})
        waivers = {"manufacturer-capability-approval": dict(GOOD_WAIVER)}
        blockers = blocking_provisions(states, waivers, AS_OF)
        self.assertEqual(len(blockers), 1)
        self.assertIn("not waivable", blockers[0][1])

    def test_a_waived_provision_with_a_live_waiver_does_not_block(self):
        states = _states(**{"design-data-package-complete": "waived"})
        waivers = {"design-data-package-complete": dict(GOOD_WAIVER)}
        self.assertEqual(blocking_provisions(states, waivers, AS_OF), [])

    def test_a_waived_provision_with_no_waiver_on_file_blocks(self):
        states = _states(**{"design-data-package-complete": "waived"})
        blockers = blocking_provisions(states, {}, AS_OF)
        self.assertIn("no recorded waiver", blockers[0][1])

    def test_a_waived_provision_with_an_expired_waiver_blocks(self):
        states = _states(**{"design-data-package-complete": "waived"})
        waivers = {
            "design-data-package-complete": dict(GOOD_WAIVER, expires_on="2026-02-01")
        }
        blockers = blocking_provisions(states, waivers, AS_OF)
        self.assertIn("waiver expired", blockers[0][1])

    def test_a_waiver_against_an_unknown_provision_rejected(self):
        with self.assertRaises(ValueError):
            blocking_provisions(ALL_SATISFIED, {"lunch-approval": dict(GOOD_WAIVER)}, AS_OF)

    def test_a_waiver_needing_an_as_of_date_rejected_without_one(self):
        states = _states(**{"design-data-package-complete": "waived"})
        waivers = {"design-data-package-complete": dict(GOOD_WAIVER)}
        with self.assertRaises(ValueError):
            blocking_provisions(states, waivers, None)


class ValidityTests(unittest.TestCase):
    def test_an_approval_inside_its_window_is_live(self):
        result = approval_validity("2025-06-01", 24, AS_OF)
        self.assertEqual(result["status"], VALIDITY_VALID)
        self.assertTrue(result["live"])
        self.assertEqual(result["expires_on"], datetime.date(2027, 6, 1))

    def test_an_approval_past_its_window_is_expired(self):
        result = approval_validity("2023-06-01", 24, AS_OF)
        self.assertEqual(result["status"], VALIDITY_EXPIRED)
        self.assertFalse(result["live"])

    def test_an_approval_exactly_on_its_expiry_day_is_still_live(self):
        result = approval_validity("2024-09-18", 24, AS_OF)
        self.assertEqual(result["status"], VALIDITY_VALID)
        self.assertEqual(result["days_remaining"], 0)

    def test_a_line_move_voids_an_otherwise_live_approval(self):
        result = approval_validity("2025-06-01", 24, AS_OF, line_changed=True)
        self.assertEqual(result["status"], VALIDITY_LINE_MOVED)
        self.assertFalse(result["live"])

    def test_an_as_of_before_the_grant_rejected(self):
        with self.assertRaises(ValueError):
            approval_validity("2026-12-01", 24, AS_OF)

    def test_a_zero_validity_window_rejected(self):
        with self.assertRaises(ValueError):
            approval_validity("2025-06-01", 0, AS_OF)

    def test_a_non_boolean_line_flag_rejected(self):
        with self.assertRaises(ValueError):
            approval_validity("2025-06-01", 24, AS_OF, line_changed="moved")


class AssessmentTests(unittest.TestCase):
    def test_a_clean_case_meets_the_provisions(self):
        result = assess_general_provisions(GOOD_CASE)
        self.assertEqual(result["verdict"], PROVISIONS_MET)
        self.assertEqual(result["blockers"], [])
        self.assertAlmostEqual(result["readiness_fraction"], 1.0, places=9)
        self.assertTrue(result["validity"]["live"])

    def test_an_open_provision_leaves_the_provisions_open(self):
        case = _case(GOOD_CASE, states=_states(**{"process-identification-document": "open"}))
        result = assess_general_provisions(case)
        self.assertEqual(result["verdict"], PROVISIONS_OPEN)
        self.assertEqual(result["blockers"], ["process-identification-document"])

    def test_an_expired_approval_outranks_a_clean_provision_set(self):
        case = _case(GOOD_CASE, granted_on="2022-06-01")
        result = assess_general_provisions(case)
        self.assertEqual(result["verdict"], APPROVAL_NOT_VALID)
        self.assertTrue(any("validity" in f for f in result["findings"]))

    def test_a_line_move_outranks_a_clean_provision_set(self):
        case = _case(GOOD_CASE, line_changed=True)
        self.assertEqual(
            assess_general_provisions(case)["verdict"], APPROVAL_NOT_VALID
        )

    def test_a_non_waivable_provision_waived_is_named(self):
        case = _case(
            GOOD_CASE,
            states=_states(**{"named-manufacturing-line": "waived"}),
            waivers={"named-manufacturing-line": dict(GOOD_WAIVER)},
        )
        result = assess_general_provisions(case)
        self.assertEqual(result["verdict"], PROVISIONS_OPEN)
        self.assertIn("named-manufacturing-line", result["non_waivable_open"])

    def test_an_assessment_without_a_grant_date_skips_validity(self):
        case = _case(GOOD_CASE)
        del case["granted_on"]
        result = assess_general_provisions(case)
        self.assertIsNone(result["validity"])
        self.assertEqual(result["verdict"], PROVISIONS_MET)

    def test_assessment_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            assess_general_provisions("satisfied")

    def test_assessment_rejects_an_incomplete_state_declaration(self):
        states = dict(ALL_SATISFIED)
        del states["approved-materials-and-parts-list"]
        with self.assertRaises(ValueError):
            assess_general_provisions(_case(GOOD_CASE, states=states))

    def test_readiness_is_reported_even_when_the_verdict_is_open(self):
        case = _case(GOOD_CASE, states=_states(**{"design-data-package-complete": "open"}))
        result = assess_general_provisions(case)
        self.assertLess(result["readiness_fraction"], 1.0)
        self.assertGreater(result["readiness_fraction"], 0.8)


if __name__ == "__main__":
    unittest.main()
