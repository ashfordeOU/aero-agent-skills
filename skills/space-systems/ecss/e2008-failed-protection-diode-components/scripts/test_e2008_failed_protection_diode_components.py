#!/usr/bin/env python3
"""Contract test for failed protection diode components, clause 9.7.2 (offline)."""

import copy
import unittest

from e2008_failed_protection_diode_components_logic import (
    DEFAULT_DESIGNATION_POLICY,
    DESIGNATION_DELIVERABLE,
    DESIGNATION_FAILED,
    DESIGNATION_UNDETERMINED,
    POPULATION_DESIGNATION_ASSIGNED,
    POPULATION_DESIGNATION_INCOMPLETE,
    RECOGNISED_FAILURE_MODES,
    REQUIRED_FAILED_COMPONENT_EVIDENCE,
    designate_lot,
    designate_part,
    missing_failed_component_evidence,
    recognised_failure_modes,
    required_failed_component_evidence,
    standing_failure_modes,
    validate_designation_policy,
)


def _part(part_id="pd-001", modes=None, **overrides):
    part = {
        "part_id": part_id,
        "observed_modes": list(modes or []),
        "inspection_complete": True,
    }
    if modes:
        part["segregation_record"] = "seg-%s" % part_id
        part["nonconformance_reference"] = "ncr-%s" % part_id
    part.update(overrides)
    return part


def _lot(records=None, offered=None, **overrides):
    lot = {
        "lot_id": "lot-pd-2026-03",
        "offered_part_ids": offered
        if offered is not None
        else ["pd-00%d" % n for n in (1, 2, 3, 4)],
        "part_records": records
        if records is not None
        else [_part("pd-00%d" % n) for n in (1, 2, 3, 4)],
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
            validate_designation_policy("segregate everything")

    def test_non_boolean_segregation_flag_rejected(self):
        broken = copy.deepcopy(DEFAULT_DESIGNATION_POLICY)
        broken["require_segregation_record"] = "yes"
        with self.assertRaises(ValueError):
            validate_designation_policy(broken)

    def test_missing_retest_flag_rejected(self):
        broken = copy.deepcopy(DEFAULT_DESIGNATION_POLICY)
        del broken["admit_retest_clearance"]
        with self.assertRaises(ValueError):
            validate_designation_policy(broken)

    def test_failed_share_allowance_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_DESIGNATION_POLICY)
        broken["max_failed_fraction"] = 1.2
        with self.assertRaises(ValueError):
            validate_designation_policy(broken)


class VocabularyTests(unittest.TestCase):
    def test_recognised_modes_come_back_as_a_tuple_copy(self):
        modes = recognised_failure_modes()
        self.assertEqual(modes, RECOGNISED_FAILURE_MODES)
        self.assertIsInstance(modes, tuple)

    def test_required_evidence_comes_back_as_a_tuple_copy(self):
        evidence = required_failed_component_evidence()
        self.assertEqual(evidence, REQUIRED_FAILED_COMPONENT_EVIDENCE)
        self.assertIsInstance(evidence, tuple)

    def test_lost_blocking_is_a_recognised_mode(self):
        self.assertIn("diode-blocking-function-lost", recognised_failure_modes())


class StandingModeTests(unittest.TestCase):
    def test_a_part_with_no_mode_has_nothing_standing(self):
        result = standing_failure_modes(_part())
        self.assertEqual(result["standing_modes"], [])

    def test_repeated_modes_collapse_to_one(self):
        part = _part(modes=["diode-body-crack", "diode-body-crack"])
        result = standing_failure_modes(part)
        self.assertEqual(result["standing_modes"], ["diode-body-crack"])

    def test_an_unrecognised_mode_rejected(self):
        part = _part(modes=["diode-slightly-sad"])
        with self.assertRaises(ValueError):
            standing_failure_modes(part)

    def test_a_clearance_for_a_mode_never_observed_rejected(self):
        part = _part(modes=["diode-body-crack"])
        part["retest_cleared_modes"] = ["encapsulation-damage"]
        with self.assertRaises(ValueError):
            standing_failure_modes(part)

    def test_a_clearance_the_policy_does_not_admit_leaves_the_mode_standing(self):
        part = _part(modes=["diode-body-crack"])
        part["retest_cleared_modes"] = ["diode-body-crack"]
        part["clearing_authority"] = "quality-manager"
        result = standing_failure_modes(part)
        self.assertEqual(result["standing_modes"], ["diode-body-crack"])
        self.assertTrue(result["notes"])

    def test_an_admitted_clearance_without_an_authority_does_not_stand(self):
        policy = copy.deepcopy(DEFAULT_DESIGNATION_POLICY)
        policy["admit_retest_clearance"] = True
        part = _part(modes=["diode-body-crack"])
        part["retest_cleared_modes"] = ["diode-body-crack"]
        result = standing_failure_modes(part, policy)
        self.assertEqual(result["standing_modes"], ["diode-body-crack"])

    def test_an_admitted_clearance_with_an_authority_removes_the_mode(self):
        policy = copy.deepcopy(DEFAULT_DESIGNATION_POLICY)
        policy["admit_retest_clearance"] = True
        part = _part(modes=["terminal-discolouration"])
        part["retest_cleared_modes"] = ["terminal-discolouration"]
        part["clearing_authority"] = "quality-manager"
        result = standing_failure_modes(part, policy)
        self.assertEqual(result["standing_modes"], [])
        self.assertEqual(result["cleared_modes"], ["terminal-discolouration"])

    def test_non_sequence_observed_modes_rejected(self):
        part = _part()
        part["observed_modes"] = "diode-body-crack"
        with self.assertRaises(ValueError):
            standing_failure_modes(part)


class EvidenceTests(unittest.TestCase):
    def test_a_documented_failed_part_misses_nothing(self):
        part = _part(modes=["diode-body-crack"])
        self.assertEqual(missing_failed_component_evidence(part), [])

    def test_a_missing_segregation_record_is_named(self):
        part = _part(modes=["diode-body-crack"])
        del part["segregation_record"]
        self.assertEqual(missing_failed_component_evidence(part), ["segregation_record"])

    def test_a_blank_nonconformance_reference_counts_as_missing(self):
        part = _part(modes=["diode-body-crack"])
        part["nonconformance_reference"] = "   "
        self.assertIn("nonconformance_reference", missing_failed_component_evidence(part))

    def test_a_policy_that_demands_neither_asks_for_nothing(self):
        policy = copy.deepcopy(DEFAULT_DESIGNATION_POLICY)
        policy["require_segregation_record"] = False
        policy["require_nonconformance_reference"] = False
        part = _part(modes=["diode-body-crack"])
        del part["segregation_record"]
        del part["nonconformance_reference"]
        self.assertEqual(missing_failed_component_evidence(part, policy), [])


class PartDesignationTests(unittest.TestCase):
    def test_a_clean_inspected_part_is_deliverable(self):
        result = designate_part(_part())
        self.assertEqual(result["designation"], DESIGNATION_DELIVERABLE)
        self.assertTrue(result["deliverable"])

    def test_one_standing_mode_is_enough_to_fail_the_part(self):
        result = designate_part(_part(modes=["terminal-discolouration"]))
        self.assertEqual(result["designation"], DESIGNATION_FAILED)
        self.assertTrue(result["failed"])

    def test_four_modes_take_the_same_designation_as_one(self):
        one = designate_part(_part(modes=["diode-body-crack"]))
        four = designate_part(
            _part(
                modes=[
                    "diode-body-crack",
                    "encapsulation-damage",
                    "solder-void-beyond-limit",
                    "diode-blocking-function-lost",
                ]
            )
        )
        self.assertEqual(one["designation"], four["designation"])
        self.assertEqual(len(four["standing_modes"]), 4)

    def test_an_unfinished_inspection_is_undetermined_not_deliverable(self):
        result = designate_part(_part(inspection_complete=False))
        self.assertEqual(result["designation"], DESIGNATION_UNDETERMINED)
        self.assertFalse(result["deliverable"])
        self.assertFalse(result["settled"])

    def test_a_standing_mode_outranks_an_unfinished_inspection(self):
        part = _part(modes=["diode-body-crack"], inspection_complete=False)
        result = designate_part(part)
        self.assertEqual(result["designation"], DESIGNATION_FAILED)

    def test_a_failed_part_without_segregation_is_not_documented(self):
        part = _part(modes=["diode-body-crack"])
        del part["segregation_record"]
        result = designate_part(part)
        self.assertFalse(result["documented"])
        self.assertEqual(result["missing_evidence"], ["segregation_record"])

    def test_a_part_without_an_identifier_rejected(self):
        part = _part()
        del part["part_id"]
        with self.assertRaises(ValueError):
            designate_part(part)

    def test_a_non_boolean_inspection_flag_rejected(self):
        part = _part(inspection_complete="almost")
        with self.assertRaises(ValueError):
            designate_part(part)

    def test_findings_name_the_part(self):
        result = designate_part(_part("pd-077", modes=["encapsulation-damage"]))
        self.assertTrue(any("pd-077" in finding for finding in result["findings"]))


class LotTests(unittest.TestCase):
    def test_a_clean_lot_has_every_designation_assigned(self):
        result = designate_lot(_lot())
        self.assertEqual(result["verdict"], POPULATION_DESIGNATION_ASSIGNED)
        self.assertEqual(result["deliverable_count"], 4)

    def test_the_deliverable_count_is_derived_not_carried_over(self):
        records = [_part("pd-00%d" % n) for n in (1, 2, 3, 4)]
        records[0] = _part("pd-001", modes=["diode-body-crack"])
        result = designate_lot(_lot(records))
        self.assertEqual(result["offered_count"], 4)
        self.assertEqual(result["deliverable_count"], 3)
        self.assertEqual(result["failed_part_ids"], ["pd-001"])

    def test_one_failed_part_breaks_a_zero_allowance_lot(self):
        records = [_part("pd-00%d" % n) for n in (1, 2, 3, 4)]
        records[1] = _part("pd-002", modes=["solder-void-beyond-limit"])
        result = designate_lot(_lot(records))
        self.assertFalse(result["failed_share_within_allowance"])
        self.assertAlmostEqual(result["failed_fraction"], 0.25, places=9)

    def test_a_failed_share_landing_on_the_allowance_is_admissible(self):
        policy = copy.deepcopy(DEFAULT_DESIGNATION_POLICY)
        policy["max_failed_fraction"] = 0.25
        records = [_part("pd-00%d" % n) for n in (1, 2, 3, 4)]
        records[1] = _part("pd-002", modes=["solder-void-beyond-limit"])
        result = designate_lot(_lot(records), policy)
        self.assertTrue(result["failed_share_within_allowance"])

    def test_an_offered_part_with_no_record_is_undetermined(self):
        records = [_part("pd-00%d" % n) for n in (1, 2, 3)]
        result = designate_lot(_lot(records))
        self.assertEqual(result["unrecorded_part_ids"], ["pd-004"])
        self.assertIn("pd-004", result["undetermined_part_ids"])
        self.assertEqual(result["verdict"], POPULATION_DESIGNATION_INCOMPLETE)

    def test_a_record_for_a_part_the_lot_does_not_offer_is_reported(self):
        records = [_part("pd-00%d" % n) for n in (1, 2, 3, 4)] + [_part("pd-999")]
        result = designate_lot(_lot(records))
        self.assertEqual(result["foreign_record_ids"], ["pd-999"])
        self.assertEqual(result["verdict"], POPULATION_DESIGNATION_INCOMPLETE)

    def test_a_foreign_record_does_not_enter_the_deliverable_count(self):
        records = [_part("pd-00%d" % n) for n in (1, 2, 3, 4)] + [_part("pd-999")]
        result = designate_lot(_lot(records))
        self.assertEqual(result["deliverable_count"], 4)

    def test_an_undocumented_failed_part_leaves_the_lot_incomplete(self):
        records = [_part("pd-00%d" % n) for n in (1, 2, 3, 4)]
        records[2] = _part("pd-003", modes=["diode-body-crack"])
        del records[2]["nonconformance_reference"]
        result = designate_lot(_lot(records))
        self.assertEqual(result["undocumented_failed_ids"], ["pd-003"])
        self.assertEqual(result["verdict"], POPULATION_DESIGNATION_INCOMPLETE)

    def test_undetermined_parts_may_be_counted_where_the_policy_says_so(self):
        policy = copy.deepcopy(DEFAULT_DESIGNATION_POLICY)
        policy["count_undetermined_as_deliverable"] = True
        records = [_part("pd-00%d" % n) for n in (1, 2, 3, 4)]
        records[0] = _part("pd-001", inspection_complete=False)
        result = designate_lot(_lot(records), policy)
        self.assertEqual(result["deliverable_count"], 4)

    def test_designations_come_back_in_identifier_order(self):
        records = [_part("pd-00%d" % n) for n in (4, 1, 3, 2)]
        result = designate_lot(_lot(records))
        ids = [entry["part_id"] for entry in result["part_designations"]]
        self.assertEqual(ids, sorted(ids))

    def test_a_repeated_part_record_rejected(self):
        records = [_part("pd-001"), _part("pd-001")]
        with self.assertRaises(ValueError):
            designate_lot(_lot(records, offered=["pd-001"]))

    def test_a_lot_offering_nothing_rejected(self):
        with self.assertRaises(ValueError):
            designate_lot(_lot(offered=[]))

    def test_a_lot_without_an_identifier_rejected(self):
        lot = _lot()
        del lot["lot_id"]
        with self.assertRaises(ValueError):
            designate_lot(lot)

    def test_non_sequence_part_records_rejected(self):
        lot = _lot()
        lot["part_records"] = {"part_id": "pd-001"}
        with self.assertRaises(ValueError):
            designate_lot(lot)

    def test_the_lot_carries_every_part_finding(self):
        records = [_part("pd-00%d" % n) for n in (1, 2, 3, 4)]
        records[3] = _part("pd-004", modes=["contact-metallisation-lifted"])
        result = designate_lot(_lot(records))
        self.assertTrue(
            any(
                "contact-metallisation-lifted" in finding
                for finding in result["findings"]
            )
        )

    def test_the_designation_is_per_part_not_per_lot(self):
        records = [_part("pd-00%d" % n) for n in (1, 2, 3, 4)]
        records[0] = _part("pd-001", modes=["diode-body-crack"])
        result = designate_lot(_lot(records))
        words = {e["designation"] for e in result["part_designations"]}
        self.assertEqual(words, {DESIGNATION_FAILED, DESIGNATION_DELIVERABLE})


if __name__ == "__main__":
    unittest.main()
