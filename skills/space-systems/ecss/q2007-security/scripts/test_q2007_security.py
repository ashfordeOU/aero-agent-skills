"""Contract test for the q2007-security leaf (stdlib unittest)."""

import unittest

from q2007_security_logic import (
    admitting_party,
    DECISION_DENIED,
    DECISION_GRANTED,
    FINDING_DATA_UNDER_PROTECTED,
    FINDING_ITEM_UNDER_PROTECTED,
    FINDING_OPEN_VISIT,
    FINDING_UNKNOWN_ZONE,
    MAX_TIER,
    MINUTES_PER_DAY,
    REASON_BADGE_EXPIRED,
    REASON_ESCORT_BADGE_EXPIRED,
    REASON_ESCORT_TIER_TOO_LOW,
    REASON_NO_ESCORT,
    REASON_OUTSIDE_HOURS,
    REASON_TIER_TOO_LOW,
    assess_site_security,
    badge_is_valid,
    escort_required,
    evaluate_access,
    holding_findings,
    open_visits,
    validate_holding,
    validate_person,
    validate_visit,
    validate_zone,
    within_authorised_hours,
    zone_occupancy,
)

DAY = 4000
NOON = 12 * 60


def zone(zone_id="Z-CHAMBER", tier=3, **kw):
    record = {
        "id": zone_id,
        "tier": tier,
        "opens_minute": 6 * 60,
        "closes_minute": 20 * 60,
    }
    record.update(kw)
    return record


def perimeter():
    return zone("Z-GATE", tier=1)


def staff(person_id="S-1", tier=3, **kw):
    record = {
        "id": person_id,
        "authorisation_tier": tier,
        "is_visitor": False,
        "badge_valid_until_day": DAY + 100,
    }
    record.update(kw)
    return record


def visitor(person_id="V-1", **kw):
    record = {
        "id": person_id,
        "authorisation_tier": 0,
        "is_visitor": True,
        "badge_valid_until_day": DAY,
    }
    record.update(kw)
    return record


def visit(visit_id="VS-1", **kw):
    record = {
        "id": visit_id,
        "person": "V-1",
        "zone": "Z-CHAMBER",
        "signed_in_minute": 9 * 60,
        "signed_out_minute": 17 * 60,
    }
    record.update(kw)
    return record


class TestValidation(unittest.TestCase):
    def test_zone_defaults_to_a_full_day_window(self):
        norm = validate_zone({"id": "Z-1", "tier": 2})
        self.assertEqual(norm["opens_minute"], 0)
        self.assertEqual(norm["closes_minute"], MINUTES_PER_DAY)

    def test_zone_tier_above_the_scale_raises(self):
        with self.assertRaises(ValueError):
            validate_zone(zone(tier=MAX_TIER + 1))

    def test_zone_tier_below_the_scale_raises(self):
        with self.assertRaises(ValueError):
            validate_zone(zone(tier=0))

    def test_zone_closing_before_it_opens_raises(self):
        with self.assertRaises(ValueError):
            validate_zone(zone(opens_minute=20 * 60, closes_minute=6 * 60))

    def test_non_mapping_zone_raises(self):
        with self.assertRaises(ValueError):
            validate_zone(["Z-1"])

    def test_person_defaults_to_no_authorisation(self):
        norm = validate_person({"id": "P-1"})
        self.assertEqual(norm["authorisation_tier"], 0)
        self.assertFalse(norm["is_visitor"])
        self.assertIsNone(norm["badge_valid_until_day"])

    def test_non_boolean_visitor_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_person(staff(is_visitor="yes"))

    def test_visit_signing_out_before_signing_in_raises(self):
        with self.assertRaises(ValueError):
            validate_visit(visit(signed_in_minute=600, signed_out_minute=300))

    def test_visit_without_a_person_raises(self):
        with self.assertRaises(ValueError):
            validate_visit(visit(person=""))

    def test_holding_tier_outside_the_scale_raises(self):
        with self.assertRaises(ValueError):
            validate_holding(
                {"id": "IT-1", "sensitivity_tier": 9, "held_in_zone": "Z-1"}, "item"
            )


class TestBadgeAndHours(unittest.TestCase):
    def test_future_badge_expiry_is_valid(self):
        self.assertTrue(badge_is_valid(staff(), DAY))

    def test_badge_expiring_today_is_still_valid(self):
        self.assertTrue(badge_is_valid(staff(badge_valid_until_day=DAY), DAY))

    def test_badge_expired_yesterday_is_not_valid(self):
        self.assertFalse(badge_is_valid(staff(badge_valid_until_day=DAY - 1), DAY))

    def test_absent_badge_record_is_not_valid(self):
        self.assertFalse(badge_is_valid(staff(badge_valid_until_day=None), DAY))

    def test_noon_is_inside_the_open_window(self):
        self.assertTrue(within_authorised_hours(zone(), NOON))

    def test_opening_minute_is_inside_the_window(self):
        self.assertTrue(within_authorised_hours(zone(), 6 * 60))

    def test_before_opening_is_outside_the_window(self):
        self.assertFalse(within_authorised_hours(zone(), 5 * 60))

    def test_minute_beyond_the_day_raises(self):
        with self.assertRaises(ValueError):
            within_authorised_hours(zone(), MINUTES_PER_DAY + 1)


class TestEscortRule(unittest.TestCase):
    def test_a_visitor_needs_an_escort_above_the_perimeter(self):
        self.assertTrue(escort_required(zone(), visitor()))

    def test_a_visitor_at_the_perimeter_needs_no_escort(self):
        self.assertFalse(escort_required(perimeter(), visitor()))

    def test_staff_never_need_an_escort(self):
        self.assertFalse(escort_required(zone(), staff()))


class TestEvaluateAccess(unittest.TestCase):
    def test_qualified_staff_are_granted(self):
        result = evaluate_access(zone(), staff(), DAY, NOON)
        self.assertEqual(result["decision"], DECISION_GRANTED)
        self.assertEqual(result["reasons"], [])

    def test_low_tier_is_denied_with_that_reason(self):
        result = evaluate_access(zone(), staff(tier=2), DAY, NOON)
        self.assertEqual(result["decision"], DECISION_DENIED)
        self.assertIn(REASON_TIER_TOO_LOW, result["reasons"])

    def test_expired_badge_is_denied(self):
        result = evaluate_access(
            zone(), staff(badge_valid_until_day=DAY - 1), DAY, NOON
        )
        self.assertIn(REASON_BADGE_EXPIRED, result["reasons"])

    def test_out_of_hours_request_is_denied(self):
        result = evaluate_access(zone(), staff(), DAY, 2 * 60)
        self.assertIn(REASON_OUTSIDE_HOURS, result["reasons"])

    def test_unescorted_visitor_is_denied(self):
        result = evaluate_access(zone(), visitor(), DAY, NOON)
        self.assertIn(REASON_NO_ESCORT, result["reasons"])

    def test_escorted_visitor_is_granted(self):
        result = evaluate_access(zone(), visitor(), DAY, NOON, escort=staff())
        self.assertEqual(result["decision"], DECISION_GRANTED)

    def test_escort_below_the_zone_tier_is_denied(self):
        result = evaluate_access(
            zone(), visitor(), DAY, NOON, escort=staff("S-2", tier=1)
        )
        self.assertIn(REASON_ESCORT_TIER_TOO_LOW, result["reasons"])

    def test_escort_with_an_expired_badge_is_denied(self):
        escort = staff("S-3", badge_valid_until_day=DAY - 5)
        result = evaluate_access(zone(), visitor(), DAY, NOON, escort=escort)
        self.assertIn(REASON_ESCORT_BADGE_EXPIRED, result["reasons"])

    def test_every_failing_reason_is_reported_not_just_the_first(self):
        person = visitor(badge_valid_until_day=DAY - 1)
        result = evaluate_access(zone(), person, DAY, 2 * 60)
        self.assertEqual(
            sorted(result["reasons"]),
            sorted(
                [
                    REASON_BADGE_EXPIRED,
                    REASON_OUTSIDE_HOURS,
                    REASON_NO_ESCORT,
                ]
            ),
        )

    def test_a_missing_escort_is_not_also_reported_as_a_low_tier(self):
        result = evaluate_access(zone(), visitor(), DAY, NOON)
        self.assertIn(REASON_NO_ESCORT, result["reasons"])
        self.assertNotIn(REASON_TIER_TOO_LOW, result["reasons"])

    def test_the_escort_is_the_admitting_party_for_a_visitor(self):
        result = evaluate_access(zone(), visitor(), DAY, NOON, escort=staff())
        self.assertEqual(result["admitting_party"], "escort")

    def test_staff_admit_themselves(self):
        result = evaluate_access(zone(), staff(), DAY, NOON)
        self.assertEqual(result["admitting_party"], "person")

    def test_an_unescorted_low_tier_person_is_denied_on_their_own_tier(self):
        result = evaluate_access(perimeter(), visitor(), DAY, NOON)
        self.assertIn(REASON_TIER_TOO_LOW, result["reasons"])


class TestVisitLog(unittest.TestCase):
    def test_a_closed_visit_is_not_open(self):
        self.assertEqual(open_visits([visit()]), [])

    def test_a_visit_without_a_sign_out_is_open(self):
        self.assertEqual(
            open_visits([visit("VS-2", signed_out_minute=None)]), ["VS-2"]
        )

    def test_duplicate_visit_id_raises(self):
        with self.assertRaises(ValueError):
            open_visits([visit("VS-1"), visit("VS-1")])

    def test_non_list_log_raises(self):
        with self.assertRaises(ValueError):
            open_visits(visit())

    def test_occupancy_counts_people_inside_at_the_minute(self):
        log = [visit("VS-1"), visit("VS-2", person="V-2")]
        self.assertEqual(zone_occupancy(log, NOON), {"Z-CHAMBER": ["V-1", "V-2"]})

    def test_occupancy_excludes_a_visit_that_has_signed_out(self):
        self.assertEqual(zone_occupancy([visit()], 18 * 60), {})

    def test_occupancy_excludes_a_visit_that_has_not_started(self):
        self.assertEqual(zone_occupancy([visit()], 8 * 60), {})

    def test_an_open_visit_still_occupies_the_zone(self):
        log = [visit("VS-3", signed_out_minute=None)]
        self.assertEqual(zone_occupancy(log, 23 * 60), {"Z-CHAMBER": ["V-1"]})


class TestHoldings(unittest.TestCase):
    def test_an_item_in_a_high_enough_zone_is_clean(self):
        holdings = [{"id": "IT-1", "sensitivity_tier": 3,
                     "held_in_zone": "Z-CHAMBER"}]
        self.assertEqual(holding_findings(holdings, [zone()], "item"), [])

    def test_an_item_left_in_a_low_zone_is_flagged(self):
        holdings = [{"id": "IT-1", "sensitivity_tier": 3, "held_in_zone": "Z-GATE"}]
        out = holding_findings(holdings, [zone(), perimeter()], "item")
        self.assertEqual(out[0]["finding"], FINDING_ITEM_UNDER_PROTECTED)

    def test_data_uses_its_own_finding_token(self):
        holdings = [{"id": "DR-1", "sensitivity_tier": 4, "held_in_zone": "Z-GATE"}]
        out = holding_findings(holdings, [zone(), perimeter()], "data")
        self.assertEqual(out[0]["finding"], FINDING_DATA_UNDER_PROTECTED)

    def test_a_holding_in_an_undeclared_zone_is_flagged(self):
        holdings = [{"id": "IT-2", "sensitivity_tier": 2, "held_in_zone": "Z-ATTIC"}]
        out = holding_findings(holdings, [zone()], "item")
        self.assertEqual(out[0]["finding"], FINDING_UNKNOWN_ZONE)

    def test_duplicate_zone_declaration_raises(self):
        with self.assertRaises(ValueError):
            holding_findings([], [zone(), zone()], "item")


class TestAssessSite(unittest.TestCase):
    def test_a_clean_site_is_secure(self):
        report = assess_site_security(
            zones=[zone(), perimeter()],
            requests=[{"zone": "Z-CHAMBER", "person": staff()}],
            visit_log=[visit()],
            items=[{"id": "IT-1", "sensitivity_tier": 3,
                    "held_in_zone": "Z-CHAMBER"}],
            data=[{"id": "DR-1", "sensitivity_tier": 2,
                   "held_in_zone": "Z-CHAMBER"}],
            as_of_day=DAY,
            minute_of_day=NOON,
        )
        self.assertTrue(report["secure"])
        self.assertEqual(report["denied_requests"], [])

    def test_a_denied_request_makes_the_site_not_secure(self):
        report = assess_site_security(
            zones=[zone()],
            requests=[{"zone": "Z-CHAMBER", "person": visitor()}],
            visit_log=[],
            items=[],
            data=[],
            as_of_day=DAY,
            minute_of_day=NOON,
        )
        self.assertFalse(report["secure"])
        self.assertEqual(len(report["denied_requests"]), 1)

    def test_an_open_visit_becomes_a_site_finding(self):
        report = assess_site_security(
            zones=[zone()],
            requests=[],
            visit_log=[visit("VS-9", signed_out_minute=None)],
            items=[],
            data=[],
            as_of_day=DAY,
            minute_of_day=NOON,
        )
        self.assertEqual(report["open_visit_ids"], ["VS-9"])
        self.assertIn(
            FINDING_OPEN_VISIT, [f["finding"] for f in report["findings"]]
        )

    def test_a_request_against_an_undeclared_zone_raises(self):
        with self.assertRaises(ValueError):
            assess_site_security(
                zones=[zone()],
                requests=[{"zone": "Z-ATTIC", "person": staff()}],
                visit_log=[],
                items=[],
                data=[],
                as_of_day=DAY,
                minute_of_day=NOON,
            )

    def test_an_empty_zone_list_raises(self):
        with self.assertRaises(ValueError):
            assess_site_security(
                zones=[],
                requests=[],
                visit_log=[],
                items=[],
                data=[],
                as_of_day=DAY,
                minute_of_day=NOON,
            )

    def test_a_non_mapping_request_raises(self):
        with self.assertRaises(ValueError):
            assess_site_security(
                zones=[zone()],
                requests=["Z-CHAMBER"],
                visit_log=[],
                items=[],
                data=[],
                as_of_day=DAY,
                minute_of_day=NOON,
            )


if __name__ == "__main__":
    unittest.main()
