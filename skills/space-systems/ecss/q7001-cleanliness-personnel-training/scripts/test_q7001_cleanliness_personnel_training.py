#!/usr/bin/env python3
"""Contract test for contamination-control training and access (offline)."""

import copy
import datetime
import unittest

from q7001_cleanliness_personnel_training_logic import (
    ACCESS_ESCORTED,
    ACCESS_GRANTED,
    ACCESS_REFUSED,
    MODULE_AWARENESS,
    MODULE_BEHAVIOUR,
    MODULE_GARMENTING,
    MODULE_MATERIALS,
    MODULE_MEASUREMENT,
    MODULE_PACKAGING,
    MODULE_SUPERVISION,
    MODULE_VALIDITY_MONTHS,
    ROLES,
    ROLE_CURRICULUM,
    ROLE_INSPECTOR,
    ROLE_OPERATOR,
    ROLE_SUPERVISOR,
    ROLE_VISITOR,
    ZONES,
    ZONE_ESCORT_RATIO,
    ZONE_ISO5,
    ZONE_ISO7,
    ZONE_ISO8,
    ZONE_UNCONTROLLED,
    add_months,
    assess_cleanroom_access,
    escort_ratio,
    module_status,
    parse_date,
    required_modules,
    training_state,
)

AS_OF = "2026-09-19"

RECORDS = [
    {"module": MODULE_AWARENESS, "completed": "2026-01-10"},
    {"module": MODULE_GARMENTING, "completed": "2026-02-01"},
    {"module": MODULE_BEHAVIOUR, "completed": "2026-02-01"},
    {"module": MODULE_MATERIALS, "completed": "2026-01-10"},
    {"module": MODULE_PACKAGING, "completed": "2026-01-10"},
]

CASE = {
    "person": "tech-0271",
    "role": ROLE_OPERATOR,
    "zone": ZONE_ISO7,
    "hands_on_hardware": True,
    "as_of": AS_OF,
    "records": RECORDS,
}


def _case(**overrides):
    case = copy.deepcopy(CASE)
    case.update(overrides)
    return case


def _records(drop=None, **dates):
    rows = [copy.deepcopy(r) for r in RECORDS]
    if drop:
        rows = [r for r in rows if r["module"] != drop]
    for row in rows:
        if row["module"] in dates:
            row["completed"] = dates[row["module"]]
    return rows


class CalendarTests(unittest.TestCase):
    def test_iso_date_parses(self):
        self.assertEqual(parse_date("as_of", AS_OF), datetime.date(2026, 9, 19))

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("as_of", "19 Sept 2026")

    def test_validity_runs_in_whole_months(self):
        self.assertEqual(add_months(datetime.date(2026, 2, 1), 12), datetime.date(2027, 2, 1))

    def test_month_end_is_clamped_not_overflowed(self):
        self.assertEqual(add_months(datetime.date(2026, 8, 31), 6), datetime.date(2027, 2, 28))

    def test_negative_validity_rejected(self):
        with self.assertRaises(ValueError):
            add_months(datetime.date(2026, 2, 1), -12)


class CurriculumTests(unittest.TestCase):
    def test_every_role_has_a_curriculum(self):
        for role in ROLES:
            self.assertTrue(ROLE_CURRICULUM[role])

    def test_every_curriculum_module_is_in_the_catalogue(self):
        for role in ROLES:
            for module in ROLE_CURRICULUM[role]:
                self.assertIn(module, MODULE_VALIDITY_MONTHS)

    def test_awareness_is_owed_by_every_role(self):
        for role in ROLES:
            self.assertIn(MODULE_AWARENESS, required_modules(role, ZONE_UNCONTROLLED))

    def test_a_tighter_zone_demands_more_than_a_looser_one(self):
        loose = set(required_modules(ROLE_OPERATOR, ZONE_ISO8))
        tight = set(required_modules(ROLE_OPERATOR, ZONE_ISO5))
        self.assertTrue(loose.issubset(tight))
        self.assertLess(len(loose), len(tight))

    def test_the_zone_adds_garmenting_to_a_visitor(self):
        self.assertIn(MODULE_GARMENTING, required_modules(ROLE_VISITOR, ZONE_ISO7))

    def test_an_uncontrolled_zone_adds_nothing(self):
        self.assertEqual(
            required_modules(ROLE_INSPECTOR, ZONE_UNCONTROLLED),
            ROLE_CURRICULUM[ROLE_INSPECTOR],
        )

    def test_the_role_still_shapes_the_curriculum_inside_one_zone(self):
        self.assertNotEqual(
            set(required_modules(ROLE_VISITOR, ZONE_ISO5)),
            set(required_modules(ROLE_SUPERVISOR, ZONE_ISO5)),
        )

    def test_a_supervisor_owes_the_supervision_module(self):
        self.assertIn(MODULE_SUPERVISION, required_modules(ROLE_SUPERVISOR, ZONE_ISO7))

    def test_a_module_owed_by_both_role_and_zone_is_listed_once(self):
        modules = required_modules(ROLE_OPERATOR, ZONE_ISO5)
        self.assertEqual(modules.count(MODULE_MATERIALS), 1)

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            required_modules("intern", ZONE_ISO7)

    def test_unknown_zone_rejected(self):
        with self.assertRaises(ValueError):
            required_modules(ROLE_OPERATOR, "iso3-cleanroom")


class CurrencyTests(unittest.TestCase):
    def test_garmenting_lapses_sooner_than_awareness(self):
        self.assertLess(
            MODULE_VALIDITY_MONTHS[MODULE_GARMENTING],
            MODULE_VALIDITY_MONTHS[MODULE_AWARENESS],
        )

    def test_expiry_follows_the_module_validity(self):
        status = module_status({"module": MODULE_GARMENTING, "completed": "2026-02-01"}, AS_OF)
        self.assertEqual(status["expires"], "2027-02-01")
        self.assertTrue(status["current"])

    def test_a_module_expiring_today_is_still_current(self):
        status = module_status(
            {"module": MODULE_GARMENTING, "completed": "2025-09-19"}, AS_OF
        )
        self.assertEqual(status["expires"], AS_OF)
        self.assertTrue(status["current"])
        self.assertEqual(status["days_remaining"], 0)

    def test_a_module_that_expired_yesterday_is_not_current(self):
        status = module_status(
            {"module": MODULE_GARMENTING, "completed": "2025-09-18"}, AS_OF
        )
        self.assertFalse(status["current"])
        self.assertEqual(status["days_remaining"], -1)

    def test_a_record_with_no_completion_date_rejected(self):
        with self.assertRaises(ValueError):
            module_status({"module": MODULE_GARMENTING}, AS_OF)

    def test_a_module_outside_the_catalogue_rejected(self):
        with self.assertRaises(ValueError):
            module_status({"module": "coffee-etiquette", "completed": "2026-01-10"}, AS_OF)

    def test_a_completion_date_in_the_future_rejected(self):
        with self.assertRaises(ValueError):
            module_status({"module": MODULE_GARMENTING, "completed": "2027-01-10"}, AS_OF)


class TrainingStateTests(unittest.TestCase):
    def test_a_full_set_is_complete(self):
        state = training_state(RECORDS, ROLE_OPERATOR, ZONE_ISO7, AS_OF)
        self.assertTrue(state["complete"])
        self.assertEqual(state["expired"], ())
        self.assertEqual(state["never_taken"], ())

    def test_expired_and_never_taken_are_kept_apart(self):
        rows = _records(drop=MODULE_PACKAGING, **{MODULE_GARMENTING: "2025-01-10"})
        state = training_state(rows, ROLE_OPERATOR, ZONE_ISO7, AS_OF)
        self.assertEqual(state["expired"], (MODULE_GARMENTING,))
        self.assertEqual(state["never_taken"], (MODULE_PACKAGING,))

    def test_a_module_not_required_does_not_make_the_set_complete(self):
        rows = _records(drop=MODULE_BEHAVIOUR)
        rows.append({"module": MODULE_MEASUREMENT, "completed": "2026-01-10"})
        state = training_state(rows, ROLE_OPERATOR, ZONE_ISO7, AS_OF)
        self.assertFalse(state["complete"])
        self.assertIn(MODULE_BEHAVIOUR, state["never_taken"])

    def test_the_earliest_expiry_is_reported(self):
        state = training_state(RECORDS, ROLE_OPERATOR, ZONE_ISO7, AS_OF)
        self.assertEqual(state["next_expiry_module"], MODULE_GARMENTING)
        self.assertEqual(state["next_expiry_date"], "2027-02-01")

    def test_the_days_to_the_next_expiry_are_reported(self):
        state = training_state(RECORDS, ROLE_OPERATOR, ZONE_ISO7, AS_OF)
        self.assertEqual(state["next_expiry_days"], 135)

    def test_duplicate_training_record_rejected(self):
        rows = _records() + [{"module": MODULE_AWARENESS, "completed": "2026-03-10"}]
        with self.assertRaises(ValueError):
            training_state(rows, ROLE_OPERATOR, ZONE_ISO7, AS_OF)

    def test_records_must_be_a_list(self):
        with self.assertRaises(ValueError):
            training_state({"module": MODULE_AWARENESS}, ROLE_OPERATOR, ZONE_ISO7, AS_OF)

    def test_no_records_leaves_everything_never_taken(self):
        state = training_state(None, ROLE_OPERATOR, ZONE_ISO7, AS_OF)
        self.assertEqual(len(state["never_taken"]), len(state["required"]))
        self.assertIsNone(state["next_expiry_date"])


class EscortTests(unittest.TestCase):
    def test_a_tighter_zone_allows_fewer_people_per_escort(self):
        self.assertLess(escort_ratio(ZONE_ISO5), escort_ratio(ZONE_ISO8))

    def test_every_controlled_zone_declares_a_ratio(self):
        for zone in ZONES:
            if zone == ZONE_UNCONTROLLED:
                continue
            self.assertIn(zone, ZONE_ESCORT_RATIO)

    def test_an_uncontrolled_zone_needs_no_escort(self):
        self.assertIsNone(escort_ratio(ZONE_UNCONTROLLED))

    def test_unknown_zone_has_no_ratio(self):
        with self.assertRaises(ValueError):
            escort_ratio("iso3-cleanroom")


class AccessDecisionTests(unittest.TestCase):
    def test_a_fully_trained_operator_is_granted_access(self):
        result = assess_cleanroom_access(CASE)
        self.assertEqual(result["decision"], ACCESS_GRANTED)
        self.assertTrue(result["may_enter"])
        self.assertIsNone(result["escort_ratio"])

    def test_the_refresher_is_reported_alongside_the_grant(self):
        result = assess_cleanroom_access(CASE)
        self.assertEqual(result["refresher_module"], MODULE_GARMENTING)
        self.assertEqual(result["refresher_due"], "2027-02-01")

    def test_a_hands_on_operation_refuses_an_incomplete_set(self):
        result = assess_cleanroom_access(_case(records=_records(drop=MODULE_BEHAVIOUR)))
        self.assertEqual(result["decision"], ACCESS_REFUSED)
        self.assertFalse(result["may_enter"])
        self.assertTrue(any("hands on flight hardware" in r for r in result["reasons"]))

    def test_an_observer_with_current_awareness_may_be_escorted(self):
        result = assess_cleanroom_access(
            _case(
                role=ROLE_VISITOR,
                hands_on_hardware=False,
                records=[{"module": MODULE_AWARENESS, "completed": "2026-01-10"}],
            )
        )
        self.assertEqual(result["decision"], ACCESS_ESCORTED)
        self.assertEqual(result["escort_ratio"], ZONE_ESCORT_RATIO[ZONE_ISO7])

    def test_an_observer_without_current_awareness_is_refused(self):
        result = assess_cleanroom_access(
            _case(
                role=ROLE_VISITOR,
                hands_on_hardware=False,
                records=[{"module": MODULE_AWARENESS, "completed": "2024-01-10"}],
            )
        )
        self.assertEqual(result["decision"], ACCESS_REFUSED)
        self.assertTrue(any("not current" in r for r in result["reasons"]))

    def test_an_expired_module_is_named_with_its_lapse_date(self):
        rows = _records(**{MODULE_GARMENTING: "2025-01-10"})
        result = assess_cleanroom_access(_case(records=rows))
        self.assertTrue(
            any(MODULE_GARMENTING in r and "lapsed" in r for r in result["reasons"])
        )

    def test_a_missing_module_is_named_as_never_taken(self):
        result = assess_cleanroom_access(_case(records=_records(drop=MODULE_PACKAGING)))
        self.assertTrue(
            any(MODULE_PACKAGING in r and "never" in r for r in result["reasons"])
        )

    def test_the_same_records_can_pass_one_zone_and_fail_a_tighter_one(self):
        rows = _records(drop=MODULE_MATERIALS)
        looser = assess_cleanroom_access(_case(zone=ZONE_ISO8, records=_records()))
        tighter = assess_cleanroom_access(_case(zone=ZONE_ISO5, records=rows))
        self.assertEqual(looser["decision"], ACCESS_GRANTED)
        self.assertEqual(tighter["decision"], ACCESS_REFUSED)

    def test_an_uncontrolled_zone_offers_no_escort_route(self):
        result = assess_cleanroom_access(
            _case(
                zone=ZONE_UNCONTROLLED,
                role=ROLE_INSPECTOR,
                hands_on_hardware=False,
                records=[{"module": MODULE_AWARENESS, "completed": "2026-01-10"}],
            )
        )
        self.assertEqual(result["decision"], ACCESS_REFUSED)

    def test_non_boolean_hands_on_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_cleanroom_access(_case(hands_on_hardware="yes"))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_cleanroom_access("tech-0271")

    def test_missing_person_rejected(self):
        case = _case()
        del case["person"]
        with self.assertRaises(ValueError):
            assess_cleanroom_access(case)

    def test_missing_role_rejected(self):
        case = _case()
        del case["role"]
        with self.assertRaises(ValueError):
            assess_cleanroom_access(case)


if __name__ == "__main__":
    unittest.main()
