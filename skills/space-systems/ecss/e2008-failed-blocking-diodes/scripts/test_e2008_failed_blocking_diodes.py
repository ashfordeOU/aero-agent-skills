#!/usr/bin/env python3
"""Contract test for failed blocking diode designation, clause 12.7.2 (offline)."""

import copy
import unittest

from e2008_failed_blocking_diodes_logic import (
    DEFAULT_DESIGNATION_POLICY,
    DESIGNATION_DELIVERABLE,
    DESIGNATION_FAILED,
    DESIGNATION_UNDETERMINED,
    EVIDENCE_NONCONFORMANCE,
    EVIDENCE_SEGREGATION,
    EVIDENCE_STRING_WITHDRAWAL,
    LOT_DESIGNATION_ASSIGNED,
    LOT_DESIGNATION_INCOMPLETE,
    LOT_FAILED_SHARE_EXCEEDED,
    RECOGNISED_FAILURE_MODES,
    designate_blocking_diode,
    designate_lot,
    recognised_failure_modes,
    required_failed_evidence,
    standing_modes,
    validate_designation_policy,
)


def _record(part_id="bd-001", modes=None, **overrides):
    record = {
        "part_id": part_id,
        "failure_modes": list(modes or []),
        "inspection_complete": True,
    }
    if modes:
        record["segregation_record"] = "quarantine-tray-7"
        record["nonconformance_reference"] = "ncr-2026-0114"
    record.update(overrides)
    return record


def _policy(**overrides):
    policy = copy.deepcopy(DEFAULT_DESIGNATION_POLICY)
    policy.update(overrides)
    return policy


def _lot(records=None, offered=None, **overrides):
    lot = {
        "lot_id": "bd-lot-2026-11",
        "offered_part_ids": offered
        if offered is not None
        else ["bd-00%d" % n for n in (1, 2, 3, 4)],
        "part_records": records
        if records is not None
        else [_record("bd-00%d" % n) for n in (1, 2, 3, 4)],
    }
    lot.update(overrides)
    return lot


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_designation_policy(DEFAULT_DESIGNATION_POLICY),
            DEFAULT_DESIGNATION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_designation_policy("segregate anything that looks odd")

    def test_policy_without_a_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_designation_policy(_policy(policy_reference="  "))

    def test_non_boolean_segregation_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_designation_policy(_policy(segregation_record_required="yes"))

    def test_non_boolean_retest_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_designation_policy(_policy(retest_clearance_admitted=1))

    def test_failed_share_allowance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_designation_policy(_policy(max_failed_fraction=1.4))

    def test_negative_failed_share_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_designation_policy(_policy(max_failed_fraction=-0.1))


class VocabularyTests(unittest.TestCase):
    def test_recognised_modes_come_back_as_a_tuple_copy(self):
        modes = recognised_failure_modes()
        self.assertEqual(modes, RECOGNISED_FAILURE_MODES)
        self.assertIsInstance(modes, tuple)

    def test_the_two_function_losses_are_recognised_modes(self):
        modes = recognised_failure_modes()
        self.assertIn("blocking-diode-reverse-blocking-lost", modes)
        self.assertIn("blocking-diode-forward-conduction-lost", modes)

    def test_an_unrecognised_mode_is_refused_rather_than_dropped(self):
        with self.assertRaises(ValueError):
            standing_modes(_record(modes=["diode-looks-tired"]))

    def test_non_sequence_modes_rejected(self):
        with self.assertRaises(ValueError):
            standing_modes({"part_id": "bd-001", "failure_modes": "die-crack"})


class StandingModeTests(unittest.TestCase):
    def test_a_repeated_mode_collapses_to_one(self):
        result = standing_modes(_record(modes=["die-crack", "die-crack"]))
        self.assertEqual(result["standing_modes"], ["die-crack"])

    def test_a_clearance_is_ignored_where_the_policy_does_not_admit_it(self):
        record = _record(modes=["die-crack"], cleared_modes=["die-crack"])
        record["clearing_authority"] = "quality-manager"
        result = standing_modes(record)
        self.assertEqual(result["standing_modes"], ["die-crack"])
        self.assertTrue(result["findings"])

    def test_a_clearance_stands_where_the_policy_admits_it_and_names_an_authority(self):
        record = _record(modes=["die-crack"], cleared_modes=["die-crack"])
        record["clearing_authority"] = "quality-manager"
        result = standing_modes(record, _policy(retest_clearance_admitted=True))
        self.assertEqual(result["standing_modes"], [])
        self.assertEqual(result["cleared_modes"], ["die-crack"])

    def test_a_clearance_without_an_authority_is_a_second_opinion(self):
        record = _record(modes=["die-crack"], cleared_modes=["die-crack"])
        result = standing_modes(record, _policy(retest_clearance_admitted=True))
        self.assertEqual(result["standing_modes"], ["die-crack"])

    def test_clearing_a_mode_never_raised_is_a_data_defect(self):
        record = _record(modes=["die-crack"], cleared_modes=["encapsulation-damage"])
        record["clearing_authority"] = "quality-manager"
        with self.assertRaises(ValueError):
            standing_modes(record, _policy(retest_clearance_admitted=True))


class EvidenceTests(unittest.TestCase):
    def test_a_fully_papered_failure_owes_nothing(self):
        self.assertEqual(required_failed_evidence(_record(modes=["die-crack"])), [])

    def test_a_missing_segregation_record_is_named(self):
        record = _record(modes=["die-crack"])
        del record["segregation_record"]
        self.assertIn(EVIDENCE_SEGREGATION, required_failed_evidence(record))

    def test_a_blank_nonconformance_reference_is_named(self):
        record = _record(modes=["die-crack"], nonconformance_reference="   ")
        self.assertIn(EVIDENCE_NONCONFORMANCE, required_failed_evidence(record))

    def test_an_allocated_string_must_be_withdrawn(self):
        record = _record(modes=["die-crack"], string_allocation="wing-2-string-14")
        self.assertIn(EVIDENCE_STRING_WITHDRAWAL, required_failed_evidence(record))

    def test_a_withdrawn_allocation_owes_nothing_further(self):
        record = _record(
            modes=["die-crack"],
            string_allocation="wing-2-string-14",
            string_allocation_withdrawn=True,
        )
        self.assertEqual(required_failed_evidence(record), [])

    def test_an_unallocated_part_owes_no_withdrawal(self):
        self.assertNotIn(
            EVIDENCE_STRING_WITHDRAWAL, required_failed_evidence(_record(modes=["die-crack"]))
        )

    def test_a_policy_demanding_nothing_asks_for_nothing(self):
        record = _record(modes=["die-crack"])
        del record["segregation_record"]
        del record["nonconformance_reference"]
        policy = _policy(
            segregation_record_required=False,
            nonconformance_reference_required=False,
            string_allocation_withdrawal_required=False,
        )
        self.assertEqual(required_failed_evidence(record, policy), [])


class DesignationTests(unittest.TestCase):
    def test_a_clean_inspected_part_is_deliverable(self):
        result = designate_blocking_diode(_record())
        self.assertEqual(result["designation"], DESIGNATION_DELIVERABLE)
        self.assertTrue(result["deliverable"])

    def test_one_standing_mode_is_enough(self):
        result = designate_blocking_diode(_record(modes=["die-crack"]))
        self.assertEqual(result["designation"], DESIGNATION_FAILED)
        self.assertTrue(result["failed"])

    def test_four_modes_take_the_same_word_as_one(self):
        one = designate_blocking_diode(_record(modes=["die-crack"]))
        four = designate_blocking_diode(
            _record(
                modes=[
                    "die-crack",
                    "encapsulation-damage",
                    "blocking-diode-reverse-blocking-lost",
                    "reverse-leakage-current-drift-exceeded",
                ]
            )
        )
        self.assertEqual(one["designation"], four["designation"])
        self.assertGreater(len(four["standing_modes"]), len(one["standing_modes"]))

    def test_an_unfinished_inspection_is_undetermined(self):
        result = designate_blocking_diode(_record(inspection_complete=False))
        self.assertEqual(result["designation"], DESIGNATION_UNDETERMINED)
        self.assertFalse(result["deliverable"])
        self.assertFalse(result["failed"])

    def test_a_standing_mode_outranks_an_unfinished_inspection(self):
        result = designate_blocking_diode(
            _record(modes=["die-crack"], inspection_complete=False)
        )
        self.assertEqual(result["designation"], DESIGNATION_FAILED)

    def test_a_failed_part_without_papers_is_undocumented(self):
        record = _record(modes=["die-crack"])
        del record["segregation_record"]
        result = designate_blocking_diode(record)
        self.assertEqual(result["designation"], DESIGNATION_FAILED)
        self.assertFalse(result["documented"])
        self.assertIn(EVIDENCE_SEGREGATION, result["missing_evidence"])

    def test_a_cleared_part_under_an_admitting_policy_is_deliverable(self):
        record = _record(modes=["die-crack"], cleared_modes=["die-crack"])
        record["clearing_authority"] = "quality-manager"
        result = designate_blocking_diode(
            record, _policy(retest_clearance_admitted=True)
        )
        self.assertEqual(result["designation"], DESIGNATION_DELIVERABLE)

    def test_a_record_without_a_part_identifier_rejected(self):
        record = _record()
        del record["part_id"]
        with self.assertRaises(ValueError):
            designate_blocking_diode(record)

    def test_a_non_boolean_inspection_flag_rejected(self):
        with self.assertRaises(ValueError):
            designate_blocking_diode(_record(inspection_complete="mostly"))

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            designate_blocking_diode(["bd-001"])

    def test_findings_name_the_part(self):
        record = _record("bd-042", modes=["die-crack"])
        del record["nonconformance_reference"]
        result = designate_blocking_diode(record)
        self.assertTrue(any("bd-042" in finding for finding in result["findings"]))


class LotTests(unittest.TestCase):
    def test_a_clean_lot_is_fully_designated(self):
        result = designate_lot(_lot())
        self.assertEqual(result["verdict"], LOT_DESIGNATION_ASSIGNED)
        self.assertEqual(result["deliverable_count"], 4)
        self.assertEqual(result["findings"], [])

    def test_the_deliverable_count_is_derived_not_the_offered_quantity(self):
        records = [_record("bd-00%d" % n) for n in (1, 2, 3, 4)]
        records[0] = _record("bd-001", modes=["die-crack"])
        result = designate_lot(_lot(records))
        self.assertEqual(result["offered_count"], 4)
        self.assertEqual(result["deliverable_count"], 3)
        self.assertEqual(result["failed_part_ids"], ["bd-001"])

    def test_the_designation_is_per_part_not_per_lot(self):
        records = [_record("bd-00%d" % n) for n in (1, 2, 3, 4)]
        records[2] = _record("bd-003", modes=["encapsulation-damage"])
        result = designate_lot(_lot(records))
        groups = result["designations_by_group"]
        self.assertEqual(groups[DESIGNATION_FAILED], ["bd-003"])
        self.assertEqual(
            groups[DESIGNATION_DELIVERABLE], ["bd-001", "bd-002", "bd-004"]
        )

    def test_an_offered_part_with_no_record_is_undetermined(self):
        records = [_record("bd-00%d" % n) for n in (1, 2, 3)]
        result = designate_lot(_lot(records))
        self.assertEqual(result["unrecorded_offered_part_ids"], ["bd-004"])
        self.assertIn("bd-004", result["undetermined_part_ids"])
        self.assertEqual(result["verdict"], LOT_DESIGNATION_INCOMPLETE)

    def test_an_undetermined_part_is_not_counted_as_deliverable(self):
        records = [_record("bd-00%d" % n) for n in (1, 2, 3)]
        records.append(_record("bd-004", inspection_complete=False))
        result = designate_lot(_lot(records))
        self.assertEqual(result["deliverable_count"], 3)
        self.assertNotIn("bd-004", result["deliverable_part_ids"])

    def test_a_policy_may_count_undetermined_parts_in(self):
        records = [_record("bd-00%d" % n) for n in (1, 2, 3)]
        records.append(_record("bd-004", inspection_complete=False))
        result = designate_lot(
            _lot(records), _policy(undetermined_countable_as_deliverable=True)
        )
        self.assertEqual(result["deliverable_count"], 4)
        self.assertEqual(result["verdict"], LOT_DESIGNATION_ASSIGNED)

    def test_a_foreign_record_is_reported_rather_than_absorbed(self):
        records = [_record("bd-00%d" % n) for n in (1, 2, 3, 4)]
        records.append(_record("bd-901", modes=["die-crack"]))
        result = designate_lot(_lot(records))
        self.assertEqual(result["foreign_record_part_ids"], ["bd-901"])
        self.assertEqual(result["verdict"], LOT_DESIGNATION_INCOMPLETE)
        self.assertNotIn("bd-901", result["failed_part_ids"])

    def test_an_undocumented_failure_leaves_the_lot_incomplete(self):
        records = [_record("bd-00%d" % n) for n in (1, 2, 3, 4)]
        failed = _record("bd-002", modes=["die-crack"])
        del failed["segregation_record"]
        records[1] = failed
        result = designate_lot(_lot(records))
        self.assertEqual(result["undocumented_failed_part_ids"], ["bd-002"])
        self.assertEqual(result["verdict"], LOT_DESIGNATION_INCOMPLETE)

    def test_a_failed_share_past_the_allowance_is_reported(self):
        records = [_record("bd-00%d" % n) for n in (1, 2, 3, 4)]
        records[0] = _record("bd-001", modes=["die-crack"])
        records[1] = _record("bd-002", modes=["encapsulation-damage"])
        result = designate_lot(_lot(records))
        self.assertAlmostEqual(result["failed_fraction"], 0.5, places=9)
        self.assertFalse(result["failed_share_within_allowance"])
        self.assertEqual(result["verdict"], LOT_FAILED_SHARE_EXCEEDED)

    def test_a_share_landing_on_the_allowance_is_admissible(self):
        records = [_record("bd-00%d" % n) for n in (1, 2, 3, 4)]
        records[0] = _record("bd-001", modes=["die-crack"])
        result = designate_lot(_lot(records), _policy(max_failed_fraction=0.25))
        self.assertTrue(result["failed_share_within_allowance"])
        self.assertEqual(result["verdict"], LOT_DESIGNATION_ASSIGNED)

    def test_designations_come_back_in_part_order(self):
        records = [_record("bd-00%d" % n) for n in (4, 1, 3, 2)]
        result = designate_lot(_lot(records))
        ids = [entry["part_id"] for entry in result["part_designations"]]
        self.assertEqual(ids, sorted(ids))

    def test_a_repeated_record_rejected(self):
        records = [_record("bd-001"), _record("bd-001")]
        with self.assertRaises(ValueError):
            designate_lot(_lot(records, offered=["bd-001"]))

    def test_a_repeated_offered_identifier_rejected(self):
        with self.assertRaises(ValueError):
            designate_lot(_lot(offered=["bd-001", "bd-001"]))

    def test_an_empty_offered_population_rejected(self):
        with self.assertRaises(ValueError):
            designate_lot(_lot(offered=[]))

    def test_a_lot_without_an_identifier_rejected(self):
        lot = _lot()
        del lot["lot_id"]
        with self.assertRaises(ValueError):
            designate_lot(lot)

    def test_non_mapping_lot_rejected(self):
        with self.assertRaises(ValueError):
            designate_lot([_record()])

    def test_a_string_allocation_still_live_leaves_the_lot_incomplete(self):
        records = [_record("bd-00%d" % n) for n in (1, 2, 3, 4)]
        records[3] = _record(
            "bd-004", modes=["die-crack"], string_allocation="wing-2-string-14"
        )
        result = designate_lot(_lot(records))
        self.assertIn("bd-004", result["undocumented_failed_part_ids"])
        self.assertEqual(result["verdict"], LOT_DESIGNATION_INCOMPLETE)


if __name__ == "__main__":
    unittest.main()
