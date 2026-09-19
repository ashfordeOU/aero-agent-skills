"""Contract test for the crimping records leaf (stdlib unittest)."""

import datetime
import unittest

from q7026_crimp_records_logic import (
    COMPLETE,
    DOSSIER_ACCEPTED,
    DOSSIER_ACCEPTED_WITH_FINDINGS,
    DOSSIER_REJECTED,
    INCOMPLETE,
    RETAINED,
    RETENTION_ELAPSED,
    UNTRACEABLE,
    add_years,
    audit_dossier,
    audit_record,
    missing_fields,
    pull_test_cadence,
    resolve_references,
    retention_state,
    validate_policy,
    validate_record,
    validate_registers,
)

AS_OF = "2026-09-19"


def policy(**kw):
    p = {"pull_test_every_n_terminations": 50, "retention_years": 10}
    p.update(kw)
    return p


def registers(**kw):
    r = {
        "tools": [{"tool_id": "CT-0114"}, {"tool_id": "CT-0208"}],
        "operators": [
            {
                "operator_id": "OP-0072",
                "certified_from": "2026-03-02",
                "certified_until": "2028-03-01",
            },
            {
                "operator_id": "OP-0099",
                "certified_from": "2026-07-01",
                "certified_until": "2028-06-30",
            },
            {
                "operator_id": "OP-0050",
                "certified_from": "2009-01-05",
                "certified_until": "2030-01-04",
            },
        ],
        "lots": [
            {"lot_id": "CL-5521", "receiving_accepted": True},
            {"lot_id": "WL-3390", "receiving_accepted": True},
            {"lot_id": "WL-4001", "receiving_accepted": False},
        ],
    }
    r.update(kw)
    return r


def record(**kw):
    e = {
        "record_id": "CR-0001",
        "crimp_date": "2026-08-12",
        "tool_id": "CT-0114",
        "operator_id": "OP-0072",
        "contact_lot": "CL-5521",
        "wire_lot": "WL-3390",
        "terminations_made": 40,
        "pull_test_reference": "PT-0001",
    }
    e.update(kw)
    return e


class TestPolicyAndRegisterValidation(unittest.TestCase):
    def test_a_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_policy("ten years")

    def test_a_zero_pull_test_interval_raises(self):
        with self.assertRaises(ValueError):
            validate_policy(policy(pull_test_every_n_terminations=0))

    def test_a_zero_retention_period_raises(self):
        with self.assertRaises(ValueError):
            validate_policy(policy(retention_years=0))

    def test_a_non_mapping_register_set_raises(self):
        with self.assertRaises(ValueError):
            validate_registers("the shop database")

    def test_an_empty_tool_register_raises(self):
        with self.assertRaises(ValueError):
            validate_registers(registers(tools=[]))

    def test_an_inverted_operator_certification_window_raises(self):
        with self.assertRaises(ValueError):
            validate_registers(
                registers(
                    operators=[
                        {
                            "operator_id": "OP-0072",
                            "certified_from": "2028-03-01",
                            "certified_until": "2026-03-02",
                        }
                    ]
                )
            )

    def test_a_lot_without_a_receiving_verdict_raises(self):
        with self.assertRaises(ValueError):
            validate_registers(
                registers(lots=[{"lot_id": "CL-5521", "receiving_accepted": "yes"}])
            )


class TestRecordValidation(unittest.TestCase):
    def test_a_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            validate_record(["CR-0001"])

    def test_a_non_iso_crimp_date_raises(self):
        with self.assertRaises(ValueError):
            validate_record(record(crimp_date="last Tuesday"))

    def test_a_zero_termination_count_raises(self):
        with self.assertRaises(ValueError):
            validate_record(record(terminations_made=0))

    def test_identifiers_are_folded_to_upper_case(self):
        checked = validate_record(record(tool_id="ct-0114"))
        self.assertEqual(checked["tool_id"], "CT-0114")

    def test_an_absent_pull_test_reference_is_kept_as_unknown(self):
        checked = validate_record(record(pull_test_reference=None))
        self.assertIsNone(checked["pull_test_reference"])


class TestMandatoryFields(unittest.TestCase):
    def test_a_full_record_is_missing_nothing(self):
        self.assertEqual(missing_fields(record()), [])

    def test_an_absent_field_is_reported(self):
        entry = record()
        del entry["operator_id"]
        self.assertIn("operator_id", missing_fields(entry))

    def test_a_blank_field_counts_as_absent(self):
        self.assertIn("wire_lot", missing_fields(record(wire_lot="   ")))

    def test_an_incomplete_record_is_not_audited_for_traceability(self):
        entry = record()
        del entry["tool_id"]
        result = audit_record(entry, registers(), policy(), AS_OF)
        self.assertEqual(result["disposition"], INCOMPLETE)
        self.assertEqual(result["unresolved"], [])


class TestReferenceResolution(unittest.TestCase):
    def test_a_fully_resolvable_record_is_traceable(self):
        self.assertTrue(resolve_references(record(), registers())["traceable"])

    def test_an_unknown_tool_identifier_does_not_resolve(self):
        result = resolve_references(record(tool_id="CT-9999"), registers())
        self.assertIn(
            "tool-identifier-not-in-the-calibration-register", result["unresolved"]
        )

    def test_an_unknown_operator_identifier_does_not_resolve(self):
        result = resolve_references(record(operator_id="OP-1234"), registers())
        self.assertIn(
            "operator-identifier-not-in-the-personnel-register",
            result["unresolved"],
        )

    def test_certification_is_judged_on_the_date_of_the_crimp(self):
        result = resolve_references(
            record(operator_id="OP-0099", crimp_date="2026-04-02"), registers()
        )
        self.assertIn(
            "operator-not-certified-on-the-date-of-the-crimp",
            result["unresolved"],
        )

    def test_the_first_day_of_a_certification_window_is_inside_it(self):
        result = resolve_references(
            record(operator_id="OP-0099", crimp_date="2026-07-01"), registers()
        )
        self.assertTrue(result["traceable"])

    def test_a_lot_with_no_receiving_record_does_not_resolve(self):
        result = resolve_references(record(contact_lot="CL-0000"), registers())
        self.assertIn("contact-lot-has-no-receiving-record", result["unresolved"])

    def test_a_received_but_unaccepted_lot_does_not_resolve(self):
        result = resolve_references(record(wire_lot="WL-4001"), registers())
        self.assertIn(
            "wire-lot-receiving-inspection-not-accepted", result["unresolved"]
        )

    def test_every_unresolved_reference_is_collected_not_just_the_first(self):
        result = resolve_references(
            record(tool_id="CT-9999", wire_lot="WL-4001"), registers()
        )
        self.assertEqual(len(result["unresolved"]), 2)


class TestRetention(unittest.TestCase):
    def test_whole_years_are_added_to_a_date(self):
        self.assertEqual(add_years("2016-08-12", 10), datetime.date(2026, 8, 12))

    def test_a_leap_day_steps_back_to_the_twenty_eighth(self):
        self.assertEqual(add_years("2016-02-29", 9), datetime.date(2025, 2, 28))

    def test_a_recent_record_is_still_within_retention(self):
        self.assertEqual(
            retention_state(record(), policy(), AS_OF)["state"], RETAINED
        )

    def test_an_old_record_has_passed_its_retention_period(self):
        self.assertEqual(
            retention_state(record(crimp_date="2010-01-04"), policy(), AS_OF)[
                "state"
            ],
            RETENTION_ELAPSED,
        )

    def test_the_last_day_of_retention_is_still_inside_it(self):
        state = retention_state(record(crimp_date="2016-09-19"), policy(), AS_OF)
        self.assertEqual(state["retain_until"], datetime.date(2026, 9, 19))
        self.assertTrue(state["still_required"])


class TestPullTestCadence(unittest.TestCase):
    def test_an_empty_record_set_raises(self):
        with self.assertRaises(ValueError):
            pull_test_cadence([], policy())

    def test_a_policed_run_holds_the_cadence(self):
        self.assertTrue(pull_test_cadence([record()], policy())["cadence_held"])

    def test_a_gap_larger_than_the_interval_is_caught(self):
        cadence = pull_test_cadence(
            [
                record(
                    record_id="CR-1",
                    crimp_date="2026-08-01",
                    terminations_made=40,
                    pull_test_reference=None,
                ),
                record(
                    record_id="CR-2",
                    crimp_date="2026-08-02",
                    terminations_made=40,
                    pull_test_reference="PT-2",
                ),
            ],
            policy(),
        )
        self.assertFalse(cadence["cadence_held"])
        self.assertIn("CR-2", cadence["gaps"])

    def test_an_unpoliced_tail_is_reported_as_an_open_run(self):
        cadence = pull_test_cadence(
            [
                record(
                    record_id="CR-1",
                    terminations_made=80,
                    pull_test_reference=None,
                )
            ],
            policy(),
        )
        self.assertIn("open-run-at-the-end-of-the-set", cadence["gaps"])

    def test_the_cadence_is_graded_in_date_order_not_list_order(self):
        cadence = pull_test_cadence(
            [
                record(
                    record_id="CR-LATE",
                    crimp_date="2026-08-20",
                    terminations_made=45,
                    pull_test_reference="PT-9",
                ),
                record(
                    record_id="CR-EARLY",
                    crimp_date="2026-08-01",
                    terminations_made=45,
                    pull_test_reference=None,
                ),
            ],
            policy(),
        )
        self.assertFalse(cadence["cadence_held"])
        self.assertEqual(cadence["gaps"], ["CR-LATE"])


class TestDossierAudit(unittest.TestCase):
    def test_an_empty_dossier_raises(self):
        with self.assertRaises(ValueError):
            audit_dossier([], registers(), policy(), AS_OF)

    def test_a_clean_dossier_is_accepted(self):
        report = audit_dossier([record()], registers(), policy(), AS_OF)
        self.assertEqual(report["verdict"], DOSSIER_ACCEPTED)
        self.assertEqual(report["results"][0]["disposition"], COMPLETE)

    def test_an_unresolved_reference_rejects_the_dossier(self):
        report = audit_dossier(
            [record(tool_id="CT-9999")], registers(), policy(), AS_OF
        )
        self.assertEqual(report["verdict"], DOSSIER_REJECTED)
        self.assertEqual(report["untraceable"], ["CR-0001"])

    def test_a_missing_field_rejects_the_dossier_separately(self):
        entry = record()
        del entry["contact_lot"]
        report = audit_dossier([entry], registers(), policy(), AS_OF)
        self.assertEqual(report["verdict"], DOSSIER_REJECTED)
        self.assertEqual(report["incomplete"], ["CR-0001"])
        self.assertEqual(report["untraceable"], [])

    def test_a_cadence_gap_is_a_finding_not_a_rejection(self):
        report = audit_dossier(
            [
                record(
                    record_id="CR-1",
                    terminations_made=80,
                    pull_test_reference=None,
                )
            ],
            registers(),
            policy(),
            AS_OF,
        )
        self.assertEqual(report["verdict"], DOSSIER_ACCEPTED_WITH_FINDINGS)
        self.assertIn("periodic-pull-test-cadence-not-held", report["findings"])

    def test_entries_past_retention_are_a_finding(self):
        report = audit_dossier(
            [record(crimp_date="2010-01-04", operator_id="OP-0050")],
            registers(),
            policy(),
            AS_OF,
        )
        self.assertEqual(report["verdict"], DOSSIER_ACCEPTED_WITH_FINDINGS)
        self.assertEqual(report["past_retention"], ["CR-0001"])

    def test_the_cadence_is_not_graded_on_an_incomplete_dossier(self):
        entry = record()
        del entry["tool_id"]
        report = audit_dossier([entry], registers(), policy(), AS_OF)
        self.assertIsNone(report["cadence"])


if __name__ == "__main__":
    unittest.main()
