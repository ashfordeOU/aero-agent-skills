#!/usr/bin/env python3
"""Contract test for fastener records and lot traceability (offline)."""

import copy
import datetime
import unittest

from q7046_fastener_records_logic import (
    CHAIN_BROKEN,
    CHAIN_CIRCULAR,
    CHAIN_MIXED,
    CHAIN_RESOLVED,
    CRITICALITIES,
    RECORD_CONFORMITY_CERTIFICATE,
    RECORD_EMBRITTLEMENT_RELIEF,
    RECORD_HEAT_TREATMENT,
    VERDICT_COMPLETE,
    VERDICT_INCOMPLETE,
    assess_records,
    missing_records,
    required_records,
    retention_deadline,
    walk_traceability,
)

DATE = datetime.date

CLEAN_CHAIN = [
    {"id": "HEAT-88", "kind": "heat"},
    {"id": "BAR-12", "kind": "bar-lot", "parents": ["HEAT-88"]},
    {"id": "MFG-31", "kind": "manufacturing-lot", "parents": ["BAR-12"]},
    {"id": "PLT-07", "kind": "coating-lot", "parents": ["MFG-31"]},
    {"id": "DEL-01", "kind": "delivery-lot", "parents": ["PLT-07"]},
]

GOOD_CASE = {
    "lot_id": "DEL-01",
    "criticality": "critical",
    "delivery_date": DATE(2026, 3, 1),
    "records_present": required_records("critical"),
    "traceability_chain": CLEAN_CHAIN,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class RequiredRecordTests(unittest.TestCase):
    def test_a_critical_lot_owes_the_most_records(self):
        self.assertGreater(
            len(required_records("critical")), len(required_records("major"))
        )
        self.assertGreater(
            len(required_records("major")), len(required_records("minor"))
        )

    def test_every_criticality_owes_a_conformity_certificate(self):
        for criticality in CRITICALITIES:
            self.assertIn(
                RECORD_CONFORMITY_CERTIFICATE, required_records(criticality)
            )

    def test_only_a_critical_lot_owes_the_embrittlement_relief_record(self):
        self.assertIn(RECORD_EMBRITTLEMENT_RELIEF, required_records("critical"))
        self.assertNotIn(RECORD_EMBRITTLEMENT_RELIEF, required_records("major"))

    def test_only_a_critical_lot_owes_the_heat_treatment_record(self):
        self.assertIn(RECORD_HEAT_TREATMENT, required_records("critical"))
        self.assertNotIn(RECORD_HEAT_TREATMENT, required_records("minor"))

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            required_records("quite-important")


class MissingRecordTests(unittest.TestCase):
    def test_a_full_file_leaves_nothing_missing(self):
        self.assertEqual(
            missing_records("major", required_records("major")), []
        )

    def test_an_empty_file_leaves_everything_missing(self):
        self.assertEqual(
            missing_records("minor", []), required_records("minor")
        )

    def test_gaps_come_back_in_the_required_order(self):
        gaps = missing_records("critical", [RECORD_CONFORMITY_CERTIFICATE])
        self.assertEqual(gaps, required_records("critical")[1:])

    def test_a_record_the_criticality_does_not_owe_is_simply_ignored(self):
        self.assertEqual(
            missing_records("minor", list(required_records("critical"))), []
        )

    def test_an_unknown_record_name_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_records("minor", ["a-note-from-the-supplier"])

    def test_a_non_sequence_record_list_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_records("minor", "everything is on file")


class RetentionTests(unittest.TestCase):
    def test_a_critical_lot_is_retained_longest(self):
        delivered = DATE(2026, 3, 1)
        self.assertGreater(
            retention_deadline(delivered, "critical"),
            retention_deadline(delivered, "major"),
        )

    def test_retention_runs_from_delivery_not_manufacture(self):
        self.assertEqual(
            retention_deadline(DATE(2026, 3, 1), "minor"), DATE(2031, 3, 1)
        )

    def test_a_leap_day_delivery_clamps_to_a_real_date(self):
        self.assertEqual(
            retention_deadline(DATE(2024, 2, 29), "major"), DATE(2034, 2, 28)
        )

    def test_a_non_date_delivery_is_rejected(self):
        with self.assertRaises(ValueError):
            retention_deadline("2026-03-01", "minor")


class TraceabilityWalkTests(unittest.TestCase):
    def test_a_clean_chain_resolves_to_one_heat(self):
        result = walk_traceability(CLEAN_CHAIN, "DEL-01")
        self.assertEqual(result["status"], CHAIN_RESOLVED)
        self.assertEqual(result["heats"], ["HEAT-88"])
        self.assertTrue(result["resolved"])

    def test_the_walk_visits_every_node_on_the_path(self):
        self.assertEqual(
            walk_traceability(CLEAN_CHAIN, "DEL-01")["nodes_walked"], 5
        )

    def test_a_parent_that_is_not_in_the_records_breaks_the_chain(self):
        chain = copy.deepcopy(CLEAN_CHAIN)
        chain[1]["parents"] = ["HEAT-NOT-FILED"]
        result = walk_traceability(chain, "DEL-01")
        self.assertEqual(result["status"], CHAIN_BROKEN)
        self.assertFalse(result["resolved"])

    def test_a_node_declared_out_of_nothing_breaks_the_chain(self):
        chain = [
            {"id": "MFG-31", "kind": "manufacturing-lot", "parents": []},
            {"id": "DEL-01", "kind": "delivery-lot", "parents": ["MFG-31"]},
        ]
        self.assertEqual(
            walk_traceability(chain, "DEL-01")["status"], CHAIN_BROKEN
        )

    def test_a_chain_that_returns_to_itself_is_a_corrupted_record(self):
        chain = [
            {"id": "MFG-31", "kind": "manufacturing-lot", "parents": ["DEL-01"]},
            {"id": "DEL-01", "kind": "delivery-lot", "parents": ["MFG-31"]},
        ]
        result = walk_traceability(chain, "DEL-01")
        self.assertEqual(result["status"], CHAIN_CIRCULAR)
        self.assertTrue(any("corrupted" in f for f in result["findings"]))

    def test_two_heats_under_one_delivery_lot_are_reported_as_mixed(self):
        chain = copy.deepcopy(CLEAN_CHAIN)
        chain.append({"id": "HEAT-99", "kind": "heat"})
        chain.append(
            {"id": "BAR-13", "kind": "bar-lot", "parents": ["HEAT-99"]}
        )
        chain[2]["parents"] = ["BAR-12", "BAR-13"]
        result = walk_traceability(chain, "DEL-01")
        self.assertEqual(result["status"], CHAIN_MIXED)
        self.assertEqual(result["heats"], ["HEAT-88", "HEAT-99"])

    def test_a_heat_declared_out_of_something_is_rejected(self):
        chain = copy.deepcopy(CLEAN_CHAIN)
        chain[0]["parents"] = ["BAR-12"]
        with self.assertRaises(ValueError):
            walk_traceability(chain, "DEL-01")

    def test_a_duplicate_node_id_is_rejected(self):
        chain = copy.deepcopy(CLEAN_CHAIN) + [
            {"id": "DEL-01", "kind": "delivery-lot", "parents": ["PLT-07"]}
        ]
        with self.assertRaises(ValueError):
            walk_traceability(chain, "DEL-01")

    def test_a_delivery_lot_not_in_the_chain_is_rejected(self):
        with self.assertRaises(ValueError):
            walk_traceability(CLEAN_CHAIN, "DEL-99")

    def test_parents_given_as_a_bare_string_are_rejected(self):
        chain = copy.deepcopy(CLEAN_CHAIN)
        chain[4]["parents"] = "PLT-07"
        with self.assertRaises(ValueError):
            walk_traceability(chain, "DEL-01")

    def test_an_empty_chain_is_rejected(self):
        with self.assertRaises(ValueError):
            walk_traceability([], "DEL-01")

    def test_an_unknown_node_kind_is_rejected(self):
        chain = copy.deepcopy(CLEAN_CHAIN)
        chain[1]["kind"] = "some-paperwork"
        with self.assertRaises(ValueError):
            walk_traceability(chain, "DEL-01")


class AssessRecordsTests(unittest.TestCase):
    def test_a_complete_file_may_be_signed(self):
        result = assess_records(GOOD_CASE)
        self.assertEqual(result["verdict"], VERDICT_COMPLETE)
        self.assertTrue(result["acceptance_signable"])
        self.assertEqual(result["findings"], [])

    def test_a_gap_in_the_file_blocks_the_signature(self):
        result = assess_records(
            _case(records_present=[RECORD_CONFORMITY_CERTIFICATE])
        )
        self.assertEqual(result["verdict"], VERDICT_INCOMPLETE)
        self.assertFalse(result["acceptance_signable"])

    def test_a_complete_file_with_a_broken_chain_still_cannot_be_signed(self):
        chain = copy.deepcopy(CLEAN_CHAIN)
        chain[1]["parents"] = ["HEAT-NOT-FILED"]
        result = assess_records(_case(traceability_chain=chain))
        self.assertFalse(result["acceptance_signable"])
        self.assertTrue(any("cannot reach a heat" in f for f in result["findings"]))

    def test_no_chain_at_all_is_reported_rather_than_assumed(self):
        case = _case()
        del case["traceability_chain"]
        result = assess_records(case)
        self.assertIsNone(result["traceability"])
        self.assertTrue(any("cannot be resolved" in f for f in result["findings"]))

    def test_the_retention_deadline_is_carried_into_the_result(self):
        self.assertEqual(
            assess_records(GOOD_CASE)["retention_deadline"],
            retention_deadline(DATE(2026, 3, 1), "critical"),
        )

    def test_a_minor_lot_needs_fewer_records_for_the_same_chain(self):
        result = assess_records(
            _case(criticality="minor", records_present=required_records("minor"))
        )
        self.assertTrue(result["acceptance_signable"])

    def test_a_case_without_a_lot_id_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_records(_case(lot_id=""))

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_records("the certificates are in the folder")

    def test_a_case_missing_the_delivery_date_is_rejected(self):
        case = _case()
        del case["delivery_date"]
        with self.assertRaises(ValueError):
            assess_records(case)


if __name__ == "__main__":
    unittest.main()
