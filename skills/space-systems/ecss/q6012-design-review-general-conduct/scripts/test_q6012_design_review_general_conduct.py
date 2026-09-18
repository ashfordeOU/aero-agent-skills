#!/usr/bin/env python3
"""Contract tests for the clause 7.3.1 design-review conduct logic."""

import unittest

from q6012_design_review_general_conduct_logic import (
    DEFAULT_RESPONSE_DAYS,
    RATIO_TOLERANCE,
    SEVERITY_WEIGHTS,
    VALID_DISPOSITIONS,
    assess_review_conduct,
    chair_independence,
    closure_ratio,
    finding_age_days,
    normalise_register,
    normalise_roster,
    notice_lead_days,
    open_severity_load,
    overdue_findings,
    quorum_status,
    validate_attendee,
    validate_finding,
)

MANDATORY_ROLES = ("chair", "rf-design-lead", "product-assurance", "foundry-interface")


def roster(**patch):
    base = [
        {"role": "chair", "person": "independent-reviewer", "chair": True},
        {"role": "rf-design-lead", "person": "circuit-designer", "design_team": True},
        {"role": "product-assurance", "person": "pa-engineer"},
        {"role": "foundry-interface", "person": "process-engineer"},
    ]
    by_role = {entry["role"]: entry for entry in base}
    for role, changes in patch.items():
        by_role[role.replace("_", "-")].update(changes)
    return list(by_role.values())


def register(**patch):
    base = [
        {"id": "f1", "severity": "major", "raised_day": 40, "closed_day": 50,
         "disposition": "reworked"},
        {"id": "f2", "severity": "minor", "raised_day": 40, "closed_day": 44,
         "disposition": "accepted"},
        {"id": "f3", "severity": "observation", "raised_day": 40,
         "closed_day": 41, "disposition": "withdrawn"},
        {"id": "f4", "severity": "minor", "raised_day": 40, "closed_day": 60,
         "disposition": "superseded"},
    ]
    by_id = {entry["id"]: entry for entry in base}
    for ident, changes in patch.items():
        by_id[ident].update(changes)
    return list(by_id.values())


def spec(**kwargs):
    payload = {
        "notice_day": 26,
        "review_day": 40,
        "required_notice_days": 10,
        "roster": roster(),
        "mandatory_roles": MANDATORY_ROLES,
        "findings": register(),
        "as_of_day": 70,
        "required_closure_ratio": 1.0,
    }
    payload.update(kwargs)
    return payload


class NoticeTests(unittest.TestCase):
    def test_lead_is_the_day_difference(self):
        self.assertEqual(notice_lead_days(26, 40), 14)

    def test_same_day_notice_gives_zero_lead(self):
        self.assertEqual(notice_lead_days(40, 40), 0)

    def test_notice_after_the_review_rejected(self):
        with self.assertRaises(ValueError):
            notice_lead_days(41, 40)

    def test_boolean_day_rejected(self):
        with self.assertRaises(ValueError):
            notice_lead_days(True, 40)

    def test_negative_day_rejected(self):
        with self.assertRaises(ValueError):
            notice_lead_days(-1, 40)


class RosterTests(unittest.TestCase):
    def test_attendee_defaults_person_to_role(self):
        record = validate_attendee({"role": "product-assurance"})
        self.assertEqual(record["person"], "product-assurance")
        self.assertFalse(record["design_team"])

    def test_blank_role_rejected(self):
        with self.assertRaises(ValueError):
            validate_attendee({"role": "   "})

    def test_non_boolean_design_team_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_attendee({"role": "chair", "design_team": "no"})

    def test_empty_roster_rejected(self):
        with self.assertRaises(ValueError):
            normalise_roster([])

    def test_two_chairs_rejected(self):
        entries = roster(product_assurance={"chair": True})
        with self.assertRaises(ValueError):
            normalise_roster(entries)

    def test_quorum_satisfied_by_a_full_roster(self):
        status = quorum_status(normalise_roster(roster()), MANDATORY_ROLES)
        self.assertTrue(status["satisfied"])
        self.assertEqual(status["missing_roles"], [])

    def test_quorum_names_the_absent_role(self):
        entries = [e for e in roster() if e["role"] != "foundry-interface"]
        status = quorum_status(normalise_roster(entries), MANDATORY_ROLES)
        self.assertEqual(status["missing_roles"], ["foundry-interface"])
        self.assertFalse(status["satisfied"])

    def test_empty_mandatory_role_list_rejected(self):
        with self.assertRaises(ValueError):
            quorum_status(normalise_roster(roster()), [])

    def test_independent_chair_recognised(self):
        chair = chair_independence(normalise_roster(roster()))
        self.assertTrue(chair["independent"])
        self.assertEqual(chair["chair_role"], "chair")

    def test_designer_chairing_is_not_independent(self):
        entries = roster(chair={"design_team": True})
        self.assertFalse(chair_independence(normalise_roster(entries))["independent"])

    def test_unchaired_roster_rejected(self):
        entries = roster(chair={"chair": False})
        with self.assertRaises(ValueError):
            chair_independence(normalise_roster(entries))


class FindingRegisterTests(unittest.TestCase):
    def test_open_entry_has_no_closure_day(self):
        record = validate_finding({"id": "f9", "severity": "minor", "raised_day": 40})
        self.assertFalse(record["closed"])
        self.assertIsNone(record["closed_day"])

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            validate_finding({"id": "f9", "severity": "showstopper", "raised_day": 40})

    def test_closure_before_the_raise_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_finding({"id": "f9", "severity": "minor", "raised_day": 40,
                              "closed_day": 39, "disposition": "accepted"})

    def test_closure_without_a_disposition_rejected(self):
        with self.assertRaises(ValueError):
            validate_finding({"id": "f9", "severity": "minor", "raised_day": 40,
                              "closed_day": 45})

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            validate_finding({"id": "f9", "severity": "minor", "raised_day": 40,
                              "closed_day": 45, "disposition": "ignored"})

    def test_disposition_without_a_closure_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_finding({"id": "f9", "severity": "minor", "raised_day": 40,
                              "disposition": "accepted"})

    def test_same_day_closure_allowed(self):
        record = validate_finding({"id": "f9", "severity": "observation",
                                   "raised_day": 40, "closed_day": 40,
                                   "disposition": "withdrawn"})
        self.assertTrue(record["closed"])

    def test_duplicate_finding_id_rejected(self):
        entries = register()
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            normalise_register(entries)

    def test_absent_register_is_empty_not_an_error(self):
        self.assertEqual(normalise_register(None), [])

    def test_every_valid_disposition_is_accepted(self):
        for i, disposition in enumerate(VALID_DISPOSITIONS):
            record = validate_finding({"id": "d%d" % i, "severity": "minor",
                                       "raised_day": 1, "closed_day": 2,
                                       "disposition": disposition})
            self.assertTrue(record["closed"])


class AgeingTests(unittest.TestCase):
    def test_closed_finding_age_is_its_turnaround(self):
        record = validate_finding({"id": "f1", "severity": "major", "raised_day": 40,
                                   "closed_day": 50, "disposition": "reworked"})
        self.assertEqual(finding_age_days(record, 200), 10)

    def test_open_finding_age_runs_to_the_as_of_day(self):
        record = validate_finding({"id": "f9", "severity": "minor", "raised_day": 40})
        self.assertEqual(finding_age_days(record, 70), 30)

    def test_as_of_before_the_raise_day_rejected(self):
        record = validate_finding({"id": "f9", "severity": "minor", "raised_day": 40})
        with self.assertRaises(ValueError):
            finding_age_days(record, 30)

    def test_closure_ratio_of_a_closed_register_is_one(self):
        self.assertAlmostEqual(closure_ratio(normalise_register(register())), 1.0,
                               places=9)

    def test_closure_ratio_counts_open_entries(self):
        entries = register(f4={"closed_day": None, "disposition": None})
        self.assertAlmostEqual(closure_ratio(normalise_register(entries)), 0.75,
                               places=9)

    def test_empty_register_closure_ratio_is_one(self):
        self.assertAlmostEqual(closure_ratio([]), 1.0, places=9)

    def test_open_load_is_severity_weighted(self):
        entries = register(f1={"closed_day": None, "disposition": None},
                           f2={"closed_day": None, "disposition": None})
        load = open_severity_load(normalise_register(entries))
        self.assertAlmostEqual(
            load, SEVERITY_WEIGHTS["major"] + SEVERITY_WEIGHTS["minor"], places=9
        )

    def test_closed_register_has_no_open_load(self):
        self.assertAlmostEqual(open_severity_load(normalise_register(register())),
                               0.0, places=9)

    def test_open_major_past_its_response_time_is_overdue(self):
        entries = register(f1={"closed_day": None, "disposition": None})
        overdue = overdue_findings(normalise_register(entries), 40 + DEFAULT_RESPONSE_DAYS["major"] + 1)
        self.assertEqual(overdue, ["f1"])

    def test_open_major_exactly_on_its_response_time_is_not_overdue(self):
        entries = register(f1={"closed_day": None, "disposition": None})
        overdue = overdue_findings(normalise_register(entries), 40 + DEFAULT_RESPONSE_DAYS["major"])
        self.assertEqual(overdue, [])

    def test_response_day_override_applies(self):
        entries = register(f2={"closed_day": None, "disposition": None})
        overdue = overdue_findings(normalise_register(entries), 45, {"minor": 2})
        self.assertEqual(overdue, ["f2"])

    def test_unknown_severity_in_override_rejected(self):
        with self.assertRaises(ValueError):
            overdue_findings(normalise_register(register()), 70, {"blocker": 1})


class AssessReviewConductTests(unittest.TestCase):
    def test_clean_review_has_no_findings(self):
        result = assess_review_conduct(spec())
        self.assertTrue(result["conducted_properly"])
        self.assertTrue(result["closed_out"])
        self.assertEqual(result["findings"], [])

    def test_short_notice_is_reported(self):
        result = assess_review_conduct(spec(notice_day=38))
        self.assertFalse(result["notice_met"])
        self.assertFalse(result["conducted_properly"])
        self.assertTrue(any("notice" in f for f in result["findings"]))

    def test_notice_exactly_at_the_required_minimum_passes(self):
        result = assess_review_conduct(spec(notice_day=30))
        self.assertEqual(result["notice_lead_days"], 10)
        self.assertTrue(result["notice_met"])

    def test_missing_quorum_role_is_reported(self):
        entries = [e for e in roster() if e["role"] != "product-assurance"]
        result = assess_review_conduct(spec(roster=entries))
        self.assertFalse(result["conducted_properly"])
        self.assertTrue(any("quorum" in f for f in result["findings"]))

    def test_designer_chair_is_reported(self):
        result = assess_review_conduct(spec(roster=roster(chair={"design_team": True})))
        self.assertFalse(result["conducted_properly"])
        self.assertTrue(any("design team" in f for f in result["findings"]))

    def test_open_finding_blocks_close_out(self):
        entries = register(f4={"closed_day": None, "disposition": None})
        result = assess_review_conduct(spec(findings=entries))
        self.assertFalse(result["closed_out"])
        self.assertTrue(result["conducted_properly"])

    def test_closure_ratio_exactly_at_the_required_value_passes(self):
        entries = register(f4={"closed_day": None, "disposition": None})
        result = assess_review_conduct(
            spec(findings=entries, required_closure_ratio=0.75, as_of_day=45)
        )
        self.assertAlmostEqual(
            result["closure_ratio"], result["required_closure_ratio"], places=9
        )
        self.assertTrue(result["closure_ratio_met"])

    def test_required_ratio_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_review_conduct(spec(required_closure_ratio=1.2))

    def test_missing_spec_key_rejected(self):
        payload = spec()
        del payload["roster"]
        with self.assertRaises(ValueError):
            assess_review_conduct(payload)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_review_conduct(["roster"])

    def test_register_absent_is_treated_as_closed_out(self):
        payload = spec()
        del payload["findings"]
        result = assess_review_conduct(payload)
        self.assertTrue(result["closed_out"])
        self.assertAlmostEqual(result["closure_ratio"], 1.0, places=9)

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(RATIO_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
