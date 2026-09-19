#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 13.2 delivery-documentation leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_delivery_data_documentation.py
"""

import unittest

from q6005_delivery_data_documentation_logic import (
    ACCEPTANCE_COVERAGE_INDEX,
    DOCUMENTATION_TOLERANCE,
    HISTORY_PHASES,
    MANDATORY_RECORD_GROUPS,
    RECORD_GROUP_PHASE,
    RECORD_GROUP_WEIGHTS,
    RECORD_STATE_CREDIT,
    VERDICTS,
    assess_delivery_documentation,
    assess_record_group,
    documentation_coverage_index,
    nonconformance_findings,
    normalize_record_group,
    record_group_weight,
    record_state_credit,
    serial_evidence,
    unevidenced_phases,
)

SPARE_GROUP = "rework-and-repair-records"
DELIVERED = ["SN0001", "SN0002", "SN0003"]


def supplied_groups(**states):
    """Every record group supplied, with named exceptions."""
    groups = []
    for name in sorted(RECORD_GROUP_WEIGHTS):
        entry = {"group": name, "state": "supplied"}
        if name in states:
            entry["state"] = states[name]
        groups.append(entry)
    return groups


def graded(**states):
    """The same set, already graded."""
    return [assess_record_group(entry) for entry in supplied_groups(**states)]


def history(**overrides):
    """A quiet lot: nothing raised, nothing reworked, nothing waived."""
    record = {
        "nonconformances_raised": False,
        "units_reworked": False,
        "waivers_approved": False,
        "waiver_references_listed": False,
    }
    record.update(overrides)
    return record


def run(**overrides):
    """Grade one delivery data package."""
    case = {
        "lot_id": "HYB-1234-LOT-07",
        "delivered_serials": list(DELIVERED),
        "evidenced_serials": list(DELIVERED),
        "record_groups": supplied_groups(),
        "lot_history": history(),
    }
    case.update(overrides)
    return assess_delivery_documentation(**case)


class RecordGroupTests(unittest.TestCase):
    def test_every_record_group_names_a_history_phase(self):
        for name in RECORD_GROUP_WEIGHTS:
            self.assertIn(RECORD_GROUP_PHASE[name], HISTORY_PHASES, name)

    def test_every_mandatory_group_carries_a_published_weight(self):
        for name in MANDATORY_RECORD_GROUPS:
            self.assertIn(name, RECORD_GROUP_WEIGHTS)

    def test_an_unknown_record_group_is_rejected(self):
        with self.assertRaises(ValueError):
            record_group_weight("the-project-newsletter")

    def test_an_unknown_record_state_is_rejected(self):
        with self.assertRaises(ValueError):
            record_state_credit("probably-somewhere")

    def test_a_group_nobody_mentioned_defaults_to_not_supplied(self):
        self.assertEqual(normalize_record_group({"group": SPARE_GROUP})["state"], "not-supplied")

    def test_a_record_group_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_record_group([SPARE_GROUP])

    def test_a_supplied_group_earns_its_full_weight(self):
        record = assess_record_group({"group": SPARE_GROUP, "state": "supplied"})
        self.assertAlmostEqual(
            record["weighted_credit"], RECORD_GROUP_WEIGHTS[SPARE_GROUP], places=9
        )
        self.assertEqual(record["findings"], [])

    def test_an_illegible_copy_earns_less_than_a_partial_one(self):
        self.assertLess(
            RECORD_STATE_CREDIT["supplied-illegible"], RECORD_STATE_CREDIT["supplied-partial"]
        )

    def test_a_missing_mandatory_group_is_marked_missing(self):
        record = assess_record_group({"group": "screening-test-data"})
        self.assertTrue(record["mandatory_missing"])
        self.assertFalse(record["evidences_phase"])

    def test_an_illegible_mandatory_group_is_flagged_unusable_not_missing(self):
        record = assess_record_group(
            {"group": "lot-acceptance-test-data", "state": "supplied-illegible"}
        )
        self.assertTrue(record["mandatory_unusable"])
        self.assertFalse(record["mandatory_missing"])

    def test_a_full_package_reaches_a_full_coverage_index(self):
        self.assertAlmostEqual(documentation_coverage_index(graded()), 1.0, places=9)

    def test_an_empty_record_set_is_rejected(self):
        with self.assertRaises(ValueError):
            documentation_coverage_index([])


class PhaseChainTests(unittest.TestCase):
    def test_a_full_package_leaves_no_phase_unevidenced(self):
        self.assertEqual(unevidenced_phases(graded()), [])

    def test_dropping_the_screening_data_leaves_the_screening_phase_bare(self):
        gaps = unevidenced_phases(graded(**{"screening-test-data": "not-supplied"}))
        self.assertEqual(gaps, ["screening"])

    def test_an_illegible_group_does_not_evidence_its_phase(self):
        gaps = unevidenced_phases(graded(**{"final-electrical-test-data": "supplied-illegible"}))
        self.assertIn("final-electrical-test", gaps)

    def test_an_observation_still_evidences_the_phase(self):
        gaps = unevidenced_phases(
            graded(**{"lot-acceptance-test-data": "supplied-with-observation"})
        )
        self.assertEqual(gaps, [])

    def test_the_phases_are_reported_in_the_published_order(self):
        gaps = unevidenced_phases(
            graded(
                **{
                    "final-electrical-test-data": "not-supplied",
                    "chip-lot-acceptance-records": "not-supplied",
                    "incoming-material-and-part-records": "not-supplied",
                }
            )
        )
        self.assertEqual(gaps, ["material-and-chip-procurement", "final-electrical-test"])


class SerialEvidenceTests(unittest.TestCase):
    def test_a_fully_indexed_shipment_documents_every_unit(self):
        result = serial_evidence(DELIVERED, DELIVERED)
        self.assertTrue(result["all_delivered_units_documented"])
        self.assertAlmostEqual(result["serial_evidence_ratio"], 1.0, places=9)

    def test_a_unit_absent_from_the_index_is_named(self):
        result = serial_evidence(DELIVERED, ["SN0001", "SN0002"])
        self.assertEqual(result["undocumented_serials"], ["SN0003"])
        self.assertAlmostEqual(result["serial_evidence_ratio"], 2.0 / 3.0, places=9)

    def test_a_record_for_a_unit_that_was_not_shipped_is_named(self):
        result = serial_evidence(DELIVERED, DELIVERED + ["SN0099"])
        self.assertEqual(result["serials_documented_but_not_delivered"], ["SN0099"])

    def test_an_empty_shipment_is_rejected(self):
        with self.assertRaises(ValueError):
            serial_evidence([], [])

    def test_a_repeated_delivered_serial_is_rejected(self):
        with self.assertRaises(ValueError):
            serial_evidence(["SN0001", "SN0001"], ["SN0001"])

    def test_a_blank_serial_is_rejected(self):
        with self.assertRaises(ValueError):
            serial_evidence(["SN0001", "  "], ["SN0001"])


class LotHistoryTests(unittest.TestCase):
    def test_a_quiet_lot_raises_nothing(self):
        self.assertEqual(nonconformance_findings(history(), graded()), [])

    def test_a_lot_with_nonconformances_and_no_records_is_reported(self):
        findings = nonconformance_findings(
            history(nonconformances_raised=True),
            graded(**{"nonconformance-and-waiver-records": "not-supplied"}),
        )
        self.assertIn("nonconformances-raised-but-no-nonconformance-records", findings)

    def test_reworked_units_with_no_rework_records_are_reported(self):
        findings = nonconformance_findings(
            history(units_reworked=True), graded(**{SPARE_GROUP: "not-supplied"})
        )
        self.assertIn("units-reworked-but-no-rework-records", findings)

    def test_an_approved_waiver_that_is_never_referenced_is_reported(self):
        findings = nonconformance_findings(history(waivers_approved=True), graded())
        self.assertIn("approved-waivers-not-referenced-in-the-package", findings)

    def test_a_referenced_waiver_raises_nothing(self):
        findings = nonconformance_findings(
            history(waivers_approved=True, waiver_references_listed=True), graded()
        )
        self.assertEqual(findings, [])

    def test_a_history_flag_that_is_not_a_boolean_is_rejected(self):
        with self.assertRaises(ValueError):
            nonconformance_findings(history(units_reworked="maybe"), graded())


class WholePackageTests(unittest.TestCase):
    def test_a_sound_package_passes_with_no_findings(self):
        result = run()
        self.assertEqual(result["verdict"], "delivery-documentation-complete")
        self.assertTrue(result["package_accepted"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["documentation_coverage_index"], 1.0, places=9)

    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_a_package_missing_a_mandatory_group_is_incomplete(self):
        result = run(record_groups=supplied_groups(**{"screening-test-data": "not-supplied"}))
        self.assertEqual(result["verdict"], "delivery-documentation-assessment-incomplete")

    def test_an_undocumented_delivered_unit_makes_the_package_deficient(self):
        result = run(evidenced_serials=["SN0001", "SN0002"])
        self.assertEqual(result["verdict"], "delivery-documentation-deficient")
        self.assertIn(
            "delivered-unit-absent-from-the-records",
            [f["finding"] for f in result["findings"]],
        )

    def test_an_illegible_mandatory_group_makes_the_package_deficient(self):
        result = run(
            record_groups=supplied_groups(**{"lot-acceptance-test-data": "supplied-illegible"})
        )
        self.assertEqual(result["verdict"], "delivery-documentation-deficient")
        self.assertFalse(result["package_accepted"])

    def test_a_reworked_lot_with_no_rework_records_is_deficient(self):
        result = run(
            record_groups=supplied_groups(**{SPARE_GROUP: "not-supplied"}),
            lot_history=history(units_reworked=True),
        )
        self.assertEqual(result["verdict"], "delivery-documentation-deficient")

    def test_an_observation_on_an_optional_group_leaves_open_actions(self):
        result = run(record_groups=supplied_groups(**{SPARE_GROUP: "supplied-with-observation"}))
        self.assertEqual(result["verdict"], "delivery-documentation-complete-with-open-actions")
        self.assertTrue(result["package_accepted"])

    def test_a_group_nobody_listed_is_graded_as_not_supplied(self):
        result = run(record_groups=[{"group": SPARE_GROUP, "state": "supplied"}])
        states = {r["group"]: r["state"] for r in result["record_groups"]}
        self.assertEqual(states["in-process-inspection-records"], "not-supplied")
        self.assertEqual(len(result["record_groups"]), len(RECORD_GROUP_WEIGHTS))

    def test_a_repeated_record_group_is_rejected(self):
        with self.assertRaises(ValueError):
            run(record_groups=supplied_groups() + [{"group": SPARE_GROUP, "state": "supplied"}])

    def test_a_blank_lot_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(lot_id="   ")

    def test_a_record_group_set_that_is_not_a_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            run(record_groups={"group": SPARE_GROUP})


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(DOCUMENTATION_TOLERANCE, 1e-6)

    def test_the_record_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(RECORD_STATE_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(RECORD_STATE_CREDIT.values()), 0.0, places=9)

    def test_the_acceptance_index_sits_under_a_full_package(self):
        self.assertLess(ACCEPTANCE_COVERAGE_INDEX, 1.0)

    def test_every_history_phase_has_at_least_one_record_group_behind_it(self):
        phases = set(RECORD_GROUP_PHASE.values())
        for phase in HISTORY_PHASES:
            self.assertIn(phase, phases)


if __name__ == "__main__":
    unittest.main()
