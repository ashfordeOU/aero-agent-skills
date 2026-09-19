"""Contract tests for the mechanical-test laboratory control logic.

The cases walk a campaign onto the floor: the calendar arithmetic that fixes
when a qualification or a certificate runs out, the authorisation each
operator holds on the run day rather than today, the status and revision a
written procedure has to be at, the traceability an equipment record has to
carry, and the coverage every campaign method owes.
"""

import unittest
from datetime import date

from q7045_test_laboratory_control_logic import (
    APPROVED_PROCEDURE_STATUSES,
    DEFAULT_DUE_SOON_DAYS,
    add_months,
    assess_laboratory_control,
    authorised_operators,
    competency_status,
    days_remaining,
    equipment_findings,
    method_coverage,
    parse_day,
    procedure_findings,
)

RUN_DAY = "2026-06-01"


def _operators():
    return [
        {
            "id": "op-1",
            "competencies": [
                {"method": "room-temperature-tensile", "qualified_on": "2025-09-01",
                 "validity_months": 24},
                {"method": "elevated-temperature-tensile", "qualified_on": "2025-09-01",
                 "validity_months": 24},
            ],
        },
        {
            "id": "op-2",
            "competencies": [
                {"method": "room-temperature-tensile", "qualified_on": "2024-01-15",
                 "validity_months": 24},
            ],
        },
    ]


def _procedures():
    return [
        {"id": "tp-001", "status": "issued", "revision": "C", "current_revision": "C"},
        {"id": "tp-002", "status": "issued", "revision": "A", "current_revision": "A"},
    ]


def _equipment():
    return [
        {"id": "frame-1", "calibrated_on": "2026-01-10", "interval_months": 12,
         "certificate": "cert-8891", "traceability": ["national-standard"]},
        {"id": "ext-1", "calibrated_on": "2026-02-28", "interval_months": 12,
         "certificate": "cert-8892", "traceability": ["national-standard"]},
    ]


def _spec(**overrides):
    spec = {
        "run_day": RUN_DAY,
        "methods": [
            {"name": "room-temperature-tensile", "procedure_id": "tp-001",
             "procedure_revision": "C", "equipment_ids": ["frame-1", "ext-1"]},
        ],
        "operators": _operators(),
        "procedures": _procedures(),
        "equipment": _equipment(),
    }
    spec.update(overrides)
    return spec


class CalendarTests(unittest.TestCase):
    def test_an_iso_day_parses(self):
        self.assertEqual(parse_day("2026-06-01"), date(2026, 6, 1))

    def test_a_date_passes_through(self):
        self.assertEqual(parse_day(date(2026, 6, 1)), date(2026, 6, 1))

    def test_a_day_the_calendar_lacks_is_refused(self):
        with self.assertRaises(ValueError):
            parse_day("2026-02-30")

    def test_free_text_is_refused(self):
        with self.assertRaises(ValueError):
            parse_day("June 2026")

    def test_a_year_is_twelve_calendar_months(self):
        self.assertEqual(add_months("2026-06-01", 12), date(2027, 6, 1))

    def test_a_month_end_falls_back_to_a_shorter_month(self):
        self.assertEqual(add_months("2026-01-31", 1), date(2026, 2, 28))

    def test_a_month_end_reaches_a_leap_day(self):
        self.assertEqual(add_months("2024-01-31", 1), date(2024, 2, 29))

    def test_negative_months_are_refused(self):
        with self.assertRaises(ValueError):
            add_months("2026-06-01", -1)

    def test_days_remaining_counts_from_the_run_day(self):
        self.assertEqual(days_remaining("2026-06-30", "2026-06-01"), 29)

    def test_days_remaining_is_negative_once_it_has_passed(self):
        self.assertEqual(days_remaining("2026-05-01", "2026-06-01"), -31)


class CompetencyTests(unittest.TestCase):
    def test_a_current_competency_is_current(self):
        status = competency_status(
            {"method": "m", "qualified_on": "2025-09-01", "validity_months": 24}, RUN_DAY
        )
        self.assertTrue(status["current"])
        self.assertFalse(status["due_soon"])

    def test_a_lapsed_competency_is_not_current(self):
        status = competency_status(
            {"method": "m", "qualified_on": "2024-01-15", "validity_months": 24}, RUN_DAY
        )
        self.assertFalse(status["current"])
        self.assertLess(status["days_remaining"], 0)

    def test_a_competency_inside_the_window_is_reported_due(self):
        status = competency_status(
            {"method": "m", "qualified_on": "2024-06-10", "validity_months": 24}, RUN_DAY
        )
        self.assertTrue(status["current"])
        self.assertTrue(status["due_soon"])

    def test_the_default_window_is_thirty_days(self):
        self.assertEqual(DEFAULT_DUE_SOON_DAYS, 30)

    def test_a_competency_missing_a_key_is_refused(self):
        with self.assertRaises(ValueError):
            competency_status({"method": "m", "validity_months": 24}, RUN_DAY)


class AuthorisationTests(unittest.TestCase):
    def test_a_qualified_operator_is_authorised(self):
        result = authorised_operators(_operators(), "room-temperature-tensile", RUN_DAY)
        self.assertIn("op-1", result["authorised"])

    def test_a_lapsed_operator_is_left_out_and_named(self):
        result = authorised_operators(_operators(), "room-temperature-tensile", RUN_DAY)
        self.assertNotIn("op-2", result["authorised"])
        self.assertIn("op-2", result["lapsed"])
        self.assertTrue(any("op-2" in message for message in result["advisories"]))

    def test_an_unheld_method_authorises_nobody(self):
        result = authorised_operators(_operators(), "fracture-toughness", RUN_DAY)
        self.assertEqual(result["authorised"], [])

    def test_an_operator_without_an_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            authorised_operators([{"competencies": []}], "m", RUN_DAY)

    def test_an_empty_method_name_is_refused(self):
        with self.assertRaises(ValueError):
            authorised_operators(_operators(), "", RUN_DAY)


class ProcedureTests(unittest.TestCase):
    def test_an_issued_current_procedure_is_usable(self):
        result = procedure_findings(_procedures()[0], "C")
        self.assertTrue(result["usable"])

    def test_a_draft_procedure_is_not_usable(self):
        procedure = dict(_procedures()[0], status="draft")
        result = procedure_findings(procedure, "C")
        self.assertFalse(result["usable"])

    def test_a_superseded_revision_is_named(self):
        procedure = dict(_procedures()[0], revision="B")
        result = procedure_findings(procedure)
        self.assertFalse(result["usable"])

    def test_a_campaign_naming_another_revision_is_a_finding(self):
        result = procedure_findings(_procedures()[0], "D")
        self.assertFalse(result["usable"])

    def test_the_approved_states_are_named_in_the_module(self):
        self.assertIn("issued", APPROVED_PROCEDURE_STATUSES)

    def test_a_procedure_missing_a_key_is_refused(self):
        with self.assertRaises(ValueError):
            procedure_findings({"id": "tp-001", "status": "issued"})


class EquipmentRecordTests(unittest.TestCase):
    def test_a_complete_record_is_usable(self):
        result = equipment_findings(_equipment()[0], RUN_DAY)
        self.assertTrue(result["usable"])
        self.assertEqual(result["findings"], [])

    def test_a_record_without_a_certificate_is_not_usable(self):
        item = dict(_equipment()[0])
        del item["certificate"]
        result = equipment_findings(item, RUN_DAY)
        self.assertFalse(result["usable"])

    def test_an_empty_traceability_chain_is_a_finding(self):
        item = dict(_equipment()[0], traceability=[])
        result = equipment_findings(item, RUN_DAY)
        self.assertFalse(result["usable"])

    def test_an_expired_certificate_is_reported_with_the_days_past(self):
        item = dict(_equipment()[0], calibrated_on="2024-01-10")
        result = equipment_findings(item, RUN_DAY)
        self.assertFalse(result["usable"])
        self.assertLess(result["days_remaining"], 0)

    def test_a_certificate_inside_the_window_is_an_advisory_not_a_block(self):
        item = dict(_equipment()[0], calibrated_on="2025-06-20")
        result = equipment_findings(item, RUN_DAY)
        self.assertTrue(result["usable"])
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["advisories"])

    def test_a_record_missing_a_key_is_refused(self):
        with self.assertRaises(ValueError):
            equipment_findings({"id": "frame-1", "interval_months": 12}, RUN_DAY)


class CoverageTests(unittest.TestCase):
    def test_a_fully_covered_method_is_ready(self):
        state = method_coverage(
            _spec()["methods"][0], _operators(), _procedures(), _equipment(), RUN_DAY
        )
        self.assertTrue(state["ready"])

    def test_a_method_with_no_authorised_operator_is_not_ready(self):
        entry = dict(_spec()["methods"][0], name="fracture-toughness")
        state = method_coverage(entry, _operators(), _procedures(), _equipment(), RUN_DAY)
        self.assertFalse(state["ready"])

    def test_a_method_naming_an_unheld_procedure_is_not_ready(self):
        entry = dict(_spec()["methods"][0], procedure_id="tp-999")
        state = method_coverage(entry, _operators(), _procedures(), _equipment(), RUN_DAY)
        self.assertFalse(state["ready"])
        self.assertIsNone(state["procedure"])

    def test_a_method_naming_equipment_with_no_record_is_not_ready(self):
        entry = dict(_spec()["methods"][0], equipment_ids=["frame-1", "furnace-9"])
        state = method_coverage(entry, _operators(), _procedures(), _equipment(), RUN_DAY)
        self.assertFalse(state["ready"])

    def test_a_method_entry_missing_a_key_is_refused(self):
        with self.assertRaises(ValueError):
            method_coverage({"name": "m"}, _operators(), _procedures(), _equipment(), RUN_DAY)


class AssessmentTests(unittest.TestCase):
    def test_a_controlled_laboratory_is_ready(self):
        result = assess_laboratory_control(_spec())
        self.assertTrue(result["ready"])
        self.assertEqual(result["findings"], [])

    def test_a_lapsed_second_operator_does_not_block_a_staffed_method(self):
        result = assess_laboratory_control(_spec())
        self.assertTrue(result["ready"])
        self.assertTrue(result["advisories"])

    def test_the_ready_methods_are_listed(self):
        result = assess_laboratory_control(_spec())
        self.assertEqual(result["methods_ready"], ["room-temperature-tensile"])

    def test_a_second_method_without_an_operator_blocks_the_campaign(self):
        spec = _spec()
        spec["methods"].append(
            {"name": "fracture-toughness", "procedure_id": "tp-002", "equipment_ids": []}
        )
        result = assess_laboratory_control(spec)
        self.assertFalse(result["ready"])
        self.assertEqual(result["methods_ready"], ["room-temperature-tensile"])

    def test_an_expired_frame_blocks_the_campaign(self):
        equipment = _equipment()
        equipment[0]["calibrated_on"] = "2024-01-10"
        result = assess_laboratory_control(_spec(equipment=equipment))
        self.assertFalse(result["ready"])

    def test_the_run_day_governs_rather_than_today(self):
        early = assess_laboratory_control(_spec(run_day="2026-06-01"))
        late = assess_laboratory_control(_spec(run_day="2027-06-01"))
        self.assertTrue(early["ready"])
        self.assertFalse(late["ready"])

    def test_an_empty_campaign_is_refused(self):
        with self.assertRaises(ValueError):
            assess_laboratory_control(_spec(methods=[]))

    def test_a_missing_key_is_refused(self):
        spec = _spec()
        del spec["procedures"]
        with self.assertRaises(ValueError):
            assess_laboratory_control(spec)

    def test_a_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_laboratory_control(["run_day"])


if __name__ == "__main__":
    unittest.main()
