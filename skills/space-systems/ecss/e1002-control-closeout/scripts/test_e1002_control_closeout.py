#!/usr/bin/env python3
"""Gate 3 behavior contract for e1002-control-closeout (stdlib, offline)."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1002_control_closeout_logic import (  # noqa: E402
    CLOSED_STATUSES, NC_STATES, ROW_STATUSES, closeout_review,
    database_violations, evidence_violations, is_verification_closed_out,
    nonconformance_violations, open_rows, validate_row_status,
    waiver_violations,
)

FMT = "csv"


def row(rid="R1", status="closed", evidence="VR-1", waiver=None):
    return {"requirement_id": rid, "status": status, "evidence_ref": evidence,
            "waiver_ref": waiver}


def delivery(rows=None, **over):
    d = {"delivered": True, "format": FMT, "machine_readable": True,
         "row_ids": [r["requirement_id"] for r in (rows or [row()])]}
    d.update(over)
    return d


def vcd(**over):
    rows = [row("R1"), row("R2")]
    v = {"rows": rows, "nonconformances": [], "approved_waivers": [],
         "database_delivery": delivery(rows)}
    v.update(over)
    return v


class StatusTest(unittest.TestCase):
    def test_every_status_validates(self):
        for s in ROW_STATUSES:
            self.assertEqual(validate_row_status(s), s)

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            validate_row_status("nearly")

    def test_closed_statuses_are_a_subset(self):
        for s in CLOSED_STATUSES:
            self.assertIn(s, ROW_STATUSES)

    def test_closed_rows_are_not_open(self):
        self.assertEqual(open_rows([row(), row("R2", "closed_with_waiver",
                                              waiver="W1")]), [])

    def test_open_and_in_progress_rows_are_listed(self):
        rows = [row("R1", "open"), row("R2", "in_progress"), row("R3")]
        self.assertEqual(open_rows(rows), ["R1", "R2"])

    def test_row_without_requirement_id_raises(self):
        with self.assertRaises(ValueError):
            open_rows([{"status": "closed"}])


class WaiverTest(unittest.TestCase):
    def test_approved_waiver_is_clean(self):
        rows = [row("R1", "closed_with_waiver", waiver="W1")]
        self.assertEqual(waiver_violations(rows, ["W1"]), [])

    def test_waiver_without_reference_is_reported(self):
        rows = [row("R1", "closed_with_waiver", waiver="")]
        f = waiver_violations(rows, ["W1"])
        self.assertEqual(f[0]["issue"], "closed_with_waiver_without_reference")

    def test_unapproved_waiver_is_reported(self):
        rows = [row("R1", "closed_with_waiver", waiver="W9")]
        f = waiver_violations(rows, ["W1"])
        self.assertEqual(f[0]["issue"], "waiver_not_approved")

    def test_plain_closed_rows_need_no_waiver(self):
        self.assertEqual(waiver_violations([row()], []), [])


class EvidenceTest(unittest.TestCase):
    def test_closed_row_with_evidence_is_clean(self):
        self.assertEqual(evidence_violations([row()]), [])

    def test_closed_row_without_evidence_is_reported(self):
        f = evidence_violations([row(evidence="")])
        self.assertEqual(f[0]["issue"], "closed_without_evidence")

    def test_open_row_needs_no_evidence_yet(self):
        self.assertEqual(evidence_violations([row(status="open", evidence="")]), [])

    def test_waiver_closure_still_needs_evidence(self):
        rows = [row("R1", "closed_with_waiver", evidence="", waiver="W1")]
        self.assertEqual(evidence_violations(rows)[0]["issue"],
                         "closed_without_evidence")


class NonconformanceTest(unittest.TestCase):
    def test_no_nonconformances_is_clean(self):
        self.assertEqual(nonconformance_violations([]), [])

    def test_dispositioned_nonconformance_is_clean(self):
        self.assertEqual(nonconformance_violations(
            [{"nc_id": "N1", "state": "dispositioned"}]), [])

    def test_open_nonconformance_is_reported(self):
        f = nonconformance_violations([{"nc_id": "N1", "state": "open"}])
        self.assertEqual(f[0]["issue"], "nonconformance_open_at_closeout")

    def test_missing_state_defaults_to_open(self):
        self.assertEqual(len(nonconformance_violations([{"nc_id": "N1"}])), 1)

    def test_unknown_state_raises(self):
        with self.assertRaises(ValueError):
            nonconformance_violations([{"nc_id": "N1", "state": "whatever"}])

    def test_declared_states_are_exactly_two(self):
        self.assertEqual(set(NC_STATES), {"open", "dispositioned"})


class DatabaseTest(unittest.TestCase):
    def test_complete_delivery_is_clean(self):
        rows = [row("R1"), row("R2")]
        self.assertEqual(database_violations(delivery(rows), rows, FMT), [])

    def test_undelivered_database_is_reported(self):
        f = database_violations({"delivered": False}, [row()], FMT)
        self.assertEqual(f[0]["issue"], "verification_database_not_delivered")

    def test_absent_delivery_record_is_reported(self):
        f = database_violations(None, [row()], FMT)
        self.assertEqual(f[0]["issue"], "verification_database_not_delivered")

    def test_wrong_format_is_reported(self):
        rows = [row()]
        f = database_violations(delivery(rows, format="pdf"), rows, FMT)
        self.assertEqual(f[0]["issue"], "database_format_not_as_agreed")

    def test_non_machine_readable_delivery_is_reported(self):
        rows = [row()]
        f = database_violations(delivery(rows, machine_readable=False), rows, FMT)
        self.assertIn("database_not_machine_readable", [x["issue"] for x in f])

    def test_incomplete_delivery_names_the_missing_rows(self):
        rows = [row("R1"), row("R2")]
        d = delivery(rows, row_ids=["R1"])
        f = database_violations(d, rows, FMT)
        self.assertEqual(f[0]["issue"], "row_absent_from_database")
        self.assertEqual(f[0]["requirement_id"], "R2")


class CloseoutTest(unittest.TestCase):
    def test_clean_programme_closes_out(self):
        r = closeout_review(vcd(), FMT)
        self.assertEqual(r["open_requirements"], [])
        self.assertTrue(is_verification_closed_out(r))

    def test_open_requirement_blocks_closeout(self):
        rows = [row("R1", "open"), row("R2")]
        v = vcd(rows=rows, database_delivery=delivery(rows))
        self.assertFalse(is_verification_closed_out(closeout_review(v, FMT)))

    def test_open_nonconformance_blocks_closeout(self):
        v = vcd(nonconformances=[{"nc_id": "N1", "state": "open"}])
        self.assertFalse(is_verification_closed_out(closeout_review(v, FMT)))

    def test_undelivered_database_blocks_closeout(self):
        v = vcd(database_delivery={"delivered": False})
        self.assertFalse(is_verification_closed_out(closeout_review(v, FMT)))

    def test_conditions_are_conjunctive(self):
        rows = [row("R1"), row("R2")]
        v = vcd(rows=rows, database_delivery=delivery(rows, row_ids=["R1"]),
                nonconformances=[{"nc_id": "N1", "state": "dispositioned"}])
        r = closeout_review(v, FMT)
        self.assertEqual(r["open_requirements"], [])
        self.assertFalse(is_verification_closed_out(r))

    def test_review_does_not_mutate_input(self):
        v = vcd()
        before = copy.deepcopy(v)
        closeout_review(v, FMT)
        self.assertEqual(v, before)


if __name__ == "__main__":
    unittest.main()
